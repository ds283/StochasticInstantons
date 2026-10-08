# SAT closure — status, evidence, and open tests

**Date:** 10 July 2026
**Prepared by:** David Seery and Claude (Opus 4.8)
**Scope.** Everything established about the `GradientCoupledInstanton` core SAT
closure between prompts 24b and 28, including the tests that overturned earlier
readings. Companion document: `HFP-STRUCTURE-STATUS.md` (non-adjointness of the
forward/response pair, characteristic analysis of the core, `H_FP` as a
consistency test). **Neither document is self-sufficient — the central open
question requires both.**

**Status in one line.** The `n=5`/`n=7` converged solutions are shaped by an
O(1)-to-dominant spurious forcing from the core SAT penalty, are demonstrably
τ-dependent, and must be treated as *provisional*, not physics. The mechanism is
identified and quantified. The fix is not yet established.

---

## 1. The central finding, and how it arose

### 1.1 The trade that was made

The SBP-SAT closure (prompt 21) adds a dissipative penalty at the core node
`y=+1` to cancel a value-type (`∝ u_core²`) energy defect that would otherwise
produce right-half-plane eigenvalues growing as `n_max^1.6`:

```
d u_core/dN  +=  -(tau / w_core) * (u_core - g_u(N))
tau = tau_multiplier * |A_core|,   tau_multiplier = 1.0 (production)
w_core = grid.weights[-1] = 2/(n_max(n_max+1))
```

Two targets, of *different kinds*:

- **`g_phi`** — computed **live** at every RHS call from the other (non-core)
  `phi` nodes, via `neumann_boundary_value(phi_full, grid.D, -1)`. Not
  self-referential (excludes `phi_core`). Needs no lagging.
- **`g_pi`** — `pi_core` has no boundary condition in the continuum problem, so
  the design (prompt 21) made its target the **lagged, self-consistent** core
  `pi(N)` from the previous Picard sweep, seeded from `FullInstanton`.

The lagged choice was made *specifically* so that the penalty forcing vanishes at
the fixed point: `g_pi -> pi_core`, so `-(tau/w_core)(pi_core - g_pi) -> 0`, and
the converged trajectory satisfies the **unpenalised** dynamics. That is the
entire justification for the claim, still asserted in `forward_rhs.py`'s module
docstring, that *"the SAT is a stabiliser, not new physics."* The original design
even specified the acceptance check: *"the SAT penalty forcing at convergence is
at the Picard-residual level (-> 0)."*

**That check was never run on a non-trivial solution.**

Prompt 22 Finding 2 then showed the lagged iteration (`theta=1.0`) diverges under
genuine coupling; prompt 22b showed Anderson mixing floors at `~1e-4`
(`newton_krylov`-confirmed structural). Prompt 22c responded by setting
`DEFAULT_SAT_THETA=0.0`, `DEFAULT_ANDERSON_M=0`, which makes `_AndersonMixer.update()`
an exact no-op: **`g_pi_core_spline` is frozen at the `FullInstanton` seed's own
`phi2(N)` for the entire solve.**

This bought iteration stability by giving up the vanishing property that was the
closure's whole justification. The consequence was never propagated. It is the
root of everything in §2.

### 1.2 Documentation defect (fix independently of anything else)

`forward_rhs.py`'s module docstring still states that `g_pi` is *"the LAGGED,
SELF-CONSISTENT core pi(N) trajectory from the previous Picard sweep"* and that
*"At Picard convergence g_pi_core_spline(N) -> pi_core(N) exactly, so the penalty
forcing -> 0 there too."* Both clauses have been false since 22c.
`picard.py`'s docstring correctly describes the frozen target. Test A (§2.1)
measures a peak forcing of **14.9** where the `forward_rhs.py` docstring promises
zero.

This stale paragraph is the proximate cause of at least two prompts' worth of
misdirected diagnosis (25, 26). It should be corrected in its own commit,
regardless of what is decided about the closure itself.

---

## 2. Evidence

### 2.1 Test A — the penalty forcing at convergence is not small

Measured **two independent ways**, on the four converged `n=5`,
`tau_multiplier=1.0` solutions, zero new solves:

1. *Residual method*: finite-difference `d(pi_core)/dN` from the persisted grids,
   subtract every other assembled term in `dpi/dN`; the remainder is the SAT
   forcing by construction.
