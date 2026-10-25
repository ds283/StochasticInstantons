# rrk-adoption campaign — implementation state

**Last updated:** 2026-10-25 · **Status: COMPLETE — 5 of 5 prompts landed (§5.7); `main` merged in
with `rpk-v030-adoption` (§5.3). R1–R7,
U1 and U2 ruled by the user; P1–P14 stand as proposed (README §6). The branch `rrk-adoption` is cut
from `main` at `1c223e8`, after `dk-and-rpk-migration` was merged into `main` (R7); its merge back
into `main` is the user's. Final suites: default 848 (847 passed, 1 skipped), `integration` 72 (71
passed, 1 skipped); `slow` 69, not run.**
The plan is [`README.md`](README.md), written on 2026-10-23 at `8b4f615`. Prompts 01–05 were written
once the user had ruled (README §2.1).

The campaign adopts `runregistrykit[stores]` `v0.2.0`: the pin, the config, the rules and a
discovery hook, a fingerprinter at format 1 with its guard, a wrapper driver that registers
`main.py` runs without changing `main.py`, and a rehearsal of registered, interrupted and
hard-killed builds. Its RunRegistryKit gates are drafted for that repository when they hold (P13).

**Campaign:** [`README.md`](README.md) ·
**Orchestrator notes:** [`orchestrator/prompt-02.md`](orchestrator/prompt-02.md) (used for 02; 01 had none),
[`orchestrator/prompt-03.md`](orchestrator/prompt-03.md) (used for 03),
[`orchestrator/prompt-04.md`](orchestrator/prompt-04.md) (used for 04),
[`orchestrator/prompt-05.md`](orchestrator/prompt-05.md) (used for 05) ·
**Checklist:** RunRegistryKit's `docs/adoption/stochasticinstantons.md` and
`docs/adoption/v0.2.0/stochasticinstantons.md` (read, never edited) ·
**Code:** `requirements.txt`, `runregistrykit.toml`, `.gitignore`, `.claude/settings.json`,
`config/fingerprint.py`, `RunDrivers/`, `tests/`, `CLAUDE.md`, `.claude/rules/run-registry.md` ·
**Results:** `.documents/rrk-adoption/` (results notes; `verification.md`, created by 04) ·
**Index:** [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) §6b (one issue, opened at
03's review)

> **Maintenance rule.** Whenever an entry is added to, narrowed in, or closed out of §3 or §4
> below, [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) is updated **in the same
> commit**: the row is added, moved or deleted, and the count and date in its header are
> corrected. See `CLAUDE.md`.

### Decisions

**Ruled by the user on 2026-10-23 (README §6.0, §6.1):**

| Decision | Decided |
|---|---|
| **R1** — the store layer | adopted, with the core |
| **R2** — how runs register | a wrapper driver; `main.py` does not depend on RunRegistryKit and is launchable by hand |
| **R3** — the provenance helper | kept: substituting it would make `main.py` and the plot scripts import the package (R2) |
| **R4** — the sidecar | created by a person after the store's first close, as ChamPBH and SGK; never by `main.py` |
| **R5** — what registers | long-running and archival runs; never the plot scripts or `--inventory` |
| **R6** — where stores live | `var/datastores/` |
| **R7** — the branch | `dk-and-rpk-migration` merged into `main` first (done: `1c223e8`, a fast-forward, not pushed); `rrk-adoption` cut from `main` |
| **U1** — discovery | a `SessionStart` hook in `.claude/settings.json` running `runregistrykit list` (01, C4) |
| **U2** — the hard-kill route | rehearsed in 04 (H3) |

**Proposed by the planner (README §6.2):** P1–P14, accepted as proposed: the user gave no ruling on
any of them.

---

## 1. Prompts

| # | Prompt | Model | Status |
|---|---|---|---|
| 01 | [`01-pin-config-and-rules.md`](01-pin-config-and-rules.md) | Sonnet | **landed** 2026-10-23 (`60687f0` and `7071bb8`) |
| 02 | [`02-the-fingerprinter.md`](02-the-fingerprinter.md) | Sonnet | **landed** 2026-10-25 (`0fcaf7c`), reviewed |
| 03 | [`03-the-wrapper.md`](03-the-wrapper.md) | Opus | **landed** 2026-10-25 (`16e1cc1`), reviewed |
| 04 | [`04-rehearse-registered-runs.md`](04-rehearse-registered-runs.md) | Opus | **landed** 2026-10-25 (`29705f2`), reviewed |
| 05 | [`05-close.md`](05-close.md) | Sonnet | **landed** 2026-10-25 (this commit) |

01 comes first; 02 and 03 each need only 01; 04 needs 02 and 03; 05 needs 04 (README §2.1).

### 1.1 Items

| Item | Prompt | What | Status |
|---|---|---|---|
| **C1** | 01 | the pin, in a commit of its own; the venv; RunRegistryKit's suite on the installed package | done |
| **C2** | 01 | `runregistrykit.toml` (no `[stores]`), `var/` ignored, `var/runs/` and `var/datastores/` | done |
| **C3** | 01 | `CLAUDE.md`'s section and `.claude/rules/run-registry.md` | done |
| **C4** | 01 | the `SessionStart` discovery hook (U1) | done |
| **C5** | 01 | `tests/test_registry_config.py` | done |
| **F1** | 02 | `config/fingerprint.py`: format 1, `SPEC_DIGESTS`, the fingerprinter | done |
| **F2** | 02 | `[stores]` in the config | done |
| **F3** | 02 | `tests/test_fingerprint_format_guard.py`, with the `v0.5.0` amendment (P5) | done |
| **F4** | 02 | `tests/test_store_fingerprint_golden.py` and its golden file (P6) | done |
| **W1** | 03 | `RunDrivers/registered_run.py` | done |
| **W2** | 03 | its arguments and refusals | done |
| **W3** | 03 | registration, the streams and the heartbeat (P7) | done |
| **W4** | 03 | Ray and the signals (P9) | done |
| **W5** | 03 | running `main.py`, finishing with the fingerprint, the exit marker | done |
| **W6** | 03 | `tests/test_registered_run*.py` | done |
| **H0** | 04 | the launcher `build_registered.sh` (P8) | done |
| **H1**–**H4** | 04 | `reference`; `resumed-a` (`SIGTERM`); `resumed-b` (`SIGKILL`, `end`); `resumed-c` | done |
| **H5** | 04 | the stores compared, with each other and with RH2's `11-reference` (P10) | done |
| **H6** | 04 | `.documents/rrk-adoption/verification.md` §1 | done |
| **Z1** | 05 | the descriptive documents | done |
| **Z2** | 05 | `CLAUDE.md`, the rules, the test counts | done |
| **Z3** | 05 | the stale prose (P12), `utilities.py`'s docstring among it | done |
| **Z4** | 05 | RunRegistryKit's G4 and G3 drafted; the handover to Phase 2 | done |
| **Z5** | 05 | the board closed; the indexes | done |

## 2. The gates

| Gate | Holds when | Status |
|---|---|---|
| **Pin** | 01's acceptance: `runregistrykit` 0.2.0 installed from the tag, not editable; the package's suite passes on it; the config, `var/`, the rules and the hook in place | **held** 2026-10-23 |
| **Fingerprint** | 02's acceptance: `SPEC_DIGESTS[1]` pinned and guarded; the golden fingerprint reproduced | **held** 2026-10-25 |
| **Wrapper** | 03's acceptance: the wrapper's tests pass; `main.py` unchanged and importing nothing of the package | **held** 2026-10-25 |
| **R** | 04's acceptance: the four registered builds recorded as planned; the resumed store and RH2's reference equal to `reference` | **held** 2026-10-25 |
| RunRegistryKit `extraction` **G4**, `interrupted-runs` **G3** | drafted by 05, committed in RunRegistryKit by the user (P13) | **drafted** 2026-10-25 (`.documents/rrk-adoption/verification.md` §2); the user's to commit there |

## 3. Active and unresolved issues

| Issue | Opened | Owner | What |
|---|---|---|---|
| `[default-suite-starts-ray-in-process]` | 2026-10-25, at 03's review (§5.5) | unowned; not this campaign's (P14) | Two modules of the default selection, `tests/test_plot_extraction_golden.py:67-78` and `tests/test_plot_adapters_golden.py:62-71`, call `ray.init(ignore_reinit_error=True)` in the pytest process from a module-scoped autouse fixture, with no address and no shutdown (each leaves the shutdown to `conftest.py`'s `live_pool`, which the default selection never builds). So the default suite starts a local Ray and leaves it up for every later module, against README §5's "no test needs Ray outside the `integration` marker" (`dk-and-rpk-migration`'s rule). And `ray.init()` with no address takes `RAY_ADDRESS` from the environment (`ray/_private/worker.py:1669-1671` at 2.55.1), so a default run in a shell where `RAY_ADDRESS` names a cluster (SI's rehearsal cluster, or another project's) attaches to it. Found by 03's agent, whose `no_ray_at_the_end` fixture therefore checks "as it found it" (03's results note, deviation 22 and observation 1). The fix is outside 03's file list: mark both modules `integration`, or init with `address="local"` and shut down at module teardown. |

### 3.1 Assigned to this campaign

None (P14).

## 4. Resolved issues

None.

## 5. Dispatch record

### 5.0 Planning (2026-10-23)

- **Evaluation.** At the user's request, RunRegistryKit `v0.2.0` was evaluated for SI, at
  `8b4f615`, the day `dk-and-rpk-migration` closed. Its findings are README §0.3: the pin resolves
  to one new distribution; the store layer fingerprints a copy of RH2's reference store over SI's
  24 classes with no problem; the core's `begin`, `finish`, stale run, refusal and `end` behave as
  documented; the package's suite passes on SI's venv but for three tests that need the package
  installed. Nothing in SI's tree, venv or stores was changed.
- **Rulings.** The user ruled R1–R7 (README §6.0) the same day. R3 resolved a conflict between
  the user's first ruling on the provenance helper (substitute) and R2.
- **Plan** written: README §0–§7, this board, and the campaign's line in `.prompts/INDEX.md`. No
  issue opened.

### 5.1 U1 and U2 ruled, the branch cut, and prompts 01–05 written (2026-10-23)

- **Rulings.** The user ruled U1 and U2 as recommended, and gave no ruling on P1–P14, which stand.
- **The branch (R7).** At the user's instruction, `dk-and-rpk-migration`'s board recorded the merge
  (its §5.31, `1c223e8`) and `main` was fast-forwarded to it from `7bb3efd`. Nothing was pushed.
  `rrk-adoption` was cut from `main` at `1c223e8`; this planning commit is its first.
- **The plan amended before commit**, by what writing the prompts measured:
  - SI's `main.py` prunes unvalidated rows at open by default (`--prune-unvalidated` is
    `store_true` with `default=True`), so a resume needs no flag; the README's three mentions say
    so;
  - `tools/compare_stores.py` opens every file `mode=ro`, so 04 compares its `reference` with RH2's
    `11-reference` too, bit for bit (P10, README §2.2 04 item 5): SI's proof that the wrapper
    changes nothing `main.py` stores;
  - SI builds a closed store with real rows only through the pool under a private Ray, so 03's
    fingerprint tests are `integration`, as 02's golden test (P11).
- **Prompts 01–05 written**, adapted from ChamPBH's `rrk-adoption` 01–05 (at `807f175`) to SI's
  layout: one test root (`tests/`, pytest, the `integration` marker), results notes under
  `.documents/rrk-adoption/`, SI's isolated cluster at `127.0.0.1:6390`, the rehearsal grid
  `quadratic-minimal.yaml` with `--targets homogeneous` (U11 of `dk-and-rpk-migration`), and two
  additions of SI's own: the discovery hook (U1) and the comparison with RH2.
- **Next:** 01.

### 5.2 After prompt 01 (2026-10-23)

- **Landed** in two commits on `rrk-adoption`: the pin alone, `60687f064a2a706bb39ea6c69fe8f4ace78375a8`, then `7071bb8` (config, ignore rule, rules, hook, test, results note). Results: [`.documents/rrk-adoption/01-pin-config-and-rules.md`](../../.documents/rrk-adoption/01-pin-config-and-rules.md).
- **Gate Pin holds.** `runregistrykit` 0.2.0 from `0bae3a3`, not editable; the freeze changed by that one line; RunRegistryKit's suite on the installed package: 410 tests, OK, 1 skipped (the three failures of README §0.3 pass). `list` on the empty root exits 0; the hook degrades to a notice with `var/runs/` aside.
- **Suites:** default 738 (737 passed, 1 skipped); `integration` 67 (66 passed, 1 skipped).
- **One deviation:** `git check-ignore -q` takes a single path, so C5 item 3 is parametrized over the two (6 tests, not 5).
- No issue opened; `OPEN-ISSUES.md` and `INDEX.md` need no change beyond the INDEX line's status (updated).
- **Next:** 02 and 03, each needing only 01.

### 5.3 `main` merged in, with `rpk-v030-adoption` (2026-10-25)

At the user's instruction, by the orchestrator of `rpk-v030-adoption` (that campaign's README §4,
item 3), before 02 is dispatched. Nothing pushed.
- **What came in.** `main` at `bb2d953`, fast-forwarded to the closed `rpk-v030-adoption`: the
  `raypoolkit` pin at `v0.3.0`; `ray_cluster.sh` taking the shared lock through
  `raypoolkit.rehearsal_lock` at `~/.raypoolkit/rehearsal-lock` (its `start`, `stop` and `status`
  keep their names and arguments); `CLAUDE.md`'s lock sentence and pin; `INFRASTRUCTURE.md` and
  `architecture-summary.md`'s pin statements; that campaign's prompts and results. No `.py` file.
- **Conflicts.** `requirements.txt` merged without one: the `raypoolkit` line at `v0.3.0` and this
  campaign's `runregistrykit[stores]` line both kept. `.prompts/INDEX.md` conflicted on its header
  and table: both campaigns' lines kept, the header recounted to 8 campaigns (0 ready, 1 live, 1
  halted, 6 complete), and this branch's `dk-and-rpk-migration` line kept, since it records P15.
  `CLAUDE.md` merged cleanly.
- **Checked on the merged tree.** No live line names the old lock location or pins `raypoolkit`
  at `v0.2.0`. `pip install --dry-run -r requirements.txt` installs nothing: the venv already holds
  `raypoolkit` 0.3.0 (since `rpk-v030-adoption` 01) and `runregistrykit` 0.2.0. `runregistrykit
  list`: no runs. Default suite 738 (737 passed, 1 skipped), as after 01.
- **For 02–05.** Nothing in them changes. README §0.3's "`raypoolkit` 0.2.0" in the venv is a
  record of 2026-10-23 and stays. 04's "Read first" 3 names the brief, whose §2 (the lock) is now
  replaced by RayPoolKit's `docs/rehearsal-lock.md` at `v0.3.0`; 04's orchestrator note should
  point the agent at the contract for the lock, and at `CLAUDE.md`'s rule that no `PURPOSE` names
  `/tmp/ray-si` and that a lock command typed by hand is the only process of its shell command.
  A held lock is still exit 3 from `start`, and `status` still reads `lock: free (…)` when free.

### 5.4 After prompt 02 (2026-10-25)

- **Landed** in one commit on `rrk-adoption`, `0fcaf7c`. Results: [`.documents/rrk-adoption/02-the-fingerprinter.md`](../../.documents/rrk-adoption/02-the-fingerprinter.md).
- **Gate Fingerprint holds.** `SPEC_DIGESTS[1]` pins 24 pairs (18 distinct); the guard names the class that changes. The golden file `tests/data/store_fingerprint_rrk-adoption-02.json` (SHA-256 `3ed2303e…0fa9`, digest `e3437a9b2f16415f5635ee121fa7f09d07ac74c30400d5973a3afaeec8fc7c78`) was written once, after two builds in two processes gave the same file and the digest the orchestrator had measured. `store fingerprint` on the store exits 0, ending `recorded: none recorded (the sidecar is absent)`.
- **Suites:** default 744 (743 passed, 1 skipped; recorded as 743 and 742 at landing, corrected at review); `integration` 70 (69 passed, 1 skipped).
- **Deviations:** the addendum is read at RunRegistryKit `main`, not the tag; this section is 5.4 not 5.3; the import list is stated as measured (10 modules, none of `ray`, `sqlalchemy`, `datastorekit`); 24 pairs (classes), 18 distinct; `take` returns a pair; the command line exits 0; B5 changes `log10_tol` in `test_inventory_store.py` (which still passes); `TestGolden` asserts the three empty classes of the harness's store. No issue opened; `OPEN-ISSUES.md` needs no change.
- **Next:** 03 (needs only 01); 04 needs 02 and 03.

**Orchestrator review of prompt 02** (2026-10-25, at `0fcaf7c`, by its note
[`orchestrator/prompt-02.md`](orchestrator/prompt-02.md) §3). It passes; nothing is opened.
1. **Scope.** The commit is the prompt's §5 list, the results note, the board and the `INDEX.md`
   line. The `.py` files changed since `24e641f` are the four of §5. `main.py` and the plot scripts
   are unchanged since `1c223e8`, and so are `test_inventory_store.py` and `test_inventory_specs.py`.
   `var/` is empty, the tree is clean and nothing is pushed.
2. **F1.** `SPEC_DIGESTS[1]` was recomputed here by the addendum's recipe and equals the pin pair
   for pair (24, in registry order). `import config.fingerprint` after `config.datastore` adds the
   10 modules reported, none of `ray`, `sqlalchemy` or `datastorekit`. `fingerprinter` is an
   instance and a `Fingerprinter`, at format 1, over `config.datastore.factories` itself.
3. **F2.** `[stores]` with the one key is appended. `EXPECTED_KEYS` gains `"stores"`, and the
   comment that promised it goes.
4. **F3.** `plain` is the addendum's, with keys as `json.dumps`. A failure names the classes and
   says to bump and pin, and "no pin" has its own test and message.
5. **F4.** `_STORE_SCRIPT` and `store` are imported, not copied. `TestGolden` and `TestCommandLine`
   are `integration`, and `TestConfigFingerprint` is not. The golden file's SHA-256 is
   `3ed2303e…0fa9`. Its `digest` is the orchestrator's pre-dispatch `e3437a9b…7c78`, with `taken`
   `null`, `problems` `{}` and formats 1 and 1, and its counts equal `EXPECTED_COUNTS`.
6. **Breakages.** The six diffs, extracted from the results note, equal the agent's scratch copies.
   Each was replayed with `git apply` in `bash` from the clean tree, its named test run, and
   reverted.
   - B1, B3 and B4 fail the pin naming `tolerance`, `GradientCoupledInstanton` alone, and every
     class respectively. B4 also fails `test_the_amendment`.
   - B2 fails the three pin tests. B6 fails `TestConfigFingerprint`.
   - B5 fails `TestGolden.test_the_golden_fingerprint`.
   - `git status` is clean after. The note's correction 7 said B5 would also fail
     `test_inventory_store.py`'s own tests. It does not, since none reads the value. The agent
     measured that, and the note is wrong in that sentence alone.
7. **Suites**, re-run at `0fcaf7c`, serially, with the load at 24:
   - default 744 (743 passed, 1 skipped, 139 deselected), 88 s;
   - `integration` 70 (69 passed, 1 skipped), 212 s;
   - `runregistrykit list`: no runs.

   The agent's own output reads 743 passed too. The results note and this section had transcribed
   it as 742 (743), and both are corrected in the residue commit, as is the note's sentence that
   this section recorded the `git apply` checks.
8. **Records.** The note has §5.1's sections, the eleven deviations with their classes, and the
   command line's output, whole. The board's row, items, gate and §5.4 are in place, as is
   `INDEX.md`'s line. `OPEN-ISSUES.md` is untouched, rightly. The commit message ends with the
   `Co-Authored-By` line.

**Residue** (this follow-up commit): "this commit" becomes `0fcaf7c` here, in the note and in
`INDEX.md`, and 01's becomes `7071bb8`. The default count is corrected. The board lists its
orchestrator notes. Prompt 02 is left as it ran: its read-first 2 (the addendum, at RunRegistryKit
`main`) and its acceptance 4 (§5.3, now §5.4) are corrections 1 and 2 of the note.

**A false premise, corrected.** Prompt 02 (F3) says SI has no polymorphic `Parent.types` keyed
by `int`, and the guard's docstring repeated it. Four specs have one: `InflatonTrajectory`'s
`potential` (`{1: …, 2: …}`), and the `diffusion_model` of `FullInstanton`, `SlowRollInstanton` and
`GradientCoupledInstanton` (`{1: 'MasslessDecoupledDiffusion'}`). So the key conversion carries SI's
own digests: without it `canonical_json` refuses those four specs. The test is unaffected. The
docstring's sentence is corrected in the residue commit, the only change there to a `.py` file.
Prompt 02 is left as it ran.

**Observation, not acted on.** In the golden store `FullInstanton` and `SlowRollInstanton` carry
the same class digest (`346bc1fe9ad3`), though their spec digests differ. The two specs differ only
in the name of the value table. The harness gives both classes three rows on the same parents, with
the same value rows, so the same content digest is expected. It is said here so that it is not
mistaken for a collision.

### 5.5 After prompt 03 (2026-10-25)

- **Landed** in one commit on `rrk-adoption`, `16e1cc1`. Results: [`.documents/rrk-adoption/03-the-wrapper.md`](../../.documents/rrk-adoption/03-the-wrapper.md).
- **Gate Wrapper holds.** `RunDrivers/registered_run.py` (W1–W5), ChamPBH's wrapper at `807f175` carried over and adapted to SI's parser, scope, banners and notify defaults; 106 tests in six modules `tests/test_registered_run*.py` and one helper, `tests/registered_run_helpers.py` (W6), run three times in a row, 106 passed each time; all six deliberate breakages caught. `main.py`, the plot scripts and `utilities.py` are unchanged since `1c223e8` and import nothing of the package (by `ast`). `CLAUDE.md`'s "Launching" sentence is definite, with the usage line.
- **Suites:** default 848 (847 passed, 1 skipped; +104); `integration` 72 (71 passed, 1 skipped; +2, the fingerprint at finish on copies of 02's golden store). `runregistrykit list`: no runs; `var/runs/` and `var/datastores/` empty.
- **Scope of 04's reference** (a tested literal): `config quadratic-minimal.yaml; targets homogeneous; potential Quadratic; m 1e-05 Mp; N_init 20–20, 1 sample; N_final 5–5, 1 sample; delta_Nstar 0.1–3, 10 samples; n_collocation_points 5; alpha_regularization 0.01; 10 shards; job rrk-adoption-04-reference`.
- **The beat on paper** (§2.3): a healthy rehearsal prints no RayWorkPool progress line (every stage under 60 s); its longest silence is `STAGE 2`, about 13 s at RH2's load, so the heartbeat's age stays under about 45 s.
- **Deviations:** 26, classified in the note: the orchestrator's twelve corrections (5.5 not 5.4; the 60 s floor with 300 s or 500 events; `** ` banners only; the registration lines as `>> `; no address check; the licence header; only `CLAUDE.md`'s sentence; the store copied per test; and four noted), ChamPBH's rulings 2 and 4–8 with the note's two breakage tests, test 8's count and the scope, and four of mine. One is structural and worth the reviewer's eye: two default-selection modules (`test_plot_extraction_golden.py`, `test_plot_adapters_golden.py`) start a local Ray in the test process and leave it up, so the new modules' "Ray not initialised at the end" check asserts "as it found it" (the note's deviation 22 and observation 1). No issue opened; `OPEN-ISSUES.md` needs no change.
- **Next:** 04 (needs 02 and 03).

