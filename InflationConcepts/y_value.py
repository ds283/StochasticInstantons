from datetime import datetime
from functools import total_ordering
from typing import Iterable, Optional, Self

from Datastore import DatastoreObject
from config.defaults import DEFAULT_FLOAT_PRECISION


@total_ordering
class y_value(DatastoreObject):
    """
    Represents a value of the radial shell coordinate y along the onion model,
    used as a sample-grid point.

    y is defined to be 0 at the outer edge of the overdense region and 1 at the
    core. Multiple instantons — and, downstream, multiple compaction-function
    evaluations of the same instanton at different times — may share the same
    y_array sample grid; persisting y_value objects in a shared database table
    makes it possible to identify shared sample points exactly by store_id
    rather than relying on floating-point equality comparisons.
    """

    def __init__(self, store_id: int, y: float, timestamp: Optional[datetime] = None):
        if store_id is None:
            raise ValueError("Store ID cannot be None")
        if y < -DEFAULT_FLOAT_PRECISION or y > 1.0 + DEFAULT_FLOAT_PRECISION:
            raise ValueError(f"y={y} is out of the physically-valid range [0, 1]")
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)
        self.y = y

    def __float__(self):
        return float(self.y)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError
        return self.store_id == other.store_id

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError
        # ascending: y=0 (outer edge) is smaller, y=1 (core) is larger.
        # This is a geometric ordering (outer-to-inner), not a temporal one.
        return self.y < other.y

    def __hash__(self):
        return ("y_value", self.store_id).__hash__()


class y_array:
    """
    An ordered, deduplicated collection of y_value sample points, sorted in
    ascending order of y (smallest y first, i.e. outer edge first).
    """

    def __init__(self, y_values: Iterable[y_value]):
        # ascending order; convert to set first to deduplicate
        self._y_array = sorted(set(y_values), key=lambda x: x.y)

    def __iter__(self):
        for y in self._y_array:
            yield y

    def __getitem__(self, key):
        return self._y_array[key]

    def __len__(self):
        return len(self._y_array)

    def __eq__(self, other):
        return not self.__ne__(other)

    def __ne__(self, other):
        if len(self._y_array) != len(other._y_array):
            return True
        if any(ya != yb for ya, yb in zip(self._y_array, other._y_array)):
            return True
        return False

    def __add__(self, other):
        full_set = set(self._y_array)
        full_set.update(set(other._y_array))
        return y_array(full_set)

    def as_float_list(self) -> list[float]:
        return [float(y) for y in self._y_array]

    @property
    def min(self) -> y_value:
        """Smallest y value (outer edge)."""
        return self._y_array[0]

    @property
    def max(self) -> y_value:
        """Largest y value (core)."""
        return self._y_array[-1]


def check_ysample(A, B):
    """
    Raise RuntimeError if two y_array instances (or objects carrying a
    y_sample attribute) do not represent the same sample grid.
    """
    A_sample: y_array = A if isinstance(A, y_array) else A.y_sample
    B_sample: y_array = B if isinstance(B, y_array) else B.y_sample
    if A_sample != B_sample:
        raise RuntimeError("y sample grids are not equal")
