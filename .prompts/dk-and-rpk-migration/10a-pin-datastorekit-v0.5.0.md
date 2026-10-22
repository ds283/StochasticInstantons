# Prompt 10a — pin `datastorekit` `v0.5.0`

**Campaign:** [`README.md`](README.md) · **Board items:** **K8**–**K11** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-22, with prompt 10b, after 10's review and the user's ruling **U12** (README
§6.1; board §5.25). Measured at `f5f395b`: no line of SI's code has changed since 10's commit
`e2c7b22`.
**Gate:**
- 10 landed and reviewed (board §1); the brief
  [`datastorekit-second-value-table-brief.md`](datastorekit-second-value-table-brief.md) answered by
  `v0.5.0` (README §0.6);
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no SI cluster is up (`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`);
- the venv holds `datastorekit` 0.4.0 at `c8570e849334…` and `raypoolkit` 0.2.0 at `eaef0ce6…`,
  neither editable; no other session runs a suite from this venv, or installs into it, while 10a
  runs.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Sonnet**. One line of `requirements.txt` changed and an install, measured
closely, as 08.
**Needs the network**: the install fetches the tag from GitHub. The orchestrator dispatches this
prompt with that permission.

**Read first:**

1. [`README.md`](README.md): §0.5, **§0.6** (the release, U12), §2.2 (10a's charter), §4.4 (rollback)
   and §5 (rules 11–13).
2. **Prompt 08 and its results note**, `.documents/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md`.
   10a is 08 again for the next release; its checks are 08's, with these differences: the line is
   **replaced**, not added; pip **replaces** a distribution rather than adding one; and K11 is about
   `v0.5.0`'s change, not `v0.3.0`'s.
3. DatastoreKit at `/Users/ds283/Documents/Code/DatastoreKit`, **read only; edit nothing there**
   (README §5 rule 12):
   - SI's checklist `docs/adoption/stochasticinstantons.md`, its **"Addendum: v0.5.0"** (the note SI's
     pin prompt reads), and `docs/adoption/README.md`'s `v0.5.0` addendum;
   - `docs/client-contract.md` §9.8;
   - `pyproject.toml` at the tag: only its `version` differs from `v0.4.0`'s.
4. Prompt 01's results note, for `utilities.installed_package_provenance()`.

---

## 1. What is wanted

The third pin, in a commit of its own (DatastoreKit adoption README §1; README §5 rule 13). It
changes no SI code: SI's specs declare nothing new until 10b, so every record and fingerprint of a
store read with SI's specs is what it was under `v0.4.0` (the addendum; README §0.6).

- **K8 — the pin.** `requirements.txt:16`,
  `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0`, becomes exactly:
  ```text
  datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.5.0
  ```
  No other line changes (73 lines before and after). `ray==2.55.1` and `SQLAlchemy==2.0.46` stay.
- **K9 — the install.** `./venv/bin/pip install -r requirements.txt`, from the repository root, as
  08's K5: never `-e`, never a local path to the DatastoreKit checkout, never `--upgrade`,
  `--force-reinstall` or `--no-deps`. **First a dry run**, which must report `Would install
  datastorekit-0.5.0` and nothing else; otherwise stop before installing. (The orchestrator's dry
  run of the one requirement, 2026-10-22, reported exactly that; README §0.6.)
- **K10 — the proof that the venv holds the tag.**
- **K11 — what SI needs of the release, on the installed package**, without touching SI's tree.

---

## 2. What to do

1. **Before.** Save to your scratch directory:
   - `./venv/bin/pip freeze` (83 lines, with
     `datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005`).
     If it is not 08's freeze, stop: the venv has moved;
   - `./venv/bin/pip check`;
   - the mtimes and sizes of `raypoolkit`'s installed files and dist-info, and of every installed
     `datastorekit/*.py`, so that K10 can show which were rewritten.
2. **The tag.** `git ls-remote --tags https://github.com/ds283/DatastoreKit v0.5.0 'v0.5.0^{}'`
   gives tag object `6a6809d570023ce32513deac4528e93ada4ef824` and commit
   `f47b9a255e9ad58e0d0eaf85644f53b575884d31` (README §0.6). `git -C
   /Users/ds283/Documents/Code/DatastoreKit rev-parse 'v0.5.0^{commit}'` agrees.
