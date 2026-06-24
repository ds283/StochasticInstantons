# Prompt: geomspace dense grid, safe boundary pinning, C_min scalars, and deserialisation warnings

## Context

This prompt folds three related fixes into a single commit:

1. **Dense grid fix**: `r_dense` is currently constructed with `np.linspace`,
   giving a linearly-spaced grid over a domain that spans up to 9 decades in
   r.  The vast majority of dense points pile up at large r, leaving the inner
   decade with only a handful of points.  When `np.gradient` divides by the
   log-r spacing of this grid, the first interval (spanning many decades)
   produces wildly inaccurate derivatives.  Fix: use `np.geomspace` so the
   dense grid is uniformly spaced in log r.

2. **Finite-difference ζ′ with safe boundary pinning**: the current
   implementation computes ζ′ from `zeta_spline.derivative()`, which produces
   endpoint artefacts.  Replace it with `np.gradient` on the dense grid, with
   the boundary values pinned to the known physical values (ζ = δN★ at r_v[0],
   ζ = 0 at r_v[-1]).  The pinning must be applied only when the spline value
   at the endpoint is already sufficiently close to the boundary value, to
   avoid introducing a false discontinuity when the endpoint sample has not
   yet reached the asymptotic regime.  The tolerance for "sufficiently close"
   is an absolute difference of 0.01 in ζ units (dimensionless).

3. **C_min scalar, compensated flag, and deserialisation warnings**: store the
   minimum value of C(r) per path as a new scalar column, add a boolean
   `compensated` flag (C_min < 0, i.e. underdense shell present) alongside
   the existing `type_II` flag (C_min < −1), and emit `print` warnings on
   deserialisation from the factory when either flag is set.

## Starting state

Both files are at their current project state — no clamped-BC, anchor, or
geomspace changes are present.

---

## Change 1: `ComputeTargets/CompactionFunction.py`

### 1a. Replace Step D in `_compute_instanton_path`

Replace the entire Step D block:

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

with:

```python
    # ── Step D: zeta(r), C(r), C_bar(r) ─────────────────────────────────
    #
    # Strategy:
    #   1. Fit a spline to (r_v, zeta_v) in log-r space for smoothing.
    #   2. Evaluate on a log-uniform dense grid (geomspace) — essential
    #      because r spans many decades; linspace concentrates all points
    #      at large r, making np.gradient wildly inaccurate at small r.
    #   3. Pin the dense grid endpoints to the known physical boundary
    #      values, but only when the spline value is already close (within
    #      _ZETA_PIN_ATOL) to avoid introducing a false discontinuity.
    #   4. Compute dζ/dr by finite differences (np.gradient in log-r space,
    #      then divide by r) — no spline derivative is used.
    #   5. Interpolate dζ/dr back to r_v via np.interp in log-r space.

    zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3)

    N_dense = max(10 * len(r_v), 500)
    r_dense = np.geomspace(r_v[0], r_v[-1], N_dense)   # log-uniform spacing
    log_r_dense = np.log(r_dense)
    zeta_dense = zeta_spline(r_dense)

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

    # Evaluate dζ/dr at sample points via linear interpolation in log-r.
    log_r_v = np.log(r_v)
    zeta_prime_v = np.interp(log_r_v, log_r_dense, zeta_prime_dense)

    C_v = (2.0 / 3.0) * (1.0 - (1.0 + r_v * zeta_prime_v) ** 2)

    C_min     = float(np.nanmin(C_v))
    type_II   = C_min < -1.0
    compensated = C_min < 0.0

    # C_bar integration — reuse r_dense / zeta_dense / zeta_prime_dense
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

### 1b. Add a module-level constant near the top of the file (after the imports)

```python
# Absolute tolerance on ζ for safe boundary pinning in Step D.
# The dense-grid endpoint is only overridden with the known physical
# boundary value when the spline already agrees within this tolerance,
# to avoid introducing a false discontinuity in the gradient.
_ZETA_PIN_ATOL = 0.01
```

### 1c. Update the result dict returned by `_compute_instanton_path`

In the `return` statement at the end of `_compute_instanton_path`, add the
new scalars to the `"diagnostics"` sub-dict:

```python
        "diagnostics": {
            "type_II": type_II,
            "compensated": compensated,
            "C_min": C_min,
            "n_valid_points": int(np.sum(valid_mask)),
            "n_total_points": len(values),
            "r_max_at_grid_edge": r_max_at_grid_edge,
            "r_peak_at_grid_edge": r_peak_at_grid_edge,
        },
