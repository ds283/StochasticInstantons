# `ShardedPool` read APIs — `read_table()` vs `inventory()`

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`. It applies whenever code calls `pool.read_table()` or
`pool.inventory()` — driver scripts (`main.py`, `plot_*.py`) and anywhere else
that consumes a `ShardedPool`.

## `pool.inventory()` is a human-readable summary tool, not a data API

`pool.inventory(cls_name)` exists to print/report what's in the datastore
(`main.py`'s `inventory()` function, `_inventory_dimensionless`,
`_inventory_object`, etc.). It returns aggregated, lossy summaries — lists of
labels, counts, earliest/latest timestamps — not full deserialised objects
with valid `store_id`s. Do not call it to fetch objects for use in a pipeline
(e.g. to obtain `delta_Nstar` instances to pass into `object_get()` payloads).

## If `pool.read_table()` raises for a replicated table, fix the config

`pool.read_table(cls_name, ...)` is the correct API for fetching fully
deserialised objects from a replicated table. If it raises
`RuntimeError: ... the read_table service is not available for objects of
class "..."`, the fix is to add an entry to `read_table_config` in
`config/sharding.py` — not to route around the gap with `pool.inventory()`.

```python
read_table_config = {
    "InflatonTrajectory": {"tables_arg": True},
    "delta_Nstar": {"tables_arg": False},   # add the missing table here
    ...
}
```

`config/sharding.py` is listed as protected infrastructure in `CLAUDE.md`, so
adding this entry requires the user's explicit go-ahead — flag the missing
entry and ask, rather than reaching for `pool.inventory()` as a workaround.

## `sharded_tables` and `replicated_tables` partition the database's tables

Every table name in `config/sharding.py` must appear in exactly one of
`replicated_tables` or `sharded_tables` — never both, never neither. A table
is replicated (copied identically to every shard) or it is sharded
(partitioned across shards by a key field); it cannot be both.

`delta_Nstar` previously appeared in both: it's the shard key type, so it
belongs in `replicated_tables`, but it was *also* listed in `sharded_tables`
(as `"delta_Nstar": "shard_key"`) on the theory that this was needed as
"metadata". It wasn't — every dispatch site (`object_get`, `object_store`,
`object_validate`) checks `replicated_tables` first and returns before ever
consulting `sharded_tables`, so the entry was dead for routing purposes. But
`ShardedPool.read_table()` checks raw membership in `sharded_tables` with no
replicated-first carve-out, so the stray entry made it reject `delta_Nstar`
as "sharded" and raise, even though it is fully replicated. Fixed by removing
`delta_Nstar` from `sharded_tables`, keeping it only in `replicated_tables`.

When adding a new table to `config/sharding.py`, add it to exactly one of the
two collections. If a table seems to need to appear in both, that's a sign
something else is being conflated with shard-key routing — read both
collections' docstring comments and `object_get`/`object_store` in
`ShardedPool.py` before adding it to either.

## `pool.read_table()` only ever works for replicated tables

`ShardedPool.read_table()` explicitly raises if `cls_name` is in
`sharded_tables` (it reads from a single, randomly chosen shard, which would
silently drop data for anything actually partitioned across shards, e.g.
`FullInstanton`, `SlowRollInstanton`). For sharded tables, fetch records via
per-item `pool.object_get(cls_name, **payload)` calls keyed by the shard key
(`delta_Nstar`), as in `main.py`'s `fi_payload`/`sri_payload` pattern — not via
`read_table()` and not via `inventory()`.
