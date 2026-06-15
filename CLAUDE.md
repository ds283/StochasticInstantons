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

Two rules have caused rework when violated. They are detailed in
`.claude/rules/ray-dispatch.md` but summarised here for visibility:

**1. Compute target classes are plain Python. Never `@ray.remote` a class.**
`InflatonTrajectory`, `FullInstanton`, `SlowRollInstanton` — and any future compute
targets — must be plain `class Foo(DatastoreObject):` with no decorator. The
`@ray.remote` decorator goes on a separate top-level *function* that does the work.
See `.claude/rules/ray-dispatch.md` for the full pattern.

**2. `sharded_tables` in `config/sharding.py` is a dict, never a list.**
It maps `table_name → shard_key_field_name` (e.g. `{"delta_Nstar": "shard_key"}`).
A list causes a silent `KeyError` deep inside `ShardedPool`.

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
