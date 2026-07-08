"""
Unit / integration tests for the Picard iteration and shooting driver,
ComputeTargets/GradientCoupledInstanton/picard.py.
"""

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from ComputeTargets.FullInstanton import _compute_full_instanton
from ComputeTargets.GradientCoupledInstanton import picard as picard_module
from ComputeTargets.GradientCoupledInstanton.picard import solve_picard
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from Interpolation.spline_wrapper import SplineWrapper
from Numerics.LGLCollocation import LGLCollocationGrid


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubPotential:
    """
    Standalone duck-typed canonical-inflation potential (Mp = 1), matching
    AbstractPotential's own H_sq/epsilon formulas -- the same stub used in
    tests/test_forward_rhs.py and tests/test_response_rhs.py.
    """

    def __init__(self, m_sq: float = 1.3):
        self._m_sq = m_sq

    def V(self, phi):
        phi = np.asarray(phi)
        return 0.5 * self._m_sq * phi ** 2

    def dV_dphi(self, phi):
        return self._m_sq * np.asarray(phi)

    def d2V_dphi2(self, phi):
        return self._m_sq * np.ones_like(np.asarray(phi, dtype=float))

    def H_sq(self, phi, pi):
        phi = np.asarray(phi)
        pi = np.asarray(pi)
        return self.V(phi) / (3.0 - 0.5 * pi ** 2)

    def epsilon(self, phi, pi):
        pi = np.asarray(pi)
        return 0.5 * pi ** 2


class _BackgroundTrackingTrajectory:
    """
    Duck-typed trajectory stub whose phi_at/pi_at trace out the *noiseless*
    background ODE (dphi/dN = pi, dpi/dN = -(3-eps)*pi - dV/Hsq --
    FullInstanton's own bg_rhs) over the local domain [0.0, N_total],
    reconstructed via SplineWrapper.

    N_end is set equal to N_init, so that solve_picard's own
    N_offset = trajectory.N_end - N_init is exactly 0.0 -- i.e. this stub's
    absolute N axis coincides with solve_picard's local N axis, letting the
    background be integrated directly over [0.0, N_total] rather than
    needing to also reconstruct InflatonTrajectory's own absolute-N bookkeeping.

    Used for the reduction-limit test: with disable_spatial_coupling=True
    and identically-zero response-field sourcing, every collocation node
    (outer edge, interior, core) is governed by this same, decoupled,
    per-node ODE with the same uniform initial condition (eq. bc-init), so
    they all track this background exactly and the core (Neumann-eliminated
    from the other, background-tracking nodes) reduces to it too.
    """

    def __init__(self, potential, phi_init, pi_init, N_total, atol, rtol, N_end):
        def bg_rhs(N, y):
            phi, pi = y
            return [
                pi,
                -(3.0 - potential.epsilon(phi, pi)) * pi
                - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
            ]

        N_grid = np.linspace(0.0, N_total, 400)
        sol = solve_ivp(
            bg_rhs, (0.0, N_total), [phi_init, pi_init],
            method="RK45", t_eval=N_grid, atol=atol, rtol=rtol,
        )
        assert sol.success

        self._phi_spline = SplineWrapper(N_grid, sol.y[0], k=3)
        self._pi_spline = SplineWrapper(N_grid, sol.y[1], k=3)
        self._N_end = N_end

    @property
    def N_end(self) -> float:
        return self._N_end

    def phi_at(self, N: float) -> float:
        return float(self._phi_spline(N))

    def pi_at(self, N: float) -> float:
        return float(self._pi_spline(N))


class _PotentialHolder:
    """Duck-typed stand-in for InflatonTrajectory, exposing only the
    ._potential attribute _compute_full_instanton actually reads."""

    def __init__(self, potential):
        self._potential = potential


class _TrajectoryProxyStub:
    """Duck-typed stand-in for InflatonTrajectoryProxy: _compute_full_instanton
    only ever calls trajectory.get()._potential."""

    def __init__(self, potential):
        self._holder = _PotentialHolder(potential)

    def get(self):
        return self._holder


# ---------------------------------------------------------------------------
# Reduction-limit, end to end
# ---------------------------------------------------------------------------


