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

import ray

from ComputeTargets.FullInstanton import FullInstantonProxy
from ComputeTargets.SlowRollInstanton import SlowRollInstantonProxy


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

    Not yet wired into any of the hand-rolled fetch loops
    (`_sweep_Ninit_or_Nfinal`, `_sweep_delta_Nstar`,
    `_generate_instanton_samples`, `_collect_doe_scalar_data`) — that
    conversion is a separate, later concern.
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
