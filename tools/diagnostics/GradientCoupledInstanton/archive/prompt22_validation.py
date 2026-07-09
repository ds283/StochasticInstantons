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
ARCHIVED -- historical/provenance only, not part of the active diagnostic
CLI (no entry in cli.py, not exercised by any test).

This is prompt 22's own validation harness (formerly
``validation_22_resolved_regime.py``), lightly adapted to import the shared
stub classes from ``..harness`` instead of redefining them, with no other
logic changes. It is kept because its own closeout note
(.documents/gradient-coupled-instanton/22-validation.md) is what correctly
predicted that "this prompt's own Studies A-E should be re-run from scratch"
once the two blockers it found (the phi_end degeneracy, Finding 1; the
Picard divergence under genuine coupling, Finding 2) were fixed -- which is
exactly what convergence_floor.py's Diagnostics 4-8 now do, on production
code, not this script's own local monkeypatched workarounds.

Do not use this module's own ``production_phi_end`` -- it deliberately
reproduces the PRE-22a degenerate formula it was written to diagnose, for
comparison against ``corrected_phi_end``. Every other module in this package
uses ``harness.production_phi_end``, which is the CURRENT (post-22a,
corrected) production formula.

Run directly (unchanged from the original):
    python -m tools.diagnostics.GradientCoupledInstanton.archive.prompt22_validation
