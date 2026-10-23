# Prompt 01 — the pin, the config and the rules

**Campaign:** [`README.md`](README.md) · **Board items:** **C1**–**C5** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-23, after the user's rulings (README §6). Measured at `8b4f615`; your own
measurement governs.
**Gate:**
- on branch `rrk-adoption`, at or after `1c223e8`, with no tracked change in `git status`
  (`git status --porcelain` empty);
- there is no `var/` at the repository root;
- no SI Ray process is running (`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
  status`). You start none.

If any of these fails, stop and ask.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Sonnet**. One requirement line, a config file, an ignore rule, a hook, two
pieces of prose, and one test module.

**Read first:**

1. [`README.md`](README.md): §0.1, §0.3, §2.2 (01's charter), §5, §6 (R1–R7, U1, P11).
2. RunRegistryKit's `README.md` at `v0.2.0`, read in its checkout
   (`/Users/ds283/Documents/Code/RunRegistryKit`; read, never edit): "Installing", "The client's
   root", "The rules", and "Ending a run whose end was never recorded".
3. The two models for the rules (read, never edit; adapt them, never copy their paths or their
   campaign history):
   - SecondaryGWKit's `CLAUDE.md` at `216e44d`, the section "Long-running jobs — the run registry"
     (`git -C /Users/ds283/Documents/Code/SecondaryGWKit show 216e44d:CLAUDE.md`, from `:87`);
   - ChamPBH's `CLAUDE.md` at `807f175`, its section of the same name.
4. This repository's `CLAUDE.md` in full, and two of `.claude/rules/`, for the form of a rules
   file: `test-selection.md` and `pool-read-apis.md`.
5. `requirements.txt` (`datastorekit` at `:16`; `raypoolkit` at `:59`), `.gitignore`, and
   `.claude/` (there is no `.claude/settings.json` today; `settings.local.json` is the user's and
   is ignored by the user's global git config).

---

## 1. What is wanted

This repository depends on RunRegistryKit `v0.2.0` with its store layer, says where its records go,
keeps them out of git, binds its agents to the registry's rules, and makes every session start by
reading the registry (U1). Nothing yet launches a registered run: 03's wrapper does that, and 02's
fingerprinter is what the store layer reads.

### 1.1 The items

- **C1 — the pin.**
  - Add `runregistrykit[stores] @ git+https://github.com/ds283/RunRegistryKit@v0.2.0` to
    `requirements.txt`, in its alphabetical place. No other line changes: `datastorekit`'s line at
    `:16` (`v0.5.0`) already satisfies the extra's floor (`>=0.4.0`).
  - Install it into the venv from the file: `./venv/bin/pip install -r requirements.txt`. **Never
    editable.**
  - Record `pip freeze` before and after. The only difference must be the one `runregistrykit`
    line; README §0.3's dry run found nothing else, and anything more is a stop.
  - **The package's own suite on the installed package.** Clone RunRegistryKit at the tag into a
    `tempfile` directory (`git clone --branch v0.2.0 <checkout> <tmp>`; its tests need a git work
    tree), and from that clone run `<SI>/venv/bin/python -m unittest discover -s
    runregistrykit/tests -t .` with **no** `PYTHONPATH`, so that the installed package is the one
    tested. Expect 410 tests, OK, one skipped. README §0.3's three failures came from a package on
    `PYTHONPATH` that a fresh interpreter could not see; they must pass here. Remove the clone.
- **C2 — the config, the ignore rule and the roots.**
  - A new `runregistrykit.toml` at the repository root, with a two-line comment naming this
    campaign and RunRegistryKit's README, and:
    ```toml
    runs_root = "var/runs"
    stores_root = "var/datastores"
    distributions = ["datastorekit", "raypoolkit"]
    ```
    The distributions are `utilities.RECORDED_DISTRIBUTIONS`'s (R3).
  - **No `[stores]` table**: 02 adds it with the module it names. Until then every store operation
    refuses for want of a fingerprinter, which is the package's behaviour, not a defect.
  - `.gitignore` gains `var/`, with a one-line comment saying what is under it (the registry's run
    directories and this repository's datastores; R6).
  - Create `var/runs/` and `var/datastores/`. The store operations refuse when the runs root is not
    a directory (README §0.3).
- **C3 — the rules.** Two pieces, in this repository's form: a short binding section in
  `CLAUDE.md`, and the detail in a rules file.
  - **`CLAUDE.md`**: a new section `## Long-running jobs — the run registry`, placed after "Build
    and test". At most about fifteen lines. It says:
    1. RunRegistryKit, pinned at `v0.2.0` with its store layer, records each registered run in
       `var/runs/`; `runregistrykit.toml` configures it. It records; it does not schedule,
       supervise, restart or lock;
    2. **discovery**: `./venv/bin/python -m runregistrykit list` at the start of a session (the hook
       of C4 runs it) and before launching anything long; report anything `running`, stale or
       unknown;
    3. registered runs are launched through the wrapper `RunDrivers/registered_run.py`, which
       prompt 03 of `rrk-adoption` adds. Write the sentence so that it is true now; 05 makes it
       definite. `main.py` stays launchable on its own, without the registry (R2), and an
       unregistered run is recorded nowhere. The plot scripts and `main.py --inventory` are never
       registered (R5);
    4. stores of registered runs live under `var/datastores/` (R6). Since `var/` is ignored,
       **never run `git clean` with `-x` or `-X`**, which deletes ignored files, the stores among
       them;
    5. the detail is `.claude/rules/run-registry.md`.
  - **`.claude/rules/run-registry.md`**, new, with no `paths:` frontmatter (so that it loads at
    session start, as the other rules files), in their form (a short statement of what it applies
    to, the rule, the failure it answers, and "What is forbidden"):
    1. **The six rules**, in RunRegistryKit's numbering, each in one or two sentences, with its
       README cited for the failures they answer: discovery; liveness (`kill -0` and the
       heartbeat, judged on the run's own host; never a command-line match such as `pgrep -f`);
       launch (detached, manifest first, pid recorded); do not babysit (one check after the
       launch, then end the turn); durability (`var/` under the root, never a scratchpad or
       `/tmp`); provenance;
    2. **the route after a hard kill**: `list` shows the run stale; a person checks; `./venv/bin/
       python -m runregistrykit end RUN_ID --reason TEXT` on its host; then the build again, which
       prunes unvalidated rows at open (`--prune-unvalidated` defaults to on). A `SIGTERM`ed run needs no `end`: it is recorded `killed`.
       `Run.finish` is never called by hand on a run that is not the caller's;
    3. **what `stale` means for SI**: a gradient-branch queue can print nothing for longer than the
       staleness window while it works (README P7). Stale means go and look, never kill;
    4. **the sidecar**: a person runs `./venv/bin/python -m runregistrykit store create PRIMARY
       --purpose TEXT` after a store's first close (R4); nothing in the code creates one;
    5. **what is forbidden**: polling a run in a loop; `pgrep -f` as a liveness test; `ray stop`
       (already `CLAUDE.md`'s); `git clean -x`/`-X`; a store of a registered run outside
       `var/datastores/`; deleting a run directory or a sidecar.

    Production runs are the user's: no campaign prompt starts one except a rehearsal its plan
    names. Keep the file as short as the model sections allow.

  Nothing else in `CLAUDE.md` changes, and no other rules file.
- **C4 — the discovery hook (U1).** A new `.claude/settings.json`, holding only a `SessionStart`
  hook that runs `./venv/bin/python -m runregistrykit list` in the project directory. Write it to
  the current Claude Code hooks schema (check it, and say where you checked). The hook must not
  fail a session when the venv or `var/runs/` is missing: its command degrades to a one-line
  notice. Nothing else goes in the file; the user's own settings stay in `settings.local.json`.
- **C5 — the test.** A new module, `tests/test_registry_config.py`, in the default selection (no
  marker), with no Ray, no store and nothing written outside a `tempfile` directory:
  1. `runregistrykit.find_client_root(client_root=<repository root>)` gives `runs_root` and
     `stores_root` equal to `<root>/var/runs` and `<root>/var/datastores`, and `distributions`
     equal to `("datastorekit", "raypoolkit")`;
  2. the config holds exactly the keys above (and, from 02 on, `[stores]`; write the test so that
     02 extends one expected set), so that a misspelt key cannot be added unnoticed;
  3. `git check-ignore -q var/runs/x var/datastores/x.sqlite`, run in the root by subprocess,
     exits 0;
  4. `runregistrykit.package_provenance(("runregistrykit",))` says 0.2.0, installed from
     `https://github.com/ds283/RunRegistryKit` at commit `0bae3a3…`, `requested_revision`
     `v0.2.0`, `editable` false: the pin's check, in the form of `tests/test_package_provenance.py`'s
     for the other two packages;
  5. `.claude/settings.json` parses as JSON and its `SessionStart` hook's command names
     `runregistrykit list`.

  The module's docstring says what it pins and why.

---

## 2. Verification

1. **Before any edit:** `pytest -m "not integration and not slow"` and `RAY_ADDRESS=local pytest -m
   integration`, serially, in the foreground, with the load (`uptime`). README §0.4's counts: 732
   (731 passed, 1 skipped) and 67 (66 passed, 1 skipped). `slow` is not run
   (`.claude/rules/test-selection.md`).
2. **After:**
   - `./venv/bin/pip show runregistrykit` and its `direct_url.json`: the tag's commit, not
     editable;
   - C1's suite run, its summary line;
   - `./venv/bin/python -m runregistrykit list` from the root: no runs, exit 0;
   - the hook's command, run by hand as the hook runs it, and once with `var/runs/` renamed aside
     (then restored): a notice, exit 0;
   - no store is opened or named by this prompt;
   - both suites: the default selection + C5's tests, `integration` unchanged.
3. **Deliberate breakages** (README §5: each recorded as a diff, never committed). Each must fail
   at least one C5 test, named in the log:
   - `var/` removed from `.gitignore`;
   - a misspelt key (`run_root`) in the config;
   - `distributions` reduced to `["datastorekit"]`.

## 3. Acceptance

1. C1–C5 as §1.1 says.
2. §2's checks, each with its command and its output, in the results note.
3. Suites: default 732 + C5's tests, all passing but the one skip; `integration` 67 (66 passed, 1
   skipped).
4. **Two commits**: first the pin alone (`requirements.txt`, in a commit of its own: README §2.2,
   01's item 1), then the rest, with the results note `.documents/rrk-adoption/01-pin-config-and-rules.md`
   in the template of `dk-and-rpk-migration` README §5.1. The board: row 01, C1–C5, the gate "Pin",
   and a `### 5.2 After prompt 01 (<date>)`. Write "this commit" where the second commit's SHA goes,
   and the first's SHA in full.

## 4. Stop conditions: stop and ask

- The install changes any distribution other than adding `runregistrykit`, or resolves a different
  `datastorekit`.
- The installed package is not `v0.2.0`'s commit (`0bae3a3`), or is editable.
- RunRegistryKit's suite fails on the installed package.
- An existing test fails.
- `list` or `find_client_root` behaves otherwise than RunRegistryKit's README says. That would be a
  package defect, reported there (README §5), never worked around here.
- The hooks schema cannot express a hook that degrades as C4 asks.
- Anything would need an edit outside §5's list.

## 5. What this prompt does not do

- **Files it changes:**
  - `requirements.txt` (one line);
  - `runregistrykit.toml` (new);
  - `.gitignore` (one rule and its comment);
  - `CLAUDE.md` (the new section of C3);
  - `.claude/rules/run-registry.md` (new);
  - `.claude/settings.json` (new);
  - `tests/test_registry_config.py` (new);
  - this board, and the results note.
- It writes no fingerprinter, no wrapper and no driver code. `main.py`, the plot scripts and
  `utilities.py` are untouched (README §5).
- It opens no store and starts no Ray. `var/runs/` and `var/datastores/` are created empty.

**Each commit** in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
