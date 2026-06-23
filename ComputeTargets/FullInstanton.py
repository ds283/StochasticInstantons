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

from datetime import datetime
from typing import List, Optional

import ray
from ray import ObjectRef

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential
from Datastore.object import DatastoreObject
from InflationConcepts.delta_Nstar import delta_Nstar
from InflationConcepts.DiffusionModel import (
    AbstractDiffusionModel,
    MasslessDecoupledDiffusion,
)
from InflationConcepts.efold_value import efold_array, efold_value
from InflationConcepts.N_final import N_final
from InflationConcepts.N_init import N_init
from MetadataConcepts.store_tag import store_tag
from MetadataConcepts.tolerance import tolerance


@ray.remote
def _compute_full_instanton(
    trajectory,             # InflatonTrajectoryProxy
    dm,                     # AbstractDiffusionModel
    phi_init: float,
    pi_init: float,
    phi_final: float,
    N_total: float,
    N_sample: list,
    atol: float,
    rtol: float,
    label: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    Solve the full MSR instanton BVP over [0, N_total] in {φ₁, φ₂, P₁, P₂}.

    Boundary conditions:
        φ₁(0) = phi_init,   φ₂(0) = pi_init
        φ₁(N_total) = phi_final,   P₂(N_total) = 0

    Algorithm: adjoint/Picard iteration with outer Newton correction on the
    Lagrange multiplier λ = P₁(N_total) to enforce the final φ condition.

    MSR action: S = ∫₀^{N_total} D₁₁(φ₁, φ₂) P₁² dN

    Returns dict with keys:
        "N_sample", "phi1", "phi2", "P1", "P2",
        "msr_action", "N_total", "failure", "diagnostics"
    """
    import time

    import numpy as np
    from scipy.integrate import solve_ivp
    from Interpolation.spline_wrapper import SplineWrapper

    compute_start = time.perf_counter()
    ode_solve_count = 0

    _lbl = label if label else f"phi_i={phi_init:.4g} phi_f={phi_final:.4g} N={N_total:.3g}"

    traj      = trajectory.get()
    potential = traj._potential

    N_GRID     = max(300, len(N_sample) * 3)
    N_grid     = np.linspace(0.0, N_total, N_GRID)
    N_grid_rev = N_grid[::-1]

    def _Dij(phi, pi):
        return dm.D_matrix(phi, pi, potential)

    # ── Initial background guess (P₁=P₂=0) ──────────────────────────────
    def bg_rhs(N, y):
        phi, pi = y
        return [
            pi,
            -(3.0 - potential.epsilon(phi, pi)) * pi
            - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
        ]

    bg_sol = solve_ivp(
        bg_rhs, (0.0, N_total), [phi_init, pi_init],
        method="RK45", t_eval=N_grid, atol=atol, rtol=rtol,
    )
    ode_solve_count += 1
    if not bg_sol.success:
        print(f"[{_lbl}] background ODE failed for initial guess")
        return {
            "failure": True, "N_total": N_total,
            "N_sample": [], "phi1": [], "phi2": [],
            "P1": [], "P2": [], "msr_action": None,
            "noise_phi1_min": None, "noise_phi1_mean": None, "noise_phi1_max": None,
            "noise_phi2_min": None, "noise_phi2_mean": None, "noise_phi2_max": None,
            "diagnostics": {
                "compute_time": time.perf_counter() - compute_start,
                "converged": False,
                "final_residual": None,
                "total_ode_solves": ode_solve_count,
                "outer_iterations": 0,
                "newton_fallback_count": 0,
                "final_lambda": None,
                "picard_iterations_per_outer": [],
                "min_picard_iterations": None,
                "max_picard_iterations": None,
                "mean_picard_iterations": None,
                "mean_time_per_picard_iteration": None,
            },
        }

    phi1_curr = bg_sol.y[0].copy()
    phi2_curr = bg_sol.y[1].copy()

    MAX_OUTER = 50
    MAX_INNER = 30
    OUTER_TOL = max(atol * 100.0, 1e-6)
    INNER_TOL = atol * 10.0

    def compute_rho(phi1_val, phi2_val):
        Mp = potential._units.PlanckMass
        return 3.0 * (Mp ** 2) * potential.H_sq(phi1_val, phi2_val)

    def picard_inner(lam, phi1_in, phi2_in):
        """Run Picard iteration for fixed λ = P₁(N_total). Returns arrays or Nones."""
        nonlocal ode_solve_count
        p1_arr = phi1_in.copy()
        p2_arr = phi2_in.copy()
        n_inner_iters = 0

        for _ in range(MAX_INNER):
            n_inner_iters += 1
            phi1_sp = SplineWrapper(N_grid, p1_arr, k=3)
            phi2_sp = SplineWrapper(N_grid, p2_arr, k=3)

            # Backward pass: terminal conds P₁(N_total)=λ, P₂(N_total)=0
            def bwd_rhs(N, y):
                P1, P2 = y
                phi1 = float(phi1_sp(N))
                phi2 = float(phi2_sp(N))
                eps  = potential.epsilon(phi1, phi2)
                Hsq  = potential.H_sq(phi1, phi2)
                return [
                    P2 * potential.d2V_dphi2(phi1) / Hsq,
                    -P1 + (3.0 - eps) * P2,
                ]

            bp = solve_ivp(
                bwd_rhs, (N_total, 0.0), [lam, 0.0],
                method="RK45", t_eval=N_grid_rev,
                atol=atol, rtol=rtol,
            )
            ode_solve_count += 1
            if not bp.success:
                return None, None, None, None, n_inner_iters

            P1_new = bp.y[0][::-1]
            P2_new = bp.y[1][::-1]
            P1_sp  = SplineWrapper(N_grid, P1_new, y_transform='sinh', k=3)
            P2_sp  = SplineWrapper(N_grid, P2_new, y_transform='sinh', k=3)

            # Forward pass with P forcing
            def fwd_rhs(N, y):
                phi1, phi2 = y
                eps = potential.epsilon(phi1, phi2)
                Hsq = potential.H_sq(phi1, phi2)
                D11, D12, D22 = _Dij(phi1, phi2)
                P1 = float(P1_sp(N))
                P2 = float(P2_sp(N))
                return [
                    phi2 + 2.0*D11*P1 + 2.0*D12*P2,
                    -(3.0-eps)*phi2 - potential.dV_dphi(phi1)/Hsq
                    + 2.0*D12*P1 + 2.0*D22*P2,
                ]

            fp = solve_ivp(
                fwd_rhs, (0.0, N_total), [phi_init, pi_init],
                method="RK45", t_eval=N_grid,
                atol=atol, rtol=rtol,
            )
            ode_solve_count += 1
            if not fp.success:
                return None, None, None, None, n_inner_iters

            phi1_new = fp.y[0]
            phi2_new = fp.y[1]
            inner_res = np.max(np.abs(phi1_new - p1_arr))
            p1_arr, p2_arr = phi1_new, phi2_new
            if inner_res < INNER_TOL:
                break

        return p1_arr, p2_arr, P1_new, P2_new, n_inner_iters

    # ── Outer Newton loop on λ ────────────────────────────────────────────
    lam = 0.0
    phi1_f = phi1_curr
    phi2_f = phi2_curr
    P1_f   = np.zeros_like(N_grid)
    P2_f   = np.zeros_like(N_grid)
    converged = False
    final_residual = None
    outer_iterations = 0
    newton_fallback_count = 0
    picard_iterations_per_outer = []
    picard_time_total = 0.0
    picard_iters_total = 0

    for outer in range(MAX_OUTER):
        outer_iterations = outer + 1
        picard_start = time.perf_counter()
        p1, p2, P1, P2, n_inner = picard_inner(lam, phi1_f, phi2_f)
        picard_time_total += time.perf_counter() - picard_start
        picard_iters_total += n_inner
        picard_iterations_per_outer.append(n_inner)
        if p1 is None:
            print(f"[{_lbl}] Picard inner failed at outer iter {outer}")
            break

        residual = p1[-1] - phi_final
        final_residual = abs(residual)
        if verbose:
            rho_T = compute_rho(p1[-1], p2[-1])
            print(
                f"[{_lbl}] outer {outer}: lambda={lam:.4g}, "
                f"phi1(T)={p1[-1]:.6g}, phi2(T)={p2[-1]:.6g}, "
                f"rho(T)={rho_T:.6g}, "
                f"res={residual:.2e}"
            )

        phi1_f, phi2_f, P1_f, P2_f = p1, p2, P1, P2

        if abs(residual) < OUTER_TOL:
            converged = True
            break

        # Finite-difference Newton step
        dlam = max(abs(lam) * 1e-4, 1e-6)
        picard_start = time.perf_counter()
        p1_p, p2_p, _, _, n_inner_p = picard_inner(lam + dlam, phi1_f, phi2_f)
        picard_time_total += time.perf_counter() - picard_start
        picard_iters_total += n_inner_p
        picard_iterations_per_outer.append(n_inner_p)
        if p1_p is not None:
            dres_dlam = (p1_p[-1] - p1[-1]) / dlam
            if abs(dres_dlam) > 1e-14:
                lam -= residual / dres_dlam
                continue
        # Fallback nudge
        newton_fallback_count += 1
        lam += (phi_final - p1[-1]) * 0.1

    diagnostics = {
        "compute_time": time.perf_counter() - compute_start,
        "converged": converged,
        "final_residual": final_residual,
        "total_ode_solves": ode_solve_count,
        "outer_iterations": outer_iterations,
        "newton_fallback_count": newton_fallback_count,
        "final_lambda": lam if converged else None,
        "picard_iterations_per_outer": picard_iterations_per_outer,
        "min_picard_iterations": min(picard_iterations_per_outer) if picard_iterations_per_outer else None,
        "max_picard_iterations": max(picard_iterations_per_outer) if picard_iterations_per_outer else None,
        "mean_picard_iterations": (
            sum(picard_iterations_per_outer) / len(picard_iterations_per_outer)
            if picard_iterations_per_outer else None
        ),
        "mean_time_per_picard_iteration": (
            picard_time_total / picard_iters_total if picard_iters_total else None
        ),
    }

    if not converged:
        print(f"[{_lbl}] outer loop did not converge "
              f"after {MAX_OUTER} iterations (target tolerance was {OUTER_TOL})")
        return {
            "failure": True, "N_total": N_total,
            "N_sample": [], "phi1": [], "phi2": [],
            "P1": [], "P2": [], "msr_action": None,
            "noise_phi1_min": None, "noise_phi1_mean": None, "noise_phi1_max": None,
            "noise_phi2_min": None, "noise_phi2_mean": None, "noise_phi2_max": None,
            "diagnostics": diagnostics,
        }

    # ── MSR action and noise amplitudes ──────────────────────────────────
    D11_arr = np.array([_Dij(phi1_f[i], phi2_f[i])[0] for i in range(len(N_grid))])
    D12_arr = np.array([_Dij(phi1_f[i], phi2_f[i])[1] for i in range(len(N_grid))])
    D22_arr = np.array([_Dij(phi1_f[i], phi2_f[i])[2] for i in range(len(N_grid))])
    msr_action = float(np.trapezoid(D11_arr * P1_f ** 2, N_grid))

    # Noise amplitude in units of Hawking standard deviations per e-fold.
    # σ_φ1 = √(2 D11) |P1| + [2 D12 / √(2 D11)] |P2|
    # σ_φ2 = [2 D12 / √(2 D22)] |P1| + √(2 D22) |P2|
    # None if the corresponding diagonal element is zero anywhere.
    abs_P1 = np.abs(P1_f)
    abs_P2 = np.abs(P2_f)

    if np.any(D11_arr == 0.0):
        noise_phi1_min = noise_phi1_mean = noise_phi1_max = None
    else:
        sqrt_2D11 = np.sqrt(2.0 * D11_arr)
        sigma_phi1 = sqrt_2D11 * abs_P1 + (2.0 * D12_arr / sqrt_2D11) * abs_P2
        noise_phi1_min  = float(sigma_phi1.min())
        noise_phi1_mean = float(sigma_phi1.mean())
        noise_phi1_max  = float(sigma_phi1.max())

    if np.any(D22_arr == 0.0):
        noise_phi2_min = noise_phi2_mean = noise_phi2_max = None
    else:
        sqrt_2D22 = np.sqrt(2.0 * D22_arr)
        sigma_phi2 = (2.0 * D12_arr / sqrt_2D22) * abs_P1 + sqrt_2D22 * abs_P2
        noise_phi2_min  = float(sigma_phi2.min())
        noise_phi2_mean = float(sigma_phi2.mean())
        noise_phi2_max  = float(sigma_phi2.max())

    # ── Output sample ─────────────────────────────────────────────────────
    N_out = sorted([n for n in N_sample if 0.0 <= n <= N_total]) or [0.0, N_total]
    N_a   = np.array(N_out)

    def interp_phi(arr):
        return SplineWrapper(N_grid, arr, k=3)(N_a).tolist()

    def interp_P(arr):
        return SplineWrapper(N_grid, arr, y_transform='sinh', k=3)(N_a).tolist()

    return {
        "failure":    False,
        "N_total":    N_total,
        "N_sample":   N_out,
        "phi1":       interp_phi(phi1_f),
        "phi2":       interp_phi(phi2_f),
        "P1":         interp_P(P1_f),
        "P2":         interp_P(P2_f),
        "msr_action": msr_action,
        "noise_phi1_min":  noise_phi1_min,
        "noise_phi1_mean": noise_phi1_mean,
        "noise_phi1_max":  noise_phi1_max,
        "noise_phi2_min":  noise_phi2_min,
        "noise_phi2_mean": noise_phi2_mean,
        "noise_phi2_max":  noise_phi2_max,
        "diagnostics": diagnostics,
    }


class FullInstantonValue(DatastoreObject):
    """
    MSR instanton field values {φ₁, φ₂, P₁, P₂} at a single e-folding sample point.

    φ₁ is the primary field (the physical trajectory).
    φ₂ is the 'quantum' field (its integral over the instanton gives the action).
    P₁ and P₂ are the response fields conjugate to φ₁ and φ₂ respectively.
    P₂ vanishes at the final time by the Schwinger-Keldysh boundary condition.
    """

    def __init__(
        self,
        store_id: Optional[int],
        N: efold_value,
        phi1: float,
        phi2: float,
        P1: float,
        P2: float,
    ):
        DatastoreObject.__init__(self, store_id)
        self._N = N
        self._phi1 = phi1
        self._phi2 = phi2
        self._P1 = P1
        self._P2 = P2

    @property
    def N(self) -> efold_value:
        return self._N

    @property
    def phi1(self) -> float:
        return self._phi1

    @property
    def phi2(self) -> float:
        return self._phi2

    @property
    def P1(self) -> float:
        return self._P1

    @property
    def P2(self) -> float:
        return self._P2


class FullInstanton(DatastoreObject):
    """
    The full MSR stochastic instanton in {φ₁, φ₂, P₁, P₂} state space.

    Parameterised by a background InflatonTrajectoryProxy, an N_init and an
    N_final value (measured backwards from end of inflation), an excess
    transition time delta_Nstar, and ODE tolerances.

    Plain Python class on the driver. Numerical work is dispatched via the
    _compute_full_instanton Ray remote function.
    """

    def __init__(
        self,
        store_id: Optional[int],
        trajectory,  # InflatonTrajectoryProxy
        N_init: N_init,
        N_final: N_final,
        delta_Nstar: delta_Nstar,
        N_sample: Optional[efold_array],
        atol: tolerance,
        rtol: tolerance,
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
        self._N_sample: Optional[efold_array] = N_sample
        self._atol: tolerance = atol
        self._rtol: tolerance = rtol
        self._diffusion_model: AbstractDiffusionModel = diffusion_model or MasslessDecoupledDiffusion()
        self._label: Optional[str] = label
        self._tags: List[store_tag] = tags or []
        self._msr_action: Optional[float] = None
        self._noise_phi1_min:  Optional[float] = None
        self._noise_phi1_mean: Optional[float] = None
        self._noise_phi1_max:  Optional[float] = None
        self._noise_phi2_min:  Optional[float] = None
        self._noise_phi2_mean: Optional[float] = None
        self._noise_phi2_max:  Optional[float] = None
        self._values: List[FullInstantonValue] = []
        self._compute_ref: Optional[ObjectRef] = None
        self._store_full_values: bool = True

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
        """Return the N_init parameter (e-folds before end of inflation at instanton start)."""
        return self._N_init

    @property
    def N_final_value(self) -> N_final:
        """Return the N_final parameter (e-folds before end of inflation at instanton end)."""
        return self._N_final

    @property
    def delta_Nstar(self) -> delta_Nstar:
        """Return the delta_Nstar shard key."""
        return self._delta_Nstar

    @property
    def msr_action(self) -> Optional[float]:
        """MSR saddle-point action; None until compute() succeeds."""
        return self._msr_action

    @property
    def noise_phi1_min(self) -> Optional[float]:
        return self._noise_phi1_min

    @property
    def noise_phi1_mean(self) -> Optional[float]:
        return self._noise_phi1_mean

    @property
    def noise_phi1_max(self) -> Optional[float]:
        return self._noise_phi1_max

    @property
    def noise_phi2_min(self) -> Optional[float]:
        return self._noise_phi2_min

    @property
    def noise_phi2_mean(self) -> Optional[float]:
        return self._noise_phi2_mean

    @property
    def noise_phi2_max(self) -> Optional[float]:
        return self._noise_phi2_max

    @property
    def diagnostics(self) -> Optional[dict]:
        """Outer Newton / inner Picard iteration diagnostics; None until compute() resolves."""
        return getattr(self, "_diagnostics", None)

    @property
    def values(self) -> List[FullInstantonValue]:
        """Sampled state-vector values; empty until compute() succeeds."""
        return self._values

    def noise_profile(
        self,
        diffusion_model: Optional[AbstractDiffusionModel] = None,
    ) -> Optional[List[dict]]:
        """
        Compute the pointwise noise amplitude in units of the Hawking standard
        deviation per e-fold at each stored sample point.

        Uses the diffusion model supplied to this call, or falls back to
        self._diffusion_model if none is given.  The caller is responsible for
        ensuring the diffusion model matches the one used during the solve;
        this cannot be verified until the diffusion model is promoted to a
        first-class datastore object.

        Returns a list of dicts, one per value in self._values, each with keys:
            "N"          : float  — e-fold coordinate (instanton time)
            "sigma_phi1" : float  — noise amplitude in φ1 channel (dimensionless)
            "sigma_phi2" : Optional[float]  — noise amplitude in φ2 channel,
                           or None if D22 = 0 at this point

        Returns None if self._values is empty (object not populated, or failed).

        Physical definition
        -------------------
        For a general diffusion matrix (D11, D12, D22):

            σ_φ1 = √(2 D11) |P1| + [2 D12 / √(2 D11)] |P2|
            σ_φ2 = [2 D12 / √(2 D22)] |P1| + √(2 D22) |P2|

        Both are dimensionless.  σ_φ2 = None when D22 = 0 (e.g.
        MasslessDecoupledDiffusion).
        """
        if not self._values:
            return None

        dm = diffusion_model if diffusion_model is not None else self._diffusion_model
        traj = self._trajectory.get()
        potential = traj._potential

        result = []
        for v in self._values:
            phi1 = v.phi1
            phi2 = v.phi2
            P1   = v.P1
            P2   = v.P2

            D11, D12, D22 = dm.D_matrix(phi1, phi2, potential)

            abs_P1 = abs(P1)
            abs_P2 = abs(P2)

            if D11 > 0.0:
                sqrt_2D11 = (2.0 * D11) ** 0.5
                sigma_phi1 = sqrt_2D11 * abs_P1 + (2.0 * D12 / sqrt_2D11) * abs_P2
            else:
                sigma_phi1 = None

            if D22 > 0.0:
                sqrt_2D22 = (2.0 * D22) ** 0.5
                sigma_phi2 = (2.0 * D12 / sqrt_2D22) * abs_P1 + sqrt_2D22 * abs_P2
            else:
                sigma_phi2 = None

            result.append({
                "N":          v.N.N,
                "sigma_phi1": sigma_phi1,
                "sigma_phi2": sigma_phi2,
            })

        return result

    def noise_profile_arrays(
        self,
        diffusion_model: Optional[AbstractDiffusionModel] = None,
    ) -> Optional[dict]:
        """
        Convenience wrapper around noise_profile() that returns numpy arrays
        rather than a list of dicts, suitable for direct use in matplotlib or
        further numerical work.

        Returns a dict with keys:
            "N"          : np.ndarray, shape (n_samples,)
            "sigma_phi1" : np.ndarray, shape (n_samples,), dtype float64
                           NaN where sigma_phi1 is None
            "sigma_phi2" : np.ndarray, shape (n_samples,), dtype float64
                           NaN where sigma_phi2 is None

        Returns None if noise_profile() returns None.
        """
        import numpy as np

        profile = self.noise_profile(diffusion_model=diffusion_model)
        if profile is None:
            return None

        N_arr  = np.array([p["N"] for p in profile], dtype=float)
        s1_arr = np.array(
            [p["sigma_phi1"] if p["sigma_phi1"] is not None else float("nan")
             for p in profile],
            dtype=float,
        )
        s2_arr = np.array(
            [p["sigma_phi2"] if p["sigma_phi2"] is not None else float("nan")
             for p in profile],
            dtype=float,
        )
        return {"N": N_arr, "sigma_phi1": s1_arr, "sigma_phi2": s2_arr}

    def compute(self, label: Optional[str] = None, verbose: bool = False) -> ObjectRef:
        """
        Dispatch the MSR instanton BVP solve as a Ray remote task.
        Returns an ObjectRef. RayWorkPool will call store() once this resolves.
        """
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        if getattr(self, "_failure", None) is not None:
            raise RuntimeError("already computed or failed")
        if self._N_sample is None:
            raise RuntimeError(
                "FullInstanton: compute() called but N_sample is not set. "
                "This object can only represent a query."
            )

        N_end = self._trajectory.N_end
        if N_end is None:
            raise RuntimeError("InflatonTrajectory not yet computed (N_end is None)")

        traj      = self._trajectory.get()
        phi_init  = traj.phi_at(N_end - float(self._N_init))
        phi_final = traj.phi_at(N_end - float(self._N_final))
        pi_init   = traj.pi_at(N_end - float(self._N_init))
        N_total   = (float(self._N_init) - float(self._N_final)) + float(self._delta_Nstar)

        atol = 10.0 ** self._atol.log10_tol
        rtol = 10.0 ** self._rtol.log10_tol

        self._compute_ref = _compute_full_instanton.remote(
            trajectory=self._trajectory,
            dm=self._diffusion_model,
            phi_init=phi_init,
            pi_init=pi_init,
            phi_final=phi_final,
            N_total=N_total,
            N_sample=self._N_sample.as_float_list() if self._N_sample else [],
            atol=atol,
            rtol=rtol,
            label=label,
            verbose=verbose,
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

        Called by store() after resolving the Ray future, and directly by
        the pipeline store-handler when results arrive from compute_pipeline
        without a compute() having been dispatched on this object.
        """
        self._diagnostics = data.get("diagnostics")
        if data.get("failure", False):
            self._failure = True
            self._values = []
            return
        self._failure = False
        self._msr_action = data["msr_action"]
        self._noise_phi1_min  = data.get("noise_phi1_min")
        self._noise_phi1_mean = data.get("noise_phi1_mean")
        self._noise_phi1_max  = data.get("noise_phi1_max")
        self._noise_phi2_min  = data.get("noise_phi2_min")
        self._noise_phi2_mean = data.get("noise_phi2_mean")
        self._noise_phi2_max  = data.get("noise_phi2_max")
        self._N_total = data["N_total"]
        self._values = [
            FullInstantonValue(store_id=None, N=N_obj, phi1=phi1, phi2=phi2, P1=P1, P2=P2)
            for N_obj, phi1, phi2, P1, P2 in zip(
                self._N_sample, data["phi1"], data["phi2"], data["P1"], data["P2"]
            )
        ]

    def set_store_full_values(self, flag: bool) -> None:
        """Control whether the factory persists per-sample FullInstantonValue rows.

        Call after construction, before pool.object_store(). When False, the factory
        writes only scalar summary columns (N_total, msr_action, diagnostics_json) and
        skips the per-sample child rows. The in-memory _values list is always populated
        after compute() regardless of this flag.
        """
        self._store_full_values = flag


class FullInstantonProxy:
    """
    Lightweight reference to a persisted FullInstanton.

    Holds N_init, N_final, delta_Nstar and the store_id so that dependent
    compute targets can route to the correct database shard without deserialising
    the full instanton data.
    """

    def __init__(self, model: FullInstanton):
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

    def get(self) -> FullInstanton:
        """
        Retrieve the full FullInstanton from the Ray object store.
        The return value should be used locally and not stored, to avoid
        inadvertent serialisation of the full instanton by Ray.
        """
        return ray.get(self._ref)
