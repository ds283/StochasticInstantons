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
Shared compaction-function scalar helpers.

Standalone, physics-free numerical core: every function here takes
already-evaluated arrays/scalars and returns plain numbers/arrays -- no
dependence on DatastoreObject, Ray, or AbstractPotential (mirrors
Numerics/OnionCoordinate.py's style). Factored out of
ComputeTargets/CompactionFunction.py so that
ComputeTargets/GradientCoupledInstanton/ can reuse the same C_bar
integration, C_min classification, and PBH-mass formula without
re-deriving them.
"""

from math import exp
from typing import Optional, Tuple

import numpy as np

from Interpolation.spline_wrapper import SplineWrapper


def classify_radii(r_v, C_v, C_threshold: float):
    """
    Compute r_max and r_peak from C(r) sample arrays.

    r_max: outermost r where C >= C_threshold, scanning inward.
           r_max_at_grid_edge=True when C_v[-1] >= C_threshold
           (peak not resolved within grid).
           r_max=None if C nowhere reaches C_threshold.

    r_peak: r at which C is maximised (nanargmax).
            r_peak_at_grid_edge=True when argmax == len-1
            (peak not resolved within grid).

    Returns (r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge).
    """
    r_max = None
    r_max_at_grid_edge = False
    for i in range(len(r_v) - 1, -1, -1):
        if C_v[i] >= C_threshold:
            r_max = float(r_v[i])
            r_max_at_grid_edge = i == len(r_v) - 1
            break

    peak_idx = int(np.nanargmax(C_v))
    r_peak = float(r_v[peak_idx])
    r_peak_at_grid_edge = peak_idx == len(r_v) - 1

    return r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge


def densify_zeta_profile(r_v, zeta_v) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build a log-uniform dense grid over [r_v[0], r_v[-1]] and evaluate
    zeta(r) and dzeta/dr on it, pinning the left-endpoint derivative to
    the exact physical boundary value.

    Strategy:
      1. Fit a spline to (r_v, zeta_v) in log-r space for smoothing.
      2. Evaluate on a log-uniform dense grid (geomspace) -- essential
         because r spans many decades; linspace concentrates all points
         at large r, making np.gradient wildly inaccurate at small r.
      3. Overwrite the left-endpoint derivative after np.gradient using
         a two-point forward difference anchored to the exact physical
         boundary value zeta_v[0]. The right endpoint needs no correction.
      4. Compute dζ/dr by finite differences (np.gradient in log-r space,
         then divide by r) -- no spline derivative is used.

    Returns (r_dense, zeta_dense, zeta_prime_dense).
    """
    zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3)

    N_dense = max(10 * len(r_v), 500)
    r_dense = np.geomspace(r_v[0], r_v[-1], N_dense)  # log-uniform spacing
    log_r_dense = np.log(r_dense)
    zeta_dense = zeta_spline(r_dense)

    # Finite-difference dζ/dr: gradient in log-r then divide by r.
    # np.gradient uses a three-point one-sided stencil at the endpoints,
    # which is sensitive to the values of the neighbouring points.  Pinning
    # zeta_dense[0] before the gradient call creates a discontinuity that
    # corrupts the stencil.  Instead, overwrite dzeta_dlogr[0] after the
    # gradient using a two-point forward difference anchored to the exact
    # physical boundary value zeta_inner = delta_Nstar.  No right-endpoint
    # override is needed: the spline is smooth there and np.gradient gives
    # the correct result.
    dzeta_dlogr = np.gradient(zeta_dense, log_r_dense)

    # zeta_v[0] is the exact computed zeta at the first sample point,
    # which equals delta_Nstar only approximately. Using the actual value
    # avoids a spurious derivative from the discrepancy.
    dzeta_dlogr[0] = (zeta_dense[1] - zeta_v[0]) / (log_r_dense[1] - log_r_dense[0])
    zeta_prime_dense = dzeta_dlogr / r_dense

    return r_dense, zeta_dense, zeta_prime_dense


def compute_C_bar(r_dense, zeta_dense, zeta_prime_dense, r_v, zeta_v) -> np.ndarray:
    """
    Compute C_bar(r) at the sample points r_v from the dense-grid zeta(r)
    and dzeta/dr profile.

    Builds the C_bar integrand on the dense grid, accumulates a trapezoid
    cumulative integral, interpolates it back to the sample points (r_v is
    a subset of [r_dense[0], r_dense[-1]] by construction so no
    extrapolation occurs), and normalises by r_v**3 * exp(3*zeta_v).
    """
    N_dense = len(r_dense)

    rz_dense = r_dense * zeta_prime_dense
    integrand = (
        r_dense**2
        * np.exp(3.0 * zeta_dense)
        * (2.0 * rz_dense + 3.0 * rz_dense**2 + rz_dense**3)
    )

    # Accumulate integral to each sample r_i using trapezoid
    cumulative = np.zeros(N_dense)
    for j in range(1, N_dense):
        cumulative[j] = cumulative[j - 1] + 0.5 * (integrand[j - 1] + integrand[j]) * (
            r_dense[j] - r_dense[j - 1]
        )

    # Interpolate cumulative integral to sample points.
    cumulative_at_r = SplineWrapper(r_dense, cumulative, x_transform='log', k=3)

    C_bar_v = np.array(
        [
            -2.0 * float(cumulative_at_r(r_v[i])) / (r_v[i] ** 3 * exp(3.0 * zeta_v[i]))
            for i in range(len(r_v))
        ]
    )

    return C_bar_v


def classify_C_min(C_v) -> dict:
    """
    Classify the compaction-function minimum.

    Returns a dict with keys C_min, compensated, type_II.
    """
    C_min = float(np.nanmin(C_v))
    type_II = C_min < -1.0
    compensated = C_min < 0.0

    return {
        "C_min": C_min,
        "compensated": compensated,
        "type_II": type_II,
    }


def pbh_mass(
    C_max: float,
    r: Optional[float],
    C_threshold: float,
    k_star: float,
    SolarMass: float,
) -> Optional[float]:
    """
    PBH mass formula, gated on r being resolved and C_max >= C_threshold.

    Mirrors the two call sites' current
    `if r is not None and C_max >= C_threshold:` guard, so both callers
    (r_max -> M_max, r_peak -> M_peak) get the gate for free.

    Returns None when the gate fails.
    """
    if r is None or C_max < C_threshold:
        return None

    return (1.0 + C_max) * 5.6e15 * (k_star * r) ** 2 * SolarMass
