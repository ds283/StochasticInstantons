# Orchestrator — prompt 08, pin `datastorekit` `v0.4.0`

Read [`../README.md`](../README.md) first: §0.4, §0.5, §2.2 (08's charter), §4.4 and §5 (rules
11–13, 16, 17). The conventions are [`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged
but where this note says otherwise. [`prompt-03.md`](prompt-03.md) is the model: 08 is 03 for the
other package, and that note's "Conventions particular to 03" hold here with `datastorekit` for
`raypoolkit`. ChamPBH's 07 (its board §5.12 and the review below it) pinned `v0.3.0` the same way;
what it found that applies is in §0.

**You do not write code.** You may:
- run the suites, `pip freeze`, `pip check`, `pip show` and read-only Python checks of the
  installed package, from the session scratchpad;
- extract `git archive v0.4.0` into the scratchpad;
- fix small residue in a follow-up commit of your own (§4).

You do not install, uninstall or upgrade anything in the venv. If the agent leaves it wrong, that is
a finding for the user, not something the review repairs.

**The prompt:** [`08-pin-datastorekit-v0.4.0.md`](../08-pin-datastorekit-v0.4.0.md) · **Board
items:** K4–K7 · **Closes:** nothing · **Narrows:** nothing · **Opens:** only what the work finds ·
**Model:** Sonnet, as the prompt recommends · **Needs the network** (GitHub for the tag, PyPI for
the isolated build's `setuptools`).

**Gate:**
- 07 landed (`0527480`) and was reviewed (`38c5e52`); the tag `pre-datastorekit` is on `origin`
  (`91e6f31`); 08–11 written (`8982fac`).
- `HEAD` is the commit that adds this note, or a later one that touches no code ("code" as
  prompt-01.md's gate defines it, which includes `requirements.txt`).
  `git diff --stat 0527480 HEAD -- . ':!.prompts' ':!.documents'` is empty.
- One prompt at a time in this checkout, and **no other session installs into this venv, or runs a
  suite or a Ray job from it, while 08 runs**: the venv is shared (README §4.4).

## 0. What makes this prompt unusual

**It is 03 again, and the review's evidence is the venv itself**, read after the commit, not the
results note's account of it. A revert does not undo the install.

**Its acceptance is "one distribution added, it is the tag, and the release does what SI needs".**
The first two halves can pass vacuously, as at 03: a "before" freeze taken late, or an install from
the local checkout that carries the right version string. Only the freeze against the committed
baseline (plus 03's one line), `direct_url.json` and the byte comparison with `git archive v0.4.0`
tell them apart. The third half, K7, can pass vacuously too: **a K7 script that imports the
extracted archive, or SI's own `Datastore` package, proves nothing about the install.** It must
print `datastorekit.__file__` under the venv's `site-packages`.

**Nothing imports the package yet, so the suites cannot fail because of it.** They show that
nothing else moved.

**Corrections to the prompt.** Pass them on.
1. **The board section** is **`### 5.21 After prompt 08 (<date>)`**, appended after §5.20 (§5.20
   records the writing of 08–11). The header's "Last updated" and status line are updated to
   match. The items K4–K7 are already rows in board §1.1; fill in their state.
2. **`requirements.txt`** has 72 lines at `HEAD`. With the pin it has 73, the pin at **`:16`**,
   between `cycler==0.12.1` (`:15`) and `distlib==0.4.3` (now `:17`). `ray==2.55.1` moves from
   `:57` to `:58`, `raypoolkit` from `:58` to `:59`, `SQLAlchemy` from `:66` to `:67`: say so in
   "State handed to the next prompt".
3. **The suites** run as README §5 rules 16–17 say, after the install, serially, with no cluster
   up. "07's counts" are **696 (695 passed, 1 skipped)** and **62 (61 passed, 1 skipped)**, re-run
   by the orchestrator at `0527480`; no Python has changed since. The `slow` block is not run.
4. **`pip` itself is not upgraded.** Every pip command prints `[notice] A new release of pip is
   available: 26.0.1 -> 26.2.1`. It is ignored.
