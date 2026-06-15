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
from InflationConcepts.efold_value import efold_value, efold_array
from InflationConcepts.delta_Nstar import delta_Nstar
from InflationConcepts.N_efolds import N_efolds
from MetadataConcepts.store_tag import store_tag
from MetadataConcepts.tolerance import tolerance


@ray.remote
def _compute_slow_roll_instanton(
    trajectory_ref: ObjectRef,
    phi_init: float,
    phi_final: float,
    N_total: float,
    potential: AbstractPotential,
    atol: float,
    rtol: float,
    label: Optional[str] = None,
) -> dict:
    """
    Solve the slow-roll instanton BVP in {φ, P₁} state space over [0, N_total].
    Boundary conditions:
        φ(0) = phi_init
        φ(N_total) = phi_final
    Algorithm: 1-dimensional root-find (scipy.optimize.brentq) on P₁(0).
    Returns a dict with keys:
        "N_sample":   list[float]
        "phi":        list[float]
        "P1":         list[float]
        "msr_action": float
        "N_total":    float
        "failure":    bool
    NOT YET IMPLEMENTED. Will be implemented in Prompt 6.
    """
    raise NotImplementedError(
        "_compute_slow_roll_instanton is not yet implemented. "
        "See the docstring for the algorithm specification."
    )


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

    Parameterised by a background InflatonTrajectoryProxy, two N_efolds values
    (N_init, N_final — measured backwards from end of inflation), an excess
    transition time delta_Nstar, and ODE tolerances.

    Plain Python class on the driver. Numerical work is dispatched via the
    _compute_slow_roll_instanton Ray remote function.
    """

    def __init__(
        self,
        store_id: Optional[int],
        trajectory,  # InflatonTrajectoryProxy
        N_init: N_efolds,
        N_final: N_efolds,
        delta_Nstar: delta_Nstar,
        N_sample: Optional[efold_array],
        atol: tolerance,
        rtol: tolerance,
        label: Optional[str] = None,
        tags: Optional[List[store_tag]] = None,
    ):
        DatastoreObject.__init__(self, store_id)
        self._trajectory = trajectory
        self._N_init: N_efolds = N_init
        self._N_final: N_efolds = N_final
        self._delta_Nstar: delta_Nstar = delta_Nstar
        self._N_sample: Optional[efold_array] = N_sample
        self._atol: tolerance = atol
        self._rtol: tolerance = rtol
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
    def N_init_value(self) -> N_efolds:
        """Return the N_init parameter (e-folds before end of inflation at instanton start)."""
        return self._N_init

    @property
    def N_final_value(self) -> N_efolds:
        """Return the N_final parameter (e-folds before end of inflation at instanton end)."""
        return self._N_final

    @property
    def delta_Nstar_value(self) -> delta_Nstar:
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

        Algorithm: 1-D root-find on P₁(0) using scipy.optimize.brentq.

        The slow-roll approximation eliminates φ₂ = π algebraically:
            π(N) ≈ -V′(φ)/(3H²(φ))
        and the response field P₂ vanishes automatically by the Schwinger-Keldysh
        condition in the slow-roll limit.

        This method is not yet implemented. It will be implemented in Prompt 6.
        """
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        traj = self._trajectory.get()
        N_end = self._trajectory.N_end
        if N_end is None:
            raise RuntimeError(
                "InflatonTrajectory has not been computed yet (N_end is None)"
            )
        phi_init  = traj.phi_at(N_end - float(self._N_init))
        phi_final = traj.phi_at(N_end - float(self._N_final))
        N_total   = (float(self._N_init) - float(self._N_final)) + float(self._delta_Nstar)
        self._compute_ref = _compute_slow_roll_instanton.remote(
            trajectory_ref=self._trajectory._ref,
            phi_init=phi_init,
            phi_final=phi_final,
            N_total=N_total,
            potential=traj._potential,
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
        self._msr_action = data["msr_action"]
        self._N_total = data["N_total"]
        self._raw_sample = {
            "N_sample": data["N_sample"],
            "phi":      data["phi"],
            "P1":       data["P1"],
        }


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
        self._N_init: N_efolds = model.N_init_value
        self._N_final: N_efolds = model.N_final_value
        self._delta_Nstar: delta_Nstar = model.delta_Nstar_value

    @property
    def store_id(self) -> Optional[int]:
        return self._store_id

    @property
    def available(self) -> bool:
        return self._store_id is not None

    @property
    def N_init(self) -> N_efolds:
        return self._N_init

    @property
    def N_final(self) -> N_efolds:
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
