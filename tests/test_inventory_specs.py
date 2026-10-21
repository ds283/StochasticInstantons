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

"""The inventory's declarations: each factory's ``inventory_spec()`` (dk-and-rpk-migration
prompt 10, N1 and N5).

No Ray and no store: importing ``config.datastore`` builds the factories, and the tables are the
ones ``datastorekit.SQL.schema.build_schema`` builds from them, in memory.

- the package's ``inventory_classes`` accepts SI's registry and orders it; 22 definitions serve
  24 registry entries (``sqla_dimensionful_quantity_factory`` serves three);
- each spec is the identity its factory's ``build`` matches, as the prompt's results note derives
  it table by table. ``EXPECTED_SPECS`` writes that table out, so that a spec which names the
  right columns but a different identity (a leaf or a parent dropped, added or moved) fails here,
  not only in review;
- every column a spec names is a column of the table the package builds; the four polymorphic
  maps are SI's registries' and ``tools/compare_stores.py``'s; no parent crosses a shard; and
  ``version`` is no parent (no lookup matches it);
- **coverage** (U8, the user's ruling, README §6.1): every registered class declares a spec, or is
  a value table read through an owner's spec, named here with its owner and slot, or is excluded
  here by name with a reason. RunRegistryKit's fingerprint, which SI adopts after this campaign,
  reads only the classes that declare a spec and passes over the rest silently, so a class in none
  of the three would go unfingerprinted. The three places are written out below; nothing here
  reads the specs to decide where a class belongs.
"""

from typing import Dict, List, Mapping, Tuple

import sqlalchemy as sqla
from datastorekit.SQL.schema import build_schema
from datastorekit.store_inventory import (
    InventorySpec,
    inventory_classes,
    inventory_specs,
)

from config.datastore import factories
from config.sharding import replicated_tables, sharded_tables
from CosmologyConcepts.Potentials.model_ids import (
    QUADRATIC_POTENTIAL,
    QUARTIC_POTENTIAL,
)
from InflationConcepts.DiffusionModel.model_ids import MASSLESS_DECOUPLED_DIFFUSION

# inventory_classes' order, derived by the package from the specs: the classes that reference
# nothing in registry order, then each class once every class it references has been placed
EXPECTED_ORDER = [
    "version",
    "store_tag",
    "redshift",
    "tolerance",
    "efold_value",
    "delta_Nstar",
    "N_init",
    "N_final",
    "n_collocation_points",
    "alpha_regularization",
    "inflaton_mass",
    "quartic_coupling",
    "phi_value",
    "pi_value",
    "MasslessDecoupledDiffusion",
    "IntegrationSolver",
    "CosmologicalParams",
    "QuadraticPotential",
    "QuarticPotential",
    "InflatonTrajectory",
    "FullInstanton",
    "GradientCoupledInstanton",
    "SlowRollInstanton",
    "CompactionFunction",
]

_POTENTIALS = "potentials"
_DIFFUSION = "diffusion models"

_TOLERANCES = {
    "atol": ("atol_serial", "tolerance"),
    "rtol": ("rtol_serial", "tolerance"),
}
_INSTANTON = {
    "trajectory": ("trajectory_serial", "InflatonTrajectory"),
    "N_init": ("N_init_serial", "N_init"),
    "N_final": ("N_final_serial", "N_final"),
    "delta_Nstar": ("delta_Nstar_serial", "delta_Nstar"),
    **_TOLERANCES,
    "diffusion_model": ("diffusion_serial", _DIFFUSION, "diffusion_type"),
}

