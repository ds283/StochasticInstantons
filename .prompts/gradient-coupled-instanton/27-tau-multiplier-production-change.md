# Prompt 27 — `tau_multiplier`: a threadable, non-persisted SAT-penalty parameter

*(Numbering assumption: continues the `.prompts/gradient-coupled-instanton/`
sequence after prompt 26. Renumber if a different slot is taken.)*

## Implements

A small, explicitly-scoped **production** change: `forward_rhs.py`'s
hardcoded `tau = abs(A_core)` becomes `tau = tau_multiplier * abs(A_core)`,
with `tau_multiplier: float = 1.0` threaded through as an ordinary keyword
parameter — `forward_rhs()` → `solve_picard()` → (for consistency with an
existing, precedented pattern; see §3 below) `_compute_gradient_coupled_instanton()`.
Default value reproduces every existing behaviour bit-for-bit; this prompt
changes nothing about what production runs actually do.

**This is the prerequisite flagged in `DIAGNOSTICS_SUITE.md` §5** — until it
lands, `diagnostic_8_tau_sensitivity` in `convergence_floor.py` cannot be
implemented (it currently raises `NotImplementedError` explaining exactly
this). A follow-on prompt (28) implements that diagnostic and a new
n≥9 tau-unlock sweep once this lands; **do not** implement either diagnostic
as part of this commit — this prompt is the production change only.

## Track / step

Production prerequisite for the τ-sensitivity study motivated by Diagnostic
9 (clean negative on the fixed-target-bias explanation for `n≥9`
non-convergence) and Diagnostic 10 (ambiguous sector attribution — forward
not exonerated, response not ruled out). Does not itself answer either
question; it only makes them answerable.

## Depends on

- `ComputeTargets/GradientCoupledInstanton/forward_rhs.py` — the file being
  changed. Read its own module docstring in full, especially the "SBP-SAT
  boundary closure" section and the large comment block immediately above
  the current `tau = abs(A_core)` line — the two empirical hardenings
  recorded there (`abs()` for sign robustness; `1×` not `0.5×` for iteration
  stability margin) are exactly the history this parameter needs to be
  threaded compatibly with.
- `ComputeTargets/GradientCoupledInstanton/picard.py`'s `solve_picard` and
  its internal `_fwd_rhs` closure — the closure already captures
  `alpha, H_sq_nl_init, grid, trajectory, potential, diffusion_model,
  disable_spatial_coupling` from the enclosing scope; `tau_multiplier`
  is captured the same way, no new parameter needs to flow through
  `_fwd_rhs`'s own call signature.
- `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`'s
  `_compute_gradient_coupled_instanton` (the Ray remote function,
  `main.py`-adjacent) — for the precedented threading pattern in §3.

## Context to read first

- `.documents/gradient-coupled-instanton/21a-production-port-notes.md`, §5.1
  and §5.2 in full — the exact reasoning that produced today's
  `tau = abs(A_core)`. This prompt must not weaken or reinterpret that
  reasoning; it only exposes the existing multiplier as a parameter.
- `tools/diagnostics/GradientCoupledInstanton/DIAGNOSTICS_SUITE.md` §5,
  "Known gaps" — the scoping note this prompt fulfils, written at the time
  `diagnostic_8_tau_sensitivity` was stubbed.
- The conversation record that produced this prompt (persistence-model
  discussion): **`tau_multiplier` is deliberately NOT a `DatastoreObject`,
  not part of any SQL factory, and not part of `GradientCoupledInstanton`'s
  persisted identity/query key** — unlike `alpha_regularization` and
  `n_collocation_points`, which earn persistence because they appear in
  downstream physical formulas and because comparing runs across their
  values is itself part of establishing correctness. `tau` is a pure
  closure/stabilisation device that the SBP-SAT design note's own
  admissibility criterion (`tau >= A(core)/2`) says should not affect the
  converged answer at all — if Diagnostic 8t (prompt 28) confirms that,
  there is nothing for a database column to disambiguate between rows. See
  §3's own note on `wallclock_budget_seconds`/`max_step` for the exact
  precedent this follows.

