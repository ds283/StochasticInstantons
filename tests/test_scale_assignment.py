"""
Unit tests for scale assignment,
ComputeTargets/GradientCoupledInstanton/scale_assignment.py.
"""

import types

import numpy as np
import pytest

from ComputeTargets.CompactionFunction import _classify_radii, ln_k_phys_Mpc
from ComputeTargets.GradientCoupledInstanton.extraction import extract_zeta_profile
from ComputeTargets.GradientCoupledInstanton.scale_assignment import assign_scales
from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import comoving_radius_ratio
from Units.Planck_units import Planck_units


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubPotential:
    """
    Standalone duck-typed canonical-inflation potential (Mp = 1), matching
    AbstractPotential's own H_sq/epsilon formulas -- the same stub used
    throughout this prompt sequence (test_picard.py, test_extraction.py, etc).
    """

    def __init__(self, m_sq: float = 1.3):
        self._m_sq = m_sq

    def V(self, phi):
        phi = np.asarray(phi)
        return 0.5 * self._m_sq * phi ** 2

    def dV_dphi(self, phi):
        return self._m_sq * np.asarray(phi)

    def H_sq(self, phi, pi):
        phi = np.asarray(phi)
        pi = np.asarray(pi)
        return self.V(phi) / (3.0 - 0.5 * pi ** 2)

    def epsilon(self, phi, pi):
        pi = np.asarray(pi)
        return 0.5 * pi ** 2


def _make_cosmo():
    """Minimal duck-typed cosmology stand-in -- only T_CMB_Kelvin is read by
    ln_k_phys_Mpc."""
    return types.SimpleNamespace(T_CMB_Kelvin=2.725)


# ---------------------------------------------------------------------------
# comoving_radius_ratio reuse sanity check
# ---------------------------------------------------------------------------


def test_r_ratio_reuses_comoving_radius_ratio():
    """
    r_ratio[0] (outer edge, y=-1) must be exactly 1.0 and r_ratio[-1] (core,
    y=+1) must be exactly exp(-delta_s_N_final) -- both already established
    as exact structural properties of comoving_radius_ratio() itself
    (tests/test_onion_coordinate.py). This test only confirms
    assign_scales() is actually calling that function correctly, not
    re-deriving the property.
    """
    grid = LGLCollocationGrid(7)
    potential = _StubPotential()
    units = Planck_units()
    cosmo = _make_cosmo()

    n_nodes = grid.n_collocation_points
    phi_final = np.full(n_nodes, 10.0)
    pi_final = np.full(n_nodes, -0.01)
    zeta = np.zeros(n_nodes)
    N_end_downflow = np.full(n_nodes, 55.0)
    phi_end_downflow = np.full(n_nodes, 1.0e-2)

    delta_s_N_final = 3.7

    result = assign_scales(
        phi_final, pi_final, zeta, N_end_downflow, phi_end_downflow,
        delta_s_N_final, grid, potential, units, cosmo,
    )

    assert result["r_ratio"][0] == pytest.approx(1.0, abs=1.0e-14)
    assert result["r_ratio"][-1] == pytest.approx(
        np.exp(-delta_s_N_final), rel=1.0e-14
    )
    np.testing.assert_allclose(
        result["r_ratio"], comoving_radius_ratio(grid.nodes, delta_s_N_final)
    )


# ---------------------------------------------------------------------------
# Compaction function chain rule
# ---------------------------------------------------------------------------


