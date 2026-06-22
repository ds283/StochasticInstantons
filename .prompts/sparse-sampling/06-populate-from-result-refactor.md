# Prompt 6 — `_populate_from_result` refactor on `FullInstanton`, `SlowRollInstanton`, `CompactionFunction`

## Context

The upcoming pipeline re-architecture (Prompt 7) will compute `FullInstanton`,
`SlowRollInstanton`, and `CompactionFunction` for each grid point inside a single
`@ray.remote` function (`compute_pipeline`). When that function returns, the
driver needs to populate all three in-memory objects from the returned result
dicts — without going through the existing `store()` pathway, which requires
`self._compute_ref` to be set (i.e., requires `compute()` to have been called
first on the driver).

This prompt performs the prerequisite refactor: extract the result-dict
→ in-memory-state population logic out of `store()` into a private
`_populate_from_result(data)` method on each of the three compute-target
classes, then have `store()` call it. This is a pure refactor — no behaviour
change for any existing call site.

**Read the current `store()` method on all three classes in full before
writing anything:**
- `ComputeTargets/FullInstanton.py::FullInstanton.store()` (lines ~496–518
  in the current file — see the pasted body in the reference section below)
- `ComputeTargets/SlowRollInstanton.py::SlowRollInstanton.store()` (lines
  ~502–522)
- `ComputeTargets/CompactionFunction.py::CompactionFunction.store()` (lines
  ~611–681)

Their exact bodies are reproduced in the reference section at the end of
this prompt. Do not guess at attribute names or dict keys — use the actual
bodies.

## Task

### 1. `FullInstanton._populate_from_result(data: dict) -> None`

Extract the body of `store()` from `data = ray.get(self._compute_ref)` onward
into a new private method. `store()` becomes:

```python
def store(self) -> None:
    """Called on the driver by RayWorkPool after compute() resolves."""
    if self._compute_ref is None:
        raise RuntimeError("store() called but no compute() is in progress")
    data = ray.get(self._compute_ref)
    self._compute_ref = None
    self._populate_from_result(data)

def _populate_from_result(self, data: dict) -> None:
    """Populate internal state from a pre-computed result dict.
    
    Called by store() after resolving the Ray future, and directly by
    the pipeline store-handler when results arrive from compute_pipeline
    without a compute() having been dispatched on this object.
    """
    self._diagnostics = data.get("diagnostics")
    if data.get("failure", False):
        self._failure = True
        self._values = []
        return
    self._failure = False
    self._msr_action = data["msr_action"]
    self._N_total = data["N_total"]
    self._values = [
        FullInstantonValue(store_id=None, N=N_obj, phi1=phi1, phi2=phi2, P1=P1, P2=P2)
        for N_obj, phi1, phi2, P1, P2 in zip(
            self._N_sample, data["phi1"], data["phi2"], data["P1"], data["P2"]
        )
    ]
```

Preserve the existing behaviour exactly, including the early return on
failure and the `FullInstantonValue` construction. Do not reorder, simplify,
or change any attribute assignments.

### 2. `SlowRollInstanton._populate_from_result(data: dict) -> None`

Same refactor. `store()` becomes a two-liner (guard + `ray.get` + delegate).
`_populate_from_result` carries the body verbatim, adapted for
`SlowRollInstantonValue(store_id=None, N=N_obj, phi=phi, P1=P1)` and
`data["phi"]`/`data["P1"]` (not `phi1`/`phi2`/`P1`/`P2` — these differ
between the two classes; do not copy-paste).

### 3. `CompactionFunction._populate_from_result(data: dict) -> None`

Same refactor. `store()` becomes:

```python
def store(self) -> None:
    if self._compute_ref is None:
        raise RuntimeError("store() called but no compute() is in progress")
    data = ray.get(self._compute_ref)
    self._compute_ref = None
    self._cosmo_store_id = data.get("cosmo_store_id")
    self._populate_from_result(data)
```

