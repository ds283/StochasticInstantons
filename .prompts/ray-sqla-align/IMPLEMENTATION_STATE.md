# ray-sqla-align campaign — implementation state

**Last updated:** 2026-10-25 · **Status: CLOSED — 1 of 1 landed and reviewed.** Planned and
ruled the same day (U1–U4); 01 dispatched at the user's word (C12) and landed in three commits
(`5f3219f`, `3a24ea5`, `dfb957b`; §5.2); its review passed and closed the campaign (§5.3). The
gates **FP** and **Token** hold.
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
| **U4** — recorded distributions | *revised:* `ray`, `SQLAlchemy`, `numpy`, `scipy` added to both lists before 01 (`c5af555`, `900d3f7`; §5.1) |

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
| 01 | [`01-move-ray-and-sqlalchemy-with-token-mode.md`](01-move-ray-and-sqlalchemy-with-token-mode.md) | Opus | ✅ landed 2026-10-25 (`5f3219f`, `3a24ea5`, `dfb957b` the records); reviewed and closed 2026-10-25 (§5.3). Results: [`01-move-ray-and-sqlalchemy-with-token-mode.md`](../../.documents/ray-sqla-align/01-move-ray-and-sqlalchemy-with-token-mode.md) |

The review of 01 closes the campaign.

**Orchestrator notes** (`orchestrator/`), written before each dispatch: [`prompt-01.md`](orchestrator/prompt-01.md) (`8c01877`), used for 01.

### 1.1 Items

| Item | Prompt | What | Status |
|---|---|---|---|
| **B1** | 01 | the baselines: the freeze (84 lines), the suites (848, 72), the token file's `ls -l` | ✅ 84 lines; 848 (847 + 1 skipped) and 72 (71 + 1 skipped); `-rw-------`, 64 bytes, 12:51 |
| **P1** | 01 | `requirements.txt:58` `ray==2.59.0`, `:68` `SQLAlchemy==2.0.55`, a commit of its own; the venv upgraded, the freeze moved by those two lines alone | ✅ `5f3219f`; the dry run and the freeze moved by those two lines alone; `pip check` clean |
| **V0** | 01 | on the pins alone: SI's cluster in token mode, and a driver attaching by address refused | ✅ the warning in `start`'s output; the driver refused (21 `InvalidAuthToken`, `AuthenticationError`), exit 1 |
| **T1** | 01 | `config/ray_auth.py`, imported by `main.py`, both plot scripts and `tests/conftest.py`; the subprocess programs inherit it | ✅ `3a24ea5`; the three subprocess programs read, all inherit |
| **T2** | 01 | `ray_cluster.sh` names the mode before `ray start`; its `actors:` line and usage say so | ✅ `3a24ea5`; `bash -n` 0 |
| **T3** | 01 | `tests/test_ray_auth.py`, with the breakages B1–B4 each caught | ✅ `3a24ea5`; 10 tests, 2.1 s standalone; B1–B4 each caught |
| **D1** | 01 | `CLAUDE.md` (the rule, the counts) and `test-selection.md` (the counts) | ✅ `3a24ea5`; 858 of 999, 72, 69 |
| **L1** | 01 | the launcher, 04's with its names changed | ✅ `3a24ea5`; `bash -n` 0, the diff recorded |
| **R1** | 01 | `reference`: `done`, fingerprint `a9f716fb…1ea7` | ✅ `done`/0; `a9f716fb…1ea7` |
| **R2** | 01 | `resumed-a`: `SIGTERM`ed, `killed`/143, the store partial | ✅ `killed`/143, `<s>` 19 s; 3 `FullInstanton` rows stored, 7 not |
| **R3** | 01 | `resumed-c`: `done`, fingerprint `a9f716fb…1ea7` | ✅ `done`/0, only the missing rows computed; sidecar `a9f716fb…1ea7` |
| **R4** | 01 | `compare_stores` equal; manifests `git_dirty` false, `packages` naming `ray` 2.59.0 and `SQLAlchemy` 2.0.55 | ✅ `RESULT: equal`; `git_head` `3a24ea5`, `git_dirty` false, the four versions recorded |

**Legend.** ✍️ written · ⬜ not yet · ✅ done.

## 2. The gates

| Gate | Holds when | Prompt | State |
|---|---|---|---|
| **FP** | R's two stores, under `ray` 2.59.0 and `SQLAlchemy` 2.0.55, each fingerprint to `a9f716fb…1ea7`, and `compare_stores` finds them equal but for bookkeeping | 01 | ✅ holds (01; re-measured at review) |
| **Token** | no log of R holds Ray's token warning or an authentication error; the cluster's `gcs_server` and `raylet` run with `RAY_AUTH_MODE=token`; the token file unchanged at mode 600; no record holds the token | 01 | ✅ holds (01; re-measured at review) |

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

