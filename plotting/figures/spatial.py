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
Spatial `(y, N)` figures for `GradientCoupledInstanton` -- design doc
`.documents/gradient-coupled-plotting/DESIGN_gradient_coupled_plotting.md`,
§6.2 (heatmaps, slice overlays, and -- P5b -- opt-in movies) and §6.3 (the
optional ζ(r)/C(r) movie through N).

All figures gate on `adapter.is_spatial()` (design §3.3's own guard
pattern), never on which *kind* of adapter is present, so a figure function
never has to special-case `GradientCoupledAdapter` beyond picking the right
data-access method (`field_2d`/`derived_at_time` vs `time_history`) --
exactly the discipline every other module in `plotting/figures/` already
follows.

Per design §5's proxy-passing caveat, the dense `(y, N)` grid must not cross
the driver-to-worker boundary as raw numpy through the `(remote_fn, args)`
work-item tuple. `_render_spatial_heatmaps_item`/`_render_spatial_slices_item`/
`_render_spatial_field_movie_item`/`_render_spatial_derived_movie_item`
below are the `@ray.remote` wrappers a driver (P8) dispatches through: they
take the cheap `GradientCoupledInstantonProxy` handle and build the
`GradientCoupledAdapter` (== `SpatialAdapter`, see `plotting/adapters/
gradient.py`) worker-side, from `.get()`, never on the driver. Movies are
rendered worker-side for the same reason and are the single most expensive
output in the whole design (§6.2 item 3), so they stay strictly opt-in,
gated behind the driver's `--movies` flag (P8's job to wire; see
`plot_InstantonSolutions.py`'s placeholder `--movies`/`--movie-format`
flags added by P5b pending P8's driver).

