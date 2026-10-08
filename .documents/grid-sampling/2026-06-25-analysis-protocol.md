# PBH Formation Analysis Protocol
_How to reproduce the minimum-action formation pathway analysis for a new potential._

> **Provenance (recovered 8 October 2026).** Written by Claude in the claude.ai
> conversation "PBH formation parameter space analysis" (25 June 2026) and never
> committed. Recovered verbatim from the personal-account claude.ai export
> (`conversations-000-2.zip`); the text below is unchanged.
>
> **Status.** Every number below that depends on the instanton solution (the
> action, the minimum-action locus, the collapse thresholds, the
> `r_max`/`r_peak` boundary) was computed with the defective FullInstanton
> response sector and is provisional until re-run
> (`handoff-notes/2026-10-08/RECONSTRUCTION.md` B.10;
> `.documents/OPEN-ISSUES.md` `[june-smsr-results-provisional]`). Only the
> mass law is kinematic and expected to survive.
> Read with RECONSTRUCTION.md Part A0.3 and `summary-F-june-science.md`.
>
> The `generate_lhc_grid.py` flags used below (`--K`, `--N-final-min`) exist
> in the tree as of 8 October 2026. The protocol inherits the June
> pipeline's response-sector defect: re-run the quadratic baseline after
> the Hamiltonian module lands before comparing other potentials with it.

---

## Background and goals

This protocol analyses PBH formation in the stochastic inflation / MSR instanton
framework. For a given inflaton potential, the pipeline computes the instanton
action S_MSR and compaction function scalars for a grid of parameter triples
(N_init, N_final, delta_Nstar). The derived quantities are:

- **ΔN = N_init − N_final**: log-width of the enhanced perturbation
- **δN★**: excess e-folds accumulated by the instanton (≈ peak ζ)
- **K = N_final + ΔN + δN★ = N_init + δN★**: determines PBH mass via
  log₁₀(M/M☉) ≈ 0.84·K − 36.5 (calibrated for the quadratic potential;
  re-calibrate for each new potential)

The three scientific questions addressed are:

1. **Threshold**: what is the minimum δN★ needed to form a PBH at each ΔN?
2. **Min-action locus**: at fixed PBH mass (fixed K), which (ΔN, δN★) pair
   minimises S_MSR?
3. **M_peak vs M_max**: when do the two mass estimates diverge, and which is
   physically correct?

All grids use `--no-store-values` mode (scalars only). The key output is
`scalar_data.csv` from `plot_InstantonSolutions.py`.

---

## Key empirical results (quadratic potential, for comparison)

These serve as a baseline when running a new potential.

**Mass calibration**: log₁₀(M/M☉) = 0.84·K − 36.5, residual RMS 0.02–0.04 dex.
K is essentially the only predictor of mass; ΔN has a weak secondary effect.

**Collapse threshold**:
- Small ΔN (< 2): δN★_th ≈ 0.55·ΔN (nearly linear)
- Large ΔN (> 2): δN★_th ≈ 1.03·ΔN^0.68
- The threshold is **mass-independent** (independent of N_final)

**Minimum-action result**: S_MSR is monotonically decreasing as (ΔN, δN★)
decrease toward the threshold. The minimum-action locus runs along the collapse
boundary at the smallest (ΔN, δN★) sampled. No interior minimum has been found;
see open question below.

**r_max vs r_peak**: diverge when ΔN/δN★ ≲ 0.45 (large δN★, narrow ΔN).
M_max/M_peak can reach 10²² in the extreme regime. The minimum-action locus
sits at ΔN/δN★ ~ 0.55–0.65, just above the divergence boundary, so M_peak ≈ M_max
throughout the physically relevant regime.

---

## Grid sequence

Run the grids in order. Each informs the design of the next.

### Grid 1: Phase A — exploratory broad coverage

**Purpose**: map the (δN★, ΔN) plane; locate the collapse threshold;
establish the mass calibration K vs log M.

