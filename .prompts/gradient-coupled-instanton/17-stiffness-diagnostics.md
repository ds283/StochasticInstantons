# Prompt 17 — Stiffness characterization: assembled-operator eigenvalue sweep + per-solve integrator instrumentation

## Context

A code review (`onion_model_implementation_review.md`) confirmed the
`GradientCoupledInstanton` solver is a faithful method-of-lines scheme —
`D`/`D2` applied as explicit matrix-vector products inside the RHS, marched
in $N$ by `scipy.solve_ivp(RK45)`, no linear solve or matrix inversion
anywhere. The consequence: the classical collocation ill-conditioning is
**traded, not removed** — it reappears as *stiffness* of the $N$-integration.
The bare $D2$ spectrum grows like $\mathcal O(n^4)$ with comparable real and
imaginary eigenvalue parts (genuinely oscillatory-stiff), exactly the
failure mode `onion_model_planning.md` flagged as this approach's specific
risk — and the eigenvalue-spectrum diagnostic the plan asked for was never
built. Before any $n_{\rm max}$ convergence scan can be trusted, the
stability envelope needs characterizing, so a divergent run isn't mistaken
for a physics result.

This prompt builds two complementary diagnostics — analytic (eigenvalue
sweep) and empirical (per-solve integrator instrumentation) — answering the
same question ("is the explicit scheme safe at production scale?") from
both sides. **Out of scope for this prompt** (explicitly deferred): the
analysis script that consumes the per-solve diagnostics across a grid; any
change to the integrator itself (e.g. switching to `Radau`); the SBP+SAT
fallback. This prompt only *measures*; acting on what it finds is a later
decision.

## Task

### Part A — assembled-operator eigenvalue sweep (standalone script)

A standalone script (place alongside `plot_InstantonSolutions.py` /
whatever existing convention the codebase uses for analysis scripts —
check first, follow it), computing the spectrum of the **assembled**
spatial operator, not bare $D2$.

**Critical — assemble the real operator, not $D2$ alone.** The review's own
$D2$ table overstates stiffness because the RHS applies physics prefactors
($4/\Delta s^2\cdot e^{\Delta s}e^{\Delta s y}$ inside `L_operator`, the
$e^{-2\Delta s_{\rm loc}}$ gradient prefactor, and the advection
coefficient) plus Neumann elimination — the actual stability limit is set
by the eigenvalues of the *assembled* linear operator acting on the free
DOF vector, with those factors and the boundary elimination folded in. The
script must build that assembled operator (the linearized map the free-DOF
state vector actually sees per RHS call, at a frozen $(N, n_{\rm max},
\alpha)$ point — the coefficients are $N$-dependent, so this is the
operator at that instant), then take its eigenvalues.

- One clean way to get the assembled operator without re-deriving it by
  hand: form it numerically as the Jacobian of the (linear-in-state)
  spatial part of the RHS — e.g. apply the RHS's spatial operators to each
  unit basis vector of the free-DOF space, columns assembling the matrix.
  This guarantees the spectrum reflects exactly what the integrator sees,
  including any prefactor/elimination detail, rather than a hand-transcribed
  operator that could drift from the real RHS. Confirm the frozen-coefficient
  assembly matches a direct finite-difference Jacobian of `forward_rhs`'s
  spatial terms (gradient/advection only, physics-source terms held out) at
  the same point, as a self-check that the assembled operator is faithful.
