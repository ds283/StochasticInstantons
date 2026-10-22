# 10a - pin `datastorekit` `v0.5.0`

**Subject:** Pin `datastorekit` `v0.5.0` in `requirements.txt`, install it into the venv in place of `v0.4.0`, and check on the installed package what SI needs of the release
**Commit:** the commit that adds this note, on branch `dk-and-rpk-migration`, on top of `3fd8778`
**Date:** 2026-10-22, by Claude Sonnet 5.5
**Result:** **COMPLETE.** K8-K11 hold. The venv's `datastorekit` is replaced: 0.4.0 uninstalled, 0.5.0
installed from the tag's commit `f47b9a255e9ad58e0d0eaf85644f53b575884d31`, and nothing else moved. Its 21
modules are the tag's, byte for byte, with no `tests/`; exactly two, `store_inventory.py` and
`store_fingerprint.py`, differ from the saved `v0.4.0` files; the install is not editable. On the installed
package the new fields, the refusal and `ENCODING_FORMAT` 1 behave as required and U5 does not move. The suites
give 730 (729 passed, 1 skipped) and 67 (66 passed, 1 skipped), as 10's. No code or test changed. No issue is
opened.

Prompt: [`.prompts/dk-and-rpk-migration/10a-pin-datastorekit-v0.5.0.md`](../../.prompts/dk-and-rpk-migration/10a-pin-datastorekit-v0.5.0.md),
corrected by the orchestrator's brief (applied; see Deviations). Scratch outputs, the archive extraction and
K11's script were kept outside the repository.

## What shipped

- **K8.** `requirements.txt:16`, replaced in place (73 lines before and after):
  ```diff
  -datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0
  +datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.5.0
  ```
- **K9.** `./venv/bin/pip install -r requirements.txt` from the repository root, run once, after one dry run
  that reported `datastorekit` alone.
- **K10, K11.** The proofs below.
- This note and the board's records (§1 rows, K8-K11, §5.26). No code, test, or file of DatastoreKit or RayPoolKit.

## Deviations from the prompt

1. **The board section is §5.26**, after §5.25; the header's "Last updated" and status line are updated to
   match (brief correction 1). `STRUCTURALLY REQUIRED`.
2. **The install prints an uninstall** of `datastorekit-0.4.0` (`Attempting uninstall`, `Found existing
   installation: datastorekit 0.4.0`, `Successfully uninstalled datastorekit-0.4.0`): the replacement the
   prompt asks for, not another distribution moved (correction 3). `STRUCTURALLY REQUIRED`.
3. **pip's `Resolved ... to commit 6a6809d5...`** names the **tag object**; the commit recorded is `f47b9a25...`
   (correction 4). `STRUCTURALLY REQUIRED`.
4. **`raypoolkit` is re-resolved, not reinstalled** (correction 5): clone and `Resolved ... 4e7eb153...` (its tag
   object), then nothing; its 16 files keep their mtimes. `STRUCTURALLY REQUIRED`.
5. **The "before" holds content** (correction 7): the SHA-256 and mtime of every installed file of
   `datastorekit` and `raypoolkit` and their dist-infos were saved by a Python `os.stat` walk. `IMPLEMENTATION CHOICE`.
6. **The suites' commands** are the brief's (`-p no:cacheprovider`, `RAY_ADDRESS=local` for the integration run;
   README §5 rules 16-17). `IMPLEMENTATION CHOICE`.
7. **K11 runs under `python -I`** with SI's root appended to `sys.path` after `site-packages`, so that no
   `PYTHONPATH` or script directory can supply `datastorekit`. `IMPLEMENTATION CHOICE`.
8. No `UNINTENDED DRIFT`.

## Verification performed

### Before

- `git status`: clean; `HEAD` `3fd8778`. No SI cluster (`ray_cluster.sh status`: lock free, no processes, the
  four ports free); `RAY_ADDRESS` unset; no `gcs_server`, `raylet` or `pytest` running.
