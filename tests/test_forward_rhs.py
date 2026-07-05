"""
Unit tests for the forward-sector collocation RHS (response fields zero),
ComputeTargets/GradientCoupledInstanton/forward_rhs.py.
"""

import inspect

import numpy as np
import pytest

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential
from ComputeTargets.InflatonTrajectory import InflatonTrajectory
from ComputeTargets.GradientCoupledInstanton.forward_rhs import (
    pack_state,
    unpack_state,
    forward_rhs,
)
from Numerics.LGLCollocation import LGLCollocationGrid


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubTrajectory:
    """Closed-form phi_before_end/pi_before_end -- no real ODE integration."""

    def phi_before_end(self, N: float) -> float:
        return 1.0 + 0.3 * N

    def pi_before_end(self, N: float) -> float:
        return -0.2 * N + 0.05 * N ** 2


class _StubPotential:
    """
    Standalone duck-typed canonical-inflation potential (Mp = 1), matching
    AbstractPotential's own H_sq/epsilon formulas, but with no Units/
    DatastoreObject dependency -- forward_rhs only needs the four methods
    below, called generically.
    """

    def __init__(self, m_sq: float = 1.3):
        self._m_sq = m_sq

    def V(self, phi):
        phi = np.asarray(phi)
        return 0.5 * self._m_sq * phi ** 2

    def dV_dphi(self, phi):
        return self._m_sq * np.asarray(phi)

    def H_sq(self, phi, pi):
        pi = np.asarray(pi)
        return self.V(phi) / (3.0 - 0.5 * pi ** 2)

    def epsilon(self, phi, pi):
        pi = np.asarray(pi)
        return 0.5 * pi ** 2


_N = 2.0
_N_INIT = 0.0
_ALPHA = 0.05
_H_SQ_NL_INIT = 1.0


def _make_grid(n_collocation_points=9):
    return LGLCollocationGrid(n_collocation_points)


# ---------------------------------------------------------------------------
# Part A -- AbstractPotential vectorization docstring note
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method_name", ["H_sq", "epsilon", "dV_dphi"])
def test_abstract_potential_docstrings_note_vectorization(method_name):
    method = getattr(AbstractPotential, method_name)
    doc = inspect.getdoc(method) or ""
    assert "ndarray" in doc
    assert "broadcast" in doc


# ---------------------------------------------------------------------------
# Part B -- InflatonTrajectory before-end convenience methods
# ---------------------------------------------------------------------------


def _make_bare_trajectory():
    return InflatonTrajectory(
        store_id=None,
        phi0=None,
        pi0=None,
        potential=None,
        samples_per_N=None,
        atol=None,
        rtol=None,
    )


def test_phi_before_end_calls_phi_at_at_N_end_minus_N():
    traj = _make_bare_trajectory()
    traj._N_end = 10.0

    calls = []

    def fake_phi_at(N):
        calls.append(N)
        return 42.0

    traj.phi_at = fake_phi_at

    result = traj.phi_before_end(3.5)

    assert calls == [10.0 - 3.5]
    assert result == 42.0


def test_pi_before_end_calls_pi_at_at_N_end_minus_N():
    traj = _make_bare_trajectory()
    traj._N_end = 7.25

    calls = []

    def fake_pi_at(N):
        calls.append(N)
        return -1.5

    traj.pi_at = fake_pi_at

    result = traj.pi_before_end(1.0)

    assert calls == [7.25 - 1.0]
    assert result == -1.5


def test_rho_before_end_calls_rho_at_at_N_end_minus_N():
    traj = _make_bare_trajectory()
    traj._N_end = 5.0

    calls = []

    def fake_rho_at(N):
        calls.append(N)
        return 0.75

    traj.rho_at = fake_rho_at

    result = traj.rho_before_end(2.0)

    assert calls == [5.0 - 2.0]
    assert result == 0.75


# ---------------------------------------------------------------------------
# Pack/unpack round trip
# ---------------------------------------------------------------------------


def test_pack_unpack_round_trip():
    grid = _make_grid()
    n_max = grid.n_max
    trajectory = _StubTrajectory()
    potential = _StubPotential()

    rng = np.random.default_rng(1234)
    state = rng.uniform(-0.5, 0.5, size=2 * n_max - 1)

    phi_full, pi_full = unpack_state(
        state, _N, _N_INIT, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )
    recovered = pack_state(phi_full, pi_full)

    np.testing.assert_array_equal(recovered, state)


