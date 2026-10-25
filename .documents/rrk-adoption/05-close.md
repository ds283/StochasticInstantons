# 05 — close

**Subject:** Close `rrk-adoption`: the descriptive documents, `CLAUDE.md` and the rules, the stale prose, RunRegistryKit's two gate records drafted, the handover to Phase 2, and the records
**Commit:** `5bd486d`, on branch `rrk-adoption`, on top of `085f45f`
**Date:** 2026-10-25, by Claude Sonnet 5.5
**Result:** **COMPLETE.** Z1–Z5 done; the campaign closes. 05 adds no code and no test: two docstrings change (`utilities.py`, `tests/test_inventory_specs.py`), each `ast`-equal without docstrings. Suites before and after, serially: default 848 (847 passed, 1 skipped, 141 deselected) and `integration` 72 (71 passed, 1 skipped), the baselines. `slow` was not run: no prompt touched its paths, and no file became `slow`. Counts by collection: 848 + 72 + 69 = 989, disjoint. `.documents/OPEN-ISSUES.md` stays at 58 open; no issue is opened or closed. No §4 stop condition was met.

Prompt: [`.prompts/rrk-adoption/05-close.md`](../../.prompts/rrk-adoption/05-close.md). The orchestrator's brief for 05 governed where it differs from the prompt: its eleven corrections are deviations 1–11 below. Scratch outputs were kept outside the repository.

## What shipped

