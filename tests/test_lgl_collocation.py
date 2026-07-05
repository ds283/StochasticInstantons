"""
Unit tests for the LGL collocation grid (Numerics/LGLCollocation.py).

Tabulated node values below are cross-checked independently of
LGLCollocationGrid's own Jacobi-tridiagonal-eigenvalue construction, using
numpy.polynomial.legendre's companion-matrix root finder on the derivative
Legendre polynomial (n_max=2..5 additionally have simple closed forms, given
in comments, which agree with the numeric values to machine precision).
"""

import numpy as np
import pytest

from config.defaults import DEFAULT_N_COLLOCATION_POINTS
from Numerics.LGLCollocation import CollocationGrid, LGLCollocationGrid


# --- Tabulated LGL node values -----------------------------------------
# n_max=2: {-1, 0, 1}
# n_max=3: {-1, -1/sqrt(5), 1/sqrt(5), 1}
# n_max=4: {-1, -sqrt(3/7), 0, sqrt(3/7), 1}
# n_max=6, n_max=8: no simple closed form; values below from an independent
# companion-matrix root find (numpy.polynomial.legendre.legroots on the
# derivative polynomial), matching the standard published LGL node tables.
TABULATED_NODES = {
    2: np.array([-1.0, 0.0, 1.0]),
    3: np.array([-1.0, -1.0 / np.sqrt(5.0), 1.0 / np.sqrt(5.0), 1.0]),
    4: np.array([-1.0, -np.sqrt(3.0 / 7.0), 0.0, np.sqrt(3.0 / 7.0), 1.0]),
    6: np.array(
        [
            -1.0,
            -0.83022389627856685,
            -0.4688487934707144,
            0.0,
            0.46884879347071423,
            0.83022389627856708,
            1.0,
        ]
    ),
    8: np.array(
        [
            -1.0,
            -0.89975799541146029,
            -0.67718627951073629,
            -0.36311746382617777,
            0.0,
            0.36311746382617816,
            0.67718627951073773,
            0.89975799541145984,
            1.0,
        ]
    ),
}


@pytest.mark.parametrize("bad_value", [2.5, "5", 5.0, None, [5]])
def test_constructor_rejects_non_integer(bad_value):
    with pytest.raises(ValueError, match="integer"):
        LGLCollocationGrid(bad_value)


@pytest.mark.parametrize("bad_value", [-1, 0, 1])
def test_constructor_rejects_too_few_points(bad_value):
    with pytest.raises(ValueError, match=">= 2"):
        LGLCollocationGrid(bad_value)


@pytest.mark.parametrize("n_collocation_points", [2, 3, 5, 9, DEFAULT_N_COLLOCATION_POINTS])
def test_n_max_and_n_collocation_points_relationship(n_collocation_points):
    grid = LGLCollocationGrid(n_collocation_points)
    assert grid.n_max == n_collocation_points - 1
    assert grid.n_collocation_points == n_collocation_points
    assert len(grid.nodes) == n_collocation_points


@pytest.mark.parametrize("n_max", sorted(TABULATED_NODES.keys()))
def test_nodes_match_tabulated_values(n_max):
    grid = LGLCollocationGrid(n_max + 1)
    np.testing.assert_allclose(grid.nodes, TABULATED_NODES[n_max], atol=1e-13, rtol=0)


@pytest.mark.parametrize("n_max", [2, 3, 4, 6, 8, DEFAULT_N_COLLOCATION_POINTS - 1])
def test_endpoint_weights_exact(n_max):
    grid = LGLCollocationGrid(n_max + 1)
    expected = 2.0 / (n_max * (n_max + 1))
    assert grid.weights[0] == pytest.approx(expected, abs=0.0, rel=1e-14)
    assert grid.weights[-1] == pytest.approx(expected, abs=0.0, rel=1e-14)


@pytest.mark.parametrize("n_max", [2, 3, 4, 5, 6, 8])
def test_quadrature_exactness(n_max):
    grid = LGLCollocationGrid(n_max + 1)
    # LGL quadrature with n_max+1 nodes is exact for polynomials up to degree
    # 2*n_max - 1.
    max_degree = 2 * n_max - 1
    for k in range(max_degree + 1):
        quad = np.sum(grid.weights * grid.nodes**k)
        exact = 0.0 if k % 2 == 1 else 2.0 / (k + 1)
        assert quad == pytest.approx(exact, abs=1e-11)


@pytest.mark.parametrize("n_max", [2, 3, 4, 5, 6, 8])
def test_differentiation_exact_on_monomials(n_max):
    grid = LGLCollocationGrid(n_max + 1)
    y = grid.nodes
    for k in range(n_max + 1):
        p = y**k
        dp_exact = k * y ** (k - 1) if k > 0 else np.zeros_like(y)
        d2p_exact = (
            k * (k - 1) * y ** (k - 2) if k > 1 else np.zeros_like(y)
        )
        np.testing.assert_allclose(grid.D @ p, dp_exact, atol=1e-9)
        np.testing.assert_allclose(grid.D2 @ p, d2p_exact, atol=1e-7)


def test_differentiation_exact_on_polynomial_combination():
    n_max = 6
    grid = LGLCollocationGrid(n_max + 1)
    y = grid.nodes
    # A degree-n_max combination: p(y) = 3 - 2y + y^2 - y^4 + y^6
    p = 3.0 - 2.0 * y + y**2 - y**4 + y**6
    dp_exact = -2.0 + 2.0 * y - 4.0 * y**3 + 6.0 * y**5
    d2p_exact = 2.0 - 12.0 * y**2 + 30.0 * y**4

    np.testing.assert_allclose(grid.D @ p, dp_exact, atol=1e-9)
    np.testing.assert_allclose(grid.D2 @ p, d2p_exact, atol=1e-7)


def test_usable_purely_through_interface_type():
    grid: CollocationGrid = LGLCollocationGrid(DEFAULT_N_COLLOCATION_POINTS)
    assert grid.n_max == DEFAULT_N_COLLOCATION_POINTS - 1
    assert grid.n_collocation_points == DEFAULT_N_COLLOCATION_POINTS
    assert grid.nodes.shape == (DEFAULT_N_COLLOCATION_POINTS,)
    assert grid.weights.shape == (DEFAULT_N_COLLOCATION_POINTS,)
    assert grid.D.shape == (DEFAULT_N_COLLOCATION_POINTS, DEFAULT_N_COLLOCATION_POINTS)
    assert grid.D2.shape == (DEFAULT_N_COLLOCATION_POINTS, DEFAULT_N_COLLOCATION_POINTS)
    assert grid.nodes[0] == pytest.approx(-1.0)
    assert grid.nodes[-1] == pytest.approx(1.0)
