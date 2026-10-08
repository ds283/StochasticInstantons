# Summary C — boundary-layer / convergence-floor thread (9–10 July) and the synthesis thread (10–11 July)

Sources read in full: `2026-07-09_Resolving-boundary-layer-issues-in-gradient-coupled-instanto.md` (3681 lines) and `2026-07-10_Synthesizing-handoff-documents-and-prioritizing-actions.md` (967 lines), compared against the repo record: `.documents/gradient-coupled-instanton/24-phase0-baseline.md`, `25-*.md`, `26*.md`, `26a*.md`, `26b*.md`, `28-tau-study-diagnostics-8t-and-13.md`, `.documents/handoff-notes/HANDOFF-gradient-coupled-instanton.md`, and the three `2026-07-10/` notes (`SAT-CLOSURE-STATUS.md`, `HFP-STRUCTURE-STATUS.md`, `HFP-CALCULATION.md`), plus `git log`, `git status`, `forward_rhs.py`, `DIAGNOSTICS_SUITE.md`.

Transcript timestamps below are as printed in the export (they appear to be UTC; repo file mtimes and commit times are BST, one hour later).

---

## 1. Dated timeline of reasoning, decisions, hypotheses raised and falsified

### Thread 1 — "Resolving boundary layer issues" (9 July 10:24 → 10 July 09:43)

**09 Jul 10:24 — David's opening brief.** Three questions: (ONE) are the four converged `n=5` solutions meaningful, and pursue the handoff's τ/α sensitivity sweeps; (TWO) "If the boundary layer matters to this extent, what is the conclusion? Do we conclude that the collocation strategy is not the right discretization"; (THREE) which of the prompt-21–24 scripts to keep as a permanent diagnostic suite.

**10:27 — Claude's first assessment.** `n=5` points are "candidate, not wrong". τ is a hardcoded local (`tau = abs(A_core)`) in `forward_rhs.py`, so a `tau_multiplier` production change is a prerequisite. Flags a *competing* hypothesis for the `n≥9` floor: the frozen `pi_core` SAT target (24a mechanism (a)), and proposes testing it first because it is cheaper. Ranks suspects: (1) fixed target, (2) τ hardening not scaling with `n`, (3) genuine stiff two-timescale physics at `N≈0` (which would argue for Radau in `N`, not a `y`-discretisation change), (4) only then "LGL collocation is structurally wrong". On TWO: LGL nodes cluster O(1/n²) at boundaries, so coarse-converges/fine-fails "would be an unusual failure mode for a spectral method". Recommends promoting the scripts into `tools/diagnostics/gci/`.

**10:37 — David: do the diagnostics package first.** Fixes the name `tools/diagnostics/GradientCoupledInstanton` ("GCI is fine for informal discussion ... in the code, I would prefer to use consistent nomenclature"), `DIAGNOSTICS_SUITE.md` in `FILE_MAP.md` style, embedded in the tree.

**10:47 — Claude builds the package.** `harness.py`, `convergence_floor.py` (Diagnostics 1–8; 8t stubbed with `NotImplementedError`), `trajectory_plots.py`, `seed_screen.py`, `spectrum.py` (thin wrapper — only ~170/1770 lines of `analyze_StiffnessSpectrum.py` had been seen), `archive/prompt22_validation.py`. Real bug surfaced during the merge: `compare_gradient_full.py` and `validation_22_resolved_regime.py` still used the pre-22a *degenerate* `phi_end`.

**13:30 — David: refactor landed.** Asks (i) what exactly the bias-corrected `n≥9` test is, (ii) whether τ is "tune-once-and-forget" or needs its own Datastore table/factory like `alpha`.

**13:32 — Decisions.** Diagnostic 9 = Diagnostic 3a's bias injection spliced onto Diagnostic 6's `n`-retry. τ persistence: **not** a `DatastoreObject`; the test is "Could two rows in the same production database legitimately need to record different values of this". `alpha`/`n_collocation_points`/`tolerance` pass; τ does not, because the closure's whole point is τ-independence of the converged answer. Revisit trigger: if 8t shows different masses/δN★ need different τ. Pattern: same as 24b's `OUTER_TOL_FLOOR`.

**13:34–13:36 — Prompt 25 drafted.** Design choice: measure `bias_n5 = max|pi_core − g_pi_core_final|` at the point itself rather than transplant Diagnostic 3a's `δ=+0.03`.

