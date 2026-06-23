# Prompt 13 — DiffusionModel as a first-class datastore object

## Context and design rationale

This prompt follows the same pattern as `AbstractPotential` / `QuadraticPotential`
/ `QuarticPotential`.  The canonical example to follow is:

- `CosmologyConcepts/Potentials/AbstractPotential.py` — abstract base inheriting
  from both `DatastoreObject` and `ABC`, defining `type_id` as an abstract property
- `InflationConcepts/QuadraticPotential.py` — concrete subclass implementing `type_id`
- `Datastore/SQL/ObjectFactories/QuadraticPotential.py` — factory
- `CosmologyConcepts/Potentials/model_ids.py` — integer type constants
- `CosmologyConcepts/Potentials/registry.py` — `POTENTIAL_REGISTRY` dict mapping
  type_id → factory, used by `read_table()` to reconstruct the right object from
  a stored `potential_type` integer

The diffusion model hierarchy replicates this structure.

### Physical design

`InflatonTrajectory` is the noiseless classical background solution.  The
diffusion model plays no role in computing it.  `FullInstanton` and
`SlowRollInstanton` use the diffusion model as a peer input alongside the
trajectory: it acts as an adapter that supplies D_ij(φ, π) pointwise along
the trajectory during the MSR solve.  The correct ownership is therefore:

```
InflatonTrajectory  ←── trajectory_serial ──┐
                                             ├── FullInstanton
DiffusionModel      ←── diffusion_serial ───┘
```

Both are independent FK inputs to the instanton.  The diffusion model is NOT
inherited from `InflatonTrajectory`; the two are peers.  This means the same
trajectory can be used with different diffusion models to produce distinct
instanton rows, which is a useful comparison (e.g. `MasslessDecoupledDiffusion`
vs a future `FullHankelDiffusion`).

---

## Step 1 — Model IDs

### File: `InflationConcepts/DiffusionModel/model_ids.py`  (new file)

```python
# Integer type identifiers for AbstractDiffusionModel subclasses.
# Each concrete subclass must return one of these from its type_id property.
# Never reuse or renumber an identifier once assigned.
MASSLESS_DECOUPLED_DIFFUSION = 1
# Future: FULL_HANKEL_DIFFUSION = 2
```

---

## Step 2 — Refactor `AbstractDiffusionModel`

### File: `InflationConcepts/DiffusionModel.py`

`AbstractDiffusionModel` currently inherits only from `ABC`.  Change it to
also inherit from `DatastoreObject`, following `AbstractPotential` exactly.

```python
from abc import ABC, abstractmethod
from datetime import datetime
from math import pi as PI
from typing import Any, Optional, Tuple

from Datastore import DatastoreObject


class AbstractDiffusionModel(DatastoreObject, ABC):
    """
    Abstract base class for the MSR stochastic diffusion matrix D_ij.

    Inherits from DatastoreObject so that concrete subclasses can be
    persisted and referenced by (diffusion_serial, diffusion_type) from
    FullInstanton and SlowRollInstanton, following the same pattern as
    AbstractPotential.

    The diffusion model is a peer input to the instanton solve alongside
    InflatonTrajectory.  It is NOT a property of the trajectory: the
    trajectory is the noiseless classical background and does not depend
    on the noise model.
    """

    def __init__(
        self,
        store_id: Optional[int],
        timestamp: Optional[datetime] = None,
    ):
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)

    @property
    @abstractmethod
    def type_id(self) -> int:
        """Integer type identifier, unique per diffusion model class."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name, e.g. 'MasslessDecoupledDiffusion'."""
        raise NotImplementedError

    @abstractmethod
    def D_matrix(
        self,
        phi: float,
        pi: float,
        potential: Any,
    ) -> Tuple[float, float, float]:
        """Return (D11, D12, D22) at field-space position (phi, pi)."""
        raise NotImplementedError
```

Update `MasslessDecoupledDiffusion` to pass `store_id` and `timestamp`
through to the new `__init__`:

```python
class MasslessDecoupledDiffusion(AbstractDiffusionModel):

    def __init__(
        self,
        store_id: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(store_id, timestamp=timestamp)

    @property
    def type_id(self) -> int:
        from InflationConcepts.DiffusionModel.model_ids import MASSLESS_DECOUPLED_DIFFUSION
        return MASSLESS_DECOUPLED_DIFFUSION

    @property
    def name(self) -> str:
        return "MasslessDecoupledDiffusion"

    def D_matrix(self, phi, pi, potential):
        H_sq = potential.H_sq(phi, pi)
        D11  = H_sq / (8.0 * PI * PI)
        return D11, 0.0, 0.0
```

`store_id=None` must remain the default so that existing call sites that
construct `MasslessDecoupledDiffusion()` without arguments continue to work
until they are updated in Steps 6 and 7.

---

## Step 3 — Diffusion model registry

### File: `InflationConcepts/DiffusionModel/registry.py`  (new file)

