# `_populate()` must ORDER BY and assert monotonicity

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`. It applies to every `_populate()` method in
`Datastore/SQL/ObjectFactories/` that reads a multi-row child/value table.

## Root cause

SQLite gives no row-order guarantee for a query without `ORDER BY`. Value lists
built without an explicit ordering are consumed downstream as implicitly-ordered
arrays — plotted as lines, fed into cumulative integrals, or zipped against an
r/N grid. Out-of-order reads produce zigzag artefacts in plots and wrong
numerical results. This was confirmed via `CompactionFunction(id=17483)`:
a fold-back in the C̄(r) curve that vanished when data was recomputed from
scratch, with the integration math independently verified correct.

## The rule

**Every `_populate()` that reads a child table must:**

1. Add an explicit `ORDER BY` on the physically meaningful ordering key:
   - `r_Mpc` (and `source`) for compaction-function samples
   - `efold_value.N` for instanton value tables (not `N_serial` — the FK serial
     is not guaranteed to correlate with ascending N)

2. Assert that the ordering key is strictly non-decreasing after the read, so
   this class of bug fails loudly rather than silently producing bad plots:

```python
# For r-ordered values (CompactionFunction):
for label, vals in (("full", full_vals), ("slow_roll", sr_vals)):
    r_vals = [v.r for v in vals]
    if any(r_vals[i] > r_vals[i + 1] for i in range(len(r_vals) - 1)):
        raise RuntimeError(
            f"CompactionFunction(id={obj.store_id}): {label} sample r-values "
            f"are not non-decreasing after ORDER BY — database may be corrupt"
        )

# For N-ordered values (FullInstanton, SlowRollInstanton):
N_vals = [v.N.N for v in obj._values]
if any(N_vals[i] > N_vals[i + 1] for i in range(len(N_vals) - 1)):
    raise RuntimeError(
        f"Foo(id={obj.store_id}): N-values are not non-decreasing after "
        f"ORDER BY — database may be corrupt"
    )
```

3. For instanton value tables, **use a JOIN** to fetch `efold_value.N` in the
   same query rather than a per-row follow-up lookup (N+1 query anti-pattern).
   Order by `efold_table.c.N`:

```python
rows = conn.execute(
    sqla.select(
        value_table.c.N_serial,
        value_table.c.fields_json,
        efold_table.c.N,
    )
    .select_from(value_table.join(efold_table, value_table.c.N_serial == efold_table.c.serial))
    .filter(value_table.c.instanton_serial == obj.store_id)
    .order_by(efold_table.c.N)
).fetchall()
```

## When the write-out order is ambiguous

If the physical ordering key of a new value table is not obvious from the
`store()` method (i.e. it is not clear whether rows are written in r, N, or
some other ascending order), **STOP and ask the user** before implementing
`_populate()`. Do not guess a sort key or skip the `ORDER BY`.

## Current ordered factories — reference

| Factory | Child table | `ORDER BY` key |
|---|---|---|
| `sqla_InflatonTrajectory_factory` | `InflatonTrajectoryValue` (joined to `efold_value`) | `efold_value.N` |
| `sqla_FullInstantonFactory` | `FullInstantonValue` (joined to `efold_value`) | `efold_value.N` |
| `sqla_SlowRollInstantonFactory` | `SlowRollInstantonValue` (joined to `efold_value`) | `efold_value.N` |
| `sqla_CompactionFunctionFactory` | `CompactionFunctionSamples` | `source`, `r_Mpc` |
| `sqla_GradientCoupledInstantonFactory` | `GradientCoupledInstantonValue` (joined to `efold_value`) | `efold_value.N` |
| `sqla_GradientCoupledInstantonFactory` | `GradientCoupledInstantonProfile` | `node_index` |

When adding a new factory with a child value/sample table, add a row to this
table and implement the `ORDER BY` + monotonicity assertion above.

## What is forbidden

```python
# NEVER — unordered read of a multi-row child table
rows = conn.execute(
    sqla.select(value_table.c.N_serial, value_table.c.fields_json)
    .filter(value_table.c.instanton_serial == obj.store_id)
).fetchall()

# NEVER — N+1 query to fetch the efold N value per row
for r in rows:
    efold_row = conn.execute(
        sqla.select(efold_table.c.serial, efold_table.c.N)
        .filter(efold_table.c.serial == r.N_serial)
    ).one()
```
