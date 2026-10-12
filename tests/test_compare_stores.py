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
The comparison of two stores by value, `tools/compare_stores.py` (dk-and-rpk-migration prompt
01, item T2; README section 4.2).

**Imitation stores.** Every comparison test builds its stores with `sqlite3` alone, in a
`tempfile` directory. A store is a primary with the layer's five tables (`shards`,
`shard_key_config`, `shard_keys`, `replicated_tables`, `sharded_tables`) and two shards. The
shards hold StochasticInstanton's own table names, so that the tool's real maps apply and nothing
is patched:
- replicated parameter tables (`tolerance`, `efold_value`, `delta_Nstar`, `inflaton_mass`,
  `quartic_coupling`), a `version` table, and `MasslessDecoupledDiffusion`;
- the two potential tables (`QuadraticPotential`, `QuarticPotential`), which
  `InflatonTrajectory.potential_serial` names through `potential_type`: one polymorphic pair;
- a replicated `InflatonTrajectory`, with a `diagnostics_json`, and its value table
  `InflatonTrajectoryValue` (composite primary key, no `serial`, a `fields_json`);
- a sharded parent `FullInstanton` with foreign keys into the parameter tables, a `version`
  column, a `label`, the `diffusion_serial`/`diffusion_type` pair, and a `diagnostics_json`
  holding timing keys (one nested) beside science keys; and its value table `FullInstantonValue`
  (composite primary key, no `serial`, a `fields_json`);
- `redshift`, on the shards but in neither of the primary's lists, as in a real store;
- the primary also lists `IntegrationSolver`, which no shard holds.

**The declared maps** (test 12) are checked against the factories' `register()` (an instance
method, which needs no store and no Ray), the two type registries and the source of
`ComputeTargets/`.

