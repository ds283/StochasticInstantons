# Prompt 03 — pin `raypoolkit` `v0.2.0`

**Campaign:** [`README.md`](README.md) · **Board items:** **K1**–**K3** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-12, with prompts 01, 02 and 04, after the user's rulings (README §6.1).
**Gate:**
- 02 landed and reviewed (board §1), with RH0's gate recorded in board §2;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no Ray cluster is up.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Sonnet**. One line of `requirements.txt` and an install, measured
closely.
**Needs the network**: the install fetches the tag from GitHub. The orchestrator dispatches this
prompt with that permission.

**Read first:**

1. [`README.md`](README.md): §0.2 ("The venv"), §2.2 (03's charter), §4.4 (rollback) and §5
   (rules 11–13).
2. RayPoolKit's `README.md` ("Installing", "Supported versions") and its
   `docs/adoption/README.md` §1, and its SI checklist item 1
   (`docs/adoption/stochasticinstantons.md`), at `/Users/ds283/Documents/Code/RayPoolKit`. **Read
   them; edit nothing in that repository** (README §5 rule 12).
3. RayPoolKit's `pyproject.toml` at the tag (`git -C <RayPoolKit> show v0.2.0:pyproject.toml`). It
   declares only `ray>=2.43`, and `packages.find` excludes `raypoolkit.tests`.
4. Prompt 01's results note, for `utilities.installed_package_provenance()` and the line it prints.
5. [`measure/out/7bb3efd-pip-freeze.txt`](measure/out/7bb3efd-pip-freeze.txt).
6. ChamPBH's 03, as done (read only): its board §5.4 and the review below it, in
   `/Users/ds283/Documents/Code/ChamPBH/prompts/dk-and-rpk-migration/IMPLEMENTATION_STATE.md`. Two
   of its findings bear on your checks:
   - pip's `Resolved … to commit 4e7eb153…` names the **tag object**, not the commit;
   - the recorded URL has **no `git+`**.

---

## 1. What is wanted

SI depends on a tagged release, pinned in `requirements.txt`, in a commit of its own (RayPoolKit
adoption README §1; README §5 rule 13). This prompt adds the pin and installs the venv from it.
Nothing in SI imports the package until 04.

- **K1 — the pin.** `requirements.txt` gains exactly this line:
  ```text
  raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0
  ```
  - It goes in sorted position. The file is in `pip freeze`'s order, case-insensitive, so the
    line goes between `ray==2.55.1` (`requirements.txt:57`) and `referencing==0.37.0` (`:58`).
  - No other line changes: `ray==2.55.1` stays as it is.
- **K2 — the install.** `./venv/bin/pip install -r requirements.txt`, from the repository root.
  - Never `pip install -e`, and never a local path to the RayPoolKit checkout. The install comes
    from the tag on GitHub, so that it is reproducible from the pin.
  - Never `--upgrade`, `--force-reinstall` or `--no-deps`. The one declared dependency, `ray>=2.43`,
    is already satisfied, so pip should add one distribution and move none. That is K3's first
    check.
  - **First, a dry run:** `./venv/bin/pip install --dry-run -r requirements.txt`, which must report
    only `raypoolkit` to be installed. If it reports anything else, stop before installing.
- **K3 — the proof that the venv holds the tag.**

---

## 2. What to do

1. **Before.** Save the following to the scratch directory you were given, or to a new temporary
   directory outside the repository:
   - `./venv/bin/pip freeze`. It must equal `measure/out/7bb3efd-pip-freeze.txt`. If it does not,
     stop: the venv has moved since the plan;
   - `./venv/bin/pip check`;
   - `./venv/bin/pip show raypoolkit`, which must find nothing.
2. **The tag.** `git ls-remote --tags https://github.com/ds283/RayPoolKit v0.2.0 'v0.2.0^{}'` gives
   tag object `4e7eb153ca98…` and commit `eaef0ce60e2fc354bb32f0ad576010e6a83c1976` (README §0.2).
   `git -C /Users/ds283/Documents/Code/RayPoolKit rev-parse 'v0.2.0^{commit}'` agrees.
3. **K1**, then the dry run, then **K2**. Keep pip's full output.
4. **K3, after:**
   1. **`pip freeze`** differs from the saved one by exactly one added line:
      `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`.
      Pip records the commit the tag resolved to. Show the diff.
   2. **`pip check`** reports no broken requirement.
   3. **`utilities.installed_package_provenance()["raypoolkit"]`** gives:
      - version `0.2.0`;
      - URL `https://github.com/ds283/RayPoolKit`;
      - commit `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`;
      - requested revision `v0.2.0`;
      - `editable: False`.

      `["datastorekit"]` is `None`. Show the line `format_package_provenance` prints.
   4. **The installed files are the tag's.** Compare the installed `raypoolkit/` package (from
      `importlib.util.find_spec("raypoolkit").submodule_search_locations`) with
      `git -C /Users/ds283/Documents/Code/RayPoolKit archive v0.2.0 raypoolkit`, extracted into a
      new directory outside both repositories:
      - every `.py` file the archive holds outside `raypoolkit/tests/` is installed, byte for byte
        (at the tag: `__init__.py`, `RayWorkPool.py`, `_timing.py`, `contract.py`);
      - `raypoolkit/tests/` is not installed;
      - nothing else `.py` is installed. Ignore `__pycache__`.

      Show the file counts and the result.
   5. **The origin.** The distribution's `direct_url.json` is a VCS record at `eaef0ce6…`,
      requested `v0.2.0`, with no `dir_info`. No `.pth`, `.egg-link` or `__editable__` file in the
      venv names RayPoolKit.
   6. **The import.** `./venv/bin/python -c "import ray; import raypoolkit; from raypoolkit import
      RayWorkPool; print(ray.is_initialized())"` prints `False`. Import nothing else, and start no
      Ray.
