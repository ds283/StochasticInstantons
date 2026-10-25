# rrk-adoption campaign — implementation state

**Last updated:** 2026-10-25 · **Status: READY — 2 of 5 prompts landed; 01–05 written (§5.1); `main` merged in
with `rpk-v030-adoption` (§5.3). R1–R7,
U1 and U2 ruled by the user; P1–P14 stand as proposed (README §6). The branch `rrk-adoption` is cut
from `main` at `1c223e8`, after `dk-and-rpk-migration` was merged into `main` (R7).**
The plan is [`README.md`](README.md), written on 2026-10-23 at `8b4f615`. Prompts 01–05 were written
once the user had ruled (README §2.1).

The campaign adopts `runregistrykit[stores]` `v0.2.0`: the pin, the config, the rules and a
discovery hook, a fingerprinter at format 1 with its guard, a wrapper driver that registers
`main.py` runs without changing `main.py`, and a rehearsal of registered, interrupted and
hard-killed builds. Its RunRegistryKit gates are drafted for that repository when they hold (P13).

**Campaign:** [`README.md`](README.md) ·
**Checklist:** RunRegistryKit's `docs/adoption/stochasticinstantons.md` and
`docs/adoption/v0.2.0/stochasticinstantons.md` (read, never edited) ·
**Code:** `requirements.txt`, `runregistrykit.toml`, `.gitignore`, `.claude/settings.json`,
`config/fingerprint.py`, `RunDrivers/`, `tests/`, `CLAUDE.md`, `.claude/rules/run-registry.md` ·
**Results:** `.documents/rrk-adoption/` (results notes; `verification.md`, created by 04) ·
**Index:** [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) (no section yet: no issue
opened)

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
| 01 | [`01-pin-config-and-rules.md`](01-pin-config-and-rules.md) | Sonnet | **landed** 2026-10-23 (`60687f0` and this commit) |
| 02 | [`02-the-fingerprinter.md`](02-the-fingerprinter.md) | Sonnet | **landed** 2026-10-25 (this commit) |
| 03 | [`03-the-wrapper.md`](03-the-wrapper.md) | Opus | written |
| 04 | [`04-rehearse-registered-runs.md`](04-rehearse-registered-runs.md) | Opus | written |
| 05 | [`05-close.md`](05-close.md) | Sonnet | written |

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
| **W1** | 03 | `RunDrivers/registered_run.py` | — |
| **W2** | 03 | its arguments and refusals | — |
| **W3** | 03 | registration, the streams and the heartbeat (P7) | — |
| **W4** | 03 | Ray and the signals (P9) | — |
| **W5** | 03 | running `main.py`, finishing with the fingerprint, the exit marker | — |
| **W6** | 03 | `tests/test_registered_run*.py` | — |
| **H0** | 04 | the launcher `build_registered.sh` (P8) | — |
| **H1**–**H4** | 04 | `reference`; `resumed-a` (`SIGTERM`); `resumed-b` (`SIGKILL`, `end`); `resumed-c` | — |
| **H5** | 04 | the stores compared, with each other and with RH2's `11-reference` (P10) | — |
| **H6** | 04 | `.documents/rrk-adoption/verification.md` §1 | — |
| **Z1** | 05 | the descriptive documents | — |
| **Z2** | 05 | `CLAUDE.md`, the rules, the test counts | — |
| **Z3** | 05 | the stale prose (P12), `utilities.py`'s docstring among it | — |
| **Z4** | 05 | RunRegistryKit's G4 and G3 drafted; the handover to Phase 2 | — |
| **Z5** | 05 | the board closed; the indexes | — |

## 2. The gates

| Gate | Holds when | Status |
|---|---|---|
| **Pin** | 01's acceptance: `runregistrykit` 0.2.0 installed from the tag, not editable; the package's suite passes on it; the config, `var/`, the rules and the hook in place | **held** 2026-10-23 |
| **Fingerprint** | 02's acceptance: `SPEC_DIGESTS[1]` pinned and guarded; the golden fingerprint reproduced | **held** 2026-10-25 |
| **Wrapper** | 03's acceptance: the wrapper's tests pass; `main.py` unchanged and importing nothing of the package | not yet |
| **R** | 04's acceptance: the four registered builds recorded as planned; the resumed store and RH2's reference equal to `reference` | not yet |
| RunRegistryKit `extraction` **G4**, `interrupted-runs` **G3** | drafted by 05, committed in RunRegistryKit by the user (P13) | not yet |

## 3. Active and unresolved issues

None.

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

- **Landed** in two commits on `rrk-adoption`: the pin alone, `60687f064a2a706bb39ea6c69fe8f4ace78375a8`, then this commit (config, ignore rule, rules, hook, test, results note). Results: [`.documents/rrk-adoption/01-pin-config-and-rules.md`](../../.documents/rrk-adoption/01-pin-config-and-rules.md).
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

- **Landed** in one commit on `rrk-adoption`, this commit. Results: [`.documents/rrk-adoption/02-the-fingerprinter.md`](../../.documents/rrk-adoption/02-the-fingerprinter.md).
- **Gate Fingerprint holds.** `SPEC_DIGESTS[1]` pins 24 pairs (18 distinct); the guard names the class that changes. The golden file `tests/data/store_fingerprint_rrk-adoption-02.json` (SHA-256 `3ed2303e…0fa9`, digest `e3437a9b2f16415f5635ee121fa7f09d07ac74c30400d5973a3afaeec8fc7c78`) was written once, after two builds in two processes gave the same file and the digest the orchestrator had measured. `store fingerprint` on the store exits 0, ending `recorded: none recorded (the sidecar is absent)`.
- **Suites:** default 743 (742 passed, 1 skipped); `integration` 70 (69 passed, 1 skipped).
- **Deviations:** the addendum is read at RunRegistryKit `main`, not the tag; this section is 5.4 not 5.3; the import list is stated as measured (10 modules, none of `ray`, `sqlalchemy`, `datastorekit`); 24 pairs (classes), 18 distinct; `take` returns a pair; the command line exits 0; B5 changes `log10_tol` in `test_inventory_store.py` (which still passes); `TestGolden` asserts the three empty classes of the harness's store. No issue opened; `OPEN-ISSUES.md` needs no change.
- **Next:** 03 (needs only 01); 04 needs 02 and 03.
