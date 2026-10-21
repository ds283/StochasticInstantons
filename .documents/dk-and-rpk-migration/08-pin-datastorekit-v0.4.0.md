# 08 — pin `datastorekit` `v0.4.0`

**Subject:** Pin `datastorekit` `v0.4.0` in `requirements.txt`, install the venv from it, and check on the installed package what SI needs of the release
**Commit:** the commit that adds this note, on branch `dk-and-rpk-migration`, on top of `7ef06ad`
**Date:** 2026-10-21, by Claude Sonnet 5.5
**Result:** **COMPLETE.** K4–K7 hold. The venv gained one distribution, `datastorekit` 0.4.0, built
from the tag's commit `c8570e849334d09085bbd84876095fc9e22bd005`; its 21 modules are the tag's, byte
for byte, with no `tests/`; the install is not editable. On the installed package U3's `timestamp`
and `v0.2.3`'s factory base behave as required, and SI's 30 registry entries (28 classes) all
instantiate on the installed `SQLAFactoryBase`. The suites give 696 (695 passed, 1 skipped) and 62
(61 passed, 1 skipped), as at 07. No code or test changed. No issue is opened.

Prompt: [`.prompts/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md`](../../.prompts/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md),
corrected by the orchestrator's brief (its seven corrections are applied; see Deviations). Scratch
outputs, the archive extraction and K7's script were kept outside the repository.

## What shipped

- **K4.** `requirements.txt` gains one line, at `:16`, between `cycler==0.12.1` (`:15`) and
  `distlib==0.4.3` (now `:17`):
  ```text
  datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0
  ```
  No other line changed (73 lines now, from 72).
- **K5.** `./venv/bin/pip install -r requirements.txt` from the repository root, run once, after one
  dry run that reported `datastorekit` alone.
- **K6, K7.** The proofs below.
- This note and the board's records. No code, test, or file of DatastoreKit or RayPoolKit.

## Deviations from the prompt

