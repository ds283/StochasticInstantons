# Prompt 28 — Diagnostic 8t + Diagnostic 13 (renumbered from prompt's own "11"): the τ study, both halves: results

Prompt: `.prompts/gradient-coupled-instanton/28-tau-study-diagnostics-8t-and-11.md`.
Implementation: `diagnostic_8_tau_sensitivity` and
`diagnostic_13_tau_unlock_n_retry` in
`tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`
(`--diagnostic 8t 13`). Depends on prompt 27 (`tau_multiplier` threaded
through `forward_rhs`/`solve_picard`, landed in `5e8d08c`), already merged.

> **Status (8 October 2026).** The measurements and both classifications
> stand. The "Combined recommendation" below is superseded: a finer
> `tau_multiplier` sweep would fit a numerical penalty to a preferred result.
> The `τ`-dependence comes from the frozen `g_pi` target and the
> over-determined two-penalty closure (Test A; `handoff-notes/2026-07-10/SAT-CLOSURE-STATUS.md`),
> and the closure is to be replaced, not tuned: one characteristic penalty in
> the `H_μ` norm, with `τ`-independence as the acceptance test (planned onion
> rebuild, `.prompts/INDEX.md`). The argument against the sweep was made on
> 10 July (`handoff-notes/2026-10-08/summary-C-boundary-handoff.md`); David
> did not rule on it, and the 8 October plan makes it moot.

## Numbering deviation (read first)

