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
Unit test confirming the Step C "latest-exit rule" monotonicity pass
(N_be_mono, removed in ComputeTargets/CompactionFunction.py's Step C) is a
no-op once the scale-assignment anchor was fixed to pure arithmetic
(N_before_end_arr = N_init_val - N_inst_arr). See
.prompts/gradient-coupled-instanton/11-fix-scale-assignment-anchor.md.
"""

import numpy as np


def test_compaction_function_N_before_end_already_monotonic():
    """
    N_inst_arr (efold_value.N per sample) is always non-decreasing --
    guaranteed by the ORDER BY efold_value.N read used to build
    instanton_obj.values (.claude/rules/populate-ordering.md). Since the
    fixed Step C computes N_before_end_arr = N_init_val - N_inst_arr, a
    constant minus a non-decreasing sequence, N_before_end_arr is
    automatically non-increasing -- exactly what the old "latest-exit
    rule" min-running-value loop (N_be_mono) used to enforce by hand. This
    confirms that property directly and quantitatively (including the tied
    -value edge case) rather than asserting it "should be obvious by
    inspection": for any non-decreasing N_inst_arr, applying the old
    min-running-value pass to N_init_val - N_inst_arr changes nothing.
    """
    rng = np.random.default_rng(0)
    N_init_val = 5.0
    # A generic non-decreasing sequence, including a repeated value (the
    # one case where "non-increasing" needs a non-strict "<=" argument).
    N_inst_arr = np.sort(rng.uniform(0.0, 4.0, size=20))
    N_inst_arr[7] = N_inst_arr[6]

    N_before_end_arr = N_init_val - N_inst_arr

    # Non-increasing by construction.
    assert np.all(np.diff(N_before_end_arr) <= 0.0)

    # The old "latest-exit rule" pass is a no-op on this array.
    N_be_mono = N_before_end_arr.copy()
    for i in range(1, len(N_be_mono)):
        N_be_mono[i] = min(N_be_mono[i], N_be_mono[i - 1])
    np.testing.assert_array_equal(N_be_mono, N_before_end_arr)
