# 01 — move `ray` and `SQLAlchemy`, with token mode named

**Subject:** SI moved to `ray` 2.59.0 and `SQLAlchemy` 2.0.55; the refusal of SI's cluster shown
on the pins alone; Ray's token mode named for every Ray start; a registered rehearsal on the fix
**Commits:** `5f3219fb483208b5738f15d1b0e95cbcacd8d8eb` (the pins),
`3a24ea53962a3a02de412032807c0fd3e9afcb3f` (the fix) and this commit (the records), on `main`, on
top of the dispatch commit `8c01877`. Nothing pushed.
**Date:** 2026-10-25, 18:26–19:00 GMT, by Claude Opus 5.5
**Result:** **COMPLETE.** B1, P1, V0, T1–T3, D1, L1 and R1–R4 done; the gates **FP** and
**Token** hold.
- **The pins.** The dry run would install `SQLAlchemy-2.0.55 ray-2.59.0` and nothing else. After
  the install the freeze (84 lines) differs from the one before in those two lines alone; `pip
  check` finds no broken requirements; the three git packages are at the same commits, none
  editable.
- **V0.** On the pins alone, `ray_cluster.sh start` printed Ray's `Token authentication is
  enabled for this Ray cluster` warning, and a driver attaching as `main.py` does was refused: 21
  `InvalidAuthToken` lines, then `AuthenticationError … RAY_AUTH_MODE is currently 'disabled' (not
  'token')`, then `ConnectionError: Failed to connect to Ray cluster at 127.0.0.1:6390`, exit 1
  after 22 s. README §0.2 holds on this machine.
- **The fix.** `config/ray_auth.py`, imported by `main.py`, both plot scripts and
  `tests/conftest.py`; `ray_cluster.sh` exporting the mode before `ray start`;
  `tests/test_ray_auth.py`, 10 tests, 2.1 s standalone; B1–B4 each caught by a named test.
- **The suites.** 848 (847 passed, 1 skipped) and 72 (71 passed, 1 skipped) before and on the
  pins; **858 (857 passed, 1 skipped) and 72 (71 passed, 1 skipped)** on the fix.
- **R.** `reference` `done`/0; `resumed-a` `killed`/143, its signal inside the narrow window
  (3 `FullInstanton` rows stored, 7 not); `resumed-c` `done`/0, computing only what was missing.
  Both stores fingerprint to `a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`,
  and `compare_stores` gives `RESULT: equal`. Every manifest records `git_head` the fix commit,
  `git_dirty` false, and `ray` 2.59.0, `SQLAlchemy` 2.0.55, numpy 2.4.6 and scipy 1.17.1.
- **The token.** `~/.ray/auth_token` is 64 bytes, `-rw-------`, mtime 2026-10-25 12:51:17, at the
  Gate and after every step; it was never printed, copied or rewritten; the final `grep -F -l -f`
  over this campaign's records found nothing (exit 1).
- No issue is opened.

Prompt: [`.prompts/ray-sqla-align/01-move-ray-and-sqlalchemy-with-token-mode.md`](../../.prompts/ray-sqla-align/01-move-ray-and-sqlalchemy-with-token-mode.md).
The orchestrator's brief for 01 governed where it differs from the prompt; its 15 corrections are
classified below. The outputs are [`out/01-*`](out/), each block headed by its command; logs have
ANSI codes removed and the JSON files are unchanged. The stores, run records and launch files
stay in `var/` (ignored), for the user. `<scratch>` below is my scratch directory,
`/private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/36d2f5c1-bddb-4d57-b35b-cf64f3d4a638/scratchpad/agent01/`;
the scripts there are committed as text under `out/`.

## What shipped

### The pins (P1), `5f3219f`

`requirements.txt:58` `ray==2.55.1` → `ray==2.59.0` and `:68` `SQLAlchemy==2.0.46` →
`SQLAlchemy==2.0.55`; no other line. The venv was upgraded in place (C2) by `./venv/bin/pip
install -r requirements.txt` (`Successfully installed SQLAlchemy-2.0.55 ray-2.59.0`), with pip
left at 26.0.1 and nothing editable. [`out/01-pip.txt`](out/01-pip.txt).

**The versions as installed**, and as R records them (U4):

| Package | Before | `pip freeze` after | R's manifests (`packages`) | R's `>> packages:` lines |
|---|---|---|---|---|
| `ray` | 2.55.1 | 2.59.0 | 2.59.0, no commit, not editable | `ray 2.59.0 (no recorded origin)` |
| `SQLAlchemy` | 2.0.46 | 2.0.55 | 2.0.55 | `SQLAlchemy 2.0.55 (no recorded origin)` |
| numpy | 2.4.6 | 2.4.6 | 2.4.6 | `numpy 2.4.6 (no recorded origin)` |
| scipy | 1.17.1 | 1.17.1 | 1.17.1 | `scipy 1.17.1 (no recorded origin)` |
| `datastorekit` | `f47b9a255e9a…` | the same | 0.5.0 at `f47b9a25…`, `v0.5.0` | `datastorekit 0.5.0 (…@f47b9a25…, requested v0.5.0)` |
| `raypoolkit` | `67a75b97a656…` | the same | 0.3.0 at `67a75b97…`, `v0.3.0` | `raypoolkit 0.3.0 (…@67a75b97…, requested v0.3.0)` |
| `runregistrykit` | `0bae3a3c501a…` | the same | 0.2.0 at `0bae3a3c…`, `v0.2.0` | — (not in `utilities.RECORDED_DISTRIBUTIONS`) |

### The fix (T1–T3, D1, L1), `3a24ea5`

Ten paths, exactly §2.7's list.
- **T1 — [`config/ray_auth.py`](../../config/ray_auth.py)** (C3), with the repository's licence
  header. The token half of SGK's `config/ray_local.py`: `RAY_AUTH_MODE = "token"`; if
  `"RAY_AUTH_MODE"` is not in `os.environ`, it is set, and if `"ray._raylet"` is in `sys.modules`,
  `sys.modules["ray._raylet"].Config.initialize("")` refreshes Ray's config. A value already set is
  left alone, and the module imports nothing from Ray. Its comment gives the three routes of
  README §0.2 and V0's refusal; that every Ray start imports it, guarded by
  `tests/test_ray_auth.py`; why the refresh is needed (SGK's
  `[02-the-token-mode-setting-comes-after-import-ray-so-every-ray-start-fails]`); and that the
  token is `~/.ray/auth_token`, kept at mode 600.
- **T1 — the importers** (C4). `main.py`, `plot_InstantonSolutions.py`,
  `plot_GradientCoupledSolutions.py` and `tests/conftest.py` each gain, among their imports, after
  `import ray` and before the first `from` import of the repository's own modules:
  ```python
  # names Ray's token mode before ray.init (config/ray_auth.py)
  import config.ray_auth  # noqa: F401
  ```
  (`conftest.py`'s comment: "names Ray's token mode for every Ray start of the suite, its
  subprocesses included"). Nothing else in them changes. `main.py`'s import is above its
  provenance line and its refusals, so `tests/test_main_refusals.py` and
  `tests/test_package_provenance.py` pass unchanged.
- **T1 — the subprocess programs**, read ([`out/01-fix.txt`](out/01-fix.txt)); all three inherit:
  - `tests/test_inflaton_trajectory_prune.py:464` is in `_POOL_SCRIPT`, run at `:513` by
    `subprocess.run([sys.executable, "-c", _POOL_SCRIPT, …], cwd=_ROOT, capture_output=True,
    text=True, timeout=600)`: no `env=`, so the child inherits the parent's environment;
  - `tests/test_inventory_store.py:80` is in `_STORE_SCRIPT`, run at `:247` the same way, no
    `env=`; the file's `_main` (`:282`) passes `env=dict(os.environ, RAY_ADDRESS=_ADDRESS)`
    (`:297`);
  - `tests/registered_run_helpers.py:110` is in the stubbed program, run by `run_stubbed` (`:363`)
    and `run_the_script` (`:380`) with `subprocess_env()`, which is `dict(os.environ)` less
    `RAY_ADDRESS` (`:254-258`; `run_the_script` also drops `PYTHONPATH`).
- **T2 — `ray_cluster.sh`** (C5). In `cmd_start`, just before `local t0=$SECONDS` and the `"$RAY_BIN"
  start --head` line:
  ```bash
      # Ray's authentication mode, named (ray-sqla-align 01). Since Ray 2.59, `ray start` infers
      # token mode from the token file (~/.ray/auth_token) unless told; SI names it, as
      # config/ray_auth.py does for every driver, so that the cluster and its drivers agree.
      export RAY_AUTH_MODE="${RAY_AUTH_MODE:-token}"
  ```
  The `actors:` line prints `RAY_AUTH_MODE=token $RAY_BIN list actors --address $SI_ADDRESS`, and
  the usage gains "The cluster runs in Ray's token mode (RAY_AUTH_MODE=token, set by start unless
  the environment holds a value), so a Ray CLI command against it needs RAY_AUTH_MODE=token in its
  environment." Nothing of the lock half, the stop or the ports changed. `bash -n`: 0.
- **T3 — [`tests/test_ray_auth.py`](../../tests/test_ray_auth.py)**, after SGK's
  `test_ray_auth_mode.py`, in SI's style (pytest functions, a docstring saying what it pins and
  why; no Ray started; nothing written). Its 10 tests:
  - `test_an_unset_mode_becomes_token`, `test_a_mode_already_set_is_left_as_it_is`: the module in
    a fresh interpreter with `RAY_AUTH_MODE` removed, then with `disabled` preset;
  - `test_ray_imported_first`, `test_the_module_imported_first`,
    `test_a_mode_already_set_is_what_ray_sees`: `ray._raylet.get_authentication_mode() ==
    AuthenticationMode.TOKEN` in a fresh interpreter, in each import order, and not with
    `disabled` preset;
  - `test_each_driver_imports_it_before_ray_init[main.py]`, `[plot_InstantonSolutions.py]`,
    `[plot_GradientCoupledSolutions.py]`: by `ast`, a module-level `import config.ray_auth` before
    the top-level statement holding the driver's `ray.init` (deviation 16);
  - `test_conftest_imports_it`: by `ast`, a module-level import in `tests/conftest.py`;
  - `test_ray_cluster_sh_exports_the_mode_before_ray_start`: by text, the `export
    RAY_AUTH_MODE="${RAY_AUTH_MODE:-token}"` line before the one `"$RAY_BIN" start` line.

  **Standalone:** `./venv/bin/python -m pytest tests/test_ray_auth.py -q -p no:cacheprovider`:
  10 passed in 2.08 s (3.2 s wall). It is in the default selection.
- **D1.** `CLAUDE.md`, "Build and test", gains after the lock's sentences: "Every Ray start runs in
  Ray's token mode, named by `config/ray_auth.py` (and by `ray_cluster.sh` for the cluster) and
  guarded by `tests/test_ray_auth.py`: a Ray CLI command against SI's cluster needs
  `RAY_AUTH_MODE=token`, and the token is `~/.ray/auth_token`, kept at mode 600." Its counts become
  858 of 999, 857 pass and 1 skipped. `.claude/rules/test-selection.md`: `:10` 999 tests; `:26`
  858 of 999 (857 pass, 1 is skipped); `:59-61` "As ray-sqla-align 01 measured them, the markers
  select 72 `integration` tests (71 pass, 1 is skipped) and 69 `slow` tests, disjoint, so 858 + 72
  + 69 = 999." (`pytest --collect-only`: 999 collected; `-m slow` 69/999.)
- **L1 — [`rehearsal/build_registered.sh`](rehearsal/build_registered.sh)** (C9), 04's launcher
  with its campaign (`ray-sqla-align`), prompt (`01`), store and job prefix (`ray-sqla-align-01-`),
  launch directory (`var/ray-sqla-align-01`) and its header's first lines changed, the usage text's
  names with them. `bash -n`: 0. The `diff -u` from 04's is in
  [`out/01-rehearsal.txt`](out/01-rehearsal.txt), its first block: five hunks, all names or the
  header.

## Deviations from the prompt

**The orchestrator's corrections** (the brief, §0):
1. **`STRUCTURALLY REQUIRED`** (correction 1). The board section is `### 5.2 After prompt 01
   (2026-10-25)`, since §5.1 is "U4 revised, before dispatch".
2. **`STRUCTURALLY REQUIRED`** (correction 2). Each manifest's `packages` names seven:
   `SQLAlchemy`, `datastorekit`, `numpy`, `ray`, `raypoolkit`, `runregistrykit`, `scipy`. Each
   `>> packages:` line names six, without `runregistrykit`. Versions as ruled: `ray` 2.59.0,
   `SQLAlchemy` 2.0.55, numpy 2.4.6, scipy 1.17.1, the four PyPI installs `(no recorded origin)`.
3. **`NOTED`, with a probe: `IMPLEMENTATION CHOICE`** (correction 3). The suites' output holds the
   token warning at no point, before the move, on the pins or on the fix (`grep -c` 0 in all six
   outputs). The probe measures it ([`out/01-token.txt`](out/01-token.txt)), each run in the
   foreground with SI's cluster down and `RAY_AUTH_MODE` unset in the shell:
   - **on the pins** (18:35:09, after the install, before 2.3's suites): `./venv/bin/python -c
     'import ray; ray.init(address="local", include_dashboard=False); ray.shutdown()'`, exit 0;
     stderr: `2026-10-25 18:35:12,849	WARNING authentication_token_setup.py:85 -- Token
     authentication is enabled for this Ray cluster. Set RAY_AUTH_MODE=disabled to opt out. For
     more information, see https://docs.ray.io/en/latest/ray-security/token-auth.html`, then
     `Started a local Ray instance.`;
   - **on the fix** (18:50:02, the fix tree, before its commit; the same content): `PYTHONPATH=.
     ./venv/bin/python -c 'import config.ray_auth; import ray; ray.init(address="local",
     include_dashboard=False); ray.shutdown()'`, exit 0; stderr only `Started a local Ray
     instance.`, no warning.

   So "expected among the new warnings" (§2.3) and "gone from both runs" (§2.7) are measured by the
   probes, not the suites. **Token**'s check of the suite output (§2.9) is kept, and is the weak
   check it is.
