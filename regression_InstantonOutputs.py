#!/usr/bin/env python3
"""
regression_InstantonOutputs.py

Standalone GP regression script for StochasticInstanton scalar outputs.
Reads scalar_data.csv produced by plot_InstantonSolutions.py --no-store-values,
fits 5 independent single-output GPs, and writes diagnostic plots plus
serialised model bundles.

Usage:
    python3 regression_InstantonOutputs.py \
        --scalar-data scalar_data-asteroid.csv \
        --output-dir  regression_output/ \
        --format      pdf \
        --seed        42
"""

import argparse
import sys
from datetime import datetime
from math import sqrt
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

VERSION_LABEL = "2026.3.0"

FEATURE_COLS = ["delta_Nstar", "delta_N", "N_final"]
THRESHOLD = 0.4

_EXPECTED_COLUMNS = {
    "N_init", "N_final", "delta_Nstar", "delta_N",
    "msr_action_full", "msr_action_sr",
    "C_peak_full", "C_bar_peak_full",
    "M_C_full_solar", "M_C_bar_full_solar", "r_max_C_full_Mpc", "r_max_C_bar_full_Mpc",
    "C_peak_sr", "C_bar_peak_sr",
    "M_C_sr_solar", "M_C_bar_sr_solar", "r_max_C_sr_Mpc", "r_max_C_bar_sr_Mpc",
}


def _make_kernel():
    return (
        ConstantKernel(1.0)
        * Matern(length_scale=[1.0, 1.0, 1.0], nu=2.5, length_scale_bounds=(1e-2, 1e2))
        + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-10, 1e0))
    )


def _extract_ard_length_scales(gp: GaussianProcessRegressor) -> np.ndarray:
    """Extract the ARD length-scales from the fitted kernel."""
    k = gp.kernel_
    # Kernel structure: (ConstantKernel * Matern) + WhiteKernel
    # k.k1 = ConstantKernel * Matern; k.k1.k2 = Matern
    try:
        return np.atleast_1d(k.k1.k2.length_scale)
    except AttributeError:
        return np.ones(len(FEATURE_COLS))


# ── Core GP routines ──────────────────────────────────────────────────────────


def load_scalar_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f"Error: input file '{path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(path, comment="#", na_values=["", " "])

    missing = _EXPECTED_COLUMNS - set(df.columns)
    if missing:
        print(
            f"Error: '{path}' is missing columns: {sorted(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    return df


def fit_gp(name: str, X_train, y_train, kernel, seed: int) -> GaussianProcessRegressor:
    gp = GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=5,
        normalize_y=True,
        random_state=seed,
    )
    print(f"  Fitting {name} on {len(y_train)} training rows …", flush=True)
    gp.fit(X_train, y_train)
    return gp


def evaluate_gp(gp: GaussianProcessRegressor, X_test_scaled, y_test) -> dict:
    y_pred, y_std = gp.predict(X_test_scaled, return_std=True)
    r2 = r2_score(y_test, y_pred)
    rmse = sqrt(mean_squared_error(y_test, y_pred))
    return {
        "y_pred": y_pred,
        "y_std": y_std,
        "r2": r2,
        "rmse": rmse,
        "lml": gp.log_marginal_likelihood_value_,
    }


def _print_bundle_diagnostics(bundle: dict):
    gp = bundle["gp"]
    m = bundle["metrics"]
    ls = _extract_ard_length_scales(gp)
    ls_str = "  ".join(f"{col}={v:.4g}" for col, v in zip(FEATURE_COLS, ls))
    n_train = bundle["n_train"]
    n_total = bundle["n_total"]

    print(f"\nGP {bundle['gp_index']} — {bundle['name']}")
    print(f"  kernel (optimised): {gp.kernel_}")
    print(f"  ARD length-scales:  {ls_str}")
    print(f"  test R2:            {m['r2']:.4f}")
    print(f"  test RMSE:          {m['rmse']:.4g}")
    print(f"  log marginal lik:   {m['lml']:.1f}")
    print(f"  training rows:      {n_train} / {n_total} ({100*n_train/n_total:.1f}% of total)")


# ── Footer ───────────────────────────────────────────────────────────────────


