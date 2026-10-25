# Orchestrator — prompt 05, close

Read [`../README.md`](../README.md) first: §1, §2.2 (05's charter), §5, §6.0, §6.2 (P12, P13) and
§7. Then the board in full, above all §5.6 (04's record and review). The conventions are note 02's
([`prompt-02.md`](prompt-02.md), which carries `dk-and-rpk-migration`'s
[`prompt-01.md`](../../dk-and-rpk-migration/orchestrator/prompt-01.md) §0 "Conventions"), restated
in §0 where 05 needs them. ChamPBH closed the same campaign on 2026-10-20; its drafts of the two
RunRegistryKit records are its `.documents/rrk-adoption-verification.md` §2 (`:572`, at ChamPBH
`58c1c93`), and they are the nearest form for Z4.

**You do not write code.** You may:
- run the suites, `runregistrykit list` and the registry's read-only commands, `ray_cluster.sh
  status`, `git grep`, and read-only Python probes (`ast`, counting) from the session scratchpad
  (`orch05/`), never committing one, and never starting Ray;
- read RunRegistryKit, ChamPBH and DatastoreKit with `git show`, never changing them;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`05-close.md`](../05-close.md) · **Board items:** Z1–Z5 · **Closes:** the campaign
· **Opens:** nothing (correction 10) · **Model:** Sonnet, as the prompt recommends · **Network:**
none. Nothing is pushed, nothing is merged.

**Gate:**
- 01 (`60687f0`, `7071bb8`), 02 (`0fcaf7c`, reviewed `ff3ddd6`), 03 (`16e1cc1`, reviewed `edb03ea`)
  and 04 (`29705f2`, reviewed `39fc819`) landed; the gates **Pin**, **Fingerprint**, **Wrapper** and
  **R** hold (board §2). `HEAD` is the commit that adds this note, on top of `39fc819`, on
  `rrk-adoption`; the tree is clean; `git worktree list` shows the main checkout alone.
- The prompt's own gate (its header), checked by the orchestrator (below).
- No other session runs a suite or a Ray job from this venv, or installs into it, while 05 runs.

## 0. What makes this prompt unusual

**It is all prose and records, and most of what it touches is a record of someone else's.** The
risk is not a wrong value but a rewritten record, a stale count, or a draft for another repository
that claims more than SI measured. So: dated notes and earlier board sections are kept byte for
byte; every count is measured, not copied; and every clause of the two drafts names where it holds.

**Corrections to the prompt**, each recorded in the results note as a deviation of the class given.

1. **The board section is `### 5.7`, not `### 5.6`** (`STRUCTURALLY REQUIRED`). §5.6 is 04's. Z5's
   `### 5.6 After prompt 05 (<date>)` becomes `### 5.7 After prompt 05 (<date>)`.

2. **RunRegistryKit's boards are read at `main`, not the tag** (`STRUCTURALLY REQUIRED`). Read-first
   6 says "at `v0.2.0`". At the tag the `interrupted-runs` board's G1 reads "not yet"; SGK's record
   there is on `main` only (`33a2cd2`). The user will commit SI's records on `main`. **Ruled:** read
   both boards at RunRegistryKit `main` (`70ee1e8` at dispatch; `git -C ../RunRegistryKit show
   main:<path>`), and the checklist, the `v0.2.0` note and `docs/adoption/v0.2.0/README.md` at
   `v0.2.0` (identical at `main`: since the tag, `docs/adoption/` changed only in its top-level
   `README.md`, the Q5 addendum). The rows the drafts replace, at `main`:
   - `prompts/extraction/IMPLEMENTATION_STATE.md:1130`: `| **G4** | not yet (SI adopts, after its
     dk-and-rpk-migration); its checklist is …`. The form is **G2** (SGK) at `:1128`. G3
     (ChamPBH) at `:1129` still reads "not yet": the user has not committed ChamPBH's draft.
   - `prompts/interrupted-runs/IMPLEMENTATION_STATE.md:1182`: `| **G3** | not yet (SI adopts) |`.
     The form is **G1** (SGK) at `:1180`. G2 (ChamPBH) at `:1181` still reads "not yet".

   So for ChamPBH's form, read its drafts (ChamPBH's verification §2.1 and §2.2), not its rows. Each
   draft replaces **the second column** of its row, as `dk-and-rpk-migration/verification.md` §4.3
   says of its own; §2's preamble gives the two paths, line numbers and RunRegistryKit's `HEAD`.

3. **SI's pin was added, not moved** (`STRUCTURALLY REQUIRED`). Z4's G3 says "its pin moved in a
   commit of its own". SI never pinned `v0.1.0`: `git log -S runregistrykit -- requirements.txt`
   gives one commit, `60687f0` ("Pin runregistrykit[stores] v0.2.0 (rrk-adoption prompt 01, C1)"),
   which changes `requirements.txt` alone, by one inserted line (`requirements.txt:63`). The draft
   says **added at `v0.2.0`, in a commit of its own**, and that the `v0.1.0` → `v0.2.0` move of the
   note's §1 did not arise.

4. **The `v0.2.0` checks are `docs/adoption/v0.2.0/README.md` §3, and they apply** (`STRUCTURALLY
   REQUIRED`). Z4 says "which of the `v0.2.0` note's §3 checks applied (none of SI's code predates
   the adoption)". The SI note (`docs/adoption/v0.2.0/stochasticinstantons.md`) has no §3; its §1
   adds the checks of `docs/adoption/v0.2.0/README.md` §3, and says each "applies to what it writes
   when it adopts". So they apply to the wrapper and the campaign's tests. **Ruled:** the G3 draft
   goes through the six, each found by `git grep` over SI's tree at the agent's `HEAD`, excluding
   `.prompts/` and `.documents/`:
   - a comparison with `liveness`'s values (`foreign`, a `stale` from an earlier boot);
   - `TERMINAL_STATES` (its fourth value, `lost`);
   - a store refusal's text (`Run.finish` → `python -m runregistrykit end`);
   - a test that begins two unfinished runs on one store;
   - a caller of `pid_alive` that relied on its raising;
   - a test that pins a record's key set (`host`, `ended`).

   For each: the grep as run, its hits, and why each hit holds. Every one was written and tested
   against `v0.2.0`, so "holds by construction, and its test passes" is the expected answer, with
   the test named. At dispatch the orchestrator's grep for `liveness|TERMINAL_STATES|pid_alive|Run\.finish|names this store|is running`
   found only `.claude/rules/run-registry.md:43` (prose: "`Run.finish` is never called by hand…")
   and `:61` ("liveness test"). The grep must also cover the key-set and two-`begin` checks, which
   need their own patterns (`set(`, `sorted(` against a manifest's or status's keys;
   `begin(` twice in a test). The draft also says: §2 of that README (every checkout sharing a runs
   root moves together) holds trivially, since SI has one checkout; and §4 (the hard-kill route) is
   `.claude/rules/run-registry.md`'s "The route after a hard kill", rehearsed in 04 (H3).