3. **K8**, then the dry run, then **K9**. Keep pip's full output.
4. **K10, after:**
   1. **`pip freeze`** differs from the saved one by exactly one line, replaced:
      `datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005`
      becomes
      `datastorekit @ git+https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31`.
      Show the diff. `pip check` is clean. pip itself is not upgraded.
   2. **`raypoolkit` was not reinstalled**: its files' mtimes are the saved ones.
   3. **`utilities.installed_package_provenance()["datastorekit"]`** gives version `0.5.0`, URL
      `https://github.com/ds283/DatastoreKit`, commit `f47b9a255e9a…`, requested revision `v0.5.0`,
      `editable: False`; `["raypoolkit"]` is unchanged. The line `format_package_provenance` prints
      should be
      `>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
   4. **The installed files are the tag's.** Against `git -C /Users/ds283/Documents/Code/DatastoreKit
      archive v0.5.0 datastorekit`, extracted into a new directory outside both repositories:
      - every `.py` file the archive holds outside `datastorekit/tests/` is installed, byte for byte
        (**21** at the tag, as at `v0.4.0`);
      - **exactly two differ from the saved `v0.4.0` files**, `store_inventory.py` and
        `store_fingerprint.py` (README §0.6); the other 19 are byte-equal to what was installed
        before;
      - `datastorekit/tests/` is not installed, nor its `data/` files; nothing else `.py` is
        installed. Ignore `__pycache__`.
   5. **The origin.** `direct_url.json` is a VCS record at `f47b9a255e9a…`, requested `v0.5.0`, with
      no `dir_info`. No `.pth`, `.egg-link` or `__editable__` file names DatastoreKit. No
      `datastorekit-0.4.0.dist-info` is left.
   6. **The import.** `./venv/bin/python -c "import ray; import datastorekit; from
      datastorekit.SQL.ShardedPool import ShardedPool; print(ray.is_initialized())"` prints
      `False`; `./venv/bin/python -m datastorekit.tools.sharded_store --help` exits 0. Start no
      Ray.
5. **K11**, a throwaway script in your scratch directory, never in the repository, importing the
   installed package (print `datastorekit.store_inventory.__file__`: it must be in the venv's
   `site-packages`), with SI's root put on `sys.path` by the script:
   - `InventorySpec` has a field `extra_values`, defaulted to an empty mapping; `Record` a field
     `extra_value_counts`, defaulted empty; `datastorekit.store_fingerprint.ENCODING_FORMAT == 1`;
   - a `Record` with `extra_value_counts` empty has `as_json()` keys exactly `key`, `tags`,
     `validated`, `value_count`; with one entry, those and `extra_value_counts`;
   - `inventory_classes(config.datastore.factories)` gives SI's 24 classes in 10's order, unchanged;
   - a copy of SI's registry whose `GradientCoupledInstanton` spec names
     `GradientCoupledInstantonProfile` in both `values` and `extra_values` raises `ValueError` from
     `inventory_classes`, naming the class and the table (do it by wrapping the entry's
     `inventory_spec` in the script, with `dataclasses.replace`; edit no SI file);
   - **U5 does not move**: `config.datastore.tables_to_drop` over all 31 non-empty sets of the five
     drop groups gives 10 closed and 21 refused, with the messages `tests/test_tables_to_drop.py`
     pins (the test is the check; run it).
6. **The suites** (`.claude/rules/test-selection.md`; the diff touches none of its slow paths): the
   default and `integration` runs give 10's counts, **730 (729 passed, 1 skipped)** and **67 (66
   passed, 1 skipped)**:
   ```bash
   ./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider
   RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider
   ```
   The orchestrator ran both against the tag's package before writing this prompt (on
   `PYTHONPATH`, the installed package untouched) and got exactly these (README §0.6). Nothing in SI
   declares the new field, so nothing may move.

---

## 3. Acceptance

1. **K8:** `git diff` of `requirements.txt` is the one line replaced, in place.
2. **K9–K11:** every check of §2 holds, and each is shown in the results note, K11's script whole.
3. The default and `integration` runs give 10's counts.
4. **No deliberate breakage** (README §5 rule 8): 10a adds no code and no test. §2.4's and §2.5's
   checks are its proof; each is one a wrong install, or a release without the field, would fail.
5. **The records**, in the same commit:
   - this board's §1 row for 10a, items K8–K11, and `### 5.N After prompt 10a (<date>)`, N the next
     free number in §5, naming the rollback: `git revert` **plus** reinstalling `v0.4.0`
     (`./venv/bin/pip install -r requirements.txt` after the revert, which pip resolves to
     `c8570e84…`), README §4.4;
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

---

## 4. Stop conditions — stop and ask

- `pip freeze` before the install is not 08's (§2.1).
- The dry run, or the install, would change, upgrade or add any distribution but `datastorekit`, or
  `pip check` reports a broken requirement. **Stop before accepting any such change.** If pip has
  already moved something, record exactly what, restore it from the saved `pip freeze`, and stop.
- The installed commit is not `f47b9a255e9a…`, the installed files differ from the tag's, more than
  the two named modules differ from `v0.4.0`'s, or the install is editable.
- Any K11 check fails. **Do not work around it in SI** (README §5 rule 11): it is a finding about the
  release.
- The install cannot reach GitHub. Do not substitute a local path, a wheel built from the checkout,
  or an editable install.
- Any suite's count or result moves.

---

## 5. What this prompt does not do

- **Files it changes:** `requirements.txt`, the results note and this board (and
  `.documents/OPEN-ISSUES.md` if an issue opens). Nothing else.
- It declares nothing new in any spec; that is 10b's.
- It changes nothing in DatastoreKit, RayPoolKit, ChamPBH or SecondaryGWKit.

---

## 6. The results note

`.documents/dk-and-rpk-migration/10a-pin-datastorekit-v0.5.0.md`, using README §5.1. It holds:
- every check of §2, with its command and output, and K11's script whole;
- pip's dry-run and install output, abridged to what it collected, built, uninstalled and
  installed;
- the two suites beside 10's counts;
- "State handed to the next prompt": the provenance line every driver now prints, and the counts
  10b starts from.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
