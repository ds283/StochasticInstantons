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

from typing import Optional

import numpy as np

from plotting.adapters.base import InstantonAdapter

# No "velocity"/"P2" channel: the slow-roll approximation slaves the field
# velocity to phi algebraically (pi = -V'(phi) / 3H^2) and P2 = 0 identically,
# so there is nothing independent to plot -- see design §3.1's table.
_CHANNELS = ("phi", "P1")

_CHANNEL_LABELS = {
    "phi": r"$\varphi$",
    "P1": r"$P_1$",
}


class SlowRollInstantonAdapter(InstantonAdapter):
    """Adapts a `SlowRollInstanton` (plus, optionally, its paired
    `CompactionFunction`) onto the solver-agnostic `InstantonAdapter`
    protocol (design §3.1-3.2's "slow-roll" row)."""

    kind = "slow-roll"
    line_style = "--"

    def __init__(self, sri, cf=None, coords: Optional[dict] = None):
        super().__init__(coords)
        self._sri = sri
        self._cf = cf
        self.display_label = "SR"

    @property
    def available(self) -> bool:
        return self._sri is not None and self._sri.available

    @property
    def failure(self) -> bool:
        return self._sri is not None and self._sri.failure

    @property
    def store_id(self) -> Optional[int]:
        return (
            self._sri.store_id
            if (self._sri is not None and self._sri.available)
            else None
        )

    @property
    def timestamp(self):
        return self._sri.timestamp if self._sri is not None else None

    @property
    def tolerances(self) -> tuple:
        if self._sri is None:
            return (None, None)
        atol_obj = getattr(self._sri, "_atol", None)
        rtol_obj = getattr(self._sri, "_rtol", None)
        return (
            atol_obj.tol if atol_obj is not None else None,
            rtol_obj.tol if rtol_obj is not None else None,
        )

    def has_channel(self, name: str) -> bool:
        return name in _CHANNELS

    def channel_label(self, channel: str) -> Optional[str]:
        return _CHANNEL_LABELS.get(channel)

    def time_history(self, channel: str):
        if not self.has_channel(channel):
            return None
        if self._sri is None or not self._sri.values:
            return None
        vals = self._sri.values
        N = np.array([v.N.N for v in vals])
        if channel == "phi":
            y = np.array([v.phi for v in vals])
        elif channel == "P1":
            y = np.array([v.P1 for v in vals])
        else:  # pragma: no cover -- guarded by has_channel above
            return None
        return N, y

    def noise_history(self) -> Optional[dict]:
        if self._sri is None or not self._sri.values:
            return None
        profile = self._sri.noise_profile_arrays()
        if profile is None:
            return None
        return {
            "N": profile["N"],
            "sigma_field": profile["sigma_phi1"],
            "sigma_mom": profile["sigma_phi2"],
        }

    def radial_profile(self) -> Optional[dict]:
        if self._cf is None or not self._cf.available or self._cf.failure:
            return None
        vals = self._cf.slow_roll_values
        if not vals:
            return None
        units = self._units()
        Mpc = units.Mpc
        return {
            "r_Mpc": np.array([v.r / Mpc for v in vals]),
            "zeta": np.array([v.zeta for v in vals]),
            "C": np.array([v.C for v in vals]),
            "C_bar": np.array([v.C_bar for v in vals]),
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
        if self._sri is not None and self._sri.available:
            result["msr_action"] = self._sri.msr_action
            result["noise_field_min"] = self._sri.noise_phi1_min
            result["noise_field_mean"] = self._sri.noise_phi1_mean
            result["noise_field_max"] = self._sri.noise_phi1_max
            result["noise_mom_min"] = self._sri.noise_phi2_min
            result["noise_mom_mean"] = self._sri.noise_phi2_mean
            result["noise_mom_max"] = self._sri.noise_phi2_max
        if self._cf is not None and self._cf.available and not self._cf.failure:
            result["C_peak"] = self._cf.C_peak_slow_roll
            result["C_bar_peak"] = self._cf.C_bar_peak_slow_roll
            result["C_min"] = self._cf.C_min_slow_roll
            result["compensated"] = self._cf.compensated_slow_roll
            result["type_II"] = self._cf.type_II_slow_roll
            result["V_end_downflow"] = self._cf.V_end_downflow_slow_roll
            result["N_end_downflow"] = self._cf.N_end_downflow_slow_roll
            result["C_threshold"] = self._cf.C_threshold
            units = self._units()
            r_max = self._cf.r_max_slow_roll
            r_peak = self._cf.r_peak_slow_roll
            M_max = self._cf.M_max_slow_roll
            M_peak = self._cf.M_peak_slow_roll
            result["r_max_Mpc"] = r_max / units.Mpc if r_max is not None else None
            result["r_peak_Mpc"] = r_peak / units.Mpc if r_peak is not None else None
            result["M_max_solar"] = M_max / units.SolarMass if M_max is not None else None
            result["M_peak_solar"] = M_peak / units.SolarMass if M_peak is not None else None
        return result

    def diagnostics(self) -> Optional[dict]:
        return self._sri.diagnostics if self._sri is not None else None

    def _units(self):
        """See `FullInstantonAdapter._units` -- same access pattern."""
        if self._sri is not None:
            return self._sri._trajectory.units
        if self._cf is not None:
            return self._cf._trajectory.units
        return None
