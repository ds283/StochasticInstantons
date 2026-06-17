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

from typing import Optional

from Datastore.object import DatastoreObject


class CosmologicalParams(DatastoreObject):
    """
    Persistable wrapper around a cosmological parameter bundle (Planck2013/2015/2018).

    Usage:
        params = Planck2018()
        cosmo  = ray.get(pool.object_get("CosmologicalParams", payload={"params": params}))

    After pool.object_get(), cosmo.store_id is set and cosmo.available is True.
    Subsequent calls with the same parameter set name return the same store_id (idempotent).
    """

    def __init__(self, store_id: Optional[int], params):
        DatastoreObject.__init__(self, store_id)
        self._params = params

    @property
    def available(self) -> bool:
        return self._my_id is not None

    @property
    def name(self) -> str:
        return self._params.name

    @property
    def omega_cc(self) -> float:
        return self._params.omega_cc

    @property
    def omega_m(self) -> float:
        return self._params.omega_m

    @property
    def h(self) -> float:
        return self._params.h

    @property
    def f_baryon(self) -> float:
        return self._params.f_baryon

    @property
    def T_CMB_Kelvin(self) -> float:
        return self._params.T_CMB_Kelvin

    @property
    def Neff(self) -> float:
        return self._params.Neff
