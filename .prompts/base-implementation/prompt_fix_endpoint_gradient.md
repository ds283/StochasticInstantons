# Prompt: Fix inner-boundary C(r) artefact in `_compute_instanton_path`

## Problem

The current Step D in `_compute_instanton_path` pins `zeta_dense[0]` and
`zeta_dense[-1]` before calling `np.gradient`.  `np.gradient` uses a
three-point one-sided stencil at each endpoint:

    dzeta_dlogr[0] = (-3·f[0] + 4·f[1] - f[2]) / (x[2] - x[0])

Pinning `zeta_dense[0]` to `zeta_inner` while `zeta_dense[1]` and
`zeta_dense[2]` remain at spline values creates a discontinuity that the
stencil amplifies into a wildly wrong derivative — producing `C[0] ≈ -5`
instead of the correct `~0.66`.

The right fix is: do not pin `zeta_dense` at all.  Instead, overwrite
`dzeta_dlogr[0]` **after** `np.gradient` with a simple two-point
forward-difference anchored to the exact inner boundary value.  No
right-endpoint override is needed — `np.gradient` produces the correct
result there when the spline values are smooth.

Numerical verification on two fresh database extracts (id=40 and id=114,
δN★=19.5 and 16.5 respectively, spanning 9 decades in r) confirmed:
- With the override: `C[0]` agrees with `C[1]` to 4 significant figures.
- Without the override: `C[0] ≈ -5` (artefact).
- Right-endpoint: `np.gradient` gives the correct result on its own for
  both full and slow-roll paths; no override is needed.

## File to change

`ComputeTargets/CompactionFunction.py` — Step D only.

## Change

Replace these lines in Step D:

```python
    # Safe boundary pinning: only override when the spline already
    # agrees with the physical boundary value to within _ZETA_PIN_ATOL.
    zeta_inner = float(instanton_obj._delta_Nstar)
    if abs(zeta_dense[0] - zeta_inner) < _ZETA_PIN_ATOL:
        zeta_dense[0] = zeta_inner
    if abs(zeta_dense[-1]) < _ZETA_PIN_ATOL:
        zeta_dense[-1] = 0.0

    # Finite-difference dζ/dr: gradient in log-r then divide by r.
    dzeta_dlogr = np.gradient(zeta_dense, log_r_dense)
    zeta_prime_dense = dzeta_dlogr / r_dense
```

with:

```python
    # Finite-difference dζ/dr: gradient in log-r then divide by r.
    # np.gradient uses a three-point one-sided stencil at the endpoints,
    # which is sensitive to the values of the neighbouring points.  Pinning
    # zeta_dense[0] before the gradient call creates a discontinuity that
    # corrupts the stencil.  Instead, overwrite dzeta_dlogr[0] after the
    # gradient using a two-point forward difference anchored to the exact
    # physical boundary value zeta_inner = delta_Nstar.  No right-endpoint
    # override is needed: the spline is smooth there and np.gradient gives
    # the correct result.
    zeta_inner = float(instanton_obj._delta_Nstar)
    dzeta_dlogr = np.gradient(zeta_dense, log_r_dense)
    dzeta_dlogr[0] = (zeta_dense[1] - zeta_inner) / (log_r_dense[1] - log_r_dense[0])
    zeta_prime_dense = dzeta_dlogr / r_dense
```

Also update the Step D comment block (lines 252–263) to reflect the new
strategy — remove mention of pinning and replace step 3 with:

```
    #   3. Overwrite the left-endpoint derivative after np.gradient using
    #      a two-point forward difference anchored to the exact physical
    #      boundary value ζ = δN★.  The right endpoint needs no correction.
```

## Acceptance criteria

- [ ] The two `zeta_dense[0] = ...` and `zeta_dense[-1] = 0.0` pinning
  lines are removed.
- [ ] `zeta_inner = float(instanton_obj._delta_Nstar)` is computed before
  the gradient call (it is needed for the override).
- [ ] `dzeta_dlogr[0]` is overwritten with
  `(zeta_dense[1] - zeta_inner) / (log_r_dense[1] - log_r_dense[0])`
  immediately after `np.gradient`.
- [ ] No right-endpoint override of `dzeta_dlogr[-1]` is added.
- [ ] The `_ZETA_PIN_ATOL` constant remains in the file (it is referenced
  by the module-level docstring and may be used in future); only its use
  in Step D is removed.
- [ ] All other lines in Step D and the rest of the file are unchanged.
- [ ] No other files are modified.