The user ruled U1–U4 the same day. U4 first dropped the planner's proposal to add the four
distributions to the manifests, as SGK's G1, because the planner said the change was forced on the
protected `utilities.RECORDED_DISTRIBUTIONS`. That overstated it (§5.1).

### 5.1 U4 revised, before dispatch (2026-10-25)

Asked by the user, the planner explained the two lists: `runregistrykit.toml`'s `distributions`
(a registered run's manifest) and `utilities.RECORDED_DISTRIBUTIONS` (each driver's `>> packages:`
line). Neither names a version, so the move needs neither change. They were meant to agree
(`rrk-adoption` R3), but each was pinned by its own test to the same literal and nothing compared
them: a latent drift. At the user's instruction:
- **`c5af555`**: `tests/test_registry_config.py` holds the toml's list equal to
  `utilities.RECORDED_DISTRIBUTIONS`. Adding `ray` to the toml alone fails it.
- **`900d3f7`**: `ray`, `SQLAlchemy`, `numpy` and `scipy` added to both lists, the user naming
  `utilities.py` for the change; `test_default_names` and `INFRASTRUCTURE.md` follow. The four
  PyPI installs print `(no recorded origin)`. Default suite 848 (847 passed, 1 skipped);
  `integration` 72 (71 passed, 1 skipped).

U4 now reads "added". Prompt 01's Gate starts after this amendment, and R4 checks that R's manifests
name `ray` 2.59.0 and `SQLAlchemy` 2.0.55.

### 5.2 After prompt 01 (2026-10-25)

01 ran on `main` from the dispatch commit `8c01877`, under the orchestrator's brief (15
corrections, each classified in the results note), 18:26–19:00 GMT. Three commits:
- **`5f3219fb483208b5738f15d1b0e95cbcacd8d8eb`** — the pins: `ray==2.59.0`, `SQLAlchemy==2.0.55`.
  The dry run would install those two and nothing else; the venv was upgraded in place, the freeze
  moved by those two lines alone, `pip check` clean, the git packages unmoved. Both suites at the
  baselines on this tree (848, 72).
- **`3a24ea53962a3a02de412032807c0fd3e9afcb3f`** — the fix: `config/ray_auth.py` and its four
  importers, `ray_cluster.sh` naming the mode, `tests/test_ray_auth.py` (10 tests), `CLAUDE.md`,
  `test-selection.md` and the launcher. Suites 858 (857 passed, 1 skipped) and 72 (71 passed, 1
  skipped).
- **`dfb957ba1a9b16f937f4c349a56e776c6dbdb25b`** — the records: the results note, `.documents/ray-sqla-align/out/`, this board
  and `INDEX.md`'s line.