```python
from dataclasses import dataclass
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase


@dataclass
class DiffusionModelInfo:
    name: str
    factory: "SQLAFactoryBase"


# Populated by each concrete subclass factory module on import.
# Keys are type_id integers; values are DiffusionModelInfo instances.
DIFFUSION_MODEL_REGISTRY: Dict[int, DiffusionModelInfo] = {}
```

---

## Step 4 — Factory for `MasslessDecoupledDiffusion`

### File: `Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py`  (new file)

Follow `Datastore/SQL/ObjectFactories/QuadraticPotential.py` as the template.
The table has no parameter columns; only the framework-supplied `serial` and
`timestamp` columns exist.

```python
import sqlalchemy as sqla
from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from InflationConcepts.DiffusionModel.model_ids import MASSLESS_DECOUPLED_DIFFUSION
from InflationConcepts.DiffusionModel.registry import (
    DIFFUSION_MODEL_REGISTRY,
    DiffusionModelInfo,
)


class sqla_MasslessDecoupledDiffusion_factory(SQLAFactoryBase):

    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [],  # No parameters: only serial and timestamp.
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion

        # MasslessDecoupledDiffusion has no parameters, so there is at most
        # one row in this table.  Look it up; insert if absent.
        row_data = conn.execute(
            sqla.select(table.c.serial, table.c.timestamp)
        ).one_or_none()

        if row_data is None:
            store_id = inserter(conn, {})
            obj = MasslessDecoupledDiffusion(store_id=store_id)
            setattr(obj, "_new_insert", True)
        else:
            obj = MasslessDecoupledDiffusion(
                store_id=row_data.serial,
                timestamp=row_data.timestamp,
            )
            setattr(obj, "_deserialized", True)

        return obj


# Register so that read_table() can reconstruct the model from a stored
# diffusion_type integer without knowing the class name at call time.
DIFFUSION_MODEL_REGISTRY[MASSLESS_DECOUPLED_DIFFUSION] = DiffusionModelInfo(
    name="MasslessDecoupledDiffusion",
    factory=sqla_MasslessDecoupledDiffusion_factory(),
)
```

---

## Step 5 — Register the factory in `Datastore.py` and `config/sharding.py`

### File: `Datastore/SQL/Datastore.py`

**Import:**

```python
from Datastore.SQL.ObjectFactories.MasslessDecoupledDiffusion import (
    sqla_MasslessDecoupledDiffusion_factory,
)
```

**Add to `_factories`** immediately before `InflatonTrajectory`:

```python
"MasslessDecoupledDiffusion": sqla_MasslessDecoupledDiffusion_factory(),
```

### File: `config/sharding.py`

Add to `replicated_tables`:

```python
"MasslessDecoupledDiffusion",
```

The diffusion model is a global configuration object identical across all
shards.  It must be replicated, not sharded.

---

## Step 6 — Remove diffusion model from `InflatonTrajectory`

`InflatonTrajectory` currently accepts and stores a `diffusion_model` argument
(see `sqla_InflatonTrajectory_factory.build()` line 101 and the
`InflatonTrajectory.__init__` signature).  This was added in error: the
trajectory is noiseless and the diffusion model plays no role in computing it.

### File: `ComputeTargets/InflatonTrajectory.py`

- Remove `diffusion_model` parameter from `InflatonTrajectory.__init__`.
- Remove `self._diffusion_model` attribute and any associated property.
- Remove any import of `MasslessDecoupledDiffusion` or `AbstractDiffusionModel`
  that exists solely to support this attribute.

### File: `Datastore/SQL/ObjectFactories/InflatonTrajectory.py`

- Remove `diffusion_model = payload.get("diffusion_model", MasslessDecoupledDiffusion())`
  from `build()`.
- Remove the `from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion`
  import that exists solely to support this default.
- Remove `diffusion_model` from the `InflatonTrajectory(...)` constructor calls
  in `build()` and `read_table()`.

### Call sites in `main.py` and elsewhere

Remove any `diffusion_model=...` keyword argument from `datastore.object_get()`
calls that request an `InflatonTrajectory`.

---

## Step 7 — Add `diffusion_serial` / `diffusion_type` to `FullInstanton`

### File: `Datastore/SQL/ObjectFactories/FullInstanton.py`

**`register()`** — add after the `rtol_serial` column:

```python
# No FK constraint: the target table is determined by diffusion_type,
# following the potential_serial / potential_type pattern.
sqla.Column("diffusion_serial", sqla.Integer, index=True, nullable=False),
sqla.Column("diffusion_type",   sqla.Integer, index=True, nullable=False),
```

**`build()`** — replace the existing
`diffusion_model = payload.get("diffusion_model", MasslessDecoupledDiffusion())`
line with validation that the model is persisted:

```python
diffusion_model = payload.get("diffusion_model")
if diffusion_model is None or diffusion_model.store_id is None:
    raise ValueError(
        "sqla_FullInstantonFactory.build(): 'diffusion_model' must be a "
        "persisted AbstractDiffusionModel with a valid store_id.  "
        "Call datastore.object_get('MasslessDecoupledDiffusion') first."
    )
```

