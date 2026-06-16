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
from InflationConcepts import delta_Nstar, N_efolds, MasslessDecoupledDiffusion, efold_array
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
    payload_builder,
    label_builder,
    title: str,
    store_handler,
):
    """
    Two-pass RayWorkPool pattern for instanton compute targets.

    Pass 1 (query): determine which objects are already in the database.
    Pass 2 (work):  compute and persist the missing ones.

    `payload_builder(item)` returns a dict of keyword arguments for pool.object_get().
    `label_builder(obj)` returns a human-readable label string for the compute step.
    """
    ## Pass 1: query
    query_queue = RayWorkPool(
        pool,
        task_list,
        task_builder=lambda item: pool.object_get(
            cls_name, _do_not_populate=True, **payload_builder(item)
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=f"{title} [query]",
        store_results=True,
        create_batch_size=20,
        process_batch_size=20,
    )
    query_queue.run()

    missing = [
        (item, obj)
        for item, obj in zip(task_list, query_queue.results)
        if not obj.available
    ]
    print(f"   -- {len(task_list) - len(missing)} already computed, "
          f"{len(missing)} to compute")

    if not missing:
        return

    ## Pass 2: fetch full objects for missing items, then compute
    def build_work_ref(item):
        return pool.object_get(cls_name, **payload_builder(item))

    work_queue = RayWorkPool(
        pool,
        [item for item, _ in missing],
        task_builder=build_work_ref,
        compute_handler=lambda obj, **kwargs: obj.compute(**kwargs),
        store_handler=store_handler,
        persist_handler=lambda obj, pool: pool.object_store(obj),
        validation_handler=lambda obj: pool.object_validate(obj),
        label_builder=label_builder,
        title=f"{title} [compute]",
        store_results=False,
        create_batch_size=5,
        process_batch_size=3,
    )
    work_queue.run()


def run_pipeline(
    pool: ShardedPool,
    model_data: dict,
    delta_Nstar_array: List[delta_Nstar],
    phi0: phi_value,
    pi0: pi_value,
    N_init: N_efolds,
    N_final: N_efolds,
    samples_per_N: float,
    atol: tolerance,
    rtol: tolerance,
    diffusion_model=None,
):
    potential = model_data["potential"]
    label = model_data["label"]
    print(f"\n>> RUNNING PIPELINE FOR MODEL: {label}")

    dm = diffusion_model or MasslessDecoupledDiffusion()

    ## -----------------------------------------------------------------------
    ## STAGE 1: Background inflaton trajectory
    ## -----------------------------------------------------------------------
    # Single object — use a one-item RayWorkPool so the store_handler hook
    # is available (needed in Step 2 once InflatonTrajectory.store() requires
    # efold_value minting via the pool).

    traj_payload = dict(
        phi0=phi0, pi0=pi0, potential=potential,
        atol=atol, rtol=rtol,
        samples_per_N=samples_per_N,
        tags=[],
        diffusion_model=dm,
    )

    traj_queue = RayWorkPool(
        pool,
        [traj_payload],
        task_builder=lambda p: pool.object_get("InflatonTrajectory", **p),
        compute_handler=lambda obj, **kwargs: obj.compute(**kwargs),
        store_handler=inflaton_trajectory_store_handler,
        persist_handler=lambda obj, pool: pool.object_store(obj),
        validation_handler=lambda obj: pool.object_validate(obj),
        label_builder=lambda obj: f"InflatonTrajectory({label})",
        title="STAGE 1: Background inflaton trajectory",
        store_results=True,
        create_batch_size=1,
        process_batch_size=1,
    )
    traj_queue.run()

    traj_obj = traj_queue.results[0]
    if not traj_obj.available:
        raise RuntimeError(
            f"InflatonTrajectory for model {label} is not available after compute queue"
        )

    traj_proxy = InflatonTrajectoryProxy(traj_obj)

    ## -----------------------------------------------------------------------
    ## STAGE 2: Full MSR instantons
    ## -----------------------------------------------------------------------

    def fi_payload(dns: delta_Nstar) -> dict:
        N_total = (float(N_init) - float(N_final)) + float(dns)
        N_grid = np.linspace(
            0.0, N_total, max(2, math.ceil(N_total * samples_per_N)), endpoint=True
        ).tolist()
        efold_objs = ray.get(
            pool.object_get("efold_value", payload_data=[{"N": N} for N in N_grid])
        )
        N_sample = efold_array(efold_objs)
        return dict(
            trajectory=traj_proxy,
            N_init=N_init,
            N_final=N_final,
            delta_Nstar=dns,
            N_sample=N_sample,
            atol=atol,
            rtol=rtol,
            diffusion_model=dm,
            tags=[],
        )

    _run_instanton_queue(
        pool=pool,
        cls_name="FullInstanton",
        task_list=delta_Nstar_array,
        payload_builder=fi_payload,
        label_builder=lambda obj: f"FullInstanton({label}, dNstar={float(obj.delta_Nstar):.4g})",
        store_handler=_default_store_handler,
        title="STAGE 2: Full MSR instantons",
    )

    ## -----------------------------------------------------------------------
    ## STAGE 3: Slow-roll instantons
    ## -----------------------------------------------------------------------

    def sri_payload(dns: delta_Nstar) -> dict:
        N_total = (float(N_init) - float(N_final)) + float(dns)
        N_grid = np.linspace(
            0.0, N_total, max(2, math.ceil(N_total * samples_per_N)), endpoint=True
        ).tolist()
        efold_objs = ray.get(
            pool.object_get("efold_value", payload_data=[{"N": N} for N in N_grid])
        )
        N_sample = efold_array(efold_objs)
        return dict(
            trajectory=traj_proxy,
            N_init=N_init,
            N_final=N_final,
            delta_Nstar=dns,
            N_sample=N_sample,
            atol=atol,
            rtol=rtol,
            diffusion_model=dm,
            tags=[],
        )

    _run_instanton_queue(
        pool=pool,
        cls_name="SlowRollInstanton",
        task_list=delta_Nstar_array,
        payload_builder=sri_payload,
        label_builder=lambda obj: f"SlowRollInstanton({label}, dNstar={float(obj.delta_Nstar):.4g})",
        store_handler=_default_store_handler,
        title="STAGE 3: Slow-roll instantons",
    )


def execute(pool: ShardedPool, units: UnitsLike):
    """
    Set up parameter grids, register database objects, and call run_pipeline()
    for each model in the model list.
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

    N_init  = N_efolds(args.N_init)
    N_final = N_efolds(args.N_final)

    ## -----------------------------------------------------------------------
    ## BUILD delta_Nstar GRID
    ## -----------------------------------------------------------------------
    if len(args.delta_Nstar_values) > 0:
        dns_sample = sorted(args.delta_Nstar_values)
    else:
        dns_sample = sorted(np.linspace(
            args.delta_Nstar_low, args.delta_Nstar_high,
            args.delta_Nstar_samples, endpoint=True,
        ).tolist())

    print(f"\n** Building delta_Nstar grid: {len(dns_sample)} values "
          f"from {dns_sample[0]:.4g} to {dns_sample[-1]:.4g}")

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
    print(f"\n** {len(model_list)} model(s) to process")

    for model_data in model_list:
        run_pipeline(
            pool=pool,
            model_data=model_data,
            delta_Nstar_array=dns_objects,
            phi0=phi0,
            pi0=pi0,
            N_init=N_init,
            N_final=N_final,
            samples_per_N=samples_per_N,
            atol=atol,
            rtol=rtol,
            diffusion_model=dm,
        )


def inventory(pool: ShardedPool, units: UnitsLike):
    print("\n@@ DATASTORE INVENTORY")
    # delta_Nstar values
    _inventory_dimensionless(pool, "delta_Nstar", "Delta N★ values")
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