The prompt names part 2 `diagnostic_11_tau_unlock_n_retry`, dispatched as
`"11"`. **That number is no longer free.** Prompt 28's own prompt file was
written (`a01962a`) before Diagnostic 11 (corridor-edge proximity, `c57c2c2`)
and Diagnostic 12 (relaxed-corridor retry, `2e2b1e5`) landed and claimed `11`
and `12` for an unrelated question (whether the `n=9` floor was a corridor-
clamp artefact — Diagnostic 12's own conclusion: no, ruled out). Implementing
part 2 as literally `"11"` would have silently overwritten the existing
`"11"` entry in `_DIAGNOSTIC_DISPATCH` (a plain dict literal — last key wins,
no error) and made `diagnostic_11_corridor_edge_proximity` unreachable from
the CLI with no warning. Renumbered to **`diagnostic_13_tau_unlock_n_retry`**,
dispatched as `"13"` (the next free slot), instead. Both new diagnostics'
own docstrings and the module docstring record this explicitly.

A second, smaller deviation: the pre-existing test
`tests/test_gci_diagnostics_convergence_floor_cli.py::test_diagnostic_8t_cli_raises_not_implemented`
asserted the old stub's `NotImplementedError`. Left unfixed, it would have
silently become a ~10-minute real-numerics test disguised as a fast,
unmarked one (it now calls the *implemented* `diagnostic_8_tau_sensitivity`
via the CLI with no budget/mass override) — the first full `pytest -m "not
integration"` run below confirms this happened (29m45s instead of the usual
~8-9 minutes). Replaced with two fast, monkeypatched dispatch-only tests
(`test_diagnostic_8t_cli_dispatches_without_running_real_numerics`,
`test_diagnostic_13_cli_dispatches_without_running_real_numerics`), matching
this file's own existing convention of using `monkeypatch` for cheap CLI-glue
coverage. `git diff --stat` is therefore not confined to
`convergence_floor.py` alone — it also touches this one test file, which was
necessary to avoid landing a real regression.

## Executive summary — both classifications

**(1) Robustness: material τ-dependence found — not tau-independent.**
Departing from the production `tau_multiplier=1.0` in *either* direction
breaks the `n=5`/`n=7` solutions reported since Diagnostic 4, in different
and both serious ways:

- `tau_multiplier=0.5` (the design note's own bare admissibility floor):
  converges to **grossly different, and in one case unphysical**, answers
  at `n=5`; at `n=7` it produces a **numerically "converged" but unphysical**
  solution (`epsilon_core=1.57 > 1`, violating the entire SAT-penalty
  derivation's own core assumption) at one point and fails outright at the
  other three.
- `tau_multiplier=2.0`: **never converges**, at any tested `delta_Nstar`, at
  either `n=5` or `n=7` — always floors at the `MAX_OUTER` cap.
- Only `tau_multiplier=1.0` reproduces the historically-recorded, presumably
  physical solutions, at both resolutions tested.

**(2) Unlock: no genuine unlock — the one nominal "convergence" is a
corridor-clamp artefact.** `tau_multiplier=4.0` is the only value (of 7
tested) that satisfies `OUTER_TOL` at `n=9`, but a direct follow-up check
(reusing Diagnostic 11's own `capture_shooting_result` probe) shows its
`final_lambda` sits **exactly** on the corridor's `lambda_c_positive` wall
(`nearest_edge_fraction=0.0`, bit-for-bit the same numeric wall Diagnostic 11
found at `tau_multiplier=1.0`) — the search is pinned at the same clamp, not
finding a free root, and at `tau_multiplier=4.0` the residual there merely
happens to dip under `0.01`. Its `final_lambda` (`+4.25`, sign-flipped from
every `n=5` result) and `msr_action` (`102.5`, ~14x smaller than the `n=5`
value at the same point) are also discontinuous with the known solution
family — inconsistent with a genuine continuum extension of Diagnostic 4's
own branch.

**Combined recommendation (per the prompt's own decision framework):**
classification (1) is the "material tau-dependence found" branch, the most
concerning of the three the prompt anticipated, **regardless of (2)'s
result.** The `n=5`/`n=7` "converged" solutions reported since Diagnostic 4
must be treated as **provisional / SAT-penalty-dependent**, not established
physics, until this is resolved. This supersedes the `n>=9` unlock question
in priority.

## Method

Direct structural copies of `diagnostic_8_alpha_sensitivity` (part 1) and
`diagnostic_9_bias_corrected_n_retry`'s baseline-then-sweep pattern (part 2),
per the prompt's own template instructions — see each function's own
docstring in `convergence_floor.py` for the full method description. Part 1
additionally accepts an optional `n` keyword (default `N_COLLOC=5`, prompt
28's own fixed resolution) so the same sweep could be re-run at `n=7` as a
quick complementary robustness cross-check, requested directly by the user
mid-session; this is exploratory follow-up, not part of the prompt's own
acceptance test (which is defined at `n=5` only).

## Part 1 — Diagnostic 8t: τ-sensitivity at `n=5` (default resolution)

`m=1e-2`, `alpha=h.ALPHA` (fixed, not swept), `tau_multipliers=(0.5, 1.0,
2.0)`, `wallclock_budget=600s`:

| `delta_Nstar` | `tau_mult` | converged | `final_residual` | `final_lambda` | `msr_action` | `max_eps_core` | outer iters | wallclock |
|---|---|---|---|---|---|---|---|---|
| 0.2 | 0.5 | **Yes** | 7.55e-4 | −4.824 | 27.93 | 0.0383 | 1 | 5.7s |
| 0.2 | **1.0** | **Yes** | 3.10e-5 | **−11.514** | **159.49** | 0.0333 | 3 | 7.9s |
| 0.2 | 2.0 | No | 0.0400 | — | — | — | 50 (floored) | 197.2s |
| 0.3 | 0.5 | **Yes** | 1.46e-3 | −6.073 | 75.00 | 0.0479 | 1 | 6.7s |
| 0.3 | **1.0** | **Yes** | 1.31e-5 | **−13.937** | **396.37** | 0.0375 | 3 | 8.5s |
| 0.3 | 2.0 | No | 0.0601 | — | — | — | 50 (floored) | 289.0s |
| 0.5 | 0.5 | **Yes** | 4.06e-5 | −7.143 | 301.39 | 0.0647 | 2 | 17.2s |
| 0.5 | **1.0** | **Yes** | 3.77e-4 | **−15.5148** | **1425.28** | 0.0482 | 3 | 22.5s |
| 0.5 | 2.0 | No | 0.1038 | — | — | — | 50 (floored) | 264.1s |
| 0.7 | 0.5 | No (Picard inner failed, λ≈−5 to −7 band) | 0.0509 | — | — | — | 50 (floored) | 308.5s |
| 0.7 | **1.0** | **Yes** | 3.50e-3 | **−15.698** | **4255.66** | 0.0559 | 3 | 15.9s |
| 0.7 | 2.0 | No | 0.1543 | — | — | — | 50 (floored) | 430.6s |

**`tau_multiplier=1.0` acceptance check — passed, bit-for-bit.** Every
`1.0` row above reproduces `24b-lambda-conversion-seeding-and-trajectory-
validation.md`'s own Part A table exactly to the precision recorded there,
and the `delta_Nstar=0.5` row (`final_lambda=-15.51477347250894`) matches
`26b-relaxed-corridor-retry.md`'s own recorded `n=5` baseline bit-for-bit.
`tau_multiplier=1.0` is confirmed a true no-op from the diagnostics side, as
prompt 27's own acceptance test required.

**Every other cell is a departure, not noise.** `tau_multiplier=0.5`'s
`msr_action` is smaller than `tau_multiplier=1.0`'s by a factor of
**4.7–5.7x** at the three points where it converges at all (`27.93` vs
`159.49`; `75.00` vs `396.37`; `301.39` vs `1425.28`) — an order-of-magnitude
larger discrepancy than Diagnostic 8a's own alpha-sensitivity check (which
found "few-percent search-path noise", the tau-independence baseline this
study was measured against). `outer_iterations=1` at all three
`tau_multiplier=0.5` convergent points (vs `3` for the equivalent
`tau_multiplier=1.0` rows) is itself a flag: the outer shooting loop is
accepting its very first bracket-seed evaluation as "converged", which is
consistent with a shallow, non-generic residual-vs-lambda landscape at this
weaker SAT penalty rather than a genuine, well-conditioned root-find.
`tau_multiplier=2.0` **never converges**, at any of the four points, always
hitting the `MAX_OUTER=50` cap (an increasing final_residual with
`delta_Nstar`: `0.040 -> 0.060 -> 0.104 -> 0.154`) rather than a wallclock
cutoff — the outer loop is failing to find a bracket/root at all, not merely
running out of time.

Anomaly flagged per the prompt's own instruction: **`tau_multiplier=2.0`'s
wallclock (197–431s) is far above the ~6–20s every converging point in this
sweep takes**, though still within the 600s budget. This alone is a
reportable signal that `tau_multiplier=2.0` puts the outer loop in a
qualitatively different (much more expensive, ultimately unsuccessful)
regime, not just a slower version of the same search.

## Part 1 supplement — Diagnostic 8t at `n=7` (exploratory, user-requested)

Same sweep, `n=7` (still cheap — seconds to a few minutes per point), to
check whether the `n=5` tau-dependence is an `n=5`-specific artefact or
persists at a finer grid:

| `delta_Nstar` | `tau_mult` | converged | `final_residual` | `final_lambda` | `msr_action` | `max_eps_core` | bailout | wallclock |
|---|---|---|---|---|---|---|---|---|
| 0.2 | 0.5 | No | 0.257 | — | — | — | descending | 600.0s (budget) |
| 0.2 | **1.0** | **Yes** | 7.68e-4 | −20.674 | 520.67 | 0.0640 | converged | 51.9s |
| 0.2 | 2.0 | No | 0.0102 | — | — | — | floored (50 iters) | 430.7s |
| 0.3 | 0.5 | No | 0.320 | — | — | — | **blown-up** | 205.5s |
| 0.3 | **1.0** | **Yes** | 7.70e-6 | −20.726 | 889.00 | 0.0769 | converged | 27.1s |
| 0.3 | 2.0 | No | 0.0463 | — | — | — | floored (50 iters) | 277.4s |
| 0.5 | 0.5 | **"Yes"** (see caveat) | 5.81e-3 | −0.00793 | **0.00738** | **1.568** | converged | 325.6s |
| 0.5 | **1.0** | **Yes** | 5.02e-5 | −16.780 | 1695.13 | 0.1243 | converged | 26.4s |
| 0.5 | 2.0 | No | 0.121 | — | — | — | floored (50 iters) | 419.5s |
| 0.7 | 0.5 | No | 1.335 | — | — | — | **diverging** | 600.0s (budget) |
| 0.7 | **1.0** | **Yes** | 1.48e-4 | −12.067 | 2580.45 | 0.1913 | converged | 88.6s |
| 0.7 | 2.0 | No | 0.120 | — | — | — | floored (50 iters) | 334.0s |

**This strengthens, not merely repeats, the `n=5` finding.**
`tau_multiplier=1.0` again converges cleanly at all four points (fresh
values, no historical record to compare against since Diagnostic 6/10 only
probed `n=7` at `delta_Nstar=0.5`). `tau_multiplier=2.0` again never
converges anywhere. `tau_multiplier=0.5` is now worse than at `n=5`: it
fails outright at three of four points (`descending`, `blown-up`,
`diverging` — three different non-convergence signatures), and at the
fourth (`delta_Nstar=0.5`) it reports `converged=True` with
`final_residual=0.0058 < OUTER_TOL` but to a **manifestly unphysical
state**: `max_epsilon_core=1.568 > 1`. Per
`21a-production-port-notes.md` §5.1, `A_core`'s sign (hence the entire
core-SAT-penalty derivation) is only guaranteed while `epsilon_core < 1`;
a solution that satisfies the outer-loop's residual tolerance while sitting
at `epsilon_core > 1` is a numerically-converged non-solution, not a
converged instanton. `final_lambda≈0` and `msr_action≈0.0074` (essentially
zero action) are consistent with this being a degenerate/trivial fixed
point rather than a genuine gradient-coupled instanton.

## Classification (1): material τ-dependence found

Both resolutions tested (`n=5`, `n=7`) show the same qualitative pattern:
`tau_multiplier=1.0` (production) is an isolated point of good behaviour,
flanked on both sides by failure modes of different character —
`tau_multiplier=0.5` produces spurious/degenerate "convergence" or outright
failure, `tau_multiplier=2.0` never converges at all. This is the prompt's
own most concerning classification: **the `n=5`/`n=7` solutions reported
since Diagnostic 4 are provisional, tau-value-dependent results, not yet
established as tau-independent continuum physics.**

## Part 2 — Diagnostic 13 (prompt's own "11"): τ-unlock retry at `n=9`

Same point as Diagnostics 6/9/10/11/12 (`m=1e-2, delta_Nstar=0.5, n=9`),
`MAX_OUTER=30`, `wallclock_budget_seconds=900`, seed fetched once (identical
across the sweep):

| `tau_multiplier` | converged | `final_residual` | `bailout_tag` | `bailout_reason` | outer iters | wallclock |
|---|---|---|---|---|---|---|
| 0.5 | No | 0.1438 | floored | wallclock_budget | 3 | 900.3s |
| 0.75 | No | — | **blown-up** | wallclock_budget | 0 | 900.6s |
| **1.0** | No | **0.1123** | floored | max_outer_exhausted | 30 | 336.8s |
| 1.5 | No | 0.0601 | floored | max_outer_exhausted | 30 | 337.3s |
| 2.0 | No | 0.0350 | floored | max_outer_exhausted | 30 | 309.4s |
| 3.0 | No | **0.01001** | floored | max_outer_exhausted | 30 | 292.8s |
| **4.0** | **"Yes"** (see caveat below) | 0.00258 | converged | converged | 10 | 110.2s |

**`tau_multiplier=1.0` cross-check — passed.** `final_residual=0.1123`
agrees with Diagnostic 6/10's own recorded `n=9` result (`≈0.112`,
`bailout_tag=floored`/`max_outer_exhausted`) to the sanity-check tolerance
the prompt's own acceptance test allows.

**`final_residual` improves monotonically and smoothly with
`tau_multiplier`** from `0.5` through `3.0` (`0.144 -> [blown-up] -> 0.112 ->
0.060 -> 0.035 -> 0.010`), crossing to just above `OUTER_TOL=0.01` at
`tau_multiplier=3.0` before nominally crossing it at `4.0`. Taken at face
value this looks like a real, physically-motivated trend — larger SAT
penalty progressively taming whatever instability floors the outer loop.

**But `tau_multiplier=4.0`'s "convergence" does not survive a direct
corridor check.** Re-running that exact point with Diagnostic 11's own
`capture_shooting_result()` probe:

```
converged=True   final_residual=0.0025760804078096555
final_lambda=4.247941624378134
last_lambda_tried=4.247941624378134
lambda_c_positive=4.247941624378134   lambda_c_negative=-10.619854060945336
nearest_edge_fraction=0.0
```

`nearest_edge_fraction=0.0` means the outer loop's last tried `lambda` sits
**exactly** on the corridor's positive clamp wall — the identical numeric
wall (`4.247941624378134`) Diagnostic 11 found the `n=9`, `tau_multiplier=1.0`
search pinned against for its entire 50-iteration budget
(`26a-corridor-edge-proximity.md`). Since `lambda_c_positive` is computed
from the `FullInstanton` seed's own `mu`/`D11` values (fetched once, outside
the `tau_multiplier` loop, identical across every row in the table above),
this wall is **the same fixed number regardless of tau_multiplier** — the
search at `tau_multiplier=4.0` is not exploring a wider, tau-shifted root
location; it is sitting at the same wall Diagnostic 12 already investigated
(and, at `tau_multiplier=1.0`, ruled out as curable by widening). The most
likely reading: raising `tau_multiplier` lowers the residual value *at the
wall itself* (consistent with the smooth, monotonic improvement across the
whole sweep), until at `4.0` that wall-pinned residual happens to dip below
`OUTER_TOL` — not because a genuine unconstrained root was found nearby.

This reading is reinforced by the physics: `final_lambda=+4.25` is
**sign-flipped** relative to every other converged solution encountered in
this entire suite (`n=5`'s four points are all in `[-15.7, -11.5]`;
Diagnostic 12's own `n=9` widening sweep found the genuine feasibility wall
in `lambda≈5-12`, positive but larger in magnitude), and `msr_action=102.5`
is roughly `14x` smaller than the `n=5`, `tau_multiplier=1.0` value at the
same `(m, delta_Nstar)` point (`1425.28`). A genuine continuum extension of
the known `n=5` solution family should land in the same neighbourhood of
`(lambda, msr_action)`-space, not flip sign and change scale by an order of
magnitude.

## Classification (2): no genuine unlock

**Clean negative, once the corridor-clamp artefact is accounted for.** No
tested `tau_multiplier` produces a converged `n=9` solution that is both (a)
a genuine root of the outer shooting problem (not corridor-pinned) and (b)
physically continuous with the known `n=5` solution family. The one nominal
`OUTER_TOL` crossing (`tau_multiplier=4.0`) fails both criteria on direct
inspection. This is complementary to, and consistent with, Diagnostic 9's
bias clean negative and Diagnostic 12's corridor clean negative — three
independent mechanisms now ruled out for the `n>=9` floor at this point.
Per the prompt's own instruction, this negative result is not grounds to
widen `tau_multipliers` speculatively.

## Combined recommendation

> **Superseded (8 October 2026):** see the status note at the top.

The prompt's own decision framework covers exactly this combination:
**"(1) material tau-dependence found: this is the more concerning outcome
regardless of (2)'s result — the n=5 'converged' solutions reported since
Diagnostic 4 would need to be treated as provisional/SAT-penalty-dependent
rather than physics, and revisiting them (which delta_Nstar/point(s) are
affected, how strongly) becomes the immediate priority over the n>=9
question."**

Concretely, this means:

- **All four `delta_Nstar` points are affected**, at both resolutions tested
  (`n=5` and `n=7`) — this is not confined to one corner of the parameter
  sweep.
- The immediate next step is understanding **why** `tau_multiplier=1.0` is
  special rather than merely the midpoint of an admissible range — is it a
  genuine, sharply-peaked stability window, or is the "physical" answer only
  the one closest to `21a`'s own hardening derivation because that
  derivation was tuned circularly against these same points? This needs a
  finer `tau_multiplier` sweep bracketing `1.0` (e.g. `{0.8, 0.9, 1.0, 1.1,
  1.2}`) at the four known points, not a repeat of this coarse
  `{0.5, 1.0, 2.0}` grid.
- The `n>=9` question (this prompt's own part 2) is now secondary to that —
  even if some future `tau_multiplier` did cleanly unlock `n=9`, the
  resulting solution's own tau-robustness would need separate verification
  given this finding, not an assumption of continuity with the (now
  provisional) `n=5` branch.
- Diagnostic 10's own response-sector fallback recommendation remains live
  and unaddressed by any of Diagnostics 9/11/12/13's clean negatives — but
  is no longer the most urgent open question, which is now the τ-dependence
  found here.

## Verification

- `git diff --stat`:
  ```
  tests/test_gci_diagnostics_convergence_floor_cli.py                          |  29 ++-
  tools/diagnostics/GradientCoupledInstanton/convergence_floor.py              | 264 ++++++++++++++++++---
  ```
  Not confined to `convergence_floor.py` alone — see "Numbering deviation"
  above for why the test-file change was necessary (fixing a real
  regression the implementation exposed, not scope creep). No production
  file (`ComputeTargets/`, `Numerics/`, `Datastore/`) touched.
- `diagnostic_8_tau_sensitivity()` ran end-to-end at the default point set
  (`n=5`); its `tau_multiplier=1.0` rows match Diagnostic 4/24b/26b's own
  recorded `final_lambda`/`msr_action` at each `delta_Nstar` bit-for-bit (see
  Part 1 table above).
- `diagnostic_13_tau_unlock_n_retry()` ran end-to-end at the default
  seven-point sweep; its `tau_multiplier=1.0` row (`final_residual=0.1123`,
  `bailout_tag=floored`/`max_outer_exhausted`) matches Diagnostic 6/10's own
  recorded `n=9` result to the sanity-check tolerance the prompt's own
  acceptance test allows.
- CLI dispatch (`python -m tools.diagnostics.GradientCoupledInstanton.
  convergence_floor --diagnostic 8t 13`) verified via a monkeypatched
  dry-run (both diagnostic functions replaced with call-recording stubs,
  confirming `cf.main(["--diagnostic", "8t", "13"])` calls each exactly
  once, in order, and returns exit code 0) rather than a second real
  end-to-end run — the real physics for both diagnostics had already been
  run and recorded directly (see tables above); re-running the full,
  expensive sweep a second time purely to exercise the CLI wrapper would
  have cost another ~30–100 minutes for no new information.
- Output JSONs present under
  `tools/diagnostics/GradientCoupledInstanton/output/convergence_floor/`:
  `diagnostic8t_tau_sensitivity.json` (n=5, the acceptance-test artefact),
  `diagnostic8t_tau_sensitivity_n7.json` (n=7 supplement, exploratory),
  `diagnostic13_tau_unlock_n_retry.json`.
- No `tau_multiplier < 0.5` was swept in either diagnostic, per the prompt's
  own constraint (21a's sign-robustness caveat).
- Since this diff touches `tools/diagnostics/GradientCoupledInstanton/`, the
  broadened test filter (`pytest -m "not integration"`, per
  `.claude/rules/test-selection.md`) was run **twice**: the first run (before
  the CLI-test fix above) passed **697, failed 1** in 29m45s — the failure
  was `test_diagnostic_8t_cli_raises_not_implemented`, now understood as a
  real regression (asserting removed behaviour, and incidentally running a
  full un-marked real solve). After the fix, a second full run passed
  **699 passed, 1 skipped, 61 deselected** in 8m35s — zero failures, and
  back to the suite's normal fast-path runtime.

## Addendum — four user-requested falsification tests

*(Originally scoped as two tests; a methodological correction to Test A and
two further tests — A2 and D — were added in a follow-up round. See "Updated
reading" at the end of this addendum for the reading that survives all
four.)*

Following the results above, a follow-up question was raised: is the
material τ-dependence found in Diagnostic 8t itself evidence that the SAT
closure is *contaminating the physics* (not merely regularising it), and is
Diagnostic 12's "corridor ruled out" conclusion actually well-founded, given
its own concession that "the search never got a clean look at the negative
side under any widening tested"? Two concrete, cheap tests were proposed to
adjudicate both questions directly. Both were run; **no new Picard/shooting
solves were needed for the first.**

### Test A — measure the SAT penalty forcing directly (zero new solves)

**Methodological correction (post-hoc, requested):** the first pass of this
test recovered the penalty as a pure residual (finite-difference
`d(pi_core)/dN` minus every other assembled term), justified by the claim
that the lagged target `g_pi(N)` was "not persisted, and only meaningful
mid-iteration." **That justification was wrong.** With
`DEFAULT_SAT_THETA=0.0`/`DEFAULT_ANDERSON_M=0` (the production default),
`_AndersonMixer.update()` is an exact no-op, so `g_pi_core_spline` is
**frozen** at the `FullInstanton` seed's own `phi2(N)` for the *entire*
solve — never updated after sweep 0 (`picard.py`'s own module docstring,
"pi_core SAT target" section). Concretely,
`g_pi_core_spline = SplineWrapper(N_grid, profile["phi2"], y_transform=
'linear', k=3)`, and `profile["phi2"]` is itself
`SplineWrapper(N_sample_FI, phi2_FI, y_transform='linear', k=3)` evaluated
onto the dense `N_grid` (`_fetch_full_instanton_profile`'s own `_interp`
helper) — i.e. re-splining an already-interpolated array back onto the
identical grid it was interpolated onto, a no-op at the `N_grid` sample
points themselves. Both `N_sample_FI` and `phi2_FI` **are** persisted in the
`.npz` (`harness.save_grids_npz`'s own schema). So the direct construction
`(tau/w_core)*(pi_core(N) - g_pi(N))`, with
`g_pi(N) = SplineWrapper(N_sample_FI, phi2_FI, y_transform='linear', k=3)(N_grid)`
and `tau/w_core = tau_multiplier*|A_core(N)|/w_core` (computed the same way
as the residual method's own `A_core`), is available at zero cost, exactly
as pointed out. Both methods were run and compared directly.

**Result — the two independent methods agree, away from a known
finite-difference artefact.** Median `|residual − direct|` across the whole
`N`-range is `~1e-6` at every `delta_Nstar` (`1.5e-6, 2.4e-6, 4.1e-6, 6.3e-6`)
against an `O(1)` penalty signal — six orders of magnitude smaller. The
"max discrepancy" (`5.6%–11.6%` of `max|penalty|`, if quoted without
qualification) is driven almost entirely by `N=0`, where the direct
construction is *exactly* zero (`pi_core(0)` starts at the target by
construction, since the sweep-0 seed IS the target profile) while `np.gradient`'s
one-sided boundary derivative is inevitably inaccurate there; a handful of
sub-percent-level residual points elsewhere coincide exactly with the
fastest-oscillating part of the early transient (`N~0.25-1.0`, visible in
`28-sat-penalty-forcing-magnitude-v2.png`), consistent with ordinary
central-difference truncation error at high curvature, not a mis-assembled
term. **Test A is now airtight**, confirmed by two independent
reconstructions rather than one.

**Result — the penalty is NOT negligible.** See
`28-sat-penalty-forcing-magnitude-v2.png` (direct-construction curve, with
the residual-method curve overlaid as a dotted check — visually
indistinguishable). At every `delta_Nstar`, the SAT forcing peaks (near the
initial transient, `N<1`) at **2–19x** the background terms' own magnitude,
then decays in a damped oscillation, settling by late `N` to a residual
level that is still **5–20% of the background terms**, not vanishing (all
figures below now from the direct construction):

| `delta_Nstar` | max\|penalty\| | max(\|3π\|, \|dV/H²\|) | max ratio | median ratio (whole `N`-range) |
|---|---|---|---|---|
| 0.2 | 2.25 | 0.77 | 1.57 | 0.051 |
| 0.3 | 3.41 | 0.81 | 2.29 | 0.072 |
| 0.5 | 6.16 | 0.92 | 3.87 | 0.126 |
| 0.7 | 14.88 | 0.98 | 14.09 | 0.195 |

**Both the peak and the median ratio grow monotonically with
`delta_Nstar`** — the closure's contamination gets *worse*, not better, at
exactly the points furthest into the "genuinely non-trivial" regime this
whole campaign has been building on. This is a direct, quantitative
confirmation of the falsification test's own stated criterion: "if it's
comparable to them, the closure is contaminating the physics" — it is, and
increasingly so. This is independent evidence for, and gives a physical
mechanism behind, Diagnostic 8t's material τ-dependence finding above: the
`n=5` solutions are not weakly perturbed by a small regularisation term,
they are shaped by an O(1) closure forcing.

**A further, unifying observation** (same zero-new-solves budget): the
corridor width itself was checked directly —
`w_core` at `n∈{5,7,9,17}` gives `n²·w_core = 2.500, 2.333, 2.250, 2.125`,
confirming `w_core ∝ 1/n²` to within 12% precisely as asserted. Since
`A_core` (the SAT's own coefficient, `(y+1)/Delta_s(N)*(1-epsilon_core)`
evaluated at the core node) does not scale with `n` at all, the SAT
forcing's own *prefactor* `tau/w_core` **grows as `n²`** — the penalty
becomes a quantitatively stronger, stiffer term in the `pi_core` equation as
resolution increases, not a weaker one. This gives a single mechanism
consistent with three previously-separate observations: (i) Diagnostic 8t's
material τ-dependence (the closure already matters at `n=5`); (ii)
Diagnostic 10's finding that RK45 step counts explode ~14x in *both*
forward and backward sectors between `n=7` and `n=9` (consistent with a
genuinely stiffer ODE system overall, not a sector-specific effect); and
(iii) the present result that the closure's contamination of the physics
gets worse with `delta_Nstar`. The picture this suggests: the SAT closure is
not a passive regulariser that a shrinking corridor merely fails to reach
around — it is an increasingly dominant term in its own right as resolution
increases, and this campaign's "the root is roughly n-independent" reading
of the `n=5 -> n=7` trend (`-15.51 -> -16.78`) should be treated cautiously,
since it is exactly the two points where the SAT prefactor is smallest.

### Test A2 — does π already satisfy its own regularity condition? (zero new solves)

**Method.** `g_phi` (φ's SAT target) is computed *live* every RHS call via
`neumann_boundary_value(phi_full, D, boundary_index=-1)` — the discrete
statement of `d(phi)/dy=0` at the core, i.e. `(D@phi)_core=0`, satisfied by
construction (a live target, never lagged). `g_pi` has no such live
analogue; it is the frozen `FullInstanton` target above. Question: on the
actual converged (`n=5`, `tau_multiplier=1.0`) solutions, does the real,
integrated `pi` *already* satisfy `(D@pi)_core~=0` to good precision — the
same regularity relation φ's own target enforces? If so, a live
`neumann_boundary_value(pi_full, D, -1)` target (mirroring `g_phi` exactly)
would reproduce the same physics "for free," removing the frozen-target
bias, the τ-dependence, the `n²` amplification, and the `FullInstanton`
dependence all at once, as proposed. Computed `(D@pi)_core / |pi_core|`
directly on the same four persisted `n=5` grids (pure algebra, `grid.D`
already available, zero new solves).

**Result — the ratio is O(1), not small, and gets worse with `delta_Nstar`.**

| `delta_Nstar` | max\|(D@pi)_core/pi_core\| | median | late-`N` (last quartile) median |
|---|---|---|---|
| 0.2 | 2.22 | 0.288 | 0.214 |
| 0.3 | 3.77 | 0.440 | 0.337 |
| 0.5 | 8.47 | 0.761 | 0.624 |
| 0.7 | 21.89 | 1.165 | 1.042 |

This is nowhere near the `~2e-7` scale quoted for the degenerate branch —
**on these genuinely non-trivial solutions, π does not already satisfy the
regularity condition φ's live target enforces.** The proposed live-Neumann
substitution is therefore not a free lunch here: replacing the frozen
`FullInstanton` target with `neumann_boundary_value(pi_full, D, -1)` would
impose `(D@pi)_core=0` on the dynamics, which is measurably **not** a
property of the actual solution family (the ratio is O(1), and grows with
`delta_Nstar` in the same monotonic pattern as Test A's own penalty ratios)
— it would be a genuine physics change, not a bias-removing simplification
that reproduces the existing, presumably-correct answers "for free." This
does not by itself defend the frozen target's own correctness (the
fixed-target bias, 22c Finding 3, is separately documented and still a live
concern) — it specifically falsifies the "live-Neumann-for-pi is a
zero-cost win" reading of that concern.

### Test B — force the search into the negative corridor at `n=9`

**Method.** `harness.sweep_evaluate` (the same tool Diagnostics 1/2 already
use) monkeypatches `solve_shooting` to evaluate `solve_picard`'s own inner
Picard fixed point at *exactly* the given `lambda` values, completely
bypassing the outer bracket/escalation search — no corridor-widening
production change needed, since this sidesteps `lam_bounds` entirely.
Evaluated 6 points evenly spanning the requested bracket,
`lambda in {-12, -15, -18, -21, -24, -26}` (centred on the requested `-18`,
covering the full `[-26,-12]` range), at `(m=1e-2, delta_Nstar=0.5, n=9)`.

**Result — uniform failure across the entire requested bracket.**

| `lambda` | success | `n_sweeps` | status |
|---|---|---|---|
| -12 | No | 31 | blown-up |
| -15 | No | 30 | diverging |
| -18 | No | 30 | diverging |
| -21 | No | 30 | diverging |
| -24 | No | 30 | diverging |
| -26 | No | 30 | diverging |

None converged; no `msr_action` is available to compare against the
`n=5 -> n=7` trend (`1425 -> 1695`), since no point reached a committed
solution. This directly answers the request: forcing evaluation into the
region Diagnostic 12 never explored does **not** turn up a hidden root —
the negative side fails just as thoroughly as the positive side.

**Important caveat — this is suggestive, not conclusive.** `sweep_evaluate`
evaluates every `lambda` from the same cold sweep-0 seed (its own docstring:
"Not warm-started between points"), whereas the real outer loop's own
escalation is warm-started at every step (each probe seeded from the
previous, nearby point's committed grid) — and the production `n=5`/`n=7`
roots are themselves found ~60x further from `lambda_seed` (order
`-0.2` to `-0.3`, from `gradient_enhancement_E~=60` and the converged
`lambda~=-15` to `-17`) than a single cold jump would reach unassisted. This
test shows a cold probe finds no fixed point anywhere across a full,
evenly-spaced 14-unit-wide swath of the requested region — meaningful
evidence against an easily-found isolated root sitting there, but it does
not fully rule out a root reachable only via an incrementally warm-started
negative-side escalation (mirroring `_bracket_from_seed`'s own geometric
expansion, but forced negative rather than left to whatever mechanism sent
the real search positive). That would be the natural next test if this
question needs closing further — not attempted here to keep this addendum
within the two specific, cheap tests requested.

### Test D — does the closure alone (no λ) already break Picard at `n=9`/`n=17`?

**Method.** The forward blow-up mode (`24a` Diagnostic 1, this campaign's own
handoff brief) is `H²_local<0`, driven by the noise source
`D11*lambda*r_tilde` — proportional to `lambda`. A genuine feasibility wall
is therefore necessarily λ-dependent (present beyond some `|lambda|`, absent
below it — exactly the structure the asymmetric corridor was derived from).
If, instead, the inner Picard map fails at `n=9`/`n=17` **at every λ tested,
including λ=0** (where the noise term vanishes identically and there is no
rare-event physics to obstruct anything), that would mean the SAT closure
alone — independent of λ — is what breaks the contraction, and no outer
search of any kind could ever succeed there. `harness.sweep_evaluate` at
`lambdas=[0.0]` (its own first entry in Diagnostic 1's `lambda_grid`
convention) was run at `n in {5,7,9,17}`, same `(m,delta_Nstar)` point.

**Result — falsified. The inner Picard converges cleanly at λ=0, at every
n tested, up to and including n=17:**

| `n` | success | residual | `n_sweeps` | status |
|---|---|---|---|---|
| 5 | **Yes** | −0.12215 | 28 | converged |
| 7 | **Yes** | −0.12108 | 34 | converged |
| 9 | **Yes** | −0.12058 | 33 | converged |
| 17 | **Yes** | −0.12005 | 23 | converged |

Not only does every resolution converge, the **outer-equation residual at
λ=0 is nearly resolution-independent** (`-0.122 -> -0.121 -> -0.121 ->
-0.120`, a 1.7% spread across a `3.4x` range in `n`) — the opposite
signature from what Test A's own `tau/w_core ~ n^2` growth might suggest in
isolation. Per the falsification test's own stated criterion ("if it
converges cleanly at λ=0 and only fails at finite λ, my reading is wrong and
the feasibility-wall story survives"): **the feasibility-wall story
survives.** The SAT closure, though materially significant wherever `pi_core`
is actually pulled away from its target (Test A), is not *by itself* what
breaks the inner Picard contraction at `n=9`/`n=17` — the map is a
well-posed contraction there in the absence of λ-driven noise sourcing. It
is specifically the λ-dependent term (or its interaction with the closure at
finite λ) that produces the failures Diagnostic 12 and Test B both found on
both sides of λ=0.

### Updated reading

**The picture that survives all four tests is more specific than either
extreme.** Test A (validated two independent ways) shows the SAT closure
has a real, `O(1)`-to-dominant effect on the dynamics wherever `pi_core`
departs from its frozen target — this is genuinely not a negligible
regularisation, and its `n²`-growing prefactor is a real, quantified
mechanism. Test A2 shows π does not already satisfy the regularity relation
that would let a live-Neumann target replace the frozen one "for free" — the
frozen target's specific value is doing real, non-trivial work, not just
acting as an arbitrary lagged placeholder for something π would do anyway.
But Test D shows the closure is not, by itself, sufficient to break the
inner Picard map at higher `n` — that requires λ away from zero, consistent
with the original λ-proportional feasibility-wall mechanism, not a
λ-independent closure breakdown. Test B (with its cold-start caveat) is
consistent with this: the search fails away from λ=0 in both directions at
`n=9`, exactly where the closure-times-noise interaction should matter.

Taken together: this is **not** "the SAT closure alone poisons everything,
finite λ included" (Test D rules that out), and it is **not** "the closure
is a negligible regulariser, the corridor is the whole story" (Test A rules
that out) either. The more precise reading is that the closure and the
λ-proportional noise sourcing **interact**: the closure is materially
significant in shaping *where* a converged solution sits for any given
(λ, n) (Test A, and Diagnostic 8t/13's own material τ-dependence), while
the λ-dependent noise term remains the proximate trigger for *why* the
inner Picard stops finding any fixed point at all once `|lambda|` grows,
increasingly readily as `n` grows (via the closure's own `n²` stiffening,
Test A's mechanism). Classification (1) (material τ-dependence, now with a
quantified `n²` mechanism) stands and is the higher-priority finding. The
`n>=9` question is not "closure-poisoned regardless of λ" (Test D), but the
closure's growing stiffness is a plausible amplifier of the genuine,
λ-driven feasibility wall becoming harder to route the outer search around
as `n` increases — worth checking directly (e.g. instrumenting how the
λ-window over which the inner Picard remains a contraction narrows with
`n`) as the natural next step, rather than either extreme reading alone.
