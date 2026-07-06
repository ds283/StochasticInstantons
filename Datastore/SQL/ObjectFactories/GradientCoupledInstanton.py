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


class sqla_GradientCoupledInstantonFactory(SQLAFactoryBase):
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
                    "n_collocation_points_serial",
                    sqla.Integer,
                    sqla.ForeignKey("n_collocation_points.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "alpha_regularization_serial",
                    sqla.Integer,
                    sqla.ForeignKey("alpha_regularization.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "atol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_gradient_coupled_instanton_atol"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column(
                    "rtol_serial",
                    sqla.Integer,
                    sqla.ForeignKey("tolerance.serial", name="fk_gradient_coupled_instanton_rtol"),
                    index=True,
                    nullable=False,
                ),
                # No FK constraint: target table is determined by diffusion_type,
                # following the potential_serial / potential_type pattern.
                sqla.Column("diffusion_serial", sqla.Integer, index=True, nullable=False),
                sqla.Column("diffusion_type",   sqla.Integer, index=True, nullable=False),
                sqla.Column(
                    "cosmo_serial",
                    sqla.Integer,
                    sqla.ForeignKey("CosmologicalParams.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column("n_fields", sqla.Integer, nullable=False, default=1),
                sqla.Column("N_total", sqla.Float(64), nullable=True),
                # Deliberately unpopulated -- see GradientCoupledInstanton.py's module
                # docstring for the scope boundary (S_MSR deferred to a follow-up prompt).
                sqla.Column("msr_action", sqla.Float(64), nullable=True),
                # Dimensionless noise amplitude in units of Hawking standard
                # deviations, evaluated at the core node (y=+1) -- same
                # construction and no-suffix convention as FullInstanton's own
                # noise_phi1_*/noise_phi2_* columns (ComputeTargets/FullInstanton.py
                # lines ~303-326); no unit conversion needed at this factory
                # boundary since the quantity is dimensionless by construction.
                sqla.Column("noise_field_min",  sqla.Float(64), nullable=True),
                sqla.Column("noise_field_mean", sqla.Float(64), nullable=True),
                sqla.Column("noise_field_max",  sqla.Float(64), nullable=True),
                sqla.Column("noise_mom_min",  sqla.Float(64), nullable=True),
                sqla.Column("noise_mom_mean", sqla.Float(64), nullable=True),
                sqla.Column("noise_mom_max",  sqla.Float(64), nullable=True),
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
        from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
            GradientCoupledInstanton,
        )

        trajectory = payload["trajectory"]  # InflatonTrajectoryProxy
        N_init_obj = payload["N_init"]  # N_init
        N_final_obj = payload["N_final"]  # N_final
        delta_Nstar_obj = payload["delta_Nstar"]  # delta_Nstar
        n_collocation_points_obj = payload["n_collocation_points"]
        alpha_regularization_obj = payload["alpha_regularization"]
        atol = payload["atol"]
        rtol = payload["rtol"]
        cosmo = payload["cosmo"]
        N_sample = payload.get("N_sample", None)
        diffusion_model = payload.get("diffusion_model")
        if diffusion_model is None or not diffusion_model.available:
            raise ValueError(
                "sqla_GradientCoupledInstantonFactory.build(): 'diffusion_model' must "
                "be a persisted AbstractDiffusionModel with a valid store_id.  "
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
            table.c.noise_field_min,
            table.c.noise_field_mean,
            table.c.noise_field_max,
            table.c.noise_mom_min,
            table.c.noise_mom_mean,
            table.c.noise_mom_max,
            table.c.label,
            table.c.diagnostics_json,
        ).filter(
            table.c.validated == True,
            table.c.trajectory_serial == trajectory.store_id,
            table.c.N_init_serial == N_init_obj.store_id,
            table.c.N_final_serial == N_final_obj.store_id,
            table.c.delta_Nstar_serial == delta_Nstar_obj.store_id,
            table.c.n_collocation_points_serial == n_collocation_points_obj.store_id,
            table.c.alpha_regularization_serial == alpha_regularization_obj.store_id,
            table.c.atol_serial == atol.store_id,
            table.c.rtol_serial == rtol.store_id,
            table.c.diffusion_serial == diffusion_model.store_id,
            table.c.diffusion_type   == diffusion_model.type_id,
            table.c.cosmo_serial == cosmo.store_id,
        )
        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            if label is None:
                label = (
                    f"GradientCoupledInstanton("
                    f"N_init={float(N_init_obj):.4g}, "
                    f"N_final={float(N_final_obj):.4g}, "
                    f"dNstar={float(delta_Nstar_obj):.4g}, "
                    f"n_colloc={int(n_collocation_points_obj)}, "
                    f"alpha={float(alpha_regularization_obj):.4g})"
                )
            return GradientCoupledInstanton(
                store_id=None,
                trajectory=trajectory,
                N_init=N_init_obj,
                N_final=N_final_obj,
                delta_Nstar=delta_Nstar_obj,
                n_collocation_points=n_collocation_points_obj,
                alpha_regularization=alpha_regularization_obj,
                atol=atol,
                rtol=rtol,
                cosmo=cosmo,
                N_sample=N_sample,
                diffusion_model=diffusion_model,
                label=label,
                tags=tags,
            )

        obj = GradientCoupledInstanton(
            store_id=row_data.serial,
            trajectory=trajectory,
            N_init=N_init_obj,
            N_final=N_final_obj,
            delta_Nstar=delta_Nstar_obj,
            n_collocation_points=n_collocation_points_obj,
            alpha_regularization=alpha_regularization_obj,
            atol=atol,
            rtol=rtol,
            cosmo=cosmo,
            N_sample=N_sample,
            diffusion_model=diffusion_model,
            label=row_data.label,
            tags=tags,
            timestamp=row_data.timestamp,
        )
        obj._trajectory_serial = trajectory.store_id
        obj._delta_Nstar_serial = delta_Nstar_obj.store_id
        units = trajectory.units
        if row_data.N_total is not None:
            obj._N_total = row_data.N_total
        if row_data.msr_action is not None:
            obj._msr_action = row_data.msr_action
        obj._noise_field_min  = row_data.noise_field_min
        obj._noise_field_mean = row_data.noise_field_mean
        obj._noise_field_max  = row_data.noise_field_max
        obj._noise_mom_min  = row_data.noise_mom_min
        obj._noise_mom_mean = row_data.noise_mom_mean
        obj._noise_mom_max  = row_data.noise_mom_max
        obj._diagnostics = (
            json.loads(row_data.diagnostics_json) if row_data.diagnostics_json else None
        )

        if not do_not_populate:
            if obj._diagnostics is not None and obj._diagnostics.get("full_values_stored", True) is False:
                raise RuntimeError(
                    f"GradientCoupledInstanton(id={obj.store_id}) was stored in "
                    f"scalars-only mode; full per-sample values were never persisted. "
                    f"Re-run with _do_not_populate=True, or recompute this instanton "
                    f"in full-fidelity mode."
                )
            self._populate(obj, row_data, tables, conn, units=units)
            self._populate_profile(obj, tables, conn, units=units)

        setattr(obj, "_deserialized", True)
        return obj

    def _populate(self, obj, row, tables, conn, units=None):
        """Load GradientCoupledInstantonValue records for a validated instanton."""
        from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
            GradientCoupledInstantonValue,
        )
        from InflationConcepts.efold_value import efold_value

        value_table = tables.get("GradientCoupledInstantonValue")
        efold_table = tables.get("efold_value")
        if value_table is None or efold_table is None:
            return

        PlanckMass = units.PlanckMass

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
                GradientCoupledInstantonValue(
                    store_id=None,
                    N=N_obj,
                    phi=[v * PlanckMass for v in data["phi_PlanckMass"]],
                    pi=[v * PlanckMass for v in data["pi_PlanckMass"]],
                    rfield=[v / PlanckMass for v in data["rfield_invPlanckMass"]],
                    rmom=[v / PlanckMass for v in data["rmom_invPlanckMass"]],
                )
            )

        N_vals = [v.N.N for v in obj._values]
        if any(N_vals[i] > N_vals[i + 1] for i in range(len(N_vals) - 1)):
            raise RuntimeError(
                f"GradientCoupledInstanton(id={obj.store_id}): N-values are not "
                f"non-decreasing after ORDER BY — database may be corrupt"
            )

    def _populate_profile(self, obj, tables, conn, units=None):
        """Load GradientCoupledInstantonProfile records — persisted unconditionally,
        regardless of store_full_values (matches CompactionFunctionSamples's own
        precedent)."""
        from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
            GradientCoupledInstantonProfileValue,
        )

        profile_table = tables.get("GradientCoupledInstantonProfile")
        if profile_table is None:
            return

        Mpc = units.Mpc

        rows = conn.execute(
            sqla.select(
                profile_table.c.node_index,
                profile_table.c.zeta,
                profile_table.c.r_ratio,
                profile_table.c.C,
                profile_table.c.r_phys_Mpc,
            )
            .filter(profile_table.c.parent_serial == obj.store_id)
            .order_by(profile_table.c.node_index)
        ).fetchall()

        obj._profile = [
            GradientCoupledInstantonProfileValue(
                node_index=r.node_index, zeta=r.zeta, r_ratio=r.r_ratio, C=r.C,
                r_phys=r.r_phys_Mpc * Mpc,
            )
            for r in rows
        ]

        node_vals = [p.node_index for p in obj._profile]
        if any(node_vals[i] > node_vals[i + 1] for i in range(len(node_vals) - 1)):
            raise RuntimeError(
                f"GradientCoupledInstanton(id={obj.store_id}): profile node_index "
                f"values are not non-decreasing after ORDER BY — database may be corrupt"
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
                "n_collocation_points_serial": obj._n_collocation_points.store_id,
                "alpha_regularization_serial": obj._alpha_regularization.store_id,
                "atol_serial": obj._atol.store_id,
                "rtol_serial": obj._rtol.store_id,
                "diffusion_serial": obj._diffusion_model.store_id,
                "diffusion_type":   obj._diffusion_model.type_id,
                "cosmo_serial": obj._cosmo.store_id,
                "n_fields": obj.n_fields,
                "N_total": None,
                "msr_action": None,
                "noise_field_min": None,
                "noise_field_mean": None,
                "noise_field_max": None,
                "noise_mom_min": None,
                "noise_mom_mean": None,
                "noise_mom_max": None,
                "label": obj._label,
                "diagnostics_json": diagnostics_json,
                "validated": False,
            })
            obj._my_id = store_id
            return obj

        units = obj._trajectory.units
        PlanckMass = units.PlanckMass
        Mpc = units.Mpc

        store_id = inserter(conn, {
            "trajectory_serial": obj._trajectory.store_id,
            "N_init_serial": obj._N_init.store_id,
            "N_final_serial": obj._N_final.store_id,
            "delta_Nstar_serial": obj._delta_Nstar.store_id,
            "n_collocation_points_serial": obj._n_collocation_points.store_id,
            "alpha_regularization_serial": obj._alpha_regularization.store_id,
            "atol_serial": obj._atol.store_id,
            "rtol_serial": obj._rtol.store_id,
            "diffusion_serial": obj._diffusion_model.store_id,
            "diffusion_type":   obj._diffusion_model.type_id,
            "cosmo_serial": obj._cosmo.store_id,
            "n_fields": obj.n_fields,
            "N_total": getattr(obj, "_N_total", None),
            "msr_action": obj.msr_action,
            "noise_field_min":  obj.noise_field_min,
            "noise_field_mean": obj.noise_field_mean,
            "noise_field_max":  obj.noise_field_max,
            "noise_mom_min":  obj.noise_mom_min,
            "noise_mom_mean": obj.noise_mom_mean,
            "noise_mom_max":  obj.noise_mom_max,
            "label": obj._label,
            "diagnostics_json": diagnostics_json,
            "validated": False,
        })
        obj._my_id = store_id

        if store_full_values:
            value_inserter = inserters["GradientCoupledInstantonValue"]
            for v in obj._values:
                value_inserter(conn, {
                    "instanton_serial": store_id,
                    "N_serial": v.N.store_id,
                    "fields_json": json.dumps({
                        "phi_PlanckMass":       [x / PlanckMass for x in v.phi],
                        "pi_PlanckMass":        [x / PlanckMass for x in v.pi],
                        "rfield_invPlanckMass": [x * PlanckMass for x in v.rfield],
                        "rmom_invPlanckMass":   [x * PlanckMass for x in v.rmom],
                    }),
                })

        # Profile rows: unconditional, regardless of store_full_values (matches
        # CompactionFunctionSamples's own precedent -- this is the actual science
        # output).
        profile_inserter = inserters["GradientCoupledInstantonProfile"]
        for p in obj._profile:
            profile_inserter(conn, {
                "parent_serial": store_id,
                "node_index": p.node_index,
                "zeta": p.zeta,
                "r_ratio": p.r_ratio,
                "C": p.C,
                "r_phys_Mpc": p.r_phys / Mpc,
            })

        return obj

    def validate(self, obj, conn, table, tables):
        if not obj.available:
            raise RuntimeError("Attempt to validate an object that has not been stored")

        if obj.failure:
            validated = True
        else:
            value_table = tables["GradientCoupledInstantonValue"]
            profile_table = tables["GradientCoupledInstantonProfile"]
            store_full_values = getattr(obj, "_store_full_values", True)
            expected_values = 0 if not store_full_values else len(obj._values)
            expected_profile = len(obj._profile)

            actual_values = conn.execute(
                sqla.select(sqla.func.count()).select_from(value_table).filter(
                    value_table.c.instanton_serial == obj.store_id
                )
            ).scalar()
            actual_profile = conn.execute(
                sqla.select(sqla.func.count()).select_from(profile_table).filter(
                    profile_table.c.parent_serial == obj.store_id
                )
            ).scalar()

            validated = (actual_values == expected_values) and (actual_profile == expected_profile)
            if not validated:
                print(f"!! WARNING: GradientCoupledInstanton {obj.store_id}: "
                      f"expected {expected_values} value rows (found {actual_values}), "
                      f"expected {expected_profile} profile rows (found {actual_profile})")

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
            # Delete child rows first; there is no ON DELETE CASCADE on either FK.
            value_table = tables.get("GradientCoupledInstantonValue")
            if value_table is not None:
                conn.execute(
                    sqla.delete(value_table).where(
                        value_table.c.instanton_serial.in_(serials)
                    )
                )
            profile_table = tables.get("GradientCoupledInstantonProfile")
            if profile_table is not None:
                conn.execute(
                    sqla.delete(profile_table).where(
                        profile_table.c.parent_serial.in_(serials)
                    )
                )
            conn.execute(sqla.delete(table).filter(table.c.serial.in_(serials)))
            return [f"Pruned {len(serials)} unvalidated GradientCoupledInstanton records"]
        elif len(rows) > 0:
            return [f"Found {len(rows)} unvalidated GradientCoupledInstanton records (not pruned)"]
        return []


