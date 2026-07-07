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
diagnostic (`--mode adjoint`), added to the same module.
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
# Prompt 18 -- discrete adjoint-consistency diagnostic ("--mode adjoint").
#
# Representative point: alpha=0.05, N=2.95, giving delta_s_N ~ 3 -- the
# regime the prompt's own hand reconstruction quotes numbers for
# (L_selfadj ~1.5-1.6, gradient-only block mismatch plateauing ~1.0).
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
    wide-transition regimes prompt 17/18 call out.
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    rows = sweep_adjoint_diagnostics(
        DEFAULT_N_MAX_VALUES, [1.0e-4, 0.1], [0.01, 5.0, 25.0],
    )
    assert len(rows) == len(DEFAULT_N_MAX_VALUES) * 2 * 3
    for row in rows:
        assert row["sbp_residual"] < 1.0e-12


def test_gradient_self_adjointness_residual_plateaus():
    """
    L_selfadj must be O(1) and NOT converge with n_max -- D2 is not the SBP
    second-derivative operator, so the assembled gradient operator L is
    structurally, not just approximately, non-self-adjoint. Anchor: ~1.5-1.6
    at Delta_s~3 (module docstring / prompt 18's own hand reconstruction),
    plateauing rather than decreasing by more than ~2x across the full
    n_max range.
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    residuals = [
        compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)["L_selfadj"]
        for n_max in DEFAULT_N_MAX_VALUES
    ]
    for r in residuals:
        assert 0.5 < r < 20.0
    assert residuals[0] / residuals[-1] < 2.0


@pytest.mark.parametrize("eliminated_suffix", ["", "_eliminated"])
def test_advection_converges_gradient_plateaus(eliminated_suffix):
    """
    Core acceptance criterion: block_mismatch_advection decreases with
    n_max (the SBP-curable advection/D operator) while block_mismatch_
    gradient does not (the structurally non-adjoint D@D-derived gradient
    operator) -- for both the full-node and eliminated representations.
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    adv_key = f"block_mismatch_advection{eliminated_suffix}"
    grad_key = f"block_mismatch_gradient{eliminated_suffix}"

    adv_vals = []
    grad_vals = []
    for n_max in DEFAULT_N_MAX_VALUES:
        diag = compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)
        adv_vals.append(diag[adv_key])
        grad_vals.append(diag[grad_key])

    # Advection-only converges towards zero with resolution.
    assert adv_vals[-1] < adv_vals[0] / 3.0
    assert adv_vals == sorted(adv_vals, reverse=True)

    # Gradient-only does not converge -- stays within a factor ~1.5 of its
    # starting value across the whole n_max range.
    assert grad_vals[-1] > grad_vals[0] / 1.5


def test_block_mismatch_gradient_eliminated_is_exactly_sqrt2():
    """
    Structural identity documented in compute_adjoint_diagnostics's own
    docstring: with advection and c(N) both zeroed, the eliminated forward/
    response gradient blocks are purely off-block-diagonal and land at
    TRANSPOSED (not coincident) positions after the role-swap reordering,
    so the weighted mismatch ratio collapses to exactly sqrt(2) regardless
    of n_max -- the eliminated representation's own boundary/SAT signature,
    distinct from the full-node (non-degenerate, plateauing) counterpart.
    """
    from analyze_StiffnessSpectrum import DEFAULT_N_MAX_VALUES

    for n_max in DEFAULT_N_MAX_VALUES:
        diag = compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)
        assert diag["block_mismatch_gradient_eliminated"] == pytest.approx(np.sqrt(2.0), rel=1.0e-10)


def test_full_dominated_by_gradient():
    """block_mismatch_full tracks block_mismatch_gradient (not the
    converging block_mismatch_advection) at large n_max, in both
    representations -- the gradient term dominates the full mismatch."""
    n_max = 192
    diag = compute_adjoint_diagnostics(n_max, ADJOINT_ALPHA, ADJOINT_N)

    assert abs(diag["block_mismatch_full"] - diag["block_mismatch_gradient"]) < \
        abs(diag["block_mismatch_full"] - diag["block_mismatch_advection"])
    assert abs(diag["block_mismatch_full_eliminated"] - diag["block_mismatch_gradient_eliminated"]) < \
        abs(diag["block_mismatch_full_eliminated"] - diag["block_mismatch_advection_eliminated"])


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
