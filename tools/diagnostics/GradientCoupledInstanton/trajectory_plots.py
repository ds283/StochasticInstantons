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
Trajectory-validation plots for converged GradientCoupledInstanton solves
(prompt 24b Part B). Refactor of ``plot_24b_trajectories.py``: generalized
to take its input/output paths as CLI arguments rather than hardcoded
filenames, and to read harness.save_grids_npz's canonical schema, so it can
be pointed at ANY convergence_floor.py diagnostic that persists grids (not
just Diagnostic 4) -- e.g. diagnostic_8_alpha_sensitivity, once that also
persists grids for its converged points.

For each converged point in the input JSON (any row with "converged": true
and a "grids_npz" key), produces:
  (1) phi_core(N)/pi_core(N) (GCI, y=+1) overlaid on FullInstanton's own
      phi1(N)/phi2(N).
  (2) epsilon(N) = 0.5*pi^2/Mp^2 for both, with a reference line at
      epsilon=1 -- the key physical check: a GCI core trajectory
      approaching epsilon=1 means the solution is skirting the H^2<0
      boundary the feasible-lambda corridor is built around.
  (3) the y-profile phi(y)/pi(y) at the final N -- confirms genuine shell
      structure, not the near-uniform trivial branch.
plus one combined figure across every converged point: S_GCI/S_FI vs the
row's own sweep variable (delta_Nstar by default, but any numeric key can
be selected via --x-key for e.g. an alpha-sensitivity sweep).

Run as a module, AFTER a convergence_floor.py diagnostic with
persist_grids=True has produced its own JSON + .npz records:

    python -m tools.diagnostics.GradientCoupledInstanton.trajectory_plots \\
        --input convergence_floor/diagnostic4_delta_nstar_walk.json