No Ray, no solve, no store outside a `tempfile` directory. A few seconds, most of it importing
the factories.
"""

import ast
import contextlib
import copy
import hashlib
import io
import json
import math
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest import mock
from urllib.parse import unquote

import pytest

import tools.compare_stores as cs

ROOT = Path(__file__).resolve().parents[1]

IMITATION_SCHEMA = """
create table version (serial integer primary key, label varchar(256));
create table tolerance (serial integer primary key, timestamp datetime, log10_tol float);
create table efold_value (serial integer primary key, timestamp datetime, N float);
create table delta_Nstar (serial integer primary key, timestamp datetime, value float);
create table inflaton_mass (
    serial integer primary key, timestamp datetime, value_PlanckMass float
);
create table quartic_coupling (serial integer primary key, timestamp datetime, value float);
create table QuadraticPotential (
    serial integer primary key,
    timestamp datetime,
    mass_id integer not null references inflaton_mass (serial),
    type_id integer not null
);
create table QuarticPotential (
    serial integer primary key,
    timestamp datetime,
    coupling_id integer not null references quartic_coupling (serial),
    type_id integer not null
);
create table MasslessDecoupledDiffusion (serial integer primary key, timestamp datetime);
create table InflatonTrajectory (
    serial integer primary key,
    version integer references version (serial),
    timestamp datetime,
    potential_serial integer not null,
    potential_type integer not null,
    atol_serial integer not null references tolerance (serial),
    rtol_serial integer not null references tolerance (serial),
    N_end float,
    diagnostics_json text,
    validated boolean not null
);
create index ix_InflatonTrajectory_potential_serial on InflatonTrajectory (potential_serial);
create table InflatonTrajectoryValue (
    trajectory_serial integer not null references InflatonTrajectory (serial),
    N_serial integer not null references efold_value (serial),
    fields_json text not null,
    primary key (trajectory_serial, N_serial)
);
create table FullInstanton (
    serial integer primary key,
    version integer references version (serial),
    timestamp datetime,
    trajectory_serial integer not null references InflatonTrajectory (serial),
    delta_Nstar_serial integer not null references delta_Nstar (serial),
    atol_serial integer not null references tolerance (serial),
    diffusion_serial integer not null,
    diffusion_type integer not null,
    msr_action float,
    label text,
    diagnostics_json text,
    validated boolean not null
);
create index ix_FullInstanton_delta_Nstar_serial on FullInstanton (delta_Nstar_serial);
create table FullInstantonValue (
    instanton_serial integer not null references FullInstanton (serial),
    N_serial integer not null references efold_value (serial),
    fields_json text not null,
    primary key (instanton_serial, N_serial)
);
create table redshift (serial integer primary key, timestamp datetime, z float);
"""

IMITATION_REPLICATED = [
    "version",
    "tolerance",
    "efold_value",
    "delta_Nstar",
    "inflaton_mass",
    "quartic_coupling",
    "QuadraticPotential",
    "QuarticPotential",
    "MasslessDecoupledDiffusion",
    "IntegrationSolver",
    "InflatonTrajectory",
    "InflatonTrajectoryValue",
]
IMITATION_SHARDED = {
    "FullInstanton": "delta_Nstar",
    "FullInstantonValue": "delta_Nstar",
}

N_GRID = [0.0, 0.5, 1.0, 1.5]

CONTENT = {
    "version": "2026.6.1",
    "tolerances": {"atol": -8.0, "rtol": -10.0},
    "dNstar": [0.1, 0.4],
    "mass": 1e-5,
    "coupling": 1e-13,
    "trajectory": {
        "potential": "QuadraticPotential",
        "N_end": 70.5,
        "diagnostics": {"compute_time": 1.25, "n_steps": 400, "final_phi": 0.7071},
        "values": [
            {"phi_PlanckMass": [15.0 - 0.1 * i], "pi_PlanckMass": [-0.01 * i]}
            for i in range(len(N_GRID))
        ],
    },
    "instantons": [
        {
            "dNstar": 0.1,
            "msr_action": 12.375,
            "label": "FullInstanton(N_init=20, N_final=5, dNstar=0.1)",
            "diagnostics": {
                "compute_time": 3.5,
                "converged": True,
                "final_residual": 1.5e-9,
                "outer_iterations": 4,
                "picard_iterations_per_outer": [3, 2, 2],
                "mean_time_per_picard_iteration": 0.01,
                "nested": {"compute_time": 0.5, "C_min": 0.25},
            },
            "values": [
                {
                    "phi1_PlanckMass": [15.0 - 0.2 * i],
                    "phi2_PlanckMass": [-0.02 * i],
                    "P1_invPlanckMass": [0.3 + 0.1 * i],
                    "P2_invPlanckMass": [0.05 * i],
                }
                for i in range(len(N_GRID))
            ],
            "shard": 0,
        },
        {
            "dNstar": 0.4,
            "msr_action": 3.0625,
            "label": "FullInstanton(N_init=20, N_final=5, dNstar=0.4)",
            "diagnostics": {
                "compute_time": 4.25,
                "converged": True,
                "final_residual": 2.5e-10,
                "outer_iterations": 5,
                "picard_iterations_per_outer": [4, 3, 2, 2],
                "mean_time_per_picard_iteration": 0.02,
                "nested": {"compute_time": 0.75, "C_min": 0.125},
            },
            "values": [
                {
                    "phi1_PlanckMass": [15.0 - 0.3 * i],
                    "phi2_PlanckMass": [-0.03 * i],
                    "P1_invPlanckMass": [0.7 + 0.1 * i],
                    "P2_invPlanckMass": [0.06 * i],
                }
                for i in range(len(N_GRID))
            ],
            "shard": 1,
        },
    ],
}


def _write_primary(path: Path, shard_records, replicated, sharded):
    conn = sqlite3.connect(path)
    with conn:
        conn.executescript(
            """
            create table shards (serial integer primary key not null,
                                 filename varchar(256) not null);
            create table shard_key_config (key_type varchar(256) primary key not null);
            create table shard_keys (key_serial integer primary key not null,
                                     shard_id integer not null references shards (serial));
            create table replicated_tables (serial integer primary key not null,
                                            "table" varchar(256) not null);
            create table sharded_tables (serial integer primary key not null,
                                         "table" varchar(256) not null,
                                         key_attr varchar(256) not null);
            """
        )
        conn.executemany(
            "insert into shards (serial, filename) values (?, ?)",
            list(enumerate(shard_records)),
        )
        conn.execute("insert into shard_key_config (key_type) values ('delta_Nstar')")
        conn.executemany(
            'insert into replicated_tables (serial, "table") values (?, ?)',
            list(enumerate(replicated)),
        )
        conn.executemany(
            'insert into sharded_tables (serial, "table", key_attr) values (?, ?, ?)',
            [(n, t, k) for n, (t, k) in enumerate(sharded.items())],
        )
    conn.close()


def build_store(
    directory: Path,
    stem: str,
    content=None,
    *,
    shards: int = 2,
    serial_offset: int = 0,
    shard_of=None,
    records: str = "bare",
    timestamp: str = "2026-10-12 12:00:00.000000",
    absolute_records=None,
    swap_potential_serials: bool = False,
) -> Path:
    """
    An imitation store at directory/stem.sqlite with `shards` shards. Replicated rows carry the
    same serials on every shard; `serial_offset` shifts every serial, `shard_of` (a list, one
    entry per instanton) moves the instantons and their values to other shards, and
    `swap_potential_serials` exchanges the two potential tables' serials. `records` is "bare"
    (the package's form) or "absolute" (StochasticInstanton's), and `absolute_records`, if given,
    are the absolute paths recorded instead (which need not exist).
    """
    content = copy.deepcopy(CONTENT if content is None else content)
    directory.mkdir(parents=True, exist_ok=True)
    primary = directory / f"{stem}.sqlite"
    shard_paths = [directory / f"{stem}-shard{i:04d}.sqlite" for i in range(shards)]

    if absolute_records is not None:
        recorded = [str(p) for p in absolute_records]
    elif records == "absolute":
        recorded = [str(p.resolve()) for p in shard_paths]
    else:
        recorded = [p.name for p in shard_paths]
    _write_primary(primary, recorded, IMITATION_REPLICATED, IMITATION_SHARDED)

    off = serial_offset
    version = off + 1
    atol, rtol = off + 10, off + 11
    efold = {N: off + 20 + i for i, N in enumerate(N_GRID)}
    dns = {v: off + 40 + i for i, v in enumerate(content["dNstar"])}
    mass, coupling = off + 50, off + 51
    quadratic, quartic = (
        (off + 61, off + 60) if swap_potential_serials else (off + 60, off + 61)
    )
    diffusion = off + 70
    trajectory = off + 80
    trajectory_data = content["trajectory"]
    potential_serial = {"QuadraticPotential": quadratic, "QuarticPotential": quartic}[
        trajectory_data["potential"]
    ]
    potential_type = trajectory_data.get(
        "potential_type",
        {"QuadraticPotential": 1, "QuarticPotential": 2}[trajectory_data["potential"]],
    )

    conns = []
    for path in shard_paths:
        conn = sqlite3.connect(path)
        conn.executescript(IMITATION_SCHEMA)
        conn.execute("insert into version values (?, ?)", (version, content["version"]))
        conn.execute(
            "insert into tolerance values (?, ?, ?)",
            (atol, timestamp, content["tolerances"]["atol"]),
        )
        conn.execute(
            "insert into tolerance values (?, ?, ?)",
            (rtol, timestamp, content["tolerances"]["rtol"]),
        )
        for N, serial in efold.items():
            conn.execute(
                "insert into efold_value values (?, ?, ?)", (serial, timestamp, N)
            )
        for value, serial in dns.items():
            conn.execute(
                "insert into delta_Nstar values (?, ?, ?)", (serial, timestamp, value)
            )
        conn.execute(
            "insert into inflaton_mass values (?, ?, ?)",
            (mass, timestamp, content["mass"]),
        )
        conn.execute(
            "insert into quartic_coupling values (?, ?, ?)",
            (coupling, timestamp, content["coupling"]),
        )
        conn.execute(
            "insert into QuadraticPotential values (?, ?, ?, ?)",
            (quadratic, timestamp, mass, 1),
        )
        conn.execute(
            "insert into QuarticPotential values (?, ?, ?, ?)",
            (quartic, timestamp, coupling, 2),
        )
        conn.execute(
            "insert into MasslessDecoupledDiffusion values (?, ?)",
            (diffusion, timestamp),
        )
        conn.execute(
            "insert into InflatonTrajectory values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                trajectory,
                version,
                timestamp,
                potential_serial,
                potential_type,
                atol,
                rtol,
                trajectory_data["N_end"],
                json.dumps(trajectory_data["diagnostics"]),
                1,
            ),
        )
        for N, fields in zip(N_GRID, trajectory_data["values"]):
            conn.execute(
                "insert into InflatonTrajectoryValue values (?, ?, ?)",
                (trajectory, efold[N], json.dumps(fields)),
            )
        conns.append(conn)

    conns[0].execute(
        "insert into redshift values (?, ?, ?)", (off + 90, timestamp, 1000.0)
    )

    for i, instanton in enumerate(content["instantons"]):
        shard = instanton["shard"] if shard_of is None else shard_of[i]
        conn = conns[shard]
        serial = off + 1000 + 10 * i
        diagnostics = instanton["diagnostics"]
        conn.execute(
            "insert into FullInstanton values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                serial,
                version,
                instanton.get("timestamp", timestamp),
                trajectory,
                dns[instanton["dNstar"]],
                atol,
                diffusion,
                instanton.get("diffusion_type", 1),
                instanton["msr_action"],
                instanton["label"],
                diagnostics
                if isinstance(diagnostics, str)
                else json.dumps(diagnostics),
                1,
            ),
        )
        for N, fields in zip(N_GRID, instanton["values"]):
            conn.execute(
                "insert into FullInstantonValue values (?, ?, ?)",
                (serial, efold[N], json.dumps(fields)),
            )

    for conn in conns:
        conn.commit()
        conn.close()
    return primary


def _tree_state(directory: Path) -> dict:
    """Every file under `directory`: its sha256, size and modification time."""
    state = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            stat = path.stat()
            state[str(path)] = (
                hashlib.sha256(path.read_bytes()).hexdigest(),
                stat.st_size,
                stat.st_mtime_ns,
            )
    return state


@pytest.fixture
def tmp():
    with tempfile.TemporaryDirectory(prefix="si-compare-stores-test-") as directory:
        yield Path(directory)


def run_tool(tmp: Path, *argv):
    """(exit code, stdout, the --json result or None) of the tool's main()."""
    out = io.StringIO()
    json_path = tmp / "result.json"
    if json_path.exists():
        json_path.unlink()
    args = list(map(str, argv))
    if len(args) == 2 and not args[0].startswith("--"):
        args += ["--json", str(json_path)]
    with contextlib.redirect_stdout(out):
        code = cs.main(args)
    result = json.loads(json_path.read_text()) if json_path.exists() else None
    return code, out.getvalue(), result


