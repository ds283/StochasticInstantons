# Prompt 07 — Fix N convention to match FullInstanton; add delta_s guard

## Context

This prompt fixes a real bug found by tracing through an inconsistency
Claude Code flagged while building prompt 06, spanning three
already-committed files (`InflatonTrajectory`, `forward_rhs.py`,
`picard.py`) plus one already-committed function (`delta_s()` in
`Numerics/OnionCoordinate.py`) that needs a guard, not a fix — its formula
was already correct.

**The confirmed, correct convention (must match `FullInstanton` exactly):**

- The instanton's own internal $N$ **starts at 0 and increases toward the
  end of inflation** — same as `FullInstanton`'s own local time variable.
- `N_init`, `N_final` (the compute target's input parameters) are
  measured **backwards** from the end of inflation, `N_init > N_final`,
  exactly as `FullInstanton` already uses them.
- `N_total = N_init - N_final + delta_Nstar`, same formula as
  `FullInstanton`.
- Conversion to `InflatonTrajectory`'s absolute argument: define
  `N_offset = N_end - N_init` **once**, then absolute $N = $
  `N_offset + N` (local). This is a two-input formula — `N_offset` and the
  local `N` — not the one-input `N_end - N` that was built by mistake.

**Why the previous version was wrong**: `delta_s()`'s formula
($\Delta s(N)=\ln(1+\alpha)+(N-N_{\rm init})+\ldots$, derived from the
tautology $a(N)/a(N_{\rm init})=e^{N-N_{\rm init}}$) only holds if $N$ is
increasing/local — the tautology's plain `+` sign forces this. But
`phi_before_end(N) = trajectory.phi_at(N_end - N)` assumed $N$ was the
backward-counted parameter directly. Both were built by the same person in
different prompts on silently incompatible assumptions; this prompt makes
them consistent, matching `FullInstanton`.

## Task

### 1. `ComputeTargets/InflatonTrajectory.py`

Remove `phi_before_end`, `pi_before_end`, `rho_before_end` entirely —
purely additive when added in prompt 04, purely subtractive to remove now.
Nothing else in the codebase depends on them (only `forward_rhs.py`,
fixed below). Do not add a replacement method here — the replacement is a
plain `phi_at(N_offset + N)` call at the point of use, not a new
convenience wrapper.

### 2. `Numerics/OnionCoordinate.py` — add a guard, not a fix

`delta_s()`'s formula is already correct. Add: raise `ValueError` if
`N < N_init` (using whatever `N_init` is actually passed to `delta_s()` at
the call site — after the fixes below, this will always be `0.0`, so in
practice the guard becomes "`N < 0`" at every real call site, but write the
check generically against the `N_init` parameter `delta_s()` actually
receives, not hardcoded to `0.0`, since that's the actual domain
constraint the tautology depends on, and the function shouldn't assume
how callers use it). This is a configuration/usage error, not a
convergence failure — same category as the other hard guards already in
this codebase — with a message stating both values. Update
`tests/test_onion_coordinate.py` to cover this.

### 3. `ComputeTargets/GradientCoupledInstanton/forward_rhs.py`

- Replace the `N_init: float` parameter (in `forward_rhs` and
  `unpack_state`) with `N_offset: float` — `forward_rhs` no longer needs
  the raw backward-counted `N_init` for anything; it only ever needed it to
  build `N_offset` (now the caller's job) and to feed `delta_s()` (now
  always `0.0`).
- Fix the outer-edge boundary row: replace
  `trajectory.phi_before_end(N)`/`.pi_before_end(N)` with
  `trajectory.phi_at(N_offset + N)`/`trajectory.pi_at(N_offset + N)`
  directly.
- Fix both `delta_s()` calls (core-only and per-node array) to pass
  literal `0.0` for the `N_init` argument, not a parameter passed through
  from outside.
- Update every test in `tests/test_forward_rhs.py` that constructs a
  state/calls `forward_rhs`/`unpack_state` for the new `N_offset`
  parameter and the corrected trajectory lookup. Add a test confirming
  $\Delta s(N{=}0)=\ln(1+\alpha)$ exactly when the full state's core node
  is set to the trajectory's own initial values (i.e. the zeroth-iterate
  scenario) — this is the concrete, checkable consequence of the
  reasoning above, not just an assertion to take on faith.

