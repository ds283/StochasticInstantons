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

"""InflatonTrajectory's factories in the form DatastoreKit will call them.

Prompt 06 of the ``dk-and-rpk-migration`` campaign: the prune of unvalidated trajectories
cascades to their ``InflatonTrajectoryValue`` rows, every ``validate_on_startup`` hook names
its fourth parameter ``prune``, the two factories declare ``owner_column`` and
``validated_column``, and ``revalidate`` recomputes the stored flag by ``validate``'s rule.

The tests without Ray build a temporary SQLite store whose tables are built from every
factory's ``register()`` in ``config.datastore.factories``, in its order, as the package's
``datastorekit.SQL.schema.build_schema`` builds them (``serial``, ``version``, ``timestamp``
and ``stepping`` by the flags, then the columns; SI's old layer's ``Datastore._build_schema``
had the same rule). All 30 tables are built because SQLAlchemy
resolves every ``ForeignKey`` at ``create_all``. The parent rows a trajectory names
(``tolerance``, ``phi_value``, ``pi_value``, ``inflaton_mass``, ``QuadraticPotential``,
``efold_value``, ``version``) are minted by their own factories' ``build()``, and the
trajectories are written and validated by ``sqla_InflatonTrajectory_factory``'s own
``store()`` and ``validate()``, each in one transaction, as the actor runs them.

The integration test runs the ``datastorekit`` package's ``ShardedPool`` in subprocesses (see
its docstring): since prompt 09 the prune at open is the package's replicated prune.
"""

import importlib
import inspect
import json
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import sqlalchemy as sqla

_config = importlib.import_module("config.datastore")

from ComputeTargets.InflatonTrajectory import (  # noqa: E402
    InflatonTrajectory,
    InflatonTrajectoryValue,
)
from Units import Planck_units  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_factories = _config.factories

# The factories whose own class defines validate_on_startup (the others inherit the package's
# SQLAFactoryBase's).
_HOOK_FACTORIES = [
    "InflatonTrajectory",
    "InflatonTrajectoryValue",
    "CosmologicalParams",
    "FullInstanton",
    "FullInstantonValue",
    "GradientCoupledInstanton",
    "GradientCoupledInstantonValue",
    "GradientCoupledInstantonProfile",
    "SlowRollInstanton",
    "SlowRollInstantonValue",
    "CompactionFunction",
    "CompactionFunctionSamples",
]


