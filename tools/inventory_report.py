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
The datastore inventory report: ``main.py --inventory`` (dk-and-rpk-migration prompt 10).

``format_inventory_report(inventory, db_name, verbose=False)`` renders the ``StoreInventory`` that
``datastorekit.store_inventory.read_inventory`` returns, as one string. It reads nothing from a store
and opens no file: whatever it prints is in the inventory it is given, which was read read-only,
with no Ray. Which key leaves are floats it learns from the tables the registry declares
(``build_schema`` over ``config.datastore.factories``, in memory, column types only). It is
modelled on SecondaryGWKit's and ChamPBH's reports of the same name, read in those repositories;
nothing is imported from either.

**What it shows.** A title naming ``db_name`` as given; the shards; the number of records and
classes; the number of named problems ("none" when there are none). Then one section per class, in
the order of ``SECTIONS`` (today's report's order first, then the classes it never showed), and any
class of the inventory that ``SECTIONS`` does not name under "Other classes", so that nothing the
inventory holds goes unprinted. Each section's title names its class, and whether it is replicated
or sharded.

- **A class whose key is one leaf** (a parameter, a quantity, an e-fold value, a tolerance, a
  redshift, a version or tag label, a cosmology's name): its values, sorted, as
  ``N value(s): [ ... ]``, or ``no values committed``. A float is printed to six significant figures
  (``.6g``), with the unit its stored column is in, read from the column's suffix (``value_PlanckMass``
  is in ``PlanckMass``: ``.claude/rules/datastore-units.md``), so no units object is needed. A
  tolerance, stored as ``log10_tol``, is printed as the tolerance itself.
- **Any other class** (the potentials, the diffusion model, the solvers): its records, each by its
  physical labels, ``:: field=value, ...``.
- **A compute target** (``InflatonTrajectory``, ``FullInstanton``, ``SlowRollInstanton``,
  ``CompactionFunction``, ``GradientCoupledInstanton``): the earliest and latest timestamp of the
  class (the inventory carries one range per class, not one per validated group), the number of
  value rows its spec counts, a ``common to every record`` line, and then the validated and the
  unvalidated records, each group with its count, each record by the physical labels that vary
  across the class and its value-row count.
- **Every named problem, whole**, one to a line under its class (``!! <problem>``). Problems are
  never truncated, by ``verbose`` or otherwise.

**Physical labels.** A key's float leaf is ``float.hex`` of the stored value; it is printed as the
number. A reference to a parent row is printed by the parent's own key, never by a digest or a
serial: a parent whose key is one leaf by its value (``delta_Nstar=0.5``, ``phi0=15 PlanckMass``),
and any other by its class and the fields of its key that vary across its own class
(``trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05
PlanckMass))``; a trajectory always shows its ``phi0`` and its potential). A polymorphic parent is
printed with its class, which its type leaf names, so the type leaf itself is not printed; a NULL
nullable parent is ``none``. A key field whose printed value is the same for every record of a
class of two or more records is printed once, on that class's ``common to every record`` line, and
left off its record lines; so two different records never print as one line, except where their
floats agree to six figures. The stored ``label`` and ``version`` of a compute target are not in any
key (no lookup matches them), so they are not in the inventory and not shown.

**Truncation.** As today's report: a list of more than ``VALUE_LIMIT`` values shows its first and
last ``VALUE_ENDS``, and a group of more than ``RECORD_LIMIT`` records its first and last
``RECORD_ENDS``, each with a line saying how many are not shown. With ``verbose``
(``main.py --show-all``) nothing is truncated.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import sqlalchemy as sqla

from datastorekit.store_inventory import ClassInventory, Record, StoreInventory

# a list of more than this many values shows its first and last VALUE_ENDS, unless verbose
VALUE_LIMIT = 20
VALUE_ENDS = 10

# a validated (or unvalidated) group of more than this many records shows its first and last
# RECORD_ENDS, unless verbose
RECORD_LIMIT = 10
RECORD_ENDS = 5

