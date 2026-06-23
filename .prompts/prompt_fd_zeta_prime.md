# Prompt: Finite-difference ζ′ on an augmented dense grid in `_compute_instanton_path`

## Context

`ComputeTargets/CompactionFunction.py`, function `_compute_instanton_path`, Step D.

The compaction function C(r) = (2/3)[1 − (1 + r ζ′(r))²] requires an accurate
derivative ζ′(r).  The current approach computes ζ′ from the chain-rule
derivative of a cubic B-spline fitted to (r_v, zeta_v).  This produces
spurious spikes in C(r) at both endpoints because the spline's endpoint
behaviour is not constrained by the known physical boundary values:

- ζ(r) = δN★  for r ≤ r_v[0]   (flat inner plateau, ζ′ = 0)
- ζ(r) = 0    for r ≥ r_v[-1]  (flat outer background, ζ′ = 0)

The fix is to:

1. Evaluate the spline on the existing dense grid `r_dense` to obtain
   smoothed ζ values.
2. Prepend the exact boundary point (r_v[0], δN★) and append (r_v[-1], 0)
   to that dense array.
3. Compute ζ′ numerically via `np.gradient` in log-r space on the augmented
   array.  Using log-r coordinates means `np.gradient` returns dζ/d(log r)`,
   which must be divided by r to give dζ/dr.
4. Evaluate C(r) and the C̄ integrand from these finite-difference derivatives
   rather than from the spline derivative callable.
5. Remove the now-unused `zeta_prime = zeta_spline.derivative()` line and
   the `_SplineDerivativeWrapper` call sites in this function.

## Starting state

The file is the version visible in the project (no clamped-BC or anchor
changes are present).  Step D currently reads:

```python
    # ── Step D: zeta(r), C(r), C_bar(r) ─────────────────────────────────
    zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3)
    zeta_prime = zeta_spline.derivative()

    C_v = np.array(
        [
            (2.0 / 3.0) * (1.0 - (1.0 + r_v[i] * float(zeta_prime(r_v[i]))) ** 2)
            for i in range(len(r_v))
        ]
    )

    type_II = bool(np.any(C_v < -1.0))

    # Dense grid for C_bar integration
    N_dense = max(10 * len(r_v), 500)
    r_dense = np.linspace(r_v[0], r_v[-1], N_dense)
    zeta_dense = zeta_spline(r_dense)
    zeta_prime_dense = zeta_prime(r_dense)

    rz_dense = r_dense * zeta_prime_dense
    integrand = (
        r_dense**2
        * np.exp(3.0 * zeta_dense)
        * (2.0 * rz_dense + 3.0 * rz_dense**2 + rz_dense**3)
    )

    # Accumulate integral to each sample r_i using trapezoid
    cumulative = np.zeros(N_dense)
    for j in range(1, N_dense):
        cumulative[j] = cumulative[j - 1] + 0.5 * (integrand[j - 1] + integrand[j]) * (
            r_dense[j] - r_dense[j - 1]
        )

    # Interpolate cumulative integral to sample points.
    # r_v is a subset of [r_dense[0], r_dense[-1]] by construction so no
    # extrapolation occurs.
    cumulative_at_r = SplineWrapper(r_dense, cumulative, x_transform='log', k=3)

    C_bar_v = np.array(
        [
            -2.0 * float(cumulative_at_r(r_v[i])) / (r_v[i] ** 3 * exp(3.0 * zeta_v[i]))
            for i in range(len(r_v))
        ]
    )
