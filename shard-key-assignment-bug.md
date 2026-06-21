# ShardedPool: shard key assignment persistence bug

## What this document is for

This document describes a latent but serious bug found in `ShardedPool._assign_shard_keys`
and confirmed in one deployment. It is written so that another Claude Code instance
can locate the same structural fault in a different codebase that shares the same
`ShardedPool` lineage, verify whether the bug is present, and apply the fix.

The bug **cannot be detected by running tests against a single clean run**. It only
manifests when a run is continued in a second invocation (e.g. after a restart or
Ctrl-C), because the fault is a divergence between what is stored on disk and what
is held in memory.

---

## Background: the in-memory / on-disk split in `ShardedPool`

`ShardedPool` partitions objects across multiple SQLite shard files according to a
shard key type (e.g. `delta_Nstar`). The mapping from shard key `store_id` to shard
index is held in:

- **In-memory**: `self._shard_keys: Dict[int, int]` — maps `store_id → shard_id`.
  Populated by `_assign_shard_keys` when new shard key objects are first seen, and
  by `_read_shard_data` on startup when an existing pool is reopened.
- **On-disk**: a `shard_keys` table in the primary SQLite file, typically defined as:
  ```python
  sqla.Table("shard_keys", meta,
      sqla.Column("<pk_column_name>", sqla.Integer, primary_key=True, nullable=False),
      sqla.Column("shard_id",         sqla.Integer, nullable=False),
  )
  ```
  where `<pk_column_name>` is something like `key_serial` or `key_id`.

`_read_shard_data` loads the on-disk table using the pk column name:
```python
self._shard_keys[key.<pk_column_name>] = key.shard_id
```

All routing — lookups, stores, validates — uses `self._shard_keys[item.store_id]`.

**The invariant that must hold**: `key.<pk_column_name>` stored on disk for a given
shard key object must equal `item.store_id` for that object. If they diverge, the
routing loaded on the next startup will differ from the routing used when the records
were originally stored, making those records permanently unfindable.

---

## The bug: `_assign_shard_keys` uses the wrong column name

### Where to look

Find the method `_assign_shard_keys` (the name may be slightly different but the
function is: given a list of shard key objects not yet in `self._shard_keys`,
assign each one to a shard, INSERT into the shard_keys table, and update
`self._shard_keys`).

The loop body will look roughly like:

```python
conn.execute(
    sqla.insert(self._shard_key_table),
    {"<something>": item.store_id, "shard_id": new_shard},
)
self._shard_keys[item.store_id] = new_shard
```

### The fault

**Check whether `"<something>"` exactly matches the primary key column name in the
`shard_keys` table definition.**

If it does not match — for example, the column is `key_serial` but the dict key is
`key_id`, or vice versa — **SQLAlchemy silently discards the unknown key**. The
INSERT proceeds with only `shard_id` bound; SQLite auto-assigns the primary key.

You can verify SQLAlchemy's behaviour with this test snippet:
```python
import sqlalchemy as sqla, tempfile, os
db = tempfile.mktemp(suffix='.sqlite')
engine = sqla.create_engine(f'sqlite:///{db}')
meta = sqla.MetaData()
t = sqla.Table('shard_keys', meta,
    sqla.Column('key_serial', sqla.Integer, primary_key=True, nullable=False),
    sqla.Column('shard_id',   sqla.Integer, nullable=False),
)
t.create(engine)
with engine.begin() as conn:
    result = conn.execute(sqla.insert(t), {'WRONG_NAME': 99, 'shard_id': 7})
    print('auto-assigned pk:', result.inserted_primary_key[0])  # prints 1, not 99
os.unlink(db)
```

### Why the bug is latent

In normal usage, shard key objects are all created in **one vectorized call on a
fresh database**, processed in `store_id` order. The auto-assigned primary keys
(1, 2, 3, …, N) then coincidentally match `store_id` values (1, 2, 3, …, N),
so `_read_shard_data` reconstructs exactly the same mapping on the next startup.
No divergence is observable, and all prior pipelines appear to work correctly.

### When it manifests

The bug causes real data loss when **any shard key object is returned out of order**
within `_assign_shard_keys`. This can happen due to non-determinism inside the
vectorized `object_get` call that creates shard key objects (e.g. shard actor
concurrency, block allocation in the serial broker, or any condition that causes one
object in the batch to be returned after objects with higher store_ids).

Concrete example observed in practice (50 shard key objects, store_id 31 returned
after 32–40):

| INSERT position | store_id in loop | auto-assigned pk | shard |
|---|---|---|---|
| 31st | 32 | 31 | 9 |
| 32nd | 33 | 32 | 0 |
| … | … | … | … |
| 39th | 40 | 39 | 7 |
| 40th | 31 | 40 | 8 |
| 41st | 41 | 41 | 9 ← back in sync |

