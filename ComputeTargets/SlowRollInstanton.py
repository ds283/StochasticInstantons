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

from typing import Optional, List

import ray
from ray import ObjectRef

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential
from Datastore.object import DatastoreObject
from InflationConcepts.DiffusionModel import AbstractDiffusionModel, MasslessDecoupledDiffusion
from InflationConcepts.efold_value import efold_value, efold_array
from InflationConcepts.delta_Nstar import delta_Nstar
from InflationConcepts.N_init import N_init
from InflationConcepts.N_final import N_final
from MetadataConcepts.store_tag import store_tag
from MetadataConcepts.tolerance import tolerance


@ray.remote
def _compute_slow_roll_instanton(
    trajectory,             # InflatonTrajectoryProxy
    phi_init: float,
    phi_final: float,
    N_total: float,
    N_sample: list,
    atol: float,
    rtol: float,
    label: Optional[str] = None,
) -> dict:
    """
    Solve the slow-roll instanton BVP over [0, N_total] in {φ, P₁}.

    Slow-roll instanton ODEs:
        dφ/dN  = -V′(φ)/(3H²) + 2 D₁₁(φ) P₁
        dP₁/dN = V″(φ)/(3H²) P₁

    where H² ≈ V(φ)/(3 Mp²) and D₁₁ is evaluated at π=0.

    Boundary conditions: φ(0) = phi_init,  φ(N_total) = phi_final.
    Free parameter: P₁(0), found by brentq on φ(N_total; P₁(0)) - phi_final = 0.

    MSR action: S = ∫₀^{N_total} D₁₁(φ) P₁² dN

    Returns dict with keys:
        "N_sample", "phi", "P1", "msr_action", "N_total", "failure"
    """
    import numpy as np
    from scipy.integrate import solve_ivp
    from scipy.optimize import brentq
    from scipy.interpolate import make_interp_spline

    traj      = trajectory.get()
    potential = traj._potential
    dm        = traj._diffusion_model

    N_GRID = max(300, len(N_sample) * 3)
    N_grid = np.linspace(0.0, N_total, N_GRID)

    # π=0 in slow-roll limit: kinetic term negligible in H² and D₁₁
    def H_sq_sr(phi):
        return potential.H_sq(phi, 0.0)

    def D11_sr(phi):
        return dm.D_matrix(phi, 0.0, potential)[0]

    def rhs(N, y):
        phi, P1 = y
        Hsq = H_sq_sr(phi)
        D11 = D11_sr(phi)
        dphi = -potential.dV_dphi(phi) / (3.0 * Hsq) + 2.0 * D11 * P1
        dP1  = (potential.d2V_dphi2(phi) / (3.0 * Hsq)) * P1
        return [dphi, dP1]

    def shoot(P1_0):
        sol = solve_ivp(rhs, (0.0, N_total), [phi_init, P1_0],
                        method="RK45", t_eval=[N_total],
                        atol=atol, rtol=rtol)
        if not sol.success:
            return np.nan
        return float(sol.y[0, -1]) - phi_final

    if label:
        print(f"[{label}] SR instanton: phi_init={phi_init:.6g}, "
              f"phi_final={phi_final:.6g}, N_total={N_total:.4g}")

    # Physically motivated initial bracket
    D11_0    = D11_sr(phi_init)
    P1_scale = abs(phi_final - phi_init) / max(2.0 * D11_0 * N_total, 1e-30)
    P1_lo, P1_hi = -10.0 * P1_scale, 10.0 * P1_scale

    f_lo, f_hi = shoot(P1_lo), shoot(P1_hi)

    for _ in range(12):
        if not (np.isnan(f_lo) or np.isnan(f_hi)) and f_lo * f_hi < 0:
            break
        P1_lo *= 2.0; P1_hi *= 2.0
        f_lo, f_hi = shoot(P1_lo), shoot(P1_hi)

    if np.isnan(f_lo) or np.isnan(f_hi) or f_lo * f_hi >= 0:
        if label:
            print(f"[{label}] SR instanton: bracketing failed "
                  f"(f_lo={f_lo:.2e}, f_hi={f_hi:.2e})")
        return {"failure": True, "N_total": N_total,
                "N_sample": [], "phi": [], "P1": [], "msr_action": None}

    try:
        P1_star = brentq(shoot, P1_lo, P1_hi,
                         xtol=atol, rtol=rtol, maxiter=200)
    except ValueError as exc:
        if label:
            print(f"[{label}] SR instanton: brentq failed: {exc}")
        return {"failure": True, "N_total": N_total,
                "N_sample": [], "phi": [], "P1": [], "msr_action": None}

    if label:
        print(f"[{label}] SR instanton converged: P₁(0) = {P1_star:.4g}")

    sol = solve_ivp(rhs, (0.0, N_total), [phi_init, P1_star],
                    method="RK45", t_eval=N_grid, atol=atol, rtol=rtol)
    if not sol.success:
        return {"failure": True, "N_total": N_total,
                "N_sample": [], "phi": [], "P1": [], "msr_action": None}

    phi_arr = sol.y[0]
    P1_arr  = sol.y[1]

    D11_arr    = np.array([D11_sr(phi_arr[i]) for i in range(len(N_grid))])
    msr_action = float(np.trapezoid(D11_arr * P1_arr ** 2, N_grid))

    N_out  = sorted([n for n in N_sample if 0.0 <= n <= N_total]) or [0.0, N_total]
    N_a    = np.array(N_out)
    phi_sp = make_interp_spline(N_grid, phi_arr, k=3)
    P1_sp  = make_interp_spline(N_grid, P1_arr,  k=3)

    return {
        "failure":    False,
        "N_total":    N_total,
        "N_sample":   N_out,
        "phi":        phi_sp(N_a).tolist(),
        "P1":         P1_sp(N_a).tolist(),
        "msr_action": msr_action,
    }


