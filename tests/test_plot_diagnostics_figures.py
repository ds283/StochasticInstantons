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
Acceptance test for Prompt P7
(.prompts/gradient-coupled-plotting/12-P7-diagnostics-figures.md):
`plotting.figures.diagnostics`'s nine diagnostics figure families, plus
`plotting.fetch.flatten_diagnostics_for_csv`'s `diagnostics_data.csv`
companion (item 9).

Follows the duck-typed-stand-in convention set by
tests/test_plot_adapters_golden.py (P2) and tests/test_plot_spatial_figures.py
(P5a) rather than driving a live Ray cluster/datastore -- this prompt's
acceptance test only needs a "mixed fixture set" of adapters, not a real
populated database.
"""

import pytest
from matplotlib import pyplot as plt

import plotting.figures.diagnostics as diagnostics
from plotting.adapters.full import FullInstantonAdapter
from plotting.adapters.gradient import GradientCoupledAdapter
from plotting.adapters.slow_roll import SlowRollInstantonAdapter
from plotting.fetch import flatten_diagnostics_for_csv, flatten_doe_points_for_csv

# ---------------------------------------------------------------------------
# Duck-typed stand-ins (mirrors tests/test_plot_adapters_golden.py,
# tests/test_plot_spatial_figures.py)
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


_SHARED_COORDS = {"N_init": 60.0, "N_final": 10.0, "delta_Nstar": 5.0}
_OTHER_COORDS = {"N_init": 61.0, "N_final": 11.0, "delta_Nstar": 6.0}


class _FullInstantonStub:
    def __init__(self, diagnostics_dict, units=None):
        self.available = True
        self.failure = False
        self.store_id = 1
        self.values = []
        self.msr_action = 1.0
        self.noise_phi1_min = self.noise_phi1_mean = self.noise_phi1_max = None
        self.noise_phi2_min = self.noise_phi2_mean = self.noise_phi2_max = None
        self.diagnostics = diagnostics_dict
        self.timestamp = None
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(1e-8)
        self._rtol = _ToleranceStub(1e-9)


class _SlowRollInstantonStub:
    def __init__(self, diagnostics_dict, units=None):
        self.available = True
        self.failure = False
        self.store_id = 2
        self.values = []
        self.msr_action = 0.5
        self.noise_phi1_min = self.noise_phi1_mean = self.noise_phi1_max = None
        self.noise_phi2_min = self.noise_phi2_mean = self.noise_phi2_max = None
        self.diagnostics = diagnostics_dict
        self.timestamp = None
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(1e-8)
        self._rtol = _ToleranceStub(1e-9)


_PARITY_KWARGS = dict(
    C_peak=0.5, C_bar_peak=0.3, C_min=-0.2, compensated=True, type_II=False,
    r_max=10.0, r_peak=4.0, M_max=15.0, M_peak=25.0,
    V_end_downflow=1e-9, N_end_downflow=0.05,
)


class _GCIStub:
    """Duck-typed stand-in for `GradientCoupledInstanton` (mirrors
    tests/test_plot_gradient_adapter.py's / tests/test_plot_spatial_figures.py's
    own `_GCIStub`)."""

    def __init__(self, diagnostics_dict, units=None, n_collocation_points_value=4):
        self.available = True
        self.failure = diagnostics_dict.get("converged") is False
        self.store_id = 3
        self.values = []
        self.profile = []
        self.msr_action = 2.0
        self.noise_field_min = self.noise_field_mean = self.noise_field_max = None
        self.noise_mom_min = self.noise_mom_mean = self.noise_mom_max = None
        self.diagnostics = diagnostics_dict
        self.timestamp = None
        self.n_collocation_points_value = n_collocation_points_value
        self._trajectory = _TrajProxyStub(units)
        self._atol = _ToleranceStub(1e-8)
        self._rtol = _ToleranceStub(1e-9)
        for key, value in _PARITY_KWARGS.items():
            setattr(self, key, value)


def _full_adapter(diag, coords=_SHARED_COORDS):
    return FullInstantonAdapter(_FullInstantonStub(diag, units=_UnitsStub()), coords=dict(coords))


def _sr_adapter(diag, coords=_SHARED_COORDS):
    return SlowRollInstantonAdapter(_SlowRollInstantonStub(diag, units=_UnitsStub()), coords=dict(coords))


def _gci_adapter(diag, coords, fidelity="dense", n_collocation_points_value=4):
    gci = _GCIStub(diag, units=_UnitsStub(), n_collocation_points_value=n_collocation_points_value)
    return GradientCoupledAdapter(gci, coords=dict(coords), fidelity=fidelity)


# ---------------------------------------------------------------------------
# Fixture: a mixed adapter set spanning FullInstanton, SlowRollInstanton, and
# GradientCoupledInstanton, including one non-converged GCI record.
# ---------------------------------------------------------------------------


@pytest.fixture
def mixed_adapters():
    full = _full_adapter(
        {
            "compute_time": 12.0, "converged": True, "final_residual": 1e-9,
            "total_ode_solves": 340, "outer_iterations": 5,
            "newton_fallback_count": 0, "final_lambda": 1.23,
            "mean_picard_iterations": 3.5,
        },
        coords=_SHARED_COORDS,
    )
    sr = _sr_adapter(
        {
            "compute_time": 3.0, "converged": True, "final_residual": 1e-10,
            "total_ode_solves": 50,
        },
        coords=_SHARED_COORDS,
    )
    gci_coords_a = {**_SHARED_COORDS, "alpha": 0.05, "n_collocation_points": 4}
    gci_converged = _gci_adapter(
        {
            "compute_time": 40.0, "compute_time_total": 45.0, "converged": True,
            "final_residual": 1e-8, "total_ode_solves": 900,
            "outer_iterations": 8, "newton_fallback_count": 1,
            "final_lambda": 2.5, "mean_picard_iterations": 4.2,
            "rk45_forward_steps_per_efold": 120.0,
            "rk45_backward_steps_per_efold": 340.0,
            "extraction_failure_mask": [False, False, True, False],
        },
        coords=gci_coords_a,
    )
    gci_coords_b = {**_OTHER_COORDS, "alpha": 0.05, "n_collocation_points": 4}
    gci_nonconverged = _gci_adapter(
        {
            "compute_time": 20.0, "compute_time_total": 22.0, "converged": False,
            "final_residual": 3.0, "total_ode_solves": 400,
            "outer_iterations": 50, "newton_fallback_count": 3,
            "final_lambda": None, "mean_picard_iterations": 6.0,
            "rk45_forward_steps_per_efold": 200.0,
            "rk45_backward_steps_per_efold": 600.0,
            "extraction_failure_mask": [False, True, True, True],
        },
        coords=gci_coords_b,
    )
    return [full, sr, gci_converged, gci_nonconverged]


@pytest.fixture
def _no_op_close(monkeypatch):
    monkeypatch.setattr(plt, "close", lambda *a, **k: None)


# ---------------------------------------------------------------------------
# Acceptance test: all nine figure families render without error against the
# mixed fixture set (items 2-8), plus the CSV emission (item 9).
# ---------------------------------------------------------------------------


class TestAcceptance_AllNineFamiliesRender:
    def test_compute_time_distributions(self, mixed_adapters, tmp_path, _no_op_close):
        diagnostics.plot_compute_time_distributions(mixed_adapters, "TestPotential", tmp_path, "png")
        assert (tmp_path / "diagnostics_compute_time_distributions.png").exists()

    def test_cost_vs_parameters(self, mixed_adapters, tmp_path, _no_op_close):
        diagnostics.plot_cost_vs_parameters(mixed_adapters, "TestPotential", tmp_path, "png")
        assert (tmp_path / "diagnostics_cost_vs_parameters.png").exists()

    def test_convergence_map(self, mixed_adapters, tmp_path, _no_op_close):
        diagnostics.plot_convergence_map(mixed_adapters, "TestPotential", tmp_path, "png")
        assert (tmp_path / "diagnostics_convergence_map.png").exists()

    def test_speedup(self, mixed_adapters, tmp_path, _no_op_close):
        diagnostics.plot_speedup(mixed_adapters, "TestPotential", tmp_path, "png")
        assert (tmp_path / "diagnostics_speedup.png").exists()

    def test_picard_newton_structure(self, mixed_adapters, tmp_path, _no_op_close):
        diagnostics.plot_picard_newton_structure(mixed_adapters, "TestPotential", tmp_path, "png")
        assert (tmp_path / "diagnostics_picard_newton_structure.png").exists()

    def test_stiffness(self, mixed_adapters, tmp_path, _no_op_close):
        diagnostics.plot_stiffness(mixed_adapters, "TestPotential", tmp_path, "png")
        assert (tmp_path / "diagnostics_stiffness.png").exists()

    def test_extraction_failure_summary(self, mixed_adapters, tmp_path, _no_op_close):
        diagnostics.plot_extraction_failure_summary(mixed_adapters, "TestPotential", tmp_path, "png")
        assert (tmp_path / "diagnostics_extraction_failure_summary.png").exists()

    def test_extraction_failure_heatmap(self, mixed_adapters, tmp_path, _no_op_close):
        diagnostics.plot_extraction_failure_heatmap(mixed_adapters, "TestPotential", tmp_path, "png")
        assert (tmp_path / "diagnostics_extraction_failure_heatmap.png").exists()

    def test_diagnostics_csv_shares_id_columns_with_scalar_csv(self, mixed_adapters):
        full, sr = mixed_adapters[0], mixed_adapters[1]
        points = [{"delta_Nstar": 5.0, "delta_N": 50.0, "adapters": [full, sr]}]

        scalar_rows = flatten_doe_points_for_csv(points)
        diag_rows = flatten_diagnostics_for_csv(points)

        id_cols = {"N_init", "N_final", "delta_Nstar", "delta_N"}
        assert id_cols <= scalar_rows[0].keys()
        assert id_cols <= diag_rows[0].keys()
        for col in id_cols:
            assert scalar_rows[0][col] == diag_rows[0][col]

        # Diagnostics were read verbatim off the already-fetched adapters --
        # no second fetch, no recomputation (design §8's own point).
        assert diag_rows[0]["diag_compute_time_full"] == 12.0
        assert diag_rows[0]["diag_compute_time_sr"] == 3.0
        assert diag_rows[0]["diag_outer_iterations_sr"] is None


# ---------------------------------------------------------------------------
# Gating: GCI-specific figures never raise / never fire on non-GCI adapters,
# and the extraction-failure family stays silent without spatial data.
# ---------------------------------------------------------------------------


class TestGating_SkipsWithoutData:
    def test_stiffness_skips_with_only_full_and_sr(self, tmp_path):
        full = _full_adapter({"compute_time": 1.0, "converged": True})
        sr = _sr_adapter({"compute_time": 1.0, "converged": True})
        diagnostics.plot_stiffness([full, sr], "TestPotential", tmp_path, "png")
        assert list(tmp_path.iterdir()) == []

    def test_extraction_failure_figures_skip_for_non_dense_gci(self, tmp_path):
        gci = _gci_adapter(
            {"converged": True, "extraction_failure_mask": [False, True]},
            coords={**_SHARED_COORDS, "alpha": 0.05, "n_collocation_points": 2},
            fidelity="profile",
        )
        diagnostics.plot_extraction_failure_summary([gci], "TestPotential", tmp_path, "png")
        diagnostics.plot_extraction_failure_heatmap([gci], "TestPotential", tmp_path, "png")
        assert list(tmp_path.iterdir()) == []

    def test_speedup_skips_with_no_shared_grid_point(self, tmp_path):
        full = _full_adapter({"compute_time": 1.0, "converged": True}, coords=_SHARED_COORDS)
        sr = _sr_adapter({"compute_time": 1.0, "converged": True}, coords=_OTHER_COORDS)
        diagnostics.plot_speedup([full, sr], "TestPotential", tmp_path, "png")
        assert list(tmp_path.iterdir()) == []

    def test_all_figures_are_no_ops_on_empty_input(self, tmp_path):
        for fn_name in (
            "plot_compute_time_distributions", "plot_cost_vs_parameters",
            "plot_convergence_map", "plot_speedup", "plot_picard_newton_structure",
            "plot_stiffness", "plot_extraction_failure_summary",
            "plot_extraction_failure_heatmap",
        ):
            getattr(diagnostics, fn_name)([], "TestPotential", tmp_path, "png")
        assert list(tmp_path.iterdir()) == []
