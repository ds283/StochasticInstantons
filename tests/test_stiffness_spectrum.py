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
Tests for prompt 17 Part A -- analyze_StiffnessSpectrum.py, the assembled-
operator eigenvalue sweep for the gradient-coupled instanton's onion-model
spatial discretisation -- and prompt 18's discrete adjoint-consistency
diagnostic (`--mode adjoint`), amended in prompt 18a to fix `L_selfadj`
(now inversion-free) and replace the `*_eliminated` columns with full-node
`*_interior` companions. Prompt 20 adds the signed spectral abscissa /
right-half-plane eigenvalue count / growth e-fold time to `--mode spectrum`.
"""

import csv

import numpy as np
import pytest

from analyze_StiffnessSpectrum import (
    ADJOINT_CSV_FIELDNAMES,
    CSV_FIELDNAMES,
    assemble_spatial_operator,
    compute_adjoint_diagnostics,
    self_check_assembled_operator,
    spectral_stability_metrics,
    sweep_adjoint_diagnostics,
    sweep_eigenvalues,
    write_csv,
)


# ---------------------------------------------------------------------------
# Self-check: assembled operator vs. finite-difference Jacobian of the real
# forward_rhs, across the parameter regimes prompt 17 explicitly calls out.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n_max, alpha, N",
    [
        (8, 0.05, 1.0),
        (16, 0.05, 5.0),
        (32, 1.0e-4, 0.01),   # near the alpha-regularized N_init coordinate singularity
        (32, 0.1, 25.0),      # wide-transition Delta_s ~ 20+ regime
        (64, 0.05, 20.0),     # production-scale n_max
    ],
)
def test_assembled_operator_matches_finite_difference_jacobian(n_max, alpha, N):
    """
    The frozen-coefficient assembled operator must faithfully reflect the
    real forward_rhs's own spatial-only Jacobian (relative tolerance, since
    the coordinate-singularity regime produces very large matrix entries --
    see analyze_StiffnessSpectrum.py's own module docstring for why the
    finite-difference construction uses a constant-H_sq/epsilon stub
    potential to make this an exact-up-to-roundoff comparison rather than a
    leading-order one).
    """
    matrix, delta_s_N = assemble_spatial_operator(n_max, alpha, N)
    assert np.isfinite(matrix).all()

    max_abs_diff = self_check_assembled_operator(n_max, alpha, N)
    scale = max(np.max(np.abs(matrix)), 1.0)
    assert max_abs_diff / scale < 1.0e-6


# ---------------------------------------------------------------------------
# Sweep smoke test: runs end-to-end and produces the structured CSV output
# with the expected columns.
# ---------------------------------------------------------------------------


def test_sweep_produces_expected_csv(tmp_path):
    n_max_values = [8, 16]
    alpha_values = [0.001, 0.05]
    N_values = [0.5, 5.0]

    rows = sweep_eigenvalues(n_max_values, alpha_values, N_values)
    assert len(rows) == len(n_max_values) * len(alpha_values) * len(N_values)
    for row in rows:
        assert set(row.keys()) == set(CSV_FIELDNAMES)
        assert row["op_norm"] > 0.0
        assert row["max_abs_re_lambda"] >= 0.0
        assert row["max_abs_im_lambda"] >= 0.0
        assert row["implied_rk45_max_dt"] > 0.0

    output_path = tmp_path / "stiffness_spectrum.csv"
    write_csv(rows, output_path)
    assert output_path.exists()

    with open(output_path, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CSV_FIELDNAMES
        read_rows = list(reader)
    assert len(read_rows) == len(rows)


def test_sweep_op_norm_grows_with_n_max():
    """Sanity check that the sweep reproduces the qualitative O(n_max^4)-ish
    growth the review's own bare-D2 table found, now for the assembled
    (prefactor-dressed) operator at a fixed (alpha, N) point."""
    rows = sweep_eigenvalues([8, 16, 32], [0.05], [5.0])
    op_norms = [r["op_norm"] for r in rows]
    assert op_norms == sorted(op_norms)
    assert op_norms[-1] > op_norms[0] * 10.0


# ---------------------------------------------------------------------------
# Prompt 18 (metric fixes in 18a) -- discrete adjoint-consistency diagnostic
# ("--mode adjoint").
#
# Representative point: alpha=0.05, N=2.95, giving delta_s_N ~ 3 -- the
# regime the prompt's own hand reconstruction quotes numbers for
# (L_selfadj ~1.0-1.4, gradient-only block mismatch plateauing ~1.0).
# ---------------------------------------------------------------------------

ADJOINT_ALPHA = 0.05
ADJOINT_N = 2.95  # delta_s_N = ln(1.05) + 2.95 ~ 2.999


def test_sbp_residual_machine_zero_across_default_grid():
    """
    sbp_residual is the sanity check on the grid/weight wiring: it must be
    ~machine-zero at every sweep point, independent of alpha/N (the SBP
    identity concerns only the LGL D matrix and its quadrature weights).
    Uses a subset of the default n_max/alpha/N lists to keep runtime
    reasonable while still spanning the coordinate-singularity and
    wide-transition regimes prompt 17/18 call out. Unaffected by the 18a
    metric fixes (sbp_residual is untouched by both fixes).
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    rows = sweep_adjoint_diagnostics(
        DEFAULT_N_MAX_VALUES, [1.0e-4, 0.1], [0.01, 5.0, 25.0],
    )
    assert len(rows) == len(DEFAULT_N_MAX_VALUES) * 2 * 3
    for row in rows:
        assert row["sbp_residual"] < 1.0e-12


