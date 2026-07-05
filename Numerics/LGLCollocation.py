# (c) University of Sussex 2026
# Created by David Seery
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Legendre-Gauss-Lobatto (LGL) collocation grids.

Standalone numerical module: nodes, quadrature weights, and first-/second-
derivative differentiation matrices on [-1, 1]. No dependence on Datastore,
Ray, or any other part of this codebase -- plain numpy in, plain numpy out.
"""

from abc import ABC, abstractmethod

import numpy as np
from scipy.linalg import eigh_tridiagonal
from scipy.special import eval_legendre


class CollocationGrid(ABC):
    """
    Abstract interface for a fixed collocation grid on [-1, 1]: node
    positions, quadrature weights, and differentiation matrices.
    """

    @property
    @abstractmethod
    def n_max(self) -> int:
        """Polynomial degree (grid has n_max + 1 nodes)."""

    @property
    @abstractmethod
    def n_collocation_points(self) -> int:
        """Number of grid nodes = n_max + 1."""

    @property
    @abstractmethod
    def nodes(self) -> np.ndarray:
        """The y_j, shape (n_collocation_points,), ascending, y_0=-1, y_{n_max}=+1."""

    @property
    @abstractmethod
    def weights(self) -> np.ndarray:
        """Quadrature weights w_j, shape (n_collocation_points,)."""

    @property
    @abstractmethod
    def D(self) -> np.ndarray:
        """First-derivative differentiation matrix, shape (n_collocation_points, n_collocation_points)."""

    @property
    @abstractmethod
    def D2(self) -> np.ndarray:
        """Second-derivative differentiation matrix, same shape."""


class LGLCollocationGrid(CollocationGrid):
    """
    Legendre-Gauss-Lobatto collocation grid of degree n_max = n_collocation_points - 1.

    Interior nodes are the roots of P_{n_max}'(y) (the derivative of the
    Legendre polynomial of degree n_max), found as the eigenvalues of the
    symmetric tridiagonal Jacobi matrix for the Jacobi weight (1-y^2)
    (Golub-Welsch construction); the endpoints y=-1, y=+1 are exact. Weights
    and differentiation matrices follow the standard closed-form LGL
    expressions in terms of P_{n_max} evaluated at the nodes.

    Everything is precomputed once in __init__; property access is O(1).
    """

    def __init__(self, n_collocation_points: int):
        if not isinstance(n_collocation_points, (int, np.integer)) or isinstance(
            n_collocation_points, bool
        ):
            raise ValueError(
                f"LGLCollocationGrid: n_collocation_points must be an integer, "
                f"got {n_collocation_points!r} of type "
                f"{type(n_collocation_points).__name__}"
            )
        if n_collocation_points < 2:
            raise ValueError(
                f"LGLCollocationGrid: n_collocation_points must be >= 2 "
                f"(need at least the two endpoints), got {n_collocation_points}"
            )

        self._n_collocation_points = int(n_collocation_points)
        self._n_max = self._n_collocation_points - 1

        self._nodes = self._build_nodes(self._n_max)
        self._weights = self._build_weights(self._n_max, self._nodes)
        self._D = self._build_D(self._n_max, self._nodes)
        self._D2 = self._D @ self._D

    @staticmethod
    def _build_nodes(n_max: int) -> np.ndarray:
        """
        Interior LGL nodes are the roots of P_{n_max}'(y), proportional to the
        Jacobi polynomial P^{(1,1)}_{n_max-1}(y). Its roots are the eigenvalues
        of the (n_max-1)x(n_max-1) symmetric tridiagonal Jacobi matrix built
        from the standard monic three-term recurrence coefficients for
        Jacobi(alpha=1, beta=1): zero diagonal (symmetric weight), off-diagonal
        b_n = sqrt(n(n+2) / [(2n+3)(2n+1)]) for n=1,...,m-1.
        """
        m = n_max - 1
        if m <= 0:
            # n_max == 1: no interior nodes, just the two endpoints.
            return np.array([-1.0, 1.0])

        diag = np.zeros(m)
        n = np.arange(1, m)
        off_diag = np.sqrt(n * (n + 2) / ((2 * n + 3) * (2 * n + 1)))

        interior, _ = eigh_tridiagonal(diag, off_diag)
        interior.sort()

        return np.concatenate(([-1.0], interior, [1.0]))

    @staticmethod
    def _build_weights(n_max: int, nodes: np.ndarray) -> np.ndarray:
        """w_j = 2 / [n_max(n_max+1) P_{n_max}(y_j)^2]."""
        Pn = eval_legendre(n_max, nodes)
        return 2.0 / (n_max * (n_max + 1) * Pn**2)

    @staticmethod
    def _build_D(n_max: int, nodes: np.ndarray) -> np.ndarray:
        """
        D_ij = P_{n_max}(y_i) / P_{n_max}(y_j) * 1/(y_i - y_j), i != j; zero on
        the interior diagonal; +/- n_max(n_max+1)/4 at the y=+1/-1 endpoints
        respectively.
        """
        Pn = eval_legendre(n_max, nodes)
        n_points = n_max + 1

        with np.errstate(divide="ignore", invalid="ignore"):
            D = (Pn[:, None] / Pn[None, :]) / (nodes[:, None] - nodes[None, :])
        np.fill_diagonal(D, 0.0)

        D[0, 0] = -n_max * (n_max + 1) / 4.0
        D[n_points - 1, n_points - 1] = n_max * (n_max + 1) / 4.0

        return D

    @property
    def n_max(self) -> int:
        return self._n_max

    @property
    def n_collocation_points(self) -> int:
        return self._n_collocation_points

    @property
    def nodes(self) -> np.ndarray:
        return self._nodes

    @property
    def weights(self) -> np.ndarray:
        return self._weights

    @property
    def D(self) -> np.ndarray:
        return self._D

    @property
    def D2(self) -> np.ndarray:
        return self._D2
