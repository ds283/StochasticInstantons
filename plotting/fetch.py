# (c) University of Sussex 2026
# Created by David Seery
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import dataclass
from typing import Any, Callable, Optional

import ray

from ComputeTargets.FullInstanton import FullInstantonProxy
from ComputeTargets.SlowRollInstanton import SlowRollInstantonProxy
from plotting.adapters.base import InstantonAdapter
from plotting.adapters.full import FullInstantonAdapter
from plotting.adapters.slow_roll import SlowRollInstantonAdapter


def _instanton_key_payload(traj_proxy, N_init, N_final, dns, atol, rtol, dm):
    return dict(
        trajectory=traj_proxy,
        N_init=N_init,
        N_final=N_final,
        delta_Nstar=dns,
        atol=atol,
        rtol=rtol,
        tags=[],
        diffusion_model=dm,
    )


def _cf_key_payload(traj_proxy, fi_proxy, sri_proxy, dns, cosmo, atol, rtol):
    return dict(
        trajectory=traj_proxy,
        full_instanton=fi_proxy,
        slow_roll_instanton=sri_proxy,
        delta_Nstar=dns,
        cosmo=cosmo,
        C_threshold=0.4,
        atol=atol,
        rtol=rtol,
        tags=[],
    )


def _qualifying_action(obj):
    """Extract msr_action from a (possibly _do_not_populate=True) query
    result, or None if the object doesn't exist / has no action recorded."""
    if obj is None or not obj.available:
        return None
    return obj.msr_action


def _extract_cf_summary(cf, units):
    """Return a 12-tuple:
        (C_peak_full, C_bar_peak_full, M_max_full_solar, M_peak_full_solar,
         C_peak_sr,   C_bar_peak_sr,   M_max_sr_solar,   M_peak_sr_solar,
         r_max_full_Mpc, r_peak_full_Mpc,
         r_max_sr_Mpc,   r_peak_sr_Mpc)
    from a CompactionFunction object, or an all-None 12-tuple when unavailable."""
    none12 = (None,) * 12
    if cf is None or not cf.available or cf.failure:
        return none12

    SolarMass = units.SolarMass
    Mpc = units.Mpc

    def _m(v):
        return v / SolarMass if v is not None else None

    def _r(v):
        return v / Mpc if v is not None else None

    return (
        cf.C_peak_full,
        cf.C_bar_peak_full,
        _m(cf.M_max_full),
        _m(cf.M_peak_full),
        cf.C_peak_slow_roll,
        cf.C_bar_peak_slow_roll,
        _m(cf.M_max_slow_roll),
        _m(cf.M_peak_slow_roll),
        _r(cf.r_max_full),
        _r(cf.r_peak_full),
        _r(cf.r_max_slow_roll),
        _r(cf.r_peak_slow_roll),
    )


def _cf_vectorized_fetch(
    pool, traj_proxy, fi_list, sri_list, dns_val, cosmo, atol, rtol
):
    """Return an index-aligned list of CompactionFunction objects (or None) for every
    element in fi_list/sri_list.  Only submits a vectorized fetch for positions where
    at least one instanton is available; positions where neither is available get None."""
    n = len(fi_list)
    valid_indices = []
    payload_data = []
    for i, (fi_obj, sri_obj) in enumerate(zip(fi_list, sri_list)):
        fi_avail = fi_obj is not None and fi_obj.available
        sri_avail = sri_obj is not None and sri_obj.available
        if fi_avail or sri_avail:
            fi_proxy = FullInstantonProxy(fi_obj) if fi_avail else None
            sri_proxy = SlowRollInstantonProxy(sri_obj) if sri_avail else None
            payload_data.append(
                {
                    **_cf_key_payload(
                        traj_proxy, fi_proxy, sri_proxy, dns_val, cosmo, atol, rtol
                    ),
                    "_do_not_populate": True,
                }
            )
            valid_indices.append(i)

    result = [None] * n
    if payload_data:
        fetched = ray.get(
            pool.object_get_vectorized(
                "CompactionFunction", dns_val, payload_data=payload_data
            )
        )
        for i, cf in zip(valid_indices, fetched):
            result[i] = cf
    return result