4. **`NOTED`** (correction 4). R's launch logs being free of the warning shows nothing by itself:
   a driver attaching by address never logs it. R's evidence is `start`'s output without the
   warning, the `gcs_server` and `raylet` environments, and the three drivers attaching at all,
   which V0 shows they cannot on the pins alone. **R also exercised the refresh:**
   `RunDrivers/registered_run.py` imports `ray` before `runpy` runs `main.py`, so `main.py`'s
   `import config.ray_auth` found `ray._raylet` loaded and refreshed Ray's config; without it the
   drivers would have attached in `disabled` mode and been refused, as in SGK's second issue.
5. **`NOTED`** (correction 5). The three subprocess sites read as the orchestrator measured
   (What shipped, T1). "No `env=`" counted as inherited; no stop.
6. **`IMPLEMENTATION CHOICE`** (correction 6). No `Monitor`: 04's waiter, unchanged
   (`diff` empty), as `<scratch>/wait_for_line.py` ([`out/01-wait_for_line.py.txt`](out/01-wait_for_line.py.txt)).
   Each wait was one foreground Bash call, `--timeout 120` for the registration line and `420` for
   the launcher's line, with a 600 000 ms tool timeout. None timed out, so none was repeated. No
   `sleep` loop, no `pgrep`, no `tail -f`, no `run_in_background`.
