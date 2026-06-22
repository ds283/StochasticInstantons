#!/usr/bin/env python3
"""
config/generate_lhc_grid.py
────────────────────────────
Generate a --sample-grid-csv-compatible CSV for StochasticInstanton DOE runs.

The effective physics parameter space is two-dimensional:
  • delta_Nstar  — excess e-folds accumulated by the instanton relative to the
                   noiseless background; controls perturbation amplitude and
                   therefore threshold crossing.
  • ΔN = N_init − N_final  — controls the log-width of the enhanced spectrum,
                   i.e. roughly ln(k_largest / k_smallest).

N_final sets the absolute physical scale (PBH mass, Mpc) and is treated as a
near-independent "calibration" axis, sampled coarsely.

For each (delta_Nstar, ΔN) sample and each N_final value, the script derives
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
at all.  Sampling both parameters densely (with N_final fixed) gives the
most information about r_max and M_PBH sensitivity.

Usage
─────
python3 config/generate_lhc_grid.py \\
    --delta-nstar-low  0.1  --delta-nstar-high 3.0  \\
    --delta-N-low      0.5  --delta-N-high     6.0  \\
    --N-final-values   16.0 17.5 19.0               \\
    --n-points         500                           \\
    --method           sobol                         \\
    --seed             42                            \\
    --output           lhc_grid_500.csv

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
             "quasi-random sampler entirely and produces a simple Cartesian "
             "product of (delta_Nstar) × (delta_N_values) × (N_final_values).  "
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
        help="Explicit list of ΔN values.  When given together with "
             "--delta-nstar-values, produces a simple Cartesian product "
             "grid rather than a quasi-random design.",
    )

    # N_final calibration values
    cal = p.add_argument_group("N_final calibration axis")
    cal.add_argument(
        "--N-final-values",
        nargs="+",
        type=float,
        default=[16.0, 17.5, 19.0],
        metavar="FLOAT",
        help="One or more N_final values (e-folds before end of inflation at "
             "instanton endpoint).  Each value produces a copy of the 2-D design.",
    )

    # Boundary guards
    bnd = p.add_argument_group("Boundary guards")
    bnd.add_argument(
        "--N-init-max",
        type=float,
        default=25.0,
        metavar="FLOAT",
        help="Drop rows where N_init = N_final + ΔN exceeds this value.",
    )
    bnd.add_argument(
        "--delta-nstar-min",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Drop rows where delta_Nstar is below this value (overrides "
             "--delta-nstar-low for post-generation filtering only; useful when "
             "the low bound is relaxed for design purposes but very small values "
             "are unphysical for a particular run).  Defaults to --delta-nstar-low.",
    )

    # Sampler
    smp = p.add_argument_group("Sampler")
    smp.add_argument(
        "--n-points",
        type=int,
        default=500,
        metavar="INT",
        help="Number of quasi-random samples in the (delta_Nstar, ΔN) plane "
             "before N_final replication.  Total rows ≤ n_points × len(N_final_values).",
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

def _sample_unit_square(n: int, method: str, seed: int):
    """
    Return an (n, 2) array of samples in [0, 1)^2 using the chosen method.

    Column 0 → delta_Nstar dimension
    Column 1 → ΔN dimension
    """
    from scipy.stats.qmc import LatinHypercube, Sobol

    if method == "sobol":
        # Sobol requires n to be a power of 2 for optimal properties; warn if not.
        log2_n = math.log2(n)
        if abs(log2_n - round(log2_n)) > 1e-9:
            n_rounded = 2 ** round(log2_n)
            print(
                f"  [info] Sobol sequences perform best for n = 2^k.  "
                f"Rounding {n} → {n_rounded}.",
                file=sys.stderr,
            )
            n = n_rounded
        sampler = Sobol(d=2, scramble=True, seed=seed)
        samples = sampler.random(n)
    else:  # lhc
        sampler = LatinHypercube(d=2, seed=seed)
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
    samples,            # (n, 2) unit-square samples
    delta_nstar_low: float,
    delta_nstar_high: float,
    delta_N_low: float,
    delta_N_high: float,
    N_final_values: list,
    N_init_max: float,
    delta_nstar_min: float,
) -> list:
    """
    Map unit-square samples to physical parameters and replicate across N_final.

    Returns a list of dicts with keys: N_init, N_final, delta_Nstar.
    Rows violating boundary constraints are dropped.

    Physical rationale for the parameter ordering
    ─────────────────────────────────────────────
    • delta_Nstar controls perturbation amplitude.  Near the threshold
      (delta_Nstar ~ 2.3 for quadratic potential), C̄_max changes rapidly;
      dense sampling near threshold is valuable.  Linear mapping is a
      reasonable first pass; log-space can be considered if the response is
      very steep at low values.
    • ΔN controls the log-width of the perturbed spectrum.  Larger ΔN means
      the compaction function is evaluated over a wider range of scales;
      r_max may be correspondingly larger.  Linear mapping in ΔN corresponds
      to uniform coverage in log(k_large / k_small).
    • N_final is replicated coarsely (3–5 values).  It shifts the absolute
      physical scale (mass, Mpc) but leaves C̄_max and C_max largely
      unchanged — the decoupling hypothesis to be verified by Step 1
      validation runs.
    """
    rows = []
    n_dropped_N_init = 0
    n_dropped_dns = 0

    for (u_dns, u_dN) in samples:
        # Map from [0, 1) to physical range (linear in both dimensions)
        dns = delta_nstar_low + u_dns * (delta_nstar_high - delta_nstar_low)
        dN  = delta_N_low    + u_dN  * (delta_N_high    - delta_N_low)

        # Enforce delta_nstar_min guard
        if dns < delta_nstar_min:
            n_dropped_dns += 1
            continue

        for N_final in N_final_values:
            N_init = N_final + dN

            # Enforce N_init ceiling
            if N_init > N_init_max:
                n_dropped_N_init += 1
                continue

            rows.append({
                "N_init":       N_init,
                "N_final":      N_final,
                "delta_Nstar":  dns,
            })

    return rows, n_dropped_N_init, n_dropped_dns


# ── CSV output ─────────────────────────────────────────────────────────────────

def _write_csv(path: Path, rows: list, args, n_samples_actual: int) -> None:
    """Write rows to CSV with a provenance comment header."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build comment block — we embed it as lines starting with '#'.
    # The pipeline's CSV reader (csv.DictReader) skips lines starting with '#'
    # if the caller uses a filtering wrapper, but the canonical convention in
    # this codebase is a plain header line first.  We therefore write the
    # provenance as comments *before* the column header.
    comment_lines = [
        f"# StochasticInstanton sample grid",
        f"# generated: {timestamp}",
        f"# method: {args.method}",
        f"# seed: {args.seed}",
        f"# n_requested: {args.n_points}",
        f"# n_samples_generated: {n_samples_actual}",
        f"# delta_nstar_range: [{args.delta_nstar_low}, {args.delta_nstar_high}]",
        f"# delta_N_range: [{args.delta_N_low}, {args.delta_N_high}]",
        f"# N_final_values: {args.N_final_values}",
        f"# N_init_max: {args.N_init_max}",
        f"# total_rows: {len(rows)}",
    ]

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

    # ── Validate bounds ───────────────────────────────────────────────────────
    if not args.N_final_values:
        parser.error("At least one --N-final-values value is required.")
    if args.n_points < 1:
        parser.error("--n-points must be >= 1.")

    delta_nstar_min = (
        args.delta_nstar_min
        if args.delta_nstar_min is not None
        else args.delta_nstar_low
    )

    # ── Choose generation mode ────────────────────────────────────────────────
    use_cartesian = (
        args.delta_nstar_values is not None or args.delta_N_values is not None
    )

    if use_cartesian:
        # Cartesian-product mode (Step 1 validation / targeted runs)
        if args.delta_nstar_values is None:
            parser.error(
                "--delta-N-values requires --delta-nstar-values "
                "(cannot mix explicit ΔN with a quasi-random delta_Nstar design)"
            )
        if args.delta_N_values is None:
            parser.error(
                "--delta-nstar-values requires --delta-N-values "
                "(cannot mix explicit delta_Nstar with a quasi-random ΔN design)"
            )
        dns_values = sorted(args.delta_nstar_values)
        dN_values  = sorted(args.delta_N_values)
        n_actual   = len(dns_values) * len(dN_values)
        print(
            f"Cartesian-product mode: {len(dns_values)} delta_Nstar × "
            f"{len(dN_values)} ΔN = {n_actual} base points …"
        )
        rows, n_dropped_N_init, n_dropped_dns = cartesian_grid(
            dns_values=dns_values,
            dN_values=dN_values,
            N_final_values=sorted(args.N_final_values),
            N_init_max=args.N_init_max,
            delta_nstar_min=delta_nstar_min,
        )
    else:
        # ── Generate unit-square samples ──────────────────────────────────────
        print(f"Generating {args.n_points} {args.method.upper()} samples (seed={args.seed}) …")
        samples, n_actual = _sample_unit_square(args.n_points, args.method, args.seed)
        print(f"  → {n_actual} unit-square samples generated.")

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

        # ── Map to physical grid ──────────────────────────────────────────────
        rows, n_dropped_N_init, n_dropped_dns = build_grid(
            samples,
            delta_nstar_low=args.delta_nstar_low,
            delta_nstar_high=args.delta_nstar_high,
            delta_N_low=args.delta_N_low,
            delta_N_high=args.delta_N_high,
            N_final_values=sorted(args.N_final_values),
            N_init_max=args.N_init_max,
            delta_nstar_min=delta_nstar_min,
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("Grid summary")
    print("────────────")
    print(f"  Sampling method    : {args.method}")
    print(f"  Seed               : {args.seed}")
    print(f"  2-D samples        : {n_actual}")
    print(f"  N_final values     : {sorted(args.N_final_values)}")
    print(f"  Maximum possible   : {n_actual * len(args.N_final_values)}")
    print(f"  Dropped (N_init>max): {n_dropped_N_init}")
    print(f"  Dropped (dns<min)  : {n_dropped_dns}")
    print(f"  Output rows        : {len(rows)}")
    if rows:
        dns_vals = [r["delta_Nstar"] for r in rows]
        dN_vals  = [r["N_init"] - r["N_final"] for r in rows]
        Ni_vals  = [r["N_init"] for r in rows]
        print()
        print(f"  delta_Nstar : [{min(dns_vals):.4f}, {max(dns_vals):.4f}]")
        print(f"  ΔN          : [{min(dN_vals):.4f}, {max(dN_vals):.4f}]")
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
    _write_csv(args.output, rows, args, n_actual)
    print()
    print(f"Written {len(rows)} rows to: {args.output}")


if __name__ == "__main__":
    main()
