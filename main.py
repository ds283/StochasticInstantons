import itertools
import math
import sys
from datetime import datetime
from typing import List, Any, Optional

import numpy as np
import ray

from ComputeTargets import (
    InflatonTrajectory,
    InflatonTrajectoryProxy,
    FullInstanton,
    SlowRollInstanton,
)
from CosmologyConcepts import phi_value, pi_value
from InflationConcepts import delta_Nstar, N_init, N_final, MasslessDecoupledDiffusion, efold_array
from Datastore.SQL.ProfileAgent import ProfileAgent
from Datastore.SQL.ShardedPool import ShardedPool
from MetadataConcepts import tolerance, store_tag
from RayTools.RayWorkPool import RayWorkPool, _default_store_handler
from Units import Planck_units
from Units.base import UnitsLike
from config.argument_parser import create_argument_parser
from config.model_list import build_model_list
from config.sharding import (
    replicated_tables,
    sharded_tables,
    get_shard_key_store_id,
    ShardKeyType,
    read_table_config,
    inventory_config,
)

VERSION_LABEL = "2026.6.1"

# Cap on the number of in-flight FullInstanton/SlowRollInstanton compute tasks.
# Each instanton solve has a non-trivial memory footprint, so this is kept
# tight (current target machine: 10-core MacBook Pro). Raise this when moving
# to a larger machine (e.g. an HPC cluster).
MAX_INFLIGHT_COMPUTE = 20

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
    item, with concurrency capped at MAX_INFLIGHT_COMPUTE.

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
                {**key_fields(item), "_do_not_populate": True}
                for item in binned[key]
            ],
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=None, # title = None means this queue is silent on the console
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
    print(f"   -- {len(task_list) - len(missing)} already computed, "
          f"{len(missing)} to compute")

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
        max_task_queue=MAX_INFLIGHT_COMPUTE,
    )
    work_queue.run()


def run_all_pipelines(
    pool: ShardedPool,
    model_list: List[dict],
    N_init_array: List[N_init],
    N_final_array: List[N_final],
    delta_Nstar_array: List[delta_Nstar],
    phi0: phi_value,
    pi0: pi_value,
    samples_per_N: float,
    atol: tolerance,
    rtol: tolerance,
    diffusion_model=None,
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
            phi0=phi0, pi0=pi0, potential=model_data["potential"],
            atol=atol, rtol=rtol,
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
        title="STAGE 1: BACKGROUND INFLATONARY TRAJECTORIES",
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

    ## -----------------------------------------------------------------------
    ## Flatten (model, N_init, N_final, delta_Nstar) into a single grid
    ## -----------------------------------------------------------------------

    grid = list(itertools.product(
        range(len(model_list)), N_init_array, N_final_array, delta_Nstar_array
    ))

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
        N_grid = np.linspace(
            0.0, N_total, max(2, math.ceil(N_total * samples_per_N)), endpoint=True
        ).tolist()
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
        title="STAGE 2: Full MSR instantons",
    )

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
        title="STAGE 3: Slow-roll instantons",
    )


def _build_grid(low, high, samples, values, label):
    if len(values) > 0:
        sample = sorted(values)
    else:
        sample = sorted(np.linspace(low, high, samples, endpoint=True).tolist())
    print(f"\n** Building {label} grid: {len(sample)} values "
          f"from {sample[0]:.4g} to {sample[-1]:.4g}")
    return sample


