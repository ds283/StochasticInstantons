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
Diagnostics as first-class figures (design doc
`.documents/gradient-coupled-plotting/DESIGN_gradient_coupled_plotting.md`,
§8; see the P7 prompt,
`.prompts/gradient-coupled-plotting/12-P7-diagnostics-figures.md`).

Adapter-driven, same convention as `plotting/figures/sweeps.py` and
`plotting/figures/doe.py`: every entry point below takes a flat list of
`InstantonAdapter` instances -- one adapter per grid point per solver kind --
grouped by `display_label` (never `.kind`). Overlaying a further solver is
just a longer `adapters` list; none of these functions need to change.

Every value plotted here is read verbatim off `adapter.diagnostics()` (a pure
read of the persisted `diagnostics_json` blob -- no recomputation) or off
`adapter.coords` (the query-context grid coordinates). GCI-specific keys
(`rk45_*`, `scale_assignment`, `extraction_failure_mask`,
`compute_time_total`, `picard_sweep_wallclock_*`) are read with `.get(...)`
and gated on their *presence*, never on `adapter.kind == "gradient-coupled"`
-- so a figure that happens to find these keys on some future non-GCI solver
would simply include it, and a GCI adapter missing one (e.g. a
`disable_spatial_coupling` run) is silently skipped for that panel rather
than raising.

Items 6-7 (Picard/Newton structure, RK45 stiffness) key off cheap-tier
`diagnostics()` alone. Item 8 (extraction-failure map, both the
grid-point-level summary and the per-node heatmap) is gated additionally on
`adapter.is_spatial()`, per the P7 prompt's explicit instruction -- even
though the summary panel's own input (`extraction_failure_mask`) rides on
the same cheap `diagnostics_json` blob, keeping the whole family behind one
uniform "dense fidelity" gate is simpler than half-gating it.

