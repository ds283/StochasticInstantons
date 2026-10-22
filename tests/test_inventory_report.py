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

"""``tools/inventory_report.py``: the report ``main.py --inventory`` prints (dk-and-rpk-migration
prompt 10, N2).

No Ray and no store: each test renders a ``StoreInventory`` built here, record by record, from
values the test chooses, in the form ``read_inventory`` returns (a float leaf as ``float.hex``, a
parent as the parent's reference digest). Every assertion is on the rendered decimal text, with
its unit, against the value chosen here; nothing is re-derived from a key. The fields asserted are
those of today's report (P18; the results note's field table): each parameter's and quantity's
values, a dimensionful one in its unit; more than 20 values truncated to the first and last ten,
and 20 shown whole; "no values committed"; per compute target the validated and unvalidated
counts, the timestamp range and the records by physical labels; and every named problem whole on
one line. ``verbose`` (``--show-all``) truncates nothing. A last test reads the module's source:
it opens no file and no store.
"""

import ast
from datetime import datetime
from pathlib import Path

from datastorekit.store_inventory import (
    ClassInventory,
    Record,
    StoreInventory,
    reference_digest,
)

from tools.inventory_report import format_inventory_report

_ROOT = Path(__file__).resolve().parent.parent

# a problem longer than any width the renderer uses, with no newline: it must print whole
_LONG_PROBLEM = (
    "orphan-value: FullInstanton: 3 FullInstantonValue row(s) on shard #1 name 1 FullInstanton "
    "row(s) that are not there; e.g. parent serials 999; "
    + "and this explanation goes on " * 20
    + "to the very end"
)

_T0 = datetime(2026, 10, 21, 10, 19, 0)
_T1 = datetime(2026, 10, 21, 10, 20, 30)


def _h(x):
    return float.hex(float(x))


def _ref(record):
    return reference_digest(record.key, (), False)


def _rec(key, validated=None, value_count=None):
    return Record(key=key, tags=(), validated=validated, value_count=value_count)


def _cls(
    name,
    records,
    replicated=True,
    parents=None,
    parent_types=None,
    problems=(),
    stamps=None,
):
    stamps = stamps or (None, None)
    return ClassInventory(
        name=name,
        replicated=replicated,
        tagged=False,
        parents=dict(parents or {}),
        records=tuple(records),
        count=len(records),
        earliest_timestamp=stamps[0],
        latest_timestamp=stamps[1],
        problems=tuple(problems),
        parent_types=dict(parent_types or {}),
    )


def _values(name, column, values):
    return _cls(name, [_rec({column: _h(v)}) for v in values])