def two(tmp: Path, content_b=None, **kwargs_b):
    a = build_store(tmp / "a", "store")
    b = build_store(tmp / "b", "store", content_b, **kwargs_b)
    return a, b


def _problems(result, kind):
    return [p for p in result["problems"] if p["kind"] == kind]


# ---------------------------------------------------------------------------
# the comparison


def test_01_equal_stores(tmp):
    """(1) Two equal stores: nothing differs, no problem, exit 0."""
    a, b = two(tmp)
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_EQUAL, text
    assert result["equal"]
    assert result["problems"] == []
    for table, entry in result["tables"].items():
        assert (entry["a_only"], entry["b_only"]) == (0, 0), table
    assert result["tables"]["FullInstantonValue"]["matched"] == 2 * len(N_GRID)
    assert result["tables"]["InflatonTrajectoryValue"]["matched"] == len(N_GRID)
    assert result["tables"]["efold_value"]["matched"] == len(N_GRID)
    assert result["bookkeeping_differences"] == {}
    assert "RESULT: equal" in text


def test_02_one_float_changed_in_its_last_bit(tmp):
    """(2) One float column moved by one ulp (math.nextafter): named with both values, exit 1."""
    content = copy.deepcopy(CONTENT)
    old = content["instantons"][0]["msr_action"]
    new = math.nextafter(old, math.inf)
    content["instantons"][0]["msr_action"] = new
    a, b = two(tmp, content)
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_DIFFERENT, text
    assert not result["equal"]
    fi = result["tables"]["FullInstanton"]
    assert (fi["a_only"], fi["b_only"]) == (1, 1)
    (pair,) = fi["near_misses"]
    (diff,) = pair["differing"]
    assert diff["column"] == "msr_action"
    assert (diff["a"], diff["b"]) == (old, new)
    assert (diff["a_hex"], diff["b_hex"]) == (old.hex(), new.hex())
    assert diff["relative_difference"] > 0.0
    assert new.hex() in text
    # its value rows pair with their counterparts, differing only through their parent
    value = result["tables"]["FullInstantonValue"]
    assert (value["rows_a_only"], value["rows_b_only"]) == ([], [])
    assert len(value["near_misses"]) == len(N_GRID)
    assert all(
        p["through_references"] == ["instanton_serial"] for p in value["near_misses"]
    )