- `pip freeze`: 83 lines, with `datastorekit @ ...@c8570e849334d09085bbd84876095fc9e22bd005` and
  `raypoolkit @ ...@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`: 08's. `pip check`: `No broken requirements found.`
- Saved: mtimes, sizes and SHA-256 of the 66 files under `datastorekit/`, `raypoolkit/` and their dist-infos
  (21 `datastorekit` modules; `raypoolkit`: 16 files).
- Tag: `git ls-remote --tags https://github.com/ds283/DatastoreKit v0.5.0 'v0.5.0^{}'` gives
  ```text
  6a6809d570023ce32513deac4528e93ada4ef824	refs/tags/v0.5.0
  f47b9a255e9ad58e0d0eaf85644f53b575884d31	refs/tags/v0.5.0^{}
  ```
  and `git -C /Users/ds283/Documents/Code/DatastoreKit rev-parse 'v0.5.0^{commit}'` gives
  `f47b9a255e9ad58e0d0eaf85644f53b575884d31`.

### The dry run

`./venv/bin/pip install --dry-run -r requirements.txt`, exit 0, besides the `Requirement already satisfied` lines:

```text
Collecting datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.5.0 (from -r requirements.txt (line 16))
  Cloning https://github.com/ds283/DatastoreKit (to revision v0.5.0) to /private/var/folders/.../datastorekit_...
  Running command git checkout -q 6a6809d570023ce32513deac4528e93ada4ef824
  Resolved https://github.com/ds283/DatastoreKit to commit 6a6809d570023ce32513deac4528e93ada4ef824
  Installing build dependencies ... done; Getting requirements to build wheel ... done; Preparing metadata ... done
Collecting raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0 (from -r requirements.txt (line 59))
  Cloning ... ; git checkout -q 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Resolved https://github.com/ds283/RayPoolKit to commit 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Installing build dependencies ... done; Getting requirements to build wheel ... done; Preparing metadata ... done
Would install datastorekit-0.5.0
```

### The install (K9)

`./venv/bin/pip install -r requirements.txt`, exit 0, besides the `already satisfied` lines:

```text
Collecting datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.5.0 (from -r requirements.txt (line 16))
  Cloning ... ; git checkout -q 6a6809d570023ce32513deac4528e93ada4ef824
  Resolved https://github.com/ds283/DatastoreKit to commit 6a6809d570023ce32513deac4528e93ada4ef824
  Installing build dependencies ... done; Getting requirements to build wheel ... done; Preparing metadata ... done
Collecting raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0 (from -r requirements.txt (line 59))
  Cloning ... ; git checkout -q 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Resolved https://github.com/ds283/RayPoolKit to commit 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Installing build dependencies ... done; Getting requirements to build wheel ... done; Preparing metadata ... done
Building wheels for collected packages: datastorekit
  Created wheel for datastorekit: filename=datastorekit-0.5.0-py3-none-any.whl size=105087 sha256=278cb1d3cbeed3146056bf4f92b31f548d25d991c17b76520070cd45a3bed4c9
Successfully built datastorekit
Installing collected packages: datastorekit
  Attempting uninstall: datastorekit
    Found existing installation: datastorekit 0.4.0
    Uninstalling datastorekit-0.4.0:
      Successfully uninstalled datastorekit-0.4.0
Successfully installed datastorekit-0.5.0
```

Only `datastorekit` was uninstalled or installed. The `Resolved ... 6a6809d5...` line is the tag object (the
checkout of the tag); the commit recorded below is `f47b9a25...`. `raypoolkit`'s lines are pip re-resolving a VCS
requirement it already holds. Every pip command printed the notice `A new release of pip is available: 26.0.1 ->
26.2.1`; pip was not upgraded (`pip --version`: 26.0.1).

### K10, after