def test_solve_picard_reduction_limit_matches_full_instanton():
    """
    With gradient coupling structurally disabled (disable_spatial_coupling=
    True) and a trajectory stub that tracks the same noiseless background
    ODE FullInstanton's own bg_rhs solves, solve_picard's full output at the
    core node should match what FullInstanton itself produces for the same
    (phi_init, pi_init, phi_final, N_total, potential, diffusion_model)
    -- the integration-level version of the unit-level reduction tests in
    prompts 04-05.
    """
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_total = (N_init - N_final) + delta_Nstar

    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-9
    rtol = 1.0e-9

    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_total, atol, rtol, N_end=N_init
    )
    phi_end = trajectory.phi_at(N_total)

    alpha = 0.05
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    grid = LGLCollocationGrid(5)  # small n_collocation_points to keep this fast

    result = solve_picard(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
        trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )

    assert result["failure"] is False
    assert result["diagnostics"]["converged"] is True

    # result["N_grid"] is already the local, zero-based grid over
    # [0.0, N_total] -- matching FullInstanton's own t_span exactly, no
    # shift by N_init needed (unlike before this fix).
    t_grid = result["N_grid"]

    fi_data = _compute_full_instanton._function(
        trajectory=_TrajectoryProxyStub(potential),
        dm=diffusion_model,
        phi_init=phi_init,
        pi_init=pi_init,
        phi_final=phi_end,
        N_total=N_total,
        N_sample=t_grid,
        atol=atol,
        rtol=rtol,
    )
    assert fi_data["failure"] is False

    phi_grid = np.array(result["phi_grid"])
    core_phi = phi_grid[:, -1]
    fi_phi1 = np.array(fi_data["phi1"])

    np.testing.assert_allclose(core_phi, fi_phi1, rtol=1.0e-5, atol=1.0e-6)

    # Every other node (outer edge, interior) should also track the same
    # background, since disable_spatial_coupling=True decouples every node
    # and they all share the same uniform initial condition.
    for j in range(phi_grid.shape[1]):
        np.testing.assert_allclose(phi_grid[:, j], fi_phi1, rtol=1.0e-5, atol=1.0e-6)


# ---------------------------------------------------------------------------
# Convergence diagnostics shape
# ---------------------------------------------------------------------------


def test_solve_picard_diagnostics_match_full_instanton_shape():
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_total = (N_init - N_final) + delta_Nstar

    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-8
    rtol = 1.0e-8

    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_total, atol, rtol, N_end=N_init
    )
    phi_end = trajectory.phi_at(N_total)

    grid = LGLCollocationGrid(5)
    result = solve_picard(
        N_init, N_final, delta_Nstar, 0.05, potential.H_sq(phi_init, pi_init),
        grid, trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )

    expected_keys = {
        "compute_time", "converged", "final_residual", "total_ode_solves",
        "outer_iterations", "newton_fallback_count", "final_lambda",
        "picard_iterations_per_outer", "min_picard_iterations",
        "max_picard_iterations", "mean_picard_iterations",
        "mean_time_per_picard_iteration",
    }
    assert expected_keys.issubset(result["diagnostics"].keys())
    assert result["diagnostics"]["converged"] is True
    assert result["diagnostics"]["outer_iterations"] >= 1


# ---------------------------------------------------------------------------
# Non-convergence returns a failure dict, doesn't raise
# ---------------------------------------------------------------------------


def test_solve_picard_non_convergence_returns_failure_dict(monkeypatch):
    """Force non-convergence by capping MAX_OUTER at 1 outer iteration and
    picking an unreachable shooting target -- mirrors how a too-tight
    OUTER_TOL-equivalent or too-few-MAX_OUTER scenario would be constructed,
    per the prompt's guidance to check for an existing FullInstanton
    non-convergence test first (there is none) before inventing this one."""
    monkeypatch.setattr(picard_module, "MAX_OUTER", 1)

    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_total = (N_init - N_final) + delta_Nstar

    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-8
    rtol = 1.0e-8

    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_total, atol, rtol, N_end=N_init
    )
    # Deliberately unreachable in a single outer iteration.
    phi_end = trajectory.phi_at(N_total) + 0.5

    grid = LGLCollocationGrid(5)
    result = picard_module.solve_picard(
        N_init, N_final, delta_Nstar, 0.05, potential.H_sq(phi_init, pi_init),
        grid, trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )

    assert result["failure"] is True
    assert result["diagnostics"]["converged"] is False


