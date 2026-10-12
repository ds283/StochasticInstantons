# Prompt 04 — adopt `raypoolkit`

**Campaign:** [`README.md`](README.md) · **Board items:** **W1**–**W5**; gate **RayPoolKit G4** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-12, with prompts 01–03, after the user's rulings (README §6.1).
**Gate:**
- 03 landed and reviewed (board §1), and the venv holds `raypoolkit` 0.2.0 at `eaef0ce6…`, not
  editable (`utilities.installed_package_provenance()`);
- on branch `dk-and-rpk-migration`, no tracked change in `git status`.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Sonnet**. Two files deleted, three imports rewritten, seven lines of
`main.py` simplified, and a handful of documentation lines corrected, each measured.

**`RayTools/` and `CLAUDE.md` are named here.** `RayTools/` is on `CLAUDE.md`'s protected list
(`CLAUDE.md:95`), and RayPoolKit's decision U5 forbids editing it until SI adopts. **This prompt
deletes it**, and changes the protected list's line that names it. Nothing else on that list is
touched.

**Read first:**

1. [`README.md`](README.md): §0.1 (item 10), §2.2 (04's charter), §4.4, §5, and §6.2 (P7, P13,
   P14).
2. RayPoolKit's adoption checklist for SI, `/Users/ds283/Documents/Code/RayPoolKit/docs/adoption/stochasticinstantons.md`,
   in full. Items 2–9 are this prompt's facts at `7bb3efd`, and its appendix is the script's
   output there. Also read its `docs/adoption/README.md` §2 (the module map) and §6. **Read; edit
   nothing in that repository** (README §5 rule 12).
3. RayPoolKit's `README.md` at the tag (`git -C <RayPoolKit> show v0.2.0:README.md`): "Changes in
   `v0.2.0`", "The constructor", "Which handlers a pool needs" and "The printed lines are part of the
   interface".
4. `RayTools/RayWorkPool.py`, which you delete:
   - `_default_store_handler` (`:79-80`);
   - the constructor (from `:84`), whose `store_handler` default is that function (`:94`).

   SI's copy already has the store/persist split that `v0.2.0` has (checklist "In one paragraph"),
   so the documents' account of the handlers stays true.
5. ChamPBH's 04, as done (read only): its board §5.5 and the review below it, in
   `/Users/ds283/Documents/Code/ChamPBH/prompts/dk-and-rpk-migration/IMPLEMENTATION_STATE.md`. Its
   throwaway commit was made with `git commit-tree` on no branch, which left no branch behind.

---

## 1. What is wanted

SI's `RayTools/RayWorkPool.py` is replaced by the packaged `raypoolkit.RayWorkPool`. By the
checklist (item 4), every one of SI's 16 constructions constructs under `v0.2.0` as it stands. So
the change is a deletion, three imports, and the removal of a private name.

- **W1 — delete `RayTools/`:** `RayTools/RayWorkPool.py` and `RayTools/__init__.py`.
  - With them goes the copy's `from Datastore.SQL.ShardedPool import ShardedPool`
    (`RayTools/RayWorkPool.py:23`), so DatastoreKit's rewrite list loses one line and no U12
    exception is needed (README U1).
  - `utilities.format_time`, which the copy imports (`:24`), stays SI's.
- **W2 — rewrite the three imports** to `from raypoolkit import RayWorkPool`:
  - `main.py:45`, which also imports `_default_store_handler` (W3);
  - `plot_GradientCoupledSolutions.py:100`;
  - `plot_InstantonSolutions.py:72`.

  These are the lines at `7bb3efd`; 01's provenance line has moved some since. Re-measure first
  (§2.1). If the script finds any other import, string literal or `import_module` naming
  `RayTools`, stop.
- **W3 — drop `_default_store_handler`** (RayPoolKit checklist item 3, option (a); README §0.1
  item 10). It is the copy's private name, and what `main.py` passes is the default: the package's
  `store_handler` defaults to `obj.store()`, as the copy's does. Seven lines change:
  1. the import at `main.py:45` keeps `RayWorkPool` only;
  2. `_run_instanton_queue` stops taking `store_handler` (its parameter at `:408`);
  3. and stops passing it to its `RayWorkPool` (`store_handler=store_handler,` at `:497`);
  4. its three callers stop passing it (`store_handler=_default_store_handler,` at `:664`, `:824`
     and `:848`);
  5. the construction at `:1092` loses `store_handler=_default_store_handler,` (`:1097`).

  Every other argument of those calls stays as it is, in place. The two other compute sites
  (`main.py:383`, `:718`) pass handlers of SI's own (`pipeline_store_handler`,
  `inflaton_trajectory_store_handler`) and are not touched.
