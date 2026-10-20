# Orchestrator — prompt 03, pin `raypoolkit` `v0.2.0`

Read [`../README.md`](../README.md) first: §0.2 ("The venv"), §0.5 (RayPoolKit as of 2026-10-19),
§2.2 (03's charter), §4.4 and §5 (rules 11–13, 16, 17). The conventions are
[`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged but where this note says otherwise.
ChamPBH's 03 note (`ChamPBH/prompts/dk-and-rpk-migration/orchestrator/prompt-03.md`) and its review
(ChamPBH board §5.4) are the model; what they found that applies to SI is in §0.

**You do not write code.** You may:
- run the suites, `pip freeze`, `pip check`, `pip show` and read-only Python checks of the
  installed package, from the session scratchpad;
- extract `git archive v0.2.0` into the scratchpad;
- fix small residue in a follow-up commit of your own (§4).

You do not install, uninstall or upgrade anything in the venv. If the agent leaves it wrong, that is
a finding for the user, not something the review repairs.

**The prompt:** [`03-pin-raypoolkit-v0.2.0.md`](../03-pin-raypoolkit-v0.2.0.md) · **Board items:**
K1–K3 · **Closes:** nothing · **Narrows:** nothing · **Opens:** only what the work finds ·
**Model:** Sonnet, as the prompt recommends · **Needs the network** (GitHub for the tag, PyPI for
the isolated build's `setuptools`).

**Gate:**
- 02 landed (`5868231`) and was reviewed (`7ceb089`); gate RH0 holds (board §2).
- `HEAD` is the commit that adds this note, or a later one that touches no code ("code" as
  prompt-01.md's gate defines it, which includes `requirements.txt`).
  `git diff --stat 5868231 HEAD -- . ':!.prompts' ':!.documents'` is empty at `8761c07`.
- One prompt at a time in this checkout, and **no other session installs into this venv, or runs
  a suite or a Ray job from it, while 03 runs**: the venv is shared (README §4.4).

## 0. What makes this prompt unusual

**It is the first prompt that changes the venv, and the venv is outside git.** A revert of 03's
commit does not undo the install (README §4.4). So the review's evidence is the venv itself, read
after the commit, not the results note's account of it.

**Its acceptance is "one distribution added, and it is the tag".** Each half can pass vacuously:
- *one added*: if the "before" freeze was taken after the install, or compared with the wrong
  file, the diff proves nothing. The review compares the venv's freeze now with the committed
  `measure/out/7bb3efd-pip-freeze.txt`, not with the agent's scratch copy;
- *the tag*: an editable install, or one from the local checkout, would carry the right version
  string and import cleanly. Only `direct_url.json` (no `dir_info`, `vcs_info.commit_id`
  `eaef0ce6…`) and the byte comparison with `git archive v0.2.0` tell them apart.

**Nothing imports the package yet, so the suites cannot fail because of it.** They are the check
that nothing *else* moved. "No deliberate breakage" is the prompt's own ruling (§3.4).

**The prompt was written on 2026-10-12, before 02.** Since then the board has grown and 05–07 are
written. Nothing in the package or the venv has moved (README §0.5; the facts below).

**Corrections to the prompt.** Pass them on.
1. **The board section.** The prompt's §3.5 names `### 5.7 After prompt 03`. §5.7 is 01a's, and
   the board runs to §5.14 (board §5.14's last bullet). 03's section is
   **`### 5.15 After prompt 03 (2026-10-20)`**, appended after §5.14. The board's header
   ("Last updated", the status line) is updated to match.
2. **The suites** are run as README §5 rules 16–17 say, both after the install, serially, with no
   cluster up:
   - `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`;
   - `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`.

   "01's counts" are **680 (679 passed, 1 skipped)** and **61 (60 passed, 1 skipped)**, the
   figures every review since 01 has re-run (last at `5868231`). The `slow` block is not run: the
   diff touches none of its paths.
3. **`pip` itself is not upgraded.** Every pip command prints
   `[notice] A new release of pip is available: 26.0.1 -> 26.2.1`. It is ignored. `pip freeze`
   does not list pip, so an upgrade would not show in K3's diff, but it would change the venv,
   which the prompt allows to change by `raypoolkit` alone.
4. **`.prompts/INDEX.md` is the orchestrator's**, at the review, as for 02. The agent does not
   touch it.

**From ChamPBH's 03, for SI** (ChamPBH board §5.4; its review passed all ten checks):
- **`Resolved https://github.com/ds283/RayPoolKit to commit 4e7eb153…`** names the **tag
  object**, not the commit: pip reports the unpeeled ref there, and its `git checkout -q
  4e7eb153…` checks out the tag. The commit recorded in `direct_url.json`, and so in `pip freeze`
  and the provenance helper, is `eaef0ce6…`. The results note quotes the line and says this. **It
  is not the prompt's "installed commit is not `eaef0ce6`" stop**; that stop is judged on
  `pip freeze` and `direct_url.json`.
- **The recorded URL has no `git+`** (PEP 610). `utilities.format_package_provenance` prints it as
  recorded (its docstring, `utilities.py:232-244`; 01's results note), so the line is the one
  below.
- `Installing build dependencies … done` fetches `setuptools>=64` into a temporary, isolated build
  environment, not into the venv.
- The built wheel goes to a temporary directory. Pip does not keep a wheel built from a VCS tag in
  its persistent cache.
- The dist-info's `RECORD` lists the four modules and their `.pyc` files; ChamPBH's hashes all
  matched.

**The facts, checked by the orchestrator on 2026-10-20 at `8761c07`, 09:20–09:35 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `8761c07` before this note. The 17
  store files of prompt-01.md §1 step 5 are in the tree (ignored); none is the agent's, and 03
  opens no store.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four
  ports free. `pgrep -fl 'gcs_server|raylet|ray::|pytest|main.py'` finds nothing. `RAY_ADDRESS`
  is unset.
- **The load** was 22.7 / 17.8 / 11.0 on 10 CPUs, from macOS daemons (`UsageTrackingAgent`,
  Spotlight, `mobileassetd`), with no suite or Ray job running. It affects only the suites' times.
- **The venv.**
  - Python 3.13.16; pip 26.0.1.
  - `pip show datastorekit raypoolkit` finds neither.
  - **`pip freeze` equals `measure/out/7bb3efd-pip-freeze.txt` byte for byte** (81 lines).
  - `pip check`: "No broken requirements found."
- **`requirements.txt`** has 71 lines, last changed at `7f4122b` (2026-06-16).
  - **`:57` is `ray==2.55.1` and `:58` is `referencing==0.37.0`**, as the prompt says. With the
    pin the file has 72 lines, the pin at `:58`.
  - Every line of it is in the freeze, exactly. The freeze has ten more (`iniconfig`, `joblib`,
    `narwhals`, `pluggy`, `pyflakes`, `Pygments`, `pytest`, `ruff`, `scikit-learn`,
    `threadpoolctl`), installed but not required. `pip install -r` leaves them alone. So
    `pip install -r` has nothing to do but the new line.
  - The order is `pip freeze`'s (`aiohttp-cors` before `aiohttp`, for instance), not
    `sort -f`'s. `ray` < `raypoolkit` < `referencing` either way.
- **The tag.** `git ls-remote --tags https://github.com/ds283/RayPoolKit` lists only `v0.1.0` and
  `v0.2.0`: `4e7eb153ca9837c6aa6ec51d702b5fa6ccf08fef refs/tags/v0.2.0` and
  `eaef0ce60e2fc354bb32f0ad576010e6a83c1976 refs/tags/v0.2.0^{}`. The local checkout at
  `/Users/ds283/Documents/Code/RayPoolKit` agrees. Its `HEAD` is `17029d9`, later than the tag
  (documents only, README §0.5), and its working tree is clean. Neither matters:
  `git archive v0.2.0` reads the tag.
- **The tag's package.** `git archive v0.2.0 raypoolkit` holds 4 `.py` files outside `tests/`
  (`__init__.py`, `RayWorkPool.py`, `_timing.py`, `contract.py`) and 9 under `raypoolkit/tests/`.
  `pyproject.toml` at the tag: `setuptools>=64` build backend, `version = "0.2.0"`,
  `requires-python = ">=3.12"`, `dependencies = ["ray>=2.43"]`, `include-package-data = false`,
  `packages.find` excluding `raypoolkit.tests*`.
- **The dry run, done by the orchestrator** with a scratch copy of `requirements.txt` holding the
  pin at line 58: exit 0, 4.2 s; 71 "Requirement already satisfied" lines and
  **`Would install raypoolkit-0.2.0`**, nothing else. Its `--report` gives `download_info`
  `{"url": "https://github.com/ds283/RayPoolKit", "vcs_info": {"vcs": "git", "requested_revision":
  "v0.2.0", "commit_id": "eaef0ce60e2fc354bb32f0ad576010e6a83c1976"}}`. It printed the `Resolved …
  4e7eb153…` line above, and pip's upgrade notice.
- **The provenance helper.** `utilities.installed_package_provenance(names=RECORDED_DISTRIBUTIONS)`
  (`utilities.py:177`), with `RECORDED_DISTRIBUTIONS = ("datastorekit", "raypoolkit")` (`:174`),
  so it is called with no argument. Today it prints
  `>> packages: datastorekit not installed; raypoolkit not installed`. After the install the
  expected line is
  `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`,
  which is what 07's prompt expects in every RH1 log (`07-…md:167-170`).
- **No test depends on the venv's real state.** `git grep -i raypoolkit` outside `.prompts/`,
  `.documents/` and Markdown finds only `RECORDED_DISTRIBUTIONS` and its comment (`utilities.py`),
  `test_package_provenance.test_default_names` (which checks the keys, not the values), and the
  fixture string `PACKAGES` in `test_rehearsal_stage_counts.py:42`, a stand-in log line. So the
  install moves no test.
- **The stores.** 03 opens none: not the 17 in the tree, not 02's under the SI rehearsal root, not
  anything else under `~/ScienceData/`.

**What the review exists to establish.**
- **(E1) K1.** The diff of `requirements.txt` is one added line, exactly the pin, at `:58`, between
  `ray==2.55.1` and `referencing==0.37.0`.
- **(E2) K2, the venv moved by one distribution.** The freeze now differs from the committed
  `7bb3efd-pip-freeze.txt` by exactly the one line
  `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`;
  `pip check` is clean.
- **(E3) K3, it is the tag.** `direct_url.json` is a VCS record with that commit and
  `requested_revision` `v0.2.0`, and no `dir_info`. The installed files are the tag's four, byte
  for byte, and nothing else. The import starts no Ray.
- **(E4) The helper sees it.** The provenance line is the one above.
- **(E5) Nothing else moved.** No file but `requirements.txt`, the results note and the board (and
  `.documents/OPEN-ISSUES.md`, if an issue opened); RayPoolKit's checkout untouched; no store
  opened; the suites at 680 and 61.
- **(E6) The records.** The board's §1 row, K1–K3, `### 5.15 After prompt 03` with the rollback.

**Conventions particular to 03.** prompt-01.md's conventions hold, except that **this prompt
installs**, exactly once, as its §1 K2 says. In addition:
- **pip.** Only the two commands the prompt names change or probe the venv: the dry run, then the
  install, both `-r requirements.txt` from the repository root. No `-e`, no local path, no
  `--upgrade`, `--force-reinstall`, `--no-deps`, `--no-build-isolation`, no upgrade of pip, and no
  `pip uninstall` except to restore after a stop (prompt §4). `pip freeze`, `pip check` and
  `pip show` are free.
- **The archive** is extracted into a new directory in the agent's scratch, never inside either
  repository.
- **RayPoolKit** is read through `git -C … show`, `archive`, `rev-parse`, `ls-remote` and its
  files, never written, and no command runs from its root.
- **Ray.** None is started: no `ray_cluster.sh`, no driver. The import check is the prompt's
  one-liner. **Never `ray stop`.**

## 1. Before you dispatch

1. **The tree.** Record the branch and `HEAD`. `git status --short` is clean and `git diff
   --cached` empty. `git log --oneline 8761c07..HEAD` touches no code.
2. **Ray and the lock.** `ray_cluster.sh status` clean; `pgrep` finds no Ray process.
3. **The venv.** `pip show datastorekit raypoolkit` finds neither, and `pip freeze` equals
   `measure/out/7bb3efd-pip-freeze.txt`. Save the freeze in the scratchpad.
4. **The load.** `uptime`, recorded and passed on.
5. **Mtimes**, for check 8: the 17 store files in the tree, and every entry under `~/ScienceData/`,
   by `/usr/bin/stat -f '%m %z %N'`, saved in the scratchpad. RayPoolKit's `git status
   --porcelain` is empty; its `HEAD` recorded.

**Done 2026-10-20, 09:20–09:35 BST,** at `8761c07`: all five hold. The freeze, the dry run and its
report, the mtimes (17 store files; 607 entries under `~/ScienceData/`) are in `orch03/` in the
session scratchpad. RayPoolKit `HEAD` `17029d9`, clean.

The suites are not re-run by the orchestrator before dispatch: no Python has changed since
`5868231`, whose review re-ran them, and the agent runs them (§0).

## 2. Dispatch

One fresh-context subagent, on **Sonnet**. Give it:
- the prompt;
- the campaign README and the board;
- 01's results note (for the provenance helper);
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read prompts 04–07.

Tell it plainly:
- **One commit, at the end.** Its results note is
  `.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md`, in README §5.1's form, with the
  prompt's §6 additions.
- **The files it may change** are the prompt's §5 list (`requirements.txt`, the results note, the
  board) and `.documents/OPEN-ISSUES.md` if an issue opens. **No code, no test, nothing in
  RayPoolKit, not the README, not `.prompts/INDEX.md`.**
- **It installs once,** after a dry run that reports only `raypoolkit`, and from the tag on
  GitHub.
- **Stop and ask** on any of the prompt's §4 conditions. If pip has moved anything but
  `raypoolkit`, it records exactly what, restores it from the saved freeze, and stops without
  committing.
- **It replies with:**
  - the results note's path and the commit;
  - the `requirements.txt` diff;
  - the dry run's and the install's lines other than "Requirement already satisfied";
  - the freeze diff, `pip check`, and the provenance line;
  - `direct_url.json` verbatim, and the file comparison's counts and result;
  - the import check's output;
  - the two suites, with the load;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — ten checks

1. **Scope.** `git show --stat <commit>` touches only `requirements.txt`, the results note and the
   board (and `.documents/OPEN-ISSUES.md`, if an issue opened). `git status --short` is clean.
   `git log` since this note shows no other commit of the agent's.
2. **E1, K1.** `git show <commit> -- requirements.txt` is the one line, at `:58`, between
   `ray==2.55.1` and `referencing==0.37.0`; `wc -l` gives 72.
3. **E2, the freeze.** `./venv/bin/pip freeze`, diffed against the **committed**
   `measure/out/7bb3efd-pip-freeze.txt`: exactly one added line, the `eaef0ce6…` one, and nothing
   removed or changed. Also against §1's scratch copy: the same. `pip check` clean.
4. **E3, the origin.** Read `raypoolkit-0.2.0.dist-info/direct_url.json` in site-packages directly:
   `url` `https://github.com/ds283/RayPoolKit`, `vcs_info.vcs` `git`, `commit_id` `eaef0ce6…`,
   `requested_revision` `v0.2.0`, and no `dir_info`. `INSTALLER` is `pip`. No `__editable__*`,
   `*.pth` or `.egg-link` naming RayPoolKit in site-packages.
5. **E3, the files.** From the scratchpad: extract `git -C <RayPoolKit> archive v0.2.0 raypoolkit`
   into a new directory, and compare with `find_spec("raypoolkit").submodule_search_locations[0]`,
   ignoring `__pycache__`: the same 4 `.py` files, byte for byte (`cmp`), no `tests/`, nothing
   else. Then the dist-info's `RECORD`: every `raypoolkit/` entry is one of the four (or a
   `__pycache__` file), and each listed hash matches the installed file.
6. **E3–E4, the import and the helper.** The prompt's import one-liner prints `False`. In a fresh
   process, `installed_package_provenance()` gives exactly `version` `0.2.0`, the URL, commit and
   revision above, `editable: False`, and `datastorekit` `None`; `format_package_provenance`
   prints §0's expected line. `pip show raypoolkit` gives `Requires: ray`.
7. **The pip account.** The results note shows the dry run's `Would install raypoolkit-0.2.0` and
   nothing else, and the install's `Successfully installed raypoolkit-0.2.0` and nothing else. It
   quotes the `Resolved … 4e7eb153…` line and says it is the tag object. pip is still 26.0.1.
8. **E5, hygiene.** RayPoolKit's `git status --porcelain` is empty and its `HEAD` is still
   `17029d9`. The §1 mtimes of the 17 store files and of `~/ScienceData/` are unchanged. No Ray
   process; the lock free. No scratch file in either repository.
9. **E5, the suites.** The agent's: 680 (679 passed, 1 skipped) and 61 (60 passed, 1 skipped),
   with the load. The orchestrator re-runs both at the agent's commit, since the install is the
   only change and the suites are its proof that nothing else moved.
10. **E6, the records.** The board's §1 row (✅, "this commit", the results note), K1–K3, the
    header, and `### 5.15 After prompt 03 (2026-10-20)` naming the rollback (`git revert` plus
    `./venv/bin/pip uninstall -y raypoolkit`). Any §3 entry has the index's row, count and date in
    the same commit. The results note follows README §5.1, with every §2 check's command and
    output.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 03* paragraph in §5.15: what
  each check found, and anything handed on to 04. Fix small residue in a follow-up commit of its
  own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 03";
  - `.prompts/INDEX.md`: the campaign's line (03 landed).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:**
  - the pin, and the freeze diff in one line;
  - the origin and the file comparison;
  - the provenance line every driver now prints;
  - the suites;
  - anything opened.
- **Then 04** can be dispatched; its note is written after this review.
