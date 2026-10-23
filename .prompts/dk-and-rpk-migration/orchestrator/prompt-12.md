# Orchestrator — prompt 12, close the migration

Read [`../README.md`](../README.md) first: §0.3, §2.2 (12's charter), §3, §4.4, §5 (rules 6, 7, 11, 12,
15, 16), §6.2 (P6, P9, P10, P13–P16), §6.3 and §7. Then the board's §5.28 (11's review and its
"Handed on") and §5.29 (12 written). The conventions are [`prompt-01.md`](prompt-01.md)'s §0
"Conventions", unchanged but where this note says otherwise. There is no earlier note of the same
kind: 12 writes no code and runs no build, but it rewrites more prose than any prompt before it, and
two of its outputs (the G4 drafts) leave this repository by the user's hand.

**You do not write code.** You may:
- run the suites, `ruff check`, both packages' scripts and read-only Python checks, from the session
  scratchpad;
- run the stale-path sweep and the `ast` comparisons yourself;
- extract the tag's tree into the scratchpad (`git archive`), never a worktree, and delete it after;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`12-close-the-migration.md`](../12-close-the-migration.md) · **Board items:** Y1–Y7 ·
**Closes:** `[test-counts-stale-in-claude-md]`, `[pool-prose-stale-after-raypoolkit-adoption]`, and the
campaign · **Opens:** only what the work finds · **Model:** Sonnet, as the prompt recommends ·
**No network.** Nothing is pushed, no tag is made, and nothing is committed in DatastoreKit,
RayPoolKit, ChamPBH or SecondaryGWKit.

**Gate:**
- 11 landed (`2179854`) and was reviewed (`18b490a`): RH2, RayPoolKit G4 and DatastoreKit G4 hold
  (board §2).
- `HEAD` is the commit that adds this note, or a later one that touches no code.
  `git diff --stat 18b490a HEAD -- . ':!.prompts' ':!.documents'` is empty.
- No SI cluster is up and the lock is free; no other session runs a suite or a Ray job from this
  venv, or installs into it, while 12 runs.

## 0. What makes this prompt unusual

**It is the campaign's last word, and most of it is prose that future sessions will take as true.**
`CLAUDE.md`, the rules and the two architecture documents are loaded or read at the start of every
later session; a sentence in them that misdescribes a package will be acted on. So the review reads
every rewritten section in full, and checks each statement about a package against the client
contract at `v0.5.0`, the package's README at its tag, or the installed code — never against the
agent's say-so. The rest is records (the board, the two indexes, `verification.md` §4) whose counts
must agree by counting, and two G4 drafts that the user will paste into the packages' boards, so
every SHA and figure in them is re-checked.

