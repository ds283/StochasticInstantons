# 03 — the wrapper

**Subject:** Add the registered-run wrapper for main.py and its tests
**Commit:** `16e1cc1`, on branch `rrk-adoption`, on top of `622c66f`
**Date:** 2026-10-25, by Claude Opus 5.5
**Result:** **COMPLETE.** W1–W6 shipped. 106 new tests in six modules and one helper: default
selection 744 → **848** (847 passed, 1 skipped; +104), `integration` 70 → **72** (71 passed, 1
skipped; +2). The new files, run three times in a row, passed 106 of 106 each time. All six
deliberate breakages caught. No §4 stop condition was met. No issue opened. `main.py`, the plot
scripts and `utilities.py` are unchanged since `1c223e8`.

Prompt: [`.prompts/rrk-adoption/03-the-wrapper.md`](../../.prompts/rrk-adoption/03-the-wrapper.md).
The orchestrator's note, [`.prompts/rrk-adoption/orchestrator/prompt-03.md`](../../.prompts/rrk-adoption/orchestrator/prompt-03.md),
governed where it differs from the prompt: its twelve corrections and the ChamPBH rulings it
restates are classified below. The model is ChamPBH's `RunDrivers/registered_run.py` at `807f175`.
Scratch outputs were kept outside the repository.

## What shipped

- **W1 — the package.** `RunDrivers/__init__.py` (the licence header and a one-line docstring) and
  `RunDrivers/registered_run.py`, run from the root as
  `PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --campaign C --prompt N --register
  SLUG --purpose "one line" -- <main.py's arguments>`. It puts `REPO_ROOT` first on `sys.path`, so
  it also runs without `PYTHONPATH` (the refusal tests run it so). `REPO_ROOT =
  Path(__file__).resolve().parents[1]`, `MAIN_PY = REPO_ROOT / "main.py"`. Both files carry
  `config/fingerprint.py`'s licence header. The module docstring says what it changes (nothing of
  `main.py`), what the heartbeat means, the signals, when there is no marker, the refusals and the
  usage.
