"""
Unit tests for the forward-sector collocation RHS, with mandatory
response-field sourcing, ComputeTargets/GradientCoupledInstanton/forward_rhs.py.
"""

import inspect
import math

import numpy as np
import pytest

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential
from ComputeTargets.GradientCoupledInstanton.forward_rhs import (
    pack_state,
    unpack_state,
    forward_rhs,
    noise_source_terms,
    diluted_diffusion_coefficients,
    n_count,
)
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import delta_s


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubTrajectory:
    """Closed-form phi_at/pi_at -- no real ODE integration."""

    def phi_at(self, N: float) -> float:
        return 1.0 + 0.3 * N

    def pi_at(self, N: float) -> float:
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


class _ConstantSpline:
    """Trivial N-independent stand-in for SplineWrapper: returns the same
    value at any N. Matches the stub used in tests/test_response_rhs.py."""

    def __init__(self, value: float):
        self._value = value

    def __call__(self, N):
        return self._value


_N = 2.0
_N_OFFSET = 0.0
_ALPHA = 0.05
_H_SQ_NL_INIT = 1.0


def _make_grid(n_collocation_points=9):
    return LGLCollocationGrid(n_collocation_points)


def _zero_splines(n_nodes):
    return [_ConstantSpline(0.0) for _ in range(n_nodes)]


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
        state, _N, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
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
        state, _N, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )

    assert phi_full[0] == trajectory.phi_at(_N_OFFSET + _N)
    assert pi_full[0] == trajectory.pi_at(_N_OFFSET + _N)

    neumann_residual = grid.D[-1, :] @ phi_full
    assert neumann_residual == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Delta_s(N=0) = ln(1+alpha) for the zeroth Picard iterate
# ---------------------------------------------------------------------------


def test_delta_s_at_N_zero_equals_log1p_alpha_for_zeroth_picard_iterate():
    """
    Concrete, checkable consequence of the N-convention fix: forward_rhs's
    own core-only Delta_s(N) computation (unpack_state then
    potential.H_sq(phi_core, pi_core) then delta_s(N, 0.0, ...)) must equal
    exactly ln(1+alpha) at N=0.0 when the full state's core node is set to
    the trajectory's own initial values -- i.e. the zeroth Picard iterate,
    where the state is uniform in y and equal to
    trajectory.phi_at(N_offset)/.pi_at(N_offset), and H_sq_nl_init is
    computed from those same values, so H_sq_core == H_sq_nl_init exactly.
    """
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()

    N_offset = 3.0
    phi_init = trajectory.phi_at(N_offset)
    pi_init = trajectory.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)

    state_init = pack_state(np.full(n_nodes, phi_init), np.full(n_nodes, pi_init))

    phi_full, pi_full = unpack_state(
        state_init, 0.0, N_offset, _ALPHA, H_sq_nl_init, grid, trajectory, potential
    )

    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(0.0, 0.0, H_sq_core, H_sq_nl_init, _ALPHA)

    assert delta_s_N == pytest.approx(np.log(1.0 + _ALPHA), abs=1e-12)


# ---------------------------------------------------------------------------
# n_count -- independent check against eq:ncount's closed form (prompt 15,
# Part A). Every OTHER test in this file that touches n_count builds its own
# reference value from this exact same formula (the production code's own
# 1.5*delta_s_N*exp(3*delta_s_loc)*exp(-1.5*(y+1)*delta_s_N)), so a wrong
# exponent/prefactor/node-indexing in eq:ncount would cancel identically on
# both sides and never be caught. This test instead hand-picks delta_s_N and
# a per-node delta_s_loc_array (plain numbers -- NOT generated by calling
# delta_s()) and re-derives eq:ncount's closed form with plain Python
# arithmetic (math.exp, not np.exp/n_count/measure or any other shared
# helper the production code also uses).
# ---------------------------------------------------------------------------


def test_n_count_matches_closed_form_hand_chosen_values():
    grid = _make_grid(5)
    y = grid.nodes  # node positions only -- not itself part of the formula under test

    delta_s_N = 3.0
    # Distinct, hand-chosen Delta_s_loc(y_j,N) values, increasing with y_j
    # (as physically expected -- Delta_s_loc(y=+1,N) coincides with the
    # core-only Delta_s_N) -- genuinely spans two orders of magnitude in the
    # resulting n_count, matching the coverage-gap investigation's own
    # finding, not a degenerate uniform fixture.
    delta_s_loc_array = np.array([0.1, 1.0, 2.0, 3.5, 4.5])

    result = n_count(delta_s_N, delta_s_loc_array, grid)

    expected = np.array([
        1.5 * delta_s_N * math.exp(3.0 * dsl) * math.exp(-1.5 * (yj + 1.0) * delta_s_N)
        for yj, dsl in zip(y, delta_s_loc_array)
    ])

    np.testing.assert_allclose(result, expected, rtol=1e-13)
    assert expected.max() / expected.min() > 10.0


