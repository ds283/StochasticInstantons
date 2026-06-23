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
from config.grid_builder import build_instanton_grid
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
        "C_peak_full": cf.C_peak_full,
        "C_bar_peak_full": cf.C_bar_peak_full,
        "r_max_full_Mpc": _div(cf.r_max_full, Mpc),
        "r_peak_full_Mpc": _div(cf.r_peak_full, Mpc),
        "M_max_full_solar": _div(cf.M_max_full, SolarMass),
        "M_peak_full_solar": _div(cf.M_peak_full, SolarMass),
        "C_peak_slow_roll": cf.C_peak_slow_roll,
        "C_bar_peak_slow_roll": cf.C_bar_peak_slow_roll,
        "r_max_slow_roll_Mpc": _div(cf.r_max_slow_roll, Mpc),
        "r_peak_slow_roll_Mpc": _div(cf.r_peak_slow_roll, Mpc),
        "M_max_slow_roll_solar": _div(cf.M_max_slow_roll, SolarMass),
        "M_peak_slow_roll_solar": _div(cf.M_peak_slow_roll, SolarMass),
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
                "C_peak_full",
                "C_bar_peak_full",
                "r_max_full_Mpc",
                "r_peak_full_Mpc",
                "M_max_full_solar",
                "M_peak_full_solar",
            ),
        ),
        (
            "SR",
            (
                "C_peak_slow_roll",
                "C_bar_peak_slow_roll",
                "r_max_slow_roll_Mpc",
                "r_peak_slow_roll_Mpc",
                "M_max_slow_roll_solar",
                "M_peak_slow_roll_solar",
            ),
        ),
    ):
        C_max, Cb_max, r_max, r_peak, M_max, M_peak = (ann.get(k) for k in keys)
        if C_max is None and M_max is None:
            continue
        parts = []
        if C_max is not None:
            parts.append(rf"$C_{{\rm peak}}$={C_max:.3g}")
        if Cb_max is not None:
            parts.append(rf"$\bar{{C}}_{{\rm peak}}$={Cb_max:.3g}")
        if r_max is not None:
            parts.append(rf"$r_{{\rm max}}$={r_max:.3g} Mpc")
        if r_peak is not None:
            parts.append(rf"$r_{{\rm peak}}$={r_peak:.3g} Mpc")
        if M_max is not None:
            parts.append(rf"$M_{{\rm max}}$={M_max:.3g} $M_\odot$")
        if M_peak is not None:
            parts.append(rf"$M_{{\rm peak}}$={M_peak:.3g} $M_\odot$")
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
    # Reserve space in absolute inches (text size is fixed in points, not
    # figure-relative), then convert to a figure-fraction for this fig's
    # actual height. Avoids over-reserving whitespace on taller figures.
    fig_height_in = fig.get_size_inches()[1]
    footer_strip_in = 0.18  # dedicated footer strip
    per_line_in = 0.22  # x-small annotation line + padding
    bottom_frac = (footer_strip_in + per_line_in * n_lines) / fig_height_in
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