# The spec table, class by class, as each build() matches (the results note gives each source):
# (leaves, {key field: (column, parent class or polymorphic map[, type column][, "nullable"])},
#  values, validated)
EXPECTED_SPECS: Dict[str, tuple] = {
    "version": (("label",), {}, None, None),
    "store_tag": (("label",), {}, None, None),
    "redshift": (("z",), {}, None, None),
    "tolerance": (("log10_tol",), {}, None, None),
    "efold_value": (("N",), {}, None, None),
    "delta_Nstar": (("value",), {}, None, None),
    "N_init": (("value",), {}, None, None),
    "N_final": (("value",), {}, None, None),
    "n_collocation_points": (("n_collocation_points",), {}, None, None),
    "alpha_regularization": (("alpha",), {}, None, None),
    "inflaton_mass": (("value_PlanckMass",), {}, None, None),
    "quartic_coupling": (("value",), {}, None, None),
    "phi_value": (("value_PlanckMass",), {}, None, None),
    "pi_value": (("value_PlanckMass",), {}, None, None),
    "QuadraticPotential": ((), {"m": ("mass_id", "inflaton_mass")}, None, None),
    "QuarticPotential": (
        (),
        {"lambda_": ("coupling_id", "quartic_coupling")},
        None,
        None,
    ),
    "MasslessDecoupledDiffusion": ((), {}, None, None),
    "IntegrationSolver": (("label", "stepping"), {}, None, None),
    "CosmologicalParams": (("name",), {}, None, None),
    "InflatonTrajectory": (
        ("potential_type",),
        {
            "phi0": ("phi0_serial", "phi_value"),
            "pi0": ("pi0_serial", "pi_value"),
            "potential": ("potential_serial", _POTENTIALS, "potential_type"),
            **_TOLERANCES,
        },
        ("InflatonTrajectoryValue", "trajectory_serial"),
        "validated",
    ),
    "FullInstanton": (
        ("diffusion_type",),
        dict(_INSTANTON),
        ("FullInstantonValue", "instanton_serial"),
        "validated",
    ),
    "SlowRollInstanton": (
        ("diffusion_type",),
        dict(_INSTANTON),
        ("SlowRollInstantonValue", "instanton_serial"),
        "validated",
    ),
    "GradientCoupledInstanton": (
        ("diffusion_type",),
        {
            **_INSTANTON,
            "n_collocation_points": (
                "n_collocation_points_serial",
                "n_collocation_points",
            ),
            "alpha_regularization": (
                "alpha_regularization_serial",
                "alpha_regularization",
            ),
            "cosmo": ("cosmo_serial", "CosmologicalParams"),
        },
        ("GradientCoupledInstantonProfile", "parent_serial"),
        "validated",
    ),
    "CompactionFunction": (
        (),
        {
            "trajectory": ("trajectory_serial", "InflatonTrajectory"),
            "full_instanton": ("full_instanton_serial", "FullInstanton", "nullable"),
            "slow_roll_instanton": (
                "slow_roll_instanton_serial",
                "SlowRollInstanton",
                "nullable",
            ),
            "delta_Nstar": ("delta_Nstar_serial", "delta_Nstar"),
            "cosmo": ("cosmo_serial", "CosmologicalParams"),
            **_TOLERANCES,
        },
        ("CompactionFunctionSamples", "parent_serial"),
        "validated",
    ),
}

_MAPS = {
    _POTENTIALS: {
        QUADRATIC_POTENTIAL: "QuadraticPotential",
        QUARTIC_POTENTIAL: "QuarticPotential",
    },
    _DIFFUSION: {MASSLESS_DECOUPLED_DIFFUSION: "MasslessDecoupledDiffusion"},
}

# N5: the registered classes that declare no spec of their own, each read through an owner's
# spec, by (owner, slot). The test checks that the owner's spec names the table in that slot
READ_THROUGH: Dict[str, Tuple[str, str]] = {
    "InflatonTrajectoryValue": ("InflatonTrajectory", "values"),
    "FullInstantonValue": ("FullInstanton", "values"),
    "SlowRollInstantonValue": ("SlowRollInstanton", "values"),
    "CompactionFunctionSamples": ("CompactionFunction", "values"),
    "GradientCoupledInstantonProfile": ("GradientCoupledInstanton", "values"),
}

# N5: the registered classes that are in no spec, each with a one-line reason
EXCLUDED: Dict[str, str] = {
    "GradientCoupledInstantonValue": (
        "written only when store_full_values is set, and a spec has one values slot, which "
        "GradientCoupledInstantonProfile (written for every row) takes; a fingerprint cannot see "
        "it: [gci-value-table-outside-the-inventory]"
    ),
}

SLOTS = ("tags", "values", "parent_sets")


def _spec(factory):
    hook = getattr(factory, "inventory_spec", None)
    return hook() if hook is not None else None


def _slot_tables(spec: InventorySpec, slot: str) -> List[str]:
    if slot == "parent_sets":
        return [p.table for p in spec.parent_sets.values()]
    value = getattr(spec, slot)
    return [] if value is None else [value[0]]