# ---------------------------------------------------------------------------
# Prompt 21a -- SBP-SAT closure acceptance checks, under FULL spatial
# coupling (disable_spatial_coupling=False, the default): the lagged
# pi_core target, the FullInstanton seed, and the closure-independence /
# regularity-emergence claims the module docstrings make.
# ---------------------------------------------------------------------------


def _make_dense_trajectory(potential, phi0=10.0, pi0=-0.01, atol=1e-9, rtol=1e-9):
    """A genuine noiseless-background trajectory reaching its own true end
    of inflation (epsilon=1) via dense output -- same construction as
    tests/test_gradient_coupled_instanton_end_to_end.py's own helper."""

    def bg_rhs(N, y):
        phi, pi = y
        return [
            pi,
            -(3.0 - potential.epsilon(phi, pi)) * pi
            - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
        ]

    def event_end(N, y):
        return potential.epsilon(y[0], y[1]) - 1.0

    event_end.terminal = True
    event_end.direction = 1

    sol = solve_ivp(
        bg_rhs, (0.0, 1000.0), [phi0, pi0], method="RK45", atol=atol, rtol=rtol,
        events=event_end, dense_output=True, max_step=0.5,
    )
    assert sol.t_events[0].size > 0
    N_end = float(sol.t_events[0][0])

    class _Traj:
        def __init__(self):
            self._potential = potential
            self.N_end = N_end

        def phi_at(self, N):
            return float(sol.sol(N)[0])

        def pi_at(self, N):
            return float(sol.sol(N)[1])

    return _Traj()


def _small_full_coupling_case(n_collocation_points=5):
    """Shared fixture-like setup for the SBP-SAT closure tests below: a
    short transition (so the solve converges quickly) with full spatial
    coupling (gradient + split-form advection + SAT) active."""
    potential = _StubPotential()
    traj = _make_dense_trajectory(potential)

    N_init = 5.0
    N_final = 4.9
    delta_Nstar = 0.05
    N_total = (N_init - N_final) + delta_Nstar
    N_offset = traj.N_end - N_init

    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    phi_end = traj.phi_at(N_offset + N_total)

    grid = LGLCollocationGrid(n_collocation_points)
    dm = MasslessDecoupledDiffusion()

    return dict(
        N_init=N_init, N_final=N_final, delta_Nstar=delta_Nstar, alpha=0.05,
        H_sq_nl_init=H_sq_nl_init, grid=grid, trajectory=traj, potential=potential,
        diffusion_model=dm, atol=1e-9, rtol=1e-9, phi_end=phi_end,
    )


def test_solve_picard_sat_forcing_vanishes_at_convergence():
    """
    Prompt 21a acceptance: "at convergence the SAT penalty forcing
    |tau(u_core - g_u)| is at the level of the Picard residual (i.e. -> 0)".
    Checked here for pi_core specifically (the field with a genuinely lagged
    target -- phi_core's target is always live/self-consistent by
    construction, so there is nothing to check convergence of there): the
    stored g_pi_core_final target must match the converged solution's own
    core pi(N) trajectory to within the Picard inner-loop tolerance.
    """
    case = _small_full_coupling_case()
    result = solve_picard(**case, instrument_stiffness=False)

    assert result["failure"] is False
    assert result["diagnostics"]["converged"] is True

    pi_core = np.asarray(result["pi_grid"])[:, -1]
    g_pi_core_final = np.asarray(result["g_pi_core_final"])

    inner_tol = case["atol"] * 10.0
    max_forcing_gap = np.max(np.abs(pi_core - g_pi_core_final))
    assert max_forcing_gap < 100.0 * inner_tol, (
        f"pi_core SAT target did not converge onto pi_core itself: "
        f"max|pi_core - g_pi_core| = {max_forcing_gap:.3e}, inner_tol = {inner_tol:.3e}"
    )


