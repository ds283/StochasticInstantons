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

import numpy as np


def _evenly_sample(seq, k):
    """Return up to k elements of seq, evenly spaced by index."""
    n = len(seq)
    if n <= k:
        return list(seq)
    idx = sorted(set(int(round(i)) for i in np.linspace(0, n - 1, k)))
    return [seq[i] for i in idx]


def _safe_name(s):
    return s.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")


def _safe_num(v: float) -> str:
    return f"{v:.4g}".replace(".", "p").replace("-", "m")
