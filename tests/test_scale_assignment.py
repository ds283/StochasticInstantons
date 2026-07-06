"""
Unit tests for scale assignment,
ComputeTargets/GradientCoupledInstanton/scale_assignment.py.
"""

import types

import numpy as np
import pytest

from ComputeTargets.CompactionFunction import _classify_radii, ln_k_phys_Mpc
from ComputeTargets.GradientCoupledInstanton.extraction import extract_zeta_profile
from ComputeTargets.GradientCoupledInstanton.picard import solve_picard
from ComputeTargets.GradientCoupledInstanton.scale_assignment import assign_scales
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import comoving_radius_ratio, delta_s
from Units.Planck_units import Planck_units

# Prompt 06's own reduction-test fixture (potential stub + trajectory stub
# that tracks the noiseless background exactly), reused directly rather than
# re-implemented -- see test_r_phys_matches_independent_core_downflow below.
from test_picard import _StubPotential as _PicardStubPotential
from test_picard import _BackgroundTrackingTrajectory


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


def test_r_phys_ln_k_linearity_self_consistency():
    """
    NOT an independent physics/reduction check -- see
    test_r_phys_matches_independent_core_downflow below for that. This test
    only confirms that assign_scales' ratio construction applies
    ln_k_phys_Mpc's own linear-in-N_before_end structure (lnk = -N_before_end
    + stuff) consistently: since eq:rphys-ratio reuses the *same* ("stuff":
    V, epsilon, V_end_downflow) Leach-Liddle inputs from the single
    outer-edge anchor for every node (by design, no per-shell re-solve -- see
    eq:rphys-ratio's own "single global ratio" argument in
    onion_model_planning.md), expanding r_phys[-1] = exp(-delta_s_N_final) *
    r_phys_out algebraically through ln_k_phys_Mpc's own formula shows this
    is *identically* what ln_k_phys_Mpc would give if called directly with
    N_before_end reduced by exactly delta_s_N_final and the *same* outer-edge
    "stuff". This equality holds by construction of ln_k_phys_Mpc's own
    shape, regardless of whether assign_scales' underlying physics is
    correct -- it cannot catch a wrong node index, a sign error in
    comoving_radius_ratio, or r_phys_out being anchored to the wrong state,
    because the reference value here is algebraically derived from the same
    computation it's checking, just with re-arranged arguments.
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


# ---------------------------------------------------------------------------
# Genuine independent reduction check -- core's own downflow vs the pipeline
# ---------------------------------------------------------------------------


def _r_phys_pipeline_and_independent_core_reference(
    alpha: float, N_init: float, N_final: float, delta_Nstar: float,
    phi_init: float, pi_init: float, atol: float, rtol: float,
):
    """
    Shared body for test_r_phys_matches_independent_core_downflow: runs
    solve_picard (disable_spatial_coupling=True, prompt 06's own mechanism)
    to convergence, feeds the converged grid through the real
    extract_zeta_profile + assign_scales pipeline, and separately computes
    the core node's r_phys by downflowing *its own* converged state directly
    -- without going through assign_scales' ratio arithmetic at all. Returns
    (r_phys_pipeline, r_phys_core_independent).
    """
    potential = _PicardStubPotential()
    diffusion_model = MasslessDecoupledDiffusion()
    units = Planck_units()
    cosmo = _make_cosmo()

    N_total = (N_init - N_final) + delta_Nstar
    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_total, atol, rtol, N_end=N_init,
    )
    phi_end = trajectory.phi_at(N_total)

    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    grid = LGLCollocationGrid(5)

    result = solve_picard(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
        trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )
    assert result["failure"] is False, result["diagnostics"]
    assert result["diagnostics"]["converged"] is True

    phi_grid = np.array(result["phi_grid"])
    pi_grid = np.array(result["pi_grid"])
    phi_final = phi_grid[-1, :]
    pi_final = pi_grid[-1, :]

    # ── Run the actual pipeline on the full converged grid ────────────────
    N_offset = trajectory.N_end - N_init
    extraction = extract_zeta_profile(
        phi_final, pi_final, N_offset=N_offset, N_total=N_total,
        trajectory=trajectory, potential=potential, atol=atol, rtol=rtol,
        units=units,
    )
    H_sq_core_final = potential.H_sq(phi_final[-1], pi_final[-1])
    delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_final, H_sq_nl_init, alpha)

    # zeta is irrelevant to r_phys (only feeds C/r_max/r_peak); zeroed here
    # exactly as the self-consistency test above does, so that a density-
    # match edge case in extract_zeta_profile's own Step 4 (unrelated to
    # r_phys) can't crash _classify_radii.
    scale_result = assign_scales(
        phi_final, pi_final, np.zeros(grid.n_collocation_points),
        extraction["N_end_downflow"], extraction["phi_end_downflow"],
        delta_s_N_final, grid, potential, units, cosmo,
    )
    r_phys_pipeline = scale_result["r_phys"][-1]

    # ── Independent reference: downflow the core's *own* converged state ──
    # directly, without touching assign_scales or the outer edge at all.
    phi_core = float(phi_final[-1])
    pi_core = float(pi_final[-1])
    sol_down, _, attempts = integrate_noiseless_trajectory(
        phi_core, pi_core, potential, atol, rtol,
    )
    assert sol_down is not None, f"core downflow failed: {attempts}"
    N_end_downflow_core = float(sol_down.t_events[0][0])
    phi_end_downflow_core = float(sol_down.y_events[0][0][0])

    lnk_core = ln_k_phys_Mpc(
        N_end_downflow_core,
        potential.V(phi_core),
        potential.epsilon(phi_core, pi_core),
        potential.V(phi_end_downflow_core),
        units, cosmo,
    )
    r_phys_core_independent = 2.0 * np.pi / np.exp(lnk_core)

    return r_phys_pipeline, r_phys_core_independent


def test_r_phys_matches_independent_core_downflow():
    """
    Genuine independent reduction check, unlike
    test_r_phys_ln_k_linearity_self_consistency above: the reference value
    here comes from downflowing the *core's own* converged state
    (integrate_noiseless_trajectory, called directly, the same way
    extraction.py's own Step 1 does) -- not from re-deriving assign_scales'
    outer-edge ratio arithmetic with shifted arguments. Reuses prompt 06's
    own reduction-test fixture classes (_StubPotential,
    _BackgroundTrackingTrajectory, imported directly from test_picard.py)
    and its disable_spatial_coupling=True mechanism, run to convergence via
    the real solve_picard -> extract_zeta_profile -> assign_scales pipeline,
    exactly as a real solve would.

    Choice of N_total -- an empirical finding, not a free parameter picked
    for convenience. Numerically probing this (see the prompt-10 session
    that added this test) shows delta_s_N_final = ln(1+alpha) + N_total +
    0.5*ln(H^2_ratio): with disable_spatial_coupling=True and phi_end tuned
    to the trivial background match, every grid node -- including the core
    -- collapses to the *same* shared trajectory (an exact consequence of
    ODE uniqueness: uniform initial data + a per-node RHS with no residual
    y-dependence once gradient/advection are both zeroed). In that
    degenerate limit the core's own downflow is numerically identical to the
    outer edge's, so the *only* difference between r_phys_pipeline and
    r_phys_core_independent is the geometric ratio factor exp(-delta_s_N_final)
    itself. Using prompt 06's own N_total (~4) makes that factor
    exp(-4) =~ 0.02 regardless of alpha -- confirmed by direct computation,
    at alpha spanning 0.05 down to 1e-9 the ratio is pinned at ~0.0197,
    *not* approaching 1 -- because delta_s_N_final is then dominated by
    N_total, not by alpha, and the O(alpha) equivalence claimed in
    onion_model.tex's "Equivalence check" section is therefore not the
    effect being measured at all. Choosing N_total itself far smaller than
    the alpha values under test (N_total ~ 1.5e-3, alpha >= 5e-3) makes
    ln(1+alpha) the dominant term in delta_s_N_final instead, so this
    *does* isolate and exercise the intended O(alpha) correction. This is a
    deliberate departure from prompt 06's own N_init/N_final/delta_Nstar
    values (which are otherwise reused unchanged, along with the potential,
    trajectory stub, and disable_spatial_coupling mechanism): reusing them
    verbatim would make this test assert a floor set by N_total instead of
    the O(alpha) property it is meant to check.

    Tolerance -- not floating-point equality. r_phys_pipeline is expected to
    agree with r_phys_core_independent only up to O(alpha) corrections (per
    onion_model.tex's own "Equivalence check against the discrete (peeling)
    scheme" section: exact as alpha->0, with O(alpha) corrections at finite
    alpha) -- mirroring how the core zeta check (prompt 08) documented its
    own approximate tolerance. Direct computation at alpha=0.05 gives a
    relative discrepancy of ~4.9% and at alpha=0.005 gives ~0.65%, i.e.
    tracking alpha itself to within a factor of a few (not more, and not
    less) -- so rel=0.1 and rel=0.02 below are deliberately generous (2x
    the observed discrepancy) rather than tight enough to make a future
    editor's re-tightening attempt look reasonable; don't tighten these
    without re-deriving the expected discrepancy from delta_s_N_final's own
    formula first.
    """
    N_init = 5.0
    N_final = 4.999
    delta_Nstar = 0.0005
    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-9
    rtol = 1.0e-9

    r_phys_pipeline_1, r_phys_core_ref_1 = _r_phys_pipeline_and_independent_core_reference(
        0.05, N_init, N_final, delta_Nstar, phi_init, pi_init, atol, rtol,
    )
    assert r_phys_pipeline_1 == pytest.approx(r_phys_core_ref_1, rel=0.1)

    # Bonus: at a smaller alpha, the discrepancy should shrink (not just be
    # "small enough" once) -- a stronger, more diagnostic check of the actual
    # O(alpha) claim than a single fixed tolerance.
    r_phys_pipeline_2, r_phys_core_ref_2 = _r_phys_pipeline_and_independent_core_reference(
        0.005, N_init, N_final, delta_Nstar, phi_init, pi_init, atol, rtol,
    )
    assert r_phys_pipeline_2 == pytest.approx(r_phys_core_ref_2, rel=0.02)

    discrepancy_1 = abs(r_phys_pipeline_1 / r_phys_core_ref_1 - 1.0)
    discrepancy_2 = abs(r_phys_pipeline_2 / r_phys_core_ref_2 - 1.0)
    assert discrepancy_2 < discrepancy_1
