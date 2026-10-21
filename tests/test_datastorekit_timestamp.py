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

"""U3 through the ``datastorekit`` package (dk-and-rpk-migration prompt 09, acceptance 5).

SI's 24 timestamp sites changed only their import: the package's ``DatastoreObject`` takes the
row's ``timestamp`` (keyword-only) and exposes it, and SI's factories pass it from the row they
read. Here, through ``live_pool`` (the package's pool), a replicated object (a ``delta_Nstar``)
and a sharded one (a ``FullInstanton``) are each stored, then fetched back by a second
``object_get`` that finds the row, and the fetched object's ``timestamp`` is compared with the
row's ``timestamp`` column, read with ``sqlite3`` ``mode=ro`` from the shard files by the
object's ``serial``: on every shard for the replicated row (one stamp across shards), and on the
one shard that holds the sharded row.

Needs Ray, so ``integration``: the objects are written and read through the package's pool,
whose ``Datastore`` actors hold the shards. The values are unique to this module, so that the
session-scoped store shared with the other integration tests holds one row for each.
"""

import sqlite3
import types
from datetime import datetime
from pathlib import Path

import pytest
import ray

from ComputeTargets.FullInstanton import FullInstanton, FullInstantonValue
from Units.Planck_units import Planck_units

_DNS_VAL = 0.937
_N_INIT_VAL = 93.7
_N_FINAL_VAL = 1.0
_LOG10_TOL = -6.0
_N_SAMPLES = [1.0, 2.0, 3.0]


def _shard_files(pool):
    primary = Path(pool.primary)
    shards = sorted(primary.parent.glob(f"{primary.stem}-shard*{primary.suffix}"))
    assert shards, f"no shard files beside {primary}"
    return shards


def _row_timestamps(pool, table, serial):
    """{shard file name: the timestamp column of *table*'s row *serial*} for each shard holding
    it, read with sqlite3 mode=ro and parsed as SQLAlchemy writes it."""
    found = {}
    for shard in _shard_files(pool):
        conn = sqlite3.connect(f"file:{shard}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                f'SELECT timestamp FROM "{table}" WHERE serial = ?', (serial,)
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) <= 1, (
            f"{shard.name}: {len(rows)} {table} rows with serial {serial}"
        )
        if rows:
            (raw,) = rows[0]
            assert raw is not None, (
                f"{shard.name}: {table} serial {serial} has no timestamp"
            )
            found[shard.name] = datetime.fromisoformat(raw)
    return found


def _check_replicated(live_pool):
    """The delta_Nstar: on every shard, the row's one stamp."""
    (stored,) = ray.get(
        live_pool.object_get("delta_Nstar", payload_data=[{"value": _DNS_VAL}])
    )
    assert stored.store_id is not None

    (fetched,) = ray.get(
        live_pool.object_get("delta_Nstar", payload_data=[{"value": _DNS_VAL}])
    )
    assert fetched.store_id == stored.store_id
    assert isinstance(fetched.timestamp, datetime), fetched.timestamp

    rows = _row_timestamps(live_pool, "delta_Nstar", fetched.store_id)
    assert set(rows) == {p.name for p in _shard_files(live_pool)}, rows
    for shard, stamp in rows.items():
        assert fetched.timestamp == stamp, f"{shard}: {fetched.timestamp} != {stamp}"


def _check_sharded(live_pool):
    """The FullInstanton: on the one shard that holds it."""
    dns, n_init, n_final, tol, efolds = ray.get(
        [
            live_pool.object_get("delta_Nstar", payload_data=[{"value": _DNS_VAL}]),
            live_pool.object_get("N_init", payload_data=[{"value": _N_INIT_VAL}]),
            live_pool.object_get("N_final", payload_data=[{"value": _N_FINAL_VAL}]),
            live_pool.object_get("tolerance", payload_data=[{"log10_tol": _LOG10_TOL}]),
            live_pool.object_get(
                "efold_value", payload_data=[{"N": n} for n in _N_SAMPLES]
            ),
        ]
    )
    dns, n_init, n_final, tol = dns[0], n_init[0], n_final[0], tol[0]
    diffusion = ray.get(live_pool.object_get("MasslessDecoupledDiffusion"))
    # a picklable stand-in for the trajectory proxy, as test_scalars_only_storage.py's
    trajectory = types.SimpleNamespace(store_id=998, units=Planck_units())

    def payload():
        return dict(
            trajectory=trajectory,
            N_init=n_init,
            N_final=n_final,
            delta_Nstar=dns,
            atol=tol,
            rtol=tol,
            diffusion_model=diffusion,
        )

    fi = FullInstanton(store_id=None, N_sample=None, **payload())
    fi._diagnostics = {"compute_time": 0.1, "converged": True}
    fi._failure = False
    fi._msr_action = 1.5
    fi._N_total = float(_N_SAMPLES[-1])
    fi._values = [
        FullInstantonValue(
            store_id=None, N=e, phi1=0.1 * (i + 1), phi2=0.2 * (i + 1), P1=0.3, P2=0.4
        )
        for i, e in enumerate(efolds)
    ]
    stored = ray.get(live_pool.object_store(fi))
    assert stored.store_id is not None
    assert ray.get(live_pool.object_validate(stored)) is True

    fetched = ray.get(live_pool.object_get("FullInstanton", **payload()))
    assert fetched.store_id == stored.store_id
    assert isinstance(fetched.timestamp, datetime), fetched.timestamp

    rows = _row_timestamps(live_pool, "FullInstanton", fetched.store_id)
    assert len(rows) == 1, (
        f"FullInstanton serial {fetched.store_id} on shards {sorted(rows)}"
    )
    ((shard, stamp),) = rows.items()
    assert fetched.timestamp == stamp, f"{shard}: {fetched.timestamp} != {stamp}"


@pytest.mark.integration
def test_replicated_and_sharded_objects_carry_their_rows_timestamp(live_pool):
    _check_replicated(live_pool)
    _check_sharded(live_pool)