- **W2 — the flags and the refusals, all before `begin`, each one `!! ` line on stderr, exit 2.**
  The four flags are required and checked non-empty after `strip()`; `argv` is split at its first
  bare `--`, and no `--` is refused (unless `-h`/`--help` is among the wrapper's own arguments).
  Both parsers have `error` replaced on the instance, so a missing flag, an unknown option, a bad
  value and a missing `--ray-address` are each one line. Refused after the parse: no database (with
  the reason: `main.py` would print its help and `sys.exit()` with no code, recorded `done`), an
  empty one, and `--inventory`. `main.py`'s `--drop` and address checks are not repeated. `--
  --help` prints `main.py`'s help, exit 0, nothing registered.
- **W3 — registration.** `register` calls `runregistrykit.begin(campaign, prompt, slug=--register,
  purpose, argv=[<the wrapper's path>, *argv], script=str(program), results=os.path.abspath(<the
  database>), scope=describe_scope(parsed, defaulted), heartbeat_means=HEARTBEAT_MEANS.format(…),
  root=runs_root, client_root=str(REPO_ROOT))`. A `ConfigError` is re-raised; any other
  `RuntimeError` becomes `Refusal(str(e)) from e`. Then `terminal` for `SIGTERM` and `SIGINT`, the
  stdout proxy (beats, `BEAT_MIN_INTERVAL`, a `StageTracker`), the stderr proxy (copies, never
  beats), and three `>> ` lines: the run id, the manifest's path and the `list` command.
- **W4 — Ray and the signals.** `main` replaces `ray.init` by `_registered_ray_init(*init_args,
  **init_kwargs)`, which calls the real `ray.init` with `main.py`'s arguments unchanged and then
  `install_killed_handler(run, latch)`.
- **W5 — the program and the finish.** `sys.argv = [str(program), *main_args]`, then
  `runpy.run_path(str(program), run_name="__main__")` in a `try` whose one handler is `except
  BaseException as exc: finish_after_exec(run, exc, latch, ray.shutdown); raise`, and
  `finish_after_exec(run, None, latch, ray.shutdown)` after it. `run` is the entry: the refusal
  print, then in a `finally` every proxy stops beating and `** driver exit status N` is printed on a
  line of its own; the copies are closed on the clean path only.
- **W6 — the tests**: 106 in six modules, and one non-test helper, `tests/registered_run_helpers.py`
  (below).
- **The prose.** `CLAUDE.md`'s "Launching" sentence (`:55-57`) is now definite, with the usage line.

### The module's public names

- `REPO_ROOT`, `MAIN_PY`: the root, and the program run in production.
- `Refusal(RuntimeError)`: a check that stops the driver before anything is registered, and
  `begin`'s own refusal; printed by `run` as one `!! ` line, exit 2.
- `EXIT_MARKER = "** driver exit status"`: `build.sh`'s marker.
- `BEAT_MIN_INTERVAL = 30.0`: the heartbeat's throttle.
- `NOTIFY_MIN_INTERVAL = 60.0`, `NOTIFY_TIME_INTERVAL = 300.0`, `NOTIFY_BATCH_SIZE = 500`:
  RayPoolKit's three notify defaults, which `main.py` does not override.
- `HEARTBEAT_MEANS`: the manifest's `heartbeat_means`, a format string (below).
- `StageTracker`: the stage, read off the run's own lines.
- `RegisteredStream`: the pass-through proxy with its copy and, on stdout, the beat (`write`,
  `writelines`, `flush`, `mid_line`, `stop_beating`, `close_copy`).
- `terminal_state(code)`: the state for a `SystemExit` that no signal caused.
- `KILLED_SIGNALS = (SIGTERM, SIGINT)`.
- `SignalLatch`, `make_killed_handler(run, latch, stream=None)`,
  `install_killed_handler(run, latch, stream=None)`, `finish_after_exec(run, exc, latch, shutdown,
  *, alarm=signal.alarm, stream=None)`: the signal design.
- `USAGE_TAIL`: the wrapper's form, for its refusals and its help.
- `parse_arguments(argv)`: the split, both parses and the refusals before `begin`; returns
  `(args, main_args, parsed, defaulted)`.
- `SCOPE_MAX_VALUES = 6`; `describe_scope(parsed, defaulted=frozenset())`: the manifest's `scope`.
- `register(args, parsed, argv, *, defaulted=frozenset(), program=MAIN_PY, runs_root=None)`:
  `begin`, `terminal`, the proxies and the three lines; returns the `Run`.
- `main(argv=None, *, program=MAIN_PY, runs_root=None)`: the work, and the tests' seam.
- `exit_status(code)`: Python's own status for `SystemExit(code)`.
- `run(argv=None, *, program=MAIN_PY, runs_root=None)`: the script's entry; the `__main__` block
  is `run()` alone.

### Per function: carried, adapted or new

| Name | From ChamPBH's `807f175` |
|---|---|
| module docstring | adapted: SI's line numbers, SI's refusals, the heartbeat as correction 2 says, Ray 2.55.1's line numbers (correction 11), the gradient branch |
| `REPO_ROOT`, `MAIN_PY`, the `sys.path` insertion | carried (the comment names no `tools/surfing_scan.py`, which SI has not) |
| `Refusal` | carried; its docstring says "as `main.py`'s own refusals exit" |
| `EXIT_MARKER`, `BEAT_MIN_INTERVAL` | carried unchanged |
| `NOTIFY_FLOOR` | **replaced** by `NOTIFY_MIN_INTERVAL`, `NOTIFY_TIME_INTERVAL`, `NOTIFY_BATCH_SIZE` (new; correction 2) |
| `HEARTBEAT_MEANS` | adapted (correction 2) |
| `_STAGE_BANNER` | adapted: `** ` only (correction 3) |
| `_QUEUE_PROGRESS`, `_QUEUE_COMPLETE` | carried unchanged (SecondaryGWKit's) |
| `StageTracker` | carried unchanged |
| `RegisteredStream` | carried unchanged (one docstring reference now `worker.py:2192`) |
| `terminal_state`, `KILLED_SIGNALS`, `SignalLatch`, `_say`, `_signal_name`, `_now` | carried unchanged |
| `make_killed_handler`, `install_killed_handler`, `finish_after_exec`, `_shut_down`, `_code_text` | carried unchanged |
| `_FLAGS`, `USAGE_TAIL`, `_refusing` | carried unchanged |
| `_wrapper_parser` | adapted: `--campaign`'s help line only |
| `parse_arguments` | adapted: no `ray_address_problem` (correction 6); its own refusal for no database (correction 5); it also returns `defaulted` |
| `SCOPE_MAX_VALUES`, `_number`, `_values` | carried unchanged |
| `_dimensionful` | dropped (ChamPBH's eV/Mp choices) |
| `_decades`, `_axis` | new |
| `describe_scope` | new, for SI's parser |
| `register` | adapted: `defaulted`, the format keys of `HEARTBEAT_MEANS`, the `>> ` lines (correction 4) |
| `main` | adapted: the four-tuple, `defaulted` passed on |
| `exit_status`, `_proxies` | carried unchanged |
| `run` | adapted: a refusal text that already begins `!! ` loses it (correction 6) |

`diff` against ChamPBH's file, over `StageTracker` to `_wrapper_parser`, shows two lines: the Ray
reference and the help string.

### `HEARTBEAT_MEANS` as committed

```
"Refreshed when the run writes a line to stdout, at most once per {interval:.0f} s, or at "
"once when the line changes the stage, and the line it came from is the `stage` in "
"status.json. RayWorkPool prints a progress line only after ray.wait has returned completed "
"work, never sooner than {notify_min:.0f} s after its last one, and otherwise only once "
"{notify_time:.0f} s have passed or more than {notify_batch} queue events have completed "
"since it (RayPoolKit's defaults, which main.py does not override), so a fresh heartbeat from "
"it means work completed within about five minutes. Several of main.py's queues are silent "
"(title=None). Ray also forwards the workers' own output to the driver's stdout, so a "
"worker's line beats too, without moving the stage. It does NOT mean any Ray task or actor "
"is progressing, and the converse does not hold: a stage that prints nothing for longer than "
"the staleness window ({stale:.0f} s, `list --stale-after`), such as a queue whose items each "
"take longer than that, is reported stale while it works, and the gradient branch's solves "
"have run for hours each. Stale means go and look."
```

Formatted, as a stubbed run's manifest holds it:

> Refreshed when the run writes a line to stdout, at most once per 30 s, or at once when the line
> changes the stage, and the line it came from is the `stage` in status.json. RayWorkPool prints a
> progress line only after ray.wait has returned completed work, never sooner than 60 s after its
> last one, and otherwise only once 300 s have passed or more than 500 queue events have completed
> since it (RayPoolKit's defaults, which main.py does not override), so a fresh heartbeat from it
> means work completed within about five minutes. Several of main.py's queues are silent
> (title=None). Ray also forwards the workers' own output to the driver's stdout, so a worker's
> line beats too, without moving the stage. It does NOT mean any Ray task or actor is progressing,
> and the converse does not hold: a stage that prints nothing for longer than the staleness window
> (900 s, `list --stale-after`), such as a queue whose items each take longer than that, is
> reported stale while it works, and the gradient branch's solves have run for hours each. Stale
> means go and look.

### The scope

Fields, from `config/argument_parser.py`, in this order: the config file, or "no config file";
`--targets`; `--potential-type` and **its own parameter only** (`m` for `Quadratic`, from
`--m-values-Mp` or the `--log10-m-*` range; `lambda` for `Quartic`, from `--lambda-values` or the
`--log10-lambda-*` range: the one `config/model_list.py:19-113` reads); the `N_init`, `N_final`
and `delta_Nstar` choices, or `sample grid <csv>` when `--sample-grid-csv` is given (it replaces
them); `n_collocation_points` and `alpha_regularization` where given; `--no-store-values` and
`stop after …` where given; the shards; the job name, or "no job name". Values read as `:g` up to
six, else a count and a range; a range reads as its arguments. The labels are `main.py`'s own
(`-- n_collocation_points:`, `delta_Nstar`, `Quadratic m`).

**04's reference** (`TestScope.test_the_scope_of_04s_reference`, a literal), for `--config
quadratic-minimal.yaml --database var/datastores/rrk-adoption-04-reference.sqlite --job-name
rrk-adoption-04-reference --targets homogeneous --n-collocation-points 5 --alpha-regularization
0.01 --ray-address 127.0.0.1:6390`:

```
config quadratic-minimal.yaml; targets homogeneous; potential Quadratic; m 1e-05 Mp; N_init 20–20, 1 sample; N_final 5–5, 1 sample; delta_Nstar 0.1–3, 10 samples; n_collocation_points 5; alpha_regularization 0.01; 10 shards; job rrk-adoption-04-reference
```

(`Quadratic`, `m` and the 10 shards come from `quadratic-minimal.yaml`; `--alpha-regularization
0.01` equals the parser's default and is shown, since it is given.)

### The stage patterns

| Pattern | | Matches |
|---|---|---|
| `_STAGE_BANNER` `^\s*\*\*\s+(\S.*?)\s*$` | **adapted** (ChamPBH's also matched `>>`) | RayWorkPool's `\n** {title}` (`:206`); `main.py`'s `** BUILDING PARAMETER SAMPLING GRIDS`, `** COSMOLOGICAL PARAMETERS: …`, `** DIFFUSION MODEL: …`, `** … LOOKUP:`, `** STAGE 4: COMPACTION FUNCTIONS`, `** Stopping after …`, `** Skipping …` |
| `_QUEUE_PROGRESS` | carried | RayWorkPool's progress line (`:588`) |
| `_QUEUE_COMPLETE` | carried | RayWorkPool's completion line (`:606`) |

Every `>> ` line a build prints is information inside a stage: `main.py:101`'s provenance,
DatastoreKit's open, replication and prune lines (`ShardedPool.py:271`, `:308`, `:2147-2177`,
`:2542-2554`), `main.py`'s grid counts (`:654-659`, `:1198-1211`). No line of SI's breaks the
progress or completion patterns. `!! WARNING` (`:541`) and the second progress line (`:592`,
`inflight: …`) move nothing.

**The registration lines are kept from the stage** by their prefix: `register` prints them as
`>> registered_run: registered as …`, `>>   manifest …`, `>>   list it with: …`, SI's own form for
information, which the banner pattern does not read. They reach stdout and `stdout.log` unaltered
and beat once with no stage; the stage stays unset until `main.py`'s first banner
(`TestRegisterInProduction` asserts `stage` is `None` after `register`).

### The tests

| Module | Tests | Time (three runs, the module's share) | What |
|---|---|---|---|
| `test_registered_run.py` | 15 | 1.9, 2.0, 2.6 s | in-process: the manifest before the program's first line; `script`, its hash, `results`, `scope`, `git_head` `"unknown"`, `packages`; `heartbeat_means`; `argv`; the three printed lines; the program's `argv`, `__name__`, `__file__`; `ray.init`'s arguments; the handler after `ray.init`; `done` at its last stage; `register(program=MAIN_PY)`; three scope tests; `ConfigError` and `RuntimeError` from `begin` |
| `test_registered_run_streams.py` | 39 | 1.5, 1.6, 2.0 s | the beat (fake clock); the stages; `main.py`'s banners (10, parametrized); the `>> ` lines (16, parametrized); `main.py`'s other lines; stderr does not beat; `stop_beating`; pass-through and copy; a failing copy; a failing heartbeat; a second thread; two threads; `mid_line`; the attributes |
| `test_registered_run_signals.py` | 24 | 1.8, 1.8, 2.1 s | the handler on a real `Run`; a second signal; `SIGINT`; a failing write; once decided; `install`; after a signal (6, parametrized); the real-run fingerprint; the alarm first; no signal (8, parametrized); a failing shutdown; **one subprocess**, a real `SIGTERM` |
| `test_registered_run_outcomes.py` | 19 | 14.3, 13.3, 15.3 s | by subprocess with Ray stubbed: the four outcomes; the marker after an unfinished line; `begin`'s refusal, `end`, and the same registration accepted; by the real script: the four flags missing, an empty flag, no `--`, no database, an empty one, an unknown option, `--inventory`, no `--ray-address`; `--help` twice |
| `test_registered_run_source.py` | 7 | 0.1, 0.1, 0.1 s | by `ast`: no driver imports the registry or the wrapper; the `run.finish(` calls (4 outside, 2 inside); `begin`'s two handlers; the `ray.init` wrapper; no `ray` at module scope; the notify numbers are RayPoolKit's; no `RayWorkPool(` in `main.py` passes a `notify_` keyword |
| `test_registered_run_fingerprint.py` (`integration`) | 2 | 15.9, 18.2, 18.6 s (the store's build, once) | 02's golden store, copied per test: with a sidecar, `written` and the golden digest; without, `not written … (there is none)` and `done` |

The three runs of the six files together (`RAY_ADDRESS=local ./venv/bin/python -m pytest -q -p
no:cacheprovider tests/test_registered_run*.py`), in a row: **106 passed** in 36.2 s (load 51.7),
37.6 s (31.1) and 41.4 s (29.8). The slowest single test is
`TestBeginsRefusal::test_refused_then_accepted_after_end`: 1.6 s at load 7, 3.4–5.9 s at load
30–50, the cost of its four subprocesses. The outcome tests take 0.8 s each at load 7 and 1.4–2.0 s
at load 30–50. **None is marked `slow`**: none drives an ODE, a Picard iteration or a dense sweep
(`.claude/rules/test-selection.md`'s bar), and their cost is interpreter start-up; P11 says none is
`slow`.

By name:
- `test_registered_run`: `TestRegistration` (`test_the_manifest_is_written_before_the_programs_first_line`,
  `test_the_manifest_records_the_program_the_store_the_scope_and_the_packages`,
  `test_heartbeat_means_states_the_floor_the_interval_and_the_gradient_branch`,
  `test_the_manifests_argv_is_the_wrappers`, `test_it_prints_the_run_id_the_manifest_and_the_list_command`);
  `TestTheProgram` (`test_it_runs_as_main_from_its_own_file_with_main_pys_arguments`,
  `test_ray_init_gets_the_programs_arguments_unchanged`,
  `test_the_wrappers_handler_replaces_rays_after_ray_init`, `test_a_returning_program_is_done_at_its_last_stage`);
  `TestRegisterInProduction` (`test_the_script_is_main_py_with_its_hash_and_this_repositorys_head`);
  `TestScope` (`test_the_scope_of_04s_reference`, `test_more_than_six_values_read_as_a_count_and_a_range`,
  `test_a_value_equal_to_the_default_is_still_given`); `TestBeginsErrors`
  (`test_a_config_error_is_not_a_refusal`, `test_a_runtime_error_is_a_refusal_with_its_text`).
- `test_registered_run_streams`: `TestTheBeat` (`test_lines_closer_than_thirty_seconds_beat_once`,
  `test_a_banner_changes_the_stage_at_once`, `test_the_progress_and_completion_stages`,
  `test_main_pys_own_banners_are_stages` ×10, `test_a_double_angle_line_is_not_a_stage` ×16,
  `test_main_pys_other_lines_move_nothing`, `test_stderr_does_not_beat`,
  `test_a_stream_that_has_stopped_beating_still_copies`); `TestThePassThrough`
  (`test_every_write_reaches_the_real_stream_unaltered_and_the_copy`,
  `test_a_copy_that_fails_costs_neither_the_line_nor_the_beat`, `test_a_heartbeat_that_fails_costs_no_line`,
  `test_a_line_from_another_thread_reaches_both_and_beats`, `test_two_threads_writing_at_once_lose_no_line`,
  `test_it_knows_when_the_last_write_left_a_line_unfinished`, `test_attributes_are_the_real_streams`).
- `test_registered_run_signals`: `TestTheHandler` (`test_on_a_real_run_it_records_killed_143_at_once_without_a_fingerprint`,
  `test_a_second_signal_is_ignored_with_a_line`, `test_sigint_gives_130`,
  `test_a_write_that_fails_does_not_stop_the_raise`, `test_once_the_outcome_is_decided_a_signal_is_only_noted`);
  `TestInstall` (`test_it_takes_sigterm_and_sigint`); `TestAfterASignal`
  (`test_it_is_killed_143_with_the_fingerprint_whatever_reaches_the_driver` ×6,
  `test_on_a_real_run_the_fingerprint_is_taken_and_the_state_stays_killed`, `test_the_alarm_is_cancelled_first`);
  `TestWithNoSignal` (`test_every_outcome_is_recorded_with_the_fingerprint` ×8,
  `test_a_shutdown_that_fails_does_not_replace_the_exception`); `TestARealSigterm`
  (`test_it_is_killed_143_and_exits_143_with_the_marker_last`).
- `test_registered_run_outcomes`: `TestTheOutcomes` (`test_each_outcome` ×4);
  `TestTheMarkerIsALineOfItsOwn` (`test_after_an_unfinished_line`); `TestBeginsRefusal`
  (`test_refused_then_accepted_after_end`); `TestTheRefusalsBeforeBegin`
  (`test_each_of_the_four_flags_missing` ×4, `test_an_empty_flag`, `test_no_bare_double_dash`,
  `test_no_database`, `test_an_empty_database`, `test_an_unrecognised_main_py_option`,
  `test_inventory`, `test_no_ray_address`); `TestHelp` (`test_the_wrappers_help`,
  `test_main_pys_help_registers_nothing`).
- `test_registered_run_source`: `test_no_driver_imports_the_registry_or_the_wrapper`,
  `test_handlers_pass_no_fingerprint_and_every_later_finish_passes_it`,
  `test_the_one_begin_call_has_the_two_handlers_in_order`,
  `test_the_ray_init_wrapper_passes_the_arguments_unchanged_then_installs_the_handler`,
  `test_the_module_imports_nothing_of_ray_at_module_scope`,
  `test_the_notify_numbers_are_raypoolkits_defaults`,
  `test_no_raywork_pool_in_main_py_passes_a_notify_keyword`.
- `test_registered_run_fingerprint`: `test_with_a_sidecar_the_golden_fingerprint_is_written_to_it`,
  `test_without_one_it_is_not_written_and_the_run_is_still_done`.

**The helper, `tests/registered_run_helpers.py`.** Run as `python -u
tests/registered_run_helpers.py RUNS_ROOT PROGRAM -- <the wrapper's arguments>` from the root, it
puts the root on `sys.path`, patches `ray.init` (a stand-in that installs a Ray-like `SIGTERM`
handler, `sys.exit(signum)`) and `ray.shutdown`, and calls `registered_run.run`; it ends with
`ray.is_initialized()` false, or says so and exits 99. As a module it holds the stand-in program
(written into the test's temporary directory; its first statement lists the manifests under the
runs root; it records `sys.argv`, `__name__`, `__file__` and the `SIGTERM` handler before and after
its `ray.init(address=…)`; it prints RayWorkPool's banner (`STAGE 2: FULL MSR INSTANTONS`),
progress and completion lines with RayWorkPool's format strings; then it returns, exits 2 or 1,
raises, waits after its banner, or ends on an unfinished line), `StringWriter`, `Recorder`,
`TakeOver`, `in_process` (the cleanup registered with `request.addfinalizer` before the call),
`reap`, the launchers, `var_state`, and the autouse fixture `no_ray_at_the_end`.

**The rules held.** No test starts Ray in the test process: `ray.init` and `ray.shutdown` are
stand-ins, patched before the wrapper wraps them. The only Ray caused is `_STORE_SCRIPT`'s private
`ray.init(address="local")`, in its subprocess, for the fingerprint module. Every run directory is in
a temporary runs root; the one store is 02's, in `test_inventory_store.store`'s `tempfile`
directory, copied into each test's `tmp_path`. The real script runs only for refusals before
`begin` and `--help`.

## Deviations from the prompt

**The orchestrator's corrections** (`orchestrator/prompt-03.md` §0):
1. **`STRUCTURALLY REQUIRED`** (correction 1): the board section is `### 5.5`, not `5.4`.
2. **`STRUCTURALLY REQUIRED`** (correction 2): the progress line's cadence is the 60 s floor
   **and** 300 s or 500 events, not "every 60 s". `HEARTBEAT_MEANS` says so; §2.3 below uses it.
   **`IMPLEMENTATION CHOICE`** (correction 2): the three numbers are module constants formatted into
   the sentence; `test_the_notify_numbers_are_raypoolkits_defaults` and
   `test_no_raywork_pool_in_main_py_passes_a_notify_keyword` (which also refuses a `**kwargs` and
   counts the 14 calls) guard them; test 1 checks the floor, the interval and the gradient branch.
3. **`IMPLEMENTATION CHOICE`** (correction 3): `_STAGE_BANNER` matches `** ` only; 16 `>> ` lines
   are tested inert and 10 `** ` banners tested to move the stage.
4. **`IMPLEMENTATION CHOICE`** (correction 4): the registration lines begin `>> `, which correction 3
   makes inert, rather than a tracker that skips them. Tested in `TestRegisterInProduction`.
5. **`NOTED`** (correction 5): SI's `--database` is `default=None`, so the no-database refusal is
   needed for the prompt's reason; its text says so. `error` is replaced on the parser instance.
6. **`STRUCTURALLY REQUIRED`** (correction 6): no address check is carried; a missing
   `--ray-address` is the parser's refusal (`test_no_ray_address`). `run` strips a leading `!! `
   from any refusal text, and every refusal test asserts no `!! !!`.
7. **`STRUCTURALLY REQUIRED`** (correction 7): the licence header is `config/fingerprint.py`'s, on
   every new `.py` file.
8. **`STRUCTURALLY REQUIRED`** (correction 8): only `CLAUDE.md`'s sentence changed;
   `.claude/rules/run-registry.md` has no sentence that names the wrapper as future and is not
   touched.
9. **`IMPLEMENTATION CHOICE`** (correction 9): the fingerprint module imports `store` (and
   `_STORE_SCRIPT`) from `test_inventory_store`, unmodified, and `GOLDEN` and `without_taken` from
   `test_store_fingerprint_golden`; each test copies the store's directory into its own `tmp_path`.
   The "without" test also asserts that the copy's directory gained no file.
10. **`NOTED`** (correction 10): `packages` holds `datastorekit`, `raypoolkit` and `runregistrykit`
    (0.5.0, 0.3.0 and 0.2.0 at their pinned commits, in the by-hand run below).
11. **`NOTED`** (correction 11): the docstrings cite Ray 2.55.1's `worker.py:1656-1661` and `:2192`.
12. **`NOTED`** (correction 12): the helper is imported as `registered_run_helpers`; its subprocess
    form inserts the root on `sys.path`. No formatter; the style matched by eye.

**ChamPBH's rulings for 03** (its note 03), as the orchestrator's note restates them:
13. **`IMPLEMENTATION CHOICE`** (ChamPBH's note 03, ruling 2): `argv` split at its first bare `--`;
    the wrapper's parser's `error` replaced; each flag non-empty after `strip()`.
14. **`IMPLEMENTATION CHOICE`** (ruling 4): the manifest's `argv` is `[<the wrapper's path>,
    *argv]`; test 1 asserts `script` and `results` absolute and `git_head` `"unknown"` for a stand-in
    in a temporary directory, with a comment. **`STRUCTURALLY REQUIRED`**: `TestRegisterInProduction`
    calls `register` alone with `program=MAIN_PY`: `script == "main.py"`, its SHA-256, `git_head`
    equal to `git rev-parse HEAD`; it restores the streams and both handlers.
15. **`IMPLEMENTATION CHOICE`** (ruling 5): the stand-in records `sys.argv`, `__name__` and
    `__file__`; `TestTheProgram` asserts them.
16. **`IMPLEMENTATION CHOICE`** (ruling 6): a `threading.RLock` around each proxy's bookkeeping only;
    the second-thread test, and a two-thread test of 400 lines.
17. **`IMPLEMENTATION CHOICE`** (ruling 7): `main` is the work, `run` the entry; `run`'s `finally`
    stops every proxy beating, then prints the marker on a line of its own, then closes the copies
    on the clean path only. The marker is never the stage (the outcome tests and the real-`SIGTERM`
    test assert the stage).
18. **`STRUCTURALLY REQUIRED`** (ruling 8): the outcomes, the real `SIGTERM` and `begin`'s refusal run
    through the helper as a subprocess with `python -u`; its `ray.init` stand-in installs
    `sys.exit(signum)`. The refusals before `begin` run the real script, no stub, no `PYTHONPATH`,
    `cwd` the root, and assert `var/runs`' listing unchanged. Every subprocess is reaped by a cleanup
    registered before its first read.
19. **`IMPLEMENTATION CHOICE`** (the note's "two tests the breakages need"): a copy whose `write`
    raises (`test_a_copy_that_fails_costs_neither_the_line_nor_the_beat`, which also asserts that a
    later line still beats) and `begin` patched to raise `ConfigError`
    (`test_a_config_error_is_not_a_refusal`).
20. **`NOTED`** (test 8): 4 `run.finish(` outside a handler, each passing `fingerprint=True`, and 2
    inside (`terminal`, `killed_handler`), neither: the note's count.
21. **`IMPLEMENTATION CHOICE`** (the note's "Scope", ChamPBH's ruling 11): the scope is the
    arguments as given. Two choices of mine within it: the potential's own parameter only (`m` for
    `Quadratic`, `lambda` for `Quartic`), since the other is never read (`config/model_list.py`), and
    "where given" read from `configargparse`'s documented `get_source_to_settings_dict()`, whose
    `defaults` entry lists the options left at their default. So a value given equal to the default
    (04's `--alpha-regularization 0.01`) is shown, and one not given is not
    (`test_a_value_equal_to_the_default_is_still_given`). `parse_arguments` returns that set as a
    fourth element, and `register` and `describe_scope` take it.

**Mine:**
22. **`STRUCTURALLY REQUIRED`: the "Ray not initialised at the end" check is "as it found it".** In
    the whole default selection, `test_plot_extraction_golden.py` and `test_plot_adapters_golden.py`
    call `ray.init(ignore_reinit_error=True)` in the test process from a module-scoped autouse
    fixture and never shut it down, so every module collected after them, these among them, starts
    with Ray initialised. The first whole-suite run failed 104 teardowns on the literal assertion,
    and no test of mine had started Ray. `no_ray_at_the_end` now records `ray.is_initialized()`
    before the test and, if it was false, asserts it false after. Run on their own (the three runs,
    the breakage replays), these modules start with Ray down, and the literal condition is asserted.
    The existing tests are not edited (Observations).
23. **`IMPLEMENTATION CHOICE`: pytest functions and classes**, with `tmp_path`, `request.addfinalizer`
    and `pytest.mark.parametrize`, in SI's style (as 02), where ChamPBH's are `unittest`.
24. **`IMPLEMENTATION CHOICE`: the helper runs by path**, `python -u tests/registered_run_helpers.py`,
    not `-m`, since `tests/` is not a package.
25. **`IMPLEMENTATION CHOICE`: `sys.argv = [str(program), *main_args]`** where the prompt writes
    `[str(MAIN_PY), …]`: the same in production, and the stand-in's own path in a test (ChamPBH's
    deviation 14).
26. **`IMPLEMENTATION CHOICE`: tests beyond the prompt's list**: an empty flag, an empty database, an
    unknown option, both `--help` tests, the two-thread test, the mid-line pair, the `ray.init`-wrapper
    and module-scope `ast` checks, `begin`'s two handlers by `ast`, and the third scope test.

No `UNINTENDED DRIFT`.

## Verification performed

**`runpy.run_path` and `main.py`** (§4's first stop condition, checked and not met). At this tree
`main.py` reads no `__file__`, installs no signal handler, and calls `ray.init(address=
args.ray_address)` as an attribute of `ray` (`:131`), so the wrapper's replacement is seen; its
`print_help`/`sys.exit()` is `:97-99`, the refusals `:114` and `:129` exit 2. Ray adds
`dirname(realpath(sys.argv[0]))` to the workers' path (`worker.py:2675`): the root, for `main.py`.

**Suites**, serially, in the foreground, `./venv/bin/python -m pytest … -q -p no:cacheprovider`
(output in the scratch directory, the verdict grepped; the load is `uptime`'s one-minute figure at
the start and the end):

| Suite | Before (at `622c66f`) | After |
|---|---|---|
| default `-m "not integration and not slow"` | 743 passed, 1 skipped (744), 139 deselected; 35.7 s; load 6.9 at the end | **847 passed, 1 skipped (848)**, 141 deselected; 47.0 s; load 6.4 → 21.4 |
| `RAY_ADDRESS=local -m integration` | 69 passed, 1 skipped (70); 57.1 s; load 25.8 at the end | **71 passed, 1 skipped (72)**; 99.8 s; load 20.4 → 55.1 |

The baselines equal the orchestrator's (744; 70). The default "after" count is the second run: the
first failed 104 teardowns (deviation 22) and nothing else.

```
$ PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --help ; echo "exit $?"   # (tail)
form: registered_run.py --campaign C --prompt N --register SLUG --purpose TEXT
-- <main.py's arguments>
** driver exit status 0
exit 0

$ ./venv/bin/python -m runregistrykit list          # after both suites
no runs under /Users/ds283/Documents/Code/StochasticInstantons/var/runs
$ ls -A var/runs var/datastores                     # both empty

$ git diff 1c223e8 --stat -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py utilities.py
(empty)
```

**One stubbed run, by hand**, on 04's arguments with the database in the scratch directory
(`python -u tests/registered_run_helpers.py <scratch>/runs <scratch>/standin_return.py --
--campaign rrk-adoption --prompt 03 --register probe --purpose … -- --config quadratic-minimal.yaml
--database <scratch>/store.sqlite --job-name rrk-adoption-04-reference --targets homogeneous
--n-collocation-points 5 --alpha-regularization 0.01 --ray-address 127.0.0.1:6390`): exit 0; stdout
began with the three `>> ` lines and ended `** driver exit status 0`; the manifest's `scope` was
04's literal; `packages` datastorekit 0.5.0 (`f47b9a25…`), raypoolkit 0.3.0 (`67a75b97…`),
runregistrykit 0.2.0 (`0bae3a3c…`); `status.json` `done`/0, stage `STAGE 2: FULL MSR INSTANTONS,
all work items complete`, and a `fingerprint_error` saying the primary does not exist.

**`begin`'s refusal**, as printed (the dead run made as the test makes it, in the scratch directory):

```
!! Cannot begin run rrk-adoption-03-resume-20261025T110753 with results "<scratch>/store.sqlite": run example-01-hard-killed-20261025T110752 is running (stale, pid 58175) and names this store by its results. A stale run is ended by a person, with `python -m runregistrykit end RUN_ID --reason TEXT`, before another run is begun on its store; the registry does not decide that a run is dead. No run directory was created
** driver exit status 2
```

**RunRegistryKit behaved as its README says** for `begin` (the refusal, nothing created), `finish`
(the state written whatever the fingerprint did; `written` / `not written: …`) and `end` (`lost`,
then `begin` accepted). No stop.

### §2.3 — the beat's timing, on paper

From `raypoolkit/RayWorkPool.py` at `v0.3.0` (`:30-32`, `:206`, `:356`, `:563-613`) and
`main.py`'s queues:
- **What prints, and when.** A titled queue prints its banner when it is built. Each pass of its
  loop submits up to `create_batch_size` items and blocks in `ray.wait(…, num_returns=
  min(process_batch_size, inflight))`, with no timeout. After the returned refs are processed (each
  one, a lookup, compute, store or validation, is one queue event), a progress notification, two
  lines (`:588`, `:592`), is printed only if more than 60 s have passed since the last one (or the
  queue's start) **and** either more than 300 s have passed or more than 500 events have been
  processed since it. The completion lines (`:606-613`) are printed when the queue ends.
- **`main.py`'s settings.** No `RayWorkPool(` call passes a `notify_` keyword (tested). Titled: `STAGE
  1: BACKGROUND INFLATIONARY TRAJECTORIES` (`:749`; `create_batch_size` and `process_batch_size` the
  number of models, so its one `ray.wait` waits for every trajectory), `STAGE 2: FULL MSR
  INSTANTONS`, `STAGE 3: SLOW-ROLL INSTANTONS` and `STAGE G: GRADIENT-COUPLED (ONION MODEL)
  INSTANTONS` (`_run_instanton_queue`'s work queue, `:525`: 5, 3, `max_task_queue` 50), `STAGE 4:
  COMPACTION FUNCTIONS AND MASSES` (`:1121`: 5, 3, 50) and, with `--no-store-values`, `STAGES 2+3+4:
  UNIFIED PIPELINE` (`:417`: 5, 3, 16). **Silent** (`title=None`): the other ten call sites, every
  lookup queue (`:255`, `:283`, `:350`, `:478`, `:621`, `:900`, `:929`, `:993`, `:1044`, `:1070`).
  `main.py` itself prints its `** ` banners, the `** … LOOKUP:` lines with their counts, and `>> `
  counts; DatastoreKit prints `>> Created/Opened sharded datastore …` at the open; Ray forwards the
  workers' lines.
- **So, per stage:** a titled stage shorter than 60 s prints its banner and its completion lines and
  nothing between them from RayWorkPool. A longer one prints a notification at the first `ray.wait`
  return after 300 s (or after 60 s, once more than 500 events, about 125 computed items, have
  completed), and then likewise. A stage whose items each take longer than 900 s returns from no
  `ray.wait` for that long, and is silent unless its workers print.
- **A healthy rehearsal build** (`quadratic-minimal.yaml`, `--targets homogeneous`: 1 model × 1 × 1 ×
  10 = 10 combinations). RH2's `11-reference` log (2026-10-22, read only) shows the stages complete
  in 6.04, 12.9, 9.59 and 2.27 s. Every titled queue is under 60 s, so **no progress line is printed
  at all**; each prints its banner and its completion lines, and between the stages the lookup
  banners and counts. **The longest silence a healthy rehearsal build can have is `STAGE 2: FULL
  MSR INSTANTONS`, banner to completion, about 13 s** at that load (the forwarded raylet line inside
  it in RH2's log is the raylet's stderr, which does not beat). The silence before `main.py`'s provenance line (its imports, after the three
  registration lines) and around `ray.init` and the pool's open is a few seconds. Since every banner
  and completion line changes the stage and beats at once, and a line 30 s or more after the last
  beat beats, the heartbeat's age in a healthy rehearsal stays under that silence plus 30 s, about
  45 s: far inside the 900 s window. A rehearsal that `list` shows stale is not healthy.
- **For longer builds** (not measured here): a homogeneous stage of many items notifies about every
  300 s plus one wait for 3 completions; the gradient branch's `STAGE G` returns from `ray.wait`
  only as solves finish, which has taken hours (`dk-and-rpk-migration` U11), so it shows stale
  while it works, as `heartbeat_means` says.

## The deliberate-breakage record

Each diff is replayable with `git apply` from a clean tree at `16e1cc1`. Before the commit each
was checked with `git apply --check`, applied, checked with `git apply -R --check`, its tests run,
and reversed, by `replay.sh` in `bash`, running the five default-selection modules of
`tests/test_registered_run*.py` (104 tests); the wrapper was then byte-identical to its committed
form (`cmp`). The checks after the commit are reported with the commit. None is committed. Every
test not named passed under each.

### B1 — the handler installed before the wrapped `ray.init` only, not after

```diff
--- a/RunDrivers/registered_run.py
+++ b/RunDrivers/registered_run.py
@@ -900,8 +900,8 @@
     latch = SignalLatch()
 
     def _registered_ray_init(*init_args, **init_kwargs):
-        context = _real_ray_init(*init_args, **init_kwargs)
         install_killed_handler(run, latch)
+        context = _real_ray_init(*init_args, **init_kwargs)
         return context
 
     ray.init = _registered_ray_init
```

3 failed: `test_registered_run.py::TestTheProgram::test_the_wrappers_handler_replaces_rays_after_ray_init`;
`test_registered_run_signals.py::TestARealSigterm::test_it_is_killed_143_and_exits_143_with_the_marker_last`
(the Ray-like handler's `SystemExit(15)` is recorded `killed`/15 and the process exits 15);
`test_registered_run_source.py::test_the_ray_init_wrapper_passes_the_arguments_unchanged_then_installs_the_handler`.

### B2 — `fingerprint=True` passed by the handler

```diff
--- a/RunDrivers/registered_run.py
+++ b/RunDrivers/registered_run.py
@@ -450,7 +450,7 @@
         code = 128 + signum
         if run is not None:
             try:
-                run.finish("killed", exit_code=code)
+                run.finish("killed", exit_code=code, fingerprint=True)
             except Exception as e:  # noqa: BLE001
                 _say(stream, f"** {name}: could not record killed at once: {e!r}")
         _say(
```

10 failed: `test_registered_run_signals.py::TestTheHandler::test_on_a_real_run_it_records_killed_143_at_once_without_a_fingerprint`,
`::TestTheHandler::test_a_second_signal_is_ignored_with_a_line`, `::TestTheHandler::test_sigint_gives_130`,
`::TestAfterASignal::test_it_is_killed_143_with_the_fingerprint_whatever_reaches_the_driver` (all six);
`test_registered_run_source.py::test_handlers_pass_no_fingerprint_and_every_later_finish_passes_it`.

### B3 — the wrapper exits 0 whatever `main.py` exited with

```diff
--- a/RunDrivers/registered_run.py
+++ b/RunDrivers/registered_run.py
@@ -962,8 +962,8 @@
         _say(sys.stderr, f"!! {text[3:] if text.startswith('!! ') else text}")
         raise SystemExit(2) from None
     except SystemExit as exc:
-        status = exit_status(exc.code)
-        raise
+        status = 0
+        raise SystemExit(0) from None
     except KeyboardInterrupt:
         status = 128 + int(signal.SIGINT)
         raise
```

3 failed: `test_registered_run_outcomes.py::TestTheOutcomes::test_each_outcome[exit-2-failed-2]`,
`[exit-1-failed-1]`; `test_registered_run_signals.py::TestARealSigterm::test_it_is_killed_143_and_exits_143_with_the_marker_last`.
(A `RuntimeError` reaches `run`'s last handler, which the diff leaves, so `[raise-failed-1]` passes.)

### B4 — the stdout proxy drops a line when the copy fails

```diff
--- a/RunDrivers/registered_run.py
+++ b/RunDrivers/registered_run.py
@@ -257,15 +257,16 @@
         return getattr(self._stream, name)
 
     def write(self, text):
-        written = self._stream.write(text)
+        written = 0
         if text:
             self._mid_line = not text.endswith("\n")
         # the output is the run's; the bookkeeping is ours, and never costs it an exception
         try:
             with self._lock:
                 self._observe(text)
+            written = self._stream.write(text)
         except Exception:  # noqa: BLE001
-            pass
+            self._copy = None
         return written
 
     def writelines(self, lines):
@@ -315,10 +316,7 @@
         if self._copy is not None:
             # a copy that has failed once is dropped rather than retried, and must not cost the
             # stage tracking or the heartbeat below
-            try:
-                self._copy.write(text)
-            except Exception:  # noqa: BLE001
-                self._copy = None
+            self._copy.write(text)
         if not self._beats:
             return
         self._pending += text
```

2 failed: `test_registered_run_streams.py::TestThePassThrough::test_a_copy_that_fails_costs_neither_the_line_nor_the_beat`,
`::TestThePassThrough::test_a_heartbeat_that_fails_costs_no_line`.

### B5 — `script` recorded as the wrapper instead of the program

```diff
--- a/RunDrivers/registered_run.py
+++ b/RunDrivers/registered_run.py
@@ -822,7 +822,7 @@
             slug=args.register,
             purpose=args.purpose,
             argv=[str(Path(__file__).resolve()), *argv],
-            script=str(program),
+            script=str(Path(__file__).resolve()),
             # the store the run's results live in, which the registry names and never writes; not
             # `checkpoint`, which is a unit ledger this run does not have
             results=os.path.abspath(parsed.database),
```

2 failed: `test_registered_run.py::TestRegistration::test_the_manifest_records_the_program_the_store_the_scope_and_the_packages`,
`::TestRegisterInProduction::test_the_script_is_main_py_with_its_hash_and_this_repositorys_head`.

### B6 — the `ConfigError` caught as a refusal

```diff
--- a/RunDrivers/registered_run.py
+++ b/RunDrivers/registered_run.py
@@ -837,8 +837,6 @@
             root=runs_root,
             client_root=str(REPO_ROOT),
         )
-    except runregistrykit.ConfigError:
-        raise
     except RuntimeError as e:
         raise Refusal(str(e)) from e
 
```

2 failed: `test_registered_run.py::TestBeginsErrors::test_a_config_error_is_not_a_refusal`;
`test_registered_run_source.py::test_the_one_begin_call_has_the_two_handlers_in_order`.

## Observations not acted on

1. **Two default-selection modules start Ray in the test process.** `test_plot_extraction_golden.py`
   (`:67-78`) and `test_plot_adapters_golden.py` (`:62-71`) call `ray.init(ignore_reinit_error=True)`
   from a module-scoped autouse fixture, with no address and no shutdown (their docstrings leave the
   shutdown to `conftest.py`'s `live_pool`, which the default selection never builds). So the default
   suite starts a local Ray, contrary to README §5's "no test needs Ray outside the `integration`
   marker", and leaves it up for every later module (deviation 22). Not this prompt's to change; no
   issue opened. The user or the orchestrator may want one.
2. **`build.sh` appends its own marker** (`:135`), so a wrapper launched by it would leave two
   (the orchestrator's note, "For 04"). 04's launcher is its own (P8).
3. **The last stage of a homogeneous run** is `Skipping gradient branch (--targets excludes
   'gradient')`, a `** ` banner `main.py` prints at the end (`:1155`). It is true, and it is what a
   `done` run's `stage` will read in 04.
4. **Ray's own driver messages go to stderr** (`ray/_private/log.py:32-35`, a handler that writes to
   whatever `sys.stderr` is; RH2's log merged both streams), so `Connecting to existing Ray cluster…`
   neither beats nor sets a stage. Of the workers' forwarded output, only their stdout lands on the
   driver's stdout and beats; their stderr, the raylet's warnings among it, goes to the driver's
   stderr (`worker.py:2197-2206`).

## State handed to the next prompt

- `RunDrivers/registered_run.py`, which 04 runs unchanged through its own launcher (P8). The scope
  of 04's reference is the literal above; its `heartbeat_means` is the formatted text above.
- What 04 should see in a healthy rehearsal (§2.3): no RayWorkPool progress line; a heartbeat age
  under about 45 s; the stage reading each banner in turn and ending `Skipping gradient branch …`;
  stdout and `stdout.log` beginning with the three `>> registered_run` lines and ending `** driver
  exit status N`; a `SIGTERM` after `ray.init` recorded `killed`/143 at once, the second record with
  the fingerprint, exit 143, and `** SIGTERM at …: recorded killed …` on stderr.
- What 04 measures: what Ray 2.55.1, attached to SI's external cluster, installs for `SIGTERM`, and
  whether `** cancelled an alarm` ever prints (P9).
- `var/runs/` and `var/datastores/` are empty; nothing was pushed.
