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

import itertools
import math
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import ray
import seaborn as sns
from matplotlib import pyplot as plt

from ComputeTargets import InflatonTrajectoryProxy
from ComputeTargets.FullInstanton import FullInstantonProxy
from ComputeTargets.SlowRollInstanton import SlowRollInstantonProxy
from config.argument_parser import create_argument_parser
from config.pipeline_setup import build_pipeline_inputs
from config.sharding import (
    ShardKeyType,
    get_shard_key_store_id,
    inventory_config,
    read_table_config,
    replicated_tables,
    sharded_tables,
)
from CosmologyModels.cosmo_params import CosmologicalParams
from CosmologyModels.params import Planck2018
from Datastore.SQL.ShardedPool import ShardedPool
from InflationConcepts import MasslessDecoupledDiffusion
from RayTools.RayWorkPool import RayWorkPool
from Units import Planck_units

VERSION_LABEL = "2026.3.0"

DEFAULT_MAX_TRAJECTORIES = 3
DEFAULT_MAX_COMBINATIONS = 10
DEFAULT_MAX_INSTANTON_SAMPLES = 30


def create_plot_parser():
    """Reuses the shared compute-pipeline parser (config/argument_parser.py)
    so plot_InstantonSolutions.py accepts the same --config YAML file as
    main.py and rebuilds identical N_init/N_final grids — those grids aren't
    recorded in a lookup table the way delta_Nstar is, so they can't be
    auto-discovered and must be reconstructed from the same CLI/config
    inputs main.py used. Unrelated compute-only flags (e.g. --shards,
    --samples-per-N) are accepted but unused here."""
    parser = create_argument_parser()

    plot_grp = parser.add_argument_group("Plotting")
    plot_grp.add_argument(
        "--output-dir",
        type=str,
        default="plots",
        help="Directory for output figures (default: 'plots/')",
    )
    plot_grp.add_argument(
        "--format",
        type=str,
        default="pdf",
        choices=["pdf", "png", "svg"],
        help="Output figure format (default: pdf)",
    )
    plot_grp.add_argument(
        "--max-trajectories",
        type=int,
        default=DEFAULT_MAX_TRAJECTORIES,
        help="Maximum number of background trajectories to render "
        f"(default: {DEFAULT_MAX_TRAJECTORIES})",
    )
    plot_grp.add_argument(
        "--max-combinations",
        type=int,
        default=DEFAULT_MAX_COMBINATIONS,
        help="Maximum number of parameter combinations per sweep-summary "
        "plot (curves on compaction_summary and msr_action figures), "
        f"evenly sampled across the grid (default: {DEFAULT_MAX_COMBINATIONS})",
    )
    plot_grp.add_argument(
        "--max-instanton-samples",
        type=int,
        default=DEFAULT_MAX_INSTANTON_SAMPLES,
        help="Maximum number of (N_init, N_final, delta_Nstar) combinations "
        "to render in the instantons/ folder, evenly sampled across "
        f"the 3-D grid (default: {DEFAULT_MAX_INSTANTON_SAMPLES})",
    )
    return parser


# ── Grid + sampling helpers ────────────────────────────────────────────────────


def _evenly_sample(seq, k):
    """Return up to k elements of seq, evenly spaced by index."""
    n = len(seq)
    if n <= k:
        return list(seq)
    idx = sorted(set(int(round(i)) for i in np.linspace(0, n - 1, k)))
    return [seq[i] for i in idx]


# ── CF annotation helpers ──────────────────────────────────────────────────────


def _extract_cf_annotation(cf, units):
    """Return a plain-dict of CF summary scalars (all in display units) or None."""
    if cf is None or not cf.available or cf.failure:
        return None
    Mpc = units.Mpc
    SolarMass = units.SolarMass

    def _div(v, u):
        return v / u if v is not None else None

    def _mul(v, u):
        return v * u if v is not None else None

    return {
        "C_max_full": cf.C_max_full,
        "C_bar_max_full": cf.C_bar_max_full,
        "r_max_C_full_Mpc": _div(cf.r_max_C_full, Mpc),
        "r_max_C_bar_full_Mpc": _div(cf.r_max_C_bar_full, Mpc),
        "M_C_full_solar": _div(cf.M_C_full, SolarMass),
        "M_C_bar_full_solar": _div(cf.M_C_bar_full, SolarMass),
        "C_max_slow_roll": cf.C_max_slow_roll,
        "C_bar_max_slow_roll": cf.C_bar_max_slow_roll,
        "r_max_C_slow_roll_Mpc": _div(cf.r_max_C_slow_roll, Mpc),
        "r_max_C_bar_slow_roll_Mpc": _div(cf.r_max_C_bar_slow_roll, Mpc),
        "M_C_slow_roll_solar": _div(cf.M_C_slow_roll, SolarMass),
        "M_C_bar_slow_roll_solar": _div(cf.M_C_bar_slow_roll, SolarMass),
    }


def _cf_annotation_text(ann):
    """Build a compact annotation string (LaTeX mathtext) from a CF annotation
    dict returned by _extract_cf_annotation, or return None if ann is None."""
    if ann is None:
        return None
    lines = []
    for label, keys in (
        (
            "Full",
            (
                "C_max_full",
                "C_bar_max_full",
                "r_max_C_full_Mpc",
                "r_max_C_bar_full_Mpc",
                "M_C_full_solar",
                "M_C_bar_full_solar",
            ),
        ),
        (
            "SR",
            (
                "C_max_slow_roll",
                "C_bar_max_slow_roll",
                "r_max_C_slow_roll_Mpc",
                "r_max_C_bar_slow_roll_Mpc",
                "M_C_slow_roll_solar",
                "M_C_bar_slow_roll_solar",
            ),
        ),
    ):
        C_max, Cb_max, r, rb, M, Mb = (ann.get(k) for k in keys)
        if C_max is None and M is None:
            continue
        parts = []
        if C_max is not None:
            parts.append(rf"$C_{{\rm max}}$={C_max:.3g}")
        if Cb_max is not None:
            parts.append(rf"$\bar{{C}}_{{\rm max}}$={Cb_max:.3g}")
        if r is not None:
            parts.append(rf"$r_{{\rm max,C}}$={r:.3g} Mpc")
        if M is not None:
            parts.append(rf"$M_C$={M:.3g} $M_\odot$")
        lines.append(f"{label}: " + ",  ".join(parts))
    return "\n".join(lines) if lines else None


