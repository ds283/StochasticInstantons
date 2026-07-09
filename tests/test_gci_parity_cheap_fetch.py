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
Acceptance test (b) for prompt U3
(.prompts/gradient-coupled-plotting/04-U3-persist-and-rehydrate-parity-columns.md).

Stores a GradientCoupledInstanton with a full computed result, then reloads
it via build() with _do_not_populate=True (the cheap fetch tier DOE/sweep
figures use). Asserts all eleven parity scalars are populated (not None)
while .values and .profile are both empty lists -- i.e. the parity-scalar
rehydration in
Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py's build() happens
unconditionally, not gated on do_not_populate (this is the whole point of
the parity requirement: these are parent-row scalars, exactly like
msr_action, not child-row values).

Setup mirrors test_gci_parity_persistence_roundtrip.py's own
_make_gci_with_parity helper (duplicated here per this test suite's existing
convention of each file carrying its own self-contained stubs/helpers, e.g.
tests/test_gci_parity_scalars.py vs.
tests/test_gradient_coupled_instanton_end_to_end.py).
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

_DNS_VAL = 0.62
_N_FINAL_VAL = 1.02
_LOG10_TOL = -6.0
_N_COLLOC_VAL = 4
_ALPHA_VAL = 0.05
_N_SAMPLES = [0.0, 0.05, 0.10]

_GCI_N_INIT_CHEAP_FETCH = 271.0

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


def _make_gci_with_parity(n_init_obj, prereqs, efold_values, n_nodes=_N_COLLOC_VAL):
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
    return obj, fake_traj


@pytest.mark.integration
def test_gci_parity_scalars_populated_on_cheap_fetch(live_pool):
    prereqs = _get_prerequisites(live_pool)
    n_init = _mint_n_init(live_pool, _GCI_N_INIT_CHEAP_FETCH)
    gci, fake_traj = _make_gci_with_parity(n_init, prereqs, prereqs["efold_values"])

    gci_stored = ray.get(live_pool.object_store(gci))
    assert gci_stored._my_id is not None

    validated = ray.get(live_pool.object_validate(gci_stored))
    assert validated is True

    gci_read = ray.get(live_pool.object_get(
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
        _do_not_populate=True,
    ))

    # The whole point of the parity requirement: cheap tier still carries
    # every parent-row scalar.
    assert gci_read.C_peak is not None
    assert gci_read.C_bar_peak is not None
    assert gci_read.C_min is not None
    assert gci_read.compensated is not None
    assert gci_read.type_II is not None
    assert gci_read.r_max is not None
    assert gci_read.r_peak is not None
    assert gci_read.M_max is not None
    assert gci_read.M_peak is not None
    assert gci_read.V_end_downflow is not None
    assert gci_read.N_end_downflow is not None

    assert gci_read.C_peak == pytest.approx(gci.C_peak)
    assert gci_read.r_max == pytest.approx(gci.r_max, rel=1e-12)
    assert gci_read.M_max == pytest.approx(gci.M_max, rel=1e-12)
    assert gci_read.V_end_downflow == pytest.approx(gci.V_end_downflow, rel=1e-12)

    # But the child-row tables (values/profile) stay empty -- that's the
    # cost this cheap tier is buying.
    assert gci_read.values == []
    assert gci_read.profile == []
