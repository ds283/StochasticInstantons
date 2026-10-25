# Prompt 01 — move `ray` and `SQLAlchemy`, with token mode named

**Campaign:** [`README.md`](README.md) · **Board items:** **B1**, **P1**, **V0**, **T1**–**T3**,
**D1**, **L1**, **R1**–**R4** · **Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-25, with the plan, measured at `03110ce`. Your own measurement governs.
**Where it runs:** on the laptop, in the main checkout, on `main` (C1).
**Gate:**
- on `main`, at the commit that amended this prompt for U4 (after `900d3f7`) or later, with
  `git status --porcelain` empty. Call that `HEAD` the dispatch commit;
- `./venv/bin/python -m runregistrykit list`: nothing `running`, stale or unknown;
- the venv holds `ray` 2.55.1 and `SQLAlchemy` 2.0.46, and `datastorekit`, `raypoolkit` and
  `runregistrykit` at `f47b9a2…`, `67a75b9…` and `0bae3a3…`, none editable;
- `ls -l ~/.ray/auth_token`: 64 bytes, `-rw-------`. **Never print its contents**;
- `./venv/bin/python -m raypoolkit.rehearsal_lock status`: the lock free;
- `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`: no SI process, the four ports
  free;
- neither `var/ray-sqla-align-01/` nor any `var/datastores/ray-sqla-align-01-*` exists.

If any of these fails, stop and ask. A held lock is another project's: never wait on it, never
break it. A missing token, or one not mode 600, is the user's to fix.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Opus**.

**Read first:**

1. [`README.md`](README.md) whole: §0.2 (the mechanism), §0.3, §2 (this charter and the gates),
   §5, and §6 (U1–U4, C1–C12).
2. **SGK** (`/Users/ds283/Documents/Code/SecondaryGWKit`; read, never edit):
   `prompts/py313-venv/IMPLEMENTATION_STATE.md` §4, both token issues; `config/ray_local.py`;
   `RunDrivers/tests/test_ray_auth_mode.py`.
3. `CLAUDE.md`: "Build and test", "Long-running jobs — the run registry" and "Protected
   infrastructure"; `.claude/rules/run-registry.md` and `.claude/rules/test-selection.md`.
4. `.prompts/rrk-adoption/04-rehearse-registered-runs.md` §1.1 (the protocol, H1, H2, H4, H5), and
   `.documents/rrk-adoption/verification.md` §1: its stage times, how it chose `--after` for
   `resumed-a`, and its commands. They are the model for R.