5. **The suites** (`.claude/rules/test-selection.md`; the diff touches none of its slow paths): the
   default and `integration` runs give 01's counts. Nothing imports the package yet, so nothing may
   move.

---

## 3. Acceptance

1. **K1:** `git diff` of `requirements.txt` is the one added line, in sorted position.
2. **K2–K3:** every check of §2 holds, and each is shown in the results note.
3. The default and `integration` runs give 01's counts.
4. **No deliberate breakage** (README §5 rule 8): 03 adds no code and no test. §2.4's checks are its
   proof; each is a check a wrong install would fail.
5. **The records**, in the same commit:
   - this board's §1 row for 03, items K1–K3, and `### 5.7 After prompt 03 (<date>)`, naming the
     rollback: `git revert` plus `./venv/bin/pip uninstall -y raypoolkit` (README §4.4);
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

---

## 4. Stop conditions — stop and ask

- `pip freeze` before the install differs from `7bb3efd-pip-freeze.txt`.
- The dry run, or the install, would change, upgrade or add any distribution but `raypoolkit`, or
  `pip check` reports a broken requirement. **Stop before accepting any such change.** If pip has
  already moved something, record exactly what, restore it from the saved `pip freeze`, and stop.
- The installed commit is not `eaef0ce6…`, the installed files differ from the tag's, or the install
  is editable.
- The install cannot reach GitHub. Do not substitute a local path, a wheel built from the checkout,
  or an editable install.
- Any suite's count or result moves.

---

## 5. What this prompt does not do

- **Files it changes:** `requirements.txt`, the results note and this board. Nothing else.
- It imports the package from no SI file, and deletes nothing. `RayTools/` is 04's.
- It changes nothing in RayPoolKit.
- It does not pin `datastorekit`, which is 08's.

---

## 6. The results note

`.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md`, using README §5.1. It holds:
- every check of §2, with its command and output;
- pip's dry-run and install output, abridged to what it collected, built and installed;
- the two suites beside 01's counts.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
