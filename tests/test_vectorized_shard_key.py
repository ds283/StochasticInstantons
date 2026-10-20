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

"""config.sharding.vectorized_shard_key, and its use at every vectorized get.

Prompt 05 of the ``dk-and-rpk-migration`` campaign (P8): DatastoreKit's
``object_get_vectorized`` accepts only the mapping form of the shard key, so every call passes
``vectorized_shard_key(key)`` and the field name is defined once.
"""

import ast
import os
from pathlib import Path

from config.sharding import sharded_tables, vectorized_shard_key

_ROOT = Path(__file__).resolve().parent.parent

# Directories not walked: tests, the venv, caches, and every dot-directory (.git, .prompts,
# .documents, .claude, ...). A filesystem walk is used, so the test does not need git.
_SKIP_DIRS = {"tests", "venv", "__pycache__", "site-packages", "node_modules"}


def test_vectorized_shard_key_is_the_mapping():
    for key in (0.1, 5.0, "a", 7):
        assert vectorized_shard_key(key) == {"delta_Nstar": key}


def test_field_name_is_every_sharded_tables_value():
    (field,) = vectorized_shard_key(0).keys()
    assert set(sharded_tables.values()) == {field}


def _python_files():
    for dirpath, dirnames, filenames in os.walk(_ROOT):
        dirnames[:] = sorted(
            d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")
        )
        for name in sorted(filenames):
            if name.endswith(".py"):
                yield Path(dirpath) / name


def _vectorized_calls():
    for path in _python_files():
        rel = path.relative_to(_ROOT)
        try:
            tree = ast.parse(path.read_text(), filename=str(rel))
        except SyntaxError as e:
            raise AssertionError(f"{rel}: cannot be parsed: {e}")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "object_get_vectorized"
            ):
                yield rel, node


def _shard_key_argument(call):
    for kw in call.keywords:
        if kw.arg == "shard_key":
            return kw.value
    if len(call.args) >= 2:
        return call.args[1]
    return None


def _is_vectorized_shard_key_call(node):
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    return (isinstance(f, ast.Name) and f.id == "vectorized_shard_key") or (
        isinstance(f, ast.Attribute) and f.attr == "vectorized_shard_key"
    )


def test_every_vectorized_get_passes_the_mapping():
    calls = list(_vectorized_calls())
    bare = [
        f"{rel}:{call.lineno}"
        for rel, call in calls
        if not _is_vectorized_shard_key_call(_shard_key_argument(call))
    ]
    assert not bare, "vectorized gets with a bare shard key: " + ", ".join(bare)
    assert len(calls) == 15, [f"{rel}:{call.lineno}" for rel, call in calls]