**What the orchestrator measured for this note** (at `f5b9334`, 2026-10-23 01:37–01:55 BST):
- **The stale-path sweep** — the script is `orch12/sweep.py` in the session scratchpad; copy it to the
  agent's own scratch directory and run it from the repository root with `./venv/bin/python -I
  <path>`; `--commit REV` reads a commit instead of the working tree. It prints `path:line: text` per
  hit on stdout and the per-file summary on stderr. Its patterns are the prompt's §2.1 list, in path
  and dotted form, with a lookbehind `(?<![A-Za-z_./])` that keeps `datastorekit/…`,
  `datastorekit.…` and `raypoolkit/…` out; it skips `.prompts/` and binary files. **At `f5b9334` it
  prints 246 lines in 21 files, exactly §1.1's**: the 17 to change (`INFRASTRUCTURE.md` 4,
  `architecture-summary.md` 6, `tools/compare_stores.py` 4, `picard.py` 1,
  `tests/test_rehearsal_stage_counts.py` 2), the 7 that stay (`tests/test_config_datastore.py` 4,
  `pool-read-apis.md` 1, `stage_counts.py` 1, `.claude/memory/bug-assign-shard-keys-key-id.md` 1), and
  222 in dated records (the results notes 01–10, 219; `verification.md:28`; `24-prerequisite-…:75`;
  `OPEN-ISSUES.md:162`). The agent may use it or its own; if its own, it shows the 246 first.
  **The sweep catches paths, not descriptions**: `tools/compare_stores.py:96-98` cite the old layer
  as `ShardedPool.py:232-291` without the `Datastore/SQL/` prefix, so the sweep misses them; they are
  in §1.1's list (`:93-98`) all the same.
- **Both packages' scripts at `f5b9334`**, each from its own root and venv: DatastoreKit's gives §1.1's
  figures exactly (7 modules absent, 201 files, 0 / 0 / 0, 25 factory imports: `config/` 22,
  `CosmologyConcepts/` 2, `tests/` 1). RayPoolKit's gives §1.1's figures **but one: 416 lines of
  non-`.py` files, not 402.** The 14 more are all in `.prompts/` (236 → 250), and are prompt 12's own
  lines; at `18b490a` it gives 402, and the two outputs differ in that line, the commit and the file
  count alone. This note's commit adds more `.prompts/` lines. **That count moves with every record
  commit, so it is not a §4 stop**: the agent reports the total and the "outside the campaign records"
  figure (166 at `f5b9334`: `.claude/` 18, `.documents/` 148), and says which of Y1–Y3's edits moved
  the latter.
- **The suites**, collected at `f5b9334`: 868; default 732; `integration` 67; `slow` 69;
  `slow and integration` none; `not integration` 801 — §1.1's. No code has changed since `18b490a`,
  whose review ran 732 (731 passed, 1 skipped) and 67 (66 passed, 1 skipped). The nine `slow`-marked
  files are `test-selection.md`'s table.
- **The venv:** `pip freeze` 83 lines; `datastorekit @ …@f47b9a255e9ad58e0d0eaf85644f53b575884d31`,
  `raypoolkit @ …@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`, neither editable; `pip check` clean; the
  provenance line is 11's:
  `>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **`ruff`** is `./venv/bin/ruff` (not on `PATH`). `check --select F401,F811,F821` on each of Y4's four
  Python files at `f5b9334`: "All checks passed!" (0 findings each).
