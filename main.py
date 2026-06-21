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
from ComputeTargets.SlowRollInstanton import SlowRollInstantonProxy
from config.argument_parser import create_argument_parser
from config.grid_builder import build_instanton_grid
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
    MasslessDecoupledDiffusion,
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
MAX_INFLIGHT_PIPELINE = 50

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

    work_queue = RayWorkPool(
        pool,
        missing,
        task_builder=build_work_ref,
        compute_handler=lambda obj, **kwargs: obj.compute(**kwargs),
        store_handler=store_handler,
        persist_handler=lambda obj, pool: pool.object_store(obj),
        validation_handler=lambda obj: pool.object_validate(obj),
        label_builder=label_builder,
        title=f"{title.upper()}",
        store_results=False,
        create_batch_size=5,
        process_batch_size=3,
        max_task_queue=MAX_INFLIGHT_PIPELINE,
    )
    work_queue.run()


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
    diffusion_model=None,
    stop_after: Optional[str] = None,
):
    """
    Run the full pipeline across every model at once, flattened into a single
    queue per stage. This keeps workers busy across model/grid boundaries —
    no worker idles waiting for the last instanton of one model's grid to
    finish before the next model's trajectory (and instanton grid) becomes
    available.
    """
    dm = diffusion_model or MasslessDecoupledDiffusion()

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
            diffusion_model=dm,
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
        )

    def full_payload(item) -> dict:
        model_idx, N_init, N_final, dns = item
        N_total = (float(N_init) - float(N_final)) + float(dns)
        # Build a shared rational grid: points at multiples of δ = 1/samples_per_N
        # so that grid points are reused across all instantons (keeps the efold_value
        # table small). Then append the exact endpoint N_total so that
        # CompactionFunction's downflow integration starts from the true instanton
        # endpoint rather than a grid point that may be up to δ/2 away.
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
        payload = key_fields(item)
        payload["N_sample"] = efold_array(efold_objs)
        payload["diffusion_model"] = dm
        return payload

    def shard_key_of(item):
        _, _, _, dns = item
        return dns

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

    C_THRESHOLD = 0.4
    C_BAR_THRESHOLD = 0.4

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
    inputs = build_pipeline_inputs(pool, units, args)
    atol, rtol = inputs["atol"], inputs["rtol"]
    phi0, pi0 = inputs["phi0"], inputs["pi0"]
    N_init_array = inputs["N_init_array"]
    N_final_array = inputs["N_final_array"]
    dns_objects = inputs["dns_array"]
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
    dm = MasslessDecoupledDiffusion()

    # If multiple --stop-after stages are given, keep only the earliest in pipeline order.
    stop_after = None
    if args.stop_after:
        matches = [s for s in _PIPELINE_STAGES if s in args.stop_after]
        if matches:
            stop_after = matches[0]

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
        diffusion_model=dm,
        stop_after=stop_after,
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
        data = pool.inventory("efold")
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
