# Prompt 4 — Scalars-only storage mode for `FullInstanton` / `SlowRollInstanton`

## Context

Per instanton, the bulk of database storage is the per-sample `(N, φ₁, φ₂,
P₁, P₂)` (or `(N, φ, P₁)` for slow-roll) arrays written into the
`FullInstantonValue`/`SlowRollInstantonValue` child tables by the **factory
`store()`** method in `Datastore/SQL/ObjectFactories/FullInstanton.py` /
`SlowRollInstanton.py` — *not* the in-memory `FullInstanton.store()` /
`SlowRollInstanton.store()` method on the `ComputeTargets` classes
themselves, which just reads the Ray compute result into `obj._values` and
must be left untouched (see below). For a sparse-sampling / sensitivity
campaign we want the option to persist only the scalar summary columns
already on the parent row (`N_total`, `msr_action`, `diagnostics_json`,
etc.) and skip writing the per-sample child rows entirely.

**Read both `ComputeTargets/FullInstanton.py` and
`ComputeTargets/SlowRollInstanton.py` in full, and both corresponding
factory files, before writing any code.** The two compute targets and
their factories are structurally near-identical (same `store()`/
`validate()`/`build()`/`_populate()` shape, same `diagnostics_json` column,
same failure-branch handling) — implement the same change in both, and
flag anything that turns out *not* to be symmetric rather than silently
papering over a difference.

### Critical subtlety — read this before touching `validate()`

`FullInstanton.compute()` populates `obj._values` in memory regardless of
how the result will be persisted — and **must continue to do so
unconditionally**, because `CompactionFunction`'s computation reads
`full_instanton_proxy.get().values` directly from the same in-memory
object within the same pipeline run (see
`ComputeTargets/CompactionFunction.py::_compute_instanton_path`, which
calls `instanton_obj.values`). **Do not touch `compute()` or the
in-memory/driver-side `store()` method on `FullInstanton`/
`SlowRollInstanton` to skip populating `_values`** — that would silently
break `CompactionFunction` for the very run where you're trying to save
space. The scalars-only mode only affects what the **factory's** `store()`
writes to the database, not what's held in memory after compute.

This means the factory's `validate()` method, which currently does:

```python
value_table = tables["FullInstantonValue"]
expected = len(obj._values)
actual = conn.execute(... count rows where instanton_serial == obj.store_id ...)
validated = (actual == expected)
```

**will be wrong in scalars-only mode if left as-is**: `obj._values` is
still fully populated (per the paragraph above), so `expected` will be
nonzero even though `store()` deliberately wrote zero child rows, and every
scalars-only instanton will permanently fail validation. `validate()` must
be made aware of the same scalars-only flag `store()` used, and expect `0`
child rows in that case — not re-derive the expectation from
`len(obj._values)` unconditionally.

## Task

Implement identically in both `ComputeTargets/FullInstanton.py` +
`Datastore/SQL/ObjectFactories/FullInstanton.py`, and
`ComputeTargets/SlowRollInstanton.py` +
`Datastore/SQL/ObjectFactories/SlowRollInstanton.py`:

### 1. A flag on the compute-target object

Add an attribute to `FullInstanton`/`SlowRollInstanton` (e.g.
`_store_full_values: bool`, default `True`), settable via a small public
method (e.g. `set_store_full_values(self, flag: bool)`) called by the
driver **after** construction and (if relevant) after `compute()`/`store()`
have populated `_values`, but **before** `pool.object_store(obj)` is
called. Do not add this as a constructor argument that has to be threaded
through every existing call site — a post-construction setter is less
invasive and keeps this prompt's diff small. Do not wire this up to any CLI
flag or to `main.py` in this prompt — that's a deliberately separate later
prompt. For this prompt, tests will set the flag directly on objects they
construct.

### 2. Factory `store()`: skip child-row writes when the flag is set

In both factories' `store()` methods:

- If `obj.failure` is `True`: no behaviour change. (No value rows are ever
  written in the failure branch today — the scalars-only flag is moot
  there.)
- If `obj.failure` is `False` and `getattr(obj, "_store_full_values",
  True)` is `False`: write the parent row exactly as today (all existing
  scalar columns unchanged), but **skip** the `for v in obj._values:
  value_inserter(...)` loop entirely.
- In the scalars-only case, before serialising `diagnostics_json`, merge in
  `{"full_values_stored": False}` (don't overwrite other existing
  diagnostics keys — merge, not replace). When the flag is `True`
  (default/unset), decide explicitly whether to also write
  `"full_values_stored": True` for forward clarity or to leave the key
  absent (treated as `True` by the build()-time guard in step 4) — pick
  one, document the choice in the commit message, and apply it
  consistently in both factories.

### 3. Factory `validate()`: expected row count must match what was actually requested

