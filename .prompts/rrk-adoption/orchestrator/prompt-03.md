# Orchestrator — prompt 03, the wrapper

Read [`../README.md`](../README.md) first: §0.2 (what ChamPBH's wrapper does), §0.3 (`main.py`'s
shape; the queues' printing), §2.2 (03's charter), §5 and §6 (R2, R3, R5, P1–P4, P7, P9, P11). Then
the board's §5.4 (02's record and review). The conventions are note 02's
([`prompt-02.md`](prompt-02.md), which carries `dk-and-rpk-migration`'s
[`prompt-01.md`](../../dk-and-rpk-migration/orchestrator/prompt-01.md) §0 "Conventions"), restated
in §2 where 03 needs them.

**You do not write code.** You may:
- run the suites and the tests the results note names;
- replay the note's deliberate-breakage diffs with `git apply`, and revert them;
- run read-only probes from the session scratchpad (`orch03/`), never committing one;
- read RunRegistryKit, ChamPBH and SGK with `git show`, never changing them;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`03-the-wrapper.md`](../03-the-wrapper.md) · **Board items:** W1–W6 · **Gate:**
"Wrapper" · **Closes:** nothing · **Opens:** only what the work finds · **Model:** Opus, as the
prompt recommends. Nothing is pushed.

**Gate:**
- 01 landed (`60687f0`, `7071bb8`) and 02 landed (`0fcaf7c`, reviewed `ff3ddd6`); the gates **Pin**
  and **Fingerprint** hold (board §2). `HEAD` is the commit that adds this note, on top of
  `ff3ddd6`, on `rrk-adoption`; the tree is clean; `git worktree list` shows the main checkout
  alone.
- The venv holds `datastorekit` 0.5.0 at `f47b9a25…`, `raypoolkit` 0.3.0 at `67a75b97…`,
  `runregistrykit` 0.2.0 at `0bae3a3c…` (none editable), `ray` 2.55.1 and `ConfigArgParse` 1.7.5.
- `ray_cluster.sh status`: lock free, no SI process, the four ports free. `var/runs/` and
  `var/datastores/` exist and are empty; `runregistrykit list`: no runs.
- No other session runs a suite or a Ray job from this venv, or installs into it, while 03 runs.
  04 is not dispatched until 03 is reviewed.

## 0. What makes this prompt unusual

**It is the code every registered run will go through, and its tests must stand in for Ray.**
Nothing in it computes, but a mistake in it is recorded as a wrong history of a run: a `done` that
was a refusal, a `failed` that was a signal, a heartbeat that claims more than it knows. ChamPBH's
`RunDrivers/registered_run.py` at `807f175` is the model, and its own orchestrator note for 03
(`prompts/rrk-adoption/orchestrator/prompt-03.md` at `807f175`) ruled eleven points that its code
and tests now embody. SI's prompt 03 was written from ChamPBH's results and carries most of them.
What follows corrects the prompt where SI differs from ChamPBH or from what the prompt assumed, and
restates the ChamPBH rulings the prompt leaves out.

**Corrections to the prompt**, each recorded in the results note as a deviation of the class given.

1. **The board section is `### 5.5`, not `### 5.4`** (`STRUCTURALLY REQUIRED`). §5.3 records the
   merge of `main` and §5.4 is 02's. Acceptance 4's `### 5.4 After prompt 03` becomes
   `### 5.5 After prompt 03 (<date>)`.

