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

import numpy as np
from matplotlib import pyplot as plt

from plotting.provenance import _provenance_footer

# Not yet converted to consume `InstantonAdapter` instances: `data_points` is
# a flat list of dicts (one per grid combination), each already combining
# both Full and SR scalars via `_full`/`_sr`-suffixed keys -- built by
# `_collect_doe_scalar_data` (still in plot_InstantonSolutions.py) across many
# separate datastore fetches, not a single materialised compute-target object
# per render call. See the same note in plotting/figures/sweeps.py.


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