5. **Where the Z1 note lives, and its form** (`IMPLEMENTATION CHOICE`, ruled here). The existing
   dated notes are single italic lines at the head of a section, `*Rewritten 2026-10-23 by
   dk-and-rpk-migration prompt 12; …*`. **Ruled:**
   - **`.documents/INFRASTRUCTURE.md` holds the note**, as a new last section, `## 13. The run
     registry — \`runregistrykit\``, after §12. Its first line is a dated italic line in the
     existing form (`*Written <date> by rrk-adoption prompt 05; …*`), then descriptive prose
     covering Z1's five points: what the registry records and where (`var/runs/<run id>/`: the
     manifest, `status.json`, `stdout.log`, `stderr.log`; a store's sidecar
     `var/datastores/<stem>.manifest.json`); the wrapper, and `main.py` launchable without it (R2,
     R3, R5); what the heartbeat means (03's `HEARTBEAT_MEANS`, summarised, with the 900 s window
     and the gradient branch); the fingerprint (format 1, `SPEC_DIGESTS` in `config/fingerprint.py`,
     the guard `tests/test_fingerprint_format_guard.py`, the golden file
     `tests/data/store_fingerprint_rrk-adoption-02.json`, never overwritten); the sidecar by a
     person after the first close (R4). It cites RunRegistryKit's `README.md` at `v0.2.0` and
     `.claude/rules/run-registry.md`, and does not copy them, as §1 treats the other two packages;
   - INFRASTRUCTURE's title becomes "how SI uses `datastorekit`, `raypoolkit` and
     `runregistrykit`", and its opening paragraph gains one sentence pointing at §13. §1's list of
     packages is not changed: the registry is neither (a) nor (b);
   - **`architecture-summary.md`**: the "Repository layout" tree gains the five entries of Z1 and
     `runregistrykit` in its packages block, each with a comment. Under the section's existing
     italic line (kept), one new italic line: `*Extended <date> by rrk-adoption prompt 05 (the run
     registry's entries); what the registry records is \`INFRASTRUCTURE.md\` §13.*`. "main.py — the
     orchestrator" gains one sentence that a registered run launches it through
     `RunDrivers/registered_run.py` (§13);
   - **`FILE_MAP.md`** has no dated notes. §1's table gains rows for `config/fingerprint.py`
     (`config_fingerprint.py`), `runregistrykit.toml` and `RunDrivers/registered_run.py`
     (`RunDrivers_registered_run.py`), as `dk-and-rpk-migration` 12 added `config_datastore.py`;
     "Files not included" gains `RunDrivers/__init__.py`, `.claude/settings.json` and `var/`, each
     with a reason. One purpose cell points at INFRASTRUCTURE §13.