def _add_cf_annotation(fig, ann_text):
    """Add ann_text as a small figure-level annotation and adjust layout.

    The footer sits at y≈0.003; the annotation is anchored at y=0.03 so
    there is always a clear gap between them regardless of line count.
    """
    if not ann_text:
        fig.tight_layout()
        return
    n_lines = ann_text.count("\n") + 1
    # 0.03 = dedicated footer strip; 0.05/line for annotation text + padding
    bottom_frac = 0.03 + 0.05 * n_lines
    fig.tight_layout(rect=[0, bottom_frac, 1, 1])
    fig.text(
        0.5,
        0.03,
        ann_text,
        ha="center",
        va="bottom",
        fontsize="x-small",
        transform=fig.transFigure,
    )


def _provenance_footer(fig, *objs, render_time=None):
    """Render a small, unobtrusive provenance line at the very bottom of fig.

    Introspects whatever public attributes are present on each object; never
    raises if an attribute is absent or if the object is not yet persisted.
    """
    if render_time is None:
        render_time = datetime.now()

    obj_parts = []
    for obj in objs:
        fields = []
        try:
            if hasattr(obj, "available") and obj.available:
                fields.append(f"id={obj.store_id}")
        except Exception:
            pass
        try:
            ts = getattr(obj, "timestamp", None)
            if ts is not None:
                fields.append(f"stored={ts.strftime('%Y-%m-%d %H:%M')}")
        except Exception:
            pass
        for attr in ("atol", "rtol", "label"):
            try:
                val = getattr(obj, attr, None)
                if val is not None:
                    try:
                        formatted = f"{float(val):.2g}"
                    except (TypeError, ValueError):
                        formatted = str(val)
                    fields.append(f"{attr}={formatted}")
            except Exception:
                pass
        if fields:
            obj_parts.append(f"{type(obj).__name__}({', '.join(fields)})")

    parts = [
        f"StochasticInstanton v{VERSION_LABEL}",
        render_time.strftime("%Y-%m-%d %H:%M:%S"),
    ]
    parts.extend(obj_parts)

    try:
        fig.text(
            0.5,
            0.003,
            "  |  ".join(parts),
            ha="center",
            va="bottom",
            fontsize=7,
            color="#888888",
            transform=fig.transFigure,
        )
    except Exception:
        pass


# ── Figure functions ──────────────────────────────────────────────────────────


def _safe_name(s):
    return s.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")


