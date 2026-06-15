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
from InflationConcepts.efold_value import efold_value


class sqla_InflatonTrajectory_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": True,
            "timestamp": True,
            "validate_on_startup": True,
            "columns": [
                sqla.Column(
                    "phi0_serial",
                    sqla.Integer,
                    sqla.ForeignKey("phi_value.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "pi0_serial",
                    sqla.Integer,
                    sqla.ForeignKey("pi_value.serial"),
                    index=True,
                    nullable=False,
                ),
                # TODO (future): add FK to potential registry table; for now a plain
                # integer is used because AbstractPotential subclasses share no
                # single concrete table.
                sqla.Column(
                    "potential_serial",
                    sqla.Integer,
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "atol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_inflaton_traj_atol"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "rtol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_inflaton_traj_rtol"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column("n_fields", sqla.Integer, nullable=False, default=1),
                sqla.Column("N_end", sqla.Float(64), nullable=True),
                sqla.Column("trajectory_json", sqla.Text, nullable=True),
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
        from ComputeTargets.InflatonTrajectory import InflatonTrajectory

        phi0 = payload["phi0"]
        pi0 = payload["pi0"]
        potential = payload["potential"]
        atol = payload["atol"]
        rtol = payload["rtol"]
        N_sample = payload.get("N_sample", None)
        tags = payload.get("tags", [])
        do_not_populate = payload.get("_do_not_populate", False)

        query = sqla.select(
            table.c.serial,
            table.c.N_end,
            table.c.validated,
            table.c.trajectory_json,
        ).filter(
            table.c.phi0_serial == phi0.store_id,
            table.c.pi0_serial == pi0.store_id,
            table.c.potential_serial == potential.store_id,
            table.c.atol_serial == atol.store_id,
            table.c.rtol_serial == rtol.store_id,
        )
        row_data = conn.execute(query).one_or_none()

        # Bypass the Ray actor wrapper so we can create a plain local instance.
        LocalClass = InflatonTrajectory.__ray_actor_class__

        if row_data is None:
            insert_data = {
                "phi0_serial": phi0.store_id,
                "pi0_serial": pi0.store_id,
                "potential_serial": potential.store_id,
                "atol_serial": atol.store_id,
                "rtol_serial": rtol.store_id,
                "n_fields": 1,
                "N_end": None,
                "trajectory_json": None,
                "validated": False,
            }
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            attribute_set = {"_new_insert": True}

            obj = LocalClass(
                store_id=store_id,
                phi0=phi0,
                pi0=pi0,
                potential=potential,
                N_sample=N_sample,
                atol=atol,
                rtol=rtol,
            )
        else:
            store_id = row_data.serial
            attribute_set = {"_deserialized": True}

            obj = LocalClass(
                store_id=store_id,
                phi0=phi0,
                pi0=pi0,
                potential=potential,
                N_sample=N_sample,
                atol=atol,
                rtol=rtol,
            )
            obj._N_end = row_data.N_end

            if row_data.validated and not do_not_populate:
                self._populate(obj, row_data, tables, conn)

        for key, value in attribute_set.items():
            setattr(obj, key, value)

        return obj

    def _populate(self, obj, row, tables, conn):
        """Deserialise trajectory_json into obj._values."""
        if row.trajectory_json is None:
            return

        from ComputeTargets.InflatonTrajectory import InflatonTrajectoryValue

        efold_table = tables["efold_value"]
        data = json.loads(row.trajectory_json)

        for item in data:
            N_serial = item["N_serial"]
            phi = item["phi"]
            pi_val = item["pi"]

            efold_row = conn.execute(
                sqla.select(efold_table.c.serial, efold_table.c.N).filter(
                    efold_table.c.serial == N_serial
                )
            ).one()

            N_obj = efold_value(store_id=efold_row.serial, N=efold_row.N)
            obj._values.append(
                InflatonTrajectoryValue(store_id=None, N=N_obj, phi=phi, pi=pi_val)
            )

    def store(self, obj, conn, table, inserter, tables, inserters):
        """Update the database record after compute() has populated the trajectory."""
        trajectory_json = json.dumps([
            {"N_serial": v.N.store_id, "phi": v.phi, "pi": v.pi}
            for v in obj.values
        ])

        conn.execute(
            sqla.update(table)
            .where(table.c.serial == obj.store_id)
            .values(
                N_end=obj.N_end,
                trajectory_json=trajectory_json,
                validated=True,
            )
        )
        return obj

    def validate(self, obj, conn, table, tables):
        """Check that the record exists and has validated=True."""
        row = conn.execute(
            sqla.select(table.c.serial, table.c.validated).filter(
                table.c.serial == obj.store_id
            )
        ).one_or_none()

        if row is None:
            return False
        return bool(row.validated)

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        query = sqla.select(table.c.serial).filter(table.c.validated == False)
        rows = conn.execute(query).fetchall()

        if prune_unvalidated and len(rows) > 0:
            serials = [r.serial for r in rows]
            conn.execute(sqla.delete(table).filter(table.c.serial.in_(serials)))
            return [f"Pruned {len(serials)} unvalidated InflatonTrajectory records"]
        elif len(rows) > 0:
            return [f"Found {len(rows)} unvalidated InflatonTrajectory records (not pruned)"]
        return []

    def read_table(self, conn, table, tables, potential_proxy=None):
        # TODO (future): filter by potential when potential_proxy is not None
        from ComputeTargets.InflatonTrajectory import InflatonTrajectory, InflatonTrajectoryValue
        from CosmologyConcepts.FieldValues import phi_value, pi_value
        from MetadataConcepts.tolerance import tolerance

        LocalClass = InflatonTrajectory.__ray_actor_class__
        phi_table = tables["phi_value"]
        pi_table = tables["pi_value"]
        atol_table = tables["tolerance"]

        query = sqla.select(
            table.c.serial,
            table.c.phi0_serial,
            table.c.pi0_serial,
            table.c.potential_serial,
            table.c.atol_serial,
            table.c.rtol_serial,
            table.c.N_end,
            table.c.trajectory_json,
            table.c.validated,
        ).filter(table.c.validated == True)

        rows = conn.execute(query).fetchall()
        results = []

        for row in rows:
            phi_row = conn.execute(
                sqla.select(phi_table.c.serial, phi_table.c["value_PlanckMass"]).filter(
                    phi_table.c.serial == row.phi0_serial
                )
            ).one()
            phi0_obj = phi_value(store_id=phi_row.serial, value=phi_row.value_PlanckMass)

            pi_row = conn.execute(
                sqla.select(pi_table.c.serial, pi_table.c["value_PlanckMass"]).filter(
                    pi_table.c.serial == row.pi0_serial
                )
            ).one()
            pi0_obj = pi_value(store_id=pi_row.serial, value=pi_row.value_PlanckMass)

            obj = LocalClass(
                store_id=row.serial,
                phi0=phi0_obj,
                pi0=pi0_obj,
                potential=None,  # TODO (future): look up from potential registry
                N_sample=None,
                atol=None,
                rtol=None,
            )
            obj._N_end = row.N_end

            if row.trajectory_json:
                self._populate(obj, row, tables, conn)

            results.append(obj)

        return results

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.serial,
            table.c.timestamp,
            table.c.phi0_serial,
            table.c.validated,
            table.c.N_end,
        )
        rows = conn.execute(query).fetchall()

        earliest_validated = None
        latest_validated = None
        earliest_unvalidated = None
        latest_unvalidated = None
        validated_labels = []
        unvalidated_labels = []

        for row in rows:
            label = f"InflatonTrajectory(phi0_serial={row.phi0_serial}, N_end={row.N_end})"
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
