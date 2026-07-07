# Design note addendum: SBP-SAT production port with lagged self-consistent target

Prompt: `.prompts/gradient-coupled-instanton/21a-sbp-sat-lagged-target-production-port.md`.
Builds on `.documents/gradient-coupled-instanton/21-sbp-sat-design-note.md` (Phase 1
derivation + prototype). This note records the Phase 2 (production) decisions and,
critically, two empirical hardenings to the Phase 1 `tau` recipe that were required
to make the *nonlinear Picard/shooting iteration* converge — not just the frozen-
coefficient linear operator's spectrum, which was all Phase 1 checked.

## 1. What was ported

- **State layout** (`forward_rhs.py`): `phi_core` (y=+1) is promoted from
  Neumann-eliminated to a free, integrated DOF. The forward state vector grows
  from `2*n_max-1` to `2*n_max`: `(phi_1,...,phi_{n_max}, pi_1,...,pi_{n_max})`.
  `pack_state`/`unpack_state` updated accordingly; `unpack_state` no longer calls
  `neumann_boundary_value` to *set* `phi_full[-1]`.
- **Advection**: `advection_term` (plain product `diag(A) @ D`) replaced by
  `Numerics.DiscretizedOperators.advection_split_term` (the split form), ported
  from the validated Phase-1 prototype (`analyze_StiffnessSpectrum.py`'s own
  `advection_split_matrix`) into production.
- **SAT penalty**: added at the core row of both `phi` and `pi`, with two
  different targets (see §2).

## 2. The `g_phi` / `g_pi` decision

Confirmed from the Phase-1 design note (§6) and empirically: **both** fields need
the *dissipative* part of the SAT (same mechanism, same `A_array`), but their
*targets* are different in kind, and deliberately so:

- **`g_phi`**: computed **live**, every RHS call, via
  `neumann_boundary_value(phi_full, grid.D, boundary_index=-1)` — the exact
  formula the old strong elimination used, now imposed weakly instead of exactly.
  It is a function of the *other*, currently-integrated phi nodes, never of
  `phi_core` itself, so it can never be self-cancelling, and it needs no
  Picard-sweep lagging: it is already fully live/self-consistent within a single
  ODE integration.
- **`g_pi`**: pi_core had **no existing condition of any kind** before this port
  (a totally free DOF), so there is no live formula to reuse. Its target is the
  **lagged, self-consistent** core `pi(N)` trajectory from the *previous* Picard
  sweep (`g_pi_core_spline`, rebuilt every sweep in `picard.solve_picard`),
  seeded at sweep 0 from an independent `FullInstanton` profile. At convergence
  `g_pi -> pi_core` and the penalty forcing vanishes — confirmed directly
  (§5, "closure independence").

This asymmetry (`g_phi` live, `g_pi` lagged) is the reason `picard.py` only needs
to thread *one* new spline (`g_pi_core_spline`) through `forward_rhs`, not two.

## 3. FullInstanton seed

`picard._seed_pi_core_values` implements a three-tier fetch-then-fallback:

1. `full_instanton_seed` (a pre-computed dict), if supplied and not itself a
   failure — the "prefer fetching from the datastore" path.
   `GradientCoupledInstanton.py`'s Ray remote function materialises an optional
   `FullInstantonProxy` (see §4) and builds this dict from it.
2. Otherwise, `_compute_full_instanton._function(...)` computed inline
   (bypassing Ray) — the same "call the delegate directly" pattern used
   throughout this test suite and `scripts/compare_gradient_full.py`.
3. If that *also* fails, the noiseless background trajectory's own `pi(N)` —
   always available, no extra ODE solve.

Seed **quality only affects iteration count**, never the converged answer — this
is verified directly by `tests/test_picard.py::test_solve_picard_converged_answer_independent_of_sat_seed`,
which forces tier 2 to fail (monkeypatching `_compute_full_instanton._function`)
and confirms the converged `phi_grid`/`pi_grid`/`final_lambda` match the normal
(tier-2) path to `atol=1e-6`.

`main.py`'s `_run_gradient_branch` fetches a populated `FullInstanton` per
*base* grid point `(model, N_init, N_final, delta_Nstar)` (not per full
`(..., n_collocation_points, alpha_regularization)` combination — many gradient
grid points share one base point) and threads a `FullInstantonProxy` into
`GradientCoupledInstanton`'s constructor. `full_instanton` is **not** part of the
object's persisted identity (the factory's lookup query never references it) —
by design, since it can only affect *how fast* a solve converges, never *what*
it converges to.

