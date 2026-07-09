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
from plotting.adapters.full import FullInstantonAdapter
from plotting.adapters.slow_roll import SlowRollInstantonAdapter
from plotting.annotations import (
    _add_cf_annotation,
    _cf_annotation_text,
    _extract_cf_annotation,
)
from plotting.dispatch import _dispatch_plot_work
from plotting.fetch import (
    _cf_key_payload,
    _cf_vectorized_fetch,
    _extract_cf_summary,
    _instanton_key_payload,
    _qualifying_action,
)
from plotting.figures.compaction import plot_zeta_and_compaction
from plotting.figures.doe import plot_doe_scalar_summary
from plotting.figures.noise import plot_noise_profile
from plotting.figures.sweeps import plot_compaction_summary, plot_msr_action_sweep
from plotting.figures.time_history import plot_instanton_fields
from plotting.provenance import VERSION_LABEL, _provenance_footer
from plotting.sampling import _evenly_sample, _safe_name, _safe_num
from RayTools.RayWorkPool import RayWorkPool
from Units import Planck_units

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


# ── Figure functions ──────────────────────────────────────────────────────────


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
    coords = {"N_init": N_init_val, "N_final": N_final_val, "delta_Nstar": dns_val}
    adapters = [
        FullInstantonAdapter(fi, coords=coords),
        SlowRollInstantonAdapter(sri, coords=coords),
    ]
    plot_instanton_fields(
        adapters,
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
    coords = {"N_init": N_init_val, "N_final": N_final_val, "delta_Nstar": dns_val}
    adapters = [
        FullInstantonAdapter(fi, coords=coords),
        SlowRollInstantonAdapter(sri, coords=coords),
    ]
    plot_noise_profile(
        adapters,
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
    fi,
    sri,
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
    coords = {"N_init": N_init_val, "N_final": N_final_val, "delta_Nstar": dns_val}
    adapters = [
        FullInstantonAdapter(fi, cf, coords=coords),
        SlowRollInstantonAdapter(sri, cf, coords=coords),
    ]
    plot_zeta_and_compaction(
        adapters,
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


# ── Sweep-direction data fetching ────────────────────────────────────────────


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
                        fi_ref,
                        sri_ref,
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
