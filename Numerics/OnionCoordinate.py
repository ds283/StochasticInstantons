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

"""
Onion coordinate utilities for the gradient-coupled instanton model.

Standalone, physics-adjacent module: every function here takes
already-evaluated scalars (or arrays) and returns a plain number/array --
no dependence on AbstractPotential, InflatonTrajectory, DatastoreObject, or
anything under Datastore/. Field/momentum reconstruction and the calls into
AbstractPotential that produce H_sq_local, H_sq_nl_init, epsilon_core belong
to the caller.

By design, no function here computes an absolute-valued r_H(N) or r_out --
every quantity is expressed as a ratio relative to r_out, or as the
dimensionless Delta_s(N) = ln(r_out/r_H(N)) itself. The one place an
absolute radius enters the pipeline (r_phys_out) is computed elsewhere, by
the existing Leach-Liddle machinery, in a later prompt.
"""

import numpy as np


def delta_s(
    N: float,
    N_init: float,
    H_sq_local: float,
    H_sq_nl_init: float,
    alpha: float,
) -> float:
    """
    Delta_s(N) = ln(1+alpha) + (N - N_init) + 0.5*ln(H_sq_local(N) / H_sq_nl_init).

    H_sq_local is used two ways by callers of this function: (1) the
    core's own H^2, evaluated at the top collocation node (y=+1) at
    whatever N the RHS is being evaluated at, giving the coordinate-
    defining Delta_s(N) used to build the y-domain itself; or (2) an
    arbitrary node's own local H^2, giving Delta_s_loc(y,N), needed
    elsewhere for the (aH)_loc-based prefactor in the gradient term. This
    function's formula is identical either way -- only the value passed
    in differs.

    H_sq_nl_init is a single fixed reference, computed once elsewhere from
    the noiseless trajectory at N_init.

    Raises ValueError if alpha < 0. alpha == 0 is a valid, well-defined
    input (giving Delta_s(N_init) = 0 exactly); no guard against it here.
    """
    if alpha < 0:
        raise ValueError(f"delta_s: alpha must be >= 0, got {alpha!r}")

    return (
        np.log(1.0 + alpha)
        + (N - N_init)
        + 0.5 * np.log(H_sq_local / H_sq_nl_init)
    )


def delta_s_derivative(epsilon_core: float) -> float:
    """d(Delta_s)/dN = 1 - epsilon_core(N)."""
    return 1.0 - epsilon_core


def advection_coefficient(y, delta_s_N: float, epsilon_core: float):
    """A(y,N) = (y+1)/Delta_s(N) * (1 - epsilon_core(N)). y may be scalar or ndarray."""
    return (np.asarray(y) + 1.0) / delta_s_N * (1.0 - epsilon_core)


def measure(y, delta_s_N: float):
    """mu(y,N) = exp(-1.5 * Delta_s(N) * y). y may be scalar or ndarray."""
    return np.exp(-1.5 * delta_s_N * np.asarray(y))


def comoving_radius_ratio(y, delta_s_N: float):
    """r(y,N)/r_out = exp[-(y+1) * Delta_s(N) / 2]. y may be scalar or ndarray."""
    return np.exp(-(np.asarray(y) + 1.0) * delta_s_N / 2.0)