"""

from __future__ import annotations

import argparse
import json
import os

import numpy as np
from matplotlib import pyplot as plt

from . import harness as h

# Mp = 1 throughout (Planck_units) -- epsilon = 0.5*pi^2/Mp^2 = 0.5*pi^2.
MP = 1.0


def _epsilon(pi_array) -> np.ndarray:
    return 0.5 * np.asarray(pi_array) ** 2 / (MP ** 2)


def plot_point(row: dict, plot_dir: str) -> dict | None:
    """Produces plots (1)-(3) for one converged row. Returns an epsilon
    summary dict, or None if the row has no persisted grids to plot."""
    npz_path = row.get("grids_npz")
    if not npz_path or not os.path.exists(npz_path):
        print(f"  [skip] no grids_npz for row {row}")
        return None

    data = h.load_grids_npz(npz_path)
    N_grid = data["N_grid"]
    phi_grid = data["phi_grid"]
    pi_grid = data["pi_grid"]
    grid_nodes = data["grid_nodes"]
    N_sample_FI = data["N_sample_FI"]
    phi1_FI = data["phi1_FI"]
    phi2_FI = data["phi2_FI"]
    m = float(data["m"])
    dNstar = float(data["delta_Nstar"])
    alpha = float(data["alpha"]) if "alpha" in data else None

    phi_core = phi_grid[:, -1]
    pi_core = pi_grid[:, -1]

    tag = f"m{m:.4g}_dNstar{dNstar}" + (f"_alpha{alpha:.3g}" if alpha is not None else "")
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))

    ax = axes[0]
    ax.plot(N_grid, phi_core, color="tab:blue", label=r"GCI $\phi_{\rm core}(N)$ ($y=+1$)")
    ax.plot(N_sample_FI, phi1_FI, "--", color="tab:blue", alpha=0.6, label=r"FI $\phi_1(N)$")
    ax2 = ax.twinx()
    ax2.plot(N_grid, pi_core, color="tab:orange", label=r"GCI $\pi_{\rm core}(N)$ ($y=+1$)")
    ax2.plot(N_sample_FI, phi2_FI, "--", color="tab:orange", alpha=0.6, label=r"FI $\phi_2(N)$")
    ax.set_xlabel("N")
    ax.set_ylabel(r"$\phi$", color="tab:blue")
    ax2.set_ylabel(r"$\pi$", color="tab:orange")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="best")
    ax.set_title(f"Trajectory overlay ({tag})")

    ax = axes[1]
    eps_gci = _epsilon(pi_core)
    eps_fi = _epsilon(phi2_FI)
    ax.plot(N_grid, eps_gci, color="tab:blue", label=r"GCI core $\epsilon(N)$")
    ax.plot(N_sample_FI, eps_fi, "--", color="tab:orange", label=r"FI $\epsilon(N)$")
    ax.axhline(1.0, color="red", linestyle=":", linewidth=1.5, label=r"$\epsilon=1$")
    ax.set_xlabel("N")
    ax.set_ylabel(r"$\epsilon$")
    ax.set_yscale("log")
    ax.legend(fontsize=7, loc="best")
    ax.set_title(f"epsilon(N): max(GCI)={np.max(eps_gci):.3g}, max(FI)={np.max(eps_fi):.3g}")

    ax = axes[2]
    ax.plot(grid_nodes, phi_grid[-1, :], "o-", color="tab:blue", label=r"$\phi(y)$")
    ax2 = ax.twinx()
    ax2.plot(grid_nodes, pi_grid[-1, :], "s-", color="tab:orange", label=r"$\pi(y)$")
    ax.set_xlabel("y")
    ax.set_ylabel(r"$\phi(y)$", color="tab:blue")
    ax2.set_ylabel(r"$\pi(y)$", color="tab:orange")
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="best")
    ax.set_title(f"y-profile at N={N_grid[-1]:.4g}")

    fig.tight_layout()
    fname = os.path.join(plot_dir, f"trajectory_{tag}.png")
    fig.savefig(fname, dpi=130)
    plt.close(fig)
    print(f"  -> wrote {fname}  (max eps GCI={np.max(eps_gci):.4g}, max eps FI={np.max(eps_fi):.4g})")
    return {
        "m": m, "delta_Nstar": dNstar, "alpha": alpha,
        "max_epsilon_gci": float(np.max(eps_gci)), "max_epsilon_fi": float(np.max(eps_fi)),
        "final_epsilon_gci": float(eps_gci[-1]),
    }


def plot_action_ratio(rows: list, plot_dir: str, x_key: str = "delta_Nstar",
                       y_key: str = "S_ratio_GCI_over_FI"):
    converged = [r for r in rows if r.get("converged") and r.get(y_key) is not None]
    converged.sort(key=lambda r: r[x_key])
    if not converged:
        print(f"  [skip] no converged rows with {y_key!r}")
        return
    xs = [r[x_key] for r in converged]
    ys = [r[y_key] for r in converged]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(xs, ys, "o-", color="tab:purple")
    for x, y in zip(xs, ys):
        ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_xlabel(x_key)
    ax.set_ylabel(r"$S_{\rm GCI} / S_{\rm FI}$")
    ax.set_title(f"Gradient-drag action ratio vs {x_key}")
    fig.tight_layout()
    fname = os.path.join(plot_dir, f"S_ratio_vs_{x_key}.png")
    fig.savefig(fname, dpi=130)
    plt.close(fig)
    print(f"  -> wrote {fname}: {list(zip(xs, ys))}")


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trajectory-validation plots for converged "
                    "GradientCoupledInstanton solves (prompt 24b Part B). "
                    "Reads a convergence_floor.py diagnostic's own JSON "
                    "record plus its per-point .npz grids.",
    )
    parser.add_argument(
        "--input", type=str, required=True,
        help="Path to a convergence_floor.py diagnostic JSON (relative to "
             "the harness output directory unless absolute), e.g. "
             "convergence_floor/diagnostic4_delta_nstar_walk.json",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="Directory to write plots into (default: "
             "<package>/output/trajectory_plots/<input-stem>/).",
    )
    parser.add_argument(
        "--x-key", type=str, default="delta_Nstar",
        help="Row key to use as the x-axis of the combined action-ratio "
             "plot (default: %(default)s; use e.g. 'alpha' for an "
             "alpha-sensitivity sweep's own JSON).",
    )
    return parser


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    input_path = args.input
    if not os.path.isabs(input_path):
        input_path = os.path.join(h.output_dir(), input_path)
    with open(input_path) as fh:
        rows = json.load(fh)
    print(f"Loaded {len(rows)} rows from {input_path}")

    plot_dir = args.output_dir or h.output_dir(
        "trajectory_plots", os.path.splitext(os.path.basename(input_path))[0],
    )
    os.makedirs(plot_dir, exist_ok=True)

    epsilon_summary = []
    for row in rows:
        if not row.get("converged"):
            print(f"  [skip] row {row.get(args.x_key)!r} did not converge")
            continue
        summary = plot_point(row, plot_dir)
        if summary is not None:
            epsilon_summary.append(summary)

    plot_action_ratio(rows, plot_dir, x_key=args.x_key)

    print("\n--- epsilon(N) summary (the key physical check) ---")
    for s in epsilon_summary:
        flag = " <-- APPROACHING 1, INVESTIGATE" if s["max_epsilon_gci"] > 0.5 else ""
        print(f"  m={s['m']:.4g} {args.x_key}={s.get(args.x_key)}: "
              f"max eps_GCI={s['max_epsilon_gci']:.4g} "
              f"(final={s['final_epsilon_gci']:.4g}), max eps_FI={s['max_epsilon_fi']:.4g}{flag}")

    summary_path = os.path.join(plot_dir, "epsilon_summary.json")
    with open(summary_path, "w") as fh:
        json.dump(epsilon_summary, fh, indent=2)
    print(f"\nDone. Plots in {plot_dir}/, epsilon summary in {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