class sqla_GradientCoupledInstantonValue_factory(SQLAFactoryBase):
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
                    sqla.ForeignKey("GradientCoupledInstanton.serial"),
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
            "sqla_GradientCoupledInstantonValue_factory.build() is not used directly; "
            "values are inserted by sqla_GradientCoupledInstantonFactory.store()."
        )

    def store(self, obj, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_GradientCoupledInstantonValue_factory.store() is not used directly; "
            "values are inserted by sqla_GradientCoupledInstantonFactory.store()."
        )

    def validate(self, obj, conn, table, tables):
        raise NotImplementedError(
            "sqla_GradientCoupledInstantonValue_factory.validate() is not used directly."
        )

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        return []


class sqla_GradientCoupledInstantonProfileFactory(SQLAFactoryBase):
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
                    sqla.ForeignKey("GradientCoupledInstanton.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column("node_index", sqla.Integer, nullable=False),
                sqla.Column("zeta", sqla.Float(64), nullable=False),
                sqla.Column("r_ratio", sqla.Float(64), nullable=False),
                sqla.Column("C", sqla.Float(64), nullable=False),
                sqla.Column("r_phys_Mpc", sqla.Float(64), nullable=False),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_GradientCoupledInstantonProfileFactory.build() is not used directly; "
            "profile rows are inserted by sqla_GradientCoupledInstantonFactory.store()."
        )

    def store(self, obj, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_GradientCoupledInstantonProfileFactory.store() is not used directly."
        )

    def validate(self, obj, conn, table, tables):
        raise NotImplementedError(
            "sqla_GradientCoupledInstantonProfileFactory.validate() is not used directly."
        )

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        return []
