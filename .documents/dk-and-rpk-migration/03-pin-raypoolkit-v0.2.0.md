# 03 — pin `raypoolkit` `v0.2.0`

**Subject:** Pin `raypoolkit` `v0.2.0` in `requirements.txt` and install the venv from it
**Commit:** this commit, on branch `dk-and-rpk-migration`, on top of `b1ab501`
**Date:** 2026-10-20, by Claude Sonnet 5.5
**Result:** **COMPLETE.** K1–K3 hold. The venv gained one distribution, `raypoolkit` 0.2.0, built
from the tag's commit `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`; its four modules are the tag's, byte
for byte; the install is not editable. The suites give 680 (679 passed, 1 skipped) and 61 (60 passed,
1 skipped), as at 01. No code or test changed. No issue is opened.

Prompt: [`.prompts/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md`](../../.prompts/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md),
corrected by the orchestrator's brief: the board section is §5.15 (the prompt's §5.7 is taken), and the
suites are run as README §5 rules 16–17 give. Scratch outputs were kept outside the repository.

## What shipped

- **K1.** `requirements.txt` gains one line, at `:58`, between `ray==2.55.1` and `referencing==0.37.0`:
  ```text
  raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0
  ```
  No other line changed (72 lines now, from 71).
- **K2.** `./venv/bin/pip install -r requirements.txt` from the repository root, run once, after a dry
  run that reported `raypoolkit` alone.
- **K3.** The proofs below.
- This note and the board's records. No code, test or RayPoolKit file.

## Deviations from the prompt

