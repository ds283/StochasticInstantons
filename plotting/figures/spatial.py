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
§6.2 items 1-2 (heatmaps + slice overlays). These are the *static, default*
tier -- movies (§6.2 item 3) are P5b and are deliberately not implemented
here.

Both figures gate on `adapter.is_spatial()` (design §3.3's own guard
pattern), never on which *kind* of adapter is present, so a figure function
never has to special-case `GradientCoupledAdapter` beyond picking the right
data-access method (`field_2d` vs `time_history`) -- exactly the discipline
every other module in `plotting/figures/` already follows.

Per design §5's proxy-passing caveat, the dense `(y, N)` grid must not cross
the driver-to-worker boundary as raw numpy through the `(remote_fn, args)`
work-item tuple. `_render_spatial_heatmaps_item`/`_render_spatial_slices_item`
below are the `@ray.remote` wrappers a driver (P8) dispatches through: they
take the cheap `GradientCoupledInstantonProxy` handle and build the
`GradientCoupledAdapter` (== `SpatialAdapter`, see `plotting/adapters/
gradient.py`) worker-side, from `.get()`, never on the driver.
"""

from pathlib import Path

import ray
import seaborn as sns
from matplotlib import pyplot as plt

from plotting.adapters.gradient import GradientCoupledAdapter
from plotting.provenance import _provenance_footer
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