def test_compaction_function_matches_analytic_chain_rule():
    """
    Construct a synthetic zeta(y) as a low-degree polynomial in y (degree 2,
    well within the exact-differentiation range of an n_max=6 LGL
    differentiation matrix -- prompt 01's own exactness guarantee), and
    confirm C(y_j) matches the hand-computed closed form using the *exact*
    analytic zeta'(y) and the analytic d(rho)/dy -- not just "looks
    reasonable."
    """
    grid = LGLCollocationGrid(7)  # n_max=6
    potential = _StubPotential()
    units = Planck_units()
    cosmo = _make_cosmo()

    y = grid.nodes
    a, b, c = 0.3, -0.7, 0.2
    zeta = a + b * y + c * y ** 2
    zeta_prime_analytic = b + 2.0 * c * y  # d(zeta)/dy, exact

    delta_s_N_final = 2.5
    r_ratio_analytic = comoving_radius_ratio(y, delta_s_N_final)
    drho_dy_analytic = -0.5 * delta_s_N_final * r_ratio_analytic
    expected_rho_zeta_prime = r_ratio_analytic * zeta_prime_analytic / drho_dy_analytic
    expected_C = (2.0 / 3.0) * (1.0 - (1.0 + expected_rho_zeta_prime) ** 2)

    n_nodes = grid.n_collocation_points
    phi_final = np.full(n_nodes, 10.0)
    pi_final = np.full(n_nodes, -0.01)
    N_end_downflow = np.full(n_nodes, 55.0)
    phi_end_downflow = np.full(n_nodes, 1.0e-2)

    result = assign_scales(
        phi_final, pi_final, zeta, N_end_downflow, phi_end_downflow,
        delta_s_N_final, grid, potential, units, cosmo,
    )

    np.testing.assert_allclose(result["C"], expected_C, rtol=1.0e-10, atol=1.0e-12)


# ---------------------------------------------------------------------------
# r_max / r_peak reuse
# ---------------------------------------------------------------------------


def test_r_max_r_peak_reuse_classify_radii_directly():
    """
    Confirm r_max/r_peak are genuinely produced by CompactionFunction's own
    _classify_radii helper (not reimplemented): feed the *same* r_phys/C
    arrays assign_scales() itself computed into a direct call to
    _classify_radii and confirm identical output.
    """
    grid = LGLCollocationGrid(9)  # n_max=8, gives more structure in C(y)
    potential = _StubPotential()
    units = Planck_units()
    cosmo = _make_cosmo()

    y = grid.nodes
    # A profile with some curvature, so C(y) is non-trivial (not flat).
    zeta = 0.05 * (1.0 - y ** 2) + 0.01 * y

    n_nodes = grid.n_collocation_points
    phi_final = np.full(n_nodes, 10.0)
    pi_final = np.full(n_nodes, -0.01)
    N_end_downflow = np.full(n_nodes, 55.0)
    phi_end_downflow = np.full(n_nodes, 1.0e-2)
    delta_s_N_final = 4.2
    C_threshold = 0.4

    result = assign_scales(
        phi_final, pi_final, zeta, N_end_downflow, phi_end_downflow,
        delta_s_N_final, grid, potential, units, cosmo, C_threshold=C_threshold,
    )

    sort_idx = np.argsort(result["r_phys"])
    expected = _classify_radii(
        result["r_phys"][sort_idx], result["C"][sort_idx], C_threshold
    )

    assert result["r_max"] == expected[0]
    assert result["r_peak"] == expected[1]
    assert result["diagnostics"]["r_max_at_grid_edge"] == expected[2]
    assert result["diagnostics"]["r_peak_at_grid_edge"] == expected[3]


# ---------------------------------------------------------------------------
# Physical scale reduction check -- exact, not approximate
# ---------------------------------------------------------------------------


