from datetime import datetime
from functools import total_ordering
from typing import Iterable, Optional, Self

from Datastore import DatastoreObject
from config.defaults import DEFAULT_FLOAT_PRECISION


@total_ordering
class efold_value(DatastoreObject):
    """
    Represents a value of the e-folding coordinate N along the inflationary
    trajectory, used as a sample-grid point.

    N is defined to be zero at the start of the integration and increases toward
    the end of inflation. Multiple compute targets (InflatonTrajectory,
    FullInstanton, SlowRollInstanton) may share the same efold_array sample grid;
    persisting efold_value objects in a shared database table makes it possible to
    identify shared sample points exactly by store_id rather than relying on
    floating-point equality comparisons.
    """

    def __init__(self, store_id: int, N: float, timestamp: Optional[datetime] = None):
        if store_id is None:
            raise ValueError("Store ID cannot be None")
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)
        self.N = N

    def __float__(self):
        return float(self.N)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.store_id == other.store_id

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.N < other.N          # ascending: earlier times are smaller

    def __hash__(self):
        return ("efold_value", self.store_id).__hash__()


class efold_array:
    """
    An ordered, deduplicated collection of efold_value sample points, sorted in
    ascending order of N (smallest N first, i.e. earliest time first).
    """

    def __init__(self, N_array: Iterable[efold_value]):
        # ascending order; convert to set first to deduplicate
        self._N_array = sorted(set(N_array), key=lambda x: x.N)

    def __iter__(self):
        for n in self._N_array:
            yield n

    def __getitem__(self, key):
        return self._N_array[key]

    def __len__(self):
        return len(self._N_array)

    def __eq__(self, other):
        return not self.__ne__(other)

    def __ne__(self, other):
        if len(self._N_array) != len(other._N_array):
            return True
        if any(na != nb for na, nb in zip(self._N_array, other._N_array)):
            return True
        return False

    def __add__(self, other):
        full_set = set(self._N_array)
        full_set.update(set(other._N_array))
        return efold_array(full_set)

    def as_float_list(self) -> list[float]:
        return [float(n) for n in self._N_array]

    @property
    def min(self) -> efold_value:
        """Smallest N value (earliest time)."""
        return self._N_array[0]

    @property
    def max(self) -> efold_value:
        """Largest N value (latest time, closest to end of inflation)."""
        return self._N_array[-1]


def check_Nsample(A, B):
    """
    Raise RuntimeError if two efold_array instances (or objects carrying an
    N_sample attribute) do not represent the same sample grid.
    """
    A_sample: efold_array = A if isinstance(A, efold_array) else A.N_sample
    B_sample: efold_array = B if isinstance(B, efold_array) else B.N_sample
    if A_sample != B_sample:
        raise RuntimeError("e-fold sample grids are not equal")