class _Store:
    """A temporary SQLite store with the tables of every registered factory."""

    def __init__(self, path):
        self.engine = sqla.create_engine(f"sqlite:///{path}")
        self.metadata = sqla.MetaData()
        self.tables = {}
        self.inserters = {}
        self.version_serial = None

        for name, factory in _factories.items():
            reg = factory.register()
            if reg is None:
                continue
            tab = sqla.Table(name, self.metadata)
            use_serial = reg.get("serial", True)
            if use_serial:
                tab.append_column(sqla.Column("serial", sqla.Integer, primary_key=True))
            use_version = reg.get("version", False)
            if use_version:
                tab.append_column(
                    sqla.Column(
                        "version",
                        sqla.Integer,
                        sqla.ForeignKey("version.serial"),
                        index=True,
                    )
                )
            use_timestamp = reg.get("timestamp", False)
            if use_timestamp:
                tab.append_column(sqla.Column("timestamp", sqla.DateTime()))
            stepping = reg.get("stepping", False)
            if stepping is True or stepping in ("minimum", "exact"):
                tab.append_column(sqla.Column("stepping", sqla.Integer))
            for col in reg.get("columns", []):
                tab.append_column(col)

            self.tables[name] = tab
            self.inserters[name] = self._inserter(
                tab, use_serial, use_version, use_timestamp
            )

        self.metadata.create_all(self.engine)
        self.version_serial = self.get("version", label="06-test").store_id

    def _inserter(self, tab, use_serial, use_version, use_timestamp):
        # The actor's insert without the serial broker: the engine assigns the serial.
        def insert(conn, payload):
            payload = dict(payload)
            if not use_serial:
                payload.pop("serial", None)
            if use_version:
                payload["version"] = self.version_serial
            if use_timestamp:
                payload["timestamp"] = datetime.now()
            result = conn.execute(sqla.insert(tab), payload)
            if use_serial:
                return result.lastrowid

        return insert

    def get(self, name, **payload):
        with self.engine.begin() as conn:
            return _factories[name].build(
                payload,
                conn,
                self.tables[name],
                self.inserters[name],
                self.tables,
                self.inserters,
            )

    def store(self, obj):
        name = type(obj).__name__
        with self.engine.begin() as conn:
            return _factories[name].store(
                obj,
                conn,
                self.tables[name],
                self.inserters[name],
                self.tables,
                self.inserters,
            )

    def validate(self, obj):
        name = type(obj).__name__
        with self.engine.begin() as conn:
            return _factories[name].validate(obj, conn, self.tables[name], self.tables)

    def validate_on_startup(self, name, prune):
        with self.engine.begin() as conn:
            return _factories[name].validate_on_startup(
                conn, self.tables[name], self.tables, prune
            )

    def revalidate(self, serial):
        with self.engine.begin() as conn:
            return _factories["InflatonTrajectory"].revalidate(
                serial, conn, self.tables["InflatonTrajectory"], self.tables
            )

    def counts(self):
        with self.engine.connect() as conn:
            return {
                name: conn.execute(
                    sqla.select(sqla.func.count()).select_from(tab)
                ).scalar()
                for name, tab in self.tables.items()
            }

    def trajectories(self):
        tab = self.tables["InflatonTrajectory"]
        with self.engine.connect() as conn:
            return {
                r.serial: r.validated
                for r in conn.execute(sqla.select(tab.c.serial, tab.c.validated))
            }

    def value_rows(self):
        """{trajectory_serial: number of InflatonTrajectoryValue rows}."""
        tab = self.tables["InflatonTrajectoryValue"]
        with self.engine.connect() as conn:
            return {
                r.trajectory_serial: r.n
                for r in conn.execute(
                    sqla.select(
                        tab.c.trajectory_serial, sqla.func.count().label("n")
                    ).group_by(tab.c.trajectory_serial)
                )
            }


class _Parents:
    """The parent objects a trajectory names, minted in the store by their factories."""

    def __init__(self, store):
        self.units = Planck_units()
        u = self.units
        self.atol = store.get("tolerance", log10_tol=-10)
        self.rtol = store.get("tolerance", log10_tol=-8)
        self.phi0 = store.get("phi_value", value=15.0 * u.PlanckMass, units=u)
        mass = store.get("inflaton_mass", value=1.0e-5 * u.PlanckMass, units=u)
        self.potential = store.get("QuadraticPotential", m=mass, units=u)
        # Five e-folds on the shard; a complete trajectory uses three of them.
        self.efolds = [store.get("efold_value", N=float(n)) for n in range(5)]
        self._store = store
        self._next_pi = 1

    def trajectory(self, efolds=None, failure=False):
        u = self.units
        pi0 = self._store.get(
            "pi_value", value=-0.1 * self._next_pi * u.PlanckMass, units=u
        )
        self._next_pi += 1
        t = InflatonTrajectory(
            store_id=None,
            phi0=self.phi0,
            pi0=pi0,
            potential=self.potential,
            samples_per_N=1.0,
            atol=self.atol,
            rtol=self.rtol,
        )
        t._diagnostics = {"compute_time": 0.0}
        if failure:
            t._failure = True
            t._N_end = None
            t._values = []
            return t
        if efolds is None:
            efolds = self.efolds[:3]
        t._failure = False
        t._N_end = efolds[-1].N if efolds else 2.0
        t._values = [
            InflatonTrajectoryValue(
                store_id=None,
                N=e,
                phi=(15.0 - e.N) * u.PlanckMass,
                pi=-0.1 * u.PlanckMass,
            )
            for e in efolds
        ]
        return t


@pytest.fixture
def store():
    with tempfile.TemporaryDirectory(prefix="si06-prune-") as tmpdir:
        s = _Store(Path(tmpdir) / "store.sqlite")
        try:
            yield s
        finally:
            s.engine.dispose()


