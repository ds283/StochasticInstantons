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
CLI-level coverage for the `trajectory-plots` subcommand of the
tools/diagnostics/GradientCoupledInstanton package. `trajectory_plots.py` is
pure post-processing -- it never runs an ODE solve, only reads a
convergence_floor.py JSON record plus its matching harness.save_grids_npz
.npz file -- so this test builds a synthetic fixture directly against that
documented schema rather than running a real (expensive) convergence_floor
diagnostic first.
"""

import json

import numpy as np

from tools.diagnostics.GradientCoupledInstanton import harness as h
from tools.diagnostics.GradientCoupledInstanton.trajectory_plots import main


def _write_synthetic_fixture(tmp_path):
    grid = h.LGLCollocationGrid(5)
    n_nodes = grid.n_max + 1

    N_grid = np.linspace(0.0, 1.0, 4)
    phi_grid = np.tile(np.linspace(14.0, 15.0, n_nodes), (4, 1))
    pi_grid = np.tile(np.linspace(-0.1, 0.1, n_nodes), (4, 1))
    rfield_grid = np.zeros_like(phi_grid)
    rmom_grid = np.zeros_like(phi_grid)
    N_sample_FI = np.linspace(0.0, 1.0, 4)
    phi1_FI = np.linspace(14.0, 15.0, 4)
    phi2_FI = np.linspace(-0.1, 0.1, 4)

    npz_path = tmp_path / "point.npz"
    h.save_grids_npz(
        str(npz_path), N_grid=N_grid, phi_grid=phi_grid, pi_grid=pi_grid,
        rfield_grid=rfield_grid, rmom_grid=rmom_grid, grid=grid,
        N_sample_FI=N_sample_FI, phi1_FI=phi1_FI, phi2_FI=phi2_FI,
        final_lambda=1.0, lambda_FI=1.0, m=1.0e-2, delta_Nstar=0.5, alpha=0.1,
    )

    json_path = tmp_path / "rows.json"
    rows = [{
        "converged": True, "grids_npz": str(npz_path),
        "delta_Nstar": 0.5, "S_ratio_GCI_over_FI": 1.0,
    }]
    json_path.write_text(json.dumps(rows))
    return json_path


def test_trajectory_plots_produces_png_and_summary(tmp_path):
    json_path = _write_synthetic_fixture(tmp_path)
    plot_dir = tmp_path / "plots"

    rc = main(["--input", str(json_path), "--output-dir", str(plot_dir)])
    assert rc == 0

    produced = {p.name for p in plot_dir.iterdir()}
    assert "trajectory_m0.01_dNstar0.5_alpha0.1.png" in produced
    assert "S_ratio_vs_delta_Nstar.png" in produced
    assert "epsilon_summary.json" in produced

    summary = json.loads((plot_dir / "epsilon_summary.json").read_text())
    assert len(summary) == 1
    assert summary[0]["m"] == 1.0e-2