7. **`IMPLEMENTATION CHOICE`** (correction 7). After each launch, the registration wait, then one
   check, `<scratch>/check.py LAUNCH`: 04's with the launch directory and its docstring's first line
   changed ([`out/01-check.py.diff`](out/01-check.py.diff)). 04's `rows.py` is used unchanged.
8. **`IMPLEMENTATION CHOICE`** (correction 8). `<s>` = 19 s, one attempt, no retune (§R2 below).
9. **`STRUCTURALLY REQUIRED`** (correction 9). `results_store_id`: `reference` `null`,
   `resumed-a` `null`, `resumed-c` `c5ea19ff19154612862eaaa647a7bd03`, the resumed store's
   `store_id` as `store create` and `store show` print it.
10. **`IMPLEMENTATION CHOICE`** (correction 10). The fingerprint in `resumed-c`'s status, the
    sidecar's after it and `store fingerprint` on the closed store are one digest,
    `a9f716fb…1ea7`; the status's and the sidecar's `classes` are equal as JSON.
11. **`STRUCTURALLY REQUIRED`** (correction 11). Every `ray_cluster.sh start`, `stop` and `status`
    and the lock module's `status` ran alone in its Bash call, `> <scratch>/<name>.txt 2>&1`, the
    exit by `echo $?`, the file read in a later call. No `PURPOSE` and no command line of mine named
    SI's temp dir. The builds, waiters, `ray status` and `ps` checks ran in calls of their own. The
    lock was free each time; no `ray stop`.
