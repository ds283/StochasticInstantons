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

from CosmologyConcepts.FieldValues import phi_value, pi_value
from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential
from Datastore.object import DatastoreObject
from InflationConcepts.DiffusionModel import AbstractDiffusionModel, MasslessDecoupledDiffusion
from InflationConcepts.efold_value import efold_value
from MetadataConcepts.store_tag import store_tag
from MetadataConcepts.tolerance import tolerance


@ray.remote
def _compute_inflaton_trajectory(
    phi0_value: float,
    pi0_value: float,
    potential: AbstractPotential,
    samples_per_N: float,
    atol: float,
    rtol: float,
    label: Optional[str] = None,
) -> dict:
    """
    Integrate the noiseless inflationary background trajectory from
    {φ₀, π₀} at N=0 until ε(φ, π) = 1 (end of inflation).

    ODE system:
        dφ/dN = π
        dπ/dN = -(3 - ε) π - V′(φ)/H²

    Terminal event: potential.epsilon(φ, π) - 1 = 0, ε increasing (+1 direction).
    Solver fallback chain: RK45 → DOP853 → Radau → BDF → LSODA.

    The sample grid is built internally from `samples_per_N` once N_end is known,
    as linspace(0, N_end, max(2, ceil(N_end * samples_per_N)), endpoint=True).
    This guarantees both 0 and N_end are members of the grid.

    Returns dict with keys:
        "N_end":    float — e-folding coordinate at end of inflation
        "N_sample": list[float] — N values sampled within [0, N_end]
        "phi":      list[float]
        "pi":       list[float]
        "failure":  bool
    """
    import math
    import numpy as np
    from scipy.integrate import solve_ivp

    # Guard: already past end of inflation?
    if potential.epsilon(phi0_value, pi0_value) >= 1.0:
        if label:
            print(f"[{label}] epsilon >= 1 at initial conditions")
        return {"failure": True, "N_end": None, "N_sample": [], "phi": [], "pi": []}

    def rhs(N, y):
        phi, pi = y
        Hsq = potential.H_sq(phi, pi)
        eps = potential.epsilon(phi, pi)
        return [pi, -(3.0 - eps) * pi - potential.dV_dphi(phi) / Hsq]

    def end_of_inflation(N, y):
        return potential.epsilon(y[0], y[1]) - 1.0

    end_of_inflation.terminal  = True
    end_of_inflation.direction = +1

    y0     = [phi0_value, pi0_value]
    N_span = (0.0, 1000.0)

    if label:
        print(f"[{label}] integrating background trajectory: "
              f"phi0={phi0_value:.6g}, pi0={pi0_value:.6g}")

    SOLVERS = ["RK45", "DOP853", "Radau", "BDF", "LSODA"]
    sol = None
    for solver in SOLVERS:
        try:
            candidate = solve_ivp(
                rhs, N_span, y0,
                method=solver,
                events=[end_of_inflation],
                dense_output=True,
                atol=atol, rtol=rtol,
            )
            if candidate.success or candidate.status == 1:
                sol = candidate
                if label:
                    print(f"[{label}] solver {solver} succeeded "
                          f"(status={candidate.status})")
                break
            if label:
                print(f"[{label}] solver {solver} "
                      f"status={candidate.status}: {candidate.message}")
        except Exception as exc:
            if label:
                print(f"[{label}] solver {solver} raised: {exc}")

    if sol is None:
        return {"failure": True, "N_end": None, "N_sample": [], "phi": [], "pi": []}

    if len(sol.t_events[0]) == 0:
        if label:
            print(f"[{label}] inflation did not end within N_span=1000")
        return {"failure": True, "N_end": None, "N_sample": [], "phi": [], "pi": []}

    N_end = float(sol.t_events[0][0])
    if label:
        print(f"[{label}] N_end = {N_end:.6g}")

    # Build sample grid now that N_end is known. linspace with endpoint=True
    # guarantees both 0.0 and N_end are members of the grid.
    n_points = max(2, math.ceil(N_end * samples_per_N))
    N_out = np.linspace(0.0, N_end, n_points, endpoint=True).tolist()

    vals = sol.sol(np.array(N_out))
    return {
        "failure":  False,
        "N_end":    N_end,
        "N_sample": N_out,
        "phi":      vals[0].tolist(),
        "pi":       vals[1].tolist(),
    }


class InflatonTrajectoryValue(DatastoreObject):
    """
    Field values {φ, π} sampled at a single e-folding coordinate N on the
    background inflationary trajectory.

    π = dφ/dN is the field velocity.
    """

    def __init__(
        self,
        store_id: Optional[int],
        N: efold_value,
        phi: float,
        pi: float,
    ):
        DatastoreObject.__init__(self, store_id)
        self._N: efold_value = N
        self._phi: float = phi
        self._pi: float = pi

    @property
    def N(self) -> efold_value:
        return self._N

    @property
    def phi(self) -> float:
        """Field value φ at this sample point."""
        return self._phi

    @property
    def pi(self) -> float:
        """Field velocity π = dφ/dN at this sample point."""
        return self._pi


