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

from datetime import datetime

VERSION_LABEL = "2026.3.0"


def _provenance_footer(fig, *objs, render_time=None, run_label: str = ""):
    """Render a small, unobtrusive provenance line at the very bottom of fig.

    Introspects whatever public attributes are present on each object; never
    raises if an attribute is absent or if the object is not yet persisted.
    When run_label is non-empty, renders a second line above the version/timestamp
    line showing the database filename, config, and active mode flags.
    """
    if render_time is None:
        render_time = datetime.now()

    obj_parts = []
    for obj in objs:
        fields = []
        try:
            if hasattr(obj, "available") and obj.available:
                fields.append(f"id={obj.store_id}")
        except Exception:
            pass
        try:
            ts = getattr(obj, "timestamp", None)
            if ts is not None:
                fields.append(f"stored={ts.strftime('%Y-%m-%d %H:%M')}")
        except Exception:
            pass
        for attr in ("atol", "rtol", "label"):
            try:
                val = getattr(obj, attr, None)
                if val is not None:
                    try:
                        formatted = f"{float(val):.2g}"
                    except (TypeError, ValueError):
                        formatted = str(val)
                    fields.append(f"{attr}={formatted}")
            except Exception:
                pass
        if fields:
            obj_parts.append(f"{type(obj).__name__}({', '.join(fields)})")

    parts = [
        f"StochasticInstanton v{VERSION_LABEL}",
        render_time.strftime("%Y-%m-%d %H:%M:%S"),
    ]
    parts.extend(obj_parts)
    bottom_line = "  |  ".join(parts)

    if run_label:
        fig_height_in = fig.get_size_inches()[1]
        two_line_strip_in = 0.30
        bottom_frac = two_line_strip_in / fig_height_in
        current_bottom = fig.subplotpars.bottom
        if bottom_frac > current_bottom:
            fig.subplots_adjust(bottom=bottom_frac)

    footer_text = "\n".join([run_label, bottom_line]) if run_label else bottom_line

    try:
        fig.text(
            0.5,
            0.003,
            footer_text,
            ha="center",
            va="bottom",
            fontsize=7,
            color="#888888",
            transform=fig.transFigure,
        )
    except Exception:
        pass
