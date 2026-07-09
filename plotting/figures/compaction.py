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

from matplotlib import pyplot as plt

from plotting.annotations import _add_cf_annotation, _cf_annotation_text
from plotting.provenance import _provenance_footer


def plot_zeta_and_compaction(
    adapters,
    N_init_val,
    N_final_val,
    dns_val,
    potential_name,
    output_dir,
    fmt,
    cf_annotation=None,
    run_label: str = "",
):
    """Three-panel figure: zeta(r), C(r), and C_bar(r) vs r in Mpc on a log
    x-axis. `adapters` is a list of `InstantonAdapter` instances, each
    wrapping the paired CompactionFunction alongside its own instanton (e.g.
    FullInstantonAdapter(fi, cf), SlowRollInstantonAdapter(sri, cf)); gated
    on `radial_profile()` (a pure read off the CompactionFunction) rather
    than the instanton's own `available`/`failure`, matching the original
    behaviour of gating on `cf.full_values`/`cf.slow_roll_values` alone."""
    profiles = [(a, a.radial_profile()) for a in adapters]
    if not any(p is not None for _, p in profiles):
        return

    # 1 column on left (zeta), 1 column on right split into 2 rows (C, C_bar)
    fig = plt.figure(figsize=(12, 5))
    ax_zeta = fig.add_subplot(1, 2, 1)
    ax_C = fig.add_subplot(2, 2, 2)
    ax_Cbar = fig.add_subplot(2, 2, 4, sharex=ax_C)

    for a, profile in profiles:
        if profile is None:
            continue
        r = profile["r_Mpc"]
        ax_zeta.plot(r, profile["zeta"], a.line_style, label=a.display_label)
        ax_C.plot(r, profile["C"], a.line_style, label=rf"$C$ ({a.display_label})")
        ax_Cbar.plot(
            r, profile["C_bar"], a.line_style, label=rf"$\bar{{C}}$ ({a.display_label})"
        )

    ax_zeta.set_xscale("log")
    ax_zeta.set_xlabel(r"$r$ / Mpc")
    ax_zeta.set_ylabel(r"$\zeta(r)$")
    ax_zeta.set_title(r"Density contrast $\zeta(r)$")
    ax_zeta.legend(fontsize="small")

    ax_C.set_xscale("log")
    ax_C.set_ylabel(r"$C(r)$")
    ax_C.set_title("Compaction function")
    ax_C.legend(fontsize="small")
    plt.setp(ax_C.get_xticklabels(), visible=False)  # shared x, hide top labels

    ax_Cbar.set_xscale("log")
    ax_Cbar.set_xlabel(r"$r$ / Mpc")
    ax_Cbar.set_ylabel(r"$\bar{C}(r)$")
    ax_Cbar.legend(fontsize="small")

    fig.suptitle(
        rf"Compaction — {potential_name}, "
        rf"$N_{{\rm init}}$={N_init_val:.3g}, $N_{{\rm final}}$={N_final_val:.3g}, "
        rf"$\delta N_\star$={dns_val:.3g}"
    )
    _add_cf_annotation(fig, _cf_annotation_text(cf_annotation))
    _provenance_footer(
        fig, *[a for a, p in profiles if p is not None], run_label=run_label
    )

    fname = output_dir / f"compaction.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