2. *Direct construction*: `(tau/w_core)*(pi_core(N) - g_pi(N))` with
   `g_pi = SplineWrapper(N_sample_FI, phi2_FI, 'linear', k=3)` — available at zero
   cost from the `.npz`, because `g_pi` is frozen (§1.1).

They agree to a median `|residual - direct| ~ 1e-6` against an O(1) signal. The
apparent max discrepancy (5.6–11.6%) sits at `N=0`, where the direct construction
is exactly zero (the sweep-0 seed *is* the target) and `np.gradient`'s one-sided
derivative is inaccurate. **Test A is corroborated, not single-method.**

| `δN★` | max\|penalty\| | max(\|3π\|, \|dV/H²\|) | max ratio | median ratio |
|---|---|---|---|---|
| 0.2 | 2.25 | 0.77 | 1.57 | 0.051 |
| 0.3 | 3.41 | 0.81 | 2.29 | 0.072 |
| 0.5 | 6.16 | 0.92 | 3.87 | 0.126 |
| 0.7 | 14.88 | 0.98 | 14.09 | 0.195 |

Reading:

- The penalty **dominates** `dpi_core/dN` for `N < 1` (the early transient), and
  persists at 5–20% of the background terms at late `N`. It does not vanish.
- Both peak and median grow monotonically with `δN★` — contamination is worst
  exactly at the points furthest into the non-trivial regime the campaign is built
  on.
- The forcing **rings** (sign changes over `N ≲ 1`; see
  `28-sat-penalty-forcing-magnitude-v2.png`). This settles the handoff brief's
  open question about the `phi_core`/`pi_core` oscillation. The brief's least-action
  argument was correct — noise cost `∫D r̃² dN` is positive-definite, so a genuine
  minimiser should not ring. **It doesn't. The penalty rings and drags `pi_core`
  with it.** This also explains `S_GCI/S_FI` climbing 15→38 while `E` stays flat at
  ~61: ringing cost, as the brief suspected, with the ringing term now identified.

### 2.2 The `n²` amplification

`w_core = 2/(n_max(n_max+1)) ∝ 1/n²` (confirmed numerically: `n²·w_core =
2.500, 2.333, 2.250, 2.125` at `n = 5,7,9,17`). `A_core` does not scale with `n`.
Therefore the penalty prefactor **`tau/w_core` grows as `n²`**: 3.6× from `n=5` to
`n=9`, 13.6× to `n=17`.

Consequence, stated sharply: with a target that does *not* satisfy
`g -> u_core` at the fixed point, the SAT is **not a consistent closure**. As
`n → ∞` at fixed `tau_multiplier`, `tau/w_core → ∞`, and the scheme's limit is the
*constrained* problem `pi_core ≡ g_pi` — i.e. "reproduce `FullInstanton`'s
`phi2(N)`", not the intended continuum PDE. The discretisation is fine; the
**closure is inconsistent**, and its inconsistency is amplified `∝ n²`.

This is the answer to the earlier question *"if the boundary layer matters this
much, is collocation the wrong discretization?"* — **No.** The boundary layer, of
thickness `~ w_core/tau`, is *created by the penalty*. The handoff brief's
uncomfortable corollary ("`n=5` may converge because it cannot resolve the layer")
is correct, but the layer is an artefact.

### 2.3 Diagnostic 8t — material τ-dependence (the headline classification)

`tau_multiplier ∈ {0.5, 1.0, 2.0}`, at `n=5` and `n=7`, all four `δN★`:

- `1.0` reproduces every historical result bit-for-bit (confirms prompt 27's
  `tau_multiplier` threading is a true no-op).
