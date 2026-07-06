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

"""
Datastore compute target for the gradient-coupled ("onion model") instanton.

Ties together the numerical pipeline built in prompts 01-13
(``LGLCollocationGrid``, ``solve_picard``, ``extract_zeta_profile``,
``assign_scales``) into a single ``ComputeTargets``/``Datastore`` object,
following the Ray-dispatch pattern set out in ``.claude/rules/ray-dispatch.md``.

Unlike ``FullInstanton``/``CompactionFunction``, which are split across two
compute targets because ``CompactionFunction`` serves two different
producers, this model has a single producer for both the raw grid solution
and the physical zeta(y)/C(y)/r_phys(y) profile, so it is kept as one class.

``cosmo`` (a persisted ``CosmologicalParams``) is threaded through as a
constructor parameter even though it is not read by any of the raw
numerical routines from prompts 01-08: ``assign_scales`` (prompt 09) needs
it to evaluate the Leach-Liddle anchor via ``ln_k_phys_Mpc``, exactly the
same role it plays for ``CompactionFunction``. This mirrors
``CompactionFunction``'s own ``cosmo`` constructor parameter and
``cosmo_serial`` FK column.

Scope boundary: the numerical MSR action ($S_{\rm MSR}$) is deliberately
out of scope here -- ``msr_action`` exists as a nullable column (matching
``FullInstanton``'s own column) but is never populated. Nothing in prompts
01-13 derived the action-functional evaluation for this model; it is
deferred to a dedicated follow-up prompt.
"""

from datetime import datetime
from typing import List, Optional

import numpy as np
import ray
from ray import ObjectRef

from Caching.ExtractionCache import ExtractionCache, InMemoryExtractionCache
from CosmologyModels.cosmo_params import CosmologicalParams
from Datastore.object import DatastoreObject
from InflationConcepts.alpha_regularization import alpha_regularization as alpha_regularization_t
from InflationConcepts.delta_Nstar import delta_Nstar
from InflationConcepts.DiffusionModel import (
    AbstractDiffusionModel,
    MasslessDecoupledDiffusion,
)
from InflationConcepts.efold_value import efold_array, efold_value
from InflationConcepts.n_collocation_points import (
    n_collocation_points as n_collocation_points_t,
)
from InflationConcepts.N_final import N_final
from InflationConcepts.N_init import N_init
from MetadataConcepts.store_tag import store_tag
from MetadataConcepts.tolerance import tolerance
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import delta_s

# C_threshold only affects assign_scales' own r_max/r_peak diagnostics,
# neither of which is persisted anywhere for this compute target (the
# profile table stores zeta/r_ratio/C/r_phys only) -- so a single fixed
# default, not a constructor parameter, is sufficient.
_C_THRESHOLD = 0.4


