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

from datetime import datetime
from math import exp, log
from math import pi as PI
from typing import List, Optional

import ray
from ray import ObjectRef

from Datastore.object import DatastoreObject
from InflationConcepts.delta_Nstar import delta_Nstar
from MetadataConcepts.store_tag import store_tag
from MetadataConcepts.tolerance import tolerance

# Absolute tolerance on ζ for safe boundary pinning in Step D.
# The dense-grid endpoint is only overridden with the known physical
# boundary value when the spline already agrees within this tolerance,
# to avoid introducing a false discontinuity in the gradient.
_ZETA_PIN_ATOL = 0.01


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


def _classify_radii(r_v, C_v, C_threshold: float):
    """
    Compute r_max and r_peak from C(r) sample arrays.

    r_max: outermost r where C >= C_threshold, scanning inward.
           r_max_at_grid_edge=True when C_v[-1] >= C_threshold
           (peak not resolved within grid).
           r_max=None if C nowhere reaches C_threshold.

    r_peak: r at which C is maximised (nanargmax).
            r_peak_at_grid_edge=True when argmax == len-1
            (peak not resolved within grid).

    Returns (r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge).
    """
    import numpy as np

    r_max = None
    r_max_at_grid_edge = False
    for i in range(len(r_v) - 1, -1, -1):
        if C_v[i] >= C_threshold:
            r_max = float(r_v[i])
            r_max_at_grid_edge = i == len(r_v) - 1
            break

    peak_idx = int(np.nanargmax(C_v))
    r_peak = float(r_v[peak_idx])
    r_peak_at_grid_edge = peak_idx == len(r_v) - 1

    return r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge


def _compute_instanton_path(
    instanton_obj,
    is_slow_roll: bool,
    traj,
    potential,
    units,
    cosmo,
    C_threshold: float,
    atol: float,
    rtol: float,
    label: Optional[str] = None,
    verbose: bool = False,
) -> dict:
    """
    Compute zeta(r), C(r), C_bar(r) for a single instanton path.

    Returns a result dict with keys: failure, r, zeta, C, C_bar, r_max,
    r_peak, M_max, M_peak, C_max, C_bar_max, V_end_downflow, N_end_downflow,
    diagnostics.
    """
    import time

    import numpy as np
    from scipy.optimize import brentq

    from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory
    from Interpolation.spline_wrapper import SplineWrapper

    compute_start = time.perf_counter()

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
        print(f"[{label or 'CompactionFunction'}] no sample values from instanton")
        return {"failure": True, "diagnostics": {"compute_time": time.perf_counter() - compute_start, "reason": "no sample values"}}

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
        print(f"[{label or 'CompactionFunction'}] downflow integration failed (trajectory did not reach end of inflation)")
        return {
            "failure": True,
            "diagnostics": {"compute_time": time.perf_counter() - compute_start, "reason": "downflow integration failed"},
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
        print(f"[{label or 'CompactionFunction'}] no valid scale assignments")
        return {
            "failure": True,
            "diagnostics": {"compute_time": time.perf_counter() - compute_start, "reason": "no valid scale assignments"},
        }

    sort_idx = np.argsort(r_arr[valid_mask])
    r_v = r_arr[valid_mask][sort_idx]
    zeta_v = zeta_arr[valid_mask][sort_idx]

    if len(r_v) < 2:
        print(f"[{label or 'CompactionFunction'}] fewer than 2 valid sample points (got {len(r_v)})")
        return {
            "failure": True,
            "diagnostics": {"compute_time": time.perf_counter() - compute_start, "reason": "fewer than 2 valid sample points"},
        }

    # ── Step D: zeta(r), C(r), C_bar(r) ─────────────────────────────────
    #
    # Strategy:
    #   1. Fit a spline to (r_v, zeta_v) in log-r space for smoothing.
    #   2. Evaluate on a log-uniform dense grid (geomspace) — essential
    #      because r spans many decades; linspace concentrates all points
    #      at large r, making np.gradient wildly inaccurate at small r.
    #   3. Overwrite the left-endpoint derivative after np.gradient using
    #      a two-point forward difference anchored to the exact physical
    #      boundary value ζ = δN★.  The right endpoint needs no correction.
    #   4. Compute dζ/dr by finite differences (np.gradient in log-r space,
    #      then divide by r) — no spline derivative is used.
    #   5. Interpolate dζ/dr back to r_v via np.interp in log-r space.

    zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3)

    N_dense = max(10 * len(r_v), 500)
    r_dense = np.geomspace(r_v[0], r_v[-1], N_dense)   # log-uniform spacing
    log_r_dense = np.log(r_dense)
    zeta_dense = zeta_spline(r_dense)

    # Finite-difference dζ/dr: gradient in log-r then divide by r.
    # np.gradient uses a three-point one-sided stencil at the endpoints,
    # which is sensitive to the values of the neighbouring points.  Pinning
    # zeta_dense[0] before the gradient call creates a discontinuity that
    # corrupts the stencil.  Instead, overwrite dzeta_dlogr[0] after the
    # gradient using a two-point forward difference anchored to the exact
    # physical boundary value zeta_inner = delta_Nstar.  No right-endpoint
    # override is needed: the spline is smooth there and np.gradient gives
    # the correct result.
    dzeta_dlogr = np.gradient(zeta_dense, log_r_dense)

    # zeta_v[0] is the exact computed zeta at the first sample point,
    # which equals delta_Nstar only approximately. Using the actual value
    # avoids a spurious derivative from the discrepancy.
    dzeta_dlogr[0] = (zeta_dense[1] - zeta_v[0]) / (log_r_dense[1] - log_r_dense[0])
    zeta_prime_dense = dzeta_dlogr / r_dense

    # Evaluate dζ/dr at sample points via linear interpolation in log-r.
    log_r_v = np.log(r_v)
    zeta_prime_v = np.interp(log_r_v, log_r_dense, zeta_prime_dense)

    C_v = (2.0 / 3.0) * (1.0 - (1.0 + r_v * zeta_prime_v) ** 2)

    C_min     = float(np.nanmin(C_v))
    type_II   = C_min < -1.0
    compensated = C_min < 0.0

    # C_bar integration — reuse r_dense / zeta_dense / zeta_prime_dense
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

    # Interpolate cumulative integral to sample points.
    # r_v is a subset of [r_dense[0], r_dense[-1]] by construction so no
    # extrapolation occurs.
    cumulative_at_r = SplineWrapper(r_dense, cumulative, x_transform='log', k=3)

    C_bar_v = np.array(
        [
            -2.0 * float(cumulative_at_r(r_v[i])) / (r_v[i] ** 3 * exp(3.0 * zeta_v[i]))
            for i in range(len(r_v))
        ]
    )

    # ── Step E: radii ─────────────────────────────────────────────────────
    r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge = (
        _classify_radii(r_v, C_v, C_threshold)
    )

    # ── Step F: PBH mass ──────────────────────────────────────────────────
    k_star = 0.05 / units.Mpc
    C_max    = float(np.nanmax(C_v))
    C_bar_max = float(np.nanmax(C_bar_v))

    M_max = None
    if r_max is not None and C_max >= C_threshold:
        M_max = (1.0 + C_max) * 5.6e15 * (k_star * r_max) ** 2 * units.SolarMass

    M_peak = None
    if r_peak is not None and C_max >= C_threshold:
        M_peak = (1.0 + C_max) * 5.6e15 * (k_star * r_peak) ** 2 * units.SolarMass

    return {
        "failure": False,
        "r": r_v.tolist(),
        "zeta": zeta_v.tolist(),
        "C": C_v.tolist(),
        "C_bar": C_bar_v.tolist(),
        "r_max": r_max,
        "r_peak": r_peak,
        "M_max": M_max,
        "M_peak": M_peak,
        "C_max": C_max,
        "C_bar_max": C_bar_max,
        "V_end_downflow": V_end_downflow,
        "N_end_downflow": N_end_downflow,
        "diagnostics": {
            "compute_time": time.perf_counter() - compute_start,
            "type_II": type_II,
            "compensated": compensated,
            "C_min": C_min,
            "n_valid_points": int(np.sum(valid_mask)),
            "n_total_points": len(values),
            "r_max_at_grid_edge": r_max_at_grid_edge,
            "r_peak_at_grid_edge": r_peak_at_grid_edge,
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
    import time

    compute_start = time.perf_counter()

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
            atol,
            rtol,
            label=label,
            verbose=verbose,
        )

    return {
        "full": full_result,
        "slow_roll": slow_roll_result,
        "cosmo_store_id": cosmo_store_id,
        "compute_time": time.perf_counter() - compute_start,
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
        atol: tolerance = None,
        rtol: tolerance = None,
        label: Optional[str] = None,
        tags: Optional[List[store_tag]] = None,
        timestamp: Optional[datetime] = None,
    ):
        if full_instanton is None and slow_roll_instanton is None:
            raise ValueError(
                "CompactionFunction: at least one of full_instanton or "
                "slow_roll_instanton must be provided."
            )
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)
        self._full_instanton = full_instanton
        self._slow_roll_instanton = slow_roll_instanton
        self._trajectory = trajectory
        self._cosmo = cosmo
        self._delta_Nstar: delta_Nstar = delta_Nstar
        self._C_threshold: float = C_threshold
        self._atol: tolerance = atol
        self._rtol: tolerance = rtol
        self._label: Optional[str] = label
        self._tags: List[store_tag] = tags or []
        self._full_values: List[CompactionFunctionValue] = []
        self._slow_roll_values: List[CompactionFunctionValue] = []
        self._compute_ref: Optional[ObjectRef] = None
        self._store_full_values: bool = True

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
    def r_max_full(self) -> Optional[float]:
        return getattr(self, "_r_max_full", None)

    @property
    def M_max_full(self) -> Optional[float]:
        return getattr(self, "_M_max_full", None)

    @property
    def r_peak_full(self) -> Optional[float]:
        return getattr(self, "_r_peak_full", None)

    @property
    def M_peak_full(self) -> Optional[float]:
        return getattr(self, "_M_peak_full", None)

    @property
    def C_peak_full(self) -> Optional[float]:
        return getattr(self, "_C_peak_full", None)

    @property
    def C_bar_peak_full(self) -> Optional[float]:
        return getattr(self, "_C_bar_peak_full", None)

    @property
    def V_end_downflow_full(self) -> Optional[float]:
        return getattr(self, "_V_end_downflow_full", None)

    @property
    def N_end_downflow_full(self) -> Optional[float]:
        return getattr(self, "_N_end_downflow_full", None)

    # Scalar summary properties for the slow-roll path.
    @property
    def r_max_slow_roll(self) -> Optional[float]:
        return getattr(self, "_r_max_slow_roll", None)

    @property
    def M_max_slow_roll(self) -> Optional[float]:
        return getattr(self, "_M_max_slow_roll", None)

    @property
    def r_peak_slow_roll(self) -> Optional[float]:
        return getattr(self, "_r_peak_slow_roll", None)

    @property
    def M_peak_slow_roll(self) -> Optional[float]:
        return getattr(self, "_M_peak_slow_roll", None)

    @property
    def C_peak_slow_roll(self) -> Optional[float]:
        return getattr(self, "_C_peak_slow_roll", None)

    @property
    def C_bar_peak_slow_roll(self) -> Optional[float]:
        return getattr(self, "_C_bar_peak_slow_roll", None)

    @property
    def C_threshold(self) -> float:
        return self._C_threshold

    @property
    def V_end_downflow_slow_roll(self) -> Optional[float]:
        return getattr(self, "_V_end_downflow_slow_roll", None)

    @property
    def N_end_downflow_slow_roll(self) -> Optional[float]:
        return getattr(self, "_N_end_downflow_slow_roll", None)

    @property
    def C_min_full(self) -> Optional[float]:
        return getattr(self, "_C_min_full", None)

    @property
    def compensated_full(self) -> Optional[bool]:
        return getattr(self, "_compensated_full", None)

    @property
    def type_II_full(self) -> Optional[bool]:
        return getattr(self, "_type_II_full", None)

    @property
    def C_min_slow_roll(self) -> Optional[float]:
        return getattr(self, "_C_min_slow_roll", None)

    @property
    def compensated_slow_roll(self) -> Optional[bool]:
        return getattr(self, "_compensated_slow_roll", None)

    @property
    def type_II_slow_roll(self) -> Optional[bool]:
        return getattr(self, "_type_II_slow_roll", None)

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
            atol=atol,
            rtol=rtol,
            label=label or self._label,
            verbose=verbose,
        )
        return self._compute_ref

    def store(self) -> None:
        """Called on the driver by RayWorkPool after compute() resolves."""
        if self._compute_ref is None:
            raise RuntimeError("store() called but no compute() is in progress")
        data = ray.get(self._compute_ref)
        self._compute_ref = None
        self._cosmo_store_id = data.get("cosmo_store_id")
        self._populate_from_result(data)

    def _populate_from_result(self, data: dict) -> None:
        """Populate internal state from a pre-computed result dict.

        Called by store() after resolving the Ray future, and directly by
        the pipeline store-handler when results arrive from compute_pipeline
        without a compute() having been dispatched on this object.
        Does NOT set _cosmo_store_id — that stays in store() because the
        pipeline path handles it separately.
        """
        full = data.get("full")
        slow_roll = data.get("slow_roll")

        full_failed = full is None or full.get("failure", True)
        slow_roll_failed = slow_roll is None or slow_roll.get("failure", True)

        if full_failed and slow_roll_failed:
            self._failure = True
            self._diagnostics = {
                "compute_time": data.get("compute_time"),
                "full": full.get("diagnostics") if full else None,
                "slow_roll": slow_roll.get("diagnostics") if slow_roll else None,
            }
            return

        self._failure = False
        self._diagnostics = {
            "compute_time": data.get("compute_time"),
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
            self._r_max_full = full.get("r_max")
            self._M_max_full = full.get("M_max")
            self._r_peak_full = full.get("r_peak")
            self._M_peak_full = full.get("M_peak")
            self._C_peak_full = full.get("C_max")
            self._C_bar_peak_full = full.get("C_bar_max")
            self._V_end_downflow_full = full.get("V_end_downflow")
            self._N_end_downflow_full = full.get("N_end_downflow")
            self._C_min_full        = full["diagnostics"].get("C_min")
            self._compensated_full  = full["diagnostics"].get("compensated")
            self._type_II_full      = full["diagnostics"].get("type_II")
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
            self._r_max_slow_roll = slow_roll.get("r_max")
            self._M_max_slow_roll = slow_roll.get("M_max")
            self._r_peak_slow_roll = slow_roll.get("r_peak")
            self._M_peak_slow_roll = slow_roll.get("M_peak")
            self._C_peak_slow_roll = slow_roll.get("C_max")
            self._C_bar_peak_slow_roll = slow_roll.get("C_bar_max")
            self._V_end_downflow_slow_roll = slow_roll.get("V_end_downflow")
            self._N_end_downflow_slow_roll = slow_roll.get("N_end_downflow")
            self._C_min_slow_roll        = slow_roll["diagnostics"].get("C_min")
            self._compensated_slow_roll  = slow_roll["diagnostics"].get("compensated")
            self._type_II_slow_roll      = slow_roll["diagnostics"].get("type_II")
        else:
            self._slow_roll_result = None

    def set_store_full_values(self, flag: bool) -> None:
        """
        When set to False, the factory's store() will skip writing child rows to
        CompactionFunctionSamples. All scalar summary columns on the parent row are
        written unconditionally. Use this for sparse-sampling campaigns where
        per-r profiles are not needed.
        """
        self._store_full_values = flag


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