- `0.5` (the design note's bare admissibility floor `tau ≥ A_core/2`): at `n=5`
  converges to `msr_action` **4.7–5.7× smaller** at three points, fails at the
  fourth; `outer_iterations=1` at all three (the outer loop accepts its first
  bracket-seed evaluation — a shallow, non-generic residual landscape, not a
  well-conditioned root find). At `n=7` it fails outright at three of four points
  (`descending`, `blown-up`, `diverging`) and at `δN★=0.5` reports
  `converged=True` at `max_epsilon_core = 1.568 > 1` with `λ ≈ 0`,
  `msr_action ≈ 0.0074` — a **numerically converged non-solution** (`A_core`'s
  sign, hence the entire SAT derivation, requires `ε_core < 1`).
- `2.0`: **never converges**, anywhere, at either resolution.

This is far outside the "few-percent search-path noise" that Diagnostic 8a
established as the α-sensitivity baseline. **Classification: material
τ-dependence.** Per the design note's own admissibility claim (*"any
`tau ≥ A(core)/2` is admissible"*), a consistent closure must not behave this way.
It does, because §1.1.

*Not a coincidence:* 22c Finding 3 ("fixed-target bias, amplified not damped —
`δ=1e-3` moves `msr_action` by `1.3e-2`, a 13× amplification") is the same defect
seen from the target side rather than the multiplier side. The converged answer
depends on `(tau/w_core)·(pi_core − g_pi)`; perturbing either factor moves it.

### 2.4 Why every prior acceptance test passed

On the `δN★ = 0.1` degenerate branch (22 Finding 1: `λ = 0`, `msr_action ≡ 0`),
`pi_core` and `g_pi` *coincide* — both are the noiseless background. The penalty
forcing is identically zero, the closure looks inert, and τ-invariance holds. That
is why 21a's acceptance table (`n ∈ {5,7,...,33}` all converging in one sweep;
τ-doubling curing an `n=7` Picard oscillation) looked clean, and why none of it
transferred to the non-trivial branch. **`λ = 0` is the same trap in λ-space** —
see §3.3.

---

## 3. Tests that overturned readings (record these as contested, not settled)

### 3.1 The live-Neumann proposal, and what was actually ruled out

Claude proposed replacing the frozen `g_pi` with a **live** target
`neumann_boundary_value(pi_full, grid.D, -1)` — the exact analogue of `g_phi` —
justified by: `π ≡ ∂φ/∂N`, so `∂_y φ = 0 ∀N ⇒ ∂_y π = 0`. It would remove the
frozen target, the fixed-target bias, the τ-dependence, the `n²` amplification, and
the `FullInstanton` dependence of the SAT, all at once — and, being live, cannot
suffer 22 Finding 2's lagged-iteration divergence, the failure that forced the
freeze.

David correctly objected that a regularity condition at the core had been tested
and failed. **A prior conversation (9 July) confirms this, but for a different
construction.** What was tested and failed:

- Hard **elimination** of `pi_core` via the Neumann coefficients
  (`c = -D[-1,:]/D[-1,-1]`), across `n ∈ {7…191}`, `Δs ∈ {0.11, 0.3, 1.0, 25}`:
  **halves the abscissa, `n^1.6` growth persists.**
- Reason: the destabilising defect is **value-type** (`∝ π_core²`); a
  **derivative-type** condition cannot cancel a value-type term. Hence *"we are
  forced to a value-type penalty `−τ(π_core − g)`, which means we must select a
  value."*

**The distinction that matters — penalized quantity vs target value:**

| | penalized quantity | target value | status |
|---|---|---|---|
| Failed | `(Dπ)_core → 0` (derivative-type), or eliminate `π_core` | — | abscissa `~n^1.6` persists |
| Production `g_phi` | `φ_core` (**value-type**) | `neumann_boundary_value(φ)` (live) | **stable at all `n`** |
| Production `g_pi` | `π_core` (value-type) | frozen `FullInstanton phi2(N)` | stable, **inconsistent** |
| **Proposed** | `π_core` (**value-type**) | `neumann_boundary_value(π)` (live) | **abscissa never checked** |

The proposal is value-type. `∂(SAT)/∂π_core = −τ/w_core` exactly as for any fixed
`g`, because `neumann_boundary_value` excludes `π_core` itself (`c[-1] = 0`), so
the stabilising diagonal entry is unchanged. `g_phi` is an existence proof that
"value-type penalty toward a live regularity-extrapolated target" is stable.

The same 9 July conversation explicitly proposed testing exactly this
(*"a dissipative penalty toward the regularity-consistent value... which vanishes
at convergence for a smooth solution"*), wrote a test script with a `sat="regularity"`
mode, and — as far as the retrieved record shows — **never reported the result**.
It then moved to the lagged target. This is an open gap, not a settled negative.

One caveat carried forward from that conversation: a `π_core`-only value-SAT
reconstruction *did not* flatten the abscissa (halved growth, kept climbing),
hypothesised to be because `φ`'s own core advection term was left untreated.
Production now SATs **both** fields, so that confound is gone — but any new
abscissa check must be on the **complete two-field closure**, not `π` alone.

### 3.2 Test A2 — and why it is probably circular

A2 measured `(D@π)_core / |π_core|` on the four converged `n=5` solutions and found
it O(1) (median `0.288 → 1.165`, growing with `δN★`), nowhere near the `~2e-7`
scale quoted on the degenerate branch. It concluded that π does **not** already
satisfy the regularity relation, so live-Neumann would be "a genuine physics
change, not a bias-removing simplification."

**Claude's dissent, recorded for the synthesis.** Those solutions were produced by
a dynamics containing (Test A) an O(1)-to-dominant forcing that drives `π_core`
toward `FullInstanton`'s `phi2(N)` — a profile from a model with *no core*, and
with no reason whatsoever to be regular there. A2 therefore measures the regularity
of a solution that was actively forced away from regularity. The tell: A2's
violation grows monotonically with `δN★` in lockstep with Test A's penalty ratios
(`0.051→0.195` vs `0.288→1.165`). Plausibly the same curve. A2 may be measuring the
contamination, not the physics.

The continuum argument (`π ≡ ∂φ/∂N`) is untouched by A2. A converged discrete
solution violating it indicates the solution has been pushed off the continuum
manifold, not that the relation is false.

**A2 is not dispositive either way until the φ-control in §4.1 is run.**

### 3.3 Test D — falsified Claude's λ-independence hypothesis, but see the caveat

Claude hypothesised: if the closure alone breaks the inner Picard map at `n≥9`,
it should fail even at `λ=0`, where the noise source `D11·λ·r̃` vanishes
identically. Stated criterion: *"if it converges cleanly at λ=0 and only fails at
finite λ, my reading is wrong."*

Result: **converges cleanly at `λ=0` at `n ∈ {5,7,9,17}`**, with near
resolution-independent residual (`−0.122 → −0.121 → −0.121 → −0.120`).
**The hypothesis as stated is falsified. Claude accepts this.**

**But `λ=0` may be the one λ that cannot discriminate.** The forcing is a
*product*, `(tau/w_core)·(π_core − g_pi)`. At `λ=0` there is no noise to drive
`π_core` away from the `FullInstanton` profile that *is* `g_pi`, so the mismatch is
`≈0`, the product is `≈0`, and the solve is clean at every `n`. The `n²` prefactor
cannot bite when its other factor vanishes. The near-`n`-independence of the
residual is what the mechanism *predicts* under those conditions, not evidence
against it. This is structurally the same trap as the `δN★=0.1` degenerate branch
(§2.4), relocated into λ-space.

What survives: the closure and λ are **multiplicatively coupled**, so a failure at
finite λ and success at `λ=0` is consistent with *both* readings —

- *Agent's reading:* λ-driven feasibility wall (`H²_local < 0`) is the trigger; the
  closure's `n²` stiffness is an amplifier.
- *Claude's reading:* the failure is `(tau/w_core)·(mismatch)`; λ merely supplies
  the mismatch.

**Neither is currently distinguished by any evidence.** §4.2 separates them.

### 3.4 Tests B / Diagnostic 12 — the corridor, and an over-read conclusion

- Diagnostic 11: at `n=9`, `last_lambda_tried == lambda_c_positive` **bit-for-bit**
  (`4.247941624378134`), for the entire 50-iteration budget. `n=7`'s converged root
  sits only 5.6% of the corridor width from the negative edge; `n=5`'s sits at 42%.
  `λ_c ∝ w_core ∝ 1/n²`, so the corridor **shrinks as `n²`** while the root
  (`−15.51` at `n=5`, `−16.78` at `n=7`) does not.
- Diagnostic 12 (production change: `CORRIDOR_POSITIVE_WIDENING`): widening up to
  10× does **not** produce convergence at `n=9`. The search moves off the wall
  (`nearest_edge_fraction` `0.000 → 0.14`) but then hits repeated
  `Picard inner failed` at the *same* `λ ≈ 5–12` values, saturating identically at
  `widening=5.0` and `10.0`.
- Test B: forced cold evaluation at `λ ∈ {−12,…,−26}` (the region 12 never probed):
  **all fail** (`blown-up` at `−12`, `diverging` elsewhere).

**Caveats that must not be lost.** (a) `sweep_evaluate` is *not warm-started*; the
real outer loop's escalation is. A cold probe finding no fixed point across a
14-unit swath is meaningful but does not rule out a root reachable only by
incremental warm-started negative escalation. (b) `Picard inner failed` /
`diverging` / `blown-up` are **Picard-convergence labels**, not confirmed
`H²_local < 0` events. The feasibility wall is *defined* by `ε_core > 1`. Nobody
has checked whether these failures are actually that. **Until §4.3 is run,
"genuine feasibility wall" is a label, not a finding.**

Claude's earlier "the root is outside the `n=9` corridor" argument is **withdrawn
as a live hypothesis**: it rests on reading `n`-independence off `n=5,7`, which are
exactly the two points where the SAT prefactor is smallest (agent's point, and
correct).

---

## 4. Tests not yet run, in priority order

Each is designed so that a negative result is informative and cheap.

### 4.1 φ-regularity control on the same grids  *(zero solves, minutes)*

Compute `(D@φ)_core / |φ_core|` on the identical four converged `n=5` grids that
A2 used.

- If **φ's ratio is small** (the design note's `O(1/τ)` boundary layer) while π's
  is O(1): that asymmetry is exactly what "φ has the right target, π has the wrong
  one" predicts. A2 becomes evidence **for** the live-Neumann proposal, not
  against it.
- If **φ's ratio is also O(1)**: the regularity picture is in trouble at `n=5` and
  something more basic is wrong — high-value negative.

This is the single cheapest test on the list and it directly adjudicates §3.2.
**Run first.**

### 4.2 Contraction-window vs `tau_multiplier` at `n=9`  *(the decisive test)*

At `n=9`, `(m=1e-2, δN★=0.5)`, scan `|λ|` upward from 0 (both signs) and record the
largest `|λ|` at which the inner Picard still converges — the *contraction window*.
Repeat at `tau_multiplier ∈ {0.5, 1.0, 2.0}` (the parameter exists, prompt 27).

- **Window width τ-independent** → genuine λ-driven feasibility wall; closure
  exonerated as *trigger*. Agent's reading of §3.3.
- **Window narrows as τ grows** → failure scales with the penalty, not the noise.
  Claude's reading.

This is the experiment §3.3 shows is missing. Use warm-started escalation (or state
explicitly that it is cold), to avoid inheriting Test B's caveat (a).

### 4.3 Is the wall actually `H²_local < 0`?  *(nearly free, run alongside 4.2)*

At each failing λ in 4.2 (and at Test B's `λ ∈ {−12,…,−26}`), record whether
`ε_core = 0.5·π_core² > 1` / `H_sq_local < 0` was actually reached, versus the
Picard iteration simply failing to contract with `ε_core` bounded well below 1.

Settles whether "feasibility wall" is a mechanism or a label (§3.4b). If the
failures are **not** `H²<0` events, the entire feasibility-wall attribution —
including Diagnostic 12's and Test D's conclusions — needs rewriting.

### 4.4 Frozen-coefficient abscissa sweep for the proposed live-Neumann-π closure  *(gate on any production change)*

`tools/diagnostics/GradientCoupledInstanton/spectrum.py --mode spectrum --closure sbp-sat`,
`n_max = 8…192`, across the `α`/`Δs` grid, for the **complete two-field closure**
with `g_pi = neumann_boundary_value(pi_full, D, -1)` (value-type penalty, live
target). The 9 July script already has a `sat="regularity"` mode; extend it to SAT
both fields.

- Flat abscissa in `n_max` → David's stability objection is answered on its own
  terms, empirically, before any production change.
- Growing abscissa → the proposal dies here, and the honest conclusion is the 9 July
  one: *a value must be selected*, and the question becomes which.

**Necessary, not sufficient.** 21a's own history: the frozen-coefficient check was
green for `tau = A_core/2`, and the nonlinear Picard iteration still oscillated at
`n=7`. This gates the change; it does not validate it. Validation is the τ-sweep
afterwards — under a consistent closure, τ-independence becomes an **acceptance
criterion**, not a hope.

### 4.5 `H_FP = −∂S_MSR/∂δN★` on the existing converged solutions  *(zero solves; closure-independent)*

From `HFP-STRUCTURE-STATUS.md`. You already have `S(δN★)` at
`δN★ ∈ {0.2, 0.3, 0.5, 0.7}` (`159.49, 396.37, 1425.28, 4255.66`) and the persisted
grids. Finite-difference `∂S/∂δN★`, instrument `H_FP`, compare.

This is an **independent** consistency test that the true solutions must satisfy,
regardless of which closure is correct. Given Test A, Claude **expects it to fail**.
If it does, the `n=5` solutions are shown to be non-physical without needing to
settle the closure question first — which is a much cheaper route to the same
conclusion. High value, low cost, and it should be run even if 4.1–4.4 are deferred.

### 4.6 The transposed SAT (from the companion document)

The `H_FP` thread found that the forward and response discretisations are **not
adjoint**: the SAT in `forward_rhs.py` has no transpose counterpart in
`response_rhs.py`. That single defect predicts, without further assumption:

- a **λ-dependent** failure (the response sector only enters through `r = λ·r̃`,
  so it is invisible at `λ=0` — consistent with Test D);
- that **worsens with `n`** (the un-transposed term carries the same `tau/w_core ~ n²`
  prefactor);
- **invisible on the degenerate branch** (§2.4);
- with **both sectors' step counts degrading together** (Diagnostic 10's ~14×
  explosion in *both* directions between `n=7` and `n=9`, which no single-sector
  hypothesis explained).

This hypothesis may account for Tests A, B, and D *simultaneously*, and for
Diagnostic 10's otherwise-ambiguous attribution. **It has not been tested. It cannot
be evaluated from this thread alone.** It is the reason the two documents must be
synthesised rather than read in sequence.

---

## 5. What is settled, what is contested

**Settled (high confidence):**

- `g_pi` is frozen at `FullInstanton phi2(N)`; the penalty forcing does **not**
  vanish at convergence (Test A, two independent methods).
- The forcing is 2–19× the background terms at peak, 5–20% at late `N`, worse at
  larger `δN★`, and it rings.
- `tau/w_core ∝ n²`. The closure is inconsistent as `n → ∞` at fixed
  `tau_multiplier`.
- The `n=5`/`n=7` solutions are materially τ-dependent (Diagnostic 8t) and must be
  treated as **provisional**.
- `forward_rhs.py`'s docstring is wrong about `g_pi` and has been since 22c.
- Derivative-type / hard-eliminated regularity on `π` does **not** cure the
  abscissa (tested 9 July; `n^1.6` persists).
- `tau_multiplier` is correctly modelled as a threaded, non-persisted parameter
  (prompt 27) — and more so if the closure is fixed, since then it genuinely will
  not affect the answer.

**Contested (do not treat as settled in the synthesis):**

- *Whether the λ-driven feasibility wall or the closure's stiffness is the
  proximate cause of the `n≥9` floor.* Test D falsifies Claude's strong form; §3.3
  argues `λ=0` cannot discriminate. → §4.2, §4.3.
- *Whether π genuinely violates core regularity, or was forced to.* A2 says the
  former; §3.2 argues circularity. → §4.1.
- *Whether a live-Neumann-π target is stable.* Never checked on the complete
  two-field closure. → §4.4.
- *Whether the failures at `λ ≈ 5–12` and `λ ∈ [−26,−12]` are `H²<0` events at
  all.* → §4.3.
- *Whether the non-adjointness (companion doc) subsumes all of the above.* → §4.6.

**Withdrawn:**

- Claude's "the `n=5→7` root is `n`-independent, so it lies outside the `n=9`
  corridor" — rests on the two points where the SAT prefactor is smallest.
- Claude's "the live-Neumann idea was overlooked" — it was considered on 9 July; a
  *different* (derivative-type) version was tested and correctly rejected. The
  value-type version remains untested.
- Claude's λ-independence hypothesis, in its stated strong form (Test D).

---

## 6. The question for the synthesis

Given (a) an inconsistent core closure with an `n²`-amplified spurious forcing, and
(b) a forward/response pair that is not discretely adjoint:

> Is the right move a **discrete variational (MAM-type) formulation** that makes the
> forward and response discretisations adjoint by construction — which would
> simultaneously fix the non-adjointness, determine the SAT target from the
> variational principle rather than by selection, and yield a clean discrete balance
> law — or a **targeted fix to `g_pi` alone** (live-Neumann, if §4.4 permits)?

The characteristic analysis in `HFP-STRUCTURE-STATUS.md` bears directly on this: the
core is **subsonic inflow with one incoming characteristic**, which is *why*
`pi_core` requires data at all, and which reframes `g_pi` as a **stated physical
model closure** (asserting the incoming characteristic carries homogeneous-instanton
data) rather than a numerical stabiliser. If that framing is accepted, the frozen
`FullInstanton` target is not a bug to be removed but a modelling assumption to be
**declared in `onion_model.tex` and tested** — and Test A's magnitudes are then the
measurement of how much that assumption is doing. This is a genuinely different
resolution from the live-Neumann proposal, and the two cannot both be right.

That question is what the fresh context is for.
