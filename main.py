import itertools
import sys
from datetime import datetime
from math import fabs
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
from InflationConcepts import efold_value, efold_array, delta_Nstar, N_efolds, MasslessDecoupledDiffusion
from Datastore.SQL.ProfileAgent import ProfileAgent
from Datastore.SQL.ShardedPool import ShardedPool
from MetadataConcepts import tolerance, store_tag
from RayTools.RayWorkPool import RayWorkPool
from Units import Planck_units
from Units.base import UnitsLike
from config.argument_parser import create_argument_parser
from config.defaults import DEFAULT_FLOAT_PRECISION
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


def _compute_and_store(pool, obj, label_str):
    """Drive the compute → store → validate cycle for a single object. Returns the final object."""
    compute_ref = obj.compute(label=label_str)
    ray.get(compute_ref)   # wait for computation (raises NotImplementedError for stubs)
    obj.store()
    stored_obj = ray.get(pool.object_store(obj))
    ray.get(pool.object_validate(stored_obj))
    return stored_obj


def _lookup_or_create(pool, cls_name, shard_key=None, **payload):
    """Look up an existing record. Returns the object; available=False means not yet computed."""
    kwargs = dict(payload)
    if shard_key is not None:
        kwargs["shard_key"] = shard_key
    return ray.get(pool.object_get(cls_name, **kwargs))


def run_pipeline(
    pool: ShardedPool,
    model_data: dict,
    delta_Nstar_array: List[delta_Nstar],
    phi0: phi_value,
    pi0: pi_value,
    N_init: N_efolds,
    N_final: N_efolds,
    N_sample: efold_array,
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
    print("\n** STAGE 1: Background inflaton trajectory")

    traj_obj = _lookup_or_create(
        pool, "InflatonTrajectory",
        phi0=phi0, pi0=pi0, potential=potential,
        atol=atol, rtol=rtol,
        N_sample=N_sample, solver_labels={}, tags=[],
        diffusion_model=dm,
    )

    if traj_obj.available:
        print(f"   -- trajectory already computed (store_id={traj_obj.store_id})")
    else:
        print(f"   -- trajectory not found, computing...")
        try:
            traj_obj = _compute_and_store(pool, traj_obj, f"InflatonTrajectory({label})")
            print(f"   -- trajectory stored (store_id={traj_obj.store_id})")
        except Exception as e:
            print(f"   !! trajectory computation failed for model {label}: {e}")
            raise

    traj_proxy = InflatonTrajectoryProxy(traj_obj)

    ## -----------------------------------------------------------------------
    ## STAGE 2: Full MSR instantons
    ## -----------------------------------------------------------------------
    print(f"\n** STAGE 2: Full MSR instantons ({len(delta_Nstar_array)} values of delta_Nstar)")

    # Parallel lookup: submit all object_get calls simultaneously, then collect.
    fi_refs = [
        pool.object_get(
            "FullInstanton",
            trajectory=traj_proxy,
            N_init=N_init,
            N_final=N_final,
            delta_Nstar=dns,
            atol=atol,
            rtol=rtol,
            N_sample=N_sample,
            diffusion_model=dm,
            tags=[],
        )
        for dns in delta_Nstar_array
    ]
    fi_objs = ray.get(fi_refs)

    new_fi = [(dns, obj) for dns, obj in zip(delta_Nstar_array, fi_objs)
              if not obj.available]
    existing_fi = len(fi_objs) - len(new_fi)
    print(f"   -- {existing_fi} already computed, {len(new_fi)} to compute")

    # Submit all compute calls in parallel, then collect and store sequentially.
    if new_fi:
        compute_pairs = []
        for dns, obj in new_fi:
            lbl = f"FullInstanton({label}, dNstar={float(dns):.4g})"
            compute_ref = obj.compute(label=lbl)
            compute_pairs.append((obj, compute_ref, lbl))

        for obj, compute_ref, lbl in compute_pairs:
            ray.get(compute_ref)
            obj.store()
            ray.get(pool.object_store(obj))
            print(f"   -- stored: {lbl}")

    ## -----------------------------------------------------------------------
    ## STAGE 3: Slow-roll instantons
    ## -----------------------------------------------------------------------
    print(f"\n** STAGE 3: Slow-roll instantons ({len(delta_Nstar_array)} values of delta_Nstar)")

    sri_refs = [
        pool.object_get(
            "SlowRollInstanton",
            trajectory=traj_proxy,
            N_init=N_init,
            N_final=N_final,
            delta_Nstar=dns,
            atol=atol,
            rtol=rtol,
            N_sample=N_sample,
            diffusion_model=dm,
            tags=[],
        )
        for dns in delta_Nstar_array
    ]
    sri_objs = ray.get(sri_refs)

    new_sri = [(dns, obj) for dns, obj in zip(delta_Nstar_array, sri_objs)
               if not obj.available]
    existing_sri = len(sri_objs) - len(new_sri)
    print(f"   -- {existing_sri} already computed, {len(new_sri)} to compute")

    if new_sri:
        compute_pairs = []
        for dns, obj in new_sri:
            lbl = f"SlowRollInstanton({label}, dNstar={float(dns):.4g})"
            compute_ref = obj.compute(label=lbl)
            compute_pairs.append((obj, compute_ref, lbl))

        for obj, compute_ref, lbl in compute_pairs:
            ray.get(compute_ref)
            obj.store()
            ray.get(pool.object_store(obj))
            print(f"   -- stored: {lbl}")


def execute(pool: ShardedPool, units: UnitsLike):
    """
    Set up parameter grids, register database objects, and call run_pipeline()
    for each model in the model list.
    """
    import math

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
    ## BUILD efold SAMPLE GRID
    ## -----------------------------------------------------------------------
    # The instanton runs from N=0 to N=N_trans + delta_Nstar_max.
    # We build a dense uniform sample grid covering the largest possible interval.
    N_trans = args.N_init - args.N_final
    N_max   = N_trans + max(dns_sample)
    N_grid_floats = np.linspace(0.0, N_max, args.N_samples, endpoint=True).tolist()

    print(f"** Building efold sample grid: {args.N_samples} points "
          f"from N=0 to N={N_max:.4g}")

    efold_objects = ray.get(
        pool.object_get(
            "efold_value",
            payload_data=[{"N": N} for N in N_grid_floats],
        )
    )

    N_sample = efold_array(efold_objects)

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
            N_sample=N_sample,
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
