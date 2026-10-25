# rpk-v030-adoption campaign — implementation state

**Last updated:** 2026-10-25 · **Status: CLOSED — 1 of 1 landed and reviewed (§5.2).** The pin
is `3d6328e`, the switch `6c60b81`; the gate **Switch** holds. The merges of README §4 wait on the
user's instruction. No ruling is needed
(README §6.1); C1–C10 stand as proposed (README §6.2). The branch `rpk-v030-adoption` is cut from
`main` at `1c223e8` (C1).
The plan is [`README.md`](README.md), written on 2026-10-25 at `7071bb8` from RayPoolKit's `v0.3.0`
contract and its switch-over checklist for this repository.

The campaign moves `raypoolkit` from `v0.2.0` to `v0.3.0` and replaces the lock half of SI's
`ray_cluster.sh` with the package's `raypoolkit.rehearsal_lock`. The lock moves to
`~/.raypoolkit/rehearsal-lock`. SGK moved alone on 2026-10-25 (its U2). With 01 landed, SI's
`ray_cluster.sh start` takes the package's lock, so README §0.2's check by hand is no longer
needed on this branch; it still applies to a checkout of `main` or `rrk-adoption` until README §4's
merges.

**Campaign:** [`README.md`](README.md) ·
**Checklist:** RayPoolKit's `docs/adoption/rehearsal-lock/stochasticinstantons.md` and
`switch-over.md` (read, never edited) ·
**Code:** `requirements.txt`, `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`,
`CLAUDE.md`, `.documents/INFRASTRUCTURE.md`, `.documents/architecture-summary.md` ·
**Results:** [`.documents/rpk-v030-adoption/`](../../.documents/rpk-v030-adoption/) ·
**Index:** [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) (no section yet: no issue
opened)

> **Maintenance rule.** Whenever an entry is added to, narrowed in, or closed out of §3 or §4
> below, [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) is updated **in the same
> commit**: the row is added, moved or deleted, and the count and date in its header are
> corrected. See `CLAUDE.md`.

### Decisions

**Ruled by the user:** none needed here. In SGK's `rpk-v030-adoption` (its U2, 2026-10-25): SGK
moves alone, and the user moves ChamPBH and SI when they can. **Instructed 2026-10-25, with the
planning commit:** 01 is not dispatched until the user says so. The projects migrate to `v0.3.0`
serially, so that only one uses Ray at a time.

**Proposed by the planner (README §6.2):** C1–C10, standing unless the user rules otherwise.

| Choice | What |
|---|---|
| **C1** — the branch | `rpk-v030-adoption` from `main`; after review, `main` fast-forwarded to it, then `main` merged into `rrk-adoption` before that campaign's 02 (README §4) |
| **C2** — the script's place | edited in place, under `.documents/dk-and-rpk-migration/rehearsal/` |
| **C3** — the stale-cluster check | dropped: `acquire`'s exit 4 covers it |
| **C4** — `stop`'s owner check | kept, reading the owner file at `default_lock_dir()` |
| **C5** — `status` | the module's listing and the script's own, then the ports |
| **C6** — commits | the pin alone, then the rest |
| **C7** — verification | the script against a scratch `HOME`; one start and stop under the real lock; no build |
| **C8** — citations "at `v0.2.0`" | left: `RayWorkPool.py` is unchanged |
| **C9** — RayPoolKit's G2 | SI's part drafted by 01, recorded by the user; the cross-check once ChamPBH has switched |
| **C10** — issues | none opened at planning |

---

## 1. Prompts

| # | Prompt | Model | Status |
|---|---|---|---|
| 01 | [`01-switch-to-the-raypoolkit-rehearsal-lock.md`](01-switch-to-the-raypoolkit-rehearsal-lock.md) | Opus | **landed** 2026-10-25 (`3d6328e`, the pin; then the switch, `6c60b81`); reviewed 2026-10-25 (§5.2). Results: [`01-switch-to-the-raypoolkit-rehearsal-lock.md`](../../.documents/rpk-v030-adoption/01-switch-to-the-raypoolkit-rehearsal-lock.md) |

The review of 01 closes the campaign; the merges of README §4 follow at the user's instruction.