def _inventory(problems=()):
    """A store of the shape SI writes: the parameters, both potentials, two trajectories, twelve
    full instantons (eleven validated) and one compaction function with no slow-roll side."""
    classes = {}

    def add(c):
        classes[c.name] = c

    add(_cls("version", [_rec({"label": "2026.6.1"})]))
    add(_cls("store_tag", []))
    add(_values("tolerance", "log10_tol", [-9.0, -7.0]))
    # 21 e-fold values: more than 20, so truncated to the first and last ten
    add(_values("efold_value", "N", [0.125 * k for k in range(21)]))
    add(_values("delta_Nstar", "value", [0.75, 0.25, 1.25]))
    # 20 N_init values: shown whole
    add(_values("N_init", "value", [30.0 + k for k in range(20)]))
    add(_values("N_final", "value", [4.0]))
    add(_values("inflaton_mass", "value_PlanckMass", [2e-06]))
    add(_values("phi_value", "value_PlanckMass", [14.5]))
    add(_values("pi_value", "value_PlanckMass", [-0.25]))
    add(_cls("MasslessDecoupledDiffusion", [_rec({})]))
    add(_cls("CosmologicalParams", [_rec({"name": "Planck2018 test"})]))

    # each one-leaf class's records by their stored leaf
    rec = {
        n: {next(iter(r.key.values())): r for r in c.records}
        for n, c in classes.items()
        if len(c.records) > 0 and len(c.records[0].key) == 1
    }

    mass = rec["inflaton_mass"][_h(2e-06)]
    quadratic = _rec({"m": _ref(mass)})
    add(_cls("QuadraticPotential", [quadratic], parents={"m": "inflaton_mass"}))
    coupling = _rec({"value": _h(3e-14)})
    add(_cls("quartic_coupling", [coupling]))
    quartic = _rec({"lambda_": _ref(coupling)})
    add(_cls("QuarticPotential", [quartic], parents={"lambda_": "quartic_coupling"}))

    atol = rec["tolerance"][_h(-9.0)]
    rtol = rec["tolerance"][_h(-7.0)]
    potentials = {1: "QuadraticPotential", 2: "QuarticPotential"}
    trajectories = []
    for potential_type, potential in ((1, quadratic), (2, quartic)):
        trajectories.append(
            _rec(
                {
                    "potential_type": potential_type,
                    "phi0": _ref(rec["phi_value"][_h(14.5)]),
                    "pi0": _ref(rec["pi_value"][_h(-0.25)]),
                    "potential": _ref(potential),
                    "atol": _ref(atol),
                    "rtol": _ref(rtol),
                },
                validated=True,
                value_count=7,
            )
        )
    add(
        _cls(
            "InflatonTrajectory",
            trajectories,
            parents={
                "phi0": "phi_value",
                "pi0": "pi_value",
                "potential": None,
                "atol": "tolerance",
                "rtol": "tolerance",
            },
            parent_types={"potential": ("potential_type", potentials)},
            stamps=(_T0, _T0),
        )
    )

    diffusion = classes["MasslessDecoupledDiffusion"].records[0]
    instantons = []
    for k in range(12):
        instantons.append(
            _rec(
                {
                    "diffusion_type": 1,
                    "trajectory": _ref(trajectories[0]),
                    "N_init": _ref(rec["N_init"][_h(30.0 + k)]),
                    "N_final": _ref(rec["N_final"][_h(4.0)]),
                    "delta_Nstar": _ref(rec["delta_Nstar"][_h(0.25)]),
                    "atol": _ref(atol),
                    "rtol": _ref(rtol),
                    "diffusion_model": _ref(diffusion),
                },
                validated=k < 11,
                value_count=3,
            )
        )
    add(
        _cls(
            "FullInstanton",
            instantons,
            replicated=False,
            parents={
                "trajectory": "InflatonTrajectory",
                "N_init": "N_init",
                "N_final": "N_final",
                "delta_Nstar": "delta_Nstar",
                "atol": "tolerance",
                "rtol": "tolerance",
                "diffusion_model": None,
            },
            parent_types={
                "diffusion_model": ("diffusion_type", {1: "MasslessDecoupledDiffusion"})
            },
            problems=problems,
            stamps=(_T0, _T1),
        )
    )
    compaction = _rec(
        {
            "trajectory": _ref(trajectories[1]),
            "full_instanton": _ref(instantons[0]),
            "slow_roll_instanton": None,
            "delta_Nstar": _ref(rec["delta_Nstar"][_h(0.75)]),
            "cosmo": _ref(classes["CosmologicalParams"].records[0]),
            "atol": _ref(atol),
            "rtol": _ref(rtol),
        },
        validated=False,
        value_count=4,
    )
    add(
        _cls(
            "CompactionFunction",
            [compaction],
            replicated=False,
            parents={
                "trajectory": "InflatonTrajectory",
                "full_instanton": "FullInstanton",
                "slow_roll_instanton": "SlowRollInstanton",
                "delta_Nstar": "delta_Nstar",
                "cosmo": "CosmologicalParams",
                "atol": "tolerance",
                "rtol": "tolerance",
            },
            stamps=(_T1, _T1),
        )
    )
    add(_cls("SlowRollInstanton", [], replicated=False))
    return StoreInventory(
        primary=Path("/stores/x.sqlite"), shards=(0, 1), classes=classes
    )


def _section(report, title):
    """The lines of the section whose title line starts with ``   -- <title> (``."""
    lines = report.split("\n")
    (start,) = [i for i, ln in enumerate(lines) if ln.startswith(f"   -- {title} (")]
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("   -- ")),
        len(lines),
    )
    return [ln for ln in lines[start:end] if ln.strip() != ""]


