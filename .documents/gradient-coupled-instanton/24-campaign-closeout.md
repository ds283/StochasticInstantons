# Prompt 24 (revised) — campaign closeout

Closes out `.prompts/gradient-coupled-instanton/24-revised-deep-dive-then-map.md`
against its own acceptance criteria.

## Acceptance criteria

- [x] **Safeguard + classification in place; no unattended point can hang.**
  Implemented in `ComputeTargets/GradientCoupledInstanton/picard.py` +
  `Numerics/ShootingSolver.py`: a per-solve `wallclock_budget_seconds`
  deadline checked at forward/backward RHS-call granularity, the inner
  Picard sweep loop, and the outer shooting loop, plus `max_step` on every
  `solve_ivp` call. Every non-convergent bail is tagged `converged`/
  `diverging`/`floored`/`descending`/`blown-up` via `_classify_bailout`,
  exposed in `diagnostics["bailout_tag"]`/`["bailout_reason"]`. Wired
  end-to-end through `GradientCoupledInstanton.py`, its factory, and new
  `main.py` CLI flags (`--gci-wallclock-budget-seconds`, `--gci-max-step`).
  18/18 new+existing tests pass; 0 regressions across the 45-test GCI suite.
  See `.documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md`.
  **Directly validated in Phase A**: the safeguard fired at `compute_time
  =3603.5s` against a `3600s` budget (3.5s margin) and again at `7224.9s`
  against `7200s` (24.9s margin) — a graceful, correctly-classified bail
  both times, never a hang, never a crash.

- [x] **Phase A go/no-go answered.** No non-trivial converged solve exists
  anywhere across `m/Mp ∈ {1e-2, 1e-3, 1e-4, 1e-5}` at `(δN★=1.0, n=5,
  α=0.1, N_init=19.5, N_final=16.0)`, even with a 1–2 hour per-point
  budget. The `m`-boundary is not a clean "converges up to X" line — nothing
  in this range converges — but the *mechanism* differs: `m∈{1e-3,1e-4,1e-5}`
  hit a genuine outer-residual floor well inside their time budget
  (structural-ish, not a budget problem); `m=1e-2` is dominated by an
  extremely expensive Armijo-backtracking cascade at its
  FullInstanton-bootstrapped `λ≈1900`, too few outer iterations completed (4
  of 50, identically on two separate runs at 1×/2× budget) to say whether it
  is convergent-but-slow or would also floor. See
  `.documents/gradient-coupled-instanton/24-phase-a-deep-dive.md` for the
  full writeup, including the CPU-contention caveat uncovered by the
  doubled-budget re-run (this ran on a shared development laptop, not a
  dedicated cluster — load average ~700 during the campaign).

- [x] **Phase B descoped.** Per the prompt's own contingency ("Phase B map
  produced *if* Phase A found a region worth mapping; otherwise Phase B is
  descoped and the finding is the Phase-A boundary") and confirmed with the
  user: Phase A found no converged region anywhere, so there is no
  convergence-map compute to spend. The Phase A four-point-plus-follow-up
  result **is** the map, at the one grid slice tested.

- [x] **Phase C descoped.** FullInstanton-consistency checking requires
  converged GCI points to compare; none exist in Phase A's results (and
  none have ever existed at production scale — see Phase 0's baseline). No
  new consistency data to report beyond what Phase 0 already catalogued
  (the tiny `N_total=0.15` toy-fixture comparison, prompt 22c's own
  fixed-target-bias regression test).

## What changed in the codebase

- `ComputeTargets/GradientCoupledInstanton/picard.py`,
  `Numerics/ShootingSolver.py`,
  `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`,
  `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`,
  `config/argument_parser.py`, `main.py` — the prerequisite wall-clock
  safeguard and classification (production code, not campaign-only).
- `tests/test_picard.py` — three new tests covering the safeguard/
  classification (wallclock bail, generous-budget-still-converges, ODE
  failure still tags blown-up).
- `.documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md`,
  `24-phase-a-deep-dive.md`, `24-campaign-closeout.md` (this file) — design/
  results notes.
- `out-gci-convergence-campaign/` — the two run databases
  (`phase_a.sqlite` + 2 shards, `phase_a_followup.sqlite` + 1 shard) and
  their logs, left in place as the primary evidence for the results table
  above.

## Known, unresolved side-finding (not fixed — out of scope)

`--no-store-values` combined with `--targets homogeneous gradient` crashes
the gradient branch's `FullInstanton` seed fetch: `_run_gradient_branch`'s
Pass-0 lookup doesn't pass `_do_not_populate=True`, so a scalars-only-stored
`FullInstanton` row makes `Datastore/SQL/ObjectFactories/FullInstanton.py`'s
`build()` raise instead of degrading gracefully. Worked around here by not
combining these two flags; flagged for a future prompt to fix if
`--no-store-values` + gradient-branch seeding is ever needed together.

## Bottom line for future prompts building on this one

GCI at `δN★=1.0` (the first resolved, non-degenerate point past the trivial
`δN★=0.1` branch) does not converge at any mass tried, for two distinct
reasons depending on mass. Any follow-on wanting a genuine non-trivial GCI
solve should treat this as a real operating-envelope boundary, not a
compute-budget problem to brute-force past: the `m∈{1e-3,1e-4,1e-5}`
floor is not budget-limited (confirmed directly — all three finished in
under 40% of a generous budget with no further progress), and the `m=1e-2`
case's true nature is still open (the doubled-budget test was inconclusive,
not negative) but would need either a cleaner (less contended) machine, a
smarter/cheaper bootstrap than jumping straight to `λ_FI`, or both, before
spending more wall-clock chasing it under this same algorithm.
