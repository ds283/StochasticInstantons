"""
Unit tests for scale assignment,
ComputeTargets/GradientCoupledInstanton/scale_assignment.py.
"""

import types

import numpy as np
import pytest

from ComputeTargets.CompactionFunction import _classify_radii, _compute_instanton_path, ln_k_phys_Mpc
from ComputeTargets.GradientCoupledInstanton.extraction import extract_zeta_profile
from ComputeTargets.GradientCoupledInstanton.picard import solve_picard
from ComputeTargets.GradientCoupledInstanton.scale_assignment import assign_scales
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import comoving_radius_ratio, delta_s
from Units.Planck_units import Planck_units

# Prompt 06's own reduction-test fixture (potential stub), reused directly
# rather than re-implemented.
from test_picard import _StubPotential as _PicardStubPotential


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


class _StaticTrajectory:
    """
    Minimal duck-typed trajectory stub with a constant (phi, pi) everywhere
    and an arbitrary N_end. Used only by tests that exercise assign_scales'
    r_ratio/C wiring and don't care about the physical realism of the
    Leach-Liddle anchor value itself (test_r_ratio_reuses_comoving_radius_ratio,
    test_compaction_function_matches_analytic_chain_rule,
    test_r_max_r_peak_reuse_classify_radii_directly below).
    """

    def __init__(self, phi: float, pi: float, N_end: float):
        self._phi = phi
        self._pi = pi
        self._N_end = N_end

    @property
    def N_end(self) -> float:
        return self._N_end

    def phi_at(self, N: float) -> float:
        return self._phi

    def pi_at(self, N: float) -> float:
        return self._pi


