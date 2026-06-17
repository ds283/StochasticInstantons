# Implementation prompt: `FullInstanton` boundary condition refactor and noiseless equations extraction

## Context

This prompt describes two tightly coupled changes to the `StochasticInstanton` codebase:

1. Extract the noiseless inflationary background ODE into a shared module
   `InflationConcepts/noiseless_equations.py` so it can be reused without
   duplication.
2. Revise the boundary conditions of `_compute_full_instanton` so that the
   instanton connects smoothly to the noiseless background at both endpoints.

These changes are prerequisite to implementing the `CompactionFunction` compute
target. No changes to `SlowRollInstanton` are required at this stage.

All file paths in this prompt use the **source-tree** layout, not the flat
`claude-context` layout.

---

## 1. New file: `InflationConcepts/noiseless_equations.py`

Create this file. It must contain three public symbols, and nothing else.

### 1.1 `noiseless_rhs(N, y, potential)`

A plain module-level function (no Ray, no class). Implements the right-hand
side of the noiseless inflationary background ODE:

```
dφ/dN = π
dπ/dN = -(3 - ε) π - V′(φ) / H²
```

where `ε = potential.epsilon(phi, pi)` and `H² = potential.H_sq(phi, pi)`.

Signature:

```python
def noiseless_rhs(N: float, y: list, potential: AbstractPotential) -> list:
```

Returns `[dphi_dN, dpi_dN]` as a plain Python list.

### 1.2 `end_of_inflation_event(N, y, potential)`

A plain module-level function that returns `potential.epsilon(y[0], y[1]) - 1.0`.
After definition, the caller is responsible for setting `.terminal = True` and
`.direction = +1` on the bound version passed to `solve_ivp`. Do not set these
attributes on the function itself (they are instance attributes of a bound
closure, not of the bare function).

Signature:

```python
def end_of_inflation_event(N: float, y: list, potential: AbstractPotential) -> float:
```

### 1.3 `integrate_noiseless_trajectory(phi0, pi0, potential, atol, rtol, label=None)`

A plain module-level function that encapsulates the full solver fallback chain
currently embedded in `_compute_inflaton_trajectory`. This is the single
implementation of "integrate the noiseless equations from `(phi0, pi0)` until
`ε = 1`".

Signature:

```python
def integrate_noiseless_trajectory(
        phi0: float,
        pi0: float,
        potential: AbstractPotential,
        atol: float,
        rtol: float,
        label: Optional[str] = None,
) -> tuple[object, str, list]:
```

Returns `(sol, solver_used, solver_attempts)` where:

- `sol` is the `scipy.integrate.OdeSolution` object (or `None` on total
  failure), with `dense_output=True` so the caller can evaluate it at
  arbitrary `N` values
- `solver_used` is the name of the solver that succeeded, or `None`
- `solver_attempts` is the list of attempt dicts already used in the existing
  fallback chain

Internal behaviour:

- Tries the solver chain `["RK45", "DOP853", "Radau", "BDF", "LSODA"]` in
  order, exactly as in the current `_compute_inflaton_trajectory`
- Uses `noiseless_rhs` (via a `lambda` or `functools.partial` that binds
  `potential`) as the RHS
- Uses `end_of_inflation_event` (again with `potential` bound) as the terminal
  event, with `.terminal = True` and `.direction = +1` set on the bound closure
- Passes `dense_output=True` to every `solve_ivp` call
- Accepts a candidate solution if `candidate.success or candidate.status == 1`
  (i.e. terminated by event), consistent with existing logic
- Prints fallback diagnostics if `label` is provided

The `N_span` upper limit should remain `(0.0, 1000.0)`.

---

## 2. Refactor `ComputeTargets/InflatonTrajectory.py`

### 2.1 Replace the inline ODE with calls to the shared module

In `_compute_inflaton_trajectory`, delete the inline `rhs`, `end_of_inflation`
definitions and the solver fallback loop. Replace with a single call:

```python
from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory

sol, solver_used, solver_attempts = integrate_noiseless_trajectory(
    phi0_value, pi0_value, potential, atol, rtol, label=label
)
```

All subsequent logic (`N_end` extraction, sample grid construction, return
dict assembly, diagnostics) is unchanged.

### 2.2 Add `rho_at(N)` interpolation method to `InflatonTrajectory`

Add alongside `phi_at` and `pi_at`:

```python
def rho_at(self, N: float) -> float:
    """
    Interpolate energy density ρ = V(φ)/(1 - ε/3) at arbitrary N,
    using the splines already built for φ and π.
    """
```

Compute as:

```
phi = self.phi_at(N)
pi  = self.pi_at(N)
rho = self._potential.H_sq(phi, pi) * 3.0 * Mp²
```

where `Mp` is `self._potential._units.PlanckMass`. Do not recompute from `V`
and `epsilon` separately — use `H_sq` directly since `ρ = 3 Mp² H²` is exact.
This is the single correct implementation; do not use the `V/(1 - ε/3)` form
as that introduces an unnecessary intermediate.

---

## 3. Refactor `ComputeTargets/FullInstanton.py`

### 3.1 Change the initial momentum boundary condition

In `FullInstanton.compute()`, the current code reads:

```python
pi_SR = traj.pi_at(N_end - float(self._N_init))
```

and passes `pi_SR_init=pi_SR` to `_compute_full_instanton`. This is correct —
`pi_at` already returns the actual trajectory momentum, not a slow-roll
approximation. **Verify** that the argument is named unambiguously in the
remote function signature. Rename the parameter from `pi_SR_init` to
`pi_init` throughout (in the remote function signature, the call site in
`compute()`, and the internal variable name in the Picard body) to remove the
misleading implication that this is a slow-roll value.