# ---------------------------------------------------------------------------
# noise_source_terms -- extracted-helper consistency (Part A refactor)
# ---------------------------------------------------------------------------


def test_noise_source_terms_matches_forward_rhs_assembly():
    """
    Direct check that the extracted noise_source_terms() helper reproduces
    exactly the two source terms forward_rhs itself now assembles from it --
    confirming the refactor moved the computation rather than changing it.
    """
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    rng = np.random.default_rng(7)
    state = rng.uniform(-0.5, 0.5, size=2 * n_max - 1)

    phi_full, pi_full = unpack_state(
        state, _N, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )

    rfield_full = rng.uniform(-0.3, 0.3, size=n_nodes)
    rmom_full = rng.uniform(-0.3, 0.3, size=n_nodes)

    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(_N, 0.0, H_sq_core, _H_SQ_NL_INIT, _ALPHA)
    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    delta_s_loc_array = delta_s(_N, 0.0, H_sq_loc_array, _H_SQ_NL_INIT, _ALPHA)

    noise_field_array, noise_mom_array = noise_source_terms(
        phi_full, pi_full, rfield_full, rmom_full, delta_s_N, delta_s_loc_array,
        grid, potential, diffusion_model,
    )

    D_matrix_vals = [
        diffusion_model.D_matrix(phi_full[j], pi_full[j], potential) for j in range(n_nodes)
    ]
    D11_arr = np.array([v[0] for v in D_matrix_vals])
    D12_arr = np.array([v[1] for v in D_matrix_vals])
    D22_arr = np.array([v[2] for v in D_matrix_vals])

    n_count_array = (
        1.5 * delta_s_N
        * np.exp(3.0 * delta_s_loc_array)
        * np.exp(-1.5 * (grid.nodes + 1.0) * delta_s_N)
    )
    D_phi_arr = 2.0 * D11_arr / n_count_array
    D_pi_arr = 2.0 * D22_arr / n_count_array
    D_phipi_arr = 2.0 * D12_arr / n_count_array

    expected_noise_field = D_phi_arr * rfield_full + D_phipi_arr * rmom_full
    expected_noise_mom = D_pi_arr * rmom_full + D_phipi_arr * rfield_full

    np.testing.assert_allclose(noise_field_array, expected_noise_field, rtol=1e-14)
    np.testing.assert_allclose(noise_mom_array, expected_noise_mom, rtol=1e-14)


def test_diluted_diffusion_coefficients_decomposes_noise_source_terms():
    """
    diluted_diffusion_coefficients() was factored out of noise_source_terms's
    own body (to let GradientCoupledInstanton's Hawking-sigma noise summary
    stats reuse just the coefficients, without any particular rfield/rmom).
    Confirm it reproduces the exact D_phi/D_pi/D_phipi values against a hand
    computation, and that combining them with rfield/rmom via
    noise_source_terms's own formula reproduces noise_source_terms's output
    exactly -- i.e. the refactor is a pure decomposition, not a behavior change.
    """
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    rng = np.random.default_rng(11)
    state = rng.uniform(-0.5, 0.5, size=2 * n_max - 1)

    phi_full, pi_full = unpack_state(
        state, _N, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )
    rfield_full = rng.uniform(-0.4, 0.4, size=n_nodes)
    rmom_full = rng.uniform(-0.4, 0.4, size=n_nodes)

    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(_N, 0.0, H_sq_core, _H_SQ_NL_INIT, _ALPHA)
    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    delta_s_loc_array = delta_s(_N, 0.0, H_sq_loc_array, _H_SQ_NL_INIT, _ALPHA)

    D_phi_arr, D_pi_arr, D_phipi_arr = diluted_diffusion_coefficients(
        phi_full, pi_full, delta_s_N, delta_s_loc_array, grid, potential, diffusion_model,
    )

    D_matrix_vals = [
        diffusion_model.D_matrix(phi_full[j], pi_full[j], potential) for j in range(n_nodes)
    ]
    D11_arr = np.array([v[0] for v in D_matrix_vals])
    D12_arr = np.array([v[1] for v in D_matrix_vals])
    D22_arr = np.array([v[2] for v in D_matrix_vals])
    n_count_array = (
        1.5 * delta_s_N
        * np.exp(3.0 * delta_s_loc_array)
        * np.exp(-1.5 * (grid.nodes + 1.0) * delta_s_N)
    )

    np.testing.assert_allclose(D_phi_arr, 2.0 * D11_arr / n_count_array, rtol=1e-14)
    np.testing.assert_allclose(D_pi_arr, 2.0 * D22_arr / n_count_array, rtol=1e-14)
    np.testing.assert_allclose(D_phipi_arr, 2.0 * D12_arr / n_count_array, rtol=1e-14)

    noise_field_array, noise_mom_array = noise_source_terms(
        phi_full, pi_full, rfield_full, rmom_full, delta_s_N, delta_s_loc_array,
        grid, potential, diffusion_model,
    )
    expected_noise_field = D_phi_arr * rfield_full + D_phipi_arr * rmom_full
    expected_noise_mom = D_pi_arr * rmom_full + D_phipi_arr * rfield_full

    np.testing.assert_allclose(noise_field_array, expected_noise_field, rtol=1e-14)
    np.testing.assert_allclose(noise_mom_array, expected_noise_mom, rtol=1e-14)


