# (c) University of Sussex 2026
# Created by David Seery
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tests for prompt 23 Phase 1 -- the response-sector spectral diagnostic
extension of analyze_StiffnessSpectrum.py. Full derivation and findings:
.documents/gradient-coupled-instanton/23-response-sbp-sat-design-note.md.

These are the executable form of the prompt's Phase 1 acceptance checklist:
  - Confirm/deny the disease (does the strong-BC response operator have an
    n_max-growing spectral abscissa, in the sense relevant to its ACTUAL
    backward-in-N integration direction).
  - Confirm/deny that a naive same-recipe SBP-SAT port cures it.
  - Adjoint-consistency of the SAT'd-forward/unchanged-response pair.

The headline finding (a legitimate "clean negative", per the prompt's own
"Clean-negative is valid... report it and scope it rather than forcing the
port"): the response sector's pre-port "strong" closure does NOT exhibit the
forward sector's disease once correctly analyzed for backward integration --
its backward-relevant spectral abscissa (response_spectral_stability_metrics,
NOT spectral_stability_metrics directly -- the sign convention differs
because response_rhs is integrated backward, see that function's own
docstring) is already bounded/n_max-independent across the whole default
sweep grid. A naive port of the forward sector's SBP-SAT closure (mirrored
with the theoretically-required sign flip on the live-Neumann-target field)
does not improve on this and makes the safe-direction stiffness (max Re, the
non-catastrophic-but-still-costly direction for backward integration)
markedly worse. Prompt 23 therefore does NOT port the SBP-SAT closure to the
response sector's advection treatment.
"""

import numpy as np
import pytest

from tools.diagnostics.GradientCoupledInstanton.spectrum import (
    DEFAULT_ALPHA_VALUES,
    DEFAULT_N_VALUES,
    assemble_response_operator_strong,
    assemble_response_operator_sbp_sat,
    response_spectral_stability_metrics,
    self_check_response_assembled_operator,
    sweep_response_eigenvalues,
    compute_forward_sat_vs_response_adjoint_mismatch,
    compute_adjoint_diagnostics,
)

# Sweeps N_MAX_SWEEP (up to n_max=192) through dense eigendecompositions --
# minutes, not seconds. Only worth running when ComputeTargets/ (or its
# numerical dependencies, incl.
# tools/diagnostics/GradientCoupledInstanton/spectrum.py) change; see
# .claude/rules/test-selection.md.
pytestmark = pytest.mark.slow

N_MAX_SWEEP = [8, 16, 32, 64, 128, 192]


# ---------------------------------------------------------------------------
# Self-check: hand-assembled matrix matches a finite-difference Jacobian of
# the real (frozen-coefficient) response_rhs, spatial-only isolated.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n_max, alpha, N, epsilon_core",
    [
        (8, 0.1, 0.1, 0.01),
        (16, 0.1, 5.0, 0.01),
        (32, 0.05, 10.0, 0.05),
    ],
)
def test_self_check_response_assembled_operator(n_max, alpha, N, epsilon_core):
    diff = self_check_response_assembled_operator(n_max, alpha, N, epsilon_core)
    assert diff < 1.0e-6


# ---------------------------------------------------------------------------
# Sign-convention sanity: response_spectral_stability_metrics must be the
# NEGATED-eigenvalue version of spectral_stability_metrics -- a regression
# guard against silently "fixing" this back to the forward convention.
# ---------------------------------------------------------------------------


def test_response_spectral_stability_metrics_is_negated_convention():
    from tools.diagnostics.GradientCoupledInstanton.spectrum import spectral_stability_metrics

    matrix, _ = assemble_response_operator_strong(16, 0.1, 5.0)
    eig = np.linalg.eigvals(matrix)

    forward_convention = spectral_stability_metrics(eig)
    response_convention = response_spectral_stability_metrics(eig)

    assert response_convention["spectral_abscissa"] == pytest.approx(-float(np.min(eig.real)))
    assert forward_convention["spectral_abscissa"] == pytest.approx(float(np.max(eig.real)))
    # The two only coincide when the spectrum happens to be symmetric about
    # zero, which is not the case at a generic sweep point -- confirms this
    # test would actually catch a regression back to the wrong convention.
    assert response_convention["spectral_abscissa"] != pytest.approx(forward_convention["spectral_abscissa"])


# ---------------------------------------------------------------------------
# Headline Phase-1 finding: the strong closure's backward-relevant abscissa
# is ALREADY bounded/n-independent across the default sweep grid -- i.e. the
# disease response_rhs.py's own pre-port docstring anticipated ("by
# symmetry") is NOT confirmed once the backward integration direction is
# correctly accounted for.
# ---------------------------------------------------------------------------


def test_strong_closure_backward_abscissa_bounded_across_default_grid():
    for alpha in DEFAULT_ALPHA_VALUES:
        for N in DEFAULT_N_VALUES:
            abscissas = []
            for n_max in N_MAX_SWEEP:
                matrix, _ = assemble_response_operator_strong(n_max, alpha, N)
                metrics = response_spectral_stability_metrics(np.linalg.eigvals(matrix))
                abscissas.append(metrics["spectral_abscissa"])
            # Ratio of the n_max=192 value to the n_max=8 value, with an
            # absolute floor on the denominator -- a relative *spread*
            # metric ((max-min)/denom) is unstable near the sign-crossing,
            # small-magnitude points this sweep includes (e.g. abscissa
            # ~-0.1 at alpha=0.1, N=1.0), where genuinely bounded O(0.1-1)
            # values can show a large-looking fractional spread despite not
            # growing at all in absolute terms. A last/first ratio with an
            # O(1) floor is the robust way to detect genuine n^1.6-ish
            # growth (ratios of 50-900+, as seen in the *unbounded*
            # direction, max Re) versus this bounded direction's mild,
            # non-diverging drift.
            a = np.array(abscissas)
            ratio = abs(a[-1]) / max(abs(a[0]), 1.0)
            assert ratio < 5.0, (
                f"alpha={alpha}, N={N}: backward-relevant abscissa n_max=8->192 ratio "
                f"{ratio:.4f} -- {a} (unexpectedly NOT bounded; the clean-negative "
                f"finding this test guards may no longer hold, see the design note)"
            )


def test_naive_sbp_sat_port_does_not_improve_safe_direction_stiffness():
    """
    Documents the negative result directly: a same-recipe SBP-SAT port (with
    the sign flip required for backward integration on the live-Neumann-
    target field) does not reduce -- and typically increases -- the
    safe-direction (max Re) growth relative to the unmodified strong
    closure, at every default-grid point. This is why prompt 23 does not
    port the closure; this test guards against silently believing otherwise
    without re-checking the numbers.
    """
    worse_count = 0
    total = 0
    for alpha in DEFAULT_ALPHA_VALUES:
        for N in DEFAULT_N_VALUES:
            m_strong, _ = assemble_response_operator_strong(192, alpha, N)
            m_sat, _, _, _ = assemble_response_operator_sbp_sat(192, alpha, N)
            max_re_strong = float(np.max(np.linalg.eigvals(m_strong).real))
            max_re_sat = float(np.max(np.linalg.eigvals(m_sat).real))
            total += 1
            if max_re_sat >= max_re_strong - 1.0e-8:
                worse_count += 1
    # Not every single point need be strictly worse (some are close/tied at
    # small |A_core|), but the overwhelming majority must be, matching the
    # design note's own sweep.
    assert worse_count / total > 0.8


# ---------------------------------------------------------------------------
# sweep_response_eigenvalues -- CLI/CSV plumbing consistency.
# ---------------------------------------------------------------------------


def test_sweep_response_eigenvalues_matches_direct_assembly():
    from tools.diagnostics.GradientCoupledInstanton.spectrum import CSV_FIELDNAMES

    rows = sweep_response_eigenvalues([8, 16], [0.1], [0.1, 10.0], closure="strong")
    assert set(rows[0].keys()) == set(CSV_FIELDNAMES)

    for row in rows:
        matrix, _ = assemble_response_operator_strong(row["n_max"], row["alpha"], row["N"])
        expected = response_spectral_stability_metrics(np.linalg.eigvals(matrix))
        assert row["spectral_abscissa"] == pytest.approx(expected["spectral_abscissa"])
        assert row["n_rhp"] == expected["n_rhp"]


def test_sweep_response_eigenvalues_rejects_unknown_closure():
    with pytest.raises(ValueError):
        sweep_response_eigenvalues([8], [0.1], [0.1], closure="bogus")


# ---------------------------------------------------------------------------
# Adjoint-consistency: the SAT'd-forward/unchanged-response pair's boundary
# mismatch stays bounded in n_max, matching the pre-existing (both-plain)
# baseline -- porting the forward sector alone (prompt 21a) did not
# introduce a new, growing forward/response asymmetry defect.
# ---------------------------------------------------------------------------


def test_sat_forward_vs_unchanged_response_mismatch_bounded_in_n():
    for alpha in (DEFAULT_ALPHA_VALUES[0], DEFAULT_ALPHA_VALUES[-1]):
        for N in DEFAULT_N_VALUES:
            d8 = compute_forward_sat_vs_response_adjoint_mismatch(8, alpha, N)
            d192 = compute_forward_sat_vs_response_adjoint_mismatch(192, alpha, N)
            ratio = d192["block_mismatch_full"] / max(d8["block_mismatch_full"], 1.0e-8)
            assert ratio < 2.0, (
                f"alpha={alpha}, N={N}: block_mismatch_full grew by {ratio:.3f}x from "
                f"n_max=8 to 192 -- the SAT'd-forward/unchanged-response boundary "
                f"mismatch is no longer bounded"
            )


def test_sat_forward_vs_unchanged_response_mismatch_comparable_to_preexisting_baseline():
    """The SAT'd-forward/unchanged-response mismatch should be the same
    order of magnitude as the pre-existing (both sectors plain) 18a
    baseline -- porting only the forward sector's advection should not, by
    itself, dramatically worsen the two sectors' adjoint consistency."""
    alpha, N = 0.1, 10.0
    baseline = compute_adjoint_diagnostics(32, alpha, N)
    sat_vs_unchanged = compute_forward_sat_vs_response_adjoint_mismatch(32, alpha, N)
    ratio = sat_vs_unchanged["block_mismatch_full"] / baseline["block_mismatch_full"]
    assert 0.1 < ratio < 10.0
