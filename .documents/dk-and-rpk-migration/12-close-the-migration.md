# Close the migration (prompt 12 of dk-and-rpk-migration)

**Subject:** the campaign's close. `CLAUDE.md`, the rules and the architecture documents now describe the two
packages; the prose in code that cited a deleted layer is corrected; the final measurements are taken; each
package's gate record is drafted for its own board; and P2 has its handover.
**Commit:** `ae4f489`, on branch `dk-and-rpk-migration`, on `47c0a77` (the orchestrator's note for 12; code
unchanged since `18b490a`). **Result:** complete. Y1–Y7 hold. No build ran, no store was opened, no Ray cluster
was started, nothing was installed, and nothing was changed outside this repository. The suites give 732 / 67 / 69
before and after, and the `ast` of every touched Python file is unchanged but for two strings.

## What shipped

Dispatched with the orchestrator's brief, which held twelve corrections to the prompt; each is applied
(see "The brief's twelve corrections" below). Counts are those of the closing runs
(`measure/out/12-suites.md`).

### Y1 — `CLAUDE.md`

- **Build and test.** "~464 of 571 tests" is now "732 of 868 tests; 731 pass and 1 is skipped", and the paragraph
  says what the other 136 are: the 67 `integration`-marked tests (which need a live Ray instance and a SQLite
  store, run as `RAY_ADDRESS=local pytest -m integration`) and the 69 `slow`-marked ones. The paragraph's other
  sentences are kept. This closes `[test-counts-stale-in-claude-md]`.
- **Critical rules 2, 3 and 5** stay SI's rules, worded as they were, each with one added pointer. Rule 2: the
  pool's constructor takes the table lists (DatastoreKit's client contract, §1, rows 5, 6 and 13). Rule 3: what the
  pool does with each list (§1, rows 5 and 6). Rule 5: "the value tables (every child table in the cascade map)" in
  place of a three-name list that disagreed with `validate-on-startup.md`'s six-row map; the package calls the hook
  (§3), and a child table joins a replicated owner's unit, so that the pool's prune reaches it, by declaring an
  `owner_column` (§2). The contract is pointed at, not copied.
- **Protected infrastructure.** The 13 entries are checked (each is a tracked file or directory: `git ls-files`
  finds 1 for each of the nine factory and `Quadrature` files, 5 under `Units/`, 4 under `MetadataConcepts/` and 1 for
  `utilities.py` and `constants.py`); none names a file of either package.
  The paragraph after them now begins "None of the list is a file of either package", names the datastore layer as
  `datastorekit` and `RayWorkPool` as `raypoolkit`, gives both pins (`datastorekit` `v0.5.0`, `raypoolkit`
  `v0.2.0`, installed from the tag and never editable, no copy in SI), points at the contract and at RayPoolKit's
  README ("Using it"), and states the rule in bold: a defect in either package is reported to that package's
  repository, fixed in a new release, and reaches SI by a new pin prompt; it is never patched or worked around in SI
  (with `v0.3.0` for `DatastoreObject.timestamp` and `v0.5.0` for `extra_values` as the precedents, in a clause).
  The sentences on `config/datastore.py` and on not reformatting are kept. Nothing else in `CLAUDE.md` changes.

### Y2 — `.claude/rules/`