- **§2.6, prototyped**, from `git archive pre-datastorekit` in the scratchpad, with the main venv and
  `-I`, the root put on `sys.path` in the code. **The prompt's order fails at the tag:** `import
  config.datastore` first raises `ImportError: cannot import name 'serial_batch_sizes' from partially
  initialized module 'config.datastore'` (the tag's `Datastore/SQL/ClientPool.py:23`). That is
  `[config-datastore-cannot-be-imported-before-the-layer]`, closed at 09 for the tree, never for the
  tag. **The layer first succeeds:** `from Datastore.SQL.ShardedPool import ShardedPool`, then `import
  config.datastore` (30 factories, the tag's own file), then `from raypoolkit import RayWorkPool` (the
  venv's package), `ray.is_initialized()` False. The tag's `main.py` also imports in full (an `import
  main` reaches its argument parser and stops at `--ray-address`). The extracted tree was deleted.
- **The tag** `pre-datastorekit` is annotated (object `9234839`), on `0527480`, and is on `origin`.
- **The cited records exist where §1.1 says:** `04-adopt-raypoolkit.md:592` ("The text of the
  RayPoolKit G4 record, for 12 to carry into its draft"), `09-adopt-datastorekit.md:725` and
  `10-port-the-inventory.md:859` ("What remains stale, for 12"), 11's "State handed to the next prompt"
  at `11-rehearse-through-both-packages.md:799`. ChamPBH's close is
  `ChamPBH/prompts/dk-and-rpk-migration/11-close-the-migration.md`, its board §5.17 at `:1781`.
- **The packages' boards**, read at their checkouts' `HEAD` (DatastoreKit `2900d82`, RayPoolKit
  `17029d9`, both clean): DatastoreKit's `prompts/extraction/IMPLEMENTATION_STATE.md` G3 at `:1538`,
  G4 at `:1539` (⬜, then its dated italic notes, 2026-10-09 to the `v0.5.0` release); RayPoolKit's
  G2 `:664`, G3 `:665`, G4 `:666` ("not yet (SI adopts `v0.2.0`, when it is next active). Checklist:
  …"). RayPoolKit's `docs/adoption/stochasticinstantons.md` is not in `v0.2.0` (last touched at
  `67f3f7e`): §8 "Its acceptance" `:177`, §9 "What goes stale in it" `:191`. DatastoreKit's at
  `v0.5.0`: §9 `:381`, §10 `:389`, the `v0.5.0` addendum `:782`.
- **The contract's sections at `v0.5.0`:** §1 is "The pool's constructor" (the table lists are its rows
  5, 6 and 13: `replicated_tables`, `sharded_tables`, `read_table_config`); §2 "The keys of
  `register()`" (`owner_column`, `validated_column`, `monotone_flags`); §3 "The factory hooks"; §4 "The
  inventory's declarations"; §7 "The other entry points" (`read_inventory`, `open_read_only`, the
  tools). **§3 carries "superseded in part by §9.5"** on `store`, `validate` and `validate_on_startup`:
  since `v0.2.3` the base defaults them. A pointer to §3 names §9.5 with it.
- **The package's own lines**, installed (= the tag): a row's `serial` is leased from the broker
  unless the payload gives one (`datastorekit/SQL/Datastore.py:793-805`); its `timestamp` is
  `insert_timestamp` if given, else `datetime.now()` (`:809-815`); a replicated write takes one
  `datetime.now()` for every shard (`datastorekit/SQL/ShardedPool.py:3202-3203`). `RayWorkPool`'s
  defaults are `DEFAULT_CREATE_BATCH_SIZE = 5`, `DEFAULT_PROCESS_BATCH_SIZE = 1`,
  `DEFAULT_MAX_TASK_QUEUE = 200` (`raypoolkit/RayWorkPool.py:26-29`); no `timeout` or `cancel` in the
  file. Contract line numbers predate some releases; where a document cites a line, it cites the
  installed package's, read by the agent.

**Where the acceptance can pass vacuously.**
- **A sweep that matches nothing passes "after".** The 246 before, at the agent's starting commit, is
  the non-vacuity; it is in the results note in full (or by file, with the 24 non-dated lines
  verbatim).
- **An `ast` comparison of a file with itself.** "Before" is `git show <start>:<path>`, "after" the
  working tree; docstrings are removed by walking every `Module`, `ClassDef`, `FunctionDef` and
  `AsyncFunctionDef` body, not the module's alone. The script is reproduced in the results note.
- **Counts copied from §1.1.** `CLAUDE.md` and `test-selection.md` carry what the agent's own runs
  print, and the results note shows the runs.
- **A rewritten document that is fluent and wrong.** Every statement about a package in Y1–Y3 has a
  pointer (contract §, README section, or `path:line` in the installed package); the §2.3 list gives
  them all, and a statement with no pointer is the agent's to justify.
- **A G4 draft with an invented figure.** Every SHA in a draft exists in SI and says what the draft
  says it does; every count is a script's or a suite's, at a named commit.
- **Counts by counting**, for `OPEN-ISSUES.md`: see correction 6.

**Corrections to the prompt.** Pass them on.
1. **The board.** Row 12 is `IMPLEMENTATION_STATE.md:78`; Y1–Y7 are `:178-184`; the status line is
   the header's first paragraph (`:3`). The new section is **`### 5.30 After prompt 12 (<date>)`**,
   after §5.29. The list of orchestrator notes (`:94-107`) is the orchestrator's, at the review; the
   agent does not add this note to it.
2. **RayPoolKit's non-`.py` count** is 416 at `f5b9334`, not 402, for the reason §0 gives; it is
   higher again at this note's commit. Report it as §0 says: not a stop.