def _provenance_footer(fig, scalar_data_path: Path = None, render_time=None):
    """Add a small provenance line at the very bottom of fig."""
    if render_time is None:
        render_time = datetime.now()

    parts = [
        f"StochasticInstanton regression v{VERSION_LABEL}",
        render_time.strftime("%Y-%m-%d %H:%M:%S"),
    ]
    if scalar_data_path is not None:
        parts.append(f"data: {scalar_data_path.name}")

    footer_text = "  |  ".join(parts)
    try:
        fig.text(
            0.5,
            0.003,
            footer_text,
            ha="center",
            va="bottom",
            fontsize=7,
            color="#888888",
            transform=fig.transFigure,
        )
    except Exception:
        pass


# ── Plots ─────────────────────────────────────────────────────────────────────


def plot_predicted_vs_actual(all_bundles: list, output_dir: Path, fmt: str,
                             scalar_data_path: Path = None, render_time=None):
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))
    axes = axes.flatten()

    for i, bundle in enumerate(all_bundles):
        ax = axes[i]
        y_test = bundle["y_test"]
        y_pred = bundle["metrics"]["y_pred"]
        y_std = bundle["metrics"]["y_std"]
        r2 = bundle["metrics"]["r2"]

        lo = min(float(y_test.min()), float(y_pred.min()))
        hi = max(float(y_test.max()), float(y_pred.max()))
        margin = 0.05 * (hi - lo)

        ax.errorbar(
            y_test, y_pred,
            yerr=y_std,
            fmt="o", markersize=4, alpha=0.7, linewidth=0.5,
        )
        ax.plot([lo - margin, hi + margin], [lo - margin, hi + margin],
                "k--", linewidth=1, label="y = x")
        ax.set_xlim(lo - margin, hi + margin)
        ax.set_ylim(lo - margin, hi + margin)
        ax.set_xlabel("Actual (transformed)")
        ax.set_ylabel("Predicted (transformed)")
        ax.set_title(f"{bundle['name']}\n$R^2 = {r2:.4f}$", fontsize=9)
        ax.set_aspect("equal", adjustable="box")

    axes[-1].set_visible(False)
    fig.suptitle("GP regression: predicted vs actual (test set)", fontsize=13)
    fig.tight_layout()
    _provenance_footer(fig, scalar_data_path, render_time)

    out_path = output_dir / f"predicted_vs_actual.{fmt}"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"   >> {out_path}")


def plot_threshold_boundary(gp1_bundle: dict, df_train: pd.DataFrame, output_dir: Path, fmt: str,
                            scalar_data_path: Path = None, render_time=None):
    gp = gp1_bundle["gp"]
    scaler = gp1_bundle["scaler"]

    N_final_vals = df_train["N_final"].values
    N_final_slices = [N_final_vals.min(), np.median(N_final_vals), N_final_vals.max()]

    dns_grid = np.linspace(0.0, 3.0, 100)
    dN_grid = np.linspace(0.5, 6.0, 100)
    DNS, DN = np.meshgrid(dns_grid, dN_grid)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)

    for ax, N_final_val in zip(axes, N_final_slices):
        X_grid = np.column_stack([
            DNS.ravel(),
            DN.ravel(),
            np.full(DNS.size, N_final_val),
        ])
        X_grid_scaled = scaler.transform(X_grid)
        mean_flat, std_flat = gp.predict(X_grid_scaled, return_std=True)
        mean_2d = mean_flat.reshape(DNS.shape)
        std_2d = std_flat.reshape(DNS.shape)

        above_confident = (mean_2d - std_2d) > THRESHOLD
        below_confident = (mean_2d + std_2d) < THRESHOLD

        ax.contourf(
            DNS, DN, above_confident.astype(float),
            levels=[0.5, 1.5], colors=["steelblue"], alpha=0.35,
        )
        ax.contourf(
            DNS, DN, below_confident.astype(float),
            levels=[0.5, 1.5], colors=["firebrick"], alpha=0.35,
        )

        try:
            cs = ax.contour(
                DNS, DN, mean_2d,
                levels=[THRESHOLD], colors=["black"], linewidths=[1.5],
            )
            ax.clabel(cs, fmt=r"$\bar{C}_{\rm max}=0.4$", fontsize=8)
        except Exception:
            pass

        mask = ~df_train["C_bar_peak_full"].isna()
        sc = ax.scatter(
            df_train.loc[mask, "delta_Nstar"],
            df_train.loc[mask, "delta_N"],
            c=df_train.loc[mask, "C_bar_peak_full"],
            s=15, alpha=0.85, vmin=0.0, vmax=1.6,
            cmap="viridis", zorder=3,
        )

        ax.set_xlabel(r"$\delta N_\star$")
        ax.set_xlim(0.0, 3.0)
        ax.set_ylim(0.5, 6.0)
        ax.set_title(f"$N_{{\\rm final}} = {N_final_val:.2f}$")

    axes[0].set_ylabel(r"$\Delta N$")
    fig.colorbar(sc, ax=axes[-1], label=r"$\bar{C}_{\rm max}$ (training points)")

    legend_elements = [
        Patch(facecolor="steelblue", alpha=0.55, label=r"$\bar{C}_{\rm max} - \sigma > 0.4$ (above)"),
        Patch(facecolor="firebrick", alpha=0.55, label=r"$\bar{C}_{\rm max} + \sigma < 0.4$ (below)"),
    ]
    axes[0].legend(handles=legend_elements, fontsize=8, loc="upper left")

    fig.suptitle(r"GP-estimated $\bar{C}_{\rm max} = 0.4$ threshold boundary", fontsize=13)
    fig.tight_layout()
    _provenance_footer(fig, scalar_data_path, render_time)

    out_path = output_dir / f"threshold_boundary.{fmt}"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"   >> {out_path}")


