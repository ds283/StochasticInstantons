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
import argparse
from pathlib import Path

import numpy as np
import ray
import sqlalchemy as sqla
import seaborn as sns
from matplotlib import pyplot as plt
from scipy.integrate import solve_ivp

from Datastore.SQL.ShardedPool import ShardedPool
from Units import Planck_units
from config.sharding import (
    ShardKeyType,
    get_shard_key_store_id,
    replicated_tables,
    sharded_tables,
    read_table_config,
    inventory_config,
)

VERSION_LABEL = "2026.3.0"


def create_plot_parser():
    parser = argparse.ArgumentParser(
        description="Generate plots from validated StochasticInstanton database records"
    )
    parser.add_argument(
        "--database", type=str, required=False, default=None,
        help="Path to the primary SQLite database file",
    )
    parser.add_argument(
        "--output-dir", type=str, default="plots",
        help="Directory for output figures (default: 'plots/')",
    )
    parser.add_argument(
        "--format", type=str, default="pdf",
        choices=["pdf", "png", "svg"],
        help="Output figure format (default: pdf)",
    )
    parser.add_argument("--db-timeout", type=int, default=60)
    parser.add_argument("--ray-address", type=str, default="auto")
    parser.add_argument(
        "--show-all", action="store_true", default=False,
        help="Show all trajectories (default: first 5 only)",
    )
    return parser


def _read_shard_count(db_path, default=1):
    """Read the number of shards from the primary database, defaulting to 1."""
    p = Path(db_path)
    if not p.exists():
        return default
    try:
        engine = sqla.create_engine(f"sqlite:///{db_path}", future=True)
        meta = sqla.MetaData()
        meta.reflect(bind=engine)
        if "shards" not in meta.tables:
            engine.dispose()
            return default
        with engine.connect() as conn:
            count = conn.execute(
                sqla.select(sqla.func.count()).select_from(meta.tables["shards"])
            ).scalar()
        engine.dispose()
        return max(int(count), 1)
    except Exception:
        return default


def _read_from_shards_direct(primary_db_path, factory_class, table_name, **factory_kwargs):
    """
    Read all records of a sharded table by querying each shard database directly
    via SQLAlchemy.  This bypasses ShardedPool (which only supports read_table for
    replicated tables) by opening the SQLite shard files directly.
    """
    primary_engine = sqla.create_engine(f"sqlite:///{primary_db_path}", future=True)
    shard_paths = []

    try:
        primary_meta = sqla.MetaData()
        primary_meta.reflect(bind=primary_engine)
        if "shards" in primary_meta.tables:
            with primary_engine.connect() as conn:
                rows = conn.execute(
                    sqla.select(primary_meta.tables["shards"].c.filename)
                ).fetchall()
                shard_paths = [r.filename for r in rows]
    except Exception as exc:
        print(f"   Warning: could not read shard list from primary DB: {exc}")
    finally:
        primary_engine.dispose()

    factory = factory_class()
    all_records = []

    for shard_path in shard_paths:
        if not Path(shard_path).exists():
            print(f"   Warning: shard file not found: {shard_path}")
            continue
        shard_engine = sqla.create_engine(f"sqlite:///{shard_path}", future=True)
        try:
            shard_meta = sqla.MetaData()
            shard_meta.reflect(bind=shard_engine)
            tables_dict = dict(shard_meta.tables)
            if table_name not in tables_dict:
                continue
            tbl = tables_dict[table_name]
            with shard_engine.connect() as conn:
                records = factory.read_table(conn, tbl, tables_dict, **factory_kwargs)
            all_records.extend(records)
        except Exception as exc:
            print(f"   Warning: error reading {table_name} from {shard_path}: {exc}")
        finally:
            shard_engine.dispose()

    return all_records


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

    fname = output_dir / f"background_phi_{_safe_name(potential.name)}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
    print(f"   Saved: {fname.name}")


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

    fname = output_dir / f"background_epsilon_{_safe_name(potential.name)}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
    print(f"   Saved: {fname.name}")


def plot_instanton_fields(traj, fi, sri, delta_Nstar_val, potential, units, output_dir, fmt):
    """Figure 3: 2×2 grid of instanton field components vs N."""
    if fi is None and sri is None:
        print(f"   Warning: no instanton data for δN★={delta_Nstar_val:.3g} — skipping Figure 3")
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

    fig.suptitle(f"Instanton fields — {potential.name}, δN★={delta_Nstar_val:.3g}")
    fig.tight_layout()

    dns_str = f"{delta_Nstar_val:.3g}".replace(".", "p")
    fname = (
        output_dir
        / f"instanton_fields_{_safe_name(potential.name)}_dNstar{dns_str}.{fmt}"
    )
    fig.savefig(fname)
    plt.close(fig)
    print(f"   Saved: {fname.name}")


