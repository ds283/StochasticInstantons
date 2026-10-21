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

"""The inventory of a store the package wrote (dk-and-rpk-migration prompt 10, N1-N3).

A two-shard store is built through the ``datastorekit`` package's ``ShardedPool``, in a
subprocess under its own private Ray (``ray.init(address="local")``), as prompt 06's I6 and 09's
acceptance 4 do, from synthetic values (no solve, so not ``slow``). Every parent is a real row
the pool wrote: three trajectories (both potential types, one failed), and of each compute target
a successful and a failed record, under keys of their own (another ``delta_Nstar``, or another
``phi0``), since a failed and a successful record with one key would be a ``duplicate``. One
compaction function is left unvalidated, with no slow-roll instanton (the nullable parent). The
store is then closed, and read in the test process by ``read_inventory``, read-only and without
Ray: every class is present with its count and **no named problem**, and the report rendered from
it shows today's fields. ``main.py --inventory`` on it exits 0 with that report, before Ray (an
address nothing listens on, and ``RAY_ADDRESS`` set to it), and changes no file; with
``--show-all`` it prints the verbose report.

Needs Ray, so ``integration``: the store is written through the package's pool, whose actors
hold the shards. ``live_pool`` cannot serve: it is one shard, and other modules write rows into
it whose parents name no row, which an inventory reports as ``unresolved-parent``. The store
lives under ``tempfile``; the pytest process never initialises Ray for it.
"""

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from datastorekit.store_inventory import read_inventory

from config.datastore import factories
from tools.inventory_report import format_inventory_report

_ROOT = Path(__file__).resolve().parent.parent
_ADDRESS = "127.0.0.1:9"