def test_L_selfadj_stays_O1_at_all_delta_s():
    """
    Prompt 18a fix 1: the inversion-free L_selfadj must stay O(1) at every
    Delta_s, including the wide-transition regime (Delta_s~25) where the
    original ‖W⁻¹ Lᵀ W − L‖/‖L‖ form blew up to ~1e7-1e9 pure roundoff
    (condition number of W ~ exp(3*Delta_s)). Anchor: ~1.0-1.4 (module
    docstring), n_max=64 across Delta_s=1..25.
    """
    import math

    for delta_s_target in (1.0, 5.0, 10.0, 15.0, 20.0, 25.0):
        N = delta_s_target - math.log(1.05)
        diag = compute_adjoint_diagnostics(64, ADJOINT_ALPHA, N)
        assert 0.9 < diag["L_selfadj"] < 2.0


def test_gradient_self_adjointness_residual_plateaus():
    """
    L_selfadj (full-node) must be O(1) and NOT converge with n_max -- D2 is
    not the SBP second-derivative operator, so the assembled gradient
    operator L is structurally, not just approximately, non-self-adjoint.
    Anchor: ~1.0-1.4 at Delta_s~3 (module docstring / prompt 18a's fixed
    metric), plateauing rather than decreasing by more than ~2x across the
    full n_max range.
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    residuals = [
        compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)["L_selfadj"]
        for n_max in DEFAULT_N_MAX_VALUES
    ]
    for r in residuals:
        assert 0.9 < r < 2.0
    assert residuals[0] / residuals[-1] < 2.0


def test_L_selfadj_interior_converges_spectrally():
    """
    Prompt 18a's key result: L_selfadj_interior -> 0 spectrally in n_max at
    every Delta_s -- the mu-weighted bulk gradient operator IS discretely
    self-adjoint; its O(1) full-node mismatch is entirely at y=+-1. Anchor
    (Delta_s=25): ~7.7e-2 -> ~3.2e-4 over n=16->192.
    """
    import math
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    N = 25.0 - math.log(1.0 + ADJOINT_ALPHA)
    residuals = [
        compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, N)["L_selfadj_interior"]
        for n_max in DEFAULT_N_MAX_VALUES
    ]
    assert residuals == sorted(residuals, reverse=True)
    assert residuals[-1] < residuals[0] / 100.0


def test_advection_converges_gradient_plateaus():
    """
    Core acceptance criterion: block_mismatch_advection decreases with
    n_max (the SBP-curable advection/D operator) while block_mismatch_
    gradient does not (the structurally non-adjoint D@D-derived gradient
    operator) -- full-node representation (the only one left after 18a
    drops *_eliminated).
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    adv_vals = []
    grad_vals = []
    for n_max in DEFAULT_N_MAX_VALUES:
        diag = compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)
        adv_vals.append(diag["block_mismatch_advection"])
        grad_vals.append(diag["block_mismatch_gradient"])

    # Advection-only converges towards zero with resolution.
    assert adv_vals[-1] < adv_vals[0] / 3.0
    assert adv_vals == sorted(adv_vals, reverse=True)

    # Gradient-only does not converge -- stays within a factor ~1.5 of its
    # starting value across the whole n_max range.
    assert grad_vals[-1] > grad_vals[0] / 1.5


