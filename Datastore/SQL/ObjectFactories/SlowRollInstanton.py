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

import sqlalchemy as sqla

from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from config.defaults import DEFAULT_FLOAT_PRECISION


class sqla_SlowRollInstantonFactory(SQLAFactoryBase):
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
                sqla.Column("N_init", sqla.Float(64), index=True, nullable=False),
                sqla.Column("N_final", sqla.Float(64), index=True, nullable=False),
                sqla.Column(
                    "delta_Nstar_serial",
                    sqla.Integer,
                    sqla.ForeignKey("delta_Nstar.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "atol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_sr_instanton_atol"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "rtol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_sr_instanton_rtol"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column("n_fields", sqla.Integer, nullable=False, default=1),
                sqla.Column("N_total", sqla.Float(64), nullable=True),
                sqla.Column("msr_action", sqla.Float(64), nullable=True),
                sqla.Column("label", sqla.Text, nullable=True),
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
        from ComputeTargets.SlowRollInstanton import SlowRollInstanton
        from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion

        trajectory = payload["trajectory"]  # InflatonTrajectoryProxy
        N_init = payload["N_init"]  # N_efolds
        N_final = payload["N_final"]  # N_efolds
        delta_Nstar_obj = payload["delta_Nstar"]  # delta_Nstar
        atol = payload["atol"]
        rtol = payload["rtol"]
        N_sample = payload.get("N_sample", None)
        diffusion_model = payload.get("diffusion_model", MasslessDecoupledDiffusion())
        tags = payload.get("tags", [])
        do_not_populate = payload.get("_do_not_populate", False)
        label = payload.get("label", None)

        N_init_val = float(N_init)
        N_final_val = float(N_final)

        # Fuzzy float comparison for N_init and N_final (defensive zero-check)
        if N_init_val != 0.0:
            N_init_cond = (
                sqla.func.abs((table.c.N_init - N_init_val) / N_init_val)
                < DEFAULT_FLOAT_PRECISION
            )
        else:
            N_init_cond = sqla.func.abs(table.c.N_init - N_init_val) < DEFAULT_FLOAT_PRECISION

        if N_final_val != 0.0:
            N_final_cond = (
                sqla.func.abs((table.c.N_final - N_final_val) / N_final_val)
                < DEFAULT_FLOAT_PRECISION
            )
        else:
            N_final_cond = sqla.func.abs(table.c.N_final - N_final_val) < DEFAULT_FLOAT_PRECISION

        query = sqla.select(
            table.c.serial,
            table.c.N_total,
            table.c.msr_action,
            table.c.label,
        ).filter(
            table.c.validated == True,
            table.c.trajectory_serial == trajectory.store_id,
            N_init_cond,
            N_final_cond,
            table.c.delta_Nstar_serial == delta_Nstar_obj.store_id,
            table.c.atol_serial == atol.store_id,
            table.c.rtol_serial == rtol.store_id,
        )
        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            if label is None:
                label = (
                    f"SlowRollInstanton("
                    f"N_init={N_init_val:.4g}, "
                    f"N_final={N_final_val:.4g}, "
                    f"dNstar={float(delta_Nstar_obj):.4g})"
                )
            return SlowRollInstanton(
                store_id=None,
                trajectory=trajectory,
                N_init=N_init,
                N_final=N_final,
                delta_Nstar=delta_Nstar_obj,
                N_sample=N_sample,
                atol=atol,
                rtol=rtol,
                diffusion_model=diffusion_model,
                label=label,
            )

        obj = SlowRollInstanton(
            store_id=row_data.serial,
            trajectory=trajectory,
            N_init=N_init,
            N_final=N_final,
            delta_Nstar=delta_Nstar_obj,
            N_sample=N_sample,
            atol=atol,
            rtol=rtol,
            diffusion_model=diffusion_model,
            label=row_data.label,
        )
        obj._trajectory_serial = trajectory.store_id
        obj._delta_Nstar_serial = delta_Nstar_obj.store_id
        if row_data.N_total is not None:
            obj._N_total = row_data.N_total
        if row_data.msr_action is not None:
            obj._msr_action = row_data.msr_action

        if not do_not_populate:
            self._populate(obj, row_data, tables, conn)

        setattr(obj, "_deserialized", True)
        return obj

    def _populate(self, obj, row, tables, conn):
        """Load SlowRollInstantonValue records for a validated instanton."""
        from ComputeTargets.SlowRollInstanton import SlowRollInstantonValue
        from InflationConcepts.efold_value import efold_value

        value_table = tables.get("SlowRollInstantonValue")
        efold_table = tables.get("efold_value")
        if value_table is None or efold_table is None:
            return

        rows = conn.execute(
            sqla.select(
                value_table.c.N_serial,
                value_table.c.fields_json,
            ).filter(value_table.c.instanton_serial == obj.store_id)
        ).fetchall()

        for r in rows:
            efold_row = conn.execute(
                sqla.select(efold_table.c.serial, efold_table.c.N).filter(
                    efold_table.c.serial == r.N_serial
                )
            ).one()
            N_obj = efold_value(store_id=efold_row.serial, N=efold_row.N)
            data = json.loads(r.fields_json)
            obj._values.append(
                SlowRollInstantonValue(
                    store_id=None,
                    N=N_obj,
                    phi=data["phi"][0],
                    P1=data["P1"][0],
                )
            )

    def store(self, obj, conn, table, inserter, tables, inserters):
        if obj.failure:
            store_id = inserter(conn, {
                "trajectory_serial": obj._trajectory.store_id,
                "N_init": float(obj._N_init),
                "N_final": float(obj._N_final),
                "delta_Nstar_serial": obj._delta_Nstar.store_id,
                "atol_serial": obj._atol.store_id,
                "rtol_serial": obj._rtol.store_id,
                "n_fields": obj.n_fields,
                "N_total": None,
                "msr_action": None,
                "label": obj._label,
                "validated": False,
            })
            obj._my_id = store_id
            return obj

        store_id = inserter(conn, {
            "trajectory_serial": obj._trajectory.store_id,
            "N_init": float(obj._N_init),
            "N_final": float(obj._N_final),
            "delta_Nstar_serial": obj._delta_Nstar.store_id,
            "atol_serial": obj._atol.store_id,
            "rtol_serial": obj._rtol.store_id,
            "n_fields": obj.n_fields,
            "N_total": getattr(obj, "_N_total", None),
            "msr_action": obj._msr_action,
            "label": obj._label,
            "validated": False,
        })
        obj._my_id = store_id

        value_inserter = inserters["SlowRollInstantonValue"]

        for v in obj._values:
            value_inserter(conn, {
                "instanton_serial": store_id,
                "N_serial": v.N.store_id,
                "fields_json": json.dumps({
                    "phi": [v.phi],
                    "P1":  [v.P1],
                }),
            })

        return obj

    def validate(self, obj, conn, table, tables):
        if not obj.available:
            raise RuntimeError("Attempt to validate an object that has not been stored")

        if obj.failure:
            validated = True
        else:
            value_table = tables["SlowRollInstantonValue"]
            expected = len(obj._values)
            actual = conn.execute(
                sqla.select(sqla.func.count()).select_from(value_table).filter(
                    value_table.c.instanton_serial == obj.store_id
                )
            ).scalar()
            validated = (actual == expected)
            if not validated:
                print(f"!! WARNING: SlowRollInstanton {obj.store_id}: "
                      f"expected {expected} value rows, found {actual}")

        conn.execute(
            sqla.update(table)
            .where(table.c.serial == obj.store_id)
            .values(validated=validated)
        )
        return validated

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        query = sqla.select(table.c.serial).filter(table.c.validated == False)
        rows = conn.execute(query).fetchall()

        if prune_unvalidated and len(rows) > 0:
            serials = [r.serial for r in rows]
            conn.execute(sqla.delete(table).filter(table.c.serial.in_(serials)))
            return [f"Pruned {len(serials)} unvalidated SlowRollInstanton records"]
        elif len(rows) > 0:
            return [f"Found {len(rows)} unvalidated SlowRollInstanton records (not pruned)"]
        return []

    def read_table(self, conn, table, tables, units=None):
        from ComputeTargets.SlowRollInstanton import SlowRollInstanton
        from InflationConcepts.delta_Nstar import delta_Nstar as DeltaNstar

        delta_Nstar_table = tables.get("delta_Nstar")

        query = sqla.select(
            table.c.serial,
            table.c.trajectory_serial,
            table.c.N_total,
            table.c.msr_action,
            table.c.delta_Nstar_serial,
            table.c.label,
        ).filter(table.c.msr_action.isnot(None))

        rows = conn.execute(query).fetchall()
        results = []

        for row in rows:
            obj = SlowRollInstanton(
                store_id=row.serial,
                trajectory=None,
                N_init=None,
                N_final=None,
                delta_Nstar=None,
                N_sample=None,
                atol=None,
                rtol=None,
                label=row.label,
            )
            obj._trajectory_serial = row.trajectory_serial
            obj._delta_Nstar_serial = row.delta_Nstar_serial

            if row.N_total is not None:
                obj._N_total = row.N_total
            if row.msr_action is not None:
                obj._msr_action = row.msr_action

            if delta_Nstar_table is not None:
                dns_row = conn.execute(
                    sqla.select(
                        delta_Nstar_table.c.serial,
                        delta_Nstar_table.c.value,
                    ).filter(delta_Nstar_table.c.serial == row.delta_Nstar_serial)
                ).one_or_none()
                if dns_row is not None:
                    obj._delta_Nstar = DeltaNstar(store_id=dns_row.serial, value=dns_row.value)

            self._populate(obj, row, tables, conn)
            results.append(obj)

        return results

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.serial,
            table.c.timestamp,
            table.c.N_init,
            table.c.N_final,
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
            label = (
                f"SlowRollInstanton("
                f"N_init={row.N_init:.4g}, "
                f"N_final={row.N_final:.4g}, "
                f"delta_Nstar_serial={row.delta_Nstar_serial})"
            )
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


class sqla_SlowRollInstantonValue_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "serial": False,
            "version": False,
            "timestamp": False,
            "columns": [
                sqla.Column(
                    "instanton_serial",
                    sqla.Integer,
                    sqla.ForeignKey("SlowRollInstanton.serial"),
                    index=True,
                    nullable=False,
                    primary_key=True,
                ),
                sqla.Column(
                    "N_serial",
                    sqla.Integer,
                    sqla.ForeignKey("efold_value.serial"),
                    index=True,
                    nullable=False,
                    primary_key=True,
                ),
                sqla.Column("fields_json", sqla.Text, nullable=False),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_SlowRollInstantonValue_factory.build() is not used directly; "
            "values are inserted by sqla_SlowRollInstantonFactory.store()."
        )

    def store(self, obj, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_SlowRollInstantonValue_factory.store() is not yet implemented. "
            "It will be implemented together with SlowRollInstanton.compute() in Prompt 6."
        )

    def validate(self, obj, conn, table, tables):
        raise NotImplementedError(
            "sqla_SlowRollInstantonValue_factory.validate() is not yet implemented."
        )

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        return []
