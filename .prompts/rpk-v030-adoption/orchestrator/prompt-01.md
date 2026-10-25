# Orchestrator — prompt 01, switch to the `raypoolkit` rehearsal lock

Read [`../README.md`](../README.md) first: §0–§0.4, §1, §2.1, §4, §5, §6.2 and §7. This is the
campaign's only note. Its conventions are `dk-and-rpk-migration`'s
([`../../dk-and-rpk-migration/orchestrator/prompt-01.md`](../../dk-and-rpk-migration/orchestrator/prompt-01.md),
§0 "Conventions"), carried over, with the lock rule of SecondaryGWKit's note for its own
`rpk-v030-adoption` 01 (SGK `5add52d`, `prompts/rpk-v030-adoption/orchestrator/prompt-01.md` §0).
What differs is said here.

**You do not write code.** You may:
- run the suites, `pip` read-only commands, the lock's `status` and `ray-processes`, and
  `ray_cluster.sh status`;
- read RayPoolKit's and SGK's repositories with `git`, never changing them;
- run a probe from the session scratchpad, against a scratch `HOME`, never committing one;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`01-switch-to-the-raypoolkit-rehearsal-lock.md`](../01-switch-to-the-raypoolkit-rehearsal-lock.md)
· **Board items:** P1, S1–S4, D1, V1, V2, G1 · **Closes:** nothing · **Opens:** nothing expected ·
**Model:** Opus, as the prompt recommends. Nothing is pushed.

**Gate:**
- The campaign is planned (`8baac35`). `HEAD` is the commit that adds this note, on
  `rpk-v030-adoption`; the tree is clean; `git worktree list` shows the main checkout alone.
- The venv holds `raypoolkit` 0.2.0 at `eaef0ce6…`, `datastorekit` 0.5.0 at `f47b9a25…` and
  `runregistrykit` 0.2.0 at `0bae3a3c…`, none editable.
- Neither lock location exists; no Ray process runs on the laptop; the old script's `status` is
  free, with no SI process and the four ports free.

## 0. What makes this prompt unusual

**It runs real Ray under a lock whose process rule reads command lines.** Contract §6: a process
whose command names `/tmp/ray-si` is a seed, and when a seed is an ancestor of the lock command,
everything else that seed started is listed. An agent's Bash command runs in a shell whose own
command line is the whole command. SGK's 01 met this (its note §0, and its `CLAUDE.md` after
`a04ef11`). So:
- **a lock command, or `ray_cluster.sh`, is the only process its shell command starts while it
  runs.** Redirect with `>> file 2>&1` and record `$?` with the builtin `echo`. **Never a pipe**,
  and never `| tee`: a `tee` beside a by-hand lock command whose line names `/tmp/ray-si` is a
  sibling under a seed, so it is listed, and `acquire` exits 4 or `ray-processes` exits 1 on a
  process that is not Ray's;
- never in the same shell command as anything else that runs while it does: the driver of step
  2.6.5, a `sleep`, a background listener;
- no background command of the agent's names `/tmp/ray-si` at any time;
- **the orchestrator runs nothing naming `/tmp/ray-si` while the agent works.** Any shell of this
  session is another process on the machine, and one naming the temp dir would be listed.

Inside the script, the module is called directly, its output unpiped; the script's command line
(`ray_cluster.sh start PURPOSE`) names no temp dir as long as no `PURPOSE` does.

**SGK has switched, and is closed.** SGK's 01 (`40d10b1`) moved SGK to the package's lock, and its
review (`88742d4`) closed that campaign on 2026-10-25 at 01:36. SGK's `acquire` now refuses with 3
while SI's old lock exists; SI's old script cannot see SGK's new lock. `~/.raypoolkit/` exists, an
empty directory made by SGK's `acquire` at 02:14 BST; the lock inside it does not. SGK's
`handover` 09 is unblocked and may run Ray, so the live check (2.6) can find the lock held: that is
a stop, never a wait. ChamPBH has started nothing, and still takes the old location.

**Corrections to the prompt**, each to be recorded as a deviation of the class given.
1. **The Gate's `runregistrykit list` cannot run on this branch** (`STRUCTURALLY REQUIRED`). It
   exits with `!! No runregistrykit.toml …`: the file is `rrk-adoption`'s (`7071bb8`), and this
   branch is cut from `main`. The item is met instead by `var/runs/` being empty (it is: measured
   at dispatch) and no `main.py` or plot driver running. **Do not create `runregistrykit.toml`.**
