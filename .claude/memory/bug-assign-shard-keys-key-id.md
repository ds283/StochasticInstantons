---
name: bug-assign-shard-keys-key-id
description: ShardedPool._assign_shard_keys used wrong column name "key_id" instead of "key_serial"
metadata:
  type: project
---

`ShardedPool._assign_shard_keys` inserted shard key assignments with
`{"key_id": item.store_id, "shard_id": new_shard}` but the actual column in
`shard_keys` is `key_serial`, not `key_id`. SQLAlchemy silently ignored the
unknown `key_id` parameter; SQLite auto-assigned `key_serial` values.

**Why:** By coincidence, auto-assigned key_serials equalled the delta_Nstar
store_ids when items were processed in store_id order — so the bug was latent
and hard to detect. However, it is believed to have contributed to 5,000
FullInstanton records being stored on wrong shards (delta_Nstar serials 31–40
each landed one ring-step early), causing them to be permanently unfindable
by the existence-check query on subsequent runs (the query routes to the
correct shard; the records are on a different shard).

**How to apply:** If shard key persistence ever appears inconsistent between
runs, suspect this class of column-name mismatch in `_assign_shard_keys`.

Fixed 2026-06-20: `Datastore/SQL/ShardedPool.py` line 819, `"key_id"` → `"key_serial"`.