_STORE_SCRIPT = r"""
import json, sys
root, db = sys.argv[1], sys.argv[2]
sys.path.insert(0, root)

import ray
from datastorekit.SQL.ShardedPool import ShardedPool
import config.datastore
from config.sharding import (ShardKeyType, get_shard_key_store_id,
                             read_table_config, replicated_tables, sharded_tables)
from ComputeTargets.InflatonTrajectory import (InflatonTrajectory, InflatonTrajectoryProxy,
                                               InflatonTrajectoryValue)
from ComputeTargets.FullInstanton import FullInstanton, FullInstantonValue
from ComputeTargets.SlowRollInstanton import SlowRollInstanton, SlowRollInstantonValue
from ComputeTargets.CompactionFunction import CompactionFunction, CompactionFunctionValue
from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
    GradientCoupledInstanton, GradientCoupledInstantonValue, GradientCoupledInstantonProfileValue)
from CosmologyModels.params import Planck2018
from Units import Planck_units

ray.init(address="local", include_dashboard=False)
result = {}
try:
    pool = ShardedPool(
        version_label="10-inventory-test", db_name=db, ShardKeyType=ShardKeyType,
        ShardKeyStoreIdGetter=get_shard_key_store_id, replicated_tables=replicated_tables,
        sharded_tables=sharded_tables, shards=2, profile_agent=None,
        job_name="10-inventory-test", prune_unvalidated=False,
        read_table_config=read_table_config, factories=config.datastore.factories,
        serial_batch_sizes=config.datastore.serial_batch_sizes,
    )
    try:
        u = Planck_units()
        g = lambda cls, **kw: ray.get(pool.object_get(cls, **kw))
        many = lambda cls, rows: ray.get(pool.object_get(cls, payload_data=rows))
        atol = g("tolerance", log10_tol=-8)
        rtol = g("tolerance", log10_tol=-6)
        phi0 = g("phi_value", value=15.0 * u.PlanckMass, units=u)
        phi0_failed = g("phi_value", value=16.0 * u.PlanckMass, units=u)
        pi0 = g("pi_value", value=-0.1 * u.PlanckMass, units=u)
        mass = g("inflaton_mass", value=1.0e-5 * u.PlanckMass, units=u)
        coupling = g("quartic_coupling", value=1.0e-13)
        quadratic = g("QuadraticPotential", m=mass, units=u)
        quartic = g("QuarticPotential", lambda_=coupling, units=u)
        dns = many("delta_Nstar", [{"value": v} for v in (0.5, 1.5, 2.5)])
        n_init = g("N_init", value=20.0)
        n_final = g("N_final", value=5.0)
        ncp = g("n_collocation_points", n_collocation_points=5)
        alpha = g("alpha_regularization", alpha=0.01)
        efolds = many("efold_value", [{"N": 0.5 * k} for k in range(25)])
        diffusion = g("MasslessDecoupledDiffusion")
        cosmo = g("CosmologicalParams", params=Planck2018())

        def trajectory(phi, potential, failure):
            t = InflatonTrajectory(store_id=None, phi0=phi, pi0=pi0, potential=potential,
                                   samples_per_N=2.0, atol=atol, rtol=rtol)
            t._failure = failure
            t._diagnostics = {"compute_time": 0.0}
            if not failure:
                t._N_end = 12.0
                t._values = [InflatonTrajectoryValue(store_id=None, N=e,
                                                     phi=(15.0 - 0.1 * e.N) * u.PlanckMass,
                                                     pi=-0.1 * u.PlanckMass) for e in efolds]
            stored = ray.get(pool.object_store(t))
            assert ray.get(pool.object_validate(stored)) is True
            return stored

        t_quadratic = trajectory(phi0, quadratic, False)
        t_quartic = trajectory(phi0, quartic, False)
        t_failed = trajectory(phi0_failed, quadratic, True)
        p_quadratic = InflatonTrajectoryProxy(t_quadratic)
        p_quartic = InflatonTrajectoryProxy(t_quartic)

        def instanton(cls, value_cls, proxy, dn, failure):
            obj = cls(store_id=None, trajectory=proxy, N_init=n_init, N_final=n_final,
                      delta_Nstar=dn, N_sample=None, atol=atol, rtol=rtol,
                      diffusion_model=diffusion)
            obj._diagnostics = {"compute_time": 0.1, "converged": not failure}
            obj._failure = failure
            if not failure:
                obj._msr_action = 1.5
                obj._N_total = 1.0
                if cls is FullInstanton:
                    obj._values = [value_cls(store_id=None, N=e, phi1=0.1, phi2=0.2, P1=0.3, P2=0.4)
                                   for e in efolds[:3]]
                else:
                    obj._values = [value_cls(store_id=None, N=e, phi=0.5, P1=0.6)
                                   for e in efolds[:3]]
            stored = ray.get(pool.object_store(obj))
            assert ray.get(pool.object_validate(stored)) is True
            return stored

        fi = [instanton(FullInstanton, FullInstantonValue, p_quadratic, dns[0], False),
              instanton(FullInstanton, FullInstantonValue, p_quartic, dns[1], False),
              instanton(FullInstanton, FullInstantonValue, p_quadratic, dns[2], True)]
        sri = [instanton(SlowRollInstanton, SlowRollInstantonValue, p_quadratic, dns[0], False),
               instanton(SlowRollInstanton, SlowRollInstantonValue, p_quartic, dns[1], False),
               instanton(SlowRollInstanton, SlowRollInstantonValue, p_quadratic, dns[2], True)]

        def compaction(proxy, full, slow, dn, failure, validate):
            cf = CompactionFunction(store_id=None, full_instanton=full, slow_roll_instanton=slow,
                                    trajectory=proxy, cosmo=cosmo, delta_Nstar=dn,
                                    C_threshold=0.4, atol=atol, rtol=rtol)
            cf._failure = failure
            cf._diagnostics = {"full": None, "slow_roll": None}
            values = [CompactionFunctionValue(store_id=None, r=(i + 1) * 1e-3 * u.Mpc,
                                              zeta=0.1, C=0.2, C_bar=0.3) for i in range(4)]
            cf._full_result = None if failure or full is None else {"failure": False}
            cf._full_values = [] if failure or full is None else values
            cf._slow_roll_result = None if failure or slow is None else {"failure": False}
            cf._slow_roll_values = [] if failure or slow is None else values
            stored = ray.get(pool.object_store(cf))
            if validate:
                assert ray.get(pool.object_validate(stored)) is True
            return stored

        # successful; unvalidated, with no slow-roll instanton (the nullable parent); failed
        compaction(p_quadratic, fi[0], sri[0], dns[0], False, True)
        compaction(p_quartic, fi[1], None, dns[1], False, False)
        compaction(p_quadratic, fi[2], sri[2], dns[2], True, True)

        def gradient(proxy, dn, failure):
            obj = GradientCoupledInstanton(
                store_id=None, trajectory=proxy, N_init=n_init, N_final=n_final, delta_Nstar=dn,
                n_collocation_points=ncp, alpha_regularization=alpha, atol=atol, rtol=rtol,
                cosmo=cosmo, N_sample=None, diffusion_model=diffusion)
            obj._diagnostics = {"compute_time": 0.1, "converged": not failure}
            obj._failure = failure
            if not failure:
                obj._N_total = 1.0
                obj._values = [GradientCoupledInstantonValue(
                    store_id=None, N=e, phi=[0.1] * 5, pi=[0.2] * 5, rfield=[0.3] * 5,
                    rmom=[0.4] * 5) for e in efolds[:3]]
                obj._profile = [GradientCoupledInstantonProfileValue(
                    node_index=j, zeta=0.01 * j, r_ratio=1.0 - 0.1 * j, C=0.05 * j,
                    r_phys=1.0e3 * (5 - j), C_bar=0.04 * j) for j in range(5)]
            stored = ray.get(pool.object_store(obj))
            assert ray.get(pool.object_validate(stored)) is True
            return stored

        gradient(p_quadratic, dns[0], False)
        gradient(p_quadratic, dns[2], True)
        result["ok"] = True
    finally:
        pool.__exit__(None, None, None)
finally:
    ray.shutdown()
print("RESULT " + json.dumps(result), flush=True)
"""