12. **`NOTED`** (correction 12). `ps -E -ww -o command= -p <pid> | grep -o
    'RAY_AUTH_MODE=[a-z]*'` gave `RAY_AUTH_MODE=token` for the `gcs_server` (74894) and the
    `raylet` (74935); the control `grep -c 'PATH='` gave 1 for each. The environment itself was
    never printed.
13. **`NOTED`** (correction 13). The final `grep -r -F -l -f ~/.ray/auth_token
    .documents/ray-sqla-align/ .prompts/ray-sqla-align/` printed nothing, exit 1, run on the tree
    this commit records.
14. **`NOTED`** (correction 14). The one-minute load: 65.83 at the Gate (18:26), 16.99 before V0's
    `start` (18:40:49), 6.14 before R's (18:50:48); every launch's is in R's table. None over 50 at
    a `start`.
15. **`NOTED`** (correction 15). `RunDrivers/registered_run.py:72`, `:81` and
    `tests/registered_run_helpers.py:27` still cite Ray 2.55.1: history, out of scope.

**My own:**

16. **`STRUCTURALLY REQUIRED`.** The plot scripts' `ray.init` (`plot_InstantonSolutions.py:1209`,
    `plot_GradientCoupledSolutions.py:975` after the fix) is in each file's `if __name__ ==
    "__main__":` block, not inside a function as README §0.3, the prompt's T3 and the brief's
    measured facts say. T3's first draft asserted "inside a function" and failed on both scripts;
    the test now checks the import is before the top-level statement holding the `ray.init` (the
    call itself in `main.py`, the `__main__` block in the plot scripts), which is the property that
    matters, and B3 is still caught by it.
17. **`IMPLEMENTATION CHOICE`.** V0's driver was run under `timeout 300` (GNU coreutils), so the
    300 s bound would have ended it by signal without a pid lookup. It was not needed: the driver
    exited 1 after 22 s.
18. **`IMPLEMENTATION CHOICE`.** Outputs beyond §1's list, all under `out/`: `01-gate.txt`,
    `01-fix.txt` (the subprocess reading), `01-B1.diff`–`01-B4.diff` (each breakage's diff as
    applied, beside `01-breakage.txt`), `01-breakage.py.txt` (the applier), the runs'
    `manifest.json` and `status.json`, both sidecars, `compare_stores`'s JSON, and the launch logs
    with the signaller's log.
19. **`NOTED`.** The dry run prints `Resolved … to commit 6a6809d…`, `caf0076…` and `895e3c7…` for
    the three git packages: their annotated tag objects. `git ls-remote` shows each tag
    dereferencing (`^{}`) to the installed commit, and pip reinstalled none of them.

## Verification performed

### B1 — the baselines, at `8c01877`

- **The Gate**, re-checked at 18:26 ([`out/01-gate.txt`](out/01-gate.txt)): `main` at `8c01877`,
  `git status --porcelain` empty, no stash, the main checkout alone; `runregistrykit list`: 4
  runs, all finished (`done`, `lost`, `killed`, `done`, 04's); `env | grep -c RAY_AUTH_MODE` 0, no
  `RAY_*` variable; Python 3.13.16, `ray==2.55.1`, `SQLAlchemy==2.0.46`, the three git packages at
  `f47b9a2…`, `67a75b9…`, `0bae3a3…`, none editable; `ls -l ~/.ray/auth_token`: `-rw------- 1
  ds283 staff 64 Oct 25 12:51`; the lock module's `status`, exit 0: `lock: free
  (/Users/ds283/.raypoolkit/rehearsal-lock does not exist)`; `ray_cluster.sh status`, exit 0: lock
  free, no process, the four ports free; no `gcs_server` or `raylet` on the machine; neither
  `var/ray-sqla-align-01/` nor `.documents/ray-sqla-align/` existed, and `var/datastores/` held
  only 04's two sidecars.
- `pip freeze`: 84 lines.

### The suites

Serially, in the foreground, never with SI's cluster up, the integration block with
`RAY_ADDRESS=local`. The default selection is `./venv/bin/python -m pytest -m "not integration and
not slow" -q -p no:cacheprovider -W default`; the integration block `RAY_ADDRESS=local
./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`. Load is the one-minute figure at
start → end. [`out/01-suites.txt`](out/01-suites.txt).

| Point | Default | Integration |
|---|---|---|
| 2.1, at `8c01877` (2.55.1, 2.0.46) | **848**: 847 passed, 1 skipped, 141 deselected, 15 warnings; 139.3 s (147 s wall, 18:27:25–18:29:52); load 41.68 → 18.69 | **72**: 71 passed, 1 skipped, 917 deselected, 1 warning; 195.3 s (199 s, 18:30:03–18:33:23); load 23.01 → 83.52 |
| 2.3, the pins alone | **848**: 847 passed, 1 skipped, 141 deselected, 9 warnings; 106.6 s (113 s, 18:35:39–18:37:33); load 24.24 → 28.84 | **72**: 71 passed, 1 skipped, 917 deselected, 0 warnings; 162.1 s (166 s, 18:37:47–18:40:33); load 30.82 → 20.60 |
| 2.7, the fix | **858**: 857 passed, 1 skipped, 141 deselected, 9 warnings; 79.1 s (84 s, 18:46:22–18:47:46); load 5.90 → 6.51 | **72**: 71 passed, 1 skipped, 927 deselected, 0 warnings; 117.7 s (120 s, 18:47:54–18:49:54); load 5.90 → 8.63 |

- **New warnings:** none at either later point. On the pins the default selection lost six: the
  five `ResourceWarning: unclosed file <… name='/dev/null' …>` from `ray/_private/node.py` (lines
  1108, 1254, 1069, 1037, 1189) and Ray's `FutureWarning: Tip: In future versions of Ray, Ray will
  no longer override accelerator visible devices env var…` (`worker.py:2051`); the integration
  block lost that `FutureWarning`, its only one. The nine left are matplotlib's (one
  `RuntimeWarning: More than 20 figures`, eight `UserWarning: Animation was deleted without
  rendering anything`). On the fix the eighth animation warning is reported against
  `test_each_driver_imports_it_before_ray_init[main.py]` rather than
  `test_registered_run.py::…test_the_manifest_is_written_before_the_programs_first_line`: it is
  raised when the collector runs, and the new tests moved where that falls.
- **The token warning** is in none of the six outputs (correction 3). No failure, so nothing was
  re-run. No `gcs_server` or `raylet` was left after any integration run.
- `ls -l ~/.ray/auth_token` after 2.3 and after 2.7: unchanged.
- `slow` (69) not run: no file under `ComputeTargets/`, `Numerics/`, `Interpolation/` or
  `tools/diagnostics/GradientCoupledInstanton/` changed.

### V0 — the refusal, at `5f3219f` ([`out/01-v0.txt`](out/01-v0.txt))

`env | grep -c RAY_AUTH_MODE` 0; load 16.99 at 18:40:49.
1. `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "ray-sqla-align 01 (V0)"`:
   **exit 0**, 13 s, gcs_server pid 71579. Its output **carried the warning**, as its second line:
   ```text
   acquired the rehearsal lock (/Users/ds283/.raypoolkit/rehearsal-lock) for StochasticInstantons: ray-sqla-align 01 (V0)
   2026-10-25 18:40:57,093	WARNING authentication_token_setup.py:85 -- Token authentication is enabled for this Ray cluster. Set RAY_AUTH_MODE=disabled to opt out. For more information, see https://docs.ray.io/en/latest/ray-security/token-auth.html
   ```
2. `timeout 300 ./venv/bin/python -c 'import ray; ray.init(address="127.0.0.1:6390");
   print(ray.cluster_resources()); ray.shutdown()'`, 18:41:18.8 → 18:41:40: **refused, exit 1,
   22 s.** 20 lines of the form
   ```text
   [2026-10-25 18:41:20,035 W 71778 80474560] gcs_client.cc:210: Failed to get cluster ID from GCS server: Unauthenticated: RPC error: InvalidAuthToken: Authentication token is missing or incorrect
   ```
   one a second from 18:41:20 to 18:41:39, then the traceback, ending
   ```text
   ray.exceptions.AuthenticationError: RPC error: InvalidAuthToken: Authentication token is missing or incorrect. Note: RAY_AUTH_MODE is currently 'disabled' (not 'token'). …
   ConnectionError: Failed to connect to Ray cluster at 127.0.0.1:6390
   ```
   `grep -c InvalidAuthToken`: 21. It never connected (`cluster_resources()` printed nothing).
