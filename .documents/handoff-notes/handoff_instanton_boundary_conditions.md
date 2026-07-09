# Hand-off document: `FullInstanton` boundary conditions and post-instanton matching

**Date:** June 2026  
**Prepared by:** David Seery and Claude (Sonnet 4.6)  
**Purpose:** Continuation context for a new conversation about `FullInstanton`
boundary condition physics and the gluing of the instanton onto subsequent
inflationary evolution.

---

## 1. Codebase state at hand-off

The following prompts have been generated (in `.prompts/`) and applied in order:

| File                            | Status  | Summary                                                                                                                                                                                                                                                                                                                 |
|---------------------------------|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `02-fullinstanton-bcs.md`       | Applied | Extract noiseless ODE to `InflationConcepts/noiseless_equations.py`; add `rho_at()` to `InflatonTrajectory`; add `drho_dphi()`, `drho_dpi()` to `AbstractPotential`; rename `pi_SR_init → pi_init` in `FullInstanton` so the initial momentum is read from the noiseless trajectory rather than slow-roll approximation |
| `02a-implement-jacobian.md`     | Applied | Attempt to change final boundary condition from `phi_final` to `rho_final`; add two-component Newton Jacobian using `drho_dphi` and `drho_dpi`. **Not converging — see §3.**                                                                                                                                            |
| `03-compaction-function.md`     | Applied | Reverts `rho_final` BC back to `phi_final`; adds `CosmologicalParams` domain object and factory; implements `CompactionFunction` compute target                                                                                                                                                                         |
| `04-orchestrate-compactions.md` | Applied | Adds Stage 4 to `main.py` orchestration pipeline                                                                                                                                                                                                                                                                        |

**Key files added or changed:**

- `InflationConcepts/noiseless_equations.py` — new; contains `noiseless_rhs`,
  `end_of_inflation_event`, `integrate_noiseless_trajectory`
- `ComputeTargets/InflatonTrajectory.py` — added `rho_at(N)` interpolation method
- `CosmologyConcepts/Potentials/AbstractPotential.py` — added `drho_dphi(phi, pi)`
  and `drho_dpi(phi, pi)` as concrete methods
- `ComputeTargets/FullInstanton.py` — `pi_SR_init` renamed `pi_init` throughout;
  `pi_init` now read from noiseless trajectory via `traj.pi_at()`; currently
  still using `phi_final` as the final BC (the `rho_final` attempt was
  reverted); enhanced diagnostic print showing `phi1(T)`, `phi2(T)`, `rho(T)`

---

## 2. Resolved design decisions

These should not be reopened without a strong physics reason.

### 2.1 Scale matching equation

Derived from Leach & Liddle (astro-ph/0305263) Eq. (2), assuming instantaneous
reheating:

```
ln(k / Mpc^-1) = -N(k)
               + ln(Mpc * Mp)
               + ln(T_CMB / Mp)
               + (1/4) * ln(pi^2 / 135)
               + (1/4) * ln( V_k / (V_end_downflow * (1 - epsilon_k/3)) )
```

where:

- `N(k)` = e-folds before end of inflation at horizon crossing (positive)
- `V_k` = potential at horizon crossing in working units
- `epsilon_k` = slow-roll parameter at horizon crossing
- `V_end_downflow` = potential at `epsilon=1` along the **downflow trajectory**
  from the instanton endpoint (not the noiseless background; see §2.3)
- All dimensional quantities in working units from `potential._units`
- `T_CMB = cosmo.T_CMB_Kelvin * units.Kelvin`

The `pi^2/135` prefactor comes from: entropy conservation gives `pi^2/30` from
the Stefan-Boltzmann relation, combined with `1/3` from the Friedmann equation
(`H^2 = V / (3Mp^2 * (1 - epsilon/3))`) when rewriting in terms of `V_end`
using `epsilon=1` at end of inflation (`rho_end = (3/2) V_end`).

A `g_star` correction of `(1/3) * ln(g_star_s_0 / g_star_reh)` was discussed
and found to be `~0.2` in `ln k`, which is within the uncertainty of the
instantaneous reheating approximation. It has been **omitted** from the
formula for simplicity. It can be added later if needed.

### 2.2 δN computed to constant-ρ surface

The separate-universe formula requires `zeta = delta N` measured to a surface
of **constant energy density**, not constant field value. At each instanton
sample point, find `N_background` by inverting `rho_noiseless(N) = rho_instanton`
via bisection on the noiseless `InflatonTrajectory`. Under slow roll this makes
essentially no difference; away from slow roll it is the correct prescription.