**Orchestrator notes** (`orchestrator/`), written before each dispatch:
- [`prompt-01.md`](orchestrator/prompt-01.md) — used for 01 (`0f190c8`).

### 1.1 Items

| Item | Prompt | What | Status |
|---|---|---|---|
| **P1** | 01 | `requirements.txt:59` at `v0.3.0`, in a commit of its own; the venv installed from it | done: `3d6328e`; `raypoolkit` 0.3.0 at `67a75b9`, not editable; the freeze moved by that line alone |
| **S1** | 01 | `ray_cluster.sh`: the lock half removed | done: the lock functions and variables gone; `owner_field` and `print_owner` kept for C4 |
| **S2** | 01 | `cmd_start`: `acquire`, `set-pid`, `release` on every failure path; the stale-cluster check dropped (C3) | done: `acquire` passed through; `set-pid` with the `gcs_server`'s pid; `release_after_failure` on every failure path and the trap |
| **S3** | 01 | `cmd_stop`: the owner check at `default_lock_dir()` (C4), `stop_cluster`, `release` | done: the owner file read at `default_lock_dir()` before `stop_cluster`; then the module's `release` |
| **S4** | 01 | `cmd_status` (C5), the header and the usage | done: the module's `status`, the script's listing, the ports; header and usage |
| **D1** | 01 | `CLAUDE.md` (the pin; the lock's sentence) and `.documents/INFRASTRUCTURE.md` | done: `CLAUDE.md` (two places), `INFRASTRUCTURE.md:41-44` and `:458`, `architecture-summary.md:344` (briefing correction 2) |
| **V1** | 01 | the scratch-`HOME` checks S-1 to S-6, and the breakages B1–B4 | done: S-1 to S-6 as planned, none reaching `ray start`; B1–B4 each caught |
| **V2** | 01 | the live check under the real lock | done: the nine steps as planned (start 0, second start 3, `release` 1 while up, stop 0, then free) |
| **G1** | 01 | the draft of SI's part of RayPoolKit's G2 record (C9) | drafted: the results note's last section, for the user to record in RayPoolKit |

## 2. The gates

| Gate | Holds when | Status |
|---|---|---|
| **Switch** | 01's acceptance: `raypoolkit` 0.3.0 installed from the tag, not editable; the checklist's item 8 holds (0 live lines name the old lock; the script calls the module); the scratch and live checks as planned; the suites unchanged | **holds** at 01 (2026-10-25), confirmed by its review (§5.2) |
| RayPoolKit `rehearsal-lock` **G2** | all three clients switched and `switch-over.md` §3's cross-check passed; SI's part drafted by 01, recorded in RayPoolKit by the user (C9) | not yet |

## 3. Active and unresolved issues

None.

### 3.1 Assigned to this campaign

None (C10).

## 4. Resolved issues

None.

## 5. Dispatch record

### 5.0 Planning (2026-10-25)

- **Evaluation.** At the user's request, RayPoolKit `v0.3.0` was evaluated for SI at `7071bb8`, on
  `rrk-adoption`. Its findings are README §0.3: `RayWorkPool` is unchanged; RayPoolKit's checklist
  for SI, measured at `7071bb8`, is true of the tree line for line; SI's change is the pin and the
  lock half of `ray_cluster.sh`, with no Python file and no test touched. SGK was found moving alone
  the same day, at the user's ruling (README §0.2). Nothing in SI's tree or venv was changed.
- **The branch (C1).** `rpk-v030-adoption` was cut from `main` at `1c223e8`; this planning commit is
  its first. `rrk-adoption` (01 of 5 landed) is untouched.
- **Plan and prompt 01** written: README §0–§7, this board, 01, and the campaign's line in
  `.prompts/INDEX.md`. No issue opened.
- **The user's instruction.** Commit the plan, dispatch nothing: the other projects are migrating
  to `v0.3.0`, and the user runs the migrations serially, one project using Ray at a time.
- **Next:** 01, when the user dispatches it.

### 5.1 After prompt 01 (2026-10-25)

- **Dispatched** by the orchestrator on 2026-10-25, at `0f190c8`, with a briefing whose five
  corrections the results note records as deviations 1–5.
- **Commits.** The pin, `3d6328e1694a6878e69d2d8437502bf41c402b4a`: `requirements.txt:59` alone.
  Then `6c60b81`: `ray_cluster.sh`, `CLAUDE.md`, `.documents/INFRASTRUCTURE.md`,
  `.documents/architecture-summary.md`, the results note and `out/`, this board and
  `.prompts/INDEX.md`. Nothing pushed.
- **Results:** [`01-switch-to-the-raypoolkit-rehearsal-lock.md`](../../.documents/rpk-v030-adoption/01-switch-to-the-raypoolkit-rehearsal-lock.md).
  The venv holds `raypoolkit` 0.3.0 at `67a75b9`, not editable, nothing else moved. Acceptance 2's
  grep 5 → 0; the script calls the module 7 times and names `.raypoolkit` only in its usage text.
  S-1 to S-6 as planned, none reaching `ray start`. The live check: start 0 (the `gcs_server`'s
  pid recorded), second start 3, `release` 1 while up, a driver connected (`CPU` 4.0), stop 0, then
  the lock free and nothing of `/tmp/ray-si` left. B1–B4 each caught. The suites 732 (731 passed,
  1 skipped) and 67 (66 passed, 1 skipped) before and after; no `.py` file changed.
- **Deviations:** ten, classified in the results note: two `STRUCTURALLY REQUIRED` (the Gate's
  `runregistrykit list`; two more pin statements), three `IMPLEMENTATION CHOICE`, four `NOTED`,
  and one `UNINTENDED DRIFT` (S-5's set-up command named `/tmp/ray-si` in the text it wrote; it ran
  alone, in the foreground, under the scratch `HOME`).
- **Issues:** none opened.
- **G1:** SI's part of RayPoolKit's G2 record drafted at the end of the results note, for the user
  to record in RayPoolKit. The cross-check of `switch-over.md` §3 is owed once ChamPBH has switched.
- **Next:** the review of 01, which closes the campaign; then README §4's merges, at the user's
  instruction.

### 5.2 Review and close (2026-10-25)

The orchestrator's review of 01 (`3d6328e`, `6c60b81`), by the nine checks of
[`orchestrator/prompt-01.md`](orchestrator/prompt-01.md) §3. Every check passed.
1. **Scope.** `3d6328e` is `requirements.txt` alone, the one line. `6c60b81`'s 13 paths are
   acceptance 8's list with `architecture-summary.md` (the note's correction 2) and
   `out/01-gate.txt` (deviation 6). No `.py` file changed since `8baac35`; no
   `runregistrykit.toml`; nothing pushed; both messages end with the `Co-Authored-By` line.
