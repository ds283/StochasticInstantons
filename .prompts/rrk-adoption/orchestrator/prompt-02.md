# Orchestrator — prompt 02, the fingerprinter

Read [`../README.md`](../README.md) first: §0.3 ("The registry", "The tests"), §0.4, §2.2 (02's
charter), §5 and §6.2 (P5, P6, P11). Then the board's §5.2 (01's record) and §5.3 (`main` merged in).
This is the campaign's first note: 01 was dispatched without one. Its conventions are
`dk-and-rpk-migration`'s
([`../../dk-and-rpk-migration/orchestrator/prompt-01.md`](../../dk-and-rpk-migration/orchestrator/prompt-01.md),
§0 "Conventions"), carried over. What differs is said here.

**You do not write code.** You may:
- run the suites, `pip` read-only commands, `runregistrykit list`, `ray_cluster.sh status`, and
  read-only Python probes from the session scratchpad;
- read RunRegistryKit, ChamPBH and SGK with `git show`, never changing them;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`02-the-fingerprinter.md`](../02-the-fingerprinter.md) · **Board items:** F1–F4 ·
**Closes:** nothing · **Opens:** nothing expected · **Model:** Sonnet, as the prompt recommends.
Nothing is pushed.

**Gate:**
- 01 landed (`60687f0`, `7071bb8`) and the gate **Pin** holds (board §2). `main` merged in at
  `24e641f` (board §5.3). `HEAD` is the commit that adds this note, on `rrk-adoption`; the tree is
  clean; `git worktree list` shows the main checkout alone.
- The venv holds `datastorekit` 0.5.0 at `f47b9a25…`, `raypoolkit` 0.3.0 at `67a75b97…` and
  `runregistrykit` 0.2.0 at `0bae3a3c…`, none editable.
- `ray_cluster.sh status`: lock free, no SI process, the four ports free. `var/runs/` and
  `var/datastores/` empty.
- No other session runs a suite or a Ray job from this venv, or installs into it, while 02 runs.

## 0. What makes this prompt unusual

**Its one committed artefact that is data, the golden file, is written once and never again.** A
golden file written from a store that is not reproducible makes a flaky test forever, and one written
from the wrong builder pins the wrong thing. So the orchestrator has measured the builder's
reproducibility and the expected digest before dispatch, and the review checks the agent's file
against them. The rest is a small module after two siblings', and a guard test from a published
recipe.

