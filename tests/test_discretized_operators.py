"""
Unit tests for the discretized L operator, advection term, and Neumann hard
elimination (Numerics/DiscretizedOperators.py).
"""

import numpy as np
import pytest

from config.defaults import DEFAULT_N_COLLOCATION_POINTS
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import advection_coefficient
from Numerics.DiscretizedOperators import (
    L_operator,
    advection_term,
    neumann_boundary_value,
)


# --- Test polynomials: (value, first derivative, second derivative) -------
# Each entry is a callable returning phi(y), phi'(y), phi''(y) for an ndarray y.


def _poly_const(y):
    return np.full_like(y, 3.0), np.zeros_like(y), np.zeros_like(y)


def _poly_linear(y):
    return 2.0 - 5.0 * y, np.full_like(y, -5.0), np.zeros_like(y)


def _poly_quadratic(y):
    phi = 1.0 - 2.0 * y + 3.0 * y**2
    dphi = -2.0 + 6.0 * y
    d2phi = np.full_like(y, 6.0)
    return phi, dphi, d2phi


def _poly_cubic(y):
    phi = 0.5 * y**3 - 2.0 * y**2 + y - 4.0
    dphi = 1.5 * y**2 - 4.0 * y + 1.0
    d2phi = 3.0 * y - 4.0
    return phi, dphi, d2phi


def _poly_quartic(y):
    phi = y**4 - y**3 + 2.0 * y - 1.0
    dphi = 4.0 * y**3 - 3.0 * y**2 + 2.0
    d2phi = 12.0 * y**2 - 6.0 * y
    return phi, dphi, d2phi


TEST_POLYNOMIALS = [
    _poly_const,
    _poly_linear,
    _poly_quadratic,
    _poly_cubic,
    _poly_quartic,
]

DELTA_S_N_VALUES = [0.1, 1.0, 3.7, 15.0]

N_MAX = 6  # degree, so n_collocation_points = 7; all test polynomials have degree <= 4


# --- L_operator exactness on polynomials -----------------------------------


@pytest.mark.parametrize("poly", TEST_POLYNOMIALS)
@pytest.mark.parametrize("delta_s_N", DELTA_S_N_VALUES)
def test_L_operator_exact_on_polynomials(poly, delta_s_N):
    grid = LGLCollocationGrid(N_MAX + 1)
    y = grid.nodes

    phi, dphi, d2phi = poly(y)

    result = L_operator(phi, delta_s_N, y, grid.D, grid.D2)

    prefactor = np.exp(delta_s_N) * np.exp(delta_s_N * y)
    expected = prefactor * (
        (4.0 / delta_s_N**2) * d2phi - (2.0 / delta_s_N) * dphi
    )

    # delta_s_N can make the prefactor span many orders of magnitude, so
    # roundoff in D2 @ f / D @ f (which is exact only up to machine
    # precision relative to the matrix entries) gets amplified by that
    # same prefactor -- scale the absolute tolerance with it rather than
    # using a fixed absolute floor.
    atol = 1e-9 * np.max(np.abs(prefactor))
    np.testing.assert_allclose(result, expected, rtol=1e-8, atol=atol)


# --- advection_term exactness ----------------------------------------------


@pytest.mark.parametrize("poly", TEST_POLYNOMIALS)
@pytest.mark.parametrize("delta_s_N", DELTA_S_N_VALUES)
@pytest.mark.parametrize("epsilon_core", [-1.0, 0.0, 0.5, 2.0])
def test_advection_term_exact_on_polynomials(poly, delta_s_N, epsilon_core):
    grid = LGLCollocationGrid(N_MAX + 1)
    y = grid.nodes

    phi, dphi, _ = poly(y)

    A_array = advection_coefficient(y, delta_s_N, epsilon_core)
    result = advection_term(phi, A_array, grid.D)

    expected = A_array * dphi

    np.testing.assert_allclose(result, expected, rtol=1e-8, atol=1e-8)


# --- neumann_boundary_value: recovers a known zero-derivative point --------


@pytest.mark.parametrize(
    "n_collocation_points", [3, 5, 7, DEFAULT_N_COLLOCATION_POINTS]
)
def test_neumann_boundary_value_recovers_known_zero_derivative(
    n_collocation_points,
):
    grid = LGLCollocationGrid(n_collocation_points)
    y = grid.nodes

    # phi(y) = (y-1)^2 has phi'(1) = 0 exactly, and phi(1) = 0.
    phi = (y - 1.0) ** 2

    # Deliberately corrupt the boundary entry to confirm it is ignored.
    phi_input = phi.copy()
    phi_input[-1] = 12345.6789

    f_b = neumann_boundary_value(phi_input, grid.D, boundary_index=-1)

    assert f_b == pytest.approx(0.0, abs=1e-9)


# --- neumann_boundary_value: structural property ---------------------------


@pytest.mark.parametrize(
    "n_collocation_points", [3, 5, 7, DEFAULT_N_COLLOCATION_POINTS]
)
@pytest.mark.parametrize("boundary_index", [-1, 0])
def test_neumann_boundary_value_structural_property(
    n_collocation_points, boundary_index
):
    rng = np.random.default_rng(1234)
    grid = LGLCollocationGrid(n_collocation_points)

    # Arbitrary, non-Neumann-consistent array.
    f = rng.uniform(-5.0, 5.0, size=n_collocation_points)

    f_b = neumann_boundary_value(f, grid.D, boundary_index=boundary_index)

    f_completed = f.copy()
    f_completed[boundary_index] = f_b

    Df = grid.D @ f_completed
    assert Df[boundary_index] == pytest.approx(0.0, abs=1e-10)


# --- Integration with prompts 01-02 ----------------------------------------


def test_integration_with_lgl_grid_and_onion_coordinate():
    grid = LGLCollocationGrid(DEFAULT_N_COLLOCATION_POINTS)
    y = grid.nodes

    delta_s_N = 4.2
    epsilon_core = 0.3

    A_array = advection_coefficient(y, delta_s_N, epsilon_core)

    # Use a low-degree polynomial well within the grid's exactness range.
    phi = 1.0 - 2.0 * y + 3.0 * y**2 - y**3
    dphi = -2.0 + 6.0 * y - 3.0 * y**2
    d2phi = 6.0 - 6.0 * y

    L_result = L_operator(phi, delta_s_N, y, grid.D, grid.D2)
    expected_L = (
        np.exp(delta_s_N)
        * np.exp(delta_s_N * y)
        * ((4.0 / delta_s_N**2) * d2phi - (2.0 / delta_s_N) * dphi)
    )
    np.testing.assert_allclose(L_result, expected_L, rtol=1e-8, atol=1e-8)

    adv_result = advection_term(phi, A_array, grid.D)
    expected_adv = A_array * dphi
    np.testing.assert_allclose(adv_result, expected_adv, rtol=1e-8, atol=1e-8)
