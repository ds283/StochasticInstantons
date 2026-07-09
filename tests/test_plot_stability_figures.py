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
Acceptance test for Prompt P6
(.prompts/gradient-coupled-plotting/11-P6-stability-convergence-figures.md):
`plotting.figures.stability`'s n_collocation/alpha convergence overlays and
plateau panels.

Unlike P4/P5a's duck-typed-adapter smoke tests, this prompt's acceptance
test explicitly asks for "a fixture database" -- so this file drives a real
`live_pool` (tests/conftest.py), storing genuine `GradientCoupledInstanton`
rows at a shared (N_init, N_final, delta_Nstar) across several
n_collocation_points/alpha_regularization values, then calls the module's
two orchestration entry points (`render_n_collocation_stability`,
`render_alpha_stability`), which do their own `fetch_over_grid`-based
fetching (design §4/§4.1) rather than taking pre-built adapters.

Setup mirrors tests/test_gci_profile_only_fetch_contract.py's own
`_make_gci`/`_get_prerequisites` helpers (duplicated here per this test
suite's existing convention of each file carrying its own self-contained
stubs -- see that file's own docstring for the same remark).
"""

import re
import types

import pytest
import ray
from matplotlib import pyplot as plt

import plotting.figures.stability as stability
from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
    GradientCoupledInstanton,
    GradientCoupledInstantonProfileValue,
)
from CosmologyModels.params import Planck2018
from Units.Planck_units import Planck_units

pytestmark = pytest.mark.integration

_DNS_VAL = 0.71
_N_FINAL_VAL = 1.11
_LOG10_TOL = -6.0
_N_COLLOC_VALS = [4, 6, 8]
_ALPHA_VALS = [0.02, 0.05, 0.08]

# Unique N_init value -- must not clash with other integration-test modules
# sharing the session-scoped live_pool database (see
# test_gci_profile_only_fetch_contract.py's own comment on the existing
# ranges: 170-174, 270-273 are already taken).
_GCI_N_INIT = 280.0
_GCI_N_INIT_SINGLE_VALUE = 281.0


def _get_prerequisites(pool):
    (dns_list, n_final_list, tol_list, n_colloc_list, alpha_list) = ray.get([
        pool.object_get("delta_Nstar", payload_data=[{"value": _DNS_VAL}]),
        pool.object_get("N_final", payload_data=[{"value": _N_FINAL_VAL}]),
        pool.object_get("tolerance", payload_data=[{"log10_tol": _LOG10_TOL}]),
        pool.object_get(
            "n_collocation_points",
            payload_data=[{"n_collocation_points": v} for v in _N_COLLOC_VALS],
        ),
        pool.object_get(
            "alpha_regularization",
            payload_data=[{"alpha": v} for v in _ALPHA_VALS],
        ),
    ])
    diffusion = ray.get(pool.object_get("MasslessDecoupledDiffusion"))
    cosmo = ray.get(pool.object_get("CosmologicalParams", params=Planck2018()))
    return {
        "dns": dns_list[0],
        "n_final": n_final_list[0],
        "tol": tol_list[0],
        "n_colloc_list": n_colloc_list,
        "alpha_list": alpha_list,
        "diffusion": diffusion,
        "cosmo": cosmo,
    }


def _mint_n_init(pool, value: float):
    return ray.get(pool.object_get("N_init", payload_data=[{"value": value}]))[0]


def _make_fake_traj():
    return types.SimpleNamespace(store_id=999, units=Planck_units())


def _make_and_store_gci(pool, n_init_obj, prereqs, n_colloc_obj, alpha_obj, fake_traj, index):
    n_nodes = int(n_colloc_obj)
    obj = GradientCoupledInstanton(
        store_id=None,
        trajectory=fake_traj,
        N_init=n_init_obj,
        N_final=prereqs["n_final"],
        delta_Nstar=prereqs["dns"],
        n_collocation_points=n_colloc_obj,
        alpha_regularization=alpha_obj,
        atol=prereqs["tol"],
        rtol=prereqs["tol"],
        cosmo=prereqs["cosmo"],
        N_sample=None,
        diffusion_model=prereqs["diffusion"],
    )
    obj._diagnostics = {"compute_time": 0.1, "converged": True}
    obj._failure = False
    obj._noise_field_min, obj._noise_field_mean, obj._noise_field_max = -0.1, 0.0, 0.1
    obj._noise_mom_min, obj._noise_mom_mean, obj._noise_mom_max = -0.2, 0.0, 0.2

    # Scalars vary slightly with `index` (the sweep position) so successive
    # differences are non-zero, finite, real convergence-style numbers.
    obj._msr_action = 1.0 + 0.01 * index
    obj._C_peak = 0.5 + 0.001 * index
    obj._C_bar_peak = 0.4 + 0.001 * index
    obj._C_min = -0.2 - 0.001 * index
    obj._compensated = True
    obj._type_II = False
    obj._r_max = 4.0e4 * (1.0 + 0.001 * index)
    obj._r_peak = 3.0e4 * (1.0 + 0.001 * index)
    obj._M_max = 3.0e-2 * (1.0 + 0.001 * index)
    obj._M_peak = 2.0e-2 * (1.0 + 0.001 * index)
    obj._V_end_downflow = 9.0e-9
    obj._N_end_downflow = 0.04

    obj._values = []  # not exercised by the profile_only/do_not_populate fetches
    obj._profile = [
        GradientCoupledInstantonProfileValue(
            node_index=j,
            zeta=0.01 * j,
            r_ratio=1.0 - 0.1 * j,
            C=0.05 * j + 0.001 * index,
            r_phys=1.0e3 * (n_nodes - j),
            C_bar=0.04 * j,
        )
        for j in range(n_nodes)
    ]

    stored = ray.get(pool.object_store(obj))
    assert stored._my_id is not None
    validated = ray.get(pool.object_validate(stored))
    assert validated is True
    return stored


@pytest.fixture(scope="module")
def stability_records(live_pool):
    """Stores a GradientCoupledInstanton at each of `_N_COLLOC_VALS` (fixed
    alpha = `_ALPHA_VALS[0]`) and at each of `_ALPHA_VALS` (fixed
    n_collocation_points = `_N_COLLOC_VALS[0]`), all at one shared
    (N_init, N_final, delta_Nstar) grid point."""
    prereqs = _get_prerequisites(live_pool)
    fake_traj = _make_fake_traj()
    n_init = _mint_n_init(live_pool, _GCI_N_INIT)

    n_colloc_list = prereqs["n_colloc_list"]
    alpha_list = prereqs["alpha_list"]

    for i, n_obj in enumerate(n_colloc_list):
        _make_and_store_gci(live_pool, n_init, prereqs, n_obj, alpha_list[0], fake_traj, i)
    for i, a_obj in enumerate(alpha_list):
        if i == 0:
            # (n_colloc_list[0], alpha_list[0]) was already stored by the
            # n_collocation loop above -- storing it again would create a
            # second, identically-keyed row and make the fetch's `.one_or_none()`
            # raise MultipleResultsFound.
            continue
        _make_and_store_gci(live_pool, n_init, prereqs, n_colloc_list[0], a_obj, fake_traj, i)

    return {
        "n_init": n_init,
        "prereqs": prereqs,
        "fake_traj": fake_traj,
        "n_colloc_list": n_colloc_list,
        "alpha_list": alpha_list,
    }


@pytest.fixture(scope="module")
def single_value_record(live_pool):
    """A single GradientCoupledInstanton at a DIFFERENT N_init, so the
    n_collocation_points_array/alpha_regularization_array passed in by the
    caller can legitimately have length 1 without colliding with
    `stability_records`'s own multi-value grid point."""
    prereqs = _get_prerequisites(live_pool)
    fake_traj = _make_fake_traj()
    n_init = _mint_n_init(live_pool, _GCI_N_INIT_SINGLE_VALUE)
    n_colloc_list = prereqs["n_colloc_list"]
    alpha_list = prereqs["alpha_list"]
    _make_and_store_gci(live_pool, n_init, prereqs, n_colloc_list[0], alpha_list[0], fake_traj, 0)
    return {
        "n_init": n_init,
        "prereqs": prereqs,
        "fake_traj": fake_traj,
        "n_colloc_list": n_colloc_list,
        "alpha_list": alpha_list,
    }


# ---------------------------------------------------------------------------
# Acceptance test (a): both overlay figures and both plateau panels render
# without error against a >=2-value fixture database.
# ---------------------------------------------------------------------------


class TestAcceptanceA_RendersAllFourFigures:
    def test_n_collocation_figures_render(self, stability_records, live_pool, tmp_path):
        r = stability_records
        stability.render_n_collocation_stability(
            live_pool, r["fake_traj"], r["n_init"], r["prereqs"]["n_final"],
            r["prereqs"]["dns"], r["alpha_list"][0], r["n_colloc_list"],
            r["prereqs"]["tol"], r["prereqs"]["tol"], r["prereqs"]["cosmo"],
            r["prereqs"]["diffusion"], "TestPotential", tmp_path, "png",
        )
        assert list(tmp_path.glob("stability_n_collocation_overlay__*.png"))
        assert list(tmp_path.glob("stability_plateau_n_collocation__*.png"))

    def test_alpha_figures_render(self, stability_records, live_pool, tmp_path):
        r = stability_records
        stability.render_alpha_stability(
            live_pool, r["fake_traj"], r["n_init"], r["prereqs"]["n_final"],
            r["prereqs"]["dns"], r["n_colloc_list"][0], r["alpha_list"],
            r["prereqs"]["tol"], r["prereqs"]["tol"], r["prereqs"]["cosmo"],
            r["prereqs"]["diffusion"], "TestPotential", tmp_path, "png",
        )
        assert list(tmp_path.glob("stability_alpha_overlay__*.png"))
        assert list(tmp_path.glob("stability_plateau_alpha__*.png"))

    def test_n_collocation_overlay_reports_finite_max_abs_diff(
        self, stability_records, live_pool, tmp_path, monkeypatch
    ):
        captured = []
        monkeypatch.setattr(plt, "close", lambda fig=None: captured.append(fig))

        r = stability_records
        stability.render_n_collocation_stability(
            live_pool, r["fake_traj"], r["n_init"], r["prereqs"]["n_final"],
            r["prereqs"]["dns"], r["alpha_list"][0], r["n_colloc_list"],
            r["prereqs"]["tol"], r["prereqs"]["tol"], r["prereqs"]["cosmo"],
            r["prereqs"]["diffusion"], "TestPotential", tmp_path, "png",
        )

        assert len(captured) == 2  # overlay figure, then plateau figure
        overlay_fig = captured[0]
        texts = [t.get_text() for t in overlay_fig.texts]
        max_diff_texts = [t for t in texts if "max|" in t]
        assert max_diff_texts, f"no max|Delta| inset found among figure texts: {texts}"

        numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", max_diff_texts[0])
        assert numbers, f"no numeric value found in inset text: {max_diff_texts[0]!r}"
        for n in numbers:
            value = float(n)
            assert value == value and value not in (float("inf"), float("-inf"))  # finite


# ---------------------------------------------------------------------------
# Acceptance test (b): all four figures are silently skipped (no exception,
# no file) when only one value of the relevant axis exists.
# ---------------------------------------------------------------------------


class TestAcceptanceB_SkipsWithSingleValue:
    def test_n_collocation_figures_skipped(self, single_value_record, live_pool, tmp_path):
        r = single_value_record
        stability.render_n_collocation_stability(
            live_pool, r["fake_traj"], r["n_init"], r["prereqs"]["n_final"],
            r["prereqs"]["dns"], r["alpha_list"][0], [r["n_colloc_list"][0]],
            r["prereqs"]["tol"], r["prereqs"]["tol"], r["prereqs"]["cosmo"],
            r["prereqs"]["diffusion"], "TestPotential", tmp_path, "png",
        )
        assert list(tmp_path.iterdir()) == []

    def test_alpha_figures_skipped(self, single_value_record, live_pool, tmp_path):
        r = single_value_record
        stability.render_alpha_stability(
            live_pool, r["fake_traj"], r["n_init"], r["prereqs"]["n_final"],
            r["prereqs"]["dns"], r["n_colloc_list"][0], [r["alpha_list"][0]],
            r["prereqs"]["tol"], r["prereqs"]["tol"], r["prereqs"]["cosmo"],
            r["prereqs"]["diffusion"], "TestPotential", tmp_path, "png",
        )
        assert list(tmp_path.iterdir()) == []
