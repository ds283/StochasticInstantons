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
GCI stability/convergence figures (design doc
`.documents/gradient-coupled-plotting/DESIGN_gradient_coupled_plotting.md`,
§6.4, reusing the overlay mechanism of §3.4). See the P6 prompt
(`.prompts/gradient-coupled-plotting/11-P6-stability-convergence-figures.md`)
and this prompt set's `00-README.md` ("Correction 1") for why the swept
`n_collocation_points`/`alpha_regularization` axes come directly from
`config/pipeline_setup.py::build_pipeline_inputs`'s existing
`n_collocation_points_array`/`alpha_regularization_array` -- never from a new
CLI flag or grid-generation helper.

Two entry points, `render_n_collocation_stability` and `render_alpha_stability`,
each fetch `GradientCoupledInstanton` records over one swept axis (fixing the
other three of `(N_init, N_final, delta_Nstar, alpha, n_collocation_points)`),
wrap each as a `GradientCoupledAdapter`, and render two figures: a profile
overlay (plus, for the n_collocation sweep only, a core-node history overlay)
and a scalar-vs-axis "plateau" panel. Both are skipped (no fetch, no file, no
exception) when fewer than two values of the swept axis were actually
computed -- see design §6.4 item 4 / the P6 prompt's Task item 4.

