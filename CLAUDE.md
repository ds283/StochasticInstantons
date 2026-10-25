# StochasticInstanton — Project Instructions

This project computes stochastic instantons in inflationary scalar field models.
It is a refactoring of ChamPBH, sharing its infrastructure but replacing all
chameleon/dark-energy physics with inflationary physics.

## Build and test

```bash
python main.py --database <path> --ray-address <address> [--inventory]
python -c "..."   # used for acceptance-criteria checks in prompts
```

`--ray-address` is required by `main.py` and both plot scripts; there is no
`auto` default. Pass `local` for a private in-process Ray instance, or a
cluster's GCS address. Rehearsals and long builds run on SI's isolated cluster
under the shared rehearsal lock: `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
start PURPOSE`, then `--ray-address 127.0.0.1:6390`. The lock is the pinned
package's `raypoolkit.rehearsal_lock` (`~/.raypoolkit/rehearsal-lock`, shared
with ChamPBH and SecondaryGWKit; its contract is RayPoolKit's
`docs/rehearsal-lock.md`), and a held lock, exit 3 (given too while the lock's
old location exists), means stop and ask, never wait. The lock lists every
process whose command line names `/tmp/ray-si`, and that process's other
descendants: so no `PURPOSE` names it, and a lock command typed by hand is the
only process of its shell command, its output redirected, never piped (the
contract, §6). Never run `ray stop`: it
stops every Ray process on the machine, other projects' clusters included (see
`.prompts/dk-and-rpk-migration/rehearsal-lock-brief.md`).

The physics notes for the onion model live in `notes/onion-model/onion_model.tex`
(build with `latexmk -pdf`; `jcappub.sty` must be installed). They are the
reference for how the calculation should be performed and carry no
implementation details.

Default test run: `pytest -m "not integration and not slow"` (732 of 868
tests; 731 pass and 1 is skipped; well under a minute). The other 136 are the
67 `integration`-marked tests, which need a live Ray instance and a SQLite
store (`RAY_ADDRESS=local pytest -m integration`), and the 69 `slow`-marked
ones. The `slow`-marked block of the suite runs real
ODE/spectral solves that take minutes each and is only worth including when
the change touches `ComputeTargets/`, `Numerics/`, `Interpolation/`, or
`tools/diagnostics/GradientCoupledInstanton/spectrum.py`. See
`.claude/rules/test-selection.md` for the full decision rule and the current
list of `slow`-marked files.

## Long-running jobs — the run registry

RunRegistryKit (`runregistrykit`, pinned at `v0.2.0` with its store layer) records each registered
run in `var/runs/`; `runregistrykit.toml` at the repository root configures it. It records; it does
not schedule, supervise, restart or lock. The detail is `.claude/rules/run-registry.md`.

- **Discovery.** Run `./venv/bin/python -m runregistrykit list` at the start of a session (the
  `SessionStart` hook in `.claude/settings.json` runs it) and before launching anything long, and
  report anything `running`, stale or unknown.
- **Launching.** A registered run goes through the wrapper `RunDrivers/registered_run.py`, from
  the root: `PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --campaign C --prompt N
  --register SLUG --purpose "one line" -- <main.py's arguments>`. `main.py` stays launchable on
  its own, without the registry, and a run launched that way is recorded nowhere. The plot scripts and `main.py --inventory` are
  never registered.
- **Stores** of registered runs live under `var/datastores/`. Since `var/` is ignored, **never run
  `git clean` with `-x` or `-X`**, which deletes ignored files, the stores among them.

## Critical rules — read before touching any file

Five rules have caused rework when violated. They are detailed in
`.claude/rules/ray-dispatch.md`, `.claude/rules/pool-read-apis.md`,
`.claude/rules/spline-interpolation.md`, and
`.claude/rules/validate-on-startup.md` but summarised here for visibility:

**1. Compute target classes are plain Python. Never `@ray.remote` a class.**
`InflatonTrajectory`, `FullInstanton`, `SlowRollInstanton` — and any future compute
targets — must be plain `class Foo(DatastoreObject):` with no decorator. The
`@ray.remote` decorator goes on a separate top-level *function* that does the work.
See `.claude/rules/ray-dispatch.md` for the full pattern.

**2. `sharded_tables` in `config/sharding.py` is a dict, never a list.**
It maps `table_name → shard_key_field_name` (e.g. `{"FullInstanton": "delta_Nstar"}`).
A list causes a silent `KeyError` deep inside `ShardedPool`. The pool is the
`datastorekit` package's; its constructor's table lists are DatastoreKit's
client contract, §1 (rows 5, 6 and 13).

