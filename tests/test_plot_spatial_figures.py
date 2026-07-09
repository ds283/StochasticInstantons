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
Acceptance test for Prompt P5a
(.prompts/gradient-coupled-plotting/09-P5a-spatial-figures-static.md):
`plotting.figures.spatial`'s heatmap + slice-overlay figures.

Follows the duck-typed-stand-in convention set by
tests/test_plot_gradient_adapter.py (P4) rather than driving a live Ray
cluster/datastore.
"""

from pathlib import Path

import numpy as np
import pytest
from matplotlib import pyplot as plt

import plotting.figures.spatial as spatial
from plotting.adapters.gradient import GradientCoupledAdapter

# ---------------------------------------------------------------------------
# Duck-typed stand-ins (mirrors tests/test_plot_gradient_adapter.py)
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
    """One dense sample row: each field a per-node list ordered y=-1..+1
    (core node is index -1)."""

    def __init__(self, N, phi, pi, rfield, rmom):
        self.N = _EfoldStub(N)
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
    the surface `GradientCoupledAdapter` reads (see
    tests/test_plot_gradient_adapter.py's own `_GCIStub`)."""

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


class _FullValueStub:
    def __init__(self, N, phi1, phi2, P1, P2):
        self.N = _EfoldStub(N)
        self.phi1 = phi1
        self.phi2 = phi2
        self.P1 = P1
        self.P2 = P2


class _FullInstantonAdapterStub:
    """A minimal non-spatial InstantonAdapter stand-in: exposes exactly the
    surface `plot_spatial_slices`' non-spatial branch reads
    (`available`/`failure`/`is_spatial`/`time_history`/`display_label`/
    `line_style`), without pulling in the real FullInstantonAdapter's own
    dependency chain."""

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


def _dense_values():
    # 4 collocation nodes; core node is the last entry of each per-node list.
    return [
        _GCIValueStub(
            N=1.0,
            phi=[0.1, 0.2, 0.3, 1.0],
            pi=[0.0, 0.0, 0.0, 2.0],
            rfield=[0.0, 0.0, 0.0, 3.0],
            rmom=[0.0, 0.0, 0.0, 4.0],
        ),
        _GCIValueStub(
            N=2.0,
            phi=[0.2, 0.3, 0.4, 5.0],
            pi=[0.0, 0.0, 0.0, 6.0],
            rfield=[0.0, 0.0, 0.0, 7.0],
            rmom=[0.0, 0.0, 0.0, 8.0],
        ),
        _GCIValueStub(
            N=3.0,
            phi=[0.3, 0.4, 0.5, 9.0],
            pi=[0.0, 0.0, 0.0, 10.0],
            rfield=[0.0, 0.0, 0.0, 11.0],
            rmom=[0.0, 0.0, 0.0, 12.0],
        ),
    ]


def _dense_gci_adapter():
    gci = _GCIStub(values=_dense_values(), units=_UnitsStub())
    return GradientCoupledAdapter(gci, coords=_COORDS, fidelity="dense")


def _non_dense_gci_adapter(tier):
    gci = _GCIStub(values=[], profile=[], units=_UnitsStub())
    return GradientCoupledAdapter(gci, coords=_COORDS, fidelity=tier)


@pytest.fixture
def _no_op_close(monkeypatch):
    monkeypatch.setattr(plt, "close", lambda *a, **k: None)


# ---------------------------------------------------------------------------
# Acceptance test (a): both figures render without error for a converged
# dense-fidelity GCI fixture, alone and overlaid with a non-spatial adapter.
# ---------------------------------------------------------------------------


class TestAcceptanceA_RendersForDenseFidelity:
    def test_heatmaps_render(self, tmp_path, _no_op_close):
        adapters = [_dense_gci_adapter()]
        spatial.plot_spatial_heatmaps(adapters, tmp_path, "png")
        assert (tmp_path / "spatial_heatmaps.png").exists()

    def test_slices_render(self, tmp_path, _no_op_close):
        adapters = [_dense_gci_adapter()]
        spatial.plot_spatial_slices(adapters, tmp_path, "png")
        assert (tmp_path / "spatial_slices.png").exists()

    def test_slices_overlay_core_node_against_full_instanton(self, tmp_path, _no_op_close):
        """The core (y=+1) y-slice must overlay cleanly against a
        FullInstantonAdapter-like adapter's own time_history("phi") when one
        is present in the passed adapters list (design §6.2 item 2)."""
        full_adapter = _FullInstantonAdapterStub(N=[1.0, 2.0, 3.0], phi1=[1.5, 2.5, 3.5])
        adapters = [_dense_gci_adapter(), full_adapter]
        spatial.plot_spatial_slices(adapters, tmp_path, "png")
        fig = plt.gcf()
        y_slice_ax = fig.axes[1]
        labels = [line.get_label() for line in y_slice_ax.get_lines()]
        assert any("core" in lbl for lbl in labels)
        assert any("Full" in lbl and "homogeneous" in lbl for lbl in labels)
        plt.close(fig)

    def test_heatmaps_have_four_panels_with_provenance(self, tmp_path, _no_op_close):
        spatial.plot_spatial_heatmaps([_dense_gci_adapter()], tmp_path, "png")
        fig = plt.gcf()
        assert len(fig.axes) >= 4  # 4 pcolormesh axes + colorbars
        footer_texts = [t.get_text() for t in fig.texts]
        assert any("StochasticInstanton" in t for t in footer_texts)
        plt.close(fig)