def test_the_title_shards_and_problems():
    report = format_inventory_report(_inventory(), "/stores/x.sqlite")
    lines = report.split("\n")
    assert lines[0] == "@@ DATASTORE INVENTORY: /stores/x.sqlite"
    assert lines[1].startswith("   read-only; 2 shards (#0, #1); ")
    assert lines[2] == "   problems: none"
    assert "0x" not in report  # no float is printed in hex


def test_each_parameter_and_quantity_by_its_values_and_unit():
    report = format_inventory_report(_inventory(), "x")
    assert _section(report, "Delta N★ values")[1:] == [
        "      3 values: [ 0.25, 0.75, 1.25 ]"
    ]
    assert _section(report, "N_final values")[1:] == ["      1 value: [ 4 ]"]
    assert _section(report, "phi_0 values")[1:] == [
        "      1 value: [ 14.5 PlanckMass ]"
    ]
    assert _section(report, "pi_0 values")[1:] == [
        "      1 value: [ -0.25 PlanckMass ]"
    ]
    assert _section(report, "Inflaton mass values")[1:] == [
        "      1 value: [ 2e-06 PlanckMass ]"
    ]
    assert _section(report, "Quartic coupling values")[1:] == [
        "      1 value: [ 3e-14 ]"
    ]
    assert _section(report, "Tolerances")[1:] == ["      2 values: [ 1e-09, 1e-07 ]"]
    assert (
        _section(report, "phi_0 values")[0]
        == "   -- phi_0 values (phi_value, replicated)"
    )


def test_an_empty_class_says_no_values_committed():
    report = format_inventory_report(_inventory(), "x")
    assert _section(report, "Store tags")[1:] == ["      no values committed"]
    assert _section(report, "Slow-roll instantons")[1:] == [
        "      0 records",
        "      @@ validated: 0 record(s)",
        "      @@ unvalidated: 0 record(s)",
    ]


def test_twenty_values_show_whole_and_twenty_one_are_truncated_unless_verbose():
    report = format_inventory_report(_inventory(), "x")
    n_init = ", ".join(str(30 + k) for k in range(20))
    assert _section(report, "N_init values")[1:] == [f"      20 values: [ {n_init} ]"]
    first = ", ".join(f"{0.125 * k:.6g}" for k in range(10))
    last = ", ".join(f"{0.125 * k:.6g}" for k in range(11, 21))
    assert _section(report, "E-fold sample values")[1:] == [
        f"      21 values: [ {first}, ... 1 value not shown (--show-all shows every one) ..., "
        f"{last} ]"
    ]
    verbose = format_inventory_report(_inventory(), "x", verbose=True)
    every = ", ".join(f"{0.125 * k:.6g}" for k in range(21))
    assert _section(verbose, "E-fold sample values")[1:] == [
        f"      21 values: [ {every} ]"
    ]


def test_a_compute_target_by_counts_timestamps_and_physical_labels():
    lines = _section(format_inventory_report(_inventory(), "x"), "Full MSR instantons")
    assert lines[0] == "   -- Full MSR instantons (FullInstanton, sharded)"
    assert lines[1] == (
        "      12 records; 36 value rows; committed 2026-10-21 10:19:00 – 2026-10-21 10:20:30"
    )
    assert lines[2] == (
        "      common to every record: delta_Nstar=0.25, N_final=4, "
        "trajectory=InflatonTrajectory(phi0=14.5 PlanckMass, "
        "potential=QuadraticPotential(m=2e-06 PlanckMass)), "
        "diffusion_model=MasslessDecoupledDiffusion, atol=1e-09, rtol=1e-07"
    )
    assert lines[3] == "      @@ validated: 11 record(s)"
    # more than ten records: the first and last five
    assert lines[4:15] == [
        "         :: N_init=30 | 3 value rows",
        "         :: N_init=31 | 3 value rows",
        "         :: N_init=32 | 3 value rows",
        "         :: N_init=33 | 3 value rows",
        "         :: N_init=34 | 3 value rows",
        "         :: ... 1 record not shown (--show-all shows every one) ...",
        "         :: N_init=36 | 3 value rows",
        "         :: N_init=37 | 3 value rows",
        "         :: N_init=38 | 3 value rows",
        "         :: N_init=39 | 3 value rows",
        "         :: N_init=40 | 3 value rows",
    ]
    assert lines[15:] == [
        "      @@ unvalidated: 1 record(s)",
        "         :: N_init=41 | 3 value rows",
    ]
    verbose = _section(
        format_inventory_report(_inventory(), "x", verbose=True), "Full MSR instantons"
    )
    assert "         :: N_init=35 | 3 value rows" in verbose
    assert not any("not shown" in ln for ln in verbose)


