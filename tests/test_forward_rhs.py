"""
Unit tests for the forward-sector collocation RHS, with mandatory
response-field sourcing and the SBP-SAT boundary closure (prompt 21a),
ComputeTargets/GradientCoupledInstanton/forward_rhs.py.
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
from Numerics.DiscretizedOperators import (
    advection_split_matrix,
    advection_split_term,
    neumann_boundary_value,
)
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import advection_coefficient, delta_s


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
# Pack/unpack round trip -- enlarged state (prompt 21a): length 2*n_max, NOT
# 2*n_max-1, since phi_core is now an integrated DOF rather than
# Neumann-eliminated.
# ---------------------------------------------------------------------------


def test_pack_unpack_round_trip():
    grid = _make_grid()
    n_max = grid.n_max
    trajectory = _StubTrajectory()
    potential = _StubPotential()

    rng = np.random.default_rng(1234)
    state = rng.uniform(-0.5, 0.5, size=2 * n_max)

    phi_full, pi_full = unpack_state(
        state, _N, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )
    recovered = pack_state(phi_full, pi_full)

    np.testing.assert_array_equal(recovered, state)


def test_pack_unpack_state_length_is_2n_max():
    """Concrete regression guard for the prompt 21a layout change: the
    integrated state vector has length 2*n_max (phi_core included), not the
    old strong-BC layout's 2*n_max-1."""
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    phi_full = np.arange(n_nodes, dtype=float)
    pi_full = -np.arange(n_nodes, dtype=float)

    state = pack_state(phi_full, pi_full)
    assert state.shape == (2 * n_max,)


# ---------------------------------------------------------------------------
# Boundary handling -- phi_core is now a free, integrated DOF: unpack_state
# must return it VERBATIM from the state vector, not overwrite it via
# neumann_boundary_value (that formula is still used elsewhere -- as
# forward_rhs's live g_phi SAT target -- just no longer to set this value).
# ---------------------------------------------------------------------------