@ray.remote
def _compute_gradient_coupled_instanton(
    trajectory,             # InflatonTrajectoryProxy
    dm,                     # AbstractDiffusionModel
    cosmo_T_CMB_Kelvin: float,
    n_collocation_points: int,
    alpha: float,
    N_init: float,
    N_final: float,
    delta_Nstar: float,
    N_sample: list,
    atol: float,
    rtol: float,
    store_full_values: bool,
    label: Optional[str] = None,
) -> dict:
    """
    Solve the gradient-coupled instanton BVP and extract its physical
    profile, per the ten-step pipeline in prompt 14 Part C.

    Returns a dict with keys:
        "failure", "N_total", "N_sample",
        "phi", "pi", "rfield", "rmom"                  (per (N_sample, node), empty if not store_full_values)
        "zeta", "r_ratio", "C", "r_phys"                (per node, at the final row)
        "noise_field_min/mean/max", "noise_mom_min/mean/max"
            -- dimensionless noise amplitude in units of Hawking standard
            deviations per e-fold, evaluated at the core node (y=+1) across
            every row of the dense solver grid, mirroring FullInstanton's own
            noise_phi1_*/noise_phi2_* construction exactly (see
            ComputeTargets/FullInstanton.py's own comment near its analogous
            computation) but generalized to this model's field/mom
            vocabulary and its shell-diluted diffusion coefficients. None if
            the corresponding diagonal diffusion coefficient is zero
            everywhere (e.g. noise_mom_* for MasslessDecoupledDiffusion,
            whose D22 is identically zero).
        "diagnostics"
    """
    import time

    from ComputeTargets.GradientCoupledInstanton.extraction import extract_zeta_profile
    from ComputeTargets.GradientCoupledInstanton.forward_rhs import diluted_diffusion_coefficients
    from ComputeTargets.GradientCoupledInstanton.picard import solve_picard
    from ComputeTargets.GradientCoupledInstanton.scale_assignment import assign_scales

    compute_start = time.perf_counter()

    _lbl = label if label else (
        f"GradientCoupledInstanton(N_init={N_init:.4g}, N_final={N_final:.4g}, "
        f"dNstar={delta_Nstar:.4g}, n_colloc={n_collocation_points})"
    )

    # ── Step 1: materialise the trajectory once ──────────────────────────────
    traj = trajectory.get()
    potential = traj._potential
    units = potential._units

    class _CosmoProxy:
        """Avoids re-serialising the full CosmologicalParams object across
        the Ray boundary -- only T_CMB_Kelvin is ever read by ln_k_phys_Mpc."""
        def __init__(self, T_CMB_Kelvin):
            self.T_CMB_Kelvin = T_CMB_Kelvin

    cosmo = _CosmoProxy(cosmo_T_CMB_Kelvin)

    # ── Step 2: collocation grid ─────────────────────────────────────────────
    grid = LGLCollocationGrid(n_collocation_points)

    N_offset = traj.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar

    # ── Step 3: H^2 at the (noiseless) initial condition ─────────────────────
    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)

    phi_end = traj.phi_at(N_offset + N_total)

    def _failure_result(diagnostics: dict) -> dict:
        return {
            "failure": True,
            "N_total": N_total,
            "N_sample": [],
            "phi": [], "pi": [], "rfield": [], "rmom": [],
            "zeta": [], "r_ratio": [], "C": [], "r_phys": [],
            "noise_field_min": None, "noise_field_mean": None, "noise_field_max": None,
            "noise_mom_min": None, "noise_mom_mean": None, "noise_mom_max": None,
            "diagnostics": diagnostics,
        }

    # ── Step 4: the full Picard/shooting pipeline ────────────────────────────
    result = solve_picard(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
        traj, potential, dm, atol, rtol, phi_end,
        label=_lbl,
    )

    # ── Step 5: bail out on non-convergence ──────────────────────────────────
    if result.get("failure", False):
        return _failure_result(result.get("diagnostics"))

    N_grid = np.asarray(result["N_grid"])
    phi_grid = np.asarray(result["phi_grid"])
    pi_grid = np.asarray(result["pi_grid"])
    rfield_grid = np.asarray(result["rfield_grid"])
    rmom_grid = np.asarray(result["rmom_grid"])
    N_total = result["N_total"]

    phi_final_row = phi_grid[-1, :]
    pi_final_row = pi_grid[-1, :]

    # ── Step 6: zeta(y) extraction at the shared final row ──────────────────
    extraction = extract_zeta_profile(
        phi_final_row, pi_final_row, N_offset, N_total, traj, potential, atol, rtol, units,
    )

    # ── Step 7: scale assignment ──────────────────────────────────────────────
    H_sq_core_final = potential.H_sq(phi_final_row[-1], pi_final_row[-1])
    delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_final, H_sq_nl_init, alpha)
    scales = assign_scales(
        extraction["zeta"], delta_s_N_final, grid, traj, N_init, N_offset, alpha,
        potential, units, cosmo, C_threshold=_C_THRESHOLD,
    )

    # ── Step 8: noise summary stats at the core node (y=+1), across every
    # row of the dense solver grid -- physically analogous to FullInstanton's
    # own single reported trajectory (the reconstructed core/horizon
    # trajectory), not an aggregate over every shell. Dimensionless, in units
    # of Hawking standard deviations, mirroring FullInstanton's own
    # noise_phi1_*/noise_phi2_* construction (ComputeTargets/FullInstanton.py
    # lines ~303-326) exactly -- same sqrt/cross-term formula and the same
    # "None if the diagonal coefficient is zero everywhere" guard -- but
    # using the shell-diluted D_phi/D_pi/D_phipi (the coefficients that
    # actually dress rfield/rmom in forward_rhs's own sourcing term) rather
    # than the raw, undiluted D_matrix output FullInstanton uses (that
    # simpler model has no shell dilution to begin with).
    rfield_core = rfield_grid[:, -1]
    rmom_core = rmom_grid[:, -1]

    D_phi_core = np.empty(len(N_grid))
    D_pi_core = np.empty(len(N_grid))
    D_phipi_core = np.empty(len(N_grid))
    for i in range(len(N_grid)):
        N_i = float(N_grid[i])
        phi_i = phi_grid[i]
        pi_i = pi_grid[i]
        H_sq_core_i = potential.H_sq(phi_i[-1], pi_i[-1])
        delta_s_N_i = delta_s(N_i, 0.0, H_sq_core_i, H_sq_nl_init, alpha)
        H_sq_loc_i = potential.H_sq(phi_i, pi_i)
        delta_s_loc_i = delta_s(N_i, 0.0, H_sq_loc_i, H_sq_nl_init, alpha)
        D_phi_i, D_pi_i, D_phipi_i = diluted_diffusion_coefficients(
            phi_i, pi_i, delta_s_N_i, delta_s_loc_i, grid, potential, dm,
        )
        D_phi_core[i] = D_phi_i[-1]
        D_pi_core[i] = D_pi_i[-1]
        D_phipi_core[i] = D_phipi_i[-1]

    abs_rfield_core = np.abs(rfield_core)
    abs_rmom_core = np.abs(rmom_core)

    if np.any(D_phi_core == 0.0):
        noise_field_min = noise_field_mean = noise_field_max = None
    else:
        sqrt_2Dphi = np.sqrt(2.0 * D_phi_core)
        sigma_field = sqrt_2Dphi * abs_rfield_core + (2.0 * D_phipi_core / sqrt_2Dphi) * abs_rmom_core
        noise_field_min  = float(sigma_field.min())
        noise_field_mean = float(sigma_field.mean())
        noise_field_max  = float(sigma_field.max())

    if np.any(D_pi_core == 0.0):
        noise_mom_min = noise_mom_mean = noise_mom_max = None
    else:
        sqrt_2Dpi = np.sqrt(2.0 * D_pi_core)
        sigma_mom = (2.0 * D_phipi_core / sqrt_2Dpi) * abs_rfield_core + sqrt_2Dpi * abs_rmom_core
        noise_mom_min  = float(sigma_mom.min())
        noise_mom_mean = float(sigma_mom.mean())
        noise_mom_max  = float(sigma_mom.max())

    # ── Step 9: interpolate onto N_sample, only if the caller wants full values ──
    # Gated on store_full_values *inside the worker* (unlike FullInstanton,
    # where this interpolation is always cheap) because building
    # n_collocation_points splines over the dense solver grid and evaluating
    # them at every N_sample point is a real cost that scalars-only campaigns
    # should not pay.
    if store_full_values and len(N_sample) > 0:
        N_out = sorted(n for n in N_sample if 0.0 <= n <= N_total) or [0.0, N_total]
        N_a = np.asarray(N_out)

        from ComputeTargets.GradientCoupledInstanton.picard import _build_node_splines

        phi_splines = _build_node_splines(N_grid, phi_grid, y_transform='linear')
        pi_splines = _build_node_splines(N_grid, pi_grid, y_transform='linear')
        rfield_splines = _build_node_splines(N_grid, rfield_grid, y_transform='sinh')
        rmom_splines = _build_node_splines(N_grid, rmom_grid, y_transform='sinh')

        phi_out = np.stack([[float(sp(N)) for sp in phi_splines] for N in N_a])
        pi_out = np.stack([[float(sp(N)) for sp in pi_splines] for N in N_a])
        rfield_out = np.stack([[float(sp(N)) for sp in rfield_splines] for N in N_a])
        rmom_out = np.stack([[float(sp(N)) for sp in rmom_splines] for N in N_a])

        N_out_list = N_out
        phi_list = phi_out.tolist()
        pi_list = pi_out.tolist()
        rfield_list = rfield_out.tolist()
        rmom_list = rmom_out.tolist()
    else:
        N_out_list = []
        phi_list = []
        pi_list = []
        rfield_list = []
        rmom_list = []

    diagnostics = dict(result["diagnostics"])
    diagnostics["scale_assignment"] = {
        "r_max": scales["r_max"],
        "r_peak": scales["r_peak"],
        "r_phys_out": scales["r_phys_out"],
        **scales["diagnostics"],
    }
    diagnostics["extraction_failure_mask"] = extraction["failure_mask"].tolist()
    diagnostics["compute_time_total"] = time.perf_counter() - compute_start

    # ── Step 10: package for store() ─────────────────────────────────────────
    return {
        "failure": False,
        "N_total": N_total,
        "N_sample": N_out_list,
        "phi": phi_list, "pi": pi_list, "rfield": rfield_list, "rmom": rmom_list,
        "zeta": extraction["zeta"].tolist(),
        "r_ratio": scales["r_ratio"].tolist(),
        "C": scales["C"].tolist(),
        "r_phys": scales["r_phys"].tolist(),
        "noise_field_min": noise_field_min,
        "noise_field_mean": noise_field_mean,
        "noise_field_max": noise_field_max,
        "noise_mom_min": noise_mom_min,
        "noise_mom_mean": noise_mom_mean,
        "noise_mom_max": noise_mom_max,
        "diagnostics": diagnostics,
    }


