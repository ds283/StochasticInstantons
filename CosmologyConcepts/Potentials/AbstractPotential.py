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

from Datastore import DatastoreObject


class AbstractPotential(DatastoreObject, ABC):
    def __init__(self, store_id: int):
        DatastoreObject.__init__(self, store_id)

    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def type_id(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def bounce_region_level1_boundary(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def bounce_region_level2_boundary(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def bounce_region_level1_max_step(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def bounce_region_level2_max_step(self) -> float:
        raise NotImplementedError

    @property
    @abstractmethod
    def hard_reflection_point(self) -> float:
        raise NotImplementedError

    # in addition, each potential should implement functions
    # log_V(), d_logV_dphi(), and d2_logV_dphi2()
    # or V(), d_V_dphi(), and d2_V_dphi2()
    # or both