1. **`pip freeze`** (83 lines) against the saved one (`diff`):
   ```text
   16c16
   < datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005
   ---
   > datastorekit @ git+https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31
   ```
   `pip check`: `No broken requirements found.`
2. **`raypoolkit` not reinstalled:** its 16 files (modules and dist-info) have the saved mtimes (none changed).
3. **Provenance.** `utilities.installed_package_provenance()` gives, for `datastorekit`,
   `{'version': '0.5.0', 'url': 'https://github.com/ds283/DatastoreKit', 'commit': 'f47b9a255e9ad58e0d0eaf85644f53b575884d31', 'requested_revision': 'v0.5.0', 'editable': False}`
   and `raypoolkit` unchanged (`0.2.0`, `eaef0ce6...`, `v0.2.0`, not editable). `format_package_provenance` prints
   ```text
   >> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
   ```
4. **The installed files are the tag's.** Against `git -C /Users/ds283/Documents/Code/DatastoreKit archive v0.5.0
   datastorekit`, extracted outside both repositories:
   - the archive holds **21** `.py` files outside `tests/`; **21 of 21** are installed, byte for byte;
   - the installed package holds those 21 files and nothing else but `__pycache__`; `tests/` is not installed;
   - against the saved `v0.4.0` SHA-256s, **exactly two differ**: `store_fingerprint.py` and
     `store_inventory.py`; the other 19 are byte-equal to what was installed before;
   - all 21 have new mtimes (the replacement rewrote them), which is expected and shows nothing.
5. **The origin.** `datastorekit-0.5.0.dist-info/direct_url.json`, verbatim:
   ```json
   {"url": "https://github.com/ds283/DatastoreKit", "vcs_info": {"commit_id": "f47b9a255e9ad58e0d0eaf85644f53b575884d31", "requested_revision": "v0.5.0", "vcs": "git"}}
   ```
   No `dir_info`. The only `.pth` in `site-packages` is `_virtualenv.pth`; no `.egg-link` or `__editable__` file.
   `datastorekit-0.4.0.dist-info` is gone; `datastorekit-0.5.0.dist-info` holds `INSTALLER`, `METADATA`, `RECORD`,
   `REQUESTED`, `WHEEL`, `direct_url.json`, `licenses`, `top_level.txt`.
6. **The import.** `./venv/bin/python -c "import ray; import datastorekit; from datastorekit.SQL.ShardedPool import
   ShardedPool; print(ray.is_initialized())"` prints `False`; `./venv/bin/python -m datastorekit.tools.sharded_store
   --help` exits 0. No Ray was started.

### K11, on the installed package

`./venv/bin/python -I k11_10a.py` (scratch directory, not in the repository). The script, whole:

```python
"""K11 for dk-and-rpk-migration prompt 10a: what SI needs of datastorekit v0.5.0, on the INSTALLED package.

Run as: ./venv/bin/python -I k11_10a.py   (-I: no PYTHONPATH, no script-directory on sys.path)
Edits nothing in SI; SI's root is put on sys.path here, after site-packages.
"""
import dataclasses
import sys

SI_ROOT = "/Users/ds283/Documents/Code/StochasticInstantons"
sys.path.append(SI_ROOT)  # appended: the venv's site-packages wins for datastorekit

import ray

import datastorekit.store_fingerprint as sf
import datastorekit.store_inventory as si

print("datastorekit.store_inventory.__file__:", si.__file__)
assert si.__file__.startswith(SI_ROOT + "/venv/lib/python3.13/site-packages/datastorekit/"), si.__file__

spec_fields = {f.name for f in dataclasses.fields(si.InventorySpec)}
rec_fields = {f.name for f in dataclasses.fields(si.Record)}
assert "extra_values" in spec_fields and si.InventorySpec().extra_values == {}
assert "extra_value_counts" in rec_fields
print("InventorySpec().extra_values:", dict(si.InventorySpec().extra_values))
print("ENCODING_FORMAT:", sf.ENCODING_FORMAT)
assert sf.ENCODING_FORMAT == 1