2. **Two more live statements of the pin** (`STRUCTURALLY REQUIRED`; README §0.3 missed them):
   - `.documents/INFRASTRUCTURE.md:455-456`, §9: "pinned in `requirements.txt` at `v0.2.0`";
   - `.documents/architecture-summary.md:343-344`, "RayWorkPool": "pinned in `requirements.txt` at
     `v0.2.0`, never editable".

   Each states the current pin, so each becomes `v0.3.0`, and nothing else in either paragraph
   moves. `architecture-summary.md` joins §5's list of files and acceptance 8's list. Other "at
   `v0.2.0`" citations stay (C8): `.claude/rules/compute-targets.md:106`,
   `datastore-factories.md:28`, `ray-dispatch.md:103` and `:248`, `picard.py:456`, and
   `INFRASTRUCTURE.md:39` (DatastoreKit's §9, "the changes after `v0.2.0`"). The results note says
   README §0.3 undercounted.
3. **What the script may name** (`IMPLEMENTATION CHOICE` of the orchestrator's, settling a
   conflict in the prompt). §2.3's last line says nothing in the script may name `.raypoolkit`, but
   S4 asks the usage text to name `~/.raypoolkit/rehearsal-lock`, and acceptance 3 allows comments
   and the usage text. **Acceptance 3 governs:**
   - `.raypoolkit` may appear in comments and the usage text, never in a line of code (B3 is the
     breakage of this);
   - `ScienceData` and `.rehearsal-lock` appear nowhere in the script, comments included, since
     acceptance 2's grep counts every line. The old location is written as "the old location"
     (contract §9), never spelled;
   - **the same holds for `CLAUDE.md`**, which acceptance 2's grep also reads: its new sentence
     says what exit 3 means without spelling the old location. `INFRASTRUCTURE.md` is under
     `.documents/` and outside the grep, but say it the same way there.
4. **`status` prints the absolute path** (`NOTED`). 2.6 step 3's `lock: HELD
   (~/.raypoolkit/rehearsal-lock)` is printed as `lock: HELD (/Users/ds283/.raypoolkit/rehearsal-lock)`
   (`rehearsal_lock.py:613`, the path from `Path.home()`).
5. **`/tmp/ray-si` exists as a directory** (`NOTED`): Ray's session directories, from earlier runs.
   "Nothing of `/tmp/ray-si` left" (2.6, acceptance 5) means no process by either rule and the four
   ports free. The directory is not removed.

**Facts from the module at the tag** (`git -C <RPK> show v0.3.0:raypoolkit/rehearsal_lock.py`).
- `default_lock_dir()` and `old_lock_dir()` are `Path.home() / …`, computed at each call
  (`:102-109`), so a scratch `HOME` moves both the lock and the old location: S-1 to S-6 never see
  the real ones.
- Its success lines, for matching: `acquired the rehearsal lock (<d>) for <project>: <purpose>`
  (`:486`); `recorded pid <pid> in <d>/owner` (`:544`); `no lock to release (<d>)` (`:554`);
  `released the rehearsal lock (<d>)` (`:597`). Refusals go to stderr; `acquire`'s exit 4 ends
  `released the lock again; not acquired` (`:421`).
- Each command imports Ray through the package root (contract §2): a few tenths of a second.

**What moves on purpose:** `requirements.txt:59` (the first commit); the venv's `raypoolkit`; the
script's lock half; `CLAUDE.md` (two places); `INFRASTRUCTURE.md` (`:41-42`, `:455-456`);
`architecture-summary.md:343-344`; `.documents/rpk-v030-adoption/` (the results note and `out/`);
the board; `.prompts/INDEX.md`'s line for this campaign.

**What must not move:** every `.py` file and every test; `datastorekit`, `runregistrykit` and `ray`
in the venv; the script's cluster half (`temp_dir_regex`, `list_cluster_pids`, `describe_pid`,
`port_listeners`, `alive`, `stop_cluster`, the ports, the `ray start` line); every record of another
campaign, the brief included; RayPoolKit, SGK and ChamPBH; any store.

**Facts checked by the orchestrator on 2026-10-25 at `8baac35`.** Pass them on.
- Tree clean, no stash, the main checkout alone, branch `rpk-v030-adoption`.
- The venv: `raypoolkit` at `eaef0ce60e2f…`, `datastorekit` at `f47b9a255e9a…`, `runregistrykit` at
  `0bae3a3c501a…`, `ray==2.55.1`; `pip freeze` 84 lines; `pip check` clean. **The dry run**, on a
  scratch copy of `requirements.txt` with the one line changed: `Would install raypoolkit-0.3.0`,
  and nothing else.
- RayPoolKit: `v0.3.0` is tag object `caf0076` peeling to `67a75b97a656accb98195a4bda93f64e6a5f3fb2`,
  locally and by `ls-remote`. Its checkout is `main` at `feae4e5`, clean.
  `git diff v0.3.0 feae4e5 -- raypoolkit pyproject.toml docs/rehearsal-lock.md` is empty. The
  checklist is at `127b2b4`, after the tag: read it at `feae4e5`, as the prompt says ("at
  `main`").
- Neither `~/ScienceData/.rehearsal-lock` nor `~/.raypoolkit/rehearsal-lock` exists. No
  `gcs_server` or `raylet` runs; no `/tmp/ray/ray_current_cluster`; `RAY_ADDRESS` unset. The old
  script's `status`: `lock: free`, no processes, the four ports free.
- Acceptance 2's grep: the 5 lines `:19`, `:45`, `:75`, `:76`, `:77`, all in the script.
  `git grep -c 'raypoolkit\.rehearsal_lock'` on the script: 0.
- `CLAUDE.md:14-20` and `:126-127`, `INFRASTRUCTURE.md:41-42` and `requirements.txt:59` are where
  the prompt puts them. The script is blob `6c8eada`, 398 lines.
- `var/runs/` is empty. Load average about 9.
- **Baselines** at `8baac35`, serially, by the orchestrator: default **732** (731 passed, 1
  skipped), 34 s, load 10 at the start; `RAY_ADDRESS=local … -m integration` **67** (66 passed, 1
  skipped), 55 s, load 16. README §0.4's counts.

## 1. Before you dispatch

1. The Gate, as §0's facts.
2. **Baselines**, both suites serially at `8baac35`, in the session scratchpad
   (`orch01/baseline-suites.txt`), with the load.
3. **The commit of this note**, alone, staged by path.

**Done at dispatch (2026-10-25):** the Gate as §0; the baselines 732 / 67 as §0
(`orch01/baseline-suites.txt`); `pip freeze` saved as `orch01/pip-freeze-before.txt` for check 2.

## 2. Dispatch

One fresh-context subagent, on **Opus**, in the main checkout. Give it the prompt, the README, the
board, `HEAD`, the baselines, and §0 of this note up to "## 1. Before you dispatch", as a copy in
the session scratchpad. The agent does not read `orchestrator/`.

Tell it plainly:
- **Two commits** (C6): the pin alone, after the install and its checks; then the rest, staged by
  explicit path, after showing `git diff --cached --name-only`. Acceptance 8's list gains
  `.documents/architecture-summary.md` (§0, correction 2).
- **The corrections of §0.** In particular: no `runregistrykit.toml`; the two further pin
  statements; the old location never spelled in the script or `CLAUDE.md`.
- **Lock commands: one per shell command, no pipe, no `tee`** (§0). The by-hand commands of 2.5
  and 2.6 name `/tmp/ray-si` only where the prompt says, and nothing else runs in that shell.
- **The breakages** are recorded as diffs that `git apply` replays from a clean tree at the second
  commit, checked with `git apply --check` and `-R --check`, replayed in `bash`; never committed.
- **The live check** runs once. If `status` shows the lock held at step 1, it stops and asks; it
  never waits.
- **Scratch** is the agent's own subdirectory of the session scratchpad, never `/tmp`, and the
  scratch `HOME` is made with `mktemp -d` inside it. No `.py` file goes into the repository.
- **Stop and ask** on any of the prompt's §4 conditions. If it stops with the lock held, it leaves
  it held and prints the owner file. If it stops after the install, it says the venv holds
  `v0.3.0`.
- **It replies with:** both commits' SHAs and `--stat`; the dry run, the freeze diff and the
  `--help` line; the script's diff; S-1 to S-6, each with its exit and lock state; 2.6's nine steps,
  each with its exit; B1–B4, each with what caught it; acceptance 2's and 3's greps; both suites
  before and after, with the load; every deviation with its class; and the G2 draft, verbatim.

## 3. The review — nine checks

1. **Scope.** `git show --stat` of each commit. The first is `requirements.txt` alone, one line.
   The second is exactly acceptance 8's list with `architecture-summary.md`. `git status --short`
   clean; no `runregistrykit.toml`; `git diff --name-only 8baac35 HEAD -- '*.py'` empty; nothing
   pushed.
2. **The venv, measured here.** `pip freeze` against `orch01/pip-freeze-before.txt`: the one
   `raypoolkit` line, now `@67a75b97…`; not editable (`direct_url.json`); `pip check` clean;
   `pip install --dry-run -r requirements.txt` installs nothing. `01-pip.txt` has the dry run
   before the install, `Would install raypoolkit-0.3.0` alone.
3. **The script, by reading.** S1: the lock functions gone, the cluster half byte-identical
   (`git diff` shows no hunk in `:149-261`). S2: `acquire … || return $?`; the stale-cluster check
   gone; `set-pid` with the `gcs_server`'s pid, its refusal handled as no `gcs_server`; `release` on
   the held-port path, the two failure paths and the trap, the return codes 4, 1, 1, 130 whatever
   `release` returns, and its refusal not hidden (no `2>/dev/null`, no `|| true` swallowing
   stderr). S3: the owner check before `stop_cluster`, at `default_lock_dir()` asked of the
   package, a missing owner file treated as not SI's. S4: `status` then the script's listing under
   its own heading, then the ports. Every module call takes its values from `$LOCK_PROJECT`,
   `$SI_TEMP_DIR`, `$SI_ADDRESS`. The header and usage say what is now true. `bash -n` passes;
   acceptance 2's grep is **0**, acceptance 3's finds `.raypoolkit` only in comments and the
   usage text.
4. **The scratch checks, re-run here.** S-1, S-2, S-3 and S-5 against a fresh scratch `HOME` of the
   orchestrator's, each as a shell command of its own, while the real `status` shows no SI process;
   the exits and lock states as the prompt's table says. S-4 and S-6 are read from `01-scratch.txt`.
   The scratch `HOME` is removed after.
5. **The live check, from `01-live.txt`.** Step by step: 0 and free; `start` 0 with the
   `gcs_server`'s pid; `status` HELD, the owner file with SI's four values and that pid, alive, the
   module's listing naming `gcs_server`, `raylet` and the client server; `ray-processes` 1 with the
   same processes; the driver's `CPU` 4.0; the second `start` 3; `release` 1; `stop` 0 and
   `released the rehearsal lock (…)`; `status` free, none, ports free; `ray-processes` 0. Then, here:
   neither lock location exists, no `gcs_server` or `raylet` runs, the old script's ports free.
6. **The breakages.** Each diff in `01-breakage.txt` is replayed with `git apply` in `bash`, from
   the clean tree at the second commit, its check run against a fresh scratch `HOME`, its failure
   seen, and reverted (`git status` clean). B2's lock in the scratch `HOME` is released by hand.
7. **The documents.** `CLAUDE.md`: the pin at `v0.3.0`, nothing else in that paragraph; one
   sentence after "under the shared rehearsal lock: …" naming the module, its location, the other
   two projects, the contract, and exit 3 as stop-and-ask; the `ray stop` sentence and its citation
   kept; the paragraph rewrapped, no other line moved. `INFRASTRUCTURE.md` and
   `architecture-summary.md` as §0 correction 2 and prompt 2.4 say.
8. **The suites, re-run here** at the second commit, serially: 732 (731 passed, 1 skipped) and 67
   (66 passed, 1 skipped), as the baselines.
9. **The records.** The results note has `dk-and-rpk-migration` README §5.1's sections, the counts,
   the deviations with classes (§0's five among them), and the G2 draft: SI's branch and commits,
   the pin at `67a75b9`, item 8 as it held (5 → 0, the module called, the suites unchanged), 2.6's
   exits, and the cross-check owed once ChamPBH has switched. The board: header "01 landed, awaiting
   review", the §1 row, the items, the gate **Switch**, `### 5.1 After prompt 01`. `INDEX.md`'s
   line. No issue opened, so `OPEN-ISSUES.md` untouched. Commit messages end with the
   `Co-Authored-By` line.

## 4. After the review

If it passes, residue first, in a follow-up commit of its own:
- "this commit" → the second commit's SHA, on the board and in the results note;
- the board's list of orchestrator notes, with this one marked "used for 01";
- README §0.3 and §2.1: the two further pin statements (§0, correction 2), and the Gate's
  `runregistrykit list` (correction 1), as a dated correction of the plan's text; prompt 01 left as
  it ran.

Then **the close**, one commit of the orchestrator's (README §2: the review of 01 closes the
campaign): the board's header (**CLOSED — 1 of 1 landed and reviewed**), its §1 row, the gate
**Switch**, `### 5.2 Review and close (<date>)` holding what each check found, and the campaign's
line in `.prompts/INDEX.md` with the header's count and date. Anything that is not residue is
opened on the board's §3 and in `OPEN-ISSUES.md` instead, in the same commit.

**Report to the user:** the pin and the venv; the script's three commands on the module; the lock
seen held and refusing under SI's real cluster; the suites; the G2 draft, theirs to record in
RayPoolKit; and that the merges of README §4 (`main` fast-forwarded to this branch, then `main`
merged into `rrk-adoption` before its 02) wait on their instruction. ChamPBH alone still takes the
old location; while it holds it, SGK's and SI's `acquire` exit 3.
