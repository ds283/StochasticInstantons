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

"""U5: ``config.datastore.tables_to_drop``, the ``--drop`` policy (dk-and-rpk-migration prompt 09).

``main.py --drop`` takes groups; the ``datastorekit`` pool takes tables, and refuses a drop that
leaves another table naming dropped rows. ``tables_to_drop`` turns the groups into tables and
refuses, before Ray starts, a request whose closure under
``datastorekit.SQL.schema.dependent_tables`` is not among the requested tables.

The decisions below are written out, not computed from the function under test: 10 of the 31
non-empty sets of the five groups are closed and 21 are refused. Every closed set holds
``compaction-function`` or is ``gradient-coupled-instanton`` alone, and none holds
``inflaton-trajectory`` but all five. ``dependent_tables`` reads the parents each factory's
``inventory_spec`` declares as well as foreign keys; the specs prompt 10 added left every decision
and message as foreign keys alone gave them, since their only new edges (a trajectory to its
potentials, and the three instantons to the diffusion model) point at tables in no drop group.

No Ray is started.
"""

import itertools
import os
import subprocess
import sys
from pathlib import Path

import pytest

from config.datastore import drop_groups, tables_to_drop

_GROUPS = [
    "inflaton-trajectory",
    "full-instanton",
    "slow-roll-instanton",
    "compaction-function",
    "gradient-coupled-instanton",
]

# The 10 closed sets, as measured on the installed package (the orchestrator's brief for 09,
# correction 9).
_CLOSED = {
    frozenset(s)
    for s in [
        ["compaction-function"],
        ["gradient-coupled-instanton"],
        ["full-instanton", "compaction-function"],
        ["slow-roll-instanton", "compaction-function"],
        ["compaction-function", "gradient-coupled-instanton"],
        ["full-instanton", "slow-roll-instanton", "compaction-function"],
        ["full-instanton", "compaction-function", "gradient-coupled-instanton"],
        ["slow-roll-instanton", "compaction-function", "gradient-coupled-instanton"],
        [
            "full-instanton",
            "slow-roll-instanton",
            "compaction-function",
            "gradient-coupled-instanton",
        ],
        _GROUPS,
    ]
}

_ALL_SETS = [
    combo
    for r in range(1, len(_GROUPS) + 1)
    for combo in itertools.combinations(_GROUPS, r)
]

# The refusal of each of the three groups that are not closed alone, verbatim.
_SINGLETON_MESSAGES = {
    "full-instanton": (
        "cannot drop full-instanton alone: CompactionFunction names its rows, so "
        "CompactionFunction and CompactionFunctionSamples must be dropped too; "
        "add --drop compaction-function"
    ),
    "slow-roll-instanton": (
        "cannot drop slow-roll-instanton alone: CompactionFunction names its rows, so "
        "CompactionFunction and CompactionFunctionSamples must be dropped too; "
        "add --drop compaction-function"
    ),
    "inflaton-trajectory": (
        "cannot drop inflaton-trajectory alone: FullInstanton, GradientCoupledInstanton, "
        "SlowRollInstanton and CompactionFunction name its rows, so FullInstanton, "
        "FullInstantonValue, GradientCoupledInstanton, GradientCoupledInstantonValue, "
        "GradientCoupledInstantonProfile, SlowRollInstanton, SlowRollInstantonValue, "
        "CompactionFunction and CompactionFunctionSamples must be dropped too; "
        "add --drop full-instanton slow-roll-instanton compaction-function "
        "gradient-coupled-instanton"
    ),
}


def test_the_groups_are_the_five():
    assert list(drop_groups) == _GROUPS
    assert len(_ALL_SETS) == 31
    assert len(_CLOSED) == 10


@pytest.mark.parametrize("group", sorted(_SINGLETON_MESSAGES))
def test_an_unclosed_group_alone_is_refused_naming_the_groups_to_add(group):
    with pytest.raises(ValueError) as caught:
        tables_to_drop([group])
    assert str(caught.value) == _SINGLETON_MESSAGES[group]


def test_every_set_is_decided_as_measured():
    """All 31 non-empty sets: a closed one gives exactly its groups' tables, in drop_groups'
    order; a refused one raises, and the groups its message says to add close it."""
    wrong = []
    for combo in _ALL_SETS:
        label = "+".join(combo)
        if frozenset(combo) in _CLOSED:
            try:
                tables = tables_to_drop(combo)
            except ValueError as e:
                wrong.append(f"{label}: refused ({e})")
                continue
            expected = [t for g in _GROUPS if g in combo for t in drop_groups[g]]
            if tables != expected:
                wrong.append(f"{label}: {tables}, expected {expected}")
        else:
            try:
                tables = tables_to_drop(combo)
            except ValueError as e:
                message = str(e)
                added = message.split("; add --drop ", 1)[-1].split()
                if not message.startswith("cannot drop ") or not added:
                    wrong.append(f"{label}: unexpected message {message!r}")
                elif any(g in combo for g in added) or not set(added) <= set(_GROUPS):
                    wrong.append(f"{label}: names {added} to add")
                elif frozenset(combo) | frozenset(added) not in _CLOSED:
                    wrong.append(f"{label}: adding {added} does not close it")
                continue
            wrong.append(f"{label}: accepted ({tables})")
    assert not wrong, "\n".join(wrong)


def test_duplicates_and_order_do_not_matter():
    assert tables_to_drop(
        ["compaction-function", "full-instanton", "full-instanton"]
    ) == [
        "FullInstantonValue",
        "FullInstanton",
        "CompactionFunctionSamples",
        "CompactionFunction",
    ]


def test_no_group_drops_nothing():
    assert tables_to_drop([]) == []


def test_an_unknown_group_is_refused():
    with pytest.raises(ValueError, match="unknown drop group"):
        tables_to_drop(["no-such-group"])


def test_no_ray_is_started():
    """In a fresh process, so the answer does not depend on test order."""
    root = Path(__file__).resolve().parent.parent
    code = (
        "from config.datastore import tables_to_drop; import ray; "
        "tables_to_drop(['inflaton-trajectory', 'full-instanton', 'slow-roll-instanton', "
        "'compaction-function', 'gradient-coupled-instanton']); "
        "assert not ray.is_initialized(); print('ok')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(root)},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
