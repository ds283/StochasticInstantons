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


class sqla_FullInstantonFactory(SQLAFactoryBase):
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
                    "N_init_serial",
                    sqla.Integer,
                    sqla.ForeignKey("N_init.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "N_final_serial",
                    sqla.Integer,
                    sqla.ForeignKey("N_final.serial"),
                    index=True,
                    nullable=False,
                ),
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
                    sqla.ForeignKey("tolerance.serial", name="fk_full_instanton_atol"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "rtol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_full_instanton_rtol"),
                    index=True,
                    nullable=False,
                ),
                # No FK constraint: target table is determined by diffusion_type,
                # following the potential_serial / potential_type pattern.
                sqla.Column("diffusion_serial", sqla.Integer, index=True, nullable=False),
                sqla.Column("diffusion_type",   sqla.Integer, index=True, nullable=False),
                sqla.Column("n_fields", sqla.Integer, nullable=False, default=1),
                sqla.Column("N_total", sqla.Float(64), nullable=True),
                sqla.Column("msr_action", sqla.Float(64), nullable=True),
                sqla.Column("noise_phi1_min",  sqla.Float(64), nullable=True),
                sqla.Column("noise_phi1_mean", sqla.Float(64), nullable=True),
                sqla.Column("noise_phi1_max",  sqla.Float(64), nullable=True),
                sqla.Column("noise_phi2_min",  sqla.Float(64), nullable=True),
                sqla.Column("noise_phi2_mean", sqla.Float(64), nullable=True),
                sqla.Column("noise_phi2_max",  sqla.Float(64), nullable=True),
                sqla.Column("label", sqla.Text, nullable=True),
                sqla.Column("diagnostics_json", sqla.Text, nullable=True),
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
        from ComputeTargets.FullInstanton import FullInstanton

        trajectory = payload["trajectory"]  # InflatonTrajectoryProxy
        N_init_obj = payload["N_init"]  # N_init
        N_final_obj = payload["N_final"]  # N_final
        delta_Nstar_obj = payload["delta_Nstar"]  # delta_Nstar
        atol = payload["atol"]
        rtol = payload["rtol"]
        N_sample = payload.get("N_sample", None)
        diffusion_model = payload.get("diffusion_model")
        if diffusion_model is None or not diffusion_model.available:
            raise ValueError(
                "sqla_FullInstantonFactory.build(): 'diffusion_model' must be a "
                "persisted AbstractDiffusionModel with a valid store_id.  "
                "Call datastore.object_get('MasslessDecoupledDiffusion') first."
            )
        tags = payload.get("tags", [])
        do_not_populate = payload.get("_do_not_populate", False)
        label = payload.get("label", None)

        query = sqla.select(
            table.c.serial,
            table.c.timestamp,
            table.c.N_total,
            table.c.msr_action,
            table.c.noise_phi1_min,
            table.c.noise_phi1_mean,
            table.c.noise_phi1_max,
            table.c.noise_phi2_min,
            table.c.noise_phi2_mean,
            table.c.noise_phi2_max,
            table.c.label,
            table.c.diagnostics_json,
        ).filter(
            table.c.validated == True,
            table.c.trajectory_serial == trajectory.store_id,
            table.c.N_init_serial == N_init_obj.store_id,
            table.c.N_final_serial == N_final_obj.store_id,
            table.c.delta_Nstar_serial == delta_Nstar_obj.store_id,
            table.c.atol_serial == atol.store_id,
            table.c.rtol_serial == rtol.store_id,
            table.c.diffusion_serial == diffusion_model.store_id,
            table.c.diffusion_type   == diffusion_model.type_id,
        )
        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            if label is None:
                label = (
                    f"FullInstanton("
                    f"N_init={float(N_init_obj):.4g}, "
                    f"N_final={float(N_final_obj):.4g}, "
                    f"dNstar={float(delta_Nstar_obj):.4g})"
                )
            return FullInstanton(
                store_id=None,
                trajectory=trajectory,
                N_init=N_init_obj,
                N_final=N_final_obj,
                delta_Nstar=delta_Nstar_obj,
                N_sample=N_sample,
                atol=atol,
                rtol=rtol,
                diffusion_model=diffusion_model,
                label=label,
            )

        obj = FullInstanton(
            store_id=row_data.serial,
            trajectory=trajectory,
            N_init=N_init_obj,
            N_final=N_final_obj,
            delta_Nstar=delta_Nstar_obj,
            N_sample=N_sample,
            atol=atol,
            rtol=rtol,
            diffusion_model=diffusion_model,
            label=row_data.label,
            timestamp=row_data.timestamp,
        )
        obj._trajectory_serial = trajectory.store_id
        obj._delta_Nstar_serial = delta_Nstar_obj.store_id
        if row_data.N_total is not None:
            obj._N_total = row_data.N_total
        if row_data.msr_action is not None:
            obj._msr_action = row_data.msr_action
        obj._noise_phi1_min  = row_data.noise_phi1_min
        obj._noise_phi1_mean = row_data.noise_phi1_mean
        obj._noise_phi1_max  = row_data.noise_phi1_max
        obj._noise_phi2_min  = row_data.noise_phi2_min
        obj._noise_phi2_mean = row_data.noise_phi2_mean
        obj._noise_phi2_max  = row_data.noise_phi2_max
        obj._diagnostics = (
            json.loads(row_data.diagnostics_json) if row_data.diagnostics_json else None
        )

        if not do_not_populate:
            if obj._diagnostics is not None and obj._diagnostics.get("full_values_stored", True) is False:
                raise RuntimeError(
                    f"FullInstanton(id={obj.store_id}) was stored in scalars-only mode; "
                    f"full per-sample values were never persisted. Re-run with "
                    f"_do_not_populate=True, or recompute this instanton in full-fidelity mode."
                )
            self._populate(obj, row_data, tables, conn, units=payload["trajectory"].units)

        setattr(obj, "_deserialized", True)
        return obj

    def _populate(self, obj, row, tables, conn, units=None):
        """Load FullInstantonValue records for a validated instanton."""
        from ComputeTargets.FullInstanton import FullInstantonValue
        from InflationConcepts.efold_value import efold_value

        value_table = tables.get("FullInstantonValue")
        efold_table = tables.get("efold_value")
        if value_table is None or efold_table is None:
            return

        rows = conn.execute(
            sqla.select(
                value_table.c.N_serial,
                value_table.c.fields_json,
                efold_table.c.N,
            )
            .select_from(value_table.join(efold_table, value_table.c.N_serial == efold_table.c.serial))
            .filter(value_table.c.instanton_serial == obj.store_id)
            .order_by(efold_table.c.N)
        ).fetchall()

        for r in rows:
            N_obj = efold_value(store_id=r.N_serial, N=r.N)
            data = json.loads(r.fields_json)
            obj._values.append(
                FullInstantonValue(
                    store_id=None,
                    N=N_obj,
                    phi1=data["phi1_PlanckMass"][0] * units.PlanckMass,
                    phi2=data["phi2_PlanckMass"][0] * units.PlanckMass,
                    P1=  data["P1_invPlanckMass"][0] / units.PlanckMass,
                    P2=  data["P2_invPlanckMass"][0] / units.PlanckMass,
                )
            )

        N_vals = [v.N.N for v in obj._values]
        if any(N_vals[i] > N_vals[i + 1] for i in range(len(N_vals) - 1)):
            raise RuntimeError(
                f"FullInstanton(id={obj.store_id}): N-values are not non-decreasing after "
                f"ORDER BY — database may be corrupt"
            )

    def store(self, obj, conn, table, inserter, tables, inserters):
        store_full_values = getattr(obj, "_store_full_values", True)

        # In scalars-only mode (success path only), merge full_values_stored=False into
        # the stored diagnostics JSON so that build() can detect this state and raise
        # rather than silently returning empty _values.  Absent key is treated as True,
        # so full-fidelity rows need no explicit marker — backwards-compatible by design.
        if not obj.failure and not store_full_values:
            diag = dict(obj.diagnostics) if obj.diagnostics is not None else {}
            diag["full_values_stored"] = False
            diagnostics_json = json.dumps(diag)
        else:
            diagnostics_json = json.dumps(obj.diagnostics) if obj.diagnostics is not None else None

        if obj.failure:
            store_id = inserter(conn, {
                "trajectory_serial": obj._trajectory.store_id,
                "N_init_serial": obj._N_init.store_id,
                "N_final_serial": obj._N_final.store_id,
                "delta_Nstar_serial": obj._delta_Nstar.store_id,
                "atol_serial": obj._atol.store_id,
                "rtol_serial": obj._rtol.store_id,
                "diffusion_serial": obj._diffusion_model.store_id,
                "diffusion_type":   obj._diffusion_model.type_id,
                "n_fields": obj.n_fields,
                "N_total": None,
                "msr_action": None,
                "noise_phi1_min": None,
                "noise_phi1_mean": None,
                "noise_phi1_max": None,
                "noise_phi2_min": None,
                "noise_phi2_mean": None,
                "noise_phi2_max": None,
                "label": obj._label,
                "diagnostics_json": diagnostics_json,
                "validated": False,
            })
            obj._my_id = store_id
            return obj

        store_id = inserter(conn, {
            "trajectory_serial": obj._trajectory.store_id,
            "N_init_serial": obj._N_init.store_id,
            "N_final_serial": obj._N_final.store_id,
            "delta_Nstar_serial": obj._delta_Nstar.store_id,
            "atol_serial": obj._atol.store_id,
            "rtol_serial": obj._rtol.store_id,
            "diffusion_serial": obj._diffusion_model.store_id,
            "diffusion_type":   obj._diffusion_model.type_id,
            "n_fields": obj.n_fields,
            "N_total": getattr(obj, "_N_total", None),
            "msr_action": obj._msr_action,
            "noise_phi1_min":  obj.noise_phi1_min,
            "noise_phi1_mean": obj.noise_phi1_mean,
            "noise_phi1_max":  obj.noise_phi1_max,
            "noise_phi2_min":  obj.noise_phi2_min,
            "noise_phi2_mean": obj.noise_phi2_mean,
            "noise_phi2_max":  obj.noise_phi2_max,
            "label": obj._label,
            "diagnostics_json": diagnostics_json,
            "validated": False,
        })
        obj._my_id = store_id

        if store_full_values:
            units = obj._trajectory.units
            value_inserter = inserters["FullInstantonValue"]

            for v in obj._values:
                value_inserter(conn, {
                    "instanton_serial": store_id,
                    "N_serial": v.N.store_id,
                    "fields_json": json.dumps({
                        "phi1_PlanckMass":  [v.phi1 / units.PlanckMass],
                        "phi2_PlanckMass":  [v.phi2 / units.PlanckMass],
                        "P1_invPlanckMass": [v.P1 * units.PlanckMass],
                        "P2_invPlanckMass": [v.P2 * units.PlanckMass],
                    }),
                })

        return obj

    def validate(self, obj, conn, table, tables):
        if not obj.available:
            raise RuntimeError("Attempt to validate an object that has not been stored")

        if obj.failure:
            validated = True
        else:
            value_table = tables["FullInstantonValue"]
            store_full_values = getattr(obj, "_store_full_values", True)
            expected = 0 if not store_full_values else len(obj._values)
            actual = conn.execute(
                sqla.select(sqla.func.count()).select_from(value_table).filter(
                    value_table.c.instanton_serial == obj.store_id
                )
            ).scalar()
            validated = (actual == expected)
            if not validated:
                print(f"!! WARNING: FullInstanton {obj.store_id}: "
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
            # Delete child value rows first; there is no ON DELETE CASCADE on the FK.
            value_table = tables.get("FullInstantonValue")
            if value_table is not None:
                conn.execute(
                    sqla.delete(value_table).where(
                        value_table.c.instanton_serial.in_(serials)
                    )
                )
            conn.execute(sqla.delete(table).filter(table.c.serial.in_(serials)))
            return [f"Pruned {len(serials)} unvalidated FullInstanton records"]
        elif len(rows) > 0:
            return [f"Found {len(rows)} unvalidated FullInstanton records (not pruned)"]
        return []

    def read_table(self, conn, table, tables, units=None):
        from ComputeTargets.FullInstanton import FullInstanton
        from InflationConcepts.delta_Nstar import delta_Nstar as DeltaNstar
        from InflationConcepts.DiffusionModel.registry import DIFFUSION_MODEL_REGISTRY
        from InflationConcepts.N_init import N_init as NInit
        from InflationConcepts.N_final import N_final as NFinal

        delta_Nstar_table = tables.get("delta_Nstar")
        N_init_table = tables.get("N_init")
        N_final_table = tables.get("N_final")

        query = sqla.select(
            table.c.serial,
            table.c.trajectory_serial,
            table.c.N_total,
            table.c.msr_action,
            table.c.noise_phi1_min,
            table.c.noise_phi1_mean,
            table.c.noise_phi1_max,
            table.c.noise_phi2_min,
            table.c.noise_phi2_mean,
            table.c.noise_phi2_max,
            table.c.N_init_serial,
            table.c.N_final_serial,
            table.c.delta_Nstar_serial,
            table.c.diffusion_serial,
            table.c.diffusion_type,
            table.c.label,
            table.c.diagnostics_json,
        ).filter(table.c.msr_action.isnot(None))

        rows = conn.execute(query).fetchall()
        results = []

        for row in rows:
            dm_info = DIFFUSION_MODEL_REGISTRY.get(row.diffusion_type)
            diffusion_model = (
                dm_info.factory.load_by_serial(conn, tables, row.diffusion_serial)
                if dm_info is not None else None
            )

            obj = FullInstanton(
                store_id=row.serial,
                trajectory=None,
                N_init=None,
                N_final=None,
                delta_Nstar=None,
                N_sample=None,
                atol=None,
                rtol=None,
                diffusion_model=diffusion_model,
                label=row.label,
            )
            obj._trajectory_serial = row.trajectory_serial
            obj._delta_Nstar_serial = row.delta_Nstar_serial

            if row.N_total is not None:
                obj._N_total = row.N_total
            if row.msr_action is not None:
                obj._msr_action = row.msr_action
            obj._noise_phi1_min  = row.noise_phi1_min
            obj._noise_phi1_mean = row.noise_phi1_mean
            obj._noise_phi1_max  = row.noise_phi1_max
            obj._noise_phi2_min  = row.noise_phi2_min
            obj._noise_phi2_mean = row.noise_phi2_mean
            obj._noise_phi2_max  = row.noise_phi2_max
            obj._diagnostics = (
                json.loads(row.diagnostics_json) if row.diagnostics_json else None
            )

            if delta_Nstar_table is not None:
                dns_row = conn.execute(
                    sqla.select(
                        delta_Nstar_table.c.serial,
                        delta_Nstar_table.c.value,
                    ).filter(delta_Nstar_table.c.serial == row.delta_Nstar_serial)
                ).one_or_none()
                if dns_row is not None:
                    obj._delta_Nstar = DeltaNstar(store_id=dns_row.serial, value=dns_row.value)

            if N_init_table is not None:
                N_init_row = conn.execute(
                    sqla.select(
                        N_init_table.c.serial,
                        N_init_table.c.value,
                    ).filter(N_init_table.c.serial == row.N_init_serial)
                ).one_or_none()
                if N_init_row is not None:
                    obj._N_init = NInit(store_id=N_init_row.serial, value=N_init_row.value)

            if N_final_table is not None:
                N_final_row = conn.execute(
                    sqla.select(
                        N_final_table.c.serial,
                        N_final_table.c.value,
                    ).filter(N_final_table.c.serial == row.N_final_serial)
                ).one_or_none()
                if N_final_row is not None:
                    obj._N_final = NFinal(store_id=N_final_row.serial, value=N_final_row.value)

            self._populate(obj, row, tables, conn, units=units)
            results.append(obj)

        return results

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.serial,
            table.c.timestamp,
            table.c.N_init_serial,
            table.c.N_final_serial,
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
                f"FullInstanton("
                f"N_init_serial={row.N_init_serial}, "
                f"N_final_serial={row.N_final_serial}, "
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


class sqla_FullInstantonValue_factory(SQLAFactoryBase):
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
                    sqla.ForeignKey("FullInstanton.serial"),
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
            "sqla_FullInstantonValue_factory.build() is not used directly; "
            "values are inserted by sqla_FullInstantonFactory.store()."
        )

    def store(self, obj, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_FullInstantonValue_factory.store() is not yet implemented. "
            "It will be implemented together with FullInstanton.compute() in Prompt 6."
        )

    def validate(self, obj, conn, table, tables):
        raise NotImplementedError(
            "sqla_FullInstantonValue_factory.validate() is not yet implemented."
        )

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        return []