6. **The test counts** (`NOTED`, measured here). At dispatch, by collection: **989** tests; default
   **848** (847 passed, 1 skipped, 141 deselected); `integration` **72** (71 passed, 1 skipped);
   `slow` **69**; 848 + 72 + 69 = 989, disjoint. So:
   - `CLAUDE.md:35-39`: "(848 of 989 tests; 847 pass and 1 is skipped; …). The other 141 are the
     72 `integration`-marked tests, … and the 69 `slow`-marked ones";
   - `.claude/rules/test-selection.md:10` (989), `:26` (848 of 989, 847 pass), and `:60-61`. That
     last sentence is dated ("At the close of dk-and-rpk-migration the markers selected 67 …"): it
     is a rules file's current statement, not a record, so it **becomes** "At the close of
     rrk-adoption the markers selected 72 `integration` tests (71 pass, 1 is skipped) and 69 `slow`
     tests, disjoint, so 848 + 72 + 69 = 989", and is not a stop. The slow table is unchanged: no
     file became `slow` (P11), which the note says.

7. **Z2's sentence check found nothing at dispatch** (`NOTED`). The orchestrator read `CLAUDE.md`'s
   section "Long-running jobs — the run registry" and `.claude/rules/run-registry.md` against
   `verification.md` §1 and found no sentence 04 contradicts. The agent checks again. `CLAUDE.md`'s
   "Protected infrastructure" names two packages, not `runregistrykit`; that is an omission, not a
   wrong sentence, and Z2's "nothing else changes" holds: the agent may record it as an observation.

8. **P12's exact texts** (`NOTED`).
   - `.claude/rules/datastore-factories.md:239-240`: "which RunRegistryKit will take for SI in the
     next infrastructure campaign". Present tense, naming `rrk-adoption`.
   - `tests/test_inventory_specs.py:33-34` (the module docstring): "RunRegistryKit's fingerprint,
     which SI adopts after this campaign, reads …". Present tense, naming `rrk-adoption`.
   - `utilities.py:191-193`: the sentence of Z3, after "(README P5).". Reflow only the lines of
     that one paragraph of the docstring, at its existing width; nothing else in the file moves.

   For each `.py` file, the `ast` check is: parse at `HEAD` and after, remove every docstring
   (the first statement of a module, class or function body when it is a string constant), and
   compare `ast.dump`. The script is the agent's, in its scratch directory, quoted in the note.

9. **The indexes** (`NOTED`, measured here).
   - `.documents/OPEN-ISSUES.md`: **58 open** rows by counting (the closed count, 31, counts issues;
     some closed rows hold several). 01–04 opened one issue, `[default-suite-starts-ray-in-process]`
     (§6b), and it stays open and unowned. So the counts do not move. §6b's intro sentence gains
     that the campaign closed on <date> and its board stays the record, as §6a's says of
     `dk-and-rpk-migration`. The header's date is the close's date. The header's paragraph "One
     campaign has a status board …" is stale (three do now) but is not 05's: an observation.
   - `.prompts/INDEX.md`: the header becomes 8 campaigns: 0 ready, **0 live**, 1 halted, **7
     complete**; the row **complete 5 / 5 on <date>** in `dk-and-rpk-migration`'s form; its
     open-issue column `§6b; 1`; the "Planned" paragraph on `rrk-adoption` (`:63-66`) past tense.

