"""
Unit tests for the onion coordinate utilities (Numerics/OnionCoordinate.py).
"""

import numpy as np
import pytest

from config.defaults import DEFAULT_N_COLLOCATION_POINTS
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import (
    advection_coefficient,
    comoving_radius_ratio,
    delta_s,
    delta_s_derivative,
    measure,
)


# --- delta_s: N_init anchor ---------------------------------------------


@pytest.mark.parametrize("alpha", [0.0, 1e-6, 1e-3, 0.1, 1.0, 5.0])
def test_delta_s_at_N_init_equals_log1p_alpha(alpha):
    H_sq = 3.7
    result = delta_s(
        N=2.0, N_init=2.0, H_sq_local=H_sq, H_sq_nl_init=H_sq, alpha=alpha
    )
    assert result == pytest.approx(np.log(1.0 + alpha), abs=1e-14)


def test_delta_s_at_N_init_alpha_zero_is_exactly_zero():
    result = delta_s(N=5.0, N_init=5.0, H_sq_local=1.0, H_sq_nl_init=1.0, alpha=0.0)
    assert result == 0.0


# --- delta_s: full formula away from N_init -----------------------------


@pytest.mark.parametrize("k", [0.0, 0.3, 1.0, 1.5, -0.5])
@pytest.mark.parametrize("alpha", [0.0, 0.05, 2.0])
def test_delta_s_full_formula_exponential_decay(k, alpha):
    N_init = 1.5
    H_sq_nl_init = 4.0
    N = N_init + 3.25

    H_sq_local = H_sq_nl_init * np.exp(-2.0 * k * (N - N_init))

    result = delta_s(
        N=N,
        N_init=N_init,
        H_sq_local=H_sq_local,
        H_sq_nl_init=H_sq_nl_init,
        alpha=alpha,
    )
    expected = np.log(1.0 + alpha) + (1.0 - k) * (N - N_init)
    assert result == pytest.approx(expected, rel=1e-12, abs=1e-12)


# --- delta_s: alpha validation -------------------------------------------


@pytest.mark.parametrize("alpha", [-1e-9, -0.1, -5.0])
def test_delta_s_rejects_negative_alpha(alpha):
    with pytest.raises(ValueError, match="alpha"):
        delta_s(N=1.0, N_init=1.0, H_sq_local=1.0, H_sq_nl_init=1.0, alpha=alpha)


# --- delta_s: N < N_init domain guard ------------------------------------


@pytest.mark.parametrize("N_init", [0.0, 1.5, -3.0])
@pytest.mark.parametrize("shortfall", [1e-9, 0.1, 5.0])
def test_delta_s_rejects_N_less_than_N_init(N_init, shortfall):
    with pytest.raises(ValueError, match="N_init"):
        delta_s(
            N=N_init - shortfall,
            N_init=N_init,
            H_sq_local=1.0,
            H_sq_nl_init=1.0,
            alpha=0.05,
        )


def test_delta_s_accepts_N_equal_to_N_init():
    # N == N_init is the boundary case (Delta_s(N_init) = ln(1+alpha)), not
    # a domain violation.
    result = delta_s(N=2.0, N_init=2.0, H_sq_local=1.0, H_sq_nl_init=1.0, alpha=0.05)
    assert result == pytest.approx(np.log(1.05), abs=1e-14)


# --- delta_s_derivative --------------------------------------------------


@pytest.mark.parametrize("epsilon_core", [-2.0, 0.0, 0.5, 1.0, 1.5, 3.0])
def test_delta_s_derivative(epsilon_core):
    assert delta_s_derivative(epsilon_core) == pytest.approx(1.0 - epsilon_core)


# --- advection_coefficient: endpoint behaviour ---------------------------


@pytest.mark.parametrize("delta_s_N", [0.1, 1.0, 5.0, 20.0])
@pytest.mark.parametrize("epsilon_core", [-1.0, 0.0, 0.5, 2.0])
def test_advection_coefficient_zero_at_y_minus_one(delta_s_N, epsilon_core):
    result = advection_coefficient(-1.0, delta_s_N, epsilon_core)
    assert result == 0.0


@pytest.mark.parametrize("delta_s_N", [0.1, 1.0, 5.0, 20.0])
@pytest.mark.parametrize("epsilon_core", [-1.0, 0.0, 0.5, 2.0])
def test_advection_coefficient_at_y_plus_one(delta_s_N, epsilon_core):
    result = advection_coefficient(1.0, delta_s_N, epsilon_core)
    expected = 2.0 / delta_s_N * (1.0 - epsilon_core)
    assert result == pytest.approx(expected)


# --- measure: endpoint values --------------------------------------------


@pytest.mark.parametrize("delta_s_N", [0.1, 1.0, 5.0, 20.0])
def test_measure_endpoints(delta_s_N):
    assert measure(-1.0, delta_s_N) == pytest.approx(np.exp(1.5 * delta_s_N))
    assert measure(1.0, delta_s_N) == pytest.approx(np.exp(-1.5 * delta_s_N))


# --- comoving_radius_ratio: endpoint consistency -------------------------


@pytest.mark.parametrize("delta_s_N", [0.1, 1.0, 5.0, 20.0])
def test_comoving_radius_ratio_at_y_minus_one_is_exactly_one(delta_s_N):
    assert comoving_radius_ratio(-1.0, delta_s_N) == 1.0


@pytest.mark.parametrize("delta_s_N", [0.1, 1.0, 5.0, 20.0])
def test_comoving_radius_ratio_at_y_plus_one(delta_s_N):
    result = comoving_radius_ratio(1.0, delta_s_N)
    assert result == pytest.approx(np.exp(-delta_s_N))


# --- vectorized input -----------------------------------------------------


def test_vectorized_input_from_lgl_grid():
    grid = LGLCollocationGrid(DEFAULT_N_COLLOCATION_POINTS)
    y = grid.nodes

    delta_s_N = 3.3
    epsilon_core = 0.2

    adv = advection_coefficient(y, delta_s_N, epsilon_core)
    mu = measure(y, delta_s_N)
    r_ratio = comoving_radius_ratio(y, delta_s_N)

    assert adv.shape == y.shape
    assert mu.shape == y.shape
    assert r_ratio.shape == y.shape

    assert adv[0] == 0.0
    assert adv[-1] == pytest.approx(2.0 / delta_s_N * (1.0 - epsilon_core))

    assert mu[0] == pytest.approx(np.exp(1.5 * delta_s_N))
    assert mu[-1] == pytest.approx(np.exp(-1.5 * delta_s_N))

    assert r_ratio[0] == 1.0
    assert r_ratio[-1] == pytest.approx(np.exp(-delta_s_N))