- Sweep over representative `(n_max, alpha, N)` including the regimes the
  review said are untested: production-scale `n_max` (not just the 8-64 of
  the review's table — go higher, e.g. up to 128+), and the wide-transition
  `Δs ~ 20` profiles (choose `N`/scenario so `delta_s_N` reaches that
  range), plus small `alpha` (near the `N_init` coordinate singularity the
  α-regularization is meant to tame).
- **Structured output**: write a CSV (or JSON — match whatever the codebase
  already uses for tabular analysis output; CSV if no precedent) with
  columns `(n_max, alpha, N, delta_s_N, op_norm, max_abs_re_lambda,
  max_abs_im_lambda, implied_rk45_max_dt)` where the implied stable step is
  `~2.8 / max_abs_lambda` (RK45's real-axis stability limit; note in a
  comment this is a rough guide, the true limit for a complex spectrum is
  region-dependent). Optionally a spectrum scatter plot per the existing
  plotting convention. This is a re-openable artifact for comparing across
  parameters, not terminal output.

### Part B — per-solve integrator instrumentation

Add measurement of what `solve_ivp` actually does during a real solve,
recorded into the diagnostics that already get persisted — **not** printed.

- **Boolean switch**: add `instrument_stiffness: bool = True` as a parameter
  on the top-level Ray-dispatched solve function (the one wrapping
  `solve_picard` inside `GradientCoupledInstanton.compute()`'s remote task).
  Default `True` for now (data wanted during characterization). Docstring
  note: expected to default to `False` eventually, once the stiffness
  envelope is understood, to avoid per-solve overhead on production runs.
- **The switch gates measurement overhead only — never the solve itself.**
  With `instrument_stiffness=False`, the physics result must be bitwise
  identical; only the extra diagnostic fields go unpopulated. The switch
  must not change `solve_ivp`'s method, tolerances, grid, or anything
  affecting the numerical answer.
- **What to record** (into `solve_picard`'s returned diagnostics dict, which
  already lands in `GradientCoupledInstanton`'s persisted `diagnostics_json`
  column — extend that dict, don't invent a new channel): per forward and
  backward integration, aggregated across all Picard sweeps of the whole
  solve — `rk45_total_steps`, `rk45_accepted_steps`, `rk45_rejected_steps`,
  `rk45_min_step`, `rk45_max_step`, `rk45_steps_per_efold` (total steps /
  `N_total`), and wall-clock per Picard sweep (min/mean/max). These come
  from `solve_ivp`'s result object (`.t` gives step locations; rejected-step
  counts may need `dense_output` or the solver's own step statistics —
  check what `solve_ivp`'s return object actually exposes for RK45 and
  record what's available, noting any that aren't cleanly accessible rather
  than computing them wrongly).
- A `stability_limited_fraction`-type measure (how often the step was
  clamped small) is desirable but only if it can be derived cleanly from
  what `solve_ivp` exposes — don't fabricate it from a heuristic if the
  solver doesn't surface the accept/reject reason. If it can't be had
  cleanly, record the raw accepted/rejected counts and leave the
  interpretation to the (out-of-scope) analysis script.

## Tests

- Part A: the assembled-operator-vs-finite-difference-Jacobian self-check
  passes (the assembled operator faithfully reflects the RHS's spatial
  terms). A smoke test that the sweep runs and produces the structured
  output file with the expected columns for a small parameter set.
- Part B: `instrument_stiffness=False` produces a bitwise-identical physics
  result to `True` (same converged solution, same `msr_action`, same
  profile) — assert this directly, it's the key correctness property of the
  switch. With `True`, the diagnostics dict gains the expected keys with
  plausible values (positive step counts, `min_step <= max_step`, etc.).

## Acceptance criteria

- [ ] Part A script computes eigenvalues of the **assembled** operator
      (prefactors + Neumann elimination folded in), self-checked against a
      finite-difference Jacobian of the RHS's spatial part.
- [ ] Sweep covers production-scale `n_max` (>64), wide `Δs~20`, and small
      `alpha`; writes a structured, re-openable file (not terminal output).
- [ ] Part B adds `instrument_stiffness: bool = True` to the top-level
      solve function; gates measurement only; `False` gives bitwise-identical
      physics (tested).
- [ ] Per-solve integrator stats recorded into the existing persisted
      diagnostics dict, not printed.
- [ ] No integrator change, no SBP+SAT, no consuming-analysis-script — all
      explicitly out of scope.

## Commit

Single commit, message along the lines of:
`Add stiffness diagnostics: assembled-operator eigenvalue sweep + gated per-solve integrator instrumentation`
