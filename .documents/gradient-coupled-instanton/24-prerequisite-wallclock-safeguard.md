# Prompt 24 prerequisite — wall-clock safeguard + non-convergence classification

**Status: complete.** Implements the checklist in
`.prompts/gradient-coupled-instanton/24-revised-deep-dive-then-map.md`'s
"Prerequisite" section, ahead of the Phase A/B/C campaign.

## What changed

`ComputeTargets/GradientCoupledInstanton/picard.py`:

- `solve_picard` gains two new optional keyword parameters:
  `wallclock_budget_seconds` (default `None` = unbounded) and `max_step`
  (default `None`, resolves to `DEFAULT_MAX_STEP_FRACTION * N_total`, i.e.
  `N_total/50`).
- A global deadline (`compute_start + wallclock_budget_seconds`) is checked
  at three layered granularities, all graceful (never a hard crash, never a
  partially-overwritten grid):
  1. **RHS-call granularity** — every forward/backward RHS evaluation
     (`_fwd_rhs`/`_bwd_rhs`) checks the deadline and raises a private
     `_WallclockBudgetExceeded` the moment it is exceeded. This is the fix
     for the actual disqualifying gap Phase 0 found (a single RK45 pass
     step-halving indefinitely): the check fires on the very next RHS call,
     regardless of how small the step has shrunk.
  2. **Inner Picard sweep loop** — checked before starting each of the
     `MAX_INNER` sweeps; a hit breaks the loop early, keeping whatever grid
     the last *completed* sweep produced (identical code path to naturally
     exhausting `MAX_INNER`).
  3. **Outer shooting loop** (`Numerics/ShootingSolver.solve_shooting`, new
     optional `deadline` parameter) — checked before every outer iteration;
     a hit exits with `ShootingResult.budget_exceeded=True`.
- `max_step` is forwarded to both `solve_ivp` calls (forward and backward
  pass) as defence-in-depth: it bounds a single accepted step so a
  pathological stride cannot itself run long before the next RHS-level
  deadline check gets a chance to fire.
- Every non-convergent bail is classified via `_classify_bailout` into
  `"converged"` / `"diverging"` / `"floored"` / `"descending"` /
  `"blown-up"`, exposed in the returned `diagnostics` dict as
  `bailout_tag`/`bailout_reason`/`outer_residual_history`/
  `wallclock_budget_exceeded`. `"blown-up"` is reserved for a genuine ODE/
  divergence failure on the *last* outer evaluation (H_sq<0, RK45
  step-death, or the prompt-22c divergence early-exit) — a wall-clock bail
  is never tagged `"blown-up"` merely because it ran out of time; it falls
  through to the residual-trend classifier (last-5-evaluations relative
  change: >+5% diverging, <-5% descending, else floored). Fewer than 2
  successful outer evaluations before a bail is treated conservatively as
  `"blown-up"` (no trend data to classify from).

`Numerics/ShootingSolver.py`: `solve_shooting` gains an optional `deadline`
parameter (default `None`, unbounded) and `ShootingResult` gains
`budget_exceeded: bool = False`. `FullInstanton.py`'s own call site is
unaffected (it does not pass `deadline`).

`ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`,
`Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`: both new knobs
threaded end-to-end (remote function → `solve_picard`; class constructor →
remote-function kwargs; factory `build()` → constructor), exactly mirroring
how `full_instanton` is already threaded — **not** part of the object's
persisted identity (a rerun with a different budget that converges to the
same answer is the same physical object).

`config/argument_parser.py`, `main.py`: new CLI flags
`--gci-wallclock-budget-seconds` / `--gci-max-step`, wired through
`_run_gradient_branch`'s `key_fields()` closure — usable from the real
`main.py` pipeline, not just a bypass script.

## What did NOT change

- Every pre-existing caller (all of `tests/test_picard.py`'s prior 15 tests,
  the GCI end-to-end/stiffness-instrumentation/phi_end-target suites, 45
  tests total) passes both new parameters as `None` implicitly and is
  therefore completely unaffected — confirmed by re-running the full suite
  after the change (0 regressions).
- No Ray-level (task-cancellation) hard timeout is implemented inside
  `picard.py`/`GradientCoupledInstanton.py` — this module has no access to
  the Ray dispatch layer, and `RayTools/RayWorkPool.py` is protected
  infrastructure (`CLAUDE.md`) not to be modified without explicit
  instruction, and exposes no per-task timeout/cancel hook. Phase A runs
  through the *real* `main.py`/`RayWorkPool` pipeline (per the prompt's own
  instruction to run through the real pipeline rather than a bypass
  script), so it relies on layers 1-2 (the in-process deadline + max_step)
  alone — there is no bespoke driver wrapping `ray.wait`/`ray.cancel` in
  front of it. This is an accepted trade-off: layers 1-2 are the tested,
  effective fix for the actual failure mode Phase 0 found (RHS-level
  deadline checks fire reliably since scipy's RK45 calls back into the RHS
  every step, so a true un-interruptible C-level hang is not expected). A
  driver that bypasses `RayWorkPool` and dispatches
  `GradientCoupledInstanton.compute()` `ObjectRef`s directly could add a
  `ray.wait(refs, timeout=...)` + `ray.cancel(ref, force=True)` outer net on
  top for extra defence-in-depth, but this was not needed for Phase A/B/C's
  own runs.

## New tests (`tests/test_picard.py`)

- `test_solve_picard_wallclock_budget_bails_gracefully_and_tags_correctly` —
  an effectively-zero budget on the one genuinely-coupled small fixture
  produces a graceful `failure=True` result tagged
  `bailout_reason="wallclock_budget"`, never `"ode_failure"`.
- `test_solve_picard_generous_budget_still_converges_and_tags_converged` — a
  budget that never binds reproduces the existing convergent result exactly,
  now tagged `bailout_tag="converged"`.
- `test_solve_picard_ode_failure_tags_blown_up` — a genuine ODE failure
  (`solve_ivp` monkeypatched to report `success=False`) with no budget set
  at all is tagged `"blown-up"`/`"ode_failure"`, isolating the structural
  path from the wall-clock path above.

All 18 tests in `tests/test_picard.py` pass (511–516s wall-clock, unchanged
from before this change within noise).