Change `expected = len(obj._values)` to account for the same flag:
`expected = 0 if getattr(obj, "_store_full_values", True) is False and not
obj.failure else len(obj._values)` (or equivalent, written however reads
most clearly — the point is the expectation must track what `store()`
actually attempted to write, not what's sitting in memory). Verify this
makes scalars-only-mode instantons validate successfully with zero child
rows, and that full-fidelity instantons are completely unaffected.

### 4. Factory `build()`: raise instead of silently returning empty `_values`

In both factories' `build()` methods, where the current code is:

```python
do_not_populate = payload.get("_do_not_populate", False)
if not do_not_populate:
    self._populate(obj, row_data, tables, conn, units=...)
```

Insert a check, after `obj._diagnostics` has been restored from
`diagnostics_json` and before the `_populate` call:

```python
if not do_not_populate:
    if obj._diagnostics is not None and obj._diagnostics.get("full_values_stored", True) is False:
        raise RuntimeError(
            f"{type(obj).__name__}(id={obj.store_id}) was stored in scalars-only "
            f"mode; full per-sample values were never persisted. Re-run with "
            f"_do_not_populate=True, or recompute this instanton in full-fidelity mode."
        )
    self._populate(obj, row_data, tables, conn, units=...)
```

Adjust the exact wording/exception type to match whatever convention the
rest of this codebase uses for similar invariant violations (check
`_populate`'s own `RuntimeError` calls for style). When `do_not_populate is
True`, behaviour is completely unchanged regardless of the flag — no
`_populate` call either way, exactly as today.

### 5. Backward compatibility

Every row in the existing 25,000-instanton production database has no
`"full_values_stored"` key in its `diagnostics_json` (or has `None` for the
whole column). `.get("full_values_stored", True)` must treat absence as
`True` — confirm this is the case for **both** an entirely absent
`diagnostics_json` column (`None`) and a present-but-key-absent
dict, and add a regression test against exactly that shape (a `diagnostics`
dict with other keys but no `full_values_stored` key) to guard against this
historically-common case being broken later.

## Acceptance criteria

- [ ] `set_store_full_values(False)` (or equivalently-named method) exists
      on both `FullInstanton` and `SlowRollInstanton`; default behaviour
      (method never called) is provably unchanged — existing tests for
      both classes still pass unmodified.
- [ ] Using the live-`ShardedPool` fixture from `tests/conftest.py`
      (added in Prompt 02b): store a successfully-computed instanton in
      full-fidelity mode, confirm child-row count equals `len(obj._values)`
      and `validate()` succeeds, as today (regression check).
- [ ] Using the same fixture: store a successfully-computed instanton with
      `set_store_full_values(False)`, confirm **zero** child rows are
      written, `validate()` succeeds (not "expected N, found 0"), and the
      stored `diagnostics_json` contains `"full_values_stored": false`
      alongside any other diagnostics keys that were present.
- [ ] Reading that scalars-only row back via `build()` with
      `_do_not_populate=True` succeeds and returns an object with
      `_values == []`, exactly as the populate-skip behaviour does today
      for full-fidelity rows.
- [ ] Reading that scalars-only row back via `build()` **without**
      `_do_not_populate` (i.e. default `False`) raises the explicit
      `RuntimeError` described above — verified by an actual test that
      asserts the raise, not just code inspection.
- [ ] Reading a normal full-fidelity row back via `build()` without
      `_do_not_populate` is completely unaffected — `_populate` runs and
      `_values` is correctly restored, exactly as today.
- [ ] A regression test confirms `diagnostics_json` containing other keys
      but no `full_values_stored` key (i.e. every row in the existing
      production database) is treated as `full_values_stored: True` and
      does **not** raise.
- [ ] A failed instanton (`obj.failure is True`) stored with
      `set_store_full_values(False)` behaves identically to one stored with
      the flag left at its default — confirm explicitly with a test, since
      the failure branch in `store()` is untouched by this change and
      should remain so.
- [ ] All of the above is implemented and tested identically for both
      `FullInstanton` and `SlowRollInstanton` — if you find a genuine
      asymmetry between the two classes/factories that changes how this
      should be implemented for one vs. the other, stop and report it
      rather than silently choosing different approaches for each.
- [ ] `git diff` touches only `ComputeTargets/FullInstanton.py`,
      `ComputeTargets/SlowRollInstanton.py`,
      `Datastore/SQL/ObjectFactories/FullInstanton.py`,
      `Datastore/SQL/ObjectFactories/SlowRollInstanton.py`, and test files.
      No changes to `main.py`, `CompactionFunction.py`, or any CLI/argument
      parser file.

## Out of scope (do not attempt in this prompt)

- `CompactionFunction`'s own scalars-only storage mode (its child table,
  `CompactionFunctionSamples`, has a different shape — separate prompt).
- Any CLI flag (`--no-store-values` or similar) or wiring into `main.py`'s
  pipeline run — a later, separate "wiring" prompt, deliberately deferred
  until the factory-level behaviour here is verified in isolation.
- Any change to `compute()` or to what `_values` contains in memory after a
  successful compute — explicitly called out above as something this
  prompt must not touch.

## Commit

One commit, message along the lines of:
`FullInstanton/SlowRollInstanton: add scalars-only storage mode with build()-time guard`
