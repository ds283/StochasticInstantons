# Prompt 5 — Scalars-only storage mode for `CompactionFunction`

## Context

This mirrors Prompt 4's change, but `CompactionFunction` is structurally
different in three ways that matter here — confirmed by direct inspection
of `Datastore/SQL/ObjectFactories/CompactionFunction.py`:

1. **All the scalar summaries you actually want for a sparse-sampling
   campaign already live on the parent row regardless of value-storage
   mode** — `r_max_C_full_Mpc`, `r_max_C_bar_full_Mpc`, `M_C_full_SolarMass`,
   `M_C_bar_full_SolarMass`, `C_max_full`, `C_bar_max_full`,
   `V_end_downflow_full_PlanckMass4`, `N_end_downflow_full`,
   `failure_full`, and the slow-roll equivalents, plus `C_threshold`/
   `C_bar_threshold`. Only the dense per-`r` profile (`r`, `zeta`, `C`,
   `C_bar` at every sampled radius) lives in the child table,
   `CompactionFunctionSamples`. This prompt only affects whether that child
   table gets populated — every column you'd need for the GP/sensitivity
   work from Prompt 3's discussion is unaffected either way.

2. **The diagnostics JSON column on `CompactionFunction`'s table is named
   `metadata`, not `diagnostics_json`** (unlike `FullInstanton`/
   `SlowRollInstanton`). Variable name in the factory is `metadata_json`.
   Do not assume the column name carries over from Prompt 4 — check every
   reference.

3. **`CompactionFunctionSamples` holds both the `full` and `slow_roll`
   sample streams in one table**, distinguished by a `source` column, and
   `validate()` already checks a single **combined** count:
   `expected = len(obj._full_values) + len(obj._slow_roll_values)` against
   total rows in `CompactionFunctionSamples` for that parent. Per the
   discussion that prompted this file, implement a **single combined**
   `_store_full_values` flag (not independent `full`/`slow_roll`
   switches) — when `False`, skip writing rows from **both**
   `obj._full_values` and `obj._slow_roll_values` (whichever happen to be
   non-empty; note `CompactionFunction` can have a partial failure — one of
   `full`/`slow_roll` succeeds while the other doesn't, in which case
   `obj.failure` is still `False` and the *non-failure* branch of `store()`
   runs, but only one of the two lists will actually be non-empty).

**Read `ComputeTargets/CompactionFunction.py` and
`Datastore/SQL/ObjectFactories/CompactionFunction.py` in full before
writing any code**, in particular the `store()` method on the
`CompactionFunction` compute-target class itself (the driver-side method
that reads the Ray result and populates `_full_values`/`_slow_roll_values`)
— this must be left untouched, for the same reason as Prompt 4: even
though there is currently no other in-pipeline compute target that
consumes `CompactionFunction`'s per-`r` values within the same run (it is
the terminal compute target — check `FILE_MAP.md` / the compute-target
dependency chain to confirm this is still true), keep the same separation
of concerns as `FullInstanton`/`SlowRollInstanton` for consistency, and
because `plot_InstantonSolutions.py` and any future analysis tooling may
read `_full_values`/`_slow_roll_values` from a freshly-computed (not yet
persisted) object.

## Task

### 1. A flag on `CompactionFunction`

Same shape as Prompt 4: add `_store_full_values: bool = True` and a public
`set_store_full_values(self, flag: bool)` setter to
`ComputeTargets/CompactionFunction.py::CompactionFunction`. Do not touch
`compute()` or the driver-side `store()` method.

### 2. Factory `store()`

In `Datastore/SQL/ObjectFactories/CompactionFunction.py`'s `store()`:

- No change to the `obj.failure` (both-streams-failed) branch.
- In the non-failure branch: if `getattr(obj, "_store_full_values", True)`
  is `False`, skip **both** `for v in obj._full_values: samples_inserter(...)`
  and `for v in obj._slow_roll_values: samples_inserter(...)` loops. All
  parent-row scalar columns are written exactly as today, unconditionally.
- Merge `{"full_values_stored": False}` into the dict backing
  `metadata_json` (built from `obj.diagnostics`, merged not replaced —
  same pattern as Prompt 4, `dict(obj.diagnostics) if obj.diagnostics is
  not None else {}`) when the flag is `False`. Leave the existing
  `metadata_json = json.dumps(obj.diagnostics) if obj.diagnostics is not
  None else None` behaviour for the `True`/default case, matching whatever
  choice Prompt 4 made about explicitly writing `True` vs. leaving the key
  absent — be consistent with that earlier choice rather than picking
  independently.

