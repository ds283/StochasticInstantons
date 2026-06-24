#!/usr/bin/env python3
"""
config/generate_lhc_grid.py
────────────────────────────
Generate a --sample-grid-csv-compatible CSV for StochasticInstanton DOE runs.

The design space is three-dimensional:
  • delta_Nstar  — excess e-folds accumulated by the instanton relative to the
                   noiseless background; controls perturbation amplitude and
                   therefore threshold crossing.
  • ΔN = N_init − N_final  — controls the log-width of the enhanced spectrum,
                   i.e. roughly ln(k_largest / k_smallest).
  • N_final      — e-folds before end of inflation at the instanton endpoint;
                   sets the absolute physical scale (PBH mass, Mpc).  Largely
                   decoupled from C_max and C̄_max but controls S_MSR at the
                   ~10%/e-fold level, so it is included as a full sampled
                   dimension rather than a replicated fixed list.

For each (delta_Nstar, ΔN, N_final) sample the script derives
  N_init = N_final + ΔN
and writes a row to the output CSV.

Physical notes
──────────────
The collapse radius r_max for C̄(r) can lie anywhere in the range
  r ~ 2π / k_largest  (scale leaving Hubble radius at N_init)
through
  r ~ 2π / k_smallest (scale leaving Hubble radius at N_final)
and may even be extrapolated beyond the grid edge when C̄ is still above
threshold at r_v[-1].  The ΔN axis therefore controls the dynamic range of
scales sampled, while delta_Nstar controls whether the threshold is crossed
at all.

Usage (quasi-random 3D design)
───────────────────────────────
python3 config/generate_lhc_grid.py \
    --delta-nstar-low  0.1  --delta-nstar-high 3.0  \
    --delta-N-low      0.5  --delta-N-high     6.0  \
    --N-final-low     15.0  --N-final-high    25.0  --N-final-samples 5 \
    --n-points         500                           \
    --method           sobol                         \
    --seed             42                            \
    --output           lhc_grid_500.csv

Usage (fixed-K mode: iso-mass min-action locus)
────────────────────────────────────────────────
Sample (delta_Nstar, ΔN) freely and set N_final = K − ΔN − delta_Nstar, keeping
N_final + ΔN + delta_Nstar = K fixed.  This holds the PBH mass approximately
constant across the grid (since log M ∝ K), so the minimum of S_MSR over the
grid traces the most-probable formation pathway at that mass.

python3 config/generate_lhc_grid.py \
    --K                43.0          \
    --delta-nstar-low   0.5  --delta-nstar-high 18.0 \
    --delta-N-low       0.5  --delta-N-high     14.0 \
    --N-final-min       5.0                          \
    --n-points         512                           \
    --method           sobol                         \
    --seed             42                            \
    --output           iso_mass_K43.csv

Usage (Cartesian product, Step 1 validation)
─────────────────────────────────────────────
python3 config/generate_lhc_grid.py \
    --delta-nstar-values 1.0 2.0 2.5 \
    --delta-N-values     3.5         \
    --N-final-values     16.0 17.0 18.0 19.0 \
    --output             step1_validation.csv

The CSV header comment records the full generation provenance.
"""

import argparse
import csv
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


