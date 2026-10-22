# Orchestrator — prompt 10a, pin `datastorekit` `v0.5.0`

Read [`../README.md`](../README.md) first: §0.5, §0.6, §2.2 (10a's charter), §4.4 and §5 (rules
11–13, 16, 17). The conventions are [`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged
but where this note says otherwise, and [`prompt-03.md`](prompt-03.md)'s "Conventions particular to
03" hold with `datastorekit` for `raypoolkit` (pip, the archive, the other repositories, no Ray).
[`prompt-08.md`](prompt-08.md) is the model: 10a is 08 for the next release, and its review
(board §5.21) is the account of what such a pin looks like when it is right.

**You do not write code.** You may:
- run the suites, `pip freeze`, `pip check`, `pip show` and read-only Python checks of the
  installed package, from the session scratchpad;
- extract `git archive v0.5.0` and `v0.4.0` into the scratchpad;
- fix small residue in a follow-up commit of your own (§4).

You do not install, uninstall or upgrade anything in the venv. If the agent leaves it wrong, that is
a finding for the user, not something the review repairs.

**The prompt:** [`10a-pin-datastorekit-v0.5.0.md`](../10a-pin-datastorekit-v0.5.0.md) · **Board
items:** K8–K11 · **Closes:** nothing · **Narrows:** nothing · **Opens:** only what the work finds ·
**Model:** Sonnet, as the prompt recommends · **Needs the network** (GitHub for the tags, PyPI for
the isolated build's `setuptools`).

**Gate:**
- 10 landed (`e2c7b22`) and was reviewed (`d0ce59c`); the brief (`f5f395b`) answered by `v0.5.0`;
  U12 ruled and 10a, 10b written (`bad346d`).
- `HEAD` is the commit that adds this note, or a later one that touches no code ("code" as
  prompt-01.md's gate defines it, which includes `requirements.txt`).
  `git diff --stat e2c7b22 HEAD -- . ':!.prompts' ':!.documents'` is empty.
- No SI cluster is up, and **no other session installs into this venv, or runs a suite or a Ray
  job from it, while 10a runs**: the venv is shared (README §4.4).

## 0. What makes this prompt unusual

**It is 08 again, but it replaces rather than adds**, and that changes what "nothing else moved"
can be shown by. At 08 the package's files were new, so their presence was the change; here pip
uninstalls `v0.4.0` and installs `v0.5.0`, so **every one of the 21 modules is rewritten**, new
mtimes included, though only two change. The mtimes cannot tell the 19 unchanged modules from
changed ones; only a byte comparison with what was installed before can, and the "before" must be
saved as content (hashes or a copy), not as mtimes. A check that compares the installed files only
with `git archive v0.5.0` shows that they are the tag's, not that the tag differs from `v0.4.0` by
two modules: that is a separate comparison, against the saved files.

**Where the acceptance can pass vacuously.**
- **K11 on the wrong package.** A script that imports the extracted archive, or a stale
  `PYTHONPATH`, proves nothing about the install. It prints `datastorekit.store_inventory.__file__`
  under the venv's `site-packages`, and fails on `v0.4.0` (the orchestrator's prototype does: its
  first assertion, on `InventorySpec.extra_values`, fails against the installed `v0.4.0`).
- **The refusal checked by a spec that names nothing.** The wrapped `GradientCoupledInstanton` spec
  must carry the real values table (`GradientCoupledInstantonProfile`) in `extra_values`; the
  assertion is on the `ValueError`'s text naming the class and the table, not merely on an
  exception.
- **"pip freeze differs by one line"** passes vacuously against a freeze taken after the install.
  The baseline is 08's, 83 lines, with the `c8570e84…` line; §1 holds a copy.
- **The suites cannot fail because of the release** while no spec declares the field; they show
  nothing else moved. That is all they are asked to show.

**Corrections to the prompt.** Pass them on.
1. **The board section** is **`### 5.26 After prompt 10a (<date>)`**, appended after §5.25. The
   header's "Last updated" (it still reads 2026-10-21) and status line are updated to match. K8–K11
   are already rows in board §1.1; fill in their state. Nothing is opened unless the work finds
   something, so `.documents/OPEN-ISSUES.md` (60 open, 28 closed) is otherwise untouched.
2. **`requirements.txt`** has 73 lines; the pin is `:16`, between `cycler==0.12.1` (`:15`) and
   `distlib==0.4.3` (`:17`). It is replaced in place, so no line moves: `ray==2.55.1` stays `:58`,
   `raypoolkit` `:59`, `SQLAlchemy` `:67`.
3. **The install's output differs from 08's, as it should.** The dry run says only `Would install
   datastorekit-0.5.0`; the real install also prints `Attempting uninstall: datastorekit`, `Found
   existing installation: datastorekit 0.4.0`, `Uninstalling datastorekit-0.4.0:` and `Successfully
   uninstalled datastorekit-0.4.0` before `Successfully installed datastorekit-0.5.0`. That is the
   replacement the prompt asks for, not "pip moved another distribution". Any other `Uninstalling`
   or `Successfully installed` name is the stop.
4. **pip's `Resolved https://github.com/ds283/DatastoreKit to commit 6a6809d5…`** names the **tag
   object**, as at 03 and 08. The recorded commit (`direct_url.json`, `pip freeze`, the helper) is
   `f47b9a255e9a…`. The results note quotes the line and says so; it is not the prompt's "installed
   commit is not `f47b9a255e9a…`" stop.
5. **`raypoolkit` is re-resolved, not reinstalled**: `Collecting raypoolkit @ …`, `Resolved
   https://github.com/ds283/RayPoolKit to commit 4e7eb153…` (its tag object), then nothing. Its
   **16 files** (12 outside `__pycache__`, 4 `.pyc`), dist-info included, keep their mtimes.
6. **`pip` itself is not upgraded.** Every pip command prints `[notice] A new release of pip is
   available: 26.0.1 -> 26.2.1`. It is ignored.
7. **The "before" of §2.1 must hold content.** Besides the mtimes and sizes, save the SHA-256 of each
   of the 21 installed `datastorekit/*.py` (or copy them into the scratch directory), so that K10.4's
   "the other 19 are byte-equal to what was installed before" is a measurement. All 21 will have new
   mtimes after the install (correction 3); that is expected and is not a finding.
8. **`stat` on `PATH` is GNU's** (`/opt/local/libexec/gnubin/stat`): use `/usr/bin/stat -f '%m %z
   %N'`, or a Python `os.stat` walk as 08's agent did.
9. **The archive's `datastorekit/tests/data/`** at `v0.5.0` holds **six** JSON files (two more than at
   `v0.4.0`: `schema_at_extra-values-01.json`, `store_fingerprint-neutral-2-encoding-1.json`). None is
   installed.
