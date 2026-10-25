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
Run provenance in the drivers' output (dk-and-rpk-migration prompt 01, item T1; README P5):
`utilities.installed_package_provenance()`, `utilities.format_package_provenance()`, and the one
line each driver prints.

**How a distribution is stood in.** Each test writes a real `<name>-<version>.dist-info`
directory (`METADATA`, and a `direct_url.json` where the case has one) into a `tempfile`
directory and puts that directory at the front of `sys.path`. The helper then finds it through
the real `importlib.metadata`, exactly as it would find an installed package. Nothing in
`importlib.metadata` is patched, so a test cannot pass because a mock was aimed at a name the
helper does not call. The stand-ins' names (`si-standin-*`) are not on PyPI and are not installed
in the venv.

No test asserts what the venv itself holds: prompts 03 and 08 install the two packages, and the
helper's output in the venv is recorded in their results notes, not pinned here.

The drivers are read with `ast`, never imported: `main.py` calls `ray.init` at import. No Ray, no
store. Under 1 s.
"""

import ast
import importlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

import utilities
from utilities import format_package_provenance, installed_package_provenance

ROOT = Path(__file__).resolve().parents[1]
DRIVERS = ("main.py", "plot_InstantonSolutions.py", "plot_GradientCoupledSolutions.py")
FIELDS = {"version", "url", "commit", "requested_revision", "editable"}

# pip records a VCS URL without its "git+" prefix (ChamPBH board section 5.4)
VCS_URL = "https://github.com/ds283/DatastoreKit"
VCS_COMMIT = "2f5417ea76cd0000000000000000000000000000"
VCS_TAG = "v0.3.0"


@pytest.fixture
def stand_in():
    """A function writing a stand-in `.dist-info` for `name` at `version` into a temporary
    `sys.path` entry. `direct_url` (a JSON-serialisable value) is written as `direct_url.json`;
    `raw_direct_url` (bytes) is written verbatim instead; with neither there is none."""
    directory = Path(tempfile.mkdtemp(prefix="si-provenance-test-"))
    sys.path.insert(0, str(directory))
    importlib.invalidate_caches()

    def make(name, version, direct_url=None, raw_direct_url=None):
        info = directory / f"{name.replace('-', '_')}-{version}.dist-info"
        info.mkdir()
        (info / "METADATA").write_text(
            f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
        )
        if direct_url is not None:
            (info / "direct_url.json").write_text(json.dumps(direct_url))
        elif raw_direct_url is not None:
            (info / "direct_url.json").write_bytes(raw_direct_url)
        return info

    make.directory = directory
    yield make

    try:
        sys.path.remove(str(directory))
    except ValueError:
        pass
    importlib.invalidate_caches()
    shutil.rmtree(directory, ignore_errors=True)


def test_not_installed(stand_in):
    """A distribution that is not installed maps to None, and the line says so."""
    name = "si-standin-absent"
    provenance = installed_package_provenance((name,))
    assert provenance == {name: None}
    assert format_package_provenance(provenance) == f">> packages: {name} not installed"


def test_vcs_install_at_a_tag(stand_in):
    """A VCS install at a tag: url, commit and requested revision from direct_url.json."""
    name = "si-standin-vcs"
    stand_in(
        name,
        "0.3.0",
        direct_url={
            "url": VCS_URL,
            "vcs_info": {
                "vcs": "git",
                "commit_id": VCS_COMMIT,
                "requested_revision": VCS_TAG,
            },
        },
    )
    provenance = installed_package_provenance((name,))
    assert set(provenance[name]) == FIELDS
    assert provenance[name] == {
        "version": "0.3.0",
        "url": VCS_URL,
        "commit": VCS_COMMIT,
        "requested_revision": VCS_TAG,
        "editable": False,
    }
    assert (
        format_package_provenance(provenance)
        == f">> packages: {name} 0.3.0 ({VCS_URL}@{VCS_COMMIT}, requested {VCS_TAG})"
    )


def test_editable_install(stand_in):
    """An editable install: editable True, no VCS fields, and the line says editable."""
    name = "si-standin-editable"
    url = "file:///Users/someone/Code/DatastoreKit"
    stand_in(name, "0.3.0", direct_url={"url": url, "dir_info": {"editable": True}})
    provenance = installed_package_provenance((name,))
    assert provenance[name] == {
        "version": "0.3.0",
        "url": url,
        "commit": None,
        "requested_revision": None,
        "editable": True,
    }
    assert (
        format_package_provenance(provenance)
        == f">> packages: {name} 0.3.0 (editable, {url})"
    )


@pytest.mark.parametrize(
    "dir_info", [{}, {"editable": False}, {"editable": "true"}, {"editable": 1}]
)
def test_editable_only_for_the_boolean_true(stand_in, dir_info):
    """dir_info without editable, or with editable anything but the boolean true, is not
    editable."""
    name = "si-standin-dir"
    url = "file:///Users/someone/Code/DatastoreKit"
    stand_in(name, "0.3.0", direct_url={"url": url, "dir_info": dir_info})
    provenance = installed_package_provenance((name,))
    assert provenance[name]["editable"] is False
    assert format_package_provenance(provenance) == f">> packages: {name} 0.3.0 ({url})"


def test_direct_url_absent(stand_in):
    """No direct_url.json: None for the three VCS fields, editable False."""
    name = "si-standin-plain"
    stand_in(name, "1.0")
    provenance = installed_package_provenance((name,))
    assert provenance[name] == {
        "version": "1.0",
        "url": None,
        "commit": None,
        "requested_revision": None,
        "editable": False,
    }
    assert (
        format_package_provenance(provenance)
        == f">> packages: {name} 1.0 (no recorded origin)"
    )


@pytest.mark.parametrize(
    "case, kwargs",
    [
        ("list", dict(direct_url=[VCS_URL, VCS_COMMIT])),
        ("string", dict(direct_url="editable")),
        ("number", dict(direct_url=3)),
        ("not-json", dict(raw_direct_url=b'{"url": "https://example.org"')),
        ("not-utf8", dict(raw_direct_url=b"\xff\xfe\x00{")),
    ],
)
def test_direct_url_not_an_object_or_unreadable(stand_in, case, kwargs):
    """direct_url.json that is a JSON list, string or number, not JSON, or not UTF-8: no fields
    from it, editable False, and no exception."""
    name = f"si-standin-bad-{case}"
    stand_in(name, "0.1", **kwargs)
    provenance = installed_package_provenance((name,))
    assert provenance[name] == {
        "version": "0.1",
        "url": None,
        "commit": None,
        "requested_revision": None,
        "editable": False,
    }
    assert (
        format_package_provenance(provenance)
        == f">> packages: {name} 0.1 (no recorded origin)"
    )


def test_direct_url_a_directory(stand_in):
    """direct_url.json present but unreadable (a directory): no fields, and no exception."""
    name = "si-standin-bad-directory"
    info = stand_in(name, "0.1")
    (info / "direct_url.json").mkdir()
    provenance = installed_package_provenance((name,))
    assert provenance[name]["url"] is None
    assert provenance[name]["editable"] is False


def test_vcs_info_or_dir_info_not_an_object(stand_in):
    """A vcs_info or dir_info that is not an object is treated as absent; url is kept."""
    name = "si-standin-odd"
    stand_in(
        name,
        "0.1",
        direct_url={"url": VCS_URL, "vcs_info": "git", "dir_info": ["editable"]},
    )
    provenance = installed_package_provenance((name,))
    assert provenance[name] == {
        "version": "0.1",
        "url": VCS_URL,
        "commit": None,
        "requested_revision": None,
        "editable": False,
    }
    assert (
        format_package_provenance(provenance) == f">> packages: {name} 0.1 ({VCS_URL})"
    )


def test_several_names_in_order_and_nothing_imported(stand_in):
    """Several names give one entry each, in order, joined by '; '. The described package is
    never imported: its stand-in module raises on import."""
    absent = "si-standin-absent"
    name = "si-standin-vcs"
    stand_in(
        name,
        "0.2.0",
        direct_url={
            "url": VCS_URL,
            "vcs_info": {"vcs": "git", "commit_id": VCS_COMMIT},
        },
    )
    module = stand_in.directory / "si_standin_vcs"
    module.mkdir()
    (module / "__init__.py").write_text(
        "raise RuntimeError('a provenance helper must not import this')\n"
    )
    provenance = installed_package_provenance((name, absent))
    assert list(provenance) == [name, absent]
    assert "si_standin_vcs" not in sys.modules
    assert (
        format_package_provenance(provenance)
        == f">> packages: {name} 0.2.0 ({VCS_URL}@{VCS_COMMIT}); {absent} not installed"
    )


def test_default_names():
    """The default names are the two packages the campaign adopts, then the four that say which
    venv ran (added with ray-sqla-align), in this order."""
    names = ("datastorekit", "raypoolkit", "ray", "SQLAlchemy", "numpy", "scipy")
    assert utilities.RECORDED_DISTRIBUTIONS == names
    assert list(installed_package_provenance()) == list(names)


# ---------------------------------------------------------------------------
# the drivers


def _is_provenance_print(node) -> bool:
    """`print(format_package_provenance(installed_package_provenance()), ...)`"""
    if not (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "print"
        and len(node.value.args) == 1
    ):
        return False
    inner = node.value.args[0]
    return (
        isinstance(inner, ast.Call)
        and isinstance(inner.func, ast.Name)
        and inner.func.id == "format_package_provenance"
        and len(inner.args) == 1
        and isinstance(inner.args[0], ast.Call)
        and isinstance(inner.args[0].func, ast.Name)
        and inner.args[0].func.id == "installed_package_provenance"
        and len(inner.args[0].args) == 0
    )


def _calls(tree, name):
    """Every call of `name` (a plain name or an attribute), anywhere in the tree."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Name) and func.id == name) or (
                isinstance(func, ast.Attribute) and func.attr == name
            ):
                found.append(node)
    return found