# ── Argument parsing ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate a quasi-random (delta_Nstar, ΔN, N_final) sampling "
                    "grid for StochasticInstanton DOE runs.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # delta_Nstar axis
    ax = p.add_argument_group("delta_Nstar axis")
    ax.add_argument(
        "--delta-nstar-low",
        type=float,
        default=0.1,
        metavar="FLOAT",
        help="Lower bound for delta_Nstar sampling (ignored if "
             "--delta-nstar-values is given).",
    )
    ax.add_argument(
        "--delta-nstar-high",
        type=float,
        default=3.0,
        metavar="FLOAT",
        help="Upper bound for delta_Nstar sampling (ignored if "
             "--delta-nstar-values is given).",
    )
    ax.add_argument(
        "--delta-nstar-values",
        nargs="+",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Explicit list of delta_Nstar values.  When given, bypasses the "
             "quasi-random sampler and produces a Cartesian product grid.  "
             "Requires --delta-N-values and --N-final-values.  "
             "Useful for Step 1 validation runs.",
    )

    # ΔN axis
    ax2 = p.add_argument_group("ΔN = N_init − N_final axis")
    ax2.add_argument(
        "--delta-N-low",
        type=float,
        default=0.5,
        metavar="FLOAT",
        help="Lower bound for ΔN = N_init − N_final.  Must be > 0 "
             "(ignored if --delta-N-values is given).",
    )
    ax2.add_argument(
        "--delta-N-high",
        type=float,
        default=6.0,
        metavar="FLOAT",
        help="Upper bound for ΔN = N_init − N_final "
             "(ignored if --delta-N-values is given).",
    )
    ax2.add_argument(
        "--delta-N-values",
        nargs="+",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Explicit list of ΔN values for Cartesian product mode.  "
             "Requires --delta-nstar-values and --N-final-values.",
    )

    # N_final axis
    ax3 = p.add_argument_group("N_final axis")
    ax3.add_argument(
        "--N-final-low",
        type=float,
        default=15.0,
        metavar="FLOAT",
        help="Lower bound for N_final sampling (ignored if "
             "--N-final-values is given).",
    )
    ax3.add_argument(
        "--N-final-high",
        type=float,
        default=25.0,
        metavar="FLOAT",
        help="Upper bound for N_final sampling (ignored if "
             "--N-final-values is given).",
    )
    ax3.add_argument(
        "--N-final-samples",
        type=int,
        default=5,
        metavar="INT",
        help="Number of quasi-random samples along the N_final axis.  "
             "The Sobol/LHC sequence fills the full (delta_Nstar, ΔN, N_final) "
             "cube, so this controls the resolution of the N_final dimension "
             "relative to the total --n-points budget.  Ignored if "
             "--N-final-values is given.",
    )
    ax3.add_argument(
        "--N-final-values",
        nargs="+",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Explicit list of N_final values for Cartesian product mode.  "
             "Requires --delta-nstar-values and --delta-N-values.",
    )

    # Fixed-K (iso-mass) mode
    km = p.add_argument_group(
        "Fixed-K mode (iso-mass min-action locus)",
        "When --K is given, N_final is computed as K - ΔN - delta_Nstar for each "
        "point and the N_final axis arguments above are ignored.  The sampler "
        "operates in 2D (delta_Nstar, ΔN) only.",
    )
    km.add_argument(
        "--K",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Fix N_final + ΔN + delta_Nstar = K.  Activates fixed-K mode.",
    )
    km.add_argument(
        "--N-final-min",
        type=float,
        default=5.0,
        metavar="FLOAT",
        help="In fixed-K mode, drop rows where the implied N_final = K - ΔN - "
             "delta_Nstar falls below this value.",
    )

    # Boundary guards
    bnd = p.add_argument_group("Boundary guards")
    bnd.add_argument(
        "--N-init-max",
        type=float,
        default=50.0,
        metavar="FLOAT",
        help="Drop rows where N_init = N_final + ΔN exceeds this value.",
    )
    bnd.add_argument(
        "--delta-nstar-min",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Drop rows where delta_Nstar is below this value (overrides "
             "--delta-nstar-low for post-generation filtering only).  "
             "Defaults to --delta-nstar-low.",
    )

    # Sampler
    smp = p.add_argument_group("Sampler")
    smp.add_argument(
        "--n-points",
        type=int,
        default=500,
        metavar="INT",
        help="Number of quasi-random samples in the 3D "
             "(delta_Nstar, ΔN, N_final) cube.  Total output rows equals "
             "this after boundary-guard filtering.",
    )
    smp.add_argument(
        "--method",
        choices=["lhc", "sobol"],
        default="sobol",
        help="Sampling method.  'sobol' gives better space-filling properties "
             "for sensitivity analysis; 'lhc' (Latin hypercube) is simpler.",
    )
    smp.add_argument(
        "--seed",
        type=int,
        default=42,
        metavar="INT",
        help="Random seed for reproducibility.",
    )

    # Output
    out = p.add_argument_group("Output")
    out.add_argument(
        "--output",
        type=Path,
        default=Path("lhc_grid.csv"),
        metavar="PATH",
        help="Output CSV path.",
    )
    out.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print a summary of what would be written without creating the file.",
    )

    return p


