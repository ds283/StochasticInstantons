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

from matplotlib import pyplot as plt

from plotting.provenance import _provenance_footer

# Adapter-driven (P2b retrofit): each function takes a flat list of
# InstantonAdapter instances -- one adapter per (swept x-value, solver kind)
# -- grouped by `display_label` (never `.kind`) into one line/series per
# solver. Overlaying a further kind (e.g. GCI) is just a longer `adapters`
# list; neither function needs to change.


def plot_msr_action_sweep(
    adapters,
    x_label,
    fixed_desc,
    potential_name,
    output_dir,
    fmt,
    swept_name,
    run_label: str = "",
):
    """One trajectory's MSR action vs the swept dimension, at one fixed
    combination of the other two dimensions (described by fixed_desc).
    `adapters`: a flat list of InstantonAdapter, one per (swept x-value,
    solver kind); the swept x-value for each adapter is read from
    `a.coords[swept_name]`."""
    live = [a for a in adapters if a.available and not a.failure]
    groups: dict = {}
    for a in live:
        groups.setdefault(a.display_label, []).append(a)

    series = {}
    for label, group in groups.items():
        pts = sorted(
            (a.coords[swept_name], a.scalars().get("msr_action")) for a in group
        )
        pts = [(x, y) for x, y in pts if y is not None]
        if pts:
            series[label] = pts

    if not series:
        return

    max_pts = max(len(pts) for pts in series.values())
    use_markers = max_pts <= 25

    fig, ax = plt.subplots(figsize=(7, 5.5))
    for label, pts in series.items():
        marker = groups[label][0].marker
        line_style = groups[label][0].line_style
        fmt_str = f"{marker}{line_style}" if use_markers else line_style
        xs, ys = zip(*pts)
        ax.semilogy(xs, ys, fmt_str, label=f"{label} MSR")

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


def plot_compaction_summary(
    adapters,
    x_label,
    fixed_desc,
    potential_name,
    output_dir,
    fmt,
    swept_name,
    threshold=None,
    run_label: str = "",
):
    """Two-panel summary: left = max C and max C̄ vs swept parameter;
    right = PBH mass in solar masses (log y-scale) vs swept parameter.
    `adapters`: a flat list of InstantonAdapter, one per (swept x-value,
    solver kind). If `threshold` is None, it is derived from the adapters'
    own `scalars()["C_threshold"]` values (warning if they disagree, taking
    the smallest) -- the driver no longer needs to aggregate this itself."""
    swept_file = {"N_init": "Ninit", "N_final": "Nfinal", "delta_Nstar": "dNstar"}[
        swept_name
    ]

    live = [a for a in adapters if a.available and not a.failure]
    groups: dict = {}
    for a in live:
        groups.setdefault(a.display_label, []).append(a)

    def _series(group, key):
        pts = sorted((a.coords[swept_name], a.scalars().get(key)) for a in group)
        pts = [(x, y) for x, y in pts if y is not None]
        if not pts:
            return [], []
        xs, ys = zip(*pts)
        return list(xs), list(ys)

    series_by_group = {
        label: {
            "C_peak": _series(group, "C_peak"),
            "C_bar_peak": _series(group, "C_bar_peak"),
            "M_max_solar": _series(group, "M_max_solar"),
            "M_peak_solar": _series(group, "M_peak_solar"),
            "r_max_Mpc": _series(group, "r_max_Mpc"),
            "r_peak_Mpc": _series(group, "r_peak_Mpc"),
        }
        for label, group in groups.items()
    }

    has_C_data = any(
        len(s["C_peak"][0]) > 0 or len(s["C_bar_peak"][0]) > 0
        for s in series_by_group.values()
    )
    has_M_data = any(
        len(s["M_max_solar"][0]) > 0 or len(s["M_peak_solar"][0]) > 0
        for s in series_by_group.values()
    )
    has_r_data = any(
        len(s["r_max_Mpc"][0]) > 0 or len(s["r_peak_Mpc"][0]) > 0
        for s in series_by_group.values()
    )
    if not has_C_data and not has_M_data and not has_r_data:
        return

    if threshold is None:
        thresholds = {a.scalars().get("C_threshold") for a in live} - {None}
        if len(thresholds) == 1:
            threshold = next(iter(thresholds))
        elif len(thresholds) > 1:
            print(
                f"  Warning: C_threshold varies across sweep: {sorted(thresholds)}. "
                "Using smallest value."
            )
            threshold = sorted(thresholds)[0]
    threshold_val = threshold if threshold is not None else 0.4

    max_pts = max(
        (len(s[key][0]) for s in series_by_group.values() for key in s), default=0
    )
    use_markers = max_pts <= 25

    fig, (ax_C, ax_M, ax_r) = plt.subplots(1, 3, figsize=(15, 5))

    for label, group in groups.items():
        marker = group[0].marker
        s = series_by_group[label]
        solid = f"{marker}-" if use_markers else "-"
        dashed = f"{marker}--" if use_markers else "--"

        xs, ys = s["C_peak"]
        if xs:
            ax_C.plot(xs, ys, solid, label=rf"$C_{{\rm peak}}$ ({label})")
        xs, ys = s["C_bar_peak"]
        if xs:
            ax_C.plot(xs, ys, dashed, label=rf"$\bar{{C}}_{{\rm peak}}$ ({label})")

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

    for label, group in groups.items():
        marker = group[0].marker
        s = series_by_group[label]
        solid = f"{marker}-" if use_markers else "-"
        dashed = f"{marker}--" if use_markers else "--"

        xs, ys = s["M_max_solar"]
        if xs:
            ax_M.semilogy(xs, ys, solid, label=rf"$M_{{\rm max}}$ ({label})")
        xs, ys = s["M_peak_solar"]
        if xs:
            ax_M.semilogy(xs, ys, dashed, label=rf"$M_{{\rm peak}}$ ({label})")

    ax_M.set_xlabel(x_label)
    ax_M.set_ylabel(r"$M_{\rm PBH}\,/\,M_\odot$")
    ax_M.set_title("PBH mass")
    if has_M_data:
        ax_M.legend(fontsize="small")

    for label, group in groups.items():
        marker = group[0].marker
        s = series_by_group[label]
        solid = f"{marker}-" if use_markers else "-"
        dashed = f"{marker}--" if use_markers else "--"

        xs, ys = s["r_max_Mpc"]
        if xs:
            ax_r.semilogy(xs, ys, solid, label=rf"$r_{{\rm max}}$ ({label})")
        xs, ys = s["r_peak_Mpc"]
        if xs:
            ax_r.semilogy(xs, ys, dashed, label=rf"$r_{{\rm peak}}$ ({label})")

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
