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
tools/diagnostics/GradientCoupledInstanton -- standalone, Ray/Datastore-
bypassing diagnostic suite for the GradientCoupledInstanton ("onion model")
compute target.

See DIAGNOSTICS_SUITE.md (this directory) for the full map of what each
module answers and how they relate to the numbered design prompts that
produced them. Nothing under this package is imported by production code
(main.py, ComputeTargets/, Datastore/) -- it is a consumer of the production
API (solve_picard, _compute_full_instanton, LGLCollocationGrid, ...), never
the other way around.

Entry point: ``python -m tools.diagnostics.GradientCoupledInstanton <command>
...`` (see cli.py for the subcommand list), or run any module directly, e.g.
``python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor 4``.
"""

__version__ = "2026.7.0"
