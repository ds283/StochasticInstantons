# Imports of the layer: StochasticInstantons (SI) at `7bb3efd`

Written by `docs/extraction/measure_client_imports.py`, reading through `git ls-tree` and `git show` only.

- **Repository:** `/Users/ds283/Documents/Code/StochasticInstantons`
- **Commit:** `7bb3efd0d0a9cc1c367b7848e27fa8b548a76bf7` (given as `7bb3efd`), 2026-10-09 Record the R1 calculation review and open its issues board
- **Layer files** (9): `Datastore/__init__.py`, `Datastore/object.py`, `Datastore/SQL/__init__.py`, `Datastore/SQL/ClientPool.py`, `Datastore/SQL/Datastore.py`, `Datastore/SQL/ProfileAgent.py`, `Datastore/SQL/SerialPoolBroker.py`, `Datastore/SQL/ShardedPool.py`, `Datastore/SQL/ObjectFactories/base.py`
- **Layer files absent at this commit:** none
- **Factory package:** `Datastore/SQL/ObjectFactories/` (its `base.py` is the layer's)
- **Files read:** 186 tracked `.py` files outside the layer; 0 do not parse

## Totals

| What | Count |
|---|---|
| Import statements naming a layer module | **48** in 47 files |
| of which nested (not at module level) | 1 |
| String literals naming a layer module | 0 (0 exactly its name) |
| `import_module` / `__import__` calls naming a layer module | 0 |
| Import statements naming a factory module (not layer imports) | 2 (2 outside `Datastore/SQL/ObjectFactories/`) |

## Layer imports, by group

| Group | Statements | Nested | Files |
|---|---|---|---|
| `(top level)` | 4 | 0 | 3 |
| `ComputeTargets/` | 5 | 0 | 5 |
| `CosmologyConcepts/` | 5 | 0 | 5 |
| `CosmologyModels/` | 1 | 0 | 1 |
| `Datastore/SQL/ObjectFactories/` | 22 | 0 | 22 |
| `InflationConcepts/` | 5 | 1 | 5 |
| `MetadataConcepts/` | 3 | 0 | 3 |
| `Quadrature/` | 1 | 0 | 1 |
| `RayTools/` | 1 | 0 | 1 |
| `tests/` | 1 | 0 | 1 |
| **total** | **48** | **1** | **47** |

## Layer imports, by module

A statement naming two layer modules is counted under each.

| Module | Statements | Names imported by `from` (statements) |
|---|---|---|
| `Datastore` | 12 | `DatastoreObject` 12 |
| `Datastore.SQL.ObjectFactories.base` | 24 | `SQLAFactoryBase` 24 |
| `Datastore.SQL.ProfileAgent` | 1 | `ProfileAgent` 1 |
| `Datastore.SQL.ShardedPool` | 5 | `ShardedPool` 5 |
| `Datastore.object` | 6 | `DatastoreObject` 6 |

## Every layer import

### `(top level)` (4)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `main.py:36` | — | `Datastore.SQL.ProfileAgent` | `ProfileAgent` |
| `main.py:37` | — | `Datastore.SQL.ShardedPool` | `ShardedPool` |
| `plot_GradientCoupledSolutions.py:61` | — | `Datastore.SQL.ShardedPool` | `ShardedPool` |
| `plot_InstantonSolutions.py:42` | — | `Datastore.SQL.ShardedPool` | `ShardedPool` |

### `ComputeTargets/` (5)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `ComputeTargets/CompactionFunction.py:25` | — | `Datastore.object` | `DatastoreObject` |
| `ComputeTargets/FullInstanton.py:23` | — | `Datastore.object` | `DatastoreObject` |
| `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py:75` | — | `Datastore.object` | `DatastoreObject` |
| `ComputeTargets/InflatonTrajectory.py:24` | — | `Datastore.object` | `DatastoreObject` |
| `ComputeTargets/SlowRollInstanton.py:23` | — | `Datastore.object` | `DatastoreObject` |

### `CosmologyConcepts/` (5)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `CosmologyConcepts/DimensionfulQuantity.py:20` | — | `Datastore` | `DatastoreObject` |
| `CosmologyConcepts/DimensionlessQuantity.py:20` | — | `Datastore` | `DatastoreObject` |
| `CosmologyConcepts/Potentials/AbstractPotential.py:6` | — | `Datastore` | `DatastoreObject` |
| `CosmologyConcepts/Potentials/registry.py:5` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `CosmologyConcepts/redshift.py:19` | — | `Datastore` | `DatastoreObject` |

### `CosmologyModels/` (1)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `CosmologyModels/cosmo_params.py:19` | — | `Datastore.object` | `DatastoreObject` |

### `Datastore/SQL/ObjectFactories/` (22)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `Datastore/SQL/ObjectFactories/CompactionFunction.py:21` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/CosmologicalParams.py:18` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/DimensionfulQuantity.py:20` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/DimensionlessQuantity.py:21` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/FullInstanton.py:21` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:20` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/InflatonTrajectory.py:20` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py:3` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/N_final.py:7` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/N_init.py:7` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/QuadraticPotential.py:8` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/QuarticPotential.py:8` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/SlowRollInstanton.py:20` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/alpha_regularization.py:22` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/delta_Nstar.py:7` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/efold.py:7` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/integration_metadata.py:18` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/n_collocation_points.py:21` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/redshift.py:20` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/store_tag.py:18` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/tolerance.py:20` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `Datastore/SQL/ObjectFactories/version.py:18` | — | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |

### `InflationConcepts/` (5)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `InflationConcepts/DiffusionModel/__init__.py:6` | — | `Datastore` | `DatastoreObject` |
| `InflationConcepts/DiffusionModel/registry.py:5` | if TYPE_CHECKING | `Datastore.SQL.ObjectFactories.base` | `SQLAFactoryBase` |
| `InflationConcepts/alpha_regularization.py:20` | — | `Datastore` | `DatastoreObject` |
| `InflationConcepts/efold_value.py:5` | — | `Datastore` | `DatastoreObject` |
| `InflationConcepts/n_collocation_points.py:22` | — | `Datastore` | `DatastoreObject` |

### `MetadataConcepts/` (3)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `MetadataConcepts/store_tag.py:16` | — | `Datastore` | `DatastoreObject` |
| `MetadataConcepts/tolerance.py:20` | — | `Datastore` | `DatastoreObject` |
| `MetadataConcepts/version.py:16` | — | `Datastore` | `DatastoreObject` |

### `Quadrature/` (1)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `Quadrature/integration_metadata.py:18` | — | `Datastore` | `DatastoreObject` |

### `RayTools/` (1)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `RayTools/RayWorkPool.py:23` | — | `Datastore.SQL.ShardedPool` | `ShardedPool` |

### `tests/` (1)

| File:line | Nested | Module | Names |
|---|---|---|---|
| `tests/conftest.py:25` | — | `Datastore.SQL.ShardedPool` | `ShardedPool` |

## String literals naming a layer module

None.

## `import_module` calls naming a layer module

None.

## Imports of factory modules, by group (count only)

| Group | Statements |
|---|---|
| `CosmologyConcepts/` | 2 |
| **total** | **2** |

## Files that do not parse

None.
