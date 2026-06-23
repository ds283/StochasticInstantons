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

import numpy as np
from scipy.interpolate import make_interp_spline


class _SplineDerivativeWrapper:
    """
    Chain-rule-corrected derivative of a SplineWrapper.

    Returned by SplineWrapper.derivative(). Computes dy/dx in original
    coordinates, accounting for both the x- and y-coordinate transforms.

    dy/dx = T_y_inv'(g(T_x(x))) · g'(T_x(x)) · T_x'(x)

    where g is the underlying raw B-spline and g' is its derivative.
    """

    def __init__(self, raw_spline, x_transform: str, y_transform: str):
        self._raw_spline = raw_spline
        self._raw_deriv = raw_spline.derivative()
        self._x_transform = x_transform
        self._y_transform = y_transform

    def __call__(self, x):
        scalar = np.ndim(x) == 0
        x_arr = np.asarray(x, dtype=float)
        x_t = SplineWrapper._apply(x_arr, self._x_transform)
        gp = self._raw_deriv(x_t)

        # dy/dx = (d T_y_inv / dg) · g'(x_t) · (d T_x / dx)
        #
        # Combine x- and y-transform factors into a single expression for
        # each of the combinations actually used in the codebase.

        if self._x_transform == 'linear':
            if self._y_transform == 'linear':
                result = gp
            elif self._y_transform == 'sinh':
                g = self._raw_spline(x_t)
                result = np.cosh(g) * gp
            elif self._y_transform == 'log':
                g = self._raw_spline(x_t)
                result = np.exp(g) * gp
            else:
                raise NotImplementedError(
                    f"derivative() not implemented for x_transform='linear', "
                    f"y_transform='{self._y_transform}'"
                )

        elif self._x_transform == 'log':
            if self._y_transform == 'linear':
                # dy/dr = g'(log r) / r
                result = gp / x_arr
            elif self._y_transform == 'sinh':
                g = self._raw_spline(x_t)
                result = np.cosh(g) * gp / x_arr
            elif self._y_transform == 'log':
                g = self._raw_spline(x_t)
                result = np.exp(g) * gp / x_arr
            else:
                raise NotImplementedError(
                    f"derivative() not implemented for x_transform='log', "
                    f"y_transform='{self._y_transform}'"
                )

        elif self._x_transform == 'sinh':
            if self._y_transform == 'linear':
                result = gp / np.sqrt(x_arr ** 2 + 1.0)
            else:
                raise NotImplementedError(
                    f"derivative() not implemented for x_transform='sinh', "
                    f"y_transform='{self._y_transform}'"
                )

        else:
            raise NotImplementedError(
                f"derivative() not implemented for x_transform='{self._x_transform}'"
            )

        return float(result) if scalar else result


class SplineWrapper:
    """
    Cubic B-spline with optional coordinate transforms on x and/or y.

    Transforms applied before building the spline distribute sample nodes
    more evenly across the domain, improving accuracy when coordinates span
    a large dynamic range.

    Supported transforms
    --------------------
    'linear' : identity (no transformation)
    'log'    : forward log(x), inverse exp — requires strictly positive values
    'sinh'   : forward arcsinh(x), inverse sinh — handles either sign with
               logarithmic spacing for large |x| and linear spacing near zero

    Parameters
    ----------
    x, y        : array-like, the sample knots in original coordinates
    x_transform : transform applied to the x coordinate before splining
    y_transform : transform applied to the y coordinate before splining
    k           : B-spline degree (default 3 = cubic)

    Root-finding in transformed coordinates
    ----------------------------------------
    To root-find f(x) = c with better numerical conditioning, work in the
    transformed space where the underlying spline is built:

        c_t   = wrapper.transform_y(c)
        lo_t  = wrapper.transform_x(x_lo)
        hi_t  = wrapper.transform_x(x_hi)
        root_t = brentq(lambda xt: wrapper.raw(xt) - c_t, lo_t, hi_t)
        x_root = wrapper.invert_x(root_t)
    """

    def __init__(
        self,
        x,
        y,
        x_transform: str = 'linear',
        y_transform: str = 'linear',
        k: int = 3,
        bc_type=None,
    ):
        _valid = {'linear', 'log', 'sinh'}
        if x_transform not in _valid:
            raise ValueError(f"x_transform must be one of {_valid}, got '{x_transform}'")
        if y_transform not in _valid:
            raise ValueError(f"y_transform must be one of {_valid}, got '{y_transform}'")

        self._x_transform = x_transform
        self._y_transform = y_transform

        x_arr = np.asarray(x, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        x_t = self._apply(x_arr, x_transform)
        y_t = self._apply(y_arr, y_transform)
        self._spline = make_interp_spline(x_t, y_t, k=k, bc_type=bc_type)

    # ── Public evaluation ────────────────────────────────────────────────────

    def __call__(self, x):
        """Evaluate at x in original coordinates, returning y in original coordinates."""
        scalar = np.ndim(x) == 0
        x_arr = np.asarray(x, dtype=float)
        x_t = self._apply(x_arr, self._x_transform)
        y_t = self._spline(x_t)
        y = self._invert(y_t, self._y_transform)
        return float(y) if scalar else y

    def raw(self, x_t):
        """Evaluate the underlying spline at pre-transformed x_t.

        Returns the pre-inverse-transformed y_t (both in transformed space).
        Used with transform_x / transform_y / invert_x for root-finding in
        transformed coordinates — see class docstring.
        """
        scalar = np.ndim(x_t) == 0
        x_t_arr = np.asarray(x_t, dtype=float)
        y_t = self._spline(x_t_arr)
        return float(y_t) if scalar else y_t

    def derivative(self) -> _SplineDerivativeWrapper:
        """Return a callable giving dy/dx in original coordinates (chain-rule corrected)."""
        return _SplineDerivativeWrapper(self._spline, self._x_transform, self._y_transform)

    # ── Transform utilities for root-finding setup ────────────────────────────

    def transform_x(self, x):
        """Apply the x-transform to x (for computing brentq search bounds)."""
        scalar = np.ndim(x) == 0
        result = self._apply(np.asarray(x, dtype=float), self._x_transform)
        return float(result) if scalar else result

    def transform_y(self, y):
        """Apply the y-transform to y (for computing brentq target values)."""
        scalar = np.ndim(y) == 0
        result = self._apply(np.asarray(y, dtype=float), self._y_transform)
        return float(result) if scalar else result

    def invert_x(self, x_t):
        """Invert the x-transform (for converting a root found in transformed space back)."""
        scalar = np.ndim(x_t) == 0
        result = self._invert(np.asarray(x_t, dtype=float), self._x_transform)
        return float(result) if scalar else result

    # ── Internal helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _apply(arr: np.ndarray, transform: str) -> np.ndarray:
        if transform == 'linear':
            return arr
        elif transform == 'log':
            return np.log(arr)
        elif transform == 'sinh':
            return np.arcsinh(arr)
        else:
            raise ValueError(f"Unknown transform '{transform}'")

    @staticmethod
    def _invert(arr: np.ndarray, transform: str) -> np.ndarray:
        if transform == 'linear':
            return arr
        elif transform == 'log':
            return np.exp(arr)
        elif transform == 'sinh':
            return np.sinh(arr)
        else:
            raise ValueError(f"Unknown transform '{transform}'")