def fetch_over_grid(
    pool, class_name, shard_key_of, key_payload_of, items, do_not_populate=True
) -> list:
    """Generic vectorized fetch over a grid of items, binned by shard key
    (design §4). `shard_key_of(item)` extracts the shard-key value for one
    item; `key_payload_of(item)` builds the datastore lookup payload dict for
    one item (without `_do_not_populate`). Issues one
    `pool.object_get_vectorized()` call per distinct shard key, then
    reassembles an index-aligned list of fetched objects (or None) in the
    same order as `items`.

    Used directly by single-class fetches, and as the per-class building
    block inside `fetch_adapters_over_grid` below (P2b retrofit) for the
    multi-class case. Still not wired into
    `plot_InstantonSolutions.py::_generate_instanton_samples`'s hand-rolled
    per-combo fetch loop — that one stays as-is (out of scope, see the P2b
    plan).
    """
    n = len(items)
    by_shard = {}
    for i, item in enumerate(items):
        shard_key = shard_key_of(item)
        by_shard.setdefault(shard_key, []).append(i)

    refs = {}
    for shard_key, indices in by_shard.items():
        payload_data = [
            {**key_payload_of(items[i]), "_do_not_populate": do_not_populate}
            for i in indices
        ]
        refs[shard_key] = pool.object_get_vectorized(
            class_name, shard_key, payload_data=payload_data
        )

    shard_keys = list(refs.keys())
    resolved = ray.get([refs[k] for k in shard_keys])
    resolved_by_shard = dict(zip(shard_keys, resolved))

    result = [None] * n
    for shard_key, indices in by_shard.items():
        for local_idx, global_idx in enumerate(indices):
            result[global_idx] = resolved_by_shard[shard_key][local_idx]
    return result


# ── Multi-class adapter fetch (P2b retrofit) ─────────────────────────────────
#
# Generalises fetch_over_grid to fetch several solver classes over the same
# grid of items and return already-constructed InstantonAdapter instances,
# so plotting/figures/sweeps.py and plotting/figures/doe.py can consume a
# flat adapter list instead of hand-rolled (fi_points, sri_points) tuples /
# _full/_sr-suffixed dicts, and adding a new solver kind (e.g. GCI) means
# adding one more ClassFetchSpec, not touching the figure functions.


@dataclass
class ClassFetchSpec:
    """One solver class to fetch over a grid of items."""

    name: str  # e.g. "full", "slow-roll" -- internal bookkeeping key
    class_name: str  # datastore class name, e.g. "FullInstanton"
    shard_key_of: Callable[[Any], Any]
    key_payload_of: Callable[[Any], dict]
    adapter_factory: Callable[[Any, Any, dict], InstantonAdapter]
    # adapter_factory(fetched_obj_or_None, cf_or_None, coords) -> InstantonAdapter


@dataclass
class CFFetchSpec:
    """How to pair a CompactionFunction fetch against two of the
    ClassFetchSpecs passed to the same fetch_adapters_over_grid call."""

    shard_key_of: Callable[[Any], Any]
    traj_proxy: Any
    fi_spec_name: str
    sri_spec_name: str
    cosmo: Any
    atol: Any
    rtol: Any


def full_sr_class_specs(traj_proxy, atol, rtol, dm) -> list:
    """Convenience builder for the standard Full+SlowRoll pair, over items
    shaped as (N_init, N_final, delta_Nstar) triples -- the same item shape
    `_collect_doe_scalar_data`'s `grid_combos` already used. Reuses
    `_instanton_key_payload` unchanged. A future GCI caller would build its
    own `ClassFetchSpec` with a payload builder that also carries
    `alpha`/`n_collocation_points` -- that is P4's job, not this one."""
    return [
        ClassFetchSpec(
            name="full",
            class_name="FullInstanton",
            shard_key_of=lambda item: item[2],
            key_payload_of=lambda item: _instanton_key_payload(
                traj_proxy, item[0], item[1], item[2], atol, rtol, dm
            ),
            adapter_factory=lambda obj, cf, coords: FullInstantonAdapter(
                obj, cf, coords=coords
            ),
        ),
        ClassFetchSpec(
            name="slow-roll",
            class_name="SlowRollInstanton",
            shard_key_of=lambda item: item[2],
            key_payload_of=lambda item: _instanton_key_payload(
                traj_proxy, item[0], item[1], item[2], atol, rtol, dm
            ),
            adapter_factory=lambda obj, cf, coords: SlowRollInstantonAdapter(
                obj, cf, coords=coords
            ),
        ),
    ]


def _cf_adapters_over_grid(
    pool, items, shard_key_of, traj_proxy, fi_list, sri_list, cosmo, atol, rtol
) -> list:
    """Bins `items` by shard key and calls the EXISTING, unmodified
    `_cf_vectorized_fetch` once per bin (never redesigns its Full/SR pairing
    logic), reassembling an index-aligned CompactionFunction-or-None list."""
    by_shard: dict = {}
    for i, item in enumerate(items):
        by_shard.setdefault(shard_key_of(item), []).append(i)

    result: list = [None] * len(items)
    for shard_key, indices in by_shard.items():
        sub_fi = [fi_list[i] for i in indices]
        sub_sri = [sri_list[i] for i in indices]
        sub_cf = _cf_vectorized_fetch(
            pool, traj_proxy, sub_fi, sub_sri, shard_key, cosmo, atol, rtol
        )
        for local_idx, global_idx in enumerate(indices):
            result[global_idx] = sub_cf[local_idx]
    return result