5. **`raypoolkit` is re-resolved, not reinstalled.** Because `requirements.txt` names it by a VCS
   URL, pip clones RayPoolKit again on every `install -r` (`Collecting raypoolkit @ …`,
   `Resolved https://github.com/ds283/RayPoolKit to commit 4e7eb153…`) and then leaves it, as
   ChamPBH's 07 found. That is not a change to `raypoolkit`; the evidence is that its 16 installed
   files and dist-info keep their mtimes (§2.1's saved copy) and the freeze's line is unchanged.
6. **pip's `Resolved https://github.com/ds283/DatastoreKit to commit 8e7c1d77…`** names the **tag
   object**, not the commit, as at 03. The recorded commit (`direct_url.json`, `pip freeze`, the
   helper) is `c8570e849334…`. The results note quotes the line and says so. It is not the prompt's
   "installed commit is not `c8570e849334…`" stop.
7. **K7, as the orchestrator ran it** against the extracted archive (not the install), with the
   prompt's design: `DatastoreObject(1, timestamp=t).timestamp == t`; `None` without it; assigning
   raises `AttributeError`; `DatastoreObject(1, t)` raises `TypeError`; a `register`+`build`
   subclass instantiates; one without `build` raises `TypeError: Can't instantiate abstract class
   NoBuild without an implementation for abstract method 'build'`; **30 of 30 registry entries
   instantiate, 28 classes, 12 defining all three of `store`, `validate`, `validate_on_startup`, 16
   none, 0 some**; `ray.is_initialized()` `False`. The quantity entries are recognised by an
   `ObjectType` attribute on the instance. The agent's run, on the installed package, must give the
   same figures. The script is `orch08/k7_proto.py` in the session scratchpad; the agent may read
   it, and must run its own against `site-packages`.

**The facts, checked by the orchestrator on 2026-10-21 at `8982fac`, 17:05–17:15 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `8982fac` before this note.
  `git diff --stat 91e6f31 8982fac` outside `.prompts/` and `.documents/` is empty. The 17 store
  files of prompt-01.md §1 step 5 are in the tree (ignored); 08 opens none.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process. `pgrep`
  finds no `gcs_server`, `raylet`, `ray::`, `pytest`, `unittest` or `main.py`. `RAY_ADDRESS` unset.
- **The load** was 48 / 82 / 86 on 10 CPUs, from the Claude desktop app, Spotlight and
  WindowServer; no suite or Ray job. It affects only the suites' times.
- **The venv.** Python 3.13.16; pip 26.0.1. `pip freeze` is 82 lines: `measure/out/7bb3efd-pip-freeze.txt`
  plus exactly 03's `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce6…`. `pip check`
  clean. `pip show datastorekit` finds nothing. site-packages has 170 entries.
- **The tag.** `git ls-remote --tags https://github.com/ds283/DatastoreKit`: `refs/tags/v0.4.0`
  `8e7c1d77b3792b57b98983e84b99fc68ab88cb89`, `^{}` `c8570e849334d09085bbd84876095fc9e22bd005`.
  The local checkout (`HEAD` `38ebb9f`, clean) agrees.
- **The tag's package.** `git archive v0.4.0 datastorekit`: **21** `.py` files outside `tests/`;
  under `datastorekit/tests/data/` four JSON files (`client_vocabulary.json`,
  `schema_at_extraction-04a.json`, `schema_at_extraction-06.json`,
  `store_fingerprint-neutral-1-encoding-1.json`). `pyproject.toml`: `version = "0.4.0"`,
  `requires-python = ">=3.12"`, `dependencies = ["ray>=2.43", "sqlalchemy>=2.0.39,<2.1"]`,
  `packages.find` excluding `datastorekit.tests*`.
- **The dry run, done by the orchestrator** with a scratch copy of `requirements.txt` holding the
  pin at `:16`: exit 0, 7.8 s; the clone of DatastoreKit at the tag object, then RayPoolKit's
  re-resolution, then **`Would install datastorekit-0.4.0`**, nothing else. Its `--report` gives
  `download_info` `{"url": "https://github.com/ds283/DatastoreKit", "vcs_info": {"vcs": "git",
  "requested_revision": "v0.4.0", "commit_id": "c8570e849334d09085bbd84876095fc9e22bd005"}}`. The
  venv's freeze was unchanged after it.
- **Who names the package today**, as the prompt's §2.4.7 says: `git grep -l datastorekit -- '*.py'`
  outside the records gives `utilities.py`, `tools/compare_stores.py`,
  `tests/test_package_provenance.py`, `tests/test_rehearsal_stage_counts.py`; none imports it.
- **The stores.** 08 opens none.

**What the review exists to establish.**
- **(E1) K4.** The diff of `requirements.txt` is the one line, at `:16`.
- **(E2) K5, the venv moved by one distribution.** The freeze differs from the committed
  `7bb3efd-pip-freeze.txt` by exactly two lines, 03's `raypoolkit` and the new
  `datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005`,
  and from §1's copy by the second alone; `raypoolkit`'s files untouched; `pip check` clean.
- **(E3) K6, it is the tag.** `direct_url.json` a VCS record at `c8570e849334…`, requested
  `v0.4.0`, no `dir_info`; the 21 modules byte for byte, no `tests/`; the import starts no Ray.
- **(E4) K7 on the install.** U3 and the base as §0's correction 7, from `site-packages`.
- **(E5) The helper sees it.** The provenance line is the prompt's.
- **(E6) Nothing else moved.** No file but `requirements.txt`, the results note and the board; the
  other repositories untouched; no store opened; the suites at 696 and 62.
- **(E7) The records.** The §1 row, K4–K7, `### 5.21` with the rollback.

## 1. Before you dispatch

1. **The tree.** `git status --short` clean, `git diff --cached` empty, `git log` since `0527480`
   records only.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no Ray process.
3. **The venv.** `pip freeze` (82 lines) saved; `pip check` clean; `pip show datastorekit` empty;
   the site-packages listing and `raypoolkit`'s file mtimes saved.
4. **The load**, recorded.
5. **Mtimes**, for check 9: the 17 store files, and every entry under `~/ScienceData/`.
   DatastoreKit's and RayPoolKit's `HEAD` and `git status --porcelain`.
6. **The tag, the archive, the dry run and K7's prototype**, as §0.

**Done 2026-10-21, 17:05–17:15 BST,** at `8982fac`: all six hold. In `orch08/` in the session
scratchpad: `pip-freeze.txt`, `site-packages-before.txt` (170), `mtimes-raypoolkit.txt` (16),
`mtimes-stores.txt` (17), `mtimes-sciencedata.txt` (834 entries), `requirements-pinned.txt`,
`dryrun.txt`, `dryrun-report.json`, `archive/` and `k7_proto.py`. DatastoreKit `38ebb9f` and
RayPoolKit `17029d9`, both clean.

## 2. Dispatch

One fresh-context subagent, on **Sonnet**, in the background. Give it:
- the prompt;
- the campaign README and the board;
- 01's and 03's results notes;
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`.

Tell it plainly:
- **One commit, at the end, made once.** Its results note is
  `.documents/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md`, in README §5.1's form, with the
  prompt's §6 additions.
- **The files it may change** are the prompt's §5 list (`requirements.txt`, the results note, the
  board) and `.documents/OPEN-ISSUES.md` if an issue opens. **No code, no test, nothing in
  DatastoreKit or RayPoolKit, not the README, not `.prompts/INDEX.md`.**
- **It installs once,** after a dry run that reports only `datastorekit`, from the tag on GitHub.
- **Stop and ask** on any of the prompt's §4 conditions. If pip has moved anything but
  `datastorekit`, it records exactly what, restores it from the saved freeze, and stops without
  committing.
- **It replies with:**
  - the results note's path and the commit;
  - the `requirements.txt` diff;
  - the dry run's and the install's lines other than "Requirement already satisfied";
  - the freeze diff, `pip check`, `raypoolkit`'s mtimes check, and the provenance line;
  - `direct_url.json` verbatim, and the file comparison's counts and result;
  - the import check's output and `sharded_store --help`'s exit status;
  - K7's output whole, with its first line showing where `datastorekit` was imported from;
  - the two suites, with the load;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — ten checks

1. **Scope.** `git show --stat <commit>` touches only `requirements.txt`, the results note and the
   board (and `.documents/OPEN-ISSUES.md`, if an issue opened). `git status --short` clean; one
   commit of the agent's since this note; no amend in the reflog.
2. **E1, K4.** `git show <commit> -- requirements.txt` is the one line at `:16`; `wc -l` 73.
3. **E2, the freeze.** `./venv/bin/pip freeze` against the **committed** `7bb3efd-pip-freeze.txt`:
   exactly the two added lines; against §1's copy: the `datastorekit` line alone. `pip check`
   clean. `raypoolkit`'s 16 files have §1's mtimes. site-packages differs from §1's listing by
   `datastorekit/` and `datastorekit-0.4.0.dist-info/` only.
4. **E3, the origin.** `datastorekit-0.4.0.dist-info/direct_url.json`, read directly: `url`
   `https://github.com/ds283/DatastoreKit`, `vcs` `git`, `commit_id` `c8570e849334…`,
   `requested_revision` `v0.4.0`, no `dir_info`. `INSTALLER` `pip`. No `__editable__*`, `.pth` or
   `.egg-link` naming DatastoreKit.
5. **E3, the files.** The archive (§1's `archive/`, or freshly extracted) against the installed
   package, `__pycache__` aside: the same 21 `.py` files, each identical under `cmp`; no `tests/`
   and no JSON data file; nothing else. Every `datastorekit/` entry of `RECORD` is one of the 21 or
   its `.pyc`, and each listed hash matches.
6. **E3–E5, import and helper.** The import one-liner prints `False`; `sharded_store --help` exits
   0. `installed_package_provenance()` gives `datastorekit` `0.4.0`, the URL, commit and revision,
   `editable: False`, and `raypoolkit` unchanged; `format_package_provenance` prints the prompt's
   line. `pip show datastorekit` gives `Requires: ray, sqlalchemy`.
7. **E4, K7 replayed.** The orchestrator's `k7_proto.py`, run with the archive **off** `sys.path`
   (so that it imports from `site-packages`; its first line says so): the same output as §0's
   correction 7. The agent's script, read: it imports from `site-packages`, and its figures equal
   these.
8. **The pip account.** The results note shows `Would install datastorekit-0.4.0` and
   `Successfully installed datastorekit-0.4.0`, nothing else; quotes both `Resolved …` lines and says
   they are tag objects; says `raypoolkit` was re-resolved, not reinstalled. pip still 26.0.1.
9. **E6, hygiene.** DatastoreKit and RayPoolKit at §1's `HEAD`s, clean (another session may move
   them; nothing of theirs may be the agent's). The 17 store files and the 834 `~/ScienceData/`
   entries keep their mtimes. No Ray process; the lock free. No scratch file in the repository.
10. **E6–E7, the suites and the records.** The agent's 696 and 62, with the load; the orchestrator
    re-runs both at `<commit>`. The board: §1 row (✅, "this commit", the results note), K4–K7,
    the header, and `### 5.21 After prompt 08` naming the rollback (`git revert` plus
    `./venv/bin/pip uninstall -y datastorekit`). The results note follows README §5.1, every §2
    check with its command and output, K7's script whole.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 08* paragraph in §5.21: what each
  check found, and anything handed on to 09. Fix small residue in a follow-up commit of its own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 08";
  - `.prompts/INDEX.md`: the campaign's line (08 landed and reviewed).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:** the pin and the freeze diff in one line; the origin and the file
  comparison; K7 on the installed package; the provenance line every driver now prints; the suites;
  anything opened.
- **Then 09** can be dispatched; its note is written after this review.