```

## Required replacement for Step D

Replace the entire Step D block above with:

```python
    # ── Step D: zeta(r), C(r), C_bar(r) ─────────────────────────────────
    #
    # Strategy: evaluate zeta on a dense grid via the spline (for smoothing),
    # then augment with the exact boundary values at both endpoints before
    # computing zeta' by finite differences in log-r space.  This avoids
    # spline endpoint-derivative artefacts while preserving the smoothing
    # benefit of the spline in the interior.

    zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3)

    # Dense grid spanning the sample range (interior only at this stage)
    N_dense = max(10 * len(r_v), 500)
    r_dense_interior = np.linspace(r_v[0], r_v[-1], N_dense)
    zeta_dense_interior = zeta_spline(r_dense_interior)

    # Augment with exact boundary values.
    # By construction: zeta(r_v[0]) = delta_Nstar, zeta(r_v[-1]) = 0.
    # Replace the first and last points of the dense grid with these exact
    # values so that np.gradient sees the correct slope at each end.
    zeta_inner = float(instanton_obj._delta_Nstar)

    r_aug    = r_dense_interior.copy()
    zeta_aug = zeta_dense_interior.copy()
    zeta_aug[0]  = zeta_inner   # exact left boundary
    zeta_aug[-1] = 0.0          # exact right boundary

    # Finite-difference dζ/d(log r) on the augmented grid, then convert to
    # dζ/dr = [dζ/d(log r)] / r.
    log_r_aug = np.log(r_aug)
    dzeta_dlogr_aug = np.gradient(zeta_aug, log_r_aug)
    zeta_prime_aug  = dzeta_dlogr_aug / r_aug   # dζ/dr in original coords

    # Interpolate dζ/dr back to the sample points r_v for C(r).
    zeta_prime_at_rv = SplineWrapper(r_aug, zeta_prime_aug, x_transform='log', k=3)

    C_v = np.array(
        [
            (2.0 / 3.0) * (1.0 - (1.0 + r_v[i] * float(zeta_prime_at_rv(r_v[i]))) ** 2)
            for i in range(len(r_v))
        ]
    )

    type_II = bool(np.any(C_v < -1.0))

    # C_bar integration uses the dense grid directly — zeta and zeta_prime
    # are already available on r_aug / zeta_prime_aug.
    r_dense       = r_aug
    zeta_dense    = zeta_aug
    zeta_prime_dense = zeta_prime_aug

    rz_dense = r_dense * zeta_prime_dense
    integrand = (
        r_dense**2
        * np.exp(3.0 * zeta_dense)
        * (2.0 * rz_dense + 3.0 * rz_dense**2 + rz_dense**3)
    )

    # Accumulate integral to each sample r_i using trapezoid
    cumulative = np.zeros(N_dense)
    for j in range(1, N_dense):
        cumulative[j] = cumulative[j - 1] + 0.5 * (integrand[j - 1] + integrand[j]) * (
            r_dense[j] - r_dense[j - 1]
        )

    # Interpolate cumulative integral to sample points.
    # r_v is a subset of [r_dense[0], r_dense[-1]] by construction so no
    # extrapolation occurs.
    cumulative_at_r = SplineWrapper(r_dense, cumulative, x_transform='log', k=3)

    C_bar_v = np.array(
        [
            -2.0 * float(cumulative_at_r(r_v[i])) / (r_v[i] ** 3 * exp(3.0 * zeta_v[i]))
            for i in range(len(r_v))
        ]
    )
```

## Acceptance criteria

- [ ] `zeta_spline` is still constructed from `(r_v, zeta_v)` with
  `x_transform='log'` exactly as before — it is used to evaluate
  `zeta_dense_interior` but its `.derivative()` method is **not called**.
- [ ] The augmented arrays `r_aug` and `zeta_aug` differ from
  `r_dense_interior` / `zeta_dense_interior` only at index 0 (set to
  `zeta_inner = float(instanton_obj._delta_Nstar)`) and index -1 (set to
  0.0).
- [ ] `zeta_prime_aug` is computed via `np.gradient(zeta_aug, log_r_aug)
  / r_aug` — not from any spline derivative callable.
- [ ] `zeta_prime_at_rv` is a fresh `SplineWrapper` fitted to
  `(r_aug, zeta_prime_aug)` with `x_transform='log'` and used only to
  evaluate C_v at the sample points r_v.
- [ ] The C̄ integration loop operates on `r_dense = r_aug` and
  `zeta_prime_dense = zeta_prime_aug` — no separate dense grid is
  constructed for the integration.
- [ ] `N_dense` retains its current definition:
  `max(10 * len(r_v), 500)`.
- [ ] Steps A, B, C, E, F and all code after Step D are **unchanged**.
- [ ] No other files are modified.
- [ ] `_SplineDerivativeWrapper` is not called anywhere in
  `_compute_instanton_path` after this change.

## Out of scope

- Changes to `SplineWrapper` or `_SplineDerivativeWrapper`.
- Any anchor-point augmentation of `(r_v, zeta_v)`.
- Any `bc_type` changes to any spline construction.
- Changes to the `store()` / `_populate_from_result()` methods.
- Any plotting changes.
- Any datastore schema changes.