Movie provenance (P5b, design §9 item 3): `plotting/provenance.py`'s
`_provenance_footer` renders a *static* `fig.text(...)` call sized against
a one-shot `subplots_adjust` -- it does not survive
`matplotlib.animation.FuncAnimation`'s frame-by-frame rendering (there is
no single "end of render" moment for that sizing logic to apply against).
`_movie_provenance_text` below rebuilds the same version/timestamp/coords
content as a plain string a frame-update callback can burn into a
persistent `fig.text` object every frame, plus an opening title-card frame
carrying that same string -- `_provenance_footer` itself must never be
called from inside a `FuncAnimation` update callback.
"""

import shutil
from datetime import datetime
from pathlib import Path

import ray
import seaborn as sns
from matplotlib import animation
from matplotlib import pyplot as plt

from plotting.adapters.gradient import GradientCoupledAdapter
from plotting.provenance import VERSION_LABEL, _provenance_footer
from plotting.sampling import _evenly_sample

# field_2d's channel name -> channel_label()'s channel name. field_2d uses
# GCI's raw per-node attribute names ("pi", not "velocity"); channel_label
# uses time_history's channel vocabulary. They agree except for the
# field-velocity channel -- see plotting/adapters/gradient.py's module
# docstring on that naming split. Order fixes the 2x2 heatmap layout to
# match time_history.py's own phi/velocity/response-1/response-2 layout.
_HEATMAP_PANELS = (
    ("phi", "phi"),
    ("pi", "velocity"),
    ("rfield", "rfield"),
    ("rmom", "rmom"),
)

# "a handful" of N-slices (design §6.2 item 2's own wording); the y-slices
# are the three fixed named shells (edge/mid/core) design calls out
# explicitly, not an evenly-sampled count.
_N_SLICE_COUNT = 5

# Movies (P5b): frames-per-second for the saved animation -- not specified
# by the design, chosen slow enough that a short, evenly-sampled frame set
# is still legible.
_MOVIE_FPS = 2


def _first_available_spatial(adapters):
    for a in adapters:
        if a.is_spatial() and a.available and not a.failure:
            return a
    return None


def _coord_tuple_text(adapter):
    """The full coordinate tuple (N_init, N_final, delta_Nstar, alpha,
    n_collocation_points), per design §9 item 1 ("every per-instanton figure
    should stamp the full coordinate tuple ... so a detached PNG is still
    self-describing"). Reads `adapter.coords`, never the wrapped object."""
    c = adapter.coords
    parts = []
    if c.get("N_init") is not None:
        parts.append(rf"$N_{{\rm init}}$={float(c['N_init']):.3g}")
    if c.get("N_final") is not None:
        parts.append(rf"$N_{{\rm final}}$={float(c['N_final']):.3g}")
    if c.get("delta_Nstar") is not None:
        parts.append(rf"$\delta N_\star$={float(c['delta_Nstar']):.3g}")
    if c.get("alpha") is not None:
        parts.append(rf"$\alpha$={float(c['alpha']):.3g}")
    if c.get("n_collocation_points") is not None:
        parts.append(rf"$n$={int(c['n_collocation_points'])}")
    return ", ".join(parts)


def plot_spatial_heatmaps(adapters, output_dir, fmt, run_label=""):
    """2x2 `pcolormesh` panel (phi, pi, r_phi, r_pi) over `(N, y)` for one
    dense-fidelity GCI adapter (design §6.2 item 1) -- the primary
    "is-the-solution-smooth" diagnostic.

    `adapters` is a list of `InstantonAdapter` instances; only the first
    spatial, available, non-failed one is drawn (design's own pseudocode
    guards on "one SpatialAdapter-fidelity GCI instance", singular). Skip
    (return without drawing) if none of the passed adapters is spatial and
    available -- copied verbatim from design §3.3's own one-liner guard.
    """
    if not any(a.is_spatial() and a.available for a in adapters):
        return
    gci = _first_available_spatial(adapters)
    if gci is None:
        return

    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    for (field_name, label_key), ax in zip(_HEATMAP_PANELS, axes.flat):
        y_nodes, N_grid, Z = gci.field_2d(field_name)
        mesh = ax.pcolormesh(N_grid, y_nodes, Z.T, shading="auto", cmap="viridis")
        fig.colorbar(mesh, ax=ax)
        ax.set_xlabel("N (e-folds)")
        ax.set_ylabel("y (LGL node)")
        ax.set_title(gci.channel_label(label_key))

    fig.suptitle(
        f"Spatial field structure ({gci.display_label}) — {_coord_tuple_text(gci)}"
    )
    _provenance_footer(fig, gci, run_label=run_label)

    fname = output_dir / f"spatial_heatmaps.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


def plot_spatial_slices(adapters, output_dir, fmt, run_label=""):
    """Companion figure to `plot_spatial_heatmaps` (design §6.2 item 2):

    - N-slices (left panel): phi vs y at a handful of evenly-sampled
      e-folds (`plotting.sampling._evenly_sample`).
    - y-slices (right panel): phi vs N at the edge (y=-1), mid, and core
      (y=+1) shells. The core slice overlays cleanly against any
      non-spatial adapter's own `time_history("phi")` in the same
      `adapters` list (e.g. a `FullInstantonAdapter`'s homogeneous field
      history) -- design §6.2 item 2's "these also overlay cleanly against
      FI/SR where an analogue exists".

    Both panels reuse the same `for a in adapters: ...` loop already used
    throughout `plotting/figures/`, gated only on `is_spatial()` to pick the
    right data-access method (`field_2d` vs `time_history`) -- never on
    which *kind* of adapter it is. Skip (return without drawing) under the
    same guard as `plot_spatial_heatmaps`.
    """
    if not any(a.is_spatial() and a.available for a in adapters):
        return

    live = [a for a in adapters if a.available and not a.failure]

    fig, (ax_N, ax_y) = plt.subplots(1, 2, figsize=(12, 5.5))

    gci_for_title = None
    for a in live:
        if not a.is_spatial():
            continue
        y_nodes, N_grid, Z = a.field_2d("phi")
        if gci_for_title is None:
            gci_for_title = a
        idxs = _evenly_sample(range(len(N_grid)), _N_SLICE_COUNT)
        for idx in idxs:
            ax_N.plot(y_nodes, Z[idx, :], label=f"{a.display_label} N={N_grid[idx]:.3g}")

    ax_N.set_xlabel("y (LGL node)")
    ax_N.set_ylabel(r"$\varphi$")
    ax_N.set_title("Profile vs y at selected e-folds")
    ax_N.legend(fontsize="x-small")

    for a in live:
        if a.is_spatial():
            y_nodes, N_grid, Z = a.field_2d("phi")
            n_y = len(y_nodes)
            edge_idx, mid_idx, core_idx = 0, n_y // 2, n_y - 1
            for idx, tag in (
                (edge_idx, "edge y=-1"),
                (mid_idx, f"mid y={y_nodes[mid_idx]:.2g}"),
                (core_idx, "core y=+1"),
            ):
                ax_y.plot(N_grid, Z[:, idx], label=f"{a.display_label} {tag}")
        else:
            hist = a.time_history("phi")
            if hist is None:
                continue
            N, phi = hist
            ax_y.plot(N, phi, a.line_style, label=f"{a.display_label} (homogeneous)")

    ax_y.set_xlabel("N (e-folds)")
    ax_y.set_ylabel(r"$\varphi$")
    ax_y.set_title("History vs N at selected shells")
    ax_y.legend(fontsize="x-small")

    if gci_for_title is not None:
        fig.suptitle(
            f"Spatial slices ({gci_for_title.display_label}) — "
            f"{_coord_tuple_text(gci_for_title)}"
        )

    _provenance_footer(fig, *live, run_label=run_label)

    fname = output_dir / f"spatial_slices.{fmt}"
    fig.savefig(fname)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Movies (P5b, opt-in `--movies`) -- design §6.2 item 3, §6.3, §9 item 3
# ---------------------------------------------------------------------------


def _movie_provenance_text(*objs, render_time=None, run_label: str = "") -> str:
    """Rebuilds the same version/timestamp/coords content
    `plotting.provenance._provenance_footer` would render via `fig.text`,
    but returns it as a plain string a `FuncAnimation` frame-update callback
    can burn into a persistent text artist every frame. Deliberately does
    NOT call `_provenance_footer` (see this module's docstring: that
    function's one-shot `subplots_adjust` sizing has no "end of render"
    moment to apply against inside an animation) -- so the field-
    introspection logic below is a duplicate of `_provenance_footer`'s, not
    a shared call, per P5b's file scope (this module + the driver only)."""
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
    return "\n".join([run_label, bottom_line]) if run_label else bottom_line


def _save_movie(anim, fname, movie_format: str):
    """Format dispatch for `FuncAnimation.save` -- the one call site gated
    on `ffmpeg` availability (Decision point), so an mp4 request fails
    loudly here with a clear message rather than raising an opaque error
    deep inside `matplotlib.animation.FFMpegWriter` on a Ray worker."""
    # DESIGN-DECISION: default movie format is gif (Pillow-only, no external dependency); mp4 is opt-in via --movie-format mp4 and requires ffmpeg on the render node -- see design doc §12 "Movie dependency".
    if movie_format == "gif":
        writer = animation.PillowWriter(fps=_MOVIE_FPS)
    elif movie_format == "mp4":
        if shutil.which("ffmpeg") is None:
            raise RuntimeError(
                "plot_spatial movie: --movie-format mp4 requires ffmpeg on "
                "the render node's PATH, but ffmpeg was not found. Install "
                "ffmpeg, or render with --movie-format gif (the default, "
                "Pillow-only)."
            )
        writer = animation.FFMpegWriter(fps=_MOVIE_FPS)
    else:
        raise ValueError(
            f"plot_spatial movie: unknown movie_format {movie_format!r}, "
            f"expected 'gif' or 'mp4'"
        )
    anim.save(str(fname), writer=writer)


def plot_spatial_field_movie(
    adapters, output_dir, movie_format: str = "gif", run_label: str = "", n_frames=None
):
    """`(y, N)` movie (design §6.2 item 3): one 2x2 panel (phi, pi, r_phi,
    r_pi, mirroring `plot_spatial_heatmaps`' panel selection), each frame a
    profile vs `y` at one stored `N`, sweeping through `N`. Same
    spatial/available guard and `_first_available_spatial` pick as the two
    static figures above; skip (no file, no exception) if none of the
    passed adapters is spatial and available.

    `n_frames`, if given, evenly-samples down to that many of the stored
    `N` grid points (`plotting.sampling._evenly_sample`) -- otherwise every
    stored sample is a frame.
    """
    if not any(a.is_spatial() and a.available for a in adapters):
        return
    gci = _first_available_spatial(adapters)
    if gci is None:
        return

    panel_data = {}
    y_nodes = N_grid = None
    for field_name, _ in _HEATMAP_PANELS:
        y_nodes, N_grid, Z = gci.field_2d(field_name)
        panel_data[field_name] = Z
    if N_grid is None or len(N_grid) == 0:
        return

    frame_idxs = list(range(len(N_grid)))
    if n_frames is not None:
        frame_idxs = _evenly_sample(frame_idxs, n_frames)

    fig, axes = plt.subplots(2, 2, figsize=(11, 9))
    lines = {}
    for (field_name, label_key), ax in zip(_HEATMAP_PANELS, axes.flat):
        (line,) = ax.plot(y_nodes, panel_data[field_name][frame_idxs[0], :])
        lines[field_name] = line
        ax.set_xlabel("y (LGL node)")
        ax.set_ylabel(gci.channel_label(label_key))
        Z = panel_data[field_name]
        zmin, zmax = float(Z.min()), float(Z.max())
        pad = 0.05 * (zmax - zmin) if zmax > zmin else 1.0
        ax.set_ylim(zmin - pad, zmax + pad)

    title = fig.suptitle("")
    card_text = fig.text(0.5, 0.5, "", ha="center", va="center", fontsize=11, wrap=True)
    footer = fig.text(
        0.5, 0.003, "", ha="center", va="bottom", fontsize=7, color="#888888",
        transform=fig.transFigure,
    )
    provenance_text = _movie_provenance_text(gci, run_label=run_label)

    def _update(frame_pos):
        footer.set_text(provenance_text)
        if frame_pos == 0:
            # Opening title card (design §9 item 3): carries the same
            # provenance string; axes hidden (not just the data lines) so
            # the card text isn't overlaid on empty tick/label chrome.
            card_text.set_text(provenance_text)
            card_text.set_visible(True)
            for ax in axes.flat:
                ax.set_visible(False)
            for line in lines.values():
                line.set_visible(False)
            return [card_text, footer, *axes.flat, *lines.values()]
        card_text.set_visible(False)
        for ax in axes.flat:
            ax.set_visible(True)
        idx = frame_idxs[frame_pos - 1]
        for field_name, _ in _HEATMAP_PANELS:
            lines[field_name].set_visible(True)
            lines[field_name].set_ydata(panel_data[field_name][idx, :])
        title.set_text(
            f"Spatial field structure ({gci.display_label}) — "
            f"N={N_grid[idx]:.3g}, {_coord_tuple_text(gci)}"
        )
        return [card_text, footer, title, *lines.values(), *axes.flat]

    anim = animation.FuncAnimation(fig, _update, frames=len(frame_idxs) + 1, blit=False)
    fname = output_dir / f"spatial_field_movie.{movie_format}"
    _save_movie(anim, fname, movie_format)
    plt.close(fig)


def plot_spatial_derived_movie(
    adapters, frame_N_objects, output_dir, movie_format: str = "gif",
    run_label: str = "", n_frames=None,
):
    """ζ(r)/C(r) movie through N (design §6.3, §6.2 item 3): each frame
    calls `SpatialAdapter.derived_at_time(N_query)` once (cache-backed via
    `GradientCoupledInstanton.zeta_C_r_at_time`'s `ExtractionCache` -- see
    this module's docstring; no second cache layer is added here).

    `frame_N_objects` MUST be the real `efold_value` objects the wrapped
    `GradientCoupledInstanton` was stored against (i.e. `v.N` for `v` in its
    `.values`), not synthetic per-frame stand-ins: `zeta_C_r_at_time`'s
    cache key is `(self.store_id, N_query.store_id)` -- identity-based on
    the query object's own `store_id` -- so a synthetic object without a
    real, distinct `store_id` would make every frame collide on the same
    cache key and silently repeat the first frame's result. The
    `@ray.remote` wrapper below sources this list from the materialised
    `GradientCoupledInstanton.values`, worker-side, alongside building the
    adapter -- see `_render_spatial_derived_movie_item`.

    `n_frames`, if given, evenly-samples `frame_N_objects` down to that
    many frames. Uses `r_ratio` (dimensionless comoving r / r_out) as the
    x-axis rather than `r_phys` converted to Mpc, since Mpc conversion
    needs the working unit system, which is only reachable via the
    adapter's private `_units()` -- `r_ratio` needs no such reach-through
    and is already part of `zeta_C_r_at_time`'s return dict.
    """
    if not any(a.is_spatial() and a.available for a in adapters):
        return
    gci = _first_available_spatial(adapters)
    if gci is None or not frame_N_objects:
        return

    frames = list(frame_N_objects)
    if n_frames is not None:
        frames = _evenly_sample(frames, n_frames)

    fig, (ax_zeta, ax_C) = plt.subplots(1, 2, figsize=(12, 5.5))
    (line_zeta,) = ax_zeta.plot([], [])
    (line_C,) = ax_C.plot([], [])
    ax_zeta.set_xlabel(r"$r / r_{\rm out}$")
    ax_zeta.set_ylabel(r"$\zeta$")
    ax_C.set_xlabel(r"$r / r_{\rm out}$")
    ax_C.set_ylabel(r"$C$")

    title = fig.suptitle("")
    card_text = fig.text(0.5, 0.5, "", ha="center", va="center", fontsize=11, wrap=True)
    footer = fig.text(
        0.5, 0.003, "", ha="center", va="bottom", fontsize=7, color="#888888",
        transform=fig.transFigure,
    )
    provenance_text = _movie_provenance_text(gci, run_label=run_label)

    def _update(frame_pos):
        footer.set_text(provenance_text)
        if frame_pos == 0:
            # Opening title card (design §9 item 3): axes hidden, not just
            # the data lines, so the card text isn't overlaid on empty
            # tick/label chrome.
            card_text.set_text(provenance_text)
            card_text.set_visible(True)
            ax_zeta.set_visible(False)
            ax_C.set_visible(False)
            line_zeta.set_visible(False)
            line_C.set_visible(False)
            return [card_text, footer, ax_zeta, ax_C, line_zeta, line_C]
        card_text.set_visible(False)
        ax_zeta.set_visible(True)
        ax_C.set_visible(True)
        line_zeta.set_visible(True)
        line_C.set_visible(True)
        result = gci.derived_at_time(frames[frame_pos - 1])
        r = result["r_ratio"]
        line_zeta.set_data(r, result["zeta"])
        line_C.set_data(r, result["C"])
        for ax in (ax_zeta, ax_C):
            ax.relim()
            ax.autoscale_view()
        title.set_text(
            rf"$\zeta(r)/C(r)$ ({gci.display_label}) — "
            f"N={float(result['N']):.3g}, {_coord_tuple_text(gci)}"
        )
        return [card_text, footer, title, line_zeta, line_C, ax_zeta, ax_C]

    anim = animation.FuncAnimation(fig, _update, frames=len(frames) + 1, blit=False)
    fname = output_dir / f"spatial_derived_movie.{movie_format}"
    _save_movie(anim, fname, movie_format)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Ray-dispatch layer (design §5's spatial-work caveat)
# ---------------------------------------------------------------------------


@ray.remote
def _render_spatial_heatmaps_item(
    gci_proxy, coords, other_adapters, output_dir_str, fmt, run_label
):
    """`@ray.remote` render wrapper for `plot_spatial_heatmaps`. Takes the
    cheap `GradientCoupledInstantonProxy` handle -- never the dense
    `(y, N)` arrays themselves -- and does `.get()` plus the
    `GradientCoupledAdapter` construction here, worker-side, per design
    §5's caveat ("do not serialise big arrays through the work queue").
    `other_adapters` are already-materialised, lightweight `InstantonAdapter`
    instances (e.g. Full/SlowRoll, for the core-slice overlay); those are
    fine to pass by value, exactly as every other figure family already
    does -- the caveat is specific to GCI's dense grid."""
    sns.set_theme()
    gci_adapter = GradientCoupledAdapter(gci_proxy.get(), coords=coords, fidelity="dense")
    plot_spatial_heatmaps(
        [gci_adapter, *other_adapters], Path(output_dir_str), fmt, run_label=run_label
    )


@ray.remote
def _render_spatial_slices_item(
    gci_proxy, coords, other_adapters, output_dir_str, fmt, run_label
):
    """Same proxy-passing convention as `_render_spatial_heatmaps_item`, for
    `plot_spatial_slices`."""
    sns.set_theme()
    gci_adapter = GradientCoupledAdapter(gci_proxy.get(), coords=coords, fidelity="dense")
    plot_spatial_slices(
        [gci_adapter, *other_adapters], Path(output_dir_str), fmt, run_label=run_label
    )


@ray.remote
def _render_spatial_field_movie_item(
    gci_proxy, coords, output_dir_str, movie_format, run_label, n_frames=None
):
    """`@ray.remote` render wrapper for `plot_spatial_field_movie`. Same
    proxy-passing convention as `_render_spatial_heatmaps_item`: the movie
    is the most expensive output in the whole design (§6.2 item 3), so it
    is rendered worker-side, from the proxy, never on the driver. Movies
    are strictly opt-in -- this wrapper is only ever dispatched by the
    driver's `--movies` work-item construction (P8); it performs no gating
    of its own (design's own instruction: an ungated call must still render
    correctly, e.g. from a test)."""
    sns.set_theme()
    gci_adapter = GradientCoupledAdapter(gci_proxy.get(), coords=coords, fidelity="dense")
    plot_spatial_field_movie(
        [gci_adapter], Path(output_dir_str), movie_format=movie_format,
        run_label=run_label, n_frames=n_frames,
    )


@ray.remote
def _render_spatial_derived_movie_item(
    gci_proxy, coords, output_dir_str, movie_format, run_label, n_frames=None
):
    """`@ray.remote` render wrapper for `plot_spatial_derived_movie`. Unlike
    the other three wrappers, this one keeps a reference to the
    materialised `GradientCoupledInstanton` (`gci_raw`, not just the
    adapter built from it): `plot_spatial_derived_movie` needs the real
    `efold_value` objects backing each stored sample (`v.N` for `v` in
    `gci_raw.values`) to pass into `derived_at_time` frame by frame, since
    `zeta_C_r_at_time`'s cache is keyed on that object's own `store_id`
    (see `plot_spatial_derived_movie`'s docstring) -- the adapter's public
    surface exposes only the float `N_grid`, not these objects, so this
    wrapper reads `.values` off the raw object it already holds from
    `gci_proxy.get()`, exactly as `GradientCoupledAdapter.field_2d` does
    internally."""
    sns.set_theme()
    gci_raw = gci_proxy.get()
    gci_adapter = GradientCoupledAdapter(gci_raw, coords=coords, fidelity="dense")
    frame_N_objects = [v.N for v in gci_raw.values]
    plot_spatial_derived_movie(
        [gci_adapter], frame_N_objects, Path(output_dir_str), movie_format=movie_format,
        run_label=run_label, n_frames=n_frames,
    )