def test_03_a_row_in_one_store_only(tmp):
    """(3) An instanton in B only is named by its physical labels, its references resolved to
    their rows' columns, not to serials or digests."""
    content = copy.deepcopy(CONTENT)
    extra = copy.deepcopy(content["instantons"][1])
    extra["dNstar"] = 0.1
    extra["shard"] = 0
    extra["label"] = "FullInstanton(N_init=20, N_final=5, dNstar=0.1) again"
    extra["msr_action"] = 99.5
    content["instantons"].append(extra)
    a, b = two(tmp, content)
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_DIFFERENT, text
    fi = result["tables"]["FullInstanton"]
    assert (fi["a_only"], fi["b_only"]) == (0, 1)
    (row,) = fi["rows_b_only"]
    assert row["msr_action"] == 99.5
    assert row["delta_Nstar_serial"]["row"] == {"value": 0.1}
    assert row["version"]["row"] == {"label": "2026.6.1"}
    assert row["diffusion_serial"] == {"table": "MasslessDecoupledDiffusion", "row": {}}
    trajectory = row["trajectory_serial"]["row"]
    assert trajectory["N_end"] == 70.5
    assert trajectory["potential_serial"]["table"] == "QuadraticPotential"
    assert trajectory["potential_serial"]["row"]["mass_id"]["row"] == {
        "value_PlanckMass": 1e-5
    }
    assert (
        "diagnostics_json" not in trajectory
    )  # a referenced row's JSON is not repeated
    assert row["diagnostics_json"]["final_residual"] == 2.5e-10
    assert "compute_time" not in row["diagnostics_json"]  # a timing key is not a label
    assert "serial" not in row and "label" not in row and "timestamp" not in row
    assert "FullInstanton{atol_serial=tolerance{log10_tol=-8.0}" in text
    # its four value rows are in B only too
    assert result["tables"]["FullInstantonValue"]["b_only"] == len(N_GRID)


def test_04_serials_and_shard_assignment_do_not_matter(tmp):
    """(4) Equal content under other serials, with the instantons on other shards: equal."""
    a, b = two(tmp, serial_offset=70000, shard_of=[1, 0])
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_EQUAL, text
    assert result["equal"]
    assert result["problems"] == []


def test_05_bookkeeping_columns_that_differ(tmp):
    """(5) timestamp (everywhere) and FullInstanton.label differ: reported apart, exit 0."""
    content = copy.deepcopy(CONTENT)
    for instanton in content["instantons"]:
        instanton["label"] = None  # as the unified pipeline writes it
    a, b = two(tmp, content, timestamp="2026-10-13 09:30:00.000000")
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_EQUAL, text
    assert result["equal"]
    bookkeeping = result["bookkeeping_differences"]
    assert bookkeeping["FullInstanton"] == {"label": 2, "timestamp": 2}
    assert bookkeeping["efold_value"] == {"timestamp": len(N_GRID)}
    assert "FullInstanton.timestamp: 2 matched row(s)" in text
    assert "FullInstanton.label: 2 matched row(s)" in text


def test_06_timing_keys_inside_diagnostics_json(tmp):
    """(6) compute_time (top level and nested) and mean_time_per_picard_iteration differ inside
    diagnostics_json: reported apart, exit 0. A science key inside it moved by one ulp: named,
    exit 1."""
    content = copy.deepcopy(CONTENT)
    diagnostics = content["instantons"][0]["diagnostics"]
    diagnostics["compute_time"] = 9.75
    diagnostics["nested"]["compute_time"] = 0.0625
    diagnostics["mean_time_per_picard_iteration"] = 0.5
    content["trajectory"]["diagnostics"]["compute_time"] = 2.0
    a, b = two(tmp, content)
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_EQUAL, text
    assert result["equal"]
    assert result["bookkeeping_differences"]["FullInstanton"] == {
        'diagnostics_json["compute_time"]': 1,
        'diagnostics_json["mean_time_per_picard_iteration"]': 1,
        'diagnostics_json["nested"]["compute_time"]': 1,
    }
    assert result["bookkeeping_differences"]["InflatonTrajectory"] == {
        'diagnostics_json["compute_time"]': 1
    }

    science = copy.deepcopy(content)
    old = science["instantons"][0]["diagnostics"]["final_residual"]
    new = math.nextafter(old, 0.0)
    science["instantons"][0]["diagnostics"]["final_residual"] = new
    c = build_store(tmp / "c", "store", science)
    code, text, result = run_tool(tmp, a, c)
    assert code == cs.EXIT_DIFFERENT, text
    (pair,) = result["tables"]["FullInstanton"]["near_misses"]
    (diff,) = pair["differing"]
    assert diff["column"] == 'diagnostics_json["final_residual"]'
    assert (diff["a"], diff["b"]) == (old, new)
    assert (diff["a_hex"], diff["b_hex"]) == (old.hex(), new.hex())
    assert new.hex() in text