def _two_trajectories(store):
    """Store two trajectories by the factory, validate the first, withhold the second."""
    parents = _Parents(store)
    kept = store.store(parents.trajectory())
    assert store.validate(kept) is True
    pruned = store.store(parents.trajectory(efolds=parents.efolds[1:4]))
    assert store.trajectories() == {kept.store_id: True, pruned.store_id: False}
    assert store.value_rows() == {kept.store_id: 3, pruned.store_id: 3}
    return kept.store_id, pruned.store_id


# ---------------------------------------------------------------------------
# I1 — the cascade
# ---------------------------------------------------------------------------


def test_prune_deletes_the_unvalidated_trajectory_and_its_value_rows(store):
    kept, pruned = _two_trajectories(store)
    before = store.counts()

    msgs = store.validate_on_startup("InflatonTrajectory", prune=True)

    assert msgs == ["Pruned 1 unvalidated InflatonTrajectory records"]
    assert store.trajectories() == {kept: True}
    # The validated trajectory keeps all its own value rows, and none names the pruned one.
    assert store.value_rows() == {kept: 3}

    after = store.counts()
    lost = {
        name: before[name] - after[name]
        for name in before
        if after[name] != before[name]
    }
    assert lost == {"InflatonTrajectory": 1, "InflatonTrajectoryValue": 3}
    # The parents the trajectories name are still there.
    for name in (
        "tolerance",
        "phi_value",
        "pi_value",
        "inflaton_mass",
        "QuadraticPotential",
        "efold_value",
        "version",
    ):
        assert after[name] == before[name] > 0, name

    # The package's second call: with prune=False the hook reports nothing.
    assert store.validate_on_startup("InflatonTrajectory", prune=False) == []
    assert store.counts() == after


def test_without_prune_the_hook_reports_and_deletes_nothing(store):
    kept, pruned = _two_trajectories(store)
    before = store.counts()

    msgs = store.validate_on_startup("InflatonTrajectory", prune=False)

    assert msgs == ["Found 1 unvalidated InflatonTrajectory records (not pruned)"]
    assert store.counts() == before
    assert store.trajectories() == {kept: True, pruned: False}
    assert store.value_rows() == {kept: 3, pruned: 3}


# ---------------------------------------------------------------------------
# I4 — revalidate agrees with validate
# ---------------------------------------------------------------------------


def _set_validated(store, serial, flag):
    tab = store.tables["InflatonTrajectory"]
    with store.engine.begin() as conn:
        conn.execute(
            sqla.update(tab).where(tab.c.serial == serial).values(validated=flag)
        )


def test_revalidate_agrees_with_validate(store):
    parents = _Parents(store)

    # A complete row: validate sets True; the flag is cleared by hand, as an interrupted
    # validate leaves it on a shard; revalidate gives True and writes it.
    complete = store.store(parents.trajectory())
    assert store.validate(complete) is True
    _set_validated(store, complete.store_id, False)
    assert store.revalidate(complete.store_id) is True
    assert store.trajectories()[complete.store_id] is True

    # A failed row: N_end NULL and no value rows. validate gives True, and so does revalidate.
    failed = store.store(parents.trajectory(failure=True))
    assert store.validate(failed) is True
    _set_validated(store, failed.store_id, False)
    assert store.revalidate(failed.store_id) is True
    assert store.trajectories()[failed.store_id] is True

    # A row whose value rows were removed by hand: revalidate gives False and writes it.
    stripped = store.store(parents.trajectory(efolds=parents.efolds[2:5]))
    assert store.validate(stripped) is True
    value_table = store.tables["InflatonTrajectoryValue"]
    with store.engine.begin() as conn:
        conn.execute(
            sqla.delete(value_table).where(
                value_table.c.trajectory_serial == stripped.store_id
            )
        )
    assert store.revalidate(stripped.store_id) is False
    assert store.trajectories()[stripped.store_id] is False

    # A non-failed row stored with no value rows: validate gives False, and so does revalidate.
    empty = store.store(parents.trajectory(efolds=[]))
    assert store.validate(empty) is False
    assert store.revalidate(empty.store_id) is False

    # Revalidating a row that holds True leaves it True, and touches no other row.
    assert store.revalidate(complete.store_id) is True
    assert store.trajectories() == {
        complete.store_id: True,
        failed.store_id: True,
        stripped.store_id: False,
        empty.store_id: False,
    }