def test_unpack_state_core_is_read_verbatim_not_eliminated():
    grid = _make_grid()
    n_max = grid.n_max
    trajectory = _StubTrajectory()
    potential = _StubPotential()

    rng = np.random.default_rng(99)
    state = rng.uniform(-0.5, 0.5, size=2 * n_max)

    phi_full, pi_full = unpack_state(
        state, _N, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential
    )

    assert phi_full[0] == trajectory.phi_at(_N_OFFSET + _N)
    assert pi_full[0] == trajectory.pi_at(_N_OFFSET + _N)

    # phi_core (last entry of the phi block in the state vector) must come
    # back out unchanged -- NOT forced to satisfy the Neumann condition
    # (state was drawn at random, so it will not satisfy it in general).
    assert phi_full[-1] == state[n_max - 1]

    neumann_residual = grid.D[-1, :] @ phi_full
    assert abs(neumann_residual) > 1.0e-6, (
        "a randomly-drawn state should NOT satisfy the Neumann condition "
        "exactly -- if it does, phi_core is being silently overwritten "
        "again somewhere"
    )


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
# reference value from this exact same formula, so a wrong exponent/prefactor/
# node-indexing in eq:ncount would cancel identically on both sides and never
# be caught. This test instead hand-picks delta_s_N and a per-node
# delta_s_loc_array (plain numbers -- NOT generated by calling delta_s()) and
# re-derives eq:ncount's closed form with plain Python arithmetic (math.exp,
# not np.exp/n_count/measure or any other shared helper the production code
# also uses).
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
    state = rng.uniform(-0.5, 0.5, size=2 * n_max)

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
    state = rng.uniform(-0.5, 0.5, size=2 * n_max)

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

    disable_spatial_coupling=True also zeroes the SAT penalties (prompt
    21a), so g_pi_core_spline is never dereferenced -- passed as None.
    """
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    rng = np.random.default_rng(2024)
    state = rng.uniform(-0.7, 0.7, size=2 * n_max)

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
        rfield_splines, rmom_splines, diffusion_model, None,
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
# disable_spatial_coupling actually decouples EVERY node uniformly (prompt
# 21a: the core is no longer a special-cased, Neumann-eliminated node -- it
# is a free DOF exactly like every other node, so with spatial coupling (and
# hence the SAT, which only exists to stabilise that coupling) switched off,
# every node's pair of rows depends only on that SAME node's own state).
# ---------------------------------------------------------------------------


def test_disable_spatial_coupling_decouples_every_node_uniformly():
    grid = _make_grid()
    n_max = grid.n_max
    n_nodes = n_max + 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()
    rfield_splines = _zero_splines(n_nodes)
    rmom_splines = _zero_splines(n_nodes)

    rng = np.random.default_rng(555)
    base_state = rng.uniform(-0.5, 0.5, size=2 * n_max)
    base_result = forward_rhs(
        _N, base_state, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential,
        rfield_splines, rmom_splines, diffusion_model, None,
        disable_spatial_coupling=True,
    )

    for node_j in range(1, n_max + 1):
        phi_idx = node_j - 1
        pi_idx = n_max + (node_j - 1)

        # Perturbing phi at this node moves ONLY its own pi-row (through
        # dV/H_sq); dphi = pi identically here, so phi itself doesn't
        # appear in any dphi row at all, own or otherwise.
        perturbed = base_state.copy()
        perturbed[phi_idx] += 0.11
        result = forward_rhs(
            _N, perturbed, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory,
            potential, rfield_splines, rmom_splines, diffusion_model, None,
            disable_spatial_coupling=True,
        )
        changed = set(np.flatnonzero(result - base_result != 0.0))
        assert changed == {pi_idx}, (
            f"node {node_j}: perturbing phi changed {changed}, expected only "
            f"its own pi-row {{{pi_idx}}} -- a decoupling regression"
        )

        # Perturbing pi at this node moves its own phi-row (identity
        # dphi=pi) AND its own pi-row (local formula depends on pi too);
        # nothing at any other node.
        perturbed2 = base_state.copy()
        perturbed2[pi_idx] += 0.37
        result2 = forward_rhs(
            _N, perturbed2, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory,
            potential, rfield_splines, rmom_splines, diffusion_model, None,
            disable_spatial_coupling=True,
        )
        changed2 = set(np.flatnonzero(result2 - base_result != 0.0))
        assert changed2 == {phi_idx, pi_idx}, (
            f"node {node_j}: perturbing pi changed {changed2}, expected "
            f"{{{phi_idx}, {pi_idx}}} -- a decoupling regression"
        )


# ---------------------------------------------------------------------------
# SBP-SAT closure (prompt 21a) -- production-module tests
# ---------------------------------------------------------------------------


def test_advection_split_matrix_matches_phase1_prototype():
    """
    Numerics.DiscretizedOperators.advection_split_matrix (the production
    home, prompt 21a) must reproduce analyze_StiffnessSpectrum.py's own
    advection_split_matrix (the frozen, independently-tested Phase-1
    prototype the abscissa gate was passed against) EXACTLY -- this is a
    straight port, not a reimplementation, so any numerical difference here
    would mean the production code has silently diverged from the validated
    construction.
    """
    from tools.diagnostics.GradientCoupledInstanton.spectrum import (
        advection_split_matrix as prototype_advection_split_matrix,
    )

    grid = _make_grid(11)
    delta_s_N = 2.3
    epsilon_core = 0.05
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    production = advection_split_matrix(A_array, grid.D)
    prototype = prototype_advection_split_matrix(A_array, grid.D)

    np.testing.assert_allclose(production, prototype, rtol=1e-14, atol=1e-14)


def test_advection_split_term_is_matrix_vector_product():
    grid = _make_grid(11)
    delta_s_N = 2.3
    epsilon_core = 0.05
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    rng = np.random.default_rng(42)
    f = rng.uniform(-1.0, 1.0, size=grid.n_collocation_points)

    result = advection_split_term(f, A_array, grid.D)
    expected = advection_split_matrix(A_array, grid.D) @ f

    np.testing.assert_allclose(result, expected, rtol=1e-14)


def test_advection_split_matrix_is_skew_under_H_up_to_boundary_term():
    """
    H @ A_split + A_split^T @ H must be exactly diagonal (design note
    Section 3), with every entry -a'*w_j EXCEPT the core row, which carries
    the +A_core correction -- the same closed form
    tests/test_sbp_sat_boundary_closure.py already validates for the Phase-1
    prototype, re-derived here against the PRODUCTION advection_split_matrix
    to confirm the port didn't silently change the construction.
    """
    grid = _make_grid(17)
    alpha, N, epsilon_core = 0.1, 0.1, 0.01
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    H = np.diag(grid.weights)
    A_split = advection_split_matrix(A_array, grid.D)
    S = H @ A_split + A_split.T @ H

    off_diag = S - np.diag(np.diag(S))
    assert np.linalg.norm(off_diag) < 1.0e-10 * np.linalg.norm(S)

    a_prime = (1.0 - epsilon_core) / delta_s_N
    expected_diag = -a_prime * grid.weights
    expected_diag[-1] += A_array[-1]

    assert A_array[0] == pytest.approx(0.0, abs=1.0e-14)
    np.testing.assert_allclose(np.diag(S), expected_diag, atol=1.0e-10, rtol=1.0e-8)
    assert S[-1, -1] > 0.0  # the un-cancelled, n-independent destabilising entry


def _core_energy_coefficients(grid, A_array, tau):
    """Shared helper: (advection_u_core_sq_coefficient, sat_u_core_sq_coefficient,
    total) for a given grid/A_array/tau -- see
    test_sat_penalty_cancels_core_energy_defect_at_production_tau's own
    docstring for the derivation each piece comes from."""
    H = np.diag(grid.weights)
    A_split = advection_split_matrix(A_array, grid.D)
    S = H @ A_split + A_split.T @ H
    advection_coeff = 0.5 * S[-1, -1]
    sat_coeff = -tau
    return advection_coeff, sat_coeff, advection_coeff + sat_coeff


def test_sat_penalty_cancels_core_energy_defect_at_minimal_design_tau():
    """
    Design note Section 4's literal, MINIMAL admissible value tau=A(core)/2
    (not forward_rhs's own, deliberately larger, production tau -- see
    test_sat_penalty_production_tau_has_iteration_stability_margin below for
    why forward_rhs uses more): the SAT penalty's own contribution to the
    core-row energy balance EXACTLY cancels the split-form advection
    operator's uncancelled +A(core) boundary term, leaving the total
    core-row energy coefficient <= 0 (in fact exactly the ordinary bulk
    decay rate -a'*w_core/2, not merely bounded) -- the base-case algebra
    forward_rhs.py's own SAT comment block cites before describing its two
    empirical hardenings.
    """
    grid = _make_grid(21)
    alpha, N, epsilon_core = 0.1, 0.1, 0.01
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    A_core = float(A_array[-1])
    tau_minimal = 0.5 * A_core
    w_core = float(grid.weights[-1])

    advection_coeff, sat_coeff, total = _core_energy_coefficients(grid, A_array, tau_minimal)

    a_prime = (1.0 - epsilon_core) / delta_s_N
    assert total == pytest.approx(-0.5 * a_prime * w_core, rel=1e-10)
    assert total <= 0.0

    # A WRONG closure (tau=0, no SAT) would leave the destabilising, positive,
    # O(1) (not shrinking with n) term -- confirm that contrast directly.
    assert advection_coeff > 0.0
    assert advection_coeff == pytest.approx(0.5 * (A_core - a_prime * w_core))


def test_sat_penalty_production_tau_has_iteration_stability_margin():
    """
    forward_rhs's own PRODUCTION tau = abs(A_core) -- twice the design
    note's minimal admissible value, and abs() rather than signed -- is a
    strictly stronger (still-admissible) closure than the minimal recipe:
    the core-row energy coefficient is MORE negative (more stable) than the
    minimal recipe's -a'*w_core/2, in the epsilon_core<1 regime this test
    fixture uses. See forward_rhs.py's own SAT comment block for the full
    empirical story (an n_collocation_points=7 Picard-sweep oscillation on
    the production acceptance case, absent at this larger tau).
    """
    grid = _make_grid(21)
    alpha, N, epsilon_core = 0.1, 0.1, 0.01
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    A_core = float(A_array[-1])
    w_core = float(grid.weights[-1])
    a_prime = (1.0 - epsilon_core) / delta_s_N

    tau_production = abs(A_core)
    _, _, total_production = _core_energy_coefficients(grid, A_array, tau_production)

    # Exact closed form (a' > 0 here): -a'*(1 + w_core/2).
    assert total_production == pytest.approx(-a_prime * (1.0 + 0.5 * w_core), rel=1e-10)

    tau_minimal = 0.5 * A_core
    _, _, total_minimal = _core_energy_coefficients(grid, A_array, tau_minimal)

    assert total_production < total_minimal < 0.0  # strictly more stable, both admissible


def test_sat_penalty_tau_stays_dissipative_when_epsilon_core_exceeds_one():
    """
    Sign-robustness regression (prompt 21a): A_core = 2*a',
    a' = (1-epsilon_core)/Delta_s(N), goes NEGATIVE once epsilon_core > 1 --
    a transient, mid-shooting/mid-Picard-iteration state that IS reachable
    even though it never occurs at the converged solution. A signed
    tau = 0.5*A_core would go negative right along with it, turning the SAT
    into an amplifier (observed directly as a pi_core runaway toward the
    H_sq singularity on the production acceptance case before this fix).
    forward_rhs's actual tau = abs(A_core) must stay dissipative
    (core coefficient <= 0) here regardless.
    """
    grid = _make_grid(15)
    alpha, N = 0.1, 0.1
    epsilon_core = 1.5  # > 1: unphysical at convergence, but a reachable transient
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    A_core = float(A_array[-1])
    assert A_core < 0.0  # confirms the regime this test targets is exercised

    w_core = float(grid.weights[-1])
    a_prime = (1.0 - epsilon_core) / delta_s_N

    tau_signed = 0.5 * A_core  # the WRONG, sign-fragile version
    _, _, total_signed = _core_energy_coefficients(grid, A_array, tau_signed)
    assert total_signed > 0.0  # confirms the failure mode this fix avoids

    tau_production = abs(A_core)  # forward_rhs's actual choice
    _, _, total_production = _core_energy_coefficients(grid, A_array, tau_production)
    assert total_production == pytest.approx(a_prime * (3.0 - 0.5 * w_core), rel=1e-10)
    assert total_production < 0.0


def test_sat_penalty_targets_are_not_self_referential():
    """
    Design note Section 6 constraint (a): the SAT target g must not depend
    algebraically on the instantaneous u_core itself, or the penalty
    (including its stabilising -tau*u_core^2 piece) would vanish identically
    and be a no-op rather than a weaker version of the penalty. Concretely:
    perturbing ONLY phi_core in the state must change forward_rhs's phi-core
    SAT contribution (through the (phi_core - g_phi) term with g_phi fixed),
    not leave it unchanged as it would if g_phi silently tracked phi_core.
    """
    grid = _make_grid(9)
    n_max = grid.n_max
    n_nodes = n_max + 1
    trajectory = _StubTrajectory()
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()
    rfield_splines = _zero_splines(n_nodes)
    rmom_splines = _zero_splines(n_nodes)
    g_pi_core_spline = _ConstantSpline(0.0)

    rng = np.random.default_rng(3)
    base_state = rng.uniform(-0.3, 0.3, size=2 * n_max)

    base_result = forward_rhs(
        _N, base_state, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential,
        rfield_splines, rmom_splines, diffusion_model, g_pi_core_spline,
    )

    phi_core_idx = n_max - 1  # last entry of the phi block
    perturbed_state = base_state.copy()
    perturbed_state[phi_core_idx] += 0.2
    perturbed_result = forward_rhs(
        _N, perturbed_state, _N_OFFSET, _ALPHA, _H_SQ_NL_INIT, grid, trajectory, potential,
        rfield_splines, rmom_splines, diffusion_model, g_pi_core_spline,
    )

    # The core dphi-row (the last phi-block entry of the packed output) must
    # move by something other than what a purely self-cancelling penalty
    # would give -- i.e. it must simply be sensitive to the perturbation at
    # all under full spatial coupling.
    dphi_core_idx = n_max - 1
    assert perturbed_result[dphi_core_idx] != pytest.approx(base_result[dphi_core_idx])
