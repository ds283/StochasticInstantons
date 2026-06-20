# StochasticInstanton — Project Instructions

This project computes stochastic instantons in inflationary scalar field models.
It is a refactoring of ChamPBH, sharing its infrastructure but replacing all
chameleon/dark-energy physics with inflationary physics.

## Build and test

```bash
python main.py --database <path> [--inventory]
python -c "..."   # used for acceptance-criteria checks in prompts
```

Ray must be running. Start a local cluster with `ray start --head` before running.

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
A list causes a silent `KeyError` deep inside `ShardedPool`.

**3. `sharded_tables` and `replicated_tables` partition the tables — never both.**
Every table name belongs in exactly one of the two collections in
`config/sharding.py`. `delta_Nstar` is the shard key type, so it belongs only
in `replicated_tables`; listing it in `sharded_tables` too made
`ShardedPool.read_table()` wrongly reject it as sharded. See
`.claude/rules/pool-read-apis.md` for the full incident and reasoning.

**4. All splines use `SplineWrapper`; never call scipy interpolation primitives directly.**
When adding a new spline, ask the human which x/y transforms to apply before
writing code. When adding a root-finder through a spline, ask the human or use
the transformed-coordinate `brentq` pattern. See
`.claude/rules/spline-interpolation.md` for the full pattern and transform
catalogue.

**5. `validate_on_startup` must cascade-delete child value rows before deleting parent rows.**
The value tables (`FullInstantonValue`, `SlowRollInstantonValue`,
`CompactionFunctionSamples`) have no `ON DELETE CASCADE`. Deleting unvalidated
parent rows without first deleting their child rows leaves orphans; SQLite then
reuses the freed serials, causing UNIQUE constraint violations on the next run.
Always `DELETE FROM <value_table> WHERE <fk_col> IN (serials)` first.
See `.claude/rules/validate-on-startup.md` for the cascade map and pattern.

## Protected infrastructure

Never modify these files unless a prompt explicitly names them and describes
exactly what to change:

```
RayTools/                          Datastore/SQL/ShardedPool.py
Datastore/object.py                Datastore/SQL/SerialPoolBroker.py
Datastore/SQL/ClientPool.py        Datastore/SQL/ProfileAgent.py
Datastore/SQL/ObjectFactories/base.py
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

When a prompt says "modify `Datastore/SQL/Datastore.py`", change only what it
describes (e.g. adding factory entries). Do not reformat or reorder anything else.

## Units convention

All physics quantities use reduced Planck units: `Mp = 1` (i.e. `8πG = 1`).
Dimensionful quantities store values divided by the appropriate unit
(e.g. `value / units.PlanckMass`). Do not store raw SI values.

## Project name

This project is **StochasticInstanton**. Use this name in comments, docstrings,
and log messages — not StochasticInflaton.