def fetch_adapters_over_grid(
    pool,
    items,
    class_specs: list,
    coords_of: Callable[[Any], dict],
    cf_spec: Optional[CFFetchSpec] = None,
    do_not_populate: bool = True,
) -> list:
    """For each spec in `class_specs`, calls the EXISTING `fetch_over_grid`
    once (unchanged). If `cf_spec` is given, pairs Full/SR (named by
    `cf_spec.fi_spec_name`/`sri_spec_name`) via `_cf_adapters_over_grid`,
    resolved *after* the per-class fetches so it can see which of them came
    back available -- exactly the existing `_cf_vectorized_fetch` pairing
    logic, just looped over however many shards `items` spans instead of a
    single shard handled by hand. Returns a list (one entry per item) of
    lists (one adapter per spec, in `class_specs` order)."""
    raw_by_spec = [
        fetch_over_grid(
            pool, spec.class_name, spec.shard_key_of, spec.key_payload_of,
            items, do_not_populate,
        )
        for spec in class_specs
    ]

    cf_list = None
    if cf_spec is not None:
        fi_idx = next(
            i for i, s in enumerate(class_specs) if s.name == cf_spec.fi_spec_name
        )
        sri_idx = next(
            i for i, s in enumerate(class_specs) if s.name == cf_spec.sri_spec_name
        )
        cf_list = _cf_adapters_over_grid(
            pool, items, cf_spec.shard_key_of, cf_spec.traj_proxy,
            raw_by_spec[fi_idx], raw_by_spec[sri_idx],
            cf_spec.cosmo, cf_spec.atol, cf_spec.rtol,
        )

    rows = []
    for i, item in enumerate(items):
        coords = coords_of(item)
        cf = cf_list[i] if cf_list is not None else None
        rows.append(
            [
                spec.adapter_factory(raw_by_spec[s][i], cf, coords)
                for s, spec in enumerate(class_specs)
            ]
        )
    return rows


def collect_doe_scalar_points(
    pool, traj_proxy, grid_combos, cosmo, atol, rtol, units, dm
) -> list:
    """Replaces `plot_InstantonSolutions.py`'s former `_collect_doe_scalar_data`
    (moved here since a later prompt in the build plan assumes this
    generalised, multi-solver DOE collection already lives in
    `plotting/fetch.py`, not the driver). `grid_combos`: list of
    `(N_init_obj, N_final_obj, dns_obj)` triples. Returns one dict per grid
    point where at least one of Full/SlowRoll is available:
        {"delta_Nstar": float, "delta_N": float,
         "adapters": [FullInstantonAdapter, SlowRollInstantonAdapter]}
    Points where neither is available are omitted entirely (same gate as
    the function this replaces)."""
    if not grid_combos:
        return []

    items = list(grid_combos)
    class_specs = full_sr_class_specs(traj_proxy, atol, rtol, dm)
    cf_spec = CFFetchSpec(
        shard_key_of=lambda item: item[2],
        traj_proxy=traj_proxy,
        fi_spec_name="full",
        sri_spec_name="slow-roll",
        cosmo=cosmo,
        atol=atol,
        rtol=rtol,
    )
    coords_of = lambda item: {
        "N_init": float(item[0]),
        "N_final": float(item[1]),
        "delta_Nstar": float(item[2]),
    }
    rows = fetch_adapters_over_grid(
        pool, items, class_specs, coords_of, cf_spec=cf_spec, do_not_populate=True
    )

    result = []
    for item, (full_adapter, sr_adapter) in zip(items, rows):
        if not (full_adapter.available or sr_adapter.available):
            continue
        result.append(
            {
                "delta_Nstar": float(item[2]),
                "delta_N": float(item[0]) - float(item[1]),
                "adapters": [full_adapter, sr_adapter],
            }
        )
    return result