10. **Nothing is opened** (`NOTED`, ruled here). The observations of 01–04's notes (01's `*.sqlite`
    rule; 02's store built twice; 03's four, the first already an issue; 04's six) are left as
    their notes hold them. §5.7 lists for the user: the merge into `main` (R7); the two records
    (Z4); 04's stores, runs and `var/rrk-adoption-04/`; README §7's observation on the wrapper's
    generic part; and that RunRegistryKit's `end` stamps the status's `heartbeat` with its own time
    (04's observation 3, documented behaviour), which the user may raise there.

11. **What the drafts name** (`STRUCTURALLY REQUIRED`). Only SI commits that exist when 05
    commits, 05's own not among them, as `dk-and-rpk-migration/verification.md` §4.3. Every count
    and digest in them is copied from a committed record (results notes, `verification.md` §1) and
    the record named. They claim nothing about RunRegistryKit's own tests or CI. Like ChamPBH's §2.3,
    the section says what the drafts do not claim.

**What the orchestrator measured at `39fc819`** (2026-10-25, 16:40–16:50 GMT). Pass them on.
- **The prompt's gate.** `git status --short` empty, main checkout only. `ray_cluster.sh status`,
  exit 0: lock free, no Ray process of the SI cluster, ports 6390, 6391, 8266 and 52366 free; no
  `raylet`, `gcs_server` or `ray::` process on the machine. `RAY_ADDRESS` unset. `runregistrykit
  list`: 4 runs, 4 finished (`reference` `done`, `resumed-a` `killed`, `resumed-b` `lost`,
  `resumed-c` `done`); nothing `running`, stale or unknown. `var/` holds 04's two stores with their
  sidecars, the four run directories and `var/rrk-adoption-04/`.
- **The venv.** `pip freeze` kept in `orch05/pip-freeze-dispatch.txt` (84 lines). A manifest's
  `packages` names `datastorekit` 0.5.0 (`f47b9a25…`), `raypoolkit` 0.3.0 (`67a75b97…`) and
  `runregistrykit` 0.2.0 (`0bae3a3c…`, `requested_revision` `v0.2.0`), none editable; the config's
  `distributions` are `["datastorekit", "raypoolkit"]` (checklist item 9, point 3).
- **RunRegistryKit**: clean, `main` at `70ee1e8`, `v0.2.0` on `0bae3a3`. ChamPBH clean at `58c1c93`.
- **Baselines**, serially, at `39fc819`: see §1.

**What moves on purpose:** the prompt's §5 list. **What must not move:** every `.py` file but the
two docstrings; `main.py` and the plot scripts (`git diff 1c223e8` empty); every test's code; the
board's §5.0–§5.6 and its decisions; every dated note; `verification.md` §1; `dk-and-rpk-migration`'s
records; `var/`; the venv; RunRegistryKit, ChamPBH, DatastoreKit and RayPoolKit.

**Conventions.** All of these bind the agent.
- **Staging and reporting.** One commit, at the end, staged by explicit path only, after showing
  `git diff --cached --name-only`. Count, then paste. "this commit" where the SHA goes.
- **Suites.** `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`
  and `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`,
  serially, in the foreground, output to a file in the scratch directory, the verdict grepped,
  `uptime` beside each; before the edits and after. `slow` is not run. No cluster is started. A
  failure is re-run alone before it is called real.
- **Scratch** is the agent's own subdirectory of the session scratchpad, never `/tmp`.
- **Stop conditions are real**: the prompt's §4, and corrections 2, 4 and 11 here (a clause that
  does not hold). A stop goes to the user through the orchestrator; the agent resumes by message.
- **Other sessions** may land commits on this branch. Check `git log` before committing.

## 1. Before you dispatch

1. The Gate, as §0's facts.
2. **Baselines**, both suites serially at `39fc819` (`orch05/default.txt`, `orch05/integration.txt`),
   with the load.
3. `pip freeze` kept for the review.
4. **The commit of this note**, alone, staged by path.

**Done at dispatch (2026-10-25):** the Gate as §0; the baselines at `39fc819`, serially: default
**848** (847 passed, 1 skipped, 141 deselected), 42 s, load 5.2; `RAY_ADDRESS=local … -m
integration` **72** (71 passed, 1 skipped), 68 s, load 5.2 → 18.6. 04's counts.

## 2. Dispatch

One fresh-context subagent, on **Sonnet**, in the main checkout. Give it the prompt, the README, the
board, `HEAD`, the baselines, and §0 of this note up to "## 1. Before you dispatch", as a copy in the
session scratchpad. The agent does not read `orchestrator/`.