def test_07_a_float_inside_fields_json_is_a_near_miss(tmp):
    """(7) One float inside one value row's fields_json moved by one ulp: that row alone is
    paired as a near miss, its path and both values named; its parent matches."""
    content = copy.deepcopy(CONTENT)
    fields = content["instantons"][1]["values"][2]
    old = fields["P1_invPlanckMass"][0]
    new = math.nextafter(old, math.inf)
    fields["P1_invPlanckMass"][0] = new
    a, b = two(tmp, content)
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_DIFFERENT, text
    assert result["tables"]["FullInstanton"]["matched"] == 2
    value = result["tables"]["FullInstantonValue"]
    assert (value["a_only"], value["b_only"]) == (1, 1)
    assert (value["rows_a_only"], value["rows_b_only"]) == ([], [])
    (pair,) = value["near_misses"]
    (diff,) = pair["differing"]
    assert diff["column"] == 'fields_json["P1_invPlanckMass"][0]'
    assert (diff["a_hex"], diff["b_hex"]) == (old.hex(), new.hex())
    assert pair["through_references"] == []
    assert pair["a"]["N_serial"]["row"] == {"N": N_GRID[2]}
    assert 'fields_json["P1_invPlanckMass"][0]' in text


def test_08_polymorphic_reference_resolved_through_its_type(tmp):
    """(8) The trajectory names its potential under another serial in B (the two potential
    tables' serials exchanged): equal. An unknown potential_type: a named problem, counted
    once, and no exception."""
    a, b = two(tmp, swap_potential_serials=True)
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_EQUAL, text
    assert result["problems"] == []

    content = copy.deepcopy(CONTENT)
    content["trajectory"]["potential_type"] = 7
    c = build_store(tmp / "c", "store", content)
    code, text, result = run_tool(tmp, a, c)
    assert code == cs.EXIT_DIFFERENT, text
    (problem,) = _problems(result, "unknown type value")
    assert problem["store"] == "B"
    assert (
        "InflatonTrajectory.potential_type = 7 maps to no table" in problem["message"]
    )
    assert problem["count"] == 1
    assert result["tables"]["InflatonTrajectory"]["b_only"] == 1

    content = copy.deepcopy(CONTENT)
    content["instantons"][0]["diffusion_type"] = 2
    d = build_store(tmp / "d", "store", content)
    code, text, result = run_tool(tmp, a, d)
    assert code == cs.EXIT_DIFFERENT, text
    (problem,) = _problems(result, "unknown type value")
    assert "FullInstanton.diffusion_type = 2 maps to no table" in problem["message"]


def test_09_absolute_and_bare_shard_records(tmp):
    """(9) A primary recording absolute paths and one recording bare names are both read, by the
    glob; no recorded path is ever opened. Every connection is mode=ro on the primary or a
    globbed shard."""
    bare = build_store(tmp / "bare", "store", records="bare")
    absolute = build_store(tmp / "absolute", "store", records="absolute")
    nowhere = [tmp / "nowhere" / f"gone-shard{i:04d}.sqlite" for i in range(2)]
    missing = build_store(tmp / "missing", "store", absolute_records=nowhere)
    # the hazard: a copied primary whose absolute records name another store's shards
    other = copy.deepcopy(CONTENT)
    other["instantons"][0]["msr_action"] = 99.0
    build_store(tmp / "decoy", "store", other)
    decoy_shards = sorted((tmp / "decoy").glob("store-shard*.sqlite"))
    copied = build_store(tmp / "copied", "store", absolute_records=decoy_shards)

    opened = []
    real_connect = sqlite3.connect

    def recording_connect(database, *args, **kwargs):
        opened.append(database)
        return real_connect(database, *args, **kwargs)

    for a, b in [(bare, absolute), (bare, missing), (bare, copied)]:
        opened.clear()
        with mock.patch("sqlite3.connect", recording_connect):
            code, text, result = run_tool(tmp, a, b)
        assert code == cs.EXIT_EQUAL, text
        allowed = {
            str(p)
            for store in (a, b)
            for p in [store] + sorted(store.parent.glob("store-shard*.sqlite"))
        }
        # the primary and both shards of each store, and nothing else
        assert len(opened) == 6
        paths = []
        for uri in opened:
            assert uri.startswith("file:"), uri
            assert uri.endswith("?mode=ro"), uri
            paths.append(unquote(uri[len("file:") : -len("?mode=ro")]))
        assert set(paths) == allowed
        for path in nowhere + decoy_shards:
            assert str(path) not in paths


