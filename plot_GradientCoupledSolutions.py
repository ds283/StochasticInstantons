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
`plot_GradientCoupledSolutions.py` -- the gradient-coupled (onion-model)
science-output driver (design doc
`.documents/gradient-coupled-plotting/DESIGN_gradient_coupled_plotting.md`,
§10; Prompt P8,
`.prompts/gradient-coupled-plotting/13-P8-new-driver-and-compare-mode.md`).

Mirrors `plot_InstantonSolutions.py`'s `create_plot_parser`/`run_plots`
structure closely, but drives `GradientCoupledInstanton` across the extra
`alpha`/`n_collocation_points` axes (read verbatim off
`config/pipeline_setup.py::build_pipeline_inputs`'s existing
`n_collocation_points_array`/`alpha_regularization_array` -- see this
prompt set's `00-README.md` "Correction 1": no new CLI quartet, no
`build_gci_inputs`). `plot_InstantonSolutions.py` itself is untouched.

Wires in whichever of P5a (spatial heatmaps/slices)/P5b (spatial movies)/P6
(stability overlays)/P7 (diagnostics figures) exist in the current tree;
all four are present as of this prompt's authoring, so this driver
dispatches the full set.
"""

import csv
import itertools
import sys
from pathlib import Path

import ray
import seaborn as sns

from ComputeTargets import InflatonTrajectoryProxy
from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
    GradientCoupledInstantonProxy,
)
from config.argument_parser import create_argument_parser
from config.grid_builder import build_gradient_grid
from config.pipeline_setup import build_pipeline_inputs
from config.sharding import (
    ShardKeyType,
    get_shard_key_store_id,
    inventory_config,
    read_table_config,
    replicated_tables,
    sharded_tables,
)
from CosmologyModels.params import Planck2018
from Datastore.SQL.ShardedPool import ShardedPool
from plotting.adapters.full import FullInstantonAdapter
from plotting.adapters.gradient import GradientCoupledAdapter
from plotting.adapters.slow_roll import SlowRollInstantonAdapter
from plotting.dispatch import _dispatch_plot_work
from plotting.fetch import (
    CFFetchSpec,
    ClassFetchSpec,
    _instanton_key_payload,
    fetch_adapters_over_grid,
    fetch_over_grid,
)
from plotting.figures.compaction import plot_zeta_and_compaction
from plotting.figures.diagnostics import (
    plot_compute_time_distributions,
    plot_convergence_map,
    plot_cost_vs_parameters,
    plot_extraction_failure_heatmap,
    plot_extraction_failure_summary,
    plot_picard_newton_structure,
    plot_speedup,
    plot_stiffness,
)
from plotting.figures.doe import plot_doe_scalar_summary
from plotting.figures.noise import plot_noise_profile
from plotting.figures.spatial import (
    _render_spatial_derived_movie_item,
    _render_spatial_field_movie_item,
    _render_spatial_heatmaps_item,
    _render_spatial_slices_item,
)
from plotting.figures.stability import (
    render_alpha_stability,
    render_n_collocation_stability,
)
from plotting.figures.sweeps import plot_compaction_summary, plot_msr_action_sweep
from plotting.figures.time_history import plot_instanton_fields
from plotting.provenance import VERSION_LABEL
from plotting.sampling import _evenly_sample, _safe_name, _safe_num
from RayTools.RayWorkPool import RayWorkPool
from Units import Planck_units

DEFAULT_MAX_TRAJECTORIES = 3
DEFAULT_MAX_COMBINATIONS = 10
DEFAULT_MAX_INSTANTON_SAMPLES = 30
DEFAULT_SPATIAL_SAMPLES = 5

# CSV companion columns (mirrors plotting/fetch.py's own _DIAGNOSTIC_CSV_KEYS
# for the homogeneous driver's diagnostics_data.csv -- kept as a local copy
# here since this driver's flatten functions are keyed by `adapter.kind`
# rather than the fixed full/slow-roll pair plotting/fetch.py's own
# flatten_diagnostics_for_csv assumes; see _flatten_gci_diagnostics_for_csv).
_DIAGNOSTIC_CSV_KEYS = (
    "compute_time",
    "converged",
    "final_residual",
    "total_ode_solves",
    "outer_iterations",
    "newton_fallback_count",
    "final_lambda",
    "mean_picard_iterations",
)


def create_plot_parser():
    """Reuses the shared compute-pipeline parser (config/argument_parser.py),
    exactly as plot_InstantonSolutions.py does, then adds a driver-local
    argument group. Deliberately does NOT add --n-collocation-{low,high,
    samples,values} or --alpha-{low,high,samples,values} -- see this prompt
    set's 00-README.md "Correction 1": the existing --n-collocation-points/
    --alpha-regularization list flags (already parsed by
    create_argument_parser()) are what both main.py and this driver consume,
    so the plotted sweep can never silently diverge from what was actually
    computed."""
    parser = create_argument_parser()

    plot_grp = parser.add_argument_group("Plotting (gradient-coupled)")
    plot_grp.add_argument(
        "--output-dir",
        type=str,
        default="plots_gradient",
        help="Directory for output figures (default: 'plots_gradient/')",
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
        f"plot, evenly sampled across the grid (default: {DEFAULT_MAX_COMBINATIONS})",
    )
    plot_grp.add_argument(
        "--max-instanton-samples",
        type=int,
        default=DEFAULT_MAX_INSTANTON_SAMPLES,
        help="Maximum number of (N_init, N_final, delta_Nstar, n_collocation_points, "
        "alpha_regularization) combinations to render in the instantons/ folder, "
        f"evenly sampled across the full grid (default: {DEFAULT_MAX_INSTANTON_SAMPLES})",
    )
    plot_grp.add_argument(
        "--spatial-samples",
        type=int,
        default=DEFAULT_SPATIAL_SAMPLES,
        help="How many of the --max-instanton-samples grid points additionally "
        "get the heavy (y,N) spatial treatment (heatmaps/slices, and movies if "
        f"--movies is set) (default: {DEFAULT_SPATIAL_SAMPLES})",
    )
    plot_grp.add_argument(
        "--movies",
        action="store_true",
        default=False,
        help="Render opt-in (y,N) spatial movies (plotting/figures/spatial.py: "
        "plot_spatial_field_movie) for the --spatial-samples grid points, in "
        "addition to the default static heatmaps/slices (default: off -- movies "
        "are the most expensive output in the design and stay strictly opt-in).",
    )
    plot_grp.add_argument(
        "--movie-format",
        type=str,
        default="gif",
        choices=["gif", "mp4"],
        help="Movie container format when --movies is set (default: gif, "
        "Pillow-only, no external dependency; mp4 requires ffmpeg on the "
        "render node).",
    )
    plot_grp.add_argument(
        "--compare-with",
        nargs="*",
        default=[],
        choices=["full", "slow-roll"],
        help="When non-empty, the detailed-sample and (N_init/N_final/delta_Nstar) "
        "sweep passes additionally fetch the matching FullInstanton/"
        "SlowRollInstanton (+ CompactionFunction) at each sampled grid point, wrap "
        "them as adapters, and overlay them on the same figures as the "
        "GradientCoupledInstanton adapter -- zero new plotting code (default: "
        "[], GCI-only).",
    )
    plot_grp.add_argument(
        "--time-resolved-derived",
        action="store_true",
        default=False,
        help="Enable the recompute-heavy zeta(r)/C(r)-through-N movie "
        "(plotting/figures/spatial.py: plot_spatial_derived_movie) for the "
        "--spatial-samples grid points. Only takes effect when --movies is also "
        "set (default: off).",
    )
    return parser


# ── GCI datastore key / grid-item helpers ────────────────────────────────────
#
# Every grid item used by this driver has the shape
# ((N_init_obj, N_final_obj, dns_obj), n_collocation_points_obj,
# alpha_regularization_obj) -- exactly config/grid_builder.py::
# build_gradient_grid's own output shape -- so one coords_of/key_payload_of
# pair works for every fetch in this file (DOE/diagnostics collection, the
# N_init/N_final/delta_Nstar sweeps, and the detailed-sample pass).


def _gci_key_payload(
    traj_proxy, N_init_obj, N_final_obj, dns_obj, ncp_obj, alpha_obj, atol, rtol, cosmo, dm
):
    """The GradientCoupledInstanton datastore identity payload (mirrors
    main.py::_run_gradient_branch's own key_fields closure and
    plotting/figures/stability.py's own _gci_key_payload)."""
    return dict(
        trajectory=traj_proxy,
        N_init=N_init_obj,
        N_final=N_final_obj,
        delta_Nstar=dns_obj,
        n_collocation_points=ncp_obj,
        alpha_regularization=alpha_obj,
        atol=atol,
        rtol=rtol,
        cosmo=cosmo,
        diffusion_model=dm,
        tags=[],
    )


def _coords_of_gci_item(item) -> dict:
    (N_init_obj, N_final_obj, dns_obj), ncp_obj, alpha_obj = item
    return {
        "N_init": float(N_init_obj),
        "N_final": float(N_final_obj),
        "delta_Nstar": float(dns_obj),
        "n_collocation_points": int(ncp_obj),
        "alpha": float(alpha_obj),
    }


def _gci_class_spec(traj_proxy, atol, rtol, cosmo, dm, fidelity: str) -> ClassFetchSpec:
    return ClassFetchSpec(
        name="gci",
        class_name="GradientCoupledInstanton",
        shard_key_of=lambda item: item[0][2],
        key_payload_of=lambda item: _gci_key_payload(
            traj_proxy, item[0][0], item[0][1], item[0][2], item[1], item[2],
            atol, rtol, cosmo, dm,
        ),
        adapter_factory=lambda obj, cf, coords: GradientCoupledAdapter(
            obj, coords=coords, fidelity=fidelity
        ),
    )


def _compare_class_specs(traj_proxy, atol, rtol, dm, compare_with) -> list:
    """ClassFetchSpecs for whichever of "full"/"slow-roll" appear in
    --compare-with -- built over the SAME nested grid-item shape as the GCI
    spec, extracting (N_init, N_final, delta_Nstar) from item[0] and
    ignoring the n_collocation_points/alpha entries (the homogeneous
    solvers don't have those axes)."""
    specs = []
    if "full" in compare_with:
        specs.append(
            ClassFetchSpec(
                name="full",
                class_name="FullInstanton",
                shard_key_of=lambda item: item[0][2],
                key_payload_of=lambda item: _instanton_key_payload(
                    traj_proxy, item[0][0], item[0][1], item[0][2], atol, rtol, dm
                ),
                adapter_factory=lambda obj, cf, coords: FullInstantonAdapter(
                    obj, cf, coords=coords
                ),
            )
        )
    if "slow-roll" in compare_with:
        specs.append(
            ClassFetchSpec(
                name="slow-roll",
                class_name="SlowRollInstanton",
                shard_key_of=lambda item: item[0][2],
                key_payload_of=lambda item: _instanton_key_payload(
                    traj_proxy, item[0][0], item[0][1], item[0][2], atol, rtol, dm
                ),
                adapter_factory=lambda obj, cf, coords: SlowRollInstantonAdapter(
                    obj, cf, coords=coords
                ),
            )
        )
    return specs


def _build_class_specs(traj_proxy, atol, rtol, cosmo, dm, compare_with, fidelity: str) -> list:
    """GCI spec first (so `adapters[0]` is always the GCI adapter at every
    call site in this file), followed by whichever compare specs apply."""
    return [_gci_class_spec(traj_proxy, atol, rtol, cosmo, dm, fidelity)] + _compare_class_specs(
        traj_proxy, atol, rtol, dm, compare_with
    )


def _cf_spec_if_full_and_sr(traj_proxy, cosmo, atol, rtol, compare_with):
    """A CompactionFunction pairing is only built when BOTH "full" and
    "slow-roll" were requested via --compare-with -- CFFetchSpec (P2b)
    requires both a fi_spec_name and an sri_spec_name to resolve against
    `class_specs`. Requesting only one of the two still overlays that
    solver's own time-history channels; it just won't carry CF-derived
    compaction scalars (C_peak/M_max/...) on its adapter, since those are
    only ever populated once a CompactionFunction is paired in."""
    if "full" not in compare_with or "slow-roll" not in compare_with:
        return None
    return CFFetchSpec(
        shard_key_of=lambda item: item[0][2],
        traj_proxy=traj_proxy,
        fi_spec_name="full",
        sri_spec_name="slow-roll",
        cosmo=cosmo,
        atol=atol,
        rtol=rtol,
    )


# ── Ray remote plot dispatch (GCI-fed) ───────────────────────────────────────


@ray.remote
def _plot_gci_fields_item(
    adapters, N_init_val, N_final_val, dns_val, potential, output_dir_str, fmt, run_label: str = ""
):
    sns.set_theme()
    output_dir = Path(output_dir_str)
    units = Planck_units()
    # cf_annotation is left None here: the legacy CF summary box is keyed to
    # the full/slow-roll-suffixed vocabulary of plotting.annotations, which
    # doesn't generalise to a GCI-primary point; the same scalars are already
    # visible per-adapter via the in-figure MSR-action annotation and via the
    # DOE/sweep/stability figures.
    plot_instanton_fields(
        adapters, N_init_val, N_final_val, dns_val, potential, units,
        output_dir, fmt, cf_annotation=None, run_label=run_label,
    )


@ray.remote
def _plot_gci_noise_item(
    adapters, N_init_val, N_final_val, dns_val, potential_name, output_dir_str, fmt, run_label: str = ""
):
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_noise_profile(
        adapters, N_init_val, N_final_val, dns_val, potential_name,
        output_dir, fmt, cf_annotation=None, run_label=run_label,
    )


@ray.remote
def _plot_gci_compaction_item(
    adapters, N_init_val, N_final_val, dns_val, potential_name, output_dir_str, fmt, run_label: str = ""
):
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_zeta_and_compaction(
        adapters, N_init_val, N_final_val, dns_val, potential_name,
        output_dir, fmt, cf_annotation=None, run_label=run_label,
    )


@ray.remote
def _plot_gci_msr_sweep_item(
    adapters, x_label, fixed_desc, potential_name, output_dir_str, fmt, swept_name, run_label: str = ""
):
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_msr_action_sweep(
        adapters, x_label, fixed_desc, potential_name, output_dir, fmt, swept_name,
        run_label=run_label,
    )


@ray.remote
def _plot_gci_compaction_summary_item(
    adapters, x_label, fixed_desc, potential_name, output_dir_str, fmt, swept_name, run_label: str = ""
):
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_compaction_summary(
        adapters, x_label, fixed_desc, potential_name, output_dir, fmt, swept_name,
        run_label=run_label,
    )


@ray.remote
def _plot_gci_doe_summary_item(
    points, potential_name, output_dir_str, fmt, threshold, run_label: str = ""
):
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_doe_scalar_summary(points, potential_name, output_dir, fmt, threshold, run_label=run_label)


@ray.remote
def _plot_gci_diagnostics_item(adapters, potential_name, output_dir_str, fmt, run_label: str = ""):
    """Renders every diagnostics figure family (P7, design §8 items 2-8) in
    one worker call, fed by the same adapter list the DOE pass already
    fetched -- no second fetch pass (design's own "costs essentially nothing
    extra" point)."""
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_compute_time_distributions(adapters, potential_name, output_dir, fmt, run_label=run_label)
    plot_cost_vs_parameters(adapters, potential_name, output_dir, fmt, run_label=run_label)
    plot_convergence_map(adapters, potential_name, output_dir, fmt, run_label=run_label)
    plot_speedup(adapters, potential_name, output_dir, fmt, run_label=run_label)
    plot_picard_newton_structure(adapters, potential_name, output_dir, fmt, run_label=run_label)
    plot_stiffness(adapters, potential_name, output_dir, fmt, run_label=run_label)
    plot_extraction_failure_summary(adapters, potential_name, output_dir, fmt, run_label=run_label)
    plot_extraction_failure_heatmap(adapters, potential_name, output_dir, fmt, run_label=run_label)


# ── Scalar + diagnostics collection (cheap tier, full grid) ──────────────────


def _collect_gci_points(pool, traj_proxy, gci_grid, cosmo, atol, rtol, dm, compare_with) -> list:
    """Cheap-tier (_do_not_populate=True) collection over the FULL gci_grid,
    fused scalars+diagnostics per design §8 ("this costs essentially nothing
    extra" -- diagnostics rides on the same parent-row fetch as the scalars).
    Returns one dict per grid point where at least one requested adapter is
    available:
        {"delta_Nstar": float, "delta_N": float, "alpha": float,
         "n_collocation_points": int, "adapters": [InstantonAdapter, ...]}
    `adapters[0]` is always the GradientCoupledAdapter; any further entries
    are the --compare-with Full/SlowRoll adapters, in that fixed order."""
    if not gci_grid:
        return []
    class_specs = _build_class_specs(traj_proxy, atol, rtol, cosmo, dm, compare_with, fidelity="scalars")
    cf_spec = _cf_spec_if_full_and_sr(traj_proxy, cosmo, atol, rtol, compare_with)
    rows = fetch_adapters_over_grid(
        pool, gci_grid, class_specs, _coords_of_gci_item, cf_spec=cf_spec, do_not_populate=True
    )

    points = []
    for item, adapters in zip(gci_grid, rows):
        if not any(a.available for a in adapters):
            continue
        (N_init_obj, N_final_obj, dns_obj), ncp_obj, alpha_obj = item
        points.append(
            {
                "delta_Nstar": float(dns_obj),
                "delta_N": float(N_init_obj) - float(N_final_obj),
                "alpha": float(alpha_obj),
                "n_collocation_points": int(ncp_obj),
                "adapters": adapters,
            }
        )
    return points


def _point_coords(p: dict) -> dict:
    for a in p["adapters"]:
        if a.coords:
            return a.coords
    return {}


def _flatten_gci_points_for_csv(points: list) -> list:
    """scalar_data.csv rows, one column-family per adapter `.kind` present
    (a fixed vocabulary: "gradient_coupled"/"full"/"slow_roll" -- CSV
    serialisation is the one place allowed to key off adapter identity, per
    plotting/fetch.py::flatten_doe_points_for_csv's own precedent)."""
    rows = []
    for p in points:
        coords = _point_coords(p)
        row = {
            "N_init": coords.get("N_init"),
            "N_final": coords.get("N_final"),
            "delta_Nstar": p["delta_Nstar"],
            "delta_N": p["delta_N"],
            "alpha": p["alpha"],
            "n_collocation_points": p["n_collocation_points"],
        }
        for a in p["adapters"]:
            prefix = a.kind.replace("-", "_")
            for key, val in a.scalars().items():
                row[f"{key}_{prefix}"] = val
        rows.append(row)
    return rows


def _flatten_gci_diagnostics_for_csv(points: list) -> list:
    """diagnostics_data.csv rows, sharing the same grid-point identification
    columns as _flatten_gci_points_for_csv's scalar_data.csv rows (design §8
    item 9), so the two can be joined downstream."""
    rows = []
    for p in points:
        coords = _point_coords(p)
        row = {
            "N_init": coords.get("N_init"),
            "N_final": coords.get("N_final"),
            "delta_Nstar": p["delta_Nstar"],
            "delta_N": p["delta_N"],
            "alpha": p["alpha"],
            "n_collocation_points": p["n_collocation_points"],
        }
        for a in p["adapters"]:
            prefix = a.kind.replace("-", "_")
            d = a.diagnostics() or {}
            for key in _DIAGNOSTIC_CSV_KEYS:
                row[f"diag_{key}_{prefix}"] = d.get(key)
        rows.append(row)
    return rows


def _run_gci_doe_and_diagnostics(
    pool, traj_proxy, potential, traj_dir, fmt, gci_grid, cosmo, atol, rtol, dm,
    compare_with, work_items: list, threshold: float = 0.4, run_label: str = "",
):
    print(f"   >> Collecting scalar+diagnostics summaries for {len(gci_grid)} grid point(s)...")
    points = _collect_gci_points(pool, traj_proxy, gci_grid, cosmo, atol, rtol, dm, compare_with)
    if not points:
        print("   >> No data found — skipping DOE/diagnostics plots and CSVs.")
        return
    print(f"   >> {len(points)} point(s) with data; queuing DOE/diagnostics plots.")

    doe_dir = traj_dir / "doe_summary"
    doe_dir.mkdir(parents=True, exist_ok=True)
    diag_dir = traj_dir / "diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)

    work_items.append(
        (_plot_gci_doe_summary_item, (points, potential.name, str(doe_dir), fmt, threshold, run_label))
    )

    all_adapters = [a for p in points for a in p["adapters"]]
    work_items.append(
        (_plot_gci_diagnostics_item, (all_adapters, potential.name, str(diag_dir), fmt, run_label))
    )

    csv_rows = _flatten_gci_points_for_csv(points)
    csv_path = doe_dir / "scalar_data.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"   >> Scalar data written to {csv_path}")

    diag_rows = _flatten_gci_diagnostics_for_csv(points)
    diag_csv_path = doe_dir / "diagnostics_data.csv"
    with open(diag_csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(diag_rows[0].keys()))
        writer.writeheader()
        writer.writerows(diag_rows)
    print(f"   >> Diagnostics data written to {diag_csv_path}")


# ── Sweep passes: N_init / N_final / delta_Nstar (fixed alpha/n_colloc) ──────
#
# alpha / n_collocation_points are swept separately, by plotting/figures/
# stability.py's own entry points (see _run_gci_stability_sweeps below) --
# plotting/figures/sweeps.py's swept_file mapping only knows about
# N_init/N_final/delta_Nstar, by design (P6 exists precisely because the
# stability overlays are a different figure family, not a third axis bolted
# onto sweeps.py).


def _sweep_gci_axis(
    pool, traj_proxy, potential, out_dir, fmt, swept_name, swept_array, fixed_other_array,
    dns_array, fixed_ncp_obj, fixed_alpha_obj, atol, rtol, cosmo, dm, max_combos,
    work_items: list, compare_with, run_label: str = "",
):
    """swept_name in {"N_init", "N_final"}. Fixes n_collocation_points/alpha
    at fixed_ncp_obj/fixed_alpha_obj (the first value of each array, per the
    driver's own choice -- alpha/n_colloc sensitivity is what
    _run_gci_stability_sweeps is for)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    combos = list(itertools.product(fixed_other_array, dns_array))
    selected = _evenly_sample(combos, max_combos)

    for other_val, dns_val in selected:
        if swept_name == "N_init":
            items = [((v, other_val, dns_val), fixed_ncp_obj, fixed_alpha_obj) for v in swept_array]
            fixed_desc = (
                f"Nfinal={float(other_val):.3g}_dNstar={float(dns_val):.3g}"
                f"_ncolloc={int(fixed_ncp_obj)}_alpha={float(fixed_alpha_obj):.3g}"
            )
            x_label = r"$N_{\rm init}$"
        else:
            items = [((other_val, v, dns_val), fixed_ncp_obj, fixed_alpha_obj) for v in swept_array]
            fixed_desc = (
                f"Ninit={float(other_val):.3g}_dNstar={float(dns_val):.3g}"
                f"_ncolloc={int(fixed_ncp_obj)}_alpha={float(fixed_alpha_obj):.3g}"
            )
            x_label = r"$N_{\rm final}$"

        class_specs = _build_class_specs(traj_proxy, atol, rtol, cosmo, dm, compare_with, fidelity="scalars")
        cf_spec = _cf_spec_if_full_and_sr(traj_proxy, cosmo, atol, rtol, compare_with)
        rows = fetch_adapters_over_grid(
            pool, items, class_specs, _coords_of_gci_item, cf_spec=cf_spec, do_not_populate=True
        )
        adapters = [a for row in rows for a in row]

        if any(a.available and not a.failure for a in adapters):
            work_items.append(
                (_plot_gci_msr_sweep_item, (adapters, x_label, fixed_desc, potential.name, str(out_dir), fmt, swept_name, run_label))
            )
        if any(
            a.scalars().get("C_peak") is not None or a.scalars().get("C_bar_peak") is not None
            for a in adapters
        ):
            work_items.append(
                (_plot_gci_compaction_summary_item, (adapters, x_label, fixed_desc, potential.name, str(out_dir), fmt, swept_name, run_label))
            )


def _sweep_gci_delta_Nstar(
    pool, traj_proxy, potential, out_dir, fmt, dns_array, N_init_array, N_final_array,
    fixed_ncp_obj, fixed_alpha_obj, atol, rtol, cosmo, dm, max_combos,
    work_items: list, compare_with, run_label: str = "",
):
    out_dir.mkdir(parents=True, exist_ok=True)
    combos = list(itertools.product(N_init_array, N_final_array))
    selected = _evenly_sample(combos, max_combos)

    items = [
        ((N_init_v, N_final_v, dns_val), fixed_ncp_obj, fixed_alpha_obj)
        for (N_init_v, N_final_v) in selected
        for dns_val in dns_array
    ]
    class_specs = _build_class_specs(traj_proxy, atol, rtol, cosmo, dm, compare_with, fidelity="scalars")
    cf_spec = _cf_spec_if_full_and_sr(traj_proxy, cosmo, atol, rtol, compare_with)
    rows = fetch_adapters_over_grid(
        pool, items, class_specs, _coords_of_gci_item, cf_spec=cf_spec, do_not_populate=True
    )

    n_dns = len(dns_array)
    for combo_idx, (N_init_v, N_final_v) in enumerate(selected):
        combo_rows = rows[combo_idx * n_dns : (combo_idx + 1) * n_dns]
        adapters = [a for row in combo_rows for a in row]
        fixed_desc = (
            f"Ninit={float(N_init_v):.3g}_Nfinal={float(N_final_v):.3g}"
            f"_ncolloc={int(fixed_ncp_obj)}_alpha={float(fixed_alpha_obj):.3g}"
        )

        if any(a.available and not a.failure for a in adapters):
            work_items.append(
                (_plot_gci_msr_sweep_item, (adapters, r"$\delta N_\star$", fixed_desc, potential.name, str(out_dir), fmt, "delta_Nstar", run_label))
            )
        if any(
            a.scalars().get("C_peak") is not None or a.scalars().get("C_bar_peak") is not None
            for a in adapters
        ):
            work_items.append(
                (_plot_gci_compaction_summary_item, (adapters, r"$\delta N_\star$", fixed_desc, potential.name, str(out_dir), fmt, "delta_Nstar", run_label))
            )


def _run_gci_stability_sweeps(
    pool, traj_proxy, potential, traj_dir, fmt, N_init_array, N_final_array, dns_array,
    n_collocation_points_array, alpha_regularization_array, atol, rtol, cosmo, dm,
    max_combos, run_label: str = "",
):
    """alpha / n_collocation_points overlays (P6), run directly on the driver
    -- render_n_collocation_stability/render_alpha_stability do their own
    fetch_over_grid-based fetching and render synchronously (no Ray dispatch,
    unlike every other figure family in this file); they self-skip (no fetch,
    no file, no exception) whenever fewer than two values of the swept axis
    were actually computed."""
    stability_dir = traj_dir / "stability"
    stability_dir.mkdir(parents=True, exist_ok=True)

    combos = list(itertools.product(N_init_array, N_final_array, dns_array))
    selected = _evenly_sample(combos, max_combos)

    # Fixed axis value for each stability sweep is the first array entry --
    # sensitivity across the OTHER axis is exactly what each call below
    # explores; sweeping both at once is a 2-D grid this driver doesn't
    # attempt to visualise.
    fixed_alpha = alpha_regularization_array[0]
    fixed_ncp = n_collocation_points_array[0]

    for N_init_obj, N_final_obj, dns_obj in selected:
        render_n_collocation_stability(
            pool, traj_proxy, N_init_obj, N_final_obj, dns_obj, fixed_alpha,
            n_collocation_points_array, atol, rtol, cosmo, dm,
            potential.name, stability_dir, fmt, run_label=run_label,
        )
        render_alpha_stability(
            pool, traj_proxy, N_init_obj, N_final_obj, dns_obj, fixed_ncp,
            alpha_regularization_array, atol, rtol, cosmo, dm,
            potential.name, stability_dir, fmt, run_label=run_label,
        )


# ── Detailed-sample pass: dense fetch, time_history/noise/compaction + spatial ──


def _generate_gci_instanton_samples(
    pool, traj_proxy, potential, out_dir, fmt, gci_grid, max_instanton_samples,
    spatial_samples, atol, rtol, cosmo, dm, compare_with, movies: bool,
    movie_format: str, time_resolved_derived: bool, work_items: list, run_label: str = "",
):
    """Evenly samples `gci_grid` down to `max_instanton_samples` points and
    does a single FULL (dense) fetch of GradientCoupledInstanton for each --
    the same fetch serves both the time_history/noise/compaction figures
    (which need the core-node dense values) and, for up to `spatial_samples`
    of that subset, the (y,N) heatmap/slice/movie dispatch (which needs the
    raw object to build a GradientCoupledInstantonProxy, per design §5's
    proxy-passing caveat)."""
    selected = _evenly_sample(gci_grid, max_instanton_samples)
    if not selected:
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_gci = fetch_over_grid(
        pool, "GradientCoupledInstanton",
        shard_key_of=lambda item: item[0][2],
        key_payload_of=lambda item: _gci_key_payload(
            traj_proxy, item[0][0], item[0][1], item[0][2], item[1], item[2],
            atol, rtol, cosmo, dm,
        ),
        items=selected, do_not_populate=False,
    )

    compare_specs = _compare_class_specs(traj_proxy, atol, rtol, dm, compare_with)
    cf_spec = _cf_spec_if_full_and_sr(traj_proxy, cosmo, atol, rtol, compare_with)
    compare_rows = fetch_adapters_over_grid(
        pool, selected, compare_specs, _coords_of_gci_item, cf_spec=cf_spec, do_not_populate=False
    )

    spatial_idx_set = set(_evenly_sample(list(range(len(selected))), spatial_samples))

    for idx, (item, raw_obj) in enumerate(zip(selected, raw_gci)):
        (N_init_obj, N_final_obj, dns_obj), ncp_obj, alpha_obj = item
        coords = _coords_of_gci_item(item)
        gci_adapter = GradientCoupledAdapter(raw_obj, coords=coords, fidelity="dense")
        other_adapters = compare_rows[idx]
        adapters = [gci_adapter, *other_adapters]

        if not any(a.available for a in adapters):
            continue

        combo_dir = out_dir / (
            f"Ninit={_safe_num(float(N_init_obj))}_Nfinal={_safe_num(float(N_final_obj))}"
            f"_dNstar={_safe_num(float(dns_obj))}_ncolloc={int(ncp_obj)}"
            f"_alpha={_safe_num(float(alpha_obj))}"
        )
        combo_dir.mkdir(parents=True, exist_ok=True)

        work_items.append(
            (_plot_gci_fields_item, (adapters, float(N_init_obj), float(N_final_obj), float(dns_obj), potential, str(combo_dir), fmt, run_label))
        )
        work_items.append(
            (_plot_gci_noise_item, (adapters, float(N_init_obj), float(N_final_obj), float(dns_obj), potential.name, str(combo_dir), fmt, run_label))
        )
        work_items.append(
            (_plot_gci_compaction_item, (adapters, float(N_init_obj), float(N_final_obj), float(dns_obj), potential.name, str(combo_dir), fmt, run_label))
        )

        if (
            idx in spatial_idx_set
            and raw_obj is not None
            and raw_obj.available
            and not raw_obj.failure
            and raw_obj.values
        ):
            gci_proxy = GradientCoupledInstantonProxy(raw_obj)
            work_items.append(
                (_render_spatial_heatmaps_item, (gci_proxy, coords, other_adapters, str(combo_dir), fmt, run_label))
            )
            work_items.append(
                (_render_spatial_slices_item, (gci_proxy, coords, other_adapters, str(combo_dir), fmt, run_label))
            )
            if movies:
                work_items.append(
                    (_render_spatial_field_movie_item, (gci_proxy, coords, str(combo_dir), movie_format, run_label))
                )
                if time_resolved_derived:
                    work_items.append(
                        (_render_spatial_derived_movie_item, (gci_proxy, coords, str(combo_dir), movie_format, run_label))
                    )


# ── Main pipeline ─────────────────────────────────────────────────────────────


def run_plots(pool, units, args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = args.format
    compare_with = list(getattr(args, "compare_with", []) or [])

    # ── Run provenance label ──────────────────────────────────────────────
    _db_stem = Path(args.database).name
    _cfg_stem = Path(args.config).name if getattr(args, "config", None) else None
    _flags = ["[scalars-only]" if getattr(args, "no_store_values", False) else "[full-fidelity]"]
    if getattr(args, "movies", False):
        _flags.append("[with-movies]")
    _run_label_parts = [p for p in [_db_stem, _cfg_stem] if p]
    _run_label_parts.append(" ".join(_flags))
    run_label = "  |  ".join(_run_label_parts)

    print("\n>> Building pipeline inputs...")
    inputs = build_pipeline_inputs(pool, units, args)
    atol, rtol = inputs["atol"], inputs["rtol"]
    N_init_array = inputs["N_init_array"]
    N_final_array = inputs["N_final_array"]
    dns_array = inputs["dns_array"]
    n_collocation_points_array = inputs["n_collocation_points_array"]
    alpha_regularization_array = inputs["alpha_regularization_array"]
    model_list = inputs["model_list"]

    selected_models = _evenly_sample(model_list, args.max_trajectories)

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
    traj_list = [t for t in raw_trajs if t.available and t._potential is not None]
    print(f"   {len(traj_list)} trajectory record(s) found in database")

    if not traj_list:
        print("No trajectories found. Run main.py first.")
        return
    if not dns_array:
        print("No delta_Nstar values found. Run main.py first.")
        return
    if not n_collocation_points_array or not alpha_regularization_array:
        print("No n_collocation_points/alpha_regularization values found. Run main.py first.")
        return

    print("\n>> Reading cosmological parameters...")
    cosmo = ray.get(pool.object_get("CosmologicalParams", params=Planck2018()))
    print(f"   Cosmological parameters: {cosmo.name} (store_id={cosmo.store_id})")

    dm = ray.get(pool.object_get("MasslessDecoupledDiffusion"))
    print(f"   Diffusion model: {dm.name} (store_id={dm.store_id})")

    max_combos = args.max_combinations
    max_instanton_samples = args.max_instanton_samples
    spatial_samples = args.spatial_samples

    work_items = []
    for traj in traj_list:
        potential = traj._potential
        traj_proxy = InflatonTrajectoryProxy(traj)
        traj_dir = output_dir / f"{_safe_name(potential.name)}_traj{traj.store_id}"
        traj_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n>> Trajectory {traj.store_id} ({potential.name}) -> {traj_dir}/")

        base_combos = list(itertools.product(N_init_array, N_final_array, dns_array))
        gci_grid = build_gradient_grid(base_combos, n_collocation_points_array, alpha_regularization_array)
        print(
            f"   >> gradient grid: {len(base_combos)} base point(s) x "
            f"{len(n_collocation_points_array)} n_collocation_points value(s) x "
            f"{len(alpha_regularization_array)} alpha_regularization value(s) = "
            f"{len(gci_grid)} combination(s)"
        )

        _run_gci_doe_and_diagnostics(
            pool, traj_proxy, potential, traj_dir, fmt, gci_grid, cosmo, atol, rtol, dm,
            compare_with, work_items, run_label=run_label,
        )

        fixed_ncp = n_collocation_points_array[0]
        fixed_alpha = alpha_regularization_array[0]

        _sweep_gci_axis(
            pool, traj_proxy, potential, traj_dir / "N-init", fmt, "N_init",
            N_init_array, N_final_array, dns_array, fixed_ncp, fixed_alpha,
            atol, rtol, cosmo, dm, max_combos, work_items, compare_with, run_label=run_label,
        )
        _sweep_gci_axis(
            pool, traj_proxy, potential, traj_dir / "N-final", fmt, "N_final",
            N_final_array, N_init_array, dns_array, fixed_ncp, fixed_alpha,
            atol, rtol, cosmo, dm, max_combos, work_items, compare_with, run_label=run_label,
        )
        _sweep_gci_delta_Nstar(
            pool, traj_proxy, potential, traj_dir / "delta-Nstar", fmt, dns_array,
            N_init_array, N_final_array, fixed_ncp, fixed_alpha,
            atol, rtol, cosmo, dm, max_combos, work_items, compare_with, run_label=run_label,
        )

        _run_gci_stability_sweeps(
            pool, traj_proxy, potential, traj_dir, fmt, N_init_array, N_final_array, dns_array,
            n_collocation_points_array, alpha_regularization_array, atol, rtol, cosmo, dm,
            max_combos, run_label=run_label,
        )

        if args.no_store_values:
            print(
                "   >> --no-store-values active: skipping detailed instanton/spatial "
                "plots (dense per-sample values were not stored)."
            )
        else:
            _generate_gci_instanton_samples(
                pool, traj_proxy, potential, traj_dir / "instantons", fmt, gci_grid,
                max_instanton_samples, spatial_samples, atol, rtol, cosmo, dm,
                compare_with, args.movies, args.movie_format, args.time_resolved_derived,
                work_items, run_label=run_label,
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
        title="GENERATING GradientCoupledSolutions PLOTS",
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
        shards=args.shards,
        profile_agent=None,
        job_name="plot_GradientCoupledSolutions",
        prune_unvalidated=False,
        drop_actions=[],
        read_table_config=read_table_config,
        inventory_config=inventory_config,
    ) as pool:
        run_plots(pool, units, args)