10. **K11, as the orchestrator ran it** against the extracted `v0.5.0` archive (not the install): the
    defaults (`InventorySpec().extra_values == {}`, `Record(...).extra_value_counts == {}`),
    `ENCODING_FORMAT == 1`, `as_json` keys `['key', 'tags', 'validated', 'value_count']` and, with one
    entry, those and `extra_value_counts`; **24 classes**, in 10's order (`version`, `store_tag`,
    `redshift`, `tolerance`, `efold_value`, `delta_Nstar`, `N_init`, `N_final`,
    `n_collocation_points`, `alpha_regularization`, `inflaton_mass`, `quartic_coupling`,
    `phi_value`, `pi_value`, `MasslessDecoupledDiffusion`, `IntegrationSolver`,
    `CosmologicalParams`, `QuadraticPotential`, `QuarticPotential`, `InflatonTrajectory`,
    `FullInstanton`, `GradientCoupledInstanton`, `SlowRollInstanton`, `CompactionFunction`); no SI
    spec declares `extra_values`; GCI's values slot `('GradientCoupledInstantonProfile',
    'parent_serial')`; the refusal exactly `ValueError: inventory_classes(): GradientCoupledInstanton
    names GradientCoupledInstantonProfile both as its value table and in its extra_values`;
    `ray.is_initialized()` `False`. `tests/test_tables_to_drop.py` on the archive: 9 passed. The
    script is `orch10a/k11_proto.py` in the session scratchpad; the agent may read it, and must run
    its own against `site-packages`.
11. **The suites** run as README §5 rules 16–17 say, after the install, serially, with no cluster
    up. "10's counts" are **730 (729 passed, 1 skipped)** and **67 (66 passed, 1 skipped)**, re-run
    by the orchestrator at `e2c7b22` and on the tag's package at `f5f395b` (README §0.6); no Python
    has changed since. The `slow` block is not run.

**The facts, checked by the orchestrator on 2026-10-22 at `bad346d`, 19:15–19:25 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `bad346d` before this note.
  `git diff --stat e2c7b22 bad346d` outside `.prompts/` and `.documents/` is empty. The 17 store
  files of prompt-01.md §1 step 5 are in the tree (ignored); 10a opens none.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four ports
  free. `pgrep` finds no `gcs_server`, `raylet`, `ray::`, `pytest`, `unittest` or `main.py`.
  `RAY_ADDRESS` unset.
- **The load** was 35 / 22 / 24 on 10 CPUs. It affects only the suites' times.
- **The venv.** Python 3.13.16; pip 26.0.1. `pip freeze` 83 lines, 08's, with
  `datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005`;
  `pip check` clean. site-packages has 172 entries, among them `datastorekit/` and
  `datastorekit-0.4.0.dist-info/` (8 files; `direct_url.json` VCS at `c8570e84…`, requested
  `v0.4.0`); the only `.pth` is `_virtualenv.pth`. The 21 installed modules equal `git archive
  v0.4.0`'s byte for byte. The helper prints
  `>> packages: datastorekit 0.4.0 (https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005, requested v0.4.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **The tags.** `git ls-remote`: `refs/tags/v0.5.0` `6a6809d570023ce32513deac4528e93ada4ef824`,
  `^{}` `f47b9a255e9ad58e0d0eaf85644f53b575884d31`; `v0.4.0` `8e7c1d77…`, `^{}` `c8570e84…`. The
  local checkout (`HEAD` `2900d82`, clean) agrees.
- **The tag's package.** `git archive v0.5.0 datastorekit`: the same **21** `.py` files outside
  `tests/` as `v0.4.0`; **`store_fingerprint.py` and `store_inventory.py` differ, the other 19 are
  identical**; `pyproject.toml` differs by `version = "0.5.0"` alone; six JSON files under
  `tests/data/` (correction 9).
- **The dry run, done by the orchestrator** with a scratch copy of `requirements.txt` holding the
  `v0.5.0` pin at `:16`: exit 0, 8.6 s; the clone of DatastoreKit at the tag object `6a6809d5…`,
  RayPoolKit's re-resolution at `4e7eb153…`, then **`Would install datastorekit-0.5.0`**, nothing
  else. Its `--report` gives `download_info` `{"url": "https://github.com/ds283/DatastoreKit",
  "vcs_info": {"vcs": "git", "requested_revision": "v0.5.0", "commit_id":
  "f47b9a255e9ad58e0d0eaf85644f53b575884d31"}}`. The venv's freeze was unchanged after it.
- **The stores.** 10a opens none.

**What the review exists to establish.**
- **(E1) K8.** The diff of `requirements.txt` is the one line replaced at `:16`; 73 lines.
- **(E2) K9, the venv moved by one distribution, replaced.** The freeze differs from §1's copy by
  the `datastorekit` line alone, `c8570e84…` → `f47b9a25…`; `raypoolkit`'s files untouched;
  `pip check` clean; pip not upgraded.
- **(E3) K10, it is the tag.** `direct_url.json` a VCS record at `f47b9a255e9a…`, requested
  `v0.5.0`, no `dir_info`; the 21 modules the tag's, byte for byte; exactly two differ from §1's
  hashes; no `tests/`; no `datastorekit-0.4.0.dist-info` left; the import starts no Ray.
- **(E4) K11 on the install.** The field, the record, the refusal and `ENCODING_FORMAT` as
  correction 10, from `site-packages`; U5 unmoved.
- **(E5) The helper sees it.** The provenance line is the prompt's.
- **(E6) Nothing else moved.** No file but `requirements.txt`, the results note and the board; the
  other repositories untouched; no store opened; the suites at 730 and 67.
- **(E7) The records.** The §1 row, K8–K11, `### 5.26` with the rollback (`git revert` plus
  `./venv/bin/pip install -r requirements.txt`).

## 1. Before you dispatch

1. **The tree.** `git status --short` clean, `git diff --cached` empty, `git log` since `e2c7b22`
   records only.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no Ray process.
3. **The venv.** `pip freeze` (83 lines) saved; `pip check` clean; the site-packages listing,
   `raypoolkit`'s file mtimes, `datastorekit`'s file mtimes and the SHA-256 of its 21 modules saved.
4. **The load**, recorded.
5. **Mtimes**, for check 9: the 17 store files, and every entry under `~/ScienceData/`.
   DatastoreKit's and RayPoolKit's `HEAD` and `git status --porcelain`.
6. **The tags, both archives, the dry run and K11's prototype**, as §0.

**Done 2026-10-22, 19:15–19:25 BST,** at `bad346d`: all six hold. In `orch10a/` in the session
scratchpad: `pip-freeze.txt` (83), `site-packages-before.txt` (172), `mtimes-raypoolkit.txt` (16),
`mtimes-datastorekit.txt` (29: 21 modules, 8 dist-info), `sha256-datastorekit-v040-installed.txt`
(21), `mtimes-stores.txt` (17), `mtimes-sciencedata.txt` (835 entries, the root included),
`requirements-pinned.txt`, `dryrun.txt`, `dryrun-report.json`, `archive-v0.5.0/`, `archive-v0.4.0/`,
`k11_proto.py` and `k11_proto.out`. DatastoreKit `2900d82` and RayPoolKit `17029d9`, both clean.

## 2. Dispatch

One fresh-context subagent, on **Sonnet**, in the background. Give it:
- the prompt;
- the campaign README and the board;
- 01's and 08's results notes;
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read 10b or 11.

Tell it plainly:
- **One commit, at the end, made once.** Its results note is
  `.documents/dk-and-rpk-migration/10a-pin-datastorekit-v0.5.0.md`, in README §5.1's form, with the
  prompt's §6 additions. Stage by explicit path, and show `git diff --cached --name-only` before
  committing.
- **The files it may change** are the prompt's §5 list (`requirements.txt`, the results note, the
  board) and `.documents/OPEN-ISSUES.md` if an issue opens. **No code, no test, nothing in
  DatastoreKit or RayPoolKit, not the README, not `.prompts/INDEX.md`.**