def test_the_trajectories_name_both_potentials_by_class():
    lines = _section(
        format_inventory_report(_inventory(), "x"), "Inflaton trajectories"
    )
    assert lines[1:] == [
        "      2 records; 14 value rows; committed 2026-10-21 10:19:00 – 2026-10-21 10:19:00",
        "      common to every record: phi0=14.5 PlanckMass, pi0=-0.25 PlanckMass, atol=1e-09, "
        "rtol=1e-07",
        "      @@ validated: 2 record(s)",
        "         :: potential=QuadraticPotential(m=2e-06 PlanckMass) | 7 value rows",
        "         :: potential=QuarticPotential(lambda_=3e-14) | 7 value rows",
        "      @@ unvalidated: 0 record(s)",
    ]


def test_a_nullable_parent_with_none_prints_none():
    lines = _section(format_inventory_report(_inventory(), "x"), "Compaction functions")
    assert (
        lines[1]
        == "      1 record; 4 value rows; committed 2026-10-21 10:20:30 – 2026-10-21 10:20:30"
    )
    assert lines[2:] == [
        "      @@ validated: 0 record(s)",
        "      @@ unvalidated: 1 record(s)",
        "         :: delta_Nstar=0.75, trajectory=InflatonTrajectory(phi0=14.5 PlanckMass, "
        "potential=QuarticPotential(lambda_=3e-14)), full_instanton=FullInstanton(N_init=30), "
        "slow_roll_instanton=none, cosmo=Planck2018 test, atol=1e-09, rtol=1e-07 | 4 value rows",
    ]


def test_a_long_problem_is_printed_whole_on_one_line():
    for verbose in (False, True):
        report = format_inventory_report(
            _inventory(problems=(_LONG_PROBLEM,)), "x", verbose
        )
        lines = report.split("\n")
        assert lines[2] == "   problems: 1, each listed in full under its class"
        assert f"         !! {_LONG_PROBLEM}" in lines
        section = _section(report, "Full MSR instantons")
        assert section[-2:] == ["      1 problem:", f"         !! {_LONG_PROBLEM}"]
    assert len(_LONG_PROBLEM) > 600


def test_every_class_of_the_inventory_is_printed():
    inventory = _inventory()
    classes = dict(inventory.classes)
    classes["Mystery"] = _cls("Mystery", [_rec({"label": "kept"})])
    report = format_inventory_report(
        StoreInventory(
            primary=inventory.primary, shards=inventory.shards, classes=classes
        ),
        "x",
    )
    for name in classes:
        assert f" ({name}, " in report, name
    assert _section(report, "Other classes")[1:] == [
        "      1 record",
        "         :: label=kept",
    ]


def _with_gradient_instantons():
    """``_inventory()`` and three gradient-coupled instantons, as prompt 10b's store holds them:
    one with full values (5 profile rows, 3 GradientCoupledInstantonValue rows), one stored
    without them (5, 0) and one failed (0, 0). The profile is the spec's ``values``; the value
    table is its one ``extra_values`` table, counted into ``extra_value_counts``."""
    inventory = _inventory()
    classes = dict(inventory.classes)
    trajectory = classes["InflatonTrajectory"].records[0]
    delta_nstar = {r.key["value"]: r for r in classes["delta_Nstar"].records}

    def gradient(dn, profile_rows, value_rows):
        return Record(
            key={
                "trajectory": _ref(trajectory),
                "delta_Nstar": _ref(delta_nstar[_h(dn)]),
            },
            tags=(),
            validated=True,
            value_count=profile_rows,
            extra_value_counts={"GradientCoupledInstantonValue": value_rows},
        )

    classes["GradientCoupledInstanton"] = _cls(
        "GradientCoupledInstanton",
        [gradient(0.25, 5, 3), gradient(0.75, 5, 0), gradient(1.25, 0, 0)],
        replicated=False,
        parents={"trajectory": "InflatonTrajectory", "delta_Nstar": "delta_Nstar"},
        stamps=(_T0, _T1),
    )
    return StoreInventory(
        primary=inventory.primary, shards=inventory.shards, classes=classes
    )