```bash
python3 config/generate_lhc_grid.py \
    --delta-nstar-low  1.5  --delta-nstar-high 18.0 \
    --delta-N-low      0.5  --delta-N-high     14.0 \
    --N-final-low     19.5  --N-final-high     20.5 \
    --n-points        1024 \
    --method          sobol \
    --seed            42 \
    --output          phase_a_grid.csv

python3 main.py \
    --database phase_a.sqlite \
    --config <potential>.yaml \
    --sample-grid-csv phase_a_grid.csv \
    --no-store-values

python3 plot_InstantonSolutions.py \
    --database phase_a.sqlite \
    --config <potential>.yaml \
    --output-dir out-phase-a \
    --no-store-values
# -> out-phase-a/.../doe_summary/scalar_data.csv
```

**Analysis** (see Section A below):
1. Fit mass calibration: log₁₀(M/M☉) vs K = N_final + ΔN + δN★
2. Fit threshold curve δN★_th(ΔN) using power law
3. Check r_max vs r_peak divergence; establish the ΔN/δN★ boundary
4. Map S_MSR landscape; note that min-S is at the grid edge (small ΔN, δN★)

**PBH formation criterion**: absence of `r_max_full_Mpc` AND `r_max_sr_Mpc`
means no PBH formed. Use `M_max_full_solar` where available, else `M_max_sr_solar`.

---

### Grid 2: Fixed-K iso-mass grids

**Purpose**: find the minimum-action (ΔN, δN★) at fixed PBH mass.
Run four separate grids, one per target mass. N_final is computed as
K − ΔN − δN★ for each point, keeping the mass approximately fixed.

Choose K values to span the mass range of interest. For the quadratic potential,
K ∈ {23, 33, 43, 53} spans asteroid to supermassive. Adjust K based on the
mass calibration from Grid 1.

The grid script `--K` mode handles this automatically:

```bash
for K in 23 33 43 53; do
    python3 config/generate_lhc_grid.py \
        --K $K \
        --delta-nstar-low  0.1  --delta-nstar-high  1.0 \
        --delta-N-low      0.05 --delta-N-high      3.0 \
        --N-final-min      3.0 \
        --n-points         512 \
        --method           sobol \
        --seed             42 \
        --output           iso_mass_K${K}.csv

    python3 main.py \
        --database iso_mass_K${K}.sqlite \
        --config <potential>.yaml \
        --sample-grid-csv iso_mass_K${K}.csv \
        --no-store-values

    python3 plot_InstantonSolutions.py \
        --database iso_mass_K${K}.sqlite \
        --config <potential>.yaml \
        --output-dir out-K${K} \
        --no-store-values
done
```

The parameter ranges above (δN★ ∈ [0.1, 1], ΔN ∈ [0.05, 3]) target the
**small-δN★ regime** identified as hosting the minimum-action locus. If the
potential has a qualitatively different threshold shape (check from Grid 1),
adjust accordingly.

**Analysis** (see Section B below):
1. Verify K constraint holds: N_final + ΔN + δN★ = K to machine precision
2. Confirm threshold is mass-independent across the four K values
3. Find min-S point in each K grid — expect it at the smallest (ΔN, δN★) corner
4. Plot S_MSR landscape and min-S locus in the (δN★, ΔN) plane

---

### Grid 3 (optional): Extended fixed-K at larger (ΔN, δN★)

**Purpose**: confirm that S_MSR continues to increase as (ΔN, δN★) grow,
and that no interior minimum exists at larger values. This grid is recommended
if the Phase A S_MSR landscape shows any hint of non-monotone behaviour.

```bash
for K in 23 33 43 53; do
    python3 config/generate_lhc_grid.py \
        --K $K \
        --delta-nstar-low  1.0  --delta-nstar-high 12.0 \
        --delta-N-low      2.0  --delta-N-high     23.0 \
        --N-final-min      3.0 \
        --n-points         512 \
        --method           sobol \
        --seed             42 \
        --output           iso_mass_large_K${K}.csv
done
```