# every class of the inventory, and its count: (records, replicated)
EXPECTED_COUNTS = {
    "version": (1, True),
    "store_tag": (0, True),
    "redshift": (0, False),
    "tolerance": (2, True),
    "efold_value": (25, True),
    "delta_Nstar": (3, True),
    "N_init": (1, True),
    "N_final": (1, True),
    "n_collocation_points": (1, True),
    "alpha_regularization": (1, True),
    "inflaton_mass": (1, True),
    "quartic_coupling": (1, True),
    "phi_value": (2, True),
    "pi_value": (1, True),
    "MasslessDecoupledDiffusion": (1, True),
    "IntegrationSolver": (0, True),
    "CosmologicalParams": (1, True),
    "QuadraticPotential": (1, True),
    "QuarticPotential": (1, True),
    "InflatonTrajectory": (3, True),
    "FullInstanton": (3, False),
    "GradientCoupledInstanton": (2, False),
    "SlowRollInstanton": (3, False),
    "CompactionFunction": (3, False),
}


@pytest.fixture(scope="module")
def store():
    with tempfile.TemporaryDirectory(prefix="si10-inventory-") as tmpdir:
        db = Path(tmpdir) / "inventory.sqlite"
        proc = subprocess.run(
            [sys.executable, "-c", _STORE_SCRIPT, str(_ROOT), str(db)],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert proc.returncode == 0, (
            f"store process failed ({proc.returncode})\nstdout:\n{proc.stdout[-4000:]}\n"
            f"stderr:\n{proc.stderr[-4000:]}"
        )
        assert "RESULT " + json.dumps({"ok": True}) in proc.stdout.splitlines()
        yield db


def _files(directory):
    """Each file in the store's directory, with its size and digest."""
    return {
        p.name: (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(Path(directory).iterdir())
    }


def _shard_counts(db, table):
    counts = []
    for shard in sorted(db.parent.glob(f"{db.stem}-shard*{db.suffix}")):
        conn = sqlite3.connect(f"file:{shard}?mode=ro", uri=True)
        try:
            counts.append(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
        finally:
            conn.close()
    return counts


def _main(db, *extra):
    return subprocess.run(
        [
            sys.executable,
            str(_ROOT / "main.py"),
            "--database",
            str(db),
            "--ray-address",
            _ADDRESS,
            "--inventory",
            *extra,
        ],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        env=dict(os.environ, RAY_ADDRESS=_ADDRESS),
    )


@pytest.mark.integration
def test_the_store_reads_back_with_every_class_and_no_problem(store):
    inventory = read_inventory(store, factories)
    assert inventory.shards == (0, 1)
    assert {
        name: (c.count, c.replicated) for name, c in inventory.classes.items()
    } == EXPECTED_COUNTS
    assert inventory.problems == ()
    # the sharded rows are on both shards, so the inventory's union is exercised
    assert all(n > 0 for n in _shard_counts(store, "FullInstanton")), store

    # every compute target's record is validated but the one compaction function left so, and
    # the value rows its spec counts are the ones written
    def flags(name):
        return sorted((r.validated, r.value_count) for r in inventory[name].records)

    assert flags("InflatonTrajectory") == [(True, 0), (True, 25), (True, 25)]
    assert flags("FullInstanton") == [(True, 0), (True, 3), (True, 3)]
    assert flags("SlowRollInstanton") == [(True, 0), (True, 3), (True, 3)]
    assert flags("GradientCoupledInstanton") == [(True, 0), (True, 5)]
    assert flags("CompactionFunction") == [(False, 4), (True, 0), (True, 8)]
    # the unvalidated compaction function has no slow-roll instanton: a nullable parent's None
    (unvalidated,) = [
        r for r in inventory["CompactionFunction"].records if not r.validated
    ]
    resolved = inventory.resolve("CompactionFunction", unvalidated)
    assert resolved["slow_roll_instanton"] is None
    assert resolved["full_instanton"]["class"] == "FullInstanton"


@pytest.mark.integration
def test_the_report_shows_the_fields_of_today_s_report(store):
    report = format_inventory_report(read_inventory(store, factories), store)
    lines = report.split("\n")
    assert lines[0] == f"@@ DATASTORE INVENTORY: {store}"
    assert lines[2] == "   problems: none"
    for line in (
        "      3 values: [ 0.5, 1.5, 2.5 ]",
        "      1 value: [ 20 ]",
        "      1 value: [ 5 ]",
        "      2 values: [ 15 PlanckMass, 16 PlanckMass ]",
        "      1 value: [ -0.1 PlanckMass ]",
        "      1 value: [ 1e-05 PlanckMass ]",
        "      1 value: [ 1e-13 ]",
        "         :: m=1e-05 PlanckMass",
        "         :: lambda_=1e-13",
        "      @@ unvalidated: 1 record(s)",
        "         :: delta_Nstar=0.5 | 5 value rows",
        "         :: delta_Nstar=2.5 | 0 value rows",
    ):
        assert line in lines, line
    # 25 e-fold values: the first and last ten
    assert any(
        ln.startswith("      25 values: [ 0, 0.5, ")
        and "... 5 values not shown (--show-all shows every one) ..." in ln
        for ln in lines
    )
    # the instantons by delta_Nstar and the trajectory's phi0 and potential, not by serials
    assert (
        "         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, "
        "potential=QuarticPotential(lambda_=1e-13)) | 3 value rows"
    ) in lines
    assert (
        sum(
            ln.startswith("      common to every record: N_init=20, N_final=5")
            for ln in lines
        )
        == 3
    )
    assert sum(ln.startswith("      @@ validated: ") for ln in lines) == 5
    assert sum(" committed " in ln for ln in lines) == 5
    assert "serial" not in report.replace("_serial", "")
    assert "0x" not in report


@pytest.mark.integration
def test_main_inventory_prints_the_report_before_ray_and_changes_nothing(store):
    before = _files(store.parent)
    result = _main(store)
    assert result.returncode == 0, result.stdout + result.stderr
    provenance, rest = result.stdout.split("\n", 1)
    assert provenance.startswith(">> packages: ")
    assert (
        rest == format_inventory_report(read_inventory(store, factories), store) + "\n"
    )
    assert result.stderr == "", result.stderr
    assert _files(store.parent) == before


@pytest.mark.integration
def test_main_inventory_show_all_is_verbose(store):
    result = _main(store, "--show-all")
    assert result.returncode == 0, result.stdout + result.stderr
    verbose = format_inventory_report(
        read_inventory(store, factories), store, verbose=True
    )
    assert result.stdout.split("\n", 1)[1] == verbose + "\n"
    every = ", ".join(f"{0.5 * k:.6g}" for k in range(25))
    assert f"      25 values: [ {every} ]" in verbose.split("\n")
