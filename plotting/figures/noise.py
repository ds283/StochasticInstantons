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
from matplotlib import pyplot as plt

from plotting.annotations import _add_cf_annotation, _cf_annotation_text
from plotting.provenance import _provenance_footer


def plot_noise_profile(
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
    """Two-panel figure: sigma_field(N) and sigma_mom(N) noise amplitude
    profiles. `adapters` is a list of `InstantonAdapter` instances."""
    live = [a for a in adapters if a.available and not a.failure]
    if not live:
        print(
            f"   Warning: no instanton data for Ninit={N_init_val:.3g}, "
            f"Nfinal={N_final_val:.3g}, dNstar={dns_val:.3g} — skipping noise profile plot"
        )
        return

    histories = [(a, a.noise_history()) for a in live]
    if not any(h is not None for _, h in histories):
        print(
            f"   Warning: noise profile unavailable for Ninit={N_init_val:.3g}, "
            f"Nfinal={N_final_val:.3g}, dNstar={dns_val:.3g} — skipping noise profile plot"
        )
        return

    fig, (ax_s1, ax_s2) = plt.subplots(1, 2, figsize=(10, 5))

    # Left panel: sigma_field
    for a, hist in histories:
        if hist is None:
            continue
        mask = ~np.isnan(hist["sigma_field"])
        if mask.any():
            ax_s1.plot(
                hist["N"][mask],
                hist["sigma_field"][mask],
                a.line_style,
                label=rf"$\sigma_{{\varphi_1}}$ ({a.display_label})",
            )

    ax_s1.set_xlabel("N (e-folds)")
    ax_s1.set_ylabel(r"$\sigma_{\varphi_1}$")
    ax_s1.set_title(r"Noise amplitude $\sigma_{\varphi_1}$")
    ax_s1.legend(fontsize="small")

    # Right panel: sigma_mom
    s2_has_data = False
    for a, hist in histories:
        if hist is None:
            continue
        mask = ~np.isnan(hist["sigma_mom"])
        if mask.any():
            ax_s2.plot(
                hist["N"][mask],
                hist["sigma_mom"][mask],
                a.line_style,
                label=rf"$\sigma_{{\varphi_2}}$ ({a.display_label})",
            )
            s2_has_data = True

    if not s2_has_data:
        ax_s2.text(
            0.5,
            0.5,
            r"No $\varphi_2$ channel data",
            ha="center",
            va="center",
            transform=ax_s2.transAxes,
            color="gray",
        )

    ax_s2.set_xlabel("N (e-folds)")
    ax_s2.set_ylabel(r"$\sigma_{\varphi_2}$")
    ax_s2.set_title(r"Noise amplitude $\sigma_{\varphi_2}$")
    if s2_has_data:
        ax_s2.legend(fontsize="small")

    fig.suptitle(
        rf"Noise profile — {potential_name}, "
        rf"$N_{{\rm init}}$={N_init_val:.3g}, $N_{{\rm final}}$={N_final_val:.3g}, "
        rf"$\delta N_\star$={dns_val:.3g}"
    )

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

    fname = output_dir / f"noise_profile.{fmt}"
    fig.savefig(fname)
    plt.close(fig)