class SlowRollInstantonValue(DatastoreObject):
    """
    Slow-roll instanton field values {φ, P₁} at a single e-folding sample point.

    In the slow-roll approximation π = dφ/dN is algebraically determined by
    the slow-roll relation π ≈ -V′(φ)/(3H²), and the response field P₂
    conjugate to π vanishes automatically at the final time.
    """

    def __init__(
        self,
        store_id: Optional[int],
        N: efold_value,
        phi: float,
        P1: float,
    ):
        DatastoreObject.__init__(self, store_id)
        self._N = N
        self._phi = phi
        self._P1 = P1

    @property
    def N(self) -> efold_value:
        return self._N

    @property
    def phi(self) -> float:
        return self._phi

    @property
    def P1(self) -> float:
        return self._P1


class SlowRollInstanton(DatastoreObject):
    """
    The slow-roll MSR stochastic instanton in {φ, P₁} state space.

    The slow-roll approximation eliminates φ₂ = π algebraically via
    π ≈ -V′(φ)/(3H²), and the Schwinger-Keldysh condition on P₂ is
    automatically satisfied. This leaves a simpler BVP with only P₁(0)
    as the free parameter.

    Parameterised by a background InflatonTrajectoryProxy, an N_init and an
    N_final value (measured backwards from end of inflation), an excess
    transition time delta_Nstar, and ODE tolerances.

    Plain Python class on the driver. Numerical work is dispatched via the
    _compute_slow_roll_instanton Ray remote function.
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
    ):
        DatastoreObject.__init__(self, store_id)
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
        self._values: List[SlowRollInstantonValue] = []
        self._compute_ref: Optional[ObjectRef] = None

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
        """MSR saddle-point action in the slow-roll approximation; None until compute() succeeds."""
        return self._msr_action

    @property
    def values(self) -> List[SlowRollInstantonValue]:
        """Sampled {φ, P₁} values; empty until compute() succeeds."""
        return self._values

    def compute(self, label: Optional[str] = None) -> ObjectRef:
        """
        Dispatch the slow-roll instanton BVP solve as a Ray remote task.
        Returns an ObjectRef. RayWorkPool will call store() once this resolves.
        """
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        if getattr(self, "_failure", None) is not None:
            raise RuntimeError("already computed or failed")
        if self._N_sample is None:
            raise RuntimeError(
                "SlowRollInstanton: compute() called but N_sample is not set. "
                "This object can only represent a query."
            )

        N_end = self._trajectory.N_end
        if N_end is None:
            raise RuntimeError("InflatonTrajectory not yet computed (N_end is None)")

        traj      = self._trajectory.get()
        phi_init  = traj.phi_at(N_end - float(self._N_init))
        phi_final = traj.phi_at(N_end - float(self._N_final))
        N_total   = (float(self._N_init) - float(self._N_final)) + float(self._delta_Nstar)

        atol = 10.0 ** self._atol.log10_tol
        rtol = 10.0 ** self._rtol.log10_tol

        self._compute_ref = _compute_slow_roll_instanton.remote(
            trajectory=self._trajectory,
            phi_init=phi_init,
            phi_final=phi_final,
            N_total=N_total,
            N_sample=self._N_sample.as_float_list() if self._N_sample else [],
            atol=atol,
            rtol=rtol,
            label=label,
        )
        return self._compute_ref

    def store(self):
        """
        Called on the driver by RayWorkPool after compute() resolves.
        Reads the result dict and populates internal state.
        """
        if self._compute_ref is None:
            raise RuntimeError("store() called but no compute() is in progress")
        data = ray.get(self._compute_ref)
        self._compute_ref = None
        if data.get("failure", False):
            self._failure = True
            self._values = []
            return
        self._failure = False
        self._msr_action = data["msr_action"]
        self._N_total = data["N_total"]
        self._values = [
            SlowRollInstantonValue(store_id=None, N=N_obj, phi=phi, P1=P1)
            for N_obj, phi, P1 in zip(self._N_sample, data["phi"], data["P1"])
        ]


class SlowRollInstantonProxy:
    """
    Lightweight reference to a persisted SlowRollInstanton.

    Holds N_init, N_final, delta_Nstar and the store_id so that dependent
    compute targets can route to the correct database shard without deserialising
    the full instanton data.
    """

    def __init__(self, model: SlowRollInstanton):
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

    def get(self) -> SlowRollInstanton:
        """
        Retrieve the full SlowRollInstanton from the Ray object store.
        The return value should be used locally and not stored, to avoid
        inadvertent serialisation of the full instanton by Ray.
        """
        return ray.get(self._ref)