def plot_ard_length_scales(all_bundles: list, output_dir: Path, fmt: str,
                           scalar_data_path: Path = None, render_time=None):
    n_gps = len(all_bundles)
    n_features = len(FEATURE_COLS)
    bar_h = 0.22
    group_gap = 0.15
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    fig, ax = plt.subplots(figsize=(10, 1.2 * n_gps * n_features))

    ytick_pos = []
    ytick_labels = []
    y = 0.0

    for bundle in all_bundles:
        ls = _extract_ard_length_scales(bundle["gp"])
        group_center = y + (n_features - 1) * bar_h / 2
        ytick_pos.append(group_center)
        ytick_labels.append(bundle["name"])

        for feat_idx, (feat, val) in enumerate(zip(FEATURE_COLS, ls)):
            ax.barh(
                y + feat_idx * bar_h, val,
                height=bar_h * 0.8,
                color=colors[feat_idx], alpha=0.85,
            )

        y += n_features * bar_h + group_gap

    ax.set_yticks(ytick_pos)
    ax.set_yticklabels(ytick_labels, fontsize=9)
    ax.set_xlabel("ARD length-scale (standardised feature units)")
    ax.set_title("GP ARD length-scales by input dimension")
    ax.axvline(1.0, color="grey", linestyle="--", linewidth=0.8, alpha=0.6)

    legend_elements = [
        Patch(facecolor=colors[i], alpha=0.85, label=FEATURE_COLS[i])
        for i in range(n_features)
    ]
    ax.legend(handles=legend_elements, fontsize=9, loc="lower right")

    fig.tight_layout()
    _provenance_footer(fig, scalar_data_path, render_time)
    out_path = output_dir / f"ard_length_scales.{fmt}"
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"   >> {out_path}")


# ── Model serialisation ───────────────────────────────────────────────────────


def save_models(all_bundles: list, output_dir: Path):
    models_dir = output_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    filenames = {
        "C_bar_peak_full":         "gp_C_bar_peak_full.joblib",
        "C_peak_full":             "gp_C_peak_full.joblib",
        "log(msr_action_full)":   "gp_log_msr_action_full.joblib",
        "log(M_C_bar_full_solar)":"gp_log_M_C_bar_full_solar.joblib",
        "log(r_max_C_bar_full_Mpc)":"gp_log_r_max_C_bar_full_Mpc.joblib",
    }

    for bundle in all_bundles:
        fname = filenames.get(bundle["name"])
        if fname is None:
            continue
        payload = {
            "gp":               bundle["gp"],
            "scaler":           bundle["scaler"],
            "feature_cols":     FEATURE_COLS,
            "target_col":       bundle["target_col"],
            "target_transform": bundle["target_transform"],
            "n_train":          bundle["n_train"],
            "n_test":           bundle["n_test"],
            "test_r2":          bundle["metrics"]["r2"],
            "test_rmse":        bundle["metrics"]["rmse"],
        }
        out_path = models_dir / fname
        joblib.dump(payload, out_path)
        print(f"   >> {out_path}")


