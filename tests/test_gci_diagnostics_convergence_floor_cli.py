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
Coverage for the `convergence-floor` subcommand of the
tools/diagnostics/GradientCoupledInstanton package. Diagnostics 1-8a each
drive real Picard/shooting solves with no CLI-exposed way to shrink the
mass/grid/budget, so a genuine end-to-end run of any of them is minutes of
wall-clock -- too expensive for routine coverage. This file splits the
difference: fast, unmarked tests for the CLI's own argument-parsing/dispatch
glue (including diagnostic 8t, which is a real dispatch path but raises
NotImplementedError before any numerics run -- see the module's own
docstring), plus one @pytest.mark.slow test that calls diagnostic_4 directly
(bypassing the CLI, since no flag controls mass/budget for it) at the
cheapest mass and a short wallclock_budget, to confirm the actual
setup/fetch/solve/JSON-write path still works end to end.
"""

import json

import pytest

from tools.diagnostics.GradientCoupledInstanton import convergence_floor as cf


def test_create_parser_diagnostic_choices():
    parser = cf.create_parser()
    args = parser.parse_args(["--diagnostic", "4", "8a"])
    assert args.diagnostic == ["4", "8a"]
    assert args.alpha_values == "0.01,0.05,0.1,0.3"

    args = parser.parse_args(["--diagnostic", "8t", "--alpha-values", "0.1,0.2"])
    assert args.diagnostic == ["8t"]
    assert args.alpha_values == "0.1,0.2"


def test_diagnostic_8t_cli_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        cf.main(["--diagnostic", "8t"])


@pytest.mark.slow
def test_diagnostic_4_direct_call_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(cf, "OUT_DIR", str(tmp_path))

    rows = cf.diagnostic_4(
        m=1.0e-5, delta_Nstars=(0.7,), wallclock_budget=2.0, persist_grids=False,
    )

    assert isinstance(rows, list)
    assert len(rows) == 1
    row = rows[0]
    for key in ("delta_Nstar", "converged", "final_lambda", "wallclock"):
        assert key in row
    assert row["delta_Nstar"] == 0.7

    written = json.loads((tmp_path / "diagnostic4_delta_nstar_walk.json").read_text())
    assert written == rows
