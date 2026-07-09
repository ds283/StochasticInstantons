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
`GradientCoupledAdapter` -- adapts a `GradientCoupledInstanton` onto the
solver-agnostic `InstantonAdapter` protocol (design doc
`.documents/gradient-coupled-plotting/DESIGN_gradient_coupled_plotting.md`,
§3.1-3.2's "gradient-coupled" row, §3.3's spatial extension).

Every method here is a PURE READ of already-persisted parity data (design
§7.5's consequence of the U1-U3 upstream work): `scalars()` and
`radial_profile()` read the eleven parity properties / the `.profile` list
straight off the wrapped `GradientCoupledInstanton`, with no reconstruction,
no fallback computation, and no physics performed in this file. If a value
is `None` on the wrapped object, the adapter reports `None`.

Design §3.3 sketches the spatial capability (`y_nodes`, `N_grid`,
`field_2d`, `derived_at_time`) as a separate `SpatialAdapter(InstantonAdapter)`
subclass. This module folds those methods directly into
`GradientCoupledAdapter` instead (the P4 prompt's own permitted alternative),
because the P4 acceptance test requires `field_2d`/`derived_at_time` to
raise `RuntimeError` -- not `AttributeError` -- when called on a
`scalars`/`profile`-fidelity instance. A subclass relationship can't do
that: a `scalars`-fidelity adapter would simply never be an instance of a
spatial subclass, so the call would fail with `AttributeError` before ever
reaching a fidelity check. Folding the methods into one class and gating
each one on `self._fidelity` (or, for `field_2d`/`derived_at_time`, on
`self._gci.values` being non-empty, mirroring the compute target's own
guard) makes the raise-not-silently-absent behaviour uniform regardless of
which fidelity tier constructed the instance. `SpatialAdapter` is kept as a
plain alias below for the class name design §3.3 and later prompts (P5a,
P5b, P7) use.
"""

from typing import List, Optional

import numpy as np

from Numerics.LGLCollocation import LGLCollocationGrid
from plotting.adapters.base import InstantonAdapter

# GCI's own field vocabulary (GradientCoupledInstantonValue's properties),
# distinct from FullInstanton's phi1/phi2/P1/P2 naming -- see design §3.1's
# table. "velocity" is time_history's channel name for the field's momentum
# pi (the direct analogue of FullInstanton's "velocity"/phi2 channel);
# field_2d uses the raw attribute names ("pi", not "velocity") per design
# §3.3's own pseudocode.
_TIME_HISTORY_CHANNELS = ("phi", "velocity", "rfield", "rmom")
_TIME_HISTORY_ATTR = {
    "phi": "phi",
    "velocity": "pi",
    "rfield": "rfield",
    "rmom": "rmom",
}

_CHANNEL_LABELS = {
    "phi": r"$\varphi$",
    "velocity": r"$\pi$",
    "rfield": r"$r_\varphi$",
    "rmom": r"$r_\pi$",
}

_SPATIAL_CHANNELS = ("phi", "pi", "rfield", "rmom")

_FIDELITY_TIERS = ("scalars", "profile", "dense")


class GradientCoupledAdapter(InstantonAdapter):
    """Adapts a `GradientCoupledInstanton` onto the solver-agnostic
    `InstantonAdapter` protocol, plus the spatial `(y, N)` extension (design
    §3.3), folded into this one class -- see module docstring for why."""

    kind = "gradient-coupled"
    line_style = ":"
    marker = "D"

    def __init__(
        self,
        gci,
        coords: Optional[dict] = None,
        fidelity: str = None,
    ):
        """`fidelity` -- one of "scalars"/"profile"/"dense", reflecting which
        of the three P3 fetch modes produced `gci`. Required, not inferred:
        an empty `.profile` is ambiguous between "not fetched" and
        "genuinely empty", so only the caller (which knows which fetch it
        issued) can supply this reliably (design §4.1)."""
        super().__init__(coords)
        if fidelity not in _FIDELITY_TIERS:
            raise ValueError(
                f"GradientCoupledAdapter: fidelity must be one of "
                f"{_FIDELITY_TIERS}, got {fidelity!r}"
            )
        self._gci = gci
        self._fidelity = fidelity

        # display_label reads n/alpha from coords (query-context, never off
        # the wrapped object -- same rule as the rest of `coords`), so it is
        # reportable even when `gci` is None or `_do_not_populate`-fetched.
        n = self._coords.get("n_collocation_points")
        alpha = self._coords.get("alpha")
        if n is not None and alpha is not None:
            self.display_label = f"GCI (n={int(n)}, α={float(alpha):.3g})"
        else:
            self.display_label = "GCI"

    @property
    def available(self) -> bool:
        return self._gci is not None and self._gci.available

    @property
    def failure(self) -> bool:
        return self._gci is not None and self._gci.failure

    @property
    def store_id(self) -> Optional[int]:
        return self._gci.store_id if (self._gci is not None and self._gci.available) else None

    @property
    def timestamp(self):
        return self._gci.timestamp if self._gci is not None else None

    @property
    def tolerances(self) -> tuple:
        if self._gci is None:
            return (None, None)
        atol_obj = getattr(self._gci, "_atol", None)
        rtol_obj = getattr(self._gci, "_rtol", None)
        return (
            atol_obj.tol if atol_obj is not None else None,
            rtol_obj.tol if rtol_obj is not None else None,
        )

    def has_channel(self, name: str) -> bool:
        return name in _TIME_HISTORY_CHANNELS

    def is_spatial(self) -> bool:
        return self._fidelity == "dense"

    def channel_label(self, channel: str) -> Optional[str]:
        return _CHANNEL_LABELS.get(channel)

    def time_history(self, channel: str):
        """Reads the CORE node (y=+1, the last entry of each per-sample
        row) -- the direct analogue of FullInstanton's homogeneous field.
        Returns None if `.values` is empty (fidelity != "dense"): a
        capability gap, not a failure, so it must not raise."""
        if not self.has_channel(channel):
            return None
        if self._gci is None or not self._gci.values:
            return None
        vals = self._gci.values
        N = np.array([v.N.N for v in vals])
        attr = _TIME_HISTORY_ATTR[channel]
        y = np.array([getattr(v, attr)[-1] for v in vals])
        return N, y

    def noise_history(self) -> Optional[dict]:
        """GCI persists only scalar noise summary statistics
        (`noise_field_min/mean/max`, `noise_mom_min/mean/max`) -- never a
        per-N sigma(N) array like FullInstanton's `noise_profile_arrays()`
        (building one honestly would mean re-deriving the diluted diffusion
        coefficients here, which is exactly the "no physics in the adapter"
        anti-pattern this file must not commit). So this method's contract
        is necessarily thinner than the base protocol's per-N
        `{"N", "sigma_field", "sigma_mom"}` array shape, and rather than
        paper over that by forcing the summary scalars into a fake
        single/triple-point "history" that `plotting/figures/noise.py`
        would plot as if it were real time-resolved data, it returns `None`
        uniformly -- the same "capability gap, not a failure" contract
        `time_history()` uses above. `plotting/figures/noise.py`'s adapter
        loop already treats a `None` history as "this adapter has nothing
        to plot here" and skips it, so a GCI adapter in the list is dropped
        from the noise-history panels without error. The summary scalars
        themselves are NOT lost -- they are exposed via `scalars()`'s
        `noise_field_*`/`noise_mom_*` keys, the same keys FullInstanton/
        SlowRollInstanton already populate there, so DOE/sweep figures see
        them uniformly across all three kinds."""
        return None

    def radial_profile(self) -> Optional[dict]:
        if self._gci is None or not self._gci.available or self._gci.failure:
            return None
        profile = self._gci.profile
        if not profile:
            return None
        units = self._units()
        Mpc = units.Mpc
        return {
            "r_Mpc": np.array([p.r_phys / Mpc for p in profile]),
            "zeta": np.array([p.zeta for p in profile]),
            "C": np.array([p.C for p in profile]),
            "C_bar": np.array([p.C_bar for p in profile]),
        }

    def scalars(self) -> dict:
        result = {
            "msr_action": None,
            "C_peak": None,
            "C_bar_peak": None,
            "C_min": None,
            "compensated": None,
            "type_II": None,
            "r_max_Mpc": None,
            "r_peak_Mpc": None,
            "M_max_solar": None,
            "M_peak_solar": None,
            "V_end_downflow": None,
            "N_end_downflow": None,
            "C_threshold": None,
            "noise_field_min": None,
            "noise_field_mean": None,
            "noise_field_max": None,
            "noise_mom_min": None,
            "noise_mom_mean": None,
            "noise_mom_max": None,
        }
        if self._gci is None or not self._gci.available or self._gci.failure:
            return result

        result["msr_action"] = self._gci.msr_action
        result["C_peak"] = self._gci.C_peak
        result["C_bar_peak"] = self._gci.C_bar_peak
        result["C_min"] = self._gci.C_min
        result["compensated"] = self._gci.compensated
        result["type_II"] = self._gci.type_II
        result["V_end_downflow"] = self._gci.V_end_downflow
        result["N_end_downflow"] = self._gci.N_end_downflow
        result["noise_field_min"] = self._gci.noise_field_min
        result["noise_field_mean"] = self._gci.noise_field_mean
        result["noise_field_max"] = self._gci.noise_field_max
        result["noise_mom_min"] = self._gci.noise_mom_min
        result["noise_mom_mean"] = self._gci.noise_mom_mean
        result["noise_mom_max"] = self._gci.noise_mom_max

        units = self._units()
        # C_threshold is a fixed module constant on the compute target (not
        # a persisted column -- see that module's own comment on why), so
        # read it from there rather than hard-coding a second copy of the
        # same number here.
        from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
            _C_THRESHOLD,
        )

        result["C_threshold"] = _C_THRESHOLD
        r_max = self._gci.r_max
        r_peak = self._gci.r_peak
        M_max = self._gci.M_max
        M_peak = self._gci.M_peak
        if units is not None:
            result["r_max_Mpc"] = r_max / units.Mpc if r_max is not None else None
            result["r_peak_Mpc"] = r_peak / units.Mpc if r_peak is not None else None
            result["M_max_solar"] = M_max / units.SolarMass if M_max is not None else None
            result["M_peak_solar"] = M_peak / units.SolarMass if M_peak is not None else None
        return result

    def diagnostics(self) -> Optional[dict]:
        return self._gci.diagnostics if self._gci is not None else None

    # ── spatial extension (design §3.3), folded in -- see module docstring ──

    @property
    def y_nodes(self) -> np.ndarray:
        """LGL collocation nodes (-1..+1), built fresh from
        `n_collocation_points` -- cheap and deterministic given that one
        integer, so (per design §3.3) this does NOT require a dense fetch;
        it works at every fidelity tier as long as `coords` carries
        `n_collocation_points`."""
        n = self._coords.get("n_collocation_points")
        if n is None and self._gci is not None:
            n = self._gci.n_collocation_points_value
        return LGLCollocationGrid(int(n)).nodes

    @property
    def N_grid(self) -> np.ndarray:
        """Stored sample N's; empty if `.values` is empty (non-dense
        fidelity)."""
        if self._gci is None:
            return np.array([])
        return np.array([v.N.N for v in self._gci.values])

    def field_2d(self, name: str):
        """`(y_nodes, N_grid, Z[N, y])` for `name in {"phi", "pi", "rfield",
        "rmom"}`, built directly from `.values` (there is no `field_2d` on
        the compute target itself -- this is adapter-level). MUST raise, not
        return `None`, when `.values` is empty -- design §3.3's own guard
        pattern; figure code is required to gate on `is_spatial()` before
        calling this, not rely on catching the raise."""
        if name not in _SPATIAL_CHANNELS:
            raise ValueError(
                f"GradientCoupledAdapter.field_2d: unknown channel {name!r}, "
                f"expected one of {_SPATIAL_CHANNELS}"
            )
        if self._gci is None or not self._gci.values:
            raise RuntimeError(
                f"GradientCoupledAdapter.field_2d({name!r}): requires "
                f"'dense' fidelity (a full fetch with store_full_values=True "
                f"that populated `.values`); this adapter is "
                f"fidelity={self._fidelity!r}."
            )
        vals = self._gci.values
        N_grid = np.array([v.N.N for v in vals])
        Z = np.array([getattr(v, name) for v in vals])
        return self.y_nodes, N_grid, Z

    def derived_at_time(self, N_query) -> dict:
        """Thin wrapper over `GradientCoupledInstanton.zeta_C_r_at_time`;
        that method's own `RuntimeError` (raised when `._values` is empty)
        propagates unchanged -- not caught, not re-raised, not swallowed."""
        if self._gci is None:
            raise RuntimeError(
                "GradientCoupledAdapter.derived_at_time: no "
                "GradientCoupledInstanton object is available for this "
                "adapter."
            )
        return self._gci.zeta_C_r_at_time(N_query)

    def _units(self):
        """Working-unit-system handle -- same `obj._trajectory.units`
        access pattern as `FullInstantonAdapter._units`/
        `SlowRollInstantonAdapter._units` (`.claude/rules/datastore-units.md`)."""
        if self._gci is not None:
            return self._gci._trajectory.units
        return None


# Design §3.3 names the spatial-capable adapter "SpatialAdapter"; kept as an
# alias to the single folded class (see module docstring) so later prompts
# (P5a, P5b, P7) that import `SpatialAdapter` by that name get an adapter
# whose field_2d/derived_at_time raise RuntimeError -- not AttributeError --
# at every fidelity tier, including scalars/profile.
SpatialAdapter = GradientCoupledAdapter
