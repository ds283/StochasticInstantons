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


def _extract_cf_annotation(cf, units):
    """Return a plain-dict of CF summary scalars (all in display units) or None."""
    if cf is None or not cf.available or cf.failure:
        return None
    Mpc = units.Mpc
    SolarMass = units.SolarMass

    def _div(v, u):
        return v / u if v is not None else None

    def _mul(v, u):
        return v * u if v is not None else None

    return {
        "C_peak_full": cf.C_peak_full,
        "C_bar_peak_full": cf.C_bar_peak_full,
        "r_max_full_Mpc": _div(cf.r_max_full, Mpc),
        "r_peak_full_Mpc": _div(cf.r_peak_full, Mpc),
        "M_max_full_solar": _div(cf.M_max_full, SolarMass),
        "M_peak_full_solar": _div(cf.M_peak_full, SolarMass),
        "C_peak_slow_roll": cf.C_peak_slow_roll,
        "C_bar_peak_slow_roll": cf.C_bar_peak_slow_roll,
        "r_max_slow_roll_Mpc": _div(cf.r_max_slow_roll, Mpc),
        "r_peak_slow_roll_Mpc": _div(cf.r_peak_slow_roll, Mpc),
        "M_max_slow_roll_solar": _div(cf.M_max_slow_roll, SolarMass),
        "M_peak_slow_roll_solar": _div(cf.M_peak_slow_roll, SolarMass),
    }


def _cf_annotation_text(ann):
    """Build a compact annotation string (LaTeX mathtext) from a CF annotation
    dict returned by _extract_cf_annotation, or return None if ann is None."""
    if ann is None:
        return None
    lines = []
    for label, keys in (
        (
            "Full",
            (
                "C_peak_full",
                "C_bar_peak_full",
                "r_max_full_Mpc",
                "r_peak_full_Mpc",
                "M_max_full_solar",
                "M_peak_full_solar",
            ),
        ),
        (
            "SR",
            (
                "C_peak_slow_roll",
                "C_bar_peak_slow_roll",
                "r_max_slow_roll_Mpc",
                "r_peak_slow_roll_Mpc",
                "M_max_slow_roll_solar",
                "M_peak_slow_roll_solar",
            ),
        ),
    ):
        C_max, Cb_max, r_max, r_peak, M_max, M_peak = (ann.get(k) for k in keys)
        if C_max is None and M_max is None:
            continue
        parts = []
        if C_max is not None:
            parts.append(rf"$C_{{\rm peak}}$={C_max:.3g}")
        if Cb_max is not None:
            parts.append(rf"$\bar{{C}}_{{\rm peak}}$={Cb_max:.3g}")
        if r_max is not None:
            parts.append(rf"$r_{{\rm max}}$={r_max:.3g} Mpc")
        if r_peak is not None:
            parts.append(rf"$r_{{\rm peak}}$={r_peak:.3g} Mpc")
        if M_max is not None:
            parts.append(rf"$M_{{\rm max}}$={M_max:.3g} $M_\odot$")
        if M_peak is not None:
            parts.append(rf"$M_{{\rm peak}}$={M_peak:.3g} $M_\odot$")
        lines.append(f"{label}: " + ",  ".join(parts))
    return "\n".join(lines) if lines else None


def _add_cf_annotation(fig, ann_text):
    """Add ann_text as a small figure-level annotation and adjust layout.

    The footer sits at y≈0.003; the annotation is anchored at y=0.03 so
    there is always a clear gap between them regardless of line count.
    """
    if not ann_text:
        fig.tight_layout()
        return
    n_lines = ann_text.count("\n") + 1
    # Reserve space in absolute inches (text size is fixed in points, not
    # figure-relative), then convert to a figure-fraction for this fig's
    # actual height. Avoids over-reserving whitespace on taller figures.
    fig_height_in = fig.get_size_inches()[1]
    footer_strip_in = 0.18  # dedicated footer strip
    per_line_in = 0.22  # x-small annotation line + padding
    bottom_frac = (footer_strip_in + per_line_in * n_lines) / fig_height_in
    fig.tight_layout(rect=[0, bottom_frac, 1, 1])
    fig.text(
        0.5,
        0.03,
        ann_text,
        ha="center",
        va="bottom",
        fontsize="x-small",
        transform=fig.transFigure,
    )