### 4. `ComputeTargets/GradientCoupledInstanton/response_rhs.py`

Fix both `delta_s()` calls the same way (literal `0.0` for `N_init`).
`response_rhs` has no trajectory dependency (the outer-edge response
condition is a trivial constant zero), so no `N_offset` parameter is
needed here — remove `N_init` from its signature entirely if it's
currently only used for the `delta_s()` calls (check; don't leave an
unused parameter). Update `tests/test_response_rhs.py` accordingly.

### 5. `ComputeTargets/GradientCoupledInstanton/picard.py`

- Compute `N_offset = trajectory.N_end - N_init` and
  `N_total = N_init - N_final + delta_Nstar` **once**, at the top, from
  the compute target's raw parameters.
- `H_sq_nl_init` (the fixed reference): confirm this is computed at
  absolute $N=$ `N_offset` (i.e. `potential.H_sq(trajectory.phi_at(N_offset),
  trajectory.pi_at(N_offset))`) — check the current implementation doesn't
  route this through a since-removed `before_end`-style call; fix if it
  does.
- Forward pass: integrate local $N$ from `0.0` to `N_total`, **increasing**
  — matching `FullInstanton`'s own `(0.0, N_total)` `t_span` exactly (this
  is a change from the current implementation, which integrates over
  absolute $N$ — replace it, don't layer a second convention on top).
- Backward/response pass: integrate local $N$ from `N_total` down to
  `0.0`, **decreasing** — matching `FullInstanton`'s `(N_total, 0.0)`
  `t_span` for `bwd_rhs` exactly.
- Terminal condition: `terminal_response_state(lam, grid, delta_s_N_final)`
  where `delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_at_N_total,
  H_sq_nl_init, alpha)` — confirm `N_total` (not an absolute value) is what
  gets passed here.
- Shooting residual unchanged in form (`phi_core(N_total) - phi_end`), just
  now genuinely using `N_total` as the local endpoint, matching
  `FullInstanton`'s `p1[-1] - phi_final` exactly in spirit.
- Pass `N_offset` into every `forward_rhs` call.
- Update `tests/test_picard.py`'s reduction-limit test if it needs
  adjusting for the corrected local-$N$ convention (it should still pass —
  this fix makes the convention *match* `FullInstanton`, so the comparison
  should if anything become more direct, not need loosening).

## Acceptance criteria

- [ ] `phi_before_end`/`pi_before_end`/`rho_before_end` removed from
      `InflatonTrajectory`.
- [ ] `delta_s()` raises `ValueError` for `N < N_init`, tested.
- [ ] `forward_rhs`/`unpack_state` take `N_offset`, not `N_init`; boundary
      row uses `trajectory.phi_at(N_offset + N)`/`.pi_at(N_offset + N)`
      directly; both `delta_s()` calls pass literal `0.0`.
- [ ] `response_rhs`'s `delta_s()` calls pass literal `0.0`; unused
      `N_init` parameter removed if applicable.
- [ ] `picard.py` computes `N_offset`/`N_total` once; forward pass
      integrates `(0.0, N_total)` increasing; backward pass integrates
      `(N_total, 0.0)` decreasing; `H_sq_nl_init` computed via `N_offset`
      directly, not a removed convenience method.
- [ ] All existing tests updated and passing; new $\Delta s(0)=\ln(1+\alpha)$
      test added; `delta_s` guard test added.
- [ ] End-to-end reduction test against `FullInstanton` (from prompt 06)
      still passes after these changes.
- [ ] No other files touched.

## Commit

Single commit, message along the lines of:
`Fix N convention to match FullInstanton (local zero-based N, single N_offset for trajectory lookups); add delta_s domain guard`
