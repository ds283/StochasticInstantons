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

import json
from datetime import datetime

import sqlalchemy as sqla

from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase


class sqla_CompactionFunctionFactory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": True,
            "timestamp": True,
            "validate_on_startup": True,
            "columns": [
                sqla.Column(
                    "trajectory_serial",
                    sqla.Integer,
                    sqla.ForeignKey("InflatonTrajectory.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "full_instanton_serial",
                    sqla.Integer,
                    sqla.ForeignKey("FullInstanton.serial"),
                    index=True,
                    nullable=True,
                ),
                sqla.Column(
                    "slow_roll_instanton_serial",
                    sqla.Integer,
                    sqla.ForeignKey("SlowRollInstanton.serial"),
                    index=True,
                    nullable=True,
                ),
                sqla.Column(
                    "delta_Nstar_serial",
                    sqla.Integer,
                    sqla.ForeignKey("delta_Nstar.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "cosmo_serial",
                    sqla.Integer,
                    sqla.ForeignKey("CosmologicalParams.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "atol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_compaction_function_atol"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "rtol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_compaction_function_rtol"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column("C_threshold", sqla.Float(64), nullable=False),
                sqla.Column("C_bar_threshold", sqla.Float(64), nullable=False),
                # Full instanton results
                sqla.Column("r_max_C_full_Mpc", sqla.Float(64), nullable=True),
                sqla.Column("r_max_C_bar_full_Mpc", sqla.Float(64), nullable=True),
                sqla.Column("M_C_full_SolarMass", sqla.Float(64), nullable=True),
                sqla.Column("M_C_bar_full_SolarMass", sqla.Float(64), nullable=True),
                sqla.Column("C_max_full", sqla.Float(64), nullable=True),
                sqla.Column("C_bar_max_full", sqla.Float(64), nullable=True),
                sqla.Column("V_end_downflow_full_PlanckMass4", sqla.Float(64), nullable=True),
                sqla.Column("N_end_downflow_full", sqla.Float(64), nullable=True),
                sqla.Column("failure_full", sqla.Integer, nullable=False, default=1),
                # Slow-roll instanton results
                sqla.Column("r_max_C_slow_roll_Mpc", sqla.Float(64), nullable=True),
                sqla.Column("r_max_C_bar_slow_roll_Mpc", sqla.Float(64), nullable=True),
                sqla.Column("M_C_slow_roll_SolarMass", sqla.Float(64), nullable=True),
                sqla.Column("M_C_bar_slow_roll_SolarMass", sqla.Float(64), nullable=True),
                sqla.Column("C_max_slow_roll", sqla.Float(64), nullable=True),
                sqla.Column("C_bar_max_slow_roll", sqla.Float(64), nullable=True),
                sqla.Column("V_end_downflow_slow_roll_PlanckMass4", sqla.Float(64), nullable=True),
                sqla.Column("N_end_downflow_slow_roll", sqla.Float(64), nullable=True),
                sqla.Column("failure_slow_roll", sqla.Integer, nullable=False, default=1),
                sqla.Column("metadata", sqla.Text, nullable=True),
                sqla.Column(
                    "validated",
                    sqla.Boolean,
                    nullable=False,
                    default=False,
                    index=True,
                ),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        from ComputeTargets.CompactionFunction import CompactionFunction

        trajectory = payload["trajectory"]
        full_instanton = payload.get("full_instanton", None)
        slow_roll_instanton = payload.get("slow_roll_instanton", None)
        delta_Nstar_obj = payload["delta_Nstar"]
        cosmo = payload["cosmo"]
        atol = payload["atol"]
        rtol = payload["rtol"]
        C_threshold = payload.get("C_threshold", 0.4)
        C_bar_threshold = payload.get("C_bar_threshold", 0.4)
        label = payload.get("label", None)
        tags = payload.get("tags", [])

        full_serial = full_instanton.store_id if full_instanton is not None else None
        slow_roll_serial = slow_roll_instanton.store_id if slow_roll_instanton is not None else None

        query = sqla.select(
            table.c.serial,
            table.c.failure_full,
            table.c.failure_slow_roll,
            table.c.r_max_C_full_Mpc,
            table.c.r_max_C_bar_full_Mpc,
            table.c.M_C_full_SolarMass,
            table.c.M_C_bar_full_SolarMass,
            table.c.C_max_full,
            table.c.C_bar_max_full,
            table.c.V_end_downflow_full_PlanckMass4,
            table.c.N_end_downflow_full,
            table.c.r_max_C_slow_roll_Mpc,
            table.c.r_max_C_bar_slow_roll_Mpc,
            table.c.M_C_slow_roll_SolarMass,
            table.c.M_C_bar_slow_roll_SolarMass,
            table.c.C_max_slow_roll,
            table.c.C_bar_max_slow_roll,
            table.c.V_end_downflow_slow_roll_PlanckMass4,
            table.c.N_end_downflow_slow_roll,
            table.c.metadata,
        ).filter(
            table.c.validated == True,
            table.c.trajectory_serial == trajectory.store_id,
            table.c.delta_Nstar_serial == delta_Nstar_obj.store_id,
            table.c.cosmo_serial == cosmo.store_id,
            table.c.atol_serial == atol.store_id,
            table.c.rtol_serial == rtol.store_id,
        )

        # Match on full_instanton_serial
        if full_serial is not None:
            query = query.filter(table.c.full_instanton_serial == full_serial)
        else:
            query = query.filter(table.c.full_instanton_serial.is_(None))

        # Match on slow_roll_instanton_serial
        if slow_roll_serial is not None:
            query = query.filter(table.c.slow_roll_instanton_serial == slow_roll_serial)
        else:
            query = query.filter(table.c.slow_roll_instanton_serial.is_(None))

        row = conn.execute(query).one_or_none()

        if row is None:
            obj = CompactionFunction(
                store_id=None,
                full_instanton=full_instanton,
                slow_roll_instanton=slow_roll_instanton,
                trajectory=trajectory,
                cosmo=cosmo,
                delta_Nstar=delta_Nstar_obj,
                C_threshold=C_threshold,
                C_bar_threshold=C_bar_threshold,
                atol=atol,
                rtol=rtol,
                label=label,
                tags=tags,
            )
            return obj

        units = trajectory.units
        PlanckMass4 = units.PlanckMass ** 4

        obj = CompactionFunction(
            store_id=row.serial,
            full_instanton=full_instanton,
            slow_roll_instanton=slow_roll_instanton,
            trajectory=trajectory,
            cosmo=cosmo,
            delta_Nstar=delta_Nstar_obj,
            C_threshold=C_threshold,
            C_bar_threshold=C_bar_threshold,
            atol=atol,
            rtol=rtol,
            label=label,
            tags=tags,
        )
        obj._failure = bool(row.failure_full) and bool(row.failure_slow_roll)
        obj._diagnostics = json.loads(row.metadata) if row.metadata else None

        def _restore_r(val):
            return val * units.Mpc if val is not None else None

        def _restore_M(val):
            return val * units.SolarMass if val is not None else None

        def _restore_V(val):
            return val * PlanckMass4 if val is not None else None

        obj._r_max_C_full             = _restore_r(row.r_max_C_full_Mpc)
        obj._r_max_C_bar_full         = _restore_r(row.r_max_C_bar_full_Mpc)
        obj._M_C_full                 = _restore_M(row.M_C_full_SolarMass)
        obj._M_C_bar_full             = _restore_M(row.M_C_bar_full_SolarMass)
        obj._C_max_full               = row.C_max_full
        obj._C_bar_max_full           = row.C_bar_max_full
        obj._V_end_downflow_full      = _restore_V(row.V_end_downflow_full_PlanckMass4)
        obj._N_end_downflow_full      = row.N_end_downflow_full
        obj._r_max_C_slow_roll        = _restore_r(row.r_max_C_slow_roll_Mpc)
        obj._r_max_C_bar_slow_roll    = _restore_r(row.r_max_C_bar_slow_roll_Mpc)
        obj._M_C_slow_roll            = _restore_M(row.M_C_slow_roll_SolarMass)
        obj._M_C_bar_slow_roll        = _restore_M(row.M_C_bar_slow_roll_SolarMass)
        obj._C_max_slow_roll          = row.C_max_slow_roll
        obj._C_bar_max_slow_roll      = row.C_bar_max_slow_roll
        obj._V_end_downflow_slow_roll = _restore_V(row.V_end_downflow_slow_roll_PlanckMass4)
        obj._N_end_downflow_slow_roll = row.N_end_downflow_slow_roll

        do_not_populate = payload.get("_do_not_populate", False)
        if not do_not_populate:
            self._populate(obj, row, tables, conn)

        setattr(obj, "_deserialized", True)
        return obj

    def _populate(self, obj, row, tables, conn):
        from ComputeTargets.CompactionFunction import CompactionFunctionValue

        samples_table = tables.get("CompactionFunctionSamples")
        if samples_table is None or not obj.available:
            return

        units = obj._trajectory.units

        rows = conn.execute(
            sqla.select(
                samples_table.c.source,
                samples_table.c.r_Mpc,
                samples_table.c.zeta,
                samples_table.c.C,
                samples_table.c.C_bar,
            ).filter(samples_table.c.parent_serial == obj.store_id)
        ).fetchall()

        full_vals = []
        sr_vals = []
        for r in rows:
            v = CompactionFunctionValue(
                store_id=None,
                r=r.r_Mpc * units.Mpc,
                zeta=r.zeta,
                C=r.C,
                C_bar=r.C_bar,
            )
            if r.source == "full":
                full_vals.append(v)
            elif r.source == "slow_roll":
                sr_vals.append(v)

        obj._full_values = full_vals
        obj._slow_roll_values = sr_vals

    def store(self, obj, conn, table, inserter, tables, inserters):
        full_instanton = obj._full_instanton
        slow_roll_instanton = obj._slow_roll_instanton
        full_serial = full_instanton.store_id if full_instanton is not None else None
        slow_roll_serial = slow_roll_instanton.store_id if slow_roll_instanton is not None else None

        full_result = getattr(obj, "_full_result", None)
        sr_result = getattr(obj, "_slow_roll_result", None)

        metadata_json = json.dumps(obj.diagnostics) if obj.diagnostics is not None else None

        units = obj._trajectory.units
        PlanckMass4 = units.PlanckMass ** 4

        def _r(result, key):
            v = result.get(key) if result is not None else None
            return v / units.Mpc if v is not None else None

        def _M(result, key):
            v = result.get(key) if result is not None else None
            return v / units.SolarMass if v is not None else None

        def _V(result, key):
            v = result.get(key) if result is not None else None
            return v / PlanckMass4 if v is not None else None

        def _plain(result, key):
            return result.get(key) if result is not None else None

        store_id = inserter(conn, {
            "trajectory_serial": obj._trajectory.store_id,
            "full_instanton_serial": full_serial,
            "slow_roll_instanton_serial": slow_roll_serial,
            "delta_Nstar_serial": obj._delta_Nstar.store_id,
            "cosmo_serial": obj._cosmo.store_id,
            "atol_serial": obj._atol.store_id,
            "rtol_serial": obj._rtol.store_id,
            "C_threshold": obj._C_threshold,
            "C_bar_threshold": obj._C_bar_threshold,
            "r_max_C_full_Mpc":                   _r(full_result, "r_max_C"),
            "r_max_C_bar_full_Mpc":               _r(full_result, "r_max_C_bar"),
            "M_C_full_SolarMass":                 _M(full_result, "M_C"),
            "M_C_bar_full_SolarMass":             _M(full_result, "M_C_bar"),
            "C_max_full":                          _plain(full_result, "C_max"),
            "C_bar_max_full":                      _plain(full_result, "C_bar_max"),
            "V_end_downflow_full_PlanckMass4":    _V(full_result, "V_end_downflow"),
            "N_end_downflow_full":                 _plain(full_result, "N_end_downflow"),
            "failure_full": 1 if (full_result is None or full_result.get("failure", True)) else 0,
            "r_max_C_slow_roll_Mpc":              _r(sr_result, "r_max_C"),
            "r_max_C_bar_slow_roll_Mpc":          _r(sr_result, "r_max_C_bar"),
            "M_C_slow_roll_SolarMass":            _M(sr_result, "M_C"),
            "M_C_bar_slow_roll_SolarMass":        _M(sr_result, "M_C_bar"),
            "C_max_slow_roll":                     _plain(sr_result, "C_max"),
            "C_bar_max_slow_roll":                 _plain(sr_result, "C_bar_max"),
            "V_end_downflow_slow_roll_PlanckMass4": _V(sr_result, "V_end_downflow"),
            "N_end_downflow_slow_roll":            _plain(sr_result, "N_end_downflow"),
            "failure_slow_roll": 1 if (sr_result is None or sr_result.get("failure", True)) else 0,
            "metadata": metadata_json,
            "validated": False,
        })
        obj._my_id = store_id

        samples_inserter = inserters["CompactionFunctionSamples"]

        for v in obj._full_values:
            samples_inserter(conn, {
                "parent_serial": store_id,
                "source": "full",
                "r_Mpc": v.r / units.Mpc,
                "zeta": v.zeta,
                "C": v.C,
                "C_bar": v.C_bar,
            })

        for v in obj._slow_roll_values:
            samples_inserter(conn, {
                "parent_serial": store_id,
                "source": "slow_roll",
                "r_Mpc": v.r / units.Mpc,
                "zeta": v.zeta,
                "C": v.C,
                "C_bar": v.C_bar,
            })

        return obj

    def validate(self, obj, conn, table, tables):
        if not obj.available:
            raise RuntimeError("Attempt to validate an object that has not been stored")

        if obj.failure:
            validated = True
        else:
            samples_table = tables.get("CompactionFunctionSamples")
            if samples_table is not None:
                expected = len(obj._full_values) + len(obj._slow_roll_values)
                actual = conn.execute(
                    sqla.select(sqla.func.count()).select_from(samples_table).filter(
                        samples_table.c.parent_serial == obj.store_id
                    )
                ).scalar()
                validated = (actual == expected)
                if not validated:
                    print(f"!! WARNING: CompactionFunction {obj.store_id}: "
                          f"expected {expected} sample rows, found {actual}")
            else:
                validated = True

        conn.execute(
            sqla.update(table)
            .where(table.c.serial == obj.store_id)
            .values(validated=validated)
        )
        return validated

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        # Migrate existing databases that pre-date the C_bar_max columns.
        existing_cols = {c["name"] for c in sqla.inspect(conn).get_columns(table.name)}
        for col_name in ("C_bar_max_full", "C_bar_max_slow_roll"):
            if col_name not in existing_cols:
                conn.execute(sqla.text(f'ALTER TABLE "{table.name}" ADD COLUMN "{col_name}" REAL'))

        query = sqla.select(table.c.serial).filter(table.c.validated == False)
        rows = conn.execute(query).fetchall()

        if prune_unvalidated and len(rows) > 0:
            serials = [r.serial for r in rows]
            conn.execute(sqla.delete(table).filter(table.c.serial.in_(serials)))
            return [f"Pruned {len(serials)} unvalidated CompactionFunction records"]
        elif len(rows) > 0:
            return [f"Found {len(rows)} unvalidated CompactionFunction records (not pruned)"]
        return []

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.serial,
            table.c.timestamp,
            table.c.delta_Nstar_serial,
            table.c.validated,
        )
        rows = conn.execute(query).fetchall()

        earliest_validated = None
        latest_validated = None
        earliest_unvalidated = None
        latest_unvalidated = None
        validated_labels = []
        unvalidated_labels = []

        for row in rows:
            label = f"CompactionFunction(delta_Nstar_serial={row.delta_Nstar_serial})"
            ts = row.timestamp

            if row.validated:
                validated_labels.append(label)
                if latest_validated is None or ts > latest_validated:
                    latest_validated = ts
                if earliest_validated is None or ts < earliest_validated:
                    earliest_validated = ts
            else:
                unvalidated_labels.append(label)
                if latest_unvalidated is None or ts > latest_unvalidated:
                    latest_unvalidated = ts
                if earliest_unvalidated is None or ts < earliest_unvalidated:
                    earliest_unvalidated = ts

        return {
            "validated": {
                "labels": validated_labels,
                "versions": [],
                "earliest_timestamp": earliest_validated,
                "latest_timestamp": latest_validated,
            },
            "unvalidated": {
                "labels": unvalidated_labels,
                "versions": [],
                "earliest_timestamp": earliest_unvalidated,
                "latest_timestamp": latest_unvalidated,
            },
        }


class sqla_CompactionFunctionSamplesFactory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "serial": True,
            "version": False,
            "timestamp": False,
            "columns": [
                sqla.Column(
                    "parent_serial",
                    sqla.Integer,
                    sqla.ForeignKey("CompactionFunction.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column("source", sqla.Text, nullable=False),
                sqla.Column("r_Mpc", sqla.Float(64), nullable=False),
                sqla.Column("zeta", sqla.Float(64), nullable=False),
                sqla.Column("C", sqla.Float(64), nullable=False),
                sqla.Column("C_bar", sqla.Float(64), nullable=False),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_CompactionFunctionSamplesFactory.build() is not used directly; "
            "samples are inserted by sqla_CompactionFunctionFactory.store()."
        )

    def store(self, obj, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_CompactionFunctionSamplesFactory.store() is not used directly."
        )

    def validate(self, obj, conn, table, tables):
        raise NotImplementedError(
            "sqla_CompactionFunctionSamplesFactory.validate() is not used directly."
        )

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        return []