Fetch-tier choice (module-wide, see design §4/§4.1's fetch-mode contract):
every sweep point is fetched TWICE -- once `_do_not_populate=True` (cheap:
scalars + diagnostics only) and once `_profile_only=True` (adds the
persisted zeta/C/C_bar/r profile, still without touching the dense (y,N)
grid). Neither ever performs a full, dense-stored fetch, so a stability
sweep never raises on a scalars-only-stored run (the very failure mode P3's
`profile_only` mode exists to avoid) -- unlike the do_not_populate/profile_only
pair, a full fetch would also raise whenever ANY swept point was computed
with `no_store_values=True` (main.py's cheaper-compute-run flag).
Consequence: `GradientCoupledAdapter.time_history(...)` (which requires the
dense `.values`, populated only by a full, non-profile_only fetch) returns
`None` for every adapter this module constructs -- a capability gap, not a
failure, exactly the contract `time_history`/`noise_history` already
document in `plotting/adapters/gradient.py`. The core-node history panel
(n_collocation sweep only) is wired up regardless, so it renders any real
per-N data for free the moment a caller passes fuller-fidelity adapters,
but under this module's own (cheap) fetches it legitimately has no lines.
"""

from matplotlib import pyplot as plt

from plotting.adapters.gradient import GradientCoupledAdapter
from plotting.annotations import _add_cf_annotation
from plotting.fetch import fetch_over_grid
from plotting.provenance import _provenance_footer

_AXIS_LABELS = {
    "n_collocation_points": r"$n_{\rm colloc}$",
    "alpha": r"$\alpha$",
}


def _gci_key_payload(
    traj_proxy, N_init_obj, N_final_obj, dns_obj,
    n_collocation_points_obj, alpha_regularization_obj, atol, rtol, cosmo, dm,
):
    """The `GradientCoupledInstanton` datastore identity payload (mirrors
    `main.py::_run_gradient_branch`'s own `key_fields` closure -- see design
    §4's GCI lookup key list)."""
    return dict(
        trajectory=traj_proxy,
        N_init=N_init_obj,
        N_final=N_final_obj,
        delta_Nstar=dns_obj,
        n_collocation_points=n_collocation_points_obj,
        alpha_regularization=alpha_regularization_obj,
        atol=atol,
        rtol=rtol,
        cosmo=cosmo,
        diffusion_model=dm,
        tags=[],
    )


def _fetch_gci_sweep(
    pool, traj_proxy, N_init_obj, N_final_obj, dns_obj, atol, rtol, cosmo, dm,
    *, sweep_axis, sweep_values, fixed_n=None, fixed_alpha=None, profile_only,
):
    """Fetch one `GradientCoupledInstanton` per value in `sweep_values` (a
    list of `n_collocation_points` objects when `sweep_axis ==
    "n_collocation_points"`, or `alpha_regularization` objects when
    `sweep_axis == "alpha"`), fixing the other of {n_collocation_points,
    alpha} at `fixed_n`/`fixed_alpha`, and `(N_init, N_final, delta_Nstar)`
    as given. Uses the existing, generic `fetch_over_grid` (P1) -- not a new
    hand-rolled fetch loop -- with `delta_Nstar` as the (constant across the
    sweep) shard key, per the design's "alpha and n_colloc are ordinary
    axes; delta_Nstar remains the shard key" constraint.

    Returns a list of `GradientCoupledAdapter`, index-aligned with
    `sweep_values`, each carrying the swept/fixed values in `coords`."""
    if sweep_axis not in ("n_collocation_points", "alpha"):
        raise ValueError(
            f"_fetch_gci_sweep: sweep_axis must be 'n_collocation_points' or "
            f"'alpha', got {sweep_axis!r}"
        )

    def key_payload_of(item):
        ncp_obj = item if sweep_axis == "n_collocation_points" else fixed_n
        alpha_obj = item if sweep_axis == "alpha" else fixed_alpha
        payload = _gci_key_payload(
            traj_proxy, N_init_obj, N_final_obj, dns_obj,
            ncp_obj, alpha_obj, atol, rtol, cosmo, dm,
        )
        if profile_only:
            payload["_profile_only"] = True
        return payload

    def shard_key_of(_item):
        return dns_obj

    raw = fetch_over_grid(
        pool, "GradientCoupledInstanton", shard_key_of, key_payload_of,
        sweep_values, do_not_populate=not profile_only,
    )

    fidelity = "profile" if profile_only else "scalars"
    adapters = []
    for item, obj in zip(sweep_values, raw):
        ncp_obj = item if sweep_axis == "n_collocation_points" else fixed_n
        alpha_obj = item if sweep_axis == "alpha" else fixed_alpha
        coords = {
            "N_init": float(N_init_obj),
            "N_final": float(N_final_obj),
            "delta_Nstar": float(dns_obj),
            "n_collocation_points": int(ncp_obj),
            "alpha": float(alpha_obj),
        }
        adapters.append(GradientCoupledAdapter(obj, coords=coords, fidelity=fidelity))
    return adapters


def _live_sorted(adapters, axis_name):
    """Available, non-failed adapters, sorted ascending by `coords[axis_name]`."""
    live = [a for a in adapters if a.available and not a.failure]
    return sorted(live, key=lambda a: a.coords[axis_name])


def _max_abs_diff(adapters_sorted, scalar_key):
    """max|Delta| of `scalars()[scalar_key]` between successive (already
    axis-sorted) adapters; `None` if fewer than two finite values are
    available."""
    vals = [a.scalars().get(scalar_key) for a in adapters_sorted]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    diffs = [abs(vals[i + 1] - vals[i]) for i in range(len(vals) - 1)]
    return max(diffs) if diffs else None


def _convergence_annotation_text(scalar_adapters, axis_name):
    """Spectral-convergence inset text (design §6.4): max|Delta| of the
    persisted scalars that best track the compaction profile / MSR saddle
    across successive resolutions, sorted by the swept axis."""
    live = _live_sorted(scalar_adapters, axis_name)
    parts = []
    for key, label in (
        ("msr_action", r"S_{\rm MSR}"),
        ("C_peak", r"C_{\rm peak}"),
    ):
        d = _max_abs_diff(live, key)
        if d is not None:
            parts.append(rf"max|$\Delta {label}$|={d:.3g}")
    return "   ".join(parts) if parts else None


def _plot_profile_overlay(
    profile_adapters,
    axis_name,
    potential_name,
    fixed_desc,
    output_dir,
    fmt,
    fname_stub,
    convergence_text=None,
    include_core_history=False,
    run_label: str = "",
):
    """Overlay ζ(r), C(r), C_bar(r) (via `radial_profile()`) -- and, when
    `include_core_history`, the core-node field history (via
    `time_history("phi")`) -- across the swept axis, reusing the exact
    `for a in adapters: ...` overlay loop pattern from P2/P4 (design §3.4).
    One line per swept value, labelled by `a.display_label` (which already
    encodes both n and alpha, per `GradientCoupledAdapter.__init__`)."""
    axis_label = _AXIS_LABELS[axis_name]
    live = _live_sorted(profile_adapters, axis_name)

    profiles = [(a, a.radial_profile()) for a in live]
    has_profile = any(p is not None for _, p in profiles)

    histories = []
    if include_core_history:
        histories = [(a, a.time_history("phi")) for a in live]
    has_history = any(h is not None for _, h in histories)

    if not has_profile and not has_history:
        return

    n_panels = 3 + (1 if include_core_history else 0)
    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 5))
    ax_zeta, ax_C, ax_Cbar = axes[0], axes[1], axes[2]
    ax_hist = axes[3] if include_core_history else None

    for a, profile in profiles:
        if profile is None:
            continue
        r = profile["r_Mpc"]
        ax_zeta.plot(r, profile["zeta"], label=a.display_label)
        ax_C.plot(r, profile["C"], label=a.display_label)
        ax_Cbar.plot(r, profile["C_bar"], label=a.display_label)

    for ax, ylabel, title in (
        (ax_zeta, r"$\zeta(r)$", r"Density contrast $\zeta(r)$"),
        (ax_C, r"$C(r)$", "Compaction function"),
        (ax_Cbar, r"$\bar{C}(r)$", "Volume-averaged compaction"),
    ):
        ax.set_xscale("log")
        ax.set_xlabel(r"$r$ / Mpc")
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        if has_profile:
            ax.legend(fontsize="x-small")

    if include_core_history:
        for a, hist in histories:
            if hist is None:
                continue
            N, phi = hist
            ax_hist.plot(N, phi, label=a.display_label)
        ax_hist.set_xlabel("N (e-folds)")
        ax_hist.set_ylabel(r"$\varphi$ (core node, $y=+1$)")
        ax_hist.set_title("Core-node field history")
        if has_history:
            ax_hist.legend(fontsize="x-small")

    fig.suptitle(
        rf"Stability sweep vs {axis_label} — {potential_name} ({fixed_desc})"
    )
    if convergence_text:
        _add_cf_annotation(fig, convergence_text)
    else:
        fig.tight_layout()
    _provenance_footer(fig, *live, run_label=run_label)

    fname = output_dir / f"{fname_stub}__{fixed_desc}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def _plot_plateau_panel(
    scalar_adapters,
    axis_name,
    potential_name,
    fixed_desc,
    output_dir,
    fmt,
    fname_stub,
    run_label: str = "",
):
    """Scalar-vs-axis "plateau" panel: `C_peak`, `msr_action`, `r_max`,
    `M_max` vs the swept axis, other axes fixed -- reads `.scalars()`
    directly off each already-fetched adapter (design §6.4 item 3); no
    scalar is recomputed here."""
    axis_label = _AXIS_LABELS[axis_name]
    live = _live_sorted(scalar_adapters, axis_name)

    def _series(key):
        pts = [(a.coords[axis_name], a.scalars().get(key)) for a in live]
        pts = [(x, y) for x, y in pts if y is not None]
        if not pts:
            return [], []
        xs, ys = zip(*pts)
        return list(xs), list(ys)

    C_peak_x, C_peak_y = _series("C_peak")
    msr_x, msr_y = _series("msr_action")
    r_max_x, r_max_y = _series("r_max_Mpc")
    M_max_x, M_max_y = _series("M_max_solar")

    if not (C_peak_x or msr_x or r_max_x or M_max_x):
        return

    fig, ((ax_C, ax_msr), (ax_r, ax_M)) = plt.subplots(2, 2, figsize=(11, 9))

    if C_peak_x:
        ax_C.plot(C_peak_x, C_peak_y, "o-")
    ax_C.set_xlabel(axis_label)
    ax_C.set_ylabel(r"$C_{\rm peak}$")
    ax_C.set_title("Compaction peak")

    if msr_x:
        ax_msr.semilogy(msr_x, msr_y, "o-")
    ax_msr.set_xlabel(axis_label)
    ax_msr.set_ylabel(r"$S_{\rm MSR}$")
    ax_msr.set_title("MSR action")

    if r_max_x:
        ax_r.semilogy(r_max_x, r_max_y, "o-")
    ax_r.set_xlabel(axis_label)
    ax_r.set_ylabel(r"$r_{\rm max}$ / Mpc")
    ax_r.set_title("PBH collapse scale")

    if M_max_x:
        ax_M.semilogy(M_max_x, M_max_y, "o-")
    ax_M.set_xlabel(axis_label)
    ax_M.set_ylabel(r"$M_{\rm max}\,/\,M_\odot$")
    ax_M.set_title("PBH mass")

    fig.suptitle(
        rf"Convergence plateau vs {axis_label} — {potential_name} ({fixed_desc})"
    )
    fig.tight_layout()
    _provenance_footer(fig, *live, run_label=run_label)

    fname = output_dir / f"{fname_stub}__{fixed_desc}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def render_n_collocation_stability(
    pool,
    traj_proxy,
    N_init_obj,
    N_final_obj,
    dns_obj,
    alpha_obj,
    n_collocation_points_array,
    atol,
    rtol,
    cosmo,
    dm,
    potential_name,
    output_dir,
    fmt,
    run_label: str = "",
):
    """n_collocation convergence overlay + plateau panel (design §6.4 item
    1 and half of item 3), fixing `(N_init, N_final, delta_Nstar, alpha)`
    and sweeping `n_collocation_points` over every value in
    `n_collocation_points_array` -- exactly what was actually computed and
    persisted for this database (Correction 1, `00-README.md`). Silently
    skips both figures (no fetch, no file, no exception) if fewer than two
    values were actually computed (design §6.4 item 4)."""
    if len(n_collocation_points_array) < 2:
        return

    fixed_desc = (
        f"Ninit={float(N_init_obj):.3g}_Nfinal={float(N_final_obj):.3g}_"
        f"dNstar={float(dns_obj):.3g}_alpha={float(alpha_obj):.3g}"
    )

    profile_adapters = _fetch_gci_sweep(
        pool, traj_proxy, N_init_obj, N_final_obj, dns_obj, atol, rtol, cosmo, dm,
        sweep_axis="n_collocation_points", sweep_values=n_collocation_points_array,
        fixed_alpha=alpha_obj, profile_only=True,
    )
    scalar_adapters = _fetch_gci_sweep(
        pool, traj_proxy, N_init_obj, N_final_obj, dns_obj, atol, rtol, cosmo, dm,
        sweep_axis="n_collocation_points", sweep_values=n_collocation_points_array,
        fixed_alpha=alpha_obj, profile_only=False,
    )

    convergence_text = _convergence_annotation_text(scalar_adapters, "n_collocation_points")

    _plot_profile_overlay(
        profile_adapters, "n_collocation_points", potential_name, fixed_desc,
        output_dir, fmt, "stability_n_collocation_overlay",
        convergence_text=convergence_text, include_core_history=True,
        run_label=run_label,
    )
    _plot_plateau_panel(
        scalar_adapters, "n_collocation_points", potential_name, fixed_desc,
        output_dir, fmt, "stability_plateau_n_collocation", run_label=run_label,
    )