def test_revalidate_raises_for_a_missing_serial(store):
    with pytest.raises(RuntimeError, match="serial 4242"):
        store.revalidate(4242)


# ---------------------------------------------------------------------------
# I2 — prune, in every hook
# ---------------------------------------------------------------------------


def test_every_hook_takes_prune():
    own = {
        name: factory
        for name, factory in _factories.items()
        if "validate_on_startup" in type(factory).__dict__
    }
    assert sorted(own) == sorted(_HOOK_FACTORIES)
    assert len(own) == 12

    wrong = {
        f"{name} ({type(factory).__name__})": list(
            inspect.signature(factory.validate_on_startup).parameters
        )
        for name, factory in own.items()
        if list(inspect.signature(factory.validate_on_startup).parameters)
        != ["conn", "table", "tables", "prune"]
    }
    assert not wrong, f"hooks not taking (conn, table, tables, prune): {wrong}"


# ---------------------------------------------------------------------------
# I3 — the two register() keys
# ---------------------------------------------------------------------------


def test_register_declares_owner_column_and_validated_column():
    value_reg = _factories["InflatonTrajectoryValue"].register()
    assert value_reg["owner_column"] == "trajectory_serial"
    (owner,) = [c for c in value_reg["columns"] if c.name == "trajectory_serial"]
    fks = list(owner.foreign_keys)
    assert len(fks) == 1
    assert fks[0].target_fullname == "InflatonTrajectory.serial"

    traj_reg = _factories["InflatonTrajectory"].register()
    assert traj_reg["validated_column"] == "validated"
    (flag,) = [c for c in traj_reg["columns"] if c.name == "validated"]
    assert isinstance(flag.type, sqla.Boolean)


# ---------------------------------------------------------------------------
# I6 — the prune at open, through the package's ShardedPool, on two shards
# ---------------------------------------------------------------------------

_POOL_SCRIPT = r"""
import json, sys
from pathlib import Path
root, mode, db = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, root)

import ray
from datastorekit.SQL.ShardedPool import ShardedPool
import config.datastore
from config.sharding import (ShardKeyType, get_shard_key_store_id,
                             read_table_config, replicated_tables, sharded_tables)
from ComputeTargets.InflatonTrajectory import InflatonTrajectory, InflatonTrajectoryValue
from Units import Planck_units

ray.init(address="local", include_dashboard=False)
try:
    pool = ShardedPool(
        version_label="06-prune-test", db_name=db, ShardKeyType=ShardKeyType,
        ShardKeyStoreIdGetter=get_shard_key_store_id, replicated_tables=replicated_tables,
        sharded_tables=sharded_tables, shards=2, profile_agent=None, job_name="06-prune-test",
        prune_unvalidated=(mode == "reopen"), read_table_config=read_table_config,
        factories=config.datastore.factories,
        serial_batch_sizes=config.datastore.serial_batch_sizes,
    )
    try:
        result = {}
        if mode == "store":
            u = Planck_units()
            atol, rtol, phi0, pi0a, pi0b = ray.get([
                pool.object_get("tolerance", log10_tol=-10),
                pool.object_get("tolerance", log10_tol=-8),
                pool.object_get("phi_value", value=15.0 * u.PlanckMass, units=u),
                pool.object_get("pi_value", value=-0.1 * u.PlanckMass, units=u),
                pool.object_get("pi_value", value=-0.2 * u.PlanckMass, units=u),
            ])
            mass = ray.get(pool.object_get("inflaton_mass", value=1.0e-5 * u.PlanckMass, units=u))
            pot = ray.get(pool.object_get("QuadraticPotential", m=mass, units=u))
            efolds = ray.get(pool.object_get(
                "efold_value", payload_data=[{"N": n} for n in (0.0, 1.0, 2.0)]))
            stored = []
            for pi0 in (pi0a, pi0b):
                t = InflatonTrajectory(store_id=None, phi0=phi0, pi0=pi0, potential=pot,
                                       samples_per_N=1.0, atol=atol, rtol=rtol)
                t._failure = False
                t._N_end = 2.0
                t._diagnostics = {"compute_time": 0.0}
                t._values = [InflatonTrajectoryValue(store_id=None, N=e,
                                                     phi=(15.0 - e.N) * u.PlanckMass,
                                                     pi=-0.1 * u.PlanckMass) for e in efolds]
                stored.append(ray.get(pool.object_store(t)))
            # Validate the first; withhold the second's validation.
            result["validated"] = ray.get(pool.object_validate(stored[0]))
            result["kept"] = stored[0].store_id
            result["pruned"] = stored[1].store_id
    finally:
        pool.__exit__(None, None, None)
finally:
    ray.shutdown()
print("RESULT " + json.dumps(result), flush=True)
"""


