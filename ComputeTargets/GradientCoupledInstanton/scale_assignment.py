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
Scale assignment for the gradient-coupled instanton model (onion_model.tex,
"Physical and comoving scale assignment", eq:compaction-yoo, eq:rphys-ratio).

Three distinct notions of scale, not to be conflated -- see
onion_model_planning.md's own "Scale assignment" panel before touching this
file:

1. Comoving radius r(y_j,N_final)/r_out -- read directly off the coordinate
   map, comoving_radius_ratio() (Numerics/OnionCoordinate.py). An absolute
   r_out is never needed anywhere in this module; everything works in this
   ratio throughout.

2. Compaction function C(y_j) (eq:compaction-yoo) -- needs rho*zeta'(rho)
   where rho = r/r_out. This product is scale-invariant (does not need
   r_out's absolute value): rho*zeta'(rho) = rho*(dzeta/dy)/(drho/dy), and
   the denominator drho/dy = -0.5*Delta_s(N_final)*rho is itself expressed
   purely in terms of the ratio rho -- no r_out dependence anywhere. Only
   the numerator dzeta/dy needs the collocation differentiation matrix
   (grid.D); the denominator is analytic.

3. Physical (present-day) scale r_phys(y_j) (eq:rphys-ratio) -- a single
   Leach-Liddle anchor solve at the outer edge (y=-1, node 0), reusing
   ln_k_phys_Mpc from CompactionFunction.py directly (not reimplemented),
   then propagated to every other node by the fixed ratio
   r_phys(y_j) = [r(y_j,N_final)/r_out] * r_phys_out -- no per-shell
   Leach-Liddle solve.

   The anchor is evaluated at the transition's *start* (local N=0, absolute
   N_offset), not at its own downflow-from-endpoint: y=-1 is Dirichlet-
   pinned to the noiseless background throughout, so its "downflow from
   the endpoint" is guaranteed to just be the remaining noiseless
   trajectory -- no integration needed. The number of e-folds from the
   transition's start to the true end of inflation is N_init itself
   (arithmetic, already known), combined with the noiseless trajectory's
   own local H at the start and its own true endpoint H (via
   AbstractPotential.H_sq -- ln_k_phys_Mpc takes H directly, not V/epsilon,
   so the Friedmann relation is not reimplemented here):

       H_start   = sqrt(potential.H_sq(trajectory.phi_at(N_offset),
                                        trajectory.pi_at(N_offset)))
       H_end_bg  = sqrt(potential.H_sq(trajectory.phi_at(trajectory.N_end),
                                        trajectory.pi_at(trajectory.N_end)))
       lnk_outer = ln_k_phys_Mpc(N_init, H_start, H_end_bg, units, cosmo)
       r_phys_out = (1.0 + alpha) * 2.0 * pi / exp(lnk_outer)

   The (1+alpha) factor is required because r_out is deliberately (1+alpha)
   larger than the true horizon at N_init (that's the whole point of the
   regularization) -- without it, r_phys_out would drift as alpha is
   varied rather than staying stable. See
   .prompts/gradient-coupled-instanton/11-fix-scale-assignment-anchor.md
   for the full derivation of why the previous (endpoint-downflow-based)
   anchor was wrong.

r_max/r_peak reuse CompactionFunction's own _classify_radii helper directly
(not reimplemented), fed r_phys (not the dimensionless ratio) since that is
the "r"-like quantity _classify_radii and its M_max/M_peak-adjacent callers
elsewhere expect -- the same convention CompactionFunction's own Step E
already uses. _classify_radii additionally expects its r array sorted
ascending (CompactionFunction always feeds it via np.argsort before calling
it); grid.nodes runs from y=-1 (outer edge, largest r) to y=+1 (core,
smallest r), i.e. r_phys is naturally *descending* in grid order, so it must
be re-sorted ascending here before the call.
"""

from math import exp, sqrt
from math import pi as PI

import numpy as np

from ComputeTargets.CompactionFunction import _classify_radii, ln_k_phys_Mpc
from Numerics.OnionCoordinate import comoving_radius_ratio


def assign_scales(
    zeta: np.ndarray,
    delta_s_N_final: float,
    grid,
    trajectory,
    N_init: float,
    N_offset: float,
    alpha: float,
    potential,
    units,
    cosmo,
    C_threshold: float = 0.4,
) -> dict:
    """
    Assign comoving, areal (via the compaction function), and physical
    (present-day) scales to every collocation node, given the already-
    extracted zeta(y) profile (extraction.py's extract_zeta_profile).

    trajectory/N_init/N_offset/alpha anchor the physical (present-day)
    scale at the transition's start (see module docstring, item 3) --
    no downflow integration anywhere in this function.

    Returns a dict with keys:
        "r_ratio"      -- comoving r(y_j,N_final)/r_out, dimensionless
        "C"            -- compaction function C(y_j) (eq:compaction-yoo)
        "r_phys"       -- physical (present-day) scale r_phys(y_j)
        "r_phys_out"   -- the single Leach-Liddle anchor value at the outer
                          edge, kept for diagnostics
        "r_max"        -- outermost r_phys where C >= C_threshold (or None)
        "r_peak"       -- r_phys at which C is maximised
        "diagnostics"  -- dict with r_max_at_grid_edge / r_peak_at_grid_edge
    """
    zeta = np.asarray(zeta, dtype=float)

    y = grid.nodes

    # ── Comoving radius (ratio) -- no separate calculation ──────────────────
    r_ratio = comoving_radius_ratio(y, delta_s_N_final)

    # ── Compaction function (eq:compaction-yoo) ──────────────────────────────
    # d(rho)/dy = -0.5 * Delta_s(N_final) * rho -- analytic, no numerical
    # differentiation; only the numerator (d zeta/dy) uses grid.D.
    dzeta_dy = grid.D @ zeta
    drho_dy = -0.5 * delta_s_N_final * r_ratio
    rho_zeta_prime = r_ratio * dzeta_dy / drho_dy
    C = (2.0 / 3.0) * (1.0 - (1.0 + rho_zeta_prime) ** 2)

    # ── Physical (present-day) scale (eq:rphys-ratio) ────────────────────────
    # Single anchor solve at the transition's start (local N=0, absolute
    # N_offset) -- y=-1 is Dirichlet-pinned to the noiseless background
    # throughout, so the number of e-folds from here to the true end of
    # inflation is N_init itself (arithmetic; no downflow integration).
    phi_start = trajectory.phi_at(N_offset)
    pi_start = trajectory.pi_at(N_offset)
    H_start = sqrt(potential.H_sq(phi_start, pi_start))
    H_end_bg = sqrt(
        potential.H_sq(trajectory.phi_at(trajectory.N_end), trajectory.pi_at(trajectory.N_end))
    )
    lnk_outer = ln_k_phys_Mpc(N_init, H_start, H_end_bg, units, cosmo)
    r_phys_out = (1.0 + alpha) * 2.0 * PI / exp(lnk_outer)
    r_phys = r_ratio * r_phys_out

    # ── r_max / r_peak: reuse CompactionFunction's own helper ────────────────
    sort_idx = np.argsort(r_phys)
    r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge = _classify_radii(
        r_phys[sort_idx], C[sort_idx], C_threshold
    )

    return {
        "r_ratio": r_ratio,
        "C": C,
        "r_phys": r_phys,
        "r_phys_out": r_phys_out,
        "r_max": r_max,
        "r_peak": r_peak,
        "diagnostics": {
            "r_max_at_grid_edge": r_max_at_grid_edge,
            "r_peak_at_grid_edge": r_peak_at_grid_edge,
        },
    }
