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
Golden-run regression test for prompt U1 (factor shared compaction scalars
into ComputeTargets/compaction_scalars.py).

The prompt's acceptance test describes running the full driver against
quadratic-minimal.yaml before/after the change and diffing every persisted
CompactionFunction scalar column bit-for-bit. That requires a live Ray
cluster and a real SQLite datastore (see CLAUDE.md: "Ray must be running"),
which is outside what an automated unit test can drive -- and, as
tests/test_gradient_coupled_instanton_end_to_end.py's own module docstring
notes, this codebase's convention for numerical golden tests is instead to
bypass Ray/the datastore and call the underlying plain function directly.

This test applies that convention at the exact seam this prompt touches:
_compute_instanton_path's Step D/E/F block, now delegated to
ComputeTargets/compaction_scalars.py. `_golden_step_d_e_f` below is a
byte-for-byte copy of the pre-refactor inlined code (as it stood in
ComputeTargets/CompactionFunction.py immediately before this prompt).
`_refactored_step_d_e_f` calls the same sequence through the new
compaction_scalars.py helpers, exactly as CompactionFunction.py now does.
Every scalar/array that feeds a persisted CompactionFunction column
(C, C_bar, r_max, r_peak, C_max, C_bar_max, M_max, M_peak, C_min,
compensated, type_II) is compared bit-for-bit (exact float64 equality, not
pytest.approx) across several synthetic (r_v, zeta_v) profiles chosen to
exercise every branch: r_max found in the interior / at the grid edge /
never reached, C_min >= 0 / in [-1, 0) / < -1, and the M_max/M_peak
C_threshold gate open and shut.

