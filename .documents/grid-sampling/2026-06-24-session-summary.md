# StochasticInstanton — Session Summary
_Analysis session, 2026-06-24. Covers Goal 2 (minimum-action formation pathway)
and connections to the Vennin et al. spectral formalism._

> **Provenance (recovered 8 October 2026).** Written by Claude in the claude.ai
> conversation "PBH formation parameter space analysis" (24 June 2026) and never
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
> Further points that override the text: the "Vennin asymptotic exponent"
> question (§7) rests on an identification retracted on 18 June
> (RECONSTRUCTION A0.1); §5.2's preference for `M_peak` is an opinion, and the
> choice of mass estimate is open (`[r-max-vs-r-peak-mass-estimate]`).

---

## 1. Grid overview

Two main grids were analysed this session, plus several targeted fixed-K grids.

| Grid | δN★ range | ΔN range | N_final | Points | Notes |
|------|-----------|----------|---------|--------|-------|
| Phase A (original) | 0.1–1.0 | 0.05–2.0 | ~20 | 512 | Mislabelled "Phase A" early in session; actually the small-δN★ grid |
| Phase A (recomputed) | 1.5–18 | 0.5–14 | ~20 | 1024 | True Phase A; compaction function bugfix applied |
| Fixed-K small (×4) | 0.1–1.0 | 0.05–2.0 | varies | ~160 formed/K | K ∈ {23, 33, 43, 53}; iso-mass grids |
| Fixed-K large (×4) | 1.0–12 | 2.0–23 | varies | ~400 formed/K | K ∈ {23, 33, 43, 53}; constrained optimisation |

---

## 2. Mass predictor

Across all grids, the PBH mass is determined almost entirely by:

$$\log_{10}(M/M_\odot) \approx 0.84 \times (N_\mathrm{final} + \Delta N + \delta N_\star) - 36.5 = 0.84\,K - 36.5$$

with residual RMS of ~0.02–0.04 dex. The combination
$K = N_\mathrm{final} + \Delta N + \delta N_\star = N_\mathrm{init} + \delta N_\star$
is the sufficient statistic for mass. N_final alone has negligible predictive power;
N_init alone is moderate. The four K values used correspond approximately to:

| K | log₁₀(M/M☉) | Mass scale |
|---|---|---|
| 23 | −16.7 | ~10⁻¹⁷ M☉ (small asteroid) |
| 33 | −8.3 | ~10⁻⁸ M☉ (large asteroid) |
| 43 | 0.1 | ~1 M☉ |
| 53 | 8.5 | ~10⁸ M☉ |

---

## 3. Collapse threshold

The threshold curve δN★_th(ΔN) was measured empirically across both grids.

**Small-ΔN regime** (Phase B / small-δN★ grid, ΔN ∈ [0.05, 2]):

$$\delta N_{\star,\mathrm{th}} \approx 0.55 \times \Delta N^{0.95} \approx 0.55\,\Delta N$$

The threshold is nearly linear, approaching zero as ΔN → 0 (physically correct).

**Large-ΔN regime** (Phase A, ΔN ∈ [0.5, 14]):

$$\delta N_{\star,\mathrm{th}} \approx 1.03 \times \Delta N^{0.68}$$

The Phase A power law was confirmed not to extrapolate correctly to small ΔN —
the true threshold flattens at small ΔN rather than diverging.

**Mass independence confirmed:** The threshold curve δN★_th(ΔN) is independent of
N_final (and hence of the target PBH mass) to high precision. C_peak is a
dimensionless function of the instanton shape (δN★, ΔN) only. This was confirmed
both theoretically and empirically (partial correlation of C_peak residuals with
N_final < 0.001 across all grids).

---

## 4. Minimum-action formation pathway

### 4.1 Result

The minimum-action (most probable) formation pathway at **fixed PBH mass** is
always at the **smallest (ΔN, δN★) pair that still achieves collapse** at that mass.
S_MSR is monotonically decreasing as (ΔN, δN★) decrease toward the threshold curve.

This was confirmed by:
- Fixed-K small grids (δN★ ∈ [0.1, 1]): min-S at ΔN ~ 0.2, δN★ ~ 0.12 (bottom-left corner)
- Fixed-K large grids (δN★ ∈ [1, 12], ΔN ∈ [2, 23]): min-S at ΔN ~ 2.5, δN★ ~ 1.4 (again bottom-left corner)

The two grids are adjacent in parameter space and point to the same region.

### 4.2 Threshold ratio

Along the minimum-action locus, the ratio δN★/ΔN ~ 0.55–0.65 is simply the
threshold ratio — the locus runs along the collapse boundary, not at some
preferred interior point.

### 4.3 Mass independence of the locus

The minimum-action locus in (δN★, ΔN) space is **independent of the target mass**
(confirmed across K = 23, 33, 43, 53). The mass is absorbed entirely into
N_final = K − ΔN − δN★.

### 4.4 Physical interpretation

Narrower perturbations (smaller ΔN, smaller δN★) are cheaper because S_MSR
scales steeply with δN★. The apparent benefit of broader perturbations (larger ΔN
is "cheaper per e-fold") is overwhelmed by the absolute cost of the larger δN★
required to maintain collapse. At fixed K, increasing ΔN also forces N_final down,
removing any trajectory-length benefit.

### 4.5 Practical implication

The optimal strategy for forming a PBH of mass M is:
1. Choose (ΔN, δN★) just above the threshold, as small as possible.
   In the δN★ < 1 regime: ΔN ~ 1.8, δN★ ~ 1 (constrained by threshold).
   At larger δN★: ΔN ~ 2–3, δN★ ~ 1.4 appear to be the min-action point
   within the sampled range, but the true minimum may sit at even smaller values.