def test_r_phys_core_reduction_matches_compaction_function_step_c():
    """
    Reduction-limit check for r_phys, in the same spirit as picard.py's own
    reduction-limit test (test_solve_picard_reduction_limit_matches_full_
    instanton): built from a genuine noiseless background trajectory (not
    arbitrary numbers), using a non-trivial (non-zero) delta_s_N_final --
    unlike zeta (prompt 08), r_phys involves no downflow-before-matching
    refinement, so its reduction to CompactionFunction's own Step C formula
    (ln_k_phys_Mpc, reused directly rather than re-derived) is exact, not
    approximate.

    eq:rphys-ratio reuses the *same* ("stuff": V, epsilon, V_end_downflow)
    Leach-Liddle inputs from the single outer-edge anchor for every node --
    by design, no per-shell re-solve (see eq:rphys-ratio's own "single
    global ratio" argument in onion_model_planning.md). Expanding
    r_phys[-1] = exp(-delta_s_N_final) * r_phys_out algebraically through
    ln_k_phys_Mpc's own formula (lnk = -N_before_end + stuff) shows this is
    *identically* what ln_k_phys_Mpc would give if called directly with
    N_before_end reduced by exactly delta_s_N_final and the *same* outer-edge
    "stuff" -- i.e. CompactionFunction's own Step C formula, evaluated at the
    core's own (geometrically shifted) reference point. This is checked here
    by direct, independent re-evaluation of ln_k_phys_Mpc with that shifted
    N_before_end, not by re-deriving assign_scales' own ratio arithmetic.
    """
    potential = _StubPotential()
    units = Planck_units()
    cosmo = _make_cosmo()
    atol = 1.0e-11
    rtol = 1.0e-11

    # A genuine noiseless background trajectory, reused (via downflow) for
    # the outer-edge node -- the actual physics is exercised, not arbitrary
    # numbers.
    phi0, pi0 = 10.0, -0.01
    sol, _, attempts = integrate_noiseless_trajectory(phi0, pi0, potential, atol, rtol)
    assert sol is not None, f"background integration failed: {attempts}"

    # Pick a point partway along the trajectory as the outer edge's state.
    N_mid = 0.5 * float(sol.t_events[0][0])
    phi_outer = float(sol.sol(N_mid)[0])
    pi_outer = float(sol.sol(N_mid)[1])

    grid = LGLCollocationGrid(6)
    n_nodes = grid.n_collocation_points
    # Only node 0 (outer edge) is read by assign_scales' Leach-Liddle
    # anchor -- the other nodes are irrelevant to this check, so they are
    # filled with the same state for simplicity (no failure_mask surprises
    # from extract_zeta_profile).
    phi_final = np.full(n_nodes, phi_outer)
    pi_final = np.full(n_nodes, pi_outer)
    zeta = np.zeros(n_nodes)

    # Downflow the outer edge's state via extract_zeta_profile's own
    # machinery (reused, not reimplemented) to get N_end_downflow/
    # phi_end_downflow.
    class _DenseTrajectory:
        @property
        def N_end(self):
            return float(sol.t_events[0][0])

        def phi_at(self, N):
            return float(sol.sol(N)[0])

        def pi_at(self, N):
            return float(sol.sol(N)[1])

    trajectory = _DenseTrajectory()
    extraction = extract_zeta_profile(
        phi_final, pi_final, N_offset=0.0, N_total=N_mid,
        trajectory=trajectory, potential=potential, atol=atol, rtol=rtol,
        units=units,
    )
    assert not np.any(extraction["failure_mask"])

    delta_s_N_final = 2.3  # genuinely non-zero -- exercises the general case
    result = assign_scales(
        phi_final, pi_final, zeta,
        extraction["N_end_downflow"], extraction["phi_end_downflow"],
        delta_s_N_final, grid, potential, units, cosmo,
    )

    # Reference: CompactionFunction's own Step C formula (ln_k_phys_Mpc),
    # called independently with N_before_end shifted by delta_s_N_final and
    # the same outer-edge "stuff" -- not through assign_scales' own ratio
    # arithmetic.
    N_before_end_core = float(extraction["N_end_downflow"][0]) - delta_s_N_final
    lnk_core_ref = ln_k_phys_Mpc(
        N_before_end_core,
        potential.V(phi_outer),
        potential.epsilon(phi_outer, pi_outer),
        potential.V(float(extraction["phi_end_downflow"][0])),
        units, cosmo,
    )
    r_phys_core_ref = 2.0 * np.pi / np.exp(lnk_core_ref)

    assert result["r_phys"][-1] == pytest.approx(r_phys_core_ref, rel=1.0e-12)