```

### 1d. Expose C_min and compensated as properties on `CompactionFunction`

Add the following properties to the `CompactionFunction` class, grouped with
the existing per-path scalar properties:

```python
    @property
    def C_min_full(self) -> Optional[float]:
        return getattr(self, "_C_min_full", None)

    @property
    def compensated_full(self) -> Optional[bool]:
        return getattr(self, "_compensated_full", None)

    @property
    def type_II_full(self) -> Optional[bool]:
        return getattr(self, "_type_II_full", None)

    @property
    def C_min_slow_roll(self) -> Optional[float]:
        return getattr(self, "_C_min_slow_roll", None)

    @property
    def compensated_slow_roll(self) -> Optional[bool]:
        return getattr(self, "_compensated_slow_roll", None)

    @property
    def type_II_slow_roll(self) -> Optional[bool]:
        return getattr(self, "_type_II_slow_roll", None)
```

### 1e. Populate new scalars in `_populate_from_result`

In `_populate_from_result`, extend the full-instanton block:

```python
        if not full_failed:
            ...
            # existing lines unchanged
            self._C_min_full        = full["diagnostics"].get("C_min")
            self._compensated_full  = full["diagnostics"].get("compensated")
            self._type_II_full      = full["diagnostics"].get("type_II")
```

And the slow-roll block:

```python
        if not slow_roll_failed:
            ...
            # existing lines unchanged
            self._C_min_slow_roll        = slow_roll["diagnostics"].get("C_min")
            self._compensated_slow_roll  = slow_roll["diagnostics"].get("compensated")
            self._type_II_slow_roll      = slow_roll["diagnostics"].get("type_II")
```

---

## Change 2: `Datastore/SQL/ObjectFactories/CompactionFunction.py`

### 2a. Add new scalar columns to `register()`

Add the following six columns to the `"columns"` list in `register()`,
immediately after the existing `failure_slow_roll` column and before
`metadata`:

```python
                # Per-path C_min and perturbation-type flags
                sqla.Column("C_min_full",          sqla.Float(64), nullable=True),
                sqla.Column("compensated_full",    sqla.Integer,   nullable=True),
                sqla.Column("type_II_full",        sqla.Integer,   nullable=True),
                sqla.Column("C_min_slow_roll",     sqla.Float(64), nullable=True),
                sqla.Column("compensated_slow_roll", sqla.Integer, nullable=True),
                sqla.Column("type_II_slow_roll",   sqla.Integer,   nullable=True),
```

### 2b. Add new columns to the SELECT in `build()`

Add to the `sqla.select(...)` call in `build()`:

```python
            table.c.C_min_full,
            table.c.compensated_full,
            table.c.type_II_full,
            table.c.C_min_slow_roll,
            table.c.compensated_slow_roll,
            table.c.type_II_slow_roll,
```

### 2c. Restore new scalars from DB row in `build()`

After the existing scalar restoration block (ending at
`obj._N_end_downflow_slow_roll = row.N_end_downflow_slow_roll`), add:

```python
        obj._C_min_full              = row.C_min_full
        obj._compensated_full        = bool(row.compensated_full) if row.compensated_full is not None else None
        obj._type_II_full            = bool(row.type_II_full) if row.type_II_full is not None else None
        obj._C_min_slow_roll         = row.C_min_slow_roll
        obj._compensated_slow_roll   = bool(row.compensated_slow_roll) if row.compensated_slow_roll is not None else None
        obj._type_II_slow_roll       = bool(row.type_II_slow_roll) if row.type_II_slow_roll is not None else None
```

### 2d. Emit deserialisation warnings in `build()`

Immediately after the scalar restoration block (after the new lines added in
2c), add:

```python
        dns_val = float(delta_Nstar_obj) if delta_Nstar_obj is not None else "?"
        sid = row.serial
        if obj._type_II_full:
            print(
                f"!! WARNING: CompactionFunction(id={sid}, delta_Nstar={dns_val}): "
                f"full instanton is type-II (C_min={obj._C_min_full:.3g} < -1). "
                f"Collapse threshold comparison using C_peak alone may be unreliable."
            )
        elif obj._compensated_full:
            print(
                f"!! WARNING: CompactionFunction(id={sid}, delta_Nstar={dns_val}): "
                f"full instanton is compensated (C_min={obj._C_min_full:.3g} < 0). "
                f"Underdense shell present; C_peak threshold criterion may overestimate "
                f"collapse probability."
            )
        if obj._type_II_slow_roll:
            print(
                f"!! WARNING: CompactionFunction(id={sid}, delta_Nstar={dns_val}): "
                f"slow-roll instanton is type-II (C_min={obj._C_min_slow_roll:.3g} < -1). "
                f"Collapse threshold comparison using C_peak alone may be unreliable."
            )
        elif obj._compensated_slow_roll:
            print(
                f"!! WARNING: CompactionFunction(id={sid}, delta_Nstar={dns_val}): "
                f"slow-roll instanton is compensated (C_min={obj._C_min_slow_roll:.3g} < 0). "
                f"Underdense shell present; C_peak threshold criterion may overestimate "
                f"collapse probability."
            )
