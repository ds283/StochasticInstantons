---
name: bug-validate-on-startup-cascade
description: validate_on_startup cascade delete bug — orphaned value rows cause UNIQUE constraint on next run
metadata:
  type: project
---

`validate_on_startup` in the three main factories previously deleted unvalidated
parent rows without first deleting child value rows. The value tables have no
`ON DELETE CASCADE` on their foreign keys. SQLite reuses freed serials, so the
next run's INSERT would hit an orphaned child row and raise UNIQUE constraint.

**Why:** Observed as `sqlite3.IntegrityError: UNIQUE constraint failed:
SlowRollInstantonValue.instanton_serial, SlowRollInstantonValue.N_serial` after
a Ctrl-C interrupted Stage 3 (leaving 13 unvalidated SlowRollInstanton rows).

**How to apply:** Every factory with a parent+child table pair must delete child
rows first. See [[validate-on-startup-rule]] and CLAUDE.md rule #5.

Fixed in 2026-06-20:
- `Datastore/SQL/ObjectFactories/FullInstanton.py` — deletes `FullInstantonValue` rows (col `instanton_serial`)
- `Datastore/SQL/ObjectFactories/SlowRollInstanton.py` — deletes `SlowRollInstantonValue` rows (col `instanton_serial`)
- `Datastore/SQL/ObjectFactories/CompactionFunction.py` — deletes `CompactionFunctionSamples` rows (col `parent_serial`)
