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
Per-shell zeta-profile extraction for the gradient-coupled instanton model
(onion_model.tex, Section "No explicit freezing; extraction of zeta(y)",
eq:zeta-extraction).

There is no explicit freezing/crossing-time search: the collocation system
is integrated over the full rectangle y in [-1,1], N in [N_init, N_final]
and zeta(y) is read off as a post-processing step from the resulting
phi(y, N_final), pi(y, N_final) -- one node at a time, via the same
downflow-then-density-match construction CompactionFunction already uses
for the single-trajectory case (its own Steps A/B), applied per shell.

N-offset convention -- see picard.py's own module docstring for the full
account of the local (zero-based) vs absolute N axes. In brief:
integrate_noiseless_trajectory always integrates from its own fresh N=0, so
the N_end_downflow it returns is a duration relative to the downflow's own
start, not an absolute e-fold. Every shell's downflow starts from the same
shared local N_total (the extraction procedure's own step 1), so the
absolute endpoint is

    N_end_abs(y_j) = N_offset + N_total + N_end_downflow(y_j)

N_offset itself is *not* recomputed here: it is threaded through from
picard.py's own already-computed value (trajectory.N_end - N_init), exactly
the redundant-computation pattern flagged as the root cause of two earlier
bugs in this sequence (see picard.py's docstring and prompt 07). The one
exception, matching CompactionFunction's own existing Step B pattern, is
trajectory.N_end read directly for the brentq search bracket's upper bound
-- an existing, unproblematic use, not the redundant one.
"""

import numpy as np
from scipy.optimize import brentq

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential
from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory


def _N_end_abs(N_offset: float, N_total: float, N_end_downflow: float) -> float:
    """
    Convert a shell's downflow duration (relative to the downflow's own
    fresh N=0) into an absolute e-fold on InflatonTrajectory's own N axis.

    Isolated as its own function -- and given its own direct unit test in
    tests/test_extraction.py -- because getting this one line wrong would
    silently corrupt every node's zeta (see the module docstring above).
    """
    return N_offset + N_total + N_end_downflow


def extract_zeta_profile(
    phi_final: np.ndarray,
    pi_final: np.ndarray,
    N_offset: float,
    N_total: float,
    trajectory,
    potential: AbstractPotential,
    atol: float,
    rtol: float,
    units,
) -> dict:
    """
    Extract the zeta(y) profile from the grid-node states at the shared
    final time N_total (local), per eq:zeta-extraction.

    Per node j:
      1. Downflow (phi_final[j], pi_final[j]) noiselessly to epsilon=1,
         reusing integrate_noiseless_trajectory directly (the same function
         CompactionFunction's own Step A already imports) -- not
         reimplemented here.
      2. rho_end(y_j) = 3 Mp^2 H^2 at the downflow's terminal state.
      3. N_end_abs(y_j) = N_offset + N_total + N_end_downflow(y_j).
      4. Density-match against the background trajectory: brentq over
         absolute N in (0, trajectory.N_end), mirroring CompactionFunction's
         own Step B bracket, tolerances, and density-bracket sanity check.
      5. zeta(y_j) = N_end_abs(y_j) - N_nl(rho_end(y_j)).

    Failures (downflow doesn't reach epsilon=1, or density-matching falls
    outside the background's own density range / brentq can't bracket a
    root) mark that node's zeta as nan and set failure_mask[j], without
    raising and without affecting any other node.

    Returns a dict with keys:
        "zeta"            -- array, nan where extraction failed for a node
        "rho_end"         -- array, nan where the downflow itself failed
        "N_end_downflow"  -- array, raw relative downflow durations (nan
                              where the downflow itself failed); kept for
                              diagnostics
        "failure_mask"    -- bool array, True where extraction failed
    """
    phi_final = np.asarray(phi_final, dtype=float)
    pi_final = np.asarray(pi_final, dtype=float)
    n_nodes = phi_final.shape[0]

    Mp = units.PlanckMass

    zeta = np.full(n_nodes, np.nan)
    rho_end = np.full(n_nodes, np.nan)
    N_end_downflow = np.full(n_nodes, np.nan)
    failure_mask = np.zeros(n_nodes, dtype=bool)

    # Background density range, used for the Step-4 sanity check below --
    # computed once, mirroring CompactionFunction's own rho_start/rho_end.
    rho_start_traj = 3.0 * Mp**2 * potential.H_sq(
        trajectory.phi_at(0.0), trajectory.pi_at(0.0)
    )
    rho_end_traj = 3.0 * Mp**2 * potential.H_sq(
        trajectory.phi_at(trajectory.N_end), trajectory.pi_at(trajectory.N_end)
    )

    for j in range(n_nodes):
        # ── Step 1: per-shell noiseless downflow to epsilon=1 ────────────
        sol_down, _, _ = integrate_noiseless_trajectory(
            float(phi_final[j]), float(pi_final[j]), potential, atol, rtol,
        )
        if sol_down is None or len(sol_down.t_events[0]) == 0:
            failure_mask[j] = True
            continue

        N_end_downflow_j = float(sol_down.t_events[0][0])
        phi_down, pi_down = sol_down.y_events[0][0]
        N_end_downflow[j] = N_end_downflow_j

        # ── Step 2: rho at the downflow's terminal state ─────────────────
        rho_end_j = 3.0 * Mp**2 * potential.H_sq(float(phi_down), float(pi_down))
        rho_end[j] = rho_end_j

        # ── Step 3: absolute N (see _N_end_abs docstring) ────────────────
        N_end_abs_j = _N_end_abs(N_offset, N_total, N_end_downflow_j)

        # ── Step 4: density-match against the background ─────────────────
        if not (rho_end_traj <= rho_end_j <= rho_start_traj):
            failure_mask[j] = True
            continue
        try:
            N_nl_j = brentq(
                lambda N: (
                    3.0 * Mp**2 * potential.H_sq(trajectory.phi_at(N), trajectory.pi_at(N))
                    - rho_end_j
                ),
                0.0,
                trajectory.N_end,
                xtol=atol,
                rtol=rtol,
            )
        except ValueError:
            failure_mask[j] = True
            continue

        # ── Step 5: zeta ──────────────────────────────────────────────────
        zeta[j] = N_end_abs_j - N_nl_j

    return {
        "zeta": zeta,
        "rho_end": rho_end,
        "N_end_downflow": N_end_downflow,
        "failure_mask": failure_mask,
    }
