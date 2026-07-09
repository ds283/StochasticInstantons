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
Acceptance test for Prompt P3
(.prompts/gradient-coupled-plotting/07-P3-profile-only-fetch-mode.md).

Exercises the three-mode fetch contract implemented in
``sqla_GradientCoupledInstantonFactory.build()`` --
``_do_not_populate`` / ``_profile_only`` / full -- crossed against the two
storage states a ``GradientCoupledInstanton`` row can be in (dense-stored,
``store_full_values=True``; scalars-only-stored, ``store_full_values=False``),
per design doc §4.1's behaviour table:

| Method / property | do_not_populate | profile_only | full (dense-stored) | full (scalars-only stored) |
|---|---|---|---|---|
| scalars            | value | value | value | value |
| diagnostics        | value | value | value | value |
| profile            | []    | populated | populated | populated |
| values (dense y,N) | []    | []        | populated | build() raises |
| zeta_C_r_at_time   | raise | raise     | (guard doesn't fire) | n/a |

``radial_profile()`` (the P4 adapter method) and ``field_2d()`` are not yet
implemented on this class -- both are out of scope for this prompt, so those
two table rows are not exercised here. For ``zeta_C_r_at_time``, the
full-dense case only confirms the guard's own precondition
(``obj._values`` is non-empty) rather than driving the method to a real
numerical result, since that needs genuine trajectory/potential physics
unrelated to the fetch-mode contract under test here (see
tests/test_gradient_coupled_instanton_end_to_end.py's own
``test_zeta_c_r_at_time_reconstructs_stored_final_row`` for that separate,
``slow``-marked concern).

Setup mirrors tests/test_gci_parity_cheap_fetch.py's own
``_make_gci_with_parity`` helper (duplicated here per this test suite's
existing convention of each file carrying its own self-contained stubs).
"""

import types

import pytest
import ray

from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
    GradientCoupledInstanton,
    GradientCoupledInstantonValue,
    GradientCoupledInstantonProfileValue,
)
from CosmologyModels.params import Planck2018
from Units.Planck_units import Planck_units

pytestmark = pytest.mark.integration

_DNS_VAL = 0.58
_N_FINAL_VAL = 1.03
_LOG10_TOL = -6.0
_N_COLLOC_VAL = 4
_ALPHA_VAL = 0.05
_N_SAMPLES = [0.0, 0.05, 0.10]

# Unique N_init values -- must not clash with other integration-test modules
# sharing the session-scoped live_pool database (170-174 and 270-271 are
# already used by test_gradient_coupled_instanton_end_to_end.py and
# test_gci_parity_cheap_fetch.py / test_gci_parity_persistence_roundtrip.py).
_GCI_N_INIT_DENSE = 272.0
_GCI_N_INIT_SCALARS_ONLY = 273.0

_PARITY_SCALARS = dict(
    C_peak=0.44,
    C_bar_peak=0.37,
    C_min=-0.21,
    compensated=True,
    type_II=False,
    r_max=4.4e4,
    r_peak=4.7e4,
    M_max=3.4e-2,
    M_peak=3.6e-2,
    V_end_downflow=9.1e-9,
    N_end_downflow=0.041,
)


def _get_prerequisites(pool):
    (dns_list, n_final_list, tol_list, n_colloc_list, alpha_list, efold_list) = ray.get([
        pool.object_get("delta_Nstar", payload_data=[{"value": _DNS_VAL}]),
        pool.object_get("N_final", payload_data=[{"value": _N_FINAL_VAL}]),
        pool.object_get("tolerance", payload_data=[{"log10_tol": _LOG10_TOL}]),
        pool.object_get("n_collocation_points", payload_data=[{"n_collocation_points": _N_COLLOC_VAL}]),
        pool.object_get("alpha_regularization", payload_data=[{"alpha": _ALPHA_VAL}]),
        pool.object_get("efold_value", payload_data=[{"N": n} for n in _N_SAMPLES]),
    ])
    diffusion = ray.get(pool.object_get("MasslessDecoupledDiffusion"))
    cosmo = ray.get(pool.object_get("CosmologicalParams", params=Planck2018()))
    return {
        "dns": dns_list[0],
        "n_final": n_final_list[0],
        "tol": tol_list[0],
        "n_colloc": n_colloc_list[0],
        "alpha": alpha_list[0],
        "efold_values": efold_list,
        "diffusion": diffusion,
        "cosmo": cosmo,
    }


def _mint_n_init(pool, value: float):
    return ray.get(pool.object_get("N_init", payload_data=[{"value": value}]))[0]


def _make_fake_traj():
    return types.SimpleNamespace(store_id=999, units=Planck_units())


def _make_gci(n_init_obj, prereqs, efold_values, n_nodes=_N_COLLOC_VAL, store_full_values=True):
    fake_traj = _make_fake_traj()
    obj = GradientCoupledInstanton(
        store_id=None,
        trajectory=fake_traj,
        N_init=n_init_obj,
        N_final=prereqs["n_final"],
        delta_Nstar=prereqs["dns"],
        n_collocation_points=prereqs["n_colloc"],
        alpha_regularization=prereqs["alpha"],
        atol=prereqs["tol"],
        rtol=prereqs["tol"],
        cosmo=prereqs["cosmo"],
        N_sample=None,
        diffusion_model=prereqs["diffusion"],
    )
    obj._diagnostics = {"compute_time": 0.1, "converged": True}
    obj._failure = False
    obj._N_total = float(_N_SAMPLES[-1])
    obj._noise_field_min, obj._noise_field_mean, obj._noise_field_max = -0.1, 0.0, 0.1
    obj._noise_mom_min, obj._noise_mom_mean, obj._noise_mom_max = -0.2, 0.0, 0.2

    for key, value in _PARITY_SCALARS.items():
        setattr(obj, f"_{key}", value)

    obj._values = [
        GradientCoupledInstantonValue(
            store_id=None,
            N=efold_obj,
            phi=[0.1 * (i + 1) + 0.01 * j for j in range(n_nodes)],
            pi=[0.2 * (i + 1) + 0.01 * j for j in range(n_nodes)],
            rfield=[0.3 * (i + 1) + 0.01 * j for j in range(n_nodes)],
            rmom=[0.4 * (i + 1) + 0.01 * j for j in range(n_nodes)],
        )
        for i, efold_obj in enumerate(efold_values)
    ]
    obj._profile = [
        GradientCoupledInstantonProfileValue(
            node_index=j,
            zeta=0.01 * j,
            r_ratio=1.0 - 0.1 * j,
            C=0.05 * j,
            r_phys=1.0e3 * (n_nodes - j),
            C_bar=0.04 * j,
        )
        for j in range(n_nodes)
    ]
    if not store_full_values:
        obj.set_store_full_values(False)
    return obj, fake_traj


def _fetch(pool, n_init, prereqs, fake_traj, do_not_populate=False, profile_only=False):
    return ray.get(pool.object_get(
        "GradientCoupledInstanton",
        trajectory=fake_traj,
        N_init=n_init,
        N_final=prereqs["n_final"],
        delta_Nstar=prereqs["dns"],
        n_collocation_points=prereqs["n_colloc"],
        alpha_regularization=prereqs["alpha"],
        atol=prereqs["tol"],
        rtol=prereqs["tol"],
        cosmo=prereqs["cosmo"],
        diffusion_model=prereqs["diffusion"],
        _do_not_populate=do_not_populate,
        _profile_only=profile_only,
    ))


@pytest.fixture(scope="module")
def dense_record(live_pool):
    """A GradientCoupledInstanton stored with store_full_values=True (the
    "full (dense-stored)" column of the design doc §4.1 table)."""
    prereqs = _get_prerequisites(live_pool)
    n_init = _mint_n_init(live_pool, _GCI_N_INIT_DENSE)
    obj, fake_traj = _make_gci(n_init, prereqs, prereqs["efold_values"], store_full_values=True)
    stored = ray.get(live_pool.object_store(obj))
    assert stored._my_id is not None
    validated = ray.get(live_pool.object_validate(stored))
    assert validated is True
    return {"n_init": n_init, "prereqs": prereqs, "fake_traj": fake_traj, "orig": obj}


@pytest.fixture(scope="module")
def scalars_only_record(live_pool):
    """A GradientCoupledInstanton stored with store_full_values=False (the
    "full (scalars-only stored)" column of the design doc §4.1 table)."""
    prereqs = _get_prerequisites(live_pool)
    n_init = _mint_n_init(live_pool, _GCI_N_INIT_SCALARS_ONLY)
    obj, fake_traj = _make_gci(n_init, prereqs, prereqs["efold_values"], store_full_values=False)
    stored = ray.get(live_pool.object_store(obj))
    assert stored._my_id is not None
    validated = ray.get(live_pool.object_validate(stored))
    assert validated is True
    return {"n_init": n_init, "prereqs": prereqs, "fake_traj": fake_traj, "orig": obj}


# ---------------------------------------------------------------------------
# scalars / diagnostics -- identical value-present behaviour across
# do_not_populate, profile_only, and full (dense-stored)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["do_not_populate", "profile_only", "full"])
def test_scalars_populated_in_every_reachable_mode(dense_record, live_pool, mode):
    kwargs = {
        "do_not_populate": mode == "do_not_populate",
        "profile_only": mode == "profile_only",
    }
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"], **kwargs)

    assert fetched.C_peak == pytest.approx(_PARITY_SCALARS["C_peak"])
    assert fetched.C_bar_peak == pytest.approx(_PARITY_SCALARS["C_bar_peak"])
    assert fetched.C_min == pytest.approx(_PARITY_SCALARS["C_min"])
    assert fetched.compensated == _PARITY_SCALARS["compensated"]
    assert fetched.type_II == _PARITY_SCALARS["type_II"]
    assert fetched.r_max == pytest.approx(_PARITY_SCALARS["r_max"], rel=1e-12)
    assert fetched.r_peak == pytest.approx(_PARITY_SCALARS["r_peak"], rel=1e-12)
    assert fetched.M_max == pytest.approx(_PARITY_SCALARS["M_max"], rel=1e-12)
    assert fetched.M_peak == pytest.approx(_PARITY_SCALARS["M_peak"], rel=1e-12)
    assert fetched.V_end_downflow == pytest.approx(_PARITY_SCALARS["V_end_downflow"], rel=1e-12)
    assert fetched.N_end_downflow == pytest.approx(_PARITY_SCALARS["N_end_downflow"])


@pytest.mark.parametrize("mode", ["do_not_populate", "profile_only", "full"])
def test_diagnostics_populated_in_every_reachable_mode(dense_record, live_pool, mode):
    kwargs = {
        "do_not_populate": mode == "do_not_populate",
        "profile_only": mode == "profile_only",
    }
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"], **kwargs)

    assert fetched._diagnostics is not None
    assert fetched._diagnostics.get("compute_time") == pytest.approx(0.1)
    assert fetched._diagnostics.get("converged") is True


# ---------------------------------------------------------------------------
# profile (zeta/C/C_bar/r) -- [] under do_not_populate; populated under
# profile_only and full, regardless of dense-vs-scalars-only storage
# ---------------------------------------------------------------------------


def test_profile_empty_under_do_not_populate(dense_record, live_pool):
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"], do_not_populate=True)
    assert fetched.profile == []


def test_profile_populated_under_profile_only_dense_stored(dense_record, live_pool):
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"], profile_only=True)
    assert len(fetched.profile) == _N_COLLOC_VAL
    assert fetched.values == []


def test_profile_populated_under_full_dense_stored(dense_record, live_pool):
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"])
    assert len(fetched.profile) == _N_COLLOC_VAL
    assert len(fetched.values) == len(_N_SAMPLES)


def test_profile_populated_under_profile_only_scalars_only_stored(scalars_only_record, live_pool):
    """The whole point of the profile_only mode (design doc §4.1): reading
    the always-persisted profile off a scalars-only-stored record succeeds,
    without tripping the dense-values guard."""
    fetched = _fetch(live_pool, scalars_only_record["n_init"], scalars_only_record["prereqs"],
                      scalars_only_record["fake_traj"], profile_only=True)
    assert len(fetched.profile) == _N_COLLOC_VAL
    assert fetched.values == []
    # Scalars/diagnostics remain available too, per invariant 4.
    assert fetched.C_peak == pytest.approx(_PARITY_SCALARS["C_peak"])
    assert fetched._diagnostics is not None
    assert fetched._diagnostics.get("full_values_stored") is False


# ---------------------------------------------------------------------------
# values (dense y,N) -- [] under do_not_populate/profile_only; populated
# under full (dense-stored); build() raises under full (scalars-only stored)
# ---------------------------------------------------------------------------


def test_values_empty_under_do_not_populate(dense_record, live_pool):
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"], do_not_populate=True)
    assert fetched.values == []


def test_values_empty_under_profile_only(dense_record, live_pool):
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"], profile_only=True)
    assert fetched.values == []


def test_values_populated_under_full_dense_stored(dense_record, live_pool):
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"])
    assert len(fetched.values) == len(_N_SAMPLES)


def test_full_fetch_raises_on_scalars_only_stored(scalars_only_record, live_pool):
    with pytest.raises(RuntimeError, match="scalars-only mode"):
        _fetch(live_pool, scalars_only_record["n_init"], scalars_only_record["prereqs"],
               scalars_only_record["fake_traj"])


# ---------------------------------------------------------------------------
# zeta_C_r_at_time -- raises under do_not_populate/profile_only (empty
# _values trips the existing "if not self._values" guard, per invariant 3);
# guard does not fire once _values is populated (full, dense-stored)
# ---------------------------------------------------------------------------


def test_zeta_c_r_at_time_raises_under_do_not_populate(dense_record, live_pool):
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"], do_not_populate=True)
    with pytest.raises(RuntimeError, match="no stored per-sample values"):
        fetched.zeta_C_r_at_time(dense_record["prereqs"]["efold_values"][0])


def test_zeta_c_r_at_time_raises_under_profile_only(dense_record, live_pool):
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"], profile_only=True)
    with pytest.raises(RuntimeError, match="no stored per-sample values"):
        fetched.zeta_C_r_at_time(dense_record["prereqs"]["efold_values"][0])


def test_zeta_c_r_at_time_guard_does_not_fire_under_full_dense_stored(dense_record, live_pool):
    """Confirms invariant 3's precondition -- a full (dense-stored) fetch
    populates _values, so the guard's `if not self._values` is False and the
    RuntimeError is not raised. Does not drive the method to a full
    numerical result: that needs genuine trajectory/potential physics
    unrelated to the fetch-mode contract under test here."""
    fetched = _fetch(live_pool, dense_record["n_init"], dense_record["prereqs"],
                      dense_record["fake_traj"])
    assert fetched.values != []