def test_10_a_shard_count_that_disagrees(tmp):
    """(10) A shard more or less than the primary's shards table records: exit 2, and an
    unreadable primary likewise."""
    a = build_store(tmp / "a", "store")
    fewer = build_store(tmp / "fewer", "store")
    (tmp / "fewer" / "store-shard0001.sqlite").unlink()
    more = build_store(tmp / "more", "store")
    shutil.copy(
        tmp / "more" / "store-shard0001.sqlite", tmp / "more" / "store-shard0002.sqlite"
    )
    for b in (fewer, more):
        code, text, result = run_tool(tmp, a, b)
        assert code == cs.EXIT_UNREADABLE, text
        assert result is None
        assert "shards table records 2 shard(s)" in text
    code, text, _ = run_tool(tmp, a, tmp / "absent.sqlite")
    assert code == cs.EXIT_UNREADABLE, text


def test_11_replicated_copies_that_differ(tmp):
    """(11) One shard's copy of a replicated table differs from the other's: a named problem
    (exit 1), for it and for the replicated table that references it, though the lowest
    shard's copies of the two stores agree and every table matches."""
    a, b = two(tmp)
    conn = sqlite3.connect(tmp / "b" / "store-shard0001.sqlite")
    with conn:
        conn.execute("update quartic_coupling set value = 2e-13")
    conn.close()
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_DIFFERENT, text
    problems = _problems(result, "replicated copies differ")
    assert {p["store"] for p in problems} == {"B"}
    assert sorted(p["message"].split(":")[0] for p in problems) == [
        "QuarticPotential",
        "quartic_coupling",
    ]
    for table, entry in result["tables"].items():
        assert (entry["a_only"], entry["b_only"]) == (0, 0), table
    assert (
        "replicated copies differ: quartic_coupling: the copy on store-shard0001"
        in text
    )


def test_13_schema_snapshot(tmp):
    """(13) The schema snapshot round-trips (exit 0 against itself); a dropped index and an
    added column are each reported (exit 1); column order is not a difference."""
    a = build_store(tmp / "a", "store")
    snapshot = tmp / "a.json"
    code, text, _ = run_tool(tmp, "--snapshot", a, "--out", snapshot)
    assert code == cs.EXIT_EQUAL, text
    data = json.loads(snapshot.read_text())
    assert data["format"] == cs.SNAPSHOT_FORMAT
    assert [["instanton_serial", "N_serial"], True] in data["tables"][
        "FullInstantonValue"
    ]["indices"]
    assert [["delta_Nstar_serial"], "delta_Nstar", ["serial"]] in data["tables"][
        "FullInstanton"
    ]["foreign_keys"]
    code, text, _ = run_tool(tmp, "--schema", a, "--against", snapshot)
    assert code == cs.EXIT_EQUAL, text
    assert "RESULT: the schemas agree" in text

    b = build_store(tmp / "b", "store")
    conn = sqlite3.connect(tmp / "b" / "store-shard0000.sqlite")
    with conn:
        conn.execute("drop index ix_FullInstanton_delta_Nstar_serial")
        conn.execute("alter table FullInstanton add column extra float")
    conn.close()
    code, text, _ = run_tool(tmp, "--schema", b, "--against", snapshot)
    assert code == cs.EXIT_DIFFERENT, text
    assert (
        'FullInstanton: index [["delta_Nstar_serial"], false] in the reference only'
        in text
    )
    assert "FullInstanton: column extra" in text

    # column order is not a difference (the package prepends serial, version, timestamp)
    c = build_store(tmp / "c", "store")
    conn = sqlite3.connect(tmp / "c" / "store-shard0000.sqlite")
    with conn:
        conn.executescript(
            """
            create table redshift2 (z float, timestamp datetime, serial integer primary key);
            insert into redshift2 select z, timestamp, serial from redshift;
            drop table redshift;
            alter table redshift2 rename to redshift;
            """
        )
    conn.close()
    code, text, _ = run_tool(tmp, "--schema", c, "--against", snapshot)
    assert code == cs.EXIT_EQUAL, text


def test_14_no_file_the_tool_reads_changes(tmp):
    """(14) Every file's checksum, size and modification time are the same after the tool, and
    it leaves no new file (no journal) beside the stores."""
    a, b = two(tmp, serial_offset=3)
    before = _tree_state(tmp)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cs.main([str(a), str(b)])
        cs.main(["--snapshot", str(a)])
    assert code == cs.EXIT_EQUAL, out.getvalue()
    assert _tree_state(tmp) == before


def test_json_keys_on_one_side_only_are_a_difference(tmp):
    """A key present in one row's JSON and not the other's is a difference (not a near miss),
    as is a timing key's sibling science key removed at depth."""
    content = copy.deepcopy(CONTENT)
    del content["instantons"][0]["diagnostics"]["outer_iterations"]
    a, b = two(tmp, content)
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_DIFFERENT, text
    fi = result["tables"]["FullInstanton"]
    assert (fi["a_only"], fi["b_only"]) == (1, 1)
    assert fi["near_misses"] == []
    (row_a,) = fi["rows_a_only"]
    (row_b,) = fi["rows_b_only"]
    assert row_a["diagnostics_json"]["outer_iterations"] == 4
    assert "outer_iterations" not in row_b["diagnostics_json"]

    content = copy.deepcopy(CONTENT)
    del content["instantons"][0]["diagnostics"]["nested"]["C_min"]
    c = build_store(tmp / "c", "store", content)
    code, text, result = run_tool(tmp, a, c)
    assert code == cs.EXIT_DIFFERENT, text


