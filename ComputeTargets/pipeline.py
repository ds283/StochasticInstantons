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

from typing import Optional

import ray
from ray import ObjectRef

from ComputeTargets.CompactionFunction import CompactionFunction, _compute_instanton_path
from ComputeTargets.FullInstanton import FullInstanton
from ComputeTargets.SlowRollInstanton import SlowRollInstanton

# Relative tolerance for the integrity check on pre-existing scalar-only rows.
# Must be loose enough to tolerate floating-point non-determinism between two
# ODE solves (typically < 1e-10), but tight enough to catch real mismatches.
# 1e-4 (100 ppm) is conservative.
PIPELINE_SCALAR_INTEGRITY_RTOL = 1e-4


def _check_scalar_integrity(
    cls_name: str,
    existing_obj,
    fresh_data: dict,
) -> None:
    """
    Verify that freshly computed scalars agree with a pre-existing DB row.

    Raises RuntimeError if msr_action or N_total disagree by more than
    PIPELINE_SCALAR_INTEGRITY_RTOL. A fresh failure result or a None stored
    value (existing row was itself a failure) is silently skipped.
    """
    if fresh_data.get("failure", False):
        return

    stored_action = existing_obj.msr_action
    stored_N_total = getattr(existing_obj, "_N_total", None)

    fresh_action = fresh_data["msr_action"]
    fresh_N_total = fresh_data["N_total"]

    for scalar_name, stored_val, fresh_val in (
        ("msr_action", stored_action, fresh_action),
        ("N_total", stored_N_total, fresh_N_total),
    ):
        if stored_val is None:
            continue
        rel_err = abs(stored_val - fresh_val) / max(abs(stored_val), 1e-300)
        if rel_err > PIPELINE_SCALAR_INTEGRITY_RTOL:
            raise RuntimeError(
                f"{cls_name}(id={existing_obj.store_id}): recomputed {scalar_name}="
                f"{fresh_val!r} disagrees with stored value {stored_val!r} "
                f"(relative error {rel_err:.2e} > tolerance "
                f"{PIPELINE_SCALAR_INTEGRITY_RTOL:.2e}). "
                f"This is a database integrity failure — the computation may be "
                f"non-deterministic or the database row may be corrupt."
            )

    stored_phi1_mean = getattr(existing_obj, "_noise_phi1_mean", None)
    fresh_phi1_mean  = fresh_data.get("noise_phi1_mean")
    if stored_phi1_mean is None and fresh_phi1_mean is not None:
        raise RuntimeError(
            f"{cls_name}(id={existing_obj.store_id}): stored row is missing "
            f"noise_phi1_mean but fresh computation produced {fresh_phi1_mean!r}. "
            f"The stored row pre-dates noise amplitude support and must be recomputed."
        )
    if stored_phi1_mean is not None and fresh_phi1_mean is not None:
        rel_err = abs(stored_phi1_mean - fresh_phi1_mean) / max(abs(stored_phi1_mean), 1e-300)
        if rel_err > PIPELINE_SCALAR_INTEGRITY_RTOL:
            raise RuntimeError(
                f"{cls_name}(id={existing_obj.store_id}): recomputed noise_phi1_mean="
                f"{fresh_phi1_mean!r} disagrees with stored value {stored_phi1_mean!r} "
                f"(relative error {rel_err:.2e} > tolerance "
                f"{PIPELINE_SCALAR_INTEGRITY_RTOL:.2e}). "
                f"This is a database integrity failure — the computation may be "
                f"non-deterministic or the database row may be corrupt."
            )


