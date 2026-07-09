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

# Adapter-driven (P2b retrofit): `points` is a list of per-grid-point dicts
# {"delta_Nstar": float, "delta_N": float, "adapters": [InstantonAdapter, ...]}
# -- built by `plotting.fetch.collect_doe_scalar_points`. The scatter's (x,y)
# position is a property of the grid point (shared across every solver kind
# there); series identity (colour/marker/legend label) is read off each
# point's adapters, grouped by `display_label` (never `.kind`), so adding a
# further solver kind to each point's `adapters` list is the entire diff
# needed to overlay it here.

# `_mass_panel` colour-maps a third variable (dN) on the same scatter as the
# max/peak split, and matplotlib can't combine a colormap fill with a hollow
# marker -- so there, quantity (max vs peak) rides on a marker-shape variant
# of the kind's own marker, not on fill. Reproduces today's exact o/s (full)
# and ^/v (SR) choices; a marker without a listed variant falls back to
# itself (max and peak coincide visually for that kind).
_PEAK_MARKER_VARIANT = {"o": "s", "^": "v", "s": "D", "v": "P", "D": "X", "P": "*"}


def plot_doe_scalar_summary(
    points,
    potential_name: str,
    output_dir,
    fmt: str,
    threshold: float = 0.4,
    run_label: str = "",
):
    from matplotlib.colors import LogNorm, Normalize
    from matplotlib.lines import Line2D

    if not points:
        return

    dns_arr = np.array([p["delta_Nstar"] for p in points])
    dN_arr = np.array([p["delta_N"] for p in points])

    # Distinct solver-kind groups present, in first-seen order (matches
    # today's Full-before-SR panel/legend ordering, since each point's
    # adapters list is built [full, slow-roll]).
    group_order = []
    group_marker: dict = {}
    for p in points:
        for a in p["adapters"]:
            if a.display_label not in group_marker:
                group_marker[a.display_label] = a.marker
                group_order.append(a.display_label)

    def _values_by_group(key):
        result = {label: [None] * len(points) for label in group_order}
        for i, p in enumerate(points):
            for a in p["adapters"]:
                result[a.display_label][i] = a.scalars().get(key)
        return result

    # ── Figure 1: compaction maxima, MSR action, threshold boundary ───────────
    cb_max = _values_by_group("C_bar_peak")
    c_max = _values_by_group("C_peak")
    act = _values_by_group("msr_action")

    any_fig1 = any(
        v is not None
        for series in (cb_max, c_max, act)
        for vals in series.values()
        for v in vals
    )
    if any_fig1:
        fig1, axes1 = plt.subplots(2, 2, figsize=(12, 10))

        def _cmp_panel(ax, values_by_group, cbar_label, title):
            ok_by_group = {
                label: np.array([v is not None for v in vals])
                for label, vals in values_by_group.items()
            }
            if not any(ok.any() for ok in ok_by_group.values()):
                return
            all_v = np.concatenate(
                [
                    np.array(
                        [v for v in values_by_group[label] if v is not None],
                        dtype=float,
                    )
                    for label in group_order
                    if ok_by_group[label].any()
                ]
            )
            vmin, vmax = float(all_v.min()), float(all_v.max())
            if vmin >= vmax:
                vmax = vmin + 1e-9

            sc_ref = None
            for label in group_order:
                ok = ok_by_group[label]
                if not ok.any():
                    continue
                v = np.array(
                    [values_by_group[label][i] for i in range(len(points)) if ok[i]],
                    dtype=float,
                )
                ec = ["red" if vv > threshold else "none" for vv in v]
                sc = ax.scatter(
                    dns_arr[ok],
                    dN_arr[ok],
                    c=v,
                    vmin=vmin,
                    vmax=vmax,
                    cmap="viridis",
                    marker=group_marker[label],
                    edgecolors=ec,
                    linewidths=0.8,
                    label=label,
                    zorder=3,
                )
                if sc_ref is None:
                    sc_ref = sc

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
            axes1[0, 0], cb_max, r"$\bar{C}_{\rm peak}$", r"$\bar{C}_{\rm peak}$"
        )
        _cmp_panel(axes1[0, 1], c_max, r"$C_{\rm peak}$", r"$C_{\rm peak}$")

        # Panel [1,0]: S_MSR with log colorbar
        ax10 = axes1[1, 0]
        idx_by_group = {
            label: [i for i, v in enumerate(vals) if v is not None]
            for label, vals in act.items()
        }
        if any(idx_by_group.values()):
            act_all = [act[label][i] for label in group_order for i in idx_by_group[label]]
            pos_vals = [v for v in act_all if v > 0]
            vmin_a = min(pos_vals) if pos_vals else 1e-10
            vmax_a = max(act_all) if act_all else 1.0
            try:
                norm_a = LogNorm(vmin=vmin_a, vmax=max(vmax_a, vmin_a * 1.01))
            except Exception:
                norm_a = Normalize(vmin=vmin_a, vmax=vmax_a)

            sc_a = None
            for label in group_order:
                idx = idx_by_group[label]
                if not idx:
                    continue
                xs = dns_arr[np.array(idx)]
                ys = dN_arr[np.array(idx)]
                cs = np.array([act[label][i] for i in idx])
                sc = ax10.scatter(
                    xs,
                    ys,
                    c=cs,
                    norm=norm_a,
                    cmap="plasma",
                    marker=group_marker[label],
                    label=label,
                    zorder=3,
                )
                if sc_a is None:
                    sc_a = sc

            if sc_a is not None:
                cb_a = fig1.colorbar(sc_a, ax=ax10)
                cb_a.set_label(r"$S_{\rm MSR}$")
            ax10.legend(fontsize="small")

        ax10.set_xlabel(r"$\delta N_\star$")
        ax10.set_ylabel(r"$\Delta N = N_{\rm init} - N_{\rm final}$")
        ax10.set_title(r"$S_{\rm MSR}$")

        # Panel [1,1]: r_max existence
        ax11 = axes1[1, 1]
        r_max_exists = _values_by_group("r_max_Mpc")
        for i in range(len(points)):
            xi, yi = dns_arr[i], dN_arr[i]
            for label in group_order:
                v = r_max_exists[label][i]
                ax11.scatter(
                    [xi],
                    [yi],
                    color="green" if v is not None else "gray",
                    marker=group_marker[label],
                    s=40,
                    alpha=1.0 if v is not None else 0.4,
                    zorder=3,
                )
        leg_elems = []
        for label in group_order:
            for exists, color in ((True, "green"), (False, "gray")):
                leg_elems.append(
                    Line2D(
                        [0],
                        [0],
                        marker=group_marker[label],
                        color="w",
                        markerfacecolor=color,
                        label=rf"{label}: $r_{{\rm max}}$ "
                        + ("exists" if exists else "absent"),
                        markersize=8,
                    )
                )
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
    M_max = _values_by_group("M_max_solar")
    M_peak = _values_by_group("M_peak_solar")
    r_max = _values_by_group("r_max_Mpc")
    r_peak = _values_by_group("r_peak_Mpc")

    any_fig2 = any(
        v is not None
        for series in (M_max, M_peak, r_max, r_peak)
        for vals in series.values()
        for v in vals
    )
    if any_fig2:
        fig2, (ax_M, ax_r) = plt.subplots(1, 2, figsize=(12, 5))
        vmin_dN = float(dN_arr.min())
        vmax_dN = float(dN_arr.max())
        if vmin_dN >= vmax_dN:
            vmax_dN = vmin_dN + 1.0

        def _mass_panel(ax, max_by_group, peak_by_group, sym_max, sym_peak, y_label, title):
            sc_ref = None
            for label in group_order:
                marker = group_marker[label]
                max_vals = max_by_group[label]
                peak_vals = peak_by_group[label]

                ok_max = np.array([v is not None and v > 0 for v in max_vals])
                if ok_max.any():
                    y = np.array([v for v in max_vals if v is not None and v > 0])
                    sc = ax.scatter(
                        dns_arr[ok_max],
                        y,
                        c=dN_arr[ok_max],
                        vmin=vmin_dN,
                        vmax=vmax_dN,
                        cmap="coolwarm",
                        marker=marker,
                        label=rf"${sym_max}$ ({label})",
                        zorder=3,
                    )
                    if sc_ref is None:
                        sc_ref = sc

                ok_peak = np.array([v is not None and v > 0 for v in peak_vals])
                if ok_peak.any():
                    y = np.array([v for v in peak_vals if v is not None and v > 0])
                    sc = ax.scatter(
                        dns_arr[ok_peak],
                        y,
                        c=dN_arr[ok_peak],
                        vmin=vmin_dN,
                        vmax=vmax_dN,
                        cmap="coolwarm",
                        marker=_PEAK_MARKER_VARIANT.get(marker, marker),
                        label=rf"${sym_peak}$ ({label})",
                        zorder=3,
                    )
                    if sc_ref is None:
                        sc_ref = sc

            if sc_ref is None:
                return None
            ax.set_yscale("log")
            ax.set_xlabel(r"$\delta N_\star$")
            ax.set_ylabel(y_label)
            ax.set_title(title)
            ax.legend(fontsize="small")
            return sc_ref

        sc_M = _mass_panel(
            ax_M,
            M_max,
            M_peak,
            r"M_{\rm max}",
            r"M_{\rm peak}",
            r"$M_{\rm PBH}\,/\,M_\odot$",
            "PBH mass",
        )
        sc_r = _mass_panel(
            ax_r,
            r_max,
            r_peak,
            r"r_{\rm max}",
            r"r_{\rm peak}",
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
