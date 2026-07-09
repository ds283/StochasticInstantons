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
Unified entry point for the GradientCoupledInstanton diagnostic suite.

    python -m tools.diagnostics.GradientCoupledInstanton <subcommand> [args...]

Each subcommand forwards its remaining argv to that module's own
``main(argv)``/``create_parser()`` -- run ``... <subcommand> --help`` for its
specific options. This file only dispatches; it adds no new behaviour of its
own, so each module remains independently runnable as
``python -m tools.diagnostics.GradientCoupledInstanton.<module> ...`` too
(useful for a script that only ever needs one of them).

Subcommands:
  convergence-floor   Diagnostics 1-8 (prompts 24a/24b, n/tau/alpha studies).
  trajectory-plots     Trajectory-validation plots for a converged-solve JSON.
  seed-screen          Cheap alpha vs n_collocation_points zeroth-iterate scan.
  spectrum              Assembled-operator eigenvalue / adjoint diagnostics.
"""

from __future__ import annotations

import sys

from . import convergence_floor, seed_screen, spectrum, trajectory_plots

_SUBCOMMANDS = {
    "convergence-floor": convergence_floor.main,
    "trajectory-plots": trajectory_plots.main,
    "seed-screen": seed_screen.main,
    "spectrum": spectrum.main,
}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        print("Available subcommands: " + ", ".join(sorted(_SUBCOMMANDS)))
        return 0 if argv else 1
    subcommand, rest = argv[0], argv[1:]
    if subcommand not in _SUBCOMMANDS:
        print(f"Unknown subcommand {subcommand!r}. "
              f"Available: {', '.join(sorted(_SUBCOMMANDS))}", file=sys.stderr)
        return 2
    return _SUBCOMMANDS[subcommand](rest)


if __name__ == "__main__":
    raise SystemExit(main())