## Assumable interfaces (exact current signatures)

`forward_rhs.py`:
```python
def forward_rhs(
    N: float, state: np.ndarray, N_offset: float, alpha: float,
    H_sq_nl_init: float, grid, trajectory, potential,
    rfield_splines, rmom_splines, diffusion_model, g_pi_core_spline,
    disable_spatial_coupling: bool = False, lam: float = 1.0,
) -> np.ndarray:
    ...
    A_core = float(A_array[-1])
    tau = abs(A_core)                    # <-- the line this prompt changes
    w_core = float(grid.weights[-1])
    g_phi_core = neumann_boundary_value(phi_full, grid.D, boundary_index=-1)
    g_pi_core = float(g_pi_core_spline(N))
    sat_phi_core = -(tau / w_core) * (phi_full[-1] - g_phi_core)
    sat_pi_core = -(tau / w_core) * (pi_full[-1] - g_pi_core)
```

`picard.py`:
```python
def solve_picard(
    N_init: float, N_final: float, delta_Nstar: float, alpha: float,
    H_sq_nl_init: float, grid, trajectory, potential, diffusion_model,
    atol: float, rtol: float, phi_end: float,
    disable_spatial_coupling: bool = False, instrument_stiffness: bool = True,
    label: Optional[str] = None, verbose: bool = False,
    full_instanton_seed: Optional[dict] = None,
    theta: float = DEFAULT_SAT_THETA, anderson_m: int = DEFAULT_ANDERSON_M,
    seed_profile: str = DEFAULT_SEED_PROFILE,
    wallclock_budget_seconds: Optional[float] = None,
    max_step: Optional[float] = None,
) -> dict:
    ...
    def _fwd_rhs(N, y, rfield_splines, rmom_splines, g_pi_core_spline, lam):
        _check_deadline()
        return forward_rhs(
            N, y, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
            rfield_splines, rmom_splines, diffusion_model, g_pi_core_spline,
            disable_spatial_coupling=disable_spatial_coupling, lam=lam,
        )
```

`GradientCoupledInstanton.py` (Ray remote):
```python
@ray.remote
def _compute_gradient_coupled_instanton(
    trajectory, dm, cosmo_T_CMB_Kelvin: float, n_collocation_points: int,
    alpha: float, N_init: float, N_final: float, delta_Nstar: float,
    N_sample: list, atol: float, rtol: float, store_full_values: bool,
    instrument_stiffness: bool = True, label: Optional[str] = None,
    full_instanton=None, wallclock_budget_seconds: Optional[float] = None,
    max_step: Optional[float] = None,
) -> dict:
```

## Task

1. **`forward_rhs.py`**: add `tau_multiplier: float = 1.0` as the new final
   keyword parameter. Change `tau = abs(A_core)` to
   `tau = tau_multiplier * abs(A_core)`. Add a short paragraph to the
   existing large comment block immediately above (do not delete or rewrite
   the existing two-hardening history — append to it) noting that
   `tau_multiplier` exposes this value for diagnostic sensitivity sweeps
   (`tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`
   Diagnostic 8t/11), default `1.0` reproducing the `21a`-derived production
   value exactly.
2. **`picard.py`**: add `tau_multiplier: float = 1.0` to `solve_picard`'s
   own signature (module-level default constant `DEFAULT_TAU_MULTIPLIER =
   1.0` next to `DEFAULT_SAT_THETA`/`DEFAULT_ANDERSON_M`/
   `DEFAULT_SEED_PROFILE`, same convention). Pass it straight through in the
   `forward_rhs(...)` call inside `_fwd_rhs` — `tau_multiplier=tau_multiplier`
   — relying on closure capture exactly as `alpha`/`disable_spatial_coupling`
   already are; no change to `_fwd_rhs`'s own call signature.