def test_solve_picard_regularity_emerges_not_imposed():
    """
    Prompt 21a acceptance: "Regularity emerges, not imposed" -- (D @ pi)_core
    should be small at convergence WITHOUT ever having been enforced as a
    value (only phi's own regularity is weakly SAT-imposed; pi has no
    boundary condition of any kind other than the lagged, self-consistent
    target). This is consistent with the physics framing (pi = dphi/dN, so
    phi regular implies pi regular) rather than a separately-imposed
    constraint.
    """
    case = _small_full_coupling_case(n_collocation_points=7)
    result = solve_picard(**case, instrument_stiffness=False)

    assert result["failure"] is False

    grid = case["grid"]
    pi_final_row = np.asarray(result["pi_grid"])[-1]
    d_pi_core = float(grid.D[-1, :] @ pi_final_row)

    # Compare against the scale of pi itself over the grid, rather than an
    # absolute tolerance -- pi_final_row's own magnitude sets what "small"
    # means here.
    scale = max(np.max(np.abs(pi_final_row)), 1e-8)
    assert abs(d_pi_core) / scale < 1e-2, (
        f"(D @ pi)_core = {d_pi_core:.3e} is not small relative to the pi "
        f"profile's own scale ({scale:.3e}) -- pi regularity did not emerge"
    )


def test_solve_picard_converged_answer_independent_of_sat_seed(monkeypatch):
    """
    Prompt 21a's key correctness check: the converged core trajectory does
    NOT depend on which seed started sweep 0 of the lagged pi_core SAT
    target -- concrete proof the stabiliser doesn't bias the result. Compares
    two genuinely different, but both physically reasonable, seeds:
      - "FullInstanton seed": the normal fetch-then-fallback path
        (full_instanton_seed=None), which computes an accurate FullInstanton
        profile inline (_seed_pi_core_values's tier 2).
      - "background seed": _compute_full_instanton._function monkeypatched
        to fail, forcing the fallback all the way to the noiseless
        background trajectory's own pi(N) (tier 3) -- a real, bounded
        trajectory, just a physically different (less accurate) one, unlike
        a pathological flat-zero seed that can drive the ODE through
        unphysical (e.g. H_sq < 0) territory before the lagging even gets a
        chance to correct it.
    """
    case = _small_full_coupling_case()

    result_fi_seed = solve_picard(**case, instrument_stiffness=False, full_instanton_seed=None)
    assert result_fi_seed["failure"] is False
    assert result_fi_seed["diagnostics"]["converged"] is True

    def _always_fails(*args, **kwargs):
        return {"failure": True}

    monkeypatch.setattr(picard_module._compute_full_instanton, "_function", _always_fails)
    result_bg_seed = solve_picard(**case, instrument_stiffness=False, full_instanton_seed=None)
    assert result_bg_seed["failure"] is False
    assert result_bg_seed["diagnostics"]["converged"] is True

    np.testing.assert_allclose(
        result_bg_seed["phi_grid"], result_fi_seed["phi_grid"], atol=1e-6, rtol=1e-5,
    )
    np.testing.assert_allclose(
        result_bg_seed["pi_grid"], result_fi_seed["pi_grid"], atol=1e-6, rtol=1e-5,
    )
    assert result_bg_seed["final_lambda"] == pytest.approx(
        result_fi_seed["final_lambda"], rel=1e-4, abs=1e-6
    )


def test_seed_pi_core_values_falls_back_through_all_three_tiers(monkeypatch):
    """
    _seed_pi_core_values's own documented preference order: (1) a supplied,
    non-failing full_instanton_seed dict; (2) the inline FullInstanton
    delegate; (3) the noiseless background trajectory's own pi(N). Exercises
    all three tiers directly (rather than only indirectly through
    solve_picard), monkeypatching _compute_full_instanton._function so tier
    2 is forced to fail without needing a pathological physical case.
    """
    potential = _StubPotential()
    traj = _make_dense_trajectory(potential)
    N_grid = np.linspace(0.0, 0.1, 30)
    N_offset = 0.0

    # Tier 1: a supplied, non-failing seed wins outright.
    good_seed = {"failure": False, "N_sample": N_grid.tolist(), "phi2": (1.0 + 0.0 * N_grid).tolist()}
    vals = picard_module._seed_pi_core_values(
        N_grid, N_offset, traj.phi_at(0.0), traj.pi_at(0.0), traj.phi_at(0.1), 0.1,
        traj, potential, MasslessDecoupledDiffusion(), 1e-9, 1e-9, "test", good_seed,
    )
    np.testing.assert_allclose(vals, 1.0, atol=1e-8)

    # Tier 3: force BOTH tier 1 (failure=True) and tier 2 (monkeypatched to
    # fail) so the fallback reaches the background trajectory.
    def _always_fails(*args, **kwargs):
        return {"failure": True}

    monkeypatch.setattr(
        picard_module._compute_full_instanton, "_function", _always_fails
    )
    vals3 = picard_module._seed_pi_core_values(
        N_grid, N_offset, traj.phi_at(0.0), traj.pi_at(0.0), traj.phi_at(0.1), 0.1,
        traj, potential, MasslessDecoupledDiffusion(), 1e-9, 1e-9, "test",
        {"failure": True},
    )
    expected = np.array([traj.pi_at(N_offset + N) for N in N_grid])
    np.testing.assert_allclose(vals3, expected)