- **Z1 — the descriptive documents.** The three documents' dated notes are kept byte for byte (§2 below).
  - [`INFRASTRUCTURE.md`](../INFRASTRUCTURE.md) holds the note, as a new last section, **§13 "The run registry — `runregistrykit`"**, headed by a dated italic line in the existing form. It says what the registry records and where (`var/runs/<run id>/`: `manifest.json`, `status.json`, `stdout.log`, `stderr.log`; a store's sidecar `var/datastores/<stem>.manifest.json`); that a registered run is launched through `RunDrivers/registered_run.py` and `main.py` stays launchable without it, and why (R2, R3, R5); what the heartbeat means, with the 900 s window and the gradient branch; the fingerprint (format 1, `SPEC_DIGESTS`, the guard `tests/test_fingerprint_format_guard.py`, the golden file `tests/data/store_fingerprint_rrk-adoption-02.json`, never overwritten); and that the sidecar is made by a person after the first close (R4). It cites RunRegistryKit's `README.md` at `v0.2.0` and `.claude/rules/run-registry.md` and does not copy them. The title becomes "how SI uses `datastorekit`, `raypoolkit` and `runregistrykit`", and the opening paragraph gains one sentence pointing at §13. §1's list is not changed.
  - [`architecture-summary.md`](../architecture-summary.md): the "Repository layout" tree gains `RunDrivers/registered_run.py`, `runregistrykit.toml`, `.claude/settings.json`, `var/` and `config/fingerprint.py`, and `runregistrykit` in its packages block, each with a comment. Under the section's existing italic line, one new italic line (`*Extended 2026-10-25 …*`). "main.py — the orchestrator" gains one sentence that a registered run launches it through the wrapper.
  - [`FILE_MAP.md`](../FILE_MAP.md) has no dated notes. §1's table gains rows for `config/fingerprint.py` (`config_fingerprint.py`), `runregistrykit.toml` and `RunDrivers/registered_run.py` (`RunDrivers_registered_run.py`); "Files not included" gains `RunDrivers/__init__.py`, `.claude/settings.json` and `var/`, each with a reason.
- **Z2 — `CLAUDE.md` and the rules.** `CLAUDE.md`'s "Build and test" and `.claude/rules/test-selection.md` carry 989 tests, 848 selected by default (847 pass, 1 skipped), 141 others, of which 72 `integration` and 69 `slow` (`CLAUDE.md:35-38`; `test-selection.md:10`, `:26`, `:60-61`). **No file became `slow`**: the slow table is unchanged. The section 01 wrote and `.claude/rules/run-registry.md` were read against `verification.md` §1 and 04's note: no sentence is wrong, so neither changed.
- **Z3 — the stale prose (P12).**
  - `.claude/rules/datastore-factories.md:239-240`: "which RunRegistryKit will take for SI in the next infrastructure campaign" is now "which RunRegistryKit takes for SI (`rrk-adoption`, `config/fingerprint.py`)".
  - `tests/test_inventory_specs.py:33-34`, in the module docstring only: "which SI adopts after this campaign" is now "which SI adopted in `rrk-adoption` (`config/fingerprint.py`)", the bullet re-wrapped.
  - `utilities.py:191-193`, in `installed_package_provenance`'s docstring, after "(README P5).": "`rrk-adoption` declined the substitution (its README §6.0, R3): `main.py` and the plot scripts would then import `runregistrykit`, and they stay launchable without it." Nothing else in the file changes. The paragraph was re-wrapped at its existing width.
- **Z4 — RunRegistryKit's gate records, drafted, and the handover.** [`verification.md`](verification.md) §2 holds the two drafts, whole, each a table cell's text ready to paste (§2.1 `extraction` `G4`; §2.2 `interrupted-runs` `G3`), the checks made for them, and §2.3 what they do not claim. §3 is the handover to Phase 2. Nothing is written in RunRegistryKit, ChamPBH or any other repository.
- **Z5 — the records.**
  - The board: status **COMPLETE** with the final suites, row 05, Z1–Z5 done, the RunRegistryKit gates "drafted … the user's to commit", and `### 5.7 After prompt 05 (2026-10-25)`, which lists what is left to the user.
  - `.prompts/INDEX.md`: the row is **complete 5 / 5 on 2026-10-25**; the header is 8 campaigns, 0 ready, 0 live, 1 halted, 7 complete; the "Planned" paragraph on this campaign is past tense.
  - `.documents/OPEN-ISSUES.md`: 58 open by counting, 31 closed, unchanged; §6b's introduction says the campaign closed and its board stays the record.

## Deviations from the prompt

The first eleven are the orchestrator brief's corrections.
1. **`STRUCTURALLY REQUIRED`: the board section is `### 5.7`, not `### 5.6`.** §5.6 is 04's.
2. **`STRUCTURALLY REQUIRED`: RunRegistryKit's two boards are read at `main`, not the tag.** At `v0.2.0` the `interrupted-runs` board's `G1` reads "not yet" and SGK's record is on `main` only. Both boards were read at `70ee1e8`, through `git show`; the checklist, the `v0.2.0` note and `docs/adoption/v0.2.0/README.md` at `v0.2.0`. The rows are `extraction:1130` (`G4`; form `G2` at `:1128`) and `interrupted-runs:1182` (`G3`; form `G1` at `:1180`). ChamPBH's rows (`:1129`, `:1181`) still read "not yet", so the form for ChamPBH is its drafts, `.documents/rrk-adoption-verification.md` §2 at `58c1c93`.
3. **`STRUCTURALLY REQUIRED`: SI's pin was added, not moved.** `git log -S runregistrykit -- requirements.txt` gives `60687f0` alone, one inserted line (`requirements.txt:63`). The `G3` draft says "added at `v0.2.0`, in a commit of its own" and that the `v0.1.0` to `v0.2.0` move of the note's §1 did not arise. (`requirements.txt` was also touched in this branch's history by `3d6328e`, the `raypoolkit` pin of `rpk-v030-adoption`, and by the merge `24e641f`; the draft says `60687f0` is the one commit of *this campaign* to touch it.)
4. **`STRUCTURALLY REQUIRED`: the `v0.2.0` checks are `docs/adoption/v0.2.0/README.md` §3, and they apply.** The `G3` draft goes through the six, each by `git grep` over SI's tracked tree excluding `.prompts/` and `.documents/`, and says §2 of that README holds trivially (one checkout; `git worktree list` shows it alone) and §4 is `.claude/rules/run-registry.md`'s route, rehearsed in 04 (H3). The greps and every hit are in `verification.md` §2 and below.
5. **`IMPLEMENTATION CHOICE`: where the Z1 note lives.** `INFRASTRUCTURE.md` §13 (with its title and one opening sentence), as the brief ruled; `architecture-summary.md` and `FILE_MAP.md` as listed under Z1 above. All three of `FILE_MAP.md`'s new rows' purpose cells point at §13, not one.
6. **`NOTED`: the test counts, measured here.** By collection: 989 tests; default 848; `integration` 72; `slow` 69; `integration and slow` none. `CLAUDE.md:35-38` and `test-selection.md:10`, `:26`, `:60-61` follow. The last is a dated sentence of a rules file, a current statement and not a record, so it **becomes** "At the close of rrk-adoption the markers selected 72 `integration` tests (71 pass, 1 is skipped) and 69 `slow` tests, disjoint, so 848 + 72 + 69 = 989", as ruled; it is not a stop.
7. **`NOTED`: Z2's sentence check found nothing.** The section "Long-running jobs — the run registry" of `CLAUDE.md` and `.claude/rules/run-registry.md` were read against `verification.md` §1 and found right. Observation: `CLAUDE.md`'s "Protected infrastructure" names two packages (`datastorekit`, `raypoolkit`), not `runregistrykit`; an omission, not a wrong sentence, and Z2's "nothing else changes" holds.
8. **`NOTED`: P12's exact texts**, as the brief gives them (above, Z3). For `utilities.py` the sentence was added and the lines of that one docstring paragraph were re-wrapped at the existing width (the paragraph's later sentences move down two lines); the `ast` check is §2.3.
9. **`NOTED`: the indexes.** 58 open rows by counting, 31 closed, unchanged: no issue opened, narrowed or closed. §6b's introduction gains that the campaign closed on 2026-10-25. The header's date was already 2026-10-25. The header's paragraph "One campaign has a status board …" is stale (three campaigns have one) and is not 05's: an observation. `INDEX.md` as under Z5.
10. **`NOTED`: nothing is opened.** The observations of 01–04's notes are left as those notes hold them; §5.7 lists for the user what the brief names.
11. **`STRUCTURALLY REQUIRED`: what the drafts name.** Only SI commits that exist (`60687f0`, `7071bb8`, `0fcaf7c`, `16e1cc1`, `29705f2`, `1c223e8`, `39fc819`), none of 05's own. Every count and digest in them is copied from a committed record and the record named. They claim nothing about RunRegistryKit's own tests or CI; §2.3 says what they do not claim.

And five of mine.
12. **`NOTED`: one deletion in `OPEN-ISSUES.md` is a line of §6b's introduction, not the header.** The brief ruled that sentence ("§6b's intro sentence gains …"); the prompt's check allows deletions "in `OPEN-ISSUES.md`'s header" only. It is a one-line replacement of a sentence by itself plus an addition.
13. **`IMPLEMENTATION CHOICE`: the first grep of check 1 was refined.** `foreign` alone matches SQL foreign keys throughout `Datastore/` (hundreds of lines); the check is for `liveness`'s fifth value, so the final pattern is `liveness`, the string `"foreign"` and the string `"stale"`.
14. **`NOTED`: the "five hold" slip, caught.** The first text of `G4` said "five hold and one is this record"; it is four hold, one does not apply (point 4) and one is this record, as ChamPBH's draft says. Corrected before the commit.
15. **`NOTED`: the second suite pair ran while the records were being written.** No test reads a `.md` file, and both `.py` docstring edits were made before it started, so the code it ran is the code committed.
16. **`NOTED`: the verification document's §2 names "this commit" nowhere.** The prompt's "write 'this commit' where the SHA goes" applies to this note, the board and `INDEX.md`; the drafts, as the brief rules, name none of 05's.

## Verification performed

Every check is the prompt's §2, in its order.

**1. The suites, before and after** (`./venv/bin/python -m pytest … -q -p no:cacheprovider`, serially, in the foreground, output to files in the scratch directory; `RAY_ADDRESS` unset, integration under `RAY_ADDRESS=local`; no cluster started; `slow` not run). The orchestrator's baselines at `39fc819` were default 848 (847 passed, 1 skipped, 141 deselected), 42 s, and `integration` 72 (71 passed, 1 skipped), 68 s.

| Selection | Before my edits | After my edits |
|---|---|---|
| default, `-m "not integration and not slow"` | **848**: 847 passed, 1 skipped, 141 deselected; 43.4 s (16:51:42–16:52:29); load 5.25 → 4.66 | **848**: 847 passed, 1 skipped, 141 deselected; 40.7 s (16:59:14–16:59:59); load 3.57 → 5.72 |
| `RAY_ADDRESS=local`, `-m integration` | **72**: 71 passed, 1 skipped, 917 deselected; 70.0 s (16:52:29–16:53:40); load 4.66 → 18.72 | **72**: 71 passed, 1 skipped, 917 deselected; 70.0 s (16:59:59–17:01:10); load 5.72 → 15.70 |

The load is `uptime`'s one-minute figure at the start and the end of each run. Nothing failed, so nothing was re-run. The counts equal 04's final ones and the baselines.

**2. The documents are additive where they are records.** `git diff --cached --numstat 39fc819 -- .documents/` (`<added> <deleted> <path>`):

```text
17	1	.documents/architecture-summary.md
6	0	.documents/FILE_MAP.md
98	1	.documents/INFRASTRUCTURE.md
1	1	.documents/OPEN-ISSUES.md
233	0	.documents/rrk-adoption/05-close.md
198	0	.documents/rrk-adoption/verification.md
```

Deletions: `INFRASTRUCTURE.md` 1 (the title line), `architecture-summary.md` 1 (the `main.py` paragraph's last line, re-wrapped with the added sentence), `OPEN-ISSUES.md` 1 (a line of §6b's introduction; deviation 12). Each is a descriptive line. Every dated note of the three Z1 documents, extracted at `HEAD` and from the working tree and compared (script below), is identical but for what Z1 adds:

```text
== .documents/architecture-summary.md: 5 dated notes at HEAD, 6 now
--- HEAD
+++ now
@@ -1,0 +2 @@
+*Extended 2026-10-25 by rrk-adoption prompt 05 (the run registry's entries); what the registry records is `INFRASTRUCTURE.md` §13.*
== .documents/INFRASTRUCTURE.md: 6 dated notes at HEAD, 7 now
--- HEAD
+++ now
@@ -6,0 +7 @@
+*Written 2026-10-25 by rrk-adoption prompt 05; the campaign's plan is `.prompts/rrk-adoption/README.md`, its record `.documents/rrk-adoption/verification.md` §1.*
== .documents/FILE_MAP.md: 0 dated notes at HEAD, 0 now
```

```python
"""Extract every dated note (a line that is a single italic sentence beginning 'Rewritten', 'Written' or
'Extended' and a date) of the three Z1 documents at REV and in the working tree; print a unified diff
per document. Usage: dated_notes.py REV"""
import re, subprocess, sys, difflib
rev = sys.argv[1]
pat = re.compile(r"^\*(Rewritten|Written|Extended) 20\d\d-\d\d-\d\d .*\*$")
for p in (".documents/architecture-summary.md", ".documents/INFRASTRUCTURE.md", ".documents/FILE_MAP.md"):
    old = subprocess.run(["git", "show", f"{rev}:{p}"], capture_output=True, text=True, check=True).stdout.splitlines()
    new = open(p).read().splitlines()
    a = [l for l in old if pat.match(l)]
    b = [l for l in new if pat.match(l)]
    print(f"== {p}: {len(a)} dated notes at {rev}, {len(b)} now")
    for l in difflib.unified_diff(a, b, "HEAD", "now", lineterm="", n=0):
        print(l)
```

**3. `ast`-equal code.** Each file parsed at `HEAD` and from the working tree, every docstring removed (the first statement of a module, class or function body when it is a string constant), `ast.dump` compared:

```text
utilities.py: ast equal without docstrings: True; ast equal with docstrings: False
tests/test_inventory_specs.py: ast equal without docstrings: True; ast equal with docstrings: False
```

```python
"""ast-equal check: parse each file at a git revision and from the working tree, remove every
docstring (the first statement of a module, class or function body when it is a string constant),
compare ast.dump. Usage: ast_equal.py REV PATH [PATH ...]"""
import ast, subprocess, sys

DOC = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

def strip(tree):
    for node in ast.walk(tree):
        if isinstance(node, DOC) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.dump(tree)

rev, paths = sys.argv[1], sys.argv[2:]
ok = True
for p in paths:
    old = subprocess.run(["git", "show", f"{rev}:{p}"], capture_output=True, text=True, check=True).stdout
    new = open(p).read()
    a, b = strip(ast.parse(old)), strip(ast.parse(new))
    full_equal = ast.dump(ast.parse(old)) == ast.dump(ast.parse(new))
    print(f"{p}: ast equal without docstrings: {a == b}; ast equal with docstrings: {full_equal}")
    ok &= a == b
sys.exit(0 if ok else 1)
```

Both give True without docstrings and False with them (the docstrings differ, as intended). `git diff --numstat HEAD -- utilities.py tests/test_inventory_specs.py`: `7 5` and `4 4`.

**4. Every citation exists.** 119 checks, run by a scratch script after the last edit (`found 119, missing 0`). The list, by group:
- **In the tree** (each path exists): `RunDrivers/registered_run.py`, `RunDrivers/__init__.py`, `runregistrykit.toml`, `config/fingerprint.py`, `config/datastore.py`, `.claude/settings.json`, `.gitignore`, `requirements.txt`, `CLAUDE.md`, `main.py`, both plot scripts, `utilities.py`, `tools/compare_stores.py`, `tests/test_fingerprint_format_guard.py`, `tests/test_store_fingerprint_golden.py`, `tests/data/store_fingerprint_rrk-adoption-02.json`, `tests/test_registry_config.py`, `tests/test_inventory_specs.py`, the six `tests/test_registered_run*.py` modules and `tests/registered_run_helpers.py`, the three rules files `.claude/rules/run-registry.md`, `test-selection.md` and `datastore-factories.md`, the three Z1 documents, `.prompts/INDEX.md`, `.documents/OPEN-ISSUES.md`, the board, `.documents/rrk-adoption/verification.md`, `.documents/rrk-adoption/rehearsal/build_registered.sh`, `.documents/dk-and-rpk-migration/verification.md` and its `rehearsal/ray_cluster.sh`.
- **Lines and names**: `requirements.txt:63` (the `runregistrykit[stores]` pin), `:16` (`datastorekit` `v0.5.0`), `:59` (`raypoolkit` `v0.3.0`); `.gitignore:23` (`var/`); `utilities.py:177` (`installed_package_provenance`); `tests/test_inventory_specs.py:455` (`"stale"`); `tests/test_registered_run_outcomes.py:238` (`"lost"`), its `TestBeginsRefusal` and `test_refused_then_accepted_after_end`; `TestGolden`, `TestConfigFingerprint` and `TestCommandLine`; `EXPECTED_KEYS`; `HEARTBEAT_MEANS`, `SPEC_DIGESTS`, `FINGERPRINT_FORMAT`, `fingerprinter`; the guard's 5 tests; the wrapper's flags `--campaign`, `--prompt`, `--register`, `--purpose`; `main.py`'s `--inventory`; `config/argument_parser.py`'s `--prune-unvalidated` and `--job-name`; the discovery hook's `runregistrykit list`; `ray_cluster.sh`'s `start`.
- **`var/`, run ids and records**: `var/`, `var/runs/`, `var/datastores/`, `var/rrk-adoption-04/`; the four run directories `rrk-adoption-04-reference-20261025T160704`, `…-resumed-a-20261025T161131`, `…-resumed-b-20261025T161352` and `…-resumed-c-20261025T161521`, each with its `manifest.json`; the two stores and their two sidecars (`store_id` `503640899e96453a968de535c5b677a8` and `b7904d18f0d24466b255fb7c0224a805` found in them); `.documents/rrk-adoption/out/04-<slug>.manifest.json` (four), `04-store.txt` (holds `a9f716fb…1ea7`), `04-refusal.txt` (holds pid 26796, the refusal's `is running (stale, pid 26796) and names this store` and `No run directory was created`), `04-checks.txt` (holds `end`'s line); the golden file (holds `e3437a9b…7c78`); 106 collected tests in `tests/test_registered_run*.py`.
- **Commits** (each resolves): `60687f0`, `7071bb8`, `0fcaf7c`, `16e1cc1`, `29705f2`, `ff3ddd6`, `edb03ea`, `39fc819`, `1c223e8`, `085f45f`, `535b7e7`, `24e641f`, `3d6328e`, `8b4f615`.
- **RunRegistryKit** (read with `git -C`): the tag `v0.2.0` is `0bae3a3c501a8264ee4be5bc24f06422af38720f`; `main` is `70ee1e8`; at `v0.2.0` `docs/adoption/stochasticinstantons.md` (its `## 9. Its acceptance`), `docs/adoption/v0.2.0/README.md` (`## 2.`, `## 3.`, `## 4.`), `docs/adoption/v0.2.0/stochasticinstantons.md`, and `README.md` (`## Using it`); at `main` the rows `prompts/extraction/IMPLEMENTATION_STATE.md:1130` (`G4`) and `:1128` (`G2`), and `prompts/interrupted-runs/IMPLEMENTATION_STATE.md:1182` (`G3`) and `:1180` (`G1`); the two issue names `[04-a-killed-process-not-yet-reaped-answers-kill-0]` and `[03-a-run-whose-manifest-cannot-be-read-names-no-store]` are in the repository.
- **ChamPBH** (read with `git -C`): `.documents/rrk-adoption-verification.md` §2 at `58c1c93`.
- **Not found / not claimed**: none missing. The drafts' `runregistrykit` fields (`packages`, `results_store_id`, the fingerprint) are read from the committed manifests, not from the running registry. The registry's own `docs/adoption/measure_client_registry.py` was not run (point 4 of item 9 does not apply, R3).

**The six checks of the `G3` draft** (`git grep` over SI's tracked tree, excluding `.prompts/` and `.documents/`; run as `bash` from the root after the last edit):

```text
## 1. a comparison with liveness's values
$ git grep -n -i -E 'liveness|"foreign"|'foreign'|"stale"' -- . :!.prompts :!.documents
.claude/rules/run-registry.md:19:2. **Liveness.** A run is alive iff its pid answers `kill -0` **and** its heartbeat is inside the
.claude/rules/run-registry.md:61:- `pgrep -f` (or any command-line match) as a liveness test.
tests/test_inventory_specs.py:455:    excluded = dict(EXCLUDED, FullInstantonValue="stale")
## 2. TERMINAL_STATES, and its fourth value
$ git grep -n -E 'TERMINAL_STATES' -- . :!.prompts :!.documents
$ git grep -n -w -E 'lost' -- . :!.prompts :!.documents (hits that name a run's state only)
.claude/rules/run-registry.md:39:   recorded `lost`.
notes/onion-model/onion_model.tex:1919:the response fields is lost, together with the one-multiply reinstatement
tests/test_registered_run_outcomes.py:238:        assert read_json(dead / "status.json")["state"] == "lost"
## 3. a store refusal's text
$ git grep -n -E 'Run\.finish|names this store|is running|runregistrykit end' -- . :!.prompts :!.documents
.claude/rules/run-registry.md:38:   `./venv/bin/python -m runregistrykit end RUN_ID --reason TEXT` on the host it ran on. The run is
.claude/rules/run-registry.md:43:A run stopped by `SIGTERM` needs no `end`: the wrapper records it `killed`. `Run.finish` is never
RunDrivers/registered_run.py:88:with `python -m runregistrykit end` (`.claude/rules/run-registry.md`, the route after a hard kill).
RunDrivers/registered_run.py:98:refused by `begin`, whose text names `python -m runregistrykit end`; nothing is created.
tests/test_registered_run_outcomes.py:170:    one `!! ` line naming `python -m runregistrykit end`, and nothing created. Once that run is
tests/test_registered_run_outcomes.py:228:        assert_one_refusal_line(refused, "python -m runregistrykit end")
## 4. a test that begins two unfinished runs on one store
$ git grep -n -E 'runregistrykit\.begin\(' -- '*.py' ':!.prompts' ':!.documents'
RunDrivers/registered_run.py:819:        run = runregistrykit.begin(
tests/test_registered_run_outcomes.py:68:run = runregistrykit.begin(
tests/test_registered_run_signals.py:85:        return runregistrykit.begin(
tests/test_registered_run_streams.py:158:        self.run = runregistrykit.begin(
## 5. a caller of pid_alive
$ git grep -n pid_alive -- . :!.prompts :!.documents
## 6. a test that pins a record's key set
$ git grep -n -E '(set|sorted|list)\(.*(manifest|status)|(manifest|status)[a-z_]*\.keys\(\)|"host"|"ended"|EXPECTED_KEYS' -- tests RunDrivers config
tests/registered_run_helpers.py:82:MANIFESTS_AT_START = sorted(_glob.glob({manifests!r}))
tests/test_registry_config.py:23:  deliberate one, so the test holds the exact set of keys: prompt 02 extends `EXPECTED_KEYS` with
tests/test_registry_config.py:45:EXPECTED_KEYS = {"runs_root", "stores_root", "distributions", "stores"}
tests/test_registry_config.py:59:    assert set(config) == EXPECTED_KEYS
```

Each hit holds: the two rules lines are prose, the `"stale"` string is a fixture reason in an unrelated test, `lost` in the outcomes test asserts that `end` records it, the `Run.finish` line says it is never called by hand, the wrapper's two lines are comments naming `end`, and the test hits name `python -m runregistrykit end` as the refusal's fragment. `begin(` is called in the wrapper and in three test modules, each beginning one run in a fresh temporary directory, except `TestBeginsRefusal`, which begins the second to assert the refusal and then `end` and the acceptance.

**5. The index.** `.documents/OPEN-ISSUES.md`'s header says **58 open**, 31 closed; its rows by counting (the `` | `[ `` rows above §7) are **58**. `.prompts/INDEX.md`'s header says 8 campaigns: 0 ready, 0 live, 1 halted, 7 complete (counted from its table: `rpk-v030-adoption`, `rrk-adoption`, `dk-and-rpk-migration`, `gradient-coupled-plotting`, `sparse-sampling`, `metadata-annotations` and `base-implementation` complete; `gradient-coupled-instanton` halted), and the `rrk-adoption` row says 5 / 5 complete on 2026-10-25 with its open-issue column `§6b; 1`, as the board does (one issue in §3, `[default-suite-starts-ray-in-process]`, listed in §6b).

**6. `./venv/bin/python -m runregistrykit list`** (exit 0), after the suites:

```text
   RUN                                        STATE      PROGRESS      AGE  PURPOSE · STAGE
   rrk-adoption-04-resumed-c-20261025T161521  done              -      47m  rrk-adoption 04 H4: the last resume of the resumed store, straight through  · Skipping gradient branch (--targets excludes 'gradient')
   rrk-adoption-04-resumed-b-20261025T161352  lost              -      49m  rrk-adoption 04 H3: a resume of the resumed store, killed with SIGKILL in STAGE 3  · STAGE 3: SLOW-ROLL INSTANTONS
   rrk-adoption-04-resumed-a-20261025T161131  killed            -      51m  rrk-adoption 04 H2: the rehearsal grid into the resumed store, interrupted with SIGTERM in STAGE 2  · STAGE 3: SLOW-ROLL INSTANTONS
   rrk-adoption-04-reference-20261025T160704  done              -      56m  rrk-adoption 04 H1: the rehearsal grid straight through, the reference store  · Skipping gradient branch (--targets excludes 'gradient')

4 run(s) under /Users/ds283/Documents/Code/StochasticInstantons/var/runs: 4 finished; 0 with no host recorded.
```

The runs of 04, as 04 recorded them, and nothing new.

**Gate, at the start.** Branch `rrk-adoption` on `085f45f`; `git status --short` empty; `git worktree list` the main checkout alone; `RAY_ADDRESS` unset; `list` as above with nothing `running`, stale or unknown; no Ray process was started by me and none was running. **Before commit:** `git log` checked for other sessions' commits.

## The deliberate-breakage record

None: 05 adds no code and no test (acceptance 2).

## Observations not acted on

- `CLAUDE.md`'s "Protected infrastructure" names `datastorekit` and `raypoolkit` and not `runregistrykit`. `runregistrykit` is pinned and never editable like them, and a defect in it is reported to its repository, not worked around. An omission, not a wrong sentence; not 05's by Z2's "nothing else changes".
- `.documents/OPEN-ISSUES.md`'s header paragraph "One campaign has a status board …" is stale: three campaigns have one now (`dk-and-rpk-migration`, `rpk-v030-adoption`, `rrk-adoption`).
- `INFRASTRUCTURE.md` §1's list is still "(a) and (b)" and says "Neither (a) nor (b) is SI's code", true of the two packages it names; §13 says the registry is neither.
- `FILE_MAP.md` describes a flat `claude-context/` bundle that no file of this repository holds; the new rows follow the form of the existing ones.
- The drafts' `G4` says "datastorekit at `:16`, `raypoolkit` at `:59`": these are the line numbers at `5bd486d`'s parent, and a later edit of `requirements.txt` moves them.

## State handed to the next prompt

`rrk-adoption` is complete and has no next prompt. For the user:
- **The merge of `rrk-adoption` into `main`** (R7). Nothing is pushed; the branch ends with the commit recording 05's review.
- **RunRegistryKit's two gate records**, to be committed there: `verification.md` §2.1 for `prompts/extraction/IMPLEMENTATION_STATE.md` §2 row `G4` (`:1130` at `70ee1e8`) and §2.2 for `prompts/interrupted-runs/IMPLEMENTATION_STATE.md` §2 row `G3` (`:1182`). Each replaces the row's second column. Bring "not merged into `main`" up to date, add a "Read here" clause, and re-check the line numbers.
- **04's stores, runs and launch logs** under `var/` (two stores with their sidecars, four run directories, `var/rrk-adoption-04/`), kept until the user removes them. Never `git clean -x` or `-X`.
- **The observation of README §7**: SI's wrapper is the third copy of SGK's; its generic part could be a module of RunRegistryKit. Whether to raise it there is the user's. And that RunRegistryKit's `end` stamps the lost status's `heartbeat` with its own time (04's observation 3, documented behaviour), which the user may raise there.
- **Phase 2's builds** launch through the wrapper: `verification.md` §3 (the four flags, the slug matching `--job-name`, detached, into `var/datastores/`; `store create --purpose …` after a store's first close; the route after a hard kill; the plot scripts and `--inventory` unregistered; a gradient-branch build may show `stale` while it works). It adds to `.documents/dk-and-rpk-migration/verification.md` §4.5 by statement and does not edit it.
- **Suites at the close:** default 848 (847 passed, 1 skipped), `integration` 72 (71 passed, 1 skipped), `slow` 69 (not run); 848 + 72 + 69 = 989.
- **No SI cluster is running and the lock is free** (nothing was started). The venv, RunRegistryKit, DatastoreKit, RayPoolKit, ChamPBH and SGK are untouched. `git revert` of `5bd486d` alone undoes 05 (records and two docstrings).
- **No issue opened;** `.documents/OPEN-ISSUES.md` is at 58 open.