**Corrections to the prompt**, each recorded as a deviation of the class given.
1. **The `v0.5.0` addendum is not at the tag** (`STRUCTURALLY REQUIRED`). Read-first 2 says
   "RunRegistryKit at `v0.2.0`" for `docs/adoption/README.md` §6 *and* its addendum. The addendum,
   "The Q5 guard under DatastoreKit `v0.5.0`", was added after the tag, at `70ee1e8` (`main`, the
   checkout's `HEAD`); at `v0.2.0` the file ends at "## `v0.2.0`". Read §6 and the addendum at
   `main` (`git show main:docs/adoption/README.md`, §6 from `:176`, the addendum from `:349`). The
   package code is read at the tag, or in the venv (they are one: the venv holds `0bae3a3`).
2. **The board section is `### 5.4`, not `### 5.3`** (`STRUCTURALLY REQUIRED`). §5.3 now records
   the merge of `main` (2026-10-25). Acceptance 4's `### 5.3 After prompt 02` becomes
   `### 5.4 After prompt 02 (<date>)`.
3. **The import check** (`IMPLEMENTATION CHOICE`, ChamPBH's deviation 2). F1's "loads nothing that
   `config.datastore` does not already load" is not literally true, and cannot be. Measured here:
   after `import config.datastore`, importing `runregistrykit.fingerprint` and building a
   `DatastoreKitFingerprinter` adds 9 modules: `runregistrykit`, `.client`, `.fingerprint`,
   `getpass`, `termios`, and `tomllib` (four). **None of `ray`, `sqlalchemy` or `datastorekit`.**
   `import config.fingerprint` adds those and itself. The agent reports its list by `sys.modules`,
   says that none of the three packages is among it, and the docstring says what is true.
4. **The count is of classes, not definitions** (`NOTED`; ChamPBH's 02 tripped on it).
   `inventory_specs(factories)` gives **24** entries, in registry order: 22 `inventory_spec`
   definitions serve 24 classes (`tests/test_inventory_specs.py:319`). `config.datastore.factories`
   has 30 entries; the other 6 have no spec. Of the 24 digests, **18 are distinct** (`version` =
   `store_tag`; `delta_Nstar` = `N_init` = `N_final` = `quartic_coupling`; `inflaton_mass` =
   `phi_value` = `pi_value`). `GradientCoupledInstanton` alone has a non-empty `extra_values`.
5. **`take` returns a pair** (`NOTED`). `DatastoreKitFingerprinter.take(primary, taken)` returns
   `(fingerprint, inventory)`. ChamPBH wrote its golden from `take(primary, None)` as
   `json.dumps(fp, indent=2, sort_keys=True) + "\n"`, so `taken` is `null` in the file, and took
   with `taken={}` in the test, comparing with `taken` removed from both. Follow it.
6. **The command line's exit** (`NOTED`). RunRegistryKit's README at `v0.2.0` ("The store
   commands", `:236-254`) gives no exit status for a store with no sidecar. ChamPBH's run of the
   same command exited **0**, printed `store:`, `digest:`, `format:`, the classes, `problems: none`
   and last `recorded: none recorded (the sidecar is absent)`, and wrote nothing. That is the
   behaviour to expect; anything else is §4's stop.
7. **The breakage "one value changed in the golden store's rows"** (`NOTED`). The fingerprint reads
   what the specs name, so the change must be to a value a spec reads. `tolerance`'s spec has the
   leaf `log10_tol` (`tolerance.py:39`), and `_STORE_SCRIPT` stores `log10_tol=-8` and `-6`: an
   uncommitted diff of `-8` to `-9` in `tests/test_inventory_store.py` is one such change. It also
   fails that module's own tests; the record says so.

**What the orchestrator measured at `24e641f`** (2026-10-25, 08:57–09:05 BST). Pass them on.
- Gate as above. `runregistrykit list`: no runs. `pip freeze` 84 lines, `pip check` clean.
- **The builder imports cleanly and is reproducible.** From a probe with `tests/` on `sys.path`,
  `from test_inventory_store import _STORE_SCRIPT` imports without modifying the module. The script,
  run twice as the `store` fixture runs it (each in its own `tempfile` directory), wrote a primary
  and two shards each time, about 30 s a build, and
  `DatastoreKitFingerprinter(config.datastore.factories, 1).take(primary, None)` gave, both times,
  `problems: {}` and **`digest` `e3437a9b2f16415f5635ee121fa7f09d07ac74c30400d5973a3afaeec8fc7c78`**,
  with `fingerprint_format` 1 and `encoding_format` 1. The fixture `store` is module-scoped; imported
  into the golden module it builds once more there.
- **The spec digests** (the addendum's `plain`, the §6 `spec_digests`): 24 pairs, the first
  `version` `02929e93…ec10` (the README's example value), `GradientCoupledInstanton`
  `0059b6b6…a9f0`. The agent computes its own; the review compares them.
- **Baselines**, serially, `./venv/bin/python -m pytest … -p no:cacheprovider`: default **738**
  (737 passed, 1 skipped), 142 s; `RAY_ADDRESS=local … -m integration` **67** (66 passed, 1
  skipped), 146 s. 01's counts. **The load was 30–44** (Time Machine, ChronoSync and other work on
  the laptop, none of it SI's): the suites ran four times slower than at 01. Slow is not a hang.
  `pytest` must be run as `./venv/bin/python -m pytest`; the bare `./venv/bin/pytest` fails at
  `conftest.py:28` (`No module named 'config'`).

**What moves on purpose:** §5's list of the prompt. **What must not move:** every other `.py` file,
`tests/test_inventory_store.py` and `tests/test_inventory_specs.py` among them; `main.py` and the
plot scripts (`git diff 1c223e8 -- main.py plot_*.py` empty); every spec, factory and registry
entry; the venv; anything under `var/`; RunRegistryKit, ChamPBH and SGK.

## 1. Before you dispatch

1. The Gate, as §0's facts.
2. **Baselines**, both suites serially at `24e641f` (`orch02/baseline-suites.txt`), with the load.
3. **The commit of this note**, alone, staged by path.

**Done at dispatch (2026-10-25):** the Gate as §0; the baselines 738 / 67 as §0
(`orch02/baseline-suites.txt`); `pip freeze` saved as `pip-freeze-before.txt`; the two builds and
the spec digests in `orch02/twice.txt` and `orch02/specs.txt`.

## 2. Dispatch

One fresh-context subagent, on **Sonnet**, in the main checkout. Give it the prompt, the README,
the board, `HEAD`, the baselines, and §0 of this note up to "## 1. Before you dispatch", as a copy in
the session scratchpad. The agent does not read `orchestrator/`.

Tell it plainly:
- **One commit**, staged by explicit path after showing `git diff --cached --name-only`; the results
  note `.documents/rrk-adoption/02-the-fingerprinter.md`; the board's `### 5.4`.
- **The corrections of §0**, each in the results note with its class.
- **The golden file is written once**, by a few lines it records, after two builds in two test
  processes have given equal fingerprints. Its digest is expected to be `e3437a9b…7c78`; if it is
  not, the agent stops and says so before committing.
- **The breakages** are recorded as diffs that `git apply` replays from a clean tree at its commit,
  checked with `git apply --check` and `-R --check`, replayed in `bash`; never committed. Each says
  which tests failed, and which others failed with them.
- **Scratch** is the agent's own subdirectory of the session scratchpad, never `/tmp`. No probe `.py`
  goes under `tests/`, `config/` or `.documents/`.
- **No Ray but the tests' own.** No cluster, no `ray start`, no `ray stop`. The suites under
  `RAY_ADDRESS=local`, and `_STORE_SCRIPT`'s private `ray.init(address="local")`.
- **Stop and ask** on any of the prompt's §4 conditions.
- **It replies with:** the commit's SHA and `--stat`; the import list; the 24 pairs and the
  distinct count; the golden file's SHA-256, digest and the two builds' digests; the command line's
  output, whole; each breakage with what failed; both suites before and after, with the load and the
  times; every deviation with its class.

## 3. The review — eight checks

1. **Scope.** `git show --stat`: exactly §5's list (with the results note and the board). `git
   status --short` clean. `git diff --name-only 24e641f HEAD -- '*.py'` is the four Python files of
   §5 and no other; `git diff 1c223e8 HEAD -- main.py plot_*.py` empty; `tests/test_inventory_store.py`
   and `tests/test_inventory_specs.py` unchanged; `var/` still empty. Nothing pushed.
2. **F1, by reading.** The docstring: who does what, the guard's name, and the import fact as
   measured. `FINGERPRINT_FORMAT = 1` with the comment on when it moves and that golden files are
   never overwritten. `SPEC_DIGESTS[1]` recomputed here by `orch02/specs.py` and compared pair by
   pair: 24 pairs in registry order. `fingerprinter` an instance, its factories `config.datastore`'s.
   The import list re-measured here.
3. **F2.** `runregistrykit.toml` gains `[stores]` with the one key, nothing else moved. In
   `tests/test_registry_config.py`, `EXPECTED_KEYS` gains `"stores"` and nothing else in the file
   moves but the comment beside it.
4. **F3, by reading and running.** `plain` is the addendum's: the `extra_values` condition, keys as
   `json.dumps`, sequences as lists. `spec_digests` is over `inventory_specs`. A failure names the
   classes and says to bump and pin; "no pin" fails with its own message. The key-type test uses
   stand-in `Parent`s keyed by `0` and `"0"`; the amendment test both ways. Runs without Ray.
5. **F4.** `_STORE_SCRIPT` and `store` imported, not copied. `TestGolden` (and the command-line
   test) marked `integration`; `TestConfigFingerprint` not. The golden file: its SHA-256 recomputed;
   its `digest` equal to §0's `e3437a9b…7c78`, `taken` `null`, `problems` `{}`, formats 1 and 1; its
   class counts equal `EXPECTED_COUNTS` of `test_inventory_store.py`. The command line's recorded
   output: exit 0, the golden digest, `recorded: none recorded (the sidecar is absent)`.
6. **The breakages.** Each diff replayed with `git apply` in `bash` from the clean tree at the
   agent's commit, the named test run, its failure seen, reverted (`git status` clean). The
   `GradientCoupledInstanton` one fails F3 naming that class alone.
7. **The suites, re-run here** at the agent's commit, serially: default 738 plus F3's and
   `TestConfigFingerprint`'s tests, `integration` 67 plus `TestGolden`'s and the command line's. All
   pass but the one skip each. `runregistrykit list`: no runs.
8. **The records.** The results note in `dk-and-rpk-migration` README §5.1's sections, with §2's
   checks and their output, §0's corrections as deviations with their classes. The board: header,
   row 02 landed, F1–F4, the gate **Fingerprint**, `### 5.4`. `INDEX.md`'s line, its status 2 / 5.
   No issue opened, so `OPEN-ISSUES.md` untouched. The commit message ends with the
   `Co-Authored-By` line.

## 4. After the review

If it passes, residue in a follow-up commit of its own:
- "this commit" → the SHA, on the board, in the results note and in `INDEX.md`;
- the board gains a list of orchestrator notes, this one marked "used for 02" (01 had none);
- `### 5.4` gains an *Orchestrator review of prompt 02* paragraph: what each check found;
- prompt 02's read-first 2 and acceptance 4 left as they ran; the board's paragraph names
  corrections 1 and 2.

Anything that is not residue is opened on the board's §3 and in `OPEN-ISSUES.md` in the same commit.

**Report to the user:** the fingerprinter and its format; the 24 pinned digests; the golden digest
and its reproducibility; the suites; and that 03, which needs only 01, is next.