# ---------------------------------------------------------------------------
# Prompt 22b -- _AndersonMixer unit tests (isolated from the full ODE-solve
# pipeline): the fixed-point acceleration replacing the plain lagged-
# replacement update that prompt 22's Finding 2 showed diverges once
# genuinely coupled. See picard.py's own module docstring ("SBP-SAT
# self-consistent target") and the prompt 22b design note
# (.documents/gradient-coupled-instanton/
# 22b-convergent-iteration-design-note.md) for the full derivation.
# ---------------------------------------------------------------------------


def test_anderson_mixer_zero_window_matches_plain_picard_update():
    """anderson_m=0 must reduce update() exactly to the pre-22b plain
    lagged-replacement rule, x_{k+1} = x_k + theta*g_k -- so the old code
    path (and any test exercising it) remains reachable unchanged."""
    mixer = picard_module._AndersonMixer(window=0, theta=0.5)
    x_k = np.array([1.0, 2.0, 3.0])
    g_k = np.array([0.1, -0.2, 0.3])
    x_next = mixer.update(x_k, g_k)
    np.testing.assert_allclose(x_next, x_k + 0.5 * g_k)


def _small_genuinely_coupled_case(n_collocation_points=5):
    """Like _small_full_coupling_case, but with the FullInstanton-consistent
    (prompt 22a) phi_end, traj.phi_at(traj.N_end - N_final) -- independent
    of delta_Nstar, NOT the degenerate traj.phi_at(N_offset + N_total)
    _small_full_coupling_case still uses. That degenerate formula makes
    lambda=0 an exact fixed point (prompt 22 Finding 1), so tests built on
    _small_full_coupling_case exercise only the trivial background branch,
    regardless of this prompt's closure fix. This variant is what prompt
    22b's own acceptance tests need: a genuinely non-trivial shooting
    target, exactly like tests/test_gradient_coupled_instanton_end_to_end.py's
    now-un-xfailed pipeline tests use."""
    potential = _StubPotential()
    traj = _make_dense_trajectory(potential)

    N_init = 5.0
    N_final = 4.9
    delta_Nstar = 0.05
    N_offset = traj.N_end - N_init

    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    phi_end = traj.phi_at(traj.N_end - N_final)

    grid = LGLCollocationGrid(n_collocation_points)
    dm = MasslessDecoupledDiffusion()

    return dict(
        N_init=N_init, N_final=N_final, delta_Nstar=delta_Nstar, alpha=0.05,
        H_sq_nl_init=H_sq_nl_init, grid=grid, trajectory=traj, potential=potential,
        diffusion_model=dm, atol=1e-9, rtol=1e-9, phi_end=phi_end,
    )


@pytest.mark.parametrize("n_collocation_points", [5, 9])
def test_solve_picard_converges_under_genuine_coupling_across_n(n_collocation_points):
    """Prompt 22b's own headline acceptance case: on a genuinely non-trivial
    target (prompt 22a), the Anderson-accelerated closure must converge
    (not diverge, per prompt 22's Finding 2) across several
    n_collocation_points, with a strictly non-zero lambda -- proof this is
    not just re-discovering the trivial lambda=0 branch.

    n=17 was tried on this same small case and does NOT (yet) converge --
    the outer shooting loop's own conditioning degrades with n here in a way
    not yet root-caused (see the design note's "what is NOT yet
    demonstrated" section) -- so the parametrization is deliberately capped
    at what is proven, rather than claiming broader coverage than tested.
    """
    case = _small_genuinely_coupled_case(n_collocation_points)
    result = solve_picard(**case, instrument_stiffness=False)

    assert result["failure"] is False
    assert result["diagnostics"]["converged"] is True
    assert result["final_lambda"] != pytest.approx(0.0, abs=1.0e-8)