**19:06 — Prompt 25 result: clean negative.** `bias_n5 = 0.0827`; seven bias-scaled perturbations at `n=9` all fail; larger `|δ|` monotonically worse. David: "It does not look positive, so we should probably proceed to testing `tau`." Asks whether any options remain for the core SAT closure beyond τ's value.

**19:08 — Claude: five distinct levers under "the SAT closure".** (1) τ magnitude; (2) **τ's functional shape in `N`** — `A_core = 2/Δs(N)` blows up as `N→0`, exactly where the oscillation lives, so a uniform multiplier can never separate "not enough damping" from "damping concentrated in the wrong place"; (3) `g_pi` target level vs *shape* vs lag cadence (Diagnostic 9 only tested a rigid additive shift); (4) the response sector's own closure — strongest "something else" candidate, since its frozen-coefficient check is "exactly the same kind of check that turned out to be insufficient for the forward sector"; (5) physics-level: whether a `pi_core` BC "falls out of the variational principle at `y=1`". Proposes using the existing `instrument_stiffness` flag first.

**19:17–19:21 — Prompt 26 drafted.** Instrumentation confirmed rich enough (per-sector RK45 step stats). Two historical facts surfaced from 21a: an `n=7` oscillation was once traced to forward τ (`0.5×→1×`), but τ at `1–8×` was separately *ruled out* for a mismatched-seed divergence (§8.1).

**21:37 — Prompt 26 result: ambiguous.** Both sectors' step counts explode ~14× at `n=7→9`; `bwd/fwd` steps-per-efold ratio crosses 1 at `n=17`. New fact: `n=7` converges. David: "I don't see anything here that is clearly diagnostic. Probably best to move on to the `tau` sweep."

**21:41 — Prompts 27 and 28 drafted.** 27: `tau_multiplier: float = 1.0` threaded `forward_rhs → solve_picard → _compute_gradient_coupled_instanton`, non-persisted (precedent: `wallclock_budget_seconds`, `max_step`). 28: Diagnostic 8t (robustness at `n=5`) + Diagnostic "11" (unlock at `n=9`, widened to seven τ values 0.5–4.0). Warning: do not sweep `τ<0.5` (below admissibility; risks the `π_core→−√6` runaway of 21a §5.1). Claude flags the branch "nobody's raised yet": if 8t finds material τ-dependence at `n=5`, that outranks the `n≥9` question.

**10 Jul 07:09 — David attaches 26a, 26b, 28 results.** (26a: `n=9` pinned bit-for-bit on `λ_c,positive`; 26b: widening up to 10× does not help, `CORRIDOR_POSITIVE_WIDENING` added to `picard.py`; 28: `τ=1.0` reproduces goldens bit-for-bit, `τ=0.5` and `τ=2.0` break everything at `n=5` and `n=7`; `τ=4.0` "unlock" at `n=9` rejected as corridor-pinned; agent recommends a finer sweep `{0.8,0.9,1.0,1.1,1.2}`.)

**07:13 — Claude's reinterpretation (the pivotal message).** "the agent's empirical work is sound ... but its causal interpretation is wrong". Mechanism: since 22c (`theta=0, anderson_m=0`) `g_pi` is **frozen** at the FullInstanton seed's `phi2(N)`; the forcing `−(τ/w_core)(pi_core − g_pi)` therefore does *not* vanish at convergence, and is linear in τ. Diagnostic 9's own `bias_n5=0.0827` against `|pi_core|≈0.31` means the target is wrong by ~27% at the converged solution. `w_core = 2/(n_max(n_max+1)) ∝ 1/n²`, so the prefactor `τ/w_core` grows ∝ n² (3.6× `n=5→9`, 13.6× `→17`). This one fact is claimed to explain: the `n≥9` floor; why Diagnostic 9's uniform shift could not help (shape mismatch, prefactor untouched); why Diagnostic 10 saw both sectors explode; the "boundary layer" (thickness `~w_core/τ`, *created by the penalty*); and the `τ=4` pseudo-convergence (hard-constraining `pi_core ≡ g_pi`). Answer to TWO: "**no.** The discretisation is fine. The *closure* is inconsistent". Rejects the finer τ sweep: "That's fitting a numerical penalty to a preferred result." Second, independent hypothesis: root ≈ n-independent (`−15.5`, `−16.8`) while corridor shrinks ∝1/n², so `n=7` is the last `n` where the root fits; 26b never probed the negative side, so "corridor ruled out" is "stronger than its evidence supports". Proposed: Step 1 measure the forcing on the persisted grids; Step 2 compute `(D@π)_core/|π|`; Step 3 seed `λ=−18` at `n=9`. The eventual production prompt would be "replace the frozen `g_pi` with a live Neumann regularity target", not "tune τ". Housekeeping: `forward_rhs.py` docstring "factually wrong ... since 22c".

