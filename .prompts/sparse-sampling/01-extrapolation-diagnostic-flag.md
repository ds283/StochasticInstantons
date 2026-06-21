# Prompt 1 — Record extrapolation diagnostics in CompactionFunction

## Context

`ComputeTargets/CompactionFunction.py`, function `_compute_instanton_path`,
Step E ("r_max") currently computes `r_max_C_bar` either by reading off the
last inward threshold-crossing of the *computed* `C_bar(r)` array, or — when
the compaction function has not decayed below threshold by the largest
computed sample — by an analytic extrapolation:

```python
r_max_C_bar = None
if C_bar_last >= C_bar_threshold:
    r_max_C_bar = r_last * (C_bar_last / C_bar_threshold) ** (1.0 / 3.0)
else:
    for i in range(len(r_v) - 1, -1, -1):
        if C_bar_v[i] >= C_bar_threshold:
            r_max_C_bar = float(r_v[i])
            break
```

The same ambiguity exists for `r_max_C`, although that branch currently has
no extrapolation fallback (it only walks the computed array backward from
the last point — if `C_v[-1] >= C_threshold` it will return `r_v[-1]` itself,
which is also a signal worth recording, since it means the *un-averaged*
compaction function had not decayed by the edge of the computed grid
either).

This information is not currently recorded anywhere. For an upcoming
sparse-sampling / sensitivity-analysis campaign over `(N_init, N_final,
delta_Nstar)`, we want to know, per grid point, whether the reported
collapse scale came from genuine interpolation within the computed
`C_bar(r)` profile or from the analytic power-law continuation beyond the
last computed sample. This is purely a diagnostic addition — it does not
change any computed value, threshold, or stored scalar.

## Task

In `ComputeTargets/CompactionFunction.py`, inside `_compute_instanton_path`,
at Step E:

1. Record whether the `r_max_C_bar` value came from the extrapolated branch.
   Use the boolean already implicit in the existing `if C_bar_last >=
   C_bar_threshold:` test — do not duplicate or re-derive the condition,
   just capture it in a variable, e.g. `r_max_C_bar_extrapolated`, at the
   point it's evaluated.

2. Record the analogous condition for `r_max_C`: whether the last computed
   sample (`r_v[-1]`) is itself above `C_threshold`, i.e. whether the
   compaction function had not decayed below threshold anywhere on the
   computed grid (`r_max_C == r_v[-1]` AND `C_v[-1] >= C_threshold`). Call
   this `r_max_C_at_grid_edge` (it is not a true extrapolation since no
   analytic continuation is performed for `C(r)`, but it flags the same
   underlying issue: the computed `r`-grid did not extend far enough to see
   the compaction function turn over).

3. Add both booleans to the `"diagnostics"` dict already returned by
   `_compute_instanton_path` (see the `return { ... "diagnostics": {
   "type_II": ..., "n_valid_points": ..., "n_total_points": ... } }` block
   at the end of the function). Use the keys `"r_max_C_bar_extrapolated"`
   and `"r_max_C_at_grid_edge"`.

4. If `r_max_C_bar` is `None` (i.e. `C_bar(r)` never exceeded threshold
   anywhere, including at the last point), `r_max_C_bar_extrapolated` must
   be `False`. Same for `r_max_C_at_grid_edge` when `r_max_C` is `None`.
   Do not let either flag be `True` when the corresponding `r_max_*` is
   `None` — that combination is meaningless and should never appear in
   stored diagnostics.

5. Do not touch `_compute_compaction_function`, `CompactionFunction.store()`,
   or any of the Datastore factory code. The existing `diagnostics_json`
   round-trip (`Datastore/SQL/ObjectFactories/CompactionFunction.py`) already
   serialises and restores the full `diagnostics` dict via
   `obj._diagnostics`/`json.loads(row.metadata)` — these new keys will pass
   through that machinery unchanged, with no schema or factory edits
   required. Confirm this by inspection, but do not modify those files.

6. No changes to any numerical computation, threshold comparison, stored
   scalar (`r_max_C`, `r_max_C_bar`, `M_C`, `M_C_bar`, `C_max`, `C_bar_max`),
   or existing diagnostics keys (`type_II`, `n_valid_points`,
   `n_total_points`). This prompt only adds two new boolean keys to the
   existing diagnostics dict.

## Acceptance criteria

- [ ] `_compute_instanton_path` returns a `diagnostics` dict containing the
      two new boolean keys `r_max_C_bar_extrapolated` and
      `r_max_C_at_grid_edge`, in addition to the three existing keys.
- [ ] `r_max_C_bar_extrapolated is True` if and only if `r_max_C_bar` was
      set via the `r_last * (C_bar_last / C_bar_threshold) ** (1/3)`
      branch.
- [ ] `r_max_C_at_grid_edge is True` if and only if `r_max_C == r_v[-1]`
      and `C_v[-1] >= C_threshold` (equivalently: the backward-scanning
      loop for `r_max_C` terminated on its very first iteration, `i = len(r_v) - 1`).
- [ ] Both flags are `False` (never `None`, never omitted) whenever the
      corresponding `r_max_C`/`r_max_C_bar` is `None`.
- [ ] No existing returned value (`r`, `zeta`, `C`, `C_bar`, `r_max_C`,
      `r_max_C_bar`, `M_C`, `M_C_bar`, `C_max`, `C_bar_max`,
      `V_end_downflow`, `N_end_downflow`, `type_II`, `n_valid_points`,
      `n_total_points`) changes value, type, or presence for any input.
- [ ] `git diff` touches only `ComputeTargets/CompactionFunction.py`.
- [ ] Write or extend a unit test (wherever existing tests for
      `CompactionFunction`/`_compute_instanton_path` live — locate via
      `git grep` before assuming a path) that constructs a synthetic
      `zeta(r)` profile that:
        - decays well below threshold within the computed grid
          (`r_max_C_bar_extrapolated == False`,
          `r_max_C_at_grid_edge == False`), and
        - remains above threshold at the last computed sample
          (`r_max_C_bar_extrapolated == True`,
          `r_max_C_at_grid_edge == True`).
      Both cases must be exercised and asserted.
- [ ] Confirm by inspection (not by editing) that
      `Datastore/SQL/ObjectFactories/CompactionFunction.py`'s
      `diagnostics_json` round-trip requires no change, and state this
      explicitly in the PR/commit description.

## Out of scope (do not attempt in this prompt)

- The `--sample-grid-csv` ingestion work for `main.py` /
  `plot_InstantonSolutions.py` (separate prompt).
- The scalars-only storage mode and `_do_not_populate` build-time guard
  for `FullInstanton`, `SlowRollInstanton`, `CompactionFunction` (separate
  prompts).
- Any change to `CompactionFunction.store()` or the Datastore factories.
- Any change to threshold values, extrapolation formula, or scale
  assignment logic.

## Commit

One commit, message along the lines of:
`CompactionFunction: record extrapolation diagnostics for r_max_C_bar / r_max_C`