Tell it plainly:
- **One commit, at the end**, with the results note `.documents/rrk-adoption/05-close.md` in
  `dk-and-rpk-migration` README §5.1's form, holding §2's verification.
- **The files it may change are the prompt's §5 list, and nothing else.**
- **§0's corrections** bind it, each recorded with its class.
- **Stop and ask** on any of the prompt's §4 conditions or §0's.
- **It replies with:** the commit's SHA, message and `--stat`; `git diff --numstat` on `.documents/`;
  the dated-note `diff` and the two `ast` results; the counts as edited; the two drafts whole; the
  six `v0.2.0` checks with their greps and hits; the citation list's length and anything it could
  not find; the indexes' counts; the suites before and after, with the load; `runregistrykit list`;
  every deviation with its class; "State handed to the next prompt", verbatim.

## 3. The review — eleven checks

1. **Scope.** `git show --stat <agent>` is the prompt's §5 list. `git status --short` clean.
   `git diff --name-only 39fc819 <agent> -- '*.py'` is `utilities.py` and
   `tests/test_inventory_specs.py`. `git diff 1c223e8 <agent> -- main.py plot_InstantonSolutions.py
   plot_GradientCoupledSolutions.py` empty. Nothing pushed; `main` unmoved.
2. **`ast`.** Both `.py` files `ast`-equal at `39fc819` and the agent's commit, docstrings removed,
   by the orchestrator's own script. `utilities.py`'s diff is the one sentence and its paragraph's
   reflow.
3. **Dated records.** Every italic dated line of the three Z1 documents, extracted at `39fc819` and
   after, `diff`ed: identical but for the two new ones. The board's §5.0–§5.6 and decisions, and
   `verification.md` §1, byte-identical (`git diff` shows additions only there).
4. **Z1 against correction 5**, by reading: §13 covers the five points, true to 03's and 04's
   records (`HEARTBEAT_MEANS`, the paths, the commands, the sidecar); the tree and the file lists
   have the entries with comments; the pointers.
5. **Z2.** The counts against collection at the agent's commit (989; 848; 72; 69). No other line of
   `CLAUDE.md` or the rules moved, but a sentence the agent shows is wrong.
6. **Z3.** The three texts present-tense, naming `rrk-adoption`; the `utilities.py` sentence verbatim.
7. **Z4, the drafts.** Each clause of checklist item 9 (points 1–5) and the G3 draft's six checks,
   §2 and §4, checked against the tree, `var/runs/` and the committed records it names. Every SI
   commit named exists. Nothing claimed that no record shows. §3's handover against README §7 and
   `dk-and-rpk-migration/verification.md` §4.5, which is unchanged.
8. **Citations.** A sample of the agent's list (every RunRegistryKit path and line, every run id,
   and ten others) resolved here.
9. **Z5.** The board: header COMPLETE with the final suites, every §1 row ✅, §2 with RunRegistryKit's
   gates "drafted, the user's", §3 and §4 as they stood, `### 5.7`. `INDEX.md`: header, row,
   "Planned". `OPEN-ISSUES.md`: 58 open by counting, §6b's sentence, the date.
10. **The note.** §5.1's form; every deviation classed; §2's six verifications with their output.
    The message ends with the `Co-Authored-By` line.
11. **The suites** at the agent's commit, serially: default 848, `integration` 72. `runregistrykit
    list` the same four runs; `var/` the same files; `pip freeze` equal to the dispatch copy.

## 4. After the review

If it passes, residue in a follow-up commit of its own:
- "this commit" → the SHA, on the board, in the note, in `verification.md` and in `INDEX.md` (and
  in the drafts only if they name 05's commit, which correction 11 forbids);
- the board's list of orchestrator notes gains this one, "used for 05";
- `### 5.7` gains an *Orchestrator review of prompt 05* paragraph: what each check found.
- Prompt 05 is left as it ran; the paragraph names corrections 1, 2, 3 and 4.

Anything that is not residue is opened on the board's §3 and in `OPEN-ISSUES.md` in the same commit.

**Report to the user:** the message as committed; the corrections that read the prompt otherwise
than it was written (the section, 1; the boards at `main`, 2; the pin added, not moved, 3; the
`v0.2.0` checks apply, 4); where the drafts are, to paste into RunRegistryKit's two rows; and what
is left to the user (§5.7): the merge into `main`, the two records, `var/`, and README §7's
observation.