3. `ray_cluster.sh stop`: **exit 0**, `SIGTERM` to 19 processes, after the 15 s grace `SIGKILL` to
   71579 (`gcs_server`), "no process names [SI's temp dir]; ports 6390 6391 8266 52366 are free",
   "released the rehearsal lock", "stopped in 20s". Then `status`, **exit 0**: `lock: free`, no
   process, the four ports free.

### The breakages (B1–B4), [`out/01-breakage.txt`](out/01-breakage.txt)

See the record below.

### R — the rehearsal, at `3a24ea5` ([`out/01-rehearsal.txt`](out/01-rehearsal.txt))

The tree was clean (`git status --porcelain` empty) from the fix commit to the end of R4; nothing
was created in it in between. `RAY_AUTH_MODE` unset in the shell.

**The cluster.**
- `ray_cluster.sh start "ray-sqla-align 01 (R)"`, 18:50:5x, load 6.14: **exit 0**, 13 s, gcs_server
  pid 74894, and **no** `Token authentication is enabled` line (`grep -c` 0). Its last lines:
  ```text
  recorded pid 74894 in /Users/ds283/.raypoolkit/rehearsal-lock/owner
  >> ray_cluster: address 127.0.0.1:6390
  >> ray_cluster: dashboard http://127.0.0.1:8266
  >> ray_cluster: actors: RAY_AUTH_MODE=token ./venv/bin/ray list actors --address 127.0.0.1:6390
  >> ray_cluster: started in 13s; gcs_server pid 74894
  ```
- `RAY_AUTH_MODE=token ./venv/bin/ray status --address 127.0.0.1:6390`, exit 0: one active node,
  **`0.0/4.0 CPU`**, `0.0/1.0 GPU`, `0B/7.30GiB memory`, `0B/2.00GiB object_store_memory`, no
  failures.
- `ray_cluster.sh status`, exit 0: the lock held by `ray-sqla-align 01 (R)`, pid 74894 alive, 19
  processes, the four ports held; `raylet` pid 74935.
- The environments: `gcs_server` 74894 `RAY_AUTH_MODE=token`; `raylet` 74935
  `RAY_AUTH_MODE=token` (correction 12).

**The builds.** Each launched by L1 from the root, checked once, then waited on. Wall time is from
the launch to the launcher's line as the waiter saw it. The fingerprint at finish is the status's,
from `taken.when` to the final `heartbeat`.

| Run id | Slug | Store | pid | State | Exit | Launched → ended | Wall | Load at launch | `results_store_id` | Fingerprint at finish |
|---|---|---|---|---|---|---|---|---|---|---|
| `ray-sqla-align-01-reference-20261025T185152` | `reference` | `reference` | 75386 | `done` | 0 | 18:51:52.4 → 18:52:57.0 | 65 s | 5.42 | `null` | `a9f716fb…1ea7`, 18:52:54 → 18:52:56 |
| `ray-sqla-align-01-resumed-a-20261025T185338` | `resumed-a` | `resumed` | 75785 | `killed` | 143 | 18:53:38.1 → 18:54:33.8 | 56 s | 5.66 | `null` | `cee70e74e3097a485f453aed47b90fcfe4e36c94eca83ece999ecc8d1fd7f2ca`, 18:54:28 → 18:54:33 |
| `ray-sqla-align-01-resumed-c-20261025T185506` | `resumed-c` | `resumed` | 76188 | `done` | 0 | 18:55:05.7 → 18:55:50.4 | 45 s | 14.50 | `c5ea19ff19154612862eaaa647a7bd03` | `a9f716fb…1ea7`, 18:55:47 → 18:55:49 |