Nine figure "families" total: items 2-8 below (7 render functions, with
item 8 split into a summary panel and a per-node heatmap, i.e. 8 entry
points) plus item 9's `diagnostics_data.csv` companion
(`plotting.fetch.flatten_diagnostics_for_csv`, not in this file).
"""

from collections import Counter

import numpy as np
from matplotlib import pyplot as plt

from plotting.provenance import _provenance_footer


def _live_adapters(adapters):
    return [a for a in adapters if a.available]


def _group_by_label(adapters):
    """Returns (order, groups): `order` is display labels in first-seen
    order (matches doe.py/sweeps.py's own convention); `groups` maps each
    label to its list of adapters."""
    order = []
    groups: dict = {}
    for a in adapters:
        if a.display_label not in groups:
            groups[a.display_label] = []
            order.append(a.display_label)
        groups[a.display_label].append(a)
    return order, groups


def _delta_N(a):
    """ΔN = N_init - N_final, read from `a.coords` -- the same quantity
    doe.py/sweeps.py plot on their own y/x axes. `None` if either coordinate
    is absent."""
    N_init = a.coords.get("N_init")
    N_final = a.coords.get("N_final")
    if N_init is None or N_final is None:
        return None
    return float(N_init) - float(N_final)


# ── Item 2: compute-time distributions ───────────────────────────────────────


def plot_compute_time_distributions(adapters, potential_name, output_dir, fmt, run_label=""):
    """Per-solver compute-time histograms, split converged vs non-converged,
    with the median of each split marked (design §8 item 1: "the compute-times
    figure ... becomes one function in this family, fed by adapters instead
    of FI-specific code")."""
    live = _live_adapters(adapters)
    order, groups = _group_by_label(live)

    series = {}
    for label in order:
        conv_times, nonconv_times = [], []
        for a in groups[label]:
            d = a.diagnostics()
            if d is None:
                continue
            t = d.get("compute_time")
            if t is None:
                continue
            if d.get("converged") is False:
                nonconv_times.append(t)
            else:
                conv_times.append(t)
        if conv_times or nonconv_times:
            series[label] = (conv_times, nonconv_times)

    if not series:
        return

    fig, axes = plt.subplots(1, len(series), figsize=(5 * len(series), 5), squeeze=False)
    for ax, label in zip(axes[0], series.keys()):
        conv_times, nonconv_times = series[label]
        if conv_times:
            ax.hist(
                conv_times, bins=min(10, max(3, len(conv_times))), alpha=0.6,
                color="tab:blue", label=f"converged (n={len(conv_times)})",
            )
            ax.axvline(float(np.median(conv_times)), color="tab:blue", linestyle="--")
        if nonconv_times:
            ax.hist(
                nonconv_times, bins=min(10, max(3, len(nonconv_times))), alpha=0.6,
                color="tab:red", label=f"non-converged (n={len(nonconv_times)})",
            )
            ax.axvline(float(np.median(nonconv_times)), color="tab:red", linestyle="--")
        ax.set_xlabel("compute time / s")
        ax.set_ylabel("count")
        ax.set_title(label)
        ax.legend(fontsize="small")

    fig.suptitle(f"Compute-time distributions — {potential_name}")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)
    fig.savefig(output_dir / f"diagnostics_compute_time_distributions.{fmt}")
    plt.close(fig)


# ── Item 3: cost vs parameters ───────────────────────────────────────────────


def plot_cost_vs_parameters(adapters, potential_name, output_dir, fmt, run_label=""):
    """Compute-time and `total_ode_solves` over the (δN★, ΔN) plane, coloured
    by cost -- one marker shape per solver kind (design §8 item 2), reusing
    doe.py's own colour-mapped-scatter convention."""
    live = _live_adapters(adapters)

    def _panel_data(diag_key):
        xs, ys, cs, markers = [], [], [], []
        for a in live:
            dns = a.coords.get("delta_Nstar")
            dN = _delta_N(a)
            d = a.diagnostics()
            v = d.get(diag_key) if d is not None else None
            if dns is None or dN is None or v is None:
                continue
            xs.append(dns)
            ys.append(dN)
            cs.append(v)
            markers.append(a.marker)
        return xs, ys, cs, markers

    ct_xs, ct_ys, ct_cs, ct_markers = _panel_data("compute_time")
    tos_xs, tos_ys, tos_cs, tos_markers = _panel_data("total_ode_solves")

    if not ct_xs and not tos_xs:
        return

    fig, (ax_ct, ax_tos) = plt.subplots(1, 2, figsize=(12, 5.5))

    def _draw(ax, xs, ys, cs, markers, cbar_label, title):
        if not xs:
            ax.set_title(f"{title} (no data)")
            return
        vmin, vmax = min(cs), max(cs)
        if vmin >= vmax:
            vmax = vmin + 1e-9
        sc = None
        for marker in sorted(set(markers)):
            idx = [i for i, m in enumerate(markers) if m == marker]
            sc = ax.scatter(
                [xs[i] for i in idx], [ys[i] for i in idx], c=[cs[i] for i in idx],
                vmin=vmin, vmax=vmax, cmap="viridis", marker=marker,
            )
        cb = fig.colorbar(sc, ax=ax)
        cb.set_label(cbar_label)
        ax.set_xlabel(r"$\delta N_\star$")
        ax.set_ylabel(r"$\Delta N$")
        ax.set_title(title)

    _draw(ax_ct, ct_xs, ct_ys, ct_cs, ct_markers, "compute time / s", "Compute time")
    _draw(ax_tos, tos_xs, tos_ys, tos_cs, tos_markers, "total ODE solves", "Total ODE solves")

    fig.suptitle(f"Solver cost vs grid parameters — {potential_name}")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)
    fig.savefig(output_dir / f"diagnostics_cost_vs_parameters.{fmt}")
    plt.close(fig)


# ── Item 4: convergence map ───────────────────────────────────────────────────


def plot_convergence_map(adapters, potential_name, output_dir, fmt, run_label=""):
    """Converged/non-converged scatter over (δN★, ΔN), one marker shape per
    solver kind (design §8 item 3). For GCI, additionally facets over
    (alpha, n_collocation_points) whenever more than one such combination is
    present -- read off `adapter.coords`, never assumed."""
    live = _live_adapters(adapters)
    order, groups = _group_by_label(live)

    splits = {}
    any_data = False
    for label in order:
        cx, cy, nx, ny = [], [], [], []
        for a in groups[label]:
            dns = a.coords.get("delta_Nstar")
            dN = _delta_N(a)
            d = a.diagnostics()
            if dns is None or dN is None or d is None:
                continue
            converged = d.get("converged")
            if converged is None:
                continue
            if converged:
                cx.append(dns)
                cy.append(dN)
            else:
                nx.append(dns)
                ny.append(dN)
        if cx or nx:
            splits[label] = (cx, cy, nx, ny)
            any_data = True

    if any_data:
        fig, ax = plt.subplots(figsize=(7, 5.5))
        for label, (cx, cy, nx, ny) in splits.items():
            marker = groups[label][0].marker
            if cx:
                ax.scatter(cx, cy, marker=marker, color="tab:green", label=f"{label}: converged")
            if nx:
                ax.scatter(nx, ny, marker=marker, color="tab:red", label=f"{label}: non-converged")

        ax.set_xlabel(r"$\delta N_\star$")
        ax.set_ylabel(r"$\Delta N$")
        ax.set_title(f"Convergence map — {potential_name}")
        ax.legend(fontsize="small")
        fig.tight_layout()
        _provenance_footer(fig, run_label=run_label)
        fig.savefig(output_dir / f"diagnostics_convergence_map.{fmt}")
        plt.close(fig)

    _plot_convergence_map_gci_facets(live, potential_name, output_dir, fmt, run_label)


