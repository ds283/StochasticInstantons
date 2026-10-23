# 01 — the pin, the config and the rules

**Subject:** Pin `runregistrykit[stores]` `v0.2.0`; add `runregistrykit.toml`, the ignore rule, the rules and the discovery hook
**Commits:** `60687f064a2a706bb39ea6c69fe8f4ace78375a8` (the pin alone) and this commit, on branch `rrk-adoption`
**Date:** 2026-10-23, by Claude Sonnet 5.5
**Result:** **COMPLETE.** C1–C5 hold. `runregistrykit` 0.2.0 is installed from the tag's commit `0bae3a3`, not editable, and is the only distribution the install changed. Its own suite passes on the installed package. Suites: default 738 (737 passed, 1 skipped), `integration` 67 (66 passed, 1 skipped). No issue is opened.

Prompt: [`.prompts/rrk-adoption/01-pin-config-and-rules.md`](../../.prompts/rrk-adoption/01-pin-config-and-rules.md). Scratch outputs were kept outside the repository.

## What shipped

- **C1.** `requirements.txt:63`: `runregistrykit[stores] @ git+https://github.com/ds283/RunRegistryKit@v0.2.0`, between `rpds-py` and `scipy`; no other line changed. Commit `60687f0`, alone. Installed with `./venv/bin/pip install -r requirements.txt`.
- **C2.** `runregistrykit.toml` (three keys, no `[stores]`); `.gitignore` gains `var/` and a comment; `var/runs/` and `var/datastores/` created empty.
- **C3.** `CLAUDE.md`: the section "Long-running jobs — the run registry" after "Build and test" (16 lines); `.claude/rules/run-registry.md`, new, no `paths:` frontmatter.
- **C4.** `.claude/settings.json`: one `SessionStart` hook. Its command changes to `$CLAUDE_PROJECT_DIR`, runs `./venv/bin/python -m runregistrykit list` if `./venv/bin/python` and `var/runs` exist, and otherwise prints a one-line notice; it always exits 0. Schema checked at https://code.claude.com/docs/en/hooks (a `matcher`-optional group holding `hooks: [{type: "command", command, statusMessage}]`; exit 0 adds stdout to the session's context; no exit code blocks a start).
- **C5.** `tests/test_registry_config.py`, 6 tests (item 3 is parametrized over two paths).

## Deviations from the prompt

1. **C5 item 3 is two `git check-ignore -q` calls, not one.** `git check-ignore -q` with two paths is `fatal: --quiet is only valid with a single pathname`. `STRUCTURALLY REQUIRED`. Consequence: the suite is 6 tests, not 5.
2. **The package's suite took 145 s**, so the commit and the suite ran as one background command. `IMPLEMENTATION CHOICE`.
3. None other.

## Verification performed

- **Gate:** branch `rrk-adoption`; `git status --porcelain` empty; no `var/`; `ray_cluster.sh status`: no SI processes, lock free. Load 63 at the start (`uptime`).
- **Before any edit:** default 731 passed, 1 skipped, 136 deselected (34.6 s); integration 66 passed, 1 skipped (51.5 s). Both as README §0.4.
- **Freeze:** `diff` of `pip freeze` before and after is one line, `70a71 > runregistrykit @ git+https://github.com/ds283/RunRegistryKit@0bae3a3c501a8264ee4be5bc24f06422af38720f`. `pip check`: no broken requirements. `datastorekit` stays at `v0.5.0`.
- **`direct_url.json`:** `{"url": "https://github.com/ds283/RunRegistryKit", "vcs_info": {"commit_id": "0bae3a3c501a8264ee4be5bc24f06422af38720f", "requested_revision": "v0.2.0", "vcs": "git"}}`; no `dir_info`, so not editable.
- **The package's suite**, from a `mktemp` clone at the tag, `env -u PYTHONPATH`, the venv's python, `-m unittest discover -s runregistrykit/tests -t .`: `Ran 410 tests in 145.238s`, `OK (skipped=1)`. Clone removed.
- **`list`** from the root: `no runs under …/var/runs`, exit 0.
- **The hook's command** run by hand with `CLAUDE_PROJECT_DIR` set: the same line, exit 0; with `var/runs/` renamed aside (then restored): `run registry: not available here (no ./venv/bin/python or var/runs/); skipped`, exit 0.
- **After:** default `737 passed, 1 skipped, 136 deselected`; integration `66 passed, 1 skipped, 807 deselected`. No store opened or named; no Ray started. `git diff 1c223e8 -- main.py plot_*.py utilities.py` empty.

## The deliberate-breakage record

Each was applied, run, and reverted; none was committed.

| Breakage | Diff | Result |
|---|---|---|
| `var/` removed from `.gitignore` | `-var/` | `test_var_is_ignored_by_git[var/runs/x]` fails (1 failed, 5 passed) |
| a misspelt key | `-runs_root = …` `+run_root = …` | `test_client_root_gives_the_roots_and_distributions` and `test_config_holds_exactly_the_expected_keys` fail (2 failed) |
| `distributions` reduced | `distributions = ["datastorekit"]` | `test_client_root_gives_the_roots_and_distributions` fails (1 failed) |

## Observations not acted on

- With `var/` removed from `.gitignore`, `var/datastores/x.sqlite` still passes `check-ignore`: another rule in `.gitignore` ignores `*.sqlite`. The second parameter therefore adds nothing for `.sqlite`; the first path carries the check.
- `pip` reports a newer pip (26.2.1). Not acted on.

## State handed to the next prompt

- `runregistrykit.toml` has no `[stores]`; 02 adds it and extends `EXPECTED_KEYS` in `tests/test_registry_config.py` with `"stores"`.
- The default suite is 738 tests (737 passed, 1 skipped); `integration` is 67 (66, 1 skipped). 02's counts start there.
- `CLAUDE.md` and the rules say the wrapper is added by prompt 03; 05 makes the sentence definite.