Inside `_compute_full_instanton`, the initial background guess currently
integrates from `[phi_init, pi_SR_init]`. This becomes `[phi_init, pi_init]`
after the rename. No other change.

### 3.2 Change the final boundary condition from fixed `φ_final` to fixed `ρ_final`

This is the substantive change. The outer Newton loop currently tunes `λ =
P₁(N_total)` to drive `φ₁(N_total) → phi_final`. Replace this with tuning `λ`
to drive `ρ(N_total) → rho_final`, where:

```
rho_final = 3 * Mp² * H_sq(phi_final_noiseless, pi_final_noiseless)
```

and `(phi_final_noiseless, pi_final_noiseless)` are the field values read from
`InflatonTrajectory` at `N_end - N_final`.

Concretely:

**In `FullInstanton.compute()`**, replace:

```python
phi_final = traj.phi_at(N_end - float(self._N_final))
```

with:

```python
rho_final = traj.rho_at(N_end - float(self._N_final))
```

and pass `rho_final=rho_final` instead of `phi_final=phi_final` to the remote
function.

**In `_compute_full_instanton`**, replace the `phi_final: float` parameter with
`rho_final: float`. The residual in the outer Newton loop becomes:

```python
def compute_rho(phi1_val, phi2_val):
    Mp = potential._units.PlanckMass
    return 3.0 * (Mp ** 2) * potential.H_sq(phi1_val, phi2_val)


residual = compute_rho(p1[-1], p2[-1]) - rho_final
```

The Newton finite-difference step perturbs `lam` and evaluates the same
`compute_rho` at the new endpoint. The fallback nudge becomes:

```python
lam += (rho_final - compute_rho(p1[-1], p2[-1])) * scale
```

where `scale` is a small positive constant (e.g. `0.1`), chosen to move `λ` in
a direction that reduces the residual. The sign of `d(rho)/d(lambda)` must be
determined numerically (it is already determined by the finite-difference Newton
step), so the fallback nudge direction may need to be corrected by a sign check.

**The `phi_final` parameter is removed entirely** from `_compute_full_instanton`.
It is no longer needed. The function signature becomes:

```python
@ray.remote
def _compute_full_instanton(
        trajectory,
        phi_init: float,
        pi_init: float,
        rho_final: float,
        N_total: float,
        N_sample: list,
        atol: float,
        rtol: float,
        label: Optional[str] = None,
) -> dict:
```

### 3.3 Convergence tolerance

The outer tolerance `OUTER_TOL` is currently a dimensionless field-space
residual. After this change it becomes an energy-density residual in units of
`Mp⁴`. Set it as a relative tolerance:

```python
OUTER_TOL = rho_final * max(atol * 100.0, 1e-6)
```

so that the convergence criterion scales correctly with the magnitude of
`rho_final`.

### 3.4 Diagnostics

In the returned `diagnostics` dict, replace `"final_phi1"` (if present) with
`"final_rho"` recording `compute_rho(p1[-1], p2[-1])` at convergence, and add
`"rho_final_target": rho_final` for ease of post-hoc inspection.

### 3.5 No changes to `FullInstantonValue`, `FullInstanton` (driver class), or `FullInstantonProxy`

The stored data (φ₁, φ₂, P₁, P₂ at each sample point, MSR action) is
unchanged. The database schema (`Datastore/SQL/ObjectFactories/FullInstanton.py`)
does not need to change.

---

## 4. Acceptance criteria

After these changes:

1. `InflatonTrajectory` produces identical results to before (the ODE is the
   same, only refactored into the shared module). Verify by running the
   trajectory pipeline on an existing test case and checking that `N_end`,
   `phi`, and `pi` arrays are unchanged.

2. `FullInstanton.compute()` no longer accepts or uses a `phi_final` argument.
   The `pi_SR_init` argument is renamed `pi_init` everywhere.

3. At convergence, `compute_rho(phi1[-1], phi2[-1])` equals `rho_final` to
   within `OUTER_TOL`.

4. `InflatonTrajectory.rho_at(N)` returns a positive float for all `N` in
   `[0, N_end]`, and agrees with `3 * Mp² * H_sq(phi_at(N), pi_at(N))` at
   spot-checked points.

5. `InflationConcepts/noiseless_equations.py` has no Ray imports, no class
   definitions, and no reference to `InflatonTrajectory` or `FullInstanton`.

6. The `_compute_full_instanton` remote function has no reference to
   `phi_final`.

---

## 5. Notes and cautions

- **Single source of truth for the noiseless ODE.** After this refactor,
  `noiseless_rhs` in `InflationConcepts/noiseless_equations.py` is the only
  place where `dφ/dN` and `dπ/dN` are written down. If the field equations
  ever change (e.g. multi-field extension, non-minimal coupling), only this
  function needs updating.

- **`FullInstanton` does not import `noiseless_equations`.** It receives a
  pre-computed `InflatonTrajectoryProxy` and reads boundary values from it via
  `phi_at`, `pi_at`, and `rho_at`. It does not re-integrate the background.

- **The Picard inner loop is unchanged.** The only changes to the Picard body
  are: (a) the initial condition uses `pi_init` instead of `pi_SR_init`, and
  (b) the residual in the outer Newton loop is computed from `rho` rather than
  `phi1`. The backward and forward ODE passes are identical.

- **`SlowRollInstanton` is not touched.** Under slow roll, surfaces of constant
  `φ` and constant `ρ` coincide to leading order, so its existing boundary
  condition remains appropriate.

- **Database compatibility.** The stored columns are unchanged, so existing
  databases remain valid. However, any previously computed `FullInstanton`
  entries were computed with the old `phi_final` boundary condition and should
  be considered superseded. If the database contains existing results, drop and
  recompute the `FullInstanton` sharded tables.