# ── Sampler ────────────────────────────────────────────────────────────────────

def _sample_unit_cube(n: int, method: str, seed: int, ndim: int = 3):
    """
    Return an (n, ndim) array of samples in [0, 1)^ndim using the chosen method.

    Standard 3D mode (ndim=3):
      Column 0 -> delta_Nstar dimension
      Column 1 -> ΔN dimension
      Column 2 -> N_final dimension

    Fixed-K 2D mode (ndim=2):
      Column 0 -> delta_Nstar dimension
      Column 1 -> ΔN dimension
      (N_final is derived as K - ΔN - delta_Nstar)
    """
    from scipy.stats.qmc import LatinHypercube, Sobol

    if method == "sobol":
        # Sobol requires n to be a power of 2 for optimal properties; warn if not.
        log2_n = math.log2(n)
        if abs(log2_n - round(log2_n)) > 1e-9:
            n_rounded = 2 ** round(log2_n)
            print(
                f"  [info] Sobol sequences perform best for n = 2^k.  "
                f"Rounding {n} -> {n_rounded}.",
                file=sys.stderr,
            )
            n = n_rounded
        sampler = Sobol(d=ndim, scramble=True, seed=seed)
        samples = sampler.random(n)
    else:  # lhc
        sampler = LatinHypercube(d=ndim, seed=seed)
        samples = sampler.random(n)

    return samples, n


# ── Grid construction ──────────────────────────────────────────────────────────

def cartesian_grid(
    dns_values: list,
    dN_values: list,
    N_final_values: list,
    N_init_max: float,
    delta_nstar_min: float,
) -> tuple:
    """
    Produce a simple Cartesian product grid for Step 1 validation runs.

    Returns (rows, n_dropped_N_init, n_dropped_dns).
    """
    rows = []
    n_dropped_N_init = 0
    n_dropped_dns = 0

    for dns in dns_values:
        if dns < delta_nstar_min:
            n_dropped_dns += len(dN_values) * len(N_final_values)
            continue
        for dN in dN_values:
            if dN <= 0.0:
                raise ValueError(f"ΔN must be > 0; got {dN}")
            for N_final in N_final_values:
                N_init = N_final + dN
                if N_init > N_init_max:
                    n_dropped_N_init += 1
                    continue
                rows.append({
                    "N_init": N_init,
                    "N_final": N_final,
                    "delta_Nstar": dns,
                })

    return rows, n_dropped_N_init, n_dropped_dns


def build_grid(
    samples,                 # (n, 3) unit-cube samples
    delta_nstar_low: float,
    delta_nstar_high: float,
    delta_N_low: float,
    delta_N_high: float,
    N_final_low: float,
    N_final_high: float,
    N_init_max: float,
    delta_nstar_min: float,
) -> tuple:
    """
    Map unit-cube samples to physical parameters.

    Returns (rows, n_dropped_N_init, n_dropped_dns).

    Physical rationale for the parameter ordering
    ─────────────────────────────────────────────
    • delta_Nstar controls perturbation amplitude.  Near the threshold
      (delta_Nstar ~ 2.3 for the quadratic potential), C̄_max changes rapidly;
      dense sampling near threshold is valuable.  Linear mapping is a
      reasonable first pass.
    • ΔN controls the log-width of the perturbed spectrum.  Larger ΔN means
      the compaction function is evaluated over a wider range of scales;
      r_max may be correspondingly larger.  Linear mapping in ΔN corresponds
      to uniform coverage in log(k_large / k_small).
    • N_final sets the absolute physical scale.  Linear mapping covers the
      desired range uniformly in e-folds, which is natural given that both
      M_PBH ~ exp(2 N_final) and S_MSR ~ exp(-0.10 N_final) are smooth
      monotone functions of N_final.
    """
    rows = []
    n_dropped_N_init = 0
    n_dropped_dns = 0

    for (u_dns, u_dN, u_Nf) in samples:
        dns     = delta_nstar_low + u_dns * (delta_nstar_high - delta_nstar_low)
        dN      = delta_N_low    + u_dN  * (delta_N_high    - delta_N_low)
        N_final = N_final_low    + u_Nf  * (N_final_high    - N_final_low)

        if dns < delta_nstar_min:
            n_dropped_dns += 1
            continue

        N_init = N_final + dN
        if N_init > N_init_max:
            n_dropped_N_init += 1
            continue

        rows.append({
            "N_init":      N_init,
            "N_final":     N_final,
            "delta_Nstar": dns,
        })

    return rows, n_dropped_N_init, n_dropped_dns