2. **The venv**, measured here. `pip freeze` differs from the dispatch freeze by the `raypoolkit`
   line alone, now `@67a75b97…`, 84 lines; `direct_url.json` is a VCS record (`v0.3.0`, no
   `dir_info`); `pip check` clean; a dry run of `requirements.txt` installs nothing. `01-pip.txt`
   records the dry run before the install, `Would install raypoolkit-0.3.0` alone.
3. **The script**, read whole. The cluster half, from "the targeted stop" to "commands", is
   byte-identical to `8baac35`'s, and so is the `ray start` line. Every module call goes through
   `rehearsal_lock` with `$LOCK_PROJECT`, `$SI_TEMP_DIR` and `$SI_ADDRESS`. `start`: `acquire …
   || return $?`, the stale-cluster check gone (C3), `release_after_failure` on the held port, the
   failed `ray start`, no `gcs_server`, a refused `set-pid` and the trap, with returns 4, 1, 1, 1,
   130 and the refusal printed. `stop`: the owner file read at `default_lock_dir()` before
   `stop_cluster`, an empty or missing owner treated as not SI's (C4). `status`: the module's, then
   the script's listing under its own heading, then the ports (C5). `bash -n` passes. Acceptance
   2's grep **0**; acceptance 3's: 7 calls, `.raypoolkit` at `:54` only, in the usage text.
4. **The scratch checks, re-run here** against a scratch `HOME` of the orchestrator's, each
   command a shell command of its own: S-1 0 free; S-2 0, `no lock to release`; S-3 `acquire` 0
   then `stop` 0, `released the rehearsal lock`; S-5 `start` 3 naming the old location, nothing
   created, then `status` `old location: PRESENT`. S-5's decoy owner file named
   `/tmp/ray-decoy`, not SI's temp dir. S-4 and S-6 read from `01-scratch.txt`, as planned.
