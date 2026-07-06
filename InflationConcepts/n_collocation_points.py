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

import numpy as np

from Datastore import DatastoreObject


@total_ordering
class n_collocation_points(DatastoreObject):
    """
    The number of Legendre-Gauss-Lobatto collocation points used to build the
    LGL grid fed to Numerics/LGLCollocation.py's LGLCollocationGrid, for the
    onion-model GradientCoupledInstanton solve.

    This is a pure numerical-implementation (solver-convergence) parameter,
    not a physical input -- it plays the same shared/replicated role that
    tolerance and delta_Nstar already play for FullInstanton.

    Deliberately has no `.n_max` (degree) property: the n_collocation_points
    - 1 subtraction happens in exactly one place in the whole codebase,
    LGLCollocationGrid itself, and must not be duplicated here.
    """

    def __init__(
        self,
        store_id: int,
        n_collocation_points: int,
        timestamp: Optional[datetime] = None,
    ):
        if store_id is None:
            raise ValueError("Store ID cannot be None")
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)

        if not isinstance(n_collocation_points, (int, np.integer)) or isinstance(
            n_collocation_points, bool
        ):
            raise ValueError(
                f"n_collocation_points: n_collocation_points must be an integer, "
                f"got {n_collocation_points!r} of type "
                f"{type(n_collocation_points).__name__}"
            )
        if n_collocation_points < 2:
            raise ValueError(
                f"n_collocation_points: n_collocation_points must be >= 2, "
                f"got {n_collocation_points}"
            )

        self._n_collocation_points: int = int(n_collocation_points)

    def __int__(self) -> int:
        return self._n_collocation_points

    def __float__(self) -> float:
        return float(self._n_collocation_points)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError

        return self.store_id == other.store_id

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError

        return self._n_collocation_points < other._n_collocation_points

    def __hash__(self):
        return (type(self).__name__, self.store_id).__hash__()
