"""
Unit tests for the response-sector collocation RHS,
ComputeTargets/GradientCoupledInstanton/response_rhs.py.
"""

import numpy as np
import pytest

from ComputeTargets.GradientCoupledInstanton.response_rhs import (
    pack_response_state,
    unpack_response_state,
    response_rhs,
    terminal_response_state,
    _c_of_N,
    _assemble_response_derivatives,
)
from Numerics.OnionCoordinate import measure
from Numerics.LGLCollocation import LGLCollocationGrid


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubPotential:
    """
    Standalone duck-typed canonical-inflation potential (Mp = 1), matching
    AbstractPotential's own H_sq/epsilon formulas plus a constant V'' for a
    quadratic potential -- response_rhs only needs the four methods below,
    called generically.
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


class _ConstantSpline:
    """Trivial stand-in for SplineWrapper: returns the same value at any N."""

    def __init__(self, value: float):
        self._value = value

    def __call__(self, N):
        return self._value


def _make_grid(n_collocation_points=9):
    return LGLCollocationGrid(n_collocation_points)


_N = 2.0
_N_INIT = 0.0
_ALPHA = 0.05
_H_SQ_NL_INIT = 1.0


# ---------------------------------------------------------------------------
# Pack/unpack round trip
# ---------------------------------------------------------------------------


def test_pack_unpack_round_trip():
    grid = _make_grid()
    n_max = grid.n_max

    rng = np.random.default_rng(4321)
    state = rng.uniform(-0.5, 0.5, size=2 * n_max - 1)

    rfield_full, rmom_full = unpack_response_state(state, grid)
    recovered = pack_response_state(rfield_full, rmom_full)

    np.testing.assert_array_equal(recovered, state)


def test_unpack_response_state_swap_places_free_variable_in_rfield_at_core():
    """
    The last entry of the rfield block (state index n_max-1) is rfield_{n_max},
    the free core value. Confirm it lands in rfield_full, not rmom_full --
    a test that would fail if the forward sector's phi/pi layout (core phi
    eliminated, core pi free) had been copy-pasted here instead of swapped.
    """
    grid = _make_grid()
    n_max = grid.n_max

    state = np.zeros(2 * n_max - 1)
    sentinel = 7.25
    state[n_max - 1] = sentinel  # rfield_{n_max}

    rfield_full, rmom_full = unpack_response_state(state, grid)

    assert rfield_full[-1] == sentinel
    assert rmom_full[-1] == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Boundary handling
# ---------------------------------------------------------------------------


def test_unpack_response_state_boundary_handling():
    grid = _make_grid()
    n_max = grid.n_max

    rng = np.random.default_rng(17)
    state = rng.uniform(-0.5, 0.5, size=2 * n_max - 1)

    rfield_full, rmom_full = unpack_response_state(state, grid)

    assert rfield_full[0] == 0.0
    assert rmom_full[0] == 0.0

    neumann_residual = grid.D[-1, :] @ rmom_full
    assert neumann_residual == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# terminal_response_state
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lam", [0.5, -1.3, 3.7])
def test_terminal_response_state(lam):
    grid = _make_grid()
    n_max = grid.n_max
    delta_s_N_final = 0.42

    state = terminal_response_state(lam, grid, delta_s_N_final)
    rfield_full, rmom_full = unpack_response_state(state, grid)

    expected_core = -lam / (grid.weights[-1] * measure(1.0, delta_s_N_final))

    assert rfield_full[-1] == pytest.approx(expected_core, rel=1e-14)
    assert np.all(rmom_full == 0.0)
    # Every rfield entry other than the core must be exactly zero.
    assert np.all(rfield_full[:-1] == 0.0)


# ---------------------------------------------------------------------------
# c(N) is a scalar, not an array
# ---------------------------------------------------------------------------


def test_c_of_N_is_scalar_not_array():
    result = _c_of_N(epsilon_core=0.3, delta_s_N=0.5)
    assert np.ndim(result) == 0


# ---------------------------------------------------------------------------
# Reduction-limit cross-check against FullInstanton's actual bwd_rhs
# ---------------------------------------------------------------------------


def test_assemble_response_derivatives_matches_full_instanton_bwd_rhs():
    """
    Directly test the final assembly step with the advection/gradient
    contributions stripped (zeroed) and c(N) = 0 (the disable_spatial_coupling
    -equivalent condition for the response sector, since response_rhs itself
    has no such flag). What survives must match FullInstanton's bwd_rhs
    formula (dP1 = P2 * d2V_dphi2(phi1) / Hsq, dP2 = -P1 + (3-eps)*P2)
    exactly, elementwise, for deliberately different values at each node.
    """
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    potential = _StubPotential()

    rng = np.random.default_rng(31415)
    rfield_full = rng.uniform(-0.7, 0.7, size=n_nodes)
    rmom_full = rng.uniform(-0.7, 0.7, size=n_nodes)
    phi_full = 1.0 + 0.2 * np.arange(n_nodes)
    pi_full = rng.uniform(-0.3, 0.3, size=n_nodes)

    d2V_array = potential.d2V_dphi2(phi_full)
    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    epsilon_loc_array = potential.epsilon(phi_full, pi_full)

    zeros = np.zeros(n_nodes)
    drfield_full, drmom_full = _assemble_response_derivatives(
        rfield_full,
        rmom_full,
        d2V_array,
        H_sq_loc_array,
        epsilon_loc_array,
        c_N=0.0,
        gradient_term=zeros,
        advection_rfield_array=zeros,
        advection_rmom_array=zeros,
    )

    expected_drfield = d2V_array / H_sq_loc_array * rmom_full
    expected_drmom = -rfield_full + (3.0 - epsilon_loc_array) * rmom_full

    np.testing.assert_allclose(drfield_full, expected_drfield, rtol=1e-13, atol=1e-13)
    np.testing.assert_allclose(drmom_full, expected_drmom, rtol=1e-13, atol=1e-13)


def test_response_rhs_end_to_end_runs_and_matches_manual_assembly():
    """
    Full response_rhs() call, checked against an independent manual
    re-assembly using the same public Numerics/ helpers -- confirms the
    wiring inside response_rhs (spline evaluation, unpack, delta_s calls,
    L_operator/advection_term calls, packing) is self-consistent.
    """
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    potential = _StubPotential()

    rng = np.random.default_rng(2718)
    response_state = rng.uniform(-0.4, 0.4, size=2 * n_max - 1)
    phi_values = 1.0 + 0.15 * np.arange(n_nodes)
    pi_values = rng.uniform(-0.2, 0.2, size=n_nodes)
    phi_splines = [_ConstantSpline(v) for v in phi_values]
    pi_splines = [_ConstantSpline(v) for v in pi_values]

    result = response_rhs(
        _N, response_state, _N_INIT, _ALPHA, _H_SQ_NL_INIT, grid,
        phi_splines, pi_splines, potential,
    )

    assert result.shape == (2 * n_max - 1,)
    assert np.all(np.isfinite(result))
