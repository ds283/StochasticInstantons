# Prompt 05 — close

**Campaign:** [`README.md`](README.md) · **Board items:** **Z1**–**Z5** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-23, with 01–04, after the user's rulings. Its orchestrator note, written after
04's review, hands it the counts and findings of 01–04, and governs where it differs from this file.
**Gate:**
- 01–04 landed and reviewed, with the gates "Pin", "Fingerprint", "Wrapper" and "R" holding (board
  §2);
- on branch `rrk-adoption`, no tracked change in `git status`;
- no SI Ray process is running, and `./venv/bin/python -m runregistrykit list` shows nothing
  `running`, stale or unknown. You start nothing.

**Closes:** the campaign; no §3 issue. **Opens:** what 01–04's results notes left as observations,
if the orchestrator note says to open them.
**Recommended model:** **Sonnet**. Prose and records, two drafts for another repository, and one
final measurement.

**Read first:**

1. [`README.md`](README.md): §1, §2.2 (05's charter), §5, §6.0, §6.2 (P12, P13), §7.
2. This board in full; results notes 01–04 (`.documents/rrk-adoption/0N-*.md`): "What shipped",
   "Observations not acted on" and "State handed to the next prompt".
3. `.documents/rrk-adoption/verification.md` §1, which 04 created.
4. The documents Z1 edits: `.documents/architecture-summary.md`, `.documents/INFRASTRUCTURE.md` and
   `.documents/FILE_MAP.md`. Find where each describes the tree, the drivers and the datastore
   packages, and how each marks a dated note.
5. P12's three places: `.claude/rules/datastore-factories.md:240`, `tests/test_inventory_specs.py:33`
   (in its module docstring) and `utilities.py:191` (in `installed_package_provenance`'s docstring).
6. RunRegistryKit at `v0.2.0` (read, never edit):
   - `prompts/extraction/IMPLEMENTATION_STATE.md` §2, row **G4**, and rows G2 (SGK) and G3
     (ChamPBH) above it, for the form;
   - `prompts/interrupted-runs/IMPLEMENTATION_STATE.md` §2, row **G3**, and row G1 (SGK) for the
     form;
   - `docs/adoption/stochasticinstantons.md` item 9, the acceptance a G4 record quotes, and
     `docs/adoption/v0.2.0/stochasticinstantons.md` §1, the checks of the `v0.2.0` note.
7. `.documents/dk-and-rpk-migration/verification.md` §4.3: how this repository drafted two G4
   records for its packages' boards; and ChamPBH's `.documents/rrk-adoption-verification.md` §2,
   its drafts of the same two RunRegistryKit records.
8. `CLAUDE.md`, `.claude/rules/test-selection.md`, [`.prompts/INDEX.md`](../INDEX.md) and
   [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md).

---

## 1. What is wanted

The repository says what the campaign changed. Phase 2's builds know how to launch through the
registry and what to do after a hard kill. RunRegistryKit's two gates have their records drafted for
the user to commit there.

### 1.1 The items

- **Z1 — the descriptive documents.** `.documents/architecture-summary.md`,
  `.documents/INFRASTRUCTURE.md` and `.documents/FILE_MAP.md` describe the code. Their dated notes
  are records, and are kept byte for byte.
  - Each tree or file list gains, with a comment: `RunDrivers/` (the wrapper), `runregistrykit.toml`,
    `config/fingerprint.py`, `.claude/settings.json` (the discovery hook), and `var/` (ignored:
    `var/runs/`, `var/datastores/`).
  - Where a document describes the datastore packages or the drivers, one dated note, in the form
    of the existing ones, says: what the registry records and where; that a registered run is
    launched through `RunDrivers/registered_run.py`, and `main.py` stays launchable without it;
    what the heartbeat means; the fingerprint format and its guard; that the store's sidecar is
    made by a person after its first close. One document holds the note; the others point at it.
- **Z2 — `CLAUDE.md` and the rules.**
  - The section 01 wrote, as 03 made it definite: anything 04 found that it states wrongly.
  - The test counts: `CLAUDE.md`'s "Build and test" and `.claude/rules/test-selection.md` (its
    counts of the default selection, of `integration` and of the total) are 04's final ones. No
    file becomes `slow`; say so.
  - Nothing else changes.
- **Z3 — the stale prose (P12).**
  - `.claude/rules/datastore-factories.md:240` and `tests/test_inventory_specs.py:33`: "will take"
    and "which SI adopts after this campaign" become present tense, naming `rrk-adoption`. The test
    file's change is to its docstring only (README §5); show by `ast` that its code is unchanged.
  - **`utilities.py`, which is on `CLAUDE.md`'s protected list.** This prompt names it and the one
    change: in `installed_package_provenance`'s docstring, after the sentence that ends "so that a
    later move to a shared registry is a substitution (README P5).", add one sentence:
    "`rrk-adoption` declined the substitution (its README §6.0, R3): `main.py` and the plot scripts
    would then import `runregistrykit`, and they stay launchable without it." Nothing else in the
    file changes; show by `ast` that its code is unchanged.
- **Z4 — RunRegistryKit's gate records, drafted (P13), and the handover.** Two new sections of
  `.documents/rrk-adoption/verification.md`:
  - **§2, the drafts**, in the form of `dk-and-rpk-migration/verification.md` §4.3, each a table
    cell's text ready to paste, naming this repository's commits:
    - **`extraction` board, G4**: SI adopted a release, `v0.2.0` directly. It quotes the checklist's
      item 9, point by point, with where each holds: the pin and the venv (01); the config and
      `var/` (01); one `begin` … `finish` run listed with its `packages` (04); the helper not
      substituted (R3: point 4 does not apply, and why); the store layer, with a fingerprinter that
      loads and `store fingerprint` reading a closed store (02, 04);
    - **`interrupted-runs` board, G3**: SI adopted `v0.2.0`, its pin moved in a commit of its own
      (01's first). It says which of the `v0.2.0` note's §3 checks applied (none of SI's code
      predates the adoption), and that the hard-kill route was rehearsed (04, H3).

    **Nothing is written in RunRegistryKit.** The user commits the records there.
  - **§3, the handover to Phase 2**: how a build is launched through the wrapper (the four flags,
    the slug matching `--job-name`, detached, into `var/datastores/`); `store create --purpose …`
    after a store's first close; the route after a hard kill (`end`, then the build again); that
    the plot scripts and `--inventory` stay unregistered; that a gradient-branch build may show
    stale while it works (P7); and 04's stores and runs under `var/`, kept until the user removes
    them. It adds to `dk-and-rpk-migration/verification.md` §4.5, Phase 2's handover, by statement,
    and does not edit it.
- **Z5 — the records.**
  - **This board closes.** The status line says **COMPLETE**, with the final suites. Every §1 row
    is ✅; §2's gates, with RunRegistryKit's left "drafted, the user's"; §3 and §4 as they stand. A
    final `### 5.6 After prompt 05 (<date>)` lists what is left to the user: the merge into `main`
    (R7); the two gate records (Z4); 04's stores and runs; the observation of README §7 on the
    wrapper's generic part.
  - **`.prompts/INDEX.md`**: the row **complete**, in `dk-and-rpk-migration`'s form, with the date,
    the final suites and the open-issue column from counting; the header's count and date; the
    paragraph under "Planned" on this campaign made past tense.
  - **`.documents/OPEN-ISSUES.md`**: anything 01–04 opened, as the board holds it; the header's
    count by counting and its date.

---

## 2. Verification

1. **The suites**, before and after: the default selection and `integration`, at the counts 04
   handed on. `slow` is not run (no prompt touched its paths).
2. **The documents are additive** where they are records. `git diff --numstat` on `.documents/`
   shows deletions only in descriptive lines and in `OPEN-ISSUES.md`'s header. Extract every dated
   note of the three Z1 documents at `HEAD` and after your edits, and `diff` them: identical but for
   what Z1 adds.
3. **`ast`-equal code**: `utilities.py` and `tests/test_inventory_specs.py`, before and after, with
   docstrings removed.
4. **Every citation exists.** Every path, function, option, run id and line that Z1–Z4 name exists
   in the tree, in `var/runs/` or in RunRegistryKit at `v0.2.0`. Give the list in the results note.
5. **The index.** `.documents/OPEN-ISSUES.md`'s count equals its rows by counting, and
   `.prompts/INDEX.md` agrees with this board.
6. `./venv/bin/python -m runregistrykit list`: the runs of 04, as 04 recorded them, and nothing new.

## 3. Acceptance

1. Z1–Z5 as §1.1 says, and §2 in the results note.
2. **No deliberate breakage**: 05 adds no code and no test.
3. **One commit**, with the results note `.documents/rrk-adoption/05-close.md` in the template of
   `dk-and-rpk-migration` README §5.1. Write "this commit" where the SHA goes.

## 4. Stop conditions: stop and ask

- A gate does not hold when you start.
- A sentence of a dated record would need rewriting rather than adding to.
- A count moves.
- A draft of Z4 cannot be written true: a point of the checklist's item 9 does not hold and is not
  explained by a ruling.
- Anything would need an edit to RunRegistryKit, to a sibling, or outside §5.

## 5. What this prompt does not do

- **Files it changes:**
  - `.documents/architecture-summary.md`, `.documents/INFRASTRUCTURE.md`, `.documents/FILE_MAP.md`;
  - `CLAUDE.md`, `.claude/rules/test-selection.md`, `.claude/rules/run-registry.md` (if Z2 finds a
    sentence wrong), `.claude/rules/datastore-factories.md`;
  - `tests/test_inventory_specs.py` (docstring) and `utilities.py` (docstring);
  - `.documents/rrk-adoption/verification.md` (§2 and §3 added);
  - `.documents/OPEN-ISSUES.md`, `.prompts/INDEX.md`;
  - this board, and the results note.
- No code, no new test, no script, no store, no run. It does not merge the branch, and writes
  nothing in another repository.

**One commit** in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