For K = 23, many points will be dropped by the N_final_min guard
(ΔN + δN★ > K − 3 = 20). Use `--n-points 1024` for K = 23 to compensate.

---

## Open question: does the minimum-action point continue to smaller (ΔN, δN★)?

In the quadratic potential, S_MSR is still decreasing at the smallest (ΔN, δN★)
sampled (ΔN ~ 0.05, δN★ ~ 0.05 near threshold). It is unknown whether:

(a) S_MSR continues to decrease as (ΔN, δN★) → 0 along the threshold, implying
    the "optimal" pathway is an arbitrarily small perturbation — which would mean
    the instanton is not the right object and the formation is dominated by
    accumulation of many small fluctuations (diffusion-dominated regime).

(b) S_MSR has a genuine minimum at some finite (ΔN, δN★), below which the
    instanton approximation breaks down or the noise amplitude becomes so small
    that the stochastic description is invalid.

**To test this**: run a dense grid at very small (ΔN, δN★):

```bash
python3 config/generate_lhc_grid.py \
    --K <chosen K> \
    --delta-nstar-low  0.01 --delta-nstar-high 0.2 \
    --delta-N-low      0.01 --delta-N-high     0.3 \
    --N-final-min      3.0 \
    --n-points         512 \
    --method           sobol \
    --seed             42 \
    --output           iso_mass_verysmall_K<K>.csv
```

If S_MSR is still decreasing here, the minimum is in the diffusion-dominated
regime and the instanton picture breaks down before the minimum is reached.
This is a qualitative question about the physics that may differ between potentials.

**Note**: this grid was not run for the quadratic potential. It is recommended
as a first step for any new potential before drawing conclusions about the
minimum-action pathway.

---

## Phase B grid (fixed N_final, small δN★)

The Phase B grid (δN★ ∈ [0.1, 1], ΔN ∈ [0.05, 2], N_final ~ 20) was run for
the quadratic potential. Its main contribution was:

- Measuring the threshold at small ΔN, showing it is nearly linear
  (δN★_th ≈ 0.55·ΔN), correcting the extrapolation of the Phase A power law
- Confirming r_max = r_peak throughout (no divergence at small δN★)

**Recommendation**: Phase B is **not needed as a separate grid** if the fixed-K
grids (Grid 2) are run, since they cover the same (δN★, ΔN) region with the
additional advantage of fixed mass. The threshold shape can be read off from
Grid 2 directly. Skip Phase B unless you specifically want the threshold at
fixed N_final (e.g. for comparison with fixed-N_final results in the literature).

---

## Analysis procedures

### Section A: Phase A analysis