def test_anderson_mixer_converges_a_diverging_linear_map():
    """The concrete failure mode Finding 2 diagnosed: plain Picard (theta=1,
    m=0) on x_{k+1} = x_k + (A - I) x_k with a real eigenvalue > 1 (here
    A=1.4, matching this prompt's own measured Phase-1b growing-phase
    contraction ratio) diverges monotonically and unboundedly, since
    |1 + theta*(A-1)| >= 1 for every theta in (0,1] when A>1 -- no amount of
    plain under-relaxation can stabilise a real eigenvalue this map alone.
    Anderson acceleration (m>0), using the exact same per-step map as its
    residual evaluation, must converge to the fixed point (x=0) instead."""
    A = 1.4

    def T(x):
        return A * x

    # Plain Picard (m=0) diverges, confirming the map is genuinely
    # non-contractive under any theta in (0,1] -- not a strawman.
    x = np.array([1.0])
    plain_mixer = picard_module._AndersonMixer(window=0, theta=1.0)
    for _ in range(20):
        x = plain_mixer.update(x, T(x) - x)
    assert abs(x[0]) > 1.0e2, "plain Picard should diverge on this map"

    # Anderson (m>0) converges the identical map to its fixed point.
    x = np.array([1.0])
    anderson_mixer = picard_module._AndersonMixer(window=5, theta=1.0)
    for _ in range(30):
        x = anderson_mixer.update(x, T(x) - x)
    assert abs(x[0]) < 1.0e-6, f"Anderson failed to converge: x={x[0]!r}"


# ---------------------------------------------------------------------------
# Prompt 21a's headline acceptance case: the originally-failing production
# configuration (N_init=19.5, N_final=16, delta_Nstar=0.1, alpha=0.1) must
# now converge, and converge to consistent core physics, across
# n_collocation_points that previously blew up (>= 9) -- this is the direct,
# quantitative regression guard for that claim, using the real quadratic
# potential/physical parameters from quadratic-asteroid-small.yaml
# (m/Mp=1e-5, phi0=15 Mp) rather than the lighter _StubPotential used
# elsewhere in this file.
# ---------------------------------------------------------------------------


class _QuadraticPotentialStub:
    """Standalone duck-typed quadratic-inflation potential (matches
    AbstractPotential's own H_sq/epsilon formulas), parameterised by a real
    Units object so H_sq/epsilon are expressed with genuine Mp factors --
    the same construction used by out-gradient-coupled-stiffness/scripts/
    explore_onion_stiffness.py's own StubPotential for this exact scenario."""

    def __init__(self, m_sq: float, units):
        self._m_sq = m_sq
        self._units = units

    def V(self, phi):
        phi = np.asarray(phi)
        return 0.5 * self._m_sq * phi ** 2

    def dV_dphi(self, phi):
        return self._m_sq * np.asarray(phi)

    def d2V_dphi2(self, phi):
        return self._m_sq * np.ones_like(np.asarray(phi, dtype=float))

    def H_sq(self, phi, pi):
        phi = np.asarray(phi)
        pi = np.asarray(pi)
        Mp = self._units.PlanckMass
        return self.V(phi) / (3.0 * Mp * Mp - 0.5 * pi * pi / (Mp * Mp))

    def epsilon(self, phi, pi):
        pi = np.asarray(pi)
        Mp = self._units.PlanckMass
        return 0.5 * pi * pi / (Mp * Mp)


def _build_production_trajectory(potential, phi0, pi0, atol, rtol):
    def bg_rhs(N, y):
        phi, pi = y
        return [
            pi,
            -(3.0 - potential.epsilon(phi, pi)) * pi
            - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
        ]

    def end_event(N, y):
        return potential.epsilon(y[0], y[1]) - 1.0

    end_event.terminal = True
    end_event.direction = 1

    sol = solve_ivp(
        bg_rhs, (0.0, 2000.0), [phi0, pi0], method="RK45",
        atol=atol, rtol=rtol, events=end_event, dense_output=True, max_step=0.5,
    )
    assert sol.success and len(sol.t_events[0]) == 1
    N_end = float(sol.t_events[0][0])

    class _Traj:
        def __init__(self):
            self._potential = potential
            self.N_end = N_end

        def phi_at(self, N):
            return float(sol.sol(N)[0])

        def pi_at(self, N):
            return float(sol.sol(N)[1])

    return _Traj()