# how each section is rendered
VALUES = "values"
RECORDS = "records"
COMPUTE = "compute"

# the sections, in order: today's report's thirteen first, in its order and with its titles, then
# the classes it never showed. A class of the inventory that is not named here is reported under
# "Other classes", so that nothing the inventory holds goes unprinted
SECTIONS: List[Tuple[str, str, str]] = [
    ("Delta N★ values", "delta_Nstar", VALUES),
    ("N_init values", "N_init", VALUES),
    ("N_final values", "N_final", VALUES),
    ("phi_0 values", "phi_value", VALUES),
    ("pi_0 values", "pi_value", VALUES),
    ("Inflaton mass values", "inflaton_mass", VALUES),
    ("Quartic coupling values", "quartic_coupling", VALUES),
    ("E-fold sample values", "efold_value", VALUES),
    ("Inflaton trajectories", "InflatonTrajectory", COMPUTE),
    ("Full MSR instantons", "FullInstanton", COMPUTE),
    ("Slow-roll instantons", "SlowRollInstanton", COMPUTE),
    ("Compaction functions", "CompactionFunction", COMPUTE),
    (
        "Gradient-coupled (onion model) instantons",
        "GradientCoupledInstanton",
        COMPUTE,
    ),
    ("Quadratic potentials", "QuadraticPotential", RECORDS),
    ("Quartic potentials", "QuarticPotential", RECORDS),
    ("Diffusion models", "MasslessDecoupledDiffusion", RECORDS),
    ("Collocation points", "n_collocation_points", VALUES),
    ("Regularization alpha values", "alpha_regularization", VALUES),
    ("Tolerances", "tolerance", VALUES),
    ("Cosmological parameters", "CosmologicalParams", VALUES),
    ("Redshifts", "redshift", VALUES),
    ("Integration solvers", "IntegrationSolver", RECORDS),
    ("Version labels", "version", VALUES),
    ("Store tags", "store_tag", VALUES),
]

# the order in which a record's key fields are printed: these first, then the rest in key order
FIELD_ORDER = (
    "delta_Nstar",
    "N_init",
    "N_final",
    "n_collocation_points",
    "alpha_regularization",
    "phi0",
    "pi0",
    "potential",
    "m",
    "lambda_",
    "trajectory",
    "full_instanton",
    "slow_roll_instanton",
    "cosmo",
    "diffusion_model",
    "atol",
    "rtol",
)

# the key fields a parent of this class always shows, beside those that vary across its class
ALWAYS_SHOWN: Dict[str, Tuple[str, ...]] = {
    "InflatonTrajectory": ("phi0", "potential"),
}

_INDENT = "      "
_RECORD_INDENT = "         "


def _float_columns() -> Dict[str, frozenset]:
    """Each table of the registry, mapped to the names of its columns the schema types as floats.
    Built in memory from the registry; no store is opened."""
    from datastorekit.SQL.schema import build_schema

    from config.datastore import factories

    tables = build_schema(sqla.MetaData(), factories).tables
    return {
        name: frozenset(c.name for c in table.columns if isinstance(c.type, sqla.Float))
        for name, table in tables.items()
    }


def _plural(n: int, word: str) -> str:
    if n == 1:
        return f"{n:,} {word}"
    return f"{n:,} {word}" + ("es" if word.endswith("s") else "s")


def _timestamp(value: Optional[datetime]) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value is not None else "?"


def _truncated(
    items: Sequence[str], verbose: bool, limit: int, ends: int, what: str
) -> List[str]:
    """``items`` whole when ``verbose`` or no more than ``limit``; otherwise the first and last
    ``ends``, with an item saying how many are not shown."""
    if verbose or len(items) <= limit:
        return list(items)
    hidden = len(items) - 2 * ends
    return (
        list(items[:ends])
        + [f"... {_plural(hidden, what)} not shown (--show-all shows every one) ..."]
        + list(items[-ends:])
    )


