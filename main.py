import math
import sys
from datetime import datetime
from typing import Any, List, Optional

import numpy as np
import ray

from ComputeTargets import (
    FullInstanton,
    InflatonTrajectory,
    InflatonTrajectoryProxy,
    SlowRollInstanton,
)
from ComputeTargets.CompactionFunction import (
    CompactionFunction,
    CompactionFunctionProxy,
)
from ComputeTargets.FullInstanton import FullInstantonProxy
from ComputeTargets.pipeline import PipelineWorkItem
from ComputeTargets.SlowRollInstanton import SlowRollInstantonProxy
from config.argument_parser import create_argument_parser
from config.grid_builder import build_gradient_grid, build_instanton_grid
from config.pipeline_setup import build_pipeline_inputs
from config.sharding import (
    ShardKeyType,
    get_shard_key_store_id,
    inventory_config,
    read_table_config,
    replicated_tables,
    sharded_tables,
)
from CosmologyConcepts import phi_value, pi_value
from CosmologyModels.cosmo_params import CosmologicalParams
from CosmologyModels.params import Planck2018
from Datastore.SQL.ProfileAgent import ProfileAgent
from Datastore.SQL.ShardedPool import ShardedPool
from InflationConcepts import (
    N_final,
    N_init,
    delta_Nstar,
    efold_array,
)
from MetadataConcepts import store_tag, tolerance
from RayTools.RayWorkPool import RayWorkPool, _default_store_handler
from Units import Planck_units
from Units.base import UnitsLike

VERSION_LABEL = "2026.6.1"

# Total pipeline depth: caps inflight items across ALL stages (lookup, compute,
# store, validation combined). Non-compute stages typically consume 10-20 slots,
# so this must be well above the desired compute parallelism. On a 10-core
# MacBook Pro, 50 keeps ~10 compute tasks queued in Ray while leaving headroom
# for the other stages. Raise further when moving to a larger machine.
#
# Used for the non-unified pipeline stages (Stages 2, 3, 4 individually), where
# each inflight slot maps to one @ray.remote(num_cpus=1) task. Ray's own CPU
# accounting limits active workers to the machine's core count; this cap mainly
# limits the queue depth above that floor.
MAX_INFLIGHT_PIPELINE = 50

# Unified-pipeline (--sample-grid-csv) cap. Each inflight slot here maps to
# THREE Python worker processes:
#   - one compute_pipeline orchestrator  (@ray.remote(num_cpus=0))
#   - one _compute_full_instanton task   (@ray.remote(num_cpus=1))
#   - one _compute_slow_roll_instanton   (@ray.remote(num_cpus=1))
#
# compute_pipeline is declared num_cpus=0 because it spends most of its time
# blocked in ray.get() waiting for sub-tasks; claiming a CPU during that wait
# would starve the sub-tasks it dispatched. But num_cpus=0 means Ray has no
# resource signal to auto-throttle concurrency — MAX_INFLIGHT_PIPELINE is the
# sole throttle. Using the full MAX_INFLIGHT_PIPELINE here would allow ~50
# orchestrators to run simultaneously, spawning ~150 Python workers and
# exhausting the OS open-file limit (typically ~256 fds on macOS).
#
# Setting this to MAX_INFLIGHT_PIPELINE // 3 keeps the peak Python worker count
# comparable to the non-unified stages while still preserving CPU saturation.
MAX_INFLIGHT_PIPELINE_UNIFIED = MAX_INFLIGHT_PIPELINE // 3

# Pipeline stage ordering — used to resolve --stop-after when multiple values
# are given (only the earliest stage wins).
_PIPELINE_STAGES = [
    "inflaton-trajectory",
    "full-instanton",
    "slow-roll-instanton",
    "compaction-function",
]

parser = create_argument_parser()
args = parser.parse_args()

if args.database is None:
    parser.print_help()
    sys.exit()

ray.init(address=args.ray_address)


def inflaton_trajectory_store_handler(obj, pool):
    """
    Custom store_handler for InflatonTrajectory.

    Calls obj.store() to resolve the Ray future and populate _raw_sample,
    then mints efold_value objects for each sample point via the pool, and
    assembles obj._values so the object is in the same fully-populated state
    as after a database load.
    """
    from ComputeTargets.InflatonTrajectory import InflatonTrajectoryValue

    obj.store()

    if obj.failure:
        # Nothing further to do for a failed trajectory.
        return

    raw = obj._raw_sample
    efold_objects = ray.get(
        pool.object_get(
            "efold_value",
            payload_data=[{"N": N} for N in raw["N_sample"]],
        )
    )

    obj._values = [
        InflatonTrajectoryValue(store_id=None, N=N_obj, phi=phi, pi=pi)
        for N_obj, phi, pi in zip(efold_objects, raw["phi"], raw["pi"])
    ]
    del obj._raw_sample


def _persist_pipeline_item(item: PipelineWorkItem, pool: ShardedPool, no_store_values: bool):
    """
    Persist FullInstanton, SlowRollInstanton, and CompactionFunction for one
    pipeline work item, in FK order: fi first, then sri, then cf.

    If fi or sri already exist in the database (scalar-only rows from a
    prior DOE run), their store_ids are reused and no new rows are inserted.
    Otherwise they are persisted as scalar-only (if no_store_values=True)
    or full-fidelity (if False).

    Returns the ObjectRef from pool.object_store(cf), which RayWorkPool
    awaits before calling the validation_handler.
    """
    fi = item.fi
    sri = item.sri
    cf = item.cf

    # ── FullInstanton ─────────────────────────────────────────────────────────
    if item.fi_existing is not None and item.fi_existing.available:
        # Reuse existing DB row as FK anchor — propagate its store_id to the
        # freshly-computed fi object. Since cf._full_instanton IS fi (Python
        # reference), this also fixes cf's FK reference.
        fi._my_id = item.fi_existing.store_id
    else:
        if no_store_values:
            fi.set_store_full_values(False)
        fi_stored = ray.get(pool.object_store(fi))
        fi._my_id = fi_stored.store_id
        ray.get(pool.object_validate(fi))

    # ── SlowRollInstanton ─────────────────────────────────────────────────────
    if item.sri_existing is not None and item.sri_existing.available:
        sri._my_id = item.sri_existing.store_id
    else:
        if no_store_values:
            sri.set_store_full_values(False)
        sri_stored = ray.get(pool.object_store(sri))
        sri._my_id = sri_stored.store_id
        ray.get(pool.object_validate(sri))

    # ── CompactionFunction ────────────────────────────────────────────────────
    # fi._my_id and sri._my_id are now set.
    # cf._full_instanton IS fi and cf._slow_roll_instanton IS sri
    # (reference semantics — set in PipelineWorkItem.store()), so
    # the factory's store() will read the correct FK serials automatically.
    if cf is None:
        # Both fi and sri failed — no CF to store. fi and sri were already
        # persisted above. Return ray.put(fi) so RayWorkPool can complete its
        # store→validate bookkeeping; fi.available is True and a second call to
        # pool.object_validate(fi) is idempotent for failed records.
        return ray.put(fi)

    if no_store_values:
        cf.set_store_full_values(False)

    return pool.object_store(cf)  # ObjectRef — RayWorkPool awaits this