### 2.3 Downflow trajectory from instanton endpoint

After the instanton ends at `(phi_final, pi_final)`, the field is generically
off the slow-roll attractor. The post-instanton evolution must be integrated
forward from `(phi_final, pi_final)` using `integrate_noiseless_trajectory`
until `epsilon = 1`. This:

- Gives the correct `V_end_downflow` for the scale matching equation (which
  may differ from the noiseless background `V_end` — this is a real isocurvature
  effect, not a gauge artifact)
- Gives the correct `N_end_downflow` (additional e-folds from instanton
  endpoint to end of inflation)
- Allows the scale assignment `N_before_end_i = N_end_downflow + (N_total - N_inst_i)`
  to be computed for each instanton sample point

Under slow roll the downflow trajectory rapidly converges to the noiseless
background. For `FullInstanton` with significant off-attractor momentum at the
endpoint, the difference is physically meaningful.

### 2.4 Spherical symmetry of the density profile

The most probable extreme fluctuation is spherically symmetric because spatial
gradients contribute `(∇φ)^2` terms to the MSR action, introducing a
probability cost. The instanton computed by the code is the spherically
symmetric saddle. The spatial profile extracted from it is therefore the
radial profile of a monopole fluctuation.

### 2.5 Latest horizon exit rule

If the instanton trajectory causes a scale to exit and re-enter the Hubble
radius (possible if `H` is non-monotonic near a feature), the perturbation
at that scale is overwritten at re-entry. The relevant `zeta` is that computed
at the **last** horizon exit — i.e. the smallest `N_before_end` seen for that
scale when scanning from the instanton start toward its end.

### 2.6 CompactionFunction architecture

- Four-part pattern: `@ray.remote` function → `CompactionFunctionValue` →
  `CompactionFunction` → `CompactionFunctionProxy`
- Accepts optional `FullInstanton` and/or `SlowRollInstanton`; at least one
  must be non-None
- Computes `C(r)` via Raatikainen et al. (2025) Eq. (2.12):
  `C(r) = (2/3) * (1 - (1 + r*zeta')^2)`
- Computes `C_bar(r)` via Raatikainen et al. (2025) Eq. (2.13) second equality,
  numerically integrated on a dense grid; extrapolated as `C_bar ~ 1/r^3`
  beyond the last sample point
- Collapse threshold: `C_bar_threshold = 0.4` (shape-independent); `C_threshold
  = 0.4` for `C(r)` comparison
- PBH mass from Tomberg (arXiv:2510.09303) Eq. (2.17):
  `M = (1 + C_max) * 5.6e15 * (k_star * r_max)^2 * M_sun`
  where `k_star = 0.05 Mpc^-1`
- Sharding key: `delta_Nstar`
- `CosmologicalParams` recorded as a normalized FK in the datastore

---

## 3. Open physics question: the `rho_final` boundary condition failure

### 3.1 What was attempted

The physically correct final boundary condition for the instanton is that the
energy density at the endpoint matches the noiseless background:

```
rho(phi1(N_total), phi2(N_total)) = rho_noiseless(N_end - N_final)
```

This was implemented by changing the outer Newton loop to target `rho_final`
instead of `phi_final`. The Jacobian was computed via the chain rule:

```
dres/dlam = (drho/dphi1) * (dphi1/dlam) + (drho/dphi2) * (dphi2/dlam)
```

where `drho/dphi1` and `drho/dphi2` are computed analytically from
`AbstractPotential.drho_dphi()` and `AbstractPotential.drho_dpi()`, and
`dphi1/dlam`, `dphi2/dlam` are finite-differenced from the perturbed Picard
solve already done for the Newton step.

### 3.2 What happened

The iteration did not converge. `rho(T)` barely changed across 50 outer
iterations for `dNstar=0.1`, and converged to within only 1–10% of `rho_final`
for larger `dNstar`. The residual was essentially flat across iterations.

### 3.3 Diagnosis

Tuning `lambda = P1(N_total)` traces a one-parameter family of endpoints
`(phi1(N_total; lambda), phi2(N_total; lambda))`. The constraint
`rho = const` is a curve in `(phi1, phi2)` space. **These two curves may not
intersect**, meaning there may be no choice of `lambda` that simultaneously
satisfies the `rho_final` condition with the given `N_total`.

