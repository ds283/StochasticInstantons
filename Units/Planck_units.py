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

from math import pi, sqrt

from Units.base import UnitsLike


class Planck_units(UnitsLike):
    def __init__(self):
        UnitsLike.__init__(self, "Planck units")

    # numerical values obtained from https://en.wikipedia.org/wiki/Planck_units,
    # assuming c = hbar = k_B = 1
    # That leaves a single dimensionful unit in which we measure mass, length, energy, time
    # We can choose this to be whatever we like; often it is GeV, but here we are choosing it
    # to be Mpc instead.

    PlanckMass = 1.0
    sqrt_NewtonG = sqrt(1.0 / (8.0 * pi)) / PlanckMass

    Metre = sqrt_NewtonG / 1.616255e-35
    Kilometre = 1000 * Metre
    Mpc = 3.08567758e22 * Metre

    Kilogram = 1.0 / (2.176434e-8 * sqrt_NewtonG)
    Second = sqrt_NewtonG / 5.391247e-44
    Kelvin = 1.0 / (1.416784e32 * sqrt_NewtonG)

    eV = PlanckMass / 2.436e27
    # keV, MeV, GeV are set by base UnitsLike

    # c should be unity for consistency, since we have assumed c = hbar = k_B = 1 in writing some of the equations above
    c = 299792458 * Metre / Second
