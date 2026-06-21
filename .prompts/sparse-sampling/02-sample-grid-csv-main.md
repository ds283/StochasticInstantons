# Prompt 2 — `config/grid_builder.py` and `--sample-grid-csv` in `main.py`

## Context

`main.py` currently builds the full `(model, N_init, N_final, delta_Nstar)`
sweep as a Cartesian product:

```python
grid = list(
    itertools.product(
        range(len(model_list)), N_init_array, N_final_array, delta_Nstar_array
    )
)
```

where `N_init_array`, `N_final_array`, and `delta_Nstar_array` (referred to
as `dns_objects` later in `main.py`) are lists of already-persisted domain
objects (`N_init`, `N_final`, `delta_Nstar` — see
`InflationConcepts/N_init.py`, `InflationConcepts/N_final.py`,
`InflationConcepts/delta_Nstar.py`), built from the `--N-init-low/--N-init-high/
--N-init-samples` (etc.) CLI arguments via `config.pipeline_setup.build_pipeline_inputs`.

**Important — read `config/pipeline_setup.py` (specifically
`build_pipeline_inputs`) before writing any code.** It is not included in
this prompt because its exact mechanism for minting/looking-up `N_init`,
`N_final`, `delta_Nstar` domain objects against the `ShardedPool` (almost
certainly via `pool.object_get(...)` calls, by analogy with how
`delta_Nstar` is minted elsewhere — see
`Datastore/SQL/ObjectFactories/delta_Nstar.py` and
`Datastore/SQL/ObjectFactories/DimensionlessQuantity.py`) is not visible to
this prompt's author and must not be guessed. The new CSV-ingestion path
introduced below **must mint its `N_init`/`N_final`/`delta_Nstar` objects
through the exact same `pool.object_get` pattern** `build_pipeline_inputs`
uses for the axis-grid path. This is not optional: if a CSV-specified
triple happens to coincide with a value already in the datastore (e.g. you
re-run an overlapping sample-grid-csv against an existing production run),
it must resolve to the *same* `store_id`, not mint a duplicate row. Getting
this wrong silently bloats the `N_init`/`N_final`/`delta_Nstar` lookup
tables and breaks the existing-record dedup that the rest of the pipeline
(`key_fields` in `main.py`) relies on for idempotent re-runs.

We want to add a second way of specifying the `(N_init, N_final,
delta_Nstar)` sweep: an explicit CSV of triples (for sparse / space-filling
/ active-learning sampling designs), as an alternative to the existing
low/high/samples axis-grid + Cartesian-product approach. This prompt:

1. extracts the existing Cartesian-product construction into a new shared
   module `config/grid_builder.py`, unchanged in behaviour;
2. adds the CSV-ingestion path alongside it in the same module;
3. wires both into `main.py`, replacing the inline `itertools.product(...)`
   call.

`plot_InstantonSolutions.py` is **out of scope for this prompt** — that's
the next prompt, and it will simply import and call the same
`config.grid_builder` functions written here.

## Task

### 1. `config/grid_builder.py` (new file)

Provide (at minimum) these two public entry points — exact signatures may
need adjusting once you've inspected `build_pipeline_inputs`'s actual
return types, but the shape should be:

```python
def build_cartesian_grid(model_list, N_init_array, N_final_array, delta_Nstar_array):
    """
    Existing behaviour, extracted verbatim from main.py: the full
    (model_idx, N_init, N_final, delta_Nstar) Cartesian product.
    """
    ...

def build_grid_from_csv(pool, csv_path, model_list, ...):
    """
    Parse csv_path (columns: N_init, N_final, delta_Nstar — float values),
    mint/look up the corresponding N_init/N_final/delta_Nstar domain
    objects via pool.object_get(...) using the SAME pattern
    build_pipeline_inputs uses for the axis-grid path, and return the
    (model_idx, N_init, N_final, delta_Nstar) tuples crossed only against
    model_list (NOT against itself).
    """
    ...

def build_instanton_grid(pool, model_list, args):
    """
    Top-level dispatcher. If args.sample_grid_csv is set, delegate to
    build_grid_from_csv. Otherwise, build N_init_array/N_final_array/
    delta_Nstar_array exactly as build_pipeline_inputs currently does and
    delegate to build_cartesian_grid. Returns the same grid structure
    main.py currently builds inline.
    """
    ...
```