- **It installs once,** after a dry run that reports only `datastorekit-0.5.0`, from the tag on
  GitHub; the uninstall of `datastorekit-0.4.0` is part of that install (correction 3).
- **It saves content, not only mtimes,** before the install (correction 7).
- **Stop and ask** on any of the prompt's §4 conditions. If pip has moved anything but
  `datastorekit`, it records exactly what, restores it from the saved freeze, and stops without
  committing.
- **It replies with:**
  - the results note's path and the commit;
  - the `requirements.txt` diff;
  - the dry run's and the install's lines other than "Requirement already satisfied";
  - the freeze diff, `pip check`, `raypoolkit`'s mtimes check, and the provenance line;
  - `direct_url.json` verbatim, the file comparison's counts and result against the tag, and the
    two modules that differ from the saved `v0.4.0` files;
  - the import check's output and `sharded_store --help`'s exit status;
  - K11's output whole, with its first line showing where `datastorekit` was imported from, and
    `test_tables_to_drop.py`'s result;
  - the two suites, with the load;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — ten checks

1. **Scope.** `git show --stat <commit>` touches only `requirements.txt`, the results note and the
   board (and `.documents/OPEN-ISSUES.md`, if an issue opened). `git status --short` clean; one
   commit of the agent's since this note; no amend in the reflog; no scratch file in the repository.
