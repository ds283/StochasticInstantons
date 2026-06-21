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
from typing import Iterable, Optional

from Datastore import DatastoreObject


@total_ordering
class DimensionfulQuantity(DatastoreObject):
    # default_unit is a class attribute; it is set for all instances of the class,
    # not on an instance-by-instance basis.
    # It should be overridden by derived classes to fix the default
    # storage unit
    default_unit: Optional[str] = None

    def __init__(self, store_id: int, value: float, name: str, timestamp: Optional[datetime] = None):
        """
        Represents a value of beta that can be used in the conformal coupling
        """
        if store_id is None:
            raise ValueError("Store ID cannot be None")
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)

        if not isinstance(value, float):
            raise ValueError("value must be a float")

        self.value: float = value
        self.name: str = name

    def __float__(self):
        """
        Cast to float. Returns numerical value.
        """
        return self.value

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError

        return self.store_id == other.store_id

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError

        return self.value < other.value

    def __hash__(self):
        return (self.name, self.store_id).__hash__()

    @property
    def as_float(self) -> float:
        return self.value


class DimensionfulQuantityArray:
    def __init__(self, value_array: Iterable[DimensionfulQuantity]):
        """
        Represents an array of dimensionless quantity objects.
        """
        # store array, sorted into ascending order
        self._value_array = sorted(set(value_array), key=lambda x: x.value)

    def __iter__(self):
        for v in self._value_array:
            yield v

    def __getitem__(self, key):
        return self._value_array[key]

    def __len__(self):
        return len(self._value_array)

    def __eq__(self, other):
        return not self.__ne__(other)

    def __ne__(self, other):
        if len(self._value_array) != len(other._value_array):
            return True

        if any(va != vb for va, vb in zip(self._value_array, other._value_array)):
            return True

        return False

    def __add__(self, other):
        full_array = set(self._value_array)
        full_array.update(set(other._value_array))
        return DimensionfulQuantityArray(full_array)

    def as_float_list(self) -> list[float]:
        return [v.as_float for v in self._value_array]

    @property
    def max(self) -> DimensionfulQuantity:
        return self._value_array[-1]

    @property
    def min(self) -> DimensionfulQuantity:
        return self._value_array[0]
