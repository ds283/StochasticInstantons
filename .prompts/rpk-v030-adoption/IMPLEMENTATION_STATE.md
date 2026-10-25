# rpk-v030-adoption campaign — implementation state

**Last updated:** 2026-10-25 · **Status: READY — 01 written, not dispatched.** No ruling is needed
(README §6.1); C1–C10 stand as proposed (README §6.2). The branch `rpk-v030-adoption` is cut from
`main` at `1c223e8` (C1).
The plan is [`README.md`](README.md), written on 2026-10-25 at `7071bb8` from RayPoolKit's `v0.3.0`
contract and its switch-over checklist for this repository.

The campaign moves `raypoolkit` from `v0.2.0` to `v0.3.0` and replaces the lock half of SI's
`ray_cluster.sh` with the package's `raypoolkit.rehearsal_lock`. The lock moves to
`~/.raypoolkit/rehearsal-lock`. SGK moved alone on 2026-10-25 (its U2), so until 01 lands SI's
cluster is started only after checking by hand that the new lock does not exist (README §0.2).

**Campaign:** [`README.md`](README.md) ·
**Checklist:** RayPoolKit's `docs/adoption/rehearsal-lock/stochasticinstantons.md` and
`switch-over.md` (read, never edited) ·
**Code:** `requirements.txt`, `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`,
`CLAUDE.md`, `.documents/INFRASTRUCTURE.md` ·
**Results:** `.documents/rpk-v030-adoption/` (created by 01) ·
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
| 01 | [`01-switch-to-the-raypoolkit-rehearsal-lock.md`](01-switch-to-the-raypoolkit-rehearsal-lock.md) | Opus | written |

The review of 01 closes the campaign; the merges of README §4 follow at the user's instruction.

### 1.1 Items

| Item | Prompt | What | Status |
|---|---|---|---|
| **P1** | 01 | `requirements.txt:59` at `v0.3.0`, in a commit of its own; the venv installed from it | — |
| **S1** | 01 | `ray_cluster.sh`: the lock half removed | — |
| **S2** | 01 | `cmd_start`: `acquire`, `set-pid`, `release` on every failure path; the stale-cluster check dropped (C3) | — |
| **S3** | 01 | `cmd_stop`: the owner check at `default_lock_dir()` (C4), `stop_cluster`, `release` | — |
| **S4** | 01 | `cmd_status` (C5), the header and the usage | — |
| **D1** | 01 | `CLAUDE.md` (the pin; the lock's sentence) and `.documents/INFRASTRUCTURE.md` | — |
| **V1** | 01 | the scratch-`HOME` checks S-1 to S-6, and the breakages B1–B4 | — |
| **V2** | 01 | the live check under the real lock | — |
| **G1** | 01 | the draft of SI's part of RayPoolKit's G2 record (C9) | — |

## 2. The gates

| Gate | Holds when | Status |
|---|---|---|
| **Switch** | 01's acceptance: `raypoolkit` 0.3.0 installed from the tag, not editable; the checklist's item 8 holds (0 live lines name the old lock; the script calls the module); the scratch and live checks as planned; the suites unchanged | not yet |
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
