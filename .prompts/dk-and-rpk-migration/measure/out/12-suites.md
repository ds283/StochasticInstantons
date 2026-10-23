# Test suites at the close of dk-and-rpk-migration (prompt 12, 2026-10-23)

Run from the repository root with `./venv/bin/python -m pytest`, serially. The default and `integration` runs were
made in the foreground, before 12's edits (from `47c0a77`, 01:45 BST) and after its Python edits (02:02 BST); the
`slow` run was made once, after, in the background (02:03:38 to 02:10:24 BST). No Ray cluster was up; the
`integration` run was `RAY_ADDRESS=local`, so that its `live_pool` fixture started a private Ray instance and shut it
down. The machine's load was that of backups and system services; no suite or Ray job of any project ran.

| Selection | Collected | Result | Wall time (pytest; `time`) | Load at start (1 / 5 / 15 min) | Output |
|---|---|---|---|---|---|
| all (`--collect-only`) | 868 | — | — | — | — |
| `-m "not integration and not slow"`, before | 732 of 868 | 731 passed, 1 skipped, 136 deselected | 37.98 s; 42.3 s | 75.5 / 97.4 / 85.6 | `12-suite-default-before.txt` |
| `RAY_ADDRESS=local`, `-m integration`, before | 67 | 66 passed, 1 skipped, 801 deselected | 57.40 s; 58.7 s | 93.9 / 99.2 / 87.0 | `12-suite-integration-before.txt` |
| `-m "not integration and not slow"`, after | 732 | 731 passed, 1 skipped, 136 deselected | 34.07 s; 38.1 s | 51.7 / 43.3 / 60.8 | `12-suite-default-after.txt` |
| `RAY_ADDRESS=local`, `-m integration`, after | 67 | 66 passed, 1 skipped, 801 deselected | 47.62 s; 48.8 s | 38.9 / 41.3 / 59.4 | `12-suite-integration-after.txt` |
| `-m slow`, after (background) | 69 | 69 passed, 799 deselected, 11 warnings | 404.36 s (6:44); 6:45.80 | 75.7 / 49.9 / 61.4 | `12-suite-slow-after.txt` |

Also: `-m "not integration"` collects 801; `-m "slow and integration"` collects none. The `slow` tests by file:
`test_gci_diagnostics_convergence_floor_cli.py` 1, `test_gci_parity_scalars.py` 1,
`test_gradient_coupled_instanton_end_to_end.py` 3, `test_gradient_coupled_instanton_stiffness_instrumentation.py` 4,
`test_msr_action.py` 5, `test_picard.py` 18, `test_response_lambda_scaling_prompt23.py` 11,
`test_response_spectrum_prompt23.py` 10, `test_sbp_sat_boundary_closure.py` 16 (the nine files of
`.claude/rules/test-selection.md`'s table; 69 in all).

Against 11's (at `66b1c81`, 732 and 67) and 02's S1 (69 passed, 390.24 s): equal.
