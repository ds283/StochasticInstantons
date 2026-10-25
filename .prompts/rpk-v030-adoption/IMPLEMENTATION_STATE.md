# rpk-v030-adoption campaign — implementation state

**Last updated:** 2026-10-25 · **Status: LIVE — 01 landed, awaiting review.** The pin is
`3d6328e`, the switch the commit after it; the gate **Switch** holds. No ruling is needed
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
`CLAUDE.md`, `.documents/INFRASTRUCTURE.md` ·
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
| 01 | [`01-switch-to-the-raypoolkit-rehearsal-lock.md`](01-switch-to-the-raypoolkit-rehearsal-lock.md) | Opus | **landed** 2026-10-25 (`3d6328e`, the pin; then the switch), awaiting review. Results: [`01-switch-to-the-raypoolkit-rehearsal-lock.md`](../../.documents/rpk-v030-adoption/01-switch-to-the-raypoolkit-rehearsal-lock.md) |

The review of 01 closes the campaign; the merges of README §4 follow at the user's instruction.

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
| **Switch** | 01's acceptance: `raypoolkit` 0.3.0 installed from the tag, not editable; the checklist's item 8 holds (0 live lines name the old lock; the script calls the module); the scratch and live checks as planned; the suites unchanged | **holds** at 01 (2026-10-25), subject to its review |
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
  Then this commit: `ray_cluster.sh`, `CLAUDE.md`, `.documents/INFRASTRUCTURE.md`,
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