def build_grid_fixed_K(
    samples,                  # (n, 2) unit-cube samples in (delta_Nstar, ΔN)
    K: float,
    delta_nstar_low: float,
    delta_nstar_high: float,
    delta_N_low: float,
    delta_N_high: float,
    N_final_min: float,
    delta_nstar_min: float,
) -> tuple:
    """
    Fixed-K mode: for each (delta_Nstar, ΔN) sample set N_final = K - ΔN - delta_Nstar.

    This keeps N_final + ΔN + delta_Nstar = K constant across the grid, so that
    log(M_PBH) is approximately fixed (up to the small residual ΔN dependence in
    the mass calibration).  The result is a 2D grid in (delta_Nstar, ΔN) space
    suitable for tracing the minimum-action formation locus at fixed mass.

    Rows are dropped when:
      • delta_Nstar < delta_nstar_min
      • N_final = K - ΔN - delta_Nstar < N_final_min  (unphysically short trajectory)

    Returns (rows, n_dropped_N_final, n_dropped_dns).
    """
    rows = []
    n_dropped_N_final = 0
    n_dropped_dns = 0

    for (u_dns, u_dN) in samples:
        dns = delta_nstar_low + u_dns * (delta_nstar_high - delta_nstar_low)
        dN  = delta_N_low    + u_dN  * (delta_N_high    - delta_N_low)

        if dns < delta_nstar_min:
            n_dropped_dns += 1
            continue

        N_final = K - dN - dns
        if N_final < N_final_min:
            n_dropped_N_final += 1
            continue

        N_init = N_final + dN
        rows.append({
            "N_init":      N_init,
            "N_final":     N_final,
            "delta_Nstar": dns,
        })

    return rows, n_dropped_N_final, n_dropped_dns

