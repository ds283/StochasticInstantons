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
spatial discretisation.
"""

import csv

import numpy as np
import pytest

from analyze_StiffnessSpectrum import (
    CSV_FIELDNAMES,
    assemble_spatial_operator,
    self_check_assembled_operator,
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