def _run_pool(mode, db):
    proc = subprocess.run(
        [sys.executable, "-c", _POOL_SCRIPT, str(_ROOT), mode, str(db)],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, (
        f"{mode} process failed ({proc.returncode})\n"
        f"stdout:\n{proc.stdout[-4000:]}\nstderr:\n{proc.stderr[-4000:]}"
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, (
        f"{mode} process printed no RESULT line\nstdout:\n{proc.stdout[-4000:]}"
    )
    return json.loads(lines[-1][len("RESULT ") :])


def _read_shard(path):
    """(trajectories {serial: validated}, value rows {trajectory_serial: n}, orphans)."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        trajectories = {
            s: bool(v)
            for s, v in conn.execute("SELECT serial, validated FROM InflatonTrajectory")
        }
        values = dict(
            conn.execute(
                "SELECT trajectory_serial, COUNT(*) FROM InflatonTrajectoryValue "
                "GROUP BY trajectory_serial"
            ).fetchall()
        )
        orphans = conn.execute(
            "SELECT COUNT(*) FROM InflatonTrajectoryValue v "
            "LEFT JOIN InflatonTrajectory t ON v.trajectory_serial = t.serial "
            "WHERE t.serial IS NULL"
        ).fetchone()[0]
    finally:
        conn.close()
    return trajectories, values, orphans


@pytest.mark.integration
def test_prune_at_open_leaves_no_orphan_on_either_shard():
    """The package's replicated prune at open (U4; dk-and-rpk-migration prompt 09, acceptance 4).

    It needs Ray because the store is written through the package's pool, whose actors hold
    the shards. It runs the package's ShardedPool in two fresh processes, one per open, each
    under its own ``ray.init(address="local")``, and never initialises or shuts down Ray in the
    pytest process. ``live_pool`` cannot serve: it is session-scoped and opened without the
    prune. Nor can a second pool share its Ray while ``live_pool`` is open: the pool names its
    actors, so a second pool cannot open in a Ray session where another is open. The package's
    ``__exit__`` does free the names (its contract §9.3), so one process would do for the two
    opens; the two processes of prompt 06's test are kept, and each exits with its Ray.
    At the reopen the package prunes the replicated class before any actor exists
    (``_prune_replicated_tables``, ``_prune_shard``), deleting from the class's unit only: the
    ``InflatonTrajectoryValue`` rows are in it because that factory declares ``owner_column``,
    or the prune is refused.
    """
    with tempfile.TemporaryDirectory(prefix="si06-prune-pool-") as tmpdir:
        db = Path(tmpdir) / "prune.sqlite"

        stored = _run_pool("store", db)
        assert stored["validated"] is True
        kept, pruned = stored["kept"], stored["pruned"]
        assert kept != pruned

        shards = sorted(Path(tmpdir).glob("prune-shard*.sqlite"))
        assert len(shards) == 2, shards

        # Before the reopen: on each shard both trajectories, one validated and one not,
        # each with all its value rows.
        for shard in shards:
            trajectories, values, orphans = _read_shard(shard)
            assert trajectories == {kept: True, pruned: False}, shard.name
            assert values == {kept: 3, pruned: 3}, shard.name
            assert orphans == 0, shard.name

        assert _run_pool("reopen", db) == {}

        # After: the validated trajectory and all its value rows; the other gone, and no
        # InflatonTrajectoryValue row naming a missing trajectory.
        for shard in shards:
            trajectories, values, orphans = _read_shard(shard)
            assert trajectories == {kept: True}, shard.name
            assert orphans == 0, f"{shard.name}: {orphans} orphaned value rows"
            assert values == {kept: 3}, shard.name
