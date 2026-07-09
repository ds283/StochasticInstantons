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


def plot_instanton_fields(
    adapters,
    N_init_val,
    N_final_val,
    dns_val,
    potential,
    units,
    output_dir,
    fmt,
    cf_annotation=None,
    run_label: str = "",
):
    """2x2 grid of instanton field components vs N, at one
    (N_init, N_final, delta_Nstar) point.

    `adapters` is a list of `InstantonAdapter` instances (e.g.
    [FullInstantonAdapter, SlowRollInstantonAdapter]); overlaying more
    solvers on the same axes is just passing a longer list (design §3.4) --
    this function never branches on which kind of adapter it was handed,
    only on `has_channel(...)`/`time_history(...)` returning data.
    """
    live = [a for a in adapters if a.available and not a.failure]
    if not live:
        print(
            f"   Warning: no instanton data for Ninit={N_init_val:.3g}, "
            f"Nfinal={N_final_val:.3g}, dNstar={dns_val:.3g} — skipping instanton fields plot"
        )
        return

    Mp = units.PlanckMass
    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    ax_phi, ax_pi, ax_P1, ax_P2 = (axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1])

    # Top-left: field trajectory, one line per adapter exposing "phi". The
    # init/final reference lines are drawn once, from the first adapter with
    # data (so with [Full, SR] this reproduces the old fi-only reference
    # lines, since Full is available and listed first).
    ref_lines_drawn = False
    for a in live:
        hist = a.time_history("phi")
        if hist is None:
            continue
        N, phi = hist
        ax_phi.plot(
            N,
            phi / Mp,
            a.line_style,
            label=rf"{a.channel_label('phi')} ({a.display_label})",
        )
        if not ref_lines_drawn:
            ax_phi.axhline(
                phi[0] / Mp,
                color="gray",
                linestyle=":",
                linewidth=0.8,
                label=r"$\varphi_{\rm init}$",
            )
            ax_phi.axhline(
                phi[-1] / Mp,
                color="gray",
                linestyle="-.",
                linewidth=0.8,
                label=r"$\varphi_{\rm final}$",
            )
            ref_lines_drawn = True

    ax_phi.set_xlabel("N (e-folds)")
    ax_phi.set_ylabel(r"$\varphi\,/\,M_{\rm P}$")
    ax_phi.set_title("Field trajectory")
    ax_phi.legend(fontsize="small")

    # Top-right: field velocity (only Full exposes this channel today) plus
    # the analytic slow-roll comparison curve pi_SR(phi), built from the same
    # adapter's own "phi" channel.
    for a in live:
        hist = a.time_history("velocity")
        if hist is None:
            continue
        N, pi = hist
        ax_pi.plot(
            N,
            pi / Mp,
            a.line_style,
            label=rf"{a.channel_label('velocity')} ({a.display_label})",
        )

        phi_hist = a.time_history("phi")
        if phi_hist is not None:
            _, phi_raw = phi_hist
            try:
                pi_sr = [
                    -potential.dV_dphi(p) / (3.0 * potential.H_sq(p, 0.0))
                    for p in phi_raw
                ]
                ax_pi.plot(
                    N,
                    [p / Mp for p in pi_sr],
                    "--",
                    label=r"$\pi_{\rm SR}(\varphi_1)$",
                )
            except Exception:
                pass

    ax_pi.set_xlabel("N (e-folds)")
    ax_pi.set_ylabel(r"field velocity / $M_{\rm P}$")
    ax_pi.set_title("Field velocity")
    ax_pi.legend(fontsize="small")

    # Bottom-left: response field P1, one line per adapter exposing it.
    for a in live:
        hist = a.time_history("P1")
        if hist is None:
            continue
        N, P1 = hist
        ax_P1.plot(
            N, P1, a.line_style, label=rf"{a.channel_label('P1')} ({a.display_label})"
        )

    ax_P1.set_xlabel("N (e-folds)")
    ax_P1.set_ylabel(r"$P_1$")
    ax_P1.set_title("Response field $P_1$")
    ax_P1.legend(fontsize="small")

    # Bottom-right: response field P2 (only Full exposes this channel).
    for a in live:
        hist = a.time_history("P2")
        if hist is None:
            continue
        N, P2 = hist
        ax_P2.plot(
            N, P2, a.line_style, label=rf"{a.channel_label('P2')} ({a.display_label})"
        )

    ax_P2.set_xlabel("N (e-folds)")
    ax_P2.set_ylabel(r"$P_2$")
    ax_P2.set_title("Response field $P_2$")
    ax_P2.legend(fontsize="small")

    fig.suptitle(
        f"Instanton fields — {potential.name}, "
        rf"$N_{{\rm init}}$={N_init_val:.3g}, $N_{{\rm final}}$={N_final_val:.3g}, "
        rf"$\delta N_\star$={dns_val:.3g}"
    )

    # MSR action annotation alongside the CF summary
    msr_parts = []
    for a in live:
        action = a.scalars().get("msr_action")
        if action is not None:
            msr_parts.append(rf"{a.display_label}: $S_{{\rm MSR}}$={action:.4g}")
    msr_text = "   ".join(msr_parts) if msr_parts else None

    cf_text = _cf_annotation_text(cf_annotation)
    ann_lines = [t for t in (cf_text, msr_text) if t]
    _add_cf_annotation(fig, "\n".join(ann_lines) if ann_lines else None)

    _provenance_footer(fig, *live, run_label=run_label)

    fname = output_dir / f"instanton_fields.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