def test_json_that_does_not_parse_is_a_named_problem(tmp):
    """A JSON column holding text that is not JSON: a named problem, compared as text."""
    content = copy.deepcopy(CONTENT)
    content["instantons"][1]["diagnostics"] = '{"compute_time": 4.25, "converged": tru'
    a, b = two(tmp, content)
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_DIFFERENT, text
    (problem,) = _problems(result, "JSON that does not parse")
    assert problem["store"] == "B"
    assert problem["message"].startswith("FullInstanton.diagnostics_json")
    assert problem["count"] == 1


def test_json_integer_float_and_boolean_are_distinct(tmp):
    """Inside JSON, 4 and 4.0 and true and 1 are different values."""
    for change in (4.0, True):
        content = copy.deepcopy(CONTENT)
        content["instantons"][0]["diagnostics"]["outer_iterations"] = change
        directory = tmp / f"case-{change!r}"
        a = build_store(directory / "a", "store")
        b = build_store(directory / "b", "store", content)
        assert not cs.compare_stores(a, b)["equal"], change


def test_classification_and_notes(tmp):
    """Listed tables take the primary's class; redshift, in neither list and with no foreign
    key, is compared as sharded and noted; a listed table no shard holds is noted; no layer
    table is a client table."""
    a, b = two(tmp)
    _, _, result = run_tool(tmp, a, b)
    kinds = {t: e["kind_a"] for t, e in result["tables"].items()}
    assert kinds == {
        "FullInstanton": "sharded",
        "FullInstantonValue": "sharded",
        "InflatonTrajectory": "replicated",
        "InflatonTrajectoryValue": "replicated",
        "MasslessDecoupledDiffusion": "replicated",
        "QuadraticPotential": "replicated",
        "QuarticPotential": "replicated",
        "delta_Nstar": "replicated",
        "efold_value": "replicated",
        "inflaton_mass": "replicated",
        "quartic_coupling": "replicated",
        "redshift": "sharded",
        "tolerance": "replicated",
        "version": "replicated",
    }
    assert result["tables"]["redshift"]["matched"] == 1
    assert any(
        "redshift is on the shards but in neither" in note for note in result["notes"]
    )
    assert any(
        "IntegrationSolver is listed as replicated" in note for note in result["notes"]
    )


def test_a_client_table_on_the_primary_is_a_named_problem(tmp):
    """A primary holding a table that is not the layer's: a named problem."""
    a, b = two(tmp)
    conn = sqlite3.connect(b)
    with conn:
        conn.execute(
            "create table version (serial integer primary key, label varchar(256))"
        )
    conn.close()
    code, text, result = run_tool(tmp, a, b)
    assert code == cs.EXIT_DIFFERENT, text
    (problem,) = _problems(result, "client table on the primary")
    assert "version" in problem["message"]


def test_help():
    """--help prints the usage and exits 0."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), pytest.raises(SystemExit) as ctx:
        cs.main(["--help"])
    assert ctx.value.code == 0
    assert "--snapshot" in out.getvalue()


def test_the_tool_imports_the_standard_library_only():
    """The tool reads stores through sqlite3 alone: it imports no layer, no Ray, no SQLAlchemy,
    nor anything of this repository."""
    tree = ast.parse((ROOT / "tools" / "compare_stores.py").read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            modules.add((node.module or "").split(".")[0])
    assert modules <= set(sys.stdlib_module_names), modules - set(
        sys.stdlib_module_names
    )
    assert "sqlite3" in modules
    source = (ROOT / "tools" / "compare_stores.py").read_text()
    assert not re.search(
        r"\battach\b", source, re.IGNORECASE
    )  # no other database is attached


# ---------------------------------------------------------------------------
# (12) the declared maps against the registries, the factories and ComputeTargets/


def _registry():
    """The factory registry: config.datastore's from dk-and-rpk-migration prompt 05 on, the
    layer's before it. Importing it imports ray, but needs no cluster."""
    try:
        from config.datastore import factories
    except ImportError:
        from Datastore.SQL.Datastore import _factories as factories
    return factories


def _registered_columns(registration):
    """The column names an actor gives a table, from its register() data."""
    names = []
    if registration.get("serial", True):
        names.append("serial")
    if registration.get("version", False):
        names.append("version")
    if registration.get("timestamp", False):
        names.append("timestamp")
    stepping = registration.get("stepping", False)
    if stepping is True or stepping in ("minimum", "exact"):
        names.append("stepping")
    return names + [c.name for c in registration.get("columns", [])]


@pytest.fixture(scope="module")
def registrations():
    return {name: factory.register() for name, factory in _registry().items()}


