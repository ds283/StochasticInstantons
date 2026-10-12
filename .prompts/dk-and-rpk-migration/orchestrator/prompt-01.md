# Orchestrator — prompt 01, rehearsal tooling and run provenance

Read [`../README.md`](../README.md) first: §0.1 (items 8, 11, 13), §0.2, §2.2 (01's charter), §3,
§4, §4.1, §4.2, §4.3, §5 and §6.2 (P1–P3, P5, P19). This is the campaign's first note, so it
states the conventions in full. They are ChamPBH's `dk-and-rpk-migration` orchestrator conventions
(`ChamPBH/prompts/dk-and-rpk-migration/orchestrator/prompt-01.md`), adjusted for SI: pytest with
an `integration` marker that starts its own Ray, results notes in `.documents/` rather than
`logs/` (P19), JSON columns, and four polymorphic references rather than three.

**You do not write code.** You may:
- run the suites and the tests the results note names;
- replay the results note's deliberate-breakage diffs with `git apply`, and revert them;
- run an in-process check or a probe from the session scratchpad, never committing one;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`01-rehearsal-tooling-and-run-provenance.md`](../01-rehearsal-tooling-and-run-provenance.md)
**Board items:** T1–T3 · **Closes:** nothing · **Narrows:** nothing · **Opens:** only what the work
finds · **Model:** Opus, as the prompt recommends.

**Gate:**
- The prompts are written (`0209137`). The tree is clean but for ignored files.
- `HEAD` is the commit that adds this note, or a later one that touches no code.
  - "Code" here means anything outside `.prompts/` and `.documents/`, and in particular
    `utilities.py`, `main.py`, the two plot drivers, `tools/`, `tests/`, `Datastore/`,
    `RayTools/`, `config/` and `requirements.txt`.
  - If a later commit touches code, re-check every fact below that it could move, and hand the
    agent the corrections as an addendum.
- One prompt at a time in this checkout. The campaign runs in the main checkout (README §4.4,
  P15), and 02 runs 01's scripts.

## 0. What makes this prompt unusual

**It ships the acceptance instrument of the whole campaign.** `tools/compare_stores.py` decides
RH0, RH1 and RH2, and later P2's comparison of its rebuilt grids with the June ones. A comparison
that passes vacuously (two stores "equal" because a table was skipped, a column dropped, a JSON
column compared as an opaque string or a float rounded) would let every later rehearsal pass
whatever the layer did. So the review spends most of its effort on T2, and asks two questions of
it:
- **does it see a difference that is there?** One ulp in one column, one ulp inside a
  `fields_json` list, one row missing, one type value it cannot map: each must be named, with
  exit 1 or a named problem;
- **does it ignore a difference that is not physics?** Serials, shard assignment, insertion
  order, `timestamp`, the timing keys inside `diagnostics_json` and `metadata`, and whatever the
  agent classes as bookkeeping: each must be reported apart, exit 0.

**The tests build imitation stores with `sqlite3`, so a tool can pass them and miss a real one.**
SI has no pilot store of the campaign's grid, but it has real stores of the same layer. The
review's probe (§3 check 6) runs the tool on a *copy* of `test-gradient.sqlite` and its ten shards,
in the scratchpad, and perturbs the copy. Read by the orchestrator (summed over shards): 10
trajectories' worth of replicated rows with 57,130 `InflatonTrajectoryValue` rows, 125 each of
`FullInstanton`, `SlowRollInstanton` and `CompactionFunction` with 60,150 / 60,150 / 120,300 child
rows, and 56 `GradientCoupledInstanton` rows **with no `GradientCoupledInstantonValue` or
`…Profile` row**; `QuarticPotential`, `quartic_coupling`, `redshift`, `store_tag` and
`IntegrationSolver` are empty. No store in the tree holds a gradient child row, so those two tables
are covered by the imitation tests here and first met for real by RH0 (02). The agent never opens it; the orchestrator opens only its
copy, through the tool, and the originals only to copy them.

