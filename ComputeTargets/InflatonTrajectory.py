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
from InflationConcepts.efold_value import efold_value, efold_array
from MetadataConcepts.store_tag import store_tag
from MetadataConcepts.tolerance import tolerance


@ray.remote
def _compute_inflaton_trajectory(
    phi0_value: float,
    pi0_value: float,
    potential: AbstractPotential,
    atol: float,
    rtol: float,
    label: Optional[str] = None,
) -> dict:
    """
    Integrate the noiseless inflationary background trajectory from {φ₀, π₀}
    at N = 0 until ε = π²/(2 Mp²) = 1 (end of inflation).
    ODE system (Mp = 1 units):
        dφ/dN = π
        dπ/dN = -3π - V′(φ)/H²
    where H² = (V(φ) + ½π²) / 3.
    Terminal event: ε(N) = π²/2 - 1 = 0, direction = +1 (ε increasing through 1).
    Solver fallback chain: RK45 → DOP853 → Radau → BDF → LSODA.
    Returns a dict with keys:
        "N_end":    float — e-folding number at end of inflation
        "N_sample": list[float] — N values of the sampled trajectory
        "phi":      list[float] — φ values at sample points
        "pi":       list[float] — π values at sample points
        "failure":  bool — True if integration failed
    NOT YET IMPLEMENTED. Will be implemented in Prompt 6.
    """
    raise NotImplementedError(
        "_compute_inflaton_trajectory is not yet implemented. "
        "See the docstring for the algorithm specification."
    )


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
        N_sample: Optional[efold_array],
        atol: tolerance,
        rtol: tolerance,
        label: Optional[str] = None,
        tags: Optional[List[store_tag]] = None,
    ):
        DatastoreObject.__init__(self, store_id)
        self._phi0: phi_value = phi0
        self._pi0: pi_value = pi0
        self._potential: AbstractPotential = potential
        self._N_sample: Optional[efold_array] = N_sample
        self._atol: tolerance = atol
        self._rtol: tolerance = rtol
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
            raise RuntimeError("InflatonTrajectory has not been computed yet")
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
            raise RuntimeError("InflatonTrajectory has not been computed yet")
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
        Returns an ObjectRef. RayWorkPool will call store() once this resolves.
        """
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        self._compute_ref = _compute_inflaton_trajectory.remote(
            phi0_value=float(self._phi0),
            pi0_value=float(self._pi0),
            potential=self._potential,
            atol=self._atol.tol,
            rtol=self._rtol.tol,
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
        self._N_end = data["N_end"]
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
