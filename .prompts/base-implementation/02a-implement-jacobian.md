# Correction prompt: fix Newton convergence in `_compute_full_instanton`

## Background

The previous refactoring prompt (`prompt_full_instanton_refactor.md`) has been
applied. The outer Newton loop now targets `ρ(N_total) = rho_final` instead of
`φ₁(N_total) = phi_final`. However, the loop is not converging — `ρ(T)` is
completely unresponsive to `λ` across iterations.

The cause is that the finite-difference Jacobian `dres/dlam` is being computed
as though the residual is a function of `φ₁` alone:

```python
dres_dlam = (p1_p[-1] - p1[-1]) / dlam
```

But the residual is now `ρ(φ₁, φ₂) - rho_final`, which depends on both `φ₁`
and `φ₂`. Near the slow-roll attractor `V(φ)` is extremely flat, so
`∂ρ/∂φ₁ · dφ₁/dλ` is tiny — the dominant sensitivity runs through `φ₂` (the
field momentum). The incorrect single-component Jacobian therefore sees
`dres/dlam ≈ 0`, the Newton step degenerates to the fallback nudge, and `λ`
marches linearly while `ρ(T)` does not move.

The fix is to compute the correct two-component Jacobian analytically and
combine it with the already-available finite-difference sensitivities
`dφ₁/dλ` and `dφ₂/dλ`.

---

## 1. Add two methods to `CosmologyConcepts/Potentials/AbstractPotential.py`

These are concrete (non-abstract) methods on the base class, expressible
entirely in terms of existing methods `V()`, `dV_dphi()`, and `epsilon()`.
No subclass changes are required.

### 1.1 `drho_dphi(self, phi, pi)`

```python
def drho_dphi(self, phi: float, pi: float) -> float:
    """
    Partial derivative of energy density ρ with respect to φ, at fixed π.

    ρ = V(φ) / (1 - ε/3)   where ε = π²/(2Mp²)

    ∂ρ/∂φ = V′(φ) / (1 - ε/3)

    Note: ε does not depend on φ for canonical inflation, so the denominator
    is constant under this partial derivative.
    """
    return self.dV_dphi(phi) / (1.0 - self.epsilon(phi, pi) / 3.0)
```

### 1.2 `drho_dpi(self, phi, pi)`

```python
def drho_dpi(self, phi: float, pi: float) -> float:
    """
    Partial derivative of energy density ρ with respect to π, at fixed φ.

    ρ = V(φ) / (1 - π²/(6Mp²))

    ∂ρ/∂π = V(φ) · π / (3Mp² · (1 - π²/(6Mp²))²)
           = V(φ) · π / (3Mp² · (1 - ε/3)²)
    """
    Mp2 = self._units.PlanckMass ** 2
    eps = self.epsilon(phi, pi)
    denom = (1.0 - eps / 3.0) ** 2
    return self.V(phi) * pi / (3.0 * Mp2 * denom)
```

Both methods belong immediately after `epsilon()` in the file. Add a blank line
between them and the existing methods for readability.

---

## 2. Fix the Newton Jacobian in `_compute_full_instanton`

In `ComputeTargets/FullInstanton.py`, locate the Newton finite-difference block
inside the outer loop. It currently looks approximately like:

```python
dlam = max(abs(lam) * 1e-4, 1e-6)
p1_p, _, _, _, n_inner_p = picard_inner(lam + dlam, phi1_f, phi2_f)
if p1_p is not None:
    dres_dlam = (p1_p[-1] - p1[-1]) / dlam
    if abs(dres_dlam) > 1e-14:
        lam -= residual / dres_dlam
        continue
```

Replace the `dres_dlam` computation with the full two-component chain rule.
The corrected block:

```python
dlam = max(abs(lam) * 1e-4, 1e-6)
p1_p, p2_p, _, _, n_inner_p = picard_inner(lam + dlam, phi1_f, phi2_f)
picard_iterations_per_outer.append(n_inner_p)
if p1_p is not None:
    phi1_final = p1[-1]
    phi2_final = p2[-1]

    # Sensitivities of endpoint fields to λ (finite difference)
    dphi1_dlam = (p1_p[-1] - phi1_final) / dlam
    dphi2_dlam = (p2_p[-1] - p2[-1]) / dlam

    # Analytical Jacobian of ρ w.r.t. field values at endpoint
    drho_dphi1 = potential.drho_dphi(phi1_final, phi2_final)
    drho_dphi2 = potential.drho_dpi(phi1_final, phi2_final)

    # Chain rule: dρ/dλ = (∂ρ/∂φ₁)(dφ₁/dλ) + (∂ρ/∂φ₂)(dφ₂/dλ)
    dres_dlam = drho_dphi1 * dphi1_dlam + drho_dphi2 * dphi2_dlam

    if abs(dres_dlam) > 1e-30:
        lam -= residual / dres_dlam
        continue
```

Note that the guard threshold is reduced from `1e-14` to `1e-30` because
`dres_dlam` is now a product of energy-density derivatives (dimensionful in
`Mp⁴`) and dimensionless field sensitivities. The appropriate scale is much
smaller than the old pure-field-space threshold.

Also note that `p2_p` must now be captured from `picard_inner` — check that
the call site unpacks all five return values (it currently discards `p2_p`
with `_`).

### Fallback nudge

The fallback nudge (reached when `dres_dlam` is too small or the perturbed
Picard fails) should be updated to use a scale relative to `rho_final`:

```python
newton_fallback_count += 1
sign = -1.0 if residual > 0.0 else 1.0
lam += sign * max(abs(lam) * 0.1, rho_final * 1e-8)
```

This avoids the nudge being either negligibly small (when `lam ≈ 0`) or
arbitrarily scaled.

---

## 3. Diagnostic output

Update the per-iteration print statement to show both `φ₁(T)` and `φ₂(T)`
alongside `ρ(T)`, so convergence behaviour is visible:

```python
if label:
    print(
        f"[{label}] outer {outer}: λ={lam:.4g}, "
        f"φ₁(T)={p1[-1]:.6g}, φ₂(T)={p2[-1]:.6g}, "
        f"ρ(T)={compute_rho(p1[-1], p2[-1]):.6g}, "
        f"res={residual:.2e}"
    )
```

---

## 4. Acceptance criteria

1. For `dNstar=0.1`, `ρ(T)` must change visibly between outer iterations — the
   pathology of a fixed `ρ(T)` across all 50 iterations must be gone.

2. At convergence, `abs(compute_rho(p1[-1], p2[-1]) - rho_final) < OUTER_TOL`.

3. `drho_dphi(phi, pi)` and `drho_dpi(phi, pi)` on the quadratic potential
   agree with a numerical finite difference on `rho_at` to within `1e-6`
   relative error at a spot-checked off-attractor point, e.g.
   `phi=14.0, pi=0.5`.

4. No change to `FullInstantonValue`, `FullInstanton` (driver), `FullInstantonProxy`,
   or any factory or database schema.

---

## 5. Notes

- **Why `drho_dpi` has `(1 - ε/3)²` in the denominator.** Differentiating
  `ρ = V / (1 - π²/6Mp²)` with respect to `π` gives a quotient-rule result
  with the denominator squared. This is not a typo.

- **`drho_dphi` has only `(1 - ε/3)¹` in the denominator.** Because `ε`
  depends only on `π`, not `φ`, the denominator is constant under `∂/∂φ` and
  the quotient rule reduces to dividing `V′` by the denominator once.

- **The perturbed Picard solve for `lam + dlam` is already being done.** This
  fix does not add any ODE solves — it only changes how the already-computed
  result `(p1_p, p2_p)` is used to form the Jacobian.

- **`potential` is accessible inside `_compute_full_instanton`.** It is
  retrieved at the top of the function via `traj = trajectory.get();
  potential = traj._potential`. The new methods `drho_dphi` and `drho_dpi`
  are therefore immediately callable as `potential.drho_dphi(...)` and
  `potential.drho_dpi(...)`.