r0 = si.Record(key={"a": 1}, tags=(), validated=True, value_count=3)
print("Record().extra_value_counts:", dict(r0.extra_value_counts))
print("as_json keys, empty:", sorted(r0.as_json()))
assert r0.extra_value_counts == {}
assert sorted(r0.as_json()) == ["key", "tags", "validated", "value_count"]
r1 = dataclasses.replace(r0, extra_value_counts={"T": 2})
print("as_json keys, one entry:", sorted(r1.as_json()))
assert sorted(r1.as_json()) == ["extra_value_counts", "key", "tags", "validated", "value_count"]

import config.datastore as cd

expected = ["version", "store_tag", "redshift", "tolerance", "efold_value", "delta_Nstar", "N_init", "N_final",
            "n_collocation_points", "alpha_regularization", "inflaton_mass", "quartic_coupling", "phi_value",
            "pi_value", "MasslessDecoupledDiffusion", "IntegrationSolver", "CosmologicalParams",
            "QuadraticPotential", "QuarticPotential", "InflatonTrajectory", "FullInstanton",
            "GradientCoupledInstanton", "SlowRollInstanton", "CompactionFunction"]
classes = si.inventory_classes(cd.factories)
print(f"inventory_classes: {len(classes)}: {', '.join(classes)}")
assert list(classes) == expected

specs = si.inventory_specs(cd.factories)
print("no SI spec declares extra_values:", all(len(s.extra_values) == 0 for s in specs.values()))
assert all(len(s.extra_values) == 0 for s in specs.values())
print("GCI values slot:", specs["GradientCoupledInstanton"].values)
assert specs["GradientCoupledInstanton"].values == ("GradientCoupledInstantonProfile", "parent_serial")


class _Wrapped:
    def __init__(self, inner):
        self._inner = inner

    def inventory_spec(self):
        spec = self._inner.inventory_spec()
        return dataclasses.replace(spec, extra_values={spec.values[0]: spec.values[1]})


bad = dict(cd.factories)
bad["GradientCoupledInstanton"] = _Wrapped(cd.factories["GradientCoupledInstanton"])
try:
    si.inventory_classes(bad)
except ValueError as e:
    print("ValueError:", e)
    assert "GradientCoupledInstanton" in str(e) and "GradientCoupledInstantonProfile" in str(e)
else:
    raise AssertionError("inventory_classes accepted values named again in extra_values")

print("ray.is_initialized():", ray.is_initialized())
assert not ray.is_initialized()
print("K11: OK")
```

Its output, whole (exit 0, `K11: OK`):

```text
datastorekit.store_inventory.__file__: /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/datastorekit/store_inventory.py
InventorySpec().extra_values: {}
ENCODING_FORMAT: 1
Record().extra_value_counts: {}
as_json keys, empty: ['key', 'tags', 'validated', 'value_count']
as_json keys, one entry: ['extra_value_counts', 'key', 'tags', 'validated', 'value_count']
inventory_classes: 24: version, store_tag, redshift, tolerance, efold_value, delta_Nstar, N_init, N_final, n_collocation_points, alpha_regularization, inflaton_mass, quartic_coupling, phi_value, pi_value, MasslessDecoupledDiffusion, IntegrationSolver, CosmologicalParams, QuadraticPotential, QuarticPotential, InflatonTrajectory, FullInstanton, GradientCoupledInstanton, SlowRollInstanton, CompactionFunction
no SI spec declares extra_values: True
GCI values slot: ('GradientCoupledInstantonProfile', 'parent_serial')
ValueError: inventory_classes(): GradientCoupledInstanton names GradientCoupledInstantonProfile both as its value table and in its extra_values
ray.is_initialized(): False
K11: OK
```

The first line shows `datastorekit` imported from the venv's `site-packages`, and the script asserts it. U5:
`./venv/bin/python -m pytest tests/test_tables_to_drop.py -q -p no:cacheprovider` gives **9 passed** (the 31 non-empty
sets of the five drop groups, 10 closed and 21 refused, with the pinned messages).

### The suites

Serially, after the install, no Ray cluster up, no `slow` block (the diff touches none of its paths).

| Run | Result | Time | `uptime` load (1/5/15 min) before; after |
|---|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **730: 729 passed, 1 skipped** (136 deselected; 10 warnings) | 35.99 s | 7.42 / 11.43 / 17.71; 7.15 / 10.83 / 17.20 |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **67: 66 passed, 1 skipped** (799 deselected; 1 warning) | 52.26 s | 7.15 / 10.83 / 17.20; 27.83 / 15.48 / 18.49 |

Both equal 10's counts. After them `pip freeze` is unchanged and `git status` showed `requirements.txt` alone (the
note and the board came after).

## The deliberate-breakage record

None: 10a adds no code and no test (README §5 rule 8). §2.4's and §2.5's checks are the proof, and each fails on
a wrong install or a release without the field: an editable or local-path install would carry `dir_info` or a
`file://` URL; another tag would fail the commit and byte comparisons; a stale `v0.4.0` would fail the first K11
assertion (`InventorySpec.extra_values`), and the script asserts its own import path; an install that moved any
other module would fail the comparison with the saved hashes.