"""

from __future__ import annotations

import csv
import io
import os
import re
import time
from contextlib import redirect_stdout

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .. import harness as h

OUT_DIR = h.output_dir("archive", "prompt22_validation")

COLOR_THETA1 = "#D55E00"    # vermillion
COLOR_THETA05 = "#0072B2"   # blue
COLOR_THETA02 = "#009E73"   # bluish green
COLOR_THETA005 = "#CC79A7"  # reddish purple
COLOR_EXT = "#E69F00"       # orange

_SWEEP_RE = re.compile(r"picard sweep (\d+)/\d+: max\|dphi\|=([0-9.eE+-]+)")


def setup():
    return h.setup(1.0e-5, phi0=15.0, pi0=0.0, atol=1.0e-8, rtol=1.0e-8)


def production_phi_end(traj, N_init, N_final, delta_Nstar):
    """The PRE-22a DEGENERATE formula this validation diagnosed (Finding 1)
    -- NOT the current production formula (use harness.production_phi_end
    for that). Reproduced verbatim, deliberately, for the comparison below."""
    N_offset = traj.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    return traj.phi_at(N_offset + N_total)


def corrected_phi_end(traj, N_final):
    """FullInstanton's own convention -- what production code was changed
    to match in prompt 22a, and what harness.production_phi_end implements
    today."""
    return traj.phi_at(traj.N_end - N_final)


def finding_1_target_degeneracy(potential, atol, rtol, traj, dm):
    """Demonstrates that the (then-)production phi_end formula is an exact
    identity with the background trajectory (degenerate BVP), for every
    delta_Nstar, while the FullInstanton-consistent target is not."""
    print("\n" + "=" * 78, flush=True)
    print("FINDING 1: phi_end target degeneracy (historical, pre-22a)", flush=True)
    print("=" * 78, flush=True)

    N_init, N_final, alpha = h.N_INIT, h.N_FINAL, h.ALPHA
    rows = []
    for delta_Nstar in (0.1, 1.0, 1.5, 1.9, 2.5, 3.0):
        grid = h.LGLCollocationGrid(9)
        N_offset = traj.N_end - N_init
        N_total = (N_init - N_final) + delta_Nstar
        phi_init = traj.phi_at(N_offset)
        pi_init = traj.pi_at(N_offset)
        H_sq_nl_init = potential.H_sq(phi_init, pi_init)

        phi_end_prod = production_phi_end(traj, N_init, N_final, delta_Nstar)
        phi_end_fixed = corrected_phi_end(traj, N_final)

        result = h.picard_module.solve_picard(
            N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
            traj, potential, dm, atol, rtol, phi_end_prod,
            instrument_stiffness=False, verbose=False,
            label=f"finding1 dNstar={delta_Nstar}",
        )
        row = {
            "delta_Nstar": delta_Nstar, "phi_end_production": phi_end_prod,
            "phi_end_corrected": phi_end_fixed,
            "target_difference": phi_end_prod - phi_end_fixed,
        }
        if result.get("failure", False):
            row.update({"converged": False, "final_lambda": None, "msr_action": None,
                        "rfield_max": None, "phi_final_spread": None})
        else:
            msr = h.compute_msr_action(
                np.asarray(result["N_grid"]), np.asarray(result["phi_grid"]),
                np.asarray(result["pi_grid"]), np.asarray(result["rfield_grid"]),
                np.asarray(result["rmom_grid"]), grid, potential, dm, H_sq_nl_init, alpha,
            )
            phi_final = np.asarray(result["phi_grid"])[-1]
            row.update({
                "converged": True, "final_lambda": result["final_lambda"], "msr_action": msr,
                "rfield_max": float(np.max(np.abs(result["rfield_grid"]))),
                "phi_final_spread": float(phi_final.max() - phi_final.min()),
            })
        rows.append(row)
        print(
            f"  delta_Nstar={delta_Nstar:<4g} production_target_diff_from_corrected="
            f"{row['target_difference']:+.4e}  converged={row['converged']} "
            f"final_lambda={row['final_lambda']!r} msr_action={row['msr_action']!r} "
            f"rfield_max={row['rfield_max']!r}",
            flush=True,
        )

    csv_path = os.path.join(OUT_DIR, "finding1_target_degeneracy.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  -> wrote {csv_path}", flush=True)
    return rows


def _run_and_capture_sweeps(N_init, N_final, delta_Nstar, alpha, grid, traj,
                             potential, dm, atol, rtol, phi_end, theta,
                             max_inner=None, label=""):
    N_offset = traj.N_end - N_init
    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)

    overrides = {"MAX_OUTER": 1}
    if max_inner is not None:
        overrides["MAX_INNER"] = max_inner
    with h.MonkeypatchGuard(h.picard_module, **overrides):
        buf = io.StringIO()
        t0 = time.perf_counter()
        with redirect_stdout(buf):
            h.picard_module.solve_picard(
                N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
                traj, potential, dm, atol, rtol, phi_end,
                instrument_stiffness=False, verbose=True, theta=theta,
                label=label,
            )
        dt = time.perf_counter() - t0

    text = buf.getvalue()
    blocks = text.split("Newton derivative probe")
    probe_text = blocks[1] if len(blocks) > 1 else ""
    sweeps = [int(m.group(1)) for m in _SWEEP_RE.finditer(probe_text)]
    residuals = [float(m.group(2)) for m in _SWEEP_RE.finditer(probe_text)]
    return sweeps, residuals, dt


def finding_2_picard_divergence(potential, atol, rtol, traj, dm):
    """Demonstrates that, once phi_end is corrected to a genuinely
    non-trivial target, the theta=1 lagged-pi_core Picard iteration diverges
    -- and that under-relaxation delays but does not cure this within a
    practical sweep budget."""
    print("\n" + "=" * 78, flush=True)
    print("FINDING 2: Picard-iteration divergence under genuine coupling (historical)", flush=True)
    print("=" * 78, flush=True)

    N_init, N_final, alpha = h.N_INIT, h.N_FINAL, h.ALPHA
    phi_end_fixed = corrected_phi_end(traj, N_final)

    cases = [
        ("n=5 dNstar=1.0 theta=1.0", 5, 1.0, 1.0, 30, COLOR_THETA1),
        ("n=5 dNstar=1.0 theta=0.5", 5, 1.0, 0.5, 30, COLOR_THETA05),
        ("n=5 dNstar=1.0 theta=0.5 (extended budget)", 5, 1.0, 0.5, 150, COLOR_EXT),
        ("n=5 dNstar=1.0 theta=0.2", 5, 1.0, 0.2, 30, COLOR_THETA02),
        ("n=5 dNstar=1.0 theta=0.05", 5, 1.0, 0.05, 30, COLOR_THETA005),
        ("n=7 dNstar=1.0 theta=1.0", 7, 1.0, 1.0, 30, COLOR_THETA1),
        ("n=5 dNstar=1.5 theta=1.0", 5, 1.5, 1.0, 30, COLOR_THETA1),
        ("n=5 dNstar=2.5 theta=1.0", 5, 2.5, 1.0, 30, COLOR_THETA1),
    ]

    all_rows, curves = [], []
    for label, n_colloc, dNstar, theta, max_inner, color in cases:
        grid = h.LGLCollocationGrid(n_colloc)
        sweeps, residuals, dt = _run_and_capture_sweeps(
            N_init, N_final, dNstar, alpha, grid, traj, potential, dm, atol, rtol,
            phi_end_fixed, theta, max_inner=max_inner, label=label,
        )
        converged = bool(residuals) and residuals[-1] < 1.0e-7
        print(
            f"  [{label}] {len(residuals)} sweeps captured in {dt:.1f}s, "
            f"min={min(residuals) if residuals else float('nan'):.3e}, "
            f"final={residuals[-1] if residuals else float('nan'):.3e}, "
            f"converged={converged}",
            flush=True,
        )
        curves.append((label, sweeps, residuals, color))
        for s, r in zip(sweeps, residuals):
            all_rows.append({"case": label, "n_collocation_points": n_colloc,
                              "delta_Nstar": dNstar, "theta": theta,
                              "sweep": s, "max_dphi": r})

    csv_path = os.path.join(OUT_DIR, "finding2_picard_divergence.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    print(f"  -> wrote {csv_path}", flush=True)

    fig, ax = plt.subplots(figsize=(8, 5.5))
    for label, sweeps, residuals, color in curves:
        style = "--" if "extended" in label else "-"
        ax.semilogy(sweeps, residuals, style, color=color, lw=1.8, label=label, alpha=0.9)
    ax.axhline(1.0e-7, color="k", ls=":", lw=1, label="INNER_TOL (target)")
    ax.set_xlabel("Picard sweep index (within the dlam~1e-6 Newton derivative probe)")
    ax.set_ylabel(r"max|$\Delta\phi$| (sweep-to-sweep residual)")
    ax.set_title("Picard-iteration (non-)convergence under genuine (corrected-target) coupling")
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    fig.tight_layout()
    png_path = os.path.join(OUT_DIR, "finding2_picard_divergence.png")
    fig.savefig(png_path, dpi=150)
    plt.close(fig)
    print(f"  -> wrote {png_path}", flush=True)


def finding_1b_full_instanton_cross_check(potential, atol, rtol, traj, dm):
    print("\n" + "=" * 78, flush=True)
    print("FINDING 1b: FullInstanton cross-check at the corrected target (historical)", flush=True)
    print("=" * 78, flush=True)

    N_init, N_final, delta_Nstar = h.N_INIT, h.N_FINAL, 1.0
    N_offset = traj.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    phi_end_fixed = corrected_phi_end(traj, N_final)

    fi_data = h._compute_full_instanton._function(
        trajectory=h.TrajectoryProxyStub(potential), dm=dm,
        phi_init=phi_init, pi_init=pi_init, phi_final=phi_end_fixed,
        N_total=N_total, N_sample=list(np.linspace(0, N_total, 300)),
        atol=atol, rtol=rtol, label="FullInstanton corrected-target cross-check",
    )
    print(
        f"  FullInstanton (same corrected target, N_total={N_total}): "
        f"failure={fi_data.get('failure')} msr_action={fi_data.get('msr_action')}",
        flush=True,
    )
    csv_path = os.path.join(OUT_DIR, "finding1b_full_instanton_cross_check.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["delta_Nstar", "N_total", "phi_init", "phi_end_corrected", "failure", "msr_action"])
        w.writerow([delta_Nstar, N_total, phi_init, phi_end_fixed,
                    fi_data.get("failure"), fi_data.get("msr_action")])
    print(f"  -> wrote {csv_path}", flush=True)
    return fi_data


def main():
    potential, units, traj, dm = setup()
    atol = rtol = h.ATOL
    finding_1_target_degeneracy(potential, atol, rtol, traj, dm)
    finding_1b_full_instanton_cross_check(potential, atol, rtol, traj, dm)
    finding_2_picard_divergence(potential, atol, rtol, traj, dm)
    print(f"\nDone (historical replay). See {OUT_DIR}/ for CSVs/PNGs, and "
          ".documents/gradient-coupled-instanton/22-validation.md for the "
          "original write-up.", flush=True)


if __name__ == "__main__":
    main()