def plot_background_fields(traj, potential, units, output_dir, fmt):
    """Two-panel figure: φ(N) and π(N) for the background trajectory."""
    if not traj._values:
        print(
            f"   Warning: trajectory {traj.store_id} has no values — skipping background fields plot"
        )
        return

    Mp = units.PlanckMass
    N_vals = [v.N.N for v in traj._values]
    phi_vals = [v.phi / Mp for v in traj._values]
    pi_vals = [v.pi / Mp for v in traj._values]

    # Slow-roll attractor φ(N) via ODE (same guard as before)
    sr_N = sr_phi = None
    try:
        from scipy.integrate import solve_ivp

        phi0_sr = traj._values[0].phi

        def sr_rhs(N, y):
            phi = y[0]
            Hsq = potential.H_sq(phi, 0.0)
            return [-potential.dV_dphi(phi) / (3.0 * Hsq)]

        # Terminal event prevents the solver stalling at the slow-roll pole
        # (e.g. φ → 0 for a quadratic potential).
        phi_floor = max(1e-3 * abs(phi0_sr), 1e-8)

        def sr_breakdown(N, y):
            return abs(y[0]) - phi_floor

        sr_breakdown.terminal = True

        N_span = (N_vals[0], N_vals[-1])
        N_eval = np.linspace(N_vals[0], N_vals[-1], max(len(N_vals), 300))
        sol = solve_ivp(
            sr_rhs, N_span, [phi0_sr], method="RK45", t_eval=N_eval, events=sr_breakdown
        )
        if sol.success:
            sr_N = sol.t
            sr_phi = sol.y[0] / Mp
    except Exception as exc:
        print(f"   Warning: slow-roll attractor integration failed: {exc}")

    # Slow-roll π at each sample point: π_SR = -V′(φ) / (3 H²_SR)
    try:
        pi_sr_vals = [
            -potential.dV_dphi(v.phi) / (3.0 * potential.H_sq(v.phi, 0.0)) / Mp
            for v in traj._values
        ]
    except Exception:
        pi_sr_vals = None

    fig, (ax_phi, ax_pi) = plt.subplots(1, 2, figsize=(10, 5))

    ax_phi.plot(N_vals, phi_vals, label="Numerical")
    if sr_N is not None:
        ax_phi.plot(sr_N, sr_phi, "--", label="Slow-roll attractor")
    ax_phi.set_xlabel("N (e-folds)")
    ax_phi.set_ylabel(r"$\varphi\,/\,M_{\rm P}$")
    ax_phi.set_title("Field")
    ax_phi.legend()

    ax_pi.plot(N_vals, pi_vals, label="Numerical")
    if pi_sr_vals is not None:
        ax_pi.plot(N_vals, pi_sr_vals, "--", label="Slow-roll")
    ax_pi.set_xlabel("N (e-folds)")
    ax_pi.set_ylabel(r"$\pi\,/\,M_{\rm P}$")
    ax_pi.set_title("Field velocity")
    ax_pi.legend()

    fig.suptitle(f"Background trajectory — {potential.name}")
    fig.tight_layout()
    _provenance_footer(fig, traj)

    fname = output_dir / f"background_fields.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def plot_epsilon(traj, potential, units, output_dir, fmt):
    """Figure: slow-roll parameter ε(N)."""
    if not traj._values:
        print(
            f"   Warning: trajectory {traj.store_id} has no values — skipping epsilon plot"
        )
        return

    N_vals = [v.N.N for v in traj._values]
    try:
        eps_vals = [potential.epsilon(v.phi, v.pi) for v in traj._values]
    except Exception as exc:
        print(f"   Warning: epsilon computation failed: {exc}")
        return

    fig, ax = plt.subplots(figsize=(7, 5.5))
    ax.plot(N_vals, eps_vals)
    ax.axhline(y=1.0, color="gray", linestyle="--", label="End of inflation")
    ax.set_xlabel("N (e-folds)")
    ax.set_ylabel(r"$\epsilon$")
    ax.set_title(rf"Slow-roll parameter $\epsilon$ — {potential.name}")
    ax.legend()
    fig.tight_layout()
    _provenance_footer(fig, traj)

    fname = output_dir / f"background_epsilon.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def plot_instanton_fields(
    fi,
    sri,
    N_init_val,
    N_final_val,
    dns_val,
    potential,
    units,
    output_dir,
    fmt,
    cf_annotation=None,
):
    """2×2 grid of instanton field components vs N, at one
    (N_init, N_final, delta_Nstar) point."""
    if fi is None and sri is None:
        print(
            f"   Warning: no instanton data for Ninit={N_init_val:.3g}, "
            f"Nfinal={N_final_val:.3g}, dNstar={dns_val:.3g} — skipping instanton fields plot"
        )
        return

    Mp = units.PlanckMass
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    ax_phi, ax_pi, ax_P1, ax_P2 = (axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1])

    # Top-left: φ₁ (full instanton) and φ (slow-roll instanton)
    if fi is not None and fi._values:
        N_fi = [v.N.N for v in fi._values]
        ax_phi.plot(
            N_fi, [v.phi1 / Mp for v in fi._values], label=r"$\varphi_1$ (full)"
        )
        phi_init = fi._values[0].phi1
        phi_final = fi._values[-1].phi1
        ax_phi.axhline(
            phi_init / Mp,
            color="gray",
            linestyle=":",
            linewidth=0.8,
            label=r"$\varphi_{\rm init}$",
        )
        ax_phi.axhline(
            phi_final / Mp,
            color="gray",
            linestyle="-.",
            linewidth=0.8,
            label=r"$\varphi_{\rm final}$",
        )

    if sri is not None and sri._values:
        N_sri = [v.N.N for v in sri._values]
        ax_phi.plot(
            N_sri, [v.phi / Mp for v in sri._values], "--", label=r"$\varphi$ (SR)"
        )

    ax_phi.set_xlabel("N (e-folds)")
    ax_phi.set_ylabel(r"$\varphi\,/\,M_{\rm P}$")
    ax_phi.set_title("Field trajectory")
    ax_phi.legend(fontsize="small")

    # Top-right: φ₂ (full instanton) + slow-roll π from trajectory
    if fi is not None and fi._values:
        N_fi = [v.N.N for v in fi._values]
        ax_pi.plot(N_fi, [v.phi2 / Mp for v in fi._values], label=r"$\varphi_2$ (full)")

        try:
            pi_sr = [
                -potential.dV_dphi(v.phi1) / (3.0 * potential.H_sq(v.phi1, 0.0))
                for v in fi._values
            ]
            ax_pi.plot(
                N_fi, [p / Mp for p in pi_sr], "--", label=r"$\pi_{\rm SR}(\varphi_1)$"
            )
        except Exception:
            pass

    ax_pi.set_xlabel("N (e-folds)")
    ax_pi.set_ylabel(r"field velocity / $M_{\rm P}$")
    ax_pi.set_title("Field velocity")
    ax_pi.legend(fontsize="small")

    # Bottom-left: P₁
    if fi is not None and fi._values:
        N_fi = [v.N.N for v in fi._values]
        ax_P1.plot(N_fi, [v.P1 for v in fi._values], label=r"$P_1$ (full)")

    if sri is not None and sri._values:
        N_sri = [v.N.N for v in sri._values]
        ax_P1.plot(N_sri, [v.P1 for v in sri._values], "--", label=r"$P_1$ (SR)")

    ax_P1.set_xlabel("N (e-folds)")
    ax_P1.set_ylabel(r"$P_1$")
    ax_P1.set_title("Response field $P_1$")
    ax_P1.legend(fontsize="small")

    # Bottom-right: P₂ (full instanton only)
    if fi is not None and fi._values:
        N_fi = [v.N.N for v in fi._values]
        ax_P2.plot(N_fi, [v.P2 for v in fi._values], label=r"$P_2$ (full)")

    ax_P2.set_xlabel("N (e-folds)")
    ax_P2.set_ylabel(r"$P_2$")
    ax_P2.set_title("Response field $P_2$")
    ax_P2.legend(fontsize="small")

    fig.suptitle(
        f"Instanton fields — {potential.name}, "
        rf"$N_{{\rm init}}$={N_init_val:.3g}, $N_{{\rm final}}$={N_final_val:.3g}, "
        rf"$\delta N_\star$={dns_val:.3g}"
    )

    # MSR action annotation alongside the CF summary
    msr_parts = []
    if fi is not None and fi.available and not fi.failure:
        action = getattr(fi, "msr_action", None)
        if action is not None:
            msr_parts.append(rf"Full: $S_{{\rm MSR}}$={action:.4g}")
    if sri is not None and sri.available and not sri.failure:
        action = getattr(sri, "msr_action", None)
        if action is not None:
            msr_parts.append(rf"SR: $S_{{\rm MSR}}$={action:.4g}")
    msr_text = "   ".join(msr_parts) if msr_parts else None

    cf_text = _cf_annotation_text(cf_annotation)
    ann_lines = [t for t in (cf_text, msr_text) if t]
    _add_cf_annotation(fig, "\n".join(ann_lines) if ann_lines else None)

    objs_for_footer = [o for o in (fi, sri) if o is not None]
    _provenance_footer(fig, *objs_for_footer)

    fname = output_dir / f"instanton_fields.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def plot_msr_action_sweep(
    x_label,
    fi_points,
    sri_points,
    fixed_desc,
    potential_name,
    output_dir,
    fmt,
    swept_name,
):
    """One trajectory's MSR action vs the swept dimension, at one fixed
    combination of the other two dimensions (described by fixed_desc).
    fi_points/sri_points: lists of (swept_value, msr_action) tuples."""
    fi_points = [(x, a) for x, a in fi_points if a is not None]
    sri_points = [(x, a) for x, a in sri_points if a is not None]
    if not fi_points and not sri_points:
        return

    fig, ax = plt.subplots(figsize=(7, 5.5))
    if fi_points:
        fi_sorted = sorted(fi_points)
        xs, ys = zip(*fi_sorted)
        ax.semilogy(xs, ys, "o-", label="Full MSR")
    if sri_points:
        sri_sorted = sorted(sri_points)
        xs, ys = zip(*sri_sorted)
        ax.semilogy(xs, ys, "s--", label="Slow-roll")

    ax.set_xlabel(x_label)
    ax.set_ylabel(r"$S_{\rm MSR}$")
    ax.set_title(f"MSR action vs {x_label} — {potential_name} ({fixed_desc})")
    ax.legend(fontsize="small")
    fig.tight_layout()
    _provenance_footer(fig)

    swept_file = {"N_init": "Ninit", "N_final": "Nfinal", "delta_Nstar": "dNstar"}[
        swept_name
    ]
    fname = output_dir / f"msr_action_vs_{swept_file}__{fixed_desc}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def _safe_num(v: float) -> str:
    return f"{v:.4g}".replace(".", "p").replace("-", "m")