**Orchestrator review of prompt 03** (2026-10-25, at `16e1cc1`, by its note
[`orchestrator/prompt-03.md`](orchestrator/prompt-03.md) §3). It passes; one issue is opened.
1. **Scope.** The commit is §0's list: the two `RunDrivers/` files, six test modules and one helper,
   `CLAUDE.md`, the note, the board and `INDEX.md`. The `.py` files changed since `ff3ddd6` are the
   nine new ones. `main.py`, the plot scripts and `utilities.py` are unchanged since `1c223e8`;
   `.claude/rules/` and every existing test are unchanged. `var/` is empty and nothing is pushed.
2. **`CLAUDE.md`.** The one sentence, made definite with the usage line. One line ran past the
   wrap; rewrapped in the residue commit.
3. **The module against ChamPBH's**, by `diff`. `RegisteredStream`, `terminal_state`,
   `SignalLatch`, `make_killed_handler`, `install_killed_handler`, `finish_after_exec` and `main`'s
   body are ChamPBH's but for comments and line references. The differences are §0's: `** `-only
   banners, `>> ` registration lines, the three notify constants and the sentence, no
   `ray_address_problem`, SI's scope (with `defaulted` from configargparse's
   `get_source_to_settings_dict`), the database refusal's reason, and one `!! ` however the text
   begins. The header is whole.
