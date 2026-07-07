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
from functools import total_ordering
from typing import Optional

from Datastore import DatastoreObject


@total_ordering
class alpha_regularization(DatastoreObject):
    """
    The coordinate regularization parameter alpha used by
    Numerics/OnionCoordinate.py's delta_s(), for the onion-model
    GradientCoupledInstanton solve.

    This is a pure numerical-implementation (solver-convergence) parameter,
    not a physical input -- it plays the same shared/replicated role that
    tolerance and delta_Nstar already play for FullInstanton.

    Named alpha_regularization rather than bare `alpha` because `alpha` is
    used constantly as a plain float parameter name throughout the
    onion-model code (delta_s, forward_rhs, scale_assignment, etc.); a class
    named identically would be an easy source of confusion between "the
    persisted concept object" and "the plain float value" at call sites.

    alpha == 0 is rejected: it makes Delta_s(N_init) = 0, which is a
    singularity of the onion coordinate map implemented by
    Numerics/OnionCoordinate.py's delta_s().
    """

    def __init__(
        self,
        store_id: int,
        alpha: float,
        timestamp: Optional[datetime] = None,
    ):
        if store_id is None:
            raise ValueError("Store ID cannot be None")
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)

        if alpha <= 0:
            raise ValueError(
                f"alpha_regularization: alpha must be > 0 "
                f"(alpha == 0 is a singularity of Delta_s at N_init), got {alpha!r}"
            )

        self._alpha: float = float(alpha)

    def __float__(self) -> float:
        return self._alpha

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError

        return self.store_id == other.store_id

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError

        return self._alpha < other._alpha

    def __hash__(self):
        return (type(self).__name__, self.store_id).__hash__()
