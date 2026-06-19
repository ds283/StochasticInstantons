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

from math import exp, log
from math import pi as PI
from typing import List, Optional

import ray
from ray import ObjectRef

from Datastore.object import DatastoreObject
from InflationConcepts.delta_Nstar import delta_Nstar
from MetadataConcepts.store_tag import store_tag
from MetadataConcepts.tolerance import tolerance


def ln_k_phys_Mpc(
    N_before_end: float,
    V_k: float,
    epsilon_k: float,
    V_end_downflow: float,
    units,
    cosmo,
) -> float:
    """
    Log of the physical wavenumber k in working_units^-1 for a mode that exits
    the Hubble radius N_before_end e-folds before the end of inflation.

    Implements Leach & Liddle (astro-ph/0305263) Eq. (2) with instantaneous
    reheating.  The result is shifted by -log(Mpc) relative to the Mpc^{-1}
    convention so that r = 2π/exp(lnk) is in working units, not in Mpc.

    All dimensional arguments must be in the working unit system.
    """
    Mp = units.PlanckMass
    Mpc = units.Mpc
    T_CMB = cosmo.T_CMB_Kelvin * units.Kelvin

    return (
        -N_before_end
        + log(Mpc * Mp)
        + log(T_CMB / Mp)
        + 0.25 * log(PI**2 / 135.0)
        + 0.25 * log(V_k / (V_end_downflow * (1.0 - epsilon_k / 3.0)))
        - log(Mpc)
    )