2. Set N_final = K − ΔN − δN★ to achieve the target mass.

---

## 5. r_max vs r_peak divergence (compaction function bugfix)

The recomputed Phase A grid (with compaction function bugfix) reveals significant
divergence between r_max (outermost r where C ≥ 0.4) and r_peak (argmax of C(r))
in 289/841 formed points.

### 5.1 Where divergence occurs

Divergence is controlled by the ratio ΔN/δN★:

- **ΔN/δN★ ≳ 0.45**: r_max ≈ r_peak (C(r) has a single peak that coincides with the threshold crossing)
- **ΔN/δN★ ≲ 0.45**: r_max >> r_peak, with log₁₀(r_max/r_peak) up to ~11 and log₁₀(M_max/M_peak) up to ~22

The diverged region corresponds to large δN★, small ΔN — profiles with a tall,
narrow central spike sitting on a broad, shallow base.

### 5.2 Physical interpretation

In the diverged regime, C(r) peaks sharply near the centre, falls below threshold,
then rises again at the outer scale. r_max picks up the outer crossing; r_peak
picks up the central spike. Physically, the central spike is expected to collapse
first and independently, making M_peak the more appropriate mass estimate.
M_max in this regime is likely a large overestimate.

### 5.3 Impact on earlier conclusions

The minimum-action grids (fixed-K, δN★ ≤ 1) are **entirely unaffected** — zero
diverged points in any of the four K values, because δN★ is too small to produce
a strong central spike. The M_peak = M_max identification holds throughout the
minimum-action analysis. The divergence only matters for the large-δN★, small-ΔN
regime which is far from the minimum-action locus.

---

## 6. Connection to Vennin et al. spectral formalism

### 6.1 Standard Vennin formalism

Vennin et al. solve for Q_φ(K) — the probability density of accumulating K total
e-folds starting from field value φ — with boundary condition Q_φ(K) = δ(K) at
φ = φ_0. This makes Q a density in K with φ a parameter. It sums over **all**
noise histories consistent with K extra e-folds, including all instanton paths and
all non-instanton paths.

### 6.2 Mapping to our formalism

- φ fixes N_init
- K = N_init + δN★, so fixing φ and K fixes δN★
- Q_φ(K) sums over all instantons at fixed (N_init, δN★) with varying N_final
  (i.e. varying ΔN), plus non-instanton histories

### 6.3 The mass-fixed question

To compute the formation probability at fixed PBH mass, one needs to integrate
Q_φ(K) over φ. But Q_φ(K) is a density in K, not in φ, making this integral
ill-defined without a measure on φ.

### 6.4 Proposed reformulation

Solving the **backwards Kolmogorov equation**:

$$\frac{\partial Q}{\partial K} = -v(\phi)\frac{\partial Q}{\partial \phi} + \frac{1}{2}\sigma^2(\phi)\frac{\partial^2 Q}{\partial \phi^2}$$

with boundary condition Q(φ; K=0) = δ(φ − φ_0) yields Q as a density in φ
with K a parameter. This is the adjoint problem, known since at least
Starobinsky & Yokoyama and used in the stochastic δN literature, but not
(to our knowledge) explicitly deployed for the mass-fixed PBH formation question.

Integrating this Q(φ; K(M)) over φ gives a quantity directly comparable to
our sum over instantons at fixed mass:

$$P(M_\mathrm{PBH}) \propto \int d\phi\; Q(\phi;\, K(M)) \times [\text{collapse criterion}]$$

### 6.5 Key comparison

The saddle-point approximation of the φ integral recovers the instanton sum,
with S_MSR playing the role of the effective action. The discrepancy between
the full Q integral and the instanton approximation would quantify when the
saddle-point approximation breaks down — i.e. when fluctuations around the
dominant instanton, or competing saddle points, contribute significantly.

This comparison does not appear to have been made explicitly in the literature,
and would constitute a concrete bridge between the MSR/instanton and
Kolmogorov/spectral approaches.

---

## 7. Open questions

- **Which mass estimate is correct at large δN★?** M_peak is physically motivated
  in the diverged regime (ΔN/δN★ < 0.45) but NR confirmation is needed.
  Contact Sam Young.

- **True minimum-action point at small (ΔN, δN★).** The min-S locus sits at the
  bottom-left corner of every grid we've run. A grid explicitly targeting
  ΔN ∈ [0.01, 0.5], δN★ ∈ [0.05, 0.5] would pin down whether the minimum
  continues to the threshold at arbitrarily small (ΔN, δN★) or whether there
  is a floor set by the validity of the instanton approximation.

- **Vennin comparison.** Solving the backwards Kolmogorov equation for Q(φ; K)
  and comparing the φ-integral to our instanton sum at fixed K. Tractable
  numerically for the quadratic potential; possibly semi-analytic via the
  existing spectral decomposition.

- **Validity of the saddle-point approximation.** The ratio of the fluctuation
  determinant to e^{−S_MSR} determines whether the instanton dominates Q.
  Not yet assessed.

- **Vennin asymptotic exponent.** Whether S_MSR ~ δN★ (exponent 1) is reached
  at δN★ >> ΔN remains open. Phase A results suggest the asymptote for the
  quadratic potential lies above 1 in the physically accessible regime.

- **FullHankelDiffusion, ρ_final BC, Ezquiaga–GBV eigenvalue comparison.**
  All deferred from previous sessions.