| File | What was found | What changed |
|---|---|---|
| `test-selection.md` | `:10` "571 tests", `:26` "464 of 571" | 868 and "732 of 868 (731 pass, 1 is skipped)"; one sentence gives the other two blocks (67 `integration`, 69 `slow`, disjoint, 732 + 67 + 69 = 868) and the `RAY_ADDRESS=local` form. The `slow` table stays (see "Observations", 1) |
| `pool-read-apis.md` | `:37-39` says `config/sharding.py` is protected infrastructure; it is not | **Kept the sentence, corrected.** `config/sharding.py` is SI's own file and not on the list; adding a `read_table_config` entry still needs the user's go-ahead because it changes which tables the pool serves through `read_table` and the package refuses an entry for a class that is not replicated at open (contract §1, row 13). The sentence is not dropped because the go-ahead is the behaviour the rule exists to keep. Pointers added: contract §7 for `read_inventory` (§3, §4 for the spec); `datastorekit/SQL/ShardedPool.py:3695-3731` for `read_table` and `:3718` for the message; `:3131` and `:3441` for the replicated-first dispatch. Every statement about the package checked against the installed lines (below) and left true |
| `datastore-factories.md` | asks nothing of a new factory's `inventory_spec()`; its `validate_on_startup` sketch deletes parent rows only (rule 5 forbids that for a factory with a child table); `_do_not_populate` is said to be used by `RayWorkPool`, which neither package reads (`grep` finds it only in `main.py`) | **a new section**, "Every registered factory is covered by the inventory" (declare `inventory_spec()` and add its `EXPECTED_SPECS` row, or be read through an owner's spec in `READ_THROUGH`, or be excluded in `EXCLUDED` with a reason; `test_every_registered_class_is_placed_exactly_once` fails otherwise); the sketch gains a sentence pointing at `validate-on-startup.md` and at contract §2 and §3; `_do_not_populate` is said to be `main.py`'s Pass 1 key, read by neither package; pointers to the contract §3 (§9.5) and RayPoolKit's README for the handlers. The replication section (`:245-301` at planning) was made the package's at 09: checked against the comment above `_replicated_write` and contract §6, true, and given the pointer `datastorekit/SQL/ShardedPool.py:3147-3169` |
| `ray-dispatch.md` | "Why `RayWorkPool` requires plain classes": every line it cites in `raypoolkit/RayWorkPool.py` (`:75-76`, `:79-80`, `:385`, `:424-426`, `:471`, `:481`) read in the installed file (equal to the tag's by `cmp`): true | one pointer: the in-flight guard `:290` and the defaults 5, 1 and 200 (`:26-29`) |
| `validate-on-startup.md` | true; the `owner_column` sentence restates the contract | pointer to contract §2 and §3 |
| `compute-targets.md` | true (`available` is `_my_id is not None` in the package's `DatastoreObject`; the `label` sentence matches the README) | pointer to RayPoolKit's README for `label_builder` |
| `proxy-pattern.md`, `populate-ordering.md`, `datastore-units.md`, `spline-interpolation.md`, `matplotlib-captions.md` | read in full: no statement about either package (they speak of Ray, of SI's own `Datastore/SQL/ObjectFactories/`, and, in `datastore-units.md`, of a factory's `read_table` hook, which matches contract §3) | true, unchanged |

- **The two shard-key notes** (`.claude/memory/bug-assign-shard-keys-key-id.md` and `shard-key-assignment-bug.md`
  **at the repository root**, tracked): **neither is edited**, since each already says where the fix lives
  (correction 3). Their lines, quoted, and the installed `v0.5.0`'s at the lines they name:
  - `.claude/memory/bug-assign-shard-keys-key-id.md:26-29`: "**Status (2026-10-21, dk-and-rpk-migration prompt
    09):** that file is deleted; SI's layer is now the `datastorekit` package (`v0.4.0`), which carries the fix in
    `ShardedPool._assign_shard_keys` (`datastorekit/SQL/ShardedPool.py:3618`: the insert names `key_serial` at
    `:3674`, and the de-duplication is at `:3626`). A change to it is made in DatastoreKit and reaches SI through its
    pin."
  - `shard-key-assignment-bug.md:3-7`: "**Status (2026-10-21, dk-and-rpk-migration prompt 09):** SI no longer carries
    a `ShardedPool` of its own; its layer is the `datastorekit` package (`v0.4.0`), which carries the fix in
    `ShardedPool._assign_shard_keys` (`datastorekit/SQL/ShardedPool.py:3618`), with both of SI's commits present:
    `3f1caad`'s `key_serial` (the insert at `:3674`) and `20d9a61`'s de-duplication (`:3626`). A change to it is made
    in DatastoreKit and reaches SI through its pin (DatastoreKit's SI adoption checklist, item 10)."
  - In the installed `v0.5.0`, `ShardedPool.py:3618` is `def _assign_shard_keys(self, obj):`, `:3626` is
    `seen_store_ids = set()` and `:3674` is `{"key_serial": item.store_id, "shard_id": new_shard},`. The notes say
    "`v0.4.0`", the pin on their date: a dated record, not stale prose.

### Y3 — the documents

- **`.documents/INFRASTRUCTURE.md`** (six sections rewritten, each beginning "*Rewritten 2026-10-23 by
  dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*"):
  the title and §1 (now "whose it is": the two packages, a table of what SI supplies and what each package does,
  pointers to the contract's sections and the README); §2 (`DatastoreObject` from `datastorekit/object.py:5-38`,
  with `timestamp`, and `store_id` raising until set); §4 (the package's hooks, two abstract and six defaulted,
  and the replication paragraph, now the recorded replicated write, with the old layer's story kept as
  history); §5 (the actor, no `inventory()`); §6 (the pool, its arguments, the method table without `inventory`,
  the inventory as `read_inventory`); §9 (`RayWorkPool` with the package's defaults, 5, 1 and 200, and SI's own
  sizes marked as SI's); and §12's invariant row. §3, §7, §8, §10 and §11 are SI's own and were read, and left
  (see below).
- **`.documents/architecture-summary.md`** (five places, each dated): the layout (the packages, `config/datastore.py`,
  `tools/`, `Datastore/` as SI's factories only); the datastore layer; `RayWorkPool` (the sketch and its defaults,
  the default handlers); `main.py`'s top-level flow (`--inventory` before Ray, `tables_to_drop`, then
  `ray.init` and the pool); the inventory (`read_inventory`, `tools/inventory_report.py`); and the invariant row.
  One further correction (Deviation 1): the Pass 2 sketch's `MAX_INFLIGHT_COMPUTE = 20`.
- **`.documents/FILE_MAP.md`**: `:54`, the `SQLAFactoryBase` row, gains `inventory_spec()` (and `revalidate()` and
  `owned_serials()`, the abstract/defaulted split of contract §3 and §9.5). All 85 rows' "original path" cells were
  checked against `git ls-files` (the script is in "Verification"): every path exists.
- **Every other line** of the three files that names `RayWorkPool`, `ShardedPool`, `Datastore` or a factory hook was
  read, outside the rewritten sections: `INFRASTRUCTURE.md` §3 (the units discipline; `store()` and `build()` as SI's
  factories apply it), §7 (the two multi-table invariants), §8 (the plain-class split and the proxy pattern; "why
  `Foo` must stay a plain class" matches `raypoolkit/RayWorkPool.py:385`, README "The objects a lookup returns"),
  §10 (the two-pass dispatch), §11 (the end-to-end trace) and the other §12 rows; `architecture-summary.md`'s
  "Compute targets", "The FooProxy pattern", the `main.py` pipeline stages and two-pass sections, and the
  end-to-end trace. All are true of the packages and are left.

### Y4 — the prose in code

| File | Lines changed (`git diff -U0` hunks) | What the text said and says |
|---|---|---|
| `tools/compare_stores.py` | `@@ -39 +39,3 @@`, `@@ -93,6 +95,7 @@`, `@@ -114,3 +117,6 @@` | the docstring's "records the absolute path of each shard" now says it is the old layer's (`pre-datastorekit`, `0527480`, `ShardedPool.py:88`, `:296`) and that `datastorekit` records each shard by its bare file name (`ShardedPool.py` `_write_shard_data`); the `LAYER_TABLES` comment cites the old layer's tables at the tag and the package's `replication_in_flight` at `datastorekit/SQL/ShardedPool.py:946`, `:995`; the two `GLOBAL_BOOKKEEPING` strings cite the old layer at the tag (`Datastore.py:539-547`, `:551-552`: the old `:317`, `:639-647`, `:651-652` did not hold at the tag, see Deviation 3) and the package (`datastorekit/SQL/Datastore.py:793-805`, `:809-815`, `ShardedPool.py:3202-3203`); the `timestamp` string states the replicated case |
| `ComputeTargets/GradientCoupledInstanton/picard.py` | `@@ -452,5 +452,6 @@` | `RayTools/RayWorkPool.py` "is protected infrastructure" becomes `RayWorkPool` as the pinned `raypoolkit` package's, not SI's to patch, with no per-task timeout or cancel hook at `v0.2.0` (none in `raypoolkit/RayWorkPool.py`); the rest of the comment stays |
| `tests/test_rehearsal_stage_counts.py` | `@@ -20,2 +20,2 @@`, `@@ -23,6 +23,8 @@` | the module docstring's fixtures "are built from" lines of `RayTools/RayWorkPool.py` and SI's actor become "were built from" them at prompt 01's commit, both since replaced by the packages, whose logs the parser has read unchanged (07 for `raypoolkit`, 11 for both) |
| `Datastore/SQL/ObjectFactories/InflatonTrajectory.py` | `@@ -34 +34,2 @@`, `@@ -289 +290 @@`, `@@ -419 +420,2 @@` | "Ignored by SI's own layer; DatastoreKit reads it …" (twice) and "SI's own layer never calls it" now say what DatastoreKit reads first and that SI's old layer, at the tag, ignored / never called it |

## Deviations from the prompt

1. **`architecture-summary.md`'s Pass 2 sketch corrected** (IMPLEMENTATION CHOICE). Its `RayWorkPool(…
   max_task_queue=MAX_INFLIGHT_COMPUTE, # = 20)` and "at most 20 instanton BVPs" name a constant `main.py` does not
   have; the cap is `MAX_INFLIGHT_PIPELINE` = 50, which counts every stage's in-flight items (`main.py:55-65`).
   Read under Y3's "every other line that names `RayWorkPool`", found false, corrected minimally; it is SI's constant,
   not a package statement.
2. **`datastore-factories.md` gains two corrections beyond the new section** (IMPLEMENTATION CHOICE): the
   `_do_not_populate` sentence (neither package reads the key) and a sentence on the `validate_on_startup` sketch
   (it contradicts rule 5 for a factory with a child table). Both found by Y2's check.
3. **The old layer's `Datastore.py` line numbers did not hold at the tag** (STRUCTURALLY REQUIRED). `tools/compare_stores.py`
   cited `Datastore/SQL/Datastore.py:317`, `:639-647`, `:651-652`, which do not hold at the tag (the layer's lines had
   moved since the strings were written); at `pre-datastorekit` the
   serial lease is `:539-547` and the timestamp `:551-552` (read with `git show`), so the strings give those. The
   `ShardedPool.py` citations (`:88`, `:296`, `:244-284`, `:232-291`, `:810-821`, `:158-191`) were checked at the tag
   and hold.
4. **§2.6's order** (correction 4; STRUCTURALLY REQUIRED, known): the prompt's order fails at the tag with the
   `ImportError` below; the layer-first order imports. "§2.6 does not import" in the prompt's §4 means the
   layer-first order failing, which it does not.
5. **A scratch git repository to run RayPoolKit's script on the working tree** (IMPLEMENTATION CHOICE). The scripts
   read a commit, and 12 makes one commit at the end. To say which of Y1–Y3's edits moved the non-`.py` count, a copy
   of the tracked files was committed in a scratch repository (in the scratch directory, with `--repository`); no SI
   commit, tag or branch was made. DatastoreKit's script has no such option.
6. **Extra files under `measure/out/`** (IMPLEMENTATION CHOICE): besides the four the prompt names, the five saved
   suite outputs and `12-g4-figures-at-other-commits.md`, which carries the script figures at the other commits the
   G4 drafts name (`f4da58f`, `ef13445`, `0527480`, `2179854`, `18b490a`).
7. **Two read-only calls the prompt does not list** (IMPLEMENTATION CHOICE, harmless): `git ls-remote --tags origin`
   to confirm the tag is on `origin` (SI's own remote; nothing sent), and `du -sk` on the rehearsal root for its
   size (`lstat` only; no store file was opened).
8. **The RayPoolKit script's non-`.py` count is 421** where §1.1 says 402 (correction 2): not a stop; reported
   below with the figure outside the campaign's records.

### The brief's twelve corrections

1. The board: row 12 is `:78`, Y1–Y7 `:178-184`; the new section is `### 5.30 After prompt 12 (2026-10-23)` after
   §5.29; the list of orchestrator notes is untouched. Applied.
2. RayPoolKit's non-`.py` count, 421: reported (see "Verification"), not a stop. Applied.
3. The second memory note is `shard-key-assignment-bug.md` at the root; neither is edited; the lines are quoted
   above. Applied.
4. §2.6: layer first; the failing order's `ImportError` recorded; the handover names the order. Applied.
5. `.prompts/INDEX.md`: the row ends `2026-10-11 → 2026-10-23`; its open-issue cell `§6a; 6` becomes `§6a; 4`; the
   header counts the table (0 live, 1 halted, 5 complete). Applied.
6. `OPEN-ISSUES.md`'s counts by counting (below). Applied.
7. The rehearsal stores' path and size are in the handover (494,140 KiB, 483 MiB, by `du -sk`). Applied.
8. The suites as §2.5 says; the default run took 34–38 s, so no split. The `slow` run in the background, waited on by
   its notification, no `sleep` loop. Applied.
9. Y4's citations are the installed lines of the brief (`Datastore.py:793-805`, `:809-815`;
   `ShardedPool.py:3202-3203`), re-read. Applied.
10. The G4 drafts: DatastoreKit's replaces the second column; the italic notes are extracted from the file, and the
    `diff` is empty (below). RayPoolKit's replaces `:666`'s second column. Both are fenced blocks, identical in
    `verification.md` §4.3 and here. Applied.
11. Y3's dated notes read "*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git
    at the tag `pre-datastorekit` (`0527480`).*", once per rewritten section. Applied.
12. Y6's handover names the tag's reading order and the store path and size; the P2 issue is
    `[hfp-closed-form-audit-not-run]` (`OPEN-ISSUES.md` §2), whose row now points at the handover. Applied.

## Verification performed

### The gate, and §1.1's figures

- **Gate (board §2).** RH2 and both G4s hold (board §5.28 and its review); branch `dk-and-rpk-migration`, `HEAD`
  `47c0a77`, `git status` clean; `ray_cluster.sh status`: "lock: free (/Users/ds283/ScienceData/.rehearsal-lock does
  not exist)", "SI cluster (/tmp/ray-si): no processes", ports 6390, 6391, 8266 and 52366 free; no `gcs_server`,
  `raylet`, `ray::`, `pytest` or `main.py` process; `RAY_ADDRESS` unset. At the end the same.
- **DatastoreKit's script** (`docs/extraction/measure_client_imports.py si --commit 47c0a77`, from its root, clean at
  `2900d82`): the 7 layer modules absent (the two `__init__.py` present, empty); 201 `.py` files read, 0 unparsed;
  **0** import statements, **0** string literals, **0** `import_module` / `__import__` calls naming a layer module;
  25 factory-module imports (`config/` 22, `CosmologyConcepts/` 2, `tests/` 1). §1.1's figures exactly.
- **RayPoolKit's script** (`docs/adoption/measure_client_pools.py si --commit 47c0a77`, clean at `17029d9`):
  `RayTools/` absent; 0 imports (0 naming a private name), 0 `import_module` / `__import__` calls; **2** string
  literals, both module docstrings (`.documents/dk-and-rpk-migration/rehearsal/stage_counts.py:16`,
  `tests/test_rehearsal_stage_counts.py:16`); **16** `RayWorkPool(...)` calls, all `constructs` (12 with
  `compute_handler=None`, 4 with one; 5 flags on 4 calls, as at 04); 1 test module; `ray.is_initialized()` False.
  **Lines of non-`.py` files: 421, where §1.1 says 402.** The 19 more are in `.prompts/` (236 at `18b490a`, 255 at
  `47c0a77`: prompt 12 and the orchestrator's note). Outside the campaign's records (`prompts/`, `.prompts/`) the
  figure is 166, as at `f5b9334` (`.claude/` 18, `.documents/` 148). **Which of Y1–Y3 moved it:** on a copy of the tree
  with their edits and nothing else, 432 in all and 177 outside the records: `.claude/` +1 (`ray-dispatch.md` +2,
  `datastore-factories.md` −1), `.documents/` +9 (`INFRASTRUCTURE.md` +5, `architecture-summary.md` +4),
  `CLAUDE.md` +1. Y4 moved nothing: the two string literals are still 2. The orchestrator re-runs at 12's commit.
  The figures at the other commits the drafts name are in `measure/out/12-g4-figures-at-other-commits.md`.
- **Suites** (`measure/out/12-suites.md`; loads at start): 868 collected; default 732 (731 passed, 1 skipped), before
  at 01:45 BST, 37.98 s, load 75.5, and after at 02:02, 34.07 s, load 51.7; `integration` 67 (66 passed, 1 skipped),
  57.40 s at load 93.9, then 47.62 s at load 38.9; `slow` 69, **69 passed** in 404.36 s at load 75.7 (02:03:38 to
  02:10:24; S1's was 390.24 s); `-m "not integration"` 801; `-m "slow and integration"` none. §1.1's counts.
- **Venv:** `pip freeze` 83 lines (the saved 81, `7bb3efd-pip-freeze.txt`, plus the two packages' lines, by `diff` of
  the sorted files); `pip check` "No broken requirements found."; `direct_url.json` of each package names its tag
  and no editable install; the provenance line is 11's, verbatim (`verification.md` §4.2).

### The stale-path sweep (§2.1)

The script is the orchestrator's, copied to the scratch directory and run from the repository root as
`./venv/bin/python -I sweep.py` (74 lines; `--commit REV` reads a commit). It is reproduced here:

```python
"""Stale-path sweep for dk-and-rpk-migration prompt 12 (orchestrator note, §0).

Prints every line of every tracked file outside `.prompts/` that names a path or
name deleted by the campaign (SI's datastore layer, `RayTools/`, and the old
layer's private names), as `path:line: text`, then a summary. Lines that name
the packages (`datastorekit/...`, `datastorekit....`) are not counted.

Run from the repository root:  python -I <this file> [--commit REV]
With --commit it reads the files at that commit (git show), not the working tree.
"""

import argparse
import re
import subprocess
import sys
from collections import Counter

LAYER = r"(?:ShardedPool|Datastore|ClientPool|SerialPoolBroker|ProfileAgent)"
PATTERNS = [
    r"Datastore/object\.py",
    rf"Datastore/SQL/{LAYER}\.py",
    r"ObjectFactories/base(?:\.py)?\b",
    r"Datastore\.object\b",
    rf"Datastore\.SQL\.{LAYER}\b",
    r"RayTools",
    r"inventory_config",
    r"drop_actions",
    r"_drop_order",
    r"pool\.inventory\(",
    r"_default_store_handler",
    r"_default_serial_batch_size",
]
# Keep the packages' own paths and dotted names out: `datastorekit/SQL/ShardedPool.py`,
# `datastorekit.SQL.ShardedPool`, and `raypoolkit/...` never name a deleted file.
REGEX = re.compile(r"(?<![A-Za-z_./])(?:" + "|".join(PATTERNS) + r")")


def files(commit):
    args = ["git", "ls-files"] if commit is None else ["git", "ls-tree", "-r", "--name-only", commit]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout.splitlines()
    return [f for f in out if not f.startswith(".prompts/")]


def text(path, commit):
    if commit is None:
        with open(path, "rb") as fh:
            data = fh.read()
    else:
        data = subprocess.run(["git", "show", f"{commit}:{path}"], capture_output=True, check=True).stdout
    if b"\0" in data:
        return None
    return data.decode("utf-8", errors="replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", default=None)
    a = ap.parse_args()
    per_file = Counter()
    for f in files(a.commit):
        t = text(f, a.commit)
        if t is None:
            continue
        for n, line in enumerate(t.splitlines(), 1):
            if REGEX.search(line):
                per_file[f] += 1
                print(f"{f}:{n}: {line.strip()[:160]}")
    print(f"== {sum(per_file.values())} lines in {len(per_file)} files", file=sys.stderr)
    for f, c in sorted(per_file.items()):
        print(f"   {c:4d}  {f}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

**Before any edit**, at `47c0a77`: **246 lines in 21 files**, exactly §1.1's (the non-vacuity):

```text
== 246 lines in 21 files
      1  .claude/memory/bug-assign-shard-keys-key-id.md
      1  .claude/rules/pool-read-apis.md
      4  .documents/INFRASTRUCTURE.md
      1  .documents/OPEN-ISSUES.md
      6  .documents/architecture-summary.md
      8  .documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md
      1  .documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md
     70  .documents/dk-and-rpk-migration/04-adopt-raypoolkit.md
     55  .documents/dk-and-rpk-migration/05-move-si-data-out-of-the-layer.md
     22  .documents/dk-and-rpk-migration/06-prepare-the-inflaton-trajectory-factories.md
      3  .documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md
      1  .documents/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md
     49  .documents/dk-and-rpk-migration/09-adopt-datastorekit.md
     10  .documents/dk-and-rpk-migration/10-port-the-inventory.md
      1  .documents/dk-and-rpk-migration/rehearsal/stage_counts.py
      1  .documents/dk-and-rpk-migration/verification.md
      1  .documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md
      1  ComputeTargets/GradientCoupledInstanton/picard.py
      4  tests/test_config_datastore.py
      2  tests/test_rehearsal_stage_counts.py
      4  tools/compare_stores.py
```

The 24 lines that are not dated records (17 to change, 7 that stay), verbatim:

```text
.claude/memory/bug-assign-shard-keys-key-id.md:24: Fixed 2026-06-20: `Datastore/SQL/ShardedPool.py` line 819, `"key_id"` → `"key_serial"`.
.claude/rules/pool-read-apis.md:9: ## There is no `pool.inventory()`
.documents/INFRASTRUCTURE.md:27: `Datastore/object.py` defines the single base class every persistable domain
.documents/INFRASTRUCTURE.md:180: `Datastore/SQL/Datastore.py` defines `@ray.remote class Datastore`, wrapping
.documents/INFRASTRUCTURE.md:190: `Datastore/SQL/ShardedPool.py` is the API every driver script (`main.py`,
.documents/INFRASTRUCTURE.md:498: | `pool.inventory()` is a reporting tool, not a data-fetch API | `.claude/rules/pool-read-apis.md` |
.documents/architecture-summary.md:153: ### DatastoreObject base class (`Datastore/object.py`)
.documents/architecture-summary.md:190: ### Datastore actor (`Datastore/SQL/Datastore.py`)
.documents/architecture-summary.md:197: ### ShardedPool (`Datastore/SQL/ShardedPool.py`)
.documents/architecture-summary.md:497: which calls `pool.inventory(cls_name)` and formats the returned aggregated
.documents/architecture-summary.md:500: `pool.inventory()` returns lossy aggregates (counts, timestamps, label lists),
.documents/architecture-summary.md:580: | `pool.inventory()` is a reporting tool, not a data-fetch API | `.claude/rules/pool-read-apis.md` |
.documents/dk-and-rpk-migration/rehearsal/stage_counts.py:26: (RayTools/RayWorkPool.py:181). The titles are main.py's: `STAGE 1: BACKGROUND INFLATIONARY
ComputeTargets/GradientCoupledInstanton/picard.py:452: #      access to the Ray dispatch layer, and RayTools/RayWorkPool.py (which
tests/test_config_datastore.py:18: The literals below were captured from SI's own layer (its ``Datastore/SQL/Datastore.py`` and
tests/test_config_datastore.py:19: ``Datastore/SQL/ClientPool.py``) at the gate of prompt 05 of the ``dk-and-rpk-migration``
tests/test_config_datastore.py:209: old layer's ``drop_actions=`` and ``inventory_config=``. A failure names the file and line."""
tests/test_config_datastore.py:234: for name in ("drop_actions", "inventory_config"):
tests/test_rehearsal_stage_counts.py:22: RayTools/RayWorkPool.py (the `** TITLE` banner at :181, the progress lines at :556-566, the
tests/test_rehearsal_stage_counts.py:26: (`Datastore/SQL/Datastore.py` `_validate_on_startup`, a factory's `Pruned N unvalidated ...`
tools/compare_stores.py:39: (`Datastore/SQL/ShardedPool.py:88`, `:296`), which for a copied store names the original's files.
tools/compare_stores.py:94: # (Datastore/SQL/ShardedPool.py:244-284, created at :287-291 by _write_shard_data) and
tools/compare_stores.py:115: "(Datastore/SQL/Datastore.py:317, :639-647); foreign keys are resolved through it",
tools/compare_stores.py:116: "timestamp": "datetime.now() at insert (Datastore/SQL/Datastore.py:651-652)",
```

The other 222 are in dated records (the results notes 01–10, 219; `verification.md:28`;
`gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md:75`; `OPEN-ISSUES.md:162`).

(The sweep reads `git ls-files`; this note is new, so it was added to the index with `git add -N` before the final
runs, and the counts below include it.)

**After**, at the working tree before `ae4f489`: **301 lines in 20 files**.

```text
== 301 lines in 20 files
      1  .claude/memory/bug-assign-shard-keys-key-id.md
      1  .claude/rules/pool-read-apis.md
      3  .documents/INFRASTRUCTURE.md
      2  .documents/architecture-summary.md
      8  .documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md
      1  .documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md
     70  .documents/dk-and-rpk-migration/04-adopt-raypoolkit.md
     55  .documents/dk-and-rpk-migration/05-move-si-data-out-of-the-layer.md
     22  .documents/dk-and-rpk-migration/06-prepare-the-inflaton-trajectory-factories.md
      3  .documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md
      1  .documents/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md
     49  .documents/dk-and-rpk-migration/09-adopt-datastorekit.md
     10  .documents/dk-and-rpk-migration/10-port-the-inventory.md
     51  .documents/dk-and-rpk-migration/12-close-the-migration.md
      1  .documents/dk-and-rpk-migration/rehearsal/stage_counts.py
     12  .documents/dk-and-rpk-migration/verification.md
      1  .documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md
      4  tests/test_config_datastore.py
      2  tests/test_rehearsal_stage_counts.py
      4  tools/compare_stores.py
```

Classification of every line after:

| Group | Lines | Class |
|---|---|---|
| `.documents/dk-and-rpk-migration/` results notes 01, 03–10 (the files' counts above) | 219 | **dated records, unchanged** (§1.1's 219) |
| `verification.md:28` | 1 | dated record, unchanged (§1.1) |
| `.documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md:75` | 1 | dated record, unchanged (§1.1) |
| `tests/test_config_datastore.py:18-19`, `:209`, `:234` | 4 | **stay** (§1.1): what the literals were captured from, and the guard that no pool passes the old layer's arguments |
| `.claude/rules/pool-read-apis.md:9` | 1 | **stays** (§1.1): the heading "There is no `pool.inventory()`" |
| `.documents/dk-and-rpk-migration/rehearsal/stage_counts.py:26` | 1 | **stays** (§1.1): dated "as of prompt 01's commit", RH0's tooling |
| `.claude/memory/bug-assign-shard-keys-key-id.md:24` | 1 | **stays** (§1.1): "Fixed 2026-06-20 …", a dated record |
| `tools/compare_stores.py:39`, `:97`, `:118`, `:120` | 4 | **mine, naming the old layer as the tag's** (`pre-datastorekit:` or "in git at the tag"), not as current |
| `tests/test_rehearsal_stage_counts.py:22`, `:24` | 2 | mine, history (past tense, "at prompt 01's commit, … since replaced") |
| `.documents/INFRASTRUCTURE.md` (3) | 3 | mine: `:57-58` name the old layer's files "there" (at the tag) in §1; `:613` the invariant row "There is no `pool.inventory()`" |
| `.documents/architecture-summary.md` (2) | 2 | mine: "There is no `pool.inventory()`" (the Inventory section and the invariant row) |
| `.documents/dk-and-rpk-migration/verification.md` §4 (11) | 11 | mine, in a dated record: the closing tables and the handover name the deleted paths as deleted, at the tag |
| this note (51) | 51 | mine, in a dated record: the sweep's before-lines quoted, the Y4 table, the deviations |
| `OPEN-ISSUES.md:162` | 0 | the row moved to §7 and no longer names the path; it was §1.1's, and left the sweep |

**No line names a deleted file as current.** Every line of the five "mine" groups above says that the file is
deleted, or in git at the tag. The count, 246 before and 301 after, includes this note's own quotations.

### `ast` and `ruff` (§2.2)

The script (`astcmp.py`; before is `git show 47c0a77:<path>`, after the working tree; docstrings are removed by
walking every `Module`, `ClassDef`, `FunctionDef` and `AsyncFunctionDef` body; a differing statement is shown with
its differing constants):

```python
"""AST comparison for prompt 12's Y4: before = `git show <start>:<path>`, after = the working tree.

Docstrings are removed by walking every Module, ClassDef, FunctionDef and AsyncFunctionDef body
(not the module's alone); the remaining dumps are compared. A differing node is shown with
ast.unparse of both sides.
"""
import ast
import subprocess
import sys

START = sys.argv[1]
PATHS = sys.argv[2:]


def strip_docstrings(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:] or [ast.Pass()]
    return tree


def count_docstrings(tree):
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            b = node.body
            if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) and isinstance(b[0].value.value, str):
                n += 1
    return n


for path in PATHS:
    before_src = subprocess.run(["git", "show", f"{START}:{path}"], capture_output=True, text=True, check=True).stdout
    after_src = open(path).read()
    b, a = ast.parse(before_src), ast.parse(after_src)
    nb, na = count_docstrings(b), count_docstrings(a)
    b, a = strip_docstrings(b), strip_docstrings(a)
    db, da = ast.dump(b), ast.dump(a)
    print(f"== {path}: docstrings before {nb}, after {na}; dumps {'IDENTICAL' if db == da else 'DIFFER'} "
          f"({len(db)} vs {len(da)} chars)")
    if db != da:
        # report differing top-level statements and, inside them, differing Constant nodes
        for i, (x, y) in enumerate(zip(b.body, a.body)):
            if ast.dump(x) != ast.dump(y):
                print(f"   top-level statement {i} (line {getattr(x, 'lineno', '?')}) differs:")
                for nx, ny in zip(ast.walk(x), ast.walk(y)):
                    if type(nx) is ast.Constant and ast.dump(nx) != ast.dump(ny):
                        print(f"     - {nx.value!r}")
                        print(f"     + {ny.value!r}")
        if len(b.body) != len(a.body):
            print(f"   statement counts differ: {len(b.body)} vs {len(a.body)}")
```

Output:

```text
== tools/compare_stores.py: docstrings before 38, after 38; dumps DIFFER (190513 vs 190779 chars)
   top-level statement 15 (line 113) differs:
     - "the layer's key, leased from the serial broker at insert (Datastore/SQL/Datastore.py:317, :639-647); foreign keys are resolved through it"
     + "the layer's key, leased from the serial broker at insert unless the payload gives one (pre-datastorekit:Datastore/SQL/Datastore.py:539-547; datastorekit/SQL/Datastore.py:793-805); foreign keys are resolved through it"
     - 'datetime.now() at insert (Datastore/SQL/Datastore.py:651-652)'
     + 'datetime.now() at insert (pre-datastorekit:Datastore/SQL/Datastore.py:551-552); datastorekit stamps a replicated row with the one datetime.now() of the write, the same on every shard (datastorekit/SQL/Datastore.py:809-815, ShardedPool.py:3202-3203)'
== ComputeTargets/GradientCoupledInstanton/picard.py: docstrings before 16, after 16; dumps IDENTICAL (90676 vs 90676 chars)
== tests/test_rehearsal_stage_counts.py: docstrings before 7, after 7; dumps IDENTICAL (23628 vs 23628 chars)
== Datastore/SQL/ObjectFactories/InflatonTrajectory.py: docstrings before 2, after 2; dumps IDENTICAL (41762 vs 41762 chars)
```

Only `tools/compare_stores.py` differs, and only in the two `GLOBAL_BOOKKEEPING` values (top-level statement 15).
Each file's changed lines are in the Y4 table above (`git diff -U0`'s hunk headers). `./venv/bin/ruff check
--select F401,F811,F821`, per file, at the end (0 findings in each; the orchestrator's note gives 0 in each at
`f5b9334`, and no import was touched):

```text
tools/compare_stores.py: All checks passed!
ComputeTargets/GradientCoupledInstanton/picard.py: All checks passed!
tests/test_rehearsal_stage_counts.py: All checks passed!
Datastore/SQL/ObjectFactories/InflatonTrajectory.py: All checks passed!
```

### The documents (§2.3)

`git diff --numstat` on `.documents/` (additions, deletions): deletions only in `INFRASTRUCTURE.md`,
`architecture-summary.md`, `FILE_MAP.md` and `OPEN-ISSUES.md`; none in `verification.md` or any results note:

```text
1	1	.documents/FILE_MAP.md
207	92	.documents/INFRASTRUCTURE.md
6	6	.documents/OPEN-ISSUES.md
124	76	.documents/architecture-summary.md
696	0	.documents/dk-and-rpk-migration/12-close-the-migration.md
178	0	.documents/dk-and-rpk-migration/verification.md
```

**Cited paths and lines** (Y1–Y3 and Y6), all read:
- *DatastoreKit's client contract* (`git -C DatastoreKit show v0.5.0:docs/client-contract.md`): §1 (rows 5, 6, 9, 11,
  12, 13, 15, 16), §2 (`owner_column`, `validated_column`, `validate_on_startup`, `timestamp`), §3, §4, §5, §6, §7,
  §9.3, §9.5, §9.6, §9.7. Its `README.md` at `v0.5.0`, "Using it". RayPoolKit's `README.md` at `v0.2.0`, "Using it" and
  its subsections "The constructor", "The handlers", "The sizes", "The objects a lookup returns", "Which handlers a
  pool needs".
- *The installed `datastorekit`* (equal to the tag's, 08 and 10a): `object.py:5-38`; `SQL/factory_base.py:5-80`;
  `SQL/Datastore.py:37`, `:793-805`, `:809-815`; `SQL/ShardedPool.py:946`, `:995`, `:3131`, `:3147-3169`, `:3171`,
  `:3202-3203`, `:3441`, `:3618`, `:3626`, `:3674`, `:3695-3731`, `:3718`; `store_inventory.py:1018`
  (`read_inventory`).
- *The installed `raypoolkit`* (`cmp`-equal to `git show v0.2.0:raypoolkit/RayWorkPool.py`): `RayWorkPool.py:26-29`,
  `:75-76`, `:79-80`, `:290`, `:385`, `:424-426`, `:471`, `:481`; no `timeout` or `cancel` anywhere in the file.
- *The tag `pre-datastorekit`* (`git show`): `Datastore/SQL/ShardedPool.py:88`, `:158-191`, `:232-291`, `:244-284`,
  `:286-291`, `:296`, `:810-821`; `Datastore/SQL/Datastore.py:539-547`, `:551-552`; `Datastore/SQL/ClientPool.py:23`.
- *The tree:* `main.py:55-65` (`MAX_INFLIGHT_PIPELINE` at `:65`), `:107-120`; `requirements.txt:16`, `:58`/`:59`;
  `config/datastore.py`, `config/sharding.py`; `tests/test_inventory_specs.py` (`EXPECTED_SPECS`, `READ_THROUGH`,
  `EXCLUDED`, `test_every_registered_class_is_placed_exactly_once`); `ComputeTargets/GradientCoupledInstanton/picard.py:450-456`.

**`FILE_MAP.md`, every row checked against the tree** (85 rows whose "original path" is not a package's):

```python
import re, subprocess
files = set(subprocess.run(['git', 'ls-files'], capture_output=True, text=True).stdout.split('\n'))
dirs = {f.rsplit('/', 1)[0] for f in files if '/' in f}
missing = []; n = 0
for i, line in enumerate(open('.documents/FILE_MAP.md'), 1):
    if not line.startswith('|') or line.startswith('|--') or line.startswith('| Flat'): continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 3: continue
    orig = cells[1].strip('`')
    if orig.startswith('raypoolkit.') or orig.startswith('datastorekit.'): continue
    n += 1
    if orig not in files and orig not in dirs: missing.append((i, orig))
print(n, 'rows checked; missing:', missing)
```

→ `85 rows checked; missing: []`.

### The index (§2.4)

`.documents/OPEN-ISSUES.md`'s counts are made by counting its rows (`count_issues.py`, in the scratch directory;
reproduced below): **open = the table rows of §1–§6a**; **closed = the rows of §7, where a row that names several
bracketed issues in its first cell counts each**: `[doc-bc-handoff-…]` ×2, `[doc-grid-sampling-…]` ×3,
`[doc-hfp-structure-status]` and its two neighbours ×3.

```text
before:  open rows: 59  by section: {'1': 12, '1a': 12, '2': 4, '3': 12, '4': 7, '5': 1, '6': 5, '6a': 6}
         closed rows: 24  closed issues (each bracketed name counted): 29      (24 + 1 + 2 + 2 = 29)
after:   open rows: 57 by section: {'1': 12, '1a': 12, '2': 4, '3': 12, '4': 7, '5': 1, '6': 5, '6a': 4}
         closed rows: 26 closed issues (each bracketed name counted): 31      (26 + 1 + 2 + 2 = 31)
```

Header: "**57 open**, 31 closed", dated 2026-10-23. The two rows left §6a for §7 (`| Issue | Closed | By |`, the form
of `[gci-value-table-outside-the-inventory]`'s row); §6a's lead-in says the campaign closed and the four issues
survive it; the sentence "One campaign has a status board" says the board is closed and holds those four;
`[hfp-closed-form-audit-not-run]`'s hook gained a pointer to the handover; no other row moved. §6a's four rows
are the board's §3 four rows, by name (`[plot-scripts-stale-version-label]`, `[redshift-registered-in-neither-table-list]`,
`[unified-pipeline-stores-null-instanton-labels]`, `[gci-picard-inner-fails-on-rehearsal-grid]`), with the owners the
board gives. `.prompts/INDEX.md`'s header counts its table: 6 rows, 0 live, 1 halted
(`gradient-coupled-instanton`), 5 complete; the campaign's row ends `2026-10-11 → 2026-10-23`, `§6a; 4`, and carries
the final suites; the "Planned" paragraph says U7 was ruled, the tag made and pushed, and Phase 2 reads the stores
there.

```python
"""Counts .documents/OPEN-ISSUES.md by its rows. Open = table rows of sections 1..6a (every row under
a '## N.' heading other than 7, excluding the header rows and separator rows). Closed = rows of
section 7, where a row that names several bracketed issues in its first cell counts each
(`[a]` and `[b]`, or `[a]`, `[b]`, `[c]`)."""
import re, sys
path = sys.argv[1] if len(sys.argv) > 1 else ".documents/OPEN-ISSUES.md"
sec = None
open_rows, closed_rows, closed_issues = [], [], 0
per_section = {}
for line in open(path):
    m = re.match(r"^## (\S+?)\.", line)
    if m:
        sec = m.group(1)
        continue
    if not line.startswith("|") or sec is None:
        continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if cells[0] in ("Issue",) or set(cells[0]) <= set("-: "):
        continue
    if sec == "7":
        closed_rows.append(cells[0])
        n = len(re.findall(r"`\[[^\]`]+\]`", cells[0]))
        closed_issues += max(n, 1)
    else:
        open_rows.append((sec, cells[0]))
        per_section[sec] = per_section.get(sec, 0) + 1
print("open rows:", len(open_rows), "by section:", per_section)
print("closed rows:", len(closed_rows), "closed issues (each bracketed name counted):", closed_issues)
multi = [(r[:60], len(re.findall(r"`\[[^\]`]+\]`", r))) for r in closed_rows if len(re.findall(r"`\[[^\]`]+\]`", r)) > 1]
print("multi-issue rows:", multi)
```

### §2.6 — the tag still reads (the handover's premise)

`git archive pre-datastorekit | tar -x -C <scratch>/tag`, then, from outside the tree, with the main checkout's venv
and `python -I`, the tree put on `sys.path` in the code. No store was opened and no worktree made. **Layer first**
(`tag_layer_first.py`):

```text
layer: Datastore.SQL.ShardedPool <scratch>/tag/Datastore/SQL/ShardedPool.py
config.datastore: 30 factories; <scratch>/tag/config/datastore.py
raypoolkit: /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/raypoolkit/__init__.py
ray.is_initialized(): False
exit status 0
```

**The prompt's order** (`import config.datastore` first; `tag_config_first.py`), which fails at the tag:

```text
Traceback (most recent call last):
  File "<scratch>/tag_config_first.py", line 3, in <module>
    import config.datastore
  File "<scratch>/tag/config/datastore.py", line 45, in <module>
    from Datastore.SQL.ObjectFactories.DimensionfulQuantity import (
        sqla_dimensionful_quantity_factory,
    )
  File "<scratch>/tag/Datastore/SQL/__init__.py", line 1, in <module>
    from .Datastore import Datastore
  File "<scratch>/tag/Datastore/SQL/Datastore.py", line 27, in <module>
    from Datastore.SQL.ClientPool import SerialPoolManager, SerialLeaseManager
  File "<scratch>/tag/Datastore/SQL/ClientPool.py", line 23, in <module>
    from config.datastore import serial_batch_sizes as _default_serial_batch_size
ImportError: cannot import name 'serial_batch_sizes' from partially initialized module 'config.datastore' (most likely due to a circular import) (<scratch>/tag/config/datastore.py)
exit status 1
```

That is `[config-datastore-cannot-be-imported-before-the-layer]`, closed at 09 for the tree and never for the tag (the
tag's `Datastore/SQL/ClientPool.py:23`). The extracted tree was deleted (`ls` of the scratch directory: no `tag`).

### The G4 drafts (P14)

Identical to `verification.md` §4.3 (the builder wrote both from one file; a `diff` of the two blocks is empty).
Each replaces the second column of the G4 row of its package's board: DatastoreKit's at `:1539`, RayPoolKit's at
`:666`.

**The carried notes.** DatastoreKit's cell ends with the cell's own italic notes, extracted from
`prompts/extraction/IMPLEMENTATION_STATE.md:1539` (the text between the leading "⬜ " and the trailing " |"), not
retyped. `diff` of the extracted text against the tail of the draft cell:

```text
$ diff dk_g4_notes_extracted.txt dk_g4_notes_in_cell.txt
$ echo $?
0
```

**DatastoreKit's G4 cell**:

```text
✅ 2026-10-22: holds. SI adopted `v0.5.0` (the pin at SI `80d99a7`, moved from `v0.4.0` at `1b1ca6d`; installed at `f47b9a255e9ad58e…`, not editable) in its campaign `dk-and-rpk-migration`, and a rehearsal through the package reproduces, bit for bit, the rehearsal made before the swap. Against the checklist, [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md) §9, with its `v0.4.0` addendum ("SI has adopted `v0.3.0` or later"), which stands in the `v0.5.0` addendum: (1) **the 9 layer files are deleted and the tag imported**: the 7 modules removed and the two `__init__.py` emptied (0 bytes, P6) by SI `f4da58f` (dk-and-rpk-migration prompt 09); `docs/extraction/measure_client_imports.py si --commit 47c0a77`, run from this repository (clean, `2900d82`) with its own venv, finds the 7 absent and 0 import statements, 0 string literals and 0 `import_module` / `__import__` calls naming a layer module in 201 tracked `.py` files (0 unparsed), the same at `f4da58f` (197 files) and `2179854`; the 25 factory-module imports it counts (`config/` 22, `CosmologyConcepts/` 2, `tests/` 1) are SI's own modules importing its factories; `requirements.txt:16` holds `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.5.0`, installed from the tag, not editable, `pip check` clean; (2) **its suites pass**: the default run 732 (731 passed, 1 skipped) and the integration run 67 (66 passed, 1 skipped) at SI `66b1c81` (RH2's tree), and the same counts again at SI `47c0a77` and after the close's prose edits; the `slow` block, 69 tests, passed after the close's edits (69 passed in 404 s, against 390 s at RH0); (3) **a small grid is rebuilt through the package**: RH2, SI `2179854` (reviewed at `18b490a`), dk-and-rpk-migration prompt 11, under a real Ray 2.55.1 cluster, through the package's `ShardedPool`, `Datastore` actors and `SerialPoolBroker` and `raypoolkit` `v0.2.0`: a quadratic-potential grid on 10 shards (one trajectory and ten each of `FullInstanton`, `SlowRollInstanton` and `CompactionFunction`), built straight through, killed by `SIGTERM` in the `FullInstanton` stage and resumed (the package's actors pruned the 2 unvalidated rows at open; the resume computed the 6 it had not kept), and built scalars-only. Each store equals SI's RH1 store of the same mode, built by SI's own layer at the tag `pre-datastorekit` (`0527480`), and so RH0's, in every stored science column (30 tables, RH1's row counts), by SI's `tools/compare_stores.py` (`sqlite3` `mode=ro`; six comparisons, each `RESULT: equal`, exit 0, only timestamps and the JSON timing keys differing); the schema equals RH1's; `scalar_data.csv` hashes to `b0564eec…58a2` at RH0, RH1 and RH2. Beyond §9: `python -m datastorekit.tools.shard_key_audit` gives `VERDICT: OK` on the three stores; a `python -m datastorekit.tools.sharded_store copy` of `11-reference` is read back with `read_inventory` with no problem and every class's count equal, compares equal, and is deleted by `ShardedPool.delete_store` — the same 11 paths `ShardedPool.closed_store_files` named, and nothing else; `main.py --inventory` reads the stores through `read_inventory` before Ray starts with `problems: none` (24 classes). Not exercised: the package's repair of an interrupted replicated write (the signal fell 2.7 s after the last one, so nothing was in flight). SI's record is `.documents/dk-and-rpk-migration/verification.md` §3 and §4 and the results notes 09 to 12 (campaign `dk-and-rpk-migration`). SI is on `v0.5.0`. *(2026-10-09: the adoption checklist is [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md), measured at SI `7bb3efd` by 07a; its stores are rebuilt, U31.)* *(2026-10-10: `v0.2.1` is ready to be tagged on extraction prompt 10's commit once CI passes there at both ends, as U23 and U28; 10 makes no tag and pushes nothing. SI's addendum is [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md#addendum-v021-extraction-prompt-10-2026-10-10).)* *(2026-10-10: `v0.2.1` is made, annotated, on 10's commit `33778b0` (tag object `0ba2e4d`) and pushed, after CI passed there at both ends, [run 38054748108](https://github.com/ds283/DatastoreKit/actions/runs/38054748108): Python 3.12.15 / Ray 2.43.0 / SQLAlchemy 2.0.39 and 3.13.16 / 2.55.1 / 2.0.46, SQLite 3.45.1 at both, each `Ran 486 tests … OK`. SI may now adopt it.)* *(2026-10-11: `v0.2.2` is ready to be tagged on `actor-names` prompt 02's commit once CI passes there at both ends, as U23 and U28; 02 makes no tag and pushes nothing. SI's addendum is [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md#addendum-v022-actor-names-prompt-02-2026-10-11).)* *(2026-10-11: `v0.2.2` is made, annotated, on 02's commit `6d8ee9a` (tag object `c32d027`) and pushed, after CI passed there at both ends, [run 38131949852](https://github.com/ds283/DatastoreKit/actions/runs/38131949852): Python 3.12.15 / Ray 2.43.0 / SQLAlchemy 2.0.39 and 3.13.16 / 2.55.1 / 2.0.46, SQLite 3.45.1 at both, each `Ran 494 tests … OK`. SI may now adopt it.)* *(2026-10-11: `v0.2.3` is ready to be tagged on `factory-defaults` prompt 02's commit once CI passes there at both ends, as U23 and U28; 02 makes no tag and pushes nothing. SI's addendum is [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md#addendum-v023-factory-defaults-prompt-02-2026-10-11).)* *(2026-10-11: `v0.2.3` is made, annotated, on `factory-defaults` 02's commit `0de2b16` (tag object `8dac562`) and pushed, after CI passed there at both ends, [run 38177954330](https://github.com/ds283/DatastoreKit/actions/runs/38177954330): Python 3.12.15 / Ray 2.43.0 / SQLAlchemy 2.0.39 and 3.13.16 / 2.55.1 / 2.0.46, SQLite 3.45.1 at both, each `Ran 504 tests … OK`. SI may now adopt it.)* *(2026-10-12: `v0.3.0` is ready to be tagged on `object-timestamp` prompt 02's commit once CI passes there at both ends, as U23 and U28; 02 makes no tag and pushes nothing. SI's addendum is [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md#addendum-v030-object-timestamp-prompt-02-2026-10-12).)* *(2026-10-12: `v0.3.0` is made, annotated, on `object-timestamp` 02's commit `2f5417e` (tag object `bf0a3b2`) and pushed, after CI passed there at both ends, [run 38220924369](https://github.com/ds283/DatastoreKit/actions/runs/38220924369): Python 3.12.15 / Ray 2.43.0 / SQLAlchemy 2.0.39 and 3.13.16 / 2.55.1 / 2.0.46, SQLite 3.45.1 at both, each `Ran 509 tests … OK`. SI may now adopt it.)* *(2026-10-14: `v0.4.0` is ready to be tagged on `fingerprint` prompt 02's commit once CI passes there at both ends, as U23 and U28; 02 makes no tag and pushes nothing. SI may adopt `v0.3.0` or `v0.4.0`, as it chooses (`fingerprint` U6). SI's addendum is [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md#addendum-v040-fingerprint-prompt-02-2026-10-14).)* *(2026-10-14: `v0.4.0` is made, annotated, on `fingerprint` 02's commit `c8570e8` (tag object `8e7c1d7`) and pushed, after CI passed there at both ends, [run 38538726292](https://github.com/ds283/DatastoreKit/actions/runs/38538726292): Python 3.12.15 / Ray 2.43.0 / SQLAlchemy 2.0.39 and 3.13.16 / 2.55.1 / 2.0.46, SQLite 3.45.1 at both, each `Ran 530 tests … OK`. SI may adopt `v0.3.0` or `v0.4.0`, as it chooses (`fingerprint` U6).)* *(2026-10-21: `v0.5.0` is ready to be tagged on `extra-values` prompt 02's commit once CI passes there at both ends, as U23 and U28; 02 makes no tag and pushes nothing. SI adopts `v0.5.0` (`extra-values` U5). SI's addendum is [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md#addendum-v050-extra-values-prompt-02-2026-10-21).)* *(2026-10-22: `v0.5.0` is made, annotated, on `extra-values` 02's commit `f47b9a2` (tag object `6a6809d`) and pushed, after CI passed at both ends on its tree, [run 39729857177](https://github.com/ds283/DatastoreKit/actions/runs/39729857177), on `dfd45c4`, whose tree outside `prompts/` is `f47b9a2`'s (the user's ruling): Python 3.12.15 / Ray 2.43.0 / SQLAlchemy 2.0.39 and 3.13.16 / 2.55.1 / 2.0.46, SQLite 3.45.1 at both, each `Ran 538 tests … OK`. SI adopts `v0.5.0` (`extra-values` U5).)*
```

**RayPoolKit's G4 cell**:

```text
**holds** 2026-10-20: SI adopted `v0.2.0` in its campaign `dk-and-rpk-migration`, and the five parts of the checklist's item 8 hold. (1) `RayTools/` is gone: `git ls-tree ef13445 RayTools` is empty (SI's prompt 04), and so it is at `0527480`, `2179854` and `47c0a77`. (2) No import of it, and none of `_default_store_handler`: `docs/adoption/measure_client_pools.py si --commit ef13445`, run from this repository (clean, `17029d9`) with its own venv, gives 0 imports (0 naming a private name) and 0 `import_module` / `__import__` calls naming `RayTools`, and 2 string literals, the module docstrings of `.documents/dk-and-rpk-migration/rehearsal/stage_counts.py:16` and `tests/test_rehearsal_stage_counts.py:16` (dated statements about the log parser's fixtures, not imports), and 1 test module naming it (that docstring); the figures are the same at `0527480`, `2179854` and `47c0a77`. SI took option (a) of item 3: it dropped `_default_store_handler`, and the compute pools use the package's default `store_handler`, `obj.store()`, which is what it passed; `git grep _default_store_handler 47c0a77 -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py` finds nothing. (3) The pin is in place and the venv installed from it: `raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0` at `requirements.txt:58` (SI `5396a3d`; `:59` since SI's DatastoreKit pin, `1b1ca6d`, sits above it), `raypoolkit` 0.2.0 at `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`, not editable, named by the provenance line of every build log from RH1 on. (4) SI's suites pass: at `ef13445` the default run 680 (679 passed, 1 skipped) and the integration run 61 (60 passed, 1 skipped), as before the change; at RH2's tree (`66b1c81`) 732 (731 passed, 1 skipped) and 67 (66 passed, 1 skipped). (5) Every site constructs: the same script gives 16 `RayWorkPool(...)` calls, every one `constructs` (12 with `compute_handler=None`, 4 with one), at `ef13445`, `0527480`, `2179854` and `47c0a77`, with `ray.is_initialized()` False; its 5 flags (on 4 calls: `MAX_INFLIGHT_PIPELINE_UNIFIED` = 16, `MAX_INFLIGHT_PIPELINE` = 50 twice, `len(traj_payloads)` twice) were checked by hand at 04, and `model_list` is never empty. The code of `ef13445` is 8 lines of `main.py` (the import, `_default_store_handler` and the `store_handler` it was passed as) and the one import line in each plot script. RH1 (SI `0527480`, `raypoolkit` alone, 2026-10-21) and RH2 (SI `2179854`, with `datastorekit` too, 2026-10-22) ran it under real Ray, on SI's isolated cluster: each built the 10-shard quadratic grid straight through, killed and resumed, and scalars-only, every pool completing and printing its lines in the layout RH0's copy printed (SI's `stage_counts.py` parsed them unchanged), every store equal to RH0's, bit for bit, by SI's `tools/compare_stores.py`. SI's record is `.documents/dk-and-rpk-migration/verification.md` §2 to §4 and the results notes 04, 07, 11 and 12 (campaign `dk-and-rpk-migration`). Checklist: [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md), measured at SI `7bb3efd`; its item 8 is the acceptance
```

## The deliberate-breakage record

None. 12 adds no code and no test (acceptance 8). The sweep's non-vacuity, the 246 lines before any edit, is the
only run that had to find something; the `ast` comparison's non-vacuity is that `tools/compare_stores.py` differs
in exactly the two strings it was changed in, where the other three files compare identical.

## Observations not acted on

1. **`test-selection.md`'s table** says four tests of `test_gradient_coupled_instanton_end_to_end.py` call the
   compute directly; `-m slow` collects three from it (the file has three `@pytest.mark.slow`). The `slow` total,
   69, is right. The table "stays" (the prompt); a one-word correction is left to whoever next edits the rule.
2. **The board's header paragraph** still says the campaign "pins `v0.4.0`" in its closing sentence; the later
   sentences and the gates table say `v0.5.0`. A dated record, left.
3. **RayPoolKit's `docs/adoption/stochasticinstantons.md` is not in `v0.2.0`**: it was read at the checkout's `HEAD`
   (`17029d9`), as the prompt says. The draft names its item 8 and "measured at SI `7bb3efd`".
4. **The draft for DatastoreKit's board cites no SI commit for 12**: 12's commit does not exist when the draft is
   written. It names `47c0a77` for the script figures; the orchestrator's re-run at 12's commit is the check.
5. **The package's repair of an interrupted replicated write** was not exercised by RH2 (board §5.28), and the draft
   says so.
6. **The scratch directory** holds the extra script outputs and the copies used for the sweeps; none is in the
   repository.

## State handed to the next prompt

There is no next prompt in this campaign. The branch `dk-and-rpk-migration` is complete and is the user's to merge.

- **For P2** (the handover, in brief; the whole is `verification.md` §4.5):
  - **The stores.** Every SI store written before `f4da58f` is refused by the tree (U31): the June stores
    (`SMSR_scaling*.sqlite`, `large-grid-1500.sqlite`, `doe-run-500.sqlite`, `quad-ast-small-*.sqlite`), the July
    `phase_a` stores, `test-gradient.sqlite`, RH0's and RH1's. They stay on disk; `tools/compare_stores.py` reads
    them at any commit after 01, and the tag `pre-datastorekit` (`0527480`, annotated, on `origin`) reads them
    with the tree.
  - **How `[hfp-closed-form-audit-not-run]` reads them** (`OPEN-ISSUES.md` §2): from a worktree at the tag that uses
    the main checkout's venv, where both packages are installed. **The reading order at the tag is the layer
    first:** `from Datastore.SQL.ShardedPool import ShardedPool`, then `import config.datastore`, then `from
    raypoolkit import RayWorkPool` (checked above; `config.datastore` first raises the `ImportError`). Read only, never
    resumed (a June store pruned after an interrupted run may hold orphans:
    `[inflaton-trajectory-prune-orphans-value-rows]`, closed at 06 for new builds only). Every driver needs
    `--ray-address`.
  - **P2's own builds** go through the packages into fresh stores, on SI's isolated cluster under the rehearsal lock
    (`ray_cluster.sh start PURPOSE`, `--ray-address 127.0.0.1:6390`, `ray_cluster.sh stop`; never `ray stop`);
    `tools/compare_stores.py` compares the rebuilt grids with the June ones, where a difference is the expected
    result. The package adds `main.py --inventory`, `python -m datastorekit.tools.shard_key_audit`, `python -m
    datastorekit.tools.sharded_store copy`, `ShardedPool.closed_store_files` and `delete_store`.
  - **The issues left open:** `[plot-scripts-stale-version-label]` (P2), `[redshift-registered-in-neither-table-list]`
    and `[unified-pipeline-stores-null-instanton-labels]` (unowned), `[gci-picard-inner-fails-on-rehearsal-grid]` (P3).
    RunRegistryKit is the next infrastructure campaign (README §7).
- **For the user: the decisions left** (README §6.3).
  1. **The two G4 commits, first.** DatastoreKit's: replace the second column of the G4 row
     (`prompts/extraction/IMPLEMENTATION_STATE.md:1539`) by the block above and in `verification.md` §4.3. RayPoolKit's:
     replace the second column of the G4 row (`:666`) the same way. Neither is committed in its repository; the user
     makes those commits, or has a session there make them.
  2. The merge of `dk-and-rpk-migration` into `main` (P15).
  3. Removing the rehearsal stores under `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`
     (494,140 KiB, 483 MiB, at 12; about 24 MB for each store with its ten shards; RH0's, RH1's and RH2's, with the
     readers' copies, the profile databases, `02-attempt-1-aborted/`, `02-attempt-2-reader-defect/` and `logs/`).
  4. The plot scripts' version label and pools (P9, P10).
  5. Whether to rename the `Datastore` package (P6).
- **State.** The suites give 732 (731 passed, 1 skipped), 67 (66 passed, 1 skipped) and `slow` 69 (all passed). No
  SI Ray process is running, the lock is free, and `ray stop` was never run. DatastoreKit (`2900d82`), RayPoolKit
  (`17029d9`), ChamPBH and SecondaryGWKit are untouched; the venv is unchanged (`pip freeze` 83 lines, `pip check`
  clean). **Rollback:** `git revert` of `ae4f489` alone; nothing in the venv.

