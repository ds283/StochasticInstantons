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

"""``main.py``'s two refusals before Ray starts (dk-and-rpk-migration prompt 09).

- ``--inventory`` refuses until prompt 10 ports the inventory to the ``datastorekit`` package,
  whose pool has no ``inventory()`` (README P11);
- ``--drop`` with a set of groups that is not closed under ``dependent_tables`` refuses, naming
  the groups to add (README U5; ``config.datastore.tables_to_drop``).

Each prints the provenance line, then its refusal on stderr, exits 2, and creates no file. The
subprocess tests run ``main.py`` from the repository root with ``--ray-address 127.0.0.1:9`` and
``RAY_ADDRESS=127.0.0.1:9``, an address nothing listens on, and a timeout, so that a regression
which got past a refusal would fail to connect instead of attaching to another cluster. That is
a guard, not the test: each asserts the message. The ``ast`` test pins the order: both refusals
are module-level statements of ``main.py`` before its ``ray.init``.

No Ray is started.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_MAIN = _ROOT / "main.py"
_ADDRESS = "127.0.0.1:9"

_INVENTORY_MESSAGE = (
    "!! --inventory: the datastore inventory is unavailable until it is ported to the "
    "datastorekit package (dk-and-rpk-migration prompt 10). Nothing was opened"
)
_DROP_MESSAGE = (
    "!! --drop: cannot drop full-instanton alone: CompactionFunction names its rows, so "
    "CompactionFunction and CompactionFunctionSamples must be dropped too; "
    "add --drop compaction-function. Nothing was opened"
)


def _run_main(*arguments, timeout=120):
    return subprocess.run(
        [sys.executable, str(_MAIN), *arguments],
        cwd=_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=dict(os.environ, RAY_ADDRESS=_ADDRESS),
    )


@pytest.mark.parametrize(
    "arguments, message",
    [
        (["--inventory"], _INVENTORY_MESSAGE),
        (["--drop", "full-instanton"], _DROP_MESSAGE),
    ],
    ids=["inventory", "drop-full-instanton"],
)
def test_main_refuses_before_ray(tmp_path, arguments, message):
    database = tmp_path / "x.sqlite"
    result = _run_main(
        "--database", str(database), "--ray-address", _ADDRESS, *arguments
    )
    assert result.returncode == 2, result.stdout + result.stderr
    # the provenance line comes first, on stdout
    assert result.stdout.startswith(">> packages: "), result.stdout
    assert message in result.stderr.splitlines(), result.stderr
    assert "Traceback" not in result.stderr
    assert sorted(os.listdir(tmp_path)) == []


def _is_ray_init(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Attribute)
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id == "ray"
        and node.value.func.attr == "init"
    )


def _is_inventory_refusal(node):
    """``if args.inventory: ... sys.exit(2)``, at module level."""
    if not (
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Attribute)
        and isinstance(node.test.value, ast.Name)
        and node.test.value.id == "args"
        and node.test.attr == "inventory"
    ):
        return False
    return any(
        isinstance(n, ast.Call)
        and ast.unparse(n.func) == "sys.exit"
        and [ast.unparse(a) for a in n.args] == ["2"]
        for n in ast.walk(node)
    )


def _is_drop_refusal(node):
    """A module-level ``try`` that calls ``tables_to_drop`` and exits 2 on ``ValueError``."""
    if not isinstance(node, ast.Try):
        return False
    calls = {ast.unparse(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)}
    handlers = [ast.unparse(h.type) for h in node.handlers if h.type is not None]
    return (
        "tables_to_drop" in calls and "sys.exit" in calls and "ValueError" in handlers
    )


def test_both_refusals_precede_ray_init():
    body = ast.parse(_MAIN.read_text(), filename="main.py").body
    inits = [i for i, node in enumerate(body) if _is_ray_init(node)]
    inventory = [i for i, node in enumerate(body) if _is_inventory_refusal(node)]
    drop = [i for i, node in enumerate(body) if _is_drop_refusal(node)]
    assert len(inits) == 1, f"module-level ray.init(...) at {inits}"
    assert len(inventory) == 1, f"module-level --inventory refusal at {inventory}"
    assert len(drop) == 1, f"module-level --drop refusal at {drop}"
    assert inventory[0] < inits[0], (
        f"the --inventory refusal (line {body[inventory[0]].lineno}) must precede "
        f"ray.init (line {body[inits[0]].lineno})"
    )
    assert drop[0] < inits[0], (
        f"the --drop refusal (line {body[drop[0]].lineno}) must precede "
        f"ray.init (line {body[inits[0]].lineno})"
    )
    # nothing else in main.py reads args.inventory: the old inventory helpers are gone
    reads = [
        n.lineno
        for n in ast.walk(ast.Module(body=body, type_ignores=[]))
        if isinstance(n, ast.Attribute)
        and isinstance(n.value, ast.Name)
        and n.value.id == "args"
        and n.attr == "inventory"
    ]
    assert reads == [body[inventory[0]].lineno], reads
