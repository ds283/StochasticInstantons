"""
Unit tests for per-shell zeta-profile extraction,
ComputeTargets/GradientCoupledInstanton/extraction.py.
"""

import numpy as np
import pytest
from scipy.optimize import brentq

from ComputeTargets.FullInstanton import _compute_full_instanton
from ComputeTargets.GradientCoupledInstanton import extraction as extraction_module
from ComputeTargets.GradientCoupledInstanton.extraction import extract_zeta_profile
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory
from Units.Planck_units import Planck_units


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubPotential:
    """
    Standalone duck-typed canonical-inflation potential (Mp = 1), matching
    AbstractPotential's own H_sq/epsilon formulas -- the same stub used in
    tests/test_picard.py, tests/test_forward_rhs.py, tests/test_response_rhs.py.
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


class _DenseTrajectory:
    """
    Duck-typed InflatonTrajectory stand-in whose phi_at/pi_at reproduce the
    *exact* noiseless background ODE (the same equations
    integrate_noiseless_trajectory itself solves) via the dense output of a
    single integration from (phi0, pi0) at absolute N=0 to end of inflation
    (epsilon=1) at absolute N=N_end -- deliberately reusing the dense
    solution object directly rather than building a second, independent
    spline representation that could introduce its own interpolation error
    on top of the one under test.
    """

    def __init__(self, potential, phi0, pi0, atol, rtol):
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
# Direct unit test of the N-offset arithmetic
# ---------------------------------------------------------------------------


def test_N_end_abs_offset_formula():
    """
    Direct, isolated unit test of the N-offset arithmetic (prompt item 3):
    N_offset converts the local, zero-based N used throughout
    GradientCoupledInstanton to InflatonTrajectory's own absolute N axis
    (see picard.py's module docstring), and N_end_downflow is itself
    relative to the downflow's own fresh N=0 (integrate_noiseless_trajectory's
    own docstring). Checked completely isolated from any ODE integration --
    hand-chosen values, exact formula, no solver noise -- so a future
    refactor touching this one line of arithmetic is caught immediately.
    """
    N_offset = 4.25
    N_total = 11.0
    N_end_downflow = 0.375

    assert extraction_module._N_end_abs(N_offset, N_total, N_end_downflow) == (
        N_offset + N_total + N_end_downflow
    )


# ---------------------------------------------------------------------------
# Outer-edge (y=-1) sanity check: zeta should be ~exactly zero
# ---------------------------------------------------------------------------


def test_extract_zeta_profile_outer_edge_is_zero():
    """
    The y=-1 node is Dirichlet-pinned to the noiseless background throughout
    the transition, so its state at local N_total is *exactly* a point on
    the background trajectory. Downflowing that point noiselessly forward
    just continues the same background curve (same equations, same
    physics) to its own end of inflation, and density-matching against that
    same background necessarily recovers the same e-fold -- so zeta(-1)
    should come out at (or extremely close to, within downflow integration
    tolerance) exactly zero. This is a strong, physically meaningful check,
    not a numerical coincidence.
    """
    potential = _StubPotential()
    units = Planck_units()
    atol = 1.0e-11
    rtol = 1.0e-11

    trajectory = _DenseTrajectory(potential, phi0=10.0, pi0=-0.01, atol=atol, rtol=rtol)

    N_offset = 0.0
    # Leave a substantial remaining downflow distance to end of inflation,
    # so the test genuinely exercises Steps 1-4, not a trivial no-op.
    N_total = 0.5 * trajectory.N_end

    phi_final = np.array([trajectory.phi_at(N_offset + N_total)])
    pi_final = np.array([trajectory.pi_at(N_offset + N_total)])

    result = extract_zeta_profile(
        phi_final, pi_final, N_offset, N_total, trajectory, potential,
        atol, rtol, units,
    )

    assert not result["failure_mask"][0]
    assert result["zeta"][0] == pytest.approx(0.0, abs=1.0e-6)


# ---------------------------------------------------------------------------
# Core reduction check -- approximate, not exact (see docstring below)
# ---------------------------------------------------------------------------


def test_extract_zeta_profile_approximately_matches_no_downflow_reference():
    """
    Unlike every previous reduction test in this sequence (prompts 04-06,
    all exact to floating-point precision), this one is only expected to be
    *approximately* consistent with the reference "no downflow" construction
    CompactionFunction's own Step B uses (see the doc comment added next to
    that step in ComputeTargets/CompactionFunction.py). extract_zeta_profile
    downflows each shell to epsilon=1 before density matching
    (eq:zeta-extraction); Step B matches rho directly at the instanton's
    own sample point. These differ by a small amount whenever the sample
    point is a genuinely different phase-space point from the background
    (not merely a later point on the *same* curve) -- exactly the
    small, single-field-negligible isocurvature-type correction discussed
    when this design was settled. The tolerance below is deliberately loose
    ("small correction", not "should be identical") -- do not tighten it
    into a spurious failure.

    The reference value is computed inline by replicating CompactionFunction
    Step B's formula for the single endpoint sample of interest, rather than
    driving the full _compute_instanton_path pipeline (which also needs
    cosmology/scale-assignment scaffolding irrelevant to this one number).
    """
    potential = _StubPotential()
    units = Planck_units()
    atol = 1.0e-10
    rtol = 1.0e-10

    trajectory = _DenseTrajectory(potential, phi0=10.0, pi0=-0.01, atol=atol, rtol=rtol)

    N_init = 3.0
    N_final = 1.0
    delta_Nstar = 0.5
    N_total = (N_init - N_final) + delta_Nstar
    N_offset = trajectory.N_end - N_init

    phi_init_local = trajectory.phi_at(N_offset + 0.0)
    pi_init_local = trajectory.pi_at(N_offset + 0.0)

    # Displace the endpoint boundary condition slightly off the background
    # trajectory -- a genuine (small) instanton, not the trivial
    # "instanton == background" case, so the two extraction routes actually
    # compare different phase-space points rather than the same curve.
    phi_final_target = trajectory.phi_at(N_offset + N_total) + 0.05

    N_sample_grid = np.linspace(0.0, N_total, 60)

    fi_data = _compute_full_instanton._function(
        trajectory=_TrajectoryProxyStub(potential),
        dm=MasslessDecoupledDiffusion(),
        phi_init=phi_init_local,
        pi_init=pi_init_local,
        phi_final=phi_final_target,
        N_total=N_total,
        N_sample=N_sample_grid.tolist(),
        atol=atol,
        rtol=rtol,
    )
    assert fi_data["failure"] is False

    phi1_arr = np.array(fi_data["phi1"])
    phi2_arr = np.array(fi_data["phi2"])

    # extract_zeta_profile's own route: downflow + match, for the single
    # core/endpoint node.
    result = extract_zeta_profile(
        phi1_arr[-1:], phi2_arr[-1:], N_offset, N_total, trajectory, potential,
        atol, rtol, units,
    )
    assert not result["failure_mask"][0]
    zeta_downflow = result["zeta"][0]

    # Reference: CompactionFunction's own Step B formula -- direct density
    # match at the instanton's own sample point, no downflow.
    Mp = units.PlanckMass
    rho_core = 3.0 * Mp ** 2 * potential.H_sq(float(phi1_arr[-1]), float(phi2_arr[-1]))
    N_bg = brentq(
        lambda N: (
            3.0 * Mp ** 2 * potential.H_sq(trajectory.phi_at(N), trajectory.pi_at(N)) - rho_core
        ),
        0.0, trajectory.N_end, xtol=atol, rtol=rtol,
    )
    N_background = N_bg - (trajectory.N_end - N_init)
    zeta_no_downflow = N_total - N_background

    assert zeta_downflow == pytest.approx(zeta_no_downflow, abs=0.01)


# ---------------------------------------------------------------------------
# Failure handling: one bad node doesn't corrupt the others
# ---------------------------------------------------------------------------


def test_extract_zeta_profile_failure_handling_does_not_corrupt_other_nodes(monkeypatch):
    """
    Inject a downflow failure (integrate_noiseless_trajectory returning no
    solution) for one specific node's state, alongside a normal, healthy
    node -- confirm the unhealthy node's zeta comes back nan with
    failure_mask set, without raising, and without perturbing the healthy
    node's result at all.
    """
    potential = _StubPotential()
    units = Planck_units()
    atol = 1.0e-9
    rtol = 1.0e-9

    trajectory = _DenseTrajectory(potential, phi0=10.0, pi0=-0.01, atol=atol, rtol=rtol)
    N_offset = 0.0
    N_total = 0.5 * trajectory.N_end

    good_phi = trajectory.phi_at(N_offset + N_total)
    good_pi = trajectory.pi_at(N_offset + N_total)
    bad_phi = 123.456
    bad_pi = 0.0

    real_integrate = extraction_module.integrate_noiseless_trajectory

    def _flaky_integrate(phi0, pi0, potential_arg, atol_arg, rtol_arg, **kwargs):
        if phi0 == bad_phi and pi0 == bad_pi:
            return None, None, [
                {"solver": "forced-failure", "status": -1, "message": "injected test failure"}
            ]
        return real_integrate(phi0, pi0, potential_arg, atol_arg, rtol_arg, **kwargs)

    monkeypatch.setattr(extraction_module, "integrate_noiseless_trajectory", _flaky_integrate)

    phi_final = np.array([good_phi, bad_phi])
    pi_final = np.array([good_pi, bad_pi])

    result = extract_zeta_profile(
        phi_final, pi_final, N_offset, N_total, trajectory, potential,
        atol, rtol, units,
    )

    assert not result["failure_mask"][0]
    assert not np.isnan(result["zeta"][0])

    assert result["failure_mask"][1]
    assert np.isnan(result["zeta"][1])