```

### 2e. Write new scalars in `store()`

In `store()`, extend the `inserter(conn, { ... })` call with:

```python
            "C_min_full":            _plain(full_result,  "diagnostics", "C_min"),
            "compensated_full":      int(_plain_bool(full_result,  "diagnostics", "compensated")),
            "type_II_full":          int(_plain_bool(full_result,  "diagnostics", "type_II")),
            "C_min_slow_roll":       _plain(sr_result,    "diagnostics", "C_min"),
            "compensated_slow_roll": int(_plain_bool(sr_result,    "diagnostics", "compensated")),
            "type_II_slow_roll":     int(_plain_bool(sr_result,    "diagnostics", "type_II")),
```

Add these two helper functions alongside the existing `_plain`, `_r`, `_M`,
`_V` helpers inside `store()`:

```python
        def _plain_diag(result, key):
            """Extract a scalar from result["diagnostics"][key], or None."""
            if result is None:
                return None
            diag = result.get("diagnostics")
            if diag is None:
                return None
            return diag.get(key)

        def _plain_diag_bool(result, key):
            """Extract a bool from result["diagnostics"][key]; default False."""
            v = _plain_diag(result, key)
            return bool(v) if v is not None else False
```

Then replace the six inserter lines above with:

```python
            "C_min_full":            _plain_diag(full_result,  "C_min"),
            "compensated_full":      int(_plain_diag_bool(full_result,  "compensated")),
            "type_II_full":          int(_plain_diag_bool(full_result,  "type_II")),
            "C_min_slow_roll":       _plain_diag(sr_result,    "C_min"),
            "compensated_slow_roll": int(_plain_diag_bool(sr_result,    "compensated")),
            "type_II_slow_roll":     int(_plain_diag_bool(sr_result,    "type_II")),
```

---

## Acceptance criteria

### `ComputeTargets/CompactionFunction.py`
- [ ] `_ZETA_PIN_ATOL = 0.01` is defined as a module-level constant.
- [ ] `r_dense` is constructed with `np.geomspace`, not `np.linspace`.
- [ ] `zeta_dense` is evaluated from `zeta_spline(r_dense)`.
- [ ] Boundary pinning is applied only when `abs(zeta_dense[0] - zeta_inner) < _ZETA_PIN_ATOL` and `abs(zeta_dense[-1]) < _ZETA_PIN_ATOL` respectively.
- [ ] `zeta_prime_dense` is computed as `np.gradient(zeta_dense, log_r_dense) / r_dense` — no spline derivative is called.
- [ ] `zeta_prime_v` (at sample points) is computed via `np.interp(log_r_v, log_r_dense, zeta_prime_dense)`.
- [ ] `C_v` is a vectorised numpy array expression, not a list comprehension.
- [ ] `C_min`, `type_II`, and `compensated` are all computed from `C_v` and included in the `"diagnostics"` dict.
- [ ] `_populate_from_result` sets `_C_min_full`, `_compensated_full`, `_type_II_full`, `_C_min_slow_roll`, `_compensated_slow_roll`, `_type_II_slow_roll`.
- [ ] Properties `C_min_full`, `compensated_full`, `type_II_full`, `C_min_slow_roll`, `compensated_slow_roll`, `type_II_slow_roll` are present on `CompactionFunction`.
- [ ] The C̄ integration loop is unchanged in structure; it reuses `r_dense`, `zeta_dense`, `zeta_prime_dense` from the computation above.

### `Datastore/SQL/ObjectFactories/CompactionFunction.py`
- [ ] Six new columns (`C_min_full`, `compensated_full`, `type_II_full`, `C_min_slow_roll`, `compensated_slow_roll`, `type_II_slow_roll`) are present in `register()`.
- [ ] All six columns are selected in `build()` and restored onto the object.
- [ ] `_plain_diag` and `_plain_diag_bool` helpers are defined inside `store()`.
- [ ] All six values are written by `store()`.
- [ ] Deserialisation warnings are emitted by `build()` for compensated and type-II cases, per path, with `delta_Nstar` and `store_id` in the message.
- [ ] Warnings for `type_II` take precedence over `compensated` per path (use `elif`).

## Out of scope

- Changes to `SplineWrapper`.
- Changes to Steps A, B, C, E, F.
- Changes to `store()` / `validate()` / `validate_on_startup()` beyond what is
  specified above.
- Any plotting changes.
- The `metadata` JSON blob is not changed in structure; `type_II`,
  `compensated`, and `C_min` live in the dedicated scalar columns only.
