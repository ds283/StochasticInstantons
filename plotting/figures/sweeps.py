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

# Not yet converted to consume `InstantonAdapter` instances: unlike
# plot_instanton_fields/plot_noise_profile/plot_zeta_and_compaction, these two
# functions are fed pre-aggregated (x, scalar) points collected across many
# separate datastore fetches by `_sweep_Ninit_or_Nfinal`/`_sweep_delta_Nstar`
# (still in plot_InstantonSolutions.py), not a single materialised
# FullInstanton/SlowRollInstanton/CompactionFunction per render call -- there
# is no adapter-able object at this function's call site to convert. That
# fetch-side aggregation is out of this prompt's scope (see the P2 prompt's
# "Files" list: plotting/fetch.py is not touched here).


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