def execute(pool: ShardedPool, units: UnitsLike):
    """
    Set up parameter grids, register database objects, and run the flattened
    work queues across every model.
    """
    ## -----------------------------------------------------------------------
    ## REGISTER TOLERANCES
    ## -----------------------------------------------------------------------
    atol, rtol = ray.get([
        pool.object_get("tolerance", log10_tol=int(round(
            math.log10(args.abs_tol)
        ))),
        pool.object_get("tolerance", log10_tol=int(round(
            math.log10(args.rel_tol)
        ))),
    ])

    ## -----------------------------------------------------------------------
    ## REGISTER INITIAL CONDITIONS
    ## -----------------------------------------------------------------------
    phi0, pi0 = ray.get([
        pool.object_get("phi_value",
                        value=args.phi0_Mp * units.PlanckMass, units=units),
        pool.object_get("pi_value",
                        value=args.pi0_Mp * units.PlanckMass, units=units),
    ])

    ## -----------------------------------------------------------------------
    ## BUILD N_init, N_final, delta_Nstar GRIDS
    ## -----------------------------------------------------------------------
    N_init_sample = _build_grid(
        args.N_init_low, args.N_init_high, args.N_init_samples,
        args.N_init_values, "N_init",
    )
    N_init_array = ray.get(
        pool.object_get(
            "N_init",
            payload_data=[{"value": v} for v in N_init_sample],
        )
    )

    N_final_sample = _build_grid(
        args.N_final_low, args.N_final_high, args.N_final_samples,
        args.N_final_values, "N_final",
    )
    N_final_array = ray.get(
        pool.object_get(
            "N_final",
            payload_data=[{"value": v} for v in N_final_sample],
        )
    )

    dns_sample = _build_grid(
        args.delta_Nstar_low, args.delta_Nstar_high, args.delta_Nstar_samples,
        args.delta_Nstar_values, "delta_Nstar",
    )
    dns_objects = ray.get(
        pool.object_get(
            "delta_Nstar",
            payload_data=[{"value": v} for v in dns_sample],
        )
    )

    ## -----------------------------------------------------------------------
    ## SAMPLING DENSITY
    ## -----------------------------------------------------------------------
    samples_per_N = args.samples_per_N
    print(f"\n** Trajectory sampling density: {samples_per_N:.4g} samples per e-fold")

    ## -----------------------------------------------------------------------
    ## BUILD MODEL LIST AND RUN PIPELINE
    ## -----------------------------------------------------------------------
    dm = MasslessDecoupledDiffusion()

    model_list = build_model_list(pool, units, args)
    total_combinations = len(model_list) * len(N_init_array) * len(N_final_array) * len(dns_objects)
    print(f"\n** {len(model_list)} model(s) to process; "
          f"{len(N_init_array)} x {len(N_final_array)} x {len(dns_objects)} "
          f"N_init/N_final/delta_Nstar grid = {total_combinations} instanton "
          f"parameter combinations per model")

    run_all_pipelines(
        pool=pool,
        model_list=model_list,
        N_init_array=N_init_array,
        N_final_array=N_final_array,
        delta_Nstar_array=dns_objects,
        phi0=phi0,
        pi0=pi0,
        samples_per_N=samples_per_N,
        atol=atol,
        rtol=rtol,
        diffusion_model=dm,
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
    _inventory_dimensionful(pool, "pi_value",  "pi_0 values",  units)
    # inflaton_mass, quartic_coupling
    _inventory_dimensionful(pool, "inflaton_mass",  "Inflaton mass values", units)
    _inventory_dimensionless(pool, "quartic_coupling", "Quartic coupling values")
    # efold values
    _inventory_efold(pool)
    # Compute targets
    _inventory_object(pool, "InflatonTrajectory",  "Inflaton trajectories")
    _inventory_object(pool, "FullInstanton",        "Full MSR instantons")
    _inventory_object(pool, "SlowRollInstanton",    "Slow-roll instantons")


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
        unit_val  = getattr(units, unit_name, 1.0)
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
            ts_late  = group.get("latest_timestamp")
            print(f"      @@ {group_name}: {n} record(s)", end="")
            if ts_early:
                print(f" | {ts_early.strftime('%Y-%m-%d %H:%M')} – "
                      f"{ts_late.strftime('%H:%M')}", end="")
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
        low  = [fmt(v) for v in vals[:10]]
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