def coverage_failures(
    registry: Mapping,
    read_through: Mapping[str, Tuple[str, str]],
    excluded: Mapping[str, str],
) -> List[str]:
    """
    Every way ``registry`` fails N5: a class in none of the three places, or in more than one; a
    read-through entry whose owner does not name the table in that slot, or names an unknown
    slot or an owner with no spec; an entry naming a class no longer registered; an exclusion with
    no reason. Empty when every registered class is placed exactly once.
    """
    failures = []
    for name in list(read_through) + list(excluded):
        if name not in registry:
            failures.append(f"{name}: named in the test but no longer registered")
    for name, reason in excluded.items():
        if not isinstance(reason, str) or reason.strip() == "":
            failures.append(f"{name}: excluded with no reason")

    for name, factory in registry.items():
        spec = _spec(factory)
        places = []
        if spec is not None:
            if not isinstance(spec, InventorySpec):
                failures.append(f"{name}: inventory_spec() returned {spec!r}")
            places.append("declares a spec")
        if name in read_through:
            places.append("read through an owner's spec")
            owner, slot = read_through[name]
            owner_spec = _spec(registry[owner]) if owner in registry else None
            if slot not in SLOTS:
                failures.append(f"{name}: read through an unknown slot {slot!r}")
            elif owner_spec is None:
                failures.append(f"{name}: its owner {owner} declares no spec")
            elif name not in _slot_tables(owner_spec, slot):
                failures.append(f"{name}: {owner}'s spec does not name it in {slot}")
        if name in excluded:
            places.append("excluded")
        if len(places) == 0:
            failures.append(
                f"{name}: declares no inventory_spec, is read through no owner's spec, and is "
                f"not excluded"
            )
        elif len(places) > 1:
            failures.append(f"{name}: in more than one place ({', '.join(places)})")
    return failures


def _specs() -> Dict[str, InventorySpec]:
    return {n: _spec(f) for n, f in factories.items() if _spec(f) is not None}


def _as_table(spec: InventorySpec) -> tuple:
    """A spec in EXPECTED_SPECS' form; a polymorphic map by its name in ``_MAPS``."""
    parents = {}
    for field, parent in spec.parents.items():
        if parent.types is None:
            entry = (parent.column, parent.of)
        else:
            (name,) = [n for n, m in _MAPS.items() if dict(parent.types) == m] or [
                dict(parent.types)
            ]
            entry = (parent.column, name, parent.type_column)
        if parent.nullable:
            entry = entry + ("nullable",)
        parents[field] = entry
    return (tuple(spec.leaves), parents, spec.values, spec.validated)


# --- the specs -------------------------------------------------------------------------------


def test_inventory_classes_accepts_the_registry_and_orders_it():
    assert inventory_classes(factories) == EXPECTED_ORDER


def test_twenty_two_definitions_serve_twenty_four_entries():
    specs = inventory_specs(factories)
    assert len(specs) == 24
    defining = {
        cls
        for name in specs
        for cls in type(factories[name]).__mro__
        if "inventory_spec" in cls.__dict__ and cls.__module__.startswith("Datastore.")
    }
    assert len(defining) == 22
    # the one dimensionful factory class serves three entries, each by its own value column
    assert {n: specs[n].leaves for n in ("inflaton_mass", "phi_value", "pi_value")} == {
        "inflaton_mass": ("value_PlanckMass",),
        "phi_value": ("value_PlanckMass",),
        "pi_value": ("value_PlanckMass",),
    }


def test_each_spec_is_the_identity_its_build_matches():
    specs = _specs()
    assert set(specs) == set(EXPECTED_SPECS)
    for name, expected in EXPECTED_SPECS.items():
        spec = specs[name]
        assert _as_table(spec) == expected, name
        assert dict(spec.parent_sets) == {}, name
        assert spec.tags is None, name


def test_every_named_column_is_a_column_of_its_table():
    tables = build_schema(sqla.MetaData(), factories).tables
    for name, spec in _specs().items():
        table = tables[name]
        assert "serial" in table.c, name
        for leaf in spec.leaves:
            assert leaf in table.c, f"{name}: leaf {leaf}"
        for field, parent in spec.parents.items():
            assert parent.column in table.c, f"{name}.{field}: {parent.column}"
            if parent.type_column is not None:
                assert parent.type_column in table.c, f"{name}.{field}"
                assert parent.type_column in spec.leaves, f"{name}.{field}"
            for of in parent.classes():
                assert of in factories, f"{name}.{field}: {of}"
        if spec.validated is not None:
            assert spec.validated in table.c, f"{name}: validated"
        if spec.values is not None:
            value_table, column = spec.values
            assert column in tables[value_table].c, f"{name}: values"
            # the value table names its owner by foreign key on that column
            assert {
                fk.column.table.name
                for fk in tables[value_table].c[column].foreign_keys
            } == {name}, f"{name}: values"