class GradientCoupledInstantonValue(DatastoreObject):
    """
    Dense grid-node state (phi, pi, rfield, rmom) at a single e-folding
    sample point. Each field is a list of length n_collocation_points,
    ordered to match LGLCollocationGrid's own node ordering (y=-1 ... y=+1).
    """

    def __init__(
        self,
        store_id: Optional[int],
        N: efold_value,
        phi: List[float],
        pi: List[float],
        rfield: List[float],
        rmom: List[float],
    ):
        DatastoreObject.__init__(self, store_id)
        self._N = N
        self._phi = phi
        self._pi = pi
        self._rfield = rfield
        self._rmom = rmom

    @property
    def N(self) -> efold_value:
        return self._N

    @property
    def phi(self) -> List[float]:
        return self._phi

    @property
    def pi(self) -> List[float]:
        return self._pi

    @property
    def rfield(self) -> List[float]:
        return self._rfield

    @property
    def rmom(self) -> List[float]:
        return self._rmom


class GradientCoupledInstantonProfileValue:
    """
    Physical profile (zeta, r_ratio, C, r_phys) at a single collocation
    node, evaluated at the transition's final row (N_total). Not a
    DatastoreObject subclass: node_index is a plain integer
    (0..n_collocation_points-1) with no FK to a y_value-style concept, since
    y is fully determined by n_collocation_points alone (LGLCollocationGrid
    is deterministic given that one integer).
    """

    def __init__(
        self,
        node_index: int,
        zeta: float,
        r_ratio: float,
        C: float,
        r_phys: float,
    ):
        self._node_index = node_index
        self._zeta = zeta
        self._r_ratio = r_ratio
        self._C = C
        self._r_phys = r_phys

    @property
    def node_index(self) -> int:
        return self._node_index

    @property
    def zeta(self) -> float:
        return self._zeta

    @property
    def r_ratio(self) -> float:
        return self._r_ratio

    @property
    def C(self) -> float:
        return self._C

    @property
    def r_phys(self) -> float:
        return self._r_phys


