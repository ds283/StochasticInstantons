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

# taken from: table 2, table 5 of http://arxiv.org/abs/1301.5839
class Planck2013:
    name = "Planck2013 best-fit Planck+WP"

    omega_cc = 0.6817
    omega_m = 1.0 - omega_cc
    h = 0.6704
    f_baryon = 0.15471  # = Omegab h^2 / (Omegab h^2 + Omegac h^2) = 0.022032 / (0.12038 + 0.022032)
    T_CMB_Kelvin = 2.7255
    Neff = 3.046  # Standard Model value


# taken from: table 4 of http://arxiv.org/abs/1502.01589
class Planck2015:
    name = "Planck2015 68% central values TT,TE,EE+lowP+lensing+ext"

    omega_cc = 0.6911
    omega_m = 1.0 - omega_cc
    h = 0.6774
    f_baryon = 0.15804  # = Omegab h^2 / (Omegab h^2 + Omegac h^2) = 0.02230 / (0.1188 + 0.02230)
    T_CMB_Kelvin = 2.7255
    Neff = 3.046  # Standard Model value


# taken from: table 2 of http://arxiv.org/abs/1807.06209v4
class Planck2018:
    name = "Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO"

    omega_cc = 0.6889
    omega_m = 1.0 - omega_cc
    h = 0.6766
    f_baryon = 0.15817  # = Omegab h^2 / (Omegab h^2 + Omegac h^2) = 0.02242 / (0.11933 + 0.02242)
    T_CMB_Kelvin = 2.7255
    Neff = 3.046  # Standard Model value