**T1 stands in `importlib.metadata`, so a mock aimed at the wrong name passes vacuously.** If
`utilities.py` does `from importlib.metadata import distribution`, a patch of
`importlib.metadata.distribution` replaces nothing the function calls, and the "not installed"
test passes only because nothing is installed. The breakages catch part of this; the probe without
a mock (§3 check 3) catches the rest.

**A registry test can pass against an empty registry.** `DIFFUSION_MODEL_REGISTRY` is `{}` until
`Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py` is imported (it fills the entry at
`:69`). A test 12 that imports only `InflationConcepts.DiffusionModel.registry` and checks "every
registry entry is in the tool's map" passes with nothing checked. The test must import the factory
module and assert the registry is non-empty, and check both directions.

**What moves on purpose:**
- `utilities.py` gains `RECORDED_DISTRIBUTIONS`, `installed_package_provenance()`,
  `format_package_provenance()` and the standard-library imports they need.
- `main.py`, `plot_InstantonSolutions.py` and `plot_GradientCoupledSolutions.py` each gain one
  import and one print. No other statement in them changes, and none is reformatted.
- New: `tools/compare_stores.py`; `tests/test_package_provenance.py`,
  `tests/test_compare_stores.py`, `tests/test_rehearsal_stage_counts.py`;
  `.documents/dk-and-rpk-migration/rehearsal/` (`build.sh`, `interrupt_when.py`,
  `stage_counts.py`, `run_readers.sh`, and any fixture);
  `.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md`.
- The board.
- No issue is expected. If one opens, the board's §3 gains it and `.documents/OPEN-ISSUES.md`
  (58 open, last updated 2026-10-11) gains the row in §6a, with its count and date, in the same
  commit.

**The facts, checked by the orchestrator on 2026-10-12 at `0209137`** (the code is `7bb3efd`'s:
`git diff --stat 7bb3efd 0209137 -- . ':!.prompts' ':!.documents'` is empty). Pass them on.

- **The venv.** Python 3.13.16; `pip freeze` is byte-identical to
  `measure/out/7bb3efd-pip-freeze.txt`. `pip show datastorekit raypoolkit` finds neither. As in
  ChamPBH, no real VCS or editable install of either package exists to test against: the tests'
  stand-ins and the review's `sys.path` probe are the only evidence.
- **ChamPBH's 01** is `d7791c5` (2026-10-12). No later ChamPBH commit touches
  `utilities.py`, `tools/compare_stores.py` or its `rehearsal/` scripts. Its review (ChamPBH board
  §5.2) found:
  - its prompt's timing list **missed `compute_time`**; the agent found it by reading the code;
  - one breakage diff in the log **had lost its trailing blank context line**, so it did not
    `git apply` as recorded. Every diff must pass `git apply --check` from a clean tree at the
    agent's commit before it is pasted;
  - a parent that cannot pair (an unmapped type value, a deleted row) lists its children
    unpaired as well as the named problem.

  And its later prompts (ChamPBH board §5.3–§5.4): a `SIGTERM`ed driver exits **134**; pip records
  a VCS URL **without** `git+`; `ray stop` kills any shell whose command line names Ray.
- **The drivers.** None imports from `utilities` today.

  | Driver | `parse_args()` | database check | `ray.init(` | `ShardedPool(` |
  |---|---|---|---|---|
  | `main.py` | `:91`, module level | `:93-95` | `:97`, module level | `:1345` (`with`, module level) |
  | `plot_InstantonSolutions.py` | `:1198` | `:1200-1202` | `:1204` | `:1207` |
  | `plot_GradientCoupledSolutions.py` | `:965` | `:967-969` | `:971` | `:974` |

  **Correction to the prompt (§2.1):** each plot script calls `ray.init` and opens its pool inside
  its module-level `if __name__ == "__main__":` block (`plot_InstantonSolutions.py:1196`,
  `plot_GradientCoupledSolutions.py:963`), **not inside `run_plots`**. The print goes in that
  block, after the database check and before `ray.init(`. §3.1's `ast` test must descend into the
  `If` node and not only a `FunctionDef`. `main.py` also constructs a `ProfileAgent` at
  `:1331-1342`, after `ray.init` and before the pool.