def test_the_polymorphic_maps_are_si_registries_and_compare_stores():
    from CosmologyConcepts.Potentials.registry import POTENTIAL_REGISTRY
    from InflationConcepts.DiffusionModel.registry import DIFFUSION_MODEL_REGISTRY
    from tools.compare_stores import POLYMORPHIC_REFERENCES

    assert {t: i.table_name for t, i in POTENTIAL_REGISTRY.items()} == _MAPS[
        _POTENTIALS
    ]
    assert {t: i.name for t, i in DIFFUSION_MODEL_REGISTRY.items()} == _MAPS[_DIFFUSION]
    specs = _specs()
    found = {}
    for name, spec in specs.items():
        for parent in spec.parents.values():
            if parent.types is not None:
                found.setdefault(name, {})[parent.column] = (
                    parent.type_column,
                    dict(parent.types),
                )
    assert found == POLYMORPHIC_REFERENCES


def test_no_parent_crosses_a_shard():
    # a sharded parent is named only by a sharded child, sharded on the same delta_Nstar; every
    # other parent is replicated, so on every shard
    for name, spec in _specs().items():
        for field, parent in spec.parents.items():
            assert not parent.cross_shard, f"{name}.{field}"
            for of in parent.classes():
                if of in sharded_tables:
                    assert sharded_tables.get(name) == sharded_tables[of], (
                        f"{name}.{field}"
                    )
                else:
                    assert of in replicated_tables, f"{name}.{field}: {of}"


def test_version_is_no_parent():
    # no SI lookup matches a version: a rerun under a new label reuses the validated row
    for name, spec in _specs().items():
        assert "version" not in spec.dependencies(), name
        assert "version" not in spec.leaves, name


# --- coverage (N5; U8) -------------------------------------------------------------------------


def test_every_registered_class_is_placed_exactly_once():
    registry = dict(factories)
    assert coverage_failures(registry, READ_THROUGH, EXCLUDED) == []
    assert len(registry) == 30
    declaring = [n for n, f in registry.items() if _spec(f) is not None]
    assert (len(declaring), len(READ_THROUGH), len(EXCLUDED)) == (24, 5, 1)


def test_a_class_in_none_of_the_three_is_named():
    registry = dict(factories)
    registry["Scratch"] = factories["FullInstantonValue"]
    assert coverage_failures(registry, READ_THROUGH, EXCLUDED) == [
        "Scratch: declares no inventory_spec, is read through no owner's spec, and is not excluded"
    ]


def test_a_class_in_two_places_is_named():
    excluded = dict(EXCLUDED, FullInstantonValue="stale")
    assert coverage_failures(dict(factories), READ_THROUGH, excluded) == [
        "FullInstantonValue: in more than one place (read through an owner's spec, excluded)"
    ]


def test_a_stale_or_unexplained_exclusion_is_named():
    assert coverage_failures(
        dict(factories), READ_THROUGH, dict(EXCLUDED, temperature="no table")
    ) == ["temperature: named in the test but no longer registered"]
    assert coverage_failures(
        dict(factories), READ_THROUGH, {"GradientCoupledInstantonValue": " "}
    ) == ["GradientCoupledInstantonValue: excluded with no reason"]


def test_a_wrong_slot_or_owner_is_named():
    read_through = dict(READ_THROUGH)
    read_through["GradientCoupledInstantonProfile"] = (
        "GradientCoupledInstanton",
        "tags",
    )
    assert coverage_failures(dict(factories), read_through, EXCLUDED) == [
        "GradientCoupledInstantonProfile: GradientCoupledInstanton's spec does not name it in tags"
    ]
    read_through = dict(READ_THROUGH)
    read_through["FullInstantonValue"] = ("SlowRollInstanton", "values")
    assert coverage_failures(dict(factories), read_through, EXCLUDED) == [
        "FullInstantonValue: SlowRollInstanton's spec does not name it in values"
    ]
