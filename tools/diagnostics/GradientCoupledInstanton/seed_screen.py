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
Cheap alpha_regularization vs n_collocation_points pre-screening scan.

Refactor of ``compare_gradient_full.py``'s own Part B/C. That script's Part A
(full Picard/shooting solve vs FullInstanton, for n_collocation_points in
{5,7,9}) is now superseded by convergence_floor.diagnostic_4 +
trajectory_plots.py, which do the same comparison on the CURRENT production
code (corrected phi_end, prompt-24b lambda-seed/corridor) rather than
compare_gradient_full.py's own pre-22a wiring -- see this module's own
"Historical note" below. Part B/C's own idea is distinct and still useful,
so it is the only part carried forward here: before spending minutes-to-
tens-of-minutes on a full Picard/shooting solve at some (alpha, n) point, it
is cheap to first check whether even the ZEROTH Picard iterate survives
there at all (``explore_onion_stiffness.run_case``, a helper this module
depends on but does not reproduce -- see harness.py's own module docstring
for why). This is a pre-screen, not a substitute for Diagnostic 8a's own
full converged-solve alpha sweep.

KNOWN BROKEN as of this refactor: ``run_case`` calls ``forward_rhs`` with
the pre-SAT-penalty positional signature. Current production
``forward_rhs`` requires a ``g_pi_core_spline`` argument that ``run_case``
never supplies and unconditionally dereferences whenever
``disable_spatial_coupling=False`` -- it predates the SAT-penalty machinery
entirely. Fixing this requires a physics decision (what
``disable_spatial_coupling``/``g_pi_core_spline`` should mean for a
zeroth-Picard-iterate screen with no FullInstanton profile yet) that is out
of scope for this refactor; this subcommand will raise until that follow-up
lands.

Historical note: the original compare_gradient_full.py's Part A used the
PRE-22a degenerate phi_end formula (``traj.phi_at(N_offset + N_total)``,
prompt 22's own Finding 1) and called solve_picard without a FullInstanton
seed or wall-clock budget -- i.e. it predates every fix this suite's other
modules assume. It is not reproduced here; use
convergence_floor.diagnostic_4 instead for a full solve/compare on
production code.

Run as a module:
    python -m tools.diagnostics.GradientCoupledInstanton.seed_screen \\
        --n-colloc 5,7,9,11,13,15,17,21,25,33 --alpha-powers 0,1,2,3
"""

from __future__ import annotations

import argparse
import csv
import os

import numpy as np

from . import harness as h
from .explore_onion_stiffness import run_case

OUT_DIR = h.output_dir("seed_screen")


def scan_alpha_vs_n_colloc(m: float = 1.0e-5, N_init: float = h.N_INIT,
                            N_final: float = h.N_FINAL, delta_Nstar: float = 0.1,
                            alpha_powers=(0, 1, 2, 3), n_colloc_values=(5, 7, 9, 11, 13, 15, 17, 21, 25, 33),
                            method: str = "RK45") -> dict:
    """For alpha in {exp(k): k in alpha_powers} and n in n_colloc_values,
    records whether the ZEROTH Picard iterate (run_case's own convention --
    see explore_onion_stiffness.py) survives. Does not call solve_picard's
    full outer shooting loop -- this is deliberately the cheap screen, not
    the full convergence check (use diagnostic_8_alpha_sensitivity for that,
    on whichever (alpha, n) combinations this screen flags as promising).
    """
    potential, units, traj, dm = h.setup(m)
    atol = rtol = h.ATOL

    alphas = [float(np.exp(k)) for k in alpha_powers]
    threshold_table = {}
    for alpha in alphas:
        print(f"-- alpha = exp({int(round(np.log(alpha)))}) = {alpha:.6g} --", flush=True)
        results = []
        for n_colloc in n_colloc_values:
            r = run_case(traj, potential, dm, N_init, N_final, delta_Nstar,
                          n_colloc, alpha, atol, rtol, method=method)
            results.append((n_colloc, bool(r["success"])))
            print(f"   n_collocation_points={n_colloc}: {'OK' if r['success'] else 'fail'}", flush=True)
        threshold_table[alpha] = results

    csv_path = os.path.join(OUT_DIR, "alpha_vs_ncolloc_threshold.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["alpha"] + [str(n) for n in n_colloc_values])
        for alpha, results in threshold_table.items():
            w.writerow([alpha] + [int(ok) for _, ok in results])
    print(f"\nWrote {csv_path}", flush=True)

    print("\nSummary (zeroth-iterate success/fail) -- rows=alpha, cols=n_collocation_points")
    header = "alpha".ljust(10) + "".join(f"{n:>6d}" for n in n_colloc_values)
    print(header)
    for alpha, results in threshold_table.items():
        row = f"{alpha:<10.4g}" + "".join(f"{'OK' if ok else '--':>6s}" for _, ok in results)
        print(row)

    return threshold_table


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cheap alpha_regularization vs n_collocation_points "
                    "zeroth-Picard-iterate pre-screen (compare_gradient_full"
                    ".py Part B/C, modernized). Not a substitute for "
                    "convergence_floor.py's own full-solve diagnostics.",
    )
    parser.add_argument("--mass", type=float, default=1.0e-5, help="m/Mp (default: %(default)s).")
    parser.add_argument("--delta-nstar", type=float, default=0.1, help="delta_Nstar (default: %(default)s).")
    parser.add_argument(
        "--alpha-powers", type=str, default="0,1,2,3",
        help="Comma-separated exponents k for alpha=exp(k) (default: %(default)s).",
    )
    parser.add_argument(
        "--n-colloc", type=str, default="5,7,9,11,13,15,17,21,25,33",
        help="Comma-separated n_collocation_points values to scan (default: %(default)s).",
    )
    parser.add_argument("--method", type=str, default="RK45", help="ODE integrator (default: %(default)s).")
    return parser


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    scan_alpha_vs_n_colloc(
        m=args.mass, delta_Nstar=args.delta_nstar,
        alpha_powers=tuple(int(x) for x in args.alpha_powers.split(",")),
        n_colloc_values=tuple(int(x) for x in args.n_colloc.split(",")),
        method=args.method,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
