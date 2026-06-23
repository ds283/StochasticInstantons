# Prompt: Spline boundary oversampling in `_compute_instanton_path`

## Context

`ComputeTargets/CompactionFunction.py`, function `_compute_instanton_path`, Step D.

The compaction function C(r) = (2/3)[1 − (1 + r ζ′(r))²] is sensitive to the
derivative ζ′(r). That derivative is obtained from a cubic B-spline fitted to
the (r_v, zeta_v) sample points. Cubic splines are unreliable near their
endpoints — the derivative there is controlled by the natural/not-a-knot
boundary condition rather than by data.

The physical boundary conditions on ζ(r) are known exactly:

- **Small-r**: ζ(r) = δN★ (constant) for r < r_v[0], so ζ′ = 0.
- **Large-r**: ζ(r) = 0 (constant) for r > r_v[-1], so ζ′ = 0.

The fix is to augment (r_v, zeta_v) with a small number of "anchor" points
beyond each endpoint before constructing the spline, then trim the output back
to the original r_v range before computing C_v and C_bar_v.

## Change required

All changes are confined to **`ComputeTargets/CompactionFunction.py`**,
inside `_compute_instanton_path`, **Step D only**.

### 1. Add a module-level constant near the top of the file (after the imports)

```python
# Number of anchor points added beyond each endpoint of the (r, zeta) grid
# before constructing the zeta spline, to suppress endpoint derivative artefacts.
# Points are spaced geometrically at factors of SPLINE_ANCHOR_FACTOR from the
# last real sample; they carry the known flat boundary value of zeta.
_N_SPLINE_ANCHORS = 4
_SPLINE_ANCHOR_FACTOR = 3.0   # each successive anchor is this many times further out
```

### 2. Replace Step D in `_compute_instanton_path`

Replace the existing Step D block:

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
```

with:

```python
    # ── Step D: zeta(r), C(r), C_bar(r) ─────────────────────────────────
    #
    # Augment (r_v, zeta_v) with anchor points beyond each endpoint before
    # building the spline.  The physical boundary conditions are:
    #   r < r_v[0]  : zeta = delta_Nstar  (flat inner plateau)
    #   r > r_v[-1] : zeta = 0            (flat outer background)
    # Anchoring the spline to these known values suppresses the endpoint
    # derivative artefacts that arise from the natural/not-a-knot condition.
    #
    # delta_Nstar value for the inner boundary:
    zeta_inner = float(instanton_obj._delta_Nstar)

    r_lo_anchors = np.array(
        [r_v[0] / (_SPLINE_ANCHOR_FACTOR ** j) for j in range(1, _N_SPLINE_ANCHORS + 1)]
    )[::-1]   # ascending order: smallest r first
    zeta_lo_anchors = np.full(_N_SPLINE_ANCHORS, zeta_inner)

    r_hi_anchors = np.array(
        [r_v[-1] * (_SPLINE_ANCHOR_FACTOR ** j) for j in range(1, _N_SPLINE_ANCHORS + 1)]
    )
    zeta_hi_anchors = np.zeros(_N_SPLINE_ANCHORS)

    r_aug   = np.concatenate([r_lo_anchors,   r_v,      r_hi_anchors])
    zeta_aug = np.concatenate([zeta_lo_anchors, zeta_v,  zeta_hi_anchors])

    zeta_spline = SplineWrapper(r_aug, zeta_aug, x_transform='log', k=3)
    zeta_prime = zeta_spline.derivative()

    # Evaluate C and the dense integration grid only over the original r_v range.
    C_v = np.array(
        [
            (2.0 / 3.0) * (1.0 - (1.0 + r_v[i] * float(zeta_prime(r_v[i]))) ** 2)
            for i in range(len(r_v))
        ]
    )

    type_II = bool(np.any(C_v < -1.0))

    # Dense grid for C_bar integration — span original data range only
    N_dense = max(10 * len(r_v), 500)
    r_dense = np.linspace(r_v[0], r_v[-1], N_dense)
    zeta_dense = zeta_spline(r_dense)
    zeta_prime_dense = zeta_prime(r_dense)
```

Everything after this point (the cumulative integral, `cumulative_at_r`,
`C_bar_v`, Steps E and F) is **unchanged**.

## Acceptance criteria

- [ ] `_N_SPLINE_ANCHORS` and `_SPLINE_ANCHOR_FACTOR` are defined as
  module-level constants near the top of the file.
- [ ] The anchor arrays `r_lo_anchors`, `zeta_lo_anchors`, `r_hi_anchors`,
  `zeta_hi_anchors` are constructed geometrically as described.
- [ ] The augmented arrays `r_aug` / `zeta_aug` are used to construct
  `zeta_spline`; the original `r_v` / `zeta_v` arrays are **not** modified.
- [ ] `C_v`, `r_dense`, and all subsequent computations use the original `r_v`
  range, not the augmented range.
- [ ] No other functions or files are modified.
- [ ] The slow-roll path (which shares this function via `is_slow_roll=True`)
  also benefits automatically, since `instanton_obj._delta_Nstar` is
  accessible on both `FullInstanton` and `SlowRollInstanton` objects.

## Out of scope

- Changes to `SplineWrapper` or `_SplineDerivativeWrapper`.
- Changes to Steps A, B, C, E, F or to the `store()` / `_populate_from_result()`
  methods.
- Any plotting changes.
- Any datastore schema changes.
