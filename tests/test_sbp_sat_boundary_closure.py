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
Tests for prompt 21 Phase 1 -- the standalone SBP-SAT boundary-closure
prototype in analyze_StiffnessSpectrum.py. Full derivation this validates:
.documents/gradient-coupled-instanton/21-sbp-sat-design-note.md.

These are the executable form of the prompt's Phase 1c acceptance gate:
  - SBP self-check (unaffected by this prompt, re-asserted as a guard).
  - The closed-form energy defect derived by hand (design note Section 3)
    matches the general definition (advection_split_energy_defect).
  - Advection-only SBP-SAT operator reproduces -A(core)/4, n-independent.
  - Full SBP-SAT operator (gradient + split advection + SAT) has an
    n-independent (bounded) spectral abscissa, in sharp contrast to the
    strong-BC baseline's growth.
  - growth_efold_time is no longer catastrophically small at small Delta_s.

No production code (ComputeTargets/GradientCoupledInstanton/) is touched or
exercised differently by this file -- Phase 1 is diagnostic-only, per the
prompt's explicit gate ("do not start Phase 2 until Phase 1's abscissa
criterion passes").
"""

import numpy as np
import pytest

from tools.diagnostics.GradientCoupledInstanton.spectrum import (
    DEFAULT_ALPHA_VALUES,
    DEFAULT_N_VALUES,
    advection_split_energy_defect,
    assemble_spatial_operator,
    assemble_spatial_operator_sbp_sat,
    spectral_stability_metrics,
    sweep_eigenvalues,
    _sbp_residual,
)
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import advection_coefficient, delta_s

# Sweeps DEFAULT_N_VALUES/DEFAULT_ALPHA_VALUES through dense eigendecomposition
# and finite-difference checks -- minutes, not seconds. Only worth running
# when ComputeTargets/ (or its numerical dependencies, incl.
# tools/diagnostics/GradientCoupledInstanton/spectrum.py) change; see
# .claude/rules/test-selection.md.
pytestmark = pytest.mark.slow


# ---------------------------------------------------------------------------
# SBP self-check -- unaffected by this prompt, re-asserted as a regression
# guard since the whole energy estimate rests on it.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_max", [8, 16, 32, 64])
def test_sbp_residual_still_machine_zero(n_max):
    grid = LGLCollocationGrid(n_max + 1)
    assert _sbp_residual(grid) < 1.0e-12


# ---------------------------------------------------------------------------
# Design note Section 3: closed-form energy defect of the split-form
# advection operator, H @ A_split + A_split^T @ H
#   = diag(-A_0, 0, ..., 0, A_core) - a' * H,     a' = (1-eps_core)/Delta_s(N)
# (using A_0 = A(-1) = 0 exactly and D @ A = a' * ones, since A(y) is affine).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n_max, alpha, N, epsilon_core",
    [
        (8, 0.1, 0.1, 0.01),
        (16, 0.1, 0.1, 0.01),
        (32, 0.05, 5.0, 0.2),
        (64, 1.0e-4, 0.01, 0.01),   # near the alpha-regularized coordinate singularity
    ],
)
def test_energy_defect_matches_closed_form(n_max, alpha, N, epsilon_core):
    grid = LGLCollocationGrid(n_max + 1)
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    S = advection_split_energy_defect(grid, A_array)

    # Off-diagonal must vanish (S is exactly diagonal, up to roundoff).
    off_diag = S - np.diag(np.diag(S))
    assert np.linalg.norm(off_diag) < 1.0e-10 * np.linalg.norm(S)

    a_prime = (1.0 - epsilon_core) / delta_s_N
    expected_diag = -a_prime * grid.weights
    expected_diag[-1] += A_array[-1]   # core row's +A_core correction

    assert A_array[0] == pytest.approx(0.0, abs=1.0e-14)   # A(-1) = 0 exactly
    np.testing.assert_allclose(np.diag(S), expected_diag, atol=1.0e-10, rtol=1.0e-8)

    # The core entry must be the ~n-independent, O(1) destabilizing one:
    # A_core - a'*w_core -> A_core as n_max grows (w_core -> 0), and stays
    # positive since epsilon_core < 1, Delta_s(N) > 0.
    assert S[-1, -1] > 0.0
    assert S[-1, -1] == pytest.approx(A_array[-1] - a_prime * grid.weights[-1])


# ---------------------------------------------------------------------------
# Advection-only sub-check: reproduces the validated -A(core)/4 constant,
# exactly and n-independently (design note Section 4).
# ---------------------------------------------------------------------------


def test_advection_only_sbp_sat_reproduces_minus_A_core_over_4():
    alpha, N, epsilon_core = 0.1, 0.1, 0.01
    abscissas = []
    A_cores = []
    for n_max in (7, 15, 31, 63, 127, 191):
        matrix, _, tau, A_core = assemble_spatial_operator_sbp_sat(
            n_max, alpha, N, epsilon_core, include_gradient=False,
        )
        assert tau == pytest.approx(0.5 * A_core)
        metrics = spectral_stability_metrics(np.linalg.eigvals(matrix))
        abscissas.append(metrics["spectral_abscissa"])
        A_cores.append(A_core)

    # A(core) itself is a fixed number at fixed (alpha, N, epsilon_core),
    # independent of n_max (frozen-coefficient construction).
    assert all(a == pytest.approx(A_cores[0]) for a in A_cores)

    target = -A_cores[0] / 4.0
    for a in abscissas:
        assert a == pytest.approx(target, rel=1.0e-6)

    # n-independent to within a tiny fraction (not just "bounded").
    spread = (max(abscissas) - min(abscissas)) / abs(target)
    assert spread < 1.0e-6


# ---------------------------------------------------------------------------
# Core acceptance criterion: full SBP-SAT operator's spectral_abscissa is
# bounded/n-independent across the whole default (alpha, N) sweep grid,
# contrasting sharply with the strong-BC baseline's n^1.6-ish growth.
# ---------------------------------------------------------------------------


N_MAX_SWEEP = [8, 16, 32, 64, 128, 192]


def test_full_sbp_sat_abscissa_bounded_in_n_across_default_grid():
    for alpha in DEFAULT_ALPHA_VALUES:
        for N in DEFAULT_N_VALUES:
            abscissas = []
            for n_max in N_MAX_SWEEP:
                matrix, _, _, _ = assemble_spatial_operator_sbp_sat(n_max, alpha, N)
                metrics = spectral_stability_metrics(np.linalg.eigvals(matrix))
                abscissas.append(metrics["spectral_abscissa"])
            a = np.array(abscissas)
            denom = max(abs(a.min()), 1.0e-8)
            rel_spread = (a.max() - a.min()) / denom
            assert rel_spread < 0.05, (
                f"alpha={alpha}, N={N}: abscissa spread {rel_spread:.4f} across "
                f"n_max={N_MAX_SWEEP} -- {a}"
            )


def test_strong_baseline_abscissa_grows_sharply_with_n_by_contrast():
    """Same (alpha, N) point as the SBP-SAT n-independence test above, but
    with the unchanged strong-BC assemble_spatial_operator -- confirms the
    comparison is meaningful (the baseline really does grow at this point,
    it isn't already flat)."""
    alpha, N = 0.1, 0.1
    abscissas = []
    for n_max in N_MAX_SWEEP:
        matrix, _ = assemble_spatial_operator(n_max, alpha, N)
        metrics = spectral_stability_metrics(np.linalg.eigvals(matrix))
        abscissas.append(metrics["spectral_abscissa"])

    assert abscissas == sorted(abscissas)
    assert abscissas[-1] > abscissas[0] * 50.0


def test_gradient_addition_does_not_reintroduce_n_growth():
    """Guard, not a fix (prompt 21): the gradient term is already stable, so
    adding it on top of the SAT-stabilized advection must not undo the
    bound. Compares advection-only vs full (advection+gradient) SBP-SAT
    abscissa across n_max at a representative wide-transition point."""
    alpha, N, epsilon_core = 0.05, 10.0, 0.05

    adv_only = []
    full = []
    for n_max in N_MAX_SWEEP:
        m_adv, _, _, _ = assemble_spatial_operator_sbp_sat(
            n_max, alpha, N, epsilon_core, include_gradient=False,
        )
        m_full, _, _, _ = assemble_spatial_operator_sbp_sat(
            n_max, alpha, N, epsilon_core, include_gradient=True,
        )
        adv_only.append(
            spectral_stability_metrics(np.linalg.eigvals(m_adv))["spectral_abscissa"]
        )
        full.append(
            spectral_stability_metrics(np.linalg.eigvals(m_full))["spectral_abscissa"]
        )

    adv_only = np.array(adv_only)
    full = np.array(full)

    adv_spread = (adv_only.max() - adv_only.min()) / max(abs(adv_only.min()), 1.0e-8)
    full_spread = (full.max() - full.min()) / max(abs(full.min()), 1.0e-8)
    assert adv_spread < 0.05
    assert full_spread < 0.05


# ---------------------------------------------------------------------------
# growth_efold_time is no longer catastrophically small (<< N_total) at
# small Delta_s / production n_max, the concrete quantity the prompt asks
# for (design note Section 5).
# ---------------------------------------------------------------------------


def test_growth_efold_time_no_longer_tiny_at_small_delta_s():
    n_max = 16
    alpha, N = 0.1, 0.1
    N_total_representative = 20.0

    strong_matrix, _ = assemble_spatial_operator(n_max, alpha, N)
    strong_metrics = spectral_stability_metrics(np.linalg.eigvals(strong_matrix))
    assert strong_metrics["growth_efold_time"] < N_total_representative / 100.0

    sbp_sat_matrix, _, _, _ = assemble_spatial_operator_sbp_sat(n_max, alpha, N)
    sbp_sat_metrics = spectral_stability_metrics(np.linalg.eigvals(sbp_sat_matrix))
    assert sbp_sat_metrics["spectral_abscissa"] <= 0.0
    assert sbp_sat_metrics["growth_efold_time"] == float("inf")


# ---------------------------------------------------------------------------
# sweep_eigenvalues(closure="sbp-sat") -- CLI/CSV plumbing consistency.
# ---------------------------------------------------------------------------


def test_sweep_eigenvalues_sbp_sat_closure_matches_direct_assembly():
    from tools.diagnostics.GradientCoupledInstanton.spectrum import CSV_FIELDNAMES

    rows = sweep_eigenvalues([8, 16], [0.1], [0.1, 10.0], closure="sbp-sat")
    assert set(rows[0].keys()) == set(CSV_FIELDNAMES)

    for row in rows:
        matrix, _, _, _ = assemble_spatial_operator_sbp_sat(row["n_max"], row["alpha"], row["N"])
        expected = spectral_stability_metrics(np.linalg.eigvals(matrix))
        assert row["spectral_abscissa"] == pytest.approx(expected["spectral_abscissa"])
        assert row["n_rhp"] == expected["n_rhp"]


def test_sweep_eigenvalues_rejects_unknown_closure():
    with pytest.raises(ValueError):
        sweep_eigenvalues([8], [0.1], [0.1], closure="bogus")


def test_sweep_eigenvalues_default_closure_unchanged():
    """No-regression check: omitting closure entirely still gives the
    'strong' (prompt-17/20) behaviour, byte-for-byte the same as passing it
    explicitly."""
    rows_default = sweep_eigenvalues([8, 16], [0.1], [0.1])
    rows_explicit = sweep_eigenvalues([8, 16], [0.1], [0.1], closure="strong")
    assert rows_default == rows_explicit