### 3. Factory `validate()`

Change `expected = len(obj._full_values) + len(obj._slow_roll_values)` to
`expected = 0 if not getattr(obj, "_store_full_values", True) else
len(obj._full_values) + len(obj._slow_roll_values)`, inside the existing
`else` (non-failure) branch, leaving the `if obj.failure: validated = True`
shortcut untouched.

### 4. Factory `build()`

Locate the existing:

```python
do_not_populate = payload.get("_do_not_populate", False)
if not do_not_populate:
    self._populate(obj, row, tables, conn)
```

(note: `_populate` here takes no `units=` argument, unlike
`FullInstanton`'s — check the actual signature, don't copy Prompt 4's call
shape blindly) and insert the same guard pattern as Prompt 4, reading
`obj._diagnostics.get("full_values_stored", True)` (recall `obj._diagnostics`
is restored from the `metadata` column, via `json.loads(row.metadata) if
row.metadata else None` — already present a few lines above this point in
`build()`), raising `RuntimeError` with a message naming
`CompactionFunction` specifically if `False` and `_do_not_populate` is not
set.

### 5. Backward compatibility

Same requirement as Prompt 4: every existing `CompactionFunction` row's
`metadata` column has no `full_values_stored` key (or is `None` entirely).
`.get("full_values_stored", True)` must treat both as `True`. Add the same
shape of regression test as Prompt 4 (a `diagnostics`/`metadata` dict with
other real keys — e.g. whatever `_compute_instanton_path`'s diagnostics
dict already contains, including the `r_max_C_bar_extrapolated`/
`r_max_C_at_grid_edge` keys added in Prompt 1 — but no `full_values_stored`
key) confirming no raise.

## Acceptance criteria

- [ ] `set_store_full_values(False)` exists on `CompactionFunction`;
      default behaviour (never called) is provably unchanged — existing
      `CompactionFunction` tests pass unmodified.
- [ ] Using the live-`ShardedPool` fixture: store a `CompactionFunction`
      computed from both a successful `FullInstanton` and a successful
      `SlowRollInstanton`, full-fidelity mode — regression check, child row
      count equals `len(_full_values) + len(_slow_roll_values)`,
      `validate()` succeeds.
- [ ] Same scenario with `set_store_full_values(False)`: zero
      `CompactionFunctionSamples` rows written, `validate()` succeeds,
      `metadata` contains `"full_values_stored": false` alongside whatever
      other diagnostics keys were present (including the Prompt-1
      extrapolation flags).
- [ ] **Partial-failure case**: construct (or mock) a scenario where only
      one of `full_instanton`/`slow_roll_instanton` succeeds (so
      `obj.failure` is `False` but only one of `_full_values`/
      `_slow_roll_values` is non-empty) — confirm `set_store_full_values(False)`
      correctly suppresses whichever list is non-empty, and that the
      already-empty list doesn't trivially make the test pass without
      actually exercising the skip logic for the non-empty one. Test both
      orderings (full succeeds/slow-roll fails, and vice versa).
- [ ] Reading a scalars-only `CompactionFunction` row via `build()` with
      `_do_not_populate=True` succeeds, `_full_values == []` and
      `_slow_roll_values == []`.
- [ ] Reading the same row via `build()` without `_do_not_populate` raises
      the explicit `RuntimeError`.
- [ ] A normal full-fidelity row is completely unaffected by this change,
      verified by test.
- [ ] Backward-compatibility regression test (absent `full_values_stored`
      key, other real diagnostics keys present) does not raise.
- [ ] `git diff` touches only `ComputeTargets/CompactionFunction.py`,
      `Datastore/SQL/ObjectFactories/CompactionFunction.py`, and test
      files. No changes to `main.py`, `FullInstanton.py`/
      `SlowRollInstanton.py` (production or factory), or any CLI/argument
      parser file.

## Out of scope (do not attempt in this prompt)

- Any CLI flag or wiring into `main.py`'s pipeline run for any of the three
  compute targets (`FullInstanton`, `SlowRollInstanton`,
  `CompactionFunction`) — that's the next, final prompt in this sequence,
  now that all three factories support the flag independently.
- Independent `full`/`slow_roll` sub-flags — explicitly rejected above in
  favour of one combined switch.

## Commit

One commit, message along the lines of:
`CompactionFunction: add scalars-only storage mode with build()-time guard`
