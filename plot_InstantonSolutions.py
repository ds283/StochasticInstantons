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

import sys
import itertools
import math
from pathlib import Path

import numpy as np
import ray
import seaborn as sns
from matplotlib import pyplot as plt

from ComputeTargets import InflatonTrajectoryProxy
from InflationConcepts import MasslessDecoupledDiffusion
from Datastore.SQL.ShardedPool import ShardedPool
from RayTools.RayWorkPool import RayWorkPool
from Units import Planck_units
from config.argument_parser import create_argument_parser
from config.sharding import (
    ShardKeyType,
    get_shard_key_store_id,
    replicated_tables,
    sharded_tables,
    read_table_config,
    inventory_config,
)

VERSION_LABEL = "2026.3.0"

# Cap on the number of "other parameter" combinations shown per sweep
# directory, unless overridden via --max-combinations.
DEFAULT_MAX_COMBINATIONS = 10


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
        "--output-dir", type=str, default="plots",
        help="Directory for output figures (default: 'plots/')",
    )
    plot_grp.add_argument(
        "--format", type=str, default="pdf",
        choices=["pdf", "png", "svg"],
        help="Output figure format (default: pdf)",
    )
    plot_grp.add_argument(
        "--max-combinations", type=int, default=DEFAULT_MAX_COMBINATIONS,
        help="Maximum number of 'other parameter' combinations (and "
             "trajectories) to show per sweep directory, evenly sampled "
             f"across the grid (default: {DEFAULT_MAX_COMBINATIONS})",
    )
    return parser


# ── Grid + sampling helpers ────────────────────────────────────────────────────

def _build_grid(low, high, samples, values, label):
    if len(values) > 0:
        sample = sorted(values)
    else:
        sample = sorted(np.linspace(low, high, samples, endpoint=True).tolist())
    print(f"\n** Building {label} grid: {len(sample)} values "
          f"from {sample[0]:.4g} to {sample[-1]:.4g}")
    return sample


def _evenly_sample(seq, k):
    """Return up to k elements of seq, evenly spaced by index."""
    n = len(seq)
    if n <= k:
        return list(seq)
    idx = sorted(set(int(round(i)) for i in np.linspace(0, n - 1, k)))
    return [seq[i] for i in idx]