Add to the SELECT filter:

```python
table.c.diffusion_serial == diffusion_model.store_id,
table.c.diffusion_type   == diffusion_model.type_id,
```

**`store()`** — add to the inserter dict for both success and failure paths:

```python
"diffusion_serial": obj._diffusion_model.store_id,
"diffusion_type":   obj._diffusion_model.type_id,
```

**`read_table()`** — reconstruct the diffusion model via the registry:

```python
from InflationConcepts.DiffusionModel.registry import DIFFUSION_MODEL_REGISTRY

dm_info = DIFFUSION_MODEL_REGISTRY.get(row.diffusion_type)
diffusion_model = (
    dm_info.factory.build(
        {}, conn,
        tables[dm_info.name], inserters[dm_info.name],
        tables, inserters,
    )
    if dm_info is not None else None
)
```

Pass the reconstructed `diffusion_model` to the `FullInstanton` constructor.

---

## Step 8 — Add `diffusion_serial` / `diffusion_type` to `SlowRollInstanton`

### File: `Datastore/SQL/ObjectFactories/SlowRollInstanton.py`

Apply the identical changes as Step 7.

---

## Step 9 — Resolve diffusion model before pipeline calls

### File: `main.py`

Before requesting any `FullInstanton` or `SlowRollInstanton`, resolve the
diffusion model to a persisted object:

```python
diffusion_model = datastore.object_get("MasslessDecoupledDiffusion")
```

Pass this resolved object (now carrying a valid `store_id`) wherever
`MasslessDecoupledDiffusion()` is currently constructed inline in the
`FullInstanton` and `SlowRollInstanton` request payloads.

Apply the same change in `ComputeTargets/pipeline.py`: the `diffusion_model`
passed into the pipeline remote function must be a persisted object with a
`store_id`, not a freshly constructed `MasslessDecoupledDiffusion()`.

---

## Migration note for existing databases

Existing databases have no `MasslessDecoupledDiffusion` table and no
`diffusion_serial` / `diffusion_type` columns on `FullInstanton` or
`SlowRollInstanton`.

For development databases: use `--drop full-instanton` and
`--drop slow-roll-instanton` on the next `main.py` invocation and re-run.
The `InflatonTrajectory` table is unaffected (Step 6 only removes in-memory
state, not any database column).

For databases where results must be preserved:

```sql
-- Create the model row first
INSERT INTO MasslessDecoupledDiffusion DEFAULT VALUES;
-- Verify: SELECT serial FROM MasslessDecoupledDiffusion;  (expect 1)

ALTER TABLE FullInstanton ADD COLUMN diffusion_serial INTEGER NOT NULL DEFAULT 1;
ALTER TABLE FullInstanton ADD COLUMN diffusion_type   INTEGER NOT NULL DEFAULT 1;

ALTER TABLE SlowRollInstanton ADD COLUMN diffusion_serial INTEGER NOT NULL DEFAULT 1;
ALTER TABLE SlowRollInstanton ADD COLUMN diffusion_type   INTEGER NOT NULL DEFAULT 1;
```

SQLite does not enforce `NOT NULL` on columns added via `ALTER TABLE` when a
`DEFAULT` is supplied; this is acceptable for migration purposes.

---

## Out of scope

- `FullHankelDiffusion` implementation.  The `model_ids.py` and `registry.py`
  files include comments marking where it should be added.
- Any change to `CompactionFunction` or its factory.
- `generate_lhc_grid.py` or `regression_InstantonOutputs.py`.

---

## Acceptance criteria

1. A fresh `main.py` run creates a `MasslessDecoupledDiffusion` table with
   one row (serial=1, no parameter columns beyond serial and timestamp).
2. Every `FullInstanton` and `SlowRollInstanton` row has `diffusion_serial=1`
   and `diffusion_type=1`.
3. `InflatonTrajectory` has no `diffusion_model` attribute or constructor
   parameter after Step 6.
4. `datastore.object_get("MasslessDecoupledDiffusion")` returns the same
   object on repeated calls (no duplicate rows inserted).
5. A loaded `FullInstanton` has `inst._diffusion_model.store_id == 1` and
   `inst._diffusion_model.type_id == MASSLESS_DECOUPLED_DIFFUSION`.
6. `MasslessDecoupledDiffusion()` with no arguments (store_id=None) does not
   raise, for backward compatibility with call sites not yet updated.
7. `read_table()` on `FullInstanton` and `SlowRollInstanton` correctly
   reconstructs the diffusion model via `DIFFUSION_MODEL_REGISTRY`.
8. The `--drop full-instanton` and `--drop slow-roll-instanton` flags continue
   to work correctly.
9. Two `FullInstanton` rows computed under different diffusion models on the
   same trajectory are stored as distinct rows and retrieved independently.