def test_block_mismatch_gradient_interior_converges_spectrally():
    """
    Prompt 18a acceptance anchor: block_mismatch_gradient_interior -> 0
    spectrally with n_max -- gradient non-adjointness is boundary-localized,
    replacing the *_eliminated sqrt(2) artifact this metric used to be
    compared against.
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    grad_interior_vals = [
        compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)["block_mismatch_gradient_interior"]
        for n_max in DEFAULT_N_MAX_VALUES
    ]
    assert grad_interior_vals == sorted(grad_interior_vals, reverse=True)
    assert grad_interior_vals[-1] < grad_interior_vals[0] / 100.0


def test_block_mismatch_advection_interior_tracks_full_node():
    """
    Prompt 18a acceptance anchor: block_mismatch_advection_interior ~=
    block_mismatch_advection at every n_max -- advection mismatch is bulk,
    not boundary, so masking the boundary out barely moves the number
    (unlike the gradient block, where interior collapses relative to
    full-node).
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    for n_max in DEFAULT_N_MAX_VALUES:
        diag = compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)
        assert diag["block_mismatch_advection_interior"] == pytest.approx(
            diag["block_mismatch_advection"], rel=0.05,
        )


def test_full_dominated_by_gradient():
    """block_mismatch_full tracks block_mismatch_gradient (not the
    converging block_mismatch_advection) at large n_max -- the gradient
    term dominates the full mismatch."""
    n_max = 192
    diag = compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)

    assert abs(diag["block_mismatch_full"] - diag["block_mismatch_gradient"]) < \
        abs(diag["block_mismatch_full"] - diag["block_mismatch_advection"])


