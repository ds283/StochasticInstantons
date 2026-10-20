# 05 — move SI's data out of the layer

**Subject:** Move SI's factory registry, drop groups and serial batch sizes into `config/datastore.py`; pass the shard key of the 15 vectorized gets as a mapping
**Commit:** `875cf41`, on branch `dk-and-rpk-migration`, on top of `818f8fa`
**Date:** 2026-10-20, by Claude Sonnet 5.5
**Result:** **COMPLETE.** M1–M6 hold. `config/datastore.py` holds `factories` (30), `drop_groups` (5) and
`serial_batch_sizes` (29), `ast`-equal to the definitions removed from the layer; the layer reads them
under its old names; the 15 vectorized gets pass `vectorized_shard_key(key)`; the schema of a store built
at the staged tree agrees with RH0's. The suites give 690 (689 passed, 1 skipped) and 61 (60 passed,
1 skipped): 680 plus the 10 new tests, and 04's 61. No stop condition of the prompt's §4 was met. One
issue is opened, for 09: a fresh `import config.datastore` fails until the layer goes (the orchestrator's
correction 1).

Prompt: [`.prompts/dk-and-rpk-migration/05-move-si-data-out-of-the-layer.md`](../../.prompts/dk-and-rpk-migration/05-move-si-data-out-of-the-layer.md),
corrected by the orchestrator's brief (fifteen corrections). Scratch scripts and outputs were kept
outside the repository, in the session scratchpad; each script that supports a claim is reproduced below.

## What shipped