1. **The board section is §5.15, not §5.7** (the prompt's number is taken). `STRUCTURALLY REQUIRED`
   (the orchestrator's correction).
2. **The suites' commands** are the brief's: `-p no:cacheprovider`, and `RAY_ADDRESS=local` for the
   integration run. `IMPLEMENTATION CHOICE`, as README §5 rule 17.
3. None other.

## Verification performed

### Before

- `pip freeze` equals `measure/out/7bb3efd-pip-freeze.txt` (`cmp`: identical; 81 lines).
- `pip check`: `No broken requirements found.`
- `pip show raypoolkit`: `WARNING: Package(s) not found: raypoolkit` (exit 1).
- Tag: `git ls-remote --tags https://github.com/ds283/RayPoolKit v0.2.0 'v0.2.0^{}'` gives
  `4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef refs/tags/v0.2.0` (the tag object) and
  `eaef0ce60e2fc354bb32f0ad576010e6a83c1976 refs/tags/v0.2.0^{}` (the commit).
  `git -C /Users/ds283/Documents/Code/RayPoolKit rev-parse 'v0.2.0^{commit}'` gives
  `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`.

### The dry run

`./venv/bin/pip install --dry-run -r requirements.txt`, exit 0, 71 `Requirement already satisfied`
lines and, besides them:

```text
Collecting raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0 (from -r requirements.txt (line 58))
  Cloning https://github.com/ds283/RayPoolKit (to revision v0.2.0) to /private/var/folders/…/raypoolkit_…
  Running command git clone --filter=blob:none --quiet https://github.com/ds283/RayPoolKit
  Running command git checkout -q 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Resolved https://github.com/ds283/RayPoolKit to commit 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Installing build dependencies: started … finished with status 'done'
  Getting requirements to build wheel: started … finished with status 'done'
  Preparing metadata (pyproject.toml): started … finished with status 'done'
Would install raypoolkit-0.2.0
```

Only `raypoolkit`. The `Resolved … 4e7eb153…` line names the **tag object**, not the commit: pip
reports the unpeeled ref, and `git checkout -q 4e7eb153…` checks out the tag. The commit recorded
below is `eaef0ce6…`. This is not the prompt's "installed commit is not `eaef0ce6`" stop, which is
judged on `pip freeze` and `direct_url.json`. The build dependency (`setuptools>=64`) went into pip's
temporary isolated build environment, not the venv.

### The install (K2)

`./venv/bin/pip install -r requirements.txt`, exit 0, besides the `already satisfied` lines:

```text
Collecting raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0 (from -r requirements.txt (line 58))
  Cloning … ; git checkout -q 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Resolved https://github.com/ds283/RayPoolKit to commit 4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef
  Installing build dependencies … done; Getting requirements to build wheel … done; Preparing metadata … done
Building wheels for collected packages: raypoolkit
  Created wheel for raypoolkit: filename=raypoolkit-0.2.0-py3-none-any.whl size=13566 sha256=39d8c20f3d7bda32fc6d28f21e35ac4d46b94980f95768c826a4b85f626bae1a
  Stored in directory: …/pip-ephem-wheel-cache-…/wheels/80/77/a3/ffb624468d503c9d448ab31dc36bc5e5207e20153b1e1fada4
Successfully built raypoolkit
Installing collected packages: raypoolkit
Successfully installed raypoolkit-0.2.0
```

One distribution installed and none moved. Both commands also printed pip's upgrade notice
(`26.0.1 -> 26.2.1`), ignored: pip itself was not upgraded.

### K3

1. **`pip freeze`** against the saved one: `diff` gives exactly
   ```text
   64a65
   > raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976
   ```
2. **`pip check`:** `No broken requirements found.`
3. **Provenance.** `utilities.installed_package_provenance()["raypoolkit"]` is
   `{'version': '0.2.0', 'url': 'https://github.com/ds283/RayPoolKit', 'commit': 'eaef0ce60e2fc354bb32f0ad576010e6a83c1976', 'requested_revision': 'v0.2.0', 'editable': False}`;
   `["datastorekit"]` is `None`. `format_package_provenance` prints (the URL as recorded, without `git+`):
   ```text
   >> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
   ```
4. **The installed files are the tag's.** Installed package:
   `venv/lib/python3.13/site-packages/raypoolkit`. Compared with
   `git -C /Users/ds283/Documents/Code/RayPoolKit archive v0.2.0 raypoolkit`, extracted into a
   scratch directory outside both repositories.

   | | `.py` files |
   |---|---|
   | archive, outside `raypoolkit/tests/` | 4: `__init__.py`, `RayWorkPool.py`, `_timing.py`, `contract.py` |
   | archive, under `raypoolkit/tests/` | 10 (including its `__init__.py` and `standins.py`) |
   | installed | 4, the same names |
   | installed, under `tests/` | none (the directory does not exist) |

   `cmp` of each of the four: identical. Nothing else `.py` is installed (`__pycache__` ignored).
   **Result: the installed files are the tag's.** The dist-info `RECORD` lists the four modules and
   their `.pyc` files, and nothing under `tests/`.
5. **The origin.** `raypoolkit-0.2.0.dist-info/direct_url.json`, verbatim:
   ```json
   {"url": "https://github.com/ds283/RayPoolKit", "vcs_info": {"commit_id": "eaef0ce60e2fc354bb32f0ad576010e6a83c1976", "requested_revision": "v0.2.0", "vcs": "git"}}
   ```
   A VCS record, no `dir_info`. In `site-packages` there is no `.egg-link` and no `__editable__`
   file; the only `.pth` is `_virtualenv.pth`, which does not name RayPoolKit.
6. **The import.** `./venv/bin/python -c "import ray; import raypoolkit; from raypoolkit import
   RayWorkPool; print(ray.is_initialized())"` prints `False`. No Ray was started.

### The suites

Serially, after the install, no Ray cluster up (`pgrep` finds none), no `slow` block (the diff touches
none of its paths).

| Run | Result | Time | `uptime` load (1/5/15 min) |
|---|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **680: 679 passed, 1 skipped** (130 deselected; 10 warnings) | 25.16 s | 5.53 / 11.96 / 9.93 after; 6.45 / 12.76 / 10.12 before |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **61: 60 passed, 1 skipped** (749 deselected; 1 warning) | 12.14 s | 17.77 / 14.25 / 10.79 after; 5.33 / 11.81 / 9.88 before |

Both equal 01's counts. After them `pip freeze` is unchanged and `git status` shows `requirements.txt` alone.

## The deliberate-breakage record

None: 03 adds no code and no test (README §5 rule 8). §2.4's checks are the proof, and each fails on a
wrong install: an editable install would carry `dir_info` and a different `direct_url.json`; a build
from the local checkout would record a `file://` URL; a stale or other-tag install would fail the
commit check and the byte comparison.

## Observations not acted on

- pip's `Resolved … to commit 4e7eb153…` is the tag object (above); a reader comparing it with the
  freeze's `eaef0ce6…` should not take them for a mismatch.
- The local RayPoolKit checkout is at a later commit than the tag (documents only, README §0.5). It
  was read through `git archive`, `rev-parse` and `ls-remote` only, and not written.

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, this commit on `b1ab501`. Tracked change: `requirements.txt`
  (one line), this note and the board.
- **The venv** (outside git) holds `raypoolkit` 0.2.0 at `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`,
  not editable; `pip freeze` is `measure/out/7bb3efd-pip-freeze.txt` plus the one
  `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`
  line. `datastorekit` is not installed (08's).
- **Every driver's provenance line** now reads `>> packages: datastorekit not installed; raypoolkit
  0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **Nothing imports `raypoolkit` yet.** `RayTools/` is intact; 04 deletes it and rewrites the three
  imports to `from raypoolkit import RayWorkPool`. The package exports `RayWorkPool` and imports
  without starting Ray.
- **Suites:** 680 (679 passed, 1 skipped) and 61 (60 passed, 1 skipped); `slow` baseline 69 of 69
  (02's S1).
- **Rollback:** `git revert` of this commit plus `./venv/bin/pip uninstall -y raypoolkit` (README
  §4.4); the revert alone does not touch the venv.
- No Ray cluster is up; the rehearsal lock is untouched; no store was opened. No issue is opened, so
  `.documents/OPEN-ISSUES.md` is unchanged. `.prompts/INDEX.md` is the orchestrator's.
