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
Acceptance test for Prompt P5b
(.prompts/gradient-coupled-plotting/10-P5b-spatial-figures-movies.md):
`plotting.figures.spatial`'s opt-in `(y,N)` and derived (zeta(r)/C(r))
movies.

Follows the duck-typed-stand-in convention set by
tests/test_plot_spatial_figures.py (P5a) / tests/test_plot_gradient_adapter.py
(P4) rather than driving a live Ray cluster/datastore.
"""

import shutil
from pathlib import Path

import numpy as np
import pytest
from matplotlib import pyplot as plt

import plotting.figures.spatial as spatial
from plotting.adapters.gradient import GradientCoupledAdapter

# ---------------------------------------------------------------------------
# Duck-typed stand-ins (mirrors tests/test_plot_spatial_figures.py, plus a
# zeta_C_r_at_time stub for the derived movie, mirroring
# tests/test_plot_gradient_adapter.py's own _GCIStub).
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
    """Duck-typed `efold_value` stand-in: carries a distinct `store_id` so
    zeta_C_r_at_time's identity-based cache key
    (self.store_id, N_query.store_id) behaves like the real thing."""

    def __init__(self, N, store_id):
        self.N = N
        self.store_id = store_id


class _GCIValueStub:
    """One dense sample row: each field a per-node list ordered y=-1..+1
    (core node is index -1)."""

    def __init__(self, N_obj, phi, pi, rfield, rmom):
        self.N = N_obj
        self.phi = phi
        self.pi = pi
        self.rfield = rfield
        self.rmom = rmom


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
    the surface `GradientCoupledAdapter` reads, plus `zeta_C_r_at_time` for
    `derived_at_time`."""

    def __init__(
        self,
        available=True,
        failure=False,
        store_id=1,
        values=None,
        profile=None,
        msr_action=1.0,
        timestamp=None,
        units=None,
        n_collocation_points_value=4,
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
        self.diagnostics = {"converged": True}
        self.timestamp = timestamp
        self.n_collocation_points_value = n_collocation_points_value
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(1e-8)
        self._rtol = _ToleranceStub(1e-9)
        for key, value in _PARITY_KWARGS.items():
            setattr(self, key, value)

    def zeta_C_r_at_time(self, N_query):
        """Mirrors the real method's cache-key contract (keyed on
        N_query.store_id) closely enough to prove distinct frames are not
        silently collapsed onto the same result: returns data that is a
        deterministic function of N_query.store_id."""
        if not self.values:
            raise RuntimeError(
                "GradientCoupledInstanton.zeta_C_r_at_time: this instance "
                "has no stored per-sample values."
            )
        s = float(N_query.store_id)
        return {
            "N": N_query.N,
            "zeta": np.array([0.1, 0.2]) * s,
            "r_ratio": np.array([0.5, 1.0]),
            "C": np.array([0.2, 0.3]) * s,
            "r_phys": np.array([1.0, 2.0]),
            "failure_mask": np.array([False, False]),
        }


class _FullValueStub:
    def __init__(self, N, phi1, phi2, P1, P2):
        self.N = N
        self.phi1 = phi1
        self.phi2 = phi2
        self.P1 = P1
        self.P2 = P2


class _FullInstantonAdapterStub:
    kind = "full"
    display_label = "Full"
    line_style = "-"
    marker = "o"

    def __init__(self, N, phi1):
        self.available = True
        self.failure = False
        self._N = np.array(N, dtype=float)
        self._phi1 = np.array(phi1, dtype=float)

    def is_spatial(self):
        return False

    def time_history(self, channel):
        if channel != "phi":
            return None
        return self._N, self._phi1


_COORDS = {
    "N_init": 60.0,
    "N_final": 10.0,
    "delta_Nstar": 5.0,
    "alpha": 0.05,
    "n_collocation_points": 4,
}


def _dense_values(n=5):
    """n dense sample rows (default 5, for the "short 5-frame movie"
    acceptance bar), 4 collocation nodes; core node is the last entry of
    each per-node list. Each row's efold_value carries a distinct store_id
    (1, 2, 3, ...) so zeta_C_r_at_time's cache-key contract can be
    exercised meaningfully."""
    rows = []
    for i in range(1, n + 1):
        N_obj = _EfoldStub(N=float(i), store_id=100 + i)
        rows.append(
            _GCIValueStub(
                N_obj,
                phi=[0.1 * i, 0.2 * i, 0.3 * i, 1.0 * i],
                pi=[0.0, 0.0, 0.0, 2.0 * i],
                rfield=[0.0, 0.0, 0.0, 3.0 * i],
                rmom=[0.0, 0.0, 0.0, 4.0 * i],
            )
        )
    return rows


def _dense_gci_adapter(n=5):
    gci = _GCIStub(values=_dense_values(n), units=_UnitsStub())
    return GradientCoupledAdapter(gci, coords=_COORDS, fidelity="dense"), gci


def _non_dense_gci_adapter(tier):
    gci = _GCIStub(values=[], profile=[], units=_UnitsStub())
    return GradientCoupledAdapter(gci, coords=_COORDS, fidelity=tier)


def _frame_N_objects(gci):
    return [v.N for v in gci.values]


@pytest.fixture
def _no_op_close(monkeypatch):
    monkeypatch.setattr(plt, "close", lambda *a, **k: None)


_HAS_FFMPEG = shutil.which("ffmpeg") is not None


# ---------------------------------------------------------------------------
# Acceptance test (a): a short (5-frame) movie renders without error for a
# converged dense-fidelity GCI test fixture in gif format (Pillow-only).
# ---------------------------------------------------------------------------


class TestAcceptanceA_RendersGifForDenseFidelity:
    def test_field_movie_renders_gif(self, tmp_path, _no_op_close):
        adapter, _ = _dense_gci_adapter()
        spatial.plot_spatial_field_movie([adapter], tmp_path, movie_format="gif")
        assert (tmp_path / "spatial_field_movie.gif").exists()

    def test_derived_movie_renders_gif(self, tmp_path, _no_op_close):
        adapter, gci = _dense_gci_adapter()
        spatial.plot_spatial_derived_movie(
            [adapter], _frame_N_objects(gci), tmp_path, movie_format="gif"
        )
        assert (tmp_path / "spatial_derived_movie.gif").exists()

    def test_field_movie_n_frames_caps_frame_count(self, tmp_path, _no_op_close, monkeypatch):
        captured = {}

        def _fake_save(anim, fname, movie_format):
            captured["n"] = anim._save_count

        monkeypatch.setattr(spatial, "_save_movie", _fake_save)
        adapter, _ = _dense_gci_adapter(n=5)
        spatial.plot_spatial_field_movie(
            [adapter], tmp_path, movie_format="gif", n_frames=3
        )
        # +1 for the opening title-card frame.
        assert captured["n"] == 4

    def test_derived_movie_n_frames_caps_frame_count(self, tmp_path, _no_op_close, monkeypatch):
        captured = {}

        def _fake_save(anim, fname, movie_format):
            captured["n"] = anim._save_count

        monkeypatch.setattr(spatial, "_save_movie", _fake_save)
        adapter, gci = _dense_gci_adapter(n=5)
        spatial.plot_spatial_derived_movie(
            [adapter], _frame_N_objects(gci), tmp_path, movie_format="gif", n_frames=3
        )
        assert captured["n"] == 4


# ---------------------------------------------------------------------------
# Acceptance test (b): mp4 path -- skipped/xfail if ffmpeg is not present on
# the test runner (Decision point: gif is Pillow-only/always-available;
# mp4 is opt-in and requires ffmpeg).
# ---------------------------------------------------------------------------


class TestAcceptanceB_Mp4Path:
    @pytest.mark.skipif(not _HAS_FFMPEG, reason="ffmpeg not installed on test runner")
    def test_field_movie_renders_mp4_when_ffmpeg_available(self, tmp_path, _no_op_close):
        adapter, _ = _dense_gci_adapter()
        spatial.plot_spatial_field_movie([adapter], tmp_path, movie_format="mp4")
        assert (tmp_path / "spatial_field_movie.mp4").exists()

    @pytest.mark.skipif(_HAS_FFMPEG, reason="ffmpeg IS installed -- this checks the missing-ffmpeg path")
    def test_mp4_raises_clear_error_when_ffmpeg_missing(self, tmp_path, _no_op_close):
        adapter, _ = _dense_gci_adapter()
        with pytest.raises(RuntimeError, match="ffmpeg"):
            spatial.plot_spatial_field_movie([adapter], tmp_path, movie_format="mp4")

    def test_unknown_movie_format_raises(self, tmp_path, _no_op_close):
        adapter, _ = _dense_gci_adapter()
        with pytest.raises(ValueError):
            spatial.plot_spatial_field_movie([adapter], tmp_path, movie_format="webm")


# ---------------------------------------------------------------------------
# Acceptance test (c): both movies are skipped (no file, no exception) when
# passed only non-spatial adapters or a non-dense-fidelity GCI adapter --
# same guard contract as P5a's static figures.
# ---------------------------------------------------------------------------


class TestAcceptanceC_SkipsWithoutSpatialData:
    def test_field_movie_skips_with_no_gci_present(self, tmp_path):
        full_adapter = _FullInstantonAdapterStub(N=[1.0, 2.0], phi1=[1.0, 2.0])
        spatial.plot_spatial_field_movie([full_adapter], tmp_path, movie_format="gif")
        assert list(tmp_path.iterdir()) == []

    def test_derived_movie_skips_with_no_gci_present(self, tmp_path):
        full_adapter = _FullInstantonAdapterStub(N=[1.0, 2.0], phi1=[1.0, 2.0])
        spatial.plot_spatial_derived_movie(
            [full_adapter], [_EfoldStub(1.0, 101)], tmp_path, movie_format="gif"
        )
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.parametrize("tier", ["scalars", "profile"])
    def test_field_movie_skips_with_non_dense_gci(self, tier, tmp_path):
        adapter = _non_dense_gci_adapter(tier)
        spatial.plot_spatial_field_movie([adapter], tmp_path, movie_format="gif")
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.parametrize("tier", ["scalars", "profile"])
    def test_derived_movie_skips_with_non_dense_gci(self, tier, tmp_path):
        adapter = _non_dense_gci_adapter(tier)
        spatial.plot_spatial_derived_movie(
            [adapter], [_EfoldStub(1.0, 101)], tmp_path, movie_format="gif"
        )
        assert list(tmp_path.iterdir()) == []

    def test_derived_movie_skips_with_empty_frame_list(self, tmp_path):
        adapter, _ = _dense_gci_adapter()
        spatial.plot_spatial_derived_movie([adapter], [], tmp_path, movie_format="gif")
        assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# Task 3: persistent per-frame provenance + opening title card (design §9
# item 3). Verifies the callback burns the footer into every frame and the
# opening frame carries the same string as a title card, WITHOUT calling
# `_provenance_footer` (which cannot survive FuncAnimation's frame-by-frame
# rendering -- see plotting/figures/spatial.py's module docstring).
# ---------------------------------------------------------------------------


class TestMovieProvenance:
    def _capture_anim(self, monkeypatch):
        captured = []
        monkeypatch.setattr(
            spatial, "_save_movie", lambda anim, fname, movie_format: captured.append(anim)
        )
        return captured

    def test_field_movie_never_calls_provenance_footer(self, tmp_path, _no_op_close, monkeypatch):
        calls = []
        monkeypatch.setattr(
            spatial, "_provenance_footer", lambda *a, **k: calls.append(1)
        )
        adapter, _ = _dense_gci_adapter()
        spatial.plot_spatial_field_movie([adapter], tmp_path, movie_format="gif")
        assert calls == []

    def test_derived_movie_never_calls_provenance_footer(self, tmp_path, _no_op_close, monkeypatch):
        calls = []
        monkeypatch.setattr(
            spatial, "_provenance_footer", lambda *a, **k: calls.append(1)
        )
        adapter, gci = _dense_gci_adapter()
        spatial.plot_spatial_derived_movie(
            [adapter], _frame_N_objects(gci), tmp_path, movie_format="gif"
        )
        assert calls == []

    def test_field_movie_opening_frame_is_title_card_with_data_hidden(
        self, tmp_path, monkeypatch
    ):
        captured = self._capture_anim(monkeypatch)
        adapter, _ = _dense_gci_adapter()
        spatial.plot_spatial_field_movie([adapter], tmp_path, movie_format="gif")
        anim = captured[0]
        anim._func(0)
        fig = anim._fig
        texts = [t for t in fig.texts if t.get_text()]
        assert any("StochasticInstanton" in t.get_text() for t in texts)
        lines = [ln for ax in fig.axes for ln in ax.get_lines()]
        assert all(not ln.get_visible() for ln in lines)
        plt.close(fig)

    def test_field_movie_data_frame_keeps_persistent_footer(self, tmp_path, monkeypatch):
        captured = self._capture_anim(monkeypatch)
        adapter, _ = _dense_gci_adapter()
        spatial.plot_spatial_field_movie([adapter], tmp_path, movie_format="gif")
        anim = captured[0]
        anim._func(1)
        fig = anim._fig
        texts = [t for t in fig.texts if t.get_text()]
        assert any("StochasticInstanton" in t.get_text() for t in texts)
        lines = [ln for ax in fig.axes for ln in ax.get_lines()]
        assert any(ln.get_visible() for ln in lines)
        plt.close(fig)

    def test_derived_movie_opening_frame_is_title_card_with_data_hidden(
        self, tmp_path, monkeypatch
    ):
        captured = self._capture_anim(monkeypatch)
        adapter, gci = _dense_gci_adapter()
        spatial.plot_spatial_derived_movie(
            [adapter], _frame_N_objects(gci), tmp_path, movie_format="gif"
        )
        anim = captured[0]
        anim._func(0)
        fig = anim._fig
        texts = [t for t in fig.texts if t.get_text()]
        assert any("StochasticInstanton" in t.get_text() for t in texts)
        lines = [ln for ax in fig.axes for ln in ax.get_lines()]
        assert all(not ln.get_visible() for ln in lines)
        plt.close(fig)

    def test_derived_movie_frames_are_not_collapsed_by_cache_key(self, tmp_path, monkeypatch):
        """Distinct frames must query zeta_C_r_at_time with distinct,
        real store_id-bearing efold objects -- not synthetic stand-ins that
        would collide on the (self.store_id, N_query.store_id) cache key
        and silently repeat the first frame's result."""
        captured = self._capture_anim(monkeypatch)
        adapter, gci = _dense_gci_adapter()
        spatial.plot_spatial_derived_movie(
            [adapter], _frame_N_objects(gci), tmp_path, movie_format="gif"
        )
        anim = captured[0]
        fig = anim._fig
        anim._func(1)
        line_zeta_frame1 = fig.axes[0].get_lines()[0].get_ydata().copy()
        anim._func(2)
        line_zeta_frame2 = fig.axes[0].get_lines()[0].get_ydata().copy()
        assert not np.allclose(line_zeta_frame1, line_zeta_frame2)
        plt.close(fig)


# ---------------------------------------------------------------------------
# Task 5: Ray-dispatch wiring -- render inside the Ray worker, from the
# proxy, exactly as P5a's static figures do.
# ---------------------------------------------------------------------------


class _GCIProxyStub:
    def __init__(self, gci):
        self._gci = gci

    def get(self):
        return self._gci


class TestRayDispatchWiring:
    def test_field_movie_item_is_a_ray_remote_function(self):
        assert hasattr(spatial._render_spatial_field_movie_item, "remote")

    def test_derived_movie_item_is_a_ray_remote_function(self):
        assert hasattr(spatial._render_spatial_derived_movie_item, "remote")

    def test_field_movie_item_builds_adapter_from_proxy_worker_side(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            spatial,
            "plot_spatial_field_movie",
            lambda adapters, output_dir, movie_format="gif", run_label="", n_frames=None: calls.append(
                (adapters, output_dir, movie_format, run_label, n_frames)
            ),
        )
        _, gci = _dense_gci_adapter()
        proxy = _GCIProxyStub(gci)
        spatial._render_spatial_field_movie_item._function(
            proxy, _COORDS, str(tmp_path), "gif", "run-label", 3
        )
        assert len(calls) == 1
        adapters, output_dir, movie_format, run_label, n_frames = calls[0]
        assert len(adapters) == 1
        assert isinstance(adapters[0], GradientCoupledAdapter)
        assert adapters[0].is_spatial() is True
        assert output_dir == Path(tmp_path)
        assert movie_format == "gif"
        assert run_label == "run-label"
        assert n_frames == 3

    def test_derived_movie_item_sources_real_efold_objects_from_raw_values(
        self, monkeypatch, tmp_path
    ):
        """Confirms the wrapper passes the GCI's own real `.N` efold
        objects (with valid store_ids), not synthetic stand-ins -- required
        for zeta_C_r_at_time's cache-key contract."""
        calls = []
        monkeypatch.setattr(
            spatial,
            "plot_spatial_derived_movie",
            lambda adapters, frame_N_objects, output_dir, movie_format="gif", run_label="", n_frames=None: calls.append(
                (adapters, frame_N_objects, output_dir, movie_format, run_label, n_frames)
            ),
        )
        _, gci = _dense_gci_adapter(n=5)
        proxy = _GCIProxyStub(gci)
        spatial._render_spatial_derived_movie_item._function(
            proxy, _COORDS, str(tmp_path), "gif", "", None
        )
        assert len(calls) == 1
        adapters, frame_N_objects, output_dir, movie_format, run_label, n_frames = calls[0]
        assert isinstance(adapters[0], GradientCoupledAdapter)
        assert [obj.store_id for obj in frame_N_objects] == [v.N.store_id for v in gci.values]
        assert output_dir == Path(tmp_path)
