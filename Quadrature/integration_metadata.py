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

from collections import namedtuple

from Datastore import DatastoreObject


class IntegrationSolver(DatastoreObject):
    def __init__(self, store_id: int, label: str, stepping: int):
        """
        Construct a datastore-backed object representing a named
        integration strategy (such as "solve_ivp+RK45")
        :param store_id: unique Datastore id. Should not be None

        :param label:
        """
        DatastoreObject.__init__(self, store_id)

        self._label = label
        self._stepping = stepping if stepping >= 0 else 0

    @property
    def label(self) -> str:
        return self._label

    @property
    def stepping(self) -> int:
        return self._stepping


IntegrationData = namedtuple(
    "IntegrationData",
    [
        "compute_time",
        "compute_steps",
        "mean_RHS_time",
        "max_RHS_time",
        "min_RHS_time",
        "RHS_evaluations",
    ],
)
