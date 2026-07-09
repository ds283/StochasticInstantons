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

from pathlib import Path

import ray
import seaborn as sns


def _dispatch_plot_work(item):
    """task_builder for RayWorkPool: item is a (remote_fn, args) pair already
    fully prepared by the data-fetch stage; just submit it."""
    remote_fn, args = item
    return remote_fn.remote(*args)


@ray.remote
def _render_item(figure_fn, payload, output_dir_str, fmt, run_label):
    """Generic Ray-remote render wrapper (design §5). Not yet wired into any
    driver — the existing per-figure `_plot_*_item` wrappers keep dispatching
    directly until P2 converts figures to consume this via adapters."""
    sns.set_theme()
    figure_fn(payload, Path(output_dir_str), fmt, run_label=run_label)