def plot_zeta_and_compaction(
    cf,
    units,
    N_init_val,
    N_final_val,
    dns_val,
    potential_name,
    output_dir,
    fmt,
    cf_annotation=None,
):
    """Two-panel figure: zeta(r) and C(r)/C_bar(r) vs r in Mpc on a log x-axis."""
    full_vals = cf.full_values
    sr_vals = cf.slow_roll_values
    if not full_vals and not sr_vals:
        return

    Mpc = units.Mpc
    fig, (ax_zeta, ax_C) = plt.subplots(1, 2, figsize=(10, 5))

    if full_vals:
        r_full = [v.r / Mpc for v in full_vals]
        ax_zeta.plot(r_full, [v.zeta for v in full_vals], label="Full")
        ax_C.plot(r_full, [v.C for v in full_vals], label=r"$C$ (full)")
        ax_C.plot(r_full, [v.C_bar for v in full_vals], "--", label=r"$\bar{C}$ (full)")

    if sr_vals:
        r_sr = [v.r / Mpc for v in sr_vals]
        ax_zeta.plot(r_sr, [v.zeta for v in sr_vals], "--", label="Slow-roll")
        ax_C.plot(r_sr, [v.C for v in sr_vals], label=r"$C$ (SR)")
        ax_C.plot(r_sr, [v.C_bar for v in sr_vals], "--", label=r"$\bar{C}$ (SR)")

    for ax in (ax_zeta, ax_C):
        ax.set_xscale("log")
        ax.set_xlabel(r"$r$ / Mpc")

    ax_zeta.set_ylabel(r"$\zeta(r)$")
    ax_zeta.set_title(r"Density contrast $\zeta(r)$")
    ax_zeta.legend(fontsize="small")

    ax_C.set_ylabel(r"$C(r)$")
    ax_C.set_title("Compaction function")
    ax_C.legend(fontsize="small")

    fig.suptitle(
        rf"Compaction — {potential_name}, "
        rf"$N_{{\rm init}}$={N_init_val:.3g}, $N_{{\rm final}}$={N_final_val:.3g}, "
        rf"$\delta N_\star$={dns_val:.3g}"
    )
    _add_cf_annotation(fig, _cf_annotation_text(cf_annotation))
    _provenance_footer(fig, cf)

    fname = output_dir / f"compaction.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def plot_compaction_summary(
    x_label,
    fi_cf_points,
    sri_cf_points,
    fixed_desc,
    potential_name,
    output_dir,
    fmt,
    swept_name,
    threshold=None,
):
    """Two-panel summary: left = max C and max C̄ vs swept parameter;
    right = PBH mass in solar masses (log y-scale) vs swept parameter."""
    swept_file = {"N_init": "Ninit", "N_final": "Nfinal", "delta_Nstar": "dNstar"}[
        swept_name
    ]

    def _unzip(points, idx):
        return [p[0] for p in points if p[idx] is not None], [
            p[idx] for p in points if p[idx] is not None
        ]

    fi_xC, fi_yC = _unzip(fi_cf_points, 1)
    fi_xCb, fi_yCb = _unzip(fi_cf_points, 2)
    fi_xM, fi_yM = _unzip(fi_cf_points, 3)
    fi_xMb, fi_yMb = _unzip(fi_cf_points, 4)
    sri_xC, sri_yC = _unzip(sri_cf_points, 1)
    sri_xCb, sri_yCb = _unzip(sri_cf_points, 2)
    sri_xM, sri_yM = _unzip(sri_cf_points, 3)
    sri_xMb, sri_yMb = _unzip(sri_cf_points, 4)

    has_C_data = any(len(v) > 0 for v in (fi_xC, fi_xCb, sri_xC, sri_xCb))
    has_M_data = any(len(v) > 0 for v in (fi_xM, fi_xMb, sri_xM, sri_xMb))
    if not has_C_data and not has_M_data:
        return

    fig, (ax_C, ax_M) = plt.subplots(1, 2, figsize=(10, 5))

    if fi_xC:
        ax_C.plot(fi_xC, fi_yC, "o-", label=r"$\max C$ (full)")
    if fi_xCb:
        ax_C.plot(fi_xCb, fi_yCb, "o--", label=r"$\max \bar{C}$ (full)")
    if sri_xC:
        ax_C.plot(sri_xC, sri_yC, "s-", label=r"$\max C$ (SR)")
    if sri_xCb:
        ax_C.plot(sri_xCb, sri_yCb, "s--", label=r"$\max \bar{C}$ (SR)")
    threshold_val = threshold if threshold is not None else 0.4
    ax_C.axhline(
        y=threshold_val,
        color="gray",
        linestyle=":",
        linewidth=0.8,
        label=f"Threshold ({threshold_val:.2f})",
    )
    ax_C.set_xlabel(x_label)
    ax_C.set_ylabel(r"$\max C,\;\max \bar{C}$")
    ax_C.set_title("Compaction function maxima")
    ax_C.legend(fontsize="small")

    if fi_xM:
        ax_M.semilogy(fi_xM, fi_yM, "o-", label=r"$M_C$ (full)")
    if fi_xMb:
        ax_M.semilogy(fi_xMb, fi_yMb, "o--", label=r"$M_{\bar{C}}$ (full)")
    if sri_xM:
        ax_M.semilogy(sri_xM, sri_yM, "s-", label=r"$M_C$ (SR)")
    if sri_xMb:
        ax_M.semilogy(sri_xMb, sri_yMb, "s--", label=r"$M_{\bar{C}}$ (SR)")
    ax_M.set_xlabel(x_label)
    ax_M.set_ylabel(r"$M_{\rm PBH}\,/\,M_\odot$")
    ax_M.set_title("PBH mass")
    if has_M_data:
        ax_M.legend(fontsize="small")

    fig.suptitle(rf"Compaction summary — {potential_name} ({fixed_desc})")
    fig.tight_layout()
    _provenance_footer(fig)

    fname = output_dir / f"compaction_summary_vs_{swept_file}__{fixed_desc}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


# ── Ray remote plot dispatch ────────────────────────────────────────────────


@ray.remote
def _plot_trajectory_item(traj_proxy, potential, output_dir_str, fmt):
    """Runs inside a Ray worker: background fields + epsilon plots."""
    traj = traj_proxy.get()
    # sns.set_theme(style="ticks", context="paper")
    sns.set_theme()
    output_dir = Path(output_dir_str)
    units = Planck_units()
    plot_background_fields(traj, potential, units, output_dir, fmt)
    plot_epsilon(traj, potential, units, output_dir, fmt)