3. **The second memory note is `shard-key-assignment-bug.md` at the repository root** (tracked), not
   under `.claude/memory/`. **Both notes already say where the fix lives**: each has a dated status
   line from 09 (2026-10-21) naming `datastorekit/SQL/ShardedPool.py` `_assign_shard_keys` at `:3618`,
   the `key_serial` insert at `:3674` and the de-duplication at `:3626`, with both SI commits in the
   root note. Those lines are the same in the installed `v0.5.0`. So Y2's condition ("if either does
   not already say") is not met: **neither is edited**, and the results note says so with the lines
   quoted. They read "`v0.4.0`", which was the pin on that date; that is a dated record, not stale
   prose.
4. **§2.6's order.** Import the layer first, as §0 records; the prompt's order raises at the tag by a
   known, closed-for-the-tree issue. Record the failing order's `ImportError` line too, as the fact
   it is, and put it in the handover: at the tag, `config.datastore` is imported after the layer, as
   the tag's drivers do. "§2.6 does not import" (prompt §4) means the layer-first order failing.
5. **`.prompts/INDEX.md`**: the campaign's row now ends `2026-10-11 → 2026-10-23` (12's writing
   commit), not `→ 2026-10-22`. Its open-issue cell is `§6a; 6` before, `§6a; 4` after. The header
   "Last updated: 2026-10-19 · 6 campaigns: 1 live, 1 halted, 4 complete; 2 more planned" becomes
   0 live, 1 halted, 5 complete, by counting the table.
6. **`OPEN-ISSUES.md`'s counts.** 59 open = 59 rows in §1–§6a. **29 closed is not 29 rows**: §7 has
   24 rows, and a row that names several bracketed issues counts each
   (`[doc-bc-handoff-…]` ×2, `[doc-grid-sampling-…]` ×3, `[doc-hfp-structure-status]` and its two
   neighbours ×3: 24 + 1 + 2 + 2 = 29). After: 57 open, 31 closed (26 rows, counted the same way).
   The results note states the rule and shows the count.
7. **The rehearsal stores** are under `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`,
   483 MB in all at dispatch (each store about 24 MB with its ten shards; with them the readers'
   copies, the profile databases, `02-attempt-1-aborted/`, `02-attempt-2-reader-defect/` and `logs/`).
   The "left for the user" line and the handover give that path and figure.
8. **The suites** are run as the prompt's §2.5 says, with the output to a file in the agent's scratch
   directory. The machine's load was **175** at 01:37 (backups and system services; no suite or Ray
   job): if the default run nears a Bash call's ten-minute cap, split it by file and add the counts.
   The `slow` run goes in the background (`run_in_background`), waited on by its notification, never a
   `sleep` loop; S1's was 390 s, and under this load may be several times that.
9. **Y4's citations** of the package are the installed lines of §0 (`Datastore.py:793-805`,
   `:809-815`; `ShardedPool.py:3202-3203`), re-read by the agent. The two `GLOBAL_BOOKKEEPING` values
   are strings the tool never prints (§1.1); they may be shortened, never given new keys.
10. **The G4 drafts.** DatastoreKit's replaces the **second column** of the G4 row at `:1539`; the first
    ("**G4**: SI adopted `v0.3.0` or later (…)") stays. Its existing italic notes are carried
    **verbatim**: the agent extracts them from the file (not retyped) and the results note shows a
    `diff` of the carried text against the cell's, empty. RayPoolKit's replaces `:666`'s second
    column. Each draft is a fenced block in `verification.md` §4 and the results note, identical in
    both (the review diffs them).
11. **Y3's dated notes** read "rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it
    described is in git at the tag `pre-datastorekit` (`0527480`)", or the agent's equivalent, once
    per rewritten section.
12. **Y6's handover** names the tag's reading order (correction 4) and the store path and size
    (correction 7). The P2 issue is `[hfp-closed-form-audit-not-run]` (`OPEN-ISSUES.md` §2).

