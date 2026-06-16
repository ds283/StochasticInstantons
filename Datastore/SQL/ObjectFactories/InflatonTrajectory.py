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
        from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion

        phi0 = payload["phi0"]
        pi0 = payload["pi0"]
        potential = payload["potential"]
        atol = payload["atol"]
        rtol = payload["rtol"]
        samples_per_N = payload.get("samples_per_N", None)
        diffusion_model = payload.get("diffusion_model", MasslessDecoupledDiffusion())
        do_not_populate = payload.get("_do_not_populate", False)

        query = sqla.select(
            table.c.serial,
            table.c.N_end,
        ).filter(
            table.c.validated == True,
            table.c.phi0_serial == phi0.store_id,
            table.c.pi0_serial == pi0.store_id,
            table.c.potential_serial == potential.store_id,
            table.c.atol_serial == atol.store_id,
            table.c.rtol_serial == rtol.store_id,
        )
        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            return InflatonTrajectory(
                store_id=None,
                phi0=phi0,
                pi0=pi0,
                potential=potential,
                samples_per_N=samples_per_N,
                atol=atol,
                rtol=rtol,
                diffusion_model=diffusion_model,
            )

        obj = InflatonTrajectory(
            store_id=row_data.serial,
            phi0=phi0,
            pi0=pi0,
            potential=potential,
            samples_per_N=samples_per_N,
            atol=atol,
            rtol=rtol,
            diffusion_model=diffusion_model,
        )
        obj._N_end = row_data.N_end

        if not do_not_populate:
            self._populate(obj, row_data, tables, conn)

        setattr(obj, "_deserialized", True)
        return obj

    def _populate(self, obj, row, tables, conn):
        """Load InflatonTrajectoryValue records for a validated trajectory."""
        from ComputeTargets.InflatonTrajectory import InflatonTrajectoryValue

        value_table = tables["InflatonTrajectoryValue"]
        efold_table = tables["efold_value"]

        rows = conn.execute(
            sqla.select(value_table.c.N_serial, value_table.c.fields_json)
            .filter(value_table.c.trajectory_serial == obj.store_id)
            .order_by(value_table.c.N_serial)
        ).fetchall()

        for r in rows:
            efold_row = conn.execute(
                sqla.select(efold_table.c.serial, efold_table.c.N).filter(
                    efold_table.c.serial == r.N_serial
                )
            ).one()
            data = json.loads(r.fields_json)
            N_obj = efold_value(store_id=efold_row.serial, N=efold_row.N)
            obj._values.append(
                InflatonTrajectoryValue(
                    store_id=None,
                    N=N_obj,
                    phi=data["phi"][0],
                    pi=data["pi"][0],
                )
            )

    def store(self, obj, conn, table, inserter, tables, inserters):
        if obj.failure:
            store_id = inserter(conn, {
                "phi0_serial": obj._phi0.store_id,
                "pi0_serial": obj._pi0.store_id,
                "potential_serial": obj._potential.store_id,
                "atol_serial": obj._atol.store_id,
                "rtol_serial": obj._rtol.store_id,
                "n_fields": obj.n_fields,
                "N_end": None,
                "validated": False,
            })
            obj._my_id = store_id
            return obj

        # _values has been fully populated by the store_handler (efold_value objects
        # already minted and assigned store_ids) before the factory is called.
        store_id = inserter(conn, {
            "phi0_serial": obj._phi0.store_id,
            "pi0_serial": obj._pi0.store_id,
            "potential_serial": obj._potential.store_id,
            "atol_serial": obj._atol.store_id,
            "rtol_serial": obj._rtol.store_id,
            "n_fields": obj.n_fields,
            "N_end": obj._N_end,
            "validated": False,
        })
        obj._my_id = store_id

        value_inserter = inserters["InflatonTrajectoryValue"]
        for v in obj._values:
            value_inserter(conn, {
                "trajectory_serial": store_id,
                "N_serial": v.N.store_id,
                "fields_json": json.dumps({"phi": [v.phi], "pi": [v.pi]}),
            })

        return obj

    def validate(self, obj, conn, table, tables):
        if not obj.available:
            raise RuntimeError("Attempt to validate an object that has not been stored")

        if obj.failure:
            validated = True
        else:
            value_table = tables["InflatonTrajectoryValue"]
            expected = len(obj._values)
            actual = conn.execute(
                sqla.select(sqla.func.count()).select_from(value_table).filter(
                    value_table.c.trajectory_serial == obj.store_id
                )
            ).scalar()
            validated = (actual == expected) and actual > 0
            if not validated:
                print(f"!! WARNING: InflatonTrajectory {obj.store_id}: "
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
            return [f"Pruned {len(serials)} unvalidated InflatonTrajectory records"]
        elif len(rows) > 0:
            return [f"Found {len(rows)} unvalidated InflatonTrajectory records (not pruned)"]
        return []

    def read_table(self, conn, table, tables, potential_proxy=None, units=None):
        from ComputeTargets.InflatonTrajectory import InflatonTrajectory
        from CosmologyConcepts.FieldValues import phi_value, pi_value

        phi_table = tables["phi_value"]
        pi_table = tables["pi_value"]

        query = sqla.select(
            table.c.serial,
            table.c.phi0_serial,
            table.c.pi0_serial,
            table.c.potential_serial,
            table.c.N_end,
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

            # Look up the potential — try QuadraticPotential first, then QuarticPotential
            potential = None
            if "QuadraticPotential" in tables and "inflaton_mass" in tables:
                quad_table = tables["QuadraticPotential"]
                mass_table = tables["inflaton_mass"]
                quad_row = conn.execute(
                    sqla.select(quad_table.c.serial, quad_table.c.mass_id).filter(
                        quad_table.c.serial == row.potential_serial
                    )
                ).one_or_none()
                if quad_row is not None:
                    mass_row = conn.execute(
                        sqla.select(
                            mass_table.c.serial,
                            mass_table.c["value_PlanckMass"],
                        ).filter(mass_table.c.serial == quad_row.mass_id)
                    ).one_or_none()
                    if mass_row is not None:
                        from InflationConcepts.inflaton_mass import inflaton_mass
                        from InflationConcepts.QuadraticPotential import QuadraticPotential
                        m = inflaton_mass(store_id=mass_row.serial, value=mass_row.value_PlanckMass)
                        potential = QuadraticPotential(store_id=quad_row.serial, m=m, units=units)

            if potential is None and "QuarticPotential" in tables and "quartic_coupling" in tables:
                quart_table = tables["QuarticPotential"]
                coupling_table = tables["quartic_coupling"]
                quart_row = conn.execute(
                    sqla.select(quart_table.c.serial, quart_table.c.coupling_id).filter(
                        quart_table.c.serial == row.potential_serial
                    )
                ).one_or_none()
                if quart_row is not None:
                    coupling_row = conn.execute(
                        sqla.select(coupling_table.c.serial, coupling_table.c.value).filter(
                            coupling_table.c.serial == quart_row.coupling_id
                        )
                    ).one_or_none()
                    if coupling_row is not None:
                        from InflationConcepts.quartic_coupling import quartic_coupling
                        from InflationConcepts.QuarticPotential import QuarticPotential
                        lam = quartic_coupling(store_id=coupling_row.serial, value=coupling_row.value)
                        potential = QuarticPotential(store_id=quart_row.serial, lambda_=lam, units=units)

            obj = InflatonTrajectory(
                store_id=row.serial,
                phi0=phi0_obj,
                pi0=pi0_obj,
                potential=potential,
                samples_per_N=None,
                atol=None,
                rtol=None,
            )
            obj._N_end = row.N_end

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


class sqla_InflatonTrajectoryValue_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "serial": False,
            "version": False,
            "timestamp": False,
            "columns": [
                sqla.Column(
                    "trajectory_serial",
                    sqla.Integer,
                    sqla.ForeignKey("InflatonTrajectory.serial"),
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
            "sqla_InflatonTrajectoryValue_factory.build() is not used directly; "
            "values are inserted by sqla_InflatonTrajectory_factory.store()."
        )

    def store(self, obj, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_InflatonTrajectoryValue_factory.store() is not used directly; "
            "values are inserted by sqla_InflatonTrajectory_factory.store()."
        )

    def validate(self, obj, conn, table, tables):
        raise NotImplementedError(
            "sqla_InflatonTrajectoryValue_factory.validate() is not used directly."
        )

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        return []