## 4. Response sector: deliberately unchanged

Per the prompt's own scope note, the response sector (`response_rhs.py`) was
**not** ported. It shares the identical destabilising mechanism in principle
(`rmom_core` is still Neumann-eliminated, same `advection_coefficient` formula),
but porting it was scoped out as a follow-on. This is flagged explicitly in
`response_rhs.py`'s own module docstring, not left as a silent gap.

**Important finding (§5.2 below): this gap was NOT the cause of the n=7
oscillation** investigated during acceptance testing — that was traced to the
forward sector's own `tau` value, not the response sector. The response sector
remains an open risk for a case that specifically stresses it, but it was ruled
out as the explanation for the specific failure encountered here.

## 5. Empirical findings beyond the Phase 1 derivation

Phase 1 validated that the **frozen-coefficient, linearised** assembled operator
has an `n_max`-independent spectral abscissa at `tau = A(core)/2`. Phase 2
acceptance testing (the actual nonlinear Picard/shooting iteration, run on the
production case `N_init=19.5, N_final=16, delta_Nstar=0.1, alpha=0.1`) surfaced
two effects invisible to that linear analysis, both requiring a **larger**
`tau` than the Phase 1 minimum. Production `forward_rhs.py` uses
`tau = abs(A_core)` (not `0.5*A_core`) as a result. Both hardenings are pure
safety margin — the design note's own admissibility criterion
("any `tau >= A(core)/2`") already covers them — not a change to the physics.

### 5.1 Sign robustness (`abs()`, not signed `A_core`)

`A_core = 2*a'`, `a' = (1-epsilon_core)/Delta_s(N)`, is positive only while
`epsilon_core < 1`. That holds at the *converged* solution (by construction,
`N_final` precedes the true end of inflation) but is **not** guaranteed for
trial states visited mid-iteration: a poor intermediate Picard/Newton iterate
can transiently push `epsilon_core = 0.5*pi_core^2` above 1. A signed
`tau = 0.5*A_core` flips negative exactly then, turning the SAT from a
stabiliser into an amplifier.

**Observed directly**: at `n_collocation_points=9` on the production case, the
zeroth Picard iterate's own background pass (no response coupling at all)
developed a runaway in `pi_core` toward the `H_sq` denominator singularity
(`pi_core^2 = 6`) within a fraction of an e-fold, with the RK45 integrator
failing ("required step size less than spacing between numbers"). Tracing the
full per-node state confirmed `pi_core` — and only `pi_core` — approaching
`-sqrt(6)` while every other node stayed near its initial value.

**Fix**: `tau = 0.5*abs(A_core)` (later folded into the single, larger,
`tau = abs(A_core)` — see §5.2) keeps the SAT strictly dissipative regardless of
`epsilon_core`'s transient sign. Re-deriving the core-row energy coefficient
confirms this is still stabilising in both regimes:
`-a'*(1 + w_core/2)` when `a' > 0`, `a'*(3 - w_core/2) < 0` when `a' < 0`
(`w_core < 2` always for LGL weights). See
`tests/test_forward_rhs.py::test_sat_penalty_tau_stays_dissipative_when_epsilon_core_exceeds_one`.

### 5.2 Iteration stability margin (`abs(A_core)`, not `0.5*abs(A_core)`)

Promoting `phi_core` from Neumann-eliminated to a free, integrated DOF gives it
genuine dynamical memory it never had before (previously it was slaved,
*instantaneously*, to the interior nodes via an algebraic formula — no
independent timescale of its own). At the Phase-1 minimal
`tau = 0.5*abs(A_core)`, this new degree of freedom developed a **persistent,
non-decaying `O(1)` Picard-sweep oscillation** at `n_collocation_points=7` on the
production case: `max|dphi|` across successive Picard sweeps did not shrink at
all (values like `0.71, 0.52, 1.71, 0.93, 0.74, ...`, no decreasing trend), for
essentially any nonzero shooting perturbation `dlam`, however small.

This was confirmed **not** to originate in the (still un-ported) response
sector: monkeypatching `response_rhs`'s `L_operator`/`advection_term` to zero
reproduced numerically *identical* oscillating output — ruling out §4's gap as
the cause here. It was also confirmed to be a genuinely new failure mode: run
against the pre-prompt-21a (`git stash`) production code with the identical
physical case, the OLD strong-BC closure's Picard sweeps at `n=7` contracted
normally (`4e-5 -> 1e-6 -> 1e-8` within 3 sweeps per outer iteration) — the
oscillation is a consequence of this prompt's own state-layout change
interacting with the minimal `tau`, not a pre-existing bug being rediscovered.