**The facts, checked by the orchestrator on 2026-10-23 at `f5b9334`, 01:37–01:55 BST.** Pass them on.
- **The tree.** Branch `dk-and-rpk-migration`, clean; `HEAD` `f5b9334` before this note. No code
  change since `18b490a`.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, ports 6390,
  6391, 8266, 52366 free. No `gcs_server`, `raylet`, `ray::`, `pytest`, `unittest` or `main.py`
  process. `RAY_ADDRESS` unset.
- **The machine.** Load 175 / 112 / 76 at 01:37 (the top processes: `ANECompilerService`,
  ChronoSync, WindowServer, `backupd`, `mds`). Disk 13 GB free (99%). BST until 25 October.
- **DatastoreKit** `2900d82`, **RayPoolKit** `17029d9`, **ChamPBH** `807f175`, **SecondaryGWKit**
  `216e44d`. Read only.
- **The 17 store files** in the tree, and the 1,061 entries under `~/ScienceData/`, recorded with
  their mtimes and sizes (check 12). 12 opens none of them.

**What the review exists to establish.**
- **(E1) Nothing names a deleted file as current** outside `.prompts/` and the dated records; the
  sweep's before and after are the agent's and the orchestrator's alike.
- **(E2) The code is unchanged**: four Python files, prose only, by `ast`; the suites at their counts;
  `ruff` as before.
- **(E3) The instructions and documents are true**: `CLAUDE.md`, the rules and the three documents,
  read in full where they changed, every package statement traced to its source.
- **(E4) The records agree**: the board closed, `.prompts/INDEX.md`, `OPEN-ISSUES.md`,
  `verification.md` §4 and the results note, by counting.
- **(E5) The G4 drafts are true and in their boards' forms**, ready to paste.
- **(E6) The handover is true**: the tag imports, the stores are where it says, the tools exist.
- **(E7) Hygiene**: no store opened, no Ray, nothing installed, nothing outside this repository.

## 1. Before you dispatch

1. **The tree.** `git status --short` clean; `git diff --cached` empty; no code change since `18b490a`.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no Ray process.
3. **The venv.** `pip freeze` saved; `pip check`; the provenance line.
4. **The load and the disk.**
5. **Mtimes**, for check 12: the 17 store files in the tree, and every entry under `~/ScienceData/`,
   by `/usr/bin/stat -f '%m %z %N'`. The four sibling repositories' `HEAD` and status.
6. **§0's measurements**: the sweep, both scripts, the collection counts, `ruff`, §2.6 prototyped,
   the cited records and line numbers, both boards' cells.

**Done 2026-10-23, 01:37–01:55 BST,** at `f5b9334`: all six hold, step 6 as §0 records. In `orch12/` in
the session scratchpad: `sweep.py`, `sweep-head.txt` (246) and `sweep-head-summary.txt`;
`dk-measure.txt`, `rpk-measure.txt`, `rpk-measure-18b490a.txt`; `pip-freeze.txt` (83);
`mtimes-stores.txt` (17), `mtimes-sciencedata.txt` (1,061); `probe/tag_import.py` (the prompt's
order) and `probe/tag_import2.py` (layer first).

## 2. Dispatch

One fresh-context subagent, on **Sonnet**, in the background. Give it:
- the prompt;
- the campaign README and the board;
- `HEAD`, the load, and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad, with `orch12/sweep.py`. It does not read `orchestrator/`.

Tell it plainly:
- **One commit, at the end, made once.** Its results note is
  `.documents/dk-and-rpk-migration/12-close-the-migration.md`, in README §5.1's form, with the prompt's
  §6 list. Stage by explicit path, and show `git diff --cached --name-only` before committing. It
  writes "this commit" for its own hash.
- **The files it may add or change** are the prompt's §5 list, and nothing else; with the memory notes
  left alone (correction 3). **No code beyond Y4's prose, no test, no rehearsal script, not the
  README, not `orchestrator/`, nothing in the venv, nothing in DatastoreKit, RayPoolKit, ChamPBH or
  SGK.** No push, no tag, no merge.
