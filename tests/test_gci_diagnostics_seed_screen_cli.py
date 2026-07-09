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
Coverage for the `seed-screen` subcommand of the
tools/diagnostics/GradientCoupledInstanton package.

`seed-screen` is currently KNOWN BROKEN independent of the import-chain bug
this suite's other tests guard against: `explore_onion_stiffness.run_case`
calls `forward_rhs` with a pre-SAT-penalty positional signature. Current
production `forward_rhs` requires a `g_pi_core_spline` argument that
`run_case` never supplies and unconditionally dereferences whenever
`disable_spatial_coupling=False` -- see seed_screen.py's own module
docstring. Fixing `run_case` needs a physics decision (what
`disable_spatial_coupling`/`g_pi_core_spline` should mean for a
zeroth-Picard-iterate screen with no FullInstanton profile yet), which is
out of scope here. This test documents the known break with a strict xfail
rather than either silently skipping coverage or asserting broken behaviour
as correct; once the follow-up production fix lands, this should start
passing and the xfail marker should be removed (strict=True makes an
unexpected pass fail the suite, so that flip won't go unnoticed).
"""

import pytest

from tools.diagnostics.GradientCoupledInstanton import seed_screen


def test_create_parser_defaults():
    parser = seed_screen.create_parser()
    args = parser.parse_args([])
    assert args.mass == 1.0e-5
    assert args.alpha_powers == "0,1,2,3"
    assert args.n_colloc == "5,7,9,11,13,15,17,21,25,33"


@pytest.mark.slow
@pytest.mark.xfail(
    strict=True,
    reason="run_case predates forward_rhs's g_pi_core_spline signature "
           "(SAT-penalty machinery) -- see seed_screen.py's module docstring "
           "and DIAGNOSTICS_SUITE.md section 2.",
)
def test_scan_alpha_vs_n_colloc_single_point(tmp_path, monkeypatch):
    monkeypatch.setattr(seed_screen, "OUT_DIR", str(tmp_path))
    seed_screen.scan_alpha_vs_n_colloc(alpha_powers=(0,), n_colloc_values=(5,))