@ray.remote
def _plot_fields_item(
    fi,
    sri,
    N_init_val,
    N_final_val,
    dns_val,
    potential,
    output_dir_str,
    fmt,
    cf_annotation=None,
):
    """Runs inside a Ray worker: one field-trajectory comparison plot."""
    # sns.set_theme(style="ticks", context="paper")
    sns.set_theme()
    output_dir = Path(output_dir_str)
    units = Planck_units()
    plot_instanton_fields(
        fi,
        sri,
        N_init_val,
        N_final_val,
        dns_val,
        potential,
        units,
        output_dir,
        fmt,
        cf_annotation,
    )


@ray.remote
def _plot_msr_sweep_item(
    x_label,
    fi_points,
    sri_points,
    fixed_desc,
    potential_name,
    output_dir_str,
    fmt,
    swept_name,
):
    """Runs inside a Ray worker: one MSR-action-vs-swept-parameter plot."""
    # sns.set_theme(style="ticks", context="paper")
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_msr_action_sweep(
        x_label,
        fi_points,
        sri_points,
        fixed_desc,
        potential_name,
        output_dir,
        fmt,
        swept_name,
    )


@ray.remote
def _plot_compaction_item(
    cf,
    N_init_val,
    N_final_val,
    dns_val,
    potential_name,
    output_dir_str,
    fmt,
    cf_annotation=None,
):
    """Runs inside a Ray worker: zeta(r) and C(r)/C_bar(r) profile plots."""
    if cf is None or not cf.available or cf.failure:
        return
    # sns.set_theme(style="ticks", context="paper")
    sns.set_theme()
    output_dir = Path(output_dir_str)
    units = Planck_units()
    plot_zeta_and_compaction(
        cf,
        units,
        N_init_val,
        N_final_val,
        dns_val,
        potential_name,
        output_dir,
        fmt,
        cf_annotation,
    )


@ray.remote
def _plot_compaction_summary_item(
    x_label,
    fi_cf_points,
    sri_cf_points,
    fixed_desc,
    potential_name,
    output_dir_str,
    fmt,
    swept_name,
    threshold=None,
):
    """Runs inside a Ray worker: two-panel compaction summary sweep plot."""
    # sns.set_theme(style="ticks", context="paper")
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_compaction_summary(
        x_label,
        fi_cf_points,
        sri_cf_points,
        fixed_desc,
        potential_name,
        output_dir,
        fmt,
        swept_name,
        threshold=threshold,
    )


def _dispatch_plot_work(item):
    """task_builder for RayWorkPool: item is a (remote_fn, args) pair already
    fully prepared by the data-fetch stage; just submit it."""
    remote_fn, args = item
    return remote_fn.remote(*args)


# ── Sweep-direction data fetching ────────────────────────────────────────────


def _instanton_key_payload(traj_proxy, N_init, N_final, dns, atol, rtol):
    return dict(
        trajectory=traj_proxy,
        N_init=N_init,
        N_final=N_final,
        delta_Nstar=dns,
        atol=atol,
        rtol=rtol,
        tags=[],
    )


def _cf_key_payload(traj_proxy, fi_proxy, sri_proxy, dns, cosmo, atol, rtol):
    return dict(
        trajectory=traj_proxy,
        full_instanton=fi_proxy,
        slow_roll_instanton=sri_proxy,
        delta_Nstar=dns,
        cosmo=cosmo,
        C_threshold=0.4,
        C_bar_threshold=0.4,
        atol=atol,
        rtol=rtol,
        tags=[],
    )


def _qualifying_action(obj):
    """Extract msr_action from a (possibly _do_not_populate=True) query
    result, or None if the object doesn't exist / has no action recorded."""
    if obj is None or not obj.available:
        return None
    return obj.msr_action


def _extract_cf_summary(cf, SolarMass):
    """Return (C_max_full, C_bar_max_full, M_C_full_solar, M_C_bar_full_solar,
               C_max_sr,   C_bar_max_sr,   M_C_sr_solar,   M_C_bar_sr_solar)
    from a CompactionFunction object, or an all-None 8-tuple when unavailable."""
    none8 = (None,) * 8
    if cf is None or not cf.available or cf.failure:
        return none8

    def _m(v):
        return v / SolarMass if v is not None else None

    return (
        cf.C_max_full,
        cf.C_bar_max_full,
        _m(cf.M_C_full),
        _m(cf.M_C_bar_full),
        cf.C_max_slow_roll,
        cf.C_bar_max_slow_roll,
        _m(cf.M_C_slow_roll),
        _m(cf.M_C_bar_slow_roll),
    )


def _cf_vectorized_fetch(
    pool, traj_proxy, fi_list, sri_list, dns_val, cosmo, atol, rtol
):
    """Return an index-aligned list of CompactionFunction objects (or None) for every
    element in fi_list/sri_list.  Only submits a vectorized fetch for positions where
    at least one instanton is available; positions where neither is available get None."""
    n = len(fi_list)
    valid_indices = []
    payload_data = []
    for i, (fi_obj, sri_obj) in enumerate(zip(fi_list, sri_list)):
        fi_avail = fi_obj is not None and fi_obj.available
        sri_avail = sri_obj is not None and sri_obj.available
        if fi_avail or sri_avail:
            fi_proxy = FullInstantonProxy(fi_obj) if fi_avail else None
            sri_proxy = SlowRollInstantonProxy(sri_obj) if sri_avail else None
            payload_data.append(
                {
                    **_cf_key_payload(
                        traj_proxy, fi_proxy, sri_proxy, dns_val, cosmo, atol, rtol
                    ),
                    "_do_not_populate": True,
                }
            )
            valid_indices.append(i)

    result = [None] * n
    if payload_data:
        fetched = ray.get(
            pool.object_get_vectorized(
                "CompactionFunction", dns_val, payload_data=payload_data
            )
        )
        for i, cf in zip(valid_indices, fetched):
            result[i] = cf
    return result