# ── Orchestration ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="GP regression on StochasticInstanton DOE scalar outputs"
    )
    parser.add_argument(
        "--scalar-data", type=Path, required=True,
        help="Path to scalar_data.csv produced by plot_InstantonSolutions.py",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("regression_output"),
        help="Directory for plots and serialised models (default: regression_output/)",
    )
    parser.add_argument(
        "--format", default="pdf", choices=["pdf", "png", "svg"],
        help="Plot file format (default: pdf)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for train/test split (default: 42)",
    )
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    sns.set_theme()
    render_time = datetime.now()

    # ── Load ──────────────────────────────────────────────────────────────────
    df = load_scalar_data(args.scalar_data)
    print(f"Loaded {len(df)} rows from '{args.scalar_data}'")

    n_total = len(df)

    # ── Stratified 80/20 split on full dataset (for GPs 1–3) ─────────────────
    strat = (df["C_bar_peak_full"] > THRESHOLD).astype(int)
    idx_train, idx_test = train_test_split(
        np.arange(n_total),
        test_size=0.2,
        random_state=args.seed,
        stratify=strat,
    )
    df_train = df.iloc[idx_train]
    df_test = df.iloc[idx_test]

    scaler = StandardScaler()
    X_train_all = scaler.fit_transform(df_train[FEATURE_COLS].values)
    X_test_all = scaler.transform(df_test[FEATURE_COLS].values)

    all_bundles = []

    # ── GP 1: C_bar_peak_full ────────────────────────────────────────────────
    mask_tr1 = ~df_train["C_bar_peak_full"].isna()
    mask_te1 = ~df_test["C_bar_peak_full"].isna()
    X_tr1 = X_train_all[mask_tr1.values]
    y_tr1 = df_train.loc[mask_tr1, "C_bar_peak_full"].values
    X_te1 = X_test_all[mask_te1.values]
    y_te1 = df_test.loc[mask_te1, "C_bar_peak_full"].values

    gp1 = fit_gp("C_bar_peak_full", X_tr1, y_tr1, _make_kernel(), args.seed)
    metrics1 = evaluate_gp(gp1, X_te1, y_te1)
    bundle1 = dict(
        name="C_bar_peak_full", gp_index=1,
        gp=gp1, scaler=scaler,
        X_test=X_te1, y_test=y_te1, metrics=metrics1,
        target_col="C_bar_peak_full", target_transform="identity",
        n_train=len(y_tr1), n_test=len(y_te1), n_total=n_total,
    )
    all_bundles.append(bundle1)
    _print_bundle_diagnostics(bundle1)

    # ── GP 2: C_peak_full ────────────────────────────────────────────────────
    mask_tr2 = ~df_train["C_peak_full"].isna()
    mask_te2 = ~df_test["C_peak_full"].isna()
    X_tr2 = X_train_all[mask_tr2.values]
    y_tr2 = df_train.loc[mask_tr2, "C_peak_full"].values
    X_te2 = X_test_all[mask_te2.values]
    y_te2 = df_test.loc[mask_te2, "C_peak_full"].values

    gp2 = fit_gp("C_peak_full", X_tr2, y_tr2, _make_kernel(), args.seed)
    metrics2 = evaluate_gp(gp2, X_te2, y_te2)
    bundle2 = dict(
        name="C_peak_full", gp_index=2,
        gp=gp2, scaler=scaler,
        X_test=X_te2, y_test=y_te2, metrics=metrics2,
        target_col="C_peak_full", target_transform="identity",
        n_train=len(y_tr2), n_test=len(y_te2), n_total=n_total,
    )
    all_bundles.append(bundle2)
    _print_bundle_diagnostics(bundle2)

    # ── GP 3: log(msr_action_full) ────────────────────────────────────────────
    mask_tr3 = ~df_train["msr_action_full"].isna()
    mask_te3 = ~df_test["msr_action_full"].isna()
    X_tr3 = X_train_all[mask_tr3.values]
    y_tr3 = np.log(df_train.loc[mask_tr3, "msr_action_full"].values.astype(float))
    X_te3 = X_test_all[mask_te3.values]
    y_te3 = np.log(df_test.loc[mask_te3, "msr_action_full"].values.astype(float))

    gp3 = fit_gp("log(msr_action_full)", X_tr3, y_tr3, _make_kernel(), args.seed)
    metrics3 = evaluate_gp(gp3, X_te3, y_te3)
    bundle3 = dict(
        name="log(msr_action_full)", gp_index=3,
        gp=gp3, scaler=scaler,
        X_test=X_te3, y_test=y_te3, metrics=metrics3,
        target_col="msr_action_full", target_transform="log",
        n_train=len(y_tr3), n_test=len(y_te3), n_total=n_total,
    )
    all_bundles.append(bundle3)
    _print_bundle_diagnostics(bundle3)

    # ── GPs 4 & 5: above-threshold subset, independent 80/20 split ───────────
    above_mask = df["C_bar_peak_full"] > THRESHOLD
    above_idx = np.where(above_mask.values)[0]
    above_train_idx, above_test_idx = train_test_split(
        above_idx, test_size=0.2, random_state=args.seed,
    )

    X_tr45 = scaler.transform(df.iloc[above_train_idx][FEATURE_COLS].values)
    X_te45 = scaler.transform(df.iloc[above_test_idx][FEATURE_COLS].values)

    # ── GP 4: log(M_C_bar_full_solar) ─────────────────────────────────────────
    y_tr4 = np.log(df.iloc[above_train_idx]["M_C_bar_full_solar"].values.astype(float))
    y_te4 = np.log(df.iloc[above_test_idx]["M_C_bar_full_solar"].values.astype(float))

    gp4 = fit_gp("log(M_C_bar_full_solar)", X_tr45, y_tr4, _make_kernel(), args.seed)
    metrics4 = evaluate_gp(gp4, X_te45, y_te4)
    bundle4 = dict(
        name="log(M_C_bar_full_solar)", gp_index=4,
        gp=gp4, scaler=scaler,
        X_test=X_te45, y_test=y_te4, metrics=metrics4,
        target_col="M_C_bar_full_solar", target_transform="log",
        n_train=len(y_tr4), n_test=len(y_te4), n_total=n_total,
    )
    all_bundles.append(bundle4)
    _print_bundle_diagnostics(bundle4)

    # ── GP 5: log(r_max_C_bar_full_Mpc) ──────────────────────────────────────
    y_tr5 = np.log(df.iloc[above_train_idx]["r_max_C_bar_full_Mpc"].values.astype(float))
    y_te5 = np.log(df.iloc[above_test_idx]["r_max_C_bar_full_Mpc"].values.astype(float))

    gp5 = fit_gp("log(r_max_C_bar_full_Mpc)", X_tr45, y_tr5, _make_kernel(), args.seed)
    metrics5 = evaluate_gp(gp5, X_te45, y_te5)
    bundle5 = dict(
        name="log(r_max_C_bar_full_Mpc)", gp_index=5,
        gp=gp5, scaler=scaler,
        X_test=X_te45, y_test=y_te5, metrics=metrics5,
        target_col="r_max_C_bar_full_Mpc", target_transform="log",
        n_train=len(y_tr5), n_test=len(y_te5), n_total=n_total,
    )
    all_bundles.append(bundle5)
    _print_bundle_diagnostics(bundle5)

    # ── Plots ─────────────────────────────────────────────────────────────────
    print("\nProducing plots …")
    plot_predicted_vs_actual(all_bundles, output_dir, args.format,
                             scalar_data_path=args.scalar_data, render_time=render_time)
    plot_threshold_boundary(bundle1, df_train, output_dir, args.format,
                            scalar_data_path=args.scalar_data, render_time=render_time)
    plot_ard_length_scales(all_bundles, output_dir, args.format,
                           scalar_data_path=args.scalar_data, render_time=render_time)

    # ── Serialise ─────────────────────────────────────────────────────────────
    print("\nSerialising models …")
    save_models(all_bundles, output_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