Note that `self._cosmo_store_id = data.get("cosmo_store_id")` stays in
`store()` and is NOT moved into `_populate_from_result` — in the pipeline
path, `cosmo_store_id` will be handled separately by the pipeline
store-handler, which has direct access to the cosmo object. Moving it
into `_populate_from_result` would couple that method to a key that only
exists in the `_compute_compaction_function` remote function's return dict,
not in the pipeline's result dict structure.

`_populate_from_result(data)` carries the rest of `store()`'s body verbatim:
the `full`/`slow_roll` extraction, both failed/partial-failure branches,
the `_diagnostics` assembly, the `CompactionFunctionValue` list
construction, and all `_r_max_C_*`/`_M_C_*`/`_C_max_*`/`_C_bar_max_*`/
`_V_end_downflow_*`/`_N_end_downflow_*` attribute assignments. `data` is
expected to have the same shape as the dict returned by
`_compute_compaction_function` — i.e., `{"full": ..., "slow_roll": ...}`
where each branch is either `None` or a result dict with `"failure"`,
`"r"`, `"zeta"`, `"C"`, `"C_bar"`, `"r_max_C"`, etc.

### 4. No other changes

- Do not modify `compute()` on any class.
- Do not modify any factory file (`Datastore/SQL/ObjectFactories/`).
- Do not modify `RayWorkPool`, `main.py`, or any other caller of `store()`.
- Do not add any new public API beyond the three private
  `_populate_from_result` methods.
- The `_store_full_values` flag and `set_store_full_values()` method added
  in Prompt 4 are unaffected — they live on the compute-target object and
  interact only with the factory's `store()`, not with
  `_populate_from_result`.

## Acceptance criteria

- [ ] `FullInstanton.store()` is behaviourally identical to before this
      change for all existing call sites — verified by running the existing
      test suite (`tests/test_scalars_only_storage.py` and any other tests
      that exercise `FullInstanton.store()`) without modification.
- [ ] `SlowRollInstanton.store()` same.
- [ ] `CompactionFunction.store()` same.
- [ ] `FullInstanton._populate_from_result(data)` called directly with a
      synthetic result dict (both success and failure branches) produces
      identical in-memory state to what `store()` would have produced from
      the same dict — verified by unit test. In particular: `_values` is
      populated correctly on success, `_values == []` and `_failure is True`
      on failure, `_msr_action` and `_N_total` are set correctly.
- [ ] Same unit tests for `SlowRollInstanton._populate_from_result`.
- [ ] Same for `CompactionFunction._populate_from_result`, including the
      partial-failure cases (full succeeds / slow-roll fails, and vice
      versa), and the both-failed case.
- [ ] `CompactionFunction._populate_from_result` does NOT set
      `self._cosmo_store_id` — this stays in `store()`. Verified by
      checking that calling `_populate_from_result` on a fresh
      `CompactionFunction` object leaves `_cosmo_store_id` unset (or
      whatever its initial value is from `__init__`).
- [ ] `git diff` touches only `ComputeTargets/FullInstanton.py`,
      `ComputeTargets/SlowRollInstanton.py`,
      `ComputeTargets/CompactionFunction.py`, and test files. No factory,
      no `main.py`, no `RayWorkPool`.

## Out of scope (do not attempt in this prompt)

- `compute_pipeline` remote function or `PipelineWorkItem` — Prompt 7.
- The integrity check (comparing freshly-computed scalars against DB-stored
  values for pre-existing scalars-only rows) — Prompt 7.
- `--no-store-values` CLI flag wiring — Prompt 8.
- Any change to `store()` beyond the refactor described above.

## Reference: current `store()` bodies