def _sweep_Ninit_or_Nfinal(
    pool,
    traj_proxy,
    potential,
    out_dir,
    fmt,
    swept_name,
    swept_array,
    fixed_other_array,
    dns_array,
    atol,
    rtol,
    max_combos,
    work_items,
    cosmo,
    units,
):
    """swept_name in {"N_init", "N_final"}. Emits MSR-action sweep plots and
    compaction summary sweep plots for each selected (other_val, dns_val) combo.
    Instanton field/compaction profile plots are handled separately by
    _generate_instanton_samples."""
    out_dir.mkdir(parents=True, exist_ok=True)
    combos = list(itertools.product(fixed_other_array, dns_array))
    selected = _evenly_sample(combos, max_combos)

    for other_val, dns_val in selected:
        if swept_name == "N_init":
            payload_data = [
                {
                    **_instanton_key_payload(
                        traj_proxy, v, other_val, dns_val, atol, rtol
                    ),
                    "_do_not_populate": True,
                }
                for v in swept_array
            ]
        else:
            payload_data = [
                {
                    **_instanton_key_payload(
                        traj_proxy, other_val, v, dns_val, atol, rtol
                    ),
                    "_do_not_populate": True,
                }
                for v in swept_array
            ]

        fi_list, sri_list = ray.get(
            [
                pool.object_get_vectorized(
                    "FullInstanton", dns_val, payload_data=payload_data
                ),
                pool.object_get_vectorized(
                    "SlowRollInstanton", dns_val, payload_data=payload_data
                ),
            ]
        )

        swept_vals = [float(v) for v in swept_array]
        fi_points = list(zip(swept_vals, (_qualifying_action(o) for o in fi_list)))
        sri_points = list(zip(swept_vals, (_qualifying_action(o) for o in sri_list)))

        if swept_name == "N_init":
            fixed_desc = f"Nfinal={float(other_val):.3g}_dNstar={float(dns_val):.3g}"
            x_label = r"$N_{\rm init}$"
        else:
            fixed_desc = f"Ninit={float(other_val):.3g}_dNstar={float(dns_val):.3g}"
            x_label = r"$N_{\rm final}$"

        if any(a is not None for _, a in fi_points) or any(
            a is not None for _, a in sri_points
        ):
            work_items.append(
                (
                    _plot_msr_sweep_item,
                    (
                        x_label,
                        fi_points,
                        sri_points,
                        fixed_desc,
                        potential.name,
                        str(out_dir),
                        fmt,
                        swept_name,
                    ),
                )
            )

        cf_list = _cf_vectorized_fetch(
            pool, traj_proxy, fi_list, sri_list, dns_val, cosmo, atol, rtol
        )
        SolarMass = units.SolarMass
        fi_cf_points = []
        sri_cf_points = []
        c_thresholds = set()
        for sv, cf in zip(swept_vals, cf_list):
            s = _extract_cf_summary(cf, SolarMass)
            fi_cf_points.append((sv, s[0], s[1], s[2], s[3]))
            sri_cf_points.append((sv, s[4], s[5], s[6], s[7]))
            if cf is not None and cf.available and not cf.failure:
                try:
                    c_thresholds.add(cf.C_threshold)
                except Exception:
                    pass
        threshold = None
        if len(c_thresholds) == 1:
            threshold = next(iter(c_thresholds))
        elif len(c_thresholds) > 1:
            print(
                f"  Warning: C_threshold varies across sweep: {sorted(c_thresholds)}. "
                "Using smallest value."
            )
            threshold = sorted(c_thresholds)[0]
        if any(
            p[1] is not None or p[3] is not None for p in fi_cf_points + sri_cf_points
        ):
            work_items.append(
                (
                    _plot_compaction_summary_item,
                    (
                        x_label,
                        fi_cf_points,
                        sri_cf_points,
                        fixed_desc,
                        potential.name,
                        str(out_dir),
                        fmt,
                        swept_name,
                        threshold,
                    ),
                )
            )


def _sweep_delta_Nstar(
    pool,
    traj_proxy,
    potential,
    out_dir,
    fmt,
    dns_array,
    N_init_array,
    N_final_array,
    atol,
    rtol,
    max_combos,
    work_items,
    cosmo,
    units,
):
    """Emits MSR-action sweep plots and compaction summary sweep plots vs
    delta_Nstar for each selected (N_init, N_final) combo.
    Instanton field/compaction profile plots are handled separately by
    _generate_instanton_samples."""
    out_dir.mkdir(parents=True, exist_ok=True)
    combos = list(itertools.product(N_init_array, N_final_array))
    selected = _evenly_sample(combos, max_combos)

    fi_refs = {}
    sri_refs = {}
    for dns_val in dns_array:
        payload_data = [
            {
                **_instanton_key_payload(
                    traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol
                ),
                "_do_not_populate": True,
            }
            for (N_init_v, N_final_v) in selected
        ]
        fi_refs[dns_val] = pool.object_get_vectorized(
            "FullInstanton", dns_val, payload_data=payload_data
        )
        sri_refs[dns_val] = pool.object_get_vectorized(
            "SlowRollInstanton", dns_val, payload_data=payload_data
        )

    fi_by_dns = dict(zip(fi_refs.keys(), ray.get(list(fi_refs.values()))))
    sri_by_dns = dict(zip(sri_refs.keys(), ray.get(list(sri_refs.values()))))

    cf_refs = {}
    cf_valid_indices_by_dns = {}
    for dns_val in dns_array:
        fi_list_d = fi_by_dns[dns_val]
        sri_list_d = sri_by_dns[dns_val]
        valid_indices = []
        cf_payload_data = []
        for i, (fi_obj, sri_obj) in enumerate(zip(fi_list_d, sri_list_d)):
            fi_avail = fi_obj is not None and fi_obj.available
            sri_avail = sri_obj is not None and sri_obj.available
            if fi_avail or sri_avail:
                fi_proxy = FullInstantonProxy(fi_obj) if fi_avail else None
                sri_proxy = SlowRollInstantonProxy(sri_obj) if sri_avail else None
                cf_payload_data.append(
                    {
                        **_cf_key_payload(
                            traj_proxy, fi_proxy, sri_proxy, dns_val, cosmo, atol, rtol
                        ),
                        "_do_not_populate": True,
                    }
                )
                valid_indices.append(i)
        if cf_payload_data:
            cf_refs[dns_val] = pool.object_get_vectorized(
                "CompactionFunction", dns_val, payload_data=cf_payload_data
            )
        cf_valid_indices_by_dns[dns_val] = valid_indices

    dns_with_refs = [(dns, ref) for dns, ref in cf_refs.items()]
    if dns_with_refs:
        dns_keys, refs = zip(*dns_with_refs)
        fetched_lists = ray.get(list(refs))
        cf_by_dns_raw = dict(zip(dns_keys, fetched_lists))
    else:
        cf_by_dns_raw = {}

    cf_by_dns = {}
    for dns_val in dns_array:
        full_list = [None] * len(selected)
        for i, cf in zip(
            cf_valid_indices_by_dns.get(dns_val, []), cf_by_dns_raw.get(dns_val, [])
        ):
            full_list[i] = cf
        cf_by_dns[dns_val] = full_list

    SolarMass = units.SolarMass

    for combo_idx, (N_init_v, N_final_v) in enumerate(selected):
        fi_points = [
            (float(dns_val), _qualifying_action(fi_by_dns[dns_val][combo_idx]))
            for dns_val in dns_array
        ]
        sri_points = [
            (float(dns_val), _qualifying_action(sri_by_dns[dns_val][combo_idx]))
            for dns_val in dns_array
        ]

        fixed_desc = f"Ninit={float(N_init_v):.3g}_Nfinal={float(N_final_v):.3g}"
        if any(a is not None for _, a in fi_points) or any(
            a is not None for _, a in sri_points
        ):
            work_items.append(
                (
                    _plot_msr_sweep_item,
                    (
                        r"$\delta N_\star$",
                        fi_points,
                        sri_points,
                        fixed_desc,
                        potential.name,
                        str(out_dir),
                        fmt,
                        "delta_Nstar",
                    ),
                )
            )

        fi_cf_points = []
        sri_cf_points = []
        c_thresholds = set()
        for dns_val in dns_array:
            cf = cf_by_dns[dns_val][combo_idx]
            s = _extract_cf_summary(cf, SolarMass)
            dns_float = float(dns_val)
            fi_cf_points.append((dns_float, s[0], s[1], s[2], s[3]))
            sri_cf_points.append((dns_float, s[4], s[5], s[6], s[7]))
            if cf is not None and cf.available and not cf.failure:
                try:
                    c_thresholds.add(cf.C_threshold)
                except Exception:
                    pass
        threshold = None
        if len(c_thresholds) == 1:
            threshold = next(iter(c_thresholds))
        elif len(c_thresholds) > 1:
            print(
                f"  Warning: C_threshold varies across sweep: {sorted(c_thresholds)}. "
                "Using smallest value."
            )
            threshold = sorted(c_thresholds)[0]
        if any(
            p[1] is not None or p[3] is not None for p in fi_cf_points + sri_cf_points
        ):
            work_items.append(
                (
                    _plot_compaction_summary_item,
                    (
                        r"$\delta N_\star$",
                        fi_cf_points,
                        sri_cf_points,
                        fixed_desc,
                        potential.name,
                        str(out_dir),
                        fmt,
                        "delta_Nstar",
                        threshold,
                    ),
                )
            )