2. **The progress line's cadence, and so `heartbeat_means`** (`STRUCTURALLY REQUIRED`). W3 says
   RayWorkPool prints a progress line "no more often than every 60 s", and README P7 that "a beat
   arrives about every minute while work completes". The floor is right; the cadence is not. At
   RayPoolKit `v0.3.0` (`RayWorkPool.py:563-600`) a progress line is printed only after `ray.wait`
   (`:356`, no timeout) has returned completed work, and only when **both** more than
   `notify_min_time_interval` (60 s) has passed since the last line **and** either
   `notify_time_interval` (300 s) has passed or more than `notify_batch_size` (500) queue events
   have been processed since it. An event is each `ray.wait` completion: an item's lookup, compute,
   store and validation each count (`self._batch += 1` per completed ref). The three defaults are
   `DEFAULT_NOTIFY_BATCH_SIZE`, `DEFAULT_NOTIFY_TIME_INTERVAL` and `DEFAULT_NOTIFY_MIN_INTERVAL`
   (`:30-32`); no `RayWorkPool(` call in `main.py` passes a `notify_` keyword. So in a queue that
   processes fewer than 500 events in five minutes, a progress line comes about every 300 s; only a
   fast queue prints as often as every 60 s. **Ruled:**
   - `HEARTBEAT_MEANS` says, in ChamPBH's words where they fit: a beat is taken from a stdout line,
     at most once every 30 s or at once when the line changes the stage, and the line is the stage;
     RayWorkPool prints a progress line only after `ray.wait` has returned completed work, never
     sooner than 60 s after the last, and otherwise only once 300 s have passed or 500 queue events
     have completed, so a fresh beat from it means work completed within about five minutes; Ray
     forwards the workers' own output to the driver's stdout, so a worker's line beats too, without
     moving the stage; several queues are silent (`title=None`); a stage that prints nothing for
     longer than the staleness window (900 s, `list --stale-after`), such as a queue whose items
     each take longer than that, shows stale while it works, **and the gradient branch's solves
     have run for hours**; stale means go and look;
   - the three numbers are module constants of the wrapper (beside `BEAT_MIN_INTERVAL`), formatted
     into the sentence. `main.py` is never imported. A test asserts that they equal RayPoolKit's
     three defaults (importing `raypoolkit`'s module imports `ray` but initialises nothing), and,
     by `ast`, that no `RayWorkPool(` call in `main.py` passes a keyword beginning `notify_`;
   - W6 test 1 asserts `heartbeat_means` states the 60 s floor, the 300 s interval and the gradient
     branch.

   The formatting and the two tests are `IMPLEMENTATION CHOICE`. The prompt's §2.3 timing on paper
   uses this rule, not "every 60 s".

3. **SI's `>>` lines are not banners** (`IMPLEMENTATION CHOICE`, ruled here). ChamPBH's
   `_STAGE_BANNER` matches `** ` or `>> `, because ChamPBH's `main.py` has `>>` banners. SI's do
   not. Every `>> ` line a build prints to stdout is information inside a stage:
   - `main.py:101`'s provenance line, `>> packages: …` (`utilities.format_package_provenance`);
   - DatastoreKit's `>> Created sharded datastore "…"` and `>> Opened existing sharded datastore
     "…"` (`datastorekit/SQL/ShardedPool.py:271`, `:308`), and its prune and replication lines
     (`:2156`, `:2177`, `:2553-2554`);
   - `main.py`'s counts, `   >> gradient branch: …` (`:654`) and `   >> N models … = … instanton
     combinations` (`:1198`, `:1206`).

   With `>>` matched, each becomes the stage. ChamPBH's own verification (§1.5, `resumed-b`'s check)
   shows a `status.json` stage `Opened existing sharded datastore "…" with 16 shards` for that
   reason. SI's banners all begin `** `: RayWorkPool's `\n** {title}` (`:206`), and `main.py`'s
   `** BUILDING PARAMETER SAMPLING GRIDS`, `** COSMOLOGICAL PARAMETERS: …`, `** DIFFUSION MODEL: …`,
   `** … LOOKUP:`, `** STAGE 4: COMPACTION FUNCTIONS`, `** Stopping after …` and `** Skipping …`.
   **Ruled:** `_STAGE_BANNER` matches `** ` only. A test feeds `StageTracker` each of the `>>` lines
   above, as printed, and asserts the stage does not move; another feeds the `** ` banners and asserts
   it does. `_QUEUE_PROGRESS` and `_QUEUE_COMPLETE` match SI's lines (`:588`, `:606`) and are carried
   unchanged. The results note lists every pattern with "carried" or "adapted".

4. **The wrapper's own registration lines are not a stage** (`IMPLEMENTATION CHOICE`). ChamPBH's
   `register` prints `** registered_run: registered as …`, `**   manifest …` and `**   list it
   with: …` through the beating proxy, so its stage reads `list it with: ./venv/bin/python -m
   runregistrykit list` until `main.py`'s first banner, which in SI comes after `ray.init` and the
   pool's open. Carry the lesson, not the bug: the three lines reach stdout and `stdout.log`
   unaltered and do not set the stage. How (a `>> ` prefix, which correction 3 makes inert and which
   is SI's own form for information; or a tracker that skips them) is the agent's choice, said in the
   note. A test asserts that after `register` the stage is still `None`.

5. **No database: the prompt's reason holds in SI** (`NOTED`). ChamPBH's ruling 1 found its
   `--database` `required=True`, so `main.py`'s help-and-`sys.exit()` was unreachable. SI's is
   `default=None` (`config/argument_parser.py:18-23`), and `main.py:97-99` does print the help and
   `sys.exit()` with no code. So W2's refusal is needed for the reason it gives: `parsed.database`
   `None` or empty after `strip()` is refused before `begin`. The parser's `error` is replaced **on
   that instance** (ChamPBH's ruling 1, its `_refusing`), so a parse failure is one `!! ` line.

6. **No address check to carry** (`STRUCTURALLY REQUIRED`). ChamPBH's `parse_arguments` refuses
   through `config.argument_parser.ray_address_problem` and strips a leading `!! ` from its text
   (ChamPBH's ruling 3). SI has no such function: `--ray-address` is `required=True`
   (`config/argument_parser.py:79-88`) and nothing in SI's code refuses a value. A missing address
   is the parser's refusal (W6 test 6); a bad one is `main.py`'s or Ray's, recorded `failed`, as W2
   says. Carry neither the call nor the strip. If the agent prints any text that already begins
   `!! `, it must not print `!! !! `.

7. **The licence header is `config/fingerprint.py`'s** (`STRUCTURALLY REQUIRED`). W1 says "as
   `main.py`'s"; `main.py` has none (it begins `import math`). 143 of SI's 207 tracked `.py` files
   carry the header `config/fingerprint.py` carries, `# (c) University of Sussex 2026` through
   `# limitations under the License.`. Every new `.py` file carries it whole.

8. **`.claude/rules/run-registry.md` has no sentence to make definite** (`STRUCTURALLY REQUIRED`).
   The prose item names both files. Only `CLAUDE.md:55-56` says the wrapper is a thing "prompt 03 of
   `rrk-adoption` adds"; the rules file never names the wrapper as future (its `:43` is already
   present tense). So `CLAUDE.md`'s sentence becomes definite, with the usage line, and the rules
   file is not changed. Nothing else in `CLAUDE.md` moves: not its suite counts (05's).

9. **W6 test 5's store: one build, two copies** (`IMPLEMENTATION CHOICE`). The prompt says "build
   the store once per module". 02's golden test imports `_STORE_SCRIPT` and the module-scoped
   `store` fixture from `test_inventory_store` unmodified, and so should this module. But one store
   cannot serve both tests: the "with a sidecar" test leaves a sidecar beside the primary, holding
   the fingerprint, which the "without" test would then see. **Measured here** (`orch03/
   copy_probe.txt`): a `shutil.copytree` of the store's directory fingerprints to the golden digest
   `e3437a9b…7c78`, equal to the original with `taken` removed. On copies, `begin(…, script=main.py,
   results=<copy>, root=<temporary>, client_root=REPO_ROOT)` then `finish("done", exit_code=0,
   fingerprint=True)` gave `fingerprint_sidecar` `written` (after `create_sidecar(<copy>, purpose=…,
   client_root=REPO_ROOT)`; the sidecar's digest the golden's) and `not written: … (there is none)`
   without one, each `done`/0 with no `fingerprint_error`, in 0.1 s; the copy without a sidecar
   gained no file. **Ruled:** the module imports `store`; each test copies the store's directory
   into its own `tmp_path` and runs there. Imported into a third module, the fixture builds once more
   (11 s here at load 8, about 30 s under heavy load).

10. **What `begin` records, measured** (`NOTED`). The manifest's `packages` has `datastorekit`,
    `raypoolkit` and `runregistrykit`: the config's two distributions plus the package itself
    (`runregistrykit/__init__.py:217-221`). W6 test 1 holds as written.

11. **Ray 2.55.1's line numbers** (`NOTED`), for the docstring and comments: `ray.init` installs
    `sys.exit(signum)` as the Python `SIGTERM` handler at its start, before the address is resolved
    (`ray/_private/worker.py:1656-1661`); `log_to_driver` defaults to `RAY_LOG_TO_DRIVER`
    (`:1610-1611`), and `print_to_stdstream` (`:2192`) writes the workers' lines into the driver's
    `sys.stdout`/`sys.stderr` from a thread; Ray's `sys.excepthook` is `:2170-2189`; the script
    directory added to the workers' path is `os.path.realpath(sys.argv[0])`'s (`:2675`). Ray 2.53's
    numbers in ChamPBH's comments do not carry over.

12. **The tests' import path** (`NOTED`). `tests/` has no `__init__.py`; `conftest.py` imports
    `config` at module scope, which works under `./venv/bin/python -m pytest` from the root (the
    bare `./venv/bin/pytest` fails at `conftest.py:28`). A helper module beside the tests, say
    `tests/registered_run_helpers.py`, imports as `registered_run_helpers` inside pytest; a
    subprocess runs it by path with `cwd` the root and the root on `sys.path` (it inserts it, as the
    wrapper does). There is no formatter in the venv (`black` is absent); match the surrounding
    style by eye.

**ChamPBH's rulings for 03 that bind here too**, which SI's prompt does not state (cite "ChamPBH's
note 03, ruling N" in the deviation):
- **(2)** `argv` split by hand at its first bare `--`; the wrapper's own parser's `error` replaced,
  so a missing or unknown flag is one `!! ` line; each flag non-empty after `strip()`.
- **(4)** `register` passes `argv=[str(Path(__file__).resolve()), *argv]`. In a test the stand-in
  lies in a temporary directory, so `begin` records `script` and `results` absolute and `git_head`
  `"unknown"` (it reads git from the script's directory); test 1 asserts that, with a comment.
  **One more test** calls `register` alone with `program=MAIN_PY` and a temporary runs root, runs
  nothing, and asserts `script == "main.py"`, `script_sha256` equal to `main.py`'s own, and
  `git_head` equal to `git rev-parse HEAD`: P4 in its production form. It restores the streams and
  both handlers it took over.
- **(5)** The stand-in records `sys.argv`, `__name__` and `__file__`; a test asserts `argv[0]` is the
  program's path, `argv[1:]` `main.py`'s arguments, `__name__` `"__main__"`.
- **(6)** Each proxy holds a `threading.RLock` around its bookkeeping only; the real write is first,
  outside the lock, unconditional. A test writes a line from a second `threading.Thread`: it reaches
  the real stream and `stdout.log`, and beats.
- **(7)** `main()` is the work; `run()` is the entry and the `__main__` block. `run`'s `finally`
  stops every proxy beating, **then** prints the marker (on a line of its own after an unfinished
  line), then closes the copies on the clean path only. The marker is never `status.json`'s stage.
- **(8)** Test 3's four outcomes, test 4's real `SIGTERM` and test 6's `begin` refusal run through
  the helper as a subprocess, `python -u` (through a pipe the banner is otherwise block-buffered and
  the signal test waits for ever). Its `ray.init` stand-in installs `sys.exit(signum)` for `SIGTERM`,
  as Ray 2.55.1 does. Test 6's refusals before `begin` run the real script, no stub, `cwd` the root:
  exit 2, stderr exactly one line beginning `!! `, no `Traceback`, stdout's last line `** driver exit
  status 2`, and `var/runs/`' listing unchanged (it exists and is empty). Every subprocess is reaped
  by a cleanup registered before its first read. In-process tests patch `ray.init` and
  `ray.shutdown` and register, before the call, a cleanup restoring `sys.stdout`, `sys.stderr`, the
  `SIGTERM` and `SIGINT` handlers, and closing the proxies' copies.
- **Two tests the breakages need**, which the prompt's W6 does not name: a copy whose `write` raises
  (the line still reaches the real stream, and later lines still beat); and `runregistrykit.begin`
  patched to raise `ConfigError`, after which `main` raises `ConfigError`, not `Refusal`, and the runs
  root is empty.
- **(test 8)** SGK's `_finish_calls` form, with handlers `terminal` and `killed_handler`: expect **4**
  `.finish(` calls outside a handler, each passing `fingerprint=True` (in `finish_after_exec`: done,
  `terminal_state`, failed, killed) and **2** inside, neither passing it. Another count is a design
  change, said in the note.
- **Scope** is the arguments as given, never the grid `main.py` builds (ChamPBH's ruling 11). For SI:
  the config file or "no config file"; `--targets`; the potential type; the `m` and `λ` choices
  (values, up to six, else a count and range; a range as its arguments); the `N_init`, `N_final` and
  `δN*` choices likewise, or `--sample-grid-csv` when given; `--n-collocation-points` and
  `--alpha-regularization` where given; `--no-store-values` and `--stop-after` where given; the
  shards; the job name. The agent may choose otherwise and says which fields and why. A test asserts,
  as a literal, the scope of 04's reference arguments: `--config quadratic-minimal.yaml --database
  var/datastores/rrk-adoption-04-reference.sqlite --job-name rrk-adoption-04-reference --targets
  homogeneous --n-collocation-points 5 --alpha-regularization 0.01 --ray-address 127.0.0.1:6390`
  (the config gives `Quadratic`, `m` `1e-05` Mp and 10 shards). The parse only reads; it starts
  nothing.

**For 04, not acted on in 03.** `dk-and-rpk-migration`'s `build.sh` appends its own `** driver exit
status N` to the log (`:135`), so a wrapper launched by it would leave two markers. 04's launcher is
its own (P8); its note says so.

**What the orchestrator measured at `ff3ddd6`** (2026-10-25, 10:40–11:00 GMT). Pass them on.
- Gate as above. `git status` clean, no worktree but the main checkout.
- **`main.py`** is unchanged since `1c223e8`. The prompt's line references hold: the parse at `:94-95`,
  `print_help`/`sys.exit()` at `:97-99`, provenance `:101`, `--inventory` `:107`, refusals `:114`
  and `:129` (both `sys.exit(2)`), `ray.init(address=args.ray_address)` at `:131` as an attribute of
  `ray`, `with ShardedPool(…)` at `:1273`. It reads no `__file__` and installs no signal handler.
- **RayWorkPool** at `v0.3.0`: the banner `\n** {title}` at `:206`, `!! WARNING` at `:541`, progress
  at `:588` and `:592`, completion at `:606-613`, as the prompt says (the line numbers did not move
  from `v0.2.0`). The cadence is correction 2's.
- **`config/argument_parser.py`**: `configargparse`, `default_config_files=["stochastic_instanton.yaml"]`
  (absent at the root), `--config` `is_config_file`, `--database` `default=None`, `--ray-address`
  `required=True`, `--inventory` `store_true`.
- **RunRegistryKit `v0.2.0`**: `begin` at `__init__.py:987` (keyword-only `client_root`, `argv`,
  `pid`); `finish` at `:805`; `DEFAULT_STALE_AFTER = 900.0` at `:114`; `ConfigError(RuntimeError)` at
  `client.py:84`; `create_sidecar(primary, purpose, *, client_root=None)` at `stores.py:846`; `end
  RUN --reason TEXT --root DIR` in `__main__.py:499-518`.
- **Correction 9's probe** (`orch03/copy_probe.py`, output `copy_probe.txt`).
- **Baselines**, serially, at `ff3ddd6`: see §1.

**What moves on purpose:** the prompt's §5 list, read through correction 8:
`RunDrivers/__init__.py` and `RunDrivers/registered_run.py`; `tests/test_registered_run*.py` and at
most one non-test helper beside them; `CLAUDE.md`'s sentence at `:55-56`; the board; the results
note `.documents/rrk-adoption/03-the-wrapper.md`; `.prompts/INDEX.md`'s campaign line (its status
3 / 5). **What must not move:** every other `.py` file; `main.py`, the plot scripts and
`utilities.py` (`git diff 1c223e8 -- main.py plot_*.py utilities.py` empty); every existing test,
`tests/test_inventory_store.py` and `tests/test_store_fingerprint_golden.py` among them; the venv;
`.claude/rules/`; anything under `var/`; RunRegistryKit, ChamPBH and SGK.

## 1. Before you dispatch

1. The Gate, as §0's facts.
2. **Baselines**, both suites serially at `ff3ddd6` (`orch03/baseline-suites.txt`), with the load.
3. **The commit of this note**, alone, staged by path.

**Done at dispatch (2026-10-25):** the Gate as §0; the baselines at `ff3ddd6`, serially
(`orch03/baseline-suites.txt`): default **744** (743 passed, 1 skipped, 139 deselected), 36 s;
`RAY_ADDRESS=local … -m integration` **70** (69 passed, 1 skipped), 61 s; the load 5.8–11.1;
`runregistrykit list`: no runs. 02's counts. Correction 9's probe in `orch03/copy_probe.txt`.

## 2. Dispatch

One fresh-context subagent, on **Opus**, in the main checkout. Give it the prompt, the README, the
board, `HEAD`, the baselines, and §0 of this note up to "## 1. Before you dispatch", as a copy in
the session scratchpad. The agent does not read `orchestrator/`, nor prompts 04–05.

Tell it plainly:
- **One commit, at the end**, staged by explicit path after showing `git diff --cached
  --name-only`; the results note `.documents/rrk-adoption/03-the-wrapper.md` in `dk-and-rpk-migration`
  README §5.1's form; the board's `### 5.5`; "this commit" where the SHA goes.
- **The files it may add or change are §0's list, and nothing else.**
- **§0's corrections and the ChamPBH rulings** bind it, each recorded with its class.
- **Per function**, the note says carried unchanged, adapted (how), or new (the prompt's §1).
- **It starts no Ray, runs no `main.py` (directly or through the wrapper), opens no store but its
  tests' temporary ones, and creates nothing under `var/`.** The integration suite's private Ray
  under `RAY_ADDRESS=local`, and `_STORE_SCRIPT`'s, are the only Ray it causes. No `ray stop`.
- **Suites** as the conventions: `./venv/bin/python -m pytest … -q -p no:cacheprovider`, serially,
  in the foreground, output to its scratch directory, the verdict grepped, `uptime` beside each; a
  failure re-run alone before it is called real. **The new test files run three times in a row** at
  the end (subprocesses, signals, threads): a flaky test is a stop. Time each new test; none may be
  `slow` without saying so.
- **Breakages** recorded as diffs `git apply` replays from a clean tree at its commit, checked with
  `--check` and `-R --check`, replayed in `bash`; never committed. Each names the tests it failed.
- **Scratch** is its own subdirectory of the session scratchpad, never `/tmp`. No probe `.py` goes
  under `RunDrivers/`, `tests/`, `config/` or `.documents/`.
- **Stop and ask** on any of the prompt's §4 conditions. An existing test that fails is a stop, never
  a reason to edit it.
- **It replies with:** the commit's SHA, message and `--stat`; the module's public names, one line
  each; `HEARTBEAT_MEANS` as committed and 04's `scope` literal; the patterns, carried or adapted; the
  new tests by name, with counts and times, and the three runs; each breakage with what failed; §2.3's
  timing on paper, with the longest silence of a healthy rehearsal build; both suites before and
  after, with the load; every deviation with its class.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <agent>` is §0's list. `git status --short` clean.
   `git diff --name-only ff3ddd6 <agent> -- '*.py'` is the new files only; `git diff 1c223e8 <agent>
   -- main.py plot_*.py utilities.py` empty; `.claude/rules/` and every existing test unchanged;
   `var/` still empty. Nothing pushed.
2. **`CLAUDE.md`.** The diff is the one sentence of correction 8, with the usage line, and nothing
   else.
3. **The module, by reading against ChamPBH's.** Diff `StageTracker`, `RegisteredStream`,
   `terminal_state`, `SignalLatch`, `make_killed_handler`, `install_killed_handler`,
   `finish_after_exec`, `register`, `main` and `run` against `807f175`'s, function by function.
   Every difference is a correction of §0, an SI adaptation the note names, or a defect. Nothing of
   ChamPBH's `ray_address_problem`, β/M/Λ scope or `NOTIFY_FLOOR = 300` came across. The header is
   whole.
4. **The refusals and the seam.** The split at `--`; both parsers' `error` replaced; the empty-flag
   and database checks; `--inventory` refused before `begin`; `begin`'s `try` with `ConfigError`
   re-raised first; nothing taken over before `begin` returns.
5. **Registration.** `begin`'s arguments: `script=program`, `results` absolute,
   `client_root=REPO_ROOT`, `root=runs_root`, the `argv` of ChamPBH's ruling 4, `scope`,
   `heartbeat_means`. `HEARTBEAT_MEANS` says correction 2's things and no "every minute". The
   registration lines set no stage.
6. **The run and the finish.** `sys.argv` set, `runpy.run_path(str(program), run_name="__main__")`,
   the `try`, `finish_after_exec(…, ray.shutdown)`, the bare re-raise; `run`'s `finally` in the order
   of ruling 7. No code reads `main.py`'s text.
7. **By probe**, from `orch03/`, with no Ray: the helper subprocess on a stand-in of the
   orchestrator's own, which prints `>> packages: x`, a `** STAGE 1: …` banner, a `>> Opened existing
   sharded datastore …` line and 50 progress lines, then `sys.exit(3)`. Exit 3 and `failed`/3; the
   marker last in stdout and `stdout.log`; `status.json`'s stage the last progress line's sentence
   under `STAGE 1`, never a `>>` line, never the marker; the beats one for each stage change, else at
   most one per 30 s. Then `registered_run.py … -- --database x --inventory --ray-address
   127.0.0.1:6390`: exit 2, one line, `var/runs/` unchanged.
8. **The tests, by reading.** Every in-process test restores streams and handlers; every subprocess
   is reaped by a cleanup registered before its first read; `ray.is_initialized()` asserted false;
   nothing written outside a `tempfile` directory or `tmp_path`. Test 7 is by `ast`, over the four
   files. Test 8 expects (4, 2). Test 5 copies the store per test and is `integration`; nothing else
   is.
9. **The breakages.** In `bash`, replay each diff with `git apply`, run the named tests, see each fail
   as the note says, revert, `git status` clean.
10. **The records.** The board: header (3 of 5), row 03 landed with "this commit", W1–W6, the gate
    **Wrapper**, `### 5.5`. The note in §5.1's form, every deviation classed, the diffs, §2.3 on
    paper. `INDEX.md`'s line. `OPEN-ISSUES.md` untouched unless an issue opened, and then in the same
    commit. The message ends with the `Co-Authored-By` line.
11. **The suites** at the agent's commit, serially: default (744 plus the new non-`integration`
    tests), `integration` (70 plus test 5's); the new files twice more. `registered_run.py --help`
    exits 0. `runregistrykit list`: no runs. `var/` empty.
12. **Ray.** After the suites, `ray_cluster.sh status` shows no SI process and the lock free; no
    process of this venv's Ray remains.

## 4. After the review

If it passes, residue in a follow-up commit of its own:
- "this commit" → the SHA, on the board, in the note and in `INDEX.md`;
- the board's list of orchestrator notes gains this one, "used for 03";
- `### 5.5` gains an *Orchestrator review of prompt 03* paragraph: what each check found.
- Prompt 03 is left as it ran; the board's paragraph names corrections 1, 2 and 8.

Anything that is not residue is opened on the board's §3 and in `OPEN-ISSUES.md` in the same commit.

**Report to the user:** the message as committed; the corrections that read the prompt otherwise than
it was written (the cadence, 2; `>>` not a banner, 3; the registration lines, 4; the store copies,
9); the new tests' count and the suites; the longest silence a healthy rehearsal build can have; and
that 04, which needs 02 and 03, is next, its note to point at `build.sh`'s second marker and the
rehearsal lock's contract (board §5.3).