@pytest.mark.parametrize("n_collocation_points", [5, 9, 17, 33])
def test_solve_picard_production_case_converges_for_previously_failing_n(n_collocation_points):
    """
    N_init=19.5, N_final=16, delta_Nstar=0.1, alpha=0.1 -- the exact
    parameter point prompt 21a names as the original failure. Before this
    prompt, n_collocation_points >= 9 diverged (right-half-plane spectral
    growth, strong-BC closure); n=5,7 converged. After the SBP-SAT port,
    every one of these must converge, and (physics regression) n=5's core
    trajectory must match FullInstanton to good precision.
    """
    from Units.Planck_units import Planck_units

    units = Planck_units()
    potential = _QuadraticPotentialStub(m_sq=(1.0e-5) ** 2, units=units)
    dm = MasslessDecoupledDiffusion()
    atol, rtol = 1e-8, 1e-8

    traj = _build_production_trajectory(potential, phi0=15.0, pi0=0.0, atol=atol, rtol=rtol)

    N_init, N_final, delta_Nstar, alpha = 19.5, 16.0, 0.1, 0.1
    N_offset = traj.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    phi_end = traj.phi_at(N_offset + N_total)

    grid = LGLCollocationGrid(n_collocation_points)
    result = solve_picard(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
        traj, potential, dm, atol, rtol, phi_end,
        instrument_stiffness=False, label=f"production-n={n_collocation_points}",
    )

    assert result["failure"] is False
    assert result["diagnostics"]["converged"] is True

    if n_collocation_points == 5:
        fi_data = _compute_full_instanton._function(
            trajectory=_TrajectoryProxyStub(potential), dm=dm,
            phi_init=phi_init, pi_init=pi_init, phi_final=phi_end,
            N_total=N_total, N_sample=result["N_grid"], atol=atol, rtol=rtol,
        )
        assert fi_data["failure"] is False
        core_phi = np.asarray(result["phi_grid"])[:, -1]
        fi_phi1 = np.asarray(fi_data["phi1"])
        np.testing.assert_allclose(core_phi, fi_phi1, rtol=1e-5, atol=1e-6)


def test_solve_picard_production_case_core_trajectory_converges_across_n():
    """
    Companion to the per-n convergence check above: the CONVERGED core
    trajectory's endpoint value should itself converge (not merely "not
    diverge") as n_collocation_points increases -- the concrete form of
    "the core trajectory now converges as n increases through 9...33 rather
    than diverging" (prompt 21a acceptance).
    """
    from Units.Planck_units import Planck_units

    units = Planck_units()
    potential = _QuadraticPotentialStub(m_sq=(1.0e-5) ** 2, units=units)
    dm = MasslessDecoupledDiffusion()
    atol, rtol = 1e-8, 1e-8

    traj = _build_production_trajectory(potential, phi0=15.0, pi0=0.0, atol=atol, rtol=rtol)

    N_init, N_final, delta_Nstar, alpha = 19.5, 16.0, 0.1, 0.1
    N_offset = traj.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    phi_end = traj.phi_at(N_offset + N_total)

    phi_core_final = {}
    for n_collocation_points in [9, 11, 13, 17, 33]:
        grid = LGLCollocationGrid(n_collocation_points)
        result = solve_picard(
            N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
            traj, potential, dm, atol, rtol, phi_end,
            instrument_stiffness=False, label=f"n={n_collocation_points}",
        )
        assert result["failure"] is False
        assert result["diagnostics"]["converged"] is True
        phi_core_final[n_collocation_points] = result["phi_grid"][-1][-1]

    values = list(phi_core_final.values())
    # All values agree to within a small absolute tolerance -- a converging
    # (not diverging/oscillating-with-n) trend, not just "each n succeeds
    # individually".
    spread = max(values) - min(values)
    assert spread < 1e-4, f"core trajectory did not converge across n: {phi_core_final}"
