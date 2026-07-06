# Prompt 10 — Strengthen the `r_phys` reduction test with a genuine independent cross-check

## Context

`tests/test_scale_assignment.py::test_r_phys_core_reduction_matches_compaction_function_step_c`
(prompt 09) verifies a real but narrower property than its name claims. It
checks that `r_phys[-1]` equals `ln_k_phys_Mpc` called directly with
`N_before_end` shifted by `-delta_s_N_final`, using the **same outer-edge**
`V`/`epsilon`/`V_end_downflow`. Because `ln_k_phys_Mpc`'s formula is
`-N_before_end + f(...)` — linear in `N_before_end`, with no other
dependence on it — this equality holds **by construction of that formula's
own shape**, regardless of whether `assign_scales`'s physics is actually
right. It's a legitimate, cheap internal-consistency check, but it cannot
catch a wrong node index, a sign error in `comoving_radius_ratio`, or
`r_phys_out` being anchored to the wrong state — because its reference
value is algebraically derived from the same computation it's checking,
just with re-arranged arguments.

This prompt does two things: relabels that existing test honestly, and
adds a **genuinely independent** reduction test — one whose reference value
comes from downflowing the **core's own** converged trajectory directly,
not from re-deriving the outer-edge anchor's own arithmetic.

## Task

### Part A — relabel the existing test, no logic change

Rename `test_r_phys_core_reduction_matches_compaction_function_step_c` to
`test_r_phys_ln_k_linearity_self_consistency` (or similar — the point is
the name and docstring should no longer imply this is a reduction/physics
check). Rewrite its docstring to state plainly: this confirms
`ln_k_phys_Mpc`'s linear `-N_before_end` structure is applied consistently
by `assign_scales`'s ratio construction — an algebraic identity, not an
independent physical cross-check. Don't change its assertions or logic,
only its name and documentation.

### Part B — the genuine independent test

`test_r_phys_matches_independent_core_downflow` in the same file:

1. **Reuse prompt 06's own reduction-test fixture/scenario** — same
   potential, `N_init`/`N_final`/`delta_Nstar`, and the same mechanism that
   test used to disable spatial coupling (`disable_spatial_coupling`
   threaded through `solve_picard`, per prompt 06). Locate and reuse it
   directly rather than constructing a fresh scenario from scratch.
2. Run `solve_picard` with spatial coupling disabled, using a **small,
   non-zero `alpha`** (not `0.0` — that's the coordinate singularity
   Claude Code already found while debugging Part A's predecessor; not
   `1.0`-scale either, since the point is to check the regime where
   `onion_notes.tex`'s §"Equivalence check" says agreement should hold up
   to $\mathcal O(\alpha)$ corrections). Get the converged core state
   $(\phi_{\rm core}(N_{\rm total}), \pi_{\rm core}(N_{\rm total}))$ — the
   last grid node's final row.
3. **Independent reference, computed without touching `assign_scales` or
   the outer edge at all**: downflow the core's own state directly via
   `integrate_noiseless_trajectory` (imported the same way
   `extraction.py` already does), giving `N_end_downflow_core`,
   `phi_end_downflow_core`. Then call `ln_k_phys_Mpc` directly with the
   core's own `V`, `epsilon`, `V_end_downflow` (not the outer edge's) —
   matching what `CompactionFunction`'s own Step C would compute for this
   trajectory's own final sample point. This is a **different downflow**
   from the one `extract_zeta_profile` computes for the outer edge — that
   independence is the entire point.
4. Run the actual pipeline (`extract_zeta_profile` + `assign_scales`) on
   the full converged grid solution from step 2, exactly as a real solve
   would, to get `result["r_phys"][-1]`.
5. Compare `result["r_phys"][-1]` against the independent core-downflow
   reference from step 3. **This should not be expected to match to
   floating-point precision** — per `onion_notes.tex`'s own "Equivalence
   check" section, agreement holds exactly only as $\alpha\to0$, with
   $\mathcal O(\alpha)$ corrections at finite $\alpha$. Choose a tolerance
   that reflects "small, $\alpha$-scale correction," document the reasoning
   in the test's own docstring (mirroring how prompt 08's core $\zeta$
   check documented its own approximate tolerance), and don't let a future
   editor tighten this into a spurious failure by mistaking it for a
   should-be-exact check.
6. **Bonus, if not much extra effort**: run this at two different small
   `alpha` values and confirm the discrepancy shrinks as `alpha` shrinks —
   a stronger, more diagnostic check than a single fixed tolerance, and
   more directly a test of the actual $\mathcal O(\alpha)$ claim rather
   than just "small enough." Don't force this if it adds significant
   complexity — a single well-reasoned tolerance is an acceptable fallback.

## Acceptance criteria

- [ ] Existing test renamed and re-documented per Part A, no logic change.
- [ ] New test's reference value comes from an independent downflow of the
      **core's own** converged state — not derived from `assign_scales`'s
      own outer-edge arithmetic.
- [ ] New test reuses prompt 06's fixture/scenario rather than constructing
      a new one from scratch.
- [ ] Tolerance is documented as reflecting an expected $\mathcal O(\alpha)$
      discrepancy, not floating-point equality.
- [ ] Both tests pass.
- [ ] No other files touched.

## Commit

Single commit, message along the lines of:
`Relabel ln_k linearity self-consistency test; add genuine independent core-downflow reduction test for r_phys`