At each check the pid file equalled `status.json`'s pid, the state was `running`, and `list`
showed the run; the manifest was born in the same second as the log or the second after
(`reference` 18:51:52 / 18:51:53, `resumed-a` 18:53:38 / 18:53:38, `resumed-c` 18:55:05 /
18:55:06). The stage at the checks: `STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES`, `null`,
`null`; never a `>> ` line. In every log the three `>> registered_run` lines are lines 1–3 and
`>> packages:` line 4.

**The stages**, from each log's `ALL WORK ITEMS COMPLETE` lines, beside 04's:

| Build | STAGE 1 | STAGE 2 | STAGE 3 | STAGE 4 | `stage_counts.py` |
|---|---|---|---|---|---|
| `reference` | 12.4 s | 21.7 s | 12.1 s | 3 s | STAGE 1 1/1/1/1; each lookup "0 already computed, 10 to compute"; STAGES 2–4 10/10/10/10; 4 `ALL WORK ITEMS COMPLETE`; exit 0: 04's `reference` record |
| `resumed-a` | 14 s | — | — | — | STAGE 1 complete; STAGE 2 lookup 0 already, 10 to compute; STAGE 2 `INCOMPLETE; no queue summary`; 1 complete line; exit 143 |
| `resumed-c` | 0.0945 s | 15.1 s | 12.6 s | 3.02 s | STAGE 1 compute 0, "no compute items evaluated"; STAGE 2 "3 already computed, 7 to compute", 7/7/7/7; STAGE 3 0 already, 10 to compute, 10/10/10/10; STAGE 4 the same; 4 complete lines; exit 0 |
| 04's `reference` (load 135) | 34.8 s | 42.9 s | 23 s | 7.46 s | — |
| 04's `resumed-c` | 0.176 s | — | 17.5 s | 4.85 s | — |

No log has a `Traceback`, an `alarm` line, a `*** SIGTERM received` banner, a `Pruned` or
`unvalidated` line or Ray's `FutureWarning` (`grep -ci` 0 each).

**R1 — `reference`.** Log ends `** driver exit status 0`, `** launcher saw exit status 0`; `list`:
`done`, stage `Skipping gradient branch (--targets excludes 'gradient')`. Status: `done`, exit 0,
digest `a9f716fb…1ea7`, `problems` `{}`, `taken` by its run id at 18:52:54 with `git_dirty` false;
`fingerprint_sidecar` "not written: … is not a problem-free registry sidecar (there is none)". Then,
at 18:53:15, `store create var/datastores/ray-sqla-align-01-reference.sqlite --purpose
"ray-sqla-align 01 R1: the reference build of the rehearsal grid under ray 2.59.0 and SQLAlchemy
2.0.55, kept for the user"`, exit 0, `store_id` `cb7b2dc3a7834ef49ed927e8b8ee7be4`; `store
fingerprint … --write`, exit 0: **digest
`a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`**, `problems: none`, "wrote the
fingerprint into the sidecar; it replaced none"; `store show`: the one run, `done`, "by results".

**R2 — `resumed-a`, and the choice of `<s>`.** From `reference`'s log as the waiter saw it, the
STAGE 2 banner (`** STAGE 2: FULL MSR INSTANTONS LOOKUP:`, line 31, with the pool banner, line 34)
arrived at 18:52:15.2. From its rows, read `mode=ro` after its `store create` and `store
fingerprint --write` ([`out/01-rehearsal.txt`](out/01-rehearsal.txt), R1's `rows.py`):

| Event in `reference` | Time | From the banner |
|---|---|---|
| `InflatonTrajectory` stored (ten replicas) | 18:52:13.761 | −1.4 s |
| the last `efold_value` minted (every shard) | 18:52:29.427 | +14.2 s |
| `FullInstanton` rows (δN★ 0.744, 0.1, 1.067, 1.389, 2.356, 1.711, 2.678, 0.422, 2.033, 3.0) | 30.778, 30.847, 30.974, 33.602, 33.622, 34.280, 35.198, 35.215, 35.501, 36.824 | +15.6, +15.6, +15.8, +18.4, +18.4, +19.1, +20.0, +20.0, +20.3, +21.6 s |
| `SlowRollInstanton` rows | 18:52:48.477–48.795 | +33.3 – +33.6 s |
| `CompactionFunction` rows | 18:52:51.637–53.618 | +36.4 – +38.4 s |

The narrow window ran from +15.6 to +21.6 s, the wide one from +15.6 to +38.4 s. **`<s>` = 19 s**
(`--after 19 --poll 0.2`): between the fifth row (+18.4) and the sixth (+19.1), so at
`reference`'s pace five rows stored and five not. The load was steady and low (5.42 at
`reference`'s launch, 5.66 at `resumed-a`'s), unlike 04's, so I aimed at the middle of the narrow
window rather than its early end: 19 s stays inside it for a pace f of `reference`'s from 0.88 to
1.22, and inside the wide one from f = 0.49 up.

