# Prompt 24 (revised) — Does GCI converge at science scale? Deep-dive, then map

**Supersedes the original prompt 24 structure.** Phase 0 (complete) established the
pivotal fact: **no converged, non-trivial (`λ≠0`) GradientCoupledInstanton (GCI)
solve at science scale exists anywhere in the record** — the only genuine `λ≠0`
solve is on the `N_total=0.15` toy fixture at `n=5`; every production-scale "pass"
is the degenerate `δN★=0.1`/`λ=0` branch or plumbing. So the first question is not
"where is GCI fast" but **"does GCI converge to a correct non-trivial solution at
science-relevant parameters at all — and if not, is the blocker slow-convergence or
structural?"** This prompt is organised around that, with a broad map second.

Run through the real `main.py`/datastore pipeline. Clean-negative is a valid, even
expected, outcome at every phase — the goal is to *know* the domain, not to force
convergence.

## Prerequisite — wall-clock safeguard + non-convergence classification

Phase 0's companion timing analysis found the disqualifying gap: `MAX_OUTER`/
`MAX_INNER` bound iteration *counts*, but nothing bounds wall-clock — no `max_step`
on the forward/backward `solve_ivp` calls, no time cutoff — so a single RK45 backward
pass can step-halve indefinitely in exactly the small-`m`/large-`δN★` corner this
campaign explores. Before any sweep:

- [ ] Add a per-solve wall-clock budget (configurable; a graceful bail that records
      state, layered with a Ray task-level hard timeout as the outer safety net, and
      a `max_step` on the `solve_ivp` calls so a single solve cannot hang before the
      loop-level check can fire).
- [ ] **Classify every non-convergence**, not just record "failed". At any bail —
      timeout, `MAX_OUTER`, `H_sq<0`, step-death — persist the residual trajectory and
      tag the outcome as one of: **converged** / **diverging** (residual growing) /
      **floored** (stalled at a residual plateau) / **descending** (residual still
      falling at bail → convergent-but-slow) / **blown-up** (`H_sq<0`/step-death →
      structural). This tag is what makes a timeout a data point rather than a hole,
      and it is what distinguishes "needs more budget" from "needs a fix" in every
      phase below.

This is the small, localised fix that unblocks everything; it lives here, not buried
in the sweep.

## Phase A — The go/no-go deep-dive (generous budget, few points, watched)

Answer the pivotal question directly. Fix a science-relevant `(δN★, n, α)` — suggest
`δN★=1.0, n=5` (or 7), `α=0.1`, `N_init=19.5, N_final=16.0` — and **walk `m/Mp` from
mild to astronomic**: e.g. `{1e-2, 1e-3, 1e-4, 1e-5}`, so `λ ~ 1/D` climbs from a
tractable scale into the resolved-regime `λ~1e9`. Generous per-point budget
(hours-scale), run watched / few-parallel, each point classified per the prerequisite.

- [ ] **Does the mild-`m` end converge?** The large-`m` case has moderate `λ` and
      should be tractable; a genuine non-trivial converged solve there
      (`λ≠0`, `msr_action>0`, finite, residual to tolerance) is the first "yes, GCI
      works on *something* non-trivial" the project has ever had. If even this fails,
      that is a deeper finding than astronomic `λ` and is the thing to report.
- [ ] **Where, and how, does it break as `m` shrinks?** Locate the `m` at which
      convergence is lost, and use the classification to state *why*: slow-descending
      (a budget/acceleration problem) versus blown-up/floored (a structural problem
      needing a numerical fix). This is the honest answer to "does some science calc
      converge, even if slow" — including the possibility that the answer is "it
      converges up to `m≈X`, then blows up structurally," which is a result, not a
      cap artefact.
- [ ] Where a point converges, sanity-check it against `FullInstanton` at the same
      `(phi_init, pi_init, phi_end, N_total)` — core trajectory / `λ` / `msr_action`
      should be *similar* (slow-roll), not necessarily equal.

**Deliverable:** a crisp statement of whether a non-trivial science-scale solve
converges, the `m`-boundary of convergence, and the nature of the failure beyond it.
This is the campaign's primary result; Phases B/C are contingent on it.

## Phase B — The map (aggressive cap, many points, parallel)

Only worth the compute if Phase A shows a non-trivial converged region to map the
edges of. Characterise the landscape cheaply:

- [ ] **Pilot first (~20–30 points)** spanning the grid corners, to get real per-point
      timing — none exists in the record — and set the map's short cap (minutes-scale)
      from it.
- [ ] Sweep `m/Mp × δN★ × n × α` (coarse then refine near boundaries), Ray-parallel,
      short cap, **every point classified** (converged / diverging / floored /
      descending / blown-up). Record iteration counts, final residual, `λ`,
      `msr_action`, wall-clock, failure tag. CSV first, plot second.
- [ ] The short cap is appropriate *here* precisely because a "descending"-tagged
      timeout is not lost — it is flagged as convergent-but-slow and handed back to a
      Phase-A-style generous run if it lands in a region of interest. A short cap
      never silently becomes a false "failed".
- [ ] Resolve the standing sub-questions the map is positioned to answer: is the 22c
      `n=9` non-convergence general or fixture-specific? How does the astronomic-`λ`
      onset scale with `m`? Does `α` shift the boundary?

**Deliverable:** the convergence map — where GCI converges, where it fails and (via
the tag) why — the explicit domain of applicability.

## Phase C — FullInstanton-consistency of the converged region

For converged points (from A and B):

- [ ] **Agreement in the limit:** small-`δN★` / mild slow-roll — GCI tracks FI closely,
      confirmed across `n` (a genuine limit, not an `n=5` coincidence).
- [ ] **Sensible divergence:** as `δN★` grows / the profile resolves, `S_GCI − S_FI`
      is smooth, monotone, physically defensible in sign and magnitude — and the gap
      itself **converges in `n`** (a non-converging gap is a resolution artefact, not
      physics).
- [ ] **Fixed-target bias, physical regime (22c Finding 3, still open):** re-measure
      at a converged resolved point where `λ_FI` is a good same-sign proxy; if not
      small, scope the pre-agreed two-pass outer self-consistency (prompt 23).
- [ ] **Downstream:** first genuine `extraction.py`/`scale_assignment.py` on a
      resolved non-flat `zeta(y)` — `C(r)`/`C̄(r)`/`r_max`/`r_peak` sensible, or report
      what breaks.

## Acceptance

- [ ] Safeguard + classification in place; no unattended point can hang.
- [ ] **Phase A go/no-go answered:** either a non-trivial science-scale solve
      converges (with the `m`-boundary and, beyond it, slow-vs-structural nature
      stated), or a crisp statement that it does not and why.
- [ ] Phase B map produced *if* Phase A found a region worth mapping; otherwise Phase B
      is descoped and the finding is the Phase-A boundary.
- [ ] Phase C consistency demonstrated for whatever converged region exists.

## Out of scope

- New numerical closures (forward/response SBP-SAT done; the two-pass self-consistency
  only if Phase C's bias demands it; any *structural* blocker Phase A surfaces is
  scoped as a follow-on, not fixed here).
- Higher potentials / the science production campaign — this establishes the operating
  envelope they run inside.