class InflatonTrajectory(DatastoreObject):
    """
    Background inflationary trajectory from initial condition {φ₀, π₀} at N = 0
    to the end of inflation at N = N_end.

    Plain Python class on the driver. Numerical work is dispatched via the
    _compute_inflaton_trajectory Ray remote function.
    """

    def __init__(
        self,
        store_id: Optional[int],
        phi0: phi_value,
        pi0: pi_value,
        potential: AbstractPotential,
        samples_per_N: Optional[float],
        atol: tolerance,
        rtol: tolerance,
        diffusion_model: Optional[AbstractDiffusionModel] = None,
        label: Optional[str] = None,
        tags: Optional[List[store_tag]] = None,
    ):
        DatastoreObject.__init__(self, store_id)
        self._phi0: phi_value = phi0
        self._pi0: pi_value = pi0
        self._potential: AbstractPotential = potential
        self._samples_per_N: Optional[float] = samples_per_N
        self._atol: tolerance = atol
        self._rtol: tolerance = rtol
        self._diffusion_model: AbstractDiffusionModel = diffusion_model or MasslessDecoupledDiffusion()
        self._label: Optional[str] = label
        self._tags: List[store_tag] = tags or []
        self._N_end: Optional[float] = None
        self._values: List[InflatonTrajectoryValue] = []
        self._compute_ref: Optional[ObjectRef] = None

    @property
    def available(self) -> bool:
        """True if this trajectory has been persisted to the datastore."""
        return self._my_id is not None

    @property
    def n_fields(self) -> int:
        """Number of scalar fields; always 1 for a single-field inflaton."""
        return 1

    @property
    def failure(self) -> bool:
        return getattr(self, "_failure", False)

    @property
    def N_end(self) -> Optional[float]:
        """E-folding coordinate at end of inflation; None until compute() succeeds."""
        return self._N_end

    @property
    def phi0(self) -> phi_value:
        return self._phi0

    @property
    def pi0(self) -> pi_value:
        return self._pi0

    @property
    def potential(self) -> AbstractPotential:
        return self._potential

    @property
    def atol(self) -> tolerance:
        return self._atol

    @property
    def rtol(self) -> tolerance:
        return self._rtol

    @property
    def values(self) -> List[InflatonTrajectoryValue]:
        return self._values

    def phi_at(self, N: float) -> float:
        """Interpolate φ at arbitrary N using a cubic spline built from _values."""
        if not self._values:
            raise RuntimeError(
                "InflatonTrajectory: phi_at() called but _values is empty. "
                "Has the trajectory been computed and fully populated?"
            )
        if not hasattr(self, "_phi_spline"):
            import numpy as np
            from scipy.interpolate import make_interp_spline
            Ns = np.array([v.N.N for v in self._values])
            phis = np.array([v.phi for v in self._values])
            self._phi_spline = make_interp_spline(Ns, phis)
        return float(self._phi_spline(N))

    def pi_at(self, N: float) -> float:
        """Interpolate π at arbitrary N using a cubic spline built from _values."""
        if not self._values:
            raise RuntimeError(
                "InflatonTrajectory: pi_at() called but _values is empty. "
                "Has the trajectory been computed and fully populated?"
            )
        if not hasattr(self, "_pi_spline"):
            import numpy as np
            from scipy.interpolate import make_interp_spline
            Ns = np.array([v.N.N for v in self._values])
            pis = np.array([v.pi for v in self._values])
            self._pi_spline = make_interp_spline(Ns, pis)
        return float(self._pi_spline(N))

    def compute(self, label: Optional[str] = None) -> ObjectRef:
        """
        Dispatch the background trajectory integration as a Ray remote task.
        Returns an ObjectRef. RayWorkPool will call the store_handler once this resolves.
        """
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        if getattr(self, "_failure", None) is not None:
            raise RuntimeError("already computed or failed")
        if self._samples_per_N is None:
            raise RuntimeError(
                "InflatonTrajectory: compute() called but samples_per_N is not set. "
                "This object can only represent a query."
            )

        atol = 10.0 ** self._atol.log10_tol
        rtol = 10.0 ** self._rtol.log10_tol

        self._compute_ref = _compute_inflaton_trajectory.remote(
            phi0_value=float(self._phi0),
            pi0_value=float(self._pi0),
            potential=self._potential,
            samples_per_N=self._samples_per_N,
            atol=atol,
            rtol=rtol,
            label=label,
        )
        return self._compute_ref

    def store(self):
        """
        Resolve the Ray future and stash the raw float arrays.

        This is called by the store_handler in RayWorkPool. The store_handler
        is responsible for the subsequent step: minting efold_value objects via
        the pool and assembling self._values from them, so that the object is
        in the same fully-populated state as after a database load.
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
        self._N_end = data["N_end"]
        # Stash raw floats as a handoff for the store_handler, which will
        # convert these to typed efold_value objects and populate self._values.
        self._raw_sample = {
            "N_sample": data["N_sample"],
            "phi":      data["phi"],
            "pi":       data["pi"],
        }


class InflatonTrajectoryProxy:
    """
    Lightweight reference to a persisted InflatonTrajectory.

    Holds N_end and the store_id so that instanton compute targets can determine
    the inflationary endpoint and look up the trajectory without deserialising
    the full trajectory data.
    """

    def __init__(self, model: InflatonTrajectory):
        self._ref: ObjectRef = ray.put(model)
        self._store_id: Optional[int] = model.store_id if model.available else None
        self._N_end: Optional[float] = model.N_end
        self._n_fields: int = model.n_fields

    @property
    def store_id(self) -> Optional[int]:
        return self._store_id

    @property
    def available(self) -> bool:
        return self._store_id is not None

    @property
    def N_end(self) -> Optional[float]:
        """E-folding coordinate at end of inflation. None if not yet computed."""
        return self._N_end

    @property
    def n_fields(self) -> int:
        return self._n_fields

    def get(self) -> InflatonTrajectory:
        """
        Retrieve the full InflatonTrajectory from the Ray object store.
        The return value should be used locally and not stored, to avoid
        inadvertent serialisation of the full trajectory by Ray.
        """
        return ray.get(self._ref)