def _generate_instanton_samples(
    pool,
    traj_proxy,
    potential,
    out_dir,
    fmt,
    N_init_array,
    N_final_array,
    dns_array,
    atol,
    rtol,
    max_instanton_samples,
    work_items,
    cosmo,
    units,
):
    """Sample the full 3-D (N_init × N_final × δN★) grid evenly and emit
    instanton_fields + compaction work items into per-combination sub-folders
    under out_dir/."""
    all_combos = list(itertools.product(N_init_array, N_final_array, dns_array))
    selected = _evenly_sample(all_combos, max_instanton_samples)
    if not selected:
        return

    # Group by dns_val for vectorized fetches (one call per shard).
    by_dns = {}
    for N_init_v, N_final_v, dns_val in selected:
        by_dns.setdefault(dns_val, []).append((N_init_v, N_final_v))

    # Issue all vectorized instanton fetches; resolve in one ray.get.
    fi_refs = {}
    sri_refs = {}
    for dns_val, combos in by_dns.items():
        payload_data = [
            {
                **_instanton_key_payload(
                    traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol
                ),
                "_do_not_populate": True,
            }
            for N_init_v, N_final_v in combos
        ]
        fi_refs[dns_val] = pool.object_get_vectorized(
            "FullInstanton", dns_val, payload_data=payload_data
        )
        sri_refs[dns_val] = pool.object_get_vectorized(
            "SlowRollInstanton", dns_val, payload_data=payload_data
        )

    all_dns = list(fi_refs.keys())
    fi_resolved = dict(zip(all_dns, ray.get([fi_refs[d] for d in all_dns])))
    sri_resolved = dict(zip(all_dns, ray.get([sri_refs[d] for d in all_dns])))

    # Vectorized CF fetch (do_not_populate for the annotation scalars).
    cf_refs = {}
    cf_index_by_dns = {}
    for dns_val, combos in by_dns.items():
        fi_list = fi_resolved[dns_val]
        sri_list = sri_resolved[dns_val]
        valid_indices = []
        cf_payload_data = []
        for i, (fi_obj, sri_obj) in enumerate(zip(fi_list, sri_list)):
            fi_avail = fi_obj is not None and fi_obj.available
            sri_avail = sri_obj is not None and sri_obj.available
            if fi_avail or sri_avail:
                fi_proxy = FullInstantonProxy(fi_obj) if fi_avail else None
                sri_proxy = SlowRollInstantonProxy(sri_obj) if sri_avail else None
                cf_payload_data.append(
                    {
                        **_cf_key_payload(
                            traj_proxy, fi_proxy, sri_proxy, dns_val, cosmo, atol, rtol
                        ),
                        "_do_not_populate": True,
                    }
                )
                valid_indices.append(i)
        cf_index_by_dns[dns_val] = valid_indices
        if cf_payload_data:
            cf_refs[dns_val] = pool.object_get_vectorized(
                "CompactionFunction", dns_val, payload_data=cf_payload_data
            )

    dns_with_cf = list(cf_refs.keys())
    cf_raw = (
        dict(zip(dns_with_cf, ray.get([cf_refs[d] for d in dns_with_cf])))
        if dns_with_cf
        else {}
    )

    # Reconstruct index-aligned cf_by_dns.
    cf_by_dns = {}
    for dns_val, combos in by_dns.items():
        full_list = [None] * len(combos)
        for i, cf in zip(cf_index_by_dns.get(dns_val, []), cf_raw.get(dns_val, [])):
            full_list[i] = cf
        cf_by_dns[dns_val] = full_list

    # Emit work items, one sub-folder per combination.
    out_dir.mkdir(parents=True, exist_ok=True)
    for dns_val, combos in by_dns.items():
        fi_list = fi_resolved[dns_val]
        sri_list = sri_resolved[dns_val]
        cf_list = cf_by_dns[dns_val]

        for combo_idx, (N_init_v, N_final_v) in enumerate(combos):
            fi_obj = fi_list[combo_idx]
            sri_obj = sri_list[combo_idx]
            fi_available = fi_obj is not None and fi_obj.available
            sri_available = sri_obj is not None and sri_obj.available
            if not fi_available and not sri_available:
                continue

            combo_dir = (
                out_dir / f"Ninit={_safe_num(float(N_init_v))}"
                f"_Nfinal={_safe_num(float(N_final_v))}"
                f"_dNstar={_safe_num(float(dns_val))}"
            )
            combo_dir.mkdir(parents=True, exist_ok=True)

            cf_annotation = _extract_cf_annotation(cf_list[combo_idx], units)

            payload = _instanton_key_payload(
                traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol
            )
            fi_ref = (
                pool.object_get("FullInstanton", **payload) if fi_available else None
            )
            sri_ref = (
                pool.object_get("SlowRollInstanton", **payload)
                if sri_available
                else None
            )
            work_items.append(
                (
                    _plot_fields_item,
                    (
                        fi_ref,
                        sri_ref,
                        float(N_init_v),
                        float(N_final_v),
                        float(dns_val),
                        potential,
                        str(combo_dir),
                        fmt,
                        cf_annotation,
                    ),
                )
            )

            fi_proxy_for_cf = FullInstantonProxy(fi_obj) if fi_available else None
            sri_proxy_for_cf = (
                SlowRollInstantonProxy(sri_obj) if sri_available else None
            )
            cf_ref = pool.object_get(
                "CompactionFunction",
                **_cf_key_payload(
                    traj_proxy,
                    fi_proxy_for_cf,
                    sri_proxy_for_cf,
                    dns_val,
                    cosmo,
                    atol,
                    rtol,
                ),
            )
            work_items.append(
                (
                    _plot_compaction_item,
                    (
                        cf_ref,
                        float(N_init_v),
                        float(N_final_v),
                        float(dns_val),
                        potential.name,
                        str(combo_dir),
                        fmt,
                        cf_annotation,
                    ),
                )
            )