# ---------------------------------------------------------------------------
# Reduction-limit cross-check
# ---------------------------------------------------------------------------


def test_disable_spatial_coupling_matches_full_instanton_fwd_rhs():
    """
    Strengthened reduction-limit test: constant (in N), nonzero,
    per-node response-field values and a real diffusion model, compared
    against FullInstanton's actual fwd_rhs formula
    (dphi1 = phi2 + 2*D11*P1 + 2*D12*P2,
     dphi2 = -(3-eps)*phi2 - dV/Hsq + 2*D12*P1 + 2*D22*P2)
    with matching nonzero P1, P2 values, to floating-point precision.

    forward_rhs's own sourcing is diluted by n_count(y_j,N) -- a genuinely
    y-dependent geometric factor that is never 1 identically, even for
    uniform phi/pi -- so the response-field splines are constructed as
    P1_target * n_count(y_j,N) (per node j) rather than a single scalar
    P1_target broadcast to every node; this exactly cancels the dilution
    and reduces forward_rhs's sourcing term to FullInstanton's undiluted
    2*D11*P1 + 2*D12*P2 term at every node.
    """
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    rng = np.random.default_rng(2024)
    state = rng.uniform(-0.7, 0.7, size=2 * n_max - 1)

    phi_full, pi_full = unpack_state(
        state, _N, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )

    P1_target = 0.42
    P2_target = -0.17

    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(_N, 0.0, H_sq_core, _H_SQ_NL_INIT, _ALPHA)
    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    delta_s_loc_array = delta_s(_N, 0.0, H_sq_loc_array, _H_SQ_NL_INIT, _ALPHA)
    n_count_array = (
        1.5 * delta_s_N
        * np.exp(3.0 * delta_s_loc_array)
        * np.exp(-1.5 * (grid.nodes + 1.0) * delta_s_N)
    )

    rfield_splines = [_ConstantSpline(P1_target * n_count_array[j]) for j in range(n_nodes)]
    rmom_splines = [_ConstantSpline(P2_target * n_count_array[j]) for j in range(n_nodes)]

    result = forward_rhs(
        _N, state, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential,
        rfield_splines, rmom_splines, diffusion_model,
        disable_spatial_coupling=True,
    )

    D_matrix_vals = [
        diffusion_model.D_matrix(phi_full[j], pi_full[j], potential) for j in range(n_nodes)
    ]
    D11_arr = np.array([v[0] for v in D_matrix_vals])
    D12_arr = np.array([v[1] for v in D_matrix_vals])
    D22_arr = np.array([v[2] for v in D_matrix_vals])

    expected_dphi_full = (
        pi_full + 2.0 * D11_arr * P1_target + 2.0 * D12_arr * P2_target
    )
    expected_dpi_full = (
        -(3.0 - potential.epsilon(phi_full, pi_full)) * pi_full
        - potential.dV_dphi(phi_full) / potential.H_sq(phi_full, pi_full)
        + 2.0 * D12_arr * P1_target
        + 2.0 * D22_arr * P2_target
    )
    expected = pack_state(expected_dphi_full, expected_dpi_full)

    np.testing.assert_allclose(result, expected, rtol=1e-12, atol=1e-12)


# ---------------------------------------------------------------------------
# disable_spatial_coupling actually decouples nodes
# ---------------------------------------------------------------------------


def test_disable_spatial_coupling_decouples_interior_nodes():
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    n_phi_interior = n_max - 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()
    rfield_splines = _zero_splines(n_nodes)
    rmom_splines = _zero_splines(n_nodes)

    rng = np.random.default_rng(555)
    base_state = rng.uniform(-0.5, 0.5, size=2 * n_max - 1)
    base_result = forward_rhs(
        _N, base_state, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential,
        rfield_splines, rmom_splines, diffusion_model,
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
        _N, perturbed_state, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory,
        potential, rfield_splines, rmom_splines, diffusion_model,
        disable_spatial_coupling=True,
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
        _N, perturbed_state2, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory,
        potential, rfield_splines, rmom_splines, diffusion_model,
        disable_spatial_coupling=True,
    )

    dpi_own_index = n_phi_interior + (node_j2 - 1)
    dpi_core_index = n_phi_interior + (n_max - 1)
    expected_changed2 = {dpi_own_index, dpi_core_index}

    diff2 = perturbed_result2 - base_result
    changed2 = set(np.flatnonzero(diff2 != 0.0))
    assert changed2 == expected_changed2