1. **The board section is §5.21**, appended after §5.20; the header's "Last updated" and status line
   are updated to match (the orchestrator's correction 1). `STRUCTURALLY REQUIRED`.
2. **The pin is at `:16`** (`requirements.txt` has 72 lines at `HEAD`, the prompt's line numbers are
   from `91e6f31`), and the lines after it move by one (correction 2). `STRUCTURALLY REQUIRED`.
3. **The suites' commands** are the brief's: `-p no:cacheprovider`, and `RAY_ADDRESS=local` for the
   integration run (correction 3; README §5 rules 16–17). `IMPLEMENTATION CHOICE`.
4. **pip's `Resolved … to commit 8e7c1d77…`** names the tag object, not the commit; it is quoted and
   explained below, and is not the prompt's "installed commit is not `c8570e849334…`" stop
   (correction 6). `STRUCTURALLY REQUIRED`.
5. **`raypoolkit` is re-resolved, not reinstalled** (correction 5): pip clones RayPoolKit again and
   leaves it; the evidence is the unchanged mtimes and freeze line. `STRUCTURALLY REQUIRED`.
6. **The baseline file** `measure/out/7bb3efd-pip-freeze.txt` is at
   `.prompts/dk-and-rpk-migration/measure/out/7bb3efd-pip-freeze.txt`; the prompt's path is relative to
   the campaign folder. `IMPLEMENTATION CHOICE`.
7. K7's registry check recognises the quantity entries by an `ObjectType` attribute on the instance
   (correction 7). `IMPLEMENTATION CHOICE`.
8. No `UNINTENDED DRIFT`.

## Verification performed

### Before

- `pip freeze` (82 lines) equals `.prompts/dk-and-rpk-migration/measure/out/7bb3efd-pip-freeze.txt`
  plus the one line `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`
  (compared sorted: no difference).
- `pip check`: `No broken requirements found.`
- `pip show datastorekit`: `WARNING: Package(s) not found: datastorekit`.
- `raypoolkit`'s 16 installed files (its modules and its dist-info) had their
  mtimes saved (nanoseconds, by a Python `os.stat` walk, since the machine's `stat` is not BSD's).
- Tag: `git ls-remote --tags https://github.com/ds283/DatastoreKit v0.4.0 'v0.4.0^{}'` gives
  ```text
  8e7c1d77b3792b57b98983e84b99fc68ab88cb89	refs/tags/v0.4.0
  c8570e849334d09085bbd84876095fc9e22bd005	refs/tags/v0.4.0^{}
  ```
  and `git -C /Users/ds283/Documents/Code/DatastoreKit rev-parse 'v0.4.0^{commit}'` gives
  `c8570e849334d09085bbd84876095fc9e22bd005`.
- No SI cluster up (`ray_cluster.sh status`: lock free, no processes, port 6390 free).

### The dry run

`./venv/bin/pip install --dry-run -r requirements.txt`, besides the `Requirement already satisfied` lines:

```text
Collecting datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0 (from -r requirements.txt (line 16))
  Cloning https://github.com/ds283/DatastoreKit (to revision v0.4.0) to /private/var/folders/…/datastorekit_…
  Running command git clone --filter=blob:none --quiet https://github.com/ds283/DatastoreKit …
  Running command git checkout -q 8e7c1d77b3792b57b98983e84b99fc68ab88cb89
  Resolved https://github.com/ds283/DatastoreKit to commit 8e7c1d77b3792b57b98983e84b99fc68ab88cb89
  Installing build dependencies: started … finished with status 'done'
  Getting requirements to build wheel: started … finished with status 'done'
  Preparing metadata (pyproject.toml): started … finished with status 'done'
Collecting raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0 (from -r requirements.txt (line 59))
  Cloning … ; git checkout -q 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Resolved https://github.com/ds283/RayPoolKit to commit 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Installing build dependencies … done; Getting requirements to build wheel … done; Preparing metadata … done
Would install datastorekit-0.4.0
```

Only `datastorekit`. The `Resolved … 8e7c1d77…` line names the **tag object**, not the commit: pip
reports the unpeeled ref, and `git checkout -q 8e7c1d77…` checks out the tag. The commit recorded below
is `c8570e84…`. The `raypoolkit` lines are pip re-resolving a VCS requirement it already holds; nothing is
installed for it. Build dependencies went into pip's temporary isolated environment.

### The install (K5)

`./venv/bin/pip install -r requirements.txt`, exit 0, besides the `already satisfied` lines:

```text
Collecting datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0 (from -r requirements.txt (line 16))
  Cloning … ; git checkout -q 8e7c1d77b3792b57b98983e84b99fc68ab88cb89
  Resolved https://github.com/ds283/DatastoreKit to commit 8e7c1d77b3792b57b98983e84b99fc68ab88cb89
  Installing build dependencies … done; Getting requirements to build wheel … done; Preparing metadata … done
Collecting raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0 (from -r requirements.txt (line 59))
  Cloning … ; git checkout -q 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Resolved https://github.com/ds283/RayPoolKit to commit 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Installing build dependencies … done; Getting requirements to build wheel … done; Preparing metadata … done
Building wheels for collected packages: datastorekit
  Building wheel for datastorekit (pyproject.toml): started … finished with status 'done'
  Created wheel for datastorekit: filename=datastorekit-0.4.0-py3-none-any.whl size=104422 sha256=8408f592b5441ccbb5a605bac97c3633bd3fb4d42c01311da61b1ebcfe571e00
  Stored in directory: …/pip-ephem-wheel-cache-…/wheels/32/04/27/8e2b019b86d57ef78abbfd9a74a23b50382c260c8a6fff8288
Successfully built datastorekit
Installing collected packages: datastorekit
Successfully installed datastorekit-0.4.0
```

One distribution installed and none moved. Both commands also printed pip's upgrade notice
(`26.0.1 -> 26.2.1`), ignored: pip itself was not upgraded.

### K6

1. **`pip freeze`** against the saved one: `diff` gives exactly
   ```text
   15a16
   > datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005
   ```
   (83 lines now). **`pip check`:** `No broken requirements found.`
2. **`raypoolkit` was not reinstalled:** the nanosecond mtimes of its 16 installed files, saved
   before, are identical after (`cmp` of the two lists); its freeze line is unchanged.
3. **Provenance.** `utilities.installed_package_provenance()["datastorekit"]` is
   `{'version': '0.4.0', 'url': 'https://github.com/ds283/DatastoreKit', 'commit': 'c8570e849334d09085bbd84876095fc9e22bd005', 'requested_revision': 'v0.4.0', 'editable': False}`;
   `["raypoolkit"]` is `{'version': '0.2.0', 'url': 'https://github.com/ds283/RayPoolKit', 'commit': 'eaef0ce60e2fc354bb32f0ad576010e6a83c1976', 'requested_revision': 'v0.2.0', 'editable': False}`,
   unchanged. `format_package_provenance` prints:
   ```text
   >> packages: datastorekit 0.4.0 (https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005, requested v0.4.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
   ```
4. **The installed files are the tag's.** Installed package:
   `venv/lib/python3.13/site-packages/datastorekit`. Compared with
   `git -C /Users/ds283/Documents/Code/DatastoreKit archive v0.4.0 datastorekit`, extracted into a
   scratch directory outside both repositories.

   | | files |
   |---|---|
   | archive, `.py` outside `datastorekit/tests/` | 21 (`__init__`, `_timing`, `contract`, `defaults`, `object`, `replication`, `shard_paths`, `store_fingerprint`, `store_inventory`, `store_reader`, `SQL/{__init__,ClientPool,Datastore,factory_base,ProfileAgent,schema,SerialPoolBroker,ShardedPool}`, `tools/{__init__,shard_key_audit,sharded_store}`) |
   | archive, `.py` under `datastorekit/tests/` | 52 |
   | archive, `.json` under `datastorekit/tests/data/` | 4 |
   | installed `.py` (ignoring `__pycache__`) | 21, the same names; none extra |
   | installed `tests/` and the four `.json` files | not present |

   Byte comparison (`filecmp`, `shallow=False`) of the 21: **21 compared, 0 different**. The dist-info
   `RECORD` has no line naming `tests`.
5. **The origin.** `datastorekit-0.4.0.dist-info/direct_url.json`, verbatim:
   ```json
   {"url": "https://github.com/ds283/DatastoreKit", "vcs_info": {"commit_id": "c8570e849334d09085bbd84876095fc9e22bd005", "requested_revision": "v0.4.0", "vcs": "git"}}
   ```
   A VCS record, no `dir_info`. No `.egg-link` and no `__editable__` file in `site-packages`; the only
   `.pth` is `_virtualenv.pth`, which does not name DatastoreKit.
6. **The import.** `./venv/bin/python -c "import ray; import datastorekit; from
   datastorekit.SQL.ShardedPool import ShardedPool; print(ray.is_initialized())"` prints `False`;
   `./venv/bin/python -m datastorekit.tools.sharded_store --help` exits **0**. No Ray was started.
7. **Nothing in SI imports the package.** `git grep -ln datastorekit -- '*.py'` outside `.prompts/` and
   `.documents/`: `tests/test_package_provenance.py`, `tests/test_rehearsal_stage_counts.py`,
   `tools/compare_stores.py` (docstring), `utilities.py`. As at `91e6f31`.

### K7, on the installed package

Run as `/Users/ds283/Documents/Code/StochasticInstantons/venv/bin/python k7_installed.py` from the
scratch directory, so that nothing of SI's tree is on `sys.path` when `datastorekit` is imported (SI's
root is appended afterwards, only to read `config.datastore`); it also asserts the module lives in the
venv's `site-packages`. Output:

```text
datastorekit from /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/datastorekit/__init__.py
timestamp round-trips
default timestamp is None
assign: AttributeError
positional: TypeError
register+build subclass instantiates
no build: TypeError: Can't instantiate abstract class NoBuild without an implementation for abstract method 'build'
30 of 30 instantiate; 28 classes; hooks {'all': 12, 'none': 16, 'some': 0}
ray initialized: False
```

Of SI's 28 factory classes, **12** define all of `store`, `validate` and `validate_on_startup`, **16**
define none, and none defines only some. All 30 registry entries instantiate on the installed base, so
nothing is a finding about the release. The script, whole:

```python
"""K7 for prompt 08: what SI needs of datastorekit v0.4.0, on the INSTALLED package.

Run as ./venv/bin/python k7_installed.py from the scratch directory. SI's tree is appended to
sys.path only after datastorekit has been imported, and only so that config.datastore and the
factory classes can be read; nothing of SI's is edited.
"""
import sys, importlib, datetime
import datastorekit
print("datastorekit from", datastorekit.__file__)
assert "site-packages" in datastorekit.__file__ and "StochasticInstantons/venv" in datastorekit.__file__
sys.path.append("/Users/ds283/Documents/Code/StochasticInstantons")
from datastorekit import DatastoreObject
from datastorekit.SQL.factory_base import SQLAFactoryBase as Base
t = datetime.datetime(2026, 10, 21, 12, 0, 0)
o = DatastoreObject(1, timestamp=t); assert o.timestamp == t; print("timestamp round-trips")
assert DatastoreObject(1).timestamp is None; print("default timestamp is None")
try: o.timestamp = t; print("FAIL assign")
except AttributeError: print("assign: AttributeError")
try: DatastoreObject(1, t); print("FAIL positional")
except TypeError: print("positional: TypeError")
class Ok(Base):
    def register(self): return {}
    def build(self, payload, conn, table, inserter, tables, inserters): return None
Ok(); print("register+build subclass instantiates")
try:
    class NoBuild(Base):
        def register(self): return {}
    NoBuild(); print("FAIL nobuild")
except TypeError as e: print("no build: TypeError:", e)
importlib.import_module("Datastore.SQL.Datastore")
from config.datastore import factories
assert datastorekit.SQL.factory_base.__file__.startswith("/Users/ds283/Documents/Code/StochasticInstantons/venv")
classes = {}; ok = 0; hooks = {"all": 0, "none": 0, "some": 0}
for name, f in factories.items():
    cls = type(f)
    if cls not in classes:
        ns = {k: v for k, v in vars(cls).items() if k not in ("__dict__", "__weakref__")}
        classes[cls] = type(cls.__name__, (Base,), ns)
        own = [h for h in ("store", "validate", "validate_on_startup") if h in vars(cls)]
        hooks["all" if len(own) == 3 else "none" if not own else "some"] += 1
    new = classes[cls]
    inst = new(f.ObjectType) if hasattr(f, "ObjectType") else new()
    assert isinstance(inst, Base); ok += 1
print(f"{ok} of {len(factories)} instantiate; {len(classes)} classes; hooks {hooks}")
import ray; print("ray initialized:", ray.is_initialized())
```

