# ray-sqla-align campaign — implementation state

**Last updated:** 2026-10-25 · **Status: READY — 0 of 1 landed.** Planned and ruled the same day
(U1–U4); prompt 01 written. **01 is dispatched when the user says so** (C12): it takes the shared
lock, and the projects use Ray one at a time.
The plan is [`README.md`](README.md), written on 2026-10-25 at `03110ce`.

The campaign moves SI's `ray` from 2.55.1 to 2.59.0 and `SQLAlchemy` from 2.0.46 to 2.0.55,
SecondaryGWKit's versions since its `py313-venv` campaign. Every other pin stays. Because Ray 2.59
turns token authentication on for `ray start --head` when `~/.ray/auth_token` exists, but never for
a driver attaching by address, the move alone would leave every driver refused by SI's rehearsal
cluster (README §0.2). So every Ray start names token mode, as SGK's do. The rehearsal fingerprint
must stay `a9f716fb…1ea7`.

**Campaign:** [`README.md`](README.md) ·
**Code:** `requirements.txt`, `config/ray_auth.py` (new), `main.py`, `plot_InstantonSolutions.py`,
`plot_GradientCoupledSolutions.py`, `tests/conftest.py`, `tests/test_ray_auth.py` (new),
`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`, `CLAUDE.md`,
`.claude/rules/test-selection.md` ·
**Results:** `.documents/ray-sqla-align/` (created by 01) ·
**Index:** [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) (no section yet: no issue
opened)

> **Maintenance rule.** Whenever an entry is added to, narrowed in, or closed out of §3 or §4
> below, [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) is updated **in the same
> commit**: the row is added, moved or deleted, and the count and date in its header are
> corrected. See `CLAUDE.md`.

### Decisions

**Ruled by the user, 2026-10-25 (README §6.1):**

| Decision | Ruled |
|---|---|
| **U1** — versions | `ray` 2.59.0 and `SQLAlchemy` 2.0.55, SGK's; every other pin unchanged |
| **U2** — token authentication | kept, and named (`RAY_AUTH_MODE=token`), as SGK does |
| **U3** — the shape | a campaign with this board and one prompt |
| **U4** — recorded distributions | unchanged; no change to the protected `utilities.py` |

**Proposed by the planner (README §6.2):** C1–C12, standing unless the user rules otherwise.

| Choice | What |
|---|---|
| **C1** — where | on `main`, no branch: one venv, nothing else in flight |
| **C2** — the venv | upgraded in place; the freeze before saved |
| **C3** — the module | `config/ray_auth.py`: SGK's token half, with the config refresh |
| **C4** — its importers | the three drivers and `tests/conftest.py`; the tests' subprocesses inherit it |
| **C5** — the cluster | `ray_cluster.sh` exports `RAY_AUTH_MODE` (default `token`) before `ray start` |
| **C6** — commits | the pins; the fix; the records |
| **C7** — V0 | the refusal measured on the pins alone, before the fix |
| **C8** — the rehearsal | `rrk-adoption` 04's H1, H2 (`SIGTERM`) and H4; no `SIGKILL` |
| **C9** — the launcher | 04's, copied with its names changed |
| **C10** — outputs | under `var/ray-sqla-align-01/` while 01 works; copied for the last commit |
| **C11** — issues | none opened at planning |
| **C12** — dispatch | at the user's word |

---

## 1. Prompts

| # | Prompt | Model | Status |
|---|---|---|---|
| 01 | [`01-move-ray-and-sqlalchemy-with-token-mode.md`](01-move-ray-and-sqlalchemy-with-token-mode.md) | Opus | ✍️ written 2026-10-25; not dispatched |

The review of 01 closes the campaign.

**Orchestrator notes** (`orchestrator/`), written before each dispatch: none yet.

### 1.1 Items

| Item | Prompt | What | Status |
|---|---|---|---|
| **B1** | 01 | the baselines: the freeze (84 lines), the suites (848, 72), the token file's `ls -l` | ⬜ |
| **P1** | 01 | `requirements.txt:58` `ray==2.59.0`, `:68` `SQLAlchemy==2.0.55`, a commit of its own; the venv upgraded, the freeze moved by those two lines alone | ⬜ |
| **V0** | 01 | on the pins alone: SI's cluster in token mode, and a driver attaching by address refused | ⬜ |
| **T1** | 01 | `config/ray_auth.py`, imported by `main.py`, both plot scripts and `tests/conftest.py`; the subprocess programs inherit it | ⬜ |
| **T2** | 01 | `ray_cluster.sh` names the mode before `ray start`; its `actors:` line and usage say so | ⬜ |
| **T3** | 01 | `tests/test_ray_auth.py`, with the breakages B1–B4 each caught | ⬜ |
| **D1** | 01 | `CLAUDE.md` (the rule, the counts) and `test-selection.md` (the counts) | ⬜ |
| **L1** | 01 | the launcher, 04's with its names changed | ⬜ |
| **R1** | 01 | `reference`: `done`, fingerprint `a9f716fb…1ea7` | ⬜ |
| **R2** | 01 | `resumed-a`: `SIGTERM`ed, `killed`/143, the store partial | ⬜ |
| **R3** | 01 | `resumed-c`: `done`, fingerprint `a9f716fb…1ea7` | ⬜ |
| **R4** | 01 | `compare_stores` equal; manifests `git_dirty` false | ⬜ |

**Legend.** ✍️ written · ⬜ not yet · ✅ done.

## 2. The gates

| Gate | Holds when | Prompt | State |
|---|---|---|---|
| **FP** | R's two stores, under `ray` 2.59.0 and `SQLAlchemy` 2.0.55, each fingerprint to `a9f716fb…1ea7`, and `compare_stores` finds them equal but for bookkeeping | 01 | ⬜ |
| **Token** | no log of R holds Ray's token warning or an authentication error; the cluster's `gcs_server` and `raylet` run with `RAY_AUTH_MODE=token`; the token file unchanged at mode 600; no record holds the token | 01 | ⬜ |

If FP fails, the bisection (Ray alone, or SQLAlchemy alone) is the user's call (README §2.2).

## 3. Active and unresolved issues

None open.

## 4. Resolved issues

None.

## 5. Dispatch record

### 5.0 Planning (2026-10-25)

Proposed in conversation on 2026-10-25, after SGK's `py313-venv` closed. Measured at `03110ce`
(README §0.3):
- the tree clean, no run `running` or stale, the lock free;
- a dry run of the two moved pins installs those two packages and nothing else;
- Ray 2.59.0's token logic read in SGK's venv: `ray start --head` turns token mode on when the token
  file exists, an attach by address never does. The token file exists (SGK's, 12:51, mode 600);
- Ray 2.55.1, SI's current, has no default token mode, so no SI run has used authentication yet.

The user ruled U1–U4 the same day; U4 drops the planner's first proposal (the four distributions
added to the manifests, as SGK's G1), because in SI that list is the protected
`utilities.RECORDED_DISTRIBUTIONS`.