5. The rehearsal tools, run unchanged: `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`,
   `interrupt_when.py` and `stage_counts.py` (read each one's `--help`);
   `.documents/rrk-adoption/rehearsal/build_registered.sh`, the launcher L1 copies.

---

## 1. What is wanted

**Move SI to `ray` 2.59.0 and `SQLAlchemy` 2.0.55, show that the move alone breaks SI's attach to
its cluster, name token mode so that it does not, and show with a registered rehearsal that the
stores are unchanged.** Three commits (C6): the pins; the fix; the records.

Throughout:
- **Save every command and its output** under `L=var/ray-sqla-align-01` (ignored by git), in
  `$L/out/`, each block headed by its command: `01-pip.txt`, `01-suites.txt`, `01-v0.txt`,
  `01-breakage.txt`, `01-rehearsal.txt`, `01-token.txt`, plus the launch logs under `$L/`. They are
  copied to `.documents/ray-sqla-align/out/` only in §2.9 (C10), so that the tree stays clean
  for R.
- **Never print, copy or rewrite `~/.ray/auth_token`.** Read it only with `ls -l` (or `stat`), and
  in §2.9's `grep -F -l -f`.
- **No `ray stop`.** SI's cluster only through `ray_cluster.sh`, each lock command a shell command
  of its own, no `PURPOSE` naming `/tmp/ray-si`.
- **A Ray CLI command against SI's cluster** (`ray status`, `ray list actors`) is run as
  `RAY_AUTH_MODE=token ./venv/bin/ray … --address 127.0.0.1:6390`, and only from §2.7 on.

## 2. What to do

**2.1 The baselines (B1).** `./venv/bin/pip freeze` (84 lines expected); `uptime`; then
`pytest -m "not integration and not slow"` and `RAY_ADDRESS=local pytest -m integration`, serially,
in the foreground, with `-W default` on the first so that new warnings show. README §0.4's counts:
848 (847 passed, 1 skipped) and 72 (71 passed, 1 skipped). Save the warnings summary of each.

**2.2 The pins (P1).** `requirements.txt:58` becomes `ray==2.59.0` and `:68` becomes
`SQLAlchemy==2.0.55`. No other line moves. Then:
- `./venv/bin/pip install --dry-run -r requirements.txt`: it would install `SQLAlchemy-2.0.55` and
  `ray-2.59.0`, and nothing else;
- `./venv/bin/pip install -r requirements.txt`. **Never editable**, and pip itself not upgraded;
- `pip freeze` again: it differs from 2.1's in exactly those two lines; `pip check` is clean; the
  three git packages are at the same commits.

**2.3 The suites on the pins alone.** Both again, as in 2.1. The counts must be 2.1's. Record every
new warning; expected among them is Ray's `Token authentication is enabled for this Ray cluster`
from the tests that start a local instance. No token is generated (the file exists): its `ls -l`
line is unchanged.

**Commit the pins** (C6): `requirements.txt` only, staged by path, after showing `git diff --cached
--name-only`. On this tree local Ray works, with a warning, and SI's cluster refuses its drivers.
2.4 measures the second half.

**2.4 V0 — the failure, shown.** Under the real lock, with `RAY_AUTH_MODE` unset in your shell
(`env | grep -c RAY_AUTH_MODE` is 0):
1. `ray_cluster.sh start "ray-sqla-align 01 (V0)"`: exit 0. Record whether its output carries
   `Token authentication is enabled`: §0.2 says it does, since the token file exists.
2. A driver attaches as `main.py` does:
   `./venv/bin/python -c 'import ray; ray.init(address="127.0.0.1:6390"); print(ray.cluster_resources()); ray.shutdown()'`,
   in the foreground. **Expected: it is refused** (`InvalidAuthToken` lines, then
   `AuthenticationError`, or another authentication refusal), non-zero exit. If it has neither
   connected nor exited after 300 s, end it by its pid, and record that.
3. `ray_cluster.sh stop`: exit 0; then `status`: the lock free, no SI process, the ports free.

**If the driver connects**, §0.2 is wrong for this machine: record what it printed, stop the
cluster, and **stop and ask**. Do not go on to the fix.

**2.5 The fix (T1–T3).**
- **T1 — `config/ray_auth.py`** (C3). The token half of SGK's `config/ray_local.py`: a constant
  `RAY_AUTH_MODE = "token"`; if `"RAY_AUTH_MODE"` is not in `os.environ`, set it and, **if
  `"ray._raylet"` is in `sys.modules`, call `sys.modules["ray._raylet"].Config.initialize("")`**.
  A value already set is left alone. The module imports nothing from Ray itself. Its comment says,
  in SI's voice and at SI's comment density: why the mode is named (README §0.2, both routes); that
  every Ray start imports it, guarded by `tests/test_ray_auth.py`; why the refresh is needed (SGK's
  `[02-the-token-mode-setting-comes-after-import-ray-so-every-ray-start-fails]`); and that the token
  is `~/.ray/auth_token`, kept at mode 600. The repository's licence header, as `config/`'s other
  files have it.
- **T1 — the importers** (C4): `main.py`, `plot_InstantonSolutions.py`,
  `plot_GradientCoupledSolutions.py` and `tests/conftest.py` each gain `import config.ray_auth  #
  noqa: F401` (with a few words saying why, if the file's style has room) at module level, among
  their imports, before any `ray.init`. Nothing else in them changes. `main.py`'s import must not
  move its refusals (`tests/test_main_refusals.py`) or its provenance line
  (`tests/test_package_provenance.py`) relative to `ray.init`.
- **T1 — the subprocess programs.** For each of `tests/test_inflaton_trajectory_prune.py:464`,
  `tests/test_inventory_store.py:80` and `tests/registered_run_helpers.py:110`, read how the
  subprocess is launched and record whether its environment is built from `os.environ` (so it
  inherits `RAY_AUTH_MODE` from `conftest`). If one is not, **stop and ask**: do not change a test's
  environment unasked.
- **T2 — `ray_cluster.sh`** (C5). In `cmd_start`, before `"$RAY_BIN" start`, `export
  RAY_AUTH_MODE="${RAY_AUTH_MODE:-token}"`, with a two- or three-line comment in the script's voice
  (README §0.2: `ray start` infers token mode from the token file unless told; SI names it). The
  `actors:` line (`:322`) prints `RAY_AUTH_MODE=token $RAY_BIN list actors --address $SI_ADDRESS`.
  The usage text gains one sentence: the cluster runs in token mode, and a Ray CLI command against
  it needs `RAY_AUTH_MODE=token`. Nothing of the lock half, the stop or the ports changes. `bash -n`.
- **T3 — `tests/test_ray_auth.py`**, after SGK's `test_ray_auth_mode.py`, in SI's test style
  (pytest, a docstring saying what it pins and why, no Ray started, nothing written):
  - the module, in a fresh interpreter with `RAY_AUTH_MODE` removed from the environment: the
    variable becomes `token`; with `disabled` preset, it stays `disabled`;
  - Ray's own mode (`ray._raylet.get_authentication_mode()`), in a fresh interpreter, is `TOKEN`
    with `ray` imported first and with the module imported first, and is not `TOKEN` with
    `disabled` preset;
  - by `ast`: each of the three drivers imports `config.ray_auth` at module level, before the
    statement holding its `ray.init` (for the plot scripts, before the function holding it);
    `tests/conftest.py` imports it at module level;
  - by text: `ray_cluster.sh` exports `RAY_AUTH_MODE` with the `:-token` default **before** its
    `"$RAY_BIN" start` line.

  It belongs in the default selection: it starts no Ray (each fresh interpreter imports `ray`, which
  takes a second or two). Time it standalone and say so.

**2.6 The documents and the launcher (D1, L1).**
- **`CLAUDE.md`, "Build and test"**: one sentence after the lock's, in the paragraph's voice and
  width: every Ray start runs in token mode, named by `config/ray_auth.py` (and by `ray_cluster.sh`
  for the cluster), guarded by `tests/test_ray_auth.py`; a Ray CLI command against SI's cluster
  needs `RAY_AUTH_MODE=token`; the token is `~/.ray/auth_token`, kept at mode 600. The test counts
  in the same section (`:35-38`) become the new ones.
- **`.claude/rules/test-selection.md`**: the counts at `:10`, `:26` and `:60-61` become the new
  ones, and the "close of rrk-adoption" sentence says which campaign measured them.
- **L1 — the launcher** (C9): copy `.documents/rrk-adoption/rehearsal/build_registered.sh` to
  `.documents/ray-sqla-align/rehearsal/build_registered.sh`, and change only its campaign
  (`ray-sqla-align`), prompt (`01`), the store and job prefix (`ray-sqla-align-01-`), the launch
  directory (`var/ray-sqla-align-01`), and its header's first lines (what it is, and that it is
  04's launcher with those names changed). Save `diff -u` of the two in `$L/out/01-rehearsal.txt`.
  `bash -n`.

**2.7 The breakages.** Apply each, run the named check, record which test failed and the diff as
applied (in `$L/out/01-breakage.txt`), and revert:
- **B1** — the refresh removed from `config/ray_auth.py`: the test with `ray` imported first fails.
- **B2** — the module overwrites a preset value: the `disabled` tests fail.
- **B3** — `plot_InstantonSolutions.py`'s import removed: the `ast` test names that file.
- **B4** — `ray_cluster.sh`'s export moved after `"$RAY_BIN" start`: the text test fails.

Then the suites, as 2.1: the default selection is 848 plus T3's tests, all passing but the one
skip; `integration` is 72. **With the fix, Ray's `Token authentication is enabled` warning is gone
from both runs.**

**Commit the fix** (C6), staged by path after showing `git diff --cached --name-only`: exactly
`config/ray_auth.py`, `main.py`, `plot_InstantonSolutions.py`,
`plot_GradientCoupledSolutions.py`, `tests/conftest.py`, `tests/test_ray_auth.py`,
`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`, `CLAUDE.md`,
`.claude/rules/test-selection.md` and `.documents/ray-sqla-align/rehearsal/build_registered.sh`.
After it, `git status --porcelain` is empty.

**2.8 R — the rehearsal (R1–R4).** On the clean tree at the fix commit, under the real lock, with
`RAY_AUTH_MODE` still unset in your shell (the script and the drivers name it). `ADDRESS=127.0.0.1:6390`,
`S=var/datastores`. Every build is `rrk-adoption` 04's, given to the wrapper through L1: `--config
quadratic-minimal.yaml --database $S/ray-sqla-align-01-<store>.sqlite --job-name
ray-sqla-align-01-<slug> --targets homogeneous --n-collocation-points 5 --alpha-regularization 0.01
--ray-address $ADDRESS`. **One check after each launch** (the manifest, `status.json` `running`
with the pid, `list`), then a `Monitor` on the log's `** launcher saw exit status` line: never a
`sleep` loop, never `pgrep`.
1. `ray_cluster.sh start "ray-sqla-align 01 (R)"`: exit 0, and **no** `Token authentication is
   enabled` line. Then `RAY_AUTH_MODE=token ./venv/bin/ray status --address $ADDRESS`: 4 CPUs. Then
   the cluster's environment: for the `gcs_server` and the `raylet` pids (from `status`),
   `ps -E -ww -o command= -p <pid>` (macOS prints the environment after the command) contains
   `RAY_AUTH_MODE=token`. Record only that match (`grep -o 'RAY_AUTH_MODE=[a-z]*'`), never the
   whole environment.
2. **R1 — `reference`**, store `reference`, straight through: `done`/0, every stage's `ALL WORK ITEMS
   COMPLETE`, `stage_counts.py` as `rrk-adoption` 04's `reference`. Then `store create`, `store
   fingerprint --write` and `store show`: the fingerprint is
   **`a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`**, and the run's recorded
   one equals it.
3. **R2 — `resumed-a`**, store `resumed`, stopped with `SIGTERM` by `interrupt_when.py $L/resumed-a.log
   $L/resumed-a.pid --banner "STAGE 2: FULL MSR INSTANTONS" --after <s>`. Choose `<s>` from R1's
   stage times, as 04 did (its verification §1, "`<s>` for `resumed-a`"), so that the store is left
   partial, and say how. A signal that leaves any stage incomplete counts; one that lands after the
   last stage is retuned and rerun on a fresh store, twice at most. Expected: the wrapper's `killed`
   line, `** driver exit status 143`, the launcher's 143; `list` shows it `killed`. Then `store
   create` on the closed store.
4. **R3 — `resumed-c`**, store `resumed`, straight through: `done`/0; the open prunes only
   unvalidated rows; `stage_counts.py` shows that only what was missing was computed; the sidecar's
   fingerprint is **`a9f716fb…1ea7`**.
5. **R4 — the comparison.** `PYTHONPATH=. ./venv/bin/python tools/compare_stores.py` on the two
   stores: equal but for bookkeeping. `store fingerprint` (without `--write`) on each: `a9f716fb…1ea7`.
   Each manifest of R: `git_dirty` false, `git_head` the fix commit, and `packages` naming `ray`
   2.59.0, `SQLAlchemy` 2.0.55, numpy 2.4.6 and scipy 1.17.1 beside the three git packages (U4).
   Each launch log's `>> packages:` line names the same six.
6. `ray_cluster.sh stop`, a command on its own; then `status`: the lock free, no SI process, the
   four ports free.

**2.9 The token check, and the records.**
- **Token** (README §2.2): `grep -c` over R's three launch logs, `start`'s output and 2.7's suite
  output for `Token authentication is enabled`, `Generated new authentication token`,
  `InvalidAuthToken` and `AuthenticationError`: all 0. `ls -l ~/.ray/auth_token`: 64 bytes, mode
  600, the 12:51 mtime, as at the Gate.
- **Copy** `$L/out/` and the launch logs to `.documents/ray-sqla-align/out/` (small text only; a
  file over about 1 MB is a finding to report first). V0's output keeps its refusal lines: they are
  the measurement.
- **Then** `grep -r -F -l -f ~/.ray/auth_token .documents/ray-sqla-align/ .prompts/ray-sqla-align/`
  prints nothing (exit 1). If it lists a file, delete that copy, and report it: nothing holding the
  token may be committed.

## 3. Acceptance

1. **The pins.** The dry run installs only `ray` 2.59.0 and `SQLAlchemy` 2.0.55; after the install
   the freeze differs from 2.1's in those two lines; `pip check` clean; the git packages unmoved. The
   pins are a commit of their own.
2. **V0** shows the attach refused on the pins alone (or the prompt stopped, §2.4).
3. **The fix**: T1–T3 as §2.5 says; B1–B4 each caught; `bash -n` passes on the script and L1.
4. **The suites**: 848 and 72 before and on the pins; after the fix, 848 + T3's and 72, with no
   token warning; `CLAUDE.md` and `test-selection.md` stating the new counts. No file under
   `ComputeTargets/`, `Numerics/`, `Interpolation/` or `Datastore/` changed, so `slow` is not run.
5. **The gates** of README §2.2: **FP** and **Token**.
6. **Nothing else moved**: `git diff <the dispatch commit> --name-only` after the third commit is
   the two commits' paths, the results note, `.documents/ray-sqla-align/out/`, the board and
   `.prompts/INDEX.md`. `utilities.py`, `runregistrykit.toml` and `RunDrivers/` are untouched: U4's
   change was made before dispatch.

## 4. Stop conditions: stop and ask

- A Gate item is not as stated, or the lock is held at any point.
- The dry run would install, upgrade or remove anything but the two packages.
- A suite count differs from what §2 expects, or a test fails.
- V0's driver connects (§2.4).
- A subprocess program in the tests does not inherit `os.environ` (§2.5).
- `~/.ray/auth_token` changes, disappears, or is found in a record.
- A build fails other than by the signal it was sent; a state or exit code is not as §2.8 says.
- **FP fails**: either store's fingerprint is not `a9f716fb…1ea7`, or `compare_stores` finds a
  difference beyond bookkeeping. Record its full output and change nothing (README §2.2).
- Anything suggests a defect in DatastoreKit, RayPoolKit or RunRegistryKit under the new versions:
  record it on the board and in `.documents/OPEN-ISSUES.md`, and stop. It is reported upstream by
  the user, never worked around here.

**If you stop with SI's cluster running**, run `ray_cluster.sh stop` first, unless the stop is what
failed. **If you stop after the install**, say that the venv holds the new versions; going back is
`pip install ray==2.55.1 SQLAlchemy==2.0.46`, and is the user's call.

## 5. What this prompt does not do

- It changes no file outside §2.6's commit list, `requirements.txt` and the records. In particular
  not `utilities.py` (protected), `runregistrykit.toml`, `RunDrivers/`, or any compute target.
- It reads, and never changes, SGK, ChamPBH and the three packages.
- It keeps R's stores under `var/datastores/`; retiring them is the user's.
- It does not push.

## 6. The results note and the board

**The results note**, `.documents/ray-sqla-align/01-move-ray-and-sqlalchemy-with-token-mode.md`,
in the template of `dk-and-rpk-migration` README §5.1: the versions as installed, and as R's manifests
and `>> packages:` lines record them (U4); every count; V0 as measured; the fix and its breakages; R as a table (run id,
slug, store, state, exit code, wall time, fingerprint), with the stage times beside 04's and the
choice of `<s>`; the token checks; the commands verbatim. Name SGK's two issues where the fix
follows them.

**The board:** the header ("01 landed, awaiting review"); the §1 row; items B1, P1, V0, T1–T3, D1,
L1 and R1–R4; the gates **FP** and **Token**; `### 5.1 After prompt 01 (<date>)`, with the first
two commits' SHAs in full and "this commit" for the third. **`.prompts/INDEX.md`:** this campaign's
line.

**Three commits** (C6), each in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`: the pins (§2.3), the fix (§2.7), the records (§2.9).
