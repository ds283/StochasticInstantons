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

from abc import ABC, abstractmethod


class UnitsLike(ABC):
    def __init__(self, name: str):
        self._name = name
        self._name_hash = hash(name)

    def __eq__(self, other):
        return self._name_hash == other._name_hash

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def system_name(self):
        return self._name

    @property
    @abstractmethod
    def Metre(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def Kilometre(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def Kilogram(self):
        raise NotImplementedError

    @property
    def Gram(self):
        return self.Kilogram / 1e3

    @property
    @abstractmethod
    def Second(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def Kelvin(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def PlanckMass(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def eV(self):
        raise NotImplementedError

    @property
    def keV(self):
        return 1e3 * self.eV

    @property
    def MeV(self):
        return 1e6 * self.eV

    @property
    def GeV(self):
        return 1e9 * self.eV

    @property
    @abstractmethod
    def c(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def Mpc(self):
        raise NotImplementedError


def check_units(A, B):
    """
    Check that objects A and B are defined with the same units.
    Assumes they both provide a .units property that returns a UnitsLike object
    :param A:
    :param B:
    :return:
    """
    if A.units != B.units:
        raise RuntimeError("Units used for wavenumber k and cosmology are not equal")