def test_a_further_value_table_is_counted_by_its_name():
    # prompt 10b: each further value table's rows, by the table's name, a 0 printed as 0, on
    # every record line and in the class's summary, after the value rows the spec's values counts
    for verbose in (False, True):
        lines = _section(
            format_inventory_report(_with_gradient_instantons(), "x", verbose),
            "Gradient-coupled (onion model) instantons",
        )
        assert lines == [
            "   -- Gradient-coupled (onion model) instantons (GradientCoupledInstanton, sharded)",
            "      3 records; 10 value rows; 3 GradientCoupledInstantonValue rows; "
            "committed 2026-10-21 10:19:00 – 2026-10-21 10:20:30",
            "      common to every record: trajectory=InflatonTrajectory(phi0=14.5 PlanckMass, "
            "potential=QuadraticPotential(m=2e-06 PlanckMass))",
            "      @@ validated: 3 record(s)",
            "         :: delta_Nstar=0.25 | 5 value rows; 3 GradientCoupledInstantonValue rows",
            "         :: delta_Nstar=0.75 | 5 value rows; 0 GradientCoupledInstantonValue rows",
            "         :: delta_Nstar=1.25 | 0 value rows; 0 GradientCoupledInstantonValue rows",
            "      @@ unvalidated: 0 record(s)",
        ]


def test_a_class_with_no_further_value_table_prints_as_before():
    # beside a class that declares one, a class that declares none prints as prompt 10's report
    # did, line for line, and names no further table
    report = format_inventory_report(_with_gradient_instantons(), "x")
    assert _section(report, "Inflaton trajectories")[1:] == [
        "      2 records; 14 value rows; committed 2026-10-21 10:19:00 – 2026-10-21 10:19:00",
        "      common to every record: phi0=14.5 PlanckMass, pi0=-0.25 PlanckMass, atol=1e-09, "
        "rtol=1e-07",
        "      @@ validated: 2 record(s)",
        "         :: potential=QuadraticPotential(m=2e-06 PlanckMass) | 7 value rows",
        "         :: potential=QuarticPotential(lambda_=3e-14) | 7 value rows",
        "      @@ unvalidated: 0 record(s)",
    ]
    assert _section(report, "Compaction functions")[1:] == [
        "      1 record; 4 value rows; committed 2026-10-21 10:20:30 – 2026-10-21 10:20:30",
        "      @@ validated: 0 record(s)",
        "      @@ unvalidated: 1 record(s)",
        "         :: delta_Nstar=0.75, trajectory=InflatonTrajectory(phi0=14.5 PlanckMass, "
        "potential=QuarticPotential(lambda_=3e-14)), full_instanton=FullInstanton(N_init=30), "
        "slow_roll_instanton=none, cosmo=Planck2018 test, atol=1e-09, rtol=1e-07 | 4 value rows",
    ]
    full = _section(report, "Full MSR instantons")
    assert full[1] == (
        "      12 records; 36 value rows; committed 2026-10-21 10:19:00 – 2026-10-21 10:20:30"
    )
    assert full[4] == "         :: N_init=30 | 3 value rows"
    # the table is named on the gradient section's four count lines and nowhere else
    gradient = _section(report, "Gradient-coupled (onion model) instantons")
    named = [ln for ln in report.split("\n") if "GradientCoupledInstantonValue" in ln]
    assert len(named) == 4
    assert all(ln in gradient for ln in named)


def test_the_report_reads_nothing():
    tree = ast.parse((_ROOT / "tools" / "inventory_report.py").read_text())
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    modules = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    modules |= {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names
    }
    for forbidden in (
        "open",
        "sqlite3",
        "create_engine",
        "read_inventory",
        "open_read_only",
        "connect",
    ):
        assert forbidden not in names, forbidden
    assert modules == {
        "datetime",
        "typing",
        "sqlalchemy",
        "datastorekit.store_inventory",
        "datastorekit.SQL.schema",
        "config.datastore",
    }
