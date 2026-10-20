# Orchestrator — prompt 04, adopt `raypoolkit`

Read [`../README.md`](../README.md) first: §0.1 (item 10), §0.5, §2.2 (04's charter), §4.4, §5
(rules 4, 7, 8, 11, 12, 15–17) and §6.2 (P7, P13, P14). The conventions are
[`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged but where this note says otherwise.
ChamPBH's 04 note (`ChamPBH/prompts/dk-and-rpk-migration/orchestrator/prompt-04.md`) and its review
(ChamPBH board §5.5) are the model; what they found that applies to SI is in §0.

**You do not write code.** You may:
- run the suites, RayPoolKit's measuring script (from its root, with its venv) and read-only
  Python checks, from the session scratchpad;
- replay the results note's deliberate-breakage diffs with `git apply`, and revert them;
- make throwaway commit objects for the script with `git commit-tree`, never on a branch;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`04-adopt-raypoolkit.md`](../04-adopt-raypoolkit.md) · **Board items:** W1–W5;
gate **RayPoolKit G4** · **Closes:** nothing · **Narrows:** nothing · **Opens:** one issue for 12
(§0, correction 6), and anything else the work finds · **Model:** Sonnet, as the prompt
recommends · **No network.**

**Gate:**
- 03 landed (`5396a3d`) and was reviewed (`0c3d4b6`); the venv holds `raypoolkit` 0.2.0 at
  `eaef0ce6…`, not editable.
- `HEAD` is the commit that adds this note, or a later one that touches no code ("code" as
  prompt-01.md's gate defines it). `git diff --stat 5396a3d HEAD -- . ':!.prompts' ':!.documents'`
  is empty at `0c3d4b6`.
- One prompt at a time in this checkout, and no other session runs a suite or a Ray job from this
  venv while 04 runs.

## 0. What makes this prompt unusual

**It is the first prompt that changes what the drivers run, and nothing runs them.** The pool
swaps from SI's copy to the package with no driver executed and no Ray started; the run under real
Ray is 07's (RH1). So the evidence is static: RayPoolKit's script, which rebuilds each of the 16
constructions and passes it to the package's own constructor; the `ast` import check; and the
suites. Each can pass vacuously:
- **the script reads git, not the working tree.** At `--commit HEAD` before the agent commits, it
  measures the *old* tree and reports 3 imports and 16 "constructs" whatever is staged. Only a
  commit of the staged tree tells it anything, so §2.3.1 is run at a throwaway commit, and the
  review runs it again at the agent's real commit;
- **the script's verdicts come from RayPoolKit's own venv,** whose `raypoolkit` is imported from
  RayPoolKit's working tree at `17029d9`, not from the tag. That is the tag's code: `git diff
  --stat v0.2.0 17029d9 -- raypoolkit pyproject.toml` is empty and the working tree is clean. The
  header says `Verdicts by: raypoolkit 0.2.0`;
- **the script looks only at `RayTools`.** It counts imports *of a `RayTools` module* and the
  private names in them. An import of a private name from `raypoolkit` is invisible to it
  (correction 7);
- **an import check that finds a module by `sys.path` alone** would find `RayTools` as a namespace
  package after the deletion, because the ignored `RayTools/__pycache__/` survives `git rm` and
  keeps the directory. The directory is residue (the facts, "The tree");
- **W3 and W4 are "these lines and no others".** A stray whitespace or keyword-order change inside
  a call would leave the script's verdicts at "constructs". The review reads the drivers' diff, not
  the counts.

**SI's suites are a real check of two of the three imports.** Unlike ChamPBH's, three default-suite
modules import a plot driver at collection: `tests/test_plot_adapters_golden.py:49` and
`tests/test_plot_extraction_golden.py:59` (`import plot_InstantonSolutions as driver`), and
`tests/test_plot_gradient_coupled_driver.py:43` (`import plot_GradientCoupledSolutions as driver`).
After the change they execute `from raypoolkit import RayWorkPool`. No test imports `main.py`, so
its import is checked by `ast` alone.

**W5 is the part the agent can get wrong while every check passes.** No test reads
`ray-dispatch.md` or the documents. The review compares each corrected statement with the package
at `v0.2.0`, line by line (§3 check 7).

**The prompt was written on 2026-10-12, at `7bb3efd`'s numbers.** Since then 01 added the
provenance lines, `CLAUDE.md` gained the `--ray-address` paragraph, and the board has grown. Nothing
in the package has moved (README §0.5).

**Corrections to the prompt.** Pass them on.
1. **The board section.** The prompt's §3.9 names `### 5.8 After prompt 04`. §5.8 is ChamPBH's
   port fixes, and the board runs to §5.15 (§5.14's last bullet). 04's section is
   **`### 5.16 After prompt 04 (2026-10-20)`**, appended after §5.15. The board's header ("Last
   updated", the status line) is updated to match.
2. **The lines at `0c3d4b6`.** The imports have not moved; everything below them in `main.py` has
   moved by +2, and the plot scripts' calls by +1 (01's provenance import and print):
   - the imports: `main.py:45`, `plot_GradientCoupledSolutions.py:100`,
     `plot_InstantonSolutions.py:72`;
   - **W3's six other lines:** `_run_instanton_queue` (`def` at `:403`) takes `store_handler,` at
     **`:412`** and passes `store_handler=store_handler,` at **`:499`**; its callers pass
     `store_handler=_default_store_handler,` at **`:666`** (STAGE G), **`:826`** (STAGE 2) and
     **`:850`** (STAGE 3); the construction at **`:1094`** passes it at **`:1099`**. (The prompt's
     `:408` for the parameter was wrong at `7bb3efd` too, where the checklist gives `:410`.)
   - the two compute sites W3 leaves: **`main.py:385`** (`pipeline_store_handler`, at `:390`) and
     **`:720`** (`inflaton_trajectory_store_handler`, at `:725`);
   - `CLAUDE.md`'s protected list names `RayTools/` at **`:101`**, not `:95`; its "never modify"
     sentence is `:97-98`;
   - `ray-dispatch.md:99-106`, `FILE_MAP.md:31`, `:287`, `INFRASTRUCTURE.md:353` and
     `architecture-summary.md:27-28`, `:321` are where the prompt says.
3. **The re-measure finds 2 string literals and 1 test module naming `RayTools`.** Neither is a §4
   stop. Both are **module docstrings** added by 01 (`84a5cfc`), not import strings:
   - `.documents/dk-and-rpk-migration/rehearsal/stage_counts.py:16`, which cites
     `RayTools/RayWorkPool.py:181` and `:581-583` "as of dk-and-rpk-migration prompt 01's commit";
   - `tests/test_rehearsal_stage_counts.py:16`, which says how its fixtures were built in 01 "from
     … RayTools/RayWorkPool.py" (`:22`; this is also the test module the script counts).

   Both stay true as dated statements, and **neither is edited**: `stage_counts.py` is frozen until
   07 (07's gate requires the rehearsal scripts unchanged since `5868231`), and the test by README
   §5 rule 7. So §2.3.1's and acceptance 3's "0 string literals" read **2, both these docstrings,
   unchanged by 04**; and §2.3.6's "no test names `RayTools` or `RayWorkPool`" reads "no test
   imports or constructs either". The results note says so, and the G4 text gives the 2 and says
   what they are.
4. **§2.1.2's `git grep` finds two more lines** than the prompt lists:
   `ComputeTargets/GradientCoupledInstanton/picard.py:452` (a comment, below) and
   `tests/test_rehearsal_stage_counts.py:22` (the docstring above). Neither is a stop.
5. **The plot scripts' diff, and `main.py`'s.** W2–W4's "one import line each" and "the import and
   W3's six other lines" stand. Seven changed lines in `main.py`: one modified, six deleted. Nothing
   else in any `RayWorkPool(` call moves.
6. **One §3 issue is opened, for 12** (README §5 rule 4; P13 leaves "the rest of the rewrite" to
   12): **`[pool-prose-stale-after-raypoolkit-adoption]`**, owner **12**, with
   `.documents/OPEN-ISSUES.md` (§6a; header 60 → 61 open) in the same commit. It holds two things
   04 does not fix:
   - `ComputeTargets/GradientCoupledInstanton/picard.py:450-456`, a July comment (`b5a3a9f`) saying
     that "RayTools/RayWorkPool.py (which main.py's own gradient branch dispatches through) is
     protected infrastructure (CLAUDE.md)" and has no per-task timeout hook. After 04 the path is
     gone and the pool is not SI's to protect; the substance still holds (the package has no
     timeout or cancel hook either: no `timeout` or `cancel` in `raypoolkit/RayWorkPool.py` at
     `v0.2.0`). It is not edited: a `ComputeTargets/` file is outside the prompt's §5 list and would
     widen the suites;
   - the constructor sketches at `INFRASTRUCTURE.md:357-373` and `architecture-summary.md:328-344`
     give `create_batch_size=10`, `process_batch_size=10`, `max_task_queue=50` as defaults. The
     copy's and the package's are both **5, 1 and 200** (`DEFAULT_*`, `:26-29` in each). The
     sketches were wrong before 04; 04 does not make them false, so P13 does not reach them.
7. **Breakage 3 is not reported by the script.** The prompt's §2.4.3 says "the script reports a
   private name". It does not: the orchestrator measured it (below), and the script reports **0
   imports and 0 private names**, since `raypoolkit.RayWorkPool` is not a `RayTools` module. Its
   catch is the agent's own import check: **§2.3.3's script also lists every name beginning with
   `_` imported from `raypoolkit` (or a submodule) in the three drivers**, and reports 0 at the
   commit and 1 under breakage 3. `git grep -n _default_store_handler -- main.py` catches it too.
   §2.3.5's check is unaffected (the keyword is still gone). The results note records exactly what
   each check says. G4 item 2's "none of `_default_store_handler`" is shown by the import check and
   the grep, not by the script.
8. **The suites** are run as README §5 rules 16–17 say, serially, in the foreground, with no
   cluster up:
   - `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`;
   - `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`.

   "03's counts" are **680 (679 passed, 1 skipped)** and **61 (60 passed, 1 skipped)**. The `slow`
   block is not run: the diff touches none of its paths (`picard.py` is not edited).
9. **`.prompts/INDEX.md` is the orchestrator's**, at the review. The agent does not touch it.

**From ChamPBH's 04, for SI** (ChamPBH board §5.5; its review passed all eleven checks):
- the ignored `RayTools/__pycache__/` was removed with the empty directory after the `git rm`, and
  logged (its D1);
- the throwaway commit was built from a copy of the index with `commit-tree`, on no branch, and
  nothing was checked out, switched or stashed;
- the import check counted a `from X import Y` whose `Y` is a submodule as resolved when
  `find_spec(f"{X}.{Y}")` resolves;
- breakage 4 ran the import script under a wrapper that sets `sys.modules["raypoolkit"] = None`,
  recorded as a command, not a diff;
- `HEAD` moved under the agent (a planning commit from another session). Check `git log` before
  measuring at `HEAD`.

**The facts, checked by the orchestrator on 2026-10-20 at `0c3d4b6`, 14:15–14:35 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `0c3d4b6` before this note.
  `git diff --cached` is empty. The 17 store files of prompt-01.md §1 step 5 are in the tree
  (ignored); none is the agent's, and 04 opens no store.
  - **`RayTools/__pycache__/`** is ignored (`!!`) and holds two files, `__init__.cpython-313.pyc`
    and `RayWorkPool.cpython-313.pyc` (2026-06-16). After the `git rm`, the agent removes that
    directory and then the empty `RayTools/`, so that no `RayTools` directory remains, and logs it.
    Nothing else is under `RayTools/`.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four
  ports free. `pgrep -fl 'gcs_server|raylet|ray::|pytest|main.py'` finds nothing. `RAY_ADDRESS` is
  unset.
- **The load** was 9.9 / 29.5 / 34.4 at 14:16, then 27 to 32, on 10 CPUs: three Python processes of
  another session, running scripts from ChamPBH's scratchpad with MacPorts' Python, not this venv.
  It affects only times. **The script took over two minutes at that load**: give its Bash call a
  timeout of 600000 ms, or run it in the background.
- **The venv** is as 03 left it. `pip freeze` is `measure/out/7bb3efd-pip-freeze.txt` plus the one
  line `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`;
  `pip check` clean; pip 26.0.1. 04 installs nothing. Every driver prints
  `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **The re-measure (§2.1.1), done by the orchestrator** at `--commit 0c3d4b6`: exit 0; **3 imports**
  (module level, at the three lines of correction 2; 1 naming `_default_store_handler`), **2 string
  literals** (correction 3), **0 `import_module` calls, 16 calls, `constructs` 16, 5 flags on 4
  calls**. Its differences from the `7bb3efd` appendix, each explained:
  - the header's commit, and `Files:` 363 → 420 tracked, 193 → 199 `.py` parsed: 01's tooling and
    tests, and the records;
  - string literals 0 → 2 and test modules 0 → 1 (correction 3);
  - **every call's line moved**: `main.py`'s by **+2** (`:221` → `:223`, … `:1092` → `:1094`), the
    plot scripts' by **+1** (`:938` → `:939`, `:1171` → `:1172`). The flags moved likewise (`:396`
    → `:398`, `:505` → `:507`, `:729-730` → `:731-732`, `:1107` → `:1109`). Every other column is
    unchanged;
  - non-`.py` lines naming `RayTools` or `RayWorkPool` 89 → 256: `.prompts/` 27 → 183 (this
    campaign's records) and `.documents/` 44 → 55 (01's and 03's results notes and
    `verification.md`); `CLAUDE.md:95` → `:101`.
- **`git grep -n -e RayTools -e _default_store_handler -- ':!.prompts' ':!.documents' ':!.claude'
  ':!CLAUDE.md'`** gives 11 lines: `RayTools/RayWorkPool.py:79`, `:94`; the three imports; the four
  uses at `main.py:666`, `:826`, `:850`, `:1099`; `picard.py:452`; and
  `tests/test_rehearsal_stage_counts.py:22`. (It does not find `:412` and `:499`, which name only
  `store_handler`.)
- **The throwaway commit, done by the orchestrator.** Build it without a branch, and without
  touching the real index or working tree:
  - **read the real index's path before setting the variable**: `REAL=$(git rev-parse --git-path
    index); cp "$REAL" <scratch>/idx; export GIT_INDEX_FILE=<scratch>/idx`. (Exported first,
    `git rev-parse --git-path index` names the copy itself, and the commit gets an empty tree; the
    orchestrator's first attempt did this, and the script then reports 0 files);
  - then `git rm --cached` or `git update-index --cacheinfo` (with `git hash-object -w`) under the
    variable, `git write-tree`, `git commit-tree <tree> -p HEAD -m …`, and `unset GIT_INDEX_FILE`.
    For the agent's real staged change, `git write-tree` of the real index will do.

  The commit is dangling and `git gc` collects it. **Never `git checkout`, `switch` or `stash`**
  with the change staged. With W1–W3 applied (the documents untouched) the orchestrator's
  throwaway `bc04d68` measured: `RayTools/` table empty, **0 imports, 0 private names, 2 string
  literals (the docstrings), 0 `import_module` calls, 16 calls, `constructs` 16**, `Files:` 418
  tracked. The two compute sites W3 touches (`main.py:493`, `:1089` there) show `store_handler`
  absent (—); the handler-spelling table has two rows of compute sites where it had one. The lines
  below `:412` move by −1 to −6, as the deletions above them.
- **Breakage 3, measured by the orchestrator** at `dd64b29` (`bc04d68`'s tree with
  `from raypoolkit.RayWorkPool import _default_store_handler` added as `main.py:46`): **0 imports,
  0 private names**; the lines below `:46` move by +1 and nothing else changes (correction 7).
- **The package's constructor defaults equal the copy's**: `5`, `1`, `200`, `500`, `300`, `60`
  (`DEFAULT_*`, `RayTools/RayWorkPool.py:26-32` and `raypoolkit/RayWorkPool.py:26-32` at the tag),
  and the keywords are the same, in the same order. The only signature difference is `pool`'s hint,
  `ShardedPool` → `DatastorePool`. So no site that leaves a size at its default changes.
- **The package, at the tag** (`git -C /Users/ds283/Documents/Code/RayPoolKit show
  v0.2.0:raypoolkit/RayWorkPool.py`), for `ray-dispatch.md:99-106`. The rule's three behaviours:
  - `if obj.available:` at **`:385`** (inside `if hasattr(obj, "available"):`, `:384`): a direct
    attribute read;
  - the compute handler called on the driver at **`:424-426`**
    (`compute_task: ObjectRef = self._compute_handler(obj, **compute_args)`), whose default is
    `obj.compute(**kwargs)` (`:75-76`): it must return an `ObjectRef`, and the pool never calls
    `.remote()` on the object;
  - the store handler called on the driver at **`:471`** (`self._store_handler(obj, self._pool)`),
    whose default is `obj.store()` (`:79-80`); then the persist handler at `:481`.

  Either these lines, or the behaviours without line numbers (the prompt allows both). Name the
  package as `raypoolkit.RayWorkPool`, pinned in `requirements.txt`.
- **The other W5 lines, at `0c3d4b6`:**
  - `CLAUDE.md:101` is `RayTools/                          Datastore/SQL/ShardedPool.py`. The
    smallest change that keeps the list's form is that line with `Datastore/SQL/ShardedPool.py`
    alone, as the list's single-entry lines are. One line changes in `CLAUDE.md`;
  - `FILE_MAP.md` maps a "claude-context flat layout" of verbatim copies (its `:1-6`); no such
    directory is in the tree. `:31` is the `RayTools_RayWorkPool.py` | `RayTools/RayWorkPool.py`
    row; it says instead that the queue is `raypoolkit.RayWorkPool`, the package pinned in
    `requirements.txt`, not a file of this repository. `:287`, `RayTools/ (other files)` in the
    "omitted" table, describes a directory that is gone and had no other files: delete the row, or
    say the same; either is an `IMPLEMENTATION CHOICE`;
  - `INFRASTRUCTURE.md:353` and `architecture-summary.md:321` each name the file in their opening
    sentence; `architecture-summary.md:27-28` are the layout's `RayTools/` and
    `  RayWorkPool.py               — distributed work-queue abstraction`. ChamPBH made its pair
    one line in parentheses naming the package and its pin. Nothing else in these documents
    changes (correction 6 for the sketches).
  - **Left as they are**: the lines the checklist's item 9 lists as staying true; the dated
    records it names (`gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md:75` and the
    rest); this campaign's results notes and `verification.md`; every line under `.prompts/`.
- **The model list.** `config/model_list.py` and `config/pipeline_setup.py` are unchanged since
  `7bb3efd` (`git diff --stat` empty). `run_all_pipelines` (`main.py:672`) is called only at
  `:1213`, with `inputs["model_list"]` (`:1155`). The checklist's item 4 reading holds at their
  current lines; the agent cites them.
- **`utilities.format_time`** is also imported by `Datastore/SQL/ProfileAgent.py:26` and
  `Quadrature/simple_quadrature.py:27`, so it is not dead after the copy goes. It is not touched.
- **The stores.** 04 opens none: not the 17 in the tree, not 02's under
  `~/ScienceData/StochasticInstantons-rehearsals/`, not anything else under `~/ScienceData/`.
- **RayPoolKit** at `/Users/ds283/Documents/Code/RayPoolKit`: `HEAD` `17029d9`, working tree clean.
  The script writes nothing, and the orchestrator's three runs left the tree clean.

**What the review exists to establish.**
- **(E1) W1.** `git ls-tree <commit> RayTools` is empty, and no `RayTools` directory is left in the
  working tree.
- **(E2) W2–W4.** The plot scripts' diff is the import line each; `main.py`'s is the import and the
  six lines of correction 2; no other line of any pool site moved.
- **(E3) By the script, at the real commit:** 0 imports, 0 `import_module` calls, the 2 docstring
  literals and nothing else, 16 calls, every one "constructs", the flags checked by hand.
- **(E4) The imports resolve** by `ast`, with no private `raypoolkit` name; the drivers
  byte-compile; §2.3.5 holds; the four breakages are caught, as correction 7 says for the third.
- **(E5) W5.** Only the named lines change, and each corrected statement agrees with the package at
  `v0.2.0`.
- **(E6) Nothing else moved.** No file outside the prompt's §5 list, the issue's index row
  excepted; the venv's freeze as 03 left it; no store opened; RayPoolKit untouched; the suites at
  680 and 61.
- **(E7) The records.** The board's §1 row, W1–W5, the **RayPoolKit G4** row of §2 (holds, by
  checklist item 8, items 1–5, RH1 to add the run under real Ray and item 6 to 12),
  `### 5.16 After prompt 04 (2026-10-20)`, the §3 issue with its index row; the results note
  carries the G4 text for 12.

**Conventions particular to 04.** prompt-01.md's conventions hold (the venv: nothing installed or
uninstalled). In addition:
- **git.** The only commit on `dk-and-rpk-migration` is the agent's one. Throwaway commits are made
  with `commit-tree` as above, on no branch. No `checkout`, `switch`, `stash`, `reset --hard` or
  `rebase`. The two deletions are staged with `git rm`.
- **RayPoolKit.** Its script is run from its root with its own venv (`cd` into it inside the one
  command, output redirected to the agent's scratch). Its files are read with `git -C … show` or
  directly; nothing there is written.
- **Ray.** None is started, and no driver is imported or run by the agent's own scripts. The
  suites' imports of the plot drivers (above) are the suites', and start no Ray.
- **Formatting.** No file is reformatted (README §5 rule 15); in particular `ruff format` is not
  run on the drivers.

## 1. Before you dispatch

1. **The tree.** Record the branch and `HEAD`. `git status --short` is clean and `git diff
   --cached` empty. `git log --oneline 0c3d4b6..HEAD` touches no code.
2. **Ray and the lock.** `ray_cluster.sh status` clean; `pgrep` finds no Ray process.
3. **The venv.** `pip freeze` saved in the scratchpad; it equals the committed
   `measure/out/7bb3efd-pip-freeze.txt` plus the one `raypoolkit` line. `pip check` clean.
4. **The load.** `uptime`, recorded and passed on.
5. **Mtimes**, for check 9: the 17 store files in the tree, and every entry under `~/ScienceData/`,
   by `/usr/bin/stat -f '%m %z %N'`, saved in the scratchpad. RayPoolKit's `git status
   --porcelain` is empty; its `HEAD` recorded.
6. **The re-measure**, the throwaway measure and breakage 3's measure, saved in the scratchpad,
   for comparison with the agent's.

**Done 2026-10-20, 14:15–14:35 BST,** at `0c3d4b6`: all six hold. The freeze, the three measures
(`measure-0c3d4b6.md`, `measure-throwaway.md` at `bc04d68`, `measure-b3.md` at `dd64b29`), the
scratch drivers and the mtimes (17 store files; 607 entries under `~/ScienceData/`, 433 of them
SI's rehearsal root) are in `orch04/` in the session scratchpad. RayPoolKit `HEAD` `17029d9`, clean.

The suites are not re-run by the orchestrator before dispatch: no Python has changed since
`5396a3d`, whose review re-ran them, and the agent runs them.

## 2. Dispatch

One fresh-context subagent, on **Sonnet**. Give it:
- the prompt;
- the campaign README and the board;
- 03's results note (the venv, and the provenance line);
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read prompts 05–07.

Tell it plainly:
- **One commit, at the end.** Its results note is
  `.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md`, in README §5.1's form, with the
  prompt's §6 additions.
- **The files it may change** are the prompt's §5 list and `.documents/OPEN-ISSUES.md` for the
  issue of correction 6. **No test, no `ComputeTargets/` file, nothing in RayPoolKit, nothing in
  the venv, not the README, not `.prompts/INDEX.md`.**
- **The script runs at a commit, not the working tree**: at a throwaway `commit-tree` commit, on no
  branch, built as §0 says.
- **Stop and ask** on any of the prompt's §4 conditions. The two docstrings and the `picard.py`
  comment of §0 are not stops.
- **It replies with:**
  - the results note's path and the commit;
  - `git diff --cached --name-only` as committed, and the drivers' diff;
  - the re-measure's totals and its difference from the `7bb3efd` appendix, explained;
  - the measure at the throwaway commit: totals and verdicts, and the flags' hand-check;
  - the import-resolution script's output (with its private-name count), and `py_compile`;
  - the four breakages and what caught each;
  - the W5 diff, file by file;
  - the two suites, with the load;
  - every deviation with its class;
  - the RayPoolKit G4 record, and the "State handed to the next prompt" section, verbatim.

## 3. The review — eleven checks

1. **Scope.** `git show --stat <commit>` touches only the two deletions, the three drivers,
   `CLAUDE.md`, `.claude/rules/ray-dispatch.md`, `FILE_MAP.md`, `INFRASTRUCTURE.md`,
   `architecture-summary.md`, the results note, the board and `.documents/OPEN-ISSUES.md`. `git
   status --short` is clean; `ls RayTools` fails. `git log` since this note shows no other commit of
   the agent's, and `git branch` no leftover branch.
2. **E1–E2, the diff.** `git ls-tree <commit> RayTools` is empty. `git diff <commit>~1 <commit> --
   main.py plot_GradientCoupledSolutions.py plot_InstantonSolutions.py`: one modified line in each
   plot script, at `:100` and `:72`; in `main.py` the import at `:45` and the six deletions at
   `:412`, `:499`, `:666`, `:826`, `:850`, `:1099`, and nothing else. No other line in any
   `RayWorkPool(` call moved.
3. **E3, the script at the real commit.** Run `measure_client_pools.py si --commit <agent's
   commit>` from RayPoolKit's root: 0 imports, 0 private names, the 2 docstring literals, 0
   `import_module` calls, 16 calls, `constructs` 16. Diff against the orchestrator's `bc04d68`
   measure: only the header, `Files:`, the non-`.py` count and table (the documents and records the
   commit changes) move; every call row equals it. Compare with the agent's throwaway measure: the
   same verdicts.
4. **E4, imports.** Re-run the results note's import-resolution script, as kept there, from the
   repository root: every import resolves, 0 private `raypoolkit` names, `ray.is_initialized()`
   `False`. `py_compile` of the three drivers succeeds.
5. **E4, breakages.** Replay breakages 1–3 with `git apply` from the clean tree (`--check` and
   `-R --check` first, in `bash`):
   - 1 fails the import check on `main.py:45`, module not found; at a throwaway commit of it, the
     script reports 1 import;
   - 2 fails it on `plot_InstantonSolutions.py:72`, no such name;
   - 3 passes resolution and is caught by the private-name count (1) and the grep; the script's
     verdict equals §0's (`dd64b29`: 0 imports, 0 private names);
   - 4: the `sys.modules` wrapper, three failures.

   Revert each; `git status` clean after.
6. **The venv.** `pip freeze` equals §1's copy; `pip check` clean. Nothing installed or removed.
7. **E5, W5, line by line.** `git diff <commit>~1 <commit>` of `CLAUDE.md` is the one line `:101`;
   of `ray-dispatch.md`, only within `:99-106`; of `FILE_MAP.md`, rows `:31` and `:287`; of
   `INFRASTRUCTURE.md`, `:353`; of `architecture-summary.md`, `:27-28` and `:321`. Each corrected
   statement names `raypoolkit` and its pin in `requirements.txt`, and the three behaviours of the
   rule agree with the package at `v0.2.0` (§0's lines, or without numbers). The rule's argument is
   unchanged. Nothing claims a feature the package lacks.
8. **The results note's measurements.** The re-measure's explanation matches §0's (+2 / +1; the
   docstrings; the counts). The throwaway measure is at a commit whose code equals the committed
   code (`git diff --name-only <throwaway> <commit>` lists only documents, the board, the note and
   the index, or nothing).
9. **E6, hygiene.** RayPoolKit's `git status --porcelain` empty, `HEAD` `17029d9`. The §1 mtimes of
   the 17 store files and of SI's rehearsal root are unchanged (the rest of `~/ScienceData/` is
   other projects', reported but not held against the agent). No Ray process; the lock free. No
   scratch file in either repository.
10. **E6, the suites.** The agent's: 680 (679 passed, 1 skipped) and 61 (60 passed, 1 skipped),
    with the load. The orchestrator re-runs both at the agent's commit: this is the first commit at
    which the plot-driver tests import `raypoolkit`.
11. **E7, the records.** The board's §1 row (✅, "this commit", the results note), W1–W5, the
    RayPoolKit G4 row of §2 (✅ holds, items 1–5, RH1 to add the run under real Ray and item 6 to
    12), and `### 5.16 After prompt 04 (2026-10-20)` naming the rollback (`git revert` alone;
    README §4.4: the installed package is inert). The §3 entry for
    `[pool-prose-stale-after-raypoolkit-adoption]` has its index row, the count (61) and date in the
    same commit. The results note follows README §5.1, carries the G4 text for 12, and every §2
    check's command and output.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 04* paragraph in §5.16: what each
  check found, and anything handed on to 05. Fix small residue in a follow-up commit of its own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 04";
  - `.prompts/INDEX.md`: the campaign's line (04 landed, RayPoolKit G4 holds).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:**
  - the swap in one line (files deleted, imports rewritten, the private name dropped, no other site
    changed);
  - the script at the commit: imports, literals, verdicts;
  - the documentation corrections;
  - the suites;
  - RayPoolKit G4, with the two docstring literals, and the issue opened.
- **Then 05** can be dispatched; its note is written after this review, with the call-site lines
  at 04's commit.