**09:03 — David reports.** Forcing "not negligible, coming in at something like O(10%)"; negative-corridor seeding "seems not to work".

**09:04 — Claude.** Test A "stronger than O(10%)": peak 1.6–14× background, growing with δN★, and it **rings** — which settles the handoff brief's open question (the least-action argument was right; "The penalty rings, and drags `π_core` along with it"), explaining `S_GCI/S_FI` 15→38 with `E≈61` flat. Methodological correction: the agent's claim that `g_pi` is "not persisted" is wrong — it is the frozen FullInstanton `phi2(N)`, so the direct construction is available. Test B reinterpreted: a λ-*independent* failure cannot be the λ-proportional noise term; "at `n=9` the inner Picard map is no longer a contraction, for any λ at all". Withdraws the corridor-vs-root hypothesis. Proposes the `λ=0` control at `n∈{5,7,9,17}` as the decisive test, plus `(D@π)_core`.

**09:15 — David's pushback.** The Neumann condition at `y=+1` was previously found not to eliminate the `n_max`-growing instability: "aren't we back to the problem that the intermediate evolution will be unstable?"

**09:15 — Claude.** Instability came from node *elimination*, not from Neumann; `g` appears only in the bounded forcing term of the energy estimate `dE/dN = −a'E + (½A_core − τ)u_core² + τ u_core g`; `g_phi` is "exactly the construction I'm proposing for π". Concedes one subtlety: a live `g` re-enters the operator off-diagonally, so the abscissa must be re-checked with `spectrum.py`.

**09:18 — David.** "No, it has not been overlooked. This idea was tested in a previous conversation and found not to work" — asks Claude to search past conversations.

**09:20 — Claude retracts "overlooked".** Finds the 9 July "Evaluating onion model implementation" thread: hard elimination of `π_core` via Neumann coefficients halves the abscissa but `n^1.6` growth persists; "a *derivative* condition can't cancel a *value*-type (π_core²) energy defect". But that thread also proposed a value-type penalty toward the "regularity-consistent value" with a `sat="regularity"` script mode, and the retrieved record never reports its result. Draws the distinction *penalized quantity* vs *target value*. Reframes 22c: "the τ-dependence isn't a new pathology. It's the invoice for a documented trade whose cost was never priced." Surfaces the parallel `H_FP` thread's non-adjointness finding.

**09:32 — David attaches Tests A (corrected), A2, B, D.** A airtight (two methods agree to ~1e-6). A2: `(D@π)_core/|π_core|` is O(1), median 0.29→1.17. B: cold evaluation at `λ∈{−12…−26}` all fail. **D: `λ=0` converges at every `n` up to 17, residual −0.122→−0.120.** Agent's reading: closure and noise term *interact*; noise term is the trigger. David: "I finally understand what you are proposing ... the distinction you were making between penalizing `(Dpi)_core` and `g = neumann_boundary_value(...)`". Asks: continue here or fresh context?