def _write_csv(path: Path, rows: list, args, n_samples_actual: int, use_cartesian: bool) -> None:
    """Write rows to CSV with a provenance comment header."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if use_cartesian:
        N_final_desc = str(sorted(args.N_final_values))
    elif args.K is not None:
        N_final_desc = f"derived: N_final = {args.K} - ΔN - delta_Nstar  (N_final_min={args.N_final_min})"
    else:
        N_final_desc = (
            f"[{args.N_final_low}, {args.N_final_high}] "
            f"({args.N_final_samples} quasi-random samples)"
        )

    comment_lines = [
        f"# StochasticInstanton sample grid",
        f"# generated: {timestamp}",
        f"# method: {'cartesian' if use_cartesian else args.method}",
        f"# seed: {args.seed}",
        f"# n_requested: {args.n_points}",
        f"# n_samples_generated: {n_samples_actual}",
        f"# delta_nstar_range: [{args.delta_nstar_low}, {args.delta_nstar_high}]",
        f"# delta_N_range: [{args.delta_N_low}, {args.delta_N_high}]",
        f"# N_final: {N_final_desc}",
    ]
    if args.K is not None:
        comment_lines.append(f"# K (= N_final + ΔN + delta_Nstar): {args.K}")
    else:
        comment_lines.append(f"# N_init_max: {args.N_init_max}")
    comment_lines.append(f"# total_rows: {len(rows)}")

    with path.open("w", newline="") as fh:
        for line in comment_lines:
            fh.write(line + "\n")
        writer = csv.DictWriter(fh, fieldnames=["N_init", "N_final", "delta_Nstar"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "N_init":      f"{row['N_init']:.8f}",
                "N_final":     f"{row['N_final']:.8f}",
                "delta_Nstar": f"{row['delta_Nstar']:.8f}",
            })


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = _build_parser()
    args = parser.parse_args()

    if args.n_points < 1:
        parser.error("--n-points must be >= 1.")

    delta_nstar_min = (
        args.delta_nstar_min
        if args.delta_nstar_min is not None
        else args.delta_nstar_low
    )

    # ── Choose generation mode ────────────────────────────────────────────────
    use_fixed_K = args.K is not None
    use_cartesian = (
        not use_fixed_K
        and (
            args.delta_nstar_values is not None
            or args.delta_N_values is not None
            or args.N_final_values is not None
        )
    )

    if use_fixed_K and use_cartesian:
        parser.error("--K cannot be combined with --delta-nstar-values / "
                     "--delta-N-values / --N-final-values.")

    if use_fixed_K:
        # Validate 2D bounds only
        if args.delta_nstar_low >= args.delta_nstar_high:
            parser.error(
                f"--delta-nstar-low ({args.delta_nstar_low}) must be < "
                f"--delta-nstar-high ({args.delta_nstar_high})"
            )
        if args.delta_N_low >= args.delta_N_high:
            parser.error(
                f"--delta-N-low ({args.delta_N_low}) must be < "
                f"--delta-N-high ({args.delta_N_high})"
            )
        if args.delta_N_low <= 0.0:
            parser.error(
                f"--delta-N-low ({args.delta_N_low}) must be > 0."
            )
        print(
            f"Generating {args.n_points} {args.method.upper()} samples "
            f"(seed={args.seed}) in fixed-K={args.K} mode ..."
        )
        samples, n_actual = _sample_unit_cube(args.n_points, args.method, args.seed, ndim=2)
        print(f"  -> {n_actual} unit-cube samples generated.")
        rows, n_dropped_N_final, n_dropped_dns = build_grid_fixed_K(
            samples,
            K=args.K,
            delta_nstar_low=args.delta_nstar_low,
            delta_nstar_high=args.delta_nstar_high,
            delta_N_low=args.delta_N_low,
            delta_N_high=args.delta_N_high,
            N_final_min=args.N_final_min,
            delta_nstar_min=delta_nstar_min,
        )
        n_dropped_N_init = n_dropped_N_final  # reuse variable for summary below
    elif use_cartesian:
        # All three explicit-values flags must be present together.
        missing = [
            name for name, val in [
                ("--delta-nstar-values", args.delta_nstar_values),
                ("--delta-N-values",     args.delta_N_values),
                ("--N-final-values",     args.N_final_values),
            ]
            if val is None
        ]
        if missing:
            parser.error(
                f"Cartesian product mode requires all three explicit-values flags; "
                f"missing: {', '.join(missing)}"
            )
        dns_values    = sorted(args.delta_nstar_values)
        dN_values     = sorted(args.delta_N_values)
        N_final_values = sorted(args.N_final_values)
        n_actual      = len(dns_values) * len(dN_values) * len(N_final_values)
        print(
            f"Cartesian-product mode: {len(dns_values)} delta_Nstar × "
            f"{len(dN_values)} ΔN × {len(N_final_values)} N_final "
            f"= {n_actual} rows …"
        )
        rows, n_dropped_N_init, n_dropped_dns = cartesian_grid(
            dns_values=dns_values,
            dN_values=dN_values,
            N_final_values=N_final_values,
            N_init_max=args.N_init_max,
            delta_nstar_min=delta_nstar_min,
        )
    else:
        # ── Validate bounds ───────────────────────────────────────────────────
        if args.delta_nstar_low >= args.delta_nstar_high:
            parser.error(
                f"--delta-nstar-low ({args.delta_nstar_low}) must be < "
                f"--delta-nstar-high ({args.delta_nstar_high})"
            )
        if args.delta_N_low >= args.delta_N_high:
            parser.error(
                f"--delta-N-low ({args.delta_N_low}) must be < "
                f"--delta-N-high ({args.delta_N_high})"
            )
        if args.delta_N_low <= 0.0:
            parser.error(
                f"--delta-N-low ({args.delta_N_low}) must be > 0 "
                f"(N_init must exceed N_final)."
            )
        if args.N_final_low >= args.N_final_high:
            parser.error(
                f"--N-final-low ({args.N_final_low}) must be < "
                f"--N-final-high ({args.N_final_high})"
            )
        if args.N_final_samples < 1:
            parser.error("--N-final-samples must be >= 1.")

        # ── Generate unit-cube samples ────────────────────────────────────────
        print(f"Generating {args.n_points} {args.method.upper()} samples (seed={args.seed}) …")
        samples, n_actual = _sample_unit_cube(args.n_points, args.method, args.seed)
        print(f"  → {n_actual} unit-cube samples generated.")

        # ── Map to physical grid ──────────────────────────────────────────────
        rows, n_dropped_N_init, n_dropped_dns = build_grid(
            samples,
            delta_nstar_low=args.delta_nstar_low,
            delta_nstar_high=args.delta_nstar_high,
            delta_N_low=args.delta_N_low,
            delta_N_high=args.delta_N_high,
            N_final_low=args.N_final_low,
            N_final_high=args.N_final_high,
            N_init_max=args.N_init_max,
            delta_nstar_min=delta_nstar_min,
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("Grid summary")
    print("────────────")
    if use_fixed_K:
        print(f"  Mode               : fixed-K = {args.K}")
        print(f"  Sampling method    : {args.method}")
        print(f"  Seed               : {args.seed}")
        print(f"  Samples generated  : {n_actual}")
        print(f"  N_final_min        : {args.N_final_min}")
        print(f"  Dropped (N_final<min): {n_dropped_N_init}")
        print(f"  Dropped (dns<min)  : {n_dropped_dns}")
    elif use_cartesian:
        print(f"  Mode               : Cartesian product")
        print(f"  Dropped (N_init>max): {n_dropped_N_init}")
        print(f"  Dropped (dns<min)  : {n_dropped_dns}")
    else:
        print(f"  Sampling method    : {args.method}")
        print(f"  Seed               : {args.seed}")
        print(f"  Samples generated  : {n_actual}")
        print(f"  N_final range      : [{args.N_final_low}, {args.N_final_high}]")
        print(f"  Dropped (N_init>max): {n_dropped_N_init}")
        print(f"  Dropped (dns<min)  : {n_dropped_dns}")
    print(f"  Output rows        : {len(rows)}")
    if rows:
        dns_vals = [r["delta_Nstar"] for r in rows]
        dN_vals  = [r["N_init"] - r["N_final"] for r in rows]
        Nf_vals  = [r["N_final"] for r in rows]
        Ni_vals  = [r["N_init"] for r in rows]
        print()
        print(f"  delta_Nstar : [{min(dns_vals):.4f}, {max(dns_vals):.4f}]")
        print(f"  ΔN          : [{min(dN_vals):.4f}, {max(dN_vals):.4f}]")
        print(f"  N_final     : [{min(Nf_vals):.4f}, {max(Nf_vals):.4f}]")
        print(f"  N_init      : [{min(Ni_vals):.4f}, {max(Ni_vals):.4f}]")

    if args.dry_run:
        print()
        print("[dry-run] No file written.")
        return

    if not rows:
        print()
        print("[warning] All rows were dropped by boundary guards — no CSV written.")
        sys.exit(1)

    # ── Write ─────────────────────────────────────────────────────────────────
    args.output.parent.mkdir(parents=True, exist_ok=True)
    _write_csv(args.output, rows, args, n_actual, use_cartesian)
    print()
    print(f"Written {len(rows)} rows to: {args.output}")


if __name__ == "__main__":
    main()
