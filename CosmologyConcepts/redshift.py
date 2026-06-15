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

from functools import total_ordering
from typing import Iterable, Self

from Datastore import DatastoreObject
from config.defaults import DEFAULT_FLOAT_PRECISION


@total_ordering
class redshift(DatastoreObject):
    def __init__(
        self,
        store_id: int,
        z: float,
    ):
        """
        Represents a redshift,
        e.g., used to sample a transfer function or power spectrum
        :param store_id: unique Datastore id. Should not be None
        :param z: redshift value
        """
        if store_id is None:
            raise ValueError("Store ID cannot be None")
        DatastoreObject.__init__(self, store_id)

        self.z = z

    def __float__(self):
        """
        Cast to float. Returns numerical value.
        :return:
        """
        return float(self.z)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError

        return self.store_id == other.store_id

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise NotImplementedError

        return self.z < other.z

    def __hash__(self):
        return ("redshift", self.store_id).__hash__()


class redshift_array:
    def __init__(self, z_array: Iterable[redshift]):
        """
        Represents an array of redshifts
        :param store_id: unique Datastore id. Should not be None
        :param z_array: array of redshift value
        """
        # store array, sorted in descending order of redshift;
        # the conversion to set ensure that we remove any duplicates
        self._z_array = sorted(set(z_array), key=lambda x: x.z, reverse=True)

    def __iter__(self):
        for z in self._z_array:
            yield z

    def __getitem__(self, key):
        return self._z_array[key]

    def __len__(self):
        return len(self._z_array)

    def __eq__(self, other):
        return not self.__ne__(other)

    def __ne__(self, other):
        if len(self._z_array) != len(other._z_array):
            return True

        if any(za != zb for za, zb in zip(self._z_array, other._z_array)):
            return True

        return False

    def __add__(self, other):
        full_set = set(self._z_array)
        full_set.update(set(other._z_array))
        return redshift_array(full_set)

    def as_float_list(self) -> list[float]:
        return [float(z) for z in self._z_array]

    @property
    def max(self) -> redshift:
        return self._z_array[0]

    @property
    def min(self) -> redshift:
        return self._z_array[-1]

    def truncate(self, z_limit, keep: str = "lower") -> Self:
        if keep == "lower":
            return self._truncate_lower(z_limit)
        if keep == "higher":
            return self._truncate_higher(z_limit)
        if keep == "lower-strict":
            return self._truncate_lower_strict(z_limit)
        if keep == "higher-strict":
            return self._truncate_higher_strict(z_limit)
        if keep == "lower-include":
            return self._truncate_lower_include(z_limit)
        if keep == "higher-include":
            return self._truncate_higher_include(z_limit)

        raise ValueError(f'Unknown truncation mode "{keep}')

    def _truncate_lower(self, max_z) -> Self:
        if isinstance(max_z, redshift):
            return redshift_array(
                z_array=[
                    z
                    for z in self._z_array
                    if z.z <= max_z.z + DEFAULT_FLOAT_PRECISION
                    or z.store_id == max_z.store_id
                ]
            )

        return redshift_array(
            z_array=[z for z in self._z_array if z.z <= max_z + DEFAULT_FLOAT_PRECISION]
        )

    def _truncate_higher(self, min_z) -> Self:
        if isinstance(min_z, redshift):
            return redshift_array(
                z_array=[
                    z
                    for z in self._z_array
                    if z.z >= min_z.z - DEFAULT_FLOAT_PRECISION
                    or z.store_id == min_z.store_id
                ]
            )

        return redshift_array(
            z_array=[z for z in self._z_array if z.z >= min_z - DEFAULT_FLOAT_PRECISION]
        )

    def _truncate_lower_strict(self, max_z) -> Self:
        if isinstance(max_z, redshift):
            return redshift_array(
                z_array=[
                    z
                    for z in self._z_array
                    if z.z < max_z.z - DEFAULT_FLOAT_PRECISION
                    and z.store_id != max_z.store_id
                ]
            )

        return redshift_array(
            z_array=[z for z in self._z_array if z.z < max_z - DEFAULT_FLOAT_PRECISION]
        )

    def _truncate_higher_strict(self, min_z) -> Self:
        if isinstance(min_z, redshift):
            return redshift_array(
                z_array=[
                    z
                    for z in self._z_array
                    if z.z > min_z.z + DEFAULT_FLOAT_PRECISION
                    and z.store_id != min_z.store_id
                ]
            )

        return redshift_array(
            z_array=[z for z in self._z_array if z.z > min_z + DEFAULT_FLOAT_PRECISION]
        )

    def _truncate_lower_include(self, max_z) -> Self:
        include_array = []
        included_endpoint = False
        for z in self._z_array:
            if isinstance(max_z, redshift):
                if (
                    z.z <= max_z.z + DEFAULT_FLOAT_PRECISION
                    or z.store_id == max_z.store_id
                ):
                    include_array.append(z)
                elif not included_endpoint:
                    include_array.append(z)
                    included_endpoint = True
            else:
                if z.z <= max_z + DEFAULT_FLOAT_PRECISION:
                    include_array.append(z)
                elif not included_endpoint:
                    include_array.append(z)
                    included_endpoint = True

        return redshift_array(include_array)

    def _truncate_higher_include(self, max_z) -> Self:
        include_array = []
        included_endpoint = False
        for z in self._z_array:
            if isinstance(max_z, redshift):
                if (
                    z.z >= max_z.z - DEFAULT_FLOAT_PRECISION
                    or z.store_id == max_z.store_id
                ):
                    include_array.append(z)
                elif not included_endpoint:
                    include_array.append(z)
                    included_endpoint = True
            else:
                if z.z >= max_z - DEFAULT_FLOAT_PRECISION:
                    include_array.append(z)
                elif not included_endpoint:
                    include_array.append(z)
                    included_endpoint = True

        return redshift_array(include_array)

    def winnow(self, sparseness: int) -> Self:
        sparseness = int(sparseness)
        if sparseness <= 0:
            raise ValueError("sparseness must be greater than zero")
        return redshift_array(z_array=self._z_array[::-sparseness])


def check_zsample(A, B):
    A_sample: redshift_array = A if isinstance(A, redshift_array) else A.z_sample
    B_sample: redshift_array = B if isinstance(B, redshift_array) else B.z_sample

    if A_sample != B_sample:
        raise RuntimeError("Redshift sample grids are not equal")