# ---------------------------------------------------------------------------
# Acceptance test (b): both figures are skipped (no file, no exception) when
# passed only non-spatial adapters or a non-dense-fidelity GCI adapter.
# ---------------------------------------------------------------------------


class TestAcceptanceB_SkipsWithoutSpatialData:
    @pytest.mark.parametrize("fn_name", ["plot_spatial_heatmaps", "plot_spatial_slices"])
    def test_skips_with_no_gci_present(self, fn_name, tmp_path):
        full_adapter = _FullInstantonAdapterStub(N=[1.0, 2.0], phi1=[1.0, 2.0])
        fn = getattr(spatial, fn_name)
        fn([full_adapter], tmp_path, "png")
        assert list(tmp_path.iterdir()) == []

    @pytest.mark.parametrize("fn_name", ["plot_spatial_heatmaps", "plot_spatial_slices"])
    @pytest.mark.parametrize("tier", ["scalars", "profile"])
    def test_skips_with_non_dense_gci(self, fn_name, tier, tmp_path):
        fn = getattr(spatial, fn_name)
        fn([_non_dense_gci_adapter(tier)], tmp_path, "png")
        assert list(tmp_path.iterdir()) == []

    def test_field_2d_never_called_without_spatial_gate(self, tmp_path):
        """Belt-and-braces: even if the guard were somehow bypassed,
        field_2d on a non-dense adapter raises RuntimeError rather than
        returning None -- confirms the guard is load-bearing, not
        incidental."""
        adapter = _non_dense_gci_adapter("profile")
        with pytest.raises(RuntimeError):
            adapter.field_2d("phi")


# ---------------------------------------------------------------------------
# Task 3: Ray-dispatch wiring -- proxy-passing caveat (design §5).
# `._function` escape hatch, per tests/test_plot_extraction_golden.py's
# TestRenderItemGeneric convention: worker-side imports aren't reachable
# from a pytest-collected module, so exercise the undecorated body directly
# rather than a real cross-process `.remote()` dispatch.
# ---------------------------------------------------------------------------


class _GCIProxyStub:
    def __init__(self, gci):
        self._gci = gci

    def get(self):
        return self._gci


class TestRayDispatchWiring:
    def test_heatmaps_item_is_a_ray_remote_function(self):
        assert hasattr(spatial._render_spatial_heatmaps_item, "remote")

    def test_slices_item_is_a_ray_remote_function(self):
        assert hasattr(spatial._render_spatial_slices_item, "remote")

    def test_heatmaps_item_builds_adapter_from_proxy_worker_side(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            spatial,
            "plot_spatial_heatmaps",
            lambda adapters, output_dir, fmt, run_label="": calls.append(
                (adapters, output_dir, fmt, run_label)
            ),
        )
        proxy = _GCIProxyStub(_GCIStub(values=_dense_values(), units=_UnitsStub()))
        spatial._render_spatial_heatmaps_item._function(
            proxy, _COORDS, [], str(tmp_path), "png", "run-label"
        )
        assert len(calls) == 1
        adapters, output_dir, fmt, run_label = calls[0]
        assert len(adapters) == 1
        assert isinstance(adapters[0], GradientCoupledAdapter)
        assert adapters[0].is_spatial() is True
        assert output_dir == Path(tmp_path)
        assert fmt == "png"
        assert run_label == "run-label"

    def test_slices_item_passes_through_other_adapters(self, monkeypatch, tmp_path):
        calls = []
        monkeypatch.setattr(
            spatial,
            "plot_spatial_slices",
            lambda adapters, output_dir, fmt, run_label="": calls.append(adapters),
        )
        full_adapter = _FullInstantonAdapterStub(N=[1.0], phi1=[1.0])
        proxy = _GCIProxyStub(_GCIStub(values=_dense_values(), units=_UnitsStub()))
        spatial._render_spatial_slices_item._function(
            proxy, _COORDS, [full_adapter], str(tmp_path), "png", ""
        )
        adapters = calls[0]
        assert len(adapters) == 2
        assert isinstance(adapters[0], GradientCoupledAdapter)
        assert adapters[1] is full_adapter