# ---------------------------------------------------------------------------
# Boundary handling
# ---------------------------------------------------------------------------


def test_unpack_state_boundary_handling():
    grid = _make_grid()
    n_max = grid.n_max
    trajectory = _StubTrajectory()
    potential = _StubPotential()

    rng = np.random.default_rng(99)
    state = rng.uniform(-0.5, 0.5, size=2 * n_max - 1)

    phi_full, pi_full = unpack_state(
        state, _N, _N_INIT, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )

    assert phi_full[0] == trajectory.phi_before_end(_N)
    assert pi_full[0] == trajectory.pi_before_end(_N)

    neumann_residual = grid.D[-1, :] @ phi_full
    assert neumann_residual == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Reduction-limit cross-check
# ---------------------------------------------------------------------------


def test_disable_spatial_coupling_matches_full_instanton_fwd_rhs():
    grid = _make_grid()
    n_max = grid.n_max
    trajectory = _StubTrajectory()
    potential = _StubPotential()

    rng = np.random.default_rng(2024)
    state = rng.uniform(-0.7, 0.7, size=2 * n_max - 1)

    phi_full, pi_full = unpack_state(
        state, _N, _N_INIT, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )

    result = forward_rhs(
        _N, state, _N_INIT, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential,
        disable_spatial_coupling=True,
    )

    expected_dphi_full = pi_full
    expected_dpi_full = (
        -(3.0 - potential.epsilon(phi_full, pi_full)) * pi_full
        - potential.dV_dphi(phi_full) / potential.H_sq(phi_full, pi_full)
    )
    expected = pack_state(expected_dphi_full, expected_dpi_full)

    np.testing.assert_allclose(result, expected, rtol=1e-13, atol=1e-13)


# ---------------------------------------------------------------------------
# disable_spatial_coupling actually decouples nodes
# ---------------------------------------------------------------------------


def test_disable_spatial_coupling_decouples_interior_nodes():
    grid = _make_grid()
    n_max = grid.n_max
    n_phi_interior = n_max - 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()

    rng = np.random.default_rng(555)
    base_state = rng.uniform(-0.5, 0.5, size=2 * n_max - 1)
    base_result = forward_rhs(
        _N, base_state, _N_INIT, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential,
        disable_spatial_coupling=True,
    )

    # --- Perturb an interior pi value. pi carries no boundary elimination,
    # so only its own node's derivatives (dphi_j through pi_j, dpi_j through
    # the local formula) may move -- nothing else.
    pi_block_index = 2
    node_j = pi_block_index + 1
    pi_state_index = n_phi_interior + pi_block_index

    perturbed_state = base_state.copy()
    perturbed_state[pi_state_index] += 0.37
    perturbed_result = forward_rhs(
        _N, perturbed_state, _N_INIT, _ALPHA, _H_SQ_NL_INIT, grid, trajectory,
        potential, disable_spatial_coupling=True,
    )

    expected_changed = {pi_state_index}
    if node_j <= n_max - 1:
        expected_changed.add(node_j - 1)

    diff = perturbed_result - base_result
    changed = set(np.flatnonzero(diff != 0.0))
    assert changed == expected_changed

    # --- Perturb an interior phi value. Every interior phi feeds into the
    # Neumann elimination of phi_full[n_max] (the hard-eliminated core row),
    # so it is expected to also move the core node's own pi-derivative --
    # but nothing at any OTHER interior node. This is the boundary-condition
    # structure, not spatial (gradient/advection) coupling, and is
    # unaffected by disable_spatial_coupling.
    phi_block_index = 2
    node_j2 = phi_block_index + 1
    assert node_j2 != n_max - 1  # keep the two affected rows distinct below

    perturbed_state2 = base_state.copy()
    perturbed_state2[phi_block_index] += 0.11
    perturbed_result2 = forward_rhs(
        _N, perturbed_state2, _N_INIT, _ALPHA, _H_SQ_NL_INIT, grid, trajectory,
        potential, disable_spatial_coupling=True,
    )

    dpi_own_index = n_phi_interior + (node_j2 - 1)
    dpi_core_index = n_phi_interior + (n_max - 1)
    expected_changed2 = {dpi_own_index, dpi_core_index}

    diff2 = perturbed_result2 - base_result
    changed2 = set(np.flatnonzero(diff2 != 0.0))
    assert changed2 == expected_changed2