def _is_main_guard(node) -> bool:
    """`if __name__ == "__main__":`"""
    test = node.test if isinstance(node, ast.If) else None
    return (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _driver_scope(tree):
    """The statements in which the driver calls ray.init: the module body (main.py), or the
    body of its module-level `if __name__ == "__main__":` block (the plot scripts)."""
    guards = [node for node in tree.body if _is_main_guard(node)]
    if guards:
        assert len(guards) == 1
        return guards[0].body
    return tree.body


@pytest.mark.parametrize("driver", DRIVERS)
def test_each_driver_prints_the_line_once_before_ray_and_its_pool(driver):
    """Each driver prints the provenance line exactly once, as a statement of the scope in
    which it calls ray.init (the module for main.py, the `__main__` block for the plot scripts),
    before `ray.init(` and before its `ShardedPool(` construction; and imports both names from
    utilities. Read with ast; no driver is imported."""
    tree = ast.parse((ROOT / driver).read_text(), filename=driver)

    assert len(_calls(tree, "installed_package_provenance")) == 1
    assert len(_calls(tree, "format_package_provenance")) == 1

    scope = _driver_scope(tree)
    prints = [node for node in scope if _is_provenance_print(node)]
    assert len(prints) == 1, "one print of the line, in the driver's scope"
    line = prints[0].lineno

    inits = [
        call
        for call in _calls(tree, "init")
        if isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "ray"
    ]
    assert len(inits) == 1, "one ray.init("
    assert any(
        isinstance(statement, ast.Expr) and statement.value is inits[0]
        for statement in scope
    ), "ray.init( is a statement of the same scope as the print"
    assert line < inits[0].lineno

    pools = _calls(tree, "ShardedPool")
    assert len(pools) >= 1, "a ShardedPool( construction"
    assert line < min(call.lineno for call in pools)

    imported = {
        alias.name
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "utilities"
        for alias in node.names
    }
    assert {"format_package_provenance", "installed_package_provenance"} <= imported
