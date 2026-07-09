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

`explore_onion_stiffness.run_case` now builds the `g_pi_core_spline` pi_core
SAT target `forward_rhs` requires whenever `disable_spatial_coupling=False`
via `picard._fetch_full_instanton_profile` -- the same fetch-then-fallback
helper production `solve_picard` itself uses -- fed by a real FullInstanton
seed that `seed_screen.scan_alpha_vs_n_colloc` fetches once per scan (see
seed_screen.py's own module docstring). This replaced the previous
KNOWN BROKEN state (`run_case` predated the `g_pi_core_spline` argument
entirely and unconditionally dereferenced it), which this test used to
document via a strict xfail.
"""

from tools.diagnostics.GradientCoupledInstanton import seed_screen


def test_create_parser_defaults():
    parser = seed_screen.create_parser()
    args = parser.parse_args([])
    assert args.mass == 1.0e-5
    assert args.alpha_powers == "0,1,2,3"
    assert args.n_colloc == "5,7,9,11,13,15,17,21,25,33"


def test_scan_alpha_vs_n_colloc_single_point(tmp_path, monkeypatch):
    monkeypatch.setattr(seed_screen, "OUT_DIR", str(tmp_path))
    seed_screen.scan_alpha_vs_n_colloc(alpha_powers=(0,), n_colloc_values=(5,))