- **W4 — change no other pool site** (P7). The 12 lookup-only sites keep
  `store_handler=None, persist_handler=None`. `git diff` of the two plot scripts is the one import
  line each.
- **W5 — the prose this commit makes false** (P13). These are the checklist's item 9 advice, and
  every one is a line that names the copy's file:
  - `CLAUDE.md:95`, the protected list. `RayTools/` leaves it, and `Datastore/SQL/ShardedPool.py`,
    which shares the line, stays. If the list's layout needs a line said otherwise, keep its
    two-column form. Add nothing else; 12 rewrites the section.
  - `.claude/rules/ray-dispatch.md:99-106`, "Why `RayWorkPool` requires plain classes". It names
    `RayTools/RayWorkPool.py` and the copy's lines 354, 436 and 393.
    - Name the package instead: `raypoolkit.RayWorkPool`, pinned in `requirements.txt`.
    - Cite the same three behaviours at the package's lines, read at the tag (`git -C <RayPoolKit>
      show v0.2.0:raypoolkit/RayWorkPool.py`), or describe them without line numbers.
    - The rule's argument is unchanged.
  - `.documents/FILE_MAP.md:31` and `:287`, the copy's two rows of the file map.
  - `.documents/INFRASTRUCTURE.md:353`, "`RayTools/RayWorkPool.py` drives every compute stage".
  - `.documents/architecture-summary.md:27-28` (the layout's `RayTools/` entry) and `:321`
    ("`RayTools/RayWorkPool.py` provides…").

  Say in each place that the queue is the `raypoolkit` package, pinned in `requirements.txt`, and
  change nothing else in those documents. Leave as they are:
  - the lines the checklist lists as staying true;
  - the dated records it names, such as
    `.documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md:75`;
  - every line under `.prompts/`.

---

## 2. What to do

### 2.1 Before

1. **Re-measure**, from RayPoolKit's root with its own venv:
   ```bash
   ./venv/bin/python docs/adoption/measure_client_pools.py si --commit <SI HEAD's hash>
   ```
   - Expect, as at `7bb3efd` ([`measure/out/7bb3efd-raypoolkit-measure_client_pools.md`](measure/out/7bb3efd-raypoolkit-measure_client_pools.md)):
     3 imports (1 naming a private name), 0 string literals, 0 `import_module` calls, and 16 calls,
     every one "constructs", with 5 flags on 4 calls.
   - The line numbers differ by what 01's provenance lines moved.
   - Save the output. Show its difference from the `7bb3efd` appendix, and explain each line of it.
2. `git grep -n -e RayTools -e _default_store_handler -- ':!.prompts' ':!.documents' ':!.claude'
   ':!CLAUDE.md'` lists only `RayTools/` itself, the three imports and the five uses of W3.

### 2.2 The change

W1–W5, as §1 says. `git rm` the two files. Do not reformat any file you touch: the diff is only the
lines §1 names (README §5 rule 15).

### 2.3 Verification

1. **By RayPoolKit's script, at a commit of the staged tree.**
   - Make a throwaway commit of the staged change with `git commit-tree` on no branch (never on
     `dk-and-rpk-migration`), and run the script at it.
   - It reports 0 imports, 0 string literals and 0 `import_module` calls naming `RayTools`; no
     private name imported; 16 calls, every one "constructs"; and `RayTools/` absent.
   - Save the output.
   - **The flags.** The script still flags the non-literal sizes (`MAX_INFLIGHT_PIPELINE`,
     `MAX_INFLIGHT_PIPELINE_UNIFIED`, `len(traj_payloads)`). Check each by hand, as the checklist's
     item 4 does. Show that `main.py`'s model list is still never empty, by the same reading of
     `config/model_list.py`, so that `len(traj_payloads)` is at least 1.
2. `git ls-tree <that commit> RayTools` is empty.
3. **The imports resolve, without running a driver.** A short script, kept in the results note:
   - parses each of the three drivers with `ast`;
   - for every `import` and `from … import` in them, finds the module with
     `importlib.util.find_spec`;
   - and for a `from` import, checks that the name is an attribute of the imported module.

   Every one resolves. It never executes a driver (`main.py` calls `ray.init` at import), and it
   reports `ray.is_initialized()` as `False` at its end.
4. `./venv/bin/python -m py_compile main.py plot_InstantonSolutions.py
   plot_GradientCoupledSolutions.py` succeeds.
5. **W3, by `ast`.** In `main.py`:
   - no `store_handler` keyword is passed anywhere but at the two compute sites W3 leaves (`:383`,
     `:718`) and the 12 lookup-only sites (`None`);
   - `_run_instanton_queue`'s parameters are those at `7bb3efd` less `store_handler`.
6. **The suites** (`.claude/rules/test-selection.md`; the diff touches none of its slow paths): the
   default and `integration` runs give 03's counts. No test names `RayTools` or `RayWorkPool`
   (checklist item 6). The integration run is the first through the package under Ray: it
   constructs no `RayWorkPool`, but it imports nothing from `RayTools/` either.

### 2.4 Deliberate breakage (README §5 rule 8)

Each is applied to the working tree, shown to be caught, reverted, and recorded as a diff that
`git apply` replays:
1. `main.py`'s import reverted to `from RayTools.RayWorkPool import RayWorkPool`. §2.3.3 fails (the
   module is gone), and the script at a throwaway commit reports one import.
2. `plot_InstantonSolutions.py`'s import misspelled as `from raypoolkit import RayWorkPoool`.
   §2.3.3 fails on the name.
3. `from raypoolkit.RayWorkPool import _default_store_handler` restored in `main.py`. The script
   reports a private name, and §2.3.5's check is unaffected; record exactly what each says.
4. `raypoolkit` made unavailable without uninstalling it (`sys.modules["raypoolkit"] = None` in the
   import-check script). All three drivers' imports fail.

---

## 3. Acceptance

1. **W1:** `RayTools/` is gone, at the commit.
2. **W2–W4:** `git diff` of the two plot scripts is the one import line each. That of `main.py` is
   the import and W3's six other lines, and nothing else.
3. **By RayPoolKit's script:** §2.3.1's figures, the flags checked by hand.
4. **The imports resolve** (§2.3.3), the drivers byte-compile (§2.3.4), and §2.3.5 holds.
5. **The suites** give 03's counts.
6. **W5:** `git diff` of `CLAUDE.md`, `.claude/rules/ray-dispatch.md` and the three documents
   touches only the lines §1 names. Each corrected statement agrees with the package at `v0.2.0`.
7. **The breakages of §2.4** are caught, and recorded as diffs.
8. **RayPoolKit's G4** is recorded on this board as holding, by its checklist item 8, items 1–5:
   1. `RayTools/` is gone;
   2. no import of it, and none of `_default_store_handler`, by the script;
   3. the pin is in `requirements.txt`, and the venv is installed from it (03);
   4. the suites pass;
   5. every site constructs, 16 found.

   Item 6, the record on RayPoolKit's own extraction board, is a commit in that repository,
   drafted at 12 (P14). RH1 (07) adds the run under real Ray.
9. **The records**, in the same commit:
   - this board's §1 row for 04, items W1–W5, the RayPoolKit G4 row of §2, and
     `### 5.8 After prompt 04 (<date>)`;
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