class GradientCoupledInstanton(DatastoreObject):
    """
    The gradient-coupled ("onion model") stochastic instanton.

    Plain Python class on the driver -- no @ray.remote (see
    .claude/rules/ray-dispatch.md). Numerical work is dispatched via the
    _compute_gradient_coupled_instanton Ray remote function.
    """

    def __init__(
        self,
        store_id: Optional[int],
        trajectory,  # InflatonTrajectoryProxy
        N_init: N_init,
        N_final: N_final,
        delta_Nstar: delta_Nstar,
        n_collocation_points: n_collocation_points_t,
        alpha_regularization: alpha_regularization_t,
        atol: tolerance,
        rtol: tolerance,
        cosmo: CosmologicalParams,
        N_sample: Optional[efold_array],
        diffusion_model: Optional[AbstractDiffusionModel] = None,
        label: Optional[str] = None,
        tags: Optional[List[store_tag]] = None,
        timestamp: Optional[datetime] = None,
    ):
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)
        self._trajectory = trajectory
        self._N_init: N_init = N_init
        self._N_final: N_final = N_final
        self._delta_Nstar: delta_Nstar = delta_Nstar
        self._n_collocation_points: n_collocation_points_t = n_collocation_points
        self._alpha_regularization: alpha_regularization_t = alpha_regularization
        self._N_sample: Optional[efold_array] = N_sample
        self._atol: tolerance = atol
        self._rtol: tolerance = rtol
        self._cosmo: CosmologicalParams = cosmo
        self._diffusion_model: AbstractDiffusionModel = diffusion_model or MasslessDecoupledDiffusion()
        self._label: Optional[str] = label
        self._tags: List[store_tag] = tags or []
        self._msr_action: Optional[float] = None  # deferred -- see module docstring
        self._noise_field_min: Optional[float] = None
        self._noise_field_mean: Optional[float] = None
        self._noise_field_max: Optional[float] = None
        self._noise_mom_min: Optional[float] = None
        self._noise_mom_mean: Optional[float] = None
        self._noise_mom_max: Optional[float] = None
        self._values: List[GradientCoupledInstantonValue] = []
        self._profile: List[GradientCoupledInstantonProfileValue] = []
        self._compute_ref: Optional[ObjectRef] = None
        self._store_full_values: bool = True
        self._extraction_cache: ExtractionCache = InMemoryExtractionCache()

    @property
    def available(self) -> bool:
        """True if this instanton has been persisted to the datastore."""
        return self._my_id is not None

    @property
    def n_fields(self) -> int:
        """Number of scalar fields; always 1 for a single-field inflaton."""
        return 1

    @property
    def failure(self) -> bool:
        return getattr(self, "_failure", False)

    @property
    def N_init_value(self) -> N_init:
        return self._N_init

    @property
    def N_final_value(self) -> N_final:
        return self._N_final

    @property
    def delta_Nstar(self) -> delta_Nstar:
        return self._delta_Nstar

    @property
    def shard_key(self) -> delta_Nstar:
        return self._delta_Nstar

    @property
    def n_collocation_points_value(self) -> n_collocation_points_t:
        return self._n_collocation_points

    @property
    def alpha_regularization_value(self) -> alpha_regularization_t:
        return self._alpha_regularization

    @property
    def msr_action(self) -> Optional[float]:
        """MSR saddle-point action; deliberately unpopulated -- see module docstring."""
        return self._msr_action

    @property
    def noise_field_min(self) -> Optional[float]:
        return self._noise_field_min

    @property
    def noise_field_mean(self) -> Optional[float]:
        return self._noise_field_mean

    @property
    def noise_field_max(self) -> Optional[float]:
        return self._noise_field_max

    @property
    def noise_mom_min(self) -> Optional[float]:
        return self._noise_mom_min

    @property
    def noise_mom_mean(self) -> Optional[float]:
        return self._noise_mom_mean

    @property
    def noise_mom_max(self) -> Optional[float]:
        return self._noise_mom_max

    @property
    def diagnostics(self) -> Optional[dict]:
        return getattr(self, "_diagnostics", None)

    @property
    def values(self) -> List[GradientCoupledInstantonValue]:
        """Dense per-sample grid rows; empty until compute() succeeds, or
        always empty if store_full_values was False."""
        return self._values

    @property
    def profile(self) -> List[GradientCoupledInstantonProfileValue]:
        """Per-node zeta/r_ratio/C/r_phys profile at the final row; empty
        until compute() succeeds."""
        return self._profile

    def compute(self, label: Optional[str] = None) -> ObjectRef:
        """
        Dispatch the gradient-coupled instanton BVP solve as a Ray remote task.
        Returns an ObjectRef. RayWorkPool will call store() once this resolves.
        """
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        if getattr(self, "_failure", None) is not None:
            raise RuntimeError("already computed or failed")
        if self._N_sample is None:
            raise RuntimeError(
                "GradientCoupledInstanton: compute() called but N_sample is not set. "
                "This object can only represent a query."
            )

        # Cheap guard -- trajectory.N_end only, no .get() (matches
        # FullInstanton's own N_end is None check).
        N_end = self._trajectory.N_end
        if N_end is None:
            raise RuntimeError("InflatonTrajectory not yet computed (N_end is None)")

        N_init_val = float(self._N_init)
        N_final_val = float(self._N_final)
        delta_Nstar_val = float(self._delta_Nstar)

        N_offset = N_end - N_init_val
        N_total = N_init_val - N_final_val + delta_Nstar_val

        if N_offset < 0:
            raise ValueError(
                f"GradientCoupledInstanton: N_init ({N_init_val}) exceeds the "
                f"trajectory's own N_end ({N_end}) -- configuration error"
            )
        if N_offset + N_total > N_end:
            raise ValueError(
                f"GradientCoupledInstanton: delta_Nstar ({delta_Nstar_val}) exceeds "
                f"N_final ({N_final_val}) -- transition would run past the end of "
                f"inflation (N_offset + N_total = {N_offset + N_total} > N_end = {N_end})"
            )

        atol = 10.0 ** self._atol.log10_tol
        rtol = 10.0 ** self._rtol.log10_tol

        self._compute_ref = _compute_gradient_coupled_instanton.remote(
            trajectory=self._trajectory,
            dm=self._diffusion_model,
            cosmo_T_CMB_Kelvin=self._cosmo.T_CMB_Kelvin,
            n_collocation_points=int(self._n_collocation_points),
            alpha=float(self._alpha_regularization),
            N_init=N_init_val,
            N_final=N_final_val,
            delta_Nstar=delta_Nstar_val,
            N_sample=self._N_sample.as_float_list() if self._N_sample else [],
            atol=atol,
            rtol=rtol,
            store_full_values=self._store_full_values,
            label=label or self._label,
        )
        return self._compute_ref

    def store(self) -> None:
        """Called on the driver by RayWorkPool after compute() resolves."""
        if self._compute_ref is None:
            raise RuntimeError("store() called but no compute() is in progress")
        data = ray.get(self._compute_ref)
        self._compute_ref = None
        self._populate_from_result(data)

    def _populate_from_result(self, data: dict) -> None:
        """Populate internal state from a pre-computed result dict.

        Called by store() after resolving the Ray future.
        """
        self._diagnostics = data.get("diagnostics")
        if data.get("failure", False):
            self._failure = True
            self._values = []
            self._profile = []
            return
        self._failure = False
        self._N_total = data["N_total"]
        self._noise_field_min = data.get("noise_field_min")
        self._noise_field_mean = data.get("noise_field_mean")
        self._noise_field_max = data.get("noise_field_max")
        self._noise_mom_min = data.get("noise_mom_min")
        self._noise_mom_mean = data.get("noise_mom_mean")
        self._noise_mom_max = data.get("noise_mom_max")

        self._profile = [
            GradientCoupledInstantonProfileValue(
                node_index=i, zeta=z, r_ratio=rr, C=c, r_phys=rp,
            )
            for i, (z, rr, c, rp) in enumerate(
                zip(data["zeta"], data["r_ratio"], data["C"], data["r_phys"])
            )
        ]

        N_sample_out = data.get("N_sample") or []
        if N_sample_out and self._N_sample is not None:
            N_by_value = {float(n): n for n in self._N_sample}
            self._values = [
                GradientCoupledInstantonValue(
                    store_id=None,
                    N=N_by_value[N_val],
                    phi=phi_row, pi=pi_row, rfield=rfield_row, rmom=rmom_row,
                )
                for N_val, phi_row, pi_row, rfield_row, rmom_row in zip(
                    N_sample_out, data["phi"], data["pi"], data["rfield"], data["rmom"],
                )
            ]
        else:
            self._values = []

    def set_store_full_values(self, flag: bool) -> None:
        """Control whether the factory persists per-sample
        GradientCoupledInstantonValue rows, and whether the worker even
        bothers interpolating them onto N_sample (see the Ray remote
        function's own Step 9 comment -- unlike FullInstanton, this
        interpolation is expensive enough to skip entirely when unwanted).
        Call before compute() is dispatched.
        """
        self._store_full_values = flag

    def zeta_C_r_at_time(self, N_query: efold_value) -> dict:
        """
        Time-resolved zeta(y,N)/C(y,N)/r_phys(y,N) reconstruction at an
        arbitrary local N (not just the stored final row), by re-running
        extract_zeta_profile + assign_scales against a (phi, pi) state
        interpolated from the stored dense GradientCoupledInstantonValue
        rows -- interpolating between adjacent efold_value rows, or exact
        if N_query coincides with one.

        Only valid when this instance was stored with store_full_values=True
        (needs the dense (phi, pi) rows); raises RuntimeError otherwise, since
        silently returning None/garbage would be worse than failing loudly.

        Cached via ExtractionCache, keyed on (self.store_id, N_query.store_id)
        -- identity-based, per the design settled in prompt 03.

        Performance: this is a new, unoptimized code path (builds
        n_collocation_points SplineWrappers from scratch on every call) --
        its cost profile has not yet been measured. Flagging here rather
        than prematurely optimizing.
        """
        if not self._values:
            raise RuntimeError(
                "GradientCoupledInstanton.zeta_C_r_at_time: this instance has no "
                "stored per-sample values (store_full_values was False, or "
                "compute() has not yet succeeded). Time-resolved reconstruction "
                "needs the dense (phi, pi) grid rows; re-run with "
                "store_full_values=True."
            )

        cache_key = (self.store_id, N_query.store_id)
        cached = self._extraction_cache.get(cache_key)
        if cached is not None:
            return cached

        from ComputeTargets.GradientCoupledInstanton.extraction import extract_zeta_profile
        from ComputeTargets.GradientCoupledInstanton.scale_assignment import assign_scales
        from Interpolation.spline_wrapper import SplineWrapper

        traj = self._trajectory.get()
        potential = traj._potential
        units = potential._units

        n_nodes = int(self._n_collocation_points)
        N_vals = np.array([v.N.N for v in self._values])
        phi_grid = np.array([v.phi for v in self._values])
        pi_grid = np.array([v.pi for v in self._values])

        # One SplineWrapper per node -- same transform convention as
        # picard.py's own phi_splines/pi_splines ('linear'; phi/pi do not
        # span a large dynamic range). Degree capped for a small number of
        # stored samples (SplineWrapper's default k=3 needs >= 4 points).
        k = min(3, max(1, len(N_vals) - 1))
        N_q = float(N_query.N)
        phi_at_Nq = np.array([
            SplineWrapper(N_vals, phi_grid[:, j], k=k)(N_q) for j in range(n_nodes)
        ])
        pi_at_Nq = np.array([
            SplineWrapper(N_vals, pi_grid[:, j], k=k)(N_q) for j in range(n_nodes)
        ])

        N_init_val = float(self._N_init)
        N_end = self._trajectory.N_end
        N_offset = N_end - N_init_val
        alpha = float(self._alpha_regularization)
        atol = 10.0 ** self._atol.log10_tol
        rtol = 10.0 ** self._rtol.log10_tol

        H_sq_nl_init = potential.H_sq(traj.phi_at(N_offset), traj.pi_at(N_offset))

        extraction = extract_zeta_profile(
            phi_at_Nq, pi_at_Nq, N_offset, N_q, traj, potential, atol, rtol, units,
        )

        H_sq_core = potential.H_sq(phi_at_Nq[-1], pi_at_Nq[-1])
        delta_s_N_q = delta_s(N_q, 0.0, H_sq_core, H_sq_nl_init, alpha)

        grid = LGLCollocationGrid(n_nodes)
        scales = assign_scales(
            extraction["zeta"], delta_s_N_q, grid, traj, N_init_val, N_offset, alpha,
            potential, units, self._cosmo, C_threshold=_C_THRESHOLD,
        )

        result = {
            "N": N_q,
            "zeta": extraction["zeta"],
            "r_ratio": scales["r_ratio"],
            "C": scales["C"],
            "r_phys": scales["r_phys"],
            "failure_mask": extraction["failure_mask"],
        }
        self._extraction_cache.set(cache_key, result)
        return result