# ── Main pipeline ─────────────────────────────────────────────────────────────


def run_plots(pool, units, args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = args.format

    print("\n>> Building pipeline inputs...")
    inputs = build_pipeline_inputs(pool, units, args)
    atol, rtol = inputs["atol"], inputs["rtol"]
    N_init_array = inputs["N_init_array"]
    N_final_array = inputs["N_final_array"]
    dns_array = inputs["dns_array"]

    selected_models = _evenly_sample(inputs["model_list"], args.max_trajectories)
    print(f"\n>> Fetching {len(selected_models)} trajectory record(s)...")
    traj_list = ray.get(
        pool.object_get(
            "InflatonTrajectory",
            payload_data=[
                {
                    "phi0": inputs["phi0"],
                    "pi0": inputs["pi0"],
                    "potential": m["potential"],
                    "atol": atol,
                    "rtol": rtol,
                    "samples_per_N": None,
                }
                for m in selected_models
            ],
        )
    )
    traj_list = [t for t in traj_list if t.available and t._potential is not None]
    print(f"   {len(traj_list)} trajectory record(s) found in database")

    if not traj_list:
        print("No trajectories found. Run main.py first.")
        return

    if not dns_array:
        print("No delta_Nstar values found. Run main.py first.")
        return

    print("\n>> Reading cosmological parameters...")
    cosmo = ray.get(pool.object_get("CosmologicalParams", params=Planck2018()))
    print(f"   Cosmological parameters: {cosmo.name} (store_id={cosmo.store_id})")

    max_combos = args.max_combinations
    max_instanton_samples = args.max_instanton_samples

    work_items = []
    for traj in traj_list:
        potential = traj._potential
        traj_proxy = InflatonTrajectoryProxy(traj)
        traj_dir = output_dir / f"{_safe_name(potential.name)}_traj{traj.store_id}"
        traj_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n>> Trajectory {traj.store_id} ({potential.name}) -> {traj_dir}/")

        work_items.append(
            (_plot_trajectory_item, (traj_proxy, potential, str(traj_dir), fmt))
        )

        _generate_instanton_samples(
            pool,
            traj_proxy,
            potential,
            traj_dir / "instantons",
            fmt,
            N_init_array=N_init_array,
            N_final_array=N_final_array,
            dns_array=dns_array,
            atol=atol,
            rtol=rtol,
            max_instanton_samples=max_instanton_samples,
            work_items=work_items,
            cosmo=cosmo,
            units=units,
        )
        _sweep_Ninit_or_Nfinal(
            pool,
            traj_proxy,
            potential,
            traj_dir / "N-init",
            fmt,
            swept_name="N_init",
            swept_array=N_init_array,
            fixed_other_array=N_final_array,
            dns_array=dns_array,
            atol=atol,
            rtol=rtol,
            max_combos=max_combos,
            work_items=work_items,
            cosmo=cosmo,
            units=units,
        )
        _sweep_Ninit_or_Nfinal(
            pool,
            traj_proxy,
            potential,
            traj_dir / "N-final",
            fmt,
            swept_name="N_final",
            swept_array=N_final_array,
            fixed_other_array=N_init_array,
            dns_array=dns_array,
            atol=atol,
            rtol=rtol,
            max_combos=max_combos,
            work_items=work_items,
            cosmo=cosmo,
            units=units,
        )
        _sweep_delta_Nstar(
            pool,
            traj_proxy,
            potential,
            traj_dir / "delta-Nstar",
            fmt,
            dns_array=dns_array,
            N_init_array=N_init_array,
            N_final_array=N_final_array,
            atol=atol,
            rtol=rtol,
            max_combos=max_combos,
            work_items=work_items,
            cosmo=cosmo,
            units=units,
        )

    print(f"\n>> Dispatching {len(work_items)} plot(s) for rendering...")
    work_queue = RayWorkPool(
        pool,
        work_items,
        task_builder=_dispatch_plot_work,
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        available_handler=None,
        validation_handler=None,
        post_handler=None,
        label_builder=None,
        create_batch_size=10,
        process_batch_size=10,
        notify_batch_size=50,
        notify_time_interval=120,
        title="GENERATING InstantonSolutions PLOTS",
        store_results=False,
    )
    work_queue.run()

    print(f"\n>> Plots written to {output_dir}/")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = create_plot_parser()
    args = parser.parse_args()

    if args.database is None:
        parser.print_help()
        sys.exit()

    ray.init(address=args.ray_address, ignore_reinit_error=True)
    units = Planck_units()

    with ShardedPool(
        version_label=VERSION_LABEL,
        db_name=args.database,
        ShardKeyType=ShardKeyType,
        ShardKeyStoreIdGetter=get_shard_key_store_id,
        replicated_tables=replicated_tables,
        sharded_tables=sharded_tables,
        timeout=args.db_timeout,
        # ShardedPool reads the actual shard count from the existing primary
        # database when it is opened, so this is only a fallback.
        shards=args.shards,
        profile_agent=None,
        job_name="plot_InstantonSolutions",
        prune_unvalidated=False,
        drop_actions=[],
        read_table_config=read_table_config,
        inventory_config=inventory_config,
    ) as pool:
        run_plots(pool, units, args)