def _compute_instanton_path(
    instanton_obj,
    is_slow_roll: bool,
    traj,
    potential,
    units,
    cosmo,
    C_threshold: float,
    C_bar_threshold: float,
    atol: float,
    rtol: float,
    label: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    Compute zeta(r), C(r), C_bar(r) for a single instanton path.

    Returns a result dict with keys: failure, r, zeta, C, C_bar, r_max_C,
    r_max_C_bar, M_C, M_C_bar, C_max, V_end_downflow, N_end_downflow, diagnostics.
    """
    import numpy as np
    from scipy.interpolate import CubicSpline
    from scipy.optimize import brentq

    from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory

    Mp = units.PlanckMass
    N_end_traj = traj.N_end
    N_init_val = float(instanton_obj.N_init_value)
    N_total = (
        float(instanton_obj._N_total)
        if hasattr(instanton_obj, "_N_total")
        else (
            float(instanton_obj._N_init)
            - float(instanton_obj._N_final)
            + float(instanton_obj._delta_Nstar)
        )
    )

    values = instanton_obj.values
    if not values:
        return {"failure": True, "diagnostics": {"reason": "no sample values"}}

    # Build per-sample arrays
    N_inst_arr = np.array([float(v.N.N) for v in values])

    if is_slow_roll:
        phi1_arr = np.array([v.phi for v in values])
        phi2_arr = np.array(
            [
                -potential.dV_dphi(v.phi) / (3.0 * potential.H_sq(v.phi, 0.0))
                for v in values
            ]
        )
    else:
        phi1_arr = np.array([v.phi1 for v in values])
        phi2_arr = np.array([v.phi2 for v in values])

    # ── Step A: downflow from instanton endpoint ──────────────────────────
    sol_down, _, _ = integrate_noiseless_trajectory(
        float(phi1_arr[-1]), float(phi2_arr[-1]), potential, atol, rtol, label=label, verbose=verbose
    )
    if sol_down is None or len(sol_down.t_events[0]) == 0:
        return {
            "failure": True,
            "diagnostics": {"reason": "downflow integration failed"},
        }

    N_end_downflow = float(sol_down.t_events[0][0])
    phi_end_downflow = float(sol_down.y_events[0][0][0])
    V_end_downflow = potential.V(phi_end_downflow)

    # ── Step B: zeta at each sample point ────────────────────────────────
    rho_start = 3.0 * Mp**2 * potential.H_sq(traj.phi_at(0.0), traj.pi_at(0.0))
    rho_end = (
        3.0 * Mp**2 * potential.H_sq(traj.phi_at(N_end_traj), traj.pi_at(N_end_traj))
    )

    zeta_arr = np.full(len(values), float("nan"))
    for i, (phi1_i, phi2_i, N_inst_i) in enumerate(zip(phi1_arr, phi2_arr, N_inst_arr)):
        rho_i = 3.0 * Mp**2 * potential.H_sq(float(phi1_i), float(phi2_i))
        if not (rho_end <= rho_i <= rho_start):
            continue
        try:
            N_bg_i = brentq(
                lambda N: (
                    3.0 * Mp**2 * potential.H_sq(traj.phi_at(N), traj.pi_at(N)) - rho_i
                ),
                0.0,
                N_end_traj,
                xtol=atol,
                rtol=rtol,
            )
        except ValueError:
            continue
        N_background_i = N_bg_i - (N_end_traj - N_init_val)
        zeta_arr[i] = float(N_inst_i) - N_background_i

    # ── Step C: scale assignment ──────────────────────────────────────────
    N_before_end_arr = N_end_downflow + (N_total - N_inst_arr)

    # Latest-exit rule: enforce monotone non-increasing N_before_end
    N_be_mono = N_before_end_arr.copy()
    for i in range(1, len(N_be_mono)):
        N_be_mono[i] = min(N_be_mono[i], N_be_mono[i - 1])

    ln_k_arr = np.full(len(values), float("nan"))
    r_arr = np.full(len(values), float("nan"))
    valid_mask = ~np.isnan(zeta_arr)

    for i in range(len(values)):
        if not valid_mask[i]:
            continue
        try:
            lnk = ln_k_phys_Mpc(
                N_be_mono[i],
                potential.V(float(phi1_arr[i])),
                potential.epsilon(float(phi1_arr[i]), float(phi2_arr[i])),
                V_end_downflow,
                units,
                cosmo,
            )
            ln_k_arr[i] = lnk
            r_arr[i] = (
                2.0 * PI / exp(lnk)
            )  # has correct units since 1/Mpc is embedded by ln_k_phys_Mpc()
        except (ValueError, ZeroDivisionError):
            valid_mask[i] = False

    # Keep only valid points and sort by r ascending
    valid_mask &= np.isfinite(r_arr)
    if not np.any(valid_mask):
        return {
            "failure": True,
            "diagnostics": {"reason": "no valid scale assignments"},
        }

    sort_idx = np.argsort(r_arr[valid_mask])
    r_v = r_arr[valid_mask][sort_idx]
    zeta_v = zeta_arr[valid_mask][sort_idx]

    if len(r_v) < 2:
        return {
            "failure": True,
            "diagnostics": {"reason": "fewer than 2 valid sample points"},
        }

    # ── Step D: zeta(r), C(r), C_bar(r) ─────────────────────────────────
    zeta_spline = CubicSpline(r_v, zeta_v)
    zeta_prime = zeta_spline.derivative()

    C_v = np.array(
        [
            (2.0 / 3.0) * (1.0 - (1.0 + r_v[i] * float(zeta_prime(r_v[i]))) ** 2)
            for i in range(len(r_v))
        ]
    )

    type_II = bool(np.any(C_v < -1.0))

    # Dense grid for C_bar integration
    N_dense = max(10 * len(r_v), 500)
    r_dense = np.linspace(r_v[0], r_v[-1], N_dense)
    zeta_dense = zeta_spline(r_dense)
    zeta_prime_dense = zeta_prime(r_dense)

    rz_dense = r_dense * zeta_prime_dense
    integrand = (
        r_dense**2
        * np.exp(3.0 * zeta_dense)
        * (2.0 * rz_dense + 3.0 * rz_dense**2 + rz_dense**3)
    )

    # Accumulate integral to each sample r_i using trapezoid
    cumulative = np.zeros(N_dense)
    for j in range(1, N_dense):
        cumulative[j] = cumulative[j - 1] + 0.5 * (integrand[j - 1] + integrand[j]) * (
            r_dense[j] - r_dense[j - 1]
        )

    # Interpolate cumulative integral to sample points
    from scipy.interpolate import interp1d

    cumulative_at_r = interp1d(
        r_dense,
        cumulative,
        kind="linear",
        bounds_error=False,
        fill_value=(cumulative[0], cumulative[-1]),
    )

    C_bar_v = np.array(
        [
            -2.0 * float(cumulative_at_r(r_v[i])) / (r_v[i] ** 3 * exp(3.0 * zeta_v[i]))
            for i in range(len(r_v))
        ]
    )

    C_bar_last = float(C_bar_v[-1])
    r_last = float(r_v[-1])

    # ── Step E: r_max ─────────────────────────────────────────────────────
    # r_max_C: largest r with C >= C_threshold
    r_max_C = None
    for i in range(len(r_v) - 1, -1, -1):
        if C_v[i] >= C_threshold:
            r_max_C = float(r_v[i])
            break

    # r_max_C_bar: analytic extrapolation or last inward crossing
    r_max_C_bar = None
    if C_bar_last >= C_bar_threshold:
        r_max_C_bar = r_last * (C_bar_last / C_bar_threshold) ** (1.0 / 3.0)
    else:
        for i in range(len(r_v) - 1, -1, -1):
            if C_bar_v[i] >= C_bar_threshold:
                r_max_C_bar = float(r_v[i])
                break

    # ── Step F: PBH mass ──────────────────────────────────────────────────
    k_star = 0.05 / units.Mpc
    C_max = float(np.nanmax(C_v))
    C_bar_max = float(np.nanmax(C_bar_v))

    M_C = None
    if r_max_C is not None:
        M_C = (1.0 + C_max) * 5.6e15 * (k_star * r_max_C) ** 2 * units.SolarMass

    M_C_bar = None
    if r_max_C_bar is not None:
        M_C_bar = (1.0 + C_max) * 5.6e15 * (k_star * r_max_C_bar) ** 2 * units.SolarMass

    return {
        "failure": False,
        "r": r_v.tolist(),
        "zeta": zeta_v.tolist(),
        "C": C_v.tolist(),
        "C_bar": C_bar_v.tolist(),
        "r_max_C": r_max_C,
        "r_max_C_bar": r_max_C_bar,
        "M_C": M_C,
        "M_C_bar": M_C_bar,
        "C_max": C_max,
        "C_bar_max": C_bar_max,
        "V_end_downflow": V_end_downflow,
        "N_end_downflow": N_end_downflow,
        "diagnostics": {
            "type_II": type_II,
            "n_valid_points": int(np.sum(valid_mask)),
            "n_total_points": len(values),
        },
    }


@ray.remote
def _compute_compaction_function(
    full_instanton_proxy,
    slow_roll_instanton_proxy,
    trajectory_proxy,
    cosmo_class_name: str,
    cosmo_store_id: int,
    cosmo_T_CMB_Kelvin: float,
    C_threshold: float,
    C_bar_threshold: float,
    atol: float,
    rtol: float,
    label: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    Compute the compaction function C(r) and C_bar(r) from the full and/or
    slow-roll MSR instanton solutions.

    Returns a dict with keys "full", "slow_roll" (each a result dict or None)
    and "cosmo_store_id".
    """
    traj = trajectory_proxy.get()
    potential = traj._potential
    units = potential._units

    class _CosmoProxy:
        def __init__(self, T_CMB_Kelvin):
            self.T_CMB_Kelvin = T_CMB_Kelvin

    cosmo = _CosmoProxy(cosmo_T_CMB_Kelvin)

    full_result = None
    if full_instanton_proxy is not None and full_instanton_proxy.available:
        fi = full_instanton_proxy.get()
        if verbose:
            print(f"[{label}] computing compaction function from full instanton")
        full_result = _compute_instanton_path(
            fi,
            False,
            traj,
            potential,
            units,
            cosmo,
            C_threshold,
            C_bar_threshold,
            atol,
            rtol,
            label=label,
            verbose=verbose,
        )

    slow_roll_result = None
    if slow_roll_instanton_proxy is not None and slow_roll_instanton_proxy.available:
        sri = slow_roll_instanton_proxy.get()
        if verbose:
            print(f"[{label}] computing compaction function from slow-roll instanton")
        slow_roll_result = _compute_instanton_path(
            sri,
            True,
            traj,
            potential,
            units,
            cosmo,
            C_threshold,
            C_bar_threshold,
            atol,
            rtol,
            label=label,
            verbose=verbose,
        )

    return {
        "full": full_result,
        "slow_roll": slow_roll_result,
        "cosmo_store_id": cosmo_store_id,
    }


class CompactionFunctionValue(DatastoreObject):
    """
    Compaction function values {r, zeta, C, C_bar} at a single comoving radius.
    r is stored in the working unit system.
    """

    def __init__(
        self,
        store_id: Optional[int],
        r: float,
        zeta: float,
        C: float,
        C_bar: float,
    ):
        DatastoreObject.__init__(self, store_id)
        self._r = r
        self._zeta = zeta
        self._C = C
        self._C_bar = C_bar

    @property
    def r(self) -> float:
        """Comoving radius in the working unit system."""
        return self._r

    @property
    def zeta(self) -> float:
        return self._zeta

    @property
    def C(self) -> float:
        return self._C

    @property
    def C_bar(self) -> float:
        return self._C_bar


class CompactionFunction(DatastoreObject):
    """
    PBH compaction function computed from the full and/or slow-roll MSR instanton.

    Parameterised by a trajectory, optional instanton proxies, cosmological
    parameters, a delta_Nstar shard key, C thresholds, and ODE tolerances.

    Plain Python class on the driver. Numerical work is dispatched via the
    _compute_compaction_function Ray remote function.
    """

    def __init__(
        self,
        store_id: Optional[int],
        full_instanton,
        slow_roll_instanton,
        trajectory,
        cosmo,
        delta_Nstar: delta_Nstar,
        C_threshold: float = 0.4,
        C_bar_threshold: float = 0.4,
        atol: tolerance = None,
        rtol: tolerance = None,
        label: Optional[str] = None,
        tags: Optional[List[store_tag]] = None,
    ):
        if full_instanton is None and slow_roll_instanton is None:
            raise ValueError(
                "CompactionFunction: at least one of full_instanton or "
                "slow_roll_instanton must be provided."
            )
        DatastoreObject.__init__(self, store_id)
        self._full_instanton = full_instanton
        self._slow_roll_instanton = slow_roll_instanton
        self._trajectory = trajectory
        self._cosmo = cosmo
        self._delta_Nstar: delta_Nstar = delta_Nstar
        self._C_threshold: float = C_threshold
        self._C_bar_threshold: float = C_bar_threshold
        self._atol: tolerance = atol
        self._rtol: tolerance = rtol
        self._label: Optional[str] = label
        self._tags: List[store_tag] = tags or []
        self._full_values: List[CompactionFunctionValue] = []
        self._slow_roll_values: List[CompactionFunctionValue] = []
        self._compute_ref: Optional[ObjectRef] = None

    @property
    def available(self) -> bool:
        return self._my_id is not None

    @property
    def failure(self) -> bool:
        return getattr(self, "_failure", False)

    @property
    def delta_Nstar(self) -> delta_Nstar:
        return self._delta_Nstar

    @property
    def shard_key(self) -> delta_Nstar:
        return self._delta_Nstar

    @property
    def full_values(self) -> List[CompactionFunctionValue]:
        return self._full_values

    @property
    def slow_roll_values(self) -> List[CompactionFunctionValue]:
        return self._slow_roll_values

    @property
    def diagnostics(self) -> Optional[dict]:
        return getattr(self, "_diagnostics", None)

    # Scalar summary properties for the full-instanton path.
    # Set either by store() (after fresh compute) or by the factory build() (after DB load).
    @property
    def r_max_C_full(self) -> Optional[float]:
        return getattr(self, "_r_max_C_full", None)

    @property
    def r_max_C_bar_full(self) -> Optional[float]:
        return getattr(self, "_r_max_C_bar_full", None)

    @property
    def M_C_full(self) -> Optional[float]:
        return getattr(self, "_M_C_full", None)

    @property
    def M_C_bar_full(self) -> Optional[float]:
        return getattr(self, "_M_C_bar_full", None)

    @property
    def C_max_full(self) -> Optional[float]:
        return getattr(self, "_C_max_full", None)

    @property
    def V_end_downflow_full(self) -> Optional[float]:
        return getattr(self, "_V_end_downflow_full", None)

    @property
    def N_end_downflow_full(self) -> Optional[float]:
        return getattr(self, "_N_end_downflow_full", None)

    # Scalar summary properties for the slow-roll path.
    @property
    def r_max_C_slow_roll(self) -> Optional[float]:
        return getattr(self, "_r_max_C_slow_roll", None)

    @property
    def r_max_C_bar_slow_roll(self) -> Optional[float]:
        return getattr(self, "_r_max_C_bar_slow_roll", None)

    @property
    def M_C_slow_roll(self) -> Optional[float]:
        return getattr(self, "_M_C_slow_roll", None)

    @property
    def M_C_bar_slow_roll(self) -> Optional[float]:
        return getattr(self, "_M_C_bar_slow_roll", None)

    @property
    def C_max_slow_roll(self) -> Optional[float]:
        return getattr(self, "_C_max_slow_roll", None)

    @property
    def C_bar_max_full(self) -> Optional[float]:
        return getattr(self, "_C_bar_max_full", None)

    @property
    def C_bar_max_slow_roll(self) -> Optional[float]:
        return getattr(self, "_C_bar_max_slow_roll", None)

    @property
    def V_end_downflow_slow_roll(self) -> Optional[float]:
        return getattr(self, "_V_end_downflow_slow_roll", None)

    @property
    def N_end_downflow_slow_roll(self) -> Optional[float]:
        return getattr(self, "_N_end_downflow_slow_roll", None)

    def compute(self, label: Optional[str] = None, verbose: bool = False) -> ObjectRef:
        """
        Dispatch the compaction function computation as a Ray remote task.
        Returns an ObjectRef. RayWorkPool will call store() once this resolves.
        """
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        if getattr(self, "_failure", None) is not None:
            raise RuntimeError("already computed or failed")

        atol = 10.0**self._atol.log10_tol
        rtol = 10.0**self._rtol.log10_tol

        self._compute_ref = _compute_compaction_function.remote(
            full_instanton_proxy=self._full_instanton,
            slow_roll_instanton_proxy=self._slow_roll_instanton,
            trajectory_proxy=self._trajectory,
            cosmo_class_name=type(self._cosmo).__name__,
            cosmo_store_id=self._cosmo.store_id,
            cosmo_T_CMB_Kelvin=self._cosmo.T_CMB_Kelvin,
            C_threshold=self._C_threshold,
            C_bar_threshold=self._C_bar_threshold,
            atol=atol,
            rtol=rtol,
            label=label or self._label,
            verbose=verbose,
        )
        return self._compute_ref

    def store(self):
        """
        Called on the driver by RayWorkPool after compute() resolves.
        Reads the result dict and populates internal state.
        """
        if self._compute_ref is None:
            raise RuntimeError("store() called but no compute() is in progress")
        data = ray.get(self._compute_ref)
        self._compute_ref = None
        self._cosmo_store_id = data.get("cosmo_store_id")

        full = data.get("full")
        slow_roll = data.get("slow_roll")

        full_failed = full is None or full.get("failure", True)
        slow_roll_failed = slow_roll is None or slow_roll.get("failure", True)

        if full_failed and slow_roll_failed:
            self._failure = True
            self._diagnostics = {
                "full": full.get("diagnostics") if full else None,
                "slow_roll": slow_roll.get("diagnostics") if slow_roll else None,
            }
            return

        self._failure = False
        self._diagnostics = {
            "full": full.get("diagnostics") if full else None,
            "slow_roll": slow_roll.get("diagnostics") if slow_roll else None,
        }

        if not full_failed:
            self._full_result = full
            self._full_values = [
                CompactionFunctionValue(store_id=None, r=r, zeta=z, C=c, C_bar=cb)
                for r, z, c, cb in zip(
                    full["r"], full["zeta"], full["C"], full["C_bar"]
                )
            ]
            self._r_max_C_full = full.get("r_max_C")
            self._r_max_C_bar_full = full.get("r_max_C_bar")
            self._M_C_full = full.get("M_C")
            self._M_C_bar_full = full.get("M_C_bar")
            self._C_max_full = full.get("C_max")
            self._C_bar_max_full = full.get("C_bar_max")
            self._V_end_downflow_full = full.get("V_end_downflow")
            self._N_end_downflow_full = full.get("N_end_downflow")
        else:
            self._full_result = None

        if not slow_roll_failed:
            self._slow_roll_result = slow_roll
            self._slow_roll_values = [
                CompactionFunctionValue(store_id=None, r=r, zeta=z, C=c, C_bar=cb)
                for r, z, c, cb in zip(
                    slow_roll["r"],
                    slow_roll["zeta"],
                    slow_roll["C"],
                    slow_roll["C_bar"],
                )
            ]
            self._r_max_C_slow_roll = slow_roll.get("r_max_C")
            self._r_max_C_bar_slow_roll = slow_roll.get("r_max_C_bar")
            self._M_C_slow_roll = slow_roll.get("M_C")
            self._M_C_bar_slow_roll = slow_roll.get("M_C_bar")
            self._C_max_slow_roll = slow_roll.get("C_max")
            self._C_bar_max_slow_roll = slow_roll.get("C_bar_max")
            self._V_end_downflow_slow_roll = slow_roll.get("V_end_downflow")
            self._N_end_downflow_slow_roll = slow_roll.get("N_end_downflow")
        else:
            self._slow_roll_result = None


class CompactionFunctionProxy:
    """
    Lightweight reference to a persisted CompactionFunction.

    Holds delta_Nstar and the store_id so that dependent compute targets can
    route to the correct database shard without deserialising the full object.
    """

    def __init__(self, model: CompactionFunction):
        self._ref: ObjectRef = ray.put(model)
        self._store_id: Optional[int] = model.store_id if model.available else None
        self._delta_Nstar: delta_Nstar = model.delta_Nstar

    @property
    def store_id(self) -> Optional[int]:
        return self._store_id

    @property
    def available(self) -> bool:
        return self._store_id is not None

    @property
    def delta_Nstar(self) -> delta_Nstar:
        return self._delta_Nstar

    @property
    def shard_key(self) -> delta_Nstar:
        return self._delta_Nstar

    def get(self) -> CompactionFunction:
        return ray.get(self._ref)