class GradientCoupledInstantonProxy:
    """
    Lightweight reference to a persisted GradientCoupledInstanton.

    Holds N_init, N_final, delta_Nstar and the store_id so that dependent
    compute targets can route to the correct database shard without
    deserialising the full instanton data. See .claude/rules/proxy-pattern.md.
    """

    def __init__(self, model: GradientCoupledInstanton):
        self._ref: ObjectRef = ray.put(model)
        self._store_id: Optional[int] = model.store_id if model.available else None
        self._N_init: N_init = model.N_init_value
        self._N_final: N_final = model.N_final_value
        self._delta_Nstar: delta_Nstar = model.delta_Nstar

    @property
    def store_id(self) -> Optional[int]:
        return self._store_id

    @property
    def available(self) -> bool:
        return self._store_id is not None

    @property
    def N_init(self) -> N_init:
        return self._N_init

    @property
    def N_final(self) -> N_final:
        return self._N_final

    @property
    def delta_Nstar(self) -> delta_Nstar:
        return self._delta_Nstar

    @property
    def shard_key(self) -> delta_Nstar:
        return self._delta_Nstar

    def get(self) -> GradientCoupledInstanton:
        """
        Retrieve the full GradientCoupledInstanton from the Ray object store.
        The return value should be used locally and not stored, to avoid
        inadvertent serialisation of the full instanton by Ray.
        """
        return ray.get(self._ref)