- **M1.** `config/datastore.py` (new; the Apache header of `config/defaults.py`, a docstring, then the
  moved imports and three dict literals). `factories` is `_factories` from `Datastore/SQL/Datastore.py:96-127`,
  `drop_groups` is `_drop_actions` (`:133-143`), `serial_batch_sizes` is `_default_serial_batch_size`
  (`ClientPool.py:24-54`). The literals are moved byte for byte, renamed only in their binding. The file is
  **not** formatted with `ruff format` (the orchestrator's recommendation, brief 10), so `_drop_actions`' hand
  alignment is kept and `git diff --color-moved` shows the blocks as moved.
- **M2.** `Datastore/SQL/Datastore.py`: the two definitions and 56 import lines (`:28-34`, `:36-66`, `:68-86`)
  are removed, and one line is added after `:27`:
  `from config.datastore import factories as _factories, drop_groups as _drop_actions`. Kept: `ClientPool`
  (`:27`), `CosmologicalParams` (the unused import, brief 7), `SQLAFactoryBase` (used by
  `_FactoryMappingType`), `ProfileAgent`, `utilities`. `_drop_order` stays. `register_factories(_factories)` and the
  method `_drop_actions` are not touched. `Datastore/SQL/ClientPool.py`: the dict is removed and
  `from config.datastore import serial_batch_sizes as _default_serial_batch_size` added after the
  `ProfileAgent` import; `.get(table, 5)` (SI's fallback) is untouched.
- **M3.** `config/sharding.py` gains `vectorized_shard_key(key) -> dict` and nothing else. The 15 calls pass
  `vectorized_shard_key(<key>)`; `main.py` and `plot_InstantonSolutions.py` add `vectorized_shard_key,` to
  their parenthesised `config.sharding` import (last, alphabetical); `plotting/fetch.py` adds
  `from config.sharding import vectorized_shard_key`. In `fetch_over_grid` the bare key remains the key of
  `by_shard` and `refs`.
- **M4.** Five test lines, in the two golden-test files (below).
- **M5.** `tests/test_config_datastore.py` (7 tests) and `tests/test_vectorized_shard_key.py` (3 tests).
- **M6.** `.documents/FILE_MAP.md`: the `Datastore.py` row now says the actor "registers the factories of
  `config/datastore.py`"; a `config/datastore.py` row follows `config/sharding.py`'s, which now names
  `vectorized_shard_key()`.
- The schema snapshot `.documents/dk-and-rpk-migration/out/05-temp-schema.json`.

## Deviations from the prompt

Classified as README §5 rule 2 asks. The brief's fifteen corrections are not repeated; each is applied as it states.

1. **`config.datastore` cannot be imported before the layer** (brief 1). `STRUCTURALLY REQUIRED`: no order of
   the definitions or the imports avoids it, and breaking it means emptying `Datastore/SQL/__init__.py`, which is
   09's (P6). Not a stop. See "The import orders" below. One refinement of the brief: it lists `import Datastore`
   and `plotting.fetch` among the orders that work, and they do, but only on their own; they do **not** load the
   layer (`Datastore/__init__.py` imports only `.object`; `plotting.fetch` imports no `Datastore.SQL`), so
   `config.datastore` imported after them still fails. The docstring of `config/datastore.py` says so. The
   `Datastore.SQL.ShardedPool` import does load the layer.
2. **M4 is five lines, not four stubs** (brief 5). `STRUCTURALLY REQUIRED`: one stub's lookup and four assertions.
   Inside the exception README §5 rule 7 names.
3. **The `main.py` lines** are those of brief 3, not the prompt's (04's deletions). Nothing to change.
4. **Where the two new imports sit** (brief 9). `IMPLEMENTATION CHOICE`: in the import block, after the
   `ClientPool` import in `Datastore.py`, after the `ProfileAgent` import in `ClientPool.py`.
5. **`config/datastore.py` is not formatted** (brief 10). `IMPLEMENTATION CHOICE`. Its docstring and header are new text;
   the dicts and the moved imports are verbatim, in the layer's order (not sorted).
6. **`ray.is_initialized()` is asserted in a subprocess** (brief 11), not "at the end" in-process.
   `IMPLEMENTATION CHOICE`; the subprocess imports the layer by `importlib` and then `config.datastore`, which is the
   import order of brief 1.
7. **The `ast` test walks the filesystem** (brief 12), pruning `tests`, `venv`, `__pycache__`, `site-packages`,
   `node_modules` and every dot-directory. `IMPLEMENTATION CHOICE`: it needs no `git`. It finds 15 calls; the ignored
   `out-*/` scripts are walked and hold none.
8. **Board section 5.17** (brief 13). `STRUCTURALLY REQUIRED`.
9. **Three extra tests** in `test_config_datastore.py`: one per-table batch-size test (so a changed size names its
   table), one asserting the layer's `_drop_order` names exactly the groups, one asserting the layer's three names are
   the module's objects. `IMPLEMENTATION CHOICE`; they test what the prompt describes, no more. The new test files
   were formatted with `ruff format` (README §5 rule 15 allows it).
10. **Long lines.** Three plot-script call arguments and one `fetch.py` argument are now over 88 columns
    (`"SlowRollInstanton", vectorized_shard_key(dns_val), payload_data=payload_data` at 12 spaces is 89; the
    others are longer). `IMPLEMENTATION CHOICE`: the prompt says "nothing else in a call changes" and rule 15 forbids
    reflowing, so the argument is wrapped in place.
11. **The comment in `vectorized_shard_key`** is inside the function body, under the docstring, since the prompt's
    text for the function has a docstring and "a comment saying" what the field name is. `IMPLEMENTATION CHOICE`.
12. **The schema build passes `include_dashboard=False`** to `ray.init(address="local", …)`. `IMPLEMENTATION CHOICE`:
    a private instance needs no dashboard; it changes nothing the check reads.
13. No `UNINTENDED DRIFT` that I know of.

## Verification performed

### Before

- Branch `dk-and-rpk-migration`, `HEAD` `818f8fa`, `git status` clean at the start. Load at the start: 13.06 11.48 11.06
  on 10 CPUs (the first reading); 5.14 / 5.75 (1-minute) at the two suite runs. No Ray process (`pgrep` finds none) and
  `RAY_ADDRESS` unset at the start.

### §2.1.1 — the capture, at the gate's `HEAD`, from the layer

`capture.py` (reads `Datastore.SQL.Datastore` and `Datastore.SQL.ClientPool` by `importlib`, never
`config.datastore`; no Ray started):

```python
"""Capture SI's layer data (registry, drop groups, drop order, batch sizes) as it is at the gate.
Reads the layer, not config.datastore. No Ray is started."""
import importlib, sys, os
sys.path.insert(0, os.getcwd())
L = importlib.import_module("Datastore.SQL.Datastore")
C = importlib.import_module("Datastore.SQL.ClientPool")
import ray

print("REGISTRY", len(L._factories))
for name, f in L._factories.items():
    ot = getattr(f, "ObjectType", None)
    extra = f"  holds={ot.__name__}" if (ot is not None and hasattr(ot, "__name__") and type(f).__name__.startswith("sqla_dim")) else ""
    print(f"  {name!r}: {type(f).__name__}{extra}")
print("DROP_GROUPS", len(L._drop_actions))
for k, v in L._drop_actions.items():
    print(f"  {k!r}: {list(v)!r}")
print("DROP_ORDER", list(L._drop_order))
print("BATCH_SIZES", len(C._default_serial_batch_size))
for k, v in C._default_serial_batch_size.items():
    print(f"  {k!r}: {v!r}")
print("ray.is_initialized():", ray.is_initialized())
reg=set(L._factories); bs=set(C._default_serial_batch_size)
print("registered, no size:", sorted(reg-bs))
print("size, not registered:", sorted(bs-reg))
```

Its output (`capture.out`):

```
REGISTRY 30
  'version': sqla_version_factory
  'store_tag': sqla_store_tag_factory
  'redshift': sqla_redshift_factory
  'tolerance': sqla_tolerance_factory
  'efold_value': sqla_efold_factory
  'delta_Nstar': sqla_delta_Nstar_factory
  'N_init': sqla_N_init_factory
  'N_final': sqla_N_final_factory
  'n_collocation_points': sqla_n_collocation_points_factory
  'alpha_regularization': sqla_alpha_regularization_factory
  'inflaton_mass': sqla_dimensionful_quantity_factory  holds=inflaton_mass
  'quartic_coupling': sqla_dimensionless_quantity_factory  holds=quartic_coupling
  'phi_value': sqla_dimensionful_quantity_factory  holds=phi_value
  'pi_value': sqla_dimensionful_quantity_factory  holds=pi_value
  'QuadraticPotential': sqla_QuadraticPotential_factory
  'QuarticPotential': sqla_QuarticPotential_factory
  'MasslessDecoupledDiffusion': sqla_MasslessDecoupledDiffusion_factory
  'IntegrationSolver': sqla_IntegrationSolver_factory
  'InflatonTrajectory': sqla_InflatonTrajectory_factory
  'InflatonTrajectoryValue': sqla_InflatonTrajectoryValue_factory
  'CosmologicalParams': sqla_cosmological_params_factory
  'FullInstanton': sqla_FullInstantonFactory
  'FullInstantonValue': sqla_FullInstantonValue_factory
  'GradientCoupledInstanton': sqla_GradientCoupledInstantonFactory
  'GradientCoupledInstantonValue': sqla_GradientCoupledInstantonValue_factory
  'GradientCoupledInstantonProfile': sqla_GradientCoupledInstantonProfileFactory
  'SlowRollInstanton': sqla_SlowRollInstantonFactory
  'SlowRollInstantonValue': sqla_SlowRollInstantonValue_factory
  'CompactionFunction': sqla_CompactionFunctionFactory
  'CompactionFunctionSamples': sqla_CompactionFunctionSamplesFactory
DROP_GROUPS 5
  'inflaton-trajectory': ['InflatonTrajectoryValue', 'InflatonTrajectory']
  'full-instanton': ['FullInstantonValue', 'FullInstanton']
  'slow-roll-instanton': ['SlowRollInstantonValue', 'SlowRollInstanton']
  'compaction-function': ['CompactionFunctionSamples', 'CompactionFunction']
  'gradient-coupled-instanton': ['GradientCoupledInstantonValue', 'GradientCoupledInstantonProfile', 'GradientCoupledInstanton']
DROP_ORDER ['compaction-function', 'slow-roll-instanton', 'full-instanton', 'gradient-coupled-instanton', 'inflaton-trajectory']
BATCH_SIZES 29
  'store_tag': 5
  'redshift': 200
  'tolerance': 5
  'temperature': 200
  'phi_value': 200
  'pi_value': 200
  'efold_value': 500
  'delta_Nstar': 10
  'N_init': 10
  'N_final': 10
  'n_collocation_points': 5
  'alpha_regularization': 5
  'inflaton_mass': 10
  'quartic_coupling': 10
  'QuadraticPotential': 10
  'QuarticPotential': 10
  'InflatonTrajectory': 20
  'MasslessDecoupledDiffusion': 5
  'FullInstanton': 20
  'FullInstantonValue': 500
  'GradientCoupledInstanton': 20
  'GradientCoupledInstantonValue': 500
  'GradientCoupledInstantonProfile': 500
  'SlowRollInstanton': 20
  'SlowRollInstantonValue': 500
  'CosmologicalParams': 5
  'CompactionFunction': 20
  'CompactionFunctionSamples': 500
  'IntegrationSolver': 6
ray.is_initialized(): False
registered, no size: ['InflatonTrajectoryValue', 'version']
size, not registered: ['temperature']
```

`tests/test_config_datastore.py` was written from this output: `_REGISTRY` is the 30 lines under `REGISTRY`
(name, factory class, and for the four quantity entries the held class, `inflaton_mass`, `quartic_coupling`,
`phi_value`, `pi_value`: two classes of factory, four entries), `_DROP_GROUPS` the five lines under `DROP_GROUPS`,
`_BATCH_SIZES` the 29 lines under `BATCH_SIZES`. The `_REGISTRY` and `_BATCH_SIZES` lists were generated from this
output by a throwaway text transform (not from the module under test), then pasted into the file and formatted; the
`_DROP_GROUPS` literal was typed from the output. It is not computed from `config.datastore` anywhere.

### §2.1.2 — `git grep -n object_get_vectorized -- '*.py'`, at the gate

```
Datastore/SQL/ShardedPool.py:584:    def object_get_vectorized(self, ObjectClass, shard_key, payload_data):
main.py:226:        task_builder=lambda key: pool.object_get_vectorized(
main.py:254:        task_builder=lambda key: pool.object_get_vectorized(
main.py:321:        task_builder=lambda key: pool.object_get_vectorized(
main.py:420:    `object_get_vectorized()` call per distinct shard key, so the number of
main.py:449:        task_builder=lambda key: pool.object_get_vectorized(
main.py:592:        task_builder=lambda key: pool.object_get_vectorized(
main.py:871:            task_builder=lambda key: pool.object_get_vectorized(
main.py:900:            task_builder=lambda key: pool.object_get_vectorized(
main.py:964:            task_builder=lambda key: pool.object_get_vectorized(
main.py:1015:                task_builder=lambda key: pool.object_get_vectorized(
main.py:1041:                task_builder=lambda key: pool.object_get_vectorized(
plot_InstantonSolutions.py:698:        fi_refs[dns_val] = pool.object_get_vectorized(
plot_InstantonSolutions.py:701:        sri_refs[dns_val] = pool.object_get_vectorized(
plot_InstantonSolutions.py:734:            cf_refs[dns_val] = pool.object_get_vectorized(
plotting/fetch.py:127:            pool.object_get_vectorized(
plotting/fetch.py:143:    `pool.object_get_vectorized()` call per distinct shard key, then
plotting/fetch.py:166:        refs[shard_key] = pool.object_get_vectorized(
tests/test_plot_adapters_golden.py:1010:    def object_get_vectorized(self, class_name, shard_key, payload_data):
tests/test_plot_extraction_golden.py:381:    def object_get_vectorized(self, class_name, shard_key, payload_data):
tests/test_plot_extraction_golden.py:450:            def object_get_vectorized(self, class_name, shard_key, payload_data):
tests/test_plot_extraction_golden.py:477:            def object_get_vectorized(self, class_name, shard_key, payload_data):
```

The definition (`ShardedPool.py:584`), 15 calls (`main.py` 10, `plot_InstantonSolutions.py` 3, `plotting/fetch.py` 2),
the two docstrings (`main.py:420`, `plotting/fetch.py:143`) and the four stubs; nothing else. No stop.

### M3 — the 15 calls, at the gate and after

| # | File | Gate | After | Key passed |
|---|---|---|---|---|
| 1 | `main.py` | 226 | 227 | `key` |
| 2 | `main.py` | 254 | 255 | `key` |
| 3 | `main.py` | 321 | 322 | `key` |
| 4 | `main.py` | 449 | 450 | `key` |
| 5 | `main.py` | 592 | 593 | `key` |
| 6 | `main.py` | 871 | 872 | `key` |
| 7 | `main.py` | 900 | 901 | `key` |
| 8 | `main.py` | 964 | 965 | `key` |
| 9 | `main.py` | 1015 | 1016 | `key` |
| 10 | `main.py` | 1041 | 1042 | `key` |
| 11 | `plot_InstantonSolutions.py` | 698 | 699 | `dns_val` |
| 12 | `plot_InstantonSolutions.py` | 701 | 702 | `dns_val` |
| 13 | `plot_InstantonSolutions.py` | 734 | 735 | `dns_val` |
| 14 | `plotting/fetch.py` | 127 | 128 | `dns_val` |
| 15 | `plotting/fetch.py` | 166 | 167 | `shard_key` |

Every call is one line shifted by the one import line each file gained at its top. The diff of each call is the
wrapped argument and nothing else (`git diff main.py plot_InstantonSolutions.py plotting/fetch.py`, the `+`/`-` lines):
10 × `key,` → `vectorized_shard_key(key),` (indentation kept), and the five inline arguments, plus one import line per file.

### M4 — the five test lines

| File | Line | Was | Now |
|---|---|---|---|
| `tests/test_plot_adapters_golden.py` | 1012 (`_MultiClassStubPool.object_get_vectorized`) | `self._responses.get((class_name, shard_key))` | `self._responses.get((class_name, shard_key["delta_Nstar"]))` |
| `tests/test_plot_adapters_golden.py` | 1047 | `called_pairs = {(c, s) for c, s, _ in pool.calls}` | `called_pairs = {(c, s["delta_Nstar"]) for c, s, _ in pool.calls}` |
| `tests/test_plot_adapters_golden.py` | 1103 | `assert cf_calls[0][1] == 5.0  # …` | `assert cf_calls[0][1]["delta_Nstar"] == 5.0  # …` |
| `tests/test_plot_extraction_golden.py` | 414 (the `_StubPool` test) | `assert shard_key == 5.0` | `assert shard_key["delta_Nstar"] == 5.0` |
| `tests/test_plot_extraction_golden.py` | 467 (the `_ShardedStubPool` test) | `shard_keys_called = {call[1] for call in pool.calls}` | `shard_keys_called = {call[1]["delta_Nstar"] for call in pool.calls}` |

The stubs at `test_plot_extraction_golden.py:381` (`_StubPool`), `:450` (`_ShardedStubPool`) and `:477`
(`_RecordingStubPool`) are **unchanged**: they record what they are given, and `_RecordingStubPool`'s test records only
payloads. With M3 applied and these five lines, the two files give 74 passed. Each line changes only where it
reads the key. Nothing else under `tests/` changed but the two new files.

### §2.1.3 — the registered tables and the batch sizes, for 09

From the capture (`registered, no size` / `size, not registered`): **`InflatonTrajectoryValue` and `version`** are
registered with no size; **`temperature`** has a size and no table. For each:

- `InflatonTrajectoryValue` registers `"serial": False` (`Datastore/SQL/ObjectFactories/InflatonTrajectory.py:390`):
  it leases none.
- `version` has a `serial` column, but the actor never leases one for it: `Datastore/SQL/Datastore.py` guards the
  lease with `… and (cls_name != "version")` (`:642` at the gate). **So no table leases under SI's fallback of 5**,
  not even `version`; the README expected `version` to.
- `temperature` is a ChamPBH leftover and moves verbatim (P12).

One more fact, for 09: three tables carry a size of 500 but register `"serial": False`, so their sizes are never read:
`FullInstantonValue` (`FullInstanton.py:548`), `SlowRollInstantonValue` (`SlowRollInstanton.py:543`) and
`GradientCoupledInstantonValue` (`GradientCoupledInstanton.py:703`). Verified by reading those lines; they move verbatim and
nothing is added.

### §2.1.4 — the names in current documents

`git grep -n -e "_factories" -e "_drop_actions" -e "_default_serial_batch_size" -- ':!.prompts'` lists only the two layer
files and `tests/test_compare_stores.py:944` (`_registry()`'s fallback import). `CLAUDE.md` and `.claude/` name none of
them. No document is added to M6. Prose that 05 leaves true and 09/12 must revisit is under "State handed".

### §2.1.5 and §2.3.2 — the lint, before and after

`./venv/bin/ruff check --select F401,F811,F821` (ruff 0.15.17, from the venv), on the two layer files, at the gate:

```
F401 [*] `CosmologyModels.cosmo_params.CosmologicalParams` imported but unused
  --> Datastore/SQL/Datastore.py:35:42
   |
33 |     sqla_dimensionless_quantity_factory,
34 | )
35 | from CosmologyModels.cosmo_params import CosmologicalParams
   |                                          ^^^^^^^^^^^^^^^^^^
36 | from Datastore.SQL.ObjectFactories.CosmologicalParams import sqla_cosmological_params_factory
37 | from Datastore.SQL.ObjectFactories.CompactionFunction import (
   |
help: Remove unused import: `CosmologyModels.cosmo_params.CosmologicalParams`

Found 1 error.
[*] 1 fixable with the `--fix` option.
```

After the move, on the two layer files and `config/datastore.py`:

```
F401 [*] `CosmologyModels.cosmo_params.CosmologicalParams` imported but unused
  --> Datastore/SQL/Datastore.py:29:42
   |
27 | from Datastore.SQL.ClientPool import SerialPoolManager, SerialLeaseManager
28 | from config.datastore import factories as _factories, drop_groups as _drop_actions
29 | from CosmologyModels.cosmo_params import CosmologicalParams
   |                                          ^^^^^^^^^^^^^^^^^^
30 | from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
31 | from Datastore.SQL.ProfileAgent import ProfileBatcher, ProfileBatchManager
   |
help: Remove unused import: `CosmologyModels.cosmo_params.CosmologicalParams`

Found 1 error.
[*] 1 fixable with the `--fix` option.
```

The one finding is the same, now at `Datastore.py:29`: `CosmologicalParams` is not a factory import and no registry
entry uses it; deleting it is a change §1 does not name, so it stays (an observation, below). `config/datastore.py`
adds none, and there is no `F821`.

### §2.3.2 — the layer is unchanged but for its imports

`git diff -U0 Datastore/SQL/Datastore.py Datastore/SQL/ClientPool.py`, hunks and added lines (the removals are the
moved definitions and imports):

```
diff --git a/Datastore/SQL/ClientPool.py b/Datastore/SQL/ClientPool.py
@@ -23,32 +23 @@ from Datastore.SQL.ProfileAgent import ProfileBatcher, ProfileBatchManager
diff --git a/Datastore/SQL/Datastore.py b/Datastore/SQL/Datastore.py
@@ -28,7 +28 @@ from Datastore.SQL.ClientPool import SerialPoolManager, SerialLeaseManager
@@ -36,31 +29,0 @@ from CosmologyModels.cosmo_params import CosmologicalParams
@@ -68,19 +30,0 @@ from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
@@ -96,33 +39,0 @@ PathType = Union[str, PathLike]
@@ -133,11 +43,0 @@ _InserterMappingType = Mapping[str, Callable]
```

`Datastore.py` loses 101 lines and gains 1; `ClientPool.py` loses 32 and gains 1. Two checks, by script
(`ast_check.py`, `moved_check.py`):

```python
import ast, subprocess
def tree(src): return ast.parse(src)
def old(p): return subprocess.check_output(["git","show","HEAD:"+p]).decode()
o = tree(old("Datastore/SQL/Datastore.py")); n = tree(open("Datastore/SQL/Datastore.py").read())
c = tree(open("config/datastore.py").read())
def assign(t, name):
    for s in t.body:
        if isinstance(s, ast.Assign) and s.targets[0].id==name: return ast.dump(s.value)
for old_n,new_n in (("_factories","factories"),("_drop_actions","drop_groups")):
    print(old_n, assign(o,old_n)==assign(c,new_n))
oc = tree(old("Datastore/SQL/ClientPool.py"))
print("_default_serial_batch_size", assign(oc,"_default_serial_batch_size")==assign(c,"serial_batch_sizes"))
# other statements equal
def rest(t, drop):
    return [ast.dump(s) for s in t.body if not (isinstance(s,(ast.Import,ast.ImportFrom)) ) and not (isinstance(s,ast.Assign) and s.targets[0].id in drop)]
print("layer non-import statements equal:", rest(o,{"_factories","_drop_actions"})==rest(n,set()))
nc = tree(open("Datastore/SQL/ClientPool.py").read())
print("clientpool non-import equal:", rest(oc,{"_default_serial_batch_size"})==rest(nc,set()))
# imports in config are all used
names = {a.asname or a.name for s in c.body if isinstance(s,(ast.Import,ast.ImportFrom)) for a in s.names}
used = {x.id for x in ast.walk(c) if isinstance(x,ast.Name)}
print("unused in config:", names-used)
```

```
_factories True
_drop_actions True
_default_serial_batch_size True
layer non-import statements equal: True
clientpool non-import equal: True
unused in config: set()
```

and every removed line, but the three binding lines (`_factories = {`, `_drop_actions = {`, `_default_serial_batch_size = {`), appears
verbatim in `config/datastore.py` (`moved_check.py`):

```python
import subprocess
cfg = open("config/datastore.py").read().split("\n")
for f in ("Datastore/SQL/Datastore.py", "Datastore/SQL/ClientPool.py"):
    d = subprocess.check_output(["git","diff","-U0",f]).decode().split("\n")
    removed = [l[1:] for l in d if l.startswith("-") and not l.startswith("---")]
    added = [l[1:] for l in d if l.startswith("+") and not l.startswith("+++")]
    missing = [l for l in removed if l.strip() and l not in cfg]
    print(f, "removed", len(removed), "added", added, "removed lines not in config/datastore.py:", missing)
```

```
Datastore/SQL/Datastore.py removed 101 added ['from config.datastore import factories as _factories, drop_groups as _drop_actions'] removed lines not in config/datastore.py: ['_factories = {', '_drop_actions = {']
Datastore/SQL/ClientPool.py removed 32 added ['from config.datastore import serial_batch_sizes as _default_serial_batch_size'] removed lines not in config/datastore.py: ['_default_serial_batch_size = {']
```

### The import orders (brief 1)

Each in a fresh process, `./venv/bin/python -I -c …` from the repository root with `sys.path[0]` the root
(`import_orders.sh`, below), at the staged tree:

```bash
#!/bin/bash
# each import order in a fresh isolated process, from the repository root
cd /Users/ds283/Documents/Code/StochasticInstantons
run() { echo "--- $1"; ./venv/bin/python -I -c "import sys; sys.path.insert(0, '.'); $1; import ray; print('OK; ray.is_initialized() =', ray.is_initialized())" 2>&1 | tail -2; }
run "import config.datastore"
run "import Datastore.SQL.ClientPool, config.datastore"
run "import Datastore.SQL.Datastore, config.datastore"
run "import Datastore; import config.datastore"
run "import Datastore"
run "import plotting.fetch"
run "import Datastore.SQL.ShardedPool, config.datastore"
run "import plotting.fetch, config.datastore"
run "import Datastore.SQL.ObjectFactories.version, config.datastore"
run "import config.sharding"
echo "--- _registry() logic of tests/test_compare_stores.py:938-945, run first"
./venv/bin/python -I -c "
import sys, importlib; sys.path.insert(0, '.')
try:
    from config.datastore import factories
    print('first attempt succeeded')
except ImportError as e:
    print('first attempt ImportError:', str(e)[:90])
    from Datastore.SQL.Datastore import _factories as factories
import config.datastore as cd
L = importlib.import_module('Datastore.SQL.Datastore')
print(len(factories), 'entries; is config.datastore.factories:', factories is cd.factories, '; layer _factories is it:', L._factories is cd.factories)
"
```

```
--- import config.datastore
    from config.datastore import serial_batch_sizes as _default_serial_batch_size
ImportError: cannot import name 'serial_batch_sizes' from partially initialized module 'config.datastore' (most likely due to a circular import) (/Users/ds283/Documents/Code/StochasticInstantons/config/datastore.py)
--- import Datastore.SQL.ClientPool, config.datastore
OK; ray.is_initialized() = False
--- import Datastore.SQL.Datastore, config.datastore
OK; ray.is_initialized() = False
--- import Datastore; import config.datastore
    from config.datastore import serial_batch_sizes as _default_serial_batch_size
ImportError: cannot import name 'serial_batch_sizes' from partially initialized module 'config.datastore' (most likely due to a circular import) (/Users/ds283/Documents/Code/StochasticInstantons/config/datastore.py)
--- import Datastore
OK; ray.is_initialized() = False
--- import plotting.fetch
OK; ray.is_initialized() = False
--- import Datastore.SQL.ShardedPool, config.datastore
OK; ray.is_initialized() = False
--- import plotting.fetch, config.datastore
    from config.datastore import serial_batch_sizes as _default_serial_batch_size
ImportError: cannot import name 'serial_batch_sizes' from partially initialized module 'config.datastore' (most likely due to a circular import) (/Users/ds283/Documents/Code/StochasticInstantons/config/datastore.py)
--- import Datastore.SQL.ObjectFactories.version, config.datastore
OK; ray.is_initialized() = False
--- import config.sharding
OK; ray.is_initialized() = False
--- _registry() logic of tests/test_compare_stores.py:938-945, run first
first attempt ImportError: cannot import name 'serial_batch_sizes' from partially initialized module 'config.datastor
30 entries; is config.datastore.factories: True ; layer _factories is it: True
```

Reading it:

- **Fails:** `import config.datastore` first; `import Datastore; import config.datastore`; `import plotting.fetch, config.datastore`
  (the last two because neither loads the layer).
- **Works:** `import Datastore.SQL.ClientPool, config.datastore`; `import Datastore.SQL.Datastore, config.datastore`;
  `import Datastore.SQL.ShardedPool, config.datastore`; `import Datastore.SQL.ObjectFactories.version, config.datastore`;
  `import Datastore` alone; `import plotting.fetch` alone; `import config.sharding`. `ray.is_initialized()` is `False`
  after each.
- **The cycle:** `Datastore/SQL/__init__.py` is `from .Datastore import Datastore`, so importing any `Datastore.SQL.*`
  module runs the layer, which imports `ClientPool.py`, which imports `config.datastore`, which imports the factories
  inside that package.
- **`_registry()`** (`tests/test_compare_stores.py:938-945`), run first in a fresh process: its first attempt
  (`from config.datastore import factories`) raises `ImportError`, the fallback loads the layer, and what it returns is
  `config.datastore.factories` (identity `True`; the layer's `_factories`, found by `importlib`, is the same object). It
  works today, and its fallback would also hide a genuine `ImportError` in `config.datastore`. The test is not edited
  (README §5 rule 7). Opened: `[config-datastore-cannot-be-imported-before-the-layer]`, owner 09.
- Today no entry point meets it: `tests/test_config_datastore.py` imports the layer first with a comment saying why,
  and `config/datastore.py`'s docstring states the rule.

### §2.3.1 — the schema does not change

Built with SI's own `ShardedPool`, at the staged tree (the uncommitted tree that became `875cf41`), under a private
Ray, in a temporary directory under the scratch directory (outside the repository), then closed; nothing stored.
`schema_build.py`:

```python
"""Build a temporary store with SI's own ShardedPool (two shards, nothing stored), then close it."""
import sys, os, tempfile, shutil
sys.path.insert(0, os.getcwd())
import ray
from Datastore.SQL.ShardedPool import ShardedPool
from config.sharding import (ShardKeyType, get_shard_key_store_id, inventory_config,
                             read_table_config, replicated_tables, sharded_tables)

tmpdir = tempfile.mkdtemp(prefix="si05-schema-", dir=sys.argv[1])
db = os.path.join(tmpdir, "temp.sqlite")
print("TMP", db)
ray.init(address="local", include_dashboard=False)
try:
    with ShardedPool(
        version_label="05-schema-check",
        db_name=db,
        ShardKeyType=ShardKeyType,
        ShardKeyStoreIdGetter=get_shard_key_store_id,
        replicated_tables=replicated_tables,
        sharded_tables=sharded_tables,
        timeout=None,
        shards=2,
        profile_agent=None,
        job_name=None,
        prune_unvalidated=False,
        drop_actions=[],
        read_table_config=read_table_config,
        inventory_config=inventory_config,
    ) as pool:
        pass
finally:
    ray.shutdown()
print("FILES", sorted(os.listdir(tmpdir)))
```

Run as `./venv/bin/python schema_build.py <scratch>/tmp-store` (output `schema_build.out`: "Created sharded datastore … with 2
shards", files `temp-shard0000.sqlite`, `temp-shard0001.sqlite`, `temp.sqlite`). Then:

```
./venv/bin/python tools/compare_stores.py --snapshot <tmp>/temp.sqlite --out .documents/dk-and-rpk-migration/out/05-temp-schema.json
./venv/bin/python tools/compare_stores.py --schema <tmp>/temp.sqlite --against .documents/dk-and-rpk-migration/out/02-reference-schema.json
```

```
compare_stores: schema of /private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/9bd97a40-1011-4f89-a2f9-f28a6c5578d2/scratchpad/agent05/tmp-store/si05-schema-0_qlf7wk/temp.sqlite against .documents/dk-and-rpk-migration/out/02-reference-schema.json
RESULT: the schemas agree
exit 0
```

(The store was built twice: the second time to take the comparison's exit status without a pipe; a re-taken snapshot
differs from the saved one only in its `source` path.) The saved snapshot's `tables` equal the reference's (30 tables);
the only key that differs between the two files is `source`, the path of the store. The temporary store was deleted; it
is the only store this prompt opened. No Ray process was left (`ray.shutdown()` in a `finally`).

### §2.3.3 — the new tests

`tests/test_config_datastore.py` (7 tests): the registry as captured (30 entries, names, order, factory classes, held
quantity classes), the drop groups (5), the batch sizes (29, in order) and per table (so a failure names the table), the
layer's three names `is` the module's three objects, `_drop_order` names exactly the groups, and a subprocess asserts
`ray.is_initialized()` is `False` after importing the layer and then `config.datastore`.
`tests/test_vectorized_shard_key.py` (3 tests): `vectorized_shard_key(k) == {"delta_Nstar": k}`; its key is every value of
`sharded_tables`; the `ast` test (15 calls, each passing a call of `vectorized_shard_key` as the second positional
argument or `shard_key=`; a failure names `file:line`). No Ray is started by either file.

### §2.3.5 — `py_compile`

`./venv/bin/python -m py_compile main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py plotting/fetch.py`: succeeds.

### §2.3.4 — the suites

| Suite | Command | 04 | Now |
|---|---|---|---|
| default | `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | 680 (679 passed, 1 skipped) | **690 (689 passed, 1 skipped)**, 130 deselected, 29.9 s; load 5.14 |
| integration | `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | 61 (60 passed, 1 skipped) | **61 (60 passed, 1 skipped)**, 759 deselected, 12.8 s; load 5.75 |

The difference in the default run is the 10 new tests: `test_config_datastore.py` 7, `test_vectorized_shard_key.py` 3. The
`slow` block is not run: the diff touches none of `.claude/rules/test-selection.md`'s paths. The integration run builds
`live_pool` through the moved registry, so it is also the check that the layer finds its data. The four changed
stubs' two files give 74 passed (before the full run). Verdicts were grepped from files in the scratch directory.

## The deliberate-breakage record

Each was applied to the working tree, run, reverted, and recorded as `diff -u` of the file before and after, labelled
`a/` and `b/` so that `git apply` replays it from a clean tree at `875cf41`. (The agent's `git apply --check` and `-R --check` of
each, in `bash`, ran after the commit and are reported in the hand-off, since a commit cannot record its own check.)

### Breakage 1 — one vectorized get reverted to the bare key (`plotting/fetch.py:167`)

```diff
--- a/plotting/fetch.py
+++ b/plotting/fetch.py
@@ -165,7 +165,7 @@
             for i in indices
         ]
         refs[shard_key] = pool.object_get_vectorized(
-            class_name, vectorized_shard_key(shard_key), payload_data=payload_data
+            class_name, shard_key, payload_data=payload_data
         )
 
     shard_keys = list(refs.keys())
```

Caught by `tests/test_vectorized_shard_key.py`:

```
E       AssertionError: vectorized gets with a bare shard key: plotting/fetch.py:167
E       assert not ['plotting/fetch.py:167']
FAILED tests/test_vectorized_shard_key.py::test_every_vectorized_get_passes_the_mapping
1 failed, 2 passed in 0.33s
```

### Breakage 2 — a batch size changed (`"FullInstantonValue": 500` → `400`)

```diff
--- a/config/datastore.py
+++ b/config/datastore.py
@@ -167,7 +167,7 @@
     "InflatonTrajectory": 20,
     "MasslessDecoupledDiffusion": 5,
     "FullInstanton": 20,
-    "FullInstantonValue": 500,
+    "FullInstantonValue": 400,
     "GradientCoupledInstanton": 20,
     "GradientCoupledInstantonValue": 500,
     "GradientCoupledInstantonProfile": 500,
```

Caught by `tests/test_config_datastore.py`:

```
E       AssertionError: assert [('store_tag'...e', 200), ...] == [('store_tag'...e', 200), ...]
E         
E         At index 19 diff: ('FullInstantonValue', 400) != ('FullInstantonValue', 500)
E         Use -v to get more diff
E           AssertionError: FullInstantonValue: 400 (captured 500)
E           assert 500 == 400
E            +  where 500 = <built-in method get of dict object at 0x10fb5aa00>('FullInstantonValue')
E            +    where <built-in method get of dict object at 0x10fb5aa00> = {'store_tag': 5, 'redshift': 200, 'tolerance': 5, 'temperature': 200, ...}.get
FAILED tests/test_config_datastore.py::test_serial_batch_sizes_as_captured - ...
FAILED tests/test_config_datastore.py::test_batch_sizes_per_table - Assertion...
2 failed, 5 passed in 0.65s
```

### Breakage 3 — a registry entry given another quantity type

```diff
--- a/config/datastore.py
+++ b/config/datastore.py
@@ -111,7 +111,7 @@
     "N_final": sqla_N_final_factory(),
     "n_collocation_points": sqla_n_collocation_points_factory(),
     "alpha_regularization": sqla_alpha_regularization_factory(),
-    "inflaton_mass": sqla_dimensionful_quantity_factory(inflaton_mass),
+    "inflaton_mass": sqla_dimensionful_quantity_factory(phi_value),
     "quartic_coupling": sqla_dimensionless_quantity_factory(quartic_coupling),
     "phi_value": sqla_dimensionful_quantity_factory(phi_value),
     "pi_value": sqla_dimensionful_quantity_factory(pi_value),
```

Caught by `tests/test_config_datastore.py`:

```
E       AssertionError: assert [('version', ...', None), ...] == [('version', ...', None), ...]
E         
E         At index 10 diff: ('inflaton_mass', 'sqla_dimensionful_quantity_factory', 'phi_value') != ('inflaton_mass', 'sqla_dimensionful_quantity_factory', 'inflaton_mass')
E         Use -v to get more diff
FAILED tests/test_config_datastore.py::test_factories_registry_as_captured - ...
1 failed, 6 passed in 0.61s
```

### Breakage 4 — the layer given a registry of its own again (a copy)

```diff
--- a/Datastore/SQL/Datastore.py
+++ b/Datastore/SQL/Datastore.py
@@ -26,6 +26,7 @@
 
 from Datastore.SQL.ClientPool import SerialPoolManager, SerialLeaseManager
 from config.datastore import factories as _factories, drop_groups as _drop_actions
+_factories = dict(_factories)
 from CosmologyModels.cosmo_params import CosmologicalParams
 from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
 from Datastore.SQL.ProfileAgent import ProfileBatcher, ProfileBatchManager
```

Caught by `tests/test_config_datastore.py (identity only; the data tests pass: 6 passed)`:

```
FAILED tests/test_config_datastore.py::test_layer_reads_the_data_from_config_datastore
1 failed, 6 passed
```

### Breakage 5 — one stub's lookup left on the bare key

```diff
--- a/tests/test_plot_adapters_golden.py
+++ b/tests/test_plot_adapters_golden.py
@@ -1009,7 +1009,7 @@
 
     def object_get_vectorized(self, class_name, shard_key, payload_data):
         self.calls.append((class_name, shard_key, payload_data))
-        response = self._responses.get((class_name, shard_key["delta_Nstar"]))
+        response = self._responses.get((class_name, shard_key))
         if response is None:
             response = [None] * len(payload_data)
         return ray.put(response)
```

Caught by `tests/test_plot_adapters_golden.py`:

```
E       TypeError: unhashable type: 'dict'
tests/test_plot_adapters_golden.py:1012: TypeError
FAILED tests/test_plot_adapters_golden.py::TestFetchAdaptersOverGrid::test_one_call_per_class_and_shard_with_correct_reassembly
FAILED tests/test_plot_adapters_golden.py::TestFetchAdaptersOverGrid::test_cf_spec_skips_shard_with_no_available_instanton
FAILED tests/test_plot_adapters_golden.py::TestCollectDoeScalarPoints::test_returns_new_shape_and_omits_unavailable_points
3 failed, 40 passed, 1 warning in 11.74s
```

Mutations were never staged or committed; each file was restored from the copy saved before it was mutated, and `cmp` of
each restored file against its saved copy reports them identical.

## Observations not acted on

- **`CosmologicalParams`** (`Datastore/SQL/Datastore.py:29`) is imported and unused, and was at the gate (`:35`). It is
  the one lint finding before and after. Not a factory import; deleting it is a change §1 does not name.
- **The alignment of `drop_groups`** (hand-aligned `"inflaton-trajectory":   [`) is kept because the file is not formatted.
  09 or 12 may run `ruff format` over it.
- **`fetch.py` and the plot script's long lines** (deviation 10).
- **`INFRASTRUCTURE.md:467`, `architecture-summary.md:461` and `:537`** are sketches that pass a bare `delta_Nstar_obj` to
  `object_get_vectorized`. SI's layer still accepts it; the package will not, so they become false at 09. `INFRASTRUCTURE.md:181`
  and `architecture-summary.md:193` ("owns a registry of all factories") stay true: the actor still owns one, filled from the module.
  `FILE_MAP.md:272` (`ClientPool.py`, protected, internal to `ShardedPool`) stays true. Recorded for 09/12; nothing opened.
- **`tests/test_compare_stores.py:938-945`**'s `_registry()` is unedited (brief 1).
- **`Datastore.SQL.Datastore` as an attribute is the actor**, not the module (brief 2); the new tests and the capture script
  use `importlib.import_module`.

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, `875cf41` on `818f8fa`. New: `config/datastore.py`, `tests/test_config_datastore.py`,
  `tests/test_vectorized_shard_key.py`, `.documents/dk-and-rpk-migration/out/05-temp-schema.json`, this note. Changed:
  `Datastore/SQL/Datastore.py`, `Datastore/SQL/ClientPool.py` (imports only), `config/sharding.py` (one function), `main.py`,
  `plot_InstantonSolutions.py`, `plotting/fetch.py` (15 arguments, one import each), the two golden-test files (five lines),
  `.documents/FILE_MAP.md`, `.documents/OPEN-ISSUES.md`, the board.
- **For 09, the data is a module.** `config.datastore.factories`, `.drop_groups` and `.serial_batch_sizes` are what
  DatastoreKit's `ShardedPool(factories=…, drop_tables=…, serial_batch_sizes=…)` takes. `_drop_order` is still in the layer
  (09 deletes it with the file, since the package orders a drop by foreign key). `register_factories`, the method
  `_drop_actions` and SI's fallback of 5 (`ClientPool.py`, now `:25`) are as they were; the package's fallback is 500.
- **The finding of §2.1.3, for 09:** registered with no size, `version` and `InflatonTrajectoryValue`; a size and no table,
  `temperature`. Neither unsized table leases a serial (`InflatonTrajectoryValue` registers `"serial": False`; `version` is excluded
  at the lease guard), so no table leases under SI's 5. Three tables carry a size of 500 and register `"serial": False`
  (`FullInstantonValue`, `SlowRollInstantonValue`, `GradientCoupledInstantonValue`): their sizes are never read. All of it moves
  verbatim (P12); 09 decides what to hand the package.
- **The shard key is a mapping** at all 15 calls: DatastoreKit takes only `{"delta_Nstar": key}`; `vectorized_shard_key` is
  the one definition. The `ast` test pins the 15. The four stubs take the mapping.
- **The import cycle** (the opened issue): until 09 deletes the layer and empties `Datastore/__init__.py` and `Datastore/SQL/__init__.py`
  (P6), `import config.datastore` must come after a `Datastore.SQL.*` import. 09's acceptance should include a fresh
  `./venv/bin/python -I -c "import config.datastore"`, and `tests/test_compare_stores.py:938-945`'s fallback can go with it.
- **Prose that 09/12 must revisit** (nothing opened): the three sketches that pass a bare `delta_Nstar_obj`
  (`INFRASTRUCTURE.md:467`, `architecture-summary.md:461`, `:537`); `FILE_MAP.md`'s two rows now name `config/datastore.py`.
- **Suites:** 690 (689 passed, 1 skipped) and 61 (60 passed, 1 skipped); `slow` baseline 69 of 69 (02's S1). 06 and 07 start
  from these.
- **The venv** is untouched (nothing installed or uninstalled). No Ray cluster is up; the rehearsal lock is untouched; the only
  store opened was the temporary one, deleted. DatastoreKit, RayPoolKit, ChamPBH and SGK are untouched.
- **The issue** `[config-datastore-cannot-be-imported-before-the-layer]` is open, owner 09 (`.documents/OPEN-ISSUES.md` §6a; 62 open).
  `.prompts/INDEX.md` is the orchestrator's.
- **Rollback:** `git revert` of `875cf41`. The venv needs nothing; reverting restores the layer's definitions and the bare shard keys.
