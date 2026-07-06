# Prompt 13 — `n_collocation_points` and `alpha_regularization` concept objects

## Context

`GradientCoupledInstanton` (the final compute target, built in a later
prompt) needs two solver-convergence parameters persisted as shared,
replicated `DatastoreObject`s and used as FKs — the same role `tolerance`
and `delta_Nstar` already play for `FullInstanton`. Both are pure
numerical-implementation parameters, not physical inputs — confirmed
early in this design: "definitely replicated. This is simply a parameter
of the numerical implementation, like `tolerance`." Neither has any
Datastore/SQL dependency anywhere else in the codebase yet — this prompt
is infrastructure only, mirroring the pattern already used for `y_value`
and (in an earlier, since-superseded design) `mode_truncation`.

Two genuinely different storage shapes, don't conflate them:

- **`n_collocation_points`**: an exact integer count (the LGL grid size
  fed to `Numerics/LGLCollocation.py`'s `LGLCollocationGrid`). Needs
  **exact equality** lookup, not tolerance-banded — it's a count, not a
  continuous physical quantity. Must be `>= 2` (matching
  `LGLCollocationGrid`'s own constructor validation — reject invalid
  values here too, don't rely on the numerics layer to catch it later).
  **Do not** expose an `.n_max`/degree property on this class — per the
  design principle settled when `LGLCollocationGrid` was built, the
  `n_collocation_points - 1` subtraction happens in exactly one place in
  the whole codebase (`LGLCollocationGrid` itself), never here.
- **`alpha_regularization`**: a continuous float (the coordinate
  regularization parameter from `Numerics/OnionCoordinate.py`'s
  `delta_s()`). Needs ordinary **tolerance-banded** float lookup, matching
  `delta_Nstar`/`y_value`'s pattern — including the zero-vs-nonzero
  absolute/relative branching, since `alpha == 0` is a valid, meaningful
  value (checked in `delta_s()` itself: "`alpha == 0` is a valid,
  well-defined input"), not just "small." Must be `>= 0`, matching
  `delta_s()`'s own guard.

Deliberately named `alpha_regularization`, not bare `alpha` — `alpha` is
used constantly as a plain float parameter name throughout the onion-model
code (`delta_s`, `forward_rhs`, `scale_assignment`, etc.); a class named
identically would be an easy source of confusion between "the persisted
concept object" and "the plain float value" at call sites. No such
collision risk for `n_collocation_points` (nothing else in the codebase
uses that exact name for a bare parameter).

## Task

### 1. `InflationConcepts/n_collocation_points.py`

`n_collocation_points(DatastoreObject)`, modelled on `InflationConcepts/
mode_truncation.py`'s structure (see project history — a standalone,
lightweight class, not a subclass of a generic `DimensionlessQuantity`):

- `__init__(self, store_id, n_collocation_points, timestamp=None)`.
  `store_id` required. Validate integer-valued (reject e.g. `17.5`) and
  `>= 2` (reject `0`, `1`, negative) — both `ValueError`, distinct
  messages.
- `__int__` returns the count; `__float__` returns it as a float (for
  compatibility with any generic FK-casting code, matching the convention
  every other concept object here follows).
- `@total_ordering` by the count; `__eq__`/`__hash__` by `store_id`.
- No array/container class — this is a single FK value per instanton, not
  a sample-grid coordinate (same reasoning as `mode_truncation` before it).

### 2. `Datastore/SQL/ObjectFactories/n_collocation_points.py`

`sqla_n_collocation_points_factory(SQLAFactoryBase)`:

- `register()`: single `Integer` column, indexed. No version, with
  timestamp.
- `build(...)`: **exact** equality lookup (`table.c.n_collocation_points
  == n_collocation_points`), not tolerance-banded — same reasoning as the
  earlier `mode_truncation` factory.
- `read_table()`/`inventory()`: same shape as other factories, ordering by
  the count ascending.

### 3. `InflationConcepts/alpha_regularization.py`

`alpha_regularization(DatastoreObject)`, modelled on `InflationConcepts/
delta_Nstar.py`:

- `__init__(self, store_id, alpha, timestamp=None)`. `store_id` required.
  Validate `alpha >= 0` (`ValueError` otherwise, matching `delta_s()`'s own
  guard — don't diverge from it).
- `__float__` returns `alpha`.
- `@total_ordering` by `alpha`; `__eq__`/`__hash__` by `store_id`.

### 4. `Datastore/SQL/ObjectFactories/alpha_regularization.py`

`sqla_alpha_regularization_factory(SQLAFactoryBase)`:

- `register()`: single `Float(64)` column, indexed.
- `build(...)`: tolerance-banded lookup, same absolute/relative branching
  as `sqla_delta_Nstar_factory`/`sqla_y_factory` (`fabs(alpha) == 0` uses
  absolute tolerance, otherwise relative). Add new
  `DEFAULT_ALPHA_PRECISION`/`DEFAULT_ALPHA_RELATIVE_PRECISION` constants to
  `config/defaults.py` — don't reuse the e-fold or `y` precision constants,
  `alpha`'s natural scale is unrelated to either.
- `read_table()`/`inventory()`: same shape as the other factories.

### 5. Wire both into all four registration points

For **both** `n_collocation_points` and `alpha_regularization`:

- `Datastore/SQL/Datastore.py`'s `_factories` dict.
- `ClientPool.py`'s `_default_serial_batch_size` — both are low-cardinality
  (a handful of distinct values swept at most), use a small batch size
  matching what `tolerance`/`mode_truncation` used, not the `500` used for
  high-cardinality tables like `y_value`/`efold_value`.
- `config/sharding.py`'s `replicated_tables` — confirmed, not
  `sharded_tables`.
- `config/sharding.py`'s `read_table_config`, both with
  `{"tables_arg": False}`.

### 6. Tests

`tests/test_n_collocation_points.py` and
`tests/test_alpha_regularization.py`, mirroring the existing
`mode_truncation`/`delta_Nstar` test structure:

- Ordering, equality, hashing.
- `n_collocation_points`: non-integer or `< 2` raises; SQL round-trip is
  exact-match (same count twice → same `store_id`; adjacent counts →
  distinct `store_id`s, no tolerance collision).
- `alpha_regularization`: negative raises; `alpha == 0` is valid and
  constructs correctly; SQL round-trip exercises both the zero-value
  absolute-tolerance branch and the nonzero relative-tolerance branch
  distinctly (don't just test one).

## Acceptance criteria

- [ ] `InflationConcepts/n_collocation_points.py` created; integer
      semantics; `< 2` or non-integer raises; no `.n_max` property.
- [ ] `InflationConcepts/alpha_regularization.py` created; `alpha < 0`
      raises; `alpha == 0` valid.
- [ ] Both SQL factories created with the correct (exact vs.
      tolerance-banded) lookup semantics — not copy-pasted from the wrong
      sibling.
- [ ] `DEFAULT_ALPHA_PRECISION`/`DEFAULT_ALPHA_RELATIVE_PRECISION` added to
      `config/defaults.py`.
- [ ] Both registered in all four locations: `Datastore.py._factories`,
      `ClientPool.py._default_serial_batch_size`, `config/sharding.py`'s
      `replicated_tables` and `read_table_config`.
- [ ] All tests pass.
- [ ] No compute-target changes — this prompt is infrastructure only, same
      as prompts 01–03 were.

## Commit

Single commit, message along the lines of:
`Add n_collocation_points (exact-match) and alpha_regularization (tolerance-banded) concept objects and SQL persistence`