class _Renderer:
    """Renders the records of one ``StoreInventory`` by their physical labels."""

    def __init__(self, inventory: StoreInventory):
        self.inventory = inventory
        self.floats = _float_columns()
        # class -> reference digest -> the records it names
        self._index: Dict[str, Dict[str, List[Record]]] = {}
        # class -> the key fields whose printed value varies across its records
        self._varying: Dict[str, Tuple[str, ...]] = {}
        # (class, record, field) -> printed value
        self._text: Dict[Tuple[str, str, str], str] = {}

    def cls(self, name: str) -> ClassInventory:
        return self.inventory[name]

    # --- parents -------------------------------------------------------------------------------

    def find(self, of: str, reference: str) -> List[Record]:
        if of not in self.inventory.classes:
            return []
        if of not in self._index:
            index: Dict[str, List[Record]] = {}
            for record in self.cls(of).records:
                index.setdefault(self.inventory.digest_of(of, record), []).append(
                    record
                )
            self._index[of] = index
        return self._index[of].get(reference, [])

    def parent(
        self, name: str, record: Record, field: str
    ) -> Tuple[Optional[str], Optional[Record], str]:
        """(the parent's class, its record or None, and the text to print when there is none)."""
        value = record.key[field]
        if value is None:
            return None, None, "none"
        of = self.cls(name).parent_class(field, record.key)
        if of is None:
            return None, None, "<a reference to no class of the inventory>"
        found = self.find(of, value)
        if len(found) != 1:
            return of, None, f"<{of} reference resolving to {len(found)} records>"
        return of, found[0], ""

    # --- fields --------------------------------------------------------------------------------

    def type_leaves(self, name: str) -> frozenset:
        """The leaves that name a polymorphic parent's class: printed through the parent."""
        return frozenset(column for column, _ in self.cls(name).parent_types.values())

    def fields(self, name: str, record: Record) -> List[str]:
        """A record's key fields as printed: FIELD_ORDER first, then the rest in key order, less
        the type leaves of its polymorphic parents."""
        hidden = self.type_leaves(name)
        present = [f for f in record.key if f not in hidden]
        first = [f for f in FIELD_ORDER if f in present]
        return first + [f for f in present if f not in first]

    def is_float(self, name: str, field: str) -> bool:
        return field in self.floats.get(name, frozenset())

    def leaf_text(self, name: str, field: str, value: Any) -> str:
        if value is None:
            return "none"
        if self.is_float(name, field):
            number = float.fromhex(value)
            if name == "tolerance" and field == "log10_tol":
                return f"{10.0**number:.6g}"
            text = f"{number:.6g}"
            if field.startswith("value_"):
                text += f" {field[len('value_') :]}"
            return text
        return str(value)

    def leaf_sort(self, name: str, field: str, value: Any) -> tuple:
        if value is None:
            return (0,)
        if self.is_float(name, field):
            return (1, float.fromhex(value))
        if isinstance(value, (bool, int, float)):
            return (1, float(value))
        return (2, str(value))

    def text(self, name: str, record: Record, field: str) -> str:
        """The printed value of key field ``field`` of ``record``, a record of class ``name``."""
        memo = (name, record.canonical_json(), field)
        if memo not in self._text:
            if field in self.cls(name).parents:
                self._text[memo] = self.ref_text(name, record, field)
            else:
                self._text[memo] = self.leaf_text(name, field, record.key[field])
        return self._text[memo]

    def sort(self, name: str, record: Record, field: str) -> tuple:
        if field in self.cls(name).parents:
            of, parent, _ = self.parent(name, record, field)
            if parent is None:
                return (0,) if record.key[field] is None else (9,)
            return (3, of, self.record_sort(of, parent, self.fields(of, parent)))
        return self.leaf_sort(name, field, record.key[field])

    def record_sort(self, name: str, record: Record, fields: Sequence[str]) -> tuple:
        return tuple(self.sort(name, record, f) for f in fields) + (
            record.canonical_json(),
        )

    def varying(self, name: str) -> Tuple[str, ...]:
        """The key fields whose printed value is not the same for every record of class ``name``."""
        if name not in self._varying:
            records = self.cls(name).records
            fields: List[str] = []
            for record in records:
                for f in self.fields(name, record):
                    if f not in fields:
                        fields.append(f)
            self._varying[name] = tuple(
                f
                for f in fields
                if len({self.text(name, r, f) if f in r.key else None for r in records})
                > 1
            )
        return self._varying[name]

    def ref_text(self, name: str, record: Record, field: str) -> str:
        """A parent by its own key: a one-leaf key by its value; any other as
        ``Class(field=value, ...)``, by the fields that vary across its class (with those
        ``ALWAYS_SHOWN``), or by its whole key where none vary."""
        of, parent, why = self.parent(name, record, field)
        if parent is None:
            return why
        own = self.fields(of, parent)
        polymorphic = field in self.cls(name).parent_types
        if len(own) == 0:
            return of
        if len(own) == 1 and own[0] not in self.cls(of).parents and not polymorphic:
            return self.text(of, parent, own[0])
        varying = set(self.varying(of)) | set(ALWAYS_SHOWN.get(of, ()))
        shown = [f for f in own if f in varying] or own
        return (
            f"{of}(" + ", ".join(f"{f}={self.text(of, parent, f)}" for f in shown) + ")"
        )

    def record_text(self, name: str, record: Record, fields: Sequence[str]) -> str:
        if len(fields) == 0:
            return "(no key fields)" if len(record.key) == 0 else "(as the common line)"
        return ", ".join(f"{f}={self.text(name, record, f)}" for f in fields)