def flatten_doe_points_for_csv(points: list) -> list:
    """CSV-compatibility shim: rebuilds the exact flat, `_full`/`_sr`-suffixed
    column dict `_collect_doe_scalar_data` used to produce, from each
    point's adapters, via `.scalars()` (mapping its generic
    `noise_field_*`/`noise_mom_*` keys back to the CSV's historical
    `noise_phi1_*`/`noise_phi2_*` names). This is the one place in the P2b
    retrofit allowed to key off adapter identity (full -> "_full" suffix,
    slow-roll -> "_sr" suffix) -- it is CSV-serialisation code, not a figure
    function, so the "never branch on kind" rule (which applies to
    plotting.figures.*) doesn't apply here. Extending this to a third
    suffix for a future solver kind is that solver's own integration work,
    not this retrofit's."""
    rows = []
    for p in points:
        full_adapter, sr_adapter = p["adapters"]
        fs, ss = full_adapter.scalars(), sr_adapter.scalars()
        coords = full_adapter.coords or sr_adapter.coords
        rows.append(
            {
                "N_init": coords["N_init"],
                "N_final": coords["N_final"],
                "delta_Nstar": p["delta_Nstar"],
                "delta_N": p["delta_N"],
                "msr_action_full": fs["msr_action"],
                "msr_action_sr": ss["msr_action"],
                "noise_phi1_min_full": fs["noise_field_min"],
                "noise_phi1_mean_full": fs["noise_field_mean"],
                "noise_phi1_max_full": fs["noise_field_max"],
                "noise_phi2_min_full": fs["noise_mom_min"],
                "noise_phi2_mean_full": fs["noise_mom_mean"],
                "noise_phi2_max_full": fs["noise_mom_max"],
                "noise_phi1_min_sr": ss["noise_field_min"],
                "noise_phi1_mean_sr": ss["noise_field_mean"],
                "noise_phi1_max_sr": ss["noise_field_max"],
                "noise_phi2_min_sr": ss["noise_mom_min"],
                "noise_phi2_mean_sr": ss["noise_mom_mean"],
                "noise_phi2_max_sr": ss["noise_mom_max"],
                "C_peak_full": fs["C_peak"],
                "C_bar_peak_full": fs["C_bar_peak"],
                "M_max_full_solar": fs["M_max_solar"],
                "M_peak_full_solar": fs["M_peak_solar"],
                "r_max_full_Mpc": fs["r_max_Mpc"],
                "r_peak_full_Mpc": fs["r_peak_Mpc"],
                "C_peak_sr": ss["C_peak"],
                "C_bar_peak_sr": ss["C_bar_peak"],
                "M_max_sr_solar": ss["M_max_solar"],
                "M_peak_sr_solar": ss["M_peak_solar"],
                "r_max_sr_Mpc": ss["r_max_Mpc"],
                "r_peak_sr_Mpc": ss["r_peak_Mpc"],
            }
        )
    return rows


# ── Diagnostics CSV companion (P7, design §8 item 9) ─────────────────────────
#
# `collect_doe_scalar_points`'s returned points already carry each grid
# point's fully-fetched adapters, and `InstantonAdapter.diagnostics()`
# rehydrates on the very same `_do_not_populate=True` fetch used to build
# `scalar_data.csv` -- the parent-row `diagnostics_json` blob rides along for
# free (design §8: "this costs essentially nothing extra"). So there is no
# second fetch pass here: `flatten_diagnostics_for_csv` just reads
# `.diagnostics()` off the adapters `collect_doe_scalar_points` already
# fetched, mirroring `flatten_doe_points_for_csv`'s own read-at-flatten-time
# pattern for `.scalars()`.

# Diagnostic keys common to every solver's diagnostics dict (verified
# against ComputeTargets/FullInstanton.py, ComputeTargets/SlowRollInstanton.py
# -- see .prompts/gradient-coupled-plotting/12-P7-diagnostics-figures.md).
# Read with `.get(...)`; a key absent for a given kind (e.g. SlowRollInstanton
# has no `outer_iterations`) yields `None` rather than raising.
_DIAGNOSTIC_CSV_KEYS = (
    "compute_time",
    "converged",
    "final_residual",
    "total_ode_solves",
    "outer_iterations",
    "newton_fallback_count",
    "final_lambda",
    "mean_picard_iterations",
)


def flatten_diagnostics_for_csv(points: list) -> list:
    """Builds `diagnostics_data.csv` rows sharing the exact same grid-point
    identification columns (`N_init`, `N_final`, `delta_Nstar`, `delta_N`) as
    `flatten_doe_points_for_csv`'s `scalar_data.csv` rows, so the two can be
    joined downstream by `regression_InstantonOutputs.py` or a sibling script
    (design §8 item 9). Mirrors `flatten_doe_points_for_csv`'s fixed
    full/slow-roll adapter-position convention -- extending this to a third
    (GCI) slot is P8's own driver-wiring job, not this function's."""
    rows = []
    for p in points:
        full_adapter, sr_adapter = p["adapters"]
        fd = full_adapter.diagnostics() or {}
        sd = sr_adapter.diagnostics() or {}
        coords = full_adapter.coords or sr_adapter.coords
        row = {
            "N_init": coords["N_init"],
            "N_final": coords["N_final"],
            "delta_Nstar": p["delta_Nstar"],
            "delta_N": p["delta_N"],
        }
        for key in _DIAGNOSTIC_CSV_KEYS:
            row[f"diag_{key}_full"] = fd.get(key)
            row[f"diag_{key}_sr"] = sd.get(key)
        rows.append(row)
    return rows