def _plot_convergence_map_gci_facets(adapters, potential_name, output_dir, fmt, run_label):
    """GCI-only facet grid over (alpha, n_collocation_points) -- gated on
    those coords keys being present (i.e. this adapter carries a GCI-shaped
    `coords` dict), never on `.kind`. Silently no-ops if fewer than two
    distinct combinations were actually fetched."""
    gci_like = [a for a in adapters if "alpha" in a.coords and "n_collocation_points" in a.coords]
    if not gci_like:
        return
    facets = sorted({(a.coords["alpha"], a.coords["n_collocation_points"]) for a in gci_like})
    if len(facets) < 2:
        return

    fig, axes = plt.subplots(1, len(facets), figsize=(5 * len(facets), 5), squeeze=False)
    for ax, (alpha, n_colloc) in zip(axes[0], facets):
        facet_adapters = [
            a for a in gci_like
            if a.coords["alpha"] == alpha and a.coords["n_collocation_points"] == n_colloc
        ]
        for a in facet_adapters:
            dns = a.coords.get("delta_Nstar")
            dN = _delta_N(a)
            d = a.diagnostics()
            if dns is None or dN is None or d is None:
                continue
            converged = d.get("converged")
            if converged is None:
                continue
            color = "tab:green" if converged else "tab:red"
            ax.scatter([dns], [dN], color=color, marker=a.marker)
        ax.set_xlabel(r"$\delta N_\star$")
        ax.set_ylabel(r"$\Delta N$")
        ax.set_title(rf"$\alpha$={alpha:.3g}, $n$={int(n_colloc)}")

    fig.suptitle(f"GCI convergence map facets — {potential_name}")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)
    fig.savefig(output_dir / f"diagnostics_convergence_map_gci_facets.{fmt}")
    plt.close(fig)


# ── Item 5: speed-up ──────────────────────────────────────────────────────────


def plot_speedup(adapters, potential_name, output_dir, fmt, run_label=""):
    """GCI vs FI vs SR compute-time ratios wherever the SAME grid point --
    matched by `(N_init, N_final, delta_Nstar)`, the coords every kind shares
    (design §7.5) -- was computed by more than one solver kind (design §8
    item 4). A genuine cross-solver comparison because the adapters share
    coords, not a hand-paired lookup."""
    live = _live_adapters(adapters)

    buckets: dict = {}
    for a in live:
        c = a.coords
        key = (c.get("N_init"), c.get("N_final"), c.get("delta_Nstar"))
        if None in key:
            continue
        d = a.diagnostics()
        t = d.get("compute_time") if d is not None else None
        if t is None:
            continue
        buckets.setdefault(key, {})[a.display_label] = t

    multi = {k: v for k, v in buckets.items() if len(v) >= 2}
    if not multi:
        return

    pair_series: dict = {}
    for key, times_by_label in multi.items():
        labels = sorted(times_by_label.keys())
        dns = key[2]
        for i in range(len(labels)):
            for j in range(i + 1, len(labels)):
                a_label, b_label = labels[i], labels[j]
                ratio = times_by_label[a_label] / times_by_label[b_label]
                pair_series.setdefault((a_label, b_label), []).append((dns, ratio))

    if not pair_series:
        return

    fig, ax = plt.subplots(figsize=(7, 5.5))
    for (a_label, b_label), pts in pair_series.items():
        pts_sorted = sorted(pts)
        xs, ys = zip(*pts_sorted)
        ax.semilogy(xs, ys, "o", label=f"{a_label} / {b_label}")

    ax.axhline(1.0, color="gray", linestyle=":", linewidth=0.8)
    ax.set_xlabel(r"$\delta N_\star$")
    ax.set_ylabel("compute-time ratio")
    ax.set_title(f"Cross-solver speed-up — {potential_name}")
    ax.legend(fontsize="small")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)
    fig.savefig(output_dir / f"diagnostics_speedup.{fmt}")
    plt.close(fig)


# ── Item 6: Picard/Newton structure ──────────────────────────────────────────