Whether `build_instanton_grid` calls `build_pipeline_inputs` itself, or
whether `main.py` continues to call `build_pipeline_inputs` and passes the
resulting arrays in, is your call — pick whichever keeps `main.py`'s
existing non-grid uses of `inputs` (atol, rtol, phi0, pi0, model_list
itself, etc. — inspect `main.py` around `inputs = build_pipeline_inputs(...)`
for the full list of consumers) intact with minimal disruption. Either way,
the Cartesian-product *axis-array construction* itself (low/high/samples →
list of domain objects) stays in `pipeline_setup.py`/`build_pipeline_inputs`
for now — only the `itertools.product(...)` combination step and the new
CSV path move into `grid_builder.py`. (We may migrate the axis-array
construction into `grid_builder.py` too at some point, but that is not part
of this prompt — don't do it preemptively.)

### 2. CSV format and validation

- Required header: `N_init,N_final,delta_Nstar` (any column order,
  case-sensitive match to these names).
- Any missing required column, non-numeric value, or empty file is a hard
  error (raise, with a message naming the file and the problem) — never
  silently coerce to NaN or skip a malformed row.
- Duplicate triples in the CSV are allowed (not an error) — they should
  simply dedupe naturally once minted, since identical float values mint/
  resolve to the same domain-object `store_id`.

### 3. `config/argument_parser.py`

Add `--sample-grid-csv` to the "Instanton parameters" argument group:

```python
inst.add_argument(
    "--sample-grid-csv",
    type=str,
    default=None,
    help="Path to a CSV file of explicit (N_init, N_final, delta_Nstar) "
    "triples, used in place of the --N-init-*/--N-final-*/--delta-Nstar-* "
    "axis-grid arguments. Crossed against --m-values-Mp / model list as "
    "usual, but NOT crossed against itself.",
)
```

If `--sample-grid-csv` is given **together with** any of
`--N-init-values`, `--N-final-values`, `--delta-Nstar-values`, or any of
the `--N-init-low/high/samples` / `--N-final-low/high/samples` /
`--delta-Nstar-low/high/samples` arguments at non-default values, this is a
configuration error: raise a clear error at startup (in
`build_instanton_grid` or wherever you find natural) rather than silently
picking one source over the other. Use whatever mechanism
`configargparse` gives you to detect "argument left at its default" versus
"explicitly supplied" if available; if it doesn't cleanly support that,
it is acceptable to document the precedence explicitly (CSV wins,
axis-grid arguments are ignored with a printed warning) instead of hard
erroring — your call once you've checked what `configargparse` exposes,
but pick one approach and make it explicit, not implicit.

### 4. `main.py`

Replace the existing:

```python
grid = list(
    itertools.product(
        range(len(model_list)), N_init_array, N_final_array, delta_Nstar_array
    )
)
```

with a call into `config.grid_builder.build_instanton_grid(...)` (or
equivalent), preserving everything downstream of `grid` (the `key_fields`
function, the `RayWorkPool` dispatch, etc.) completely unchanged. Remove
the `import itertools` from `main.py` only if it is no longer used there
after this change — check first.

## Acceptance criteria

- [ ] `config/grid_builder.py` exists with `build_cartesian_grid`,
      `build_grid_from_csv`, `build_instanton_grid` (or equivalently named/
      shaped functions — naming is not sacred, the three responsibilities
      are).
- [ ] Running `main.py` with no `--sample-grid-csv` produces an
      **identical** `grid` list (same tuples, same order) to the current
      `main` branch, for at least one existing `--config` YAML / CLI
      invocation used in this repo's test suite or documented examples.
      This must be verified by an actual test, not just code inspection.
- [ ] Running `main.py` with `--sample-grid-csv` pointing at a CSV whose
      triples exactly match a subset of an existing axis-grid run resolves
      to the **same `store_id`s** for `N_init`/`N_final`/`delta_Nstar` as
      the axis-grid run — verified by a test that runs both paths against
      the same `ShardedPool`/database and compares store IDs, not just
      compares float values.
- [ ] Malformed CSV (missing column, non-numeric value, empty file) raises
      a clear, specific exception rather than crashing deep in pandas/csv
      internals or silently producing `NaN`/empty grid.
- [ ] Simultaneous `--sample-grid-csv` and explicit axis-grid arguments is
      handled per whichever of the two approaches above you settle on
      (hard error or documented-precedence warning) — pick one, implement
      it, and state which in the commit message.
- [ ] `git diff` touches `config/grid_builder.py` (new),
      `config/argument_parser.py`, and `main.py` only.
      `plot_InstantonSolutions.py` is untouched.
- [ ] Unit tests for `config/grid_builder.py` covering: (a) cartesian path
      matches `itertools.product` directly for a small synthetic
      `model_list`/axis-array input; (b) CSV path produces the correct
      `len(model_list) * len(csv_rows)` tuples with correct crossing
      (model varies, triple does not get crossed against itself); (c) each
      malformed-CSV case from the bullet above.

## Out of scope (do not attempt in this prompt)

- `plot_InstantonSolutions.py` changes (next prompt).
- The scalars-only storage mode / `_do_not_populate` build-time guard for
  `FullInstanton`, `SlowRollInstanton`, `CompactionFunction`.
- Migrating the axis-array construction itself (currently in
  `build_pipeline_inputs`) into `grid_builder.py` — noted above as
  deliberately deferred.
- Generating sample-grid CSVs (e.g. via Latin hypercube / Sobol) — that's
  a standalone analysis script, not part of the pipeline codebase.

## Commit

One commit, message along the lines of:
`config: extract grid construction into grid_builder.py; add --sample-grid-csv`
