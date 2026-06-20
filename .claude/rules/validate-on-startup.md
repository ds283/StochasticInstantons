# `validate_on_startup` must cascade to child value rows

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`. It applies to every factory in `Datastore/SQL/ObjectFactories/`
that has `"validate_on_startup": True` and owns a separate value/sample table.

## The problem

SQLite value tables use a composite primary key with a foreign key back to the
parent table, but **no `ON DELETE CASCADE`**:

```python
sqla.Column("instanton_serial", sqla.Integer,
            sqla.ForeignKey("FullInstanton.serial"), primary_key=True),
sqla.Column("N_serial",         sqla.Integer,
            sqla.ForeignKey("efold_value.serial"),  primary_key=True),
```

When `validate_on_startup` deletes unvalidated parent rows, the child rows are
**orphaned** — they remain in the DB with now-dangling `instanton_serial`
references. SQLite without `AUTOINCREMENT` reuses deleted rowids, so the next
INSERT into the parent table may claim a serial that still has orphaned child
rows, causing a UNIQUE constraint violation on the child table's composite PK.

This was observed as:
```
sqlite3.IntegrityError: UNIQUE constraint failed:
    SlowRollInstantonValue.instanton_serial, SlowRollInstantonValue.N_serial
```
on the run after a Ctrl-C interruption, when `validate_on_startup` pruned 13
unvalidated `SlowRollInstanton` rows but left their value rows behind.

## The rule

**Always delete child rows before deleting parent rows in `validate_on_startup`.**

```python
def validate_on_startup(self, conn, table, tables, prune_unvalidated):
    rows = conn.execute(
        sqla.select(table.c.serial).filter(table.c.validated == False)
    ).fetchall()

    if prune_unvalidated and rows:
        serials = [r.serial for r in rows]
        # Delete child rows first — no ON DELETE CASCADE on the FK.
        value_table = tables.get("FooValue")   # replace with actual name
        if value_table is not None:
            conn.execute(
                sqla.delete(value_table).where(
                    value_table.c.parent_serial.in_(serials)  # use actual FK column
                )
            )
        conn.execute(
            sqla.delete(table).where(table.c.serial.in_(serials))
        )
        return [f"Pruned {len(serials)} unvalidated Foo records"]
    if rows:
        return [f"Found {len(rows)} unvalidated Foo records (not pruned)"]
    return []
```

Use `tables.get(...)` (not `tables[...]`) so the method degrades gracefully if
the schema hasn't been migrated yet.

## Current cascade map

| Parent factory              | Parent table         | Value table              | FK column on value table |
|-----------------------------|----------------------|--------------------------|--------------------------|
| `sqla_FullInstantonFactory` | `FullInstanton`      | `FullInstantonValue`     | `instanton_serial`       |
| `sqla_SlowRollInstantonFactory` | `SlowRollInstanton` | `SlowRollInstantonValue` | `instanton_serial`    |
| `sqla_CompactionFunctionFactory` | `CompactionFunction` | `CompactionFunctionSamples` | `parent_serial`     |

When adding a new factory that has both a parent table and a child value/sample
table, add a row to this table and implement the cascade delete pattern above.

## What is forbidden

```python
# NEVER — leaves orphaned value rows behind, causing UNIQUE constraint
# violations on the next run when SQLite reuses the deleted serial
def validate_on_startup(self, conn, table, tables, prune_unvalidated):
    ...
    conn.execute(sqla.delete(table).filter(table.c.serial.in_(serials)))
```