### The suites

Serially, after the install, no Ray cluster up, no `slow` block (the diff touches none of its paths).

| Run | Result | Time | `uptime` load (1/5/15 min) before; after |
|---|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **696: 695 passed, 1 skipped** (131 deselected; 10 warnings) | 30.51 s | 25.41 / 52.80 / 72.07; 33.54 / 51.82 / 70.94 |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **62: 61 passed, 1 skipped** (765 deselected; 1 warning) | 32.84 s | 31.89 / 51.18 / 70.60; 60.33 / 56.42 / 71.74 |

Both equal 07's counts. The machine was loaded by desktop apps (10 CPUs); this affects the times only.
After them `pip freeze` is unchanged and `git status` shows `requirements.txt` alone.

## The deliberate-breakage record

None: 08 adds no code and no test (README §5 rule 8). §2.4's and §2.5's checks are the proof, and each
fails on a wrong install or a release without U3: an editable or local-path install would carry
`dir_info` or a `file://` URL; another tag would fail the commit and byte comparisons; a release
without U3 would fail the `timestamp` checks; one whose base did not accept SI's classes would fail
the 30-entry instantiation.

## Observations not acted on

- pip's `Resolved … to commit 8e7c1d77…` is the tag object; a reader comparing it with the freeze's
  `c8570e84…` should not take them for a mismatch. The same holds for `raypoolkit`'s `4e7eb153…`.
- Each `pip install -r` re-clones RayPoolKit (a VCS requirement) and leaves it installed, as ChamPBH's
  07 found.
- The machine's `stat` is GNU-style (`-f` is a filesystem query), so mtimes were read with Python.

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, one commit on `7ef06ad`. Tracked change: `requirements.txt`
  (one line), this note and the board.
- **`requirements.txt`** has 73 lines; the pin is at `:16`, between `cycler==0.12.1` (`:15`) and
  `distlib==0.4.3` (`:17`). `ray==2.55.1` moved from `:57` to `:58`, `raypoolkit` from `:58` to `:59`
  and `SQLAlchemy` from `:66` to `:67`.
- **The venv** (outside git) holds `datastorekit` 0.4.0 at `c8570e849334d09085bbd84876095fc9e22bd005`
  and `raypoolkit` 0.2.0 at `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`, neither editable; `pip freeze`
  (83 lines) is `measure/out/7bb3efd-pip-freeze.txt` plus those two lines. `pip check` is clean.
- **Every driver's provenance line** now reads `>> packages: datastorekit 0.4.0
  (https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005, requested v0.4.0);
  raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976,
  requested v0.2.0)`.
- **Nothing imports `datastorekit` yet.** The layer (`Datastore/`) is intact; 09 swaps to the package.
  The installed package imports without starting Ray; U3's `timestamp` and `SQLAFactoryBase` behave as
  09 needs, and SI's 30 registry entries (28 classes: 12 define all three of `store`, `validate`,
  `validate_on_startup`, 16 none) instantiate on the installed base.
- **Suites:** 696 (695 passed, 1 skipped) and 62 (61 passed, 1 skipped); `slow` baseline 69 of 69 (02's
  S1), not run.
- **Rollback:** `git revert` of this commit plus `./venv/bin/pip uninstall -y datastorekit` (README
  §4.4); the revert alone does not touch the venv.
- No Ray cluster is up; the rehearsal lock is untouched; no store was opened. No issue is opened, so
  `.documents/OPEN-ISSUES.md` is unchanged. `.prompts/INDEX.md` is the orchestrator's.
