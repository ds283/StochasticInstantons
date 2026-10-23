# Prompt 03 — the wrapper

**Campaign:** [`README.md`](README.md) · **Board items:** **W1**–**W6** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-23, after the user's rulings (README §6). Its orchestrator note, written after
01's and 02's reviews, hands it their counts and governs where it differs from this file.
**Gate:**
- 01 and 02 landed and reviewed, with the gates "Pin" and "Fingerprint" holding (board §2);
- on branch `rrk-adoption`, no tracked change in `git status`;
- no SI Ray process is running. You start no cluster; only the `integration` tests of W6 item 5
  start a private Ray, in a subprocess, through 02's store builder.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Opus**. Signal handling around Ray, a stream proxy, and the order of a
run's last writes. Each was measured the hard way in SecondaryGWKit and carried into ChamPBH; carry
the lessons over, not the bugs.

**Read first:**

1. [`README.md`](README.md): §0.2 (what the siblings do), §0.3 (`main.py`'s shape; the queues'
   printing), §2.2 (03's charter), §5, §6 (R2, R3, R5, P1–P4, P7, P9, P11).
2. **ChamPBH at `807f175`** (read, never edit), the model:
   - `RunDrivers/registered_run.py`, in full. Its docstring (what it changes, what the heartbeat
     means, SIGNALS, REFUSALS); `HEARTBEAT_MEANS`, `BEAT_MIN_INTERVAL` and the patterns;
     `StageTracker`, `RegisteredStream`, `terminal_state`, `SignalLatch`, `make_killed_handler`,
     `install_killed_handler`, `finish_after_exec`, `register`, `main` and `run`;
   - its tests `RunDrivers/tests/test_registered_run*.py` and their helpers;
   - its prompt 03 (`prompts/rrk-adoption/03-the-wrapper.md`), its results note, and its prompt 04's
     verification (`.documents/rrk-adoption-verification.md` §1.4–§1.7: the heartbeat, the signal
     and the hard-kill route as measured).
3. SecondaryGWKit at `216e44d` (read, never edit): `RunDrivers/scoped_pipeline_run.py`, from which
   ChamPBH's was carried, and `docs/a3-v2-readiness-audit.md` S1–S4, what Ray does to a driver's
   `SIGTERM`, measured.
4. RunRegistryKit at `v0.2.0`: its `README.md`, "A run", "Ending a run whose end was never
   recorded" and "The store layer"; `begin`, `Run.heartbeat` and `Run.finish` in
   `runregistrykit/__init__.py`.
5. This repository:
   - `main.py:94-131` (the parse; the provenance line at `:101`; `--inventory` at `:107`; the
     refusals at `:114` and `:129`; `ray.init` at `:131`) and `:1273` (the pool);
   - `config/argument_parser.py` (`create_argument_parser`; `--config` is a YAML file read by
     `configargparse`; `--ray-address` is required);
   - `raypoolkit/RayWorkPool.py` in the venv: the banner (`:206`), the progress lines (`:541`,
     `:588`, `:592`) and the completion lines (`:606-613`), and the notify defaults
     (`DEFAULT_NOTIFY_MIN_INTERVAL = 60`), which `main.py`'s queues do not override;
   - `.documents/dk-and-rpk-migration/rehearsal/build.sh` and `interrupt_when.py`: the
     `** driver exit status` marker, the pid file, and the note that a `SIGTERM`ed driver has been
     seen to exit 134, not 143, because of Ray's failure-signal handler;
   - 02's `tests/test_store_fingerprint_golden.py`: a closed temporary store with real rows;
   - `CLAUDE.md`'s section "Long-running jobs — the run registry" and
     `.claude/rules/run-registry.md`, as 01 wrote them.

---

## 1. What is wanted

A `main.py` run can be launched as a registered run, with `main.py` itself unchanged and still
launchable on its own (R2). The wrapper records the run before anything starts; keeps its heartbeat
and stage current from `main.py`'s own output; records how it ended, a signal included; takes the
store's fingerprint once the store is closed; and exits as `main.py` would have.

It is ChamPBH's `RunDrivers/registered_run.py`, carried over and adapted to SI: SI's parser and
scope, SI's banners and notify interval, and SI's refusals. Where SI's needs are the same as
ChamPBH's, its code is carried over as it is; say in the results note, per function, whether it was
carried unchanged, adapted (and how), or written new.

### 1.1 The items

- **W1 — the package.** `RunDrivers/__init__.py` (a one-line docstring) and
  `RunDrivers/registered_run.py`, run from the repository root:

  ```
  PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --campaign C --prompt N \
      --register SLUG --purpose "one line" -- <main.py's arguments, verbatim>
  ```

  It puts the repository root first on `sys.path` itself, so that it also works without
  `PYTHONPATH`. `REPO_ROOT` is `Path(__file__).resolve().parents[1]` and `MAIN_PY` is
  `REPO_ROOT / "main.py"`. The module docstring is this file's §1 in your words: what it changes
  (nothing of `main.py`), what the heartbeat means, the signals, the refusals and the usage. The
  file header is the repository's (copyright and licence, as `main.py`'s).