def plot_picard_newton_structure(adapters, potential_name, output_dir, fmt, run_label=""):
    """Outer-iteration and Picard-iteration-count distributions, plus
    Newton-fallback frequency vs δN★ (design §8 item 5). Gated purely on
    `diagnostics()` key presence -- FullInstanton's own Picard shooting loop
    carries the same keys, so it is included automatically wherever present,
    not excluded by a `.kind` check (design's own "never branch on kind"
    rule)."""
    live = _live_adapters(adapters)
    order, groups = _group_by_label(live)

    outer_iter_series, picard_iter_series, newton_series = {}, {}, {}
    for label in order:
        outer_vals, picard_vals, newton_pts = [], [], []
        for a in groups[label]:
            d = a.diagnostics()
            if d is None:
                continue
            oi = d.get("outer_iterations")
            if oi is not None:
                outer_vals.append(oi)
            mpi = d.get("mean_picard_iterations")
            if mpi is not None:
                picard_vals.append(mpi)
            nf = d.get("newton_fallback_count")
            dns = a.coords.get("delta_Nstar")
            if nf is not None and dns is not None:
                newton_pts.append((dns, nf))
        if outer_vals:
            outer_iter_series[label] = outer_vals
        if picard_vals:
            picard_iter_series[label] = picard_vals
        if newton_pts:
            newton_series[label] = newton_pts

    if not outer_iter_series and not picard_iter_series and not newton_series:
        return

    fig, (ax_outer, ax_picard, ax_newton) = plt.subplots(1, 3, figsize=(15, 5))

    for label, vals in outer_iter_series.items():
        ax_outer.hist(vals, bins=min(10, max(3, len(vals))), alpha=0.6, label=label)
    ax_outer.set_xlabel("outer iterations")
    ax_outer.set_ylabel("count")
    ax_outer.set_title("Outer-iteration count")
    if outer_iter_series:
        ax_outer.legend(fontsize="small")

    for label, vals in picard_iter_series.items():
        ax_picard.hist(vals, bins=min(10, max(3, len(vals))), alpha=0.6, label=label)
    ax_picard.set_xlabel("mean Picard iterations / outer step")
    ax_picard.set_ylabel("count")
    ax_picard.set_title("Picard-iteration count")
    if picard_iter_series:
        ax_picard.legend(fontsize="small")

    for label, pts in newton_series.items():
        pts_sorted = sorted(pts)
        xs, ys = zip(*pts_sorted)
        ax_newton.plot(xs, ys, "o", label=label)
    ax_newton.set_xlabel(r"$\delta N_\star$")
    ax_newton.set_ylabel("Newton-fallback count")
    ax_newton.set_title("Newton-fallback frequency")
    if newton_series:
        ax_newton.legend(fontsize="small")

    fig.suptitle(f"Picard/Newton iteration structure — {potential_name}")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)
    fig.savefig(output_dir / f"diagnostics_picard_newton_structure.{fmt}")
    plt.close(fig)


# ── Item 7: RK45 stiffness ────────────────────────────────────────────────────


def plot_stiffness(adapters, potential_name, output_dir, fmt, run_label=""):
    """RK45 steps-per-efold, forward vs backward, vs δN★ (design §8 item 6).
    `rk45_{forward,backward}_steps_per_efold` are GCI-exclusive keys (no
    other solver instruments RK45 step counts), so this figure is
    effectively GCI-only in practice -- but the gate is key presence via
    `.get(...)`, not `.kind`."""
    live = _live_adapters(adapters)
    order, groups = _group_by_label(live)

    fwd_series, bwd_series = {}, {}
    for label in order:
        fwd_pts, bwd_pts = [], []
        for a in groups[label]:
            d = a.diagnostics()
            if d is None:
                continue
            dns = a.coords.get("delta_Nstar")
            if dns is None:
                continue
            fwd = d.get("rk45_forward_steps_per_efold")
            bwd = d.get("rk45_backward_steps_per_efold")
            if fwd is not None:
                fwd_pts.append((dns, fwd))
            if bwd is not None:
                bwd_pts.append((dns, bwd))
        if fwd_pts:
            fwd_series[label] = fwd_pts
        if bwd_pts:
            bwd_series[label] = bwd_pts

    if not fwd_series and not bwd_series:
        return

    fig, (ax_fwd, ax_bwd) = plt.subplots(1, 2, figsize=(11, 5))
    for label, pts in fwd_series.items():
        pts_sorted = sorted(pts)
        xs, ys = zip(*pts_sorted)
        ax_fwd.plot(xs, ys, "o-", label=label)
    ax_fwd.set_xlabel(r"$\delta N_\star$")
    ax_fwd.set_ylabel("RK45 steps / e-fold (forward)")
    ax_fwd.set_title("Forward-direction stiffness")
    if fwd_series:
        ax_fwd.legend(fontsize="small")

    for label, pts in bwd_series.items():
        pts_sorted = sorted(pts)
        xs, ys = zip(*pts_sorted)
        ax_bwd.plot(xs, ys, "o-", label=label)
    ax_bwd.set_xlabel(r"$\delta N_\star$")
    ax_bwd.set_ylabel("RK45 steps / e-fold (backward)")
    ax_bwd.set_title("Backward-direction stiffness")
    if bwd_series:
        ax_bwd.legend(fontsize="small")

    fig.suptitle(f"RK45 stiffness — {potential_name}")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)
    fig.savefig(output_dir / f"diagnostics_stiffness.{fmt}")
    plt.close(fig)