def render_alpha_stability(
    pool,
    traj_proxy,
    N_init_obj,
    N_final_obj,
    dns_obj,
    n_collocation_points_obj,
    alpha_regularization_array,
    atol,
    rtol,
    cosmo,
    dm,
    potential_name,
    output_dir,
    fmt,
    run_label: str = "",
):
    """alpha (outer-boundary regularisation) overlay + plateau panel (design
    §6.4 item 2 and the other half of item 3), fixing `(N_init, N_final,
    delta_Nstar, n_collocation_points)` and sweeping `alpha` over every
    value in `alpha_regularization_array`. Silently skips both figures (no
    fetch, no file, no exception) if fewer than two values were actually
    computed (design §6.4 item 4)."""
    if len(alpha_regularization_array) < 2:
        return

    fixed_desc = (
        f"Ninit={float(N_init_obj):.3g}_Nfinal={float(N_final_obj):.3g}_"
        f"dNstar={float(dns_obj):.3g}_ncolloc={int(n_collocation_points_obj)}"
    )

    profile_adapters = _fetch_gci_sweep(
        pool, traj_proxy, N_init_obj, N_final_obj, dns_obj, atol, rtol, cosmo, dm,
        sweep_axis="alpha", sweep_values=alpha_regularization_array,
        fixed_n=n_collocation_points_obj, profile_only=True,
    )
    scalar_adapters = _fetch_gci_sweep(
        pool, traj_proxy, N_init_obj, N_final_obj, dns_obj, atol, rtol, cosmo, dm,
        sweep_axis="alpha", sweep_values=alpha_regularization_array,
        fixed_n=n_collocation_points_obj, profile_only=False,
    )

    convergence_text = _convergence_annotation_text(scalar_adapters, "alpha")

    _plot_profile_overlay(
        profile_adapters, "alpha", potential_name, fixed_desc,
        output_dir, fmt, "stability_alpha_overlay",
        convergence_text=convergence_text, include_core_history=False,
        run_label=run_label,
    )
    _plot_plateau_panel(
        scalar_adapters, "alpha", potential_name, fixed_desc,
        output_dir, fmt, "stability_plateau_alpha", run_label=run_label,
    )