2. **E1, K8.** `git show <commit> -- requirements.txt` is one line removed and one added, both
   `:16`, differing only in `v0.4.0` → `v0.5.0`; `wc -l` 73.
3. **E2, the freeze.** `./venv/bin/pip freeze` against §1's copy: exactly the `datastorekit` line,
   `@c8570e849334…` → `@f47b9a255e9a…`, nothing else; 83 lines. `pip check` clean. `raypoolkit`'s
   16 files have §1's mtimes and sizes. site-packages differs from §1's listing by
   `datastorekit-0.4.0.dist-info/` → `datastorekit-0.5.0.dist-info/` only. pip still 26.0.1.
4. **E3, the origin.** `datastorekit-0.5.0.dist-info/direct_url.json`, read directly: `url`
   `https://github.com/ds283/DatastoreKit`, `vcs` `git`, `commit_id` `f47b9a255e9a…`,
   `requested_revision` `v0.5.0`, no `dir_info`. `INSTALLER` `pip`. No `__editable__*`, `.pth` (but
   `_virtualenv.pth`) or `.egg-link` naming DatastoreKit.
5. **E3, the files.** §1's `archive-v0.5.0/` against the installed package, `__pycache__` aside: the
   same 21 `.py` files, each identical under `cmp`; no `tests/` and no JSON data file; nothing else.
   Every `datastorekit/` entry of `RECORD` is one of the 21 or its `.pyc`, and each listed hash
   matches. Against §1's `sha256-datastorekit-v040-installed.txt`: **exactly
   `store_fingerprint.py` and `store_inventory.py` differ**, the other 19 hash the same.