5. **The live check**, from `01-live.txt`. Step 1 free; `start` 0, `recorded pid 17315`; `status`
   HELD with SI's values and `pid: 17315`, alive, 18 processes by each rule (the `gcs_server`, the
   client server 17317, the `raylet`); `ray-processes` 1; the driver `CPU` 4.0; the second `start`
   3; `release` 1, `the recorded pid 17315 is alive`; `stop` 0 after SIGKILL to two survivors of
   the grace period, `released the rehearsal lock`; `status` free, none, ports free;
   `ray-processes` 0. Here: neither lock location exists, and no `gcs_server` or `raylet` runs.
   The live check ran on the working tree before `6c60b81`; the agent's clean copy of the script,
   taken a minute after it for the breakages, is blob `74c3c73`, the committed one.
6. **The breakages**, extracted here from `01-breakage.txt` and replayed in `bash` from the clean
   tree at `6c60b81`: each `git apply --check` 0 and `-R --check` 1. B1 under a ChamPBH scratch
   lock: `stop_cluster`'s two lines, then `release` refused, exit 1. B2 under SI's scratch lock:
   `stop` 1, the lock left held, released by hand. B3: acceptance 3's grep gains `:332`, a line of
   code. B4: acceptance 2's grep finds `:54`. Each reverted; the tree clean.
7. **The documents.** `CLAUDE.md`: the pin at `v0.3.0`; one sentence naming the module, its
   location, the other two projects, the contract and exit 3 (the old location described, not
   spelled); the `ray stop` sentence kept. `INFRASTRUCTURE.md:41-44` and `:458`,
   `architecture-summary.md:344` as the prompt and the note say.
8. **The suites, re-run here** at `6c60b81`: default 732 (731 passed, 1 skipped) in 32 s;
   integration 67 (66 passed, 1 skipped) in 51 s, load 9–51. The orchestrator's baselines at
   `8baac35` were the same.
9. **The records.** The results note has every section of `dk-and-rpk-migration` README §5.1's
   template, the counts, ten classified deviations (the note's five among them) and the G2 draft.
   The board and `INDEX.md` as prompt §6. No issue opened.

**Remarks, neither a defect in the work.**
- **Deviation 7**, S-5's set-up `printf` naming `/tmp/ray-si` in the scratch owner file, broke the
  rule of the note's §0 in a command that ran alone, in the foreground, and listed nothing. The
  review's own S-5 used a decoy value.
- `INFRASTRUCTURE.md:46` still says the section "points at those two documents", where the lock's
  contract is now a third (the results note's observation). Left: the documents are the two
  packages' and the contract is one of RayPoolKit's.

**Residue, fixed in `ea17836`:**
- `6c60b81` for "this commit" and "the commit after it" in the results note, its G2 draft and this
  board; `architecture-summary.md` on the board's Code line; the orchestrator's note listed;
- README §0.3 corrected, dated: the two further pin statements, and `runregistrykit list`
  measured on `rrk-adoption`;
- `CLAUDE.md`'s lock sentence now also says why no `PURPOSE` names `/tmp/ray-si`, and that a lock
  command typed by hand is the only process of its shell command, redirected, never piped (the
  note's §0, and SGK's `CLAUDE.md` after `a04ef11`).

**Handed on.**
- **README §4's merges**, at the user's instruction: `main` fast-forwarded to this branch, then
  `main` merged into `rrk-adoption` before its 02 (two expected conflicts, `requirements.txt` and
  `.prompts/INDEX.md`). Until then, a checkout of `main` or `rrk-adoption` still runs the old
  script, and README §0.2's check by hand applies there.
- **G2:** the draft at the end of the results note is the user's to record in RayPoolKit. With
  SI's switch, all three clients are on the package's lock: ChamPBH had already switched (its
  `95ad91d`, "Switch the cluster script to the raypoolkit v0.3.0 rehearsal lock", pinning
  `v0.3.0`), so the cross-check of `switch-over.md` §3 is owed now. *Corrected 2026-10-25 at the
  user's word: the review first said ChamPBH still took the old location.*

**The campaign is closed.** No issue was opened, so `.documents/OPEN-ISSUES.md` is unchanged.
