# Prompt 02b — Live `ShardedPool` test fixture, and the deferred dedup test

## Context

Prompt 2 added `config/grid_builder.py::build_grid_from_csv`, which mints
`N_init`/`N_final`/`delta_Nstar` domain objects via `pool.object_get(...)`,
on the design assumption that this resolves to the same `store_id`s as the
existing axis-grid path (`build_pipeline_inputs` → `build_cartesian_grid`)
when given the same float values. The existing test suite
(`tests/test_grid_builder.py`) verified this only against a mock pool that
returns a fresh object on every call — it does not verify idempotent
deduplication against a real, shared datastore, which was an explicit
acceptance criterion of prompt 2 that wasn't met.

There is currently no reusable fixture for testing against a live
`ShardedPool`. This prompt builds one, then uses it to write the missing
dedup test. The fixture is deliberately written for reuse beyond this one
test — upcoming prompts (the scalars-only storage mode and
`_do_not_populate` build-time guard for `FullInstanton`,
`SlowRollInstanton`, `CompactionFunction`) will need to verify store/build
round-trips against a real database, not mocks, and should be able to
depend on this fixture rather than each rolling their own.

**Before writing anything**, inspect how `ShardedPool` is constructed and
used in `plot_InstantonSolutions.py` (the `with ShardedPool(...) as pool:`
block near the bottom of the file, including its imports from
`config.sharding`) and in `main.py`'s `ray.init(...)` call — this prompt's
fixture should follow the same construction pattern, not invent a new one.
Also check whether `pytest.ini`/`pyproject.toml`/`tests/conftest.py`
already define any markers (e.g. `slow`, `integration`) or `ray.init`
conventions elsewhere in the test suite, and follow existing convention if
one exists rather than introducing a second one.

## Task

### 1. A reusable live-`ShardedPool` fixture

Add a pytest fixture (suggest `tests/conftest.py`, or a new
`tests/fixtures_sharded_pool.py` imported by `conftest.py` — match whatever
the existing test layout favours) that:

- Initialises Ray appropriately for a single-process test run (local mode
  or `ray.init(ignore_reinit_error=True)` with a small `num_cpus`, by
  analogy with `main.py`/`plot_InstantonSolutions.py`'s `ray.init(...)`
  call — avoid leaving a Ray session running across unrelated test files if
  the existing suite doesn't already handle that; check for an existing
  session-scoped Ray fixture before adding a second one).