---

## 4. Stop conditions — stop and ask

- The re-measure (§2.1) finds something the checklist does not:
  - an import, string literal or `import_module` naming `RayTools`;
  - a call whose verdict is not "constructs";
  - a number of calls other than 16.
- A site turns out to need a change to construct, or to keep its behaviour. P7 and the checklist say
  none does; if one does, that is a finding about the package or the checklist.
- `_default_store_handler` turns out not to be the default: a site whose behaviour would change
  without it.
- An import does not resolve, or any suite's count or result moves.
- A defect in `raypoolkit` itself: it is not patched or worked around here (README §5 rule 11).

---

## 5. What this prompt does not do

- **Files it changes:**
  - it deletes `RayTools/RayWorkPool.py` and `RayTools/__init__.py`;
  - the import line in each of the three drivers, and W3's lines in `main.py`;
  - `CLAUDE.md:95`, `.claude/rules/ray-dispatch.md:99-106`, and the lines of `FILE_MAP.md`,
    `INFRASTRUCTURE.md` and `architecture-summary.md` that §1 names;
  - the results note and this board.

  Nothing else.
- It touches no `Datastore/` file: `RayTools/RayWorkPool.py:23`'s layer import is deleted with the
  file, not rewritten.
- It runs no build and starts no Ray cluster. The run under real Ray is 07's.
- It changes nothing in RayPoolKit.

---

## 6. The results note

`.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md`, using README §5.1. It holds:
- the re-measure and the measure at the throwaway commit, with their difference from the `7bb3efd`
  appendix;
- the hand-check of the flags;
- the import-resolution script and its output;
- the deliberate-breakage record, as diffs;
- the two suites beside 03's counts;
- **the text of the RayPoolKit G4 record**, for 12 to carry into its draft for RayPoolKit's board.

**One commit**, in the repository's form, staged by explicit path only (`git rm` for the two
deletions), after showing `git diff --cached --name-only`.