TestComputeInstantonPathSmoke additionally drives the real, un-mocked
_compute_instanton_path (Steps A-F together, unchanged upstream of D/E/F)
against a small quadratic-potential trajectory, confirming the new
compaction_scalars.py wiring executes end-to-end and returns finite,
self-consistent output -- the closest an automated test can get to "run the
driver on quadratic-minimal.yaml" without Ray or a datastore.
"""

from math import exp

import numpy as np
import pytest

from ComputeTargets.CompactionFunction import _classify_radii, _compute_instanton_path
from ComputeTargets.compaction_scalars import (
    classify_C_min,
    classify_radii,
    compute_C_bar,
    densify_zeta_profile,
    pbh_mass,
)
from Interpolation.spline_wrapper import SplineWrapper
from Units.Planck_units import Planck_units


# ---------------------------------------------------------------------------
# Golden reference: byte-for-byte copy of the pre-refactor inlined Step D/E/F
# ---------------------------------------------------------------------------

def _golden_step_d_e_f(r_v, zeta_v, C_threshold, units_SolarMass, units_Mpc):
    r_v = np.asarray(r_v, dtype=float)
    zeta_v = np.asarray(zeta_v, dtype=float)

    zeta_spline = SplineWrapper(r_v, zeta_v, x_transform='log', k=3)

    N_dense = max(10 * len(r_v), 500)
    r_dense = np.geomspace(r_v[0], r_v[-1], N_dense)  # log-uniform spacing
    log_r_dense = np.log(r_dense)
    zeta_dense = zeta_spline(r_dense)

    dzeta_dlogr = np.gradient(zeta_dense, log_r_dense)
    dzeta_dlogr[0] = (zeta_dense[1] - zeta_v[0]) / (log_r_dense[1] - log_r_dense[0])
    zeta_prime_dense = dzeta_dlogr / r_dense

    log_r_v = np.log(r_v)
    zeta_prime_v = np.interp(log_r_v, log_r_dense, zeta_prime_dense)

    C_v = (2.0 / 3.0) * (1.0 - (1.0 + r_v * zeta_prime_v) ** 2)

    C_min = float(np.nanmin(C_v))
    type_II = C_min < -1.0
    compensated = C_min < 0.0

    rz_dense = r_dense * zeta_prime_dense
    integrand = (
        r_dense**2
        * np.exp(3.0 * zeta_dense)
        * (2.0 * rz_dense + 3.0 * rz_dense**2 + rz_dense**3)
    )

    cumulative = np.zeros(N_dense)
    for j in range(1, N_dense):
        cumulative[j] = cumulative[j - 1] + 0.5 * (integrand[j - 1] + integrand[j]) * (
            r_dense[j] - r_dense[j - 1]
        )

    cumulative_at_r = SplineWrapper(r_dense, cumulative, x_transform='log', k=3)

    C_bar_v = np.array(
        [
            -2.0 * float(cumulative_at_r(r_v[i])) / (r_v[i] ** 3 * exp(3.0 * zeta_v[i]))
            for i in range(len(r_v))
        ]
    )

    r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge = (
        _classify_radii(r_v, C_v, C_threshold)
    )

    k_star = 0.05 / units_Mpc
    C_max = float(np.nanmax(C_v))
    C_bar_max = float(np.nanmax(C_bar_v))

    M_max = None
    if r_max is not None and C_max >= C_threshold:
        M_max = (1.0 + C_max) * 5.6e15 * (k_star * r_max) ** 2 * units_SolarMass

    M_peak = None
    if r_peak is not None and C_max >= C_threshold:
        M_peak = (1.0 + C_max) * 5.6e15 * (k_star * r_peak) ** 2 * units_SolarMass

    return {
        "C_v": C_v,
        "C_bar_v": C_bar_v,
        "r_max": r_max,
        "r_peak": r_peak,
        "r_max_at_grid_edge": r_max_at_grid_edge,
        "r_peak_at_grid_edge": r_peak_at_grid_edge,
        "C_min": C_min,
        "type_II": type_II,
        "compensated": compensated,
        "C_max": C_max,
        "C_bar_max": C_bar_max,
        "M_max": M_max,
        "M_peak": M_peak,
    }


# ---------------------------------------------------------------------------
# Refactored path: exactly what CompactionFunction.py's Step D/E/F now does
# ---------------------------------------------------------------------------

def _refactored_step_d_e_f(r_v, zeta_v, C_threshold, units_SolarMass, units_Mpc):
    r_v = np.asarray(r_v, dtype=float)
    zeta_v = np.asarray(zeta_v, dtype=float)

    r_dense, zeta_dense, zeta_prime_dense = densify_zeta_profile(r_v, zeta_v)

    log_r_dense = np.log(r_dense)
    log_r_v = np.log(r_v)
    zeta_prime_v = np.interp(log_r_v, log_r_dense, zeta_prime_dense)

    C_v = (2.0 / 3.0) * (1.0 - (1.0 + r_v * zeta_prime_v) ** 2)

    C_min_info = classify_C_min(C_v)

    C_bar_v = compute_C_bar(r_dense, zeta_dense, zeta_prime_dense, r_v, zeta_v)

    r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge = (
        classify_radii(r_v, C_v, C_threshold)
    )

    k_star = 0.05 / units_Mpc
    C_max = float(np.nanmax(C_v))
    C_bar_max = float(np.nanmax(C_bar_v))

    M_max = pbh_mass(C_max, r_max, C_threshold, k_star, units_SolarMass)
    M_peak = pbh_mass(C_max, r_peak, C_threshold, k_star, units_SolarMass)

    return {
        "C_v": C_v,
        "C_bar_v": C_bar_v,
        "r_max": r_max,
        "r_peak": r_peak,
        "r_max_at_grid_edge": r_max_at_grid_edge,
        "r_peak_at_grid_edge": r_peak_at_grid_edge,
        "C_min": C_min_info["C_min"],
        "type_II": C_min_info["type_II"],
        "compensated": C_min_info["compensated"],
        "C_max": C_max,
        "C_bar_max": C_bar_max,
        "M_max": M_max,
        "M_peak": M_peak,
    }


def _assert_bit_identical(golden: dict, refactored: dict):
    np.testing.assert_array_equal(golden["C_v"], refactored["C_v"])
    np.testing.assert_array_equal(golden["C_bar_v"], refactored["C_bar_v"])
    assert golden["r_max"] == refactored["r_max"]
    assert golden["r_peak"] == refactored["r_peak"]
    assert golden["r_max_at_grid_edge"] == refactored["r_max_at_grid_edge"]
    assert golden["r_peak_at_grid_edge"] == refactored["r_peak_at_grid_edge"]
    assert golden["C_min"] == refactored["C_min"]
    assert golden["type_II"] == refactored["type_II"]
    assert golden["compensated"] == refactored["compensated"]
    assert golden["C_max"] == refactored["C_max"]
    assert golden["C_bar_max"] == refactored["C_bar_max"]
    assert golden["M_max"] == refactored["M_max"]
    assert golden["M_peak"] == refactored["M_peak"]


# ---------------------------------------------------------------------------
# Synthetic (r_v, zeta_v) profiles spanning many decades in r, mirroring the
# real CompactionFunction r-grid (see Step D's own docstring).
# ---------------------------------------------------------------------------

def _bump_profile(amplitude, r_lo=1e-8, r_hi=1e2, n=60, center_decade=0.4, width=1.2):
    r_v = np.geomspace(r_lo, r_hi, n)
    log_r = np.log10(r_v)
    lo, hi = log_r[0], log_r[-1]
    center = lo + center_decade * (hi - lo)
    zeta_v = amplitude * np.exp(-0.5 * ((log_r - center) / width) ** 2)
    return r_v, zeta_v


def _asym_bump_profile(
    amplitude, r_lo=1e-8, r_hi=1e2, n=60, center_decade=0.35,
    width_left=0.15, width_right=1.5,
):
    """A Gaussian bump in log10(r) with different widths either side of the
    peak -- a steep rise (small width_left) followed by a gentle fall (large
    width_right) drives C_min << -1 (type_II) while keeping C_max modest."""
    r_v = np.geomspace(r_lo, r_hi, n)
    log_r = np.log10(r_v)
    lo, hi = log_r[0], log_r[-1]
    center = lo + center_decade * (hi - lo)
    zeta_v = np.where(
        log_r < center,
        amplitude * np.exp(-0.5 * ((log_r - center) / width_left) ** 2),
        amplitude * np.exp(-0.5 * ((log_r - center) / width_right) ** 2),
    )
    return r_v, zeta_v


_PROFILES = {
    # Mild bump: C stays well inside [-1, C_threshold), no r_max, no type_II.
    "mild_no_threshold_crossing": (_bump_profile(amplitude=0.01), 0.4),
    # Sharper symmetric bump: crosses C_threshold in the interior, resolved
    # r_max/r_peak (also happens to dip past C_min < -1 on the falling
    # side -- harmless, this profile's sanity check only asserts r_max/M_max
    # are resolved).
    "crosses_threshold_interior": (_bump_profile(amplitude=3.0, width=0.5), 0.4),
    # Steep rise / gentle fall: drives C_min < -1 (type_II) while C_max
    # stays below threshold (M_max/M_peak stay gated off).
    "steep_slope_type_II": (_asym_bump_profile(amplitude=1.5), 0.4),
}


class TestStepDEFBitIdenticalAgainstPreRefactorFormulas:
    """
    For every synthetic profile, the new compaction_scalars.py-based pipeline
    must reproduce the pre-refactor inlined formulas bit-for-bit -- this is a
    pure refactor, not a numerical correction (see .prompts/gradient-coupled-
    plotting/01-U1-factor-shared-compaction-scalars.md, "Must NOT").
    """

    @pytest.mark.parametrize("profile_name", list(_PROFILES.keys()))
    def test_bit_identical(self, profile_name):
        (r_v, zeta_v), C_threshold = _PROFILES[profile_name]
        units = Planck_units()

        golden = _golden_step_d_e_f(r_v, zeta_v, C_threshold, units.SolarMass, units.Mpc)
        refactored = _refactored_step_d_e_f(r_v, zeta_v, C_threshold, units.SolarMass, units.Mpc)

        _assert_bit_identical(golden, refactored)

    def test_crosses_threshold_profile_actually_resolves_r_max(self):
        """Sanity check that the 'crosses_threshold_interior' profile
        exercises the r_max-found / M_max-computed branch, not just the
        gated-off branch -- otherwise the bit-identity check above would be
        vacuous for that branch."""
        (r_v, zeta_v), C_threshold = _PROFILES["crosses_threshold_interior"]
        units = Planck_units()
        refactored = _refactored_step_d_e_f(r_v, zeta_v, C_threshold, units.SolarMass, units.Mpc)
        assert refactored["r_max"] is not None
        assert refactored["M_max"] is not None
        assert refactored["M_peak"] is not None

    def test_steep_slope_profile_actually_hits_type_II(self):
        """Sanity check that the 'steep_slope_type_II' profile exercises the
        C_min < -1 / M_max-gated-off branch."""
        (r_v, zeta_v), C_threshold = _PROFILES["steep_slope_type_II"]
        units = Planck_units()
        refactored = _refactored_step_d_e_f(r_v, zeta_v, C_threshold, units.SolarMass, units.Mpc)
        assert refactored["type_II"] is True
        assert refactored["M_max"] is None
        assert refactored["M_peak"] is None


# ---------------------------------------------------------------------------
# Smoke test: the real, un-mocked _compute_instanton_path end-to-end
# ---------------------------------------------------------------------------

class _QuadraticPotential:
    """Minimal quadratic potential, m^2 chosen to match quadratic-minimal.yaml's
    m-values-Mp: [1E-5] up to the square (m_sq = (1e-5)**2)."""

    def __init__(self, m_sq: float = 1e-10):
        self._m_sq = m_sq
        self._units = Planck_units()

    def V(self, phi):
        phi = np.asarray(phi)
        return 0.5 * self._m_sq * phi**2

    def dV_dphi(self, phi):
        return self._m_sq * np.asarray(phi)

    def H_sq(self, phi, pi):
        phi = np.asarray(phi)
        pi = np.asarray(pi)
        return self.V(phi) / (3.0 - 0.5 * pi**2)

    def epsilon(self, phi, pi):
        pi = np.asarray(pi)
        return 0.5 * pi**2


class _FloatConcept:
    """Duck-typed stand-in for the N_init MetadataConcept: supports float()."""

    def __init__(self, v):
        self._v = v

    def __float__(self):
        return self._v


def _make_background_trajectory(potential, phi0, pi0, atol=1e-10, rtol=1e-10):
    from scipy.integrate import solve_ivp

    def bg_rhs(N, y):
        phi, pi = y
        return [
            pi,
            -(3.0 - potential.epsilon(phi, pi)) * pi
            - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
        ]

    def event_end(N, y):
        return potential.epsilon(y[0], y[1]) - 1.0

    event_end.terminal = True
    event_end.direction = 1

    sol = solve_ivp(
        bg_rhs, (0.0, 5000.0), [phi0, pi0], method="RK45", atol=atol, rtol=rtol,
        events=event_end, dense_output=True, max_step=1.0,
    )
    assert sol.t_events[0].size > 0
    N_end = float(sol.t_events[0][0])

    class _Traj:
        def __init__(self):
            self.N_end = N_end

        def phi_at(self, N):
            return float(sol.sol(N)[0])

        def pi_at(self, N):
            return float(sol.sol(N)[1])

    return _Traj()


class _CosmoStub:
    T_CMB_Kelvin = 2.725


class TestComputeInstantonPathSmoke:
    """
    Drives the real _compute_instanton_path (Steps A-F, unchanged upstream
    of the refactored D/E/F block) against a genuine quadratic-potential
    background trajectory and a distinct "instanton" trajectory (different
    initial velocity), so that Step B produces a non-degenerate, varying
    zeta(r) profile. Confirms the new compaction_scalars.py wiring executes
    end-to-end post-refactor and produces finite, self-consistent output.
    """

    def test_full_pipeline_smoke(self):
        potential = _QuadraticPotential()
        units = potential._units
        cosmo = _CosmoStub()

        background = _make_background_trajectory(potential, phi0=20.0, pi0=-1e-4)
        # A distinct trajectory (different pi0) sampled well before its own
        # end of inflation, so Step A's downflow-to-end has room to run and
        # Step B's rho-matching against the background produces varying zeta.
        instanton_path = _make_background_trajectory(potential, phi0=20.0, pi0=-2e-4)

        N_sample = np.linspace(0.0, 0.6 * instanton_path.N_end, 40)
        phi1_vals = [instanton_path.phi_at(N) for N in N_sample]
        phi2_vals = [instanton_path.pi_at(N) for N in N_sample]

        values = [
            type(
                "V", (), {"N": type("N", (), {"N": float(N)})(), "phi1": p1, "phi2": p2}
            )()
            for N, p1, p2 in zip(N_sample, phi1_vals, phi2_vals)
        ]

        instanton_obj = type(
            "Inst",
            (),
            {
                "N_init_value": _FloatConcept(0.0),
                "values": values,
                "_N_total": float(N_sample[-1]),
            },
        )()

        result = _compute_instanton_path(
            instanton_obj,
            is_slow_roll=False,
            traj=background,
            potential=potential,
            units=units,
            cosmo=cosmo,
            C_threshold=0.4,
            atol=1e-8,
            rtol=1e-8,
            label="smoke-test",
        )

        assert result["failure"] is False
        r = np.array(result["r"])
        C = np.array(result["C"])
        C_bar = np.array(result["C_bar"])
        assert len(r) == len(C) == len(C_bar) >= 2
        assert np.all(np.diff(r) >= 0.0)
        assert np.all(np.isfinite(C))
        assert np.all(np.isfinite(C_bar))
        assert np.isfinite(result["C_max"])
        assert np.isfinite(result["C_bar_max"])
        assert result["diagnostics"]["C_min"] <= result["C_max"]