def _representative_points(seq):
    """Return up to 3 elements of seq (first, middle, last), de-duplicated."""
    n = len(seq)
    if n == 0:
        return []
    idx = sorted(set([0, n // 2, n - 1]))
    return [seq[i] for i in idx]


# ── Figure functions ──────────────────────────────────────────────────────────

def _safe_name(s):
    return s.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")


def plot_background_trajectory(traj, potential, units, output_dir, fmt):
    """Figure 1: φ(N) numerical vs slow-roll attractor."""
    if not traj._values:
        print(f"   Warning: trajectory {traj.store_id} has no values — skipping Figure 1")
        return

    Mp = units.PlanckMass
    N_vals = [v.N.N for v in traj._values]
    phi_vals = [v.phi / Mp for v in traj._values]

    fig, ax = plt.subplots()
    ax.plot(N_vals, phi_vals, label="Numerical")

    # Slow-roll attractor: dφ/dN = -V′(φ) / (3 H²_SR),  H²_SR = V(φ)/3Mp²
    try:
        from scipy.integrate import solve_ivp

        phi0_sr = traj._values[0].phi

        def sr_rhs(N, y):
            phi = y[0]
            Hsq = potential.H_sq(phi, 0.0)
            return [-potential.dV_dphi(phi) / (3.0 * Hsq)]

        N_span = (N_vals[0], N_vals[-1])
        N_eval = np.linspace(N_vals[0], N_vals[-1], max(len(N_vals), 300))
        sr_sol = solve_ivp(sr_rhs, N_span, [phi0_sr], method="RK45", t_eval=N_eval)
        if sr_sol.success:
            ax.plot(sr_sol.t, sr_sol.y[0] / Mp, "--", label="Slow-roll attractor")
    except Exception as exc:
        print(f"   Warning: slow-roll attractor integration failed: {exc}")

    ax.set_xlabel("N (e-folds)")
    ax.set_ylabel(r"$\varphi\,/\,M_{\rm P}$")
    ax.set_title(f"Background trajectory — {potential.name}")
    ax.legend()
    fig.tight_layout()

    fname = output_dir / f"background_phi.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
    print(f"   Saved: {fname}")


def plot_epsilon(traj, potential, units, output_dir, fmt):
    """Figure 2: slow-roll parameter ε(N)."""
    if not traj._values:
        print(f"   Warning: trajectory {traj.store_id} has no values — skipping Figure 2")
        return

    N_vals = [v.N.N for v in traj._values]
    try:
        eps_vals = [potential.epsilon(v.phi, v.pi) for v in traj._values]
    except Exception as exc:
        print(f"   Warning: epsilon computation failed: {exc}")
        return

    fig, ax = plt.subplots()
    ax.plot(N_vals, eps_vals)
    ax.axhline(y=1.0, color="gray", linestyle="--", label="End of inflation")
    ax.set_xlabel("N (e-folds)")
    ax.set_ylabel(r"$\epsilon$")
    ax.set_title(fr"Slow-roll parameter $\epsilon$ — {potential.name}")
    ax.legend()
    fig.tight_layout()

    fname = output_dir / f"background_epsilon.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
    print(f"   Saved: {fname}")


def plot_instanton_fields(fi, sri, N_init_val, N_final_val, dns_val, potential, units, output_dir, fmt):
    """Figure 3: 2×2 grid of instanton field components vs N, at one
    (N_init, N_final, delta_Nstar) point."""
    if fi is None and sri is None:
        print(f"   Warning: no instanton data for Ninit={N_init_val:.3g}, "
              f"Nfinal={N_final_val:.3g}, δN★={dns_val:.3g} — skipping Figure 3")
        return

    Mp = units.PlanckMass
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    ax_phi, ax_pi, ax_P1, ax_P2 = (
        axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]
    )

    # Top-left: φ₁ (full instanton) and φ (slow-roll instanton)
    if fi is not None and fi._values:
        N_fi = [v.N.N for v in fi._values]
        ax_phi.plot(N_fi, [v.phi1 / Mp for v in fi._values], label=r"$\varphi_1$ (full)")
        # φ_init and φ_final horizontal lines
        phi_init = fi._values[0].phi1
        phi_final = fi._values[-1].phi1
        ax_phi.axhline(phi_init / Mp, color="gray", linestyle=":", linewidth=0.8, label=r"$\varphi_{\rm init}$")
        ax_phi.axhline(phi_final / Mp, color="gray", linestyle="-.", linewidth=0.8, label=r"$\varphi_{\rm final}$")

    if sri is not None and sri._values:
        N_sri = [v.N.N for v in sri._values]
        ax_phi.plot(N_sri, [v.phi / Mp for v in sri._values], "--", label=r"$\varphi$ (SR)")

    ax_phi.set_xlabel("N (e-folds)")
    ax_phi.set_ylabel(r"$\varphi\,/\,M_{\rm P}$")
    ax_phi.set_title("Field trajectory")
    ax_phi.legend(fontsize="small")

    # Top-right: φ₂ (full instanton) + slow-roll π from trajectory
    if fi is not None and fi._values:
        N_fi = [v.N.N for v in fi._values]
        ax_pi.plot(N_fi, [v.phi2 / Mp for v in fi._values], label=r"$\varphi_2$ (full)")

        # Overlay slow-roll π = -V′/(3H²_SR) computed from φ₁
        try:
            pi_sr = [
                -potential.dV_dphi(v.phi1) / (3.0 * potential.H_sq(v.phi1, 0.0))
                for v in fi._values
            ]
            ax_pi.plot(N_fi, [p / Mp for p in pi_sr], "--", label=r"$\pi_{\rm SR}(\varphi_1)$")
        except Exception:
            pass

    ax_pi.set_xlabel("N (e-folds)")
    ax_pi.set_ylabel(r"field velocity / $M_{\rm P}$")
    ax_pi.set_title("Field velocity")
    ax_pi.legend(fontsize="small")

    # Bottom-left: P₁
    if fi is not None and fi._values:
        N_fi = [v.N.N for v in fi._values]
        ax_P1.plot(N_fi, [v.P1 for v in fi._values], label=r"$P_1$ (full)")

    if sri is not None and sri._values:
        N_sri = [v.N.N for v in sri._values]
        ax_P1.plot(N_sri, [v.P1 for v in sri._values], "--", label=r"$P_1$ (SR)")

    ax_P1.set_xlabel("N (e-folds)")
    ax_P1.set_ylabel(r"$P_1$")
    ax_P1.set_title("Response field $P_1$")
    ax_P1.legend(fontsize="small")

    # Bottom-right: P₂ (full instanton only)
    if fi is not None and fi._values:
        N_fi = [v.N.N for v in fi._values]
        ax_P2.plot(N_fi, [v.P2 for v in fi._values], label=r"$P_2$ (full)")

    ax_P2.set_xlabel("N (e-folds)")
    ax_P2.set_ylabel(r"$P_2$")
    ax_P2.set_title("Response field $P_2$")
    ax_P2.legend(fontsize="small")

    fig.suptitle(
        f"Instanton fields — {potential.name}, "
        rf"Ninit={N_init_val:.3g}, Nfinal={N_final_val:.3g}, $\delta N_\star$={dns_val:.3g}"
    )
    fig.tight_layout()

    fname = (
        output_dir
        / f"instanton_fields_Ninit={_safe_num(N_init_val)}_Nfinal={_safe_num(N_final_val)}"
          f"_dNstar={_safe_num(dns_val)}.{fmt}"
    )
    fig.savefig(fname)
    plt.close(fig)
    print(f"   Saved: {fname}")


def plot_msr_action_sweep(x_label, fi_points, sri_points, fixed_desc, potential_name,
                           output_dir, fmt, swept_name):
    """One trajectory's MSR action vs the swept dimension, at one fixed
    combination of the other two dimensions (described by fixed_desc).
    fi_points/sri_points: lists of (swept_value, msr_action) tuples."""
    fi_points = [(x, a) for x, a in fi_points if a is not None]
    sri_points = [(x, a) for x, a in sri_points if a is not None]
    if not fi_points and not sri_points:
        return

    fig, ax = plt.subplots()
    if fi_points:
        fi_sorted = sorted(fi_points)
        xs, ys = zip(*fi_sorted)
        ax.semilogy(xs, ys, "o-", label="Full MSR")
    if sri_points:
        sri_sorted = sorted(sri_points)
        xs, ys = zip(*sri_sorted)
        ax.semilogy(xs, ys, "s--", label="Slow-roll")

    ax.set_xlabel(x_label)
    ax.set_ylabel(r"$S_{\rm MSR}$")
    ax.set_title(f"MSR action vs {x_label} — {potential_name} ({fixed_desc})")
    ax.legend(fontsize="small")
    fig.tight_layout()

    swept_file = {"N_init": "Ninit", "N_final": "Nfinal", "delta_Nstar": "dNstar"}[swept_name]
    fname = output_dir / f"msr_action_vs_{swept_file}__{fixed_desc}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
    print(f"   Saved: {fname}")


def _safe_num(v: float) -> str:
    return f"{v:.4g}".replace(".", "p").replace("-", "m")


# ── Ray remote plot dispatch ────────────────────────────────────────────────

@ray.remote
def _plot_trajectory_item(traj, potential, output_dir_str, fmt):
    """Runs inside a Ray worker: background trajectory + epsilon plots."""
    sns.set_theme(style="ticks", context="paper")
    output_dir = Path(output_dir_str)
    units = Planck_units()
    plot_background_trajectory(traj, potential, units, output_dir, fmt)
    plot_epsilon(traj, potential, units, output_dir, fmt)


@ray.remote
def _plot_fields_item(fi, sri, N_init_val, N_final_val, dns_val, potential, output_dir_str, fmt):
    """Runs inside a Ray worker: one field-trajectory comparison plot."""
    sns.set_theme(style="ticks", context="paper")
    output_dir = Path(output_dir_str)
    units = Planck_units()
    plot_instanton_fields(fi, sri, N_init_val, N_final_val, dns_val, potential, units, output_dir, fmt)


@ray.remote
def _plot_msr_sweep_item(x_label, fi_points, sri_points, fixed_desc, potential_name,
                          output_dir_str, fmt, swept_name):
    """Runs inside a Ray worker: one MSR-action-vs-swept-parameter plot."""
    sns.set_theme(style="ticks", context="paper")
    output_dir = Path(output_dir_str)
    plot_msr_action_sweep(x_label, fi_points, sri_points, fixed_desc, potential_name,
                          output_dir, fmt, swept_name)


def _dispatch_plot_work(item):
    """task_builder for RayWorkPool: item is a (remote_fn, args) pair already
    fully prepared by the data-fetch stage; just submit it."""
    remote_fn, args = item
    return remote_fn.remote(*args)


# ── Sweep-direction data fetching ────────────────────────────────────────────

def _instanton_key_payload(traj_proxy, N_init, N_final, dns, atol, rtol):
    return dict(
        trajectory=traj_proxy,
        N_init=N_init,
        N_final=N_final,
        delta_Nstar=dns,
        atol=atol,
        rtol=rtol,
        tags=[],
    )


def _qualifying_action(obj):
    """Extract msr_action from a (possibly _do_not_populate=True) query
    result, or None if the object doesn't exist / has no action recorded."""
    if obj is None or not obj.available:
        return None
    return obj.msr_action


def _sweep_Ninit_or_Nfinal(pool, traj_proxy, potential, out_dir, fmt,
                            swept_name, swept_array, fixed_other_array, dns_array,
                            atol, rtol, max_combos, work_items):
    """swept_name in {"N_init", "N_final"}. delta_Nstar is one of the two
    fixed 'other' dimensions here, so every point on one curve already
    shares one shard — one object_get_vectorized() call per curve."""
    out_dir.mkdir(parents=True, exist_ok=True)
    combos = list(itertools.product(fixed_other_array, dns_array))
    selected = _evenly_sample(combos, max_combos)

    for other_val, dns_val in selected:
        if swept_name == "N_init":
            payload_data = [
                {**_instanton_key_payload(traj_proxy, v, other_val, dns_val, atol, rtol),
                 "_do_not_populate": True}
                for v in swept_array
            ]
        else:
            payload_data = [
                {**_instanton_key_payload(traj_proxy, other_val, v, dns_val, atol, rtol),
                 "_do_not_populate": True}
                for v in swept_array
            ]

        fi_list, sri_list = ray.get([
            pool.object_get_vectorized("FullInstanton", dns_val, payload_data=payload_data),
            pool.object_get_vectorized("SlowRollInstanton", dns_val, payload_data=payload_data),
        ])

        swept_vals = [float(v) for v in swept_array]
        fi_points = list(zip(swept_vals, (_qualifying_action(o) for o in fi_list)))
        sri_points = list(zip(swept_vals, (_qualifying_action(o) for o in sri_list)))

        if swept_name == "N_init":
            fixed_desc = f"Nfinal={float(other_val):.3g}_dNstar={float(dns_val):.3g}"
            x_label = r"$N_{\rm init}$"
        else:
            fixed_desc = f"Ninit={float(other_val):.3g}_dNstar={float(dns_val):.3g}"
            x_label = r"$N_{\rm final}$"

        if any(a is not None for _, a in fi_points) or any(a is not None for _, a in sri_points):
            work_items.append((_plot_msr_sweep_item, (
                x_label, fi_points, sri_points, fixed_desc,
                potential.name, str(out_dir), fmt, swept_name,
            )))

        for rep_v in _representative_points(swept_array):
            if swept_name == "N_init":
                N_init_v, N_final_v = rep_v, other_val
            else:
                N_init_v, N_final_v = other_val, rep_v
            payload = _instanton_key_payload(traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol)
            fi_full, sri_full = ray.get([
                pool.object_get("FullInstanton", **payload),
                pool.object_get("SlowRollInstanton", **payload),
            ])
            fi_full = fi_full if (fi_full is not None and fi_full.available) else None
            sri_full = sri_full if (sri_full is not None and sri_full.available) else None
            if fi_full is None and sri_full is None:
                continue
            work_items.append((_plot_fields_item, (
                fi_full, sri_full, float(N_init_v), float(N_final_v), float(dns_val),
                potential, str(out_dir), fmt,
            )))


def _sweep_delta_Nstar(pool, traj_proxy, potential, out_dir, fmt,
                        dns_array, N_init_array, N_final_array,
                        atol, rtol, max_combos, work_items):
    """Each curve point has a different delta_Nstar (a different shard), but
    across the selected (N_init, N_final) combos, points sharing one
    delta_Nstar value do share a shard — bin across combos by delta_Nstar
    and issue one object_get_vectorized() call per distinct value."""
    out_dir.mkdir(parents=True, exist_ok=True)
    combos = list(itertools.product(N_init_array, N_final_array))
    selected = _evenly_sample(combos, max_combos)

    fi_refs = {}
    sri_refs = {}
    for dns_val in dns_array:
        payload_data = [
            {**_instanton_key_payload(traj_proxy, N_init_v, N_final_v, dns_val, atol, rtol),
             "_do_not_populate": True}
            for (N_init_v, N_final_v) in selected
        ]
        fi_refs[dns_val] = pool.object_get_vectorized("FullInstanton", dns_val, payload_data=payload_data)
        sri_refs[dns_val] = pool.object_get_vectorized("SlowRollInstanton", dns_val, payload_data=payload_data)

    fi_by_dns = dict(zip(fi_refs.keys(), ray.get(list(fi_refs.values()))))
    sri_by_dns = dict(zip(sri_refs.keys(), ray.get(list(sri_refs.values()))))

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
        if any(a is not None for _, a in fi_points) or any(a is not None for _, a in sri_points):
            work_items.append((_plot_msr_sweep_item, (
                r"$\delta N_\star$", fi_points, sri_points, fixed_desc,
                potential.name, str(out_dir), fmt, "delta_Nstar",
            )))

        for rep_dns in _representative_points(dns_array):
            payload = _instanton_key_payload(traj_proxy, N_init_v, N_final_v, rep_dns, atol, rtol)
            fi_full, sri_full = ray.get([
                pool.object_get("FullInstanton", **payload),
                pool.object_get("SlowRollInstanton", **payload),
            ])
            fi_full = fi_full if (fi_full is not None and fi_full.available) else None
            sri_full = sri_full if (sri_full is not None and sri_full.available) else None
            if fi_full is None and sri_full is None:
                continue
            work_items.append((_plot_fields_item, (
                fi_full, sri_full, float(N_init_v), float(N_final_v), float(rep_dns),
                potential, str(out_dir), fmt,
            )))


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_plots(pool, units, args):
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = args.format

    print("\n>> Reading trajectories...")
    trajectories = ray.get(pool.read_table("InflatonTrajectory", units=units))
    print(f"   Found {len(trajectories)} trajectory record(s)")

    if not trajectories:
        print("No trajectories found. Run main.py first.")
        return

    traj_list = [t for t in trajectories if t._potential is not None]
    traj_list = _evenly_sample(traj_list, args.max_combinations)

    print(">> Reading delta_Nstar values...")
    dns_array = sorted(ray.get(pool.read_table("delta_Nstar")), key=lambda d: float(d))
    print(f"   Found {len(dns_array)} delta_Nstar value(s)")

    if not dns_array:
        print("No delta_Nstar values found. Run main.py first.")
        return

    atol, rtol = ray.get([
        pool.object_get("tolerance", log10_tol=int(round(math.log10(args.abs_tol)))),
        pool.object_get("tolerance", log10_tol=int(round(math.log10(args.rel_tol)))),
    ])

    N_init_sample = _build_grid(
        args.N_init_low, args.N_init_high, args.N_init_samples, args.N_init_values, "N_init"
    )
    N_init_array = ray.get(
        pool.object_get("N_init", payload_data=[{"value": v} for v in N_init_sample])
    )

    N_final_sample = _build_grid(
        args.N_final_low, args.N_final_high, args.N_final_samples, args.N_final_values, "N_final"
    )
    N_final_array = ray.get(
        pool.object_get("N_final", payload_data=[{"value": v} for v in N_final_sample])
    )

    max_combos = args.max_combinations

    work_items = []
    for traj in traj_list:
        potential = traj._potential
        traj_proxy = InflatonTrajectoryProxy(traj)
        traj_dir = output_dir / f"{_safe_name(potential.name)}_traj{traj.store_id}"
        traj_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n>> Trajectory {traj.store_id} ({potential.name}) -> {traj_dir}/")

        work_items.append((_plot_trajectory_item, (traj, potential, str(traj_dir), fmt)))

        _sweep_Ninit_or_Nfinal(
            pool, traj_proxy, potential, traj_dir / "N-init", fmt,
            swept_name="N_init", swept_array=N_init_array,
            fixed_other_array=N_final_array, dns_array=dns_array,
            atol=atol, rtol=rtol, max_combos=max_combos, work_items=work_items,
        )
        _sweep_Ninit_or_Nfinal(
            pool, traj_proxy, potential, traj_dir / "N-final", fmt,
            swept_name="N_final", swept_array=N_final_array,
            fixed_other_array=N_init_array, dns_array=dns_array,
            atol=atol, rtol=rtol, max_combos=max_combos, work_items=work_items,
        )
        _sweep_delta_Nstar(
            pool, traj_proxy, potential, traj_dir / "delta-Nstar", fmt,
            dns_array=dns_array, N_init_array=N_init_array, N_final_array=N_final_array,
            atol=atol, rtol=rtol, max_combos=max_combos, work_items=work_items,
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
        shards=1,
        profile_agent=None,
        job_name="plot_InstantonSolutions",
        prune_unvalidated=False,
        drop_actions=[],
        read_table_config=read_table_config,
        inventory_config=inventory_config,
    ) as pool:
        run_plots(pool, units, args)