- **Pre-images**, for the `ast` comparison (§3 check 4): `git rev-parse 0209137:<path>` gives
  `utilities.py` `bb9b4a141360…` (166 lines), `main.py` `573fcf402e0f…` (1365),
  `plot_InstantonSolutions.py` `434649c48cde…` (1225), `plot_GradientCoupledSolutions.py`
  `2169f059182b…` (990).
- **Formatting.** `ruff` 0.15.17 is in the venv. `ruff format --check` would reformat
  `utilities.py`, `main.py` and `plot_GradientCoupledSolutions.py` today. **Do not run
  `ruff format` on any of the four** (prompt §3.5); a new file may be formatted.
- **The licence header.** SI's Python files start with the 15-line "(c) University of Sussex
  2026 / Created by David Seery / Apache License 2.0" header (`utilities.py:1-15`). Every new
  Python file carries it. (ChamPBH needed a follow-up commit, `e513e8c`, for two files without it.)
- **Polymorphic references: four, not two.** Read from every factory's `register()` (no `ray`
  cluster needed): a `*_serial` column with no `ForeignKey` beside a `*_type` column.

  | Table | Pair | `path:line` |
  |---|---|---|
  | `InflatonTrajectory` | `potential_serial` / `potential_type` | `Datastore/SQL/ObjectFactories/InflatonTrajectory.py:53-63` |
  | `FullInstanton` | `diffusion_serial` / `diffusion_type` | `FullInstanton.py:78-79` |
  | `SlowRollInstanton` | `diffusion_serial` / `diffusion_type` | `SlowRollInstanton.py:77-78` |
  | `GradientCoupledInstanton` | `diffusion_serial` / `diffusion_type` | `GradientCoupledInstanton.py:91-92` |

  The prompt (§2.2) and README §0.1 item 11 and §4.2 name only the first and last. The prompt
  already asks the agent to find any other pair; the agent declares all four, and the results note
  says the README undercounted. The type values: `QUADRATIC_POTENTIAL = 1`, `QUARTIC_POTENTIAL = 2`
  (`CosmologyConcepts/Potentials/model_ids.py`; `POTENTIAL_REGISTRY` at `registry.py:27-42`);
  `MASSLESS_DECOUPLED_DIFFUSION = 1` (`InflationConcepts/DiffusionModel/model_ids.py`; registry
  filled at `MasslessDecoupledDiffusion.py:69`). An existing store's `FullInstanton` rows carry
  `diffusion_type = 1`.
- **Text columns**, every one in `register()`: `version.label`, `store_tag.label`,
  `IntegrationSolver.label`, `CosmologicalParams.name`; `label` and `diagnostics_json` on
  `FullInstanton`, `SlowRollInstanton` and `GradientCoupledInstanton`; `diagnostics_json` on
  `InflatonTrajectory`; `fields_json` on the four value tables; `metadata` on
  `CompactionFunction` (`CompactionFunction.py:111`, written at `:362-364`); `source` on
  `CompactionFunctionSamples` (`'full'` and `'slow_roll'` in an existing store). No other column is
  text.