- **W2 — its arguments and its refusals**, all before `begin()`, each one `!! ` line on stderr with
  **exit status 2**, as `main.py`'s own refusals (P3):
  - `--campaign`, `--prompt`, `--register` and `--purpose` are required, each a non-empty string
    (P2); `main.py`'s arguments follow a bare `--`;
  - `main.py`'s arguments are parsed with `config.argument_parser.create_argument_parser()`, so
    that a `--database` given in a `--config` YAML file is seen. The parse is for reading only:
    `main.py` parses its own `sys.argv` again. A parse that fails (a missing `--ray-address`, for
    one) is a refusal, with the parser's message;
  - **refused**: no database (`main.py` would print its help and `sys.exit()` with no code, which
    would be recorded `done`); an empty one; `--inventory` (R5);
  - `main.py`'s other checks (`--drop`, the address) are **not** repeated: they are `main.py`'s. A
    run that `main.py` then refuses is recorded `failed` with exit code 2, which is true;
  - a `Refusal(RuntimeError)` class, printed by the entry point as one `!! ` line with no traceback.
    A `ConfigError` from the package is not a refusal and keeps its traceback.
- **W3 — registration**, `register(...)`, called before Ray and before `main.py` runs. It calls
  `runregistrykit.begin(campaign, prompt, slug, purpose, script=<the program>, results=<the
  database>, scope=…, heartbeat_means=HEARTBEAT_MEANS, root=runs_root, client_root=REPO_ROOT)`:
  - **`script` is the program run, `main.py` in production (P4)**. `client_root=REPO_ROOT` always;
  - `results` is the database as the parser resolved it, made absolute;
  - `scope` is one line derived from the parsed arguments, never typed: the config file,
    `--targets`, the potential and grid options that select what is built (counts and ranges when
    long), `--n-collocation-points` and `--alpha-regularization` where given, `--no-store-values`,
    the shards and the job name. Choose the fields from `config/argument_parser.py` and say which;
  - `heartbeat_means` (P7) says: a beat is taken from stdout, at most once every 30 s, and the line
    is the stage; `RayWorkPool` prints a progress line only after completed work, and in this
    repository no more often than every 60 s (RayPoolKit's default, which `main.py` does not
    override), so a fresh beat means work completed recently; several queues are silent
    (`title=None`); **a queue whose items each take longer than the staleness window shows stale
    while it works, and the gradient branch's solves have run for hours**: stale means go and look;
  - `runs_root` is `None` in production (the config's `var/runs`); a test passes a temporary one;
  - a `RuntimeError` from `begin` becomes a `Refusal` with `begin`'s text, which names
    `python -m runregistrykit end` when the store is held by an unfinished run. Nothing is created.
    A `ConfigError` is re-raised first, since it is a `RuntimeError` at `v0.2.0`;
  - then the pre-Ray handler for `SIGTERM` and `SIGINT`, and the two stream proxies: **stdout**
    beats, `BEAT_MIN_INTERVAL = 30.0`, its stage read by `StageTracker`; **stderr** is copied and
    never beats. Check ChamPBH's patterns against SI's lines (`RayWorkPool.py:206`, `:541`, `:588`,
    `:592`, `:606-613`, and `main.py`'s own prints); carry them over unchanged unless a line of
    SI's breaks them, and say which;
  - it prints the run id, the manifest's path and the `list` command.
- **W4 — Ray and the signals**, ChamPBH's design (P9): a `SignalLatch`, `make_killed_handler` and
  `install_killed_handler` for `SIGTERM` and `SIGINT`; `ray.init` replaced, before `main.py` runs,
  by a wrapper that calls the real `ray.init` **with `main.py`'s arguments, unchanged**, and
  installs the handler once it returns. `main.py` attaches to the cluster its `--ray-address`
  names. 04 measures what Ray 2.55.1, attached to SI's external cluster, installs. Until then, do
  not simplify on the assumption that it installs nothing.
- **W5 — running `main.py` and finishing.**
  - `sys.argv = [str(MAIN_PY), *main_args]`, then `runpy.run_path(str(program),
    run_name="__main__")`. Nothing of `main.py`'s text is read, substituted or compiled.
  - The `try` around it, and `finish_after_exec`, as ChamPBH's, with `ray.shutdown` as the
    shutdown: `alarm(0)` first; then `done`/0 for a return, `terminal_state(code)` for a
    `SystemExit`, `failed`/1 for any other exception, each with `fingerprint=True`. The fingerprint
    is taken only here, after `main.py`'s `with ShardedPool` has closed, and never in a signal
    handler. On a signal, `killed`, `128 + signum`, with the fingerprint. Otherwise `main.py`'s own
    exception is re-raised, so that its traceback is what it always was.
  - At the very end, `** driver exit status N` on stdout, the status the process exits with: the
    marker `interrupt_when.py` and a `Monitor` read. A `SIGKILL` prints nothing.
  - The test seam: `main(argv=None, *, program=MAIN_PY, runs_root=None)`; the script's entry is
    `run()`.
- **W6 — the tests**, `tests/test_registered_run*.py`, with a non-test helper module beside them if
  you need one (`tests/registered_run_helpers.py`, say). Pytest, in SI's style.
  - **The rules for every test.** None starts Ray in the test process: `ray.init` and
    `ray.shutdown` are replaced by stand-ins (`monkeypatch` or `unittest.mock.patch.object`) before
    the wrapper wraps them, and each test asserts `ray.is_initialized()` is false at the end. Every
    run directory is in a temporary runs root, every store in a `tempfile` directory, and nothing
    under `var/` is read or created.
  - **The stand-in program** is a small script written into the test's temporary directory. It
    calls `ray.init(address=…)` as `main.py` does, prints `RayWorkPool`'s banner and progress lines
    (from `RayWorkPool.py`'s format strings), and then returns, exits with a code, raises, or waits
    to be signalled.
  1. **Registration:** the manifest exists before the stand-in's first line runs; it records
     `script` as the stand-in's path and hash, `results` as the absolute database, `scope`, and
     `heartbeat_means` with the 60 s floor and the gradient branch stated; its `packages` names
     `runregistrykit`, `datastorekit` and `raypoolkit`; its `argv` is the wrapper's.
  2. **The heartbeat:** lines closer together than 30 s beat once (a fake clock); a banner changes
     the stage at once; the stage reads the progress line's title and fraction, and "all work items
     complete" at the end; stderr writes do not beat; every write reaches the real stream unaltered,
     and `stdout.log` holds it.
  3. **The outcomes**, for a return, `sys.exit(2)`, `sys.exit(1)` and a `RuntimeError`: the status
     is `done`/0, `failed`/2, `failed`/1 and `failed`/1; the wrapper's own exit status is the same;
     `** driver exit status N` is the last stdout line; the `RuntimeError`'s traceback reaches
     `stderr.log`.
  4. **The signals:** the handler, called directly with a real `Run`, records `killed`/143 at once,
     without a fingerprint, and raises `SystemExit(143)`; `finish_after_exec` keeps `killed`
     whatever exception then arrives, and adds the fingerprint; a second signal is ignored with a
     line; a stand-in `ray.init` that installs its own `SIGTERM` handler, as Ray does, is followed
     by the wrapper's; **one subprocess**: the wrapper on a stand-in that waits, sent a real
     `SIGTERM` once its banner is on stdout, gives `killed`/143 and exit status 143. The subprocess
     stubs `ray.init` through the helper module, and is reaped in a cleanup registered before its
     first read.
  5. **The fingerprint** (`integration`, P11), on a closed temporary store built as 02's golden test
     builds it: with a sidecar made by `runregistrykit.stores.create_sidecar(…,
     client_root=REPO_ROOT)`, a `done` run's status has `fingerprint_sidecar: "written"` and the
     sidecar's fingerprint equals the golden digest; without one, the status says "not written", and
     the run is still `done`. Build the store once per module.
  6. **The refusals** (exit 2, one `!! ` line, no traceback, nothing created in the runs root): each
     of the four required flags missing; no `--`; no database; `--inventory`; `main.py`'s parser
     refusing (no `--ray-address`); and `begin` on a store that an unfinished run in the same runs
     root names. After `python -m runregistrykit end <that run> --reason … --root <the runs root>`
     (by subprocess, on a dead child's run), the same registration is accepted.
  7. **`main.py` is unchanged**: none of `main.py`, `plot_InstantonSolutions.py`,
     `plot_GradientCoupledSolutions.py` and `utilities.py` imports `runregistrykit` (by `ast`).
     The `git diff 1c223e8` check is the results note's, not a test's.
  8. **By `ast`**: every `.finish(` in the wrapper that lies inside a signal handler passes no
     `fingerprint=True`, and every one after the program passes it.
- **The prose this commit makes false.** `CLAUDE.md`'s section "Long-running jobs — the run
  registry" and `.claude/rules/run-registry.md` name the wrapper as a thing prompt 03 adds; make
  each sentence definite, with the usage line. Nothing else.

---

## 2. Verification

1. **Before any edit:** both suites at the counts 02 handed on.
2. **After:**
   - both suites: the default selection with W6's tests but item 5, and `integration` with item 5;
   - `PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --help`, exit 0;
   - no `var/runs/` entry created by the suites (`./venv/bin/python -m runregistrykit list`: no
     runs);
   - `git diff 1c223e8 -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py
     utilities.py` empty.
3. **The beat's timing, on paper.** From `RayWorkPool.py` and `main.py`'s queue settings, say in
   the results note how often a progress line can be printed in each stage, which stages are silent,
   and the longest silence a healthy rehearsal build (`quadratic-minimal.yaml`, `--targets
   homogeneous`; README §0.3) could have, so that 04 knows what to expect.
4. **Deliberate breakages** (README §5: each recorded as a diff, never committed). Each must fail at
   least one new test, named in the results note:
   - the handler installed before the wrapped `ray.init` only, not after;
   - `fingerprint=True` passed by the handler;
   - the wrapper exits 0 whatever `main.py` exited with;
   - the stdout proxy drops a line when the copy fails;
   - `script` recorded as the wrapper instead of the program;
   - the `ConfigError` caught as a refusal.

## 3. Acceptance

1. W1–W6 as §1.1 says, and the prose of §1.1's last item.
2. §2's checks in the results note, each with its command and output.
3. Suites: the counts 02 handed on, plus W6's tests in their selections.
4. **One commit**, with the results note `.documents/rrk-adoption/03-the-wrapper.md`. The board: row
   03, W1–W6, the gate "Wrapper", and a `### 5.4 After prompt 03 (<date>)`. Write "this commit"
   where the SHA goes.

## 4. Stop conditions: stop and ask

- `main.py` cannot be run by `runpy.run_path` as it is. (It reads no `__file__` and installs no
  signal handler at `1c223e8`; find what changed before stopping.)
- A test cannot be written without starting Ray in the test process, or without a running cluster.
- RunRegistryKit behaves otherwise than its README says for `begin`, `finish` or `end`. That is a
  package defect, reported there, never worked around (README §5).
- A choice here would change what `main.py` computes, or would need an edit to `main.py`, the plot
  scripts or `utilities.py`.
- Anything would need an edit outside §5's list.

## 5. What this prompt does not do

- **Files it changes:**
  - `RunDrivers/__init__.py` and `RunDrivers/registered_run.py` (new);
  - `tests/test_registered_run*.py` and any non-test helper beside them (new);
  - `CLAUDE.md` and `.claude/rules/run-registry.md` (the sentences of §1.1's last item);
  - this board, and the results note.
- It runs no real build, starts no cluster, and opens no store but its tests' temporary ones.
- It does not touch `main.py`, the plot scripts, `utilities.py` or the rehearsal scripts.

**One commit** in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