def _values_lines(renderer: _Renderer, name: str, verbose: bool) -> List[str]:
    """A class whose key is one leaf: its values, sorted, or "no values committed"."""
    cls = renderer.cls(name)
    if cls.count == 0:
        return [f"{_INDENT}no values committed"]
    one_leaf = all(
        len(r.key) == 1 and next(iter(r.key)) not in cls.parents for r in cls.records
    )
    if not one_leaf:
        return _records_lines(renderer, name, verbose)
    field = next(iter(cls.records[0].key))
    ordered = sorted(
        cls.records,
        key=lambda r: (
            renderer.leaf_sort(name, field, r.key[field]),
            r.canonical_json(),
        ),
    )
    texts = [renderer.leaf_text(name, field, r.key[field]) for r in ordered]
    shown = _truncated(texts, verbose, VALUE_LIMIT, VALUE_ENDS, "value")
    return [f"{_INDENT}{_plural(cls.count, 'value')}: [ {', '.join(shown)} ]"]


def _record_lines(
    renderer: _Renderer, name: str, records: Sequence[Record], fields_of, verbose: bool
) -> List[str]:
    entries = []
    for record in records:
        fields = fields_of(record)
        line = renderer.record_text(name, record, fields)
        if record.value_count is not None:
            line += f" | {_plural(record.value_count, 'value row')}"
        entries.append((renderer.record_sort(name, record, fields), line))
    entries.sort(key=lambda e: e[0])
    texts = [line for _, line in entries]
    return [
        f"{_RECORD_INDENT}:: {t}"
        for t in _truncated(texts, verbose, RECORD_LIMIT, RECORD_ENDS, "record")
    ]


def _records_lines(renderer: _Renderer, name: str, verbose: bool) -> List[str]:
    """Any other class: its records by their physical labels, sorted."""
    cls = renderer.cls(name)
    if cls.count == 0:
        return [f"{_INDENT}no records committed"]
    lines = [f"{_INDENT}{_plural(cls.count, 'record')}"]
    lines.extend(
        _record_lines(
            renderer, name, cls.records, lambda r: renderer.fields(name, r), verbose
        )
    )
    return lines


