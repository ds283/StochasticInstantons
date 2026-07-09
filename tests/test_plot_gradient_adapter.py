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
Acceptance test for Prompt P4
(.prompts/gradient-coupled-plotting/08-P4-gradient-coupled-adapter.md):
`GradientCoupledAdapter` / `SpatialAdapter`, as pure reads.

Follows the duck-typed-stand-in convention set by
tests/test_plot_adapters_golden.py (P2) rather than driving a live Ray
cluster/datastore: a `_GCIStub` mimics the subset of `GradientCoupledInstanton`
this adapter reads, at each of the three P3 fetch-mode fidelity tiers
("scalars", "profile", "dense"). tests/test_plot_adapters_golden.py's own
`TestOverlayGeneralizesToNAdapters` already established (with its
`_FakeThirdAdapter`) that a third adapter kind whose `noise_history()`
returns `None` is handled gracefully by every P2 figure function -- this
file exercises the real `GradientCoupledAdapter` the same way.

1. Unit tests for every `InstantonAdapter`/spatial method against the three
   fidelity tiers.
2. Acceptance test (a): the five homogeneous P2 figure functions, unchanged,
   render without error when handed `[gci_adapter, full_adapter, sr_adapter]`
   at each fidelity tier.
3. Acceptance test (b): `field_2d`/`derived_at_time` raise `RuntimeError`
   (not `None`, not a silent no-op) on a `scalars`/`profile`-fidelity
   instance.