@ray.remote(num_cpus=0)
def compute_pipeline(
    trajectory,
    N_init_obj,
    N_final_obj,
    delta_Nstar_obj,
    N_sample,
    atol_obj,
    rtol_obj,
    dm,
    cosmo,
    C_threshold: float,
    label: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    Orchestrate FullInstanton, SlowRollInstanton and CompactionFunction for
    one grid point inside a single Ray worker.

    num_cpus=0: this function blocks on nested Ray tasks while holding no CPU.
    The actual CPU work runs inside _compute_full_instanton.remote() and
    _compute_slow_roll_instanton.remote(), which each claim their own CPU slots.
    """
    fi = FullInstanton(
        store_id=None,
        trajectory=trajectory,
        N_init=N_init_obj,
        N_final=N_final_obj,
        delta_Nstar=delta_Nstar_obj,
        N_sample=N_sample,
        atol=atol_obj,
        rtol=rtol_obj,
        diffusion_model=dm,
    )
    sri = SlowRollInstanton(
        store_id=None,
        trajectory=trajectory,
        N_init=N_init_obj,
        N_final=N_final_obj,
        delta_Nstar=delta_Nstar_obj,
        N_sample=N_sample,
        atol=atol_obj,
        rtol=rtol_obj,
        diffusion_model=dm,
    )

    fi_ref = fi.compute(label=label, verbose=verbose)
    sri_ref = sri.compute(label=label, verbose=verbose)
    fi_data, sri_data = ray.get([fi_ref, sri_ref])

    fi._populate_from_result(fi_data)
    sri._populate_from_result(sri_data)

    traj = trajectory.get()
    potential = traj._potential
    units = potential._units
    atol_f = 10.0 ** atol_obj.log10_tol
    rtol_f = 10.0 ** rtol_obj.log10_tol

    # Call _compute_instanton_path directly: fi and sri are populated in memory
    # but have no store_id. CompactionFunction.compute() gates on
    # proxy.available (i.e. store_id is not None), which would incorrectly
    # suppress both branches here. _compute_instanton_path only needs
    # instanton_obj.N_init_value, .N_final_value, and .values — all set by
    # _populate_from_result — so calling it directly is correct.
    full_cf_result = None
    if not fi.failure:
        full_cf_result = _compute_instanton_path(
            fi, False, traj, potential, units, cosmo,
            C_threshold, atol_f, rtol_f,
            label=label, verbose=verbose,
        )

    sr_cf_result = None
    if not sri.failure:
        sr_cf_result = _compute_instanton_path(
            sri, True, traj, potential, units, cosmo,
            C_threshold, atol_f, rtol_f,
            label=label, verbose=verbose,
        )

    return {
        "fi_data":   fi_data,
        "sri_data":  sri_data,
        "full":      full_cf_result,
        "slow_roll": sr_cf_result,
    }


class PipelineWorkItem:
    """
    Driver-side work item for the unified pipeline.

    Wraps compute_pipeline.remote() to present the standard
    compute()/store()/available interface that RayWorkPool expects.
    Reconstructs FullInstanton, SlowRollInstanton and CompactionFunction
    in memory after the remote function resolves.
    """

    def __init__(
        self,
        grid_item,
        traj_proxy,
        N_sample,
        dm,
        cosmo,
        C_threshold: float,
        C_bar_threshold: float = 0.4,  # accepted for backward compat; unused
        atol_obj=None,
        rtol_obj=None,
        fi_existing=None,
        sri_existing=None,
    ):
        self._grid_item = grid_item
        self._traj_proxy = traj_proxy
        self._N_sample = N_sample
        self._dm = dm
        self._cosmo = cosmo
        self._C_threshold = C_threshold
        self._atol_obj = atol_obj
        self._rtol_obj = rtol_obj
        self._fi_existing = fi_existing
        self._sri_existing = sri_existing

        self._compute_ref: Optional[ObjectRef] = None
        self._fi: Optional[FullInstanton] = None
        self._sri: Optional[SlowRollInstanton] = None
        self._cf: Optional[CompactionFunction] = None

    @property
    def available(self) -> bool:
        """Always False — PipelineWorkItem is only created for missing CF rows."""
        return False

    @property
    def delta_Nstar(self):
        """delta_Nstar domain object for shard routing."""
        return self._grid_item[3]

    @property
    def fi(self) -> Optional[FullInstanton]:
        return self._fi

    @property
    def sri(self) -> Optional[SlowRollInstanton]:
        return self._sri

    @property
    def cf(self) -> Optional[CompactionFunction]:
        return self._cf

    @property
    def fi_existing(self):
        """DB-loaded scalar-only FullInstanton, if found before dispatch."""
        return self._fi_existing

    @property
    def sri_existing(self):
        """DB-loaded scalar-only SlowRollInstanton, if found before dispatch."""
        return self._sri_existing

    def compute(self, label=None, verbose=False) -> ObjectRef:
        """Dispatch compute_pipeline as a Ray remote task. Returns an ObjectRef."""
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        _, N_init_obj, N_final_obj, delta_Nstar_obj = self._grid_item
        self._compute_ref = compute_pipeline.remote(
            trajectory=self._traj_proxy,
            N_init_obj=N_init_obj,
            N_final_obj=N_final_obj,
            delta_Nstar_obj=delta_Nstar_obj,
            N_sample=self._N_sample,
            atol_obj=self._atol_obj,
            rtol_obj=self._rtol_obj,
            dm=self._dm,
            cosmo=self._cosmo,
            C_threshold=self._C_threshold,
            label=label,
            verbose=verbose,
        )
        return self._compute_ref

    def store(self) -> None:
        """
        Called by RayWorkPool's store_handler after compute() resolves.

        Resolves the Ray future, reconstructs FullInstanton, SlowRollInstanton
        and CompactionFunction in memory, and runs scalar integrity checks
        against any pre-existing DB rows.
        """
        if self._compute_ref is None:
            raise RuntimeError("store() called but no compute() is in progress")
        data = ray.get(self._compute_ref)
        self._compute_ref = None

        _, N_init_obj, N_final_obj, delta_Nstar_obj = self._grid_item

        self._fi = FullInstanton(
            store_id=None,
            trajectory=self._traj_proxy,
            N_init=N_init_obj,
            N_final=N_final_obj,
            delta_Nstar=delta_Nstar_obj,
            N_sample=self._N_sample,
            atol=self._atol_obj,
            rtol=self._rtol_obj,
            diffusion_model=self._dm,
        )
        self._fi._populate_from_result(data["fi_data"])

        if self._fi_existing is not None and self._fi_existing.available:
            _check_scalar_integrity("FullInstanton", self._fi_existing, data["fi_data"])

        self._sri = SlowRollInstanton(
            store_id=None,
            trajectory=self._traj_proxy,
            N_init=N_init_obj,
            N_final=N_final_obj,
            delta_Nstar=delta_Nstar_obj,
            N_sample=self._N_sample,
            atol=self._atol_obj,
            rtol=self._rtol_obj,
            diffusion_model=self._dm,
        )
        self._sri._populate_from_result(data["sri_data"])

        if self._sri_existing is not None and self._sri_existing.available:
            _check_scalar_integrity("SlowRollInstanton", self._sri_existing, data["sri_data"])

        # Pass fi/sri directly (not as proxies) — compute() is never called on
        # the CF in the pipeline path, so no ray.put() is needed here.
        fi_for_cf = self._fi if not self._fi.failure else None
        sri_for_cf = self._sri if not self._sri.failure else None

        if fi_for_cf is None and sri_for_cf is None:
            # Both branches failed; _cf remains None — handled in persist step.
            return

        self._cf = CompactionFunction(
            store_id=None,
            full_instanton=fi_for_cf,
            slow_roll_instanton=sri_for_cf,
            trajectory=self._traj_proxy,
            cosmo=self._cosmo,
            delta_Nstar=delta_Nstar_obj,
            C_threshold=self._C_threshold,
            atol=self._atol_obj,
            rtol=self._rtol_obj,
        )
        self._cf._cosmo_store_id = self._cosmo.store_id
        self._cf._populate_from_result({
            "full":      data["full"],
            "slow_roll": data["slow_roll"],
        })