**09:33 — Claude.** Accepts Test D falsifies the strong hypothesis, but argues `λ=0` is the one λ that cannot discriminate (forcing is a *product*; at `λ=0` the mismatch factor is zero — "the same trap as the δN★=0.1 degenerate branch, relocated into λ-space"). Proposes the *contraction-window vs τ* experiment and the `ε_core>1` check. Argues A2 is circular (violation ratios track Test A's penalty ratios) and proposes the φ-control. Recommends a fresh context with two status documents and the synthesis question "MAM-type discrete variational formulation vs targeted `g_π` fix". Adds `H_FP = −∂S/∂δN★` as a closure-independent test, expected to fail.

**09:40–09:43 — David asks for, and Claude writes, `SAT-CLOSURE-STATUS.md`** with settled/contested/withdrawn sections and §4 open tests.

### Thread 2 — "Synthesizing handoff documents" (10 July 09:57 → 11 July 12:26)

**10 Jul 09:57 — David.** Three asks: prioritise the two notes; how does the prompt-23 negative (response-sector SBP was *stiffer*) intersect with non-adjointness; MAM-type discrete variational formulation vs targeted `g_π` fix.

**10:07 — Claude: "Four corrections that reorder everything".**
- **C1.** For LGL, `w_core · D[-1,-1] = 1/2` exactly (verified numerically at `n_pts=5,7,9,17,33`), so `sat_phi_core = −2τ (Dφ)_core` identically: `g_phi` is a *derivative-type* penalty. The SAT-CLOSURE §3.1 table collapses — the "failed" and "production `g_phi`" rows are the same construction. A live `g_pi` would replace the only negative-definite term with an indefinite rank-one one; "**Prediction: §4.4 returns `n^1.6`.**"
- **C2.** The code applies advection to both fields, so `π = ∂_Nφ − A∂_yφ`, hence `∂_yπ|_core = −A_core (∂²_yφ)_core ≠ 0`. The continuum justification for live-Neumann-π is false *in this code*; A2's O(1) ratio is expected; the right control is `(Dπ)_core` vs `−A_core(D²φ)_core`. "Live-Neumann-π is dead on two independent grounds."
- **C3.** `g_pi` as a declared physical closure (HFP §2(c)/(d)) is *also* wrong: one incoming characteristic ⇒ one BC; the code imposes two forward penalties — over-determination whose strength grows ∝n². Root cause: the SAT was derived against the wrong energy norm (`Σw(φ²+π²)` instead of `Σwμ(π² + c²(∂_yφ)²)`); the correct norm gives a single rank-one penalty on `(Dφ)_core` along the incoming eigenvector. HFP's "reconciliation" (`g_phi` live, `g_pi` fixed) is "wrong in both halves".
- **C4.** The `S_MSR` error from the dropped variational terms is `O(R²)` not `O(R)`; "Your published-facing results ... are `FullInstanton` results ... Those results are probably fine." *(Retracted at 10:28.)*
- Tiers 0–4 of actions; Q2 answered: a transpose cannot be stiffer (same eigenvalues, singular values, numerical abscissa); prompt 23 built a *different* matrix by analogy; the response state vector is "one DOF short of what the adjoint requires"; but do not transpose the *current* over-determined operator. Q3 answered: separate (a) discrete adjoint consistency, (b) MAM minimiser, (c) the boundary term; reject (b) (degenerate `D12=D22=0`); (a) is right but must be preceded by (c); cheap route = generate the response RHS by AD/complex-step of `forward_rhs`.

**10:23 — David's physics objection.** `H(φ)`, `ε(φ)` are "**genuinely not present** in the original Langevin equations" — they come from the Einstein equations; treating them as locally determined is "a-priori inconsistent"; re-introducing their variation gives Langevin equations not equivalent to the original. Is this on the critical path?

**10:28 — Claude.** Calls the code a "chimera" (forward uses local `H(φ,π)`, backward is the adjoint of a frozen-`H` system) — *partly retracted at 10:47*. Two consistent theories (A frozen background / B local constraint); (A) is unavailable because it has no δN physics. Explicit calculation: `∂f₂/∂φ = −(3−ε)[V''/V − (V'/V)²]`; for `V ∝ φ^p` the exact `P1_dot = −1/(p−1) ×` coded. **Quadratic: exactly the wrong sign at equal magnitude**; quartic `−1/3`; USR null. "I retract 'your `FullInstanton` physics is probably fine'." Every `S_MSR` number (min-action locus, `δN★_th(ΔN)`, the 1.2–1.4 exponent) is suspect; Vennin's exponent-1 mismatch becomes "a live suspect".

**10:34 — David.** Pushes back on the Routhian argument with the `a³φ̇²` example; asks whether the terms appear only in the response-sector equations.

**10:35 — Claude.** "Yes. That is exactly what I mean" — concedes the Routhian/auxiliary-field argument was wrong; the MSR action is for the already-reduced SDE on `(φ,π)`; tangent-map argument needs no variational principle; proposes the 20-line finite-difference check of `bwd_rhs` against the forward tangent map. Physical statement: "a noise realization moves `H`".

**10:45 — David.** "I don't have an objection! I am trying to understand" — proposes order: fix response sector (physics + "evaluated on the noiseless background" code bug) → instrument `H_FP` → then C3.

**10:47 — Claude.** No "evaluated on background" bug exists — both sectors evaluate at local fields; single defect is the *functional form*; retracts "chimera" ("the adjoint of no system whatsoever"). Full exact adjoint for `FullInstanton`: four omissions — (1) `−P2 dV²/(V·Hsq)` in `P1_dot`; (2) `−2εP2` (`3−ε → 3−3ε`); (3) `−(dV/V)πP2`; (4) both diffusion terms `∝ D11 P1²`, which are **quadratic in `P1`** and therefore break the `r = λ r̃` architecture (Riccati). Amends David's order: split Tier 1 into class 1 (frozen-state Jacobian identities — run *now*), class 2 (`H_FP` baseline drift — run now as a number), class 3 (grid physics — defer). "Don't hand-derive the fix" — generate by AD. Six-step sequence 0–5, C3 last.

**11 Jul 08:35–08:36 — David checks understanding; decisions.** Analytic operator for production/publication ("this is how 99% of physics is done"; `O(n²)` cost objection); Claude concedes: analytic for production, numerical complex-step as a one-time oracle. Adjointness is "a correctness issue", not structurally required — agreed, with the refinement that the shooting target is then not a stationary point, so the `S` error is `O(R)=O(1)`. Dropping `∂D/∂u` is empirical and the staged fix measures it for free. Retaining it requires rebuilding the λ loop — agreed, plus the Riccati blow-up caveat (integrate `M` blocks, `P = M₂M₁⁻¹`).

**08:43–08:45 — λ strategy.** Linearity buys (a) dynamic-range protection (the stated reason, `λ~1e9`) and (b) cheap outer-residual rescaling. At `λ~O(10)` (a) "largely evaporates"; (b) is lost regardless. Cautions: confirm λ in the production corner; Riccati blow-up is λ-size-independent; document `r̃=r/λ` in the tex as *contingent on linearity*.

**08:48 — David.** "I don't think we know how large `lambda` will be until we have rebuilt the correct adjoint sector" — deferred. Asks whether a genuine Riccati blow-up means a model approximation breaks down. Claude: no — conjugate point = representation breakdown; model-domain failure is `H_sq_local→0`; log both separately.

**10:40–12:26 — Vocabulary.** Tangent map vs response field vs Riccati variable `W`; pushforward/pullback yes, "symplectic, not Riemannian".

---

## 2. The synthesis thread: what was agreed, decided, and planned

**Priorities actually agreed (final form, 10 Jul 10:47, confirmed 11 Jul 08:36):**

```
0. Class-1 checks on current code at a frozen state (FullInstanton, 2x2):
   adjoint residual E = J_resp + J_fwd^T (complex-step) and the
   finite-difference tangent-map check. Record H_FP baseline drift. ~a day.
1. Restore ∂f/∂u only (terms 1–3). Linear, homogeneous, architecture-safe.
   Residual H_FP drift is then exactly the ∂D/∂u contribution.
2. Decide on ∂D/∂u from that number (if material: Riccati/M-block solver and
   rebuild of the λ loop; if not: state as approximation with measured bound).
3. Class-3 checks: H_FP = −∂S/∂δN★, log-log exponent, three-potential
   falsification set (quadratic sign flip; quartic −1/3; USR null — the
   load-bearing prediction). Re-run FullInstanton grids.
4. Port to GCI response_rhs (interior terms, closure-independent).
5. C3: rebuild the core SAT from the characteristic analysis (single penalty
   on (Dφ)_core in the energy norm μ(π²+c²(∂_yφ)²)), then transpose to get
   the response-sector boundary rows.
```

David's own proposed order (10:45) was "fix response sector → instrument `H_FP` → C3"; Claude's amendments (accepted without objection) were to insert step 0 first, to split `∂f` from `∂D`, and to put C3 last.

**Contested questions and David's positions:**

- *Live-Neumann `g_pi` vs model-closure `g_pi`.* Neither was adopted. Claude's C1–C3 argue both are wrong and the fix is a single characteristic penalty on `(Dφ)_core`. David did not contest C1–C3; his energy went into the response-sector adjoint question. **No explicit sign-off on C3 from David is recorded**, only his agreement that C3 comes last.
- *MAM / discrete-variational vs Picard.* MAM as a minimiser was rejected (degenerate noise, Grafke); "discrete adjoint consistency inside the current Picard architecture" was endorsed. David's decision on *how* to obtain the adjoint: **analytic for production and publication**, with numerical complex-step only as a one-time consistency oracle ("I will need this operator worked out correctly, analytically, for publication anyway").
- *What to do first.* Step 0 (frozen-state Jacobian identities on `FullInstanton`) — not Tier 1 as the two notes had it, and *not* the `H_FP = −∂S/∂δN★` grid test, which was explicitly downgraded to class 3 / "worthless on the current grids".
- *Physics of `∂H/∂φ`.* David's final understanding, confirmed by Claude: the derivative terms appear **only** in the response-sector equations; the Langevin/forward equations are unchanged. David's stance that `a(t)` is never varied in the scalar EOM stands; the resolution is that the MSR action is written for the already-reduced SDE. The onion's `H_sq_loc` (truncated constraint lacking gradient and curvature terms) was flagged by Claude as a genuine reason for caution that David's objection *does* reach — deferred until the `FullInstanton` result is in.
- *λ magnitude / Riccati.* Deferred by David: cannot be known until the adjoint sector is rebuilt.

**Documents/prompts planned next.** Thread 1 planned `SAT-CLOSURE-STATUS.md` (written), `HFP-STRUCTURE-STATUS.md` (written in the parallel thread), and "a third produced *in* the new context" — the synthesis document. **That third document was never written**; the synthesis exists only as the chat. No prompt 29 (or any prompt for steps 0–5) was drafted in either thread. Thread 1 also recommended a standalone commit fixing the `forward_rhs.py` docstring (done in part — see §3).

**Did the synthesis conclude anything the three 10 July notes do not contain?** Yes — essentially the whole of Thread 2 is absent from the repo. See §3, items marked NOT RECORDED. Most importantly: C1 (the exact identity `w_core·D[-1,-1]=1/2` and its consequence that live-Neumann-π is predicted unstable), C2 (`∂_yπ|_core = −A_core ∂²_yφ`), C3 (over-determination; wrong energy norm; single-penalty fix), the four missing terms in `bwd_rhs` with the quadratic-potential **sign flip**, the retraction of "FullInstanton is fine", the `∂D/∂u`/Riccati consequence, and the six-step plan.

---

## 3. Substantive conclusions — recorded in the repo or not

**RECORDED**

| Conclusion | Where |
|---|---|
| Diagnostics package design, shared harness, pre-22a `phi_end` bug in two predecessor scripts | `tools/diagnostics/GradientCoupledInstanton/DIAGNOSTICS_SUITE.md` §2; commits `d61086d`, `d5073b8` |
| τ is a threaded, non-persisted parameter, not a `DatastoreObject` (and the test for when to promote it) | `.prompts/.../27-tau-multiplier-production-change.md`; `SAT-CLOSURE-STATUS.md` §5 "settled"; commit `5e8d08c` |
| Diagnostic 9 clean negative (fixed-target bias does not explain `n≥9`) | `25-bias-corrected-n-geq-9-retry.md`; `24-phase0-baseline.md` §6.3 |
| Diagnostic 10 ambiguous; `n=7` converges with sharper transient | `26-sector-attribution-instrument-stiffness.md`; `24-phase0-baseline.md` §6.3–6.4 |
| Corridor pinned at `n=9`; widening does not help; `CORRIDOR_POSITIVE_WIDENING` added | `26a-*.md`, `26b-*.md`; commits `c57c2c2`, `2e2b1e5` |
| Material τ-dependence at `n=5`/`n=7`; `τ=4` pseudo-unlock rejected | `28-tau-study-diagnostics-8t-and-13.md` Parts 1–2; `SAT-CLOSURE-STATUS.md` §2.3 |
| Frozen `g_pi` since 22c; forcing does not vanish; `τ/w_core ∝ n²`; Test A two ways; ringing explained; collocation not the problem, closure is | `28-*.md` addendum Test A; `SAT-CLOSURE-STATUS.md` §1.1, §2.1–2.2 |
| Live-Neumann proposal, penalized-quantity vs target-value distinction, 9 July history, A2 dissent, Test D accepted with product caveat, Test B caveats, corridor-vs-root withdrawn | `SAT-CLOSURE-STATUS.md` §3, §5 |
| Open tests 4.1–4.6 and the synthesis question | `SAT-CLOSURE-STATUS.md` §4, §6; `HFP-STRUCTURE-STATUS.md` "Relation to work already inflight" |
| `forward_rhs.py` *module docstring* fixed (fixed-target regime described) | commit `4c7f38e` (10 Jul 09:48 BST) |

**NOT RECORDED (highest-value output of this comparison)**

1. **C1 — `w_core · D[-1,-1] = 1/2` exactly; `g_phi`'s SAT is `−2τ(Dφ)_core`, a derivative-type penalty.** Consequence: `SAT-CLOSURE-STATUS.md` §3.1's table conflates two identical constructions; the "contested" item "whether a live-Neumann-π target is stable" is predicted *settled negative* (`n^1.6` returns); §4.4 should be retired. The repo still lists it as open.
2. **C2 — `∂_yπ|_core = −A_core(∂²_yφ)_core ≠ 0` because advection acts on both fields.** Live-Neumann-π's continuum justification is false in this code; A2's O(1) ratio is *expected*; §4.1's φ-control is the wrong control (correct one: `(Dπ)_core` vs `−A_core(D²φ)_core`). Repo still recommends §4.1 "Run first".
3. **C3 — two forward penalties vs one incoming characteristic = over-determination; the SAT was derived in the wrong energy norm; fix is a single rank-one penalty on `(Dφ)_core` along the incoming eigenvector, coefficient set by `(2/Δs)(2−ε_core)`, not `A_core`.** This rejects *both* resolutions the repo's §6 poses (live-Neumann and model-closure) and the `HFP-STRUCTURE-STATUS.md` reconciliation paragraph ("`g_phi` live Neumann ... `g_pi` fixed model closure"), which the chat calls "wrong in both halves". HFP §2(c)/(d) ("`pi_core` is genuinely underdetermined by data") is argued to confuse a missing energy bound with a missing boundary condition.
4. **The response sector is not the adjoint of the forward sector in its *functional form*: four omitted terms in `FullInstanton.bwd_rhs`**, and the quadratic-potential **sign reversal at equal magnitude** of the `P1_dot` drift term (`exact = −1/(p−1) × coded`; quartic `−1/3`; USR null). `HFP-STRUCTURE-STATUS.md` §4 says the fix "is cheap" and lists only `∂/∂φ` terms; the chat establishes `∂ε/∂π` and `∂D/∂π` are also missing and that the consequence is O(1).
5. **Retractions**: C4's "`S` error is `O(R²)`" and "FullInstanton physics is probably fine" (retracted — all `S_MSR` numbers, the minimum-action locus, `δN★_th(ΔN)` and the 1.2–1.4 exponent are suspect; Vennin exponent-1 discrepancy is a live suspect); "chimera" / "evaluated on the noiseless background" (retracted — no such bug; the evaluation point is correct). None of these appear in the repo, and HFP §4's "error linear in R" framing is the version that survives, but without the magnitude estimate.
6. **`∂D/∂u` terms are quadratic in `P1` and break the `r = λ r̃` architecture** (`response_rhs.py` docstring states linearity is exact; the chat says it is an approximation contingent on dropping `∂D/∂u`); Riccati structure; `M₂M₁⁻¹` solver; staged fix measures the `∂D` contribution as the residual `H_FP` drift. No tex/docstring flag recorded.
7. **Q2 answer**: a transpose cannot be stiffer than the original (identical eigenvalues, singular values, numerical abscissa); prompt 23's negative concerned a different matrix; the response state vector is one DOF short of the adjoint; do not transpose the current operator before fixing C3. Not recorded.
8. **Q3 answer**: (a)/(b)/(c) decomposition; MAM rejected; discrete adjoint consistency endorsed; AD-generated adjoint as a cheap route; David's decision for analytic-for-production. Not recorded.
9. **The agreed six-step sequence and the class 1/2/3 split of tests.** It *supersedes* both repo orderings: `SAT-CLOSURE-STATUS.md` §4 (4.1 "run first", 4.5 "should be run even if 4.1–4.4 are deferred") and `HFP-STRUCTURE-STATUS.md` "Suggested ordering" (1. instrument `H_FP` first). In the chat, 4.1 and 4.4 are retired, 4.2 becomes "a diagnostic, not an arbiter", 4.3 is "hygiene", and 4.5 is class 3 — "worthless on the current grids" until the adjoint is fixed.
10. **From Thread 1**: the τ-shape-in-`N` lever (lever 2 at 19:08); the Radau-in-`N` suggestion; the explicit *rejection* of the finer τ sweep `{0.8…1.2}` — which the committed `28-*.md` "Combined recommendation" still proposes as "the immediate next step", unrebutted in the repo; the `tau_multiplier<0.5` warning (in the prompt 28 file only).
11. **David's physics position** on the origin of `H(φ)`, `ε(φ)` (Einstein equations, not Langevin), the Routhian concession, and the final agreed statement that derivative terms live only in the response sector; the caution that the onion's `H_sq_loc` is a truncated constraint. Not recorded anywhere, and it is tex-relevant.
12. **λ magnitude and Riccati/conjugate-point discussion**; recommendation to document `r̃=r/λ` as contingent on linearity in `onion_model.tex`; the pushforward/pullback/symplectic vocabulary.

**Repo-state defects noticed during the comparison**

- `forward_rhs.py` inline comment block (around lines 539–546) still says `g_pi` is the "LAGGED SELF-CONSISTENT core pi(N) trajectory" and "forcing -> 0 there too" — the module docstring was fixed in `4c7f38e` but this block was not. `SAT-CLOSURE-STATUS.md` §1.2 (written 09:43 UTC from stale uploaded files) says the docstring is still wrong; it is now half right.
- `DIAGNOSTICS_SUITE.md` §5 still says "Diagnostic 8t ... is not implemented and will raise `NotImplementedError`"; `24-phase0-baseline.md` §6.5 still says 8t is "still blocked". Both are stale relative to the 28 results.
- Diagnostics 8t/13 code (`convergence_floor.py`, +264 lines) and the test change are **uncommitted** (`git status: M`). `28-tau-study-diagnostics-8t-and-13.md`, the v2 PNG, and the entire `handoff-notes/2026-07-10/` directory are **untracked**. The Test A/A2/B/D scripts are not in the repo at all; only their results survive, in the 28 addendum.

---

## 4. Open questions and doubts raised by David that were never resolved

1. **"If the boundary layer matters to this extent, what is the conclusion?"** Answered in Thread 1 (closure inconsistent, discretisation fine — recorded) but *re-answered* in Thread 2 (over-determined closure in the wrong norm; C3) — the second answer is unrecorded and David never explicitly endorsed it.
2. **Whether the regularity-value-target abscissa test from the 9 July conversation was ever run.** Claude could not find the result; C1 predicts it fails, but no one checked.
3. **Whether the `n≥9` inner-Picard failures are actually `H²_local<0` events** (SAT-CLOSURE §4.3). Downgraded to "hygiene" but never run.
4. **How large λ is in the production corner** — David: unknowable until the adjoint sector is rebuilt. Determines whether the linear `r̃` architecture can be abandoned.
5. **Whether `∂D/∂u` is material** — explicitly left empirical; to be measured by the staged fix. David's related doubt that `D_ij`'s field dependence is an "adiabatic substitution" rather than a constraint was acknowledged but not settled.
6. **Whether differentiating the onion's truncated `H_sq_loc` is legitimate** (David's "a-priori inconsistent" worry survives for the GCI even after it was dissolved for `FullInstanton`). Deferred.
7. **David's 09:15 doubt** ("aren't we back to the problem that the intermediate evolution will be unstable?") was answered "no" in Thread 1 and then, by C1 in Thread 2, effectively "yes" — the two threads disagree and the repo carries only the first answer.
8. **Vennin's asymptotic exponent of 1 vs the measured 1.2–1.4 slope** — raised as a suspect of the sign-flipped response term; never checked.
9. **Who decides on C3** — the single-characteristic-penalty redesign was asserted by Claude and sequenced last by David, but David's "what is the conclusion?" question about the SAT closure itself never received a recorded decision from him.
10. **Whether the finer τ sweep should run** — the committed 28 document says yes; Claude said no; David did not rule.

---

## 5. One-paragraph verdict

The 9–10 July thread converted a τ-sweep result into a mechanism (frozen `g_pi`, `τ/w_core ∝ n²`) and wrote it up well in `SAT-CLOSURE-STATUS.md`, with its own errors (overlooked claim, λ-independence) honestly logged. The 10–11 July synthesis then overturned a large part of that document — the live-Neumann proposal, the model-closure alternative, the φ-control, the abscissa gate, and the priority order — and uncovered a larger defect (the response sector's missing derivative terms, with a sign reversal for the quadratic potential) that puts every `S_MSR` number, including `FullInstanton`'s, in question. **Nothing from the synthesis thread is in the repository.** The three 10 July notes are the last written record, and on at least five points (§3 items 1–3, 9, and the HFP "reconciliation") they are now known to be wrong or superseded by conclusions that exist only in the chat.