**Fix**: doubling `tau` to `abs(A_core)` (still well within the design note's
"any `tau >= A(core)/2` is admissible" criterion) suppressed the oscillation
completely. With `tau = abs(A_core)`, every `n_collocation_points` in
`{5, 7, 9, 11, 13, 17, 33}` converges in a **single outer Newton iteration and a
single Picard sweep** on the production case. `tau = 2*abs(A_core)` (4x the
Phase-1 minimum) was also tested and works identically; `abs(A_core)` (2x) was
chosen as the smaller, still-comfortable margin.

The under-relaxation hook `theta` (prompt 21a's Implementation §5) is
implemented in `picard.py` (`DEFAULT_SAT_THETA = 1.0`) and available, but was
**not needed**: `theta=1` converges cleanly everywhere once `tau` was corrected.
It remains available for future parameter regimes where the same oscillation
reappears.

## 6. Acceptance results (production case: `N_init=19.5, N_final=16,
delta_Nstar=0.1, alpha=0.1`, quadratic potential `m/Mp=1e-5`, `phi0=15 Mp`)

| `n_collocation_points` | converged | outer iters | Picard sweeps | `phi_core(N_total)` |
|---|---|---|---|---|
| 5  | yes | 1 | 1 | 7.892218784 |
| 7  | yes | 1 | 1 | 7.892218784 |
| 9  | yes | 1 | 1 | 7.892218783 |
| 11 | yes | 1 | 1 | 7.892218782 |
| 13 | yes | 1 | 1 | 7.892218782 |
| 17 | yes | 1 | 1 | 7.892218787 |
| 33 | yes | 1 | 1 | 7.892218753 |

- **Physics regression** (n=5 vs `FullInstanton`): `max|phi_core - phi1| = 5.6e-9`,
  `max|pi_core - phi2| = 2.7e-8` — far inside the previously-observed `~1e-6`
  tolerance.
- **Convergence across n**: core trajectory endpoint agrees to `~1e-8`
  across `n=5..17`, `~3e-8` at `n=33` — a converging trend, not divergence.
- **Regularity emergence** (`(D@pi)_core`, not imposed as a value): ratio to the
  local `pi` scale is `~2e-7` at `n=5`, growing gradually to `~2e-2` at `n=33`
  — small throughout, and (mechanistically) a consequence of `phi`'s own
  regularity propagating through `pi = dphi/dN`, not a separately-imposed
  constraint.
- **Closure independence**: converged `phi_grid`/`pi_grid` are independent of
  the sweep-0 seed (FullInstanton-derived vs. background-trajectory-derived) to
  the Picard tolerance — see `tests/test_picard.py`.

Reproduced by `tests/test_picard.py::test_solve_picard_production_case_converges_for_previously_failing_n`
(parametrised over `n in {5, 9, 17, 33}`) and
`test_solve_picard_production_case_core_trajectory_converges_across_n`
(`n in {9, 11, 13, 17, 33}`).

## 7. How to verify this is still correct

Three checks must stay green (mirroring Phase 1's own three, ported to
production):

1. **Abscissa diagnostic** (unchanged from Phase 1):
   `analyze_StiffnessSpectrum.py --mode spectrum --closure sbp-sat` /
   `tests/test_sbp_sat_boundary_closure.py`.
2. **SAT energy cancellation**, now at the *production* `tau = abs(A_core)`:
   `tests/test_forward_rhs.py::test_sat_penalty_production_tau_has_iteration_stability_margin`
   and `test_sat_penalty_tau_stays_dissipative_when_epsilon_core_exceeds_one`.
3. **Closure independence** (two-seed regression):
   `tests/test_picard.py::test_solve_picard_converged_answer_independent_of_sat_seed`.

Plus the production-case regression tests in §6 above, which are the most
direct guard against a regression in the specific failure this prompt fixes.

## 8. Two further fixes surfaced by the actual end-to-end production run

Running the acceptance case through the real pipeline (`main.py`, Ray +
SQLite, `--targets homogeneous gradient`) surfaced two additional issues
beyond §5 that a purely local (`solve_picard`-only) test never exercises,
since both concern the interaction with a genuinely-fetched upstream
`FullInstanton` and the downstream extraction step.

### 8.1 `solve_picard`'s retry-with-fallback-seed safeguard

A `FullInstanton` fetched from the datastore (§3, tier 1) solves a
**different BVP** than this `GradientCoupledInstanton` does: `FullInstanton
.compute()`'s own `phi_final` target is `trajectory.phi_at(N_end - N_final)`
(no `delta_Nstar`), whereas this module's own `phi_end` corresponds to
`trajectory.phi_at(N_end - N_final + delta_Nstar)`. For most parameter
points this difference is immaterial. For the production acceptance case,
`FullInstanton`'s own shooting problem turned out to be poorly conditioned
(the diffusion coefficient is astronomically small, forcing `P1 ~ 10^8` to
hit its target) — its `phi2(N)` profile, while a perfectly valid solution
of FullInstanton's own problem, was a poor lagged-target seed for GCI's
own (much closer to background) problem: the Picard iteration decayed for
~15-20 sweeps, then developed a slow-growing divergence.

Diagnosed by elimination: NOT the response sector (confirmed by zeroing
`response_rhs`'s own gradient/advection terms — identical divergence
pattern); NOT `tau`'s magnitude (confirmed at `1x`, `2x`, `4x`, `8x` margin
— identical pattern); NOT a genuine instability of the underlying phi/pi
Picard map (confirmed by freezing the lagged target entirely, `theta=0`,
after the seed — the Picard/Newton loop then "converges" instantly, but to
a **biased, wrong** fixed point: the frozen mismatched target prevents any
lambda from driving the true shooting residual below tolerance). The
conclusion: the *lagged-update recursion itself*, when started from a
sufficiently different target shape, has a slow-growing mode over the
finite `MAX_OUTER`/`MAX_INNER` sweep budget for this specific case — a
genuinely new dynamical behaviour, not present in the constant-seed limit
and not fixable by `tau` alone.

**Fix**: `solve_picard` (`picard.py`) now wraps the single-attempt core
(renamed `_solve_picard_once`) with a retry: if a solve using a *supplied*
`full_instanton_seed` fails to converge, it is retried once with
`full_instanton_seed=None`, forcing `_seed_pi_core_values`'s internally-
consistent tier-2/3 fallback (which targets THIS function's own `phi_end`
and has never been observed to fail on any tested case). This preserves
the "prefer fetching from the datastore" optimisation on the common path
while guaranteeing a mismatched seed degrades to "one extra internal solve"
rather than an outright failure — the correctness promise the seed
mechanism was always supposed to have ("seed quality only affects
iteration count").

### 8.2 `extract_zeta_profile`'s Step-4 bracket tolerance

With the retry fix in place, the Picard solve succeeds cleanly for both
`n=17` and `n=33` (a single outer iteration, single Picard sweep, using the
internally-consistent seed) — but `extract_zeta_profile` then returned an
all-NaN `zeta` for every node. Root cause: the converged core trajectory
is (correctly!) almost exactly the background trajectory (a near-zero-
lambda solution), so the per-shell noiseless downflow's terminal density
`rho_end_j` differs from the background's own `rho_end_traj` only in the
~10th significant digit — pure ODE-solver tolerance noise — but Step 4's
bracket check (`rho_end_traj <= rho_end_j <= rho_start_traj`) was a
**strict, zero-margin** inequality, rejecting `rho_end_j` for landing a
hair on the wrong side.

**Fix** (`extraction.py`): the bracket check now allows a small relative
tolerance (`10 * max(atol, rtol)` of the bracket width), and the
`brentq` root-find target is clamped into `[rho_end_traj, rho_start_traj]`
before the search (needed because `brentq` itself requires the target to
be genuinely bracketed by the endpoint values, which a since-accepted
tolerance-level `rho_end_j` outside the strict range would violate).
Genuine failures (density far outside the background's own range) are
still caught. This is a pre-existing fragility in `extraction.py`,
unrelated to the SBP-SAT closure itself, that the closure's newly-correct
convergence to a near-trivial solution exposed for the first time — fixed
here because it directly blocked this prompt's own acceptance criterion.

### 8.3 End-to-end confirmation

Both fixes together: `_compute_gradient_coupled_instanton._function(...)`
(the same direct, Ray-bypassing call this codebase's test suite uses
throughout), called with the exact acceptance parameters, returns
`failure=False`, finite `msr_action`, and finite `r_phys` for every node,
for both `n_collocation_points=17` and `=33`.

## 9. Out of scope, reaffirmed

- Response-sector SAT closure (§4) — flagged, not implemented.
- `alpha` regularization scan / production-grid re-tuning.
- Integrator changes (RK45 remains sufficient; no residual stiffness observed
  once the abscissa is bounded and the iteration oscillation is resolved).