def _provenance_footer(fig, *objs, render_time=None, run_label: str = ""):
    """Render a small, unobtrusive provenance line at the very bottom of fig.

    Introspects whatever public attributes are present on each object; never
    raises if an attribute is absent or if the object is not yet persisted.
    When run_label is non-empty, renders a second line above the version/timestamp
    line showing the database filename, config, and active mode flags.
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
    bottom_line = "  |  ".join(parts)

    if run_label:
        fig_height_in = fig.get_size_inches()[1]
        two_line_strip_in = 0.30
        bottom_frac = two_line_strip_in / fig_height_in
        current_bottom = fig.subplotpars.bottom
        if bottom_frac > current_bottom:
            fig.subplots_adjust(bottom=bottom_frac)

    footer_text = "\n".join([run_label, bottom_line]) if run_label else bottom_line

    try:
        fig.text(
            0.5,
            0.003,
            footer_text,
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


def plot_background_fields(
    traj, potential, units, output_dir, fmt, run_label: str = ""
):
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
    _provenance_footer(fig, traj, run_label=run_label)

    fname = output_dir / f"background_fields.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def plot_epsilon(traj, potential, units, output_dir, fmt, run_label: str = ""):
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
    _provenance_footer(fig, traj, run_label=run_label)

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
    run_label: str = "",
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
    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
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
    _provenance_footer(fig, *objs_for_footer, run_label=run_label)

    fname = output_dir / f"instanton_fields.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def plot_noise_profile(
    fi,
    sri,
    N_init_val,
    N_final_val,
    dns_val,
    potential_name,
    output_dir,
    fmt,
    cf_annotation=None,
    run_label: str = "",
):
    """Two-panel figure: sigma_phi1(N) and sigma_phi2(N) noise amplitude profiles."""
    if fi is None and sri is None:
        print(
            f"   Warning: no instanton data for Ninit={N_init_val:.3g}, "
            f"Nfinal={N_final_val:.3g}, dNstar={dns_val:.3g} — skipping noise profile plot"
        )
        return

    fi_prof = None
    if fi is not None and fi._values:
        fi_prof = fi.noise_profile_arrays()

    sri_prof = None
    if sri is not None and sri._values:
        sri_prof = sri.noise_profile_arrays()

    if fi_prof is None and sri_prof is None:
        print(
            f"   Warning: noise profile unavailable for Ninit={N_init_val:.3g}, "
            f"Nfinal={N_final_val:.3g}, dNstar={dns_val:.3g} — skipping noise profile plot"
        )
        return

    fig, (ax_s1, ax_s2) = plt.subplots(1, 2, figsize=(10, 5))

    # Left panel: sigma_phi1
    if fi_prof is not None:
        N_fi = fi_prof["N"]
        s1_fi = fi_prof["sigma_phi1"]
        mask = ~np.isnan(s1_fi)
        if mask.any():
            ax_s1.plot(N_fi[mask], s1_fi[mask], label=r"$\sigma_{\varphi_1}$ (full)")

    if sri_prof is not None:
        N_sri = sri_prof["N"]
        s1_sri = sri_prof["sigma_phi1"]
        mask = ~np.isnan(s1_sri)
        if mask.any():
            ax_s1.plot(
                N_sri[mask], s1_sri[mask], "--", label=r"$\sigma_{\varphi_1}$ (SR)"
            )

    ax_s1.set_xlabel("N (e-folds)")
    ax_s1.set_ylabel(r"$\sigma_{\varphi_1}$")
    ax_s1.set_title(r"Noise amplitude $\sigma_{\varphi_1}$")
    ax_s1.legend(fontsize="small")

    # Right panel: sigma_phi2
    s2_has_data = False
    if fi_prof is not None:
        N_fi = fi_prof["N"]
        s2_fi = fi_prof["sigma_phi2"]
        mask = ~np.isnan(s2_fi)
        if mask.any():
            ax_s2.plot(N_fi[mask], s2_fi[mask], label=r"$\sigma_{\varphi_2}$ (full)")
            s2_has_data = True

    if sri_prof is not None:
        N_sri = sri_prof["N"]
        s2_sri = sri_prof["sigma_phi2"]
        mask = ~np.isnan(s2_sri)
        if mask.any():
            ax_s2.plot(
                N_sri[mask], s2_sri[mask], "--", label=r"$\sigma_{\varphi_2}$ (SR)"
            )
            s2_has_data = True

    if not s2_has_data:
        ax_s2.text(
            0.5,
            0.5,
            r"No $\varphi_2$ channel data",
            ha="center",
            va="center",
            transform=ax_s2.transAxes,
            color="gray",
        )

    ax_s2.set_xlabel("N (e-folds)")
    ax_s2.set_ylabel(r"$\sigma_{\varphi_2}$")
    ax_s2.set_title(r"Noise amplitude $\sigma_{\varphi_2}$")
    if s2_has_data:
        ax_s2.legend(fontsize="small")

    fig.suptitle(
        rf"Noise profile — {potential_name}, "
        rf"$N_{{\rm init}}$={N_init_val:.3g}, $N_{{\rm final}}$={N_final_val:.3g}, "
        rf"$\delta N_\star$={dns_val:.3g}"
    )

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
    _provenance_footer(fig, *objs_for_footer, run_label=run_label)

    fname = output_dir / f"noise_profile.{fmt}"
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
    run_label: str = "",
):
    """One trajectory's MSR action vs the swept dimension, at one fixed
    combination of the other two dimensions (described by fixed_desc).
    fi_points/sri_points: lists of (swept_value, msr_action) tuples."""
    fi_points = [(x, a) for x, a in fi_points if a is not None]
    sri_points = [(x, a) for x, a in sri_points if a is not None]
    if not fi_points and not sri_points:
        return

    max_pts = max(len(fi_points), len(sri_points))
    use_markers = max_pts <= 25
    fmt_fi = "o-" if use_markers else "-"
    fmt_sri = "s--" if use_markers else "--"

    fig, ax = plt.subplots(figsize=(7, 5.5))
    if fi_points:
        fi_sorted = sorted(fi_points)
        xs, ys = zip(*fi_sorted)
        ax.semilogy(xs, ys, fmt_fi, label="Full MSR")
    if sri_points:
        sri_sorted = sorted(sri_points)
        xs, ys = zip(*sri_sorted)
        ax.semilogy(xs, ys, fmt_sri, label="Slow-roll")

    ax.set_xlabel(x_label)
    ax.set_ylabel(r"$S_{\rm MSR}$")
    ax.set_title(f"MSR action vs {x_label} — {potential_name} ({fixed_desc})")
    ax.legend(fontsize="small")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)

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
    run_label: str = "",
):
    """Three-panel figure: zeta(r), C(r), and C_bar(r) vs r in Mpc on a log x-axis."""
    full_vals = cf.full_values
    sr_vals = cf.slow_roll_values
    if not full_vals and not sr_vals:
        return

    Mpc = units.Mpc

    # 1 column on left (zeta), 1 column on right split into 2 rows (C, C_bar)
    fig = plt.figure(figsize=(12, 5))
    ax_zeta = fig.add_subplot(1, 2, 1)
    ax_C = fig.add_subplot(2, 2, 2)
    ax_Cbar = fig.add_subplot(2, 2, 4, sharex=ax_C)

    if full_vals:
        r_full = [v.r / Mpc for v in full_vals]
        ax_zeta.plot(r_full, [v.zeta for v in full_vals], label="Full")
        ax_C.plot(r_full, [v.C for v in full_vals], label=r"$C$ (full)")
        ax_Cbar.plot(r_full, [v.C_bar for v in full_vals], label=r"$\bar{C}$ (full)")

    if sr_vals:
        r_sr = [v.r / Mpc for v in sr_vals]
        ax_zeta.plot(r_sr, [v.zeta for v in sr_vals], "--", label="Slow-roll")
        ax_C.plot(r_sr, [v.C for v in sr_vals], "--", label=r"$C$ (SR)")
        ax_Cbar.plot(r_sr, [v.C_bar for v in sr_vals], "--", label=r"$\bar{C}$ (SR)")

    ax_zeta.set_xscale("log")
    ax_zeta.set_xlabel(r"$r$ / Mpc")
    ax_zeta.set_ylabel(r"$\zeta(r)$")
    ax_zeta.set_title(r"Density contrast $\zeta(r)$")
    ax_zeta.legend(fontsize="small")

    ax_C.set_xscale("log")
    ax_C.set_ylabel(r"$C(r)$")
    ax_C.set_title("Compaction function")
    ax_C.legend(fontsize="small")
    plt.setp(ax_C.get_xticklabels(), visible=False)  # shared x, hide top labels

    ax_Cbar.set_xscale("log")
    ax_Cbar.set_xlabel(r"$r$ / Mpc")
    ax_Cbar.set_ylabel(r"$\bar{C}(r)$")
    ax_Cbar.legend(fontsize="small")

    fig.suptitle(
        rf"Compaction — {potential_name}, "
        rf"$N_{{\rm init}}$={N_init_val:.3g}, $N_{{\rm final}}$={N_final_val:.3g}, "
        rf"$\delta N_\star$={dns_val:.3g}"
    )
    _add_cf_annotation(fig, _cf_annotation_text(cf_annotation))
    _provenance_footer(fig, cf, run_label=run_label)

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
    run_label: str = "",
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
    fi_xr, fi_yr = _unzip(fi_cf_points, 5)
    fi_xrb, fi_yrb = _unzip(fi_cf_points, 6)
    sri_xC, sri_yC = _unzip(sri_cf_points, 1)
    sri_xCb, sri_yCb = _unzip(sri_cf_points, 2)
    sri_xM, sri_yM = _unzip(sri_cf_points, 3)
    sri_xMb, sri_yMb = _unzip(sri_cf_points, 4)
    sri_xr, sri_yr = _unzip(sri_cf_points, 5)
    sri_xrb, sri_yrb = _unzip(sri_cf_points, 6)

    has_C_data = any(len(v) > 0 for v in (fi_xC, fi_xCb, sri_xC, sri_xCb))
    has_M_data = any(len(v) > 0 for v in (fi_xM, fi_xMb, sri_xM, sri_xMb))
    has_r_data = any(len(v) > 0 for v in (fi_xr, fi_xrb, sri_xr, sri_xrb))
    if not has_C_data and not has_M_data and not has_r_data:
        return

    all_series = (
        fi_xC,
        fi_xCb,
        sri_xC,
        sri_xCb,
        fi_xM,
        fi_xMb,
        sri_xM,
        sri_xMb,
        fi_xr,
        fi_xrb,
        sri_xr,
        sri_xrb,
    )
    max_pts = max((len(x) for x in all_series), default=0)
    use_markers = max_pts <= 25
    fmt_full_s = "o-" if use_markers else "-"
    fmt_full_d = "o--" if use_markers else "--"
    fmt_sr_s = "s-" if use_markers else "-"
    fmt_sr_d = "s--" if use_markers else "--"

    fig, (ax_C, ax_M, ax_r) = plt.subplots(1, 3, figsize=(15, 5))

    if fi_xC:
        ax_C.plot(fi_xC, fi_yC, fmt_full_s, label=r"$C_{\rm peak}$ (full)")
    if fi_xCb:
        ax_C.plot(fi_xCb, fi_yCb, fmt_full_d, label=r"$\bar{C}_{\rm peak}$ (full)")
    if sri_xC:
        ax_C.plot(sri_xC, sri_yC, fmt_sr_s, label=r"$C_{\rm peak}$ (SR)")
    if sri_xCb:
        ax_C.plot(sri_xCb, sri_yCb, fmt_sr_d, label=r"$\bar{C}_{\rm peak}$ (SR)")
    threshold_val = threshold if threshold is not None else 0.4
    ax_C.axhline(
        y=threshold_val,
        color="gray",
        linestyle=":",
        linewidth=0.8,
        label=f"Threshold ({threshold_val:.2f})",
    )
    ax_C.set_xlabel(x_label)
    ax_C.set_ylabel(r"$C_{\rm peak},\;\bar{C}_{\rm peak}$")
    ax_C.set_title("Compaction function peak values")
    ax_C.legend(fontsize="small")

    if fi_xM:
        ax_M.semilogy(fi_xM, fi_yM, fmt_full_s, label=r"$M_{\rm max}$ (full)")
    if fi_xMb:
        ax_M.semilogy(fi_xMb, fi_yMb, fmt_full_d, label=r"$M_{\rm peak}$ (full)")
    if sri_xM:
        ax_M.semilogy(sri_xM, sri_yM, fmt_sr_s, label=r"$M_{\rm max}$ (SR)")
    if sri_xMb:
        ax_M.semilogy(sri_xMb, sri_yMb, fmt_sr_d, label=r"$M_{\rm peak}$ (SR)")
    ax_M.set_xlabel(x_label)
    ax_M.set_ylabel(r"$M_{\rm PBH}\,/\,M_\odot$")
    ax_M.set_title("PBH mass")
    if has_M_data:
        ax_M.legend(fontsize="small")

    if fi_xr:
        ax_r.semilogy(fi_xr, fi_yr, fmt_full_s, label=r"$r_{\rm max}$ (full)")
    if fi_xrb:
        ax_r.semilogy(fi_xrb, fi_yrb, fmt_full_d, label=r"$r_{\rm peak}$ (full)")
    if sri_xr:
        ax_r.semilogy(sri_xr, sri_yr, fmt_sr_s, label=r"$r_{\rm max}$ (SR)")
    if sri_xrb:
        ax_r.semilogy(sri_xrb, sri_yrb, fmt_sr_d, label=r"$r_{\rm peak}$ (SR)")
    ax_r.set_xlabel(x_label)
    ax_r.set_ylabel(r"$r_{\rm PBH}\,/\,\mathrm{Mpc}$")
    ax_r.set_title("PBH collapse scale")
    if has_r_data:
        ax_r.legend(fontsize="small")

    fig.suptitle(rf"Compaction summary — {potential_name} ({fixed_desc})")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)

    fname = output_dir / f"compaction_summary_vs_{swept_file}__{fixed_desc}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


# ── Ray remote plot dispatch ────────────────────────────────────────────────


@ray.remote
def _plot_trajectory_item(
    traj_proxy, potential, output_dir_str, fmt, run_label: str = ""
):
    """Runs inside a Ray worker: background fields + epsilon plots."""
    traj = traj_proxy.get()
    # sns.set_theme(style="ticks", context="paper")
    sns.set_theme()
    output_dir = Path(output_dir_str)
    units = Planck_units()
    plot_background_fields(traj, potential, units, output_dir, fmt, run_label=run_label)
    plot_epsilon(traj, potential, units, output_dir, fmt, run_label=run_label)


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
    run_label: str = "",
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
        run_label=run_label,
    )


@ray.remote
def _plot_noise_profile_item(
    fi,
    sri,
    N_init_val,
    N_final_val,
    dns_val,
    potential_name,
    output_dir_str,
    fmt,
    cf_annotation=None,
    run_label: str = "",
):
    """Runs inside a Ray worker: noise amplitude sigma_phi1/phi2 vs N plot."""
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_noise_profile(
        fi,
        sri,
        N_init_val,
        N_final_val,
        dns_val,
        potential_name,
        output_dir,
        fmt,
        cf_annotation,
        run_label=run_label,
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
    run_label: str = "",
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
        run_label=run_label,
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
    run_label: str = "",
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
        run_label=run_label,
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
    run_label: str = "",
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
        run_label=run_label,
    )


def _dispatch_plot_work(item):
    """task_builder for RayWorkPool: item is a (remote_fn, args) pair already
    fully prepared by the data-fetch stage; just submit it."""
    remote_fn, args = item
    return remote_fn.remote(*args)


# ── Sweep-direction data fetching ────────────────────────────────────────────


def _instanton_key_payload(traj_proxy, N_init, N_final, dns, atol, rtol, dm):
    return dict(
        trajectory=traj_proxy,
        N_init=N_init,
        N_final=N_final,
        delta_Nstar=dns,
        atol=atol,
        rtol=rtol,
        tags=[],
        diffusion_model=dm,
    )


def _cf_key_payload(traj_proxy, fi_proxy, sri_proxy, dns, cosmo, atol, rtol):
    return dict(
        trajectory=traj_proxy,
        full_instanton=fi_proxy,
        slow_roll_instanton=sri_proxy,
        delta_Nstar=dns,
        cosmo=cosmo,
        C_threshold=0.4,
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


def _extract_cf_summary(cf, units):
    """Return a 12-tuple:
        (C_peak_full, C_bar_peak_full, M_max_full_solar, M_peak_full_solar,
         C_peak_sr,   C_bar_peak_sr,   M_max_sr_solar,   M_peak_sr_solar,
         r_max_full_Mpc, r_peak_full_Mpc,
         r_max_sr_Mpc,   r_peak_sr_Mpc)
    from a CompactionFunction object, or an all-None 12-tuple when unavailable."""
    none12 = (None,) * 12
    if cf is None or not cf.available or cf.failure:
        return none12

    SolarMass = units.SolarMass
    Mpc = units.Mpc

    def _m(v):
        return v / SolarMass if v is not None else None

    def _r(v):
        return v / Mpc if v is not None else None

    return (
        cf.C_peak_full,
        cf.C_bar_peak_full,
        _m(cf.M_max_full),
        _m(cf.M_peak_full),
        cf.C_peak_slow_roll,
        cf.C_bar_peak_slow_roll,
        _m(cf.M_max_slow_roll),
        _m(cf.M_peak_slow_roll),
        _r(cf.r_max_full),
        _r(cf.r_peak_full),
        _r(cf.r_max_slow_roll),
        _r(cf.r_peak_slow_roll),
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
    dm,
    run_label: str = "",
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
                        traj_proxy, v, other_val, dns_val, atol, rtol, dm
                    ),
                    "_do_not_populate": True,
                }
                for v in swept_array
            ]
        else:
            payload_data = [
                {
                    **_instanton_key_payload(
                        traj_proxy, other_val, v, dns_val, atol, rtol, dm
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
                        run_label,
                    ),
                )
            )

        cf_list = _cf_vectorized_fetch(
            pool, traj_proxy, fi_list, sri_list, dns_val, cosmo, atol, rtol
        )
        fi_cf_points = []
        sri_cf_points = []
        c_thresholds = set()
        for sv, cf in zip(swept_vals, cf_list):
            s = _extract_cf_summary(cf, units)
            fi_cf_points.append((sv, s[0], s[1], s[2], s[3], s[8], s[9]))
            sri_cf_points.append((sv, s[4], s[5], s[6], s[7], s[10], s[11]))
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
                        run_label,
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
    dm,
    run_label: str = "",
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
                    traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol, dm
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
                        run_label,
                    ),
                )
            )

        fi_cf_points = []
        sri_cf_points = []
        c_thresholds = set()
        for dns_val in dns_array:
            cf = cf_by_dns[dns_val][combo_idx]
            s = _extract_cf_summary(cf, units)
            dns_float = float(dns_val)
            fi_cf_points.append((dns_float, s[0], s[1], s[2], s[3], s[8], s[9]))
            sri_cf_points.append((dns_float, s[4], s[5], s[6], s[7], s[10], s[11]))
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
                        run_label,
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
    dm,
    combos=None,
    run_label: str = "",
):
    """Sample the full 3-D (N_init × N_final × δN★) grid evenly and emit
    instanton_fields + compaction work items into per-combination sub-folders
    under out_dir/. When combos is provided (CSV mode), use it directly instead
    of building the Cartesian product from N_init_array/N_final_array/dns_array."""
    if combos is None:
        all_combos = list(itertools.product(N_init_array, N_final_array, dns_array))
    else:
        all_combos = combos
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
                    traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol, dm
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
                traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol, dm
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
                        run_label,
                    ),
                )
            )
            work_items.append(
                (
                    _plot_noise_profile_item,
                    (
                        fi_ref,
                        sri_ref,
                        float(N_init_v),
                        float(N_final_v),
                        float(dns_val),
                        potential.name,
                        str(combo_dir),
                        fmt,
                        cf_annotation,
                        run_label,
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
                        run_label,
                    ),
                )
            )


# ── DOE scalar collection and summary plots ───────────────────────────────────


def _collect_doe_scalar_data(
    pool,
    traj_proxy,
    grid_combos,
    cosmo,
    atol,
    rtol,
    units,
    dm,
) -> list:
    """Return a list of dicts (one per available grid point) with scalar summaries.
    Grid points where neither FullInstanton nor SlowRollInstanton is available
    are omitted entirely."""
    if not grid_combos:
        return []

    # Group by dns value (shard key) to allow one vectorized fetch per shard.
    by_dns = {}
    for combo_idx, (N_init_obj, N_final_obj, dns_obj) in enumerate(grid_combos):
        key = float(dns_obj)
        if key not in by_dns:
            by_dns[key] = {"dns_obj": dns_obj, "pairs": []}
        by_dns[key]["pairs"].append((combo_idx, N_init_obj, N_final_obj))

    # Issue vectorized instanton fetches per shard.
    fi_refs = {}
    sri_refs = {}
    for dns_float, group in by_dns.items():
        dns_val = group["dns_obj"]
        pairs = group["pairs"]
        payload_data = [
            {
                **_instanton_key_payload(
                    traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol, dm
                ),
                "_do_not_populate": True,
            }
            for _, N_init_v, N_final_v in pairs
        ]
        fi_refs[dns_float] = pool.object_get_vectorized(
            "FullInstanton", dns_val, payload_data=payload_data
        )
        sri_refs[dns_float] = pool.object_get_vectorized(
            "SlowRollInstanton", dns_val, payload_data=payload_data
        )

    dns_floats = list(by_dns.keys())
    fi_results = ray.get([fi_refs[d] for d in dns_floats])
    sri_results = ray.get([sri_refs[d] for d in dns_floats])
    fi_by_dns = dict(zip(dns_floats, fi_results))
    sri_by_dns = dict(zip(dns_floats, sri_results))

    # Fetch CF scalars per shard.
    cf_by_dns = {}
    for dns_float, group in by_dns.items():
        dns_val = group["dns_obj"]
        fi_list = fi_by_dns[dns_float]
        sri_list = sri_by_dns[dns_float]
        cf_by_dns[dns_float] = _cf_vectorized_fetch(
            pool, traj_proxy, fi_list, sri_list, dns_val, cosmo, atol, rtol
        )

    result = []
    for dns_float, group in by_dns.items():
        dns_val = group["dns_obj"]
        pairs = group["pairs"]
        fi_list = fi_by_dns[dns_float]
        sri_list = sri_by_dns[dns_float]
        cf_list = cf_by_dns[dns_float]

        for local_idx, (_, N_init_obj, N_final_obj) in enumerate(pairs):
            fi_obj = fi_list[local_idx]
            sri_obj = sri_list[local_idx]
            cf_obj = cf_list[local_idx]

            fi_avail = fi_obj is not None and fi_obj.available
            sri_avail = sri_obj is not None and sri_obj.available
            if not fi_avail and not sri_avail:
                continue

            s = _extract_cf_summary(cf_obj, units)
            result.append(
                {
                    "N_init": float(N_init_obj),
                    "N_final": float(N_final_obj),
                    "delta_Nstar": float(dns_val),
                    "delta_N": float(N_init_obj) - float(N_final_obj),
                    "msr_action_full": _qualifying_action(fi_obj),
                    "msr_action_sr": _qualifying_action(sri_obj),
                    "noise_phi1_min_full": fi_obj.noise_phi1_min if fi_avail else None,
                    "noise_phi1_mean_full": fi_obj.noise_phi1_mean
                    if fi_avail
                    else None,
                    "noise_phi1_max_full": fi_obj.noise_phi1_max if fi_avail else None,
                    "noise_phi2_min_full": fi_obj.noise_phi2_min if fi_avail else None,
                    "noise_phi2_mean_full": fi_obj.noise_phi2_mean
                    if fi_avail
                    else None,
                    "noise_phi2_max_full": fi_obj.noise_phi2_max if fi_avail else None,
                    "noise_phi1_min_sr": sri_obj.noise_phi1_min if sri_avail else None,
                    "noise_phi1_mean_sr": sri_obj.noise_phi1_mean
                    if sri_avail
                    else None,
                    "noise_phi1_max_sr": sri_obj.noise_phi1_max if sri_avail else None,
                    "noise_phi2_min_sr": sri_obj.noise_phi2_min if sri_avail else None,
                    "noise_phi2_mean_sr": sri_obj.noise_phi2_mean
                    if sri_avail
                    else None,
                    "noise_phi2_max_sr": sri_obj.noise_phi2_max if sri_avail else None,
                    "C_peak_full": s[0],
                    "C_bar_peak_full": s[1],
                    "M_max_full_solar": s[2],
                    "M_peak_full_solar": s[3],
                    "r_max_full_Mpc": s[8],
                    "r_peak_full_Mpc": s[9],
                    "C_peak_sr": s[4],
                    "C_bar_peak_sr": s[5],
                    "M_max_sr_solar": s[6],
                    "M_peak_sr_solar": s[7],
                    "r_max_sr_Mpc": s[10],
                    "r_peak_sr_Mpc": s[11],
                }
            )

    return result


def plot_doe_scalar_summary(
    data_points,
    potential_name: str,
    output_dir,
    fmt: str,
    threshold: float = 0.4,
    run_label: str = "",
):
    from matplotlib.colors import LogNorm, Normalize
    from matplotlib.lines import Line2D

    if not data_points:
        return

    dns_arr = np.array([d["delta_Nstar"] for d in data_points])
    dN_arr = np.array([d["delta_N"] for d in data_points])

    # ── Figure 1: compaction maxima, MSR action, threshold boundary ───────────
    cb_max_f = [d["C_bar_peak_full"] for d in data_points]
    cb_max_s = [d["C_bar_peak_sr"] for d in data_points]
    c_max_f = [d["C_peak_full"] for d in data_points]
    c_max_s = [d["C_peak_sr"] for d in data_points]
    act_f = [d["msr_action_full"] for d in data_points]
    act_s = [d["msr_action_sr"] for d in data_points]

    any_fig1 = any(
        v is not None for v in cb_max_f + cb_max_s + c_max_f + c_max_s + act_f + act_s
    )
    if any_fig1:
        fig1, axes1 = plt.subplots(2, 2, figsize=(12, 10))

        def _cmp_panel(ax, full_vals, sr_vals, cbar_label, title):
            f_ok = np.array([v is not None for v in full_vals])
            s_ok = np.array([v is not None for v in sr_vals])
            if not f_ok.any() and not s_ok.any():
                return
            v_f = np.array([v for v in full_vals if v is not None], dtype=float)
            v_s = np.array([v for v in sr_vals if v is not None], dtype=float)
            parts = [arr for arr in (v_f, v_s) if len(arr) > 0]
            all_v = np.concatenate(parts)
            vmin, vmax = float(all_v.min()), float(all_v.max())
            if vmin >= vmax:
                vmax = vmin + 1e-9

            sc_ref = None
            if f_ok.any():
                ec = ["red" if v > threshold else "none" for v in v_f]
                sc_ref = ax.scatter(
                    dns_arr[f_ok],
                    dN_arr[f_ok],
                    c=v_f,
                    vmin=vmin,
                    vmax=vmax,
                    cmap="viridis",
                    marker="o",
                    edgecolors=ec,
                    linewidths=0.8,
                    label="Full",
                    zorder=3,
                )
            if s_ok.any():
                ec = ["red" if v > threshold else "none" for v in v_s]
                sc2 = ax.scatter(
                    dns_arr[s_ok],
                    dN_arr[s_ok],
                    c=v_s,
                    vmin=vmin,
                    vmax=vmax,
                    cmap="viridis",
                    marker="^",
                    edgecolors=ec,
                    linewidths=0.8,
                    label="SR",
                    zorder=3,
                )
                if sc_ref is None:
                    sc_ref = sc2

            cb = fig1.colorbar(sc_ref, ax=ax)
            cb.set_label(cbar_label)
            if vmin < threshold < vmax:
                t_norm = (threshold - vmin) / (vmax - vmin)
                cb.ax.axhline(t_norm, color="k", linestyle="--", linewidth=1.0)
            ax.set_xlabel(r"$\delta N_\star$")
            ax.set_ylabel(r"$\Delta N = N_{\rm init} - N_{\rm final}$")
            ax.set_title(title)
            ax.legend(fontsize="small")

        _cmp_panel(
            axes1[0, 0],
            cb_max_f,
            cb_max_s,
            r"$\bar{C}_{\rm peak}$",
            r"$\bar{C}_{\rm peak}$",
        )
        _cmp_panel(axes1[0, 1], c_max_f, c_max_s, r"$C_{\rm peak}$", r"$C_{\rm peak}$")

        # Panel [1,0]: S_MSR with log colorbar
        ax10 = axes1[1, 0]
        f_idx = [i for i, v in enumerate(act_f) if v is not None]
        s_idx = [i for i, v in enumerate(act_s) if v is not None]
        if f_idx or s_idx:
            act_all = [act_f[i] for i in f_idx] + [act_s[i] for i in s_idx]
            pos_vals = [v for v in act_all if v > 0]
            vmin_a = min(pos_vals) if pos_vals else 1e-10
            vmax_a = max(act_all) if act_all else 1.0
            try:
                norm_a = LogNorm(vmin=vmin_a, vmax=max(vmax_a, vmin_a * 1.01))
            except Exception:
                norm_a = Normalize(vmin=vmin_a, vmax=vmax_a)

            sc_a = None
            if f_idx:
                xs = dns_arr[np.array(f_idx)]
                ys = dN_arr[np.array(f_idx)]
                cs = np.array([act_f[i] for i in f_idx])
                sc_a = ax10.scatter(
                    xs,
                    ys,
                    c=cs,
                    norm=norm_a,
                    cmap="plasma",
                    marker="o",
                    label="Full",
                    zorder=3,
                )

            common = [
                (act_f[i], act_s[i])
                for i in range(len(data_points))
                if act_f[i] is not None and act_s[i] is not None
            ]
            sr_differs = any(
                abs(af - asr) / (abs(af) + 1e-30) > 0.01 for af, asr in common
            )
            if (sr_differs or not f_idx) and s_idx:
                xs = dns_arr[np.array(s_idx)]
                ys = dN_arr[np.array(s_idx)]
                cs = np.array([act_s[i] for i in s_idx])
                sc2 = ax10.scatter(
                    xs,
                    ys,
                    c=cs,
                    norm=norm_a,
                    cmap="plasma",
                    marker="^",
                    label="SR",
                    zorder=3,
                )
                if sc_a is None:
                    sc_a = sc2

            if sc_a is not None:
                cb_a = fig1.colorbar(sc_a, ax=ax10)
                cb_a.set_label(r"$S_{\rm MSR}$")
            ax10.legend(fontsize="small")

        ax10.set_xlabel(r"$\delta N_\star$")
        ax10.set_ylabel(r"$\Delta N = N_{\rm init} - N_{\rm final}$")
        ax10.set_title(r"$S_{\rm MSR}$")

        # Panel [1,1]: r_max existence
        ax11 = axes1[1, 1]
        for i, d in enumerate(data_points):
            rmf = d["r_max_full_Mpc"]
            rms = d["r_max_sr_Mpc"]
            xi, yi = dns_arr[i], dN_arr[i]
            ax11.scatter(
                [xi],
                [yi],
                color="green" if rmf is not None else "gray",
                marker="o",
                s=40,
                alpha=1.0 if rmf is not None else 0.4,
                zorder=3,
            )
            ax11.scatter(
                [xi],
                [yi],
                color="green" if rms is not None else "gray",
                marker="^",
                s=40,
                alpha=1.0 if rms is not None else 0.4,
                zorder=3,
            )
        leg_elems = [
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="green",
                label=r"Full: $r_{\rm max}$ exists",
                markersize=8,
            ),
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor="gray",
                label=r"Full: $r_{\rm max}$ absent",
                markersize=8,
            ),
            Line2D(
                [0],
                [0],
                marker="^",
                color="w",
                markerfacecolor="green",
                label=r"SR: $r_{\rm max}$ exists",
                markersize=8,
            ),
            Line2D(
                [0],
                [0],
                marker="^",
                color="w",
                markerfacecolor="gray",
                label=r"SR: $r_{\rm max}$ absent",
                markersize=8,
            ),
        ]
        ax11.legend(handles=leg_elems, fontsize="small")
        ax11.set_xlabel(r"$\delta N_\star$")
        ax11.set_ylabel(r"$\Delta N = N_{\rm init} - N_{\rm final}$")
        ax11.set_title(r"$r_{\rm max}$ (PBH collapse scale) existence")

        fig1.suptitle(f"DOE scalar summary — {potential_name}")
        fig1.tight_layout()
        _provenance_footer(fig1, run_label=run_label)
        fig1.savefig(output_dir / f"doe_compaction_action.{fmt}")
        plt.close(fig1)

    # ── Figure 2: PBH mass and collapse radius ────────────────────────────────
    M_max_f = [d["M_max_full_solar"] for d in data_points]
    M_peak_f = [d["M_peak_full_solar"] for d in data_points]
    M_max_s = [d["M_max_sr_solar"] for d in data_points]
    M_peak_s = [d["M_peak_sr_solar"] for d in data_points]
    r_max_f = [d["r_max_full_Mpc"] for d in data_points]
    r_peak_f = [d["r_peak_full_Mpc"] for d in data_points]
    r_max_s = [d["r_max_sr_Mpc"] for d in data_points]
    r_peak_s = [d["r_peak_sr_Mpc"] for d in data_points]

    any_fig2 = any(
        v is not None
        for v in M_max_f
        + M_peak_f
        + M_max_s
        + M_peak_s
        + r_max_f
        + r_peak_f
        + r_max_s
        + r_peak_s
    )
    if any_fig2:
        fig2, (ax_M, ax_r) = plt.subplots(1, 2, figsize=(12, 5))
        vmin_dN = float(dN_arr.min())
        vmax_dN = float(dN_arr.max())
        if vmin_dN >= vmax_dN:
            vmax_dN = vmin_dN + 1.0

        def _mass_panel(
            ax, full_max_vals, sr_max_vals, full_peak_vals, sr_peak_vals, y_label, title
        ):
            fm_ok = np.array([v is not None and v > 0 for v in full_max_vals])
            sm_ok = np.array([v is not None and v > 0 for v in sr_max_vals])
            fp_ok = np.array([v is not None and v > 0 for v in full_peak_vals])
            sp_ok = np.array([v is not None and v > 0 for v in sr_peak_vals])
            if (
                not fm_ok.any()
                and not sm_ok.any()
                and not fp_ok.any()
                and not sp_ok.any()
            ):
                return None
            sc_ref = None
            if fm_ok.any():
                yf = np.array([v for v in full_max_vals if v is not None and v > 0])
                sc_ref = ax.scatter(
                    dns_arr[fm_ok],
                    yf,
                    c=dN_arr[fm_ok],
                    vmin=vmin_dN,
                    vmax=vmax_dN,
                    cmap="coolwarm",
                    marker="o",
                    label=r"$M_{\rm max}$ (full)",
                    zorder=3,
                )
            if sm_ok.any():
                ys = np.array([v for v in sr_max_vals if v is not None and v > 0])
                sc2 = ax.scatter(
                    dns_arr[sm_ok],
                    ys,
                    c=dN_arr[sm_ok],
                    vmin=vmin_dN,
                    vmax=vmax_dN,
                    cmap="coolwarm",
                    marker="^",
                    label=r"$M_{\rm max}$ (SR)",
                    zorder=3,
                )
                if sc_ref is None:
                    sc_ref = sc2
            if fp_ok.any():
                yf = np.array([v for v in full_peak_vals if v is not None and v > 0])
                sc3 = ax.scatter(
                    dns_arr[fp_ok],
                    yf,
                    c=dN_arr[fp_ok],
                    vmin=vmin_dN,
                    vmax=vmax_dN,
                    cmap="coolwarm",
                    marker="s",
                    label=r"$M_{\rm peak}$ (full)",
                    zorder=3,
                )
                if sc_ref is None:
                    sc_ref = sc3
            if sp_ok.any():
                ys = np.array([v for v in sr_peak_vals if v is not None and v > 0])
                sc4 = ax.scatter(
                    dns_arr[sp_ok],
                    ys,
                    c=dN_arr[sp_ok],
                    vmin=vmin_dN,
                    vmax=vmax_dN,
                    cmap="coolwarm",
                    marker="v",
                    label=r"$M_{\rm peak}$ (SR)",
                    zorder=3,
                )
                if sc_ref is None:
                    sc_ref = sc4
            ax.set_yscale("log")
            ax.set_xlabel(r"$\delta N_\star$")
            ax.set_ylabel(y_label)
            ax.set_title(title)
            ax.legend(fontsize="small")
            return sc_ref

        sc_M = _mass_panel(
            ax_M,
            M_max_f,
            M_max_s,
            M_peak_f,
            M_peak_s,
            r"$M_{\rm PBH}\,/\,M_\odot$",
            "PBH mass",
        )
        sc_r = _mass_panel(
            ax_r,
            r_max_f,
            r_max_s,
            r_peak_f,
            r_peak_s,
            r"$r_{\rm PBH}\,/\,{\rm Mpc}$",
            "PBH collapse scale",
        )

        sc_cb = sc_M if sc_M is not None else sc_r
        if sc_cb is not None:
            cb2 = fig2.colorbar(sc_cb, ax=ax_r)
            cb2.set_label(r"$\Delta N = N_{\rm init} - N_{\rm final}$")

        fig2.suptitle(f"DOE mass and collapse scale — {potential_name}")
        fig2.tight_layout()
        _provenance_footer(fig2, run_label=run_label)
        fig2.savefig(output_dir / f"doe_mass_collapse.{fmt}")
        plt.close(fig2)


@ray.remote
def _plot_doe_summary_item(
    data_points, potential_name, output_dir_str, fmt, threshold, run_label: str = ""
):
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_doe_scalar_summary(
        data_points, potential_name, output_dir, fmt, threshold, run_label=run_label
    )


def _run_doe_summary_plots(
    pool,
    traj_proxy,
    potential,
    traj_dir,
    fmt: str,
    grid_combos,
    cosmo,
    atol,
    rtol,
    units,
    dm,
    work_items: list,
    threshold: float = 0.4,
    run_label: str = "",
):
    print(f"   >> Collecting scalar summaries for {len(grid_combos)} grid point(s)...")
    data_points = _collect_doe_scalar_data(
        pool, traj_proxy, grid_combos, cosmo, atol, rtol, units, dm
    )
    if not data_points:
        print("   >> No data found — skipping DOE summary plots and CSV.")
        return

    print(f"   >> {len(data_points)} point(s) with data; queuing DOE summary plots.")
    doe_dir = traj_dir / "doe_summary"
    doe_dir.mkdir(parents=True, exist_ok=True)

    work_items.append(
        (
            _plot_doe_summary_item,
            (data_points, potential.name, str(doe_dir), fmt, threshold, run_label),
        )
    )

    import csv

    csv_path = doe_dir / "scalar_data.csv"
    fieldnames = list(data_points[0].keys())
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_points)
    print(f"   >> Scalar data written to {csv_path}")


# ── Main pipeline ─────────────────────────────────────────────────────────────


def run_plots(pool, units, args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = args.format

    # ── Run provenance label ──────────────────────────────────────────────
    _db_stem = Path(args.database).name
    _cfg_stem = Path(args.config).name if getattr(args, "config", None) else None
    _flags = []
    if getattr(args, "no_store_values", False):
        _flags.append("[summary-only]")
    _run_label_parts = [p for p in [_db_stem, _cfg_stem] if p]
    if _flags:
        _run_label_parts.append(" ".join(_flags))
    run_label = "  |  ".join(_run_label_parts)

    print("\n>> Building pipeline inputs...")
    if getattr(args, "sample_grid_csv", None):
        print(
            f"   -- sample-grid-csv: active — "
            f"N_init/N_final/delta_Nstar taken from '{args.sample_grid_csv}'"
        )
    inputs = build_pipeline_inputs(pool, units, args)
    atol, rtol = inputs["atol"], inputs["rtol"]
    N_init_array = inputs["N_init_array"]
    N_final_array = inputs["N_final_array"]
    dns_array = inputs["dns_array"]
    model_list = inputs["model_list"]

    selected_models = _evenly_sample(model_list, args.max_trajectories)
    # Map each selected model back to its index in model_list (needed to filter
    # CSV grid tuples per trajectory; _evenly_sample returns elements by reference).
    id_to_model_idx = {id(m): i for i, m in enumerate(model_list)}
    selected_model_indices = [id_to_model_idx[id(sm)] for sm in selected_models]

    print(f"\n>> Fetching {len(selected_models)} trajectory record(s)...")
    raw_trajs = ray.get(
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
    # Preserve the model_idx for each trajectory so CSV tuples can be filtered
    # per trajectory inside the loop.
    filtered = [
        (selected_model_indices[i], t)
        for i, t in enumerate(raw_trajs)
        if t.available and t._potential is not None
    ]
    traj_list = [t for _, t in filtered]
    traj_model_indices = [idx for idx, _ in filtered]
    print(f"   {len(traj_list)} trajectory record(s) found in database")

    if not traj_list:
        print("No trajectories found. Run main.py first.")
        return

    csv_mode = getattr(args, "sample_grid_csv", None)

    if not csv_mode and not dns_array:
        print("No delta_Nstar values found. Run main.py first.")
        return

    print("\n>> Reading cosmological parameters...")
    cosmo = ray.get(pool.object_get("CosmologicalParams", params=Planck2018()))
    print(f"   Cosmological parameters: {cosmo.name} (store_id={cosmo.store_id})")

    dm = ray.get(pool.object_get("MasslessDecoupledDiffusion"))
    print(f"   Diffusion model: {dm.name} (store_id={dm.store_id})")

    max_combos = args.max_combinations
    max_instanton_samples = args.max_instanton_samples

    if csv_mode:
        csv_grid = build_instanton_grid(
            pool, model_list, args, N_init_array, N_final_array, dns_array
        )
        if not csv_grid:
            print("No grid points found in --sample-grid-csv. Nothing to plot.")
            return
    else:
        csv_grid = None

    work_items = []
    for traj_idx, traj in enumerate(traj_list):
        potential = traj._potential
        traj_proxy = InflatonTrajectoryProxy(traj)
        traj_dir = output_dir / f"{_safe_name(potential.name)}_traj{traj.store_id}"
        traj_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n>> Trajectory {traj.store_id} ({potential.name}) -> {traj_dir}/")

        work_items.append(
            (
                _plot_trajectory_item,
                (traj_proxy, potential, str(traj_dir), fmt, run_label),
            )
        )

        if csv_grid is not None:
            model_idx = traj_model_indices[traj_idx]
            traj_combos = [
                (N_init, N_final, dns)
                for (midx, N_init, N_final, dns) in csv_grid
                if midx == model_idx
            ]
            if not traj_combos:
                print(
                    f"   Skipping trajectory {traj.store_id}: no grid combos for this model."
                )
                continue
        else:
            traj_combos = None

        if args.no_store_values:
            print(
                "   >> --no-store-values active: skipping per-instanton field and "
                "compaction-profile plots (value rows were not stored)."
            )
        else:
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
                dm=dm,
                combos=traj_combos,
                run_label=run_label,
            )

        if csv_grid is not None:
            seen_init, seen_final, seen_dns = {}, {}, {}
            for N_init_obj, N_final_obj, dns_obj in traj_combos:
                seen_init.setdefault(float(N_init_obj), N_init_obj)
                seen_final.setdefault(float(N_final_obj), N_final_obj)
                seen_dns.setdefault(float(dns_obj), dns_obj)
            eff_N_init = [v for _, v in sorted(seen_init.items())]
            eff_N_final = [v for _, v in sorted(seen_final.items())]
            eff_dns = [v for _, v in sorted(seen_dns.items())]
            print(
                "   >> --sample-grid-csv active: sweep plots will reflect sparse DOE coverage"
            )
        else:
            eff_N_init = N_init_array
            eff_N_final = N_final_array
            eff_dns = dns_array

        _sweep_Ninit_or_Nfinal(
            pool,
            traj_proxy,
            potential,
            traj_dir / "N-init",
            fmt,
            swept_name="N_init",
            swept_array=eff_N_init,
            fixed_other_array=eff_N_final,
            dns_array=eff_dns,
            atol=atol,
            rtol=rtol,
            max_combos=max_combos,
            work_items=work_items,
            cosmo=cosmo,
            units=units,
            dm=dm,
            run_label=run_label,
        )
        _sweep_Ninit_or_Nfinal(
            pool,
            traj_proxy,
            potential,
            traj_dir / "N-final",
            fmt,
            swept_name="N_final",
            swept_array=eff_N_final,
            fixed_other_array=eff_N_init,
            dns_array=eff_dns,
            atol=atol,
            rtol=rtol,
            max_combos=max_combos,
            work_items=work_items,
            cosmo=cosmo,
            units=units,
            dm=dm,
            run_label=run_label,
        )
        _sweep_delta_Nstar(
            pool,
            traj_proxy,
            potential,
            traj_dir / "delta-Nstar",
            fmt,
            dns_array=eff_dns,
            N_init_array=eff_N_init,
            N_final_array=eff_N_final,
            atol=atol,
            rtol=rtol,
            max_combos=max_combos,
            work_items=work_items,
            cosmo=cosmo,
            units=units,
            dm=dm,
            run_label=run_label,
        )

        grid_combos = (
            traj_combos
            if csv_grid is not None
            else list(itertools.product(N_init_array, N_final_array, dns_array))
        )
        _run_doe_summary_plots(
            pool=pool,
            traj_proxy=traj_proxy,
            potential=potential,
            traj_dir=traj_dir,
            fmt=fmt,
            grid_combos=grid_combos,
            cosmo=cosmo,
            atol=atol,
            rtol=rtol,
            units=units,
            dm=dm,
            work_items=work_items,
            threshold=0.4,
            run_label=run_label,
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