# ── Item 8: extraction-failure map (GCI-only, spatial) ───────────────────────


def plot_extraction_failure_summary(adapters, potential_name, output_dir, fmt, run_label=""):
    """Fraction of failed shells vs grid point (δN★, ΔN) (design §8 item 7,
    first half). Gated on `adapter.is_spatial()` -- per the P7 prompt's
    explicit instruction, unlike items 6-7 above which only need cheap-tier
    `diagnostics()`."""
    live = [a for a in adapters if a.available and a.is_spatial()]

    pts = []
    for a in live:
        d = a.diagnostics()
        if d is None:
            continue
        mask = d.get("extraction_failure_mask")
        if not mask:
            continue
        dns = a.coords.get("delta_Nstar")
        dN = _delta_N(a)
        if dns is None or dN is None:
            continue
        pts.append((dns, dN, float(np.mean(mask))))

    if not pts:
        return

    dns_arr = np.array([p[0] for p in pts])
    dN_arr = np.array([p[1] for p in pts])
    frac_arr = np.array([p[2] for p in pts])

    fig, ax = plt.subplots(figsize=(7, 5.5))
    sc = ax.scatter(dns_arr, dN_arr, c=frac_arr, cmap="Reds", vmin=0.0, vmax=1.0)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("fraction of failed shells")
    ax.set_xlabel(r"$\delta N_\star$")
    ax.set_ylabel(r"$\Delta N$")
    ax.set_title(f"Extraction-failure fraction — {potential_name}")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)
    fig.savefig(output_dir / f"diagnostics_extraction_failure_summary.{fmt}")
    plt.close(fig)


def plot_extraction_failure_heatmap(adapters, potential_name, output_dir, fmt, run_label=""):
    """Per-node (vs y) extraction-failure heatmap for individual solves
    (design §8 item 7, second half): one row per GCI solve, one column per
    collocation node, coloured by whether ζ-extraction failed at that shell.
    Gated on `adapter.is_spatial()` (needs `.y_nodes`, from `SpatialAdapter`,
    P4)."""
    live = [a for a in adapters if a.available and a.is_spatial()]

    rows = []
    for a in live:
        d = a.diagnostics()
        if d is None:
            continue
        mask = d.get("extraction_failure_mask")
        if not mask:
            continue
        rows.append((a, np.asarray(mask, dtype=float)))

    if not rows:
        return

    # Only adapters sharing the same node count can share one heatmap's
    # column axis -- use whichever node count is most common among the
    # fetched solves.
    counts = Counter(len(m) for _, m in rows)
    common_n = counts.most_common(1)[0][0]
    rows = [(a, m) for a, m in rows if len(m) == common_n]
    if not rows:
        return

    rows.sort(key=lambda am: am[0].coords.get("delta_Nstar", 0.0))
    y_nodes = rows[0][0].y_nodes
    Z = np.stack([m for _, m in rows])  # shape (n_solves, n_nodes)

    fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(rows))))
    pcm = ax.pcolormesh(y_nodes, np.arange(len(rows)), Z, cmap="Reds", vmin=0.0, vmax=1.0, shading="nearest")
    cb = fig.colorbar(pcm, ax=ax)
    cb.set_label("extraction failed (1) / ok (0)")
    ax.set_xlabel(r"$y$")
    ax.set_ylabel(r"solve index (sorted by $\delta N_\star$)")
    ax.set_title(f"Per-node extraction-failure map — {potential_name}")
    fig.tight_layout()
    _provenance_footer(fig, run_label=run_label)
    fig.savefig(output_dir / f"diagnostics_extraction_failure_heatmap.{fmt}")
    plt.close(fig)
