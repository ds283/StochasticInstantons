# Prompt 08 — pin `datastorekit` `v0.4.0`

**Campaign:** [`README.md`](README.md) · **Board items:** **K4**–**K7** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-21, with prompts 09–11, after 07's review (board §5.19).
**Gate:**
- 07 landed and reviewed (board §1); gate RH1 holds in board §2, and the tag `pre-datastorekit` is
  on `origin`, peeling to `0527480`;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no SI cluster is up (`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`);
- the venv holds `raypoolkit` 0.2.0 at `eaef0ce6…` and no `datastorekit`.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Sonnet**. One line of `requirements.txt` and an install, measured
closely, as 03.
**Needs the network**: the install fetches the tag from GitHub. The orchestrator dispatches this
prompt with that permission.

**Read first:**

1. [`README.md`](README.md): §0.4, §0.5 (the release and why `v0.4.0`, U10), §2.2 (08's charter),
   §4.4 (rollback) and §5 (rules 11–13).
2. **Prompt 03 and its results note**, `.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md`.
   08 is 03 again for the other package, and its checks are 03's with the names changed.
3. DatastoreKit at `/Users/ds283/Documents/Code/DatastoreKit`, **read only; edit nothing there**
   (README §5 rule 12):
   - `docs/adoption/README.md` §1 ("The release and the pin") and §3 ("What the wheel does not
     ship");
   - SI's checklist `docs/adoption/stochasticinstantons.md`, the addenda for `v0.2.3`, `v0.3.0`
     and `v0.4.0`;
   - `pyproject.toml` at the tag (`git -C <DatastoreKit> show v0.4.0:pyproject.toml`). It declares
     `ray>=2.43` and `sqlalchemy>=2.0.39,<2.1`, both already satisfied by SI's pins (`ray==2.55.1`,
     `SQLAlchemy==2.0.46`), and `packages.find` excludes `datastorekit.tests`.
4. ChamPBH's 07, as done (read only): its board §5.12 and the review below it, in
   `/Users/ds283/Documents/Code/ChamPBH/prompts/dk-and-rpk-migration/IMPLEMENTATION_STATE.md`. It
   pinned `v0.3.0` and found what 03 found: pip's `Resolved … to commit` names the **tag object**,
   and `raypoolkit` is re-resolved, not reinstalled.
5. Prompt 01's results note, for `utilities.installed_package_provenance()`.

---

## 1. What is wanted

The second pin, in a commit of its own (DatastoreKit adoption README §1; README §5 rule 13).
Nothing in SI imports the package until 09.

- **K4 — the pin.** `requirements.txt` gains exactly this line:
  ```text
  datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0
  ```
  - In sorted position, case-insensitive, as 03's: between `cycler==0.12.1`
    (`requirements.txt:15` at `91e6f31`) and `distlib==0.4.3` (`:16`).
  - No other line changes. `ray==2.55.1` and `SQLAlchemy==2.0.46` stay (README §5 rule 13).
- **K5 — the install.** `./venv/bin/pip install -r requirements.txt`, from the repository root, as
  03's K2: never `-e`, never a local path to the DatastoreKit checkout, never `--upgrade`,
  `--force-reinstall` or `--no-deps`. **First a dry run**, which must report only `datastorekit`
  to be installed; otherwise stop before installing.
- **K6 — the proof that the venv holds the tag.**
- **K7 — what SI needs of the release, on the installed package** (U3, and `v0.2.3`'s factory
  base), without touching SI's tree.

---

## 2. What to do

1. **Before.** Save to your scratch directory:
   - `./venv/bin/pip freeze`. It must equal `measure/out/7bb3efd-pip-freeze.txt` plus exactly one
     line, 03's `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`
     (82 lines). If it differs otherwise, stop: the venv has moved;
   - `./venv/bin/pip check`;
   - `./venv/bin/pip show datastorekit`, which must find nothing;
   - the mtimes of `raypoolkit`'s installed files and dist-info, so that K6 can show it was not
     reinstalled.
2. **The tag.** `git ls-remote --tags https://github.com/ds283/DatastoreKit v0.4.0 'v0.4.0^{}'`
   gives tag object `8e7c1d77b3792b57b98983e84b99fc68ab88cb89` and commit
   `c8570e849334d09085bbd84876095fc9e22bd005` (README §0.5). `git -C
   /Users/ds283/Documents/Code/DatastoreKit rev-parse 'v0.4.0^{commit}'` agrees.
3. **K4**, then the dry run, then **K5**. Keep pip's full output.
4. **K6, after:**
   1. **`pip freeze`** differs from the saved one by exactly one added line:
      `datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005`.
      Show the diff. `pip check` is clean.
   2. **`raypoolkit` was not reinstalled**: its files' mtimes are the saved ones.
   3. **`utilities.installed_package_provenance()["datastorekit"]`** gives version `0.4.0`, URL
      `https://github.com/ds283/DatastoreKit`, commit `c8570e849334…`, requested revision
      `v0.4.0`, `editable: False`; `["raypoolkit"]` is unchanged. Show the line
      `format_package_provenance` prints. It should be
      `>> packages: datastorekit 0.4.0 (https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005, requested v0.4.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
   4. **The installed files are the tag's.** Compare the installed `datastorekit/` with
      `git -C /Users/ds283/Documents/Code/DatastoreKit archive v0.4.0 datastorekit`, extracted into
      a new directory outside both repositories:
      - every `.py` file the archive holds outside `datastorekit/tests/` is installed, byte for
        byte (**21** at the tag, `datastorekit/store_fingerprint.py` among them);
      - `datastorekit/tests/` is not installed, nor its `data/` files (four JSON files at the tag,
        the fingerprint's golden file among them);
      - nothing else `.py` is installed. Ignore `__pycache__`.
   5. **The origin.** `direct_url.json` is a VCS record at `c8570e849334…`, requested `v0.4.0`,
      with no `dir_info`. No `.pth`, `.egg-link` or `__editable__` file names DatastoreKit.
   6. **The import.** `./venv/bin/python -c "import ray; import datastorekit; from
      datastorekit.SQL.ShardedPool import ShardedPool; print(ray.is_initialized())"` prints
      `False`; `./venv/bin/python -m datastorekit.tools.sharded_store --help` exits 0. Start no
      Ray.
   7. **Nothing in SI names the package yet.** `git grep -n datastorekit -- '*.py'` outside
      `.prompts/` and `.documents/` finds the four files that name it as a string, as at
      `91e6f31`: `utilities.py` (the provenance helper), `tools/compare_stores.py` (its docstring: it
      never reads through the package), `tests/test_package_provenance.py` and
      `tests/test_rehearsal_stage_counts.py`. None imports it.
5. **K7**, a throwaway script in your scratch directory, never in the repository, run with
   `./venv/bin/python` from that directory so that nothing of SI's tree is on `sys.path` but what
   you put there. It imports the installed package (print `datastorekit.__file__`: it must be in
   the venv's `site-packages`):
   - **U3** (`v0.3.0`'s change, carried into `v0.4.0`):
     - `datastorekit.DatastoreObject(1, timestamp=t)` reads `t` back from `.timestamp`;
     - without the argument, `.timestamp` is `None`;
     - assigning to `.timestamp` raises `AttributeError`;
     - `datastorekit.DatastoreObject(1, t)` raises `TypeError` (keyword-only, README §0.4);
   - **the factory base** (`v0.2.3`'s change): a subclass of
     `datastorekit.SQL.factory_base.SQLAFactoryBase` defining only `register` and `build`
     instantiates; one without `build` raises `TypeError` naming it;
   - **SI's 30 registry entries on the installed base.** Without editing SI: for each class in
     `config.datastore.factories` (imported with the layer first, as
     `tests/test_config_datastore.py` does), build a class of the same name from the class's own
     `vars()` (less `__dict__` and `__weakref__`) with the installed `SQLAFactoryBase` as its only
     base, and instantiate it as the registry does (`config/datastore.py:103-134`: the three
     `sqla_dimensionful_quantity_factory` entries and the one `sqla_dimensionless_quantity_factory`
     entry take their held class, `inflaton_mass`, `phi_value`, `pi_value`, `quartic_coupling`).
     All 30 must instantiate (28 classes). Report how many of SI's factory classes
     define all of `store`, `validate` and `validate_on_startup`, and how many none (ChamPBH's 07
     did the same; its K7 script is in its log 07).
6. **The suites** (`.claude/rules/test-selection.md`; the diff touches none of its slow paths):
   the default and `integration` runs give 07's counts, **696 (695 passed, 1 skipped)** and **62
   (61 passed, 1 skipped)**:
   ```bash
   ./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider
   RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider
   ```
   Nothing imports the package yet, so nothing may move.

---

## 3. Acceptance

1. **K4:** `git diff` of `requirements.txt` is the one added line, in sorted position.
2. **K5–K7:** every check of §2 holds, and each is shown in the results note, K7's script whole.
3. The default and `integration` runs give 07's counts.
4. **No deliberate breakage** (README §5 rule 8): 08 adds no code and no test. §2.4's and §2.5's
   checks are its proof; each is one a wrong install, or a release without U3, would fail.
5. **The records**, in the same commit:
   - this board's §1 row for 08, items K4–K7, and `### 5.N After prompt 08 (<date>)`, N the next
     free number in §5, naming the rollback: `git revert` **plus** `./venv/bin/pip uninstall -y
     datastorekit` (README §4.4);
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

---

## 4. Stop conditions — stop and ask

- `pip freeze` before the install is not 03's (§2.1).
- The dry run, or the install, would change, upgrade or add any distribution but `datastorekit`, or
  `pip check` reports a broken requirement. **Stop before accepting any such change.** If pip has
  already moved something, record exactly what, restore it from the saved `pip freeze`, and stop.
- The installed commit is not `c8570e849334…`, the installed files differ from the tag's, or the
  install is editable.
- Any K7 check fails, or any of the 30 entries does not instantiate on the installed base. **Do not
  work around it in SI** (README §5 rule 11): it is a finding about the release.
- The install cannot reach GitHub. Do not substitute a local path, a wheel built from the checkout,
  or an editable install.
- Any suite's count or result moves.

---

## 5. What this prompt does not do

- **Files it changes:** `requirements.txt`, the results note and this board (and
  `.documents/OPEN-ISSUES.md` if an issue opens). Nothing else.
- It imports the package from no SI file, and deletes nothing. The layer is 09's.
- It changes nothing in DatastoreKit, RayPoolKit, ChamPBH or SecondaryGWKit.

---

## 6. The results note

`.documents/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md`, using README §5.1. It holds:
- every check of §2, with its command and output, and K7's script whole;
- pip's dry-run and install output, abridged to what it collected, built and installed;
- the two suites beside 07's counts;
- "State handed to the next prompt": the provenance line every driver now prints, and the counts
  09 starts from.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