"""

import numpy as np
import pytest
from matplotlib import pyplot as plt

import plotting.figures.compaction as compaction
import plotting.figures.doe as doe
import plotting.figures.noise as noise
import plotting.figures.sweeps as sweeps
import plotting.figures.time_history as time_history
from Numerics.LGLCollocation import LGLCollocationGrid
from plotting.adapters.full import FullInstantonAdapter
from plotting.adapters.gradient import GradientCoupledAdapter, SpatialAdapter
from plotting.adapters.slow_roll import SlowRollInstantonAdapter

# ---------------------------------------------------------------------------
# Duck-typed stand-ins
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


class _GCIValueStub:
    """Mimics GradientCoupledInstantonValue: one dense sample row, each
    field a per-node list ordered y=-1..+1 (core node is index -1)."""

    def __init__(self, N, phi, pi, rfield, rmom):
        self.N = _EfoldStub(N)
        self.phi = phi
        self.pi = pi
        self.rfield = rfield
        self.rmom = rmom


class _GCIProfileStub:
    """Mimics GradientCoupledInstantonProfileValue."""

    def __init__(self, zeta, r_ratio, C, r_phys, C_bar):
        self.zeta = zeta
        self.r_ratio = r_ratio
        self.C = C
        self.r_phys = r_phys
        self.C_bar = C_bar


_PARITY_KWARGS = dict(
    C_peak=0.5,
    C_bar_peak=0.3,
    C_min=-0.2,
    compensated=True,
    type_II=False,
    r_max=10.0,
    r_peak=4.0,
    M_max=15.0,
    M_peak=25.0,
    V_end_downflow=1e-9,
    N_end_downflow=0.05,
)


class _GCIStub:
    """Duck-typed stand-in for `GradientCoupledInstanton`, covering exactly
    the surface `GradientCoupledAdapter` reads."""

    def __init__(
        self,
        available=True,
        failure=False,
        store_id=1,
        values=None,
        profile=None,
        msr_action=None,
        timestamp=None,
        units=None,
        atol=1e-8,
        rtol=1e-9,
        n_collocation_points_value=4,
        parity=None,
        zeta_c_r_at_time_raises=None,
    ):
        self.available = available
        self.failure = failure
        self.store_id = store_id if available else None
        self.values = values or []
        self.profile = profile or []
        self.msr_action = msr_action
        self.noise_field_min = -0.1
        self.noise_field_mean = 0.0
        self.noise_field_max = 0.1
        self.noise_mom_min = -0.2
        self.noise_mom_mean = 0.0
        self.noise_mom_max = 0.2
        self.diagnostics = {"converged": True, "outer_iterations": 4}
        self.timestamp = timestamp
        self.n_collocation_points_value = n_collocation_points_value
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(atol)
        self._rtol = _ToleranceStub(rtol)
        for key, value in (parity or _PARITY_KWARGS).items():
            setattr(self, key, value)
        self._zeta_c_r_at_time_raises = zeta_c_r_at_time_raises

    def zeta_C_r_at_time(self, N_query):
        if self._zeta_c_r_at_time_raises is not None:
            raise self._zeta_c_r_at_time_raises
        if not self.values:
            raise RuntimeError(
                "GradientCoupledInstanton.zeta_C_r_at_time: this instance has "
                "no stored per-sample values."
            )
        return {
            "N": N_query.N,
            "zeta": np.array([0.1, 0.2]),
            "r_ratio": np.array([0.5, 1.0]),
            "C": np.array([0.2, 0.3]),
            "r_phys": np.array([1.0, 2.0]),
            "failure_mask": np.array([False, False]),
        }


_COORDS = {
    "N_init": 60.0,
    "N_final": 10.0,
    "delta_Nstar": 5.0,
    "alpha": 0.05,
    "n_collocation_points": 4,
}


def _dense_values():
    # 4 collocation nodes (matches n_collocation_points_value default of 4);
    # core node is the last entry of each per-node list.
    return [
        _GCIValueStub(
            N=1.0, phi=[0.1, 0.2, 0.3, 1.0], pi=[0.0, 0.0, 0.0, 2.0],
            rfield=[0.0, 0.0, 0.0, 3.0], rmom=[0.0, 0.0, 0.0, 4.0],
        ),
        _GCIValueStub(
            N=2.0, phi=[0.2, 0.3, 0.4, 5.0], pi=[0.0, 0.0, 0.0, 6.0],
            rfield=[0.0, 0.0, 0.0, 7.0], rmom=[0.0, 0.0, 0.0, 8.0],
        ),
    ]


def _profile_rows():
    return [
        _GCIProfileStub(zeta=0.1, r_ratio=0.5, C=0.2, r_phys=20.0, C_bar=0.15),
        _GCIProfileStub(zeta=0.2, r_ratio=1.0, C=0.3, r_phys=40.0, C_bar=0.25),
    ]


# ---------------------------------------------------------------------------
# 1. Constructor / fidelity plumbing
# ---------------------------------------------------------------------------


class TestFidelityConstruction:
    def test_rejects_unknown_fidelity(self):
        with pytest.raises(ValueError):
            GradientCoupledAdapter(_GCIStub(), coords=_COORDS, fidelity="bogus")

    def test_rejects_missing_fidelity(self):
        with pytest.raises(ValueError):
            GradientCoupledAdapter(_GCIStub(), coords=_COORDS)

    def test_is_spatial_true_only_for_dense(self):
        for tier in ("scalars", "profile"):
            adapter = GradientCoupledAdapter(_GCIStub(), coords=_COORDS, fidelity=tier)
            assert adapter.is_spatial() is False
        adapter = GradientCoupledAdapter(_GCIStub(), coords=_COORDS, fidelity="dense")
        assert adapter.is_spatial() is True

    def test_kind_line_style_marker(self):
        adapter = GradientCoupledAdapter(_GCIStub(), coords=_COORDS, fidelity="scalars")
        assert adapter.kind == "gradient-coupled"
        assert adapter.line_style == ":"
        assert adapter.marker == "D"

    def test_spatial_adapter_is_the_same_class(self):
        """P4's own permitted choice: fold SpatialAdapter into
        GradientCoupledAdapter rather than subclass it, so a scalars/profile
        instance still has field_2d/derived_at_time and raises RuntimeError
        instead of AttributeError (see acceptance test (b) below)."""
        assert SpatialAdapter is GradientCoupledAdapter


class TestDisplayLabelFromCoords:
    def test_label_uses_coords_not_wrapped_object(self):
        """coords carries n_collocation_points/alpha from the query context;
        the wrapped object may not even exist (e.g. a do_not_populate fetch
        that came up empty) so the label must never scrape them off it."""
        adapter = GradientCoupledAdapter(None, coords=_COORDS, fidelity="scalars")
        assert adapter.display_label == "GCI (n=4, α=0.05)"

    def test_label_falls_back_when_coords_incomplete(self):
        adapter = GradientCoupledAdapter(None, coords={}, fidelity="scalars")
        assert adapter.display_label == "GCI"

    def test_coords_reports_all_five_gci_fields(self):
        adapter = GradientCoupledAdapter(None, coords=_COORDS, fidelity="scalars")
        assert adapter.coords == _COORDS


# ---------------------------------------------------------------------------
# 2. Identity / capability
# ---------------------------------------------------------------------------


class TestIdentity:
    def test_available_and_failure(self):
        assert (
            GradientCoupledAdapter(None, fidelity="scalars").available is False
        )
        assert (
            GradientCoupledAdapter(_GCIStub(available=False), fidelity="scalars").available
            is False
        )
        assert (
            GradientCoupledAdapter(_GCIStub(available=True), fidelity="scalars").available
            is True
        )
        assert (
            GradientCoupledAdapter(_GCIStub(failure=True), fidelity="scalars").failure
            is True
        )

    def test_store_id_and_timestamp(self):
        assert GradientCoupledAdapter(None, fidelity="scalars").store_id is None
        adapter = GradientCoupledAdapter(
            _GCIStub(available=True, store_id=42), fidelity="scalars"
        )
        assert adapter.store_id == 42

    def test_tolerances(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(atol=1e-7, rtol=1e-8), fidelity="scalars"
        )
        assert adapter.tolerances == (1e-7, 1e-8)
        assert adapter.atol == 1e-7
        assert adapter.rtol == 1e-8
        assert GradientCoupledAdapter(None, fidelity="scalars").tolerances == (None, None)

    def test_has_channel_excludes_p1_p2(self):
        adapter = GradientCoupledAdapter(_GCIStub(), fidelity="scalars")
        for channel in ("phi", "velocity", "rfield", "rmom"):
            assert adapter.has_channel(channel)
        assert not adapter.has_channel("P1")
        assert not adapter.has_channel("P2")

    def test_channel_labels(self):
        adapter = GradientCoupledAdapter(_GCIStub(), fidelity="scalars")
        assert adapter.channel_label("phi") == r"$\varphi$"
        assert adapter.channel_label("velocity") == r"$\pi$"
        assert adapter.channel_label("rfield") == r"$r_\varphi$"
        assert adapter.channel_label("rmom") == r"$r_\pi$"


# ---------------------------------------------------------------------------
# 3. time_history -- core node (y=+1, last entry) extraction
# ---------------------------------------------------------------------------


class TestTimeHistory:
    def test_reads_core_node_per_channel(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(values=_dense_values()), fidelity="dense"
        )
        N, phi = adapter.time_history("phi")
        assert list(N) == [1.0, 2.0]
        assert list(phi) == [1.0, 5.0]

        _, vel = adapter.time_history("velocity")
        assert list(vel) == [2.0, 6.0]

        _, rf = adapter.time_history("rfield")
        assert list(rf) == [3.0, 7.0]

        _, rm = adapter.time_history("rmom")
        assert list(rm) == [4.0, 8.0]

    def test_none_when_no_dense_values(self):
        for tier in ("scalars", "profile"):
            adapter = GradientCoupledAdapter(_GCIStub(values=[]), fidelity=tier)
            assert adapter.time_history("phi") is None

    def test_none_for_unknown_or_p1_p2_channel(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(values=_dense_values()), fidelity="dense"
        )
        assert adapter.time_history("P1") is None
        assert adapter.time_history("nonsense") is None


# ---------------------------------------------------------------------------
# 4. noise_history -- must return None uniformly (design's documented
#    asymmetry; scalars() carries the real summary values instead)
# ---------------------------------------------------------------------------


class TestNoiseHistory:
    def test_always_none(self):
        for tier in ("scalars", "profile", "dense"):
            adapter = GradientCoupledAdapter(
                _GCIStub(values=_dense_values()), fidelity=tier
            )
            assert adapter.noise_history() is None
        assert GradientCoupledAdapter(None, fidelity="scalars").noise_history() is None


# ---------------------------------------------------------------------------
# 5. radial_profile -- pure read off .profile
# ---------------------------------------------------------------------------


class TestRadialProfile:
    def test_applies_mpc_conversion(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(profile=_profile_rows(), units=_UnitsStub()), fidelity="profile"
        )
        profile = adapter.radial_profile()
        assert list(profile["r_Mpc"]) == pytest.approx([10.0, 20.0])  # /Mpc(2.0)
        assert list(profile["zeta"]) == pytest.approx([0.1, 0.2])
        assert list(profile["C"]) == pytest.approx([0.2, 0.3])
        assert list(profile["C_bar"]) == pytest.approx([0.15, 0.25])

    def test_none_when_unavailable_or_empty(self):
        assert GradientCoupledAdapter(None, fidelity="scalars").radial_profile() is None
        adapter = GradientCoupledAdapter(_GCIStub(profile=[]), fidelity="scalars")
        assert adapter.radial_profile() is None
        adapter = GradientCoupledAdapter(_GCIStub(failure=True), fidelity="profile")
        assert adapter.radial_profile() is None


# ---------------------------------------------------------------------------
# 6. scalars -- pure read off the eleven parity properties + noise + C_threshold
# ---------------------------------------------------------------------------


class TestScalars:
    def test_reads_parity_properties_and_units_conversion(self):
        units = _UnitsStub()
        adapter = GradientCoupledAdapter(
            _GCIStub(msr_action=3.14, units=units), fidelity="scalars"
        )
        s = adapter.scalars()
        assert s["msr_action"] == 3.14
        assert s["C_peak"] == _PARITY_KWARGS["C_peak"]
        assert s["C_bar_peak"] == _PARITY_KWARGS["C_bar_peak"]
        assert s["C_min"] == _PARITY_KWARGS["C_min"]
        assert s["compensated"] == _PARITY_KWARGS["compensated"]
        assert s["type_II"] == _PARITY_KWARGS["type_II"]
        assert s["V_end_downflow"] == _PARITY_KWARGS["V_end_downflow"]
        assert s["N_end_downflow"] == _PARITY_KWARGS["N_end_downflow"]
        assert s["r_max_Mpc"] == pytest.approx(_PARITY_KWARGS["r_max"] / units.Mpc)
        assert s["r_peak_Mpc"] == pytest.approx(_PARITY_KWARGS["r_peak"] / units.Mpc)
        assert s["M_max_solar"] == pytest.approx(
            _PARITY_KWARGS["M_max"] / units.SolarMass
        )
        assert s["M_peak_solar"] == pytest.approx(
            _PARITY_KWARGS["M_peak"] / units.SolarMass
        )
        assert s["noise_field_min"] == -0.1
        assert s["noise_field_mean"] == 0.0
        assert s["noise_field_max"] == 0.1
        assert s["noise_mom_min"] == -0.2
        assert s["noise_mom_mean"] == 0.0
        assert s["noise_mom_max"] == 0.2
        assert s["C_threshold"] == pytest.approx(0.4)

    def test_all_none_when_unavailable(self):
        adapter = GradientCoupledAdapter(None, fidelity="scalars")
        s = adapter.scalars()
        assert all(v is None for v in s.values())

    def test_all_none_when_failed(self):
        adapter = GradientCoupledAdapter(_GCIStub(failure=True), fidelity="scalars")
        s = adapter.scalars()
        assert all(v is None for v in s.values())

    def test_scalars_available_at_every_fidelity_tier(self):
        """Design §4.1's contract table: scalars are a value at every tier,
        including the cheap 'scalars' fetch."""
        for tier in ("scalars", "profile", "dense"):
            adapter = GradientCoupledAdapter(
                _GCIStub(msr_action=1.0), fidelity=tier
            )
            assert adapter.scalars()["msr_action"] == 1.0


class TestDiagnostics:
    def test_diagnostics(self):
        assert GradientCoupledAdapter(None, fidelity="scalars").diagnostics() is None
        adapter = GradientCoupledAdapter(_GCIStub(), fidelity="scalars")
        assert adapter.diagnostics() == {"converged": True, "outer_iterations": 4}


# ---------------------------------------------------------------------------
# 7. Spatial extension: y_nodes, N_grid, field_2d, derived_at_time
# ---------------------------------------------------------------------------


class TestSpatialExtension:
    def test_y_nodes_from_coords_no_dense_fetch_required(self):
        for tier in ("scalars", "profile", "dense"):
            adapter = GradientCoupledAdapter(_GCIStub(), coords=_COORDS, fidelity=tier)
            expected = LGLCollocationGrid(4).nodes
            assert np.allclose(adapter.y_nodes, expected)

    def test_y_nodes_falls_back_to_object_when_coords_missing(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(n_collocation_points_value=6), coords={}, fidelity="scalars"
        )
        assert np.allclose(adapter.y_nodes, LGLCollocationGrid(6).nodes)

    def test_N_grid(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(values=_dense_values()), coords=_COORDS, fidelity="dense"
        )
        assert list(adapter.N_grid) == [1.0, 2.0]
        assert list(
            GradientCoupledAdapter(None, coords=_COORDS, fidelity="scalars").N_grid
        ) == []

    def test_field_2d_dense_fidelity_returns_expected_shape(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(values=_dense_values()), coords=_COORDS, fidelity="dense"
        )
        y, N, Z = adapter.field_2d("phi")
        assert np.allclose(y, LGLCollocationGrid(4).nodes)
        assert list(N) == [1.0, 2.0]
        assert Z.shape == (2, 4)
        assert list(Z[:, -1]) == [1.0, 5.0]  # core node matches time_history("phi")

    def test_field_2d_unknown_channel_raises_value_error(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(values=_dense_values()), coords=_COORDS, fidelity="dense"
        )
        with pytest.raises(ValueError):
            adapter.field_2d("velocity")  # field_2d uses "pi", not "velocity"

    def test_derived_at_time_wraps_and_propagates(self):
        adapter = GradientCoupledAdapter(
            _GCIStub(values=_dense_values()), coords=_COORDS, fidelity="dense"
        )
        result = adapter.derived_at_time(_EfoldStub(1.5))
        assert result["N"] == 1.5
        assert "zeta" in result and "C" in result

    def test_derived_at_time_raises_when_no_object(self):
        adapter = GradientCoupledAdapter(None, coords=_COORDS, fidelity="scalars")
        with pytest.raises(RuntimeError):
            adapter.derived_at_time(_EfoldStub(1.5))


# ---------------------------------------------------------------------------
# 8. Acceptance test (b): field_2d/derived_at_time raise RuntimeError (not
#    None, not a silent no-op) on scalars/profile-fidelity instances.
# ---------------------------------------------------------------------------


class TestAcceptanceB_RaiseNotNoneOnNonDenseFidelity:
    @pytest.mark.parametrize("tier", ["scalars", "profile"])
    def test_field_2d_raises_runtime_error(self, tier):
        adapter = GradientCoupledAdapter(
            _GCIStub(profile=_profile_rows(), values=[]), coords=_COORDS, fidelity=tier
        )
        with pytest.raises(RuntimeError):
            adapter.field_2d("phi")

    @pytest.mark.parametrize("tier", ["scalars", "profile"])
    def test_derived_at_time_raises_runtime_error(self, tier):
        adapter = GradientCoupledAdapter(
            _GCIStub(profile=_profile_rows(), values=[]), coords=_COORDS, fidelity=tier
        )
        with pytest.raises(RuntimeError):
            adapter.derived_at_time(_EfoldStub(1.5))


# ---------------------------------------------------------------------------
# 9. Acceptance test (a): the five homogeneous P2 figure functions, unchanged,
#    render without error with a GradientCoupledAdapter in the list, at each
#    of the three fidelity tiers.
# ---------------------------------------------------------------------------


class _PotentialStub:
    name = "quadratic"

    def dV_dphi(self, phi):
        return 0.5 * phi

    def H_sq(self, phi, pi):
        return 1.0 + 0.01 * phi**2


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
    def __init__(self, values=None, msr_action=None, units=None):
        self.available = True
        self.failure = False
        self.store_id = 1
        self.values = values or []
        self.msr_action = msr_action
        self.noise_phi1_min = 0.1
        self.noise_phi1_mean = 0.2
        self.noise_phi1_max = 0.3
        self.noise_phi2_min = 0.4
        self.noise_phi2_mean = 0.5
        self.noise_phi2_max = 0.6
        self.diagnostics = {"picard_iterations": 7}
        self.timestamp = None
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(1e-8)
        self._rtol = _ToleranceStub(1e-9)

    def noise_profile_arrays(self):
        if not self.values:
            return None
        N = np.array([v.N.N for v in self.values], dtype=float)
        s1 = np.array([0.5 * abs(v.P1) for v in self.values], dtype=float)
        s2 = np.array([0.25 * abs(v.P2) for v in self.values], dtype=float)
        return {"N": N, "sigma_phi1": s1, "sigma_phi2": s2}


class _SlowRollInstantonStub:
    def __init__(self, values=None, msr_action=None, units=None):
        self.available = True
        self.failure = False
        self.store_id = 2
        self.values = values or []
        self.msr_action = msr_action
        self.noise_phi1_min = 0.05
        self.noise_phi1_mean = 0.15
        self.noise_phi1_max = 0.25
        self.noise_phi2_min = None
        self.noise_phi2_mean = None
        self.noise_phi2_max = None
        self.diagnostics = {"brentq_iterations": 12}
        self.timestamp = None
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(1e-8)
        self._rtol = _ToleranceStub(1e-9)

    def noise_profile_arrays(self):
        if not self.values:
            return None
        N = np.array([v.N.N for v in self.values], dtype=float)
        s1 = np.array([0.4 * abs(v.P1) for v in self.values], dtype=float)
        s2 = np.full_like(N, float("nan"))
        return {"N": N, "sigma_phi1": s1, "sigma_phi2": s2}


def _build_three_way_adapters(gci_fidelity):
    coords = dict(_COORDS)
    gci_values = _dense_values() if gci_fidelity == "dense" else []
    gci_profile = _profile_rows() if gci_fidelity in ("profile", "dense") else []
    gci = _GCIStub(
        values=gci_values, profile=gci_profile, msr_action=1.23, units=_UnitsStub()
    )
    gci_adapter = GradientCoupledAdapter(gci, coords=coords, fidelity=gci_fidelity)

    fi_values = [
        _FullValueStub(N=1.0, phi1=10.0, phi2=1.0, P1=0.1, P2=0.01),
        _FullValueStub(N=2.0, phi1=20.0, phi2=2.0, P1=0.2, P2=0.02),
    ]
    sri_values = [
        _SlowRollValueStub(N=1.0, phi=11.0, P1=0.15),
        _SlowRollValueStub(N=2.0, phi=21.0, P1=0.25),
    ]
    full_adapter = FullInstantonAdapter(
        _FullInstantonStub(values=fi_values, msr_action=1.5, units=_UnitsStub()),
        coords=coords,
    )
    sr_adapter = SlowRollInstantonAdapter(
        _SlowRollInstantonStub(values=sri_values, msr_action=1.6, units=_UnitsStub()),
        coords=coords,
    )
    return [gci_adapter, full_adapter, sr_adapter]


@pytest.fixture
def _no_op_close(monkeypatch):
    monkeypatch.setattr(plt, "close", lambda *a, **k: None)


class TestAcceptanceA_UnchangedFiguresAcceptGCIAdapter:
    @pytest.mark.parametrize("tier", ["scalars", "profile", "dense"])
    def test_time_history(self, tier, tmp_path, _no_op_close):
        adapters = _build_three_way_adapters(tier)
        time_history.plot_instanton_fields(
            adapters, 60.0, 10.0, 5.0, _PotentialStub(), _UnitsStub(), tmp_path, "png"
        )
        fig = plt.gcf()
        phi_labels = [line.get_label() for line in fig.axes[0].get_lines()]
        if tier == "dense":
            assert any("GCI" in lbl for lbl in phi_labels)
        plt.close(fig)

    @pytest.mark.parametrize("tier", ["scalars", "profile", "dense"])
    def test_noise(self, tier, tmp_path, _no_op_close):
        adapters = _build_three_way_adapters(tier)
        noise.plot_noise_profile(adapters, 60.0, 10.0, 5.0, "quadratic", tmp_path, "png")
        plt.close(plt.gcf())

    @pytest.mark.parametrize("tier", ["scalars", "profile", "dense"])
    def test_compaction(self, tier, tmp_path, _no_op_close):
        adapters = _build_three_way_adapters(tier)
        compaction.plot_zeta_and_compaction(
            adapters, 60.0, 10.0, 5.0, "quadratic", tmp_path, "png"
        )
        fig = plt.gcf()
        if tier in ("profile", "dense"):
            zeta_labels = [line.get_label() for line in fig.axes[0].get_lines()]
            assert any("GCI" in lbl for lbl in zeta_labels)
        plt.close(fig)

    @pytest.mark.parametrize("tier", ["scalars", "profile", "dense"])
    def test_sweeps(self, tier, tmp_path, _no_op_close):
        adapters = _build_three_way_adapters(tier)
        sweeps.plot_msr_action_sweep(
            adapters, "x", "fixed", "quadratic", tmp_path, "png", "N_init"
        )
        fig = plt.gcf()
        labels = [line.get_label() for line in fig.axes[0].get_lines()]
        assert any("GCI" in lbl for lbl in labels)
        plt.close(fig)

        sweeps.plot_compaction_summary(
            adapters, "x", "fixed", "quadratic", tmp_path, "png", "N_init"
        )
        plt.close(plt.gcf())

    @pytest.mark.parametrize("tier", ["scalars", "profile", "dense"])
    def test_doe(self, tier, tmp_path):
        adapters = _build_three_way_adapters(tier)
        points = [{"delta_Nstar": 5.0, "delta_N": 50.0, "adapters": adapters}]
        doe.plot_doe_scalar_summary(points, "quadratic", tmp_path, "png")
        assert (tmp_path / "doe_compaction_action.png").exists()