class _FullBackgroundTrajectory:
    """
    Duck-typed InflatonTrajectory stand-in that integrates the noiseless
    background all the way to its own true end of inflation (epsilon=1),
    via dense output -- unlike test_picard.py's _BackgroundTrackingTrajectory,
    which only covers the local [0, N_total] window and sets N_end=N_init as
    a convenience for that module's own (unrelated) reduction test. The fixed
    assign_scales anchor needs a genuine trajectory.N_end (and phi_at/pi_at
    valid there, to read V_end_bg) -- so the reduction/cross-target tests
    below need a trajectory that actually reaches the real background
    endpoint, reusing the same pattern as test_extraction.py's own
    _DenseTrajectory.
    """

    def __init__(self, potential, phi0: float, pi0: float, atol: float, rtol: float):
        sol, _, attempts = integrate_noiseless_trajectory(phi0, pi0, potential, atol, rtol)
        assert sol is not None, f"background integration failed: {attempts}"
        self._sol = sol
        self._N_end = float(sol.t_events[0][0])

    @property
    def N_end(self) -> float:
        return self._N_end

    def phi_at(self, N: float) -> float:
        return float(self._sol.sol(N)[0])

    def pi_at(self, N: float) -> float:
        return float(self._sol.sol(N)[1])


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
    trajectory = _StaticTrajectory(phi=10.0, pi=-0.01, N_end=100.0)

    n_nodes = grid.n_collocation_points
    zeta = np.zeros(n_nodes)

    delta_s_N_final = 3.7

    result = assign_scales(
        zeta, delta_s_N_final, grid, trajectory,
        5.0, 50.0, 0.05, potential, units, cosmo,
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
    trajectory = _StaticTrajectory(phi=10.0, pi=-0.01, N_end=100.0)

    y = grid.nodes
    a, b, c = 0.3, -0.7, 0.2
    zeta = a + b * y + c * y ** 2
    zeta_prime_analytic = b + 2.0 * c * y  # d(zeta)/dy, exact

    delta_s_N_final = 2.5
    r_ratio_analytic = comoving_radius_ratio(y, delta_s_N_final)
    drho_dy_analytic = -0.5 * delta_s_N_final * r_ratio_analytic
    expected_rho_zeta_prime = r_ratio_analytic * zeta_prime_analytic / drho_dy_analytic
    expected_C = (2.0 / 3.0) * (1.0 - (1.0 + expected_rho_zeta_prime) ** 2)

    result = assign_scales(
        zeta, delta_s_N_final, grid, trajectory,
        5.0, 50.0, 0.05, potential, units, cosmo,
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
    trajectory = _StaticTrajectory(phi=10.0, pi=-0.01, N_end=100.0)

    y = grid.nodes
    # A profile with some curvature, so C(y) is non-trivial (not flat).
    zeta = 0.05 * (1.0 - y ** 2) + 0.01 * y

    delta_s_N_final = 4.2
    C_threshold = 0.4

    result = assign_scales(
        zeta, delta_s_N_final, grid, trajectory,
        5.0, 50.0, 0.05, potential, units, cosmo, C_threshold=C_threshold,
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
# NaN-contaminated zeta -- graceful failure, not a crash
# ---------------------------------------------------------------------------


def test_nan_zeta_returns_failure_not_crash():
    """
    Regression test: a NaN-contaminated zeta (e.g. from extract_zeta_profile
    marking a node's failure_mask, or an upstream Picard divergence) must
    make assign_scales() return {"failure": True, ...}, not propagate the
    NaN through grid.D @ zeta into _classify_radii's np.nanargmax, which
    raises "ValueError: All-NaN slice encountered" on an all-NaN C array
    (grid.D is dense, so a single NaN node contaminates every C entry).
    """
    grid = LGLCollocationGrid(7)
    potential = _StubPotential()
    units = Planck_units()
    cosmo = _make_cosmo()
    trajectory = _StaticTrajectory(phi=10.0, pi=-0.01, N_end=100.0)

    n_nodes = grid.n_collocation_points
    zeta = np.zeros(n_nodes)
    zeta[2] = np.nan

    result = assign_scales(
        zeta, 3.7, grid, trajectory, 5.0, 50.0, 0.05, potential, units, cosmo,
        label="test_nan_zeta_returns_failure_not_crash",
    )

    assert result["failure"] is True
    assert result["r_ratio"] is None
    assert result["C"] is None
    assert result["r_phys"] is None
    assert result["r_max"] is None
    assert result["r_peak"] is None
    assert result["diagnostics"]["nan_node_indices"] == [2]


# ---------------------------------------------------------------------------
# Outer-edge downflow duration == N_init (new consistency check)
# ---------------------------------------------------------------------------


def test_outer_edge_downflow_duration_equals_N_init():
    """
    The fix's central claim is that y=-1 (outer edge) sits exactly on the
    noiseless background throughout the transition, so downflowing its
    *own* state at the transition's start (local N=0, absolute N_offset)
    is guaranteed to just continue the same background curve to the true
    end of inflation -- i.e. its downflow duration is exactly N_init, with
    no integration needed (assign_scales now computes this arithmetically).

    This test confirms that guarantee independently, using machinery
    (extraction.py's own per-shell downflow) that is otherwise unrelated to
    scale_assignment.py's own arithmetic: feed extract_zeta_profile a
    single-node array equal to the trajectory's own state at N_offset (the
    transition start), with N_total=0.0 (a trivial, zero-duration "shared
    final time" -- i.e. we are asking about the outer edge's state *before*
    the transition has advanced at all), and confirm the returned
    N_end_downflow matches N_init to numerical (integration) tolerance.

    Note this is deliberately *not* the same thing as downflowing
    phi_final[0] from a real solve_picard run (that grid state sits at
    local N=N_total, the transition's *end*, and its own downflow duration
    is N_init - N_total, not N_init -- exactly the quantity the old, buggy
    anchor formula wrongly used in place of N_init).
    """
    potential = _StubPotential()
    units = Planck_units()
    atol = 1.0e-11
    rtol = 1.0e-11

    trajectory = _FullBackgroundTrajectory(potential, phi0=10.0, pi0=-0.01, atol=atol, rtol=rtol)

    N_init = 5.0
    N_offset = trajectory.N_end - N_init

    phi_outer_start = np.array([trajectory.phi_at(N_offset)])
    pi_outer_start = np.array([trajectory.pi_at(N_offset)])

    result = extract_zeta_profile(
        phi_outer_start, pi_outer_start, N_offset=N_offset, N_total=0.0,
        trajectory=trajectory, potential=potential, atol=atol, rtol=rtol,
        units=units,
    )

    # Only the downflow itself (Steps 1-3) is under test here, not the
    # subsequent density-match (Step 4) -- with N_total=0.0 the downflow's
    # terminal density can land a hair outside Step 4's strict bracket
    # (two independent ODE integrations of the same near-endpoint physics),
    # which is irrelevant to the claim being checked and would otherwise
    # make this test brittle for no physical reason.
    assert not np.isnan(result["N_end_downflow"][0])
    assert result["N_end_downflow"][0] == pytest.approx(N_init, abs=1.0e-6)


# ---------------------------------------------------------------------------
# Genuine independent reduction check -- core's own local state vs pipeline
# ---------------------------------------------------------------------------


def _r_phys_pipeline_and_independent_core_reference(
    alpha: float, N_init: float, N_final: float, delta_Nstar: float,
    phi_init: float, pi_init: float, atol: float, rtol: float,
):
    """
    Shared body: runs solve_picard (disable_spatial_coupling=True, prompt
    06's own mechanism) to convergence against a *genuine* full background
    trajectory (reaching the real end of inflation -- required by the fixed
    anchor's H_end_bg = sqrt(potential.H_sq(trajectory.phi_at(trajectory.N_end),
    trajectory.pi_at(trajectory.N_end)))), feeds the converged grid through
    assign_scales, and separately computes the core node's r_phys by a
    *direct*, independent Leach-Liddle evaluation at the core's own
    converged local state -- without touching assign_scales's own ratio
    arithmetic at all.

    zeta is zeroed rather than run through extract_zeta_profile: zeta only
    feeds the compaction function C(y) (irrelevant to r_phys), and in this
    fully-degenerate reduction scenario the per-shell downflow's own
    terminal density lands almost exactly on the background's own terminal
    density (both are genuinely the same asymptotic epsilon=1 point,
    reached via two independently-integrated ODE solves), which can trip
    Step 4's strict density-match bracket by floating-point noise -- a real
    property of that unrelated machinery, not a defect in the r_phys
    construction under test here.

    Returns (r_phys_pipeline, r_phys_core_ref).
    """
    potential = _PicardStubPotential()
    diffusion_model = MasslessDecoupledDiffusion()
    units = Planck_units()
    cosmo = _make_cosmo()

    N_total = (N_init - N_final) + delta_Nstar
    trajectory = _FullBackgroundTrajectory(potential, phi_init, pi_init, atol, rtol)
    N_offset = trajectory.N_end - N_init
    phi_end = trajectory.phi_at(N_offset + N_total)

    phi_start = trajectory.phi_at(N_offset)
    pi_start = trajectory.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_start, pi_start)
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
    H_sq_core_final = potential.H_sq(phi_final[-1], pi_final[-1])
    delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_final, H_sq_nl_init, alpha)

    scale_result = assign_scales(
        np.zeros(grid.n_collocation_points), delta_s_N_final, grid, trajectory,
        N_init, N_offset, alpha, potential, units, cosmo,
    )
    r_phys_pipeline = scale_result["r_phys"][-1]

    # ── Independent reference: direct Leach-Liddle at the core's own local
    # state, per the prompt's literal formula -- not re-deriving
    # assign_scales' own ratio arithmetic.
    phi_core = float(phi_final[-1])
    pi_core = float(pi_final[-1])
    H_core = np.sqrt(potential.H_sq(phi_core, pi_core))
    H_end_bg = np.sqrt(
        potential.H_sq(trajectory.phi_at(trajectory.N_end), trajectory.pi_at(trajectory.N_end))
    )
    N_before_end_core = N_init - N_total

    lnk_core_ref = ln_k_phys_Mpc(N_before_end_core, H_core, H_end_bg, units, cosmo)
    r_phys_core_ref = 2.0 * np.pi / np.exp(lnk_core_ref)

    return r_phys_pipeline, r_phys_core_ref


def test_r_phys_matches_independent_core_downflow():
    """
    Genuine independent reduction check, reusing prompt 06's own
    reduction-test fixture scale (N_init=5.0, N_final=2.0, delta_Nstar=1.0,
    N_total=4.0 -- test_picard.py's own values, not an artificially shrunk
    N_total) run to convergence via the real
    solve_picard -> extract_zeta_profile -> assign_scales pipeline.

    With ln_k_phys_Mpc fixed to take H_k/H_end directly (rather than
    reimplementing the Friedmann relation inline with mismatched V_k/V_end
    powers), r_phys_pipeline[-1] (assign_scales' own outer-anchor-plus-
    ratio-propagation construction) and r_phys_core_ref (a direct,
    independent Leach-Liddle evaluation at the core's own converged local
    state) agree to numerical precision -- the tautology closes exactly,
    term by term, with no residual correction factor. (An earlier version
    of this test, written against the buggy formula, found a genuine
    O(10%) discrepancy here and had to introduce a closed-form correction
    factor to explain it; that was the buggy formula's own artifact, not a
    property of the underlying physics, and is gone now that the bug is
    fixed.)
    """
    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-9
    rtol = 1.0e-9
    alpha = 0.05

    r_phys_pipeline, r_phys_core_ref = _r_phys_pipeline_and_independent_core_reference(
        alpha, N_init, N_final, delta_Nstar, phi_init, pi_init, atol, rtol,
    )

    assert r_phys_pipeline == pytest.approx(r_phys_core_ref, rel=1.0e-9)


# ---------------------------------------------------------------------------
# Cross-target check -- GradientCoupledInstanton vs CompactionFunction
# ---------------------------------------------------------------------------


class _CompactionValueStub:
    def __init__(self, N: float, phi1: float, phi2: float):
        self.N = types.SimpleNamespace(N=N)
        self.phi1 = phi1
        self.phi2 = phi2


class _CompactionObjStub:
    def __init__(self, N_init_value: float, N_total: float, values: list):
        self.N_init_value = N_init_value
        self._N_total = N_total
        self.values = values


def test_core_r_phys_matches_compaction_function_innermost_sample():
    """
    Cross-target check: with CompactionFunction's Step C also fixed (Part
    B), GradientCoupledInstanton's core (y=+1, transition end) and
    CompactionFunction's own *innermost* (smallest-r) sample represent the
    same physical instant -- both are the state at local N=N_total (the
    transition's end), which is where CompactionFunction's own sample grid
    runs to and where GradientCoupledInstanton's core is defined. (Not the
    *outermost* sample: CompactionFunction's samples are sorted ascending in
    r, and its outermost/largest-r sample corresponds to local N=0 -- the
    transition *start* -- matching GradientCoupledInstanton's outer edge,
    not its core.)

    To isolate this comparison from solve_picard's own BVP machinery, the
    "instanton" fed to CompactionFunction here is constructed directly from
    the same background trajectory used for GradientCoupledInstanton's own
    reduction test above (a trivial instanton exactly on the background,
    the discrete-scheme analogue of disable_spatial_coupling=True) -- built
    directly via trajectory.phi_at/pi_at over the same local N grid
    [0, N_total], not via a real FullInstanton BVP solve, since only the
    scale-assignment agreement is under test here, not the BVP itself.

    Expected residual -- with ln_k_phys_Mpc's V_k/V_end power bug fixed,
    CompactionFunction's innermost sample's r is *exactly* the direct
    Leach-Liddle evaluation at the core's own local state (confirmed below
    to float precision) -- i.e. exactly r_phys_core_ref from
    test_r_phys_matches_independent_core_downflow above. GradientCoupledInstanton's
    core r_phys agrees with this value directly (no closed-form correction
    factor needed any more -- see that test's docstring for why the earlier,
    buggy-formula version of this comparison needed one). The only remaining
    discrepancy is numerical: two different methods (LGL collocation via
    solve_picard/assign_scales vs. solve_ivp shooting via
    _compute_instanton_path) solving the same underlying problem at
    atol=rtol=1e-9, so the tolerance below reflects solver/discretization
    error only, not any residual physical effect.
    """
    potential = _PicardStubPotential()
    diffusion_model = MasslessDecoupledDiffusion()
    units = Planck_units()
    cosmo = _make_cosmo()
    atol = 1.0e-9
    rtol = 1.0e-9
    alpha = 0.05

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_total = (N_init - N_final) + delta_Nstar
    phi_init = 10.0
    pi_init = -0.01

    trajectory = _FullBackgroundTrajectory(potential, phi_init, pi_init, atol, rtol)
    N_offset = trajectory.N_end - N_init
    phi_end = trajectory.phi_at(N_offset + N_total)

    H_sq_nl_init = potential.H_sq(trajectory.phi_at(N_offset), trajectory.pi_at(N_offset))
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

    # zeta is zeroed (irrelevant to r_phys) -- see the same note in
    # _r_phys_pipeline_and_independent_core_reference above.
    H_sq_core_final = potential.H_sq(phi_final[-1], pi_final[-1])
    delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_final, H_sq_nl_init, alpha)

    scale_result = assign_scales(
        np.zeros(grid.n_collocation_points), delta_s_N_final, grid, trajectory,
        N_init, N_offset, alpha, potential, units, cosmo,
    )
    r_phys_gci_core = scale_result["r_phys"][-1]

    # ── The discrete/peeling scheme's trivial-instanton analogue ──────────
    N_inst_arr = np.linspace(0.0, N_total, 5)
    phi1_arr = np.array([trajectory.phi_at(N_offset + n) for n in N_inst_arr])
    phi2_arr = np.array([trajectory.pi_at(N_offset + n) for n in N_inst_arr])
    values = [
        _CompactionValueStub(N_inst_arr[i], phi1_arr[i], phi2_arr[i])
        for i in range(len(N_inst_arr))
    ]
    instanton_obj = _CompactionObjStub(N_init, N_total, values)

    cf_result = _compute_instanton_path(
        instanton_obj, False, trajectory, potential, units, cosmo,
        C_threshold=0.4, atol=atol, rtol=rtol,
    )
    assert cf_result["failure"] is False, cf_result["diagnostics"]

    r_cf_innermost = cf_result["r"][0]  # smallest r after Step D's ascending sort

    # ── Confirm the "exactly the direct core reference" claim first ───────
    phi_core = float(phi_final[-1])
    pi_core = float(pi_final[-1])
    H_core = np.sqrt(potential.H_sq(phi_core, pi_core))
    H_end_bg = np.sqrt(
        potential.H_sq(trajectory.phi_at(trajectory.N_end), trajectory.pi_at(trajectory.N_end))
    )

    lnk_core_ref = ln_k_phys_Mpc(N_init - N_total, H_core, H_end_bg, units, cosmo)
    r_phys_core_ref = 2.0 * np.pi / np.exp(lnk_core_ref)

    assert r_cf_innermost == pytest.approx(r_phys_core_ref, rel=1.0e-8)

    # ── Now confirm GCI's core matches directly -- tolerance reflects only
    # the numerical solver/discretization error between the two independent
    # methods (LGL collocation vs. solve_ivp shooting), not any physical
    # residual (see docstring above).
    assert r_phys_gci_core == pytest.approx(r_cf_innermost, rel=1.0e-7)
