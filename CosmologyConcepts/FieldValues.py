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

from typing import Union

from CosmologyConcepts import DimensionfulQuantity


class phi_value(DimensionfulQuantity):
    default_unit = "PlanckMass"

    def __init__(self, store_id: int, value: float):
        super().__init__(store_id, value, "phi_value")


class pi_value(DimensionfulQuantity):
    default_unit = "PlanckMass"

    def __init__(self, store_id: int, value: float):
        super().__init__(store_id, value, "pi_value")


FieldLike = Union[phi_value, pi_value, float]


def GetFieldValue(value: FieldLike) -> float:
    if isinstance(value, phi_value):
        return value.as_float

    if isinstance(value, pi_value):
        return value.as_float

    if isinstance(value, float):
        return value

    raise ValueError("Expected a FieldLike object")
