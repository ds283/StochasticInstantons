# Which tests to run: the `slow` marker and when to include it

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`. It applies whenever you are deciding which tests to run after a
change — do not default to running the whole suite "to be safe"; it is
expensive for no benefit on most changes.

## The problem

`tests/` has 571 tests. A block of them are not unit tests but real numerical
solves — Picard shooting iterations, `solve_ivp` backward integrations, dense
spectral eigendecompositions swept across `n_max` up to 192 — each costing
tens of seconds to minutes. Run together, un-filtered, the suite takes far
longer than is useful for routine iteration, and several of these files take
long enough that a naive full run reads as a hang rather than "still working".
None of this is needed for a change that doesn't touch the numerics.

## The rule

**Default to:**

```bash
pytest -m "not integration and not slow"
```

This currently selects 464 of 571 tests and completes in well under a
minute. Use this after any change unless the diff below says otherwise.

**Broaden to include `-m "not integration"` (dropping the `slow` exclusion,
keeping `integration` excluded)** only when the diff touches:

- `ComputeTargets/` (any file — this is where every `slow`-marked test's
  subject code lives)
- `Numerics/` (LGL collocation, onion coordinate — inputs to the same solves)
- `Interpolation/` (`SplineWrapper` — used inside the solves)
- `analyze_StiffnessSpectrum.py` (the spectral-diagnostic module two `slow`
  files test directly; it is a top-level script, not under `ComputeTargets/`,
  so don't rely on a directory check alone)

A quick check before choosing:

```bash
git diff --name-only <base>...HEAD   # or: git status --short
```

If none of the paths above appear, stay on the fast default — the `slow`
tests exercise code the diff cannot have affected.

**Only add `-m "integration"` (or drop the `-m` filter entirely) when the
task specifically calls for it** — e.g. verifying a `Datastore/`,
`config/sharding.py`, or factory `store()`/`build()` change, per the existing
`integration` marker's own purpose (needs a live Ray cluster + SQLite
database; see `pyproject.toml`'s marker description). Don't combine
`integration` and `slow` in one run just because both are "the exhaustive
option" — pick the marker(s) that match what actually changed.

## Why a marker instead of directory-matching alone

A first instinct is "if the diff touches `ComputeTargets/`, just run
`tests/test_*.py` for files that import from there" — but that conflates two
different things: which tests exercise the changed *code*, and which tests
are *slow*. Plenty of fast tests import `ComputeTargets` (e.g.
`test_scale_assignment.py`, `test_stiffness_spectrum.py` — despite the name,
9s) and plenty of the slow ones are gated behind real ODE/spectral solves
regardless of which specific file changed. The `slow` marker records the
actual empirical cost (measured directly, see below), so the decision is
"is this expensive to run" not "does this filename look numerical".

## Current `slow`-marked files — reference

Measured standalone with `-m "not integration"`; each one individually
exceeded a 45-second cap (or, for the two borderline ones, came close):

| File | What makes it slow |
|---|---|
| `test_gci_parity_scalars.py` | Real `solve_ivp` downflow + a full GCI Picard solve |
| `test_gradient_coupled_instanton_end_to_end.py` | 4 of its tests call `_compute_gradient_coupled_instanton._function(...)` directly (real compute); its 3 guard-clause tests and its `live_pool`-based class (already `@pytest.mark.integration`) are **not** marked `slow` — they're cheap or already excluded |
| `test_gradient_coupled_instanton_stiffness_instrumentation.py` | Every test runs a full GCI Picard solve |
| `test_msr_action.py` | Real `solve_picard`/`solve_ivp` runs back every test |
| `test_picard.py` | Every test drives a real Picard shooting solve |
| `test_response_lambda_scaling_prompt23.py` | Parametrized `solve_ivp` backward passes across lambda values (measured 36s standalone) |
| `test_response_spectrum_prompt23.py` | Sweeps `n_max` up to 192 through dense eigendecompositions (via `analyze_StiffnessSpectrum.py`) |
| `test_sbp_sat_boundary_closure.py` | Same dense-eigendecomposition sweep, forward-sector version |

Whole-file-slow modules carry a module-level `pytestmark = pytest.mark.slow`
(house style already uses per-test `@pytest.mark.integration` decorators for
partially-slow files — follow that pattern, not a blanket module mark, when
only some tests in a file are expensive; `test_gradient_coupled_instanton_end_to_end.py`
is the current example of this mixed case).

## When adding a new test

If a new test drives a real ODE integration, Picard/Newton iteration, or a
dense linear-algebra sweep over a parameter grid (not a stub/mock), mark it
`@pytest.mark.slow` (or add `pytestmark = pytest.mark.slow` if the whole file
will be that way) and add a row to the table above. If unsure whether a new
test counts, time it standalone — the bar is "does this test individually
take more than a few seconds", not "does it touch `ComputeTargets/`".

## What is forbidden

```bash
# NEVER — defaults to the full suite "to be safe" when the diff doesn't
# touch ComputeTargets/Numerics/Interpolation/analyze_StiffnessSpectrum.py
pytest
```

Don't run the unfiltered suite (or add `-m slow`/drop `-m` entirely) as a
reflexive habit. Match the marker filter to what the diff actually touches,
per the rule above.