## Observations not acted on

- pip's `Resolved ... 6a6809d5...` is the tag object, and `raypoolkit`'s `4e7eb153...` likewise; a reader comparing
  them with the freeze's `f47b9a25...` and `eaef0ce6...` should not take them for a mismatch.
- Each `pip install -r` re-clones RayPoolKit (a VCS requirement) and leaves it installed.
- Importing `config.datastore` from the K11 script leaves the tree unchanged (`git status` showed the pin alone).

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, one commit on `3fd8778`. Tracked change: `requirements.txt` (one line), this
  note and the board.
- **`requirements.txt`** has 73 lines; the pin is `:16`, `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.5.0`,
  between `cycler==0.12.1` (`:15`) and `distlib==0.4.3` (`:17`). `ray==2.55.1` is `:58`, `raypoolkit` `:59`,
  `SQLAlchemy` `:67`.
- **The venv** (outside git) holds `datastorekit` 0.5.0 at `f47b9a255e9ad58e0d0eaf85644f53b575884d31` and `raypoolkit`
  0.2.0 at `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`, neither editable; `pip freeze` is 83 lines, 08's but for
  the `datastorekit` line. `pip check` is clean.
- **Every driver's provenance line** now reads `>> packages: datastorekit 0.5.0
  (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0
  (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **What 10b starts from:** SI declares no `extra_values`; the installed `InventorySpec.extra_values` and
  `Record.extra_value_counts` default empty, `as_json` carries the latter only when not empty, `ENCODING_FORMAT` is
  1, and `inventory_classes` refuses a `values` table named again in `extra_values` (`ValueError:
  inventory_classes(): GradientCoupledInstanton names GradientCoupledInstantonProfile both as its value table and
  in its extra_values`). `GradientCoupledInstanton`'s values slot is `('GradientCoupledInstantonProfile',
  'parent_serial')`. SI's registry gives 24 inventory classes.
- **Suites:** 730 (729 passed, 1 skipped) and 67 (66 passed, 1 skipped); `slow` baseline 69 of 69 (02's S1), not run.
- **Rollback:** `git revert` of this commit **plus** `./venv/bin/pip install -r requirements.txt` after the revert,
  which pip resolves to `v0.4.0` (`c8570e84...`) (README §4.4); the revert alone leaves `v0.5.0` in the venv.
- No Ray cluster is up; the rehearsal lock is untouched; no store was opened. No issue is opened, so
  `.documents/OPEN-ISSUES.md` is unchanged. `.prompts/INDEX.md` and the README are the orchestrator's.