def test_adjoint_sweep_produces_expected_csv(tmp_path):
    n_max_values = [8, 16]
    alpha_values = [0.001, 0.05]
    N_values = [0.5, 5.0]

    rows = sweep_adjoint_diagnostics(n_max_values, alpha_values, N_values)
    assert len(rows) == len(n_max_values) * len(alpha_values) * len(N_values)
    for row in rows:
        assert set(row.keys()) == set(ADJOINT_CSV_FIELDNAMES)
        assert row["sbp_residual"] >= 0.0
        assert row["L_selfadj"] > 0.0
        assert row["L_selfadj_interior"] >= 0.0

    output_path = tmp_path / "adjoint_diagnostic.csv"
    write_csv(rows, output_path, fieldnames=ADJOINT_CSV_FIELDNAMES)
    assert output_path.exists()

    with open(output_path, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ADJOINT_CSV_FIELDNAMES
        read_rows = list(reader)
    assert len(read_rows) == len(rows)


def test_spectrum_mode_unaffected_by_adjoint_addition(tmp_path):
    """No-regression check (acceptance criterion): sweep_eigenvalues/
    write_csv's default behaviour for --mode spectrum is untouched by the
    prompt 18 addition."""
    rows = sweep_eigenvalues([8, 16], [0.05], [5.0])
    assert set(rows[0].keys()) == set(CSV_FIELDNAMES)

    output_path = tmp_path / "spectrum.csv"
    write_csv(rows, output_path)
    with open(output_path, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == CSV_FIELDNAMES


# ---------------------------------------------------------------------------
# Prompt 20 -- signed spectral abscissa + RHP eigenvalue count.
#
# max_abs_re_lambda (prompt 17) discards sign, so a spurious +1500 (a genuine
# growing mode) is indistinguishable from a stable -1500. These tests check
# that the new columns preserve sign and correctly localize the instability
# to the initial layer (small N, near the alpha-regularized N_init
# coordinate singularity).
# ---------------------------------------------------------------------------


def test_spectral_abscissa_positive_and_grows_with_n_max_at_small_delta_s():
    """
    Acceptance anchor: at small Delta_s (N=0.1, alpha=0.1) the signed
    spectral abscissa is POSITIVE -- a genuine growing mode -- and increases
    monotonically with n_max. The exact magnitudes depend on the real
    background state; sign and monotone growth are the acceptance criteria.
    """
    n_max_values = [8, 16, 32, 64]
    abscissas = []
    for n_max in n_max_values:
        matrix, _ = assemble_spatial_operator(n_max, 0.1, 0.1)
        metrics = spectral_stability_metrics(np.linalg.eigvals(matrix))
        abscissas.append(metrics["spectral_abscissa"])

    assert all(a > 0.0 for a in abscissas)
    assert abscissas == sorted(abscissas)


def test_n_rhp_positive_and_reaches_full_rank_at_smallest_delta_s():
    """
    Acceptance anchor: n_rhp > 0 at small Delta_s and grows with n_max,
    approaching the full 2*n_max-1 unstable modes at the smallest Delta_s
    in the default sweep (N=0.01).
    """
    for n_max in (8, 16, 32):
        matrix, _ = assemble_spatial_operator(n_max, 0.1, 0.01)
        metrics = spectral_stability_metrics(np.linalg.eigvals(matrix))
        assert metrics["n_rhp"] > 0
        assert metrics["n_rhp"] == 2 * n_max - 1


def test_spectral_abscissa_shrinks_by_orders_of_magnitude_away_from_N_init():
    """
    Acceptance anchor: moving from the initial layer (small N) into the
    production wide-transition regime (N>=5) the spectral abscissa drops by
    orders of magnitude at fixed (production) n_max -- consistent with the
    empirical blow-up localizing near N_init. At n_max=16, alpha=0.1 this
    frozen-coefficient reconstruction does not drive the abscissa
    non-positive by N=25 (it stays O(1)), so this checks the localizing
    trend rather than a sign flip.
    """
    n_max = 16
    matrix_small, _ = assemble_spatial_operator(n_max, 0.1, 0.1)
    matrix_large, _ = assemble_spatial_operator(n_max, 0.1, 25.0)
    abscissa_small = spectral_stability_metrics(np.linalg.eigvals(matrix_small))["spectral_abscissa"]
    abscissa_large = spectral_stability_metrics(np.linalg.eigvals(matrix_large))["spectral_abscissa"]

    assert abscissa_large < abscissa_small / 50.0


def test_growth_efold_time_much_less_than_N_total_at_small_delta_s():
    """
    Acceptance anchor: growth_efold_time << N_total at production n_max and
    small Delta_s -- the quantitative statement that the solve cannot
    survive the initial layer regardless of step size.
    """
    matrix, _ = assemble_spatial_operator(16, 0.1, 0.1)
    metrics = spectral_stability_metrics(np.linalg.eigvals(matrix))
    N_total_representative = 20.0
    assert metrics["growth_efold_time"] < N_total_representative / 100.0


def test_growth_efold_time_is_inf_when_abscissa_non_positive():
    """When every mode is stable (abscissa <= 0), there is no growing mode
    and growth_efold_time must report inf rather than a negative timescale,
    with n_rhp == 0."""
    metrics = spectral_stability_metrics(np.array([-1.0, -2.0, -0.5]))
    assert metrics["spectral_abscissa"] < 0.0
    assert metrics["n_rhp"] == 0
    assert metrics["growth_efold_time"] == float("inf")


def test_sweep_eigenvalues_reports_prompt20_columns_consistently():
    """spectral_abscissa/n_rhp/growth_efold_time from the sweep must agree
    with directly recomputing them from the same assembled operator, and
    existing prompt-17 columns must be untouched."""
    rows = sweep_eigenvalues([8, 16], [0.1], [0.1, 25.0])
    assert set(rows[0].keys()) == set(CSV_FIELDNAMES)

    for row in rows:
        matrix, _ = assemble_spatial_operator(row["n_max"], row["alpha"], row["N"], )
        expected = spectral_stability_metrics(np.linalg.eigvals(matrix))
        assert row["spectral_abscissa"] == pytest.approx(expected["spectral_abscissa"])
        assert row["n_rhp"] == expected["n_rhp"]
        if np.isinf(expected["growth_efold_time"]):
            assert np.isinf(row["growth_efold_time"])
        else:
            assert row["growth_efold_time"] == pytest.approx(expected["growth_efold_time"])
