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
Compare two StochasticInstanton sharded stores by what they hold, never by how it is laid out;
or write and compare a store's schema snapshot.

    ./venv/bin/python tools/compare_stores.py A.sqlite B.sqlite [--json OUT] [--max-rows N]
    ./venv/bin/python tools/compare_stores.py --snapshot A.sqlite [--out F]
    ./venv/bin/python tools/compare_stores.py --schema A.sqlite --against F

A.sqlite and B.sqlite are primaries. Exit 0 when nothing compared differs, 1 when something does
(a row in one store only, a science value that differs, or a named problem), 2 when a store
cannot be read. Written for dk-and-rpk-migration prompt 01 (README section 4.2), as the
acceptance instrument of the rehearsals RH0, RH1 and RH2 and of P2's comparison of its rebuilt
grids with the June ones. Modelled on ChamPBH's tool of the same name (ChamPBH d7791c5), which it
does not import.

**Reading.** Every file is opened `sqlite3.connect("file:PATH?mode=ro", uri=True)` and nothing
else: never through `Datastore`, `ShardedPool`, `datastorekit`, SQLAlchemy or Ray, none of which
is imported. So a store of either format is read: StochasticInstanton's own (absolute shard
records) and DatastoreKit's (bare shard names, and a `replication_in_flight` table on the
primary). The shards are found by the glob `<stem>-shard*<suffix>` beside the primary, and their
number is checked against the rows of the primary's `shards` table. **No path read from the
`shards` table is ever opened**, nor is its `filename` column read: a StochasticInstanton primary
records the absolute path of each shard of the resolved primary
(`Datastore/SQL/ShardedPool.py:88`, `:296`), which for a copied store names the original's files.

**What is compared.** Every row of every client table (a table on the shards that is not the
layer's), as a multiset of identities. A row's identity is its columns but the bookkeeping ones
(`GLOBAL_BOOKKEEPING`, `BOOKKEEPING_COLUMNS`), each value in canonical form (a float by
`float.hex` of the stored value, so to the last bit), with each foreign-key column replaced by the
identity of the row it names on the same shard, recursively, and each declared polymorphic
reference (`POLYMORPHIC_REFERENCES`) resolved the same way through its type column. A JSON column
(`JSON_COLUMNS`) is parsed and compared structurally: its floats by `float.hex`, recursively
through lists and objects, a key present on one side only a difference, and its timing keys
(`TIMING_KEYS`, at any depth) set aside as bookkeeping. So serials, shard assignment, insertion
order and timings do not matter, and every stored science value does. A replicated table is
compared once, by its lowest shard's copy; within each store every shard's copy is checked equal
to that one, and a difference is a named problem.

**What is not compared.** The primary's own tables (`LAYER_TABLES`), and the bookkeeping columns
and timing keys, whose differences between matched rows are counted and reported apart. A table
the primary lists but no shard holds is noted and skipped. A table on the shards that is in
neither of the primary's lists (`redshift` in a StochasticInstanton store; it is registered but in
neither list of `config/sharding.py`) is noted, classified by its foreign keys as ChamPBH's tool
does (with none, it is sharded: its rows are taken from every shard), and compared.

**Output.** Per table, the rows matched and in each store only; each unmatched row rendered by its
physical labels (a referenced row by its own columns, not a digest); near misses (an A-only and a
B-only row whose non-float content agrees, inside JSON too, and whose references name rows that
both stores hold or rows that are themselves near misses), each differing float, in a column or at
a path inside JSON, with both values and their relative difference; the bookkeeping differences;
the problems. `--json` also writes the whole result. The human output lists at most `--max-rows`
rows per list (default 20); the JSON lists every one.

**Schema snapshot.** For each client table on the lowest shard: its columns (name, declared type,
not null, primary key), its indices (the tuple of their columns and whether unique, not their
names) and its foreign keys, each as a set, written as sorted JSON. `--schema A --against F`
reports each difference. Column order is never a difference.