3. **`GradientCoupledInstanton.py`**: add `tau_multiplier: float = 1.0` to
   `_compute_gradient_coupled_instanton`'s signature, passed straight through
   to its own `solve_picard(...)` call — the same threading pattern already
   used for `wallclock_budget_seconds`/`max_step` (prompt 24 prerequisite:
   present in the Ray remote's signature, forwarded to `solve_picard`, **not**
   part of the object's persisted identity or query key). This step is
   included for consistency with that precedent, not because prompt 28's
   diagnostics need it — they call `solve_picard` directly, bypassing Ray
   entirely, same as every other diagnostic in this package.
4. Update `forward_rhs`'s and `solve_picard`'s own docstrings to document
   the new parameter in the same style/detail as neighbouring parameters
   (`lam`, `wallclock_budget_seconds`).

## Constraints

- Default `tau_multiplier=1.0` at every call site — this commit changes
  behaviour for nobody who doesn't explicitly pass a different value.
- `tau_multiplier` must reach `forward_rhs`'s core-SAT-penalty line via
  ordinary parameter threading/closure capture — no monkeypatching, no
  module-level mutable state, no environment variable.
- Do not touch `alpha`, `n_collocation_points`, or anything under
  `Datastore/`/`config/` — this parameter is deliberately outside that
  system (see "Context to read first").
- Do not change `tau`'s sign convention, `w_core`, `g_phi_core`, or
  `g_pi_core` — only the scalar multiplying `abs(A_core)`.

## Must NOT

- Must NOT add a `Datastore/SQL/ObjectFactories/tau_*.py` factory, a
  `InflationConcepts/tau_*.py` concept class, or any `config/sharding.py`
  registration. `tau_multiplier` is not part of any object's persisted
  identity.
- Must NOT add `tau_multiplier` to `GradientCoupledInstanton`'s factory
  lookup/query key, mirroring exactly how `full_instanton` itself is
  excluded (see `21a-production-port-notes.md` §3's own note: "not part of
  the object's persisted identity... by design, since it can only affect
  how fast/whether a solve converges").
- Must NOT implement `diagnostic_8_tau_sensitivity` or any new
  n≥9-tau-unlock diagnostic in this commit — that is prompt 28, dependent on
  this one landing first.
- Must NOT change the default value of `tau` (i.e. `tau_multiplier=1.0` must
  compute bit-for-bit the same `tau` as today's hardcoded `abs(A_core)`).

## Acceptance test

- [ ] `forward_rhs(..., tau_multiplier=1.0)` (the default) produces
      bit-for-bit identical output to the pre-change `forward_rhs(...)` on
      every existing test fixture that exercises the SAT penalty.
- [ ] `solve_picard(..., tau_multiplier=1.0)` (the default, i.e. every
      pre-existing call site, which does not pass this argument at all)
      reproduces the existing golden results bit-for-bit:
      `delta_Nstar∈{0.2,0.3,0.5,0.7}`, `m/Mp=1e-2`, `n=5` (Diagnostic 4's own
      results) and the `n=7` control point from Diagnostic 10.
- [ ] A new regression test,
      `tests/test_forward_rhs.py::test_tau_multiplier_default_reproduces_production_tau`,
      asserts `tau_multiplier=1.0` gives `tau == abs(A_core)` exactly (not
      just "close"), and a second new test asserts
      `tau_multiplier=2.0` gives `tau == 2.0 * abs(A_core)` exactly.
- [ ] `_compute_gradient_coupled_instanton`'s existing test suite passes
      unmodified (the new parameter's default must not require updating any
      existing call site).
- [ ] `git diff --stat` shows changes confined to `forward_rhs.py`,
      `picard.py`, `GradientCoupledInstanton.py`, and their associated test
      files — no `Datastore/`, `config/`, or `InflationConcepts/` changes.
- [ ] Full test suite (`pytest -m "not integration"`, per
      `.claude/rules/test-selection.md`) passes with zero new failures
      relative to the pre-change baseline.

## Decision point

None — report back once landed so prompt 28 (Diagnostic 8t completion +
the n≥9 tau-unlock sweep) can proceed.