4. **Refusals and seam**, by reading: as ruled; nothing is taken over before `begin` returns.
5. **Registration.** `begin`'s arguments as ruled. `HEARTBEAT_MEANS` says correction 2's things and
   no "every minute".
6. **The run and the finish**, by reading: as ruled; no code reads `main.py`'s text.
7. **By probe** (`orch03/probe7/`): the helper's runner, with `Run.heartbeat` counted, on a stand-in
   of the orchestrator's printing `>> packages:`, a `** STAGE 1` banner, a `>> Opened existing
   sharded datastore` line, 50 progress lines, 20 plain lines and a `>> gradient branch` count, then
   `sys.exit(3)`. Exit 3, `failed`/3, the marker last in stdout and `stdout.log`, the stage the 100 %
   progress sentence under `STAGE 1`. 52 beats: one at registration with no stage, one for the
   banner and one for each progress line; the `>>` and plain lines gave none. The fingerprint of the
   absent store is a `fingerprint_error`, and the record stands. The real script on `-- --database x
   --inventory --ray-address 127.0.0.1:6390`: exit 2, one `!! ` line, the marker, `var/` unchanged.
   `--help` exits 0.
8. **The tests**, by reading: in-process takeovers restored by finalizers registered first; the two
   `Popen` children reaped by a finalizer registered before the first read; the other subprocesses
   time out at 300 s; test 7 by `ast` over the four files; test 8 asserts (4, 2); the fingerprint
   module `integration`, copying the store per test, and nothing else marked.
9. **Breakages.** The six diffs, extracted from the note, each replayed with `git apply` in `bash`
   from the clean tree and the five default-selection modules run. Each failed exactly the tests the
   note names (3, 10, 3, 2, 2 and 2); `git status` clean after each revert.
10. **Records.** The note in §5.1's form, with the 26 deviations classed, the diffs and §2.3 on
    paper. The board's row, items, gate and §5.5, and `INDEX.md`'s line, are in place. The message
    ends with the `Co-Authored-By` line.
11. **Suites**, re-run at `16e1cc1`, serially, load 4–13: default 848 (847 passed, 1 skipped, 141
    deselected), 46 s; `integration` 72 (71 passed, 1 skipped), 68 s; the new files twice more, 106 passed each time (19 s, 18 s). `runregistrykit list`:
    no runs; `var/` empty.
12. **Ray.** After the suites, `ray_cluster.sh status`: lock free, no SI process, the four ports free; no
    Ray process of this venv remains.

**Deviation 22 accepted, and its cause opened.** Two default-selection modules start a local Ray in
the pytest process and leave it up, so the agent's `no_ray_at_the_end` asserts "Ray as it was
found". Confirmed by reading (`test_plot_extraction_golden.py:67-78`, `test_plot_adapters_golden.py:62-71`;
neither is new). Run alone, as in the agent's three runs and the breakage replays, the new modules
start with Ray down and the literal check is made. The cause is not 03's to fix, and it is more
than the agent recorded: with no address, `ray.init()` takes `RAY_ADDRESS` from the environment, so
a default run in a shell that names a cluster attaches to it. Opened as
`[default-suite-starts-ray-in-process]` (§3; `OPEN-ISSUES.md` §6b).

**Residue** (this follow-up commit): "this commit" becomes `16e1cc1` here, in the note and in
`INDEX.md`; the board lists this note; `CLAUDE.md`'s line rewrapped; the issue opened, with
`OPEN-ISSUES.md` at 58 open and `INDEX.md`'s column at §6b, 1. Prompt 03 is left as it ran: its
acceptance 4 (§5.4, now §5.5), its cadence (W3, P7) and its prose item (the rules file) are
corrections 1, 2 and 8 of the note.

**For 04's note.** A `done` homogeneous run's stage will read `Skipping gradient branch (--targets
excludes 'gradient')`, `main.py`'s last `** ` line (the note's observation 3); `build.sh` writes a
second marker (observation 2); and the lock's contract (§5.3).

### 5.6 After prompt 04 (2026-10-25)

- **Landed** in one commit on `rrk-adoption`, `29705f2`. Results:
  [`.documents/rrk-adoption/04-rehearse-registered-runs.md`](../../.documents/rrk-adoption/04-rehearse-registered-runs.md);
  the record, [`.documents/rrk-adoption/verification.md`](../../.documents/rrk-adoption/verification.md) §1,
  with its outputs under `.documents/rrk-adoption/out/04-*`.
- **A stop at the gate, lifted.** At 15:42 the gate found `~/ScienceData` absent, and with it RH2's
  `11-reference`; the agent stopped before anything ran. The user restored it from a backup. The
  orchestrator checked it at 15:59 (the store and its ten shards back, mtime 22 Oct 21:29; its schema
  agrees with RH2's recorded snapshot), and 04 ran from step 1 at 16:00.
- **Gate R holds.** On SI's isolated cluster (`start` 16:05:41 and `stop` about 16:17:30, both exit
  0, under the lock), four builds ran through the wrapper, launched by H0's launcher
  (`.documents/rrk-adoption/rehearsal/build_registered.sh`, which detaches itself):
  - `reference`: `done`/0;
  - `resumed-a`: `killed`/143, after a `SIGTERM` 33 s after the STAGE 2 banner. It fell inside the
    wide window, a narrow miss (all ten `FullInstanton` rows stored), and was recorded, not retuned;
  - `resumed-b`: `SIGKILL`ed 10 s into STAGE 3, then `stale` with `!!`. A launch on its store was
    refused, exit 2, with nothing created. `end` recorded it `lost`, verified;
  - `resumed-c`: `done`/0, computing only the 20 rows missing.

  Every manifest was written before `main.py`'s first line. `results_store_id` is `null`, `null`
  and the resumed store's id twice.
- **The stores and P9.**
  - `compare_stores`: the reference against the resumed store, and the reference against RH2's
    `11-reference`, each `RESULT: equal`, timestamps and timing keys aside.
  - Both `var/` stores fingerprint to `a9f716fb…1ea7`.
  - P9: Ray 2.55.1, attached to the cluster, installs its Python `SIGTERM` handler (the probe), and
    the wrapper's replaces it. The driver exited 143 (RH2's 15), with no absl banner and no alarm
    line. Nothing was left in Ray after the `SIGKILL`.
- **Suites:** before and after, default 848 (847 passed, 1 skipped) and `integration` 72 (71 passed,
  1 skipped), the baselines; `pip freeze` unchanged.
- **Deviations:** 26, classed in the note. They are the brief's 18 corrections, and eight of the
  agent's:
  - the gate's stop, `NOTED`;
  - `--poll 0.2`;
  - the waits and check in one call;
  - three scratch scripts;
  - no prune report, since nothing was unvalidated;
  - three `ALL WORK ITEMS COMPLETE` lines for `resumed-c`;
  - RH2's mtimes listed;
  - and one harmless slip: a command line naming the cluster's temp dir, run after the stop.
- **Observed:** the package's repair of a replicated write in flight ran at both resumes. That
  was the benign case, a `get`, so nothing was repaired. No issue opened; `OPEN-ISSUES.md` needs no
  change.
- **Next:** 05 (needs 04).

**Orchestrator review of prompt 04** (2026-10-25, at `29705f2`, by its note
[`orchestrator/prompt-04.md`](orchestrator/prompt-04.md) §3). It passes; nothing is opened.
1. **Scope.** The commit is correction 2's list: the launcher, the note, `verification.md`, 34 files
   under `out/04-*` (308 KB, none over 55 KB), the board and `INDEX.md`'s line. No `.py` file changed
   since `edb03ea`; `main.py`, the plot scripts and `utilities.py` are unchanged since `1c223e8`;
   nothing under `var/` is committed. The tree is clean and nothing is pushed.
2. **The venv.** `pip freeze` equals the one taken at dispatch.
3. **The cluster.** `ray_cluster.sh status`, exit 0: lock free, no SI process, the four ports free;
   no `raylet`, `gcs_server` or `ray::` process on the machine.
4. **The runs, from the registry.** `list` shows the four: `reference` `done`, `resumed-a` `killed`,
   `resumed-b` `lost`, `resumed-c` `done`. Each run directory's `manifest.json` and `status.json` is
   byte-identical to its copy under `out/`. In each: `script` `main.py` with its SHA-256
   `07fbf19a…3744`; `results` the store, relative; `git_head` `535b7e7`, `git_dirty` true
   (correction 17); 03's scope with each job name; `heartbeat_means` as 03 wrote it;
   `results_store_id` `null`, `null`, `b7904d18…` and `b7904d18…` (correction 13). `resumed-b`'s
   `ended` is verified, `pid_answers` false, with its reason.
5. **The order.** Each launch log opens with the three `>> registered_run` lines, then
   `>> packages:`; each log was born at or before its manifest's `created` (`/usr/bin/stat`).
6. **H2's signal.** `sent SIGTERM` at 16:12:33 UTC; the handler's line at 16:12:33 `+0000`; the
   final record's heartbeat 16:12:38: 0 s and 5 s, ±1 s. Then `** driver exit status 143` and the
   launcher's 143. No absl banner and no alarm line in the log (`grep -c` 0).
7. **H3's route.** The launcher's 137 and no driver marker; the `stale` line and its summary; the
   refused launch's one `!! ` line, its marker 2 and the empty `find var/runs` diff; `end`'s line;
   the `lost` record. Correction 11's fourth snapshot, 20 s after the kill: the baseline's pids, no
   live worker, no `ALIVE` actor.
8. **The delays**, from the reference's rows re-read `mode=ro` here: `FullInstanton` rows at
   +32.2 to +42.6 s after the `STAGE 2` banner (16:07:55.5), so 33 s falls between the second and
   third rows; `SlowRollInstanton` rows from +21.0 s after the `STAGE 3` banner, so 10 s (under half
   of 23 s) stores none at the reference's pace. `stage_counts.py` on the four logs equals `out/`'s:
   `resumed-b` and `resumed-c` find 10 `FullInstanton` rows already computed, and `resumed-c`
   computes the 20 missing rows.
9. **The stores, re-measured.** `compare_stores.py`: reference against resumed, `RESULT: equal`;
   reference against RH2's `11-reference`, `RESULT: equal`, RH2's files' mtimes and sizes unchanged
   and no journal beside them. `store fingerprint` on each `var/` store: `a9f716fb…1ea7`, each
   matching its sidecar. `store show`: the runs as logged.
10. **The launcher**, by reading: correction 7's requirements hold; `bash -n` passes; no line names
    `/tmp/ray-si`.
11. **The records.** The board's header, row, items, gate and §5.6; the note in §5.1's form with its
    26 deviations classed and the commands verbatim; `verification.md` §1's table and heartbeat ages
    match `out/`, and it claims no history of beats. `INDEX.md`'s line. `OPEN-ISSUES.md` untouched,
    rightly. The message ends with the `Co-Authored-By` line.
12. **The suites** at `29705f2`, serially, with no cluster up and `RAY_ADDRESS` unset, load 4–24:
    default 848 (847 passed, 1 skipped, 141 deselected), 44 s; `integration` 72 (71 passed, 1
    skipped), 70 s. `runregistrykit list` afterwards: 4 runs, 4 finished.

**The stop at the gate.** `~/ScienceData` had been removed, since nothing was meant to live there
once RayPoolKit `v0.3.0` moved the lock out of it, and RH2's stores went with it; prompt 04, written
on 2026-10-23, still named them there. The
user restored the directory from a backup, and 04 ran unchanged (deviation 19). The old lock
location `~/ScienceData/.rehearsal-lock` was not restored, so `start` had no reason to refuse.

**Observations, not acted on.**
- Both signals landed during a replicated `efold_value` `get`, so DatastoreKit's repair of a
  replicated write in flight ran at both resumes, in its benign case (nothing to repair). RH2 never
  reached that path.
- `end` stamps the lost status's `heartbeat` with its own time; the last real beat survives only in
  `ended.evidence.heartbeat`. It is RunRegistryKit's documented behaviour (every status write stamps
  the heartbeat), recorded in `verification.md` §1.4.
- `resumed-a`'s recorded purpose says "in STAGE 2"; its signal landed 1.5 s into `STAGE 3`. The
  record is left as written.

**Residue** (this follow-up commit): "this commit" becomes `29705f2` here, in the note and in
`INDEX.md`; the board lists this note. Prompt 04 is left as it ran: its board section (§5.5, now
§5.6), its file list (the board and `INDEX.md`), its 134 (RH2's 15) and its `Monitor` (a waiter
that reads the log) are corrections 1, 2, 3 and 6 of the note.

### 5.7 After prompt 05 (2026-10-25)

- **Landed** in one commit on `rrk-adoption`, this commit. Results:
  [`.documents/rrk-adoption/05-close.md`](../../.documents/rrk-adoption/05-close.md); the drafts and the
  handover, [`.documents/rrk-adoption/verification.md`](../../.documents/rrk-adoption/verification.md) §2
  and §3.
- **The campaign is complete.** Z1–Z5 are done and no §3 issue is closed or opened by 05.
  - **Z1.** `INFRASTRUCTURE.md` holds the dated note, as a new §13 and its title; `architecture-summary.md`
    and `FILE_MAP.md` gain the entries of the run registry and point at it. Every dated note of the
    three documents is kept byte for byte.
  - **Z2.** `CLAUDE.md` and `.claude/rules/test-selection.md` carry the counts below; no sentence of the
    registry section or of `run-registry.md` was found wrong. No file became `slow`.
  - **Z3.** The three stale sentences are present tense, and `utilities.py`'s docstring has the one
    sentence of the prompt; both `.py` files are `ast`-equal without docstrings.
  - **Z4.** RunRegistryKit's `extraction` `G4` and `interrupted-runs` `G3` are drafted (§2.1, §2.2); the
    handover is §3.
  - **Z5.** This board, `.prompts/INDEX.md` and `.documents/OPEN-ISSUES.md` (58 open, unchanged).
- **Suites** before and after 05's edits, serially: default 848 (847 passed, 1 skipped, 141 deselected) and
  `integration` 72 (71 passed, 1 skipped), the baselines of 04's close. Collection: 848 + 72 + 69 = 989,
  disjoint.

**What is left to the user.**
- **The merge of `rrk-adoption` into `main`** (R7). Nothing is pushed.
- **The two gate records**, in RunRegistryKit (`prompts/extraction/IMPLEMENTATION_STATE.md` §2, row `G4`;
  `prompts/interrupted-runs/IMPLEMENTATION_STATE.md` §2, row `G3`), from `verification.md` §2.1 and §2.2.
- **04's stores, runs and launch logs** under `var/`, which stay until the user removes them.
- **The observation of README §7** on the wrapper's generic part (the stream proxies, the stage tracker,
  the signal latch and the finish after the program unwinds), which could be a module of RunRegistryKit
  with each client supplying its parser, scope and stage patterns: whether to raise it there is the
  user's.
- **`end` stamps `heartbeat`.** RunRegistryKit's `end` stamps the lost status's `heartbeat` with its own
  time, keeping the last real beat in `ended.evidence.heartbeat` (04's observation 3, documented
  behaviour of the package); the user may raise it there.