Run from the repository root.
"""

import argparse
import glob
import hashlib
import json
import math
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

EXIT_EQUAL = 0
EXIT_DIFFERENT = 1
EXIT_UNREADABLE = 2

# The primary's own tables, which are the layer's and are never compared: StochasticInstanton's
# (Datastore/SQL/ShardedPool.py:244-284, created at :287-291 by _write_shard_data) and
# DatastoreKit's, which adds replication_in_flight (client contract section 5). A
# StochasticInstanton primary holds these five and no client table: the primary's engine creates
# nothing else (ShardedPool.py:232-291) and writes only shard_keys after creation (:810-821);
# every Datastore actor is given a shard file, never the primary (:158-191).
LAYER_TABLES = frozenset(
    {
        "shards",
        "shard_key_config",
        "shard_keys",
        "replicated_tables",
        "sharded_tables",
        "replication_in_flight",
    }
)

# Bookkeeping columns: reported, never compared. Each depends on the run or on the code path that
# wrote the row, not on the physics. GLOBAL_BOOKKEEPING applies to every table that has the
# column; BOOKKEEPING_COLUMNS adds per-table ones. Each entry says why. (prompt 01 section 2.2)
GLOBAL_BOOKKEEPING = {
    "serial": "the layer's key, leased from the serial broker at insert "
    "(Datastore/SQL/Datastore.py:317, :639-647); foreign keys are resolved through it",
    "timestamp": "datetime.now() at insert (Datastore/SQL/Datastore.py:651-652)",
}

_LABEL_WHY = (
    "set by the code path, not the run: a row stored by the per-stage queue carries the "
    "factory's default, a .4g rendering of N_init, N_final and dNstar that the row's foreign "
    "keys already compare to the bit ({factory}); a row stored by the unified pipeline "
    "(--no-store-values) is constructed with no label (ComputeTargets/pipeline.py:{line}), so the "
    "column is NULL. One grid built both ways differs here and nowhere in its physics"
)

BOOKKEEPING_COLUMNS = {
    "FullInstanton": {
        "label": _LABEL_WHY.format(
            factory="Datastore/SQL/ObjectFactories/FullInstanton.py:149-155, written at :285, "
            ":310",
            line="288-298",
        ),
    },
    "SlowRollInstanton": {
        "label": _LABEL_WHY.format(
            factory="Datastore/SQL/ObjectFactories/SlowRollInstanton.py:148-154, written at "
            ":282, :307",
            line="304-314",
        ),
    },
    # GradientCoupledInstanton.label is NOT bookkeeping: its only writer is main.py's gradient
    # branch, whose payload carries no label (main.py:632-643), so the column is always the
    # factory's default rendering of the physics (GradientCoupledInstanton.py:223-231, written at
    # :492, :536). It cannot differ between two builds of one grid on one tree, and is compared.
}

# JSON columns: parsed and compared structurally. Each is written only by json.dumps, or NULL,
# at the line given; a value that does not parse is a named problem, and is compared as text.
# Every other Text column (the three label columns, CompactionFunctionSamples.source) is text.
JSON_COLUMNS = {
    "InflatonTrajectory": {
        "diagnostics_json": "Datastore/SQL/ObjectFactories/InflatonTrajectory.py:204"
    },
    "InflatonTrajectoryValue": {
        "fields_json": "Datastore/SQL/ObjectFactories/InflatonTrajectory.py:222-225"
    },
    "FullInstanton": {
        "diagnostics_json": "Datastore/SQL/ObjectFactories/FullInstanton.py:259-264"
    },
    "FullInstantonValue": {
        "fields_json": "Datastore/SQL/ObjectFactories/FullInstanton.py:324-329"
    },
    "SlowRollInstanton": {
        "diagnostics_json": "Datastore/SQL/ObjectFactories/SlowRollInstanton.py:256-261"
    },
    "SlowRollInstantonValue": {
        "fields_json": "Datastore/SQL/ObjectFactories/SlowRollInstanton.py:321-324"
    },
    "GradientCoupledInstanton": {
        "diagnostics_json": "Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:452-457"
    },
    "GradientCoupledInstantonValue": {
        "fields_json": "Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:548-553"
    },
    "CompactionFunction": {
        "metadata": "Datastore/SQL/ObjectFactories/CompactionFunction.py:358-364"
    },
}

# Timing keys inside a JSON column: bookkeeping at any depth, reported when they differ and never
# counted. Each is a time.perf_counter() interval. Not timing keys: wallclock_budget_seconds and
# wallclock_budget_exceeded (ComputeTargets/GradientCoupledInstanton/picard.py:1724-1725), the
# solve's configuration and its outcome against it, constant when unbudgeted; bailout_reason,
# whose value "wallclock_budget" (:1697) is the same outcome; and every step or iteration count
# and rk45_* statistic, which the integrator sets, not the clock.
TIMING_KEYS = {
    "compute_time": "the worker's elapsed time: ComputeTargets/InflatonTrajectory.py:76, :99, "
    ":114, :140; FullInstanton.py:111, :269; SlowRollInstanton.py:146, :180, :241, :268, :306; "
    "CompactionFunction.py:143, :168, :252, :263, :315, :404, copied to the metadata's top "
    "level at :671, :679 and nested under 'full'/'slow_roll'; "
    "GradientCoupledInstanton/picard.py:1704",
    "compute_time_total": "GradientCoupledInstanton's elapsed time "
    "(ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py:453)",
    "mean_time_per_picard_iteration": "Picard time over Picard iterations "
    "(ComputeTargets/FullInstanton.py:122, :283; GradientCoupledInstanton/picard.py:1718)",
    "picard_sweep_wallclock_min": "per-sweep wall time, under instrument_stiffness "
    "(ComputeTargets/GradientCoupledInstanton/picard.py:1276)",
    "picard_sweep_wallclock_mean": "per-sweep wall time, under instrument_stiffness "
    "(ComputeTargets/GradientCoupledInstanton/picard.py:1277-1279)",
    "picard_sweep_wallclock_max": "per-sweep wall time, under instrument_stiffness "
    "(ComputeTargets/GradientCoupledInstanton/picard.py:1280)",
}

# Polymorphic references: a serial column with no foreign key, whose table is named by a type
# column. table -> serial column -> (type column, {type value: table}). Every such pair in the
# factories' register() is here (a *_serial column with no ForeignKey beside a *_type column):
# - potential_serial / potential_type on InflatonTrajectory
#   (Datastore/SQL/ObjectFactories/InflatonTrajectory.py:52-63, written at :194-195 from the
#   potential's type_id). The values are CosmologyConcepts/Potentials/model_ids.py's, and each
#   table is POTENTIAL_REGISTRY's table_name (CosmologyConcepts/Potentials/registry.py:27-42);
# - diffusion_serial / diffusion_type on FullInstanton (FullInstanton.py:78-79), SlowRollInstanton
#   (SlowRollInstanton.py:77-78) and GradientCoupledInstanton (GradientCoupledInstanton.py:91-92),
#   written from the diffusion model's type_id. The value is
#   InflationConcepts/DiffusionModel/model_ids.py's, and the table is DIFFUSION_MODEL_REGISTRY's
#   name (filled at Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py:69-72).
# tests/test_compare_stores.py checks these maps against both registries; this tool imports
# neither. A type value a map lacks is a named problem, not a crash.
_POTENTIAL_TYPES = {1: "QuadraticPotential", 2: "QuarticPotential"}
_DIFFUSION_TYPES = {1: "MasslessDecoupledDiffusion"}
POLYMORPHIC_REFERENCES = {
    "InflatonTrajectory": {"potential_serial": ("potential_type", _POTENTIAL_TYPES)},
    "FullInstanton": {"diffusion_serial": ("diffusion_type", _DIFFUSION_TYPES)},
    "SlowRollInstanton": {"diffusion_serial": ("diffusion_type", _DIFFUSION_TYPES)},
    "GradientCoupledInstanton": {
        "diffusion_serial": ("diffusion_type", _DIFFUSION_TYPES)
    },
}

SNAPSHOT_FORMAT = "stochasticinstanton-compare-stores-schema"
SNAPSHOT_VERSION = 1

# how many examples of one kind of problem are kept
_PROBLEM_EXAMPLES = 5

# longest rendering of one value in the human output
_RENDER_WIDTH = 120


class StoreReadError(Exception):
    """A store cannot be read: exit 2."""


def connect_ro(path) -> sqlite3.Connection:
    """
    A read-only connection to one SQLite file: URI `file:PATH?mode=ro`. A write through it
    raises sqlite3.OperationalError. Every connection this tool opens is made here.
    """
    return sqlite3.connect(
        "file:" + quote(os.fspath(path), safe="/") + "?mode=ro", uri=True
    )


def canonical_float(value: float):
    """A float's canonical form: its stored bits, by float.hex."""
    return ["f", value.hex()]