**Measured:**
- **V0**, on the pins alone: `ray_cluster.sh start` printed Ray's `Token authentication is
  enabled` warning, and a driver attaching by address was refused (21 `InvalidAuthToken` lines,
  then `AuthenticationError … RAY_AUTH_MODE is currently 'disabled' (not 'token')`), exit 1 after
  22 s. README §0.2 holds on this machine.
- **The warning, by probe** (the suites capture logging and never show it): a local `ray.init` on
  the pins logged it; the same with `import config.ray_auth` first, on the fix, did not.
- **B1–B4** each caught by a named test of `tests/test_ray_auth.py`.
- **R**, on the clean fix tree: `reference` `done`/0; `resumed-a` `killed`/143 with `<s>` = 19 s,
  inside the narrow window (3 `FullInstanton` rows stored, 7 not); `resumed-c` `done`/0,
  computing only what was missing. Both stores fingerprint to `a9f716fb…1ea7` and `compare_stores`
  gives `RESULT: equal`: **FP holds.** No R log or `start` output holds a token warning or an
  authentication error, the `gcs_server` and `raylet` ran with `RAY_AUTH_MODE=token`, the token
  file is unchanged (64 bytes, mode 600, 12:51:17), and no record holds it: **Token holds.**
- The manifests: `git_head` `3a24ea5`, `git_dirty` false, `ray` 2.59.0, `SQLAlchemy` 2.0.55, numpy
  2.4.6, scipy 1.17.1 (U4).

**Found:** the plot scripts call `ray.init` in their `__main__` block, not inside a function as the
README and the prompt say; T3 checks the import against the top-level statement holding the call.
No issue opened. The venv holds the new versions; R's two stores are in `var/datastores/` for the
user to retire. Nothing pushed.

### 5.3 Review and close (2026-10-25)

*Orchestrator review of prompt 01*, after
[`orchestrator/prompt-01.md`](orchestrator/prompt-01.md)'s eleven checks, at `dfb957b`, 19:00–19:12
GMT. All eleven passed.
1. **Scope.** `5f3219f` is `requirements.txt` alone, two lines; `3a24ea5` is exactly the prompt's
   ten paths; `dfb957b` is the results note, 30 files under `out/`, this board and `INDEX.md`.
   `git diff 8c01877 dfb957b --name-only` is 44 paths, acceptance 6's list. Nothing under
   `utilities.py`, `runregistrykit.toml`, `RunDrivers/`, `ComputeTargets/`, `Numerics/`,
   `Interpolation/` or `Datastore/` moved. The tree clean; nothing pushed.
2. **The venv.** `pip freeze` against the orchestrator's before dispatch: the `ray` and
   `SQLAlchemy` lines alone; `pip check` clean; nothing editable; a dry run of `requirements.txt`
   installs nothing. `01-pip.txt` has the dry run (`Would install SQLAlchemy-2.0.55 ray-2.59.0`)
   before the install.
3. **The token file.** 64 bytes, mode 600, 12:51:17. `grep -r -F -l -f` over
   `.documents/ray-sqla-align/` and `.prompts/ray-sqla-align/`, and `git grep -F -l -f` over
   `HEAD`: both exit 1.
4. **The fix, by reading.** `config/ray_auth.py`, the four importers, `ray_cluster.sh` (three
   hunks: the usage sentence, the export before `"$RAY_BIN" start`, the `actors:` line; none in
   the lock half, the stop or the ports) and L1 (names and header only) as the prompt says.
   `bash -n` passes on both scripts.
5. **T3 and the breakages.** `tests/test_ray_auth.py`: 10 passed, 3.5 s standalone. Each of
   `out/01-B1.diff`–`01-B4.diff` replayed with `git apply`: B1 failed `test_ray_imported_first`;
   B2 the two `disabled` tests; B3 the `ast` test for `plot_InstantonSolutions.py`; B4 the text
   test. Each reverted, the tree clean.
6. **V0.** `start` 0 with Ray's token warning; the driver refused (`InvalidAuthToken`, then
   `AuthenticationError … RAY_AUTH_MODE is currently 'disabled'`), exit 1 after 22 s; `stop` 0;
   `status` free.
7. **The runs.** `list`: `reference` `done`, `resumed-a` `killed`, `resumed-c` `done`. Each
   `manifest.json` and `status.json` equals its committed copy; `script_sha256` is `main.py`'s;
   `results_store_id` null, null, `c5ea19ff…bd03`; `git_head` `3a24ea5`, `git_dirty` false; the
   seven packages with `ray` 2.59.0 and `SQLAlchemy` 2.0.55 (correction 2).
8. **R2.** The wrapper's `killed` lines, `** driver exit status 143` and the launcher's 143.
   R1's rows, re-read read-only: `FullInstanton` from +15.6 to +21.6 s after the `LOOKUP:` banner
   (18:52:15.2), so `<s>` = 19 s was inside the narrow window; the resumed store holds three
   `FullInstanton` rows from `resumed-a` (18:54:26) and seven from `resumed-c`, as its lookup's
   "3 already computed, 7 to compute".
9. **The stores.** `compare_stores.py`: `RESULT: equal`. `store fingerprint` on each:
   `a9f716fb…1ea7`, each matching its sidecar. The sidecars: `cb7b2dc3…` and `c5ea19ff…`,
   created at `3a24ea5` with `git_dirty` false.
10. **The records.** The results note in `dk-and-rpk-migration` README §5.1's form, 19
    deviations classed (the brief's 15 among them). It named only SGK's second issue; the residue
    commit `8857138` names the first beside it and replaces "this commit" with `dfb957b`.
11. **The suites** at `dfb957b`, serially, no cluster up: default 858 (857 passed, 1 skipped), 70
    s; `integration` 72 (71 passed, 1 skipped), 198 s. Correction 3's second probe, re-run: no
    warning. `ray_cluster.sh status`: lock free, no SI process, the four ports free. `list`: the
    same seven runs.

**Corrections that read the prompt otherwise than it was written:** 1 (this board's section is
§5.2, not §5.1), 2 (a manifest names seven packages, a `>> packages:` line six), 3 (Ray's token
warning is a `logging` call that pytest does not show, so two probes measured it). The agent's own
deviation 16 corrects the plan: the plot scripts call `ray.init` in their `if __name__ ==
"__main__":` blocks, not inside a function as README §0.3, the prompt (§2.5, T3) and the
orchestrator's note say; T3 tests the import against the top-level statement holding the call.
Prompt 01 is left as it ran.

**The campaign is closed.** SI runs `ray` 2.59.0 and `SQLAlchemy` 2.0.55, with every Ray start in
named token mode. No issue was opened. R's two stores, `ray-sqla-align-01-reference` and
`ray-sqla-align-01-resumed`, stay under `var/datastores/` for the user to retire (README §3), with
their run records under `var/runs/`. Nothing is pushed. README §7 hands the token-mode fix to
ChamPBH, still on `ray` 2.53.0.