def _run_pipeline_queue(
    pool: ShardedPool,
    task_list: list,
    key_fields,
    full_payload,
    shard_key_of,
    traj_proxies: list,
    cosmo,
    atol,
    rtol,
    dm,
    C_threshold: float,
    C_bar_threshold: float,
    no_store_values: bool,
    title: str = "STAGES 2+3+4: UNIFIED PIPELINE",
):
    """
    Unified pipeline queue: looks up pre-existing FullInstanton/SlowRollInstanton
    and CompactionFunction rows, then dispatches compute_pipeline for missing items.

    Pre-dispatch Steps A and B do scalar-only lookups for fi and sri (no value
    rows fetched). Step C does the CF existence check using those store_ids.
    The compute step runs a single RayWorkPool that computes all three targets
    per grid point in one Ray task via PipelineWorkItem.
    """
    ## Step A: vectorized FullInstanton lookup (scalar-only)
    binned = {}
    for item in task_list:
        binned.setdefault(shard_key_of(item), []).append(item)
    shard_keys = list(binned.keys())

    fi_query_queue = RayWorkPool(
        pool,
        shard_keys,
        task_builder=lambda key: pool.object_get_vectorized(
            "FullInstanton",
            key,
            payload_data=[
                {**key_fields(item), "_do_not_populate": True} for item in binned[key]
            ],
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=None,
        store_results=True,
        create_batch_size=20,
        process_batch_size=20,
    )
    fi_query_queue.run()

    fi_existing_map = {
        id(item): obj
        for key, objs in zip(shard_keys, fi_query_queue.results)
        for item, obj in zip(binned[key], objs)
    }

    ## Step B: vectorized SlowRollInstanton lookup (scalar-only)
    sri_query_queue = RayWorkPool(
        pool,
        shard_keys,
        task_builder=lambda key: pool.object_get_vectorized(
            "SlowRollInstanton",
            key,
            payload_data=[
                {**key_fields(item), "_do_not_populate": True} for item in binned[key]
            ],
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=None,
        store_results=True,
        create_batch_size=20,
        process_batch_size=20,
    )
    sri_query_queue.run()

    sri_existing_map = {
        id(item): obj
        for key, objs in zip(shard_keys, sri_query_queue.results)
        for item, obj in zip(binned[key], objs)
    }

    ## Step C: CF existence check using actual instanton store_ids.
    ## Only query for items where at least one instanton is in the DB; the rest
    ## trivially have no CF (FK constraint) and go straight into cf_missing.

    def cf_key_fields(item):
        model_idx, N_init_obj, N_final_obj, dns = item
        fi_obj = fi_existing_map[id(item)]
        sri_obj = sri_existing_map[id(item)]
        fi_proxy = FullInstantonProxy(fi_obj) if fi_obj.available else None
        sri_proxy = SlowRollInstantonProxy(sri_obj) if sri_obj.available else None
        return dict(
            trajectory=traj_proxies[model_idx],
            full_instanton=fi_proxy,
            slow_roll_instanton=sri_proxy,
            delta_Nstar=dns,
            cosmo=cosmo,
            C_threshold=C_threshold,
            C_bar_threshold=C_bar_threshold,
            atol=atol,
            rtol=rtol,
            tags=[],
        )

    skippable = [
        item
        for item in task_list
        if not fi_existing_map[id(item)].available
        and not sri_existing_map[id(item)].available
    ]
    checkable = [
        item
        for item in task_list
        if fi_existing_map[id(item)].available or sri_existing_map[id(item)].available
    ]

    cf_binned = {}
    for item in checkable:
        cf_binned.setdefault(shard_key_of(item), []).append(item)
    cf_shard_keys = list(cf_binned.keys())

    cf_query_queue = RayWorkPool(
        pool,
        cf_shard_keys,
        task_builder=lambda key: pool.object_get_vectorized(
            "CompactionFunction",
            key,
            payload_data=[
                {**cf_key_fields(item), "_do_not_populate": True}
                for item in cf_binned[key]
            ],
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=None,
        store_results=True,
        create_batch_size=20,
        process_batch_size=20,
    )
    cf_query_queue.run()

    cf_checkable_missing = [
        item
        for key, objs in zip(cf_shard_keys, cf_query_queue.results)
        for item, obj in zip(cf_binned[key], objs)
        if not obj.available
    ]
    cf_missing = cf_checkable_missing + skippable

    n_already = len(checkable) - len(cf_checkable_missing)
    n_skipped = len(skippable)
    print(
        f"\n** PIPELINE LOOKUP:\n"
        f"   -- {n_already} already computed, "
        f"{len(cf_missing)} to compute"
        + (f", {n_skipped} skipped (no instanton available)" if n_skipped > 0 else "")
    )

    if not cf_missing:
        return

    ## Compute step: single RayWorkPool for cf_missing
    def build_pipeline_item(item):
        model_idx, N_init_obj, N_final_obj, dns = item
        payload = full_payload(item)
        work_item = PipelineWorkItem(
            grid_item=item,
            traj_proxy=traj_proxies[model_idx],
            N_sample=payload["N_sample"],
            dm=dm,
            cosmo=cosmo,
            C_threshold=C_threshold,
            C_bar_threshold=C_bar_threshold,
            atol_obj=atol,
            rtol_obj=rtol,
            fi_existing=fi_existing_map[id(item)],
            sri_existing=sri_existing_map[id(item)],
        )
        return ray.put(work_item)

    def pipeline_store_handler(item, pool):
        item.store()

    def pipeline_persist_handler(item, pool):
        return _persist_pipeline_item(item, pool, no_store_values)

    pipeline_queue = RayWorkPool(
        pool,
        cf_missing,
        task_builder=build_pipeline_item,
        compute_handler=lambda obj, **kw: obj.compute(**kw),
        store_handler=pipeline_store_handler,
        persist_handler=pipeline_persist_handler,
        validation_handler=lambda obj: pool.object_validate(obj),
        label_builder=lambda obj: f"Pipeline(dNstar={float(obj.delta_Nstar):.4g})",
        title=title,
        store_results=False,
        create_batch_size=5,
        process_batch_size=3,
        max_task_queue=MAX_INFLIGHT_PIPELINE_UNIFIED,
    )
    pipeline_queue.run()


def _run_instanton_queue(
    pool: ShardedPool,
    cls_name: str,
    task_list: list,
    key_fields,
    full_payload,
    shard_key_of,
    label_builder,
    title: str,
    store_handler,
    no_store_values: bool = False,
):
    """
    Two-pass RayWorkPool pattern for instanton compute targets, flattened
    across every (model, N_init, N_final, delta_Nstar) combination at once.

    Pass 1 (query): determine which objects are already in the database.
    Existence checks are binned by shard key (delta_Nstar) and issued as one
    `object_get_vectorized()` call per distinct shard key, so the number of
    actor round-trips doesn't scale with the size of the N_init x N_final
    grid added on top of delta_Nstar.

    Pass 2 (work): compute and persist the missing ones, one Ray task per
    item, with pipeline depth capped at MAX_INFLIGHT_PIPELINE.

    `key_fields(item)` returns the cheap kwargs dict identifying the object
    (no N_sample) for Pass 1. `full_payload(item)` returns the full kwargs
    dict (including N_sample) for Pass 2. `shard_key_of(item)` returns the
    delta_Nstar shard key for binning. `label_builder(obj)` returns a
    human-readable label string for the compute step.

    `no_store_values`, when True, wraps the persist step so it calls
    `obj.set_store_full_values(False)` before `pool.object_store(obj)` —
    every compute target reachable through this helper (FullInstanton,
    SlowRollInstanton, GradientCoupledInstanton) implements
    `set_store_full_values`.
    """
    ## Pass 1: vectorized query, binned by shard key
    binned = {}
    for item in task_list:
        binned.setdefault(shard_key_of(item), []).append(item)

    shard_keys = list(binned.keys())

    query_queue = RayWorkPool(
        pool,
        shard_keys,
        task_builder=lambda key: pool.object_get_vectorized(
            cls_name,
            key,
            payload_data=[
                {**key_fields(item), "_do_not_populate": True} for item in binned[key]
            ],
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=None,  # title = None means this queue is silent on the console
        store_results=True,
        create_batch_size=20,
        process_batch_size=20,
    )
    query_queue.run()

    missing = [
        item
        for key, objs in zip(shard_keys, query_queue.results)
        for item, obj in zip(binned[key], objs)
        if not obj.available
    ]
    print(
        f"\n** {title.upper()} LOOKUP:\n"
        f"   -- {len(task_list) - len(missing)} already computed, "
        f"{len(missing)} to compute"
    )

    if not missing:
        return

    ## Pass 2: fetch full objects for missing items, then compute
    def build_work_ref(item):
        return pool.object_get(cls_name, **full_payload(item))

    if no_store_values:
        def persist_handler(obj, pool):
            obj.set_store_full_values(False)
            return pool.object_store(obj)
    else:
        persist_handler = lambda obj, pool: pool.object_store(obj)

    work_queue = RayWorkPool(
        pool,
        missing,
        task_builder=build_work_ref,
        compute_handler=lambda obj, **kwargs: obj.compute(**kwargs),
        store_handler=store_handler,
        persist_handler=persist_handler,
        validation_handler=lambda obj: pool.object_validate(obj),
        label_builder=label_builder,
        title=f"{title.upper()}",
        store_results=False,
        create_batch_size=5,
        process_batch_size=3,
        max_task_queue=MAX_INFLIGHT_PIPELINE,
    )
    work_queue.run()


def _build_N_sample(N_total: float, samples_per_N: float, pool: ShardedPool) -> efold_array:
    """
    Build the shared per-instanton e-fold sample grid used by BOTH the
    homogeneous and gradient branches: points at multiples of
    δ = 1/samples_per_N (so that grid points are reused across all
    instantons, keeping the efold_value table small), plus the exact
    endpoint N_total so that downstream radial-profile extraction starts
    from the true instanton endpoint rather than a grid point that may be
    up to δ/2 away.

    Both branches must agree on this convention for any homogeneous-vs-
    gradient comparison at the same grid point to be apples-to-apples —
    do not duplicate this logic at either call site.
    """
    step = 1.0 / samples_per_N
    n_steps = math.floor(N_total * samples_per_N)
    shared_points = [i * step for i in range(n_steps + 1)]
    if abs(n_steps * step - N_total) > 1e-12 * max(N_total, 1.0):
        N_grid = shared_points + [N_total]
    else:
        N_grid = shared_points
    efold_objs = ray.get(
        pool.object_get("efold_value", payload_data=[{"N": N} for N in N_grid])
    )
    return efold_array(efold_objs)


def _run_gradient_branch(
    pool: ShardedPool,
    base_grid: list,
    n_collocation_points_array: list,
    alpha_regularization_array: list,
    traj_proxies: list,
    cosmo,
    atol: tolerance,
    rtol: tolerance,
    dm,
    samples_per_N: float,
    no_store_values: bool,
    wallclock_budget_seconds: Optional[float] = None,
    max_step: Optional[float] = None,
):
    """
    Gradient (onion-model) branch: dispatch GradientCoupledInstanton across
    the base (model, N_init, N_final, delta_Nstar) grid crossed against
    n_collocation_points and alpha_regularization.

    wallclock_budget_seconds, max_step (prompt 24 prerequisite): forwarded
    unchanged into every GradientCoupledInstanton's constructor kwargs (see
    key_fields below) -- runtime-only knobs, not part of the object's
    persisted identity (same treatment as full_instanton). None (default)
    preserves the pre-prompt-24 unbounded behaviour.
    """
    ## Pass 0 (prompt 21a): fetch the upstream FullInstanton -- POPULATED,
    ## since its per-sample (N, phi2) values are what seeds the SAT closure's
    ## lagged pi_core target -- for each BASE grid point (not the full
    ## gradient_grid: many (n_collocation_points, alpha_regularization)
    ## combinations share the same underlying FullInstanton, so this is
    ## O(len(base_grid)) round trips, not O(len(gradient_grid))). Best
    ## effort: a missing/failed/unpopulated FullInstanton just means
    ## GradientCoupledInstanton.py's own Ray remote function falls back to
    ## computing one inline (picard.solve_picard's own fetch-then-fallback);
    ## it never blocks the gradient branch.
    def _base_key_fields(item) -> dict:
        model_idx, N_init_obj, N_final_obj, dns_obj = item
        return dict(
            trajectory=traj_proxies[model_idx],
            N_init=N_init_obj, N_final=N_final_obj, delta_Nstar=dns_obj,
            atol=atol, rtol=rtol, tags=[], diffusion_model=dm,
        )

    def _base_shard_key(item):
        return item[3]  # delta_Nstar

    fi_seed_binned = {}
    for item in base_grid:
        fi_seed_binned.setdefault(_base_shard_key(item), []).append(item)
    fi_seed_shard_keys = list(fi_seed_binned.keys())

    fi_seed_queue = RayWorkPool(
        pool,
        fi_seed_shard_keys,
        task_builder=lambda key: pool.object_get_vectorized(
            "FullInstanton",
            key,
            payload_data=[_base_key_fields(item) for item in fi_seed_binned[key]],
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=None,
        store_results=True,
        create_batch_size=20,
        process_batch_size=20,
    )
    fi_seed_queue.run()

    fi_proxy_by_base_id = {}
    for key, objs in zip(fi_seed_shard_keys, fi_seed_queue.results):
        for item, obj in zip(fi_seed_binned[key], objs):
            fi_proxy_by_base_id[id(item)] = (
                FullInstantonProxy(obj) if obj.available and not obj.failure else None
            )

    gradient_grid = build_gradient_grid(
        base_grid, n_collocation_points_array, alpha_regularization_array
    )
    n_base = len(base_grid)
    n_ncp = len(n_collocation_points_array)
    n_alpha = len(alpha_regularization_array)
    n_fi_seeds = sum(1 for v in fi_proxy_by_base_id.values() if v is not None)
    print(
        f"\n   >> gradient branch: {n_base} base grid point(s) x "
        f"{n_ncp} n_collocation_points value(s) x {n_alpha} alpha_regularization "
        f"value(s) = {len(gradient_grid)} gradient instanton combination(s)\n"
        f"   >> SAT closure seed: {n_fi_seeds}/{n_base} base grid point(s) have "
        f"an already-computed FullInstanton available to seed from"
    )

    def key_fields(item) -> dict:
        base_item, ncp_obj, alpha_obj = item
        model_idx, N_init_obj, N_final_obj, dns_obj = base_item
        return dict(
            trajectory=traj_proxies[model_idx],
            N_init=N_init_obj, N_final=N_final_obj, delta_Nstar=dns_obj,
            n_collocation_points=ncp_obj, alpha_regularization=alpha_obj,
            atol=atol, rtol=rtol, cosmo=cosmo, diffusion_model=dm, tags=[],
            full_instanton=fi_proxy_by_base_id.get(id(base_item)),
            wallclock_budget_seconds=wallclock_budget_seconds,
            max_step=max_step,
        )

    def full_payload(item) -> dict:
        base_item, ncp_obj, alpha_obj = item
        model_idx, N_init_obj, N_final_obj, dns_obj = base_item
        N_total = (float(N_init_obj) - float(N_final_obj)) + float(dns_obj)
        payload = key_fields(item)
        payload["N_sample"] = _build_N_sample(N_total, samples_per_N, pool)
        return payload

    def shard_key_of(item):
        base_item, _, _ = item
        return base_item[3]  # delta_Nstar

    _run_instanton_queue(
        pool=pool, cls_name="GradientCoupledInstanton", task_list=gradient_grid,
        key_fields=key_fields, full_payload=full_payload, shard_key_of=shard_key_of,
        label_builder=lambda obj: (
            f"GradientCoupledInstanton(dNstar={float(obj.delta_Nstar):.4g}, "
            f"Ninit={float(obj.N_init_value):.4g}, Nfinal={float(obj.N_final_value):.4g}, "
            f"n_colloc={int(obj.n_collocation_points_value)}, "
            f"alpha={float(obj.alpha_regularization_value):.4g})"
        ),
        store_handler=_default_store_handler,
        title="STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS",
        no_store_values=no_store_values,
    )


def run_all_pipelines(
    pool: ShardedPool,
    model_list: List[dict],
    grid: list,
    phi0: phi_value,
    pi0: pi_value,
    samples_per_N: float,
    atol: tolerance,
    rtol: tolerance,
    cosmo,  # CosmologicalParams instance
    targets: List[str],
    n_collocation_points_array: Optional[list] = None,
    alpha_regularization_array: Optional[list] = None,
    diffusion_model=None,
    stop_after: Optional[str] = None,
    no_store_values: bool = False,
):
    """
    Run the full pipeline across every model at once, flattened into a single
    queue per stage. This keeps workers busy across model/grid boundaries —
    no worker idles waiting for the last instanton of one model's grid to
    finish before the next model's trajectory (and instanton grid) becomes
    available.
    """
    dm = diffusion_model
    if dm is None or not dm.available:
        raise ValueError(
            "run_all_pipelines(): diffusion_model must be provided and persisted. "
            "Call pool.object_get('MasslessDecoupledDiffusion') first."
        )

    ## -----------------------------------------------------------------------
    ## STAGE 1: Background inflaton trajectories — one flat queue, all models
    ## -----------------------------------------------------------------------

    traj_payloads = [
        dict(
            phi0=phi0,
            pi0=pi0,
            potential=model_data["potential"],
            atol=atol,
            rtol=rtol,
            samples_per_N=samples_per_N,
            tags=[],
        )
        for model_data in model_list
    ]

    traj_queue = RayWorkPool(
        pool,
        traj_payloads,
        task_builder=lambda p: pool.object_get("InflatonTrajectory", **p),
        compute_handler=lambda obj, **kwargs: obj.compute(**kwargs),
        store_handler=inflaton_trajectory_store_handler,
        persist_handler=lambda obj, pool: pool.object_store(obj),
        validation_handler=lambda obj: pool.object_validate(obj),
        label_builder=lambda obj: "InflatonTrajectory",
        title="STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES",
        store_results=True,
        create_batch_size=len(traj_payloads),
        process_batch_size=len(traj_payloads),
    )
    traj_queue.run()

    traj_proxies = []
    for model_data, traj_obj in zip(model_list, traj_queue.results):
        if not traj_obj.available:
            raise RuntimeError(
                f"InflatonTrajectory for model {model_data['label']} is not "
                f"available after compute queue"
            )
        traj_proxies.append(InflatonTrajectoryProxy(traj_obj))

    if stop_after == "inflaton-trajectory":
        print("\n** Stopping after Stage 1 (--stop-after inflaton-trajectory)")
        return

    def _run_homogeneous_branch():
        def key_fields(item) -> dict:
            """Cheap identifying fields only — no N_sample. Used for Pass-1
            existence checks, so we don't pay for minting an e-fold grid just to
            find out the object is already in the database. atol/rtol must be
            included here (not just in full_payload): the factory's lookup query
            matches on atol_serial/rtol_serial in addition to trajectory, N_init,
            N_final and delta_Nstar."""
            model_idx, N_init, N_final, dns = item
            return dict(
                trajectory=traj_proxies[model_idx],
                N_init=N_init,
                N_final=N_final,
                delta_Nstar=dns,
                atol=atol,
                rtol=rtol,
                tags=[],
                diffusion_model=dm,
            )

        def full_payload(item) -> dict:
            model_idx, N_init, N_final, dns = item
            N_total = (float(N_init) - float(N_final)) + float(dns)
            payload = key_fields(item)
            payload["N_sample"] = _build_N_sample(N_total, samples_per_N, pool)
            payload["diffusion_model"] = dm
            return payload

        def shard_key_of(item):
            _, _, _, dns = item
            return dns

        C_THRESHOLD = 0.4
        C_BAR_THRESHOLD = 0.4

        if no_store_values:
            # Unified pipeline: compute all three targets per grid point in a single
            # Ray task. Stages 2, 3, and 4 are merged.
            if stop_after in {"full-instanton", "slow-roll-instanton"}:
                print(
                    f"\n!! WARNING: --stop-after {stop_after!r} is not supported in "
                    f"pipeline mode (--no-store-values). The full pipeline will run "
                    f"(FullInstanton + SlowRollInstanton + CompactionFunction)."
                )
            _run_pipeline_queue(
                pool=pool,
                task_list=grid,
                key_fields=key_fields,
                full_payload=full_payload,
                shard_key_of=shard_key_of,
                traj_proxies=traj_proxies,
                cosmo=cosmo,
                atol=atol,
                rtol=rtol,
                dm=dm,
                C_threshold=C_THRESHOLD,
                C_bar_threshold=C_BAR_THRESHOLD,
                no_store_values=True,
            )
            return

        ## -----------------------------------------------------------------------
        ## STAGE 2: Full MSR instantons — one flat queue, all models and grid points
        ## -----------------------------------------------------------------------

        _run_instanton_queue(
            pool=pool,
            cls_name="FullInstanton",
            task_list=grid,
            key_fields=key_fields,
            full_payload=full_payload,
            shard_key_of=shard_key_of,
            label_builder=lambda obj: (
                f"FullInstanton(dNstar={float(obj.delta_Nstar):.4g}, "
                f"Ninit={float(obj.N_init_value):.4g}, "
                f"Nfinal={float(obj.N_final_value):.4g})"
            ),
            store_handler=_default_store_handler,
            title="STAGE 2: FULL MSR INSTANTONS",
        )

        if stop_after == "full-instanton":
            print("\n** Stopping after Stage 2 (--stop-after full-instanton)")
            return

        ## -----------------------------------------------------------------------
        ## STAGE 3: Slow-roll instantons — one flat queue, all models and grid points
        ## -----------------------------------------------------------------------

        _run_instanton_queue(
            pool=pool,
            cls_name="SlowRollInstanton",
            task_list=grid,
            key_fields=key_fields,
            full_payload=full_payload,
            shard_key_of=shard_key_of,
            label_builder=lambda obj: (
                f"SlowRollInstanton(dNstar={float(obj.delta_Nstar):.4g}, "
                f"Ninit={float(obj.N_init_value):.4g}, "
                f"Nfinal={float(obj.N_final_value):.4g})"
            ),
            store_handler=_default_store_handler,
            title="STAGE 3: SLOW-ROLL INSTANTONS",
        )

        if stop_after == "slow-roll-instanton":
            print("\n** Stopping after Stage 3 (--stop-after slow-roll-instanton)")
            return

        ## -----------------------------------------------------------------------
        ## STAGE 4: Compaction functions — two-pass pattern with upstream lookup
        ## -----------------------------------------------------------------------

        print("\n** STAGE 4: COMPACTION FUNCTIONS")

        ## Pass 1a: look up FullInstanton for ALL grid items, binned by shard key.
        ## We need instanton store_ids before we can do the CF existence check, since
        ## the CompactionFunction factory matches on full_instanton_serial and
        ## slow_roll_instanton_serial as part of its identity query.
        fi_binned_all = {}
        for item in grid:
            fi_binned_all.setdefault(shard_key_of(item), []).append(item)
        fi_shard_keys_all = list(fi_binned_all.keys())

        fi_lookup_all_queue = RayWorkPool(
            pool,
            fi_shard_keys_all,
            task_builder=lambda key: pool.object_get_vectorized(
                "FullInstanton",
                key,
                payload_data=[
                    {**key_fields(item), "_do_not_populate": True}
                    for item in fi_binned_all[key]
                ],
            ),
            compute_handler=None,
            store_handler=None,
            persist_handler=None,
            validation_handler=None,
            title=None,
            store_results=True,
            create_batch_size=20,
            process_batch_size=20,
        )
        fi_lookup_all_queue.run()

        fi_results_all = {
            id(item): obj
            for key, objs in zip(fi_shard_keys_all, fi_lookup_all_queue.results)
            for item, obj in zip(fi_binned_all[key], objs)
        }

        ## Pass 1b: look up SlowRollInstanton for ALL grid items
        sr_lookup_all_queue = RayWorkPool(
            pool,
            fi_shard_keys_all,
            task_builder=lambda key: pool.object_get_vectorized(
                "SlowRollInstanton",
                key,
                payload_data=[
                    {**key_fields(item), "_do_not_populate": True}
                    for item in fi_binned_all[key]
                ],
            ),
            compute_handler=None,
            store_handler=None,
            persist_handler=None,
            validation_handler=None,
            title=None,
            store_results=True,
            create_batch_size=20,
            process_batch_size=20,
        )
        sr_lookup_all_queue.run()

        sr_results_all = {
            id(item): obj
            for key, objs in zip(fi_shard_keys_all, sr_lookup_all_queue.results)
            for item, obj in zip(fi_binned_all[key], objs)
        }

        ## Pass 1c: CF existence check using actual instanton store_ids.
        ## Only check items where at least one instanton is available; the rest are
        ## skipped entirely (no upstream data to compute a CF from).

        def cf_key_fields(item) -> dict:
            """Identifying fields for the CF existence check. Includes instanton proxies
            so the factory can match on full_instanton_serial / slow_roll_instanton_serial."""
            model_idx, N_init_obj, N_final_obj, dns = item
            fi_obj = fi_results_all[id(item)]
            sr_obj = sr_results_all[id(item)]
            fi_proxy = FullInstantonProxy(fi_obj) if fi_obj.available else None
            sr_proxy = SlowRollInstantonProxy(sr_obj) if sr_obj.available else None
            return dict(
                trajectory=traj_proxies[model_idx],
                full_instanton=fi_proxy,
                slow_roll_instanton=sr_proxy,
                delta_Nstar=dns,
                cosmo=cosmo,
                C_threshold=C_THRESHOLD,
                C_bar_threshold=C_BAR_THRESHOLD,
                atol=atol,
                rtol=rtol,
                tags=[],
            )

        checkable = [
            item
            for item in grid
            if fi_results_all[id(item)].available or sr_results_all[id(item)].available
        ]

        cf_binned = {}
        for item in checkable:
            cf_binned.setdefault(shard_key_of(item), []).append(item)
        cf_shard_keys = list(cf_binned.keys())

        cf_query_queue = RayWorkPool(
            pool,
            cf_shard_keys,
            task_builder=lambda key: pool.object_get_vectorized(
                "CompactionFunction",
                key,
                payload_data=[
                    {**cf_key_fields(item), "_do_not_populate": True}
                    for item in cf_binned[key]
                ],
            ),
            compute_handler=None,
            store_handler=None,
            persist_handler=None,
            validation_handler=None,
            title=None,
            store_results=True,
            create_batch_size=20,
            process_batch_size=20,
        )
        cf_query_queue.run()

        cf_missing = [
            item
            for key, objs in zip(cf_shard_keys, cf_query_queue.results)
            for item, obj in zip(cf_binned[key], objs)
            if not obj.available
        ]

        n_no_instanton = len(grid) - len(checkable)
        print(
            f"\n** COMPACTION FUNCTIONS LOOKUP:\n"
            f"   -- {len(checkable) - len(cf_missing)} already computed, "
            f"{len(cf_missing)} to compute"
            + (
                f", {n_no_instanton} skipped (no instanton available)"
                if n_no_instanton > 0
                else ""
            )
        )

        if cf_missing:
            ## Pass 2a: re-fetch FullInstantons WITH population for the missing CF items.
            ## The Pass 1a objects were fetched with _do_not_populate=True, so their
            ## _values lists are empty.  Wrapping one in a proxy and passing it to
            ## _compute_compaction_function would cause "no sample values" immediately.
            fi_binned_missing = {}
            for item in cf_missing:
                fi_binned_missing.setdefault(shard_key_of(item), []).append(item)
            fi_shard_keys_missing = list(fi_binned_missing.keys())

            fi_refetch_queue = RayWorkPool(
                pool,
                fi_shard_keys_missing,
                task_builder=lambda key: pool.object_get_vectorized(
                    "FullInstanton",
                    key,
                    payload_data=[key_fields(item) for item in fi_binned_missing[key]],
                ),
                compute_handler=None,
                store_handler=None,
                persist_handler=None,
                validation_handler=None,
                title=None,
                store_results=True,
                create_batch_size=20,
                process_batch_size=20,
            )
            fi_refetch_queue.run()

            fi_results_compute = {
                id(item): obj
                for key, objs in zip(fi_shard_keys_missing, fi_refetch_queue.results)
                for item, obj in zip(fi_binned_missing[key], objs)
            }

            ## Pass 2b: same for SlowRollInstanton
            sr_refetch_queue = RayWorkPool(
                pool,
                fi_shard_keys_missing,
                task_builder=lambda key: pool.object_get_vectorized(
                    "SlowRollInstanton",
                    key,
                    payload_data=[key_fields(item) for item in fi_binned_missing[key]],
                ),
                compute_handler=None,
                store_handler=None,
                persist_handler=None,
                validation_handler=None,
                title=None,
                store_results=True,
                create_batch_size=20,
                process_batch_size=20,
            )
            sr_refetch_queue.run()

            sr_results_compute = {
                id(item): obj
                for key, objs in zip(fi_shard_keys_missing, sr_refetch_queue.results)
                for item, obj in zip(fi_binned_missing[key], objs)
            }

            def build_cf_work_ref(item):
                model_idx, N_init_obj, N_final_obj, dns = item

                fi_obj = fi_results_compute[id(item)]
                sr_obj = sr_results_compute[id(item)]

                fi_proxy = FullInstantonProxy(fi_obj) if fi_obj.available else None
                sr_proxy = SlowRollInstantonProxy(sr_obj) if sr_obj.available else None

                if fi_proxy is None and sr_proxy is None:
                    return None

                return pool.object_get(
                    "CompactionFunction",
                    trajectory=traj_proxies[model_idx],
                    full_instanton=fi_proxy,
                    slow_roll_instanton=sr_proxy,
                    delta_Nstar=dns,
                    cosmo=cosmo,
                    C_threshold=C_THRESHOLD,
                    C_bar_threshold=C_BAR_THRESHOLD,
                    atol=atol,
                    rtol=rtol,
                    tags=[],
                )

            cf_work_queue = RayWorkPool(
                pool,
                cf_missing,
                task_builder=build_cf_work_ref,
                compute_handler=lambda obj, **kwargs: obj.compute(**kwargs),
                store_handler=_default_store_handler,
                persist_handler=lambda obj, pool: pool.object_store(obj),
                validation_handler=lambda obj: pool.object_validate(obj),
                label_builder=lambda obj: (
                    f"CompactionFunction(dNstar={float(obj.delta_Nstar):.4g})"
                ),
                title="STAGE 4: COMPACTION FUNCTIONS AND MASSES",
                store_results=False,
                create_batch_size=5,
                process_batch_size=3,
                max_task_queue=MAX_INFLIGHT_PIPELINE,
            )
            cf_work_queue.run()

    if "homogeneous" in targets:
        _run_homogeneous_branch()
    else:
        print("\n** Skipping homogeneous branch (--targets excludes 'homogeneous')")

    if "gradient" in targets:
        _run_gradient_branch(
            pool=pool, base_grid=grid,
            n_collocation_points_array=n_collocation_points_array,
            alpha_regularization_array=alpha_regularization_array,
            traj_proxies=traj_proxies, cosmo=cosmo, atol=atol, rtol=rtol, dm=dm,
            samples_per_N=samples_per_N, no_store_values=no_store_values,
            wallclock_budget_seconds=args.gci_wallclock_budget_seconds,
            max_step=args.gci_max_step,
        )
    else:
        print("\n** Skipping gradient branch (--targets excludes 'gradient')")


def execute(pool: ShardedPool, units: UnitsLike):
    """
    Set up parameter grids, register database objects, and run the flattened
    work queues across every model.
    """
    ## -----------------------------------------------------------------------
    ## BUILD PARAMETER GRIDS AND REGISTER DATABASE OBJECTS
    ## -----------------------------------------------------------------------
    print("\n** BUILDING PARAMETER SAMPLING GRIDS")
    print(f'   -- using potential type "{args.potential_type}"')
    if getattr(args, "sample_grid_csv", None):
        print(
            f"   -- sample-grid-csv: active — "
            f"N_init/N_final/delta_Nstar taken from '{args.sample_grid_csv}'"
        )
    inputs = build_pipeline_inputs(pool, units, args)
    atol, rtol = inputs["atol"], inputs["rtol"]
    phi0, pi0 = inputs["phi0"], inputs["pi0"]
    N_init_array = inputs["N_init_array"]
    N_final_array = inputs["N_final_array"]
    dns_objects = inputs["dns_array"]
    n_collocation_points_array = inputs["n_collocation_points_array"]
    alpha_regularization_array = inputs["alpha_regularization_array"]
    model_list = inputs["model_list"]

    ## -----------------------------------------------------------------------
    ## SAMPLING DENSITY
    ## -----------------------------------------------------------------------
    samples_per_N = args.samples_per_N
    print(f"   -- time sampling: {samples_per_N:.4g} samples per e-fold")

    ## -----------------------------------------------------------------------
    ## BUILD INSTANTON PARAMETER GRID
    ## -----------------------------------------------------------------------
    grid = build_instanton_grid(pool, model_list, args, N_init_array, N_final_array, dns_objects)

    n_models = len(model_list)
    if getattr(args, "sample_grid_csv", None):
        n_csv = len(grid) // n_models if n_models > 0 else len(grid)
        total_combinations = len(grid)
        print(
            f"\n   >> {n_models} model{'s' if n_models != 1 else ''} × "
            f"{n_csv} CSV sample point{'s' if n_csv != 1 else ''} = "
            f"{total_combinations} instanton combination{'s' if total_combinations != 1 else ''}"
        )
    else:
        per_model_combinations = len(N_init_array) * len(N_final_array) * len(dns_objects)
        total_combinations = n_models * per_model_combinations
        print(
            f"\n   >> {n_models} model{'s' if n_models != 1 else ''} and "
            f"{len(N_init_array)} x {len(N_final_array)} x {len(dns_objects)} "
            f"N_init/N_final/delta_Nstar grid = {per_model_combinations} "
            f"parameter combination{'s' if per_model_combinations != 1 else ''} per model = "
            f"{total_combinations} instanton combinations"
        )

    ## -----------------------------------------------------------------------
    ## REGISTER COSMOLOGICAL PARAMETERS
    ## -----------------------------------------------------------------------
    cosmo = ray.get(pool.object_get("CosmologicalParams", params=Planck2018()))
    print(f"\n** COSMOLOGICAL PARAMETERS: {cosmo.name} (store_id={cosmo.store_id})")

    ## -----------------------------------------------------------------------
    ## BUILD MODEL LIST AND RUN PIPELINE
    ## -----------------------------------------------------------------------
    dm = ray.get(pool.object_get("MasslessDecoupledDiffusion"))
    print(f"\n** DIFFUSION MODEL: {dm.name} (store_id={dm.store_id})")

    # If multiple --stop-after stages are given, keep only the earliest in pipeline order.
    stop_after = None
    if args.stop_after:
        matches = [s for s in _PIPELINE_STAGES if s in args.stop_after]
        if matches:
            stop_after = matches[0]

    if stop_after is not None and "homogeneous" not in args.targets:
        print(
            f"\n!! WARNING: --stop-after {stop_after!r} has no effect since "
            f"'homogeneous' is not selected in --targets {args.targets!r}"
        )

    run_all_pipelines(
        pool=pool,
        model_list=model_list,
        grid=grid,
        phi0=phi0,
        pi0=pi0,
        samples_per_N=samples_per_N,
        atol=atol,
        rtol=rtol,
        cosmo=cosmo,
        targets=args.targets,
        n_collocation_points_array=n_collocation_points_array,
        alpha_regularization_array=alpha_regularization_array,
        diffusion_model=dm,
        stop_after=stop_after,
        no_store_values=args.no_store_values,
    )


def inventory(pool: ShardedPool, units: UnitsLike):
    print("\n@@ DATASTORE INVENTORY")
    # delta_Nstar values
    _inventory_dimensionless(pool, "delta_Nstar", "Delta N★ values")
    # N_init, N_final values
    _inventory_dimensionless(pool, "N_init", "N_init values")
    _inventory_dimensionless(pool, "N_final", "N_final values")
    # phi0, pi0
    _inventory_dimensionful(pool, "phi_value", "phi_0 values", units)
    _inventory_dimensionful(pool, "pi_value", "pi_0 values", units)
    # inflaton_mass, quartic_coupling
    _inventory_dimensionful(pool, "inflaton_mass", "Inflaton mass values", units)
    _inventory_dimensionless(pool, "quartic_coupling", "Quartic coupling values")
    # efold values
    _inventory_efold(pool)
    # Compute targets
    _inventory_object(pool, "InflatonTrajectory", "Inflaton trajectories")
    _inventory_object(pool, "FullInstanton", "Full MSR instantons")
    _inventory_object(pool, "SlowRollInstanton", "Slow-roll instantons")
    _inventory_object(pool, "CompactionFunction", "Compaction functions")
    _inventory_object(pool, "GradientCoupledInstanton", "Gradient-coupled (onion model) instantons")


def _inventory_dimensionless(pool, type_name, label):
    print(f"\n   -- {label}")
    try:
        data = pool.inventory(type_name)
        vals = sorted(data.get("values", []))
        _print_value_list(vals, fmt=lambda v: f"{v:.6g}")
    except Exception as e:
        print(f"      (error: {e})")


def _inventory_dimensionful(pool, type_name, label, units):
    print(f"\n   -- {label}")
    try:
        data = pool.inventory(type_name, units)
        unit_name = data.get("unit", "?")
        unit_val = getattr(units, unit_name, 1.0)
        vals = sorted(data.get("values", []))
        _print_value_list(vals, fmt=lambda v: f"{v / unit_val:.6g} {unit_name}")
    except Exception as e:
        print(f"      (error: {e})")


def _inventory_efold(pool):
    print("\n   -- E-fold sample values")
    try:
        data = pool.inventory("efold_value")
        vals = sorted(data.get("values", []))
        _print_value_list(vals, fmt=lambda v: f"{v:.6g}")
    except Exception as e:
        print(f"      (error: {e})")


def _inventory_object(pool, type_name, label):
    print(f"\n   -- {label}")
    try:
        data = pool.inventory(type_name)
        for group_name, group in [
            ("validated", data.get("validated", {})),
            ("unvalidated", data.get("unvalidated", {})),
        ]:
            labels = sorted(group.get("labels", []))
            n = len(labels)
            ts_early = group.get("earliest_timestamp")
            ts_late = group.get("latest_timestamp")
            print(f"      @@ {group_name}: {n} record(s)", end="")
            if ts_early:
                print(
                    f" | {ts_early.strftime('%Y-%m-%d %H:%M')} – "
                    f"{ts_late.strftime('%H:%M')}",
                    end="",
                )
            print()
            _print_label_list(labels)
    except Exception as e:
        print(f"      (error: {e})")


def _print_value_list(vals, fmt):
    n = len(vals)
    if n == 0:
        print("      no values committed")
    elif n <= 20:
        print(f"      {n} value(s): [ {', '.join(fmt(v) for v in vals)} ]")
    else:
        low = [fmt(v) for v in vals[:10]]
        high = [fmt(v) for v in vals[-10:]]
        print(f"      {n} values: [ {', '.join(low)}, ..., {', '.join(high)} ]")


def _print_label_list(labels):
    if not labels:
        return
    show = labels if len(labels) <= 10 else labels[:5] + ["..."] + labels[-5:]
    for lbl in show:
        print(f"         :: {lbl}")


# ── ProfileAgent (optional) ──────────────────────────────────────────────────
profile_agent = None
if args.profile_db is not None:
    ts = datetime.now().replace(microsecond=0).isoformat()
    if args.job_name:
        lbl = f'{VERSION_LABEL}-job-"{args.job_name}"-db-"{args.database}"-{ts}'
    else:
        lbl = f'{VERSION_LABEL}-db-"{args.database}"-shards-{args.shards}-{ts}'
    profile_agent = ProfileAgent.options(name="ProfileAgent").remote(
        db_name=args.profile_db,
        timeout=args.db_timeout,
        label=lbl,
    )

# ── ShardedPool ───────────────────────────────────────────────────────────────
with ShardedPool(
    version_label=VERSION_LABEL,
    db_name=args.database,
    ShardKeyType=ShardKeyType,
    ShardKeyStoreIdGetter=get_shard_key_store_id,
    replicated_tables=replicated_tables,
    sharded_tables=sharded_tables,
    timeout=args.db_timeout,
    shards=args.shards,
    profile_agent=profile_agent,
    job_name=args.job_name,
    prune_unvalidated=args.prune_unvalidated,
    drop_actions=args.drop,
    read_table_config=read_table_config,
    inventory_config=inventory_config,
) as pool:
    units = Planck_units()
    if args.inventory:
        inventory(pool, units)
    else:
        execute(pool, units)