**What it did.** `interrupt_when.py` ([`out/01-resumed-a.interrupt.log`](out/01-resumed-a.interrupt.log)):
```text
[2026-10-25T18:54:08+00:00] interrupt_when: saw "STAGE 2: FULL MSR INSTANTONS"; waiting 19 s
[2026-10-25T18:54:27+00:00] interrupt_when: sent SIGTERM to pid 75785
```
(the waiter saw the banner at 18:54:08.9). The last `efold_value` was minted at 18:54:24.794
(+15.9 s), and three `FullInstanton` rows were stored, at 18:54:26.332, 26.344 and 26.484 (+17.4 to
+17.6 s; δN★ 0.422, 0.744, 0.1), all validated: the driver ran at about 1.12 of `reference`'s time,
the load rising to 20 during it. **The signal fell inside the narrow window**: 3 `FullInstanton`
rows stored and validated, 7 not, no `SlowRollInstanton` or `CompactionFunction` row; no orphan;
`replication_in_flight` empty; `efold_value` 7,521 on every shard. One attempt, no retune.

The log after the STAGE 2 banner (lines 34–38):
```text
** STAGE 2: FULL MSR INSTANTONS
** SIGTERM at 2026-10-25 18:54:28 +0000: recorded killed, exit code 143; stopping main.py; the process will exit with status 143
** SIGTERM: main.py ended with SystemExit(1); recording killed, exit code 143
** driver exit status 143
** launcher saw exit status 143
```
Signal (18:54:27, by `interrupt_when.py`'s second-resolution clock) to the `killed` record
(18:54:28 +0000): about 1 s, ±1 s; to the final record (heartbeat 18:54:33): 6 s. No `***
SIGTERM received` banner, no `cancelled an alarm` line: under Ray 2.59.0 the wrapper still
records `killed`/143. `list`: `killed`. Status: `killed`, exit 143, stage `STAGE 2: FULL MSR
INSTANTONS`, fingerprint `cee70e74…f2ca`, `fingerprint_sidecar` "not written … (there is none)".
Then `store create var/datastores/ray-sqla-align-01-resumed.sqlite --purpose "ray-sqla-align 01
R2-R3: the rehearsal grid built by a resume after SIGTERM, under ray 2.59.0 and SQLAlchemy 2.0.55,
kept for the user"`, exit 0, `store_id` `c5ea19ff19154612862eaaa647a7bd03`.

**R3 — `resumed-c`.** Its open printed `>> Opened existing sharded datastore
"…/var/datastores/ray-sqla-align-01-resumed.sqlite" with 10 shards` and no prune report: there was
no unvalidated row to prune, and the STAGE 2 lookup found the three validated rows ("3 already
computed, 7 to compute"). `done`/0; `stage_counts.py` above: only what was missing was computed.
Status: digest `a9f716fb…1ea7`, `taken` by its run id at 18:55:47, `fingerprint_sidecar`
`"written"`; the sidecar's digest and `taken` are the same, and the `classes` of status and sidecar
are equal as JSON. After it, `mode=ro`: every table 10 rows (the trajectory 1 × 10 replicas), all
validated, no orphan, `replication_in_flight` empty, `efold_value` 7,521 on every shard.

**R4 — the comparison.**
- `PYTHONPATH=. ./venv/bin/python tools/compare_stores.py --json
  <scratch>/compare-reference-resumed.json var/datastores/ray-sqla-align-01-reference.sqlite
  var/datastores/ray-sqla-align-01-resumed.sqlite` (18:56:05): **exit 0, `RESULT: equal`**,
  `problems: none`; 30 tables matched, 0 rows in A only or B only, among them `FullInstanton` 10,
  `FullInstantonValue` 16,564, `SlowRollInstantonValue` 16,564, `CompactionFunctionSamples` 33,128,
  `InflatonTrajectoryValue` 5,713, `efold_value` 7,521. The bookkeeping that differs is the
  timestamps and the JSON timing keys (`compute_time` and `mean_time_per_picard_iteration`), as at
  04. [`out/01-compare-reference-resumed.json`](out/01-compare-reference-resumed.json).
- `store fingerprint` without `--write`, exit 0 each: the reference **`a9f716fb…1ea7`**, "matches
  the fingerprint taken 2026-10-25T18:53:16+00:00 by a person, at 3a24ea53…"; the resumed store
  **`a9f716fb…1ea7`**, "matches the fingerprint taken 2026-10-25T18:55:47+00:00 by run
  ray-sqla-align-01-resumed-c-20261025T185506, at 3a24ea53…". The two sidecars' `classes`, 24
  classes, are equal as JSON.
- `store show`: reference — `ray-sqla-align-01-reference-20261025T185152 done finished by results`;
  resumed — `ray-sqla-align-01-resumed-c-20261025T185506 done finished by results and
  results_store_id`, `ray-sqla-align-01-resumed-a-20261025T185338 killed finished by results`.
- **The manifests** ([`out/01-*.manifest.json`](out/)): `script` `main.py`, `script_sha256`
  `3c756c01a393136590538a4558071476681794cb1db8bc50eb6bf6b73fadeede` (`shasum -a 256 main.py` at
  the fix); **`git_head` `3a24ea53962a3a02de412032807c0fd3e9afcb3f`, `git_dirty` false** in all
  three; `packages` the seven of correction 2, each `editable: false`.
- **Each launch log's `>> packages:` line**, identical in all three:
  ```text
  >> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.3.0 (https://github.com/ds283/RayPoolKit@67a75b97a656accb98195a4bda93f64e6a5f3fb2, requested v0.3.0); ray 2.59.0 (no recorded origin); SQLAlchemy 2.0.55 (no recorded origin); numpy 2.4.6 (no recorded origin); scipy 1.17.1 (no recorded origin)
  ```

**The stop.** The three drivers' pids answered `kill -0` with "no such process", and
`interrupt_when.py` returns after its `sent` line. `ray_cluster.sh stop`, alone: **exit 0**,
`SIGTERM` to 19 processes, after the grace `SIGKILL` to 74894 and 74895, "no process names [SI's
temp dir]; ports 6390 6391 8266 52366 are free", "released the rehearsal lock", "stopped in 19s".
`status` at 18:57, **exit 0**: `lock: free (/Users/ds283/.raypoolkit/rehearsal-lock does not
exist)`, no process, the four ports free; no `gcs_server` or `raylet` on the machine.

### The gates

- **FP holds.** Both stores, built under `ray` 2.59.0 and `SQLAlchemy` 2.0.55, fingerprint to
  `a9f716fb…1ea7`, `rrk-adoption` 04's digest under 2.55.1 and 2.0.46, and `compare_stores` finds
  them equal but for bookkeeping.
- **Token holds** ([`out/01-token.txt`](out/01-token.txt), 18:57:59):
  - `grep -c` of `Token authentication is enabled`, `Generated new authentication token`,
    `InvalidAuthToken` and `AuthenticationError` over R's three launch logs, R's `start` output,
    2.7's two suite outputs and correction 3's second probe: **0 in every file, for every
    pattern.** (The suite outputs are the weak check, correction 3.) For contrast, the first
    pattern counts 1 in V0's `start` output and 1 in the probe on the pins;
  - the cluster's `gcs_server` and `raylet` ran with `RAY_AUTH_MODE=token`;
  - `ls -l ~/.ray/auth_token`: `-rw------- 1 ds283 staff 64 Oct 25 12:51`; `/usr/bin/stat`:
    `2026-10-25 12:51:17 64 -rw-------`, as at the Gate;
  - `grep -r -F -l -f ~/.ray/auth_token .documents/ray-sqla-align/ .prompts/ray-sqla-align/`:
    nothing, **exit 1** (correction 13), on the tree this commit records.

### Nothing else moved

`git diff 8c01877 --name-only` after this commit: `requirements.txt`; the fix's ten paths; this
note, `.documents/ray-sqla-align/out/`, the board and `.prompts/INDEX.md`. `utilities.py`,
`runregistrykit.toml`, `RunDrivers/` and every file under `ComputeTargets/`, `Numerics/`,
`Interpolation/` and `Datastore/` are untouched. `.documents/OPEN-ISSUES.md` is unchanged: no issue
opened.

## The deliberate-breakage record

Each applied to the fix tree by `<scratch>/breakage.py` (one exact replacement,
[`out/01-breakage.py.txt`](out/01-breakage.py.txt)), `tests/test_ray_auth.py` run, the file
restored from a saved copy (`cmp`: identical). Each diff as applied is `out/01-B<n>.diff`; at the
fix commit, on the clean tree, `git apply --check` passes (exit 0) and `git apply -R --check`
fails (exit 1, "patch does not apply") for all four. Never committed to the code.

| | Breakage | Caught by | Result |
|---|---|---|---|
| **B1** | the refresh removed from `config/ray_auth.py` (`if "ray._raylet" in sys.modules: … Config.initialize("")` deleted) | `test_ray_imported_first` | 1 failed, 9 passed |
| **B2** | the module overwrites a preset value (`if "RAY_AUTH_MODE" not in os.environ:` → `if True:`) | `test_a_mode_already_set_is_left_as_it_is`, `test_a_mode_already_set_is_what_ray_sees` | 2 failed, 8 passed |
| **B3** | `plot_InstantonSolutions.py`'s comment and `import config.ray_auth` removed | `test_each_driver_imports_it_before_ray_init[plot_InstantonSolutions.py]`, naming the file | 1 failed, 9 passed |
| **B4** | `ray_cluster.sh`'s export moved after `"$RAY_BIN" start` (to after `local rc=$?`; `bash -n` still 0) | `test_ray_cluster_sh_exports_the_mode_before_ray_start` ("exports RAY_AUTH_MODE after its ray start") | 1 failed, 9 passed |

## Observations not acted on

- **Ray 2.59.0 removes six warnings from SI's default suite** and the one from its integration
  block: the five unclosed `/dev/null` `ResourceWarning`s of `ray/_private/node.py` and the
  accelerator `FutureWarning`. The `FutureWarning` 04 found in every launch log is gone from R's.
- **`ray status` reports `0.0/1.0 GPU`** on SI's cluster under 2.59.0. 04's `ray status` under 2.55.1
  (`.documents/rrk-adoption/out/04-cluster.txt`) has a CPU line and no GPU line.
  `ray_cluster.sh` passes `--num-cpus` and no `--num-gpus`. Not measured further: the stores are
  equal, and nothing here depends on it.
- **The stop needed `SIGKILL` for the `gcs_server`** both times (V0: 71579; R: 74894 and 74895),
  after the 15 s grace, as at 04. The script confirms nothing left and the ports free.
- **R's `reference` ran 1.9 to 2.8 times faster than 04's, stage for stage,** at a load of about 6
  against 04's peak of 135, and still slower than RH2's (6.04, 12.9, 9.59, 2.27 s): stage times
  follow the load, not the version.

## State handed to the review

- `main` at this commit, three commits ahead of `8c01877`, **not pushed**.
- **The venv holds `ray` 2.59.0 and `SQLAlchemy` 2.0.55.** Going back is `pip install ray==2.55.1
  SQLAlchemy==2.0.46`, the user's call; the freeze before is in [`out/01-pip.txt`](out/01-pip.txt).
- R's two stores, `var/datastores/ray-sqla-align-01-reference.sqlite` (`store_id`
  `cb7b2dc3a7834ef49ed927e8b8ee7be4`) and `ray-sqla-align-01-resumed.sqlite` (`c5ea19ff…bd03`),
  with their shards and sidecars, and the three runs under `var/runs/`, for the user to retire.
  The launch files are in `var/ray-sqla-align-01/`.
- SI's cluster is stopped and the lock free.
- No issue opened; `OPEN-ISSUES.md` unchanged. The review of 01 closes the campaign.
