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
InstantonAdapter -- the base protocol every solver-specific adapter
implements (design doc `.documents/gradient-coupled-plotting/
DESIGN_gradient_coupled_plotting.md`, §3.1-3.2).

FullInstanton, SlowRollInstanton and (eventually) GradientCoupledInstanton
expose the same physics through different attribute vocabularies. A figure
function must never see those solver-specific names; it sees only this
interface, driven entirely by adapter-supplied data (labels, styles,
channel availability) so it never has to branch on which solver produced
the adapter (design's settled decision #2 -- see the P2 prompt's
"Constraints").
"""

import abc
from typing import Optional


class InstantonAdapter(abc.ABC):
    """Solver-agnostic view onto one instanton record (plus, where relevant,
    its paired CompactionFunction) at a single grid point."""

    # Plain identity attributes, set by each subclass's __init__ (design's
    # own pseudocode presents these as attributes, not properties) --
    # deliberately not `abc.abstractmethod`, since an ABC's abstract-method
    # check inspects the *class*, and would still fire even though every
    # subclass assigns these in __init__.
    kind: str
    display_label: str
    line_style: str
    # Matplotlib marker character for this kind, e.g. "o"/"^" -- lets sweep
    # and DOE scatter figures draw one shape per solver identity without
    # ever branching on `.kind` (added in the P2b retrofit alongside
    # `line_style`, same category of addition as `atol`/`rtol`/
    # `channel_label`: needed to preserve visually-distinct overlays while
    # keeping figure functions solver-agnostic).
    marker: str

    def __init__(self, coords: Optional[dict] = None):
        # Grid coordinates (N_init, N_final, delta_Nstar, and for GCI alpha /
        # n_collocation_points) supplied by the CALLER from the query context
        # -- never read off the wrapped object. This is deliberate: under a
        # `_do_not_populate` fetch (or a fetch that simply came up empty) the
        # wrapped object may not exist at all, but the coordinates that were
        # queried are still known and must still be reportable.
        self._coords = dict(coords) if coords is not None else {}

    @property
    def coords(self) -> dict:
        return dict(self._coords)

    @property
    @abc.abstractmethod
    def available(self) -> bool:
        """True if the wrapped record has been persisted to the datastore."""

    @property
    @abc.abstractmethod
    def failure(self) -> bool:
        """True if the wrapped record exists but its solve failed."""

    @property
    @abc.abstractmethod
    def store_id(self) -> Optional[int]:
        ...

    @property
    @abc.abstractmethod
    def timestamp(self):
        ...

    @property
    @abc.abstractmethod
    def tolerances(self) -> tuple:
        """(atol, rtol) as plain floats, or (None, None) if unavailable."""

    @property
    def atol(self):
        """Flat convenience scalar alongside `tolerances`, added specifically
        so `plotting.provenance._provenance_footer`'s existing
        `getattr(obj, "atol", None)` introspection keeps working unchanged
        when called with an adapter instead of a raw compute-target object."""
        return self.tolerances[0]

    @property
    def rtol(self):
        return self.tolerances[1]

    @abc.abstractmethod
    def has_channel(self, name: str) -> bool:
        """name in {"phi", "velocity", "rfield", "rmom", "P1", "P2",
        "noise_field", "noise_mom", ...} -- whichever channels this kind of
        solver can, in principle, expose."""

    def is_spatial(self) -> bool:
        """True only for a spatial (GCI) adapter; overridden there."""
        return False

    @abc.abstractmethod
    def channel_label(self, channel: str) -> Optional[str]:
        """LaTeX symbol (no surrounding $...$? -- see subclasses) for a
        channel, e.g. r"$\\varphi_1$" for FullInstanton's "phi" channel vs
        r"$\\varphi$" for SlowRollInstanton's. Lets figure functions build
        legend labels purely from adapter-supplied data, without branching
        on which kind of adapter they were handed."""

    @abc.abstractmethod
    def time_history(self, channel: str):
        """Returns (N, values) as numpy arrays, or None if the channel is
        absent or no dense sample data is available."""

    @abc.abstractmethod
    def noise_history(self) -> Optional[dict]:
        """{"N", "sigma_field", "sigma_mom"} numpy arrays (NaN where a
        channel is absent), or None if no dense sample data is available."""

    @abc.abstractmethod
    def radial_profile(self) -> Optional[dict]:
        """{"r_Mpc", "zeta", "C", "C_bar"} numpy arrays, or None if no
        compaction-function profile is available for this adapter's path."""

    @abc.abstractmethod
    def scalars(self) -> dict:
        """A flat dict with a fixed, solver-agnostic key vocabulary:
        msr_action, C_peak, C_bar_peak, C_min, compensated, type_II,
        r_max_Mpc, r_peak_Mpc, M_max_solar, M_peak_solar, V_end_downflow,
        N_end_downflow, C_threshold, noise_field_{min,mean,max},
        noise_mom_{min,mean,max}. Values are None where not available."""

    @abc.abstractmethod
    def diagnostics(self) -> Optional[dict]:
        ...