def canonical_value(value):
    """
    A stored value in canonical form, for an identity: a float by `canonical_float`, an integer
    (and so a boolean) as an integer, a string as it is, bytes in hex, NULL as None. Each is
    tagged with its kind, so that 1 and 1.0 and "1" differ.
    """
    if value is None:
        return None
    if isinstance(value, float):
        return canonical_float(value)
    if isinstance(value, int):
        return ["i", int(value)]
    if isinstance(value, str):
        return ["s", value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        return ["x", bytes(value).hex()]
    return ["?", repr(value)]


def canonical_json(value, timing_keys, skeleton=False):
    """
    A parsed JSON value in canonical form: an object as its sorted (key, value) pairs less the
    timing keys, at any depth; a list in order; a float by `canonical_float` (or, for the
    skeleton that pairs near misses, by the bare tag "f"); a boolean, an integer and a string
    each tagged with its kind; null as None.
    """
    if isinstance(value, dict):
        return [
            "d",
            [
                [key, canonical_json(value[key], timing_keys, skeleton)]
                for key in sorted(value)
                if key not in timing_keys
            ],
        ]
    if isinstance(value, list):
        return ["l", [canonical_json(item, timing_keys, skeleton) for item in value]]
    if isinstance(value, bool):
        return ["b", value]
    if isinstance(value, float):
        return ["f"] if skeleton else canonical_float(value)
    if isinstance(value, int):
        return ["i", value]
    if isinstance(value, str):
        return ["s", value]
    if value is None:
        return None
    return ["?", repr(value)]


def json_timings(value, timing_keys, path="") -> dict:
    """{path: value} for each timing key in a parsed JSON value, at any depth."""
    out = {}
    if isinstance(value, dict):
        for key, item in value.items():
            if key in timing_keys:
                out[f"{path}[{json.dumps(key)}]"] = item
            elif isinstance(item, (dict, list)):
                out.update(
                    json_timings(item, timing_keys, f"{path}[{json.dumps(key)}]")
                )
    elif isinstance(value, list):
        for i, item in enumerate(value):
            if isinstance(item, (dict, list)):
                out.update(json_timings(item, timing_keys, f"{path}[{i}]"))
    return out


class _Skeleton:
    """A parsed JSON value whose float-less skeleton is computed only if a near key needs it."""

    __slots__ = ("parsed",)

    def __init__(self, parsed):
        self.parsed = parsed


def json_without_timings(value, timing_keys):
    """A parsed JSON value with its timing keys removed at any depth, for labels."""
    if isinstance(value, dict):
        return {
            key: json_without_timings(item, timing_keys)
            for key, item in value.items()
            if key not in timing_keys
        }
    if isinstance(value, list):
        return [json_without_timings(item, timing_keys) for item in value]
    return value


def json_float_differences(a, b, timing_keys, path=""):
    """
    [(path, a, b)] for each float that differs between two parsed JSON values of one skeleton
    (equal but for their floats, timing keys aside).
    """
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key in timing_keys or key not in a or key not in b:
                continue
            out += json_float_differences(
                a[key], b[key], timing_keys, f"{path}[{json.dumps(key)}]"
            )
    elif isinstance(a, list) and isinstance(b, list):
        for i, (x, y) in enumerate(zip(a, b)):
            out += json_float_differences(x, y, timing_keys, f"{path}[{i}]")
    elif isinstance(a, float) and isinstance(b, float):
        if canonical_float(a) != canonical_float(b):
            out.append((path, a, b))
    return out


def is_float_type(declared: str) -> bool:
    """SQLite's rule for REAL affinity: the declared type contains REAL, FLOA or DOUB."""
    declared = (declared or "").upper()
    return any(word in declared for word in ("REAL", "FLOA", "DOUB"))


def _digest(obj) -> bytes:
    return hashlib.blake2b(
        json.dumps(obj, separators=(",", ":"), ensure_ascii=True).encode(),
        digest_size=16,
    ).digest()


def _sort_key(value):
    return json.dumps(value, sort_keys=True, default=repr)


class _Problems:
    """Named problems, counted by kind, with a few examples of each."""

    def __init__(self):
        self._items = {}

    def add(self, store: str, kind: str, message: str, example=None):
        key = (store, kind, message)
        item = self._items.setdefault(
            key,
            {
                "store": store,
                "kind": kind,
                "message": message,
                "count": 0,
                "examples": [],
            },
        )
        item["count"] += 1
        if example is not None and len(item["examples"]) < _PROBLEM_EXAMPLES:
            item["examples"].append(example)

    def as_list(self):
        return [self._items[key] for key in sorted(self._items)]

    def __len__(self):
        return len(self._items)


# ---------------------------------------------------------------------------
# reading a store


class Store:
    """
    One sharded store, read through read-only sqlite3 connections only: the primary, and the
    shards found by the glob `<stem>-shard*<suffix>` beside it.
    """

    def __init__(self, primary, name: str, problems: _Problems, notes: list):
        self.name = name
        self.problems = problems
        self.notes = notes
        self.primary = Path(os.path.abspath(os.path.expanduser(os.fspath(primary))))
        self.connections = []
        if not self.primary.is_file():
            raise StoreReadError(f'{name}: primary "{self.primary}" is not a file')

        try:
            self._read_primary()
            self._find_shards()
            self._read_shards()
        except sqlite3.Error as e:
            self.close()
            raise StoreReadError(f'{name}: cannot read "{self.primary}": {e}') from e
        except StoreReadError:
            self.close()
            raise

    def close(self):
        for conn in self.connections:
            conn.close()
        self.connections = []

    @staticmethod
    def _tables(conn):
        return sorted(
            row[0]
            for row in conn.execute(
                "select name from sqlite_master where type = 'table' "
                "and name not like 'sqlite_%'"
            )
        )

    def _read_primary(self):
        conn = connect_ro(self.primary)
        try:
            tables = self._tables(conn)
            if "shards" not in tables:
                raise StoreReadError(
                    f'{self.name}: "{self.primary}" has no shards table; it is not the primary '
                    f"of a sharded store"
                )
            # only the number of records is read: never a recorded path
            self.recorded_shards = conn.execute(
                'select count(*) from "shards"'
            ).fetchone()[0]

            self.replicated = []
            if "replicated_tables" in tables:
                self.replicated = [
                    row[0]
                    for row in conn.execute(
                        'select "table" from "replicated_tables" order by serial'
                    )
                ]
            self.sharded = {}
            if "sharded_tables" in tables:
                self.sharded = {
                    row[0]: row[1]
                    for row in conn.execute(
                        'select "table", key_attr from "sharded_tables" order by serial'
                    )
                }
            if "replication_in_flight" in tables:
                in_flight = conn.execute(
                    'select count(*) from "replication_in_flight"'
                ).fetchone()[0]
                if in_flight > 0:
                    self.problems.add(
                        self.name,
                        "replication in flight",
                        f"the primary's replication_in_flight holds {in_flight} row(s): an "
                        f"interrupted replicated write, so the shards may differ",
                    )

            client = [t for t in tables if t not in LAYER_TABLES]
            if client:
                self.problems.add(
                    self.name,
                    "client table on the primary",
                    f"the primary holds tables that are not the layer's, which are not "
                    f"compared: {client}",
                )
        finally:
            conn.close()

    def _find_shards(self):
        stem = self.primary.stem
        suffix = self.primary.suffix
        pattern = (
            glob.escape(os.fspath(self.primary.parent / f"{stem}-shard"))
            + "*"
            + glob.escape(suffix)
        )
        self.shard_files = [Path(p) for p in sorted(glob.glob(pattern))]
        if len(self.shard_files) != self.recorded_shards:
            raise StoreReadError(
                f"{self.name}: the primary's shards table records {self.recorded_shards} "
                f"shard(s), but {len(self.shard_files)} file(s) match {pattern}"
            )
        if len(self.shard_files) == 0:
            raise StoreReadError(f"{self.name}: the store has no shards")

    def _read_shards(self):
        self.shard_tables = []
        for path in self.shard_files:
            conn = connect_ro(path)
            self.connections.append(conn)
            tables = self._tables(conn)
            layer = [t for t in tables if t in LAYER_TABLES]
            if layer:
                self.problems.add(
                    self.name,
                    "layer table on a shard",
                    f"shard {path.name} holds the layer's tables {layer}",
                )
            self.shard_tables.append({t for t in tables if t not in LAYER_TABLES})

        self.client_tables = sorted(set().union(*self.shard_tables))
        for table in self.replicated:
            if table not in self.client_tables:
                self.notes.append(
                    f"{self.name}: {table} is listed as replicated by the primary but no shard "
                    f"holds it; not compared"
                )
        for table in self.sharded:
            if table not in self.client_tables:
                self.notes.append(
                    f"{self.name}: {table} is listed as sharded by the primary but no shard "
                    f"holds it; not compared"
                )

        self._columns = {}
        self._foreign_keys = {}

    # -- schema, per shard

    def columns(self, shard: int, table: str):
        """[(name, declared type, not null, primary key position)], in table order."""
        key = (shard, table)
        if key not in self._columns:
            self._columns[key] = [
                (row[1], row[2] or "", bool(row[3]), int(row[5]))
                for row in self.connections[shard].execute(
                    f'pragma table_info("{table}")'
                )
            ]
        return self._columns[key]

    def foreign_keys(self, shard: int, table: str):
        """{column: (referenced table, referenced column)} for single-column foreign keys."""
        key = (shard, table)
        if key not in self._foreign_keys:
            groups = defaultdict(list)
            for row in self.connections[shard].execute(
                f'pragma foreign_key_list("{table}")'
            ):
                groups[row[0]].append((row[2], row[3], row[4]))
            fks = {}
            for parts in groups.values():
                if len(parts) != 1:
                    self.problems.add(
                        self.name,
                        "composite foreign key",
                        f"{table}: a composite foreign key {parts} is compared as plain values",
                    )
                    continue
                ref_table, column, ref_column = parts[0]
                if ref_column is None:
                    # a foreign key into the referenced table's primary key
                    pk = [c[0] for c in self.columns(shard, ref_table) if c[3] == 1]
                    ref_column = pk[0] if pk else "serial"
                fks[column] = (ref_table, ref_column)
            self._foreign_keys[key] = fks
        return self._foreign_keys[key]

    def listed(self, table: str) -> bool:
        return table in self.replicated or table in self.sharded

    def kind(self, table: str) -> str:
        """
        "replicated" or "sharded". A table the primary lists as replicated is replicated; one it
        lists as sharded is sharded. A table in neither list (redshift in a StochasticInstanton
        store; a replicated class's *_tags table in a DatastoreKit one) is replicated if its
        foreign keys, other than into store_tag, all name replicated tables (DatastoreKit's
        client contract section 5), and otherwise sharded: its rows are taken from every shard.
        """
        if table in self.replicated:
            return "replicated"
        if table in self.sharded:
            return "sharded"
        shard = self.lowest_shard(table)
        refs = [
            ref
            for ref, _ in self.foreign_keys(shard, table).values()
            if ref != "store_tag"
        ]
        if refs and all(ref in self.replicated for ref in refs):
            return "replicated"
        return "sharded"

    def lowest_shard(self, table: str) -> int:
        for shard, tables in enumerate(self.shard_tables):
            if table in tables:
                return shard
        raise KeyError(table)

    def shards_holding(self, table: str):
        return [
            shard for shard, tables in enumerate(self.shard_tables) if table in tables
        ]

    def rows(self, shard: int, table: str):
        """(column names, an iterator over the rows), streamed."""
        cursor = self.connections[shard].execute(f'select * from "{table}"')
        names = [d[0] for d in cursor.description]
        return names, cursor


# ---------------------------------------------------------------------------
# identities


class Identities:
    """
    Row identities of one store. A row's identity is its non-bookkeeping columns, in canonical
    form, with each foreign key and declared polymorphic reference replaced by the digest of the
    identity of the row it names on the same shard, and each JSON column by its parsed value's
    canonical form less its timing keys. Digests are memoised by (shard, table, key column, key
    value), so a value table resolves its parent once.

    A part of an identity is (column, canonical value, how, location, near, timings) where `how`
    is one of "value", "float", "json", "fk" or "poly"; `location` is (shard, table, key column,
    key value) of a referenced row, or None; `near` is what a near key keeps of the part (None for
    a float column; for a JSON column that parses, its parsed value, whose float-less skeleton a
    near key computes when it needs it; the canonical value otherwise); and `timings` is a JSON
    column's {path: value} of its timing keys (None for any other column).
    """

    def __init__(
        self, store: Store, bookkeeping, polymorphic, json_columns, timing_keys
    ):
        self.store = store
        self.bookkeeping = bookkeeping
        self.polymorphic = polymorphic
        self.json_columns = json_columns
        self.timing_keys = frozenset(timing_keys)
        self._index = {}
        self._digests = {}
        self._labels = {}
        self._near = {}
        self._active = set()
        self._reported = set()
        # False while a row already counted is read again (pass 2, near keys), so that each
        # problem is counted once per occurrence
        self.report = True

    def _problem(self, *args, occurrence=None, **kwargs):
        """
        Name a problem. `occurrence` identifies the row it was found in, (table, the row's
        values): a row read more than once (as a reference, in the check of a replicated table's
        copies, in the comparison itself), or held by every shard of a replicated table, is
        counted once.
        """
        if not self.report:
            return
        if occurrence is not None:
            key = (args[1], args[2], occurrence)
            if key in self._reported:
                return
            self._reported.add(key)
        self.store.problems.add(*args, **kwargs)

    # -- per-table facts

    def bookkeeping_columns(self, table: str, names) -> list:
        """The bookkeeping columns this table has, in its column order."""
        declared = set(GLOBAL_BOOKKEEPING) | set(self.bookkeeping.get(table, {}))
        return [n for n in names if n in declared]

    def json_columns_of(self, table: str, names) -> list:
        """The JSON columns this table has, in its column order."""
        declared = set(self.json_columns.get(table, {}))
        return [n for n in names if n in declared]

    def _layout(self, shard: int, table: str, names):
        """For each column: how it enters the identity."""
        fks = self.store.foreign_keys(shard, table)
        poly = self.polymorphic.get(table, {})
        types = {c[0]: c[1] for c in self.store.columns(shard, table)}
        bookkeeping = set(self.bookkeeping_columns(table, names))
        json_columns = set(self.json_columns_of(table, names))
        layout = []
        for i, name in enumerate(names):
            if name in bookkeeping:
                continue
            if name in poly and poly[name][0] in names:
                type_column = poly[name][0]
                layout.append(
                    (name, "poly", i, names.index(type_column), poly[name][1])
                )
            elif name in poly:
                self._problem(
                    self.store.name,
                    "unknown type value",
                    f"{table}.{name} is declared polymorphic, but {table} has no column "
                    f"{poly[name][0]}; compared as a plain value",
                )
                layout.append((name, "value", i, None, None))
            elif name in fks:
                layout.append((name, "fk", i, fks[name], None))
            elif name in json_columns:
                layout.append((name, "json", i, None, None))
            elif is_float_type(types.get(name)):
                layout.append((name, "float", i, None, None))
            else:
                layout.append((name, "value", i, None, None))
        return layout

    # -- JSON

    def parse_json(self, table: str, column: str, value, shard: int, occurrence=None):
        """(parsed value, True), or (None, False) for text that is not JSON (a problem)."""
        if value is None:
            return None, True
        if not isinstance(value, (str, bytes, bytearray)):
            self._problem(
                self.store.name,
                "JSON that does not parse",
                f"{table}.{column} holds a {type(value).__name__}, not JSON text; compared as "
                f"a plain value",
                example=f"shard {shard}: {value!r}",
                occurrence=occurrence,
            )
            return None, False
        try:
            return json.loads(value), True
        except ValueError:
            self._problem(
                self.store.name,
                "JSON that does not parse",
                f"{table}.{column} holds text that is not JSON; compared as text",
                example=f"shard {shard}: {str(value)[:80]!r}",
                occurrence=occurrence,
            )
            return None, False

    # -- lookup of a referenced row

    def _lookup(self, shard: int, table: str, column: str, value):
        key = (shard, table, column)
        if key not in self._index:
            index = {}
            if table in self.store.shard_tables[shard]:
                names, cursor = self.store.rows(shard, table)
                if column in names:
                    position = names.index(column)
                    for row in cursor:
                        index[row[position]] = (names, row)
            self._index[key] = index
        return self._index[key].get(value)

    # -- the identity of a row

    def parts(self, shard: int, table: str, names, row, layout=None):
        """
        [(column, canonical value or reference, how, location, near, timings)] for the row. A
        reference
        is ["ref", table, digest hex], and its location is (shard, table, key column, key value)
        of the row it names; one that cannot be resolved is ["unresolved", table].
        """
        if layout is None:
            layout = self._layout(shard, table, names)
        parts = []
        for name, how, i, extra, mapping in layout:
            value = row[i]
            if how in ("value", "float"):
                canonical = canonical_value(value)
                parts.append(
                    (
                        name,
                        canonical,
                        how,
                        None,
                        None if how == "float" else canonical,
                        None,
                    )
                )
            elif how == "json":
                parsed, ok = self.parse_json(table, name, value, shard, (table, row))
                if ok:
                    canonical = ["j", canonical_json(parsed, self.timing_keys)]
                    near = _Skeleton(parsed)
                    timings = json_timings(parsed, self.timing_keys)
                else:
                    canonical = near = canonical_value(value)
                    timings = {}
                parts.append((name, canonical, how, None, near, timings))
            elif how == "fk":
                ref_table, ref_column = extra
                reference = self._reference(
                    shard, table, name, ref_table, ref_column, value, (table, row)
                )
                parts.append(
                    (
                        name,
                        reference,
                        how,
                        (shard, ref_table, ref_column, value),
                        reference,
                        None,
                    )
                )
            else:  # polymorphic
                type_value = row[extra]
                ref_table = mapping.get(type_value)
                if ref_table is None:
                    type_column = names[extra]
                    self._problem(
                        self.store.name,
                        "unknown type value",
                        f"{table}.{type_column} = {type_value!r} maps to no table",
                        example=f"shard {shard}, {name} = {value!r}",
                        occurrence=(table, row),
                    )
                    unmapped = ["unmapped", type_value, canonical_value(value)]
                    parts.append((name, unmapped, how, None, unmapped, None))
                else:
                    reference = self._reference(
                        shard, table, name, ref_table, "serial", value, (table, row)
                    )
                    parts.append(
                        (
                            name,
                            reference,
                            how,
                            (shard, ref_table, "serial", value),
                            reference,
                            None,
                        )
                    )
        return parts

    def _reference(
        self, shard, table, column, ref_table, ref_column, value, occurrence=None
    ):
        if value is None:
            return None
        digest = self.digest_of(shard, ref_table, ref_column, value)
        if digest is None:
            self._problem(
                self.store.name,
                "unresolved reference",
                f"{table}.{column} names a row of {ref_table} that is not on its shard",
                example=f"shard {shard}, {ref_table}.{ref_column} = {value!r}",
                occurrence=occurrence,
            )
            return ["unresolved", ref_table]
        return ["ref", ref_table, digest.hex()]

    def digest_of(self, shard: int, table: str, column: str, value):
        """The digest of the row of `table` whose `column` is `value` on `shard`, or None."""
        key = (shard, table, column, value)
        if key in self._digests:
            return self._digests[key]
        found = self._lookup(shard, table, column, value)
        if found is None:
            return None
        if key in self._active:
            self._problem(
                self.store.name, "cyclic reference", f"{table}: a cycle of references"
            )
            return None
        self._active.add(key)
        try:
            names, row = found
            digest = self.row_digest(shard, table, names, row)
        finally:
            self._active.discard(key)
        self._digests[key] = digest
        return digest

    def row_digest(self, shard, table, names, row, layout=None, parts=None):
        if parts is None:
            parts = self.parts(shard, table, names, row, layout)
        return _digest([table, sorted([p[0], p[1]] for p in parts)])

    def near_key(self, table, parts, matched) -> bytes:
        """
        The digest of the identity without its floats (float columns dropped, a JSON column's
        floats replaced by a bare tag), in which a reference to a row that both stores hold (its
        digest is in `matched`, by table) stays its digest, and a reference to any other row
        becomes that row's own near key, recursively. Two unmatched rows with one near key are a
        near miss: they differ only in floats, their own or their references'. So the children
        of a near-missed parent pair with their counterparts.
        """
        items = []
        for name, value, how, location, near, _ in parts:
            if how == "float":
                continue
            if (
                location is not None
                and isinstance(value, list)
                and value[0] == "ref"
                and value[2] not in matched.get(value[1], ())
            ):
                items.append(
                    [name, ["near", value[1], self._near_key_at(location, matched)]]
                )
            elif isinstance(near, _Skeleton):
                skeleton = canonical_json(near.parsed, self.timing_keys, skeleton=True)
                items.append([name, ["j", skeleton]])
            else:
                items.append([name, near])
        return _digest([table, sorted(items)])

    def _near_key_at(self, location, matched) -> str:
        if location in self._near:
            return self._near[location]
        found = self._lookup(*location)
        if found is None:
            result = "unresolved"
        else:
            names, row = found
            shard, table = location[0], location[1]
            report, self.report = self.report, False
            try:
                parts = self.parts(shard, table, names, row)
            finally:
                self.report = report
            result = self.near_key(table, parts, matched).hex()
        self._near[location] = result
        return result

    # -- physical labels

    def labels(self, shard: int, table: str, names, row, depth=0):
        """The row by its physical labels: {column: value}, a reference as
        {"table": ..., "row": {...}}, bookkeeping columns left out. A JSON column is shown parsed
        and without its timing keys, and only for the row itself, not for a row it references."""
        layout = self._layout(shard, table, names)
        out = {}
        for name, how, i, extra, mapping in layout:
            value = row[i]
            if how in ("value", "float"):
                out[name] = value
                continue
            if how == "json":
                if depth > 0:
                    continue
                report, self.report = self.report, False
                try:
                    parsed, ok = self.parse_json(table, name, value, shard)
                finally:
                    self.report = report
                out[name] = (
                    json_without_timings(parsed, self.timing_keys) if ok else value
                )
                continue
            if how == "fk":
                ref_table, ref_column = extra
            else:
                ref_table, ref_column = mapping.get(row[extra]), "serial"
                if ref_table is None:
                    out[name] = {"unmapped type": row[extra], "serial": value}
                    continue
            if value is None:
                out[name] = None
                continue
            out[name] = self._ref_labels(shard, ref_table, ref_column, value, depth)
        return out

    def _ref_labels(self, shard, table, column, value, depth):
        key = (shard, table, column, value)
        if key in self._labels:
            return self._labels[key]
        found = self._lookup(shard, table, column, value)
        if found is None or depth > 16:
            result = {"table": table, "unresolved": value}
        else:
            names, row = found
            result = {
                "table": table,
                "row": self.labels(shard, table, names, row, depth + 1),
            }
        self._labels[key] = result
        return result


# ---------------------------------------------------------------------------
# comparing


def _bookkeeping_names(ids: Identities, table: str, names) -> list:
    """The bookkeeping columns compared between matched rows (all but serial), then the JSON
    columns, whose timing keys are compared."""
    bk = [n for n in ids.bookkeeping_columns(table, names) if n != "serial"]
    return bk + [f"{n}:timings" for n in ids.json_columns_of(table, names)]


def _bookkeeping_values(names, row, parts, bk_names) -> tuple:
    """A row's bookkeeping tuple: each bookkeeping column's value, then each JSON column's
    {path: value} of its timing keys, taken from the row's identity parts."""
    timings = {p[0]: p[5] for p in parts if p[2] == "json"}
    out = []
    for name in bk_names:
        if name.endswith(":timings"):
            out.append(timings.get(name[: -len(":timings")]) or {})
        else:
            out.append(row[names.index(name)])
    return tuple(out)


def _collect(ids: Identities, table: str, shards, keep_bookkeeping=True, memo=True):
    """
    Stream the table's rows on the given shards: a Counter of digests, and for each digest the
    list of its rows' bookkeeping tuples (without serial; a JSON column's timing keys as a
    {path: value} dict). With `memo`, each row's digest is memoised by its serial, for the rows
    that reference it; a table that nothing references (a value table) is not memoised.
    """
    counter = Counter()
    bookkeeping = defaultdict(list)
    store = ids.store
    bk_names = None
    for shard in shards:
        names, cursor = store.rows(shard, table)
        layout = ids._layout(shard, table, names)
        bk = _bookkeeping_names(ids, table, names)
        bk_names = bk
        has_serial = memo and "serial" in names
        serial_position = names.index("serial") if has_serial else None
        for row in cursor:
            parts = ids.parts(shard, table, names, row, layout)
            digest = ids.row_digest(shard, table, names, row, parts=parts)
            counter[digest] += 1
            if has_serial:
                ids._digests[(shard, table, "serial", row[serial_position])] = digest
            if keep_bookkeeping and bk:
                bookkeeping[digest].append(_bookkeeping_values(names, row, parts, bk))
    return counter, bookkeeping, bk_names or []


def _rows_with(ids: Identities, table: str, shards, wanted: Counter):
    """The rows whose digests are in `wanted`, as many of each as wanted."""
    remaining = Counter(wanted)
    out = []
    report, ids.report = ids.report, False
    try:
        for shard in shards:
            names, cursor = ids.store.rows(shard, table)
            layout = ids._layout(shard, table, names)
            for row in cursor:
                parts = ids.parts(shard, table, names, row, layout)
                digest = ids.row_digest(shard, table, names, row, parts=parts)
                if remaining[digest] > 0:
                    remaining[digest] -= 1
                    out.append(
                        {
                            "parts": parts,
                            "labels": ids.labels(shard, table, names, row),
                            "values": {names[i]: row[i] for i in range(len(names))},
                            "shard": shard,
                        }
                    )
    finally:
        ids.report = report
    return out


def _relative_difference(a, b):
    if not isinstance(a, float) or not isinstance(b, float):
        return None
    if math.isnan(a) or math.isnan(b):
        return None
    scale = max(abs(a), abs(b))
    if scale == 0.0:
        return 0.0
    return abs(a - b) / scale


def _float_hex(value):
    return value.hex() if isinstance(value, float) else None


def _difference(column, a, b):
    return {
        "column": column,
        "a": a,
        "b": b,
        "a_hex": _float_hex(a),
        "b_hex": _float_hex(b),
        "relative_difference": _relative_difference(a, b),
    }


def _pair_near_misses(table, ids_a, ids_b, a_rows, b_rows, matched):
    """
    Pair A-only and B-only rows with one near key (`Identities.near_key`). Returns (pairs,
    unpaired A rows, unpaired B rows). Each pair lists its own floats that differ, in a column
    or at a path inside a JSON column, with both values, and the references through which it
    differs (those whose rows differ).
    """
    by_key_a = defaultdict(list)
    by_key_b = defaultdict(list)
    for row in a_rows:
        by_key_a[ids_a.near_key(table, row["parts"], matched)].append(row)
    for row in b_rows:
        by_key_b[ids_b.near_key(table, row["parts"], matched)].append(row)

    timing_keys = ids_a.timing_keys
    pairs, only_a, only_b = [], [], []
    for key in list(by_key_a) + [k for k in by_key_b if k not in by_key_a]:
        list_a = sorted(by_key_a.get(key, []), key=lambda r: _sort_key(r["parts"]))
        list_b = sorted(by_key_b.get(key, []), key=lambda r: _sort_key(r["parts"]))
        n = min(len(list_a), len(list_b))
        for row_a, row_b in zip(list_a[:n], list_b[:n]):
            differing = []
            through = []
            parts_b = {p[0]: p[1] for p in row_b["parts"]}
            for name, value, how, location, _, _ in row_a["parts"]:
                if parts_b.get(name) == value:
                    continue
                if how == "float":
                    differing.append(
                        _difference(
                            name, row_a["values"].get(name), row_b["values"].get(name)
                        )
                    )
                elif how == "json":
                    parsed_a = json.loads(row_a["values"][name])
                    parsed_b = json.loads(row_b["values"][name])
                    for path, va, vb in json_float_differences(
                        parsed_a, parsed_b, timing_keys
                    ):
                        differing.append(_difference(f"{name}{path}", va, vb))
                elif location is not None:
                    through.append(name)
            pairs.append(
                {
                    "a": row_a["labels"],
                    "b": row_b["labels"],
                    "differing": differing,
                    "through_references": through,
                }
            )
        only_a.extend(list_a[n:])
        only_b.extend(list_b[n:])
    return pairs, only_a, only_b


def _referenced_tables(store: Store, polymorphic) -> set:
    """Every table a foreign key or a declared polymorphic reference of the store names."""
    out = set()
    for table in store.client_tables:
        shard = store.lowest_shard(table)
        out |= {ref for ref, _ in store.foreign_keys(shard, table).values()}
    for pairs in polymorphic.values():
        for _, mapping in pairs.values():
            out |= set(mapping.values())
    return out


def _compare_bookkeeping(table, names, bk_a, bk_b, matched: Counter, result):
    """Count, per bookkeeping column (and per timing key's path inside a JSON column), the
    matched rows on which it differs."""
    counts = Counter()
    for digest in matched:
        rows_a = sorted(bk_a.get(digest, []), key=_sort_key)
        rows_b = sorted(bk_b.get(digest, []), key=_sort_key)
        for tuple_a, tuple_b in zip(rows_a, rows_b):
            for name, va, vb in zip(names, tuple_a, tuple_b):
                if name.endswith(":timings"):
                    column = name[: -len(":timings")]
                    for path in sorted(set(va) | set(vb)):
                        if va.get(path, _MISSING) != vb.get(path, _MISSING):
                            counts[f"{column}{path}"] += 1
                elif va != vb:
                    counts[name] += 1
    if counts:
        result[table] = dict(sorted(counts.items()))


_MISSING = object()


def _check_replicated_copies(ids: Identities, table: str, problems: _Problems):
    """Each shard's copy of a replicated table, checked equal to the lowest shard's."""
    shards = ids.store.shards_holding(table)
    if len(ids.store.shard_tables) != len(shards):
        missing = [
            ids.store.shard_files[s].name
            for s in range(len(ids.store.shard_tables))
            if s not in shards
        ]
        problems.add(
            ids.store.name,
            "replicated copies differ",
            f"{table}: no copy on {missing}",
        )
    reference = None
    for shard in shards:
        if reference is None:
            # the lowest shard's copy is read again, and counted, by the comparison itself
            report, ids.report = ids.report, False
            try:
                counter, _, _ = _collect(ids, table, [shard], keep_bookkeeping=False)
            finally:
                ids.report = report
            reference = (shard, counter)
            continue
        counter, _, _ = _collect(ids, table, [shard], keep_bookkeeping=False)
        if counter != reference[1]:
            only_ref = sum((reference[1] - counter).values())
            only_here = sum((counter - reference[1]).values())
            problems.add(
                ids.store.name,
                "replicated copies differ",
                f"{table}: the copy on {ids.store.shard_files[shard].name} differs from the "
                f"copy on {ids.store.shard_files[reference[0]].name} ({only_ref} row(s) only "
                f"in the latter, {only_here} only in the former)",
            )
    return reference


def compare_stores(
    path_a,
    path_b,
    bookkeeping=None,
    polymorphic=None,
    json_columns=None,
    timing_keys=None,
) -> dict:
    """
    Compare the stores whose primaries are `path_a` and `path_b`. Returns the result as a dict
    (see `format_result`); raises StoreReadError if either cannot be read. The maps default to
    this module's StochasticInstanton constants.
    """
    bookkeeping = BOOKKEEPING_COLUMNS if bookkeeping is None else bookkeeping
    polymorphic = POLYMORPHIC_REFERENCES if polymorphic is None else polymorphic
    json_columns = JSON_COLUMNS if json_columns is None else json_columns
    timing_keys = TIMING_KEYS if timing_keys is None else timing_keys

    problems = _Problems()
    notes = []
    store_a = Store(path_a, "A", problems, notes)
    try:
        store_b = Store(path_b, "B", problems, notes)
    except StoreReadError:
        store_a.close()
        raise

    try:
        ids_a = Identities(store_a, bookkeeping, polymorphic, json_columns, timing_keys)
        ids_b = Identities(store_b, bookkeeping, polymorphic, json_columns, timing_keys)

        tables = sorted(set(store_a.client_tables) | set(store_b.client_tables))
        result_tables = {}
        bookkeeping_differences = {}
        different = False

        # the tables some foreign key or polymorphic reference names
        referenced = _referenced_tables(store_a, polymorphic) | _referenced_tables(
            store_b, polymorphic
        )

        # pass 1: every table's multiset of identities, in each store
        collected = {}
        for table in tables:
            entry = {}
            sides = []
            for ids, store, label in ((ids_a, store_a, "a"), (ids_b, store_b, "b")):
                if table not in store.client_tables:
                    entry[f"kind_{label}"] = None
                    notes.append(f"{store.name}: holds no table {table}")
                    sides.append((Counter(), {}, [], []))
                    continue
                kind = store.kind(table)
                entry[f"kind_{label}"] = kind
                if not store.listed(table):
                    notes.append(
                        f"{store.name}: {table} is on the shards but in neither of the "
                        f"primary's table lists; compared as {kind}"
                        + (
                            " (its rows taken from every shard)"
                            if kind == "sharded"
                            else " (its lowest shard's copy)"
                        )
                    )
                if kind == "replicated":
                    _check_replicated_copies(ids, table, problems)
                    shards = [store.lowest_shard(table)]
                else:
                    shards = store.shards_holding(table)
                counter, bk, bk_names = _collect(
                    ids, table, shards, memo=table in referenced
                )
                sides.append((counter, bk, bk_names, shards))

            if (
                entry["kind_a"] is not None
                and entry["kind_b"] is not None
                and entry["kind_a"] != entry["kind_b"]
            ):
                problems.add(
                    "A/B",
                    "classified differently",
                    f"{table} is {entry['kind_a']} in A and {entry['kind_b']} in B",
                )
            collected[table] = (entry, sides)

        # the rows both stores hold, of each table some row names
        matched_digests = {}
        for table in referenced:
            if table in collected:
                sides = collected[table][1]
                matched_digests[table] = {
                    digest.hex() for digest in (sides[0][0] & sides[1][0])
                }

        # pass 2: the tables that differ, row by row
        for table in tables:
            entry, sides = collected[table]
            counter_a, bk_a, bk_names_a, shards_a = sides[0]
            counter_b, bk_b, bk_names_b, shards_b = sides[1]
            matched = counter_a & counter_b
            a_only = counter_a - counter_b
            b_only = counter_b - counter_a
            entry["matched"] = sum(matched.values())
            entry["a_only"] = sum(a_only.values())
            entry["b_only"] = sum(b_only.values())
            entry["near_misses"] = []
            entry["rows_a_only"] = []
            entry["rows_b_only"] = []

            if bk_names_a and bk_names_a == bk_names_b:
                _compare_bookkeeping(
                    table, bk_names_a, bk_a, bk_b, matched, bookkeeping_differences
                )

            if a_only or b_only:
                different = True
                rows_a = _rows_with(ids_a, table, shards_a, a_only) if a_only else []
                rows_b = _rows_with(ids_b, table, shards_b, b_only) if b_only else []
                pairs, only_a, only_b = _pair_near_misses(
                    table, ids_a, ids_b, rows_a, rows_b, matched_digests
                )
                entry["near_misses"] = pairs
                entry["rows_a_only"] = [row["labels"] for row in only_a]
                entry["rows_b_only"] = [row["labels"] for row in only_b]

            result_tables[table] = entry

        problem_list = problems.as_list()
        if problem_list:
            different = True

        return {
            "a": {
                "primary": str(store_a.primary),
                "shards": [str(p) for p in store_a.shard_files],
            },
            "b": {
                "primary": str(store_b.primary),
                "shards": [str(p) for p in store_b.shard_files],
            },
            "tables": result_tables,
            "bookkeeping_differences": bookkeeping_differences,
            "problems": problem_list,
            "notes": sorted(set(notes)),
            "equal": not different,
        }
    except sqlite3.Error as e:
        raise StoreReadError(f"cannot read a store: {e}") from e
    finally:
        store_a.close()
        store_b.close()


# ---------------------------------------------------------------------------
# rendering


def _clip(text: str) -> str:
    if len(text) <= _RENDER_WIDTH:
        return text
    return text[: _RENDER_WIDTH - 3] + "..."


def render_value(value) -> str:
    if isinstance(value, dict):
        if "row" in value and "table" in value:
            inner = ", ".join(
                f"{k}={render_value(v)}" for k, v in sorted(value["row"].items())
            )
            return f"{value['table']}{{{inner}}}"
        if "unresolved" in value and "table" in value:
            return f"{value['table']}{{unresolved: {value['unresolved']!r}}}"
        return _clip(json.dumps(value, sort_keys=True, default=repr))
    if isinstance(value, list):
        return _clip(json.dumps(value, default=repr))
    return _clip(repr(value))


def render_row(table: str, labels: dict) -> str:
    inner = ", ".join(f"{k}={render_value(v)}" for k, v in sorted(labels.items()))
    return f"{table}{{{inner}}}"


def format_result(result: dict, max_rows: int = 20) -> str:
    lines = [
        f"compare_stores: A = {result['a']['primary']} ({len(result['a']['shards'])} shards)",
        f"                B = {result['b']['primary']} ({len(result['b']['shards'])} shards)",
        "",
        "tables:",
    ]
    width = max([len(t) for t in result["tables"]] + [5])
    for table, entry in result["tables"].items():
        kind = entry["kind_a"] or "-"
        if entry["kind_b"] != entry["kind_a"]:
            kind = f"{entry['kind_a'] or '-'}/{entry['kind_b'] or '-'}"
        flag = "" if entry["a_only"] == 0 and entry["b_only"] == 0 else "   <-- differs"
        lines.append(
            f"  {table:<{width}}  {kind:<10}  matched {entry['matched']:>8}  "
            f"A only {entry['a_only']:>6}  B only {entry['b_only']:>6}{flag}"
        )

    differing = [t for t, e in result["tables"].items() if e["a_only"] or e["b_only"]]
    if differing:
        lines += ["", "differences:"]
    for table in differing:
        entry = result["tables"][table]
        lines.append(f"  {table}:")
        own = [p for p in entry["near_misses"] if p["differing"]]
        inherited = [p for p in entry["near_misses"] if not p["differing"]]
        if own:
            lines.append(f"    near misses ({len(own)}):")
            for pair in own[:max_rows]:
                lines.append(f"      A: {render_row(table, pair['a'])}")
                for d in pair["differing"]:
                    rel = d["relative_difference"]
                    rel_text = "n/a" if rel is None else f"{rel:.3e}"
                    lines.append(
                        f"        {d['column']}: A = {d['a']!r} ({d['a_hex']}), "
                        f"B = {d['b']!r} ({d['b_hex']}), relative difference {rel_text}"
                    )
                if pair["through_references"]:
                    lines.append(
                        f"        and through {', '.join(pair['through_references'])}"
                    )
            if len(own) > max_rows:
                lines.append(f"      ... and {len(own) - max_rows} more (see --json)")
        if inherited:
            through = sorted({c for p in inherited for c in p["through_references"]})
            lines.append(
                f"    {len(inherited)} paired row(s) whose own columns agree, differing only "
                f"through {', '.join(through)} (see --json)"
            )
        for key, name in (("rows_a_only", "A"), ("rows_b_only", "B")):
            rows = entry[key]
            if not rows:
                continue
            lines.append(f"    in {name} only ({len(rows)}):")
            for row in rows[:max_rows]:
                lines.append(f"      {render_row(table, row)}")
            if len(rows) > max_rows:
                lines.append(f"      ... and {len(rows) - max_rows} more (see --json)")

    lines += [
        "",
        "bookkeeping that differs between matched rows (not compared):",
    ]
    if result["bookkeeping_differences"]:
        for table, counts in result["bookkeeping_differences"].items():
            for column, n in counts.items():
                lines.append(f"  {table}.{column}: {n} matched row(s)")
    else:
        lines.append("  none")

    if result["notes"]:
        lines += ["", "notes:"]
        lines += [f"  - {note}" for note in result["notes"]]

    lines += ["", "problems:"]
    if result["problems"]:
        for item in result["problems"]:
            lines.append(
                f"  - [{item['store']}] {item['kind']}: {item['message']} "
                f"(x{item['count']})"
            )
            for example in item["examples"]:
                lines.append(f"      e.g. {example}")
    else:
        lines.append("  none")

    lines += [
        "",
        (
            "RESULT: equal"
            if result["equal"]
            else "RESULT: the stores differ, or a problem was named"
        ),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# schema snapshots


def schema_snapshot(path) -> dict:
    """The schema of each client table on the store's lowest shard, as sets in sorted lists."""
    problems = _Problems()
    store = Store(path, "store", problems, [])
    try:
        conn = store.connections[0]
        tables = {}
        for table in sorted(store.shard_tables[0]):
            columns = sorted(
                [name, declared, not_null, pk > 0]
                for name, declared, not_null, pk in store.columns(0, table)
            )
            indices = []
            for row in conn.execute(f'pragma index_list("{table}")'):
                index_name, unique = row[1], bool(row[2])
                cols = [
                    r[2]
                    for r in sorted(conn.execute(f'pragma index_info("{index_name}")'))
                ]
                indices.append([cols, unique])
            groups = defaultdict(list)
            for row in conn.execute(f'pragma foreign_key_list("{table}")'):
                groups[row[0]].append((row[1], row[3], row[2], row[4]))
            fks = []
            for parts in groups.values():
                parts.sort()
                fks.append([[p[1] for p in parts], parts[0][2], [p[3] for p in parts]])
            tables[table] = {
                "columns": columns,
                "indices": sorted(indices),
                "foreign_keys": sorted(fks, key=_sort_key),
            }
        return {
            "format": SNAPSHOT_FORMAT,
            "version": SNAPSHOT_VERSION,
            "source": str(store.primary),
            "tables": tables,
        }
    except sqlite3.Error as e:
        raise StoreReadError(f'cannot read the schema of "{store.primary}": {e}') from e
    finally:
        store.close()


def compare_schemas(snapshot: dict, reference: dict) -> list:
    """Each difference between a store's snapshot and a reference snapshot, as a line."""
    out = []
    tables_s = snapshot["tables"]
    tables_r = reference["tables"]
    for table in sorted(set(tables_r) - set(tables_s)):
        out.append(f"{table}: in the reference only")
    for table in sorted(set(tables_s) - set(tables_r)):
        out.append(f"{table}: in the store only")
    for table in sorted(set(tables_s) & set(tables_r)):
        s, r = tables_s[table], tables_r[table]
        cols_s = {c[0]: c[1:] for c in s["columns"]}
        cols_r = {c[0]: c[1:] for c in r["columns"]}
        for name in sorted(set(cols_r) - set(cols_s)):
            out.append(f"{table}: column {name} {cols_r[name]} in the reference only")
        for name in sorted(set(cols_s) - set(cols_r)):
            out.append(f"{table}: column {name} {cols_s[name]} in the store only")
        for name in sorted(set(cols_s) & set(cols_r)):
            if list(cols_s[name]) != list(cols_r[name]):
                out.append(
                    f"{table}: column {name} is [type, not null, primary key] = "
                    f"{list(cols_s[name])} in the store, {list(cols_r[name])} in the reference"
                )
        for key, what in (("indices", "index"), ("foreign_keys", "foreign key")):
            set_s = {json.dumps(x) for x in s[key]}
            set_r = {json.dumps(x) for x in r[key]}
            for item in sorted(set_r - set_s):
                out.append(f"{table}: {what} {item} in the reference only")
            for item in sorted(set_s - set_r):
                out.append(f"{table}: {what} {item} in the store only")
    return out


# ---------------------------------------------------------------------------
# command line


def _parser():
    parser = argparse.ArgumentParser(
        prog="compare_stores.py",
        description="Compare two StochasticInstanton sharded stores by value, read-only "
        "through sqlite3; or write or compare a store's schema snapshot. Exit 0: equal; 1: they "
        "differ; 2: a store cannot be read.",
    )
    parser.add_argument(
        "stores", nargs="*", metavar="PRIMARY", help="A.sqlite B.sqlite"
    )
    parser.add_argument("--json", metavar="OUT", help="also write the full result here")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=20,
        metavar="N",
        help="rows listed per table and list in the human output (default 20; --json has all)",
    )
    parser.add_argument(
        "--snapshot", metavar="PRIMARY", help="write this store's schema snapshot"
    )
    parser.add_argument(
        "--out", metavar="F", help="with --snapshot: the file (default: stdout)"
    )
    parser.add_argument(
        "--schema", metavar="PRIMARY", help="compare this store's schema with --against"
    )
    parser.add_argument("--against", metavar="F", help="with --schema: a snapshot file")
    return parser


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)

    try:
        if args.snapshot is not None:
            if args.stores or args.schema or args.against or args.json:
                parser.error("--snapshot takes one store and optionally --out")
            text = json.dumps(schema_snapshot(args.snapshot), indent=2, sort_keys=True)
            if args.out:
                Path(args.out).write_text(text + "\n")
                print(f"compare_stores: schema snapshot written to {args.out}")
            else:
                print(text)
            return EXIT_EQUAL

        if args.schema is not None:
            if args.stores or args.against is None or args.out or args.json:
                parser.error("--schema takes one store and --against F")
            try:
                reference = json.loads(Path(args.against).read_text())
            except (OSError, ValueError) as e:
                print(
                    f"!! compare_stores: cannot read the snapshot {args.against}: {e}"
                )
                return EXIT_UNREADABLE
            if (
                not isinstance(reference, dict)
                or reference.get("format") != SNAPSHOT_FORMAT
            ):
                print(f"!! compare_stores: {args.against} is not a schema snapshot")
                return EXIT_UNREADABLE
            differences = compare_schemas(schema_snapshot(args.schema), reference)
            print(f"compare_stores: schema of {args.schema} against {args.against}")
            for line in differences:
                print(f"  {line}")
            print(
                "RESULT: the schemas agree"
                if not differences
                else f"RESULT: {len(differences)} difference(s)"
            )
            return EXIT_DIFFERENT if differences else EXIT_EQUAL

        if len(args.stores) != 2 or args.out or args.against:
            parser.error("give two primaries, A.sqlite B.sqlite")
        result = compare_stores(args.stores[0], args.stores[1])
    except StoreReadError as e:
        print(f"!! compare_stores: {e}")
        return EXIT_UNREADABLE

    print(format_result(result, max_rows=args.max_rows))
    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2, default=repr) + "\n")
    return EXIT_EQUAL if result["equal"] else EXIT_DIFFERENT


if __name__ == "__main__":
    sys.exit(main())
