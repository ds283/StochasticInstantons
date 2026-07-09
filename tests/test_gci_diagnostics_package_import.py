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
Import smoke test for the tools/diagnostics/GradientCoupledInstanton
package. Every module in the package imports `harness` (directly or via
`cli`) at module scope, so a single broken import anywhere in that chain
(e.g. harness.py depending on a module that has moved) silently breaks every
subcommand and poisons pytest collection of any test file that imports
`spectrum.py`. This test exists so that class of bug fails here, fast, at
collection time, rather than being discovered only when a subcommand is run
by hand.
"""

import importlib


def test_every_module_imports():
    for name in (
        "harness",
        "cli",
        "convergence_floor",
        "seed_screen",
        "spectrum",
        "trajectory_plots",
        "explore_onion_stiffness",
        "__main__",
    ):
        importlib.import_module(f"tools.diagnostics.GradientCoupledInstanton.{name}")
    importlib.import_module(
        "tools.diagnostics.GradientCoupledInstanton.archive.prompt22_validation"
    )


def test_cli_subcommands_are_registered():
    from tools.diagnostics.GradientCoupledInstanton import cli

    assert set(cli._SUBCOMMANDS) == {
        "convergence-floor",
        "trajectory-plots",
        "seed-screen",
        "spectrum",
    }
    for fn in cli._SUBCOMMANDS.values():
        assert callable(fn)


def test_cli_help_lists_every_subcommand(capsys):
    from tools.diagnostics.GradientCoupledInstanton import cli

    rc = cli.main([])
    out = capsys.readouterr().out
    assert rc == 1
    for name in cli._SUBCOMMANDS:
        assert name in out