def plot_msr_action(trajectories, full_instantons, sr_instantons, potential, units, output_dir, fmt):
    """Figure 4: MSR action vs δN★, with one line per trajectory."""
    if not full_instantons and not sr_instantons:
        return

    # Build a map: trajectory_store_id → potential_name
    traj_map = {t.store_id: t for t in trajectories if t._potential is not None}

    # Group by trajectory_serial
    fi_by_traj = {}
    for fi in full_instantons:
        traj_id = getattr(fi, "_trajectory_serial", None)
        if traj_id is not None and fi._msr_action is not None:
            fi_by_traj.setdefault(traj_id, []).append(fi)

    sri_by_traj = {}
    for sri in sr_instantons:
        traj_id = getattr(sri, "_trajectory_serial", None)
        if traj_id is not None and sri._msr_action is not None:
            sri_by_traj.setdefault(traj_id, []).append(sri)

    all_traj_ids = sorted(set(list(fi_by_traj.keys()) + list(sri_by_traj.keys())))
    if not all_traj_ids:
        return

    palette = sns.color_palette("tab10", n_colors=max(len(all_traj_ids), 1))
    fig, ax = plt.subplots()

    for color, traj_id in zip(palette, all_traj_ids):
        traj = traj_map.get(traj_id)
        traj_label = traj._potential.name if traj is not None else f"traj#{traj_id}"

        fi_list = sorted(
            fi_by_traj.get(traj_id, []),
            key=lambda x: float(x._delta_Nstar) if x._delta_Nstar is not None else 0.0,
        )
        if fi_list:
            dns_vals = [float(fi._delta_Nstar) for fi in fi_list if fi._delta_Nstar is not None]
            actions = [fi._msr_action for fi in fi_list if fi._delta_Nstar is not None]
            ax.semilogy(dns_vals, actions, "o-", color=color, label=f"{traj_label} (full)")

        sri_list = sorted(
            sri_by_traj.get(traj_id, []),
            key=lambda x: float(x._delta_Nstar) if x._delta_Nstar is not None else 0.0,
        )
        if sri_list:
            dns_vals = [float(sri._delta_Nstar) for sri in sri_list if sri._delta_Nstar is not None]
            actions = [sri._msr_action for sri in sri_list if sri._delta_Nstar is not None]
            ax.semilogy(dns_vals, actions, "s--", color=color, label=f"{traj_label} (SR)")

    ax.set_xlabel(r"$\delta N_\star$")
    ax.set_ylabel(r"$S_{\rm MSR}$")
    ax.set_title(f"MSR action vs δN★ — {potential.name}")
    ax.legend(fontsize="small")
    fig.tight_layout()

    fname = output_dir / f"msr_action_{_safe_name(potential.name)}.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
    print(f"   Saved: {fname.name}")


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_plots(pool, units, args):
    from Datastore.SQL.ObjectFactories.FullInstanton import sqla_FullInstantonFactory
    from Datastore.SQL.ObjectFactories.SlowRollInstanton import sqla_SlowRollInstantonFactory

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    fmt = args.format

    print("\n>> Reading trajectories from database...")
    trajectories = ray.get(pool.read_table("InflatonTrajectory", units=units))
    print(f"   Found {len(trajectories)} validated trajectory record(s)")

    print(">> Reading full instantons from database...")
    full_instantons = _read_from_shards_direct(
        args.database, sqla_FullInstantonFactory, "FullInstanton"
    )
    print(f"   Found {len(full_instantons)} full instanton record(s)")

    print(">> Reading slow-roll instantons from database...")
    sr_instantons = _read_from_shards_direct(
        args.database, sqla_SlowRollInstantonFactory, "SlowRollInstanton"
    )
    print(f"   Found {len(sr_instantons)} slow-roll instanton record(s)")

    if len(trajectories) == 0:
        print("No validated trajectories found. Run main.py first.")
        return

    traj_list = trajectories if args.show_all else trajectories[:5]

    for traj in traj_list:
        potential = traj._potential
        if potential is None:
            print(f"   Warning: trajectory store_id={traj.store_id} has no potential — skipping")
            continue
        print(f"\n>> Plotting trajectory: {potential.name}")

        plot_background_trajectory(traj, potential, units, output_dir, fmt)
        plot_epsilon(traj, potential, units, output_dir, fmt)

        fi_for_traj = [
            fi for fi in full_instantons
            if getattr(fi, "_trajectory_serial", None) == traj.store_id
        ]
        sri_for_traj = [
            sri for sri in sr_instantons
            if getattr(sri, "_trajectory_serial", None) == traj.store_id
        ]

        dns_map = {}
        for fi in fi_for_traj:
            dns_serial = getattr(fi, "_delta_Nstar_serial", None)
            if dns_serial is not None:
                dns_map.setdefault(dns_serial, {})["full"] = fi
        for sri in sri_for_traj:
            dns_serial = getattr(sri, "_delta_Nstar_serial", None)
            if dns_serial is not None:
                dns_map.setdefault(dns_serial, {})["sr"] = sri

        for dns_serial, pair in sorted(dns_map.items()):
            fi = pair.get("full")
            sri = pair.get("sr")
            dns_obj = (fi._delta_Nstar if fi is not None else None) or (
                sri._delta_Nstar if sri is not None else None
            )
            if dns_obj is None:
                continue
            dns_val = float(dns_obj)
            plot_instanton_fields(traj, fi, sri, dns_val, potential, units, output_dir, fmt)

    if full_instantons or sr_instantons:
        rep_potential = next(
            (t._potential for t in trajectories if t._potential is not None), None
        )
        if rep_potential is not None:
            plot_msr_action(
                trajectories, full_instantons, sr_instantons,
                rep_potential, units, output_dir, fmt,
            )

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

    sns.set_theme(style="ticks", context="paper")

    shard_count = _read_shard_count(args.database)

    with ShardedPool(
        version_label=VERSION_LABEL,
        db_name=args.database,
        ShardKeyType=ShardKeyType,
        ShardKeyStoreIdGetter=get_shard_key_store_id,
        replicated_tables=replicated_tables,
        sharded_tables=sharded_tables,
        timeout=args.db_timeout,
        shards=shard_count,
        profile_agent=None,
        job_name="plot_InstantonSolutions",
        prune_unvalidated=False,
        drop_actions=[],
        read_table_config=read_table_config,
        inventory_config=inventory_config,
    ) as pool:
        run_plots(pool, units, args)
