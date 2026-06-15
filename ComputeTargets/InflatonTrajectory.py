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


@ray.remote
class InflatonTrajectory(DatastoreObject):
    """
    Background inflationary trajectory from initial condition {φ₀, π₀} at N = 0
    to the end of inflation at N = N_end.

    Decorated with @ray.remote so it can be dispatched as a compute actor.
    When the datastore factory creates instances locally it uses
    InflatonTrajectory.__ray_actor_class__(…) to bypass the actor wrapper.
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

    # available() and n_fields() are defined as regular methods rather than
    # properties so they can be invoked via .remote() on a Ray actor handle.

    def available(self) -> bool:
        """True if this trajectory has been persisted to the datastore."""
        return self._my_id is not None

    def n_fields(self) -> int:
        """Number of scalar fields; always 1 for a single-field inflaton."""
        return 1

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

    @property
    def failure(self) -> bool:
        return getattr(self, "_failure", False)

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

    def compute(self) -> bool:
        """
        Integrate the noiseless single-field inflationary equations from {φ₀, π₀}
        at N = 0 until ε = 1 (end of inflation), where ε = π²/(2 Mp²).

        The integration uses scipy.integrate.solve_ivp with the following ODE:

            dφ/dN = π
            dπ/dN = -3π - V′(φ)/H²

        where H² = [V(φ) + ½ π²] / (3 Mp²)  (Friedmann equation, Mp = 1 convention).

        A terminal event is registered for ε = 1 (i.e. π² = 2 Mp²), which halts
        the integration when inflation ends.

        Solver fallback chain: RK45 → DOP853 → Radau → BDF → LSODA.
        If all solvers fail, sets self._failure = True and returns False.
        On success, populates self._N_end and self._values, and returns True.

        This method raises NotImplementedError and will be implemented in Prompt 5.
        """
        raise NotImplementedError(
            "InflatonTrajectory.compute() is not yet implemented. "
            "See the docstring for the algorithm specification."
        )


class InflatonTrajectoryProxy:
    """
    Lightweight reference to a persisted InflatonTrajectory.

    Holds N_end and the store_id so that instanton compute targets can determine
    the inflationary endpoint and look up the trajectory without deserialising
    the full trajectory data.
    """

    def __init__(self, model: InflatonTrajectory):
        self._ref: ObjectRef = ray.put(model)
        # model.available() is a method (not a property) on the Ray actor class,
        # so it must be called with parentheses.
        self._store_id: Optional[int] = model.store_id if model.available() else None
        self._N_end: Optional[float] = model.N_end
        self._n_fields: int = model.n_fields()

    @property
    def store_id(self) -> int:
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