### `FullInstanton.store()`
```python
def store(self):
    if self._compute_ref is None:
        raise RuntimeError("store() called but no compute() is in progress")
    data = ray.get(self._compute_ref)
    self._compute_ref = None
    self._diagnostics = data.get("diagnostics")
    if data.get("failure", False):
        self._failure = True
        self._values = []
        return
    self._failure = False
    self._msr_action = data["msr_action"]
    self._N_total = data["N_total"]
    self._values = [
        FullInstantonValue(store_id=None, N=N_obj, phi1=phi1, phi2=phi2, P1=P1, P2=P2)
        for N_obj, phi1, phi2, P1, P2 in zip(
            self._N_sample, data["phi1"], data["phi2"], data["P1"], data["P2"]
        )
    ]
```

### `SlowRollInstanton.store()`
```python
def store(self):
    if self._compute_ref is None:
        raise RuntimeError("store() called but no compute() is in progress")
    data = ray.get(self._compute_ref)
    self._compute_ref = None
    self._diagnostics = data.get("diagnostics")
    if data.get("failure", False):
        self._failure = True
        self._values = []
        return
    self._failure = False
    self._msr_action = data["msr_action"]
    self._N_total = data["N_total"]
    self._values = [
        SlowRollInstantonValue(store_id=None, N=N_obj, phi=phi, P1=P1)
        for N_obj, phi, P1 in zip(self._N_sample, data["phi"], data["P1"])
    ]
```

### `CompactionFunction.store()`
```python
def store(self):
    if self._compute_ref is None:
        raise RuntimeError("store() called but no compute() is in progress")
    data = ray.get(self._compute_ref)
    self._compute_ref = None
    self._cosmo_store_id = data.get("cosmo_store_id")

    full = data.get("full")
    slow_roll = data.get("slow_roll")

    full_failed = full is None or full.get("failure", True)
    slow_roll_failed = slow_roll is None or slow_roll.get("failure", True)

    if full_failed and slow_roll_failed:
        self._failure = True
        self._diagnostics = {
            "full": full.get("diagnostics") if full else None,
            "slow_roll": slow_roll.get("diagnostics") if slow_roll else None,
        }
        return

    self._failure = False
    self._diagnostics = {
        "full": full.get("diagnostics") if full else None,
        "slow_roll": slow_roll.get("diagnostics") if slow_roll else None,
    }

    if not full_failed:
        self._full_result = full
        self._full_values = [
            CompactionFunctionValue(store_id=None, r=r, zeta=z, C=c, C_bar=cb)
            for r, z, c, cb in zip(full["r"], full["zeta"], full["C"], full["C_bar"])
        ]
        self._r_max_C_full = full.get("r_max_C")
        self._r_max_C_bar_full = full.get("r_max_C_bar")
        self._M_C_full = full.get("M_C")
        self._M_C_bar_full = full.get("M_C_bar")
        self._C_max_full = full.get("C_max")
        self._C_bar_max_full = full.get("C_bar_max")
        self._V_end_downflow_full = full.get("V_end_downflow")
        self._N_end_downflow_full = full.get("N_end_downflow")
    else:
        self._full_result = None

    if not slow_roll_failed:
        self._slow_roll_result = slow_roll
        self._slow_roll_values = [
            CompactionFunctionValue(store_id=None, r=r, zeta=z, C=c, C_bar=cb)
            for r, z, c, cb in zip(
                slow_roll["r"], slow_roll["zeta"], slow_roll["C"], slow_roll["C_bar"]
            )
        ]
        self._r_max_C_slow_roll = slow_roll.get("r_max_C")
        self._r_max_C_bar_slow_roll = slow_roll.get("r_max_C_bar")
        self._M_C_slow_roll = slow_roll.get("M_C")
        self._M_C_bar_slow_roll = slow_roll.get("M_C_bar")
        self._C_max_slow_roll = slow_roll.get("C_max")
        self._C_bar_max_slow_roll = slow_roll.get("C_bar_max")
        self._V_end_downflow_slow_roll = slow_roll.get("V_end_downflow")
        self._N_end_downflow_slow_roll = slow_roll.get("N_end_downflow")
    else:
        self._slow_roll_result = None
```

## Commit

One commit, message along the lines of:
`ComputeTargets: extract _populate_from_result from store() on all three targets`