def test_12a_polymorphic_maps_equal_the_registries(registrations):
    """(12) Every polymorphic entry equals POTENTIAL_REGISTRY's or DIFFUSION_MODEL_REGISTRY's
    map, in both directions; both registries are non-empty (the diffusion registry is filled
    only when its factory module is imported); each registry key is its class's type_id and a
    model_ids constant; and each mapped table is registered with a serial."""
    import Datastore.SQL.ObjectFactories.MasslessDecoupledDiffusion  # noqa: F401  fills it
    from CosmologyConcepts.Potentials import model_ids as potential_ids
    from CosmologyConcepts.Potentials.registry import POTENTIAL_REGISTRY
    from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
    from InflationConcepts.DiffusionModel import model_ids as diffusion_ids
    from InflationConcepts.DiffusionModel.registry import DIFFUSION_MODEL_REGISTRY

    assert len(POTENTIAL_REGISTRY) > 0
    assert len(DIFFUSION_MODEL_REGISTRY) > 0

    potential_map = {key: info.table_name for key, info in POTENTIAL_REGISTRY.items()}
    diffusion_map = {key: info.name for key, info in DIFFUSION_MODEL_REGISTRY.items()}
    assert cs.POLYMORPHIC_REFERENCES == {
        "InflatonTrajectory": {"potential_serial": ("potential_type", potential_map)},
        "FullInstanton": {"diffusion_serial": ("diffusion_type", diffusion_map)},
        "SlowRollInstanton": {"diffusion_serial": ("diffusion_type", diffusion_map)},
        "GradientCoupledInstanton": {
            "diffusion_serial": ("diffusion_type", diffusion_map)
        },
    }

    def constants(module):
        return {
            v for k, v in vars(module).items() if k.isupper() and isinstance(v, int)
        }

    assert set(POTENTIAL_REGISTRY) == constants(potential_ids)
    assert set(DIFFUSION_MODEL_REGISTRY) == constants(diffusion_ids)
    for key, info in POTENTIAL_REGISTRY.items():
        assert info.type_id == key
        assert info.cls.type_id.fget(None) == key
        assert info.cls.__name__ == info.table_name
    assert DIFFUSION_MODEL_REGISTRY[MasslessDecoupledDiffusion().type_id].name == (
        "MasslessDecoupledDiffusion"
    )

    for pairs in cs.POLYMORPHIC_REFERENCES.values():
        for _, mapping in pairs.values():
            for table in mapping.values():
                assert table in registrations and registrations[table] is not None
                assert "serial" in _registered_columns(registrations[table])


def test_12b_every_polymorphic_pair_is_declared(registrations):
    """(12) Each declared pair names two registered columns, the serial one with no foreign
    key; and every *_serial column with no foreign key, and every *_type column, in any
    factory's register() is a declared pair, so a fifth pair cannot be missed."""
    declared = set()
    for table, pairs in cs.POLYMORPHIC_REFERENCES.items():
        by_name = {c.name: c for c in registrations[table]["columns"]}
        for serial_column, (type_column, _) in pairs.items():
            declared |= {(table, serial_column), (table, type_column)}
            assert serial_column in by_name and type_column in by_name
            assert len(by_name[serial_column].foreign_keys) == 0

    found = set()
    for table, registration in registrations.items():
        if not registration:
            continue
        for column in registration.get("columns", []):
            if (column.name.endswith("_serial") and len(column.foreign_keys) == 0) or (
                column.name.endswith("_type")
            ):
                found.add((table, column.name))
    assert found == declared


def test_12c_bookkeeping_and_json_columns_name_registered_columns(registrations):
    """(12) Every bookkeeping column names a column some factory's register() declares; every
    JSON column is a registered Text column; and every registered Text column is either a JSON
    column or one of the four known to hold plain text."""
    import sqlalchemy as sqla

    columns = {name: _registered_columns(r) for name, r in registrations.items() if r}
    for column in cs.GLOBAL_BOOKKEEPING:
        assert any(column in names for names in columns.values()), column
    for table, entries in cs.BOOKKEEPING_COLUMNS.items():
        for column in entries:
            assert column in columns[table], f"{table}.{column}"

    text_columns = set()
    for table, registration in registrations.items():
        if not registration:
            continue
        for column in registration.get("columns", []):
            if isinstance(column.type, sqla.Text):
                text_columns.add((table, column.name))
    json_columns = {
        (table, column)
        for table, entries in cs.JSON_COLUMNS.items()
        for column in entries
    }
    assert json_columns <= text_columns
    assert text_columns - json_columns == {
        ("FullInstanton", "label"),
        ("SlowRollInstanton", "label"),
        ("GradientCoupledInstanton", "label"),
        ("CompactionFunctionSamples", "source"),
    }


_TIME_LIKE = re.compile(
    r"""["']([A-Za-z0-9_]*(?:time|wallclock|clock|elapsed|seconds|duration)[A-Za-z0-9_]*)["']"""
)

# string literals in ComputeTargets/ that look like times and are not timing keys
_NOT_TIMING = {
    "wallclock_budget_seconds": "the solve's configured budget, constant when unbudgeted",
    "wallclock_budget_exceeded": "the solve's outcome against its budget",
    "wallclock_budget": "a value of bailout_reason, not a key",
}


def test_12d_timing_keys_appear_in_compute_targets():
    """(12) Every JSON timing key is a string literal in ComputeTargets/; and every time-like
    string literal there is a timing key or one of the three known not to be."""
    source = "\n".join(
        path.read_text() for path in sorted((ROOT / "ComputeTargets").rglob("*.py"))
    )
    for key in cs.TIMING_KEYS:
        assert f'"{key}"' in source or f"'{key}'" in source, key
    found = set(_TIME_LIKE.findall(source))
    assert found - set(_NOT_TIMING) == set(cs.TIMING_KEYS)
