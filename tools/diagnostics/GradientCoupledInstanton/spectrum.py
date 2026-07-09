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
IMPORTANT -- deliberately a thin wrapper, not a rewrite.

``analyze_StiffnessSpectrum.py`` (~1770 lines: assembled-operator eigenvalue
sweeps, the discrete-adjoint diagnostic, self-checks against a finite-
difference Jacobian, CSV/plot output, its own argparse CLI) was reviewed only
in outline for this refactor -- its full body was not re-derived or
re-transcribed here, to avoid silently introducing a transcription error
into a numerically delicate diagnostic nobody would think to re-verify
against the original. This module therefore does NOT reproduce its
numerics. Instead it:

  1. imports the existing module from wherever it lives in the repo today
     (unmodified), and
  2. re-exports its ``main``/``create_parser`` so it participates in this
     package's unified ``cli.py`` dispatch.

**Follow-up needed** (tracked in DIAGNOSTICS_SUITE.md's "Known gaps"): once
``analyze_StiffnessSpectrum.py`` is physically ``git mv``'d into this
directory (e.g. as ``spectrum_impl.py``), this wrapper's import line below
should be updated to a relative import and the fallback path-based import
removed. That move is a pure relocation (import-path fixups only, per this
package's own docstring in ``__init__.py``) and is safe to do without a
line-by-line re-review; a full *rewrite* onto the shared harness is a
separate, much lower-priority task, since this script does not use
``harness.py``'s trajectory/FullInstanton machinery at all -- it works
entirely with frozen-coefficient, potential-independent synthetic operators
(see its own module docstring) and has no InflatonTrajectory/AbstractPotential
dependency to share.

Usage (unchanged from the original):
    python -m tools.diagnostics.GradientCoupledInstanton.spectrum \\
        --mode spectrum --n-max 8,16,32,64,128 --alpha 0.001,0.05 --plot
    python -m tools.diagnostics.GradientCoupledInstanton.spectrum \\
        --mode adjoint --output adjoint_diagnostic.csv
"""

from __future__ import annotations

import importlib.util
import os
import sys

from . import harness as h  # ensures STOCHASTIC_INSTANTONS_REPO is on sys.path

_MODULE_NAME = "analyze_StiffnessSpectrum"

# Prefer an already-relocated copy sitting alongside this file (post git-mv,
# per this module's own docstring); fall back to searching the repo root the
# harness bootstrap already put on sys.path.
_local_path = os.path.join(os.path.dirname(__file__), f"{_MODULE_NAME}.py")
if os.path.exists(_local_path):
    _spec = importlib.util.spec_from_file_location(_MODULE_NAME, _local_path)
    _impl = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_impl)
else:
    _impl = importlib.import_module(_MODULE_NAME)

main = _impl.main
create_parser = _impl.create_parser

# Re-export everything else for callers that want the underlying functions
# directly (e.g. a future notebook), without committing this wrapper to an
# explicit __all__ list that would need updating every time the original
# script's own API changes.
for _name in dir(_impl):
    if not _name.startswith("_"):
        globals().setdefault(_name, getattr(_impl, _name))

if __name__ == "__main__":
    sys.exit(main())