def _compute_lines(renderer: _Renderer, name: str, verbose: bool) -> List[str]:
    """A compute target: its timestamps and value rows, the fields common to every record, and
    its validated and unvalidated records, each by the fields that vary across the class."""
    cls = renderer.cls(name)
    lines: List[str] = []

    summary = [_plural(cls.count, "record")]
    if any(r.value_count is not None for r in cls.records):
        total = sum(r.value_count or 0 for r in cls.records)
        summary.append(_plural(total, "value row"))
    if cls.earliest_timestamp is not None:
        summary.append(
            f"committed {_timestamp(cls.earliest_timestamp)} – {_timestamp(cls.latest_timestamp)}"
        )
    lines.append(f"{_INDENT}{'; '.join(summary)}")

    varying = set(renderer.varying(name)) if cls.count > 1 else None
    if varying is not None and cls.count > 0:
        first = cls.records[0]
        common = [f for f in renderer.fields(name, first) if f not in varying]
        if len(common) > 0:
            lines.append(
                f"{_INDENT}common to every record: {renderer.record_text(name, first, common)}"
            )

    def fields_of(record: Record) -> List[str]:
        fields = renderer.fields(name, record)
        return fields if varying is None else [f for f in fields if f in varying]

    groups = [
        ("validated", [r for r in cls.records if r.validated is True]),
        ("unvalidated", [r for r in cls.records if r.validated is False]),
    ]
    null = [r for r in cls.records if r.validated is None]
    if len(null) > 0:
        groups.append(("validated NULL", null))
    for title, records in groups:
        lines.append(f"{_INDENT}@@ {title}: {len(records):,} record(s)")
        lines.extend(_record_lines(renderer, name, records, fields_of, verbose))
    return lines


def _section_lines(
    renderer: _Renderer, title: str, name: str, kind: str, verbose: bool
) -> List[str]:
    cls = renderer.cls(name)
    where = "replicated" if cls.replicated else "sharded"
    lines = ["", f"   -- {title} ({name}, {where})"]
    if kind == VALUES:
        lines.extend(_values_lines(renderer, name, verbose))
    elif kind == COMPUTE:
        lines.extend(_compute_lines(renderer, name, verbose))
    else:
        lines.extend(_records_lines(renderer, name, verbose))

    # every problem, whole
    if len(cls.problems) > 0:
        lines.append(f"{_INDENT}{_plural(len(cls.problems), 'problem')}:")
        for problem in cls.problems:
            lines.append(f"{_RECORD_INDENT}!! {problem}")
    return lines


def format_inventory_report(
    inventory: StoreInventory, db_name: Any, verbose: bool = False
) -> str:
    """
    Render ``inventory`` (what ``read_inventory`` returns) as the text of the inventory report, one
    string. ``db_name`` is printed in the title as given. With ``verbose`` every value and record is
    listed; otherwise a list of more than ``VALUE_LIMIT`` values shows its first and last
    ``VALUE_ENDS``, and a group of more than ``RECORD_LIMIT`` records its first and last
    ``RECORD_ENDS``. Every problem is printed whole either way.
    """
    renderer = _Renderer(inventory)
    problems = inventory.problems
    total = sum(c.count for c in inventory.classes.values())

    lines = [f"@@ DATASTORE INVENTORY: {db_name}"]
    shard_list = ", ".join(f"#{s}" for s in inventory.shards)
    lines.append(
        f"   read-only; {_plural(len(inventory.shards), 'shard')} ({shard_list}); "
        f"{_plural(total, 'record')} in {_plural(len(inventory.classes), 'class')}"
    )
    lines.append(
        "   problems: none"
        if len(problems) == 0
        else f"   problems: {len(problems):,}, each listed in full under its class"
    )

    named = set()
    for title, name, kind in SECTIONS:
        if name in inventory.classes:
            named.add(name)
            lines.extend(_section_lines(renderer, title, name, kind, verbose))
    for name in inventory.classes:
        if name not in named:
            lines.extend(
                _section_lines(renderer, "Other classes", name, RECORDS, verbose)
            )

    return "\n".join(lines)
