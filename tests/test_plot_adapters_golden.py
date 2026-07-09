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
Golden-run regression test for prompt P2
(.prompts/gradient-coupled-plotting/06-P2-adapter-layer-and-figure-conversion.md):
introduce `InstantonAdapter` and convert `plot_instanton_fields`,
`plot_noise_profile` and `plot_zeta_and_compaction` to consume a list of
adapters instead of raw `(fi, sri)`/`cf` objects.

As with tests/test_plot_extraction_golden.py (P1) and
tests/test_compaction_scalars_refactor_golden.py (U1), the prompt's own
acceptance test describes a before/after byte-diff of a real driver run
against a live Ray cluster and populated SQLite datastore -- outside what an
automated unit test can drive. This codebase's convention for this class of
"pure refactor, prove no behaviour changed" test is instead to exercise the
moved/converted code directly against stand-in objects:

1. Re-export identity for all six figure functions moved by this prompt (plus
   P1's), the same "moved, not duplicated" guard as P1's own test.
2. Behavioural unit tests for `FullInstantonAdapter`/`SlowRollInstantonAdapter`
   against duck-typed stand-ins for FullInstanton/SlowRollInstanton/
   CompactionFunction -- including the coords-from-query-context requirement
   (design §3.2, brief §3 item 2's "Trap") for a `_do_not_populate=True`-style
   fetch.
3. Smoke tests for the three converted figure functions confirming the
   overlay loop draws one line per adapter with the expected legend labels,
   for the two-adapter (Full + SR) case this prompt's acceptance test calls
   out explicitly.
"""

import numpy as np
import pytest
import ray
from matplotlib import pyplot as plt

import plot_InstantonSolutions as driver
import plotting.adapters.full as full_adapter_module
import plotting.adapters.slow_roll as slow_roll_adapter_module
import plotting.fetch as fetch
import plotting.figures.compaction as compaction
import plotting.figures.doe as doe
import plotting.figures.noise as noise
import plotting.figures.sweeps as sweeps
import plotting.figures.time_history as time_history
from plotting.adapters.full import FullInstantonAdapter
from plotting.adapters.slow_roll import SlowRollInstantonAdapter


@pytest.fixture(scope="module", autouse=True)
def _ray_ready():
    """The P2b fetch-helper tests below (TestFetchAdaptersOverGrid,
    TestCollectDoeScalarPoints) exercise ray.put/ray.get through a stub
    pool, same as tests/test_plot_extraction_golden.py's own fixture of the
    same name -- a bare local Ray init is enough, no live_pool/database.
    Does not call ray.shutdown(); conftest.py's session-scoped live_pool
    fixture owns that."""
    ray.init(ignore_reinit_error=True)
    yield


# ---------------------------------------------------------------------------
# Duck-typed stand-ins for FullInstanton / SlowRollInstanton / CompactionFunction
# ---------------------------------------------------------------------------


class _UnitsStub:
    PlanckMass = 1.0
    Mpc = 2.0
    SolarMass = 5.0


class _TrajProxyStub:
    def __init__(self, units=None):
        self.units = units if units is not None else _UnitsStub()


class _ToleranceStub:
    def __init__(self, tol):
        self.tol = tol


class _EfoldStub:
    def __init__(self, N):
        self.N = N


class _FullValueStub:
    def __init__(self, N, phi1, phi2, P1, P2):
        self.N = _EfoldStub(N)
        self.phi1 = phi1
        self.phi2 = phi2
        self.P1 = P1
        self.P2 = P2


class _SlowRollValueStub:
    def __init__(self, N, phi, P1):
        self.N = _EfoldStub(N)
        self.phi = phi
        self.P1 = P1


class _FullInstantonStub:
    def __init__(
        self,
        available=True,
        failure=False,
        store_id=1,
        values=None,
        msr_action=None,
        timestamp=None,
        units=None,
        atol=1e-8,
        rtol=1e-9,
    ):
        self.available = available
        self.failure = failure
        self.store_id = store_id if available else None
        self.values = values or []
        self.msr_action = msr_action
        self.noise_phi1_min = 0.1
        self.noise_phi1_mean = 0.2
        self.noise_phi1_max = 0.3
        self.noise_phi2_min = 0.4
        self.noise_phi2_mean = 0.5
        self.noise_phi2_max = 0.6
        self.diagnostics = {"picard_iterations": 7}
        self.timestamp = timestamp
        # Needed only when this stub is wrapped in a FullInstantonProxy (the
        # P2b fetch.py::_cf_vectorized_fetch call path), which reads these
        # directly -- matches the real FullInstanton's own properties.
        self.N_init_value = 60.0
        self.N_final_value = 10.0
        self.delta_Nstar = 5.0
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(atol)
        self._rtol = _ToleranceStub(rtol)

    def noise_profile_arrays(self):
        if not self.values:
            return None
        N = np.array([v.N.N for v in self.values], dtype=float)
        s1 = np.array([0.5 * abs(v.P1) for v in self.values], dtype=float)
        s2 = np.array([0.25 * abs(v.P2) for v in self.values], dtype=float)
        return {"N": N, "sigma_phi1": s1, "sigma_phi2": s2}


class _SlowRollInstantonStub:
    def __init__(
        self,
        available=True,
        failure=False,
        store_id=2,
        values=None,
        msr_action=None,
        timestamp=None,
        units=None,
        atol=1e-8,
        rtol=1e-9,
    ):
        self.available = available
        self.failure = failure
        self.store_id = store_id if available else None
        self.values = values or []
        self.msr_action = msr_action
        self.noise_phi1_min = 0.05
        self.noise_phi1_mean = 0.15
        self.noise_phi1_max = 0.25
        self.noise_phi2_min = None
        self.noise_phi2_mean = None
        self.noise_phi2_max = None
        self.diagnostics = {"brentq_iterations": 12}
        self.timestamp = timestamp
        # See _FullInstantonStub's own comment on these three.
        self.N_init_value = 60.0
        self.N_final_value = 10.0
        self.delta_Nstar = 5.0
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(atol)
        self._rtol = _ToleranceStub(rtol)

    def noise_profile_arrays(self):
        if not self.values:
            return None
        N = np.array([v.N.N for v in self.values], dtype=float)
        s1 = np.array([0.4 * abs(v.P1) for v in self.values], dtype=float)
        s2 = np.full_like(N, float("nan"))
        return {"N": N, "sigma_phi1": s1, "sigma_phi2": s2}


class _CFValueStub:
    def __init__(self, r, zeta, C, C_bar):
        self.r = r
        self.zeta = zeta
        self.C = C
        self.C_bar = C_bar


class _CompactionFunctionStub:
    def __init__(
        self,
        available=True,
        failure=False,
        full_values=None,
        slow_roll_values=None,
        units=None,
        **kwargs,
    ):
        self.available = available
        self.failure = failure
        self.full_values = full_values or []
        self.slow_roll_values = slow_roll_values or []
        self.C_threshold = kwargs.get("C_threshold", 0.4)
        self._trajectory = _TrajProxyStub(units)
        for key in (
            "C_peak_full",
            "C_bar_peak_full",
            "C_min_full",
            "compensated_full",
            "type_II_full",
            "r_max_full",
            "r_peak_full",
            "M_max_full",
            "M_peak_full",
            "V_end_downflow_full",
            "N_end_downflow_full",
            "C_peak_slow_roll",
            "C_bar_peak_slow_roll",
            "C_min_slow_roll",
            "compensated_slow_roll",
            "type_II_slow_roll",
            "r_max_slow_roll",
            "r_peak_slow_roll",
            "M_max_slow_roll",
            "M_peak_slow_roll",
            "V_end_downflow_slow_roll",
            "N_end_downflow_slow_roll",
        ):
            setattr(self, key, kwargs.get(key))


_FULL_CF_KWARGS = dict(
    C_peak_full=0.5,
    C_bar_peak_full=0.3,
    r_max_full=10.0,
    r_peak_full=4.0,
    M_max_full=15.0,
    M_peak_full=25.0,
    C_peak_slow_roll=0.45,
    C_bar_peak_slow_roll=0.28,
    r_max_slow_roll=8.0,
    r_peak_slow_roll=3.0,
    M_max_slow_roll=10.0,
    M_peak_slow_roll=20.0,
)


# ---------------------------------------------------------------------------
# 1. Re-point, don't duplicate: driver re-exports must be the SAME function
#    objects as the new plotting.* modules (P1's own convention, extended to
#    the figure functions this prompt moves/converts).
# ---------------------------------------------------------------------------


class TestDriverReExportsAreIdentical:
    def test_time_history_noise_compaction(self):
        assert driver.plot_instanton_fields is time_history.plot_instanton_fields
        assert driver.plot_noise_profile is noise.plot_noise_profile
        assert driver.plot_zeta_and_compaction is compaction.plot_zeta_and_compaction

    def test_sweeps_and_doe_converted(self):
        """P2b retrofit: these three were also converted to consume
        InstantonAdapter lists (plot_msr_action_sweep/plot_compaction_summary
        take a flat adapter list; plot_doe_scalar_summary takes a list of
        per-grid-point {"delta_Nstar", "delta_N", "adapters"} dicts) -- see
        the module docstrings in sweeps.py/doe.py."""
        assert driver.plot_msr_action_sweep is sweeps.plot_msr_action_sweep
        assert driver.plot_compaction_summary is sweeps.plot_compaction_summary
        assert driver.plot_doe_scalar_summary is doe.plot_doe_scalar_summary

    def test_adapters_are_reexported(self):
        assert driver.FullInstantonAdapter is full_adapter_module.FullInstantonAdapter
        assert (
            driver.SlowRollInstantonAdapter
            is slow_roll_adapter_module.SlowRollInstantonAdapter
        )


# ---------------------------------------------------------------------------
# 2. InstantonAdapter behaviour, including the coords-from-query-context
#    requirement.
# ---------------------------------------------------------------------------


class TestCoordsFromQueryContext:
    def test_coords_populated_for_do_not_populate_style_fetch(self):
        """A `_do_not_populate=True` fetch leaves `_values` empty even though
        the record is available -- coords must still report the query
        context, not anything scraped off the (dense-data-less) object."""
        fi = _FullInstantonStub(available=True, values=[])
        coords = {"N_init": 60.0, "N_final": 10.0, "delta_Nstar": 5.0}
        adapter = FullInstantonAdapter(fi, coords=coords)

        assert adapter.available is True
        assert adapter.time_history("phi") is None  # no dense data
        assert adapter.coords == coords

    def test_coords_populated_even_when_object_is_entirely_absent(self):
        """The fetch may come up with nothing at all (obj is None); coords
        must still be reportable since they describe what was queried, not
        what was found."""
        coords = {"N_init": 60.0, "N_final": 10.0, "delta_Nstar": 5.0}
        adapter = FullInstantonAdapter(None, coords=coords)

        assert adapter.available is False
        assert adapter.coords == coords

    def test_coords_defaults_to_empty_dict(self):
        adapter = FullInstantonAdapter(None)
        assert adapter.coords == {}


class TestFullInstantonAdapter:
    def test_available_and_failure_reflect_wrapped_object(self):
        assert FullInstantonAdapter(None).available is False
        assert FullInstantonAdapter(_FullInstantonStub(available=False)).available is False
        assert FullInstantonAdapter(_FullInstantonStub(available=True)).available is True
        assert (
            FullInstantonAdapter(_FullInstantonStub(failure=True)).failure is True
        )

    def test_store_id_none_when_unavailable(self):
        assert FullInstantonAdapter(None).store_id is None
        assert (
            FullInstantonAdapter(_FullInstantonStub(available=False)).store_id is None
        )
        assert (
            FullInstantonAdapter(_FullInstantonStub(available=True, store_id=42)).store_id
            == 42
        )

    def test_tolerances_and_flat_atol_rtol(self):
        adapter = FullInstantonAdapter(
            _FullInstantonStub(atol=1e-8, rtol=1e-9)
        )
        assert adapter.tolerances == (1e-8, 1e-9)
        assert adapter.atol == 1e-8
        assert adapter.rtol == 1e-9
        assert FullInstantonAdapter(None).tolerances == (None, None)

    def test_has_channel(self):
        adapter = FullInstantonAdapter(_FullInstantonStub())
        for channel in ("phi", "velocity", "P1", "P2"):
            assert adapter.has_channel(channel)
        assert not adapter.has_channel("rfield")

    def test_channel_label_symbols(self):
        adapter = FullInstantonAdapter(_FullInstantonStub())
        assert adapter.channel_label("phi") == r"$\varphi_1$"
        assert adapter.channel_label("velocity") == r"$\varphi_2$"
        assert adapter.channel_label("P1") == r"$P_1$"
        assert adapter.channel_label("P2") == r"$P_2$"

    def test_time_history_returns_raw_arrays_per_channel(self):
        values = [
            _FullValueStub(N=1.0, phi1=10.0, phi2=1.0, P1=0.1, P2=0.01),
            _FullValueStub(N=2.0, phi1=20.0, phi2=2.0, P1=0.2, P2=0.02),
        ]
        adapter = FullInstantonAdapter(_FullInstantonStub(values=values))

        N, phi = adapter.time_history("phi")
        assert list(N) == [1.0, 2.0]
        assert list(phi) == [10.0, 20.0]

        _, vel = adapter.time_history("velocity")
        assert list(vel) == [1.0, 2.0]

        _, P1 = adapter.time_history("P1")
        assert list(P1) == pytest.approx([0.1, 0.2])

        _, P2 = adapter.time_history("P2")
        assert list(P2) == pytest.approx([0.01, 0.02])

    def test_time_history_none_when_no_dense_values(self):
        adapter = FullInstantonAdapter(_FullInstantonStub(values=[]))
        assert adapter.time_history("phi") is None

    def test_noise_history_renames_channels(self):
        values = [_FullValueStub(N=1.0, phi1=1.0, phi2=1.0, P1=2.0, P2=4.0)]
        adapter = FullInstantonAdapter(_FullInstantonStub(values=values))
        hist = adapter.noise_history()
        assert set(hist.keys()) == {"N", "sigma_field", "sigma_mom"}
        assert hist["sigma_field"][0] == pytest.approx(0.5 * 2.0)
        assert hist["sigma_mom"][0] == pytest.approx(0.25 * 4.0)

    def test_radial_profile_applies_mpc_conversion(self):
        cf = _CompactionFunctionStub(
            full_values=[_CFValueStub(r=20.0, zeta=0.1, C=0.2, C_bar=0.3)],
            units=_UnitsStub(),
        )
        adapter = FullInstantonAdapter(_FullInstantonStub(), cf)
        profile = adapter.radial_profile()
        assert profile["r_Mpc"][0] == pytest.approx(10.0)  # 20.0 / Mpc(2.0)
        assert profile["zeta"][0] == pytest.approx(0.1)
        assert profile["C"][0] == pytest.approx(0.2)
        assert profile["C_bar"][0] == pytest.approx(0.3)

    def test_radial_profile_none_when_cf_missing_or_empty(self):
        assert FullInstantonAdapter(_FullInstantonStub()).radial_profile() is None
        cf = _CompactionFunctionStub(full_values=[])
        assert FullInstantonAdapter(_FullInstantonStub(), cf).radial_profile() is None

    def test_scalars_matches_extract_cf_summary_unit_conversion(self):
        """scalars()'s r_max_Mpc/M_max_solar must apply the exact same
        conversion as `plotting.fetch._extract_cf_summary` (division by
        units.Mpc/units.SolarMass) -- cross-checked directly against it."""
        units = _UnitsStub()
        cf = _CompactionFunctionStub(units=units, **_FULL_CF_KWARGS)
        expected = fetch._extract_cf_summary(cf, units)

        adapter = FullInstantonAdapter(_FullInstantonStub(msr_action=3.14), cf)
        s = adapter.scalars()

        assert s["msr_action"] == 3.14
        assert s["C_peak"] == expected[0]
        assert s["C_bar_peak"] == expected[1]
        assert s["M_max_solar"] == pytest.approx(expected[2])
        assert s["M_peak_solar"] == pytest.approx(expected[3])
        assert s["r_max_Mpc"] == pytest.approx(expected[8])
        assert s["r_peak_Mpc"] == pytest.approx(expected[9])

    def test_scalars_all_none_when_nothing_available(self):
        adapter = FullInstantonAdapter(None, None)
        s = adapter.scalars()
        assert all(v is None for v in s.values())

    def test_diagnostics(self):
        assert FullInstantonAdapter(None).diagnostics() is None
        fi = _FullInstantonStub()
        assert FullInstantonAdapter(fi).diagnostics() == {"picard_iterations": 7}

    def test_display_label_kind_and_line_style(self):
        adapter = FullInstantonAdapter(_FullInstantonStub())
        assert adapter.display_label == "Full"
        assert adapter.kind == "full"
        assert adapter.line_style == "-"
        assert adapter.is_spatial() is False


class TestSlowRollInstantonAdapter:
    def test_has_channel_excludes_velocity_and_p2(self):
        adapter = SlowRollInstantonAdapter(_SlowRollInstantonStub())
        assert adapter.has_channel("phi")
        assert adapter.has_channel("P1")
        assert not adapter.has_channel("velocity")
        assert not adapter.has_channel("P2")

    def test_time_history_velocity_is_none(self):
        adapter = SlowRollInstantonAdapter(
            _SlowRollInstantonStub(values=[_SlowRollValueStub(N=1.0, phi=1.0, P1=0.1)])
        )
        assert adapter.time_history("velocity") is None
        assert adapter.time_history("P2") is None

    def test_time_history_phi_and_p1(self):
        values = [
            _SlowRollValueStub(N=1.0, phi=5.0, P1=0.5),
            _SlowRollValueStub(N=2.0, phi=6.0, P1=0.6),
        ]
        adapter = SlowRollInstantonAdapter(_SlowRollInstantonStub(values=values))
        N, phi = adapter.time_history("phi")
        assert list(phi) == [5.0, 6.0]
        _, P1 = adapter.time_history("P1")
        assert list(P1) == pytest.approx([0.5, 0.6])

    def test_scalars_reads_slow_roll_suffixed_properties(self):
        units = _UnitsStub()
        cf = _CompactionFunctionStub(units=units, **_FULL_CF_KWARGS)
        expected = fetch._extract_cf_summary(cf, units)

        adapter = SlowRollInstantonAdapter(_SlowRollInstantonStub(msr_action=2.71), cf)
        s = adapter.scalars()

        assert s["msr_action"] == 2.71
        assert s["C_peak"] == expected[4]
        assert s["C_bar_peak"] == expected[5]
        assert s["M_max_solar"] == pytest.approx(expected[6])
        assert s["M_peak_solar"] == pytest.approx(expected[7])
        assert s["r_max_Mpc"] == pytest.approx(expected[10])
        assert s["r_peak_Mpc"] == pytest.approx(expected[11])

    def test_display_label_kind_and_line_style(self):
        adapter = SlowRollInstantonAdapter(_SlowRollInstantonStub())
        assert adapter.display_label == "SR"
        assert adapter.kind == "slow-roll"
        assert adapter.line_style == "--"


# ---------------------------------------------------------------------------
# 3. Converted figure functions: one line per adapter, correct legend labels,
#    for the two-adapter (Full + SR) overlay case.
# ---------------------------------------------------------------------------


class _PotentialStub:
    name = "quadratic"

    def dV_dphi(self, phi):
        return 0.5 * phi

    def H_sq(self, phi, pi):
        return 1.0 + 0.01 * phi**2


@pytest.fixture
def _no_op_close(monkeypatch):
    """Keep the figure open past the function call so its axes can be
    inspected, mirroring the technique already used by
    TestAnnotationHelpers/TestProvenanceFooter in
    tests/test_plot_extraction_golden.py (those just never call plt.close;
    here the function under test always does, so it is monkeypatched out)."""
    monkeypatch.setattr(plt, "close", lambda *a, **k: None)


class TestPlotInstantonFieldsOverlay:
    def test_two_adapter_overlay_draws_expected_lines(self, tmp_path, _no_op_close):
        fi_values = [
            _FullValueStub(N=1.0, phi1=10.0, phi2=1.0, P1=0.1, P2=0.01),
            _FullValueStub(N=2.0, phi1=20.0, phi2=2.0, P1=0.2, P2=0.02),
        ]
        sri_values = [
            _SlowRollValueStub(N=1.0, phi=11.0, P1=0.15),
            _SlowRollValueStub(N=2.0, phi=21.0, P1=0.25),
        ]
        fi = _FullInstantonStub(values=fi_values, msr_action=1.5)
        sri = _SlowRollInstantonStub(values=sri_values, msr_action=1.6)
        adapters = [FullInstantonAdapter(fi), SlowRollInstantonAdapter(sri)]

        time_history.plot_instanton_fields(
            adapters,
            60.0,
            10.0,
            5.0,
            _PotentialStub(),
            _UnitsStub(),
            tmp_path,
            "png",
        )

        fig = plt.gcf()
        ax_phi, ax_pi, ax_P1, ax_P2 = fig.axes[0], fig.axes[1], fig.axes[2], fig.axes[3]

        phi_labels = [line.get_label() for line in ax_phi.get_lines()]
        assert r"$\varphi_1$ (Full)" in phi_labels
        assert r"$\varphi$ (SR)" in phi_labels
        # init/final reference lines drawn exactly once
        assert phi_labels.count(r"$\varphi_{\rm init}$") == 1
        assert phi_labels.count(r"$\varphi_{\rm final}$") == 1

        pi_labels = [line.get_label() for line in ax_pi.get_lines()]
        assert r"$\varphi_2$ (Full)" in pi_labels  # SR has no velocity channel

        P1_labels = [line.get_label() for line in ax_P1.get_lines()]
        assert r"$P_1$ (Full)" in P1_labels
        assert r"$P_1$ (SR)" in P1_labels

        P2_labels = [line.get_label() for line in ax_P2.get_lines()]
        assert r"$P_2$ (Full)" in P2_labels
        assert not any("SR" in lbl for lbl in P2_labels)  # SR has no P2 channel

        plt.close(fig)

    def test_skips_when_no_adapter_available(self, tmp_path, capsys):
        adapters = [FullInstantonAdapter(None), SlowRollInstantonAdapter(None)]
        time_history.plot_instanton_fields(
            adapters, 60.0, 10.0, 5.0, _PotentialStub(), _UnitsStub(), tmp_path, "png"
        )
        assert not list(tmp_path.iterdir())
        assert "skipping instanton fields plot" in capsys.readouterr().out


class TestPlotNoiseProfileOverlay:
    def test_two_adapter_overlay_draws_expected_lines(self, tmp_path, _no_op_close):
        fi = _FullInstantonStub(
            values=[_FullValueStub(N=1.0, phi1=1.0, phi2=1.0, P1=2.0, P2=4.0)],
            msr_action=1.5,
        )
        sri = _SlowRollInstantonStub(
            values=[_SlowRollValueStub(N=1.0, phi=1.0, P1=1.0)], msr_action=1.6
        )
        adapters = [FullInstantonAdapter(fi), SlowRollInstantonAdapter(sri)]

        noise.plot_noise_profile(
            adapters, 60.0, 10.0, 5.0, "quadratic", tmp_path, "png"
        )

        fig = plt.gcf()
        ax_s1, ax_s2 = fig.axes[0], fig.axes[1]
        s1_labels = [line.get_label() for line in ax_s1.get_lines()]
        assert r"$\sigma_{\varphi_1}$ (Full)" in s1_labels
        assert r"$\sigma_{\varphi_1}$ (SR)" in s1_labels

        s2_labels = [line.get_label() for line in ax_s2.get_lines()]
        assert r"$\sigma_{\varphi_2}$ (Full)" in s2_labels
        assert not any("SR" in lbl for lbl in s2_labels)  # SR sigma_mom is all-NaN

        plt.close(fig)


class TestPlotZetaAndCompactionOverlay:
    def test_two_adapter_overlay_draws_expected_lines(self, tmp_path, _no_op_close):
        cf = _CompactionFunctionStub(
            full_values=[_CFValueStub(r=20.0, zeta=0.1, C=0.2, C_bar=0.3)],
            slow_roll_values=[_CFValueStub(r=16.0, zeta=0.05, C=0.15, C_bar=0.25)],
            units=_UnitsStub(),
        )
        fi = _FullInstantonStub()
        sri = _SlowRollInstantonStub()
        adapters = [
            FullInstantonAdapter(fi, cf),
            SlowRollInstantonAdapter(sri, cf),
        ]

        compaction.plot_zeta_and_compaction(
            adapters, 60.0, 10.0, 5.0, "quadratic", tmp_path, "png"
        )

        fig = plt.gcf()
        ax_zeta, ax_C, ax_Cbar = fig.axes[0], fig.axes[1], fig.axes[2]

        zeta_labels = [line.get_label() for line in ax_zeta.get_lines()]
        assert "Full" in zeta_labels
        assert "SR" in zeta_labels

        C_labels = [line.get_label() for line in ax_C.get_lines()]
        assert r"$C$ (Full)" in C_labels
        assert r"$C$ (SR)" in C_labels

        Cbar_labels = [line.get_label() for line in ax_Cbar.get_lines()]
        assert r"$\bar{C}$ (Full)" in Cbar_labels
        assert r"$\bar{C}$ (SR)" in Cbar_labels

        plt.close(fig)

    def test_gated_on_radial_profile_not_instanton_availability(self, tmp_path, _no_op_close):
        """Matches the original behaviour of gating purely on
        cf.full_values/slow_roll_values, independent of whether the paired
        instanton object itself is available."""
        cf = _CompactionFunctionStub(
            full_values=[_CFValueStub(r=20.0, zeta=0.1, C=0.2, C_bar=0.3)],
            units=_UnitsStub(),
        )
        # fi is None (never fetched) -- radial_profile still available via cf.
        adapters = [
            FullInstantonAdapter(None, cf),
            SlowRollInstantonAdapter(None, cf),
        ]

        compaction.plot_zeta_and_compaction(
            adapters, 60.0, 10.0, 5.0, "quadratic", tmp_path, "png"
        )

        fig = plt.gcf()
        ax_zeta = fig.axes[0]
        zeta_labels = [line.get_label() for line in ax_zeta.get_lines()]
        assert "Full" in zeta_labels
        assert "SR" not in zeta_labels  # cf.slow_roll_values is empty

        plt.close(fig)


# ---------------------------------------------------------------------------
# 4. P2b retrofit: plotting/fetch.py's generic multi-class adapter fetch,
#    and the now-adapter-driven sweeps.py/doe.py figure functions.
# ---------------------------------------------------------------------------


class TestInstantonAdapterMarker:
    def test_full_and_slow_roll_markers(self):
        assert FullInstantonAdapter(None).marker == "o"
        assert SlowRollInstantonAdapter(None).marker == "^"


class TestPlotMsrActionSweepOverlay:
    def test_two_kind_overlay_draws_expected_lines(self, tmp_path, _no_op_close):
        N_init_vals = [50.0, 55.0, 60.0]
        adapters = []
        for i, N_init in enumerate(N_init_vals):
            coords = {"N_init": N_init, "N_final": 10.0, "delta_Nstar": 5.0}
            fi = _FullInstantonStub(msr_action=1.0 + 0.1 * i)
            sri = _SlowRollInstantonStub(msr_action=2.0 + 0.1 * i)
            adapters.append(FullInstantonAdapter(fi, coords=coords))
            adapters.append(SlowRollInstantonAdapter(sri, coords=coords))

        sweeps.plot_msr_action_sweep(
            adapters,
            r"$N_{\rm init}$",
            "Nfinal=10_dNstar=5",
            "quadratic",
            tmp_path,
            "png",
            "N_init",
        )

        fig = plt.gcf()
        lines = fig.axes[0].get_lines()
        labels = [line.get_label() for line in lines]
        assert "Full MSR" in labels
        assert "SR MSR" in labels

        full_line = next(line for line in lines if line.get_label() == "Full MSR")
        assert list(full_line.get_xdata()) == N_init_vals  # already ascending, x-sorted

        plt.close(fig)

    def test_skips_when_no_data(self, tmp_path):
        adapters = [FullInstantonAdapter(None), SlowRollInstantonAdapter(None)]
        sweeps.plot_msr_action_sweep(
            adapters, "x", "fixed", "quadratic", tmp_path, "png", "N_init"
        )
        assert not list(tmp_path.iterdir())


class TestPlotCompactionSummaryOverlay:
    def test_two_kind_overlay_draws_expected_lines(self, tmp_path, _no_op_close):
        adapters = []
        for N_init in (50.0, 60.0):
            coords = {"N_init": N_init, "N_final": 10.0, "delta_Nstar": 5.0}
            cf = _CompactionFunctionStub(units=_UnitsStub(), **_FULL_CF_KWARGS)
            adapters.append(
                FullInstantonAdapter(_FullInstantonStub(), cf, coords=coords)
            )
            adapters.append(
                SlowRollInstantonAdapter(_SlowRollInstantonStub(), cf, coords=coords)
            )

        sweeps.plot_compaction_summary(
            adapters, r"$N_{\rm init}$", "fixed", "quadratic", tmp_path, "png", "N_init"
        )

        fig = plt.gcf()
        ax_C, ax_M, ax_r = fig.axes[0], fig.axes[1], fig.axes[2]

        C_labels = [line.get_label() for line in ax_C.get_lines()]
        assert r"$C_{\rm peak}$ (Full)" in C_labels
        assert r"$\bar{C}_{\rm peak}$ (Full)" in C_labels
        assert r"$C_{\rm peak}$ (SR)" in C_labels
        assert r"$\bar{C}_{\rm peak}$ (SR)" in C_labels

        M_labels = [line.get_label() for line in ax_M.get_lines()]
        assert r"$M_{\rm max}$ (Full)" in M_labels
        assert r"$M_{\rm peak}$ (SR)" in M_labels

        r_labels = [line.get_label() for line in ax_r.get_lines()]
        assert r"$r_{\rm max}$ (Full)" in r_labels

        plt.close(fig)

    def test_threshold_mismatch_warns_and_uses_smallest(
        self, tmp_path, _no_op_close, capsys
    ):
        cf_a = _CompactionFunctionStub(
            units=_UnitsStub(), C_threshold=0.4, **_FULL_CF_KWARGS
        )
        cf_b = _CompactionFunctionStub(
            units=_UnitsStub(), C_threshold=0.3, **_FULL_CF_KWARGS
        )
        adapters = [
            FullInstantonAdapter(
                _FullInstantonStub(),
                cf_a,
                coords={"N_init": 60.0, "N_final": 10.0, "delta_Nstar": 5.0},
            ),
            FullInstantonAdapter(
                _FullInstantonStub(),
                cf_b,
                coords={"N_init": 55.0, "N_final": 10.0, "delta_Nstar": 5.0},
            ),
        ]

        sweeps.plot_compaction_summary(
            adapters, "x", "fixed", "quadratic", tmp_path, "png", "N_init"
        )

        assert "C_threshold varies across sweep" in capsys.readouterr().out

        fig = plt.gcf()
        threshold_lines = [
            line
            for line in fig.axes[0].get_lines()
            if line.get_label().startswith("Threshold")
        ]
        assert len(threshold_lines) == 1
        assert "0.30" in threshold_lines[0].get_label()
        plt.close(fig)


class TestPlotDoeScalarSummaryOverlay:
    def test_two_kind_points_render_without_error(self, tmp_path):
        points = []
        for i, dns in enumerate((3.0, 5.0)):
            fi = _FullInstantonStub(msr_action=1.0 + i, store_id=i + 1)
            sri = _SlowRollInstantonStub(msr_action=2.0 + i, store_id=i + 10)
            cf = _CompactionFunctionStub(units=_UnitsStub(), **_FULL_CF_KWARGS)
            points.append(
                {
                    "delta_Nstar": dns,
                    "delta_N": 50.0 - i,
                    "adapters": [
                        FullInstantonAdapter(fi, cf),
                        SlowRollInstantonAdapter(sri, cf),
                    ],
                }
            )

        doe.plot_doe_scalar_summary(points, "quadratic", tmp_path, "png")

        assert (tmp_path / "doe_compaction_action.png").exists()
        assert (tmp_path / "doe_mass_collapse.png").exists()

    def test_skips_when_no_points(self, tmp_path):
        doe.plot_doe_scalar_summary([], "quadratic", tmp_path, "png")
        assert not list(tmp_path.iterdir())


class _FakeThirdAdapter:
    """Minimal duck-typed third adapter kind (not Full/SR), used to prove the
    five overlay-capable figure functions never hard-code a two-kind
    assumption -- exactly the property P4's later GradientCoupledAdapter
    depends on."""

    kind = "fake-third"
    marker = "D"
    line_style = ":"

    def __init__(self, coords=None):
        self.display_label = "Fake3"
        self._coords = coords or {}

    @property
    def coords(self):
        return dict(self._coords)

    @property
    def available(self):
        return True

    @property
    def failure(self):
        return False

    @property
    def store_id(self):
        return 999

    @property
    def timestamp(self):
        return None

    @property
    def tolerances(self):
        return (1e-8, 1e-9)

    @property
    def atol(self):
        return self.tolerances[0]

    @property
    def rtol(self):
        return self.tolerances[1]

    def has_channel(self, name):
        return name == "phi"

    def is_spatial(self):
        return False

    def channel_label(self, channel):
        return r"$\chi$" if channel == "phi" else None

    def time_history(self, channel):
        if channel != "phi":
            return None
        return np.array([1.0, 2.0]), np.array([3.0, 4.0])

    def noise_history(self):
        return None

    def radial_profile(self):
        return {
            "r_Mpc": np.array([1.0]),
            "zeta": np.array([0.1]),
            "C": np.array([0.2]),
            "C_bar": np.array([0.3]),
        }

    def scalars(self):
        return {
            "msr_action": 9.9,
            "C_peak": 0.6,
            "C_bar_peak": 0.4,
            "C_min": -0.1,
            "compensated": True,
            "type_II": False,
            "r_max_Mpc": 7.0,
            "r_peak_Mpc": 3.0,
            "M_max_solar": 12.0,
            "M_peak_solar": 6.0,
            "V_end_downflow": None,
            "N_end_downflow": None,
            "C_threshold": 0.4,
            "noise_field_min": None,
            "noise_field_mean": None,
            "noise_field_max": None,
            "noise_mom_min": None,
            "noise_mom_mean": None,
            "noise_mom_max": None,
        }

    def diagnostics(self):
        return None


class TestOverlayGeneralizesToNAdapters:
    def test_all_figure_families_render_a_third_series(self, tmp_path, _no_op_close):
        coords = {"N_init": 60.0, "N_final": 10.0, "delta_Nstar": 5.0}
        fi = _FullInstantonStub(
            values=[_FullValueStub(N=1.0, phi1=1.0, phi2=1.0, P1=0.1, P2=0.01)],
            msr_action=1.0,
        )
        sri = _SlowRollInstantonStub(
            values=[_SlowRollValueStub(N=1.0, phi=1.0, P1=0.1)], msr_action=2.0
        )
        cf = _CompactionFunctionStub(
            full_values=[_CFValueStub(r=20.0, zeta=0.1, C=0.2, C_bar=0.3)],
            slow_roll_values=[_CFValueStub(r=16.0, zeta=0.05, C=0.15, C_bar=0.25)],
            units=_UnitsStub(),
        )
        adapters = [
            FullInstantonAdapter(fi, cf, coords=coords),
            SlowRollInstantonAdapter(sri, cf, coords=coords),
            _FakeThirdAdapter(coords=coords),
        ]

        time_history.plot_instanton_fields(
            adapters, 60.0, 10.0, 5.0, _PotentialStub(), _UnitsStub(), tmp_path, "png"
        )
        fig = plt.gcf()
        phi_labels = [line.get_label() for line in fig.axes[0].get_lines()]
        assert any("Fake3" in lbl for lbl in phi_labels)
        plt.close(fig)

        # third adapter's noise_history() is None -- must not raise, and its
        # absence from the legend is expected (no data to draw).
        noise.plot_noise_profile(
            adapters, 60.0, 10.0, 5.0, "quadratic", tmp_path, "png"
        )
        plt.close(plt.gcf())

        compaction.plot_zeta_and_compaction(
            adapters, 60.0, 10.0, 5.0, "quadratic", tmp_path, "png"
        )
        fig = plt.gcf()
        zeta_labels = [line.get_label() for line in fig.axes[0].get_lines()]
        assert "Fake3" in zeta_labels
        plt.close(fig)

        sweeps.plot_msr_action_sweep(
            adapters, "x", "fixed", "quadratic", tmp_path, "png", "N_init"
        )
        fig = plt.gcf()
        labels = [line.get_label() for line in fig.axes[0].get_lines()]
        assert "Fake3 MSR" in labels
        plt.close(fig)

        sweeps.plot_compaction_summary(
            adapters, "x", "fixed", "quadratic", tmp_path, "png", "N_init"
        )
        fig = plt.gcf()
        C_labels = [line.get_label() for line in fig.axes[0].get_lines()]
        assert any("Fake3" in lbl for lbl in C_labels)
        plt.close(fig)

        points = [{"delta_Nstar": 5.0, "delta_N": 50.0, "adapters": adapters}]
        doe.plot_doe_scalar_summary(points, "quadratic", tmp_path, "png")
        assert (tmp_path / "doe_compaction_action.png").exists()


class _MultiClassStubPool:
    """Stand-in for ShardedPool's vectorized-fetch API across several solver
    classes at once, keyed by (class_name, shard_key)."""

    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    def object_get_vectorized(self, class_name, shard_key, payload_data):
        self.calls.append((class_name, shard_key, payload_data))
        response = self._responses.get((class_name, shard_key))
        if response is None:
            response = [None] * len(payload_data)
        return ray.put(response)


class TestFetchAdaptersOverGrid:
    def test_one_call_per_class_and_shard_with_correct_reassembly(self):
        items = [(60.0, 10.0, 5.0), (60.0, 10.0, 5.0), (55.0, 12.0, 3.0)]
        fi_a = _FullInstantonStub(store_id=1, msr_action=1.1)
        fi_b = _FullInstantonStub(store_id=2, msr_action=1.2)
        fi_c = _FullInstantonStub(store_id=3, msr_action=1.3)
        sri_a = _SlowRollInstantonStub(store_id=11, msr_action=2.1)
        sri_b = _SlowRollInstantonStub(store_id=12, msr_action=2.2)

        responses = {
            ("FullInstanton", 5.0): [fi_a, fi_b],
            ("SlowRollInstanton", 5.0): [sri_a, sri_b],
            ("FullInstanton", 3.0): [fi_c],
            ("SlowRollInstanton", 3.0): [None],
        }
        pool = _MultiClassStubPool(responses)

        class_specs = fetch.full_sr_class_specs(
            traj_proxy="traj-sentinel", atol=1e-8, rtol=1e-9, dm="dm-sentinel"
        )
        coords_of = lambda item: {
            "N_init": item[0],
            "N_final": item[1],
            "delta_Nstar": item[2],
        }
        rows = fetch.fetch_adapters_over_grid(pool, items, class_specs, coords_of)

        assert len(rows) == 3
        assert len(pool.calls) == 4  # 2 classes x 2 distinct shards
        called_pairs = {(c, s) for c, s, _ in pool.calls}
        assert called_pairs == {
            ("FullInstanton", 5.0),
            ("SlowRollInstanton", 5.0),
            ("FullInstanton", 3.0),
            ("SlowRollInstanton", 3.0),
        }

        full0, sr0 = rows[0]
        assert full0.store_id == 1
        assert sr0.store_id == 11
        assert full0.coords == {"N_init": 60.0, "N_final": 10.0, "delta_Nstar": 5.0}

        full2, sr2 = rows[2]
        assert full2.store_id == 3
        assert sr2.available is False

    def test_cf_spec_skips_shard_with_no_available_instanton(self):
        items = [(60.0, 10.0, 5.0), (55.0, 12.0, 3.0)]
        fi_a = _FullInstantonStub(store_id=1)
        cf_a = _CompactionFunctionStub(
            full_values=[_CFValueStub(r=20.0, zeta=0.1, C=0.2, C_bar=0.3)],
            units=_UnitsStub(),
        )
        responses = {
            ("FullInstanton", 5.0): [fi_a],
            ("SlowRollInstanton", 5.0): [None],
            ("FullInstanton", 3.0): [None],
            ("SlowRollInstanton", 3.0): [None],
            ("CompactionFunction", 5.0): [cf_a],
        }
        pool = _MultiClassStubPool(responses)

        class_specs = fetch.full_sr_class_specs(
            traj_proxy="traj-sentinel", atol=1e-8, rtol=1e-9, dm="dm-sentinel"
        )
        cf_spec = fetch.CFFetchSpec(
            shard_key_of=lambda item: item[2],
            traj_proxy="traj-sentinel",
            fi_spec_name="full",
            sri_spec_name="slow-roll",
            cosmo="cosmo-sentinel",
            atol=1e-8,
            rtol=1e-9,
        )
        coords_of = lambda item: {
            "N_init": item[0],
            "N_final": item[1],
            "delta_Nstar": item[2],
        }
        rows = fetch.fetch_adapters_over_grid(
            pool, items, class_specs, coords_of, cf_spec=cf_spec
        )

        cf_calls = [c for c in pool.calls if c[0] == "CompactionFunction"]
        assert len(cf_calls) == 1
        assert cf_calls[0][1] == 5.0  # only the shard with an available instanton

        full0, _ = rows[0]
        assert full0.radial_profile() is not None
        full1, _ = rows[1]
        assert full1.radial_profile() is None


class TestCollectDoeScalarPoints:
    def test_returns_new_shape_and_omits_unavailable_points(self):
        grid_combos = [(60.0, 10.0, 5.0), (55.0, 12.0, 3.0), (50.0, 8.0, 5.0)]
        fi_a = _FullInstantonStub(store_id=1, msr_action=1.1)
        sri_a = _SlowRollInstantonStub(store_id=11, msr_action=2.1)
        cf_a = _CompactionFunctionStub(units=_UnitsStub(), **_FULL_CF_KWARGS)

        responses = {
            ("FullInstanton", 5.0): [fi_a, None],
            ("SlowRollInstanton", 5.0): [sri_a, None],
            ("FullInstanton", 3.0): [None],
            ("SlowRollInstanton", 3.0): [None],
            ("CompactionFunction", 5.0): [cf_a, None],
        }
        pool = _MultiClassStubPool(responses)

        points = fetch.collect_doe_scalar_points(
            pool,
            "traj-sentinel",
            grid_combos,
            "cosmo-sentinel",
            1e-8,
            1e-9,
            _UnitsStub(),
            "dm-sentinel",
        )

        # combo 1 (dns=3.0, neither available) and combo 2 (dns=5.0, second
        # slot -- also neither available there) are both omitted.
        assert len(points) == 1
        assert points[0]["delta_Nstar"] == 5.0
        assert points[0]["delta_N"] == pytest.approx(50.0)
        full_a, sr_a = points[0]["adapters"]
        assert full_a.store_id == 1
        assert sr_a.store_id == 11

    def test_empty_grid_combos_returns_empty_list(self):
        pool = _MultiClassStubPool({})
        assert (
            fetch.collect_doe_scalar_points(
                pool,
                "traj-sentinel",
                [],
                "cosmo-sentinel",
                1e-8,
                1e-9,
                _UnitsStub(),
                "dm-sentinel",
            )
            == []
        )

    def test_flatten_reproduces_golden_flat_dict(self):
        coords = {"N_init": 60.0, "N_final": 10.0, "delta_Nstar": 5.0}
        fi = _FullInstantonStub(msr_action=1.5)
        sri = _SlowRollInstantonStub(msr_action=1.6)
        cf = _CompactionFunctionStub(units=_UnitsStub(), **_FULL_CF_KWARGS)
        full_a = FullInstantonAdapter(fi, cf, coords=coords)
        sr_a = SlowRollInstantonAdapter(sri, cf, coords=coords)
        points = [{"delta_Nstar": 5.0, "delta_N": 50.0, "adapters": [full_a, sr_a]}]

        rows = fetch.flatten_doe_points_for_csv(points)
        assert len(rows) == 1
        row = rows[0]

        # Cross-check against the pre-existing, still-unchanged helpers this
        # replaces -- same values _collect_doe_scalar_data used to compute.
        s = fetch._extract_cf_summary(cf, _UnitsStub())
        assert row["N_init"] == 60.0
        assert row["N_final"] == 10.0
        assert row["delta_Nstar"] == 5.0
        assert row["delta_N"] == 50.0
        assert row["msr_action_full"] == fetch._qualifying_action(fi)
        assert row["msr_action_sr"] == fetch._qualifying_action(sri)
        assert row["noise_phi1_min_full"] == fi.noise_phi1_min
        assert row["noise_phi2_max_sr"] == sri.noise_phi2_max
        assert row["C_peak_full"] == s[0]
        assert row["C_bar_peak_full"] == s[1]
        assert row["M_max_full_solar"] == pytest.approx(s[2])
        assert row["M_peak_full_solar"] == pytest.approx(s[3])
        assert row["C_peak_sr"] == s[4]
        assert row["r_max_full_Mpc"] == pytest.approx(s[8])
        assert row["r_max_sr_Mpc"] == pytest.approx(s[10])
        assert row["r_peak_sr_Mpc"] == pytest.approx(s[11])
