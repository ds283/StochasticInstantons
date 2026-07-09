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

    def test_sweeps_and_doe_unconverted_but_moved(self):
        """These three were moved verbatim (no adapter conversion -- see the
        module docstrings in sweeps.py/doe.py); re-export identity is the
        entire regression guard for them."""
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
