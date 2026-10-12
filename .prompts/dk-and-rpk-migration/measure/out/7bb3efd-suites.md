# Test suites at `7bb3efd` (2026-10-11)

Run from the repository root with `./venv/bin/python -m pytest`, in the foreground, serially.
No Ray cluster was up; the `integration` run's `live_pool` fixture started its own local Ray
(`ray.init`) and shut it down.

| Selection | Collected | Result | Wall time |
|---|---|---|---|
| all (`--collect-only`) | 761 | — | — |
| `-m "not integration and not slow"` (the default run) | 631 of 761 | 630 passed, 1 skipped | 110 s |
| `-m "integration"` | 61 of 761 | 60 passed, 1 skipped | 24 s |
| `-m "slow and not integration"` | 69 of 761 | not run at planning (prompt 02 measures it) | — |

No test is both `integration` and `slow` (`-m "integration and slow"` collects none).
`CLAUDE.md:21` and `.claude/rules/test-selection.md:10`, `:26` still say 464 of 571.

The integration run's full output is `7bb3efd-suite-integration.txt`.