**3. `sharded_tables` and `replicated_tables` partition the tables — never both.**
Every table name belongs in exactly one of the two collections in
`config/sharding.py`. `delta_Nstar` is the shard key type, so it belongs only
in `replicated_tables`; listing it in `sharded_tables` too made
`ShardedPool.read_table()` wrongly reject it as sharded. See
`.claude/rules/pool-read-apis.md` for the full incident and reasoning, and
DatastoreKit's client contract, §1 (rows 5 and 6), for what the pool does with
each list.

**4. All splines use `SplineWrapper`; never call scipy interpolation primitives directly.**
When adding a new spline, ask the human which x/y transforms to apply before
writing code. When adding a root-finder through a spline, ask the human or use
the transformed-coordinate `brentq` pattern. See
`.claude/rules/spline-interpolation.md` for the full pattern and transform
catalogue.

**5. `validate_on_startup` must cascade-delete child value rows before deleting parent rows.**
The value tables (every child table in the cascade map) have no
`ON DELETE CASCADE`. Deleting unvalidated
parent rows without first deleting their child rows leaves orphans; SQLite then
reuses the freed serials, causing UNIQUE constraint violations on the next run.
Always `DELETE FROM <value_table> WHERE <fk_col> IN (serials)` first.
See `.claude/rules/validate-on-startup.md` for the cascade map and pattern. The
package calls the hook (DatastoreKit's client contract, §3, with §9.5); for a replicated
table it prunes the owner with the rows of its unit, which a child table joins
by declaring an `owner_column` (§2).

## Campaigns, the campaign index and the open-issues board

Work is organised in campaigns: prompts in `.prompts/<campaign>/`, results
notes in `.documents/<campaign>/`. Every new campaign opens an
`IMPLEMENTATION_STATE.md` status board in its prompt folder; the board is the
record for that campaign's issues. Two project-wide files index them:

- `.prompts/INDEX.md` — one line per campaign (status, dates, what it owns,
  where its results and open issues are).
- `.documents/OPEN-ISSUES.md` — one line per open issue, pointing at the
  board (or, for issues no board owns yet, the reconstruction, a tex `todo` or
  a results note) that holds its content. It is an index, not a record.

**Maintenance rule.** Whenever an issue is opened, narrowed or closed — on a
board, in a results note, in a tex `todo`, or by a decision of the user —
update `OPEN-ISSUES.md` **in the same commit**: add the line, move it between
sections, or move it to the closed section, and correct the count and the date
in its header. When a campaign is created, changes status or closes, update
its line in `INDEX.md` in the same commit. When a campaign's board adopts an
issue that `OPEN-ISSUES.md` points elsewhere, re-point the row at the board.

## Protected infrastructure

Never modify these files unless a prompt explicitly names them and describes
exactly what to change:

```
Datastore/SQL/ObjectFactories/version.py
Datastore/SQL/ObjectFactories/store_tag.py
Datastore/SQL/ObjectFactories/tolerance.py
Datastore/SQL/ObjectFactories/DimensionlessQuantity.py
Datastore/SQL/ObjectFactories/DimensionfulQuantity.py
Datastore/SQL/ObjectFactories/integration_metadata.py
Datastore/SQL/ObjectFactories/redshift.py
Quadrature/integration_metadata.py
Quadrature/supervisors/base.py
Units/    MetadataConcepts/    utilities.py    constants.py
```

None of the list is a file of either package. The datastore layer (`ShardedPool`,
the `Datastore` actor, `ClientPool`, `SerialPoolBroker`, `ProfileAgent`,
`DatastoreObject` and `SQLAFactoryBase`) is the `datastorekit` package, and
`RayWorkPool` is the `raypoolkit` package. Each is pinned to a tag in
`requirements.txt` (`datastorekit` `v0.5.0`, `raypoolkit` `v0.3.0`), installed
from it and never editable; SI has no copy of either. What a client supplies to
the first is DatastoreKit's `docs/client-contract.md` at the tag; how the second
is called is RayPoolKit's `README.md` at its tag, "Using it".
**A defect in either package is reported to that package's repository, fixed in
a new release, and reaches SI by a new pin prompt; it is never patched or worked
around in SI** (DatastoreKit's `v0.3.0` for `DatastoreObject.timestamp` and
`v0.5.0` for `extra_values` were made at SI's request). SI's own data for the
datastore package (the factory registry, the `--drop` groups and the serial
batch sizes) is `config/datastore.py`. Do not reformat or reorder anything else
in a file you are told to modify.

## Units convention

All physics quantities use reduced Planck units: `Mp = 1` (i.e. `8πG = 1`).
Dimensionful quantities store values divided by the appropriate unit
(e.g. `value / units.PlanckMass`). Do not store raw SI values.

## Project name

This project is **StochasticInstanton**. Use this name in comments, docstrings,
and log messages — not StochasticInflaton.
