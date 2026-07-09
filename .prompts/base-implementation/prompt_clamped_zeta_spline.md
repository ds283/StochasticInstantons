# Prompt: Clamped boundary condition on the ζ spline in `_compute_instanton_path`

## Context

`ComputeTargets/CompactionFunction.py`, function `_compute_instanton_path`, Step D.

The compaction function C(r) = (2/3)[1 − (1 + r ζ′(r))²] is sensitive to the
derivative ζ′(r), which is obtained from a cubic B-spline fitted to the sample
points (r_v, zeta_v).  The default `not-a-knot` endpoint condition leaves the
first derivative at both ends unconstrained, producing spurious spikes in C(r)
at the inner and outer grid boundaries.

The physical boundary conditions on ζ(r) are known exactly:

- **Small-r**: ζ = δN★ (flat inner plateau) → dζ/dr = 0.
- **Large-r**: ζ = 0 (flat outer background) → dζ/dr = 0.

Because the spline is built in log-r space (x_transform='log'), the correct
condition is dζ/d(log r) = 0 at both endpoints — i.e. the "clamped" boundary
condition.  `scipy.interpolate.make_interp_spline` accepts this directly via
`bc_type="clamped"`, which is the named alias for `([(1, 0.0)], [(1, 0.0)])`.

## Changes required

### 1. `Interpolation/spline_wrapper.py` — add `bc_type` parameter to `SplineWrapper`

Add an optional `bc_type` parameter (default `None`) to `SplineWrapper.__init__`
and pass it through to `make_interp_spline`.  All existing call sites pass no
`bc_type` and must be unaffected.

Replace the current `__init__` signature and `make_interp_spline` call:

```python
    def __init__(
        self,
        x,
        y,
        x_transform: str = 'linear',
        y_transform: str = 'linear',
        k: int = 3,
    ):
        ...
        self._spline = make_interp_spline(x_t, y_t, k=k)
```

with:

```python
    def __init__(
        self,
        x,
        y,
        x_transform: str = 'linear',
        y_transform: str = 'linear',
        k: int = 3,
        bc_type=None,
    ):
        ...
        self._spline = make_interp_spline(x_t, y_t, k=k, bc_type=bc_type)
```

No other methods in `SplineWrapper` or `_SplineDerivativeWrapper` require any
change.

### 2. `ComputeTargets/CompactionFunction.py` — use `bc_type="clamped"` for the ζ spline only

In `_compute_instanton_path`, Step D, change the single line that constructs
`zeta_spline`:

```python
    zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3)
```

to:

```python
    zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3,
                                bc_type="clamped")
```

The second `SplineWrapper` in Step D (`cumulative_at_r`) must **not** be
changed — its boundary behaviour is not governed by the same physical
argument.

## Acceptance criteria

- [ ] `SplineWrapper.__init__` accepts `bc_type=None` as an optional keyword
  argument and passes it to `make_interp_spline`.
- [ ] All existing `SplineWrapper(...)` call sites in the codebase pass no
  `bc_type` and continue to behave identically (default `None` → not-a-knot,
  same as before).
- [ ] The `zeta_spline` in `_compute_instanton_path` is constructed with
  `bc_type="clamped"`.
- [ ] The `cumulative_at_r` spline in `_compute_instanton_path` is
  **unchanged** (no `bc_type`).
- [ ] No other files are modified.

## Out of scope

- Any anchor-point augmentation of (r_v, zeta_v) — this approach is
  superseded by the boundary condition fix and must not be added.
- Changes to `_SplineDerivativeWrapper`.
- Changes to Steps A, B, C, E, F or to `store()` / `_populate_from_result()`.
- Any plotting changes.
- Any datastore schema changes.