- Creates a temporary SQLite database (use pytest's built-in `tmp_path`)
  with `shards=1` — a single shard is sufficient for these tests and keeps
  setup/teardown fast.
- Constructs `ShardedPool` using `config.sharding`'s `ShardKeyType`,
  `get_shard_key_store_id`, `replicated_tables`, `sharded_tables`,
  `read_table_config`, `inventory_config` — the same production
  configuration objects used everywhere else, not test-only stand-ins,
  since the whole point is to exercise the real factory/table wiring.
- Yields the live `pool` (as a context manager, matching the `with
  ShardedPool(...) as pool:` pattern), and tears down cleanly — pool
  closed, no leftover Ray actors, temp DB file cleaned up automatically via
  `tmp_path`.
- Keep the fixture parameters close to production defaults
  (`prune_unvalidated=False`, `drop_actions=[]`, a fixed
  `version_label`/`job_name` string for test runs) rather than
  over-generalising — it only needs to support what this prompt and the
  near-future store/build-guard prompts require. Don't build a
  configurable-everything fixture speculatively.
- If constructing `ShardedPool` requires non-trivial setup beyond what's
  visible from `plot_InstantonSolutions.py` (e.g. database schema
  initialisation, an `inventory`-only first pass), discover this by running
  it, not by guessing — iterate until a pool actually comes up clean
  against an empty temp database.

Mark any test using this fixture appropriately (new or existing marker —
follow repo convention per the investigation above; if none exists,
introduce `@pytest.mark.integration` and register it in `pytest.ini`/
`pyproject.toml`, and note in the commit message that you did so) so the
fast unit-test suite (`tests/test_grid_builder.py` etc.) can continue to be
run without spinning up Ray/SQLite if desired.

### 2. The dedup test itself

Using the fixture, write a test (in `tests/test_grid_builder.py` or a new
`tests/test_grid_builder_integration.py` — your call, but don't mix
fixture-using and mock-using tests in a way that makes it unclear which is
which) that:

1. Mints an `N_init` object (and ideally also `N_final`, `delta_Nstar`) for
   a specific float value against the live pool, via whatever call
   `build_pipeline_inputs`/`build_cartesian_grid`'s path actually uses
   (call it directly, or call `build_pipeline_inputs` itself if that's
   feasible against the fixture's minimal pool — your judgement on which
   is more robust against future drift in `build_pipeline_inputs`'s
   internals).
2. Records the resulting `store_id`(s).
3. Calls `build_grid_from_csv` with a CSV containing the **same** float
   value(s), against the **same** pool.
4. Asserts the resulting `store_id`(s) are identical to step 2 — not just
   that the float values match.
5. Additionally queries the relevant table (e.g. via `pool.read_table` or
   the factory's `inventory` method, whichever is more direct) to assert
   there is exactly **one** row for that value, not two — this is the
   actual failure mode being guarded against (duplicate near-identical
   rows), and asserting only on `store_id` equality without also checking
   row count would miss a factory that happens to return a stale ID while
   still inserting a duplicate row.

Also add the inverse sanity check: two **different** float values produce
**different** `store_id`s, mediated through both paths — i.e. confirm the
test isn't trivially passing because everything maps to a single sentinel
ID regardless of input.

## Acceptance criteria

- [ ] A reusable live-`ShardedPool` pytest fixture exists, documented with
      a docstring explaining it's intended for reuse by future
      store/build round-trip tests, not just this one.
- [ ] The fixture tears down cleanly — running the test file twice in a
      row, or alongside the rest of the suite, does not leave stale Ray
      actors, locked SQLite files, or fail on the second run.
- [ ] A new test verifies `store_id` equality between the axis-grid path
      and the CSV path for matching float values, against a real pool —
      not a mock.
- [ ] The same test (or a sibling) verifies no duplicate row is created in
      the underlying table for the matching value.
- [ ] A sanity check confirms distinct float values still resolve to
      distinct `store_id`s through both paths.
- [ ] Existing fast tests in `tests/test_grid_builder.py` are unaffected
      and still run without requiring Ray/a live pool (verify by running
      just that file, or whatever subset the repo's marker convention
      excludes, in isolation).
- [ ] `git diff` is limited to test files
      (`tests/conftest.py`/`tests/fixtures_sharded_pool.py`,
      `tests/test_grid_builder.py` and/or a new integration test file) and,
      if a new marker was introduced, the relevant `pytest.ini`/
      `pyproject.toml` entry. No production code
      (`config/grid_builder.py`, `main.py`, factories) should need to
      change to make this test pass — if it does, stop and report back
      rather than altering production code to fit the test, since that
      would indicate the original prompt-2 implementation has a real bug,
      not just a test gap.

## Out of scope (do not attempt in this prompt)

- `plot_InstantonSolutions.py` changes.
- The scalars-only storage mode / `_do_not_populate` build-time guard for
  `FullInstanton`, `SlowRollInstanton`, `CompactionFunction` — but do leave
  the fixture in a state that's obviously reusable for that work (e.g.
  don't hardcode anything to `N_init`/`delta_Nstar`-only tables in a way
  that would need rewriting).
- Any change to `config/grid_builder.py` itself, unless the dedup test
  reveals an actual bug — see the last acceptance-criteria bullet.

## Commit

One commit, message along the lines of:
`tests: add live ShardedPool fixture; verify CSV/axis-grid store_id dedup`