6. **E3–E5, import and helper.** The import one-liner prints `False`; `sharded_store --help` exits
   0. `installed_package_provenance()` gives `datastorekit` `0.5.0`, the URL, `f47b9a255e9a…`,
   `v0.5.0`, `editable: False`, and `raypoolkit` unchanged; `format_package_provenance` prints the
   prompt's line. `pip show datastorekit` gives `Version: 0.5.0`, `Requires: ray, sqlalchemy`.
7. **E4, K11 replayed.** The orchestrator's `k11_proto.py`, run with `DSK_ROOT` unset (so that it
   imports from `site-packages`; its first line says so): the same output as correction 10.
   `tests/test_tables_to_drop.py` on the installed package: 9 passed. The agent's script, read: it
   imports from `site-packages`, puts SI's root on `sys.path` itself, edits no SI file, wraps the
   GCI entry with `dataclasses.replace`, asserts on the error's text, and its figures equal these.
8. **The pip account.** The results note shows `Would install datastorekit-0.5.0`, the uninstall of
   `datastorekit-0.4.0` and `Successfully installed datastorekit-0.5.0`, nothing else; quotes both
   `Resolved …` lines (`6a6809d5…`, `4e7eb153…`) and says they are tag objects; says `raypoolkit`
   was re-resolved, not reinstalled.
9. **E6, hygiene.** DatastoreKit and RayPoolKit at §1's `HEAD`s, clean (another session may move
   them; nothing of theirs may be the agent's). The 17 store files and the 835 `~/ScienceData/`
   entries keep their mtimes. No Ray process; the lock free.
10. **E6–E7, the suites and the records.** The agent's 730 and 67, with the load; the orchestrator
    re-runs both at `<commit>`, serially. The board: §1 row (✅, "this commit", the results note),
    K8–K11, the header, and `### 5.26 After prompt 10a` naming the rollback (`git revert` plus
    `./venv/bin/pip install -r requirements.txt`, which resolves to `c8570e84…`). The results note
    follows README §5.1, every §2 check with its command and output, K11's script whole, and "State
    handed to the next prompt" with the provenance line and the counts 10b starts from.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 10a* paragraph in §5.26: what each
  check found, and anything handed on to 10b. Fix small residue in a follow-up commit of its own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 10a";
  - `.prompts/INDEX.md`: the campaign's line (10a landed and reviewed).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:** the pin and the freeze diff in one line; the origin, the file comparison
  and the two changed modules; K11 on the installed package; the provenance line every driver now
  prints; the suites; anything opened.
- **Then 10b** can be dispatched; its note is written after this review, at 10a's commit.