- **The `label` columns are the open question.** `RayWorkPool` passes its `label_builder`'s value
  to `compute(label=…)` (`RayTools/RayWorkPool.py:385-391`). `main.py`'s builders are built from
  the physics: `:391` (`Pipeline(dNstar=…)`), `:658` (`GradientCoupledInstanton(dNstar=…,
  Ninit=…, …)`), `:726` (`"InflatonTrajectory"`), `:819`, `:843`, `:1100`. None carries a job name
  or a time. But **an existing July store's `FullInstanton.label` reads `FullInstanton(N_init=20.12,
  N_final=19, dNstar=0.825)`, a format none of today's builders produces**, and the factories
  write `obj._label`, not the compute argument (`FullInstanton.py:285`, `:310`). The agent traces
  what reaches the column today, and whether one row's label can differ between two builds of one
  grid on one tree (the unified pipeline at `:391` against a per-stage queue; a straight build
  against a resumed one). If it can, it is bookkeeping by that argument, with the `path:line`; if
  it cannot, it is compared. Either is fine if the code settles it; only a label the code cannot
  settle is a §4 stop.
- **Timing keys**, by `git grep` at `0209137`: `compute_time` in every compute target, including
  `CompactionFunction`'s `metadata` (`CompactionFunction.py:143`, `:168`, `:252`, `:263`, `:315`,
  `:404`, and copied at `:671`, `:679`); `compute_time_total` (`GradientCoupledInstanton.py:453`);
  `mean_time_per_picard_iteration` (`FullInstanton.py:122`, `:283`; `picard.py:1718`);
  `picard_sweep_wallclock_min`/`_mean`/`_max` (`picard.py:1276-1280`, set only under
  `instrument_stiffness`). The grep found no other clock read whose value is stored; the agent
  confirms, including any nesting of one diagnostics dict inside another. The `reason` strings
  the orchestrator saw are constants, but `scale_assignment.py:169` stores a `reason` variable:
  the agent checks it carries no time.
- **The tables.** A shard of an existing SI store holds 30 tables, the registry's 30, and **no
  `*_tags` table** (SI has none). `redshift` is on every shard but in **neither** table list
  (`config/sharding.py`; `[redshift-registered-in-neither-table-list]`), like ChamPBH's
  `LambdaCDM`: the tool must not crash on it, and what it reports is the agent's choice, logged.
  `InflatonTrajectory` and `InflatonTrajectoryValue` are **replicated**; the four instanton
  families and their children are sharded. `GradientCoupledInstantonProfile` and
  `CompactionFunctionSamples` have a `serial` but are children (`parent_serial`, FK).
- **What an SI primary holds.** Read by the orchestrator from `test-gradient.sqlite` and
  `out-gci-convergence-campaign/phase_a.sqlite` (`mode=ro&immutable=1`, mtimes unchanged): the
  five tables `replicated_tables`, `shard_key_config`, `shard_keys`, `sharded_tables`, `shards`,
  and no client table. The `shards` rows are absolute paths into this checkout. The agent confirms
  from the code (prompt §2.2); it does not open those stores.
- **The readers' flags exist.** `config/argument_parser.py` has `--config`, `--database`,
  `--inventory`, `--targets`, `--no-store-values`, `--n-collocation-points`,
  `--alpha-regularization`, `--profile-db`, `--job-name`, `--ray-address`, `--prune-unvalidated`,
  `--shards`. Both plot parsers extend it (`create_plot_parser`, `plot_InstantonSolutions.py:80`,
  `plot_GradientCoupledSolutions.py:125`) and add `--output-dir`. `quadratic-minimal.yaml` is at
  the repository root. The agent still checks each flag (prompt §2.3).
- **The log lines** `stage_counts.py` reads: `RayWorkPool` prints `\n** {title}` (`:181`),
  `   -- ALL WORK ITEMS COMPLETE in time …` and `      Queue summary: …` (`:581-586`), and
  `      (no compute items were evaluated - all assets read from datastore)` (`:588-590`).
  `main.py:860` prints `** STAGE 4: COMPACTION FUNCTIONS` itself, outside a pool, and `:1103`
  titles a pool `STAGE 4: COMPACTION FUNCTIONS AND MASSES`: the parser must not conflate them.
- **DatastoreKit `v0.3.0`** resolves to `2f5417ea76cd…`; `datastorekit/shard_paths.py` and
  `docs/client-contract.md` §5 ("The layer's own tables") exist at the tag.
- **`.documents/dk-and-rpk-migration/` does not exist.** 01 creates it.
- **Ray, and another session.** **SecondaryGWKit's rehearsal is running on this machine**:
  `docs/handover/quadsource_atol_sweep.py --build --rehearsal` (pid 69779, its Python 3.12 venv,
  started 09:19), with an in-process Ray instance and live `Datastore` actors. It wrote no
  `/tmp/ray/ray_current_cluster`, and `RAY_ADDRESS` is unset, so `live_pool`'s bare `ray.init()`
  (`tests/conftest.py:52`) starts an instance of its own (Ray 2.55.1,
  `ray/_private/services.py:408-454`). **A `ray start` anywhere would change that**, so run the
  integration suite with `RAY_ADDRESS=local`, which forces a private instance. **Never run
  `ray stop` or `ray start`**: `ray stop` would kill the other session's rehearsal.
- **Load.** The load average was 45–66 at dispatch, from that rehearsal and system daemons.
  Suites run slower than at planning; that is not a failure.
- **Not touched, and staying:** every factory, `Datastore/SQL/`, `RayTools/`, `config/`,
  `requirements.txt`, every existing test, `CLAUDE.md`, `.claude/rules/`, the README and the
  other prompts, and every store in the tree: `test-gradient*.sqlite` (12 files) and the five
  files under `out-gci-convergence-campaign/`.
- **Baselines at `0209137`** (2026-10-12, run by the orchestrator, serially):
  - `-m "not integration and not slow"`: **631 collected, 630 passed, 1 skipped**, 328 s (110 s at
    planning; load average 66 at the start);
  - `RAY_ADDRESS=local … -m integration`: **61, 60 passed, 1 skipped**, 104 s (24 s at planning;
    load average 261 at the start). `RAY_ADDRESS=local` works: `live_pool` started its own
    instance and left the other session's alone.
- **Expected counts after 01:** the default run 631 + the new tests, by module; integration 61,
  unchanged.

**What the review exists to establish.**
- **(E1) The provenance helper.** `None` for a distribution not installed; otherwise exactly the
  five keys, each from its PEP 610 place. An absent, unreadable or non-object `direct_url.json`
  gives `None, None, None, False` and never raises. It imports nothing it describes, and uses the
  standard library only. It works against the real `importlib.metadata`, not only the mock.
- **(E2) The drivers.** Each prints the line exactly once, before `ray.init(` and `ShardedPool(`,
  in the scope where those are called; nothing else in any driver changes.
- **(E3) The comparison reads only what it should.** Every `sqlite3.connect` is `mode=ro` on a
  globbed file; no path from a `shards` table is ever opened; no layer, Ray or SQLAlchemy is
  imported; no file changes.
- **(E4) The comparison sees every physics difference and only those.** Canonical floats by
  `float.hex`, inside JSON too; foreign keys resolved recursively on the same shard; `version` by
  label; all four polymorphic pairs declared and mapped; JSON compared structurally, with timing
  keys set aside at any depth; the bookkeeping list justified entry by entry; replicated copies
  cross-checked; near misses paired; exit codes 0/1/2 as specified. On a real store, not only on
  imitations.
- **(E5) The scripts.** Each prints its usage, takes `REHEARSAL_ROOT`, starts no Ray; `build.sh` is
  README §4.1's command verbatim but for its parameters; `interrupt_when.py` signals only the pid
  it is given, and only after the banner and the delay; `run_readers.sh`'s flags exist.
- **(E6) The pins.** The six breakages each fail the named test, for the stated reason.
- **(E7) The records.** The results note, the board's §1 row, T1–T3, `### 5.5 After prompt 01`;
  the counts.

**Conventions.** All of these bind the agent, and the brief says so.
- **Staging and reporting.** Stage by explicit path only, and show `git diff --cached --name-only`
  before committing. Count, then paste. A results note states only what the diff and the tests
  show.
- **The SHA.** The agent writes "this commit"; the orchestrator substitutes the SHA in its
  follow-up.
- **Suites.**
  - `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`, and
    `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`. Write
    the output to a file in the agent's scratch directory, and grep the verdict from it.
  - Run each **in the foreground**, serially, within the turn. A Bash call is capped at ten
    minutes. If the default run nears the cap under load, split it by file and add the counts.
  - A failure is re-run alone before it is called real.
- **Breakage diffs** are recorded so that `git apply` replays them from a clean tree at the agent's
  commit. Check each with `git apply --check` and `-R --check` after committing, and replay in
  `bash`, not zsh.
- **Scratch.** The agent uses its own subdirectory of the session scratchpad, never `/tmp`. Python's
  `tempfile` in tests is fine. No scratch `.py` file goes under `tools/`, `tests/` or
  `.documents/`, even for a moment.
- **The venv.** The agent installs nothing, uninstalls nothing and runs no `pip install`. 03 is
  the first prompt that changes the venv.
- **Stores.** The agent opens no store but a test's temporary one: not `test-gradient*.sqlite`,
  nothing under `out-*/`, and it does not create `~/ScienceData/StochasticInstantons-rehearsals/`
  (02 does).
- **Ray.** The agent starts no cluster, runs no driver, and never runs `ray start` or `ray stop`.
  The integration suite's own instance, under `RAY_ADDRESS=local`, is the only Ray it causes.
- **Stop conditions are real.** A stop goes to the user through the orchestrator, and the agent
  resumes with `SendMessage`.
- **Other sessions** may land commits on this branch. Review against the agent's commit, and check
  `git log` before measuring at `HEAD`.

## 1. Before you dispatch

1. **The tree.** Record the branch (`dk-and-rpk-migration`) and `HEAD`.
   - `git status --short` shows nothing tracked, and `git diff --cached` is empty.
   - `git log --oneline 0209137..HEAD` touches no code; otherwise see the gate.
2. **Ray.** `ls /tmp/ray/ray_current_cluster` finds nothing and `RAY_ADDRESS` is unset. Any Ray
   process running is another session's (check its venv path), and is left alone.
3. **The venv.** `./venv/bin/pip show datastorekit raypoolkit` finds neither (the prompt's gate).
4. **Baselines.** Both suites at `HEAD`, serially, in the background of the orchestrator's session,
   with the load average. Give the agent the numbers.
5. **The stores' mtimes**, for check 9: `/usr/bin/stat -f '%m %z %N'` over every `*.sqlite` and
   `*.db` file in the tree outside `venv/` and `.git/` (17 files at dispatch), saved in the
   scratchpad. (The `stat` on `PATH` may be GNU's; use `/usr/bin/stat`.)

**Done at dispatch (2026-10-12):** `HEAD` `0209137` + this note; clean; no
`ray_current_cluster`; neither package installed; the suites (630 + 1 / 60 + 1); 17 store files
recorded in `orch01/stores-mtimes-before.txt` in the session scratchpad. The baselines are in §0.

## 2. Dispatch

Dispatch one fresh-context subagent, on **Opus**. Give it:
- the prompt;
- the campaign README and the board;
- `HEAD` and the baselines;
- §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the session scratchpad.
  The agent does not read `orchestrator/`, and does not read prompts 02–04.

Tell it plainly:
- **One commit, at the end.** Its results note is
  `.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md`, in README §5.1's
  form, with the prompt's §6 additions.
- **The files it may add or change are the prompt's §5 list, and nothing else** — with
  `.documents/OPEN-ISSUES.md` only if an issue opens. It must not touch `orchestrator/`,
  `measure/`, `README.md`, `.prompts/INDEX.md`, any factory, `Datastore/SQL/`, `RayTools/`,
  `config/` or any existing test.
- **It runs no build, opens no real store, installs nothing, and starts and stops no Ray.**
- **The corrections in §0**: the plot scripts' `__main__` block, the four polymorphic pairs, the
  empty-until-imported diffusion registry, the `label` question, the licence header.
- **Stop and ask** on any of the prompt's §4 conditions. An existing test that fails is current
  behaviour moving, never a reason to edit it.
- **It replies with** the results note's path; the provenance line's exact format, and its output
  in this venv; the bookkeeping list, the JSON timing keys and the polymorphic map, with their
  `path:line`s; how it classed `label`; the new tests by module, with counts; both suites; every
  deviation with its class; and the "State handed to the next prompt" section, verbatim.

## 3. The review — ten checks

1. **Scope.** `git show --stat <commit>` touches only the prompt's §5 list (plus
   `.documents/OPEN-ISSUES.md` if an issue opened). `git status --short` shows nothing else
   changed or added.
2. **E1, by reading.** `utilities.py`'s diff is the two imports (or so), the constant and the two
   functions; nothing pre-existing moved. The helper reads `version` from metadata, `url`,
   `vcs_info.commit_id`, `vcs_info.requested_revision`, `dir_info.editable` from
   `direct_url.json`, and treats a non-object `vcs_info`/`dir_info` as absent, as SGK's and
   ChamPBH's do. Call it from the scratchpad on odd `direct_url.json` contents (a list, a string,
   not JSON, not UTF-8, `editable` as `"true"`, a `read_text` that raises): it returns, never
   raises.
3. **E1, without a mock.** Put a stand-in `datastorekit-0.3.0.dist-info` (with `METADATA` and a
   VCS `direct_url.json` at `v0.3.0` / `2f5417ea76cd…`) first on `sys.path` in a
   `./venv/bin/python -I` process with the repository on its path, and call both functions.
   - `datastorekit` gives every field, `editable: False`; `raypoolkit` gives `None`; the line says
     so.
   - Repeat with an editable `direct_url.json` (`{"url": "file:///…", "dir_info": {"editable":
     true}}`): the line says `editable` visibly. Then with the file removed.
4. **E2, by `ast` against the pre-images**, docstrings stripped. For `main.py`, the module body
   differs from `0209137`'s by exactly one import and one expression statement printing the line,
   at module level, before `ray.init(` (so before the `With` whose context is `ShardedPool(`).
   For each plot script, the module body differs by one import, and the `if __name__ ==
   "__main__":` body by one expression statement before `ray.init(`. Every other top-level
   statement dumps identically. `utilities.py`: every pre-existing function dumps identically.
5. **E3, the opens.** Run the tool on check 6's copies under a wrapper from the scratchpad that
   replaces `sqlite3.connect` with a logger and then runs `tools/compare_stores.py` by
   `runpy.run_path(..., run_name="__main__")`. Every open is `file:…?mode=ro` with `uri=True`, on a
   file the glob finds inside the copies, and none of the originals that the copies' `shards`
   tables name. Then grep the tool for `import` and `ATTACH`: no `Datastore`, `datastorekit`,
   `ray`, `sqlalchemy`, `ComputeTargets`, `CosmologyConcepts`, `InflationConcepts`, and no
   `ATTACH`.
6. **E4, a real store.** Copy `test-gradient.sqlite` and its ten shards into a scratch directory
   twice, as `A/` and `B/` (renamed so the glob finds them; the profile database is not part of
   the store). Then, on the copies only:
   - `A` against `B`: exit 0, every client table compared with its row count, and the wall time;
   - in `B`, one `FullInstantonValue.fields_json` float moved one ulp (`math.nextafter`, re-dumped
     with `json.dumps`): exit 1, the row named by physical labels, paired as a near miss with both
     values and the relative difference;
   - restored; in `B`, one `GradientCoupledInstanton.diagnostics_json` `compute_time_total` (or
     `compute_time`) changed, and one `timestamp`: exit 0, both reported as bookkeeping;
   - restored; in `B`, one science key inside a `diagnostics_json` moved one ulp: exit 1, named;
   - restored; in `B`, one `FullInstanton.diffusion_type` set to 99: a named problem, no
     traceback; and one `InflatonTrajectory.potential_type` set to 2 on every shard (a type that
     maps, to a serial `QuarticPotential` does not hold): a named unresolved reference;
   - restored; in `B`, one replicated row's float changed on one shard only: a named problem;
   - restored; in `B`, one `CompactionFunction` row and its samples deleted: exit 1, A-only rows
     named by their labels;
   - restored; one shard file removed from `B`: exit 2;
   - `--snapshot A` then `--schema B --against` it: no difference; then one index dropped in `B`'s
     shard 0: reported.

   Delete the copies afterwards.
7. **E4, by reading.** The bookkeeping list: each entry with its `path:line`, each confirmed where
   it is written; no physics column in it (`validated`, the failure columns, every `noise_*`,
   every `M_*`, `S_MSR`, step and iteration counts, the `wallclock_budget*` keys, every value-table
   column). The polymorphic map: all four pairs, each value with its source, and test 12 checking
   both registries non-empty and equal in both directions. The JSON columns: each confirmed as
   `json.dumps` output; timing keys matched at any depth. `redshift` handled as the results note
   says. The memo is a digest keyed by shard, table and row key.
8. **E5 and E6.**
   - Each script's `--help` or usage line. `build.sh`'s command against README §4.1, token by
     token, for both modes. `run_readers.sh`'s flags against the parsers.
   - `interrupt_when.py`, from the scratchpad: a `sleep 600` whose pid is in a pidfile, a log that
     gains the banner after a few seconds; it waits the delay, sends `SIGTERM` to that pid only,
     and says so. A second run where the process exits before the banner: it says so, exit
     non-zero.
   - `stage_counts.py` on a synthetic log written from §0's print shapes, with both `STAGE 4`
     lines: the counts as expected.
   - In `bash`, replay each of the six breakage diffs with `git apply`, run the named test, see it
     fail for the stated reason and nothing else fail; revert with `git apply -R`; `git status`
     clean.
9. **The stores' mtimes** match §1 step 5. `~/ScienceData/StochasticInstantons-rehearsals/` does
   not exist.
10. **E7 and the suites.**
    - The results note has README §5.1's sections and the prompt's §6 additions, and says the
      README undercounted the polymorphic pairs.
    - The board has the §1 row (✅, "this commit", the results note), T1–T3 and
      `### 5.5 After prompt 01`.
    - No §3 entry and the index untouched, or, if one opened, the index's row, count and date in
      the same commit.
    - Both suites at `HEAD`, serially: the default run 631 + the new tests, all passing (1
      skipped); integration 61 (60 passed, 1 skipped). The new files carry the licence header.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 01* paragraph in §5.5: what each
  check found, the probe's outcome, and anything handed on to 02. Fix small residue in a follow-up
  commit of its own:
  - "this commit" → the SHA (board and results note);
  - a list of the orchestrator notes on the board, with this one marked "used for 01";
  - `.prompts/INDEX.md`: the campaign's line (01 landed; `.documents/dk-and-rpk-migration/` is
    created by 01, not 02);
  - README §0.1 item 11 and §4.2: four polymorphic pairs, not two (a dated correction, as the
    README's other revisions are).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:**
  - the provenance line, and its output in this venv and in the probe;
  - the comparison's behaviour on the `test-gradient` copy: the clean pass, its time, and each
    perturbation;
  - the bookkeeping list, the timing keys, the polymorphic map, and how `label` was classed;
  - the tests added, by module, and the breakages;
  - the suites' counts.
- **Then 02**, RH0. It runs these scripts and this tool unchanged (README §4). Its note is written
  after this review. It needs a machine no other session is loading: the SGK rehearsal running at
  this dispatch must have finished.