This is not necessarily a numerical failure. It may reflect a genuine physical
constraint: the noise realization encoded in the instanton (through `P1`)
cannot simultaneously deliver the field to the required density surface given
the fixed total duration `N_total = (N_init - N_final) + delta_Nstar`.

### 3.4 Physical interpretation (open question)

Two interpretations are possible:

**Interpretation A: genuine physical constraint.** For a given `delta_Nstar`,
there are transitions that cannot be described as instantons with the current
single-field noise model — they require a different noise realization or a
different `N_total`. This would mean those transitions are super-exponentially
suppressed (no saddle-point contribution), which is surprising on physical
grounds since any transition should in principle be describable by *some* noise
history.

**Interpretation B: artefact of the single-Lagrange-multiplier setup.** With
one free parameter `lambda`, we can satisfy one scalar condition at the
endpoint. The `phi_final` condition is satisfied reliably. The `rho_final`
condition is not, because `rho` depends on both `phi1` and `phi2`, and the
one-parameter family traced by `lambda` does not generically intersect the
constant-`rho` surface.

In the multi-field case this distinction becomes sharper: the constant-`rho`
surface is codimension-1 in the full `(phi^i, pi^i)` field space, and with one
`lambda` per field we might expect to be able to satisfy it — but the instanton
equations couple the fields, so it is not obvious.

**The question for next conversation:** is Interpretation A or B correct? And
if B, what is the right way to add the additional degree of freedom needed
to impose `rho_final`? Candidates:

- Allow `N_total` to float (so `delta_Nstar` becomes an output rather than
  an input) — but this inverts the scan parameter
- Add a second Lagrange multiplier constraining `phi2` at the endpoint,
  paired with the `rho_final` condition — but this requires a structural
  change to the Picard BVP formulation
- Accept `phi_final` as the boundary condition and compute `delta_Nstar`
  self-consistently from the endpoint `rho` — scan over `phi_final` instead
  of `delta_Nstar`

### 3.5 Current state

The `rho_final` attempt has been **reverted**. The codebase currently uses
`phi_final` as the final boundary condition, which converges reliably. The
momentum mismatch `pi_final ≠ pi_SR(phi_final)` is accepted and handled
correctly by the downflow trajectory integration in `CompactionFunction`.

---

## 4. Open implementation question: `phi_final` vs `rho_final` for scale matching

With `phi_final` as the boundary condition, the instanton endpoint satisfies
`phi1(N_total) = phi_final` exactly but `rho(phi1, phi2)` at the endpoint will
not precisely equal `rho_noiseless(N_end - N_final)`. The discrepancy is a
momentum mismatch: `phi2(N_total) ≠ pi_SR(phi_final)`.

For the `CompactionFunction` computation this is handled correctly:

- The downflow trajectory is integrated from the actual `(phi_final, phi2(N_total))`
- `V_end_downflow` is computed from that trajectory, not the noiseless background
- The δN calculation uses `rho_at()` bisection on the noiseless trajectory

The residual question is whether the `phi_final` BC introduces a small but
systematic error in `delta_Nstar` as defined. With `phi_final` BC, `delta_Nstar`
is an input that sets `N_total`, but the actual excess e-folds (measured to
constant-`rho`) may differ slightly. This is a post-processing correction that
can be computed from the converged instanton without changing the BC.

---

## 5. Key literature references

| Reference                                    | Role                              |
|----------------------------------------------|-----------------------------------|
| Leach & Liddle, astro-ph/0305263, Eq. (2)    | Scale matching equation           |
| Raatikainen et al. (2025), Eq. (2.12)–(2.13) | `C(r)` and `C_bar(r)` definitions |
| Tomberg, arXiv:2510.09303, Eq. (2.17)        | PBH mass formula                  |
| Musco & Miller (2005); Musco (2019)          | PBH collapse threshold background |

---

## 6. Architectural invariants (do not violate)

- **Single source of truth for the noiseless ODE**: `InflationConcepts/noiseless_equations.py`
  only. No other file may define `dφ/dN` or `dπ/dN`.
- **`FullInstanton` does not import `noiseless_equations`**: it receives a
  pre-computed `InflatonTrajectoryProxy` and reads boundary values from it.
  The downflow integration lives in `CompactionFunction` only.
- **All unit handling via `potential._units`**: no hard-coded conversion
  constants anywhere. `Mp`, `Mpc`, `Kelvin` all from `UnitsLike`.
- **Datastore provenance**: every computed quantity records all inputs as
  normalized FK references, including `CosmologicalParams`.
- **Sharding key is `delta_Nstar`** for all instanton and compaction function
  tables.