**In-memory after Run 1**: `self._shard_keys[31]=8`, `self._shard_keys[32]=9`, …
(set by `self._shard_keys[item.store_id] = new_shard` — correct).

**On disk after Run 1** (wrong column name, auto-pk): `pk=31 → shard=9`,
`pk=32 → shard=0`, …, `pk=40 → shard=8`.

**In-memory after restart** (loaded by `_read_shard_data`): `self._shard_keys[31]=9`,
`self._shard_keys[32]=0`, … — **all 10 keys in the displaced window are wrong**.

Result: every record stored in Run 1 under shard key store_ids 31–40 is queried
from the wrong shard on Run 2 → permanently unfindable. In the observed case:
10 displaced keys × 500 records each = **5,000 records silently orphaned**.

The out-of-order window is always bounded: once the late-arriving item is processed,
auto-pk assignment resynchronises with store_id for all subsequent items.

---

## How to confirm the bug is present

1. Find the `shard_keys` table definition. Note the exact name of its primary key
   column.

2. Find the INSERT in `_assign_shard_keys`. Check the dict key that is supposed to
   set the primary key column.

3. If these two names differ → the bug is present.

4. Optionally, add the following instrumentation to `_assign_shard_keys` to capture
   the auto-assigned pk at runtime and flag any mismatch:

```python
result = conn.execute(
    sqla.insert(self._shard_key_table),
    {"<dict_key_name>": item.store_id, "shard_id": new_shard},
)
assigned_pk = result.inserted_primary_key[0]
if assigned_pk != item.store_id:
    print(
        f"!! _assign_shard_keys MISMATCH: "
        f"store_id={item.store_id}, assigned pk={assigned_pk}, shard={new_shard}"
    )
else:
    print(
        f">> _assign_shard_keys: store_id={item.store_id} → pk={assigned_pk} → shard={new_shard}"
    )
```

   Also add after `conn.commit()`:
```python
print(
    f">> _assign_shard_keys: committed {len(missing_keys)} assignment(s). "
    f"Full mapping: { {k: v for k, v in sorted(self._shard_keys.items())} }"
)
```

   Run the pipeline on a fresh database with `--stop-after <first-compute-stage>`.
   Look for `!!` lines. If none appear, the ordering was sequential this time and the
   bug is still latent. Cross-check by querying the `shard_keys` table directly:
   every `pk` value must equal the `store_id` of the corresponding shard key object.

---

## The fix

Change the INSERT dict key from the wrong name to the exact primary key column name
used in the table definition. In one deployment the wrong name was `"key_id"` and
the correct name was `"key_serial"`:

```python
# BEFORE (wrong — SQLAlchemy silently discards the unknown key)
conn.execute(
    sqla.insert(self._shard_key_table),
    {"key_id": item.store_id, "shard_id": new_shard},
)

# AFTER (correct — pk is persisted as item.store_id)
conn.execute(
    sqla.insert(self._shard_key_table),
    {"key_serial": item.store_id, "shard_id": new_shard},
)
```

The exact names will differ between deployments. The principle is always the same:
the dict key must be the literal column name from the `sqla.Column(...)` definition
for the primary key column in `self._shard_key_table`.

---

## After applying the fix

1. Drop and recreate any database that was produced with the buggy code (the on-disk
   `shard_keys` table may contain wrong pk values, and there is no safe way to repair
   the mapping without knowing the original insertion order).

2. Re-run the pipeline from scratch on a fresh database. The instrumentation above
   will confirm that `store_id == assigned_pk` for every assignment.

3. The fix is safe to apply even if the bug has never manifested (it corrects a
   latent fault without changing observable behaviour in the common sequential case).

---

## Related issue: `validate_on_startup` cascade deletes

This is a separate bug in the same codebase family but unrelated to shard key
routing. If a run is interrupted (Ctrl-C) after some objects are partially stored
but not validated, `validate_on_startup` on the next run will delete the unvalidated
parent rows. If the parent factory does not first delete child value rows (and the
value tables have no `ON DELETE CASCADE` on their foreign keys), orphaned child rows
remain. SQLite without `AUTOINCREMENT` reuses freed rowids, so a subsequent INSERT
into the parent table may claim a serial that still has orphaned child rows, causing
a UNIQUE constraint violation.

Pattern to check: in every factory's `validate_on_startup` method, ensure child
value rows are deleted before parent rows:

```python
# Delete child value rows first — there is no ON DELETE CASCADE on the FK.
value_table = tables.get("FooValue")
if value_table is not None:
    conn.execute(
        sqla.delete(value_table).where(value_table.c.parent_fk_col.in_(serials))
    )
conn.execute(sqla.delete(table).where(table.c.serial.in_(serials)))
```

Use `tables.get(...)` rather than `tables[...]` so the method degrades gracefully if
the schema has not yet been migrated to add the value table.
