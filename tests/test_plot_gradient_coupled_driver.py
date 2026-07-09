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
Acceptance test for Prompt P8
(.prompts/gradient-coupled-plotting/13-P8-new-driver-and-compare-mode.md):
`plot_GradientCoupledSolutions.py`'s CLI surface and `--compare-with` wiring.

Per the prompt's own acceptance-test guidance ("preferably assert on the
adapter list length passed into the figure function via a unit test on the
wiring code itself, rather than parsing rendered image content"), this file
does not drive a live Ray cluster/database end-to-end. Instead:

1. CLI surface: `create_plot_parser()` accepts the driver-local flags this
   prompt specifies, and does NOT add the forbidden
   `--n-collocation-{low,high,samples,values}` / `--alpha-{low,high,samples,
   values}` quartets (this prompt set's `00-README.md` "Correction 1").
2. Pure wiring unit tests: `_build_class_specs`/`_compare_class_specs`/
   `_cf_spec_if_full_and_sr`/`_coords_of_gci_item`/`_gci_key_payload` --
   the functions that determine how many adapters end up in the list handed
   to each figure function, and in what order, as `--compare-with` varies.
3. An adapter-list-length test that exercises the real `ClassFetchSpec`
   `adapter_factory` callables built by `_build_class_specs` against
   duck-typed stand-ins for `GradientCoupledInstanton`/`FullInstanton`/
   `SlowRollInstanton` (mirroring `tests/test_plot_gradient_adapter.py`'s own
   stub convention), confirming `_collect_gci_points` produces an
   `adapters` list of the expected length/order for every `--compare-with`
   combination, with `adapters[0]` always the GradientCoupledAdapter.
"""

import plot_GradientCoupledSolutions as driver
from plotting.adapters.full import FullInstantonAdapter
from plotting.adapters.gradient import GradientCoupledAdapter
from plotting.adapters.slow_roll import SlowRollInstantonAdapter


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def _option_strings(parser):
    names = set()
    for action in parser._actions:
        names.update(action.option_strings)
    return names


def test_cli_has_expected_driver_flags():
    parser = driver.create_plot_parser()
    names = _option_strings(parser)
    for flag in (
        "--output-dir",
        "--format",
        "--max-trajectories",
        "--max-combinations",
        "--max-instanton-samples",
        "--movies",
        "--movie-format",
        "--compare-with",
        "--spatial-samples",
        "--time-resolved-derived",
    ):
        assert flag in names, f"expected flag {flag!r} missing from parser"


def test_cli_does_not_add_forbidden_axis_quartets():
    parser = driver.create_plot_parser()
    names = _option_strings(parser)
    for flag in (
        "--n-collocation-low",
        "--n-collocation-high",
        "--n-collocation-samples",
        "--n-collocation-values",
        "--alpha-low",
        "--alpha-high",
        "--alpha-samples",
        "--alpha-values",
    ):
        assert flag not in names, f"forbidden flag {flag!r} was added (see 00-README.md Correction 1)"


def test_cli_compare_with_choices_and_default():
    parser = driver.create_plot_parser()
    action = next(a for a in parser._actions if "--compare-with" in a.option_strings)
    assert action.default == []
    assert set(action.choices) == {"full", "slow-roll"}


# ---------------------------------------------------------------------------
# Pure wiring helpers
# ---------------------------------------------------------------------------

_TRAJ_PROXY = object()
_ATOL = object()
_RTOL = object()
_COSMO = object()
_DM = object()

_ITEM = ((60.0, 10.0, 0.5), 24, 0.02)


def test_coords_of_gci_item():
    coords = driver._coords_of_gci_item(_ITEM)
    assert coords == {
        "N_init": 60.0,
        "N_final": 10.0,
        "delta_Nstar": 0.5,
        "n_collocation_points": 24,
        "alpha": 0.02,
    }


def test_gci_key_payload_carries_identity_fields():
    payload = driver._gci_key_payload(
        _TRAJ_PROXY, 60.0, 10.0, 0.5, 24, 0.02, _ATOL, _RTOL, _COSMO, _DM
    )
    assert payload["trajectory"] is _TRAJ_PROXY
    assert payload["N_init"] == 60.0
    assert payload["N_final"] == 10.0
    assert payload["delta_Nstar"] == 0.5
    assert payload["n_collocation_points"] == 24
    assert payload["alpha_regularization"] == 0.02
    assert payload["atol"] is _ATOL
    assert payload["rtol"] is _RTOL
    assert payload["cosmo"] is _COSMO
    assert payload["diffusion_model"] is _DM
    assert payload["tags"] == []


def test_build_class_specs_length_and_order_track_compare_with():
    for compare_with, expected_names in (
        ([], ["gci"]),
        (["full"], ["gci", "full"]),
        (["slow-roll"], ["gci", "slow-roll"]),
        (["full", "slow-roll"], ["gci", "full", "slow-roll"]),
    ):
        specs = driver._build_class_specs(
            _TRAJ_PROXY, _ATOL, _RTOL, _COSMO, _DM, compare_with, fidelity="scalars"
        )
        assert [s.name for s in specs] == expected_names
        # GCI spec is always first, regardless of --compare-with order, so
        # every call site in the driver can rely on adapters[0] being the
        # GradientCoupledAdapter.
        assert specs[0].name == "gci"
        assert specs[0].class_name == "GradientCoupledInstanton"


def test_cf_spec_only_built_when_both_full_and_slow_roll_requested():
    assert driver._cf_spec_if_full_and_sr(_TRAJ_PROXY, _COSMO, _ATOL, _RTOL, []) is None
    assert driver._cf_spec_if_full_and_sr(_TRAJ_PROXY, _COSMO, _ATOL, _RTOL, ["full"]) is None
    assert driver._cf_spec_if_full_and_sr(_TRAJ_PROXY, _COSMO, _ATOL, _RTOL, ["slow-roll"]) is None
    cf_spec = driver._cf_spec_if_full_and_sr(_TRAJ_PROXY, _COSMO, _ATOL, _RTOL, ["full", "slow-roll"])
    assert cf_spec is not None
    assert cf_spec.fi_spec_name == "full"
    assert cf_spec.sri_spec_name == "slow-roll"


# ---------------------------------------------------------------------------
# Adapter-list-length wiring, via the real ClassFetchSpec.adapter_factory
# callables built by _build_class_specs (no live Ray/pool involved)
# ---------------------------------------------------------------------------


class _UnitsStub:
    PlanckMass = 1.0
    Mpc = 2.0
    SolarMass = 5.0


class _TrajStub:
    units = _UnitsStub()


class _ToleranceStub:
    tol = 1e-8


class _GCIStub:
    """Minimal duck-typed stand-in for GradientCoupledInstanton, covering
    exactly the surface GradientCoupledAdapter reads at "scalars" fidelity
    (mirrors tests/test_plot_gradient_adapter.py's own _GCIStub)."""

    def __init__(self, available=True):
        self.available = available
        self.failure = False
        self.store_id = 1 if available else None
        self.values = []
        self.profile = []
        self.msr_action = 1e-3
        self.noise_field_min = -0.1
        self.noise_field_mean = 0.0
        self.noise_field_max = 0.1
        self.noise_mom_min = -0.2
        self.noise_mom_mean = 0.0
        self.noise_mom_max = 0.2
        self.diagnostics = {"converged": True}
        self.timestamp = None
        self.n_collocation_points_value = 24
        self._trajectory = _TrajStub()
        self._atol = _ToleranceStub()
        self._rtol = _ToleranceStub()
        self.C_peak = 0.5
        self.C_bar_peak = 0.3
        self.C_min = -0.1
        self.compensated = True
        self.type_II = False
        self.r_max = 10.0
        self.r_peak = 4.0
        self.M_max = 15.0
        self.M_peak = 25.0
        self.V_end_downflow = 1e-9
        self.N_end_downflow = 0.05


class _HomogeneousStub:
    """Minimal duck-typed stand-in shared by FullInstanton/SlowRollInstanton
    -- both adapters read the same subset of attributes at "scalars"
    fidelity (do_not_populate=True, no CompactionFunction paired)."""

    def __init__(self, available=True):
        self.available = available
        self.failure = False
        self.store_id = 2 if available else None
        self.values = []
        self.msr_action = 2e-3
        self.noise_phi1_min = -0.1
        self.noise_phi1_mean = 0.0
        self.noise_phi1_max = 0.1
        self.noise_phi2_min = -0.2
        self.noise_phi2_mean = 0.0
        self.noise_phi2_max = 0.2
        self.diagnostics = {"converged": True}
        self.timestamp = None
        self._trajectory = _TrajStub()
        self._atol = _ToleranceStub()
        self._rtol = _ToleranceStub()


def _fake_fetch_adapters_over_grid(pool, items, class_specs, coords_of, cf_spec=None, do_not_populate=True):
    """Stands in for plotting.fetch.fetch_adapters_over_grid: skips the
    pool/Ray round-trip entirely, but calls the SAME adapter_factory
    callables _build_class_specs wired up, against a duck-typed stand-in
    object per spec -- so this exercises the driver's real wiring, not a
    re-implementation of it."""
    stub_by_class = {
        "GradientCoupledInstanton": _GCIStub(),
        "FullInstanton": _HomogeneousStub(),
        "SlowRollInstanton": _HomogeneousStub(),
    }
    rows = []
    for item in items:
        coords = coords_of(item)
        rows.append(
            [
                spec.adapter_factory(stub_by_class[spec.class_name], None, coords)
                for spec in class_specs
            ]
        )
    return rows


def test_collect_gci_points_adapter_list_length_tracks_compare_with(monkeypatch):
    monkeypatch.setattr(driver, "fetch_adapters_over_grid", _fake_fetch_adapters_over_grid)

    gci_grid = [_ITEM]

    for compare_with, expected_len, expected_kinds in (
        ([], 1, ["gradient-coupled"]),
        (["full"], 2, ["gradient-coupled", "full"]),
        (["slow-roll"], 2, ["gradient-coupled", "slow-roll"]),
        (["full", "slow-roll"], 3, ["gradient-coupled", "full", "slow-roll"]),
    ):
        points = driver._collect_gci_points(
            pool=None, traj_proxy=_TRAJ_PROXY, gci_grid=gci_grid, cosmo=_COSMO,
            atol=_ATOL, rtol=_RTOL, dm=_DM, compare_with=compare_with,
        )
        assert len(points) == 1
        adapters = points[0]["adapters"]
        assert len(adapters) == expected_len
        assert [a.kind for a in adapters] == expected_kinds
        # adapters[0] is always the GCI adapter -- every call site in the
        # driver (and every figure function fed by it) can rely on this.
        assert isinstance(adapters[0], GradientCoupledAdapter)
        if "full" in compare_with:
            assert any(isinstance(a, FullInstantonAdapter) for a in adapters)
        if "slow-roll" in compare_with:
            assert any(isinstance(a, SlowRollInstantonAdapter) for a in adapters)


def test_flatten_gci_points_for_csv_has_one_column_family_per_kind():
    monkeypatch_targets = {
        "GradientCoupledInstanton": _GCIStub(),
        "FullInstanton": _HomogeneousStub(),
    }
    class_specs = driver._build_class_specs(
        _TRAJ_PROXY, _ATOL, _RTOL, _COSMO, _DM, ["full"], fidelity="scalars"
    )
    coords = driver._coords_of_gci_item(_ITEM)
    adapters = [
        spec.adapter_factory(monkeypatch_targets[spec.class_name], None, coords)
        for spec in class_specs
    ]
    points = [
        {
            "delta_Nstar": 0.5,
            "delta_N": 50.0,
            "alpha": 0.02,
            "n_collocation_points": 24,
            "adapters": adapters,
        }
    ]
    rows = driver._flatten_gci_points_for_csv(points)
    assert len(rows) == 1
    row = rows[0]
    assert row["N_init"] == 60.0
    assert row["delta_Nstar"] == 0.5
    assert row["C_peak_gradient_coupled"] == 0.5
    assert row["msr_action_full"] == 2e-3