```python
import pandas as pd, numpy as np
from scipy.optimize import curve_fit

df = pd.read_csv('scalar_data.csv')
df['pbh_formed'] = df['r_max_full_Mpc'].notna() | df['r_max_sr_Mpc'].notna()
df['M_best'] = df['M_max_full_solar'].where(
    df['M_max_full_solar'].notna(), df['M_max_sr_solar'])
df['S_best'] = df['msr_action_full'].where(
    df['msr_action_full'].notna(), df['msr_action_sr'])
df['delta_N'] = df['N_init'] - df['N_final']
df['K'] = df['N_final'] + df['delta_N'] + df['delta_Nstar']
formed = df[df['pbh_formed']].copy()
formed['log_M'] = np.log10(formed['M_best'])
formed['log_S'] = np.log10(formed['S_best'])

# 1. Mass calibration
c = np.polyfit(formed['K'], formed['log_M'], 1)
print(f'log_M = {c[0]:.3f} * K + {c[1]:.3f}')

# 2. Threshold curve
dN_bins = np.arange(0, 14.5, 0.5)
thresh_rows = []
for lo, hi in zip(dN_bins[:-1], dN_bins[1:]):
    strip = df[(df['delta_N'] >= lo) & (df['delta_N'] < hi)]
    f = strip[strip['pbh_formed']]
    nf = strip[~strip['pbh_formed']]
    if len(f) == 0: continue
    min_f = f['delta_Nstar'].min()
    max_nf = nf['delta_Nstar'].max() if len(nf) > 0 else np.nan
    th = (min_f + max_nf)/2 if not np.isnan(max_nf) else min_f
    thresh_rows.append({'dN': (lo+hi)/2, 'threshold': th})
thresh = pd.DataFrame(thresh_rows)
popt, _ = curve_fit(lambda x,a,b: a*x**b,
                    thresh['dN'], thresh['threshold'], p0=[1.0, 0.68])
print(f'Threshold: delta_Nstar_th = {popt[0]:.3f} * delta_N^{popt[1]:.3f}')

# 3. r_max vs r_peak divergence
f2 = formed[formed['r_max_full_Mpc'].notna() & formed['r_peak_full_Mpc'].notna()].copy()
f2['r_ratio'] = f2['r_max_full_Mpc'] / f2['r_peak_full_Mpc']
f2['dN_over_dNstar'] = f2['delta_N'] / f2['delta_Nstar']
print(f'Diverged (r_ratio>1.01): {(f2["r_ratio"]>1.01).sum()} / {len(f2)}')
# Divergence occurs when delta_N / delta_Nstar < ~0.45 (quadratic potential)
```

### Section B: Fixed-K analysis

```python
# Load all four K grids
dfs = {}
for K in [23, 33, 43, 53]:
    df = pd.read_csv(f'scalar_data-K{K}.csv')
    df['pbh_formed'] = df['r_max_full_Mpc'].notna() | df['r_max_sr_Mpc'].notna()
    df['S_best'] = df['msr_action_full'].where(
        df['msr_action_full'].notna(), df['msr_action_sr'])
    df['delta_N'] = df['N_init'] - df['N_final']
    dfs[K] = df

# For each K: threshold, min-S point, S landscape
for K, df in dfs.items():
    formed = df[df['pbh_formed']].copy()
    formed['log_S'] = np.log10(formed['S_best'])

    # Min-S point
    idx = formed['log_S'].idxmin()
    r = formed.loc[idx]
    print(f'K={K}: min-S at δN★={r["delta_Nstar"]:.3f}, '
          f'ΔN={r["delta_N"]:.3f}, log_S={r["log_S"]:.3f}')

    # Min-S by ΔN bin (check for monotonicity)
    bins = np.arange(0, 3.2, 0.2)
    for lo, hi in zip(bins[:-1], bins[1:]):
        sub = formed[(formed['delta_N'] >= lo) & (formed['delta_N'] < hi)]
        if len(sub) < 2: continue
        print(f'  ΔN=[{lo:.1f},{hi:.1f}): min log_S={sub["log_S"].min():.3f}')
```

---

## Checklist for a new potential

- [ ] Run Grid 1 (Phase A). Fit mass calibration and threshold.
- [ ] Compare threshold shape and exponent with quadratic baseline.
- [ ] Check r_max vs r_peak divergence boundary (is ΔN/δN★ ~ 0.45 universal?).
- [ ] Choose K values for Grid 2 based on mass calibration.
- [ ] Run Grid 2 (fixed-K, small δN★). Confirm min-S at bottom-left corner.
- [ ] Check whether threshold is mass-independent (compare threshold fits across K).
- [ ] Run very-small-(ΔN, δN★) grid to probe whether S continues decreasing.
- [ ] If Phase A shows non-monotone S_MSR, run Grid 3 (extended fixed-K).
- [ ] Compare all results with quadratic potential baseline.
- [ ] Flag any qualitative differences (different threshold exponent, interior
      minimum found, r_max/r_peak boundary shifted) for potential-specific follow-up.