- **It opens no store, runs no build or driver, starts no cluster** (the integration suite's private
  instance aside), and **never runs `ray stop`**.
- **The scratch** is its own subdirectory of the session scratchpad; no scratch file in the repository,
  even for a moment.
- **Stop and ask** on any of the prompt's §4 conditions, as corrected by §0 (the RayPoolKit count and
  §2.6's order are not stops). The orchestrator takes a stop to the user, and the agent resumes by
  `SendMessage`.
- **It replies with:**
  - the results note's path and the commit;
  - the gate and its own §1.1 figures, against the prompt's and §0's;
  - the sweep before (summary by file) and after (every line, classified);
  - Y1–Y4 file by file: what changed, what was checked and left true, and why;
  - the `ast` results and `ruff` counts per Python file;
  - the suites before and after (with the load and times) and the `slow` run;
  - both scripts' figures at its starting commit;
  - §2.6's output, both orders;
  - the two G4 drafts, verbatim, and the verbatim-notes `diff`;
  - the board's §5.30, the `INDEX.md` row and header, and `OPEN-ISSUES.md`'s header and moved rows,
    with how each count was made;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <commit>` touches only the prompt's §5 list (and not the two memory
   notes). One commit of the agent's on this note's, no amend in the reflog, no tag, nothing pushed;
   `git status --short` clean; no scratch file in the repository. `git diff --numstat` on
   `.documents/`: deletions only in `INFRASTRUCTURE.md`, `architecture-summary.md`, `FILE_MAP.md` and
   `OPEN-ISSUES.md`; `verification.md` and every results note only appended to.
2. **E1, the sweep.** `orch12/sweep.py --commit <parent>` prints the 246 lines; on the agent's commit,
   every line is one the prompt's §2.1 allows, at its new place if moved, and each new line names a
   deleted path as deleted. Compared with the agent's after-list: equal.
3. **E2, prose only.** An `ast` script of the orchestrator's own (docstrings stripped at every level)
   on the four Python files, parent against commit: identical but for the two `GLOBAL_BOOKKEEPING`
   string values in `tools/compare_stores.py` and the test module's docstring. `git diff -U0` on each
   shows only comment, docstring or those two strings. `ruff check --select F401,F811,F821`: 0 each.
4. **E3, `CLAUDE.md`.** The diff touches only "Build and test"'s counts, critical rules 2, 3 and 5's
   added pointers (and rule 5's value-table list), and the paragraph after the protected list. The
   counts equal the suites' (check 11). Every protected entry exists in the tree and none is a
   package's file. Both packages are named, pinned to tags in `requirements.txt`, never editable, with
   the upstream rule. Each contract pointer resolves to the section named (§0's map).
5. **E3, the rules.** Each changed rule file's diff read in full. `pool-read-apis.md`'s claim
   corrected and the choice explained. `datastore-factories.md`'s coverage section names
   `inventory_spec()` (contract §4), `values` / `extra_values`, and `EXPECTED_SPECS`, `READ_THROUGH`,
   `EXCLUDED` as `tests/test_inventory_specs.py` spells them (`:106`, `:206`, `:217`); its replication
   section unchanged. `test-selection.md`'s counts are the runs'. Each unchanged rule file's
   "true, unchanged" is spot-checked against the package for one claim each.
6. **E3, the documents.** The rewritten sections of `INFRASTRUCTURE.md` and `architecture-summary.md`
   read in full; each statement about a package traced to the contract, the package README at its
   tag, or the installed code; the `RayWorkPool` sketches give 5 / 1 / 200 or say they are examples;
   each rewritten section has its dated note; no earlier dated note edited. `FILE_MAP.md:54` names
   `inventory_spec()`; the agent's "every row checked" is spot-checked on five rows.
7. **E3, the citations.** A script extracts every `path:line` and `path` in backticks from the diff of
   `CLAUDE.md`, `.claude/rules/`, the three documents and `verification.md` §4, and checks each exists
   (in the tree, at `pre-datastorekit`, or in the installed package, as cited) and that each cited line
   holds what the text says it does, for a sample of ten. The agent's §2.3 list agrees.
8. **E5, the G4 drafts.** `verification.md` §4's two blocks equal the results note's. DatastoreKit's
   cell begins `✅ 2026-10-22: holds.`, follows G3's form, maps checklist §9's parts (with the addenda's
   "`v0.3.0` or later") to `f4da58f`, `1b1ca6d`, `80d99a7`, `19716cd`, `2179854` and the scripts'
   figures, and ends with the existing italic notes, byte-equal to `:1539`'s (re-extracted and
   `diff`ed). RayPoolKit's begins `**holds** 2026-10-20:`, follows G2/G3's form, maps item 8's five
   parts to `ef13445`, `5396a3d` and the figures, names RH1 (`0527480`) and RH2 (`2179854`), and keeps
   the checklist pointer. Every SHA exists and is the commit described.
9. **E4 and E6, `verification.md` §4.** The RH0–RH2 table against §1–§3 (commits, packages, exit
   statuses, `RESULT:` lines, `b0564eec…58a2`); Y5's figures against `measure/out/12-*` and check 10;
   the closing list covers every item of DatastoreKit's §10 and RayPoolKit's §9, each with where done
   or why left; the handover's premises: the tag's reading order (correction 4), the stores' path and
   size, the tools named by their module paths in the installed package, `[hfp-closed-form-audit-not-run]`
   in `OPEN-ISSUES.md` §2.
10. **E2, the measurements.** Both packages' scripts re-run at the agent's commit, each against
    `measure/out/12-*` (differing only in the commit, and in RayPoolKit's `.prompts/` count as §0
    explains); the literal count of `RayTools` as the agent reports it. `pip freeze` equals
    `orch12/pip-freeze.txt`; `pip check` clean.
11. **E2, the suites.** The orchestrator re-runs default and `integration` at the agent's commit: 732
    (731 passed, 1 skipped) and 67 (66 passed, 1 skipped). The agent's `slow` run, 69 passed, read from
    its output; re-run by the orchestrator only if check 3 finds any change to code.
12. **E4 and E7, the records and hygiene.** The board: status **COMPLETE** with the counts; row 12 ✅;
    Y1–Y7; the line after §2's table; the two issues in §4 with how; §3's four others unchanged;
    `### 5.30` with every issue left open and its owner and every decision left to the user.
    `.prompts/INDEX.md`'s row and header, and `OPEN-ISSUES.md`'s header and rows, by counting
    (correction 6), agreeing with the board. The 17 store files and every `~/ScienceData/` entry keep
    their §1 mtimes and sizes; no Ray process; the lock free; the four sibling repositories at their §1
    `HEAD`s, nothing of theirs changed by the agent.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 12* paragraph in §5.30: what each
  check found, and anything handed on. Fix small residue in a follow-up commit of its own:
  - "this commit" → the SHA (board, results note, `verification.md` §4, `INDEX.md`, and the G4 drafts
    if they name it);
  - this note added to the board's list of orchestrator notes, marked "used for 12".
- Anything the review finds that is not residue is opened on the board's §3 and in the index in the
  same commit, which re-opens the campaign's status line; say so to the user.
- **Report to the user:**
  - that the campaign is closed, and on what evidence;
  - **the two G4 drafts, for the user to commit in DatastoreKit and RayPoolKit** (P14), with where each
    goes (`prompts/extraction/IMPLEMENTATION_STATE.md`, the G4 row's second column);
  - the decisions left: the merge of `dk-and-rpk-migration` into `main` (P15); removing the rehearsal
    stores (483 MB); the plot scripts' label and pools (P9, P10); renaming `Datastore` (P6);
  - the handover to P2, in two lines;
  - anything opened.
