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
Every Ray start of StochasticInstanton runs in Ray's token mode, named (ray-sqla-align prompt 01,
items T1-T3; after SecondaryGWKit's RunDrivers/tests/test_ray_auth_mode.py).

What this pins, and why:
- `config/ray_auth.py` sets `RAY_AUTH_MODE=token` at import unless the environment already holds
  a value. Since Ray 2.59 a driver attaching to an explicit address never turns token mode on by
  itself, while `ray start --head` does whenever `~/.ray/auth_token` exists, so without the module
  SI's cluster refuses `main.py` (ray-sqla-align 01, V0).
- Ray reads the mode into its config when `ray` is imported, and the drivers import `ray` first,
  so the module refreshes Ray's config when `ray` is already imported. Ray's own mode is read in a
  fresh interpreter in both import orders: without the refresh, the order of `main.py` keeps
  `disabled` (SecondaryGWKit's issue
  [02-the-token-mode-setting-comes-after-import-ray-so-every-ray-start-fails]).
- Each driver imports the module at module level before the top-level statement holding its
  `ray.init` (main.py's call itself; for the plot scripts, their `if __name__ == "__main__":`
  block), and `tests/conftest.py` imports it, so that the suite's Ray
  starts, and the subprocesses that inherit its environment, run in token mode too. Read by `ast`.
- `ray_cluster.sh` exports the mode, defaulting to `token`, before its `ray start`. Read as text.

No Ray instance is started: each fresh interpreter imports `ray` (a second or two) and reads its
config. The test's own environment is not changed. Nothing is written.
"""

import ast
import os
import pathlib
import re
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

RAY_CLUSTER_SH = ROOT / ".documents" / "dk-and-rpk-migration" / "rehearsal" / "ray_cluster.sh"

# the drivers: main.py calls ray.init at module level, the plot scripts in their __main__ block
DRIVERS = ["main.py", "plot_InstantonSolutions.py", "plot_GradientCoupledSolutions.py"]


def _fresh(program, environment=None):
    """The last line a fresh interpreter prints running PROGRAM from the repository root, with
    `RAY_AUTH_MODE` removed from this process's environment and ENVIRONMENT added."""
    env = {k: v for k, v in os.environ.items() if k != "RAY_AUTH_MODE"}
    env.update(environment or {})
    env["PYTHONPATH"] = str(ROOT)
    done = subprocess.run(
        [sys.executable, "-c", program],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    return done.stdout.strip().splitlines()[-1]


MODE_PROBE = "import os, config.ray_auth; print(os.environ.get('RAY_AUTH_MODE'))"


def test_an_unset_mode_becomes_token():
    """With nothing set, Ray would choose the mode itself, by how it is started."""
    assert _fresh(MODE_PROBE) == "token"


def test_a_mode_already_set_is_left_as_it_is():
    """A person's explicit choice in the environment wins over SI's."""
    assert _fresh(MODE_PROBE, {"RAY_AUTH_MODE": "disabled"}) == "disabled"


RAY_PROBE = (
    "{first}\n"
    "{second}\n"
    "from ray._raylet import AuthenticationMode, get_authentication_mode\n"
    "print(get_authentication_mode() == AuthenticationMode.TOKEN)\n"
)


def _ray_sees_token_mode(first, second, environment=None):
    """Whether Ray's own config is in token mode after the two imports, in a fresh interpreter.
    `get_authentication_mode` reads the config a driver would start with; nothing is started."""
    return _fresh(RAY_PROBE.format(first=first, second=second), environment) == "True"


def test_ray_imported_first():
    """The order of main.py, the plot scripts and registered_run.py: `ray`, then the module."""
    assert _ray_sees_token_mode("import ray", "import config.ray_auth")


def test_the_module_imported_first():
    assert _ray_sees_token_mode("import config.ray_auth", "import ray")


def test_a_mode_already_set_is_what_ray_sees():
    """With `disabled` already set, Ray is not in token mode, whatever the module does."""
    assert not _ray_sees_token_mode(
        "import ray", "import config.ray_auth", {"RAY_AUTH_MODE": "disabled"}
    )


def _imports_ray_auth(node):
    return isinstance(node, ast.Import) and any(
        alias.name == "config.ray_auth" for alias in node.names
    )


def _calls_ray_init(node):
    return any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "init"
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "ray"
        for n in ast.walk(node)
    )


@pytest.mark.parametrize("name", DRIVERS)
def test_each_driver_imports_it_before_ray_init(name):
    """A driver that does not import the module attaches in `disabled` mode and is refused."""
    tree = ast.parse((ROOT / name).read_text(), filename=name)
    imports = [node.lineno for node in tree.body if _imports_ray_auth(node)]
    assert imports, f"{name} does not import config.ray_auth at module level"
    holders = [node for node in tree.body if _calls_ray_init(node)]
    assert holders, f"{name} has no top-level statement holding ray.init"
    assert min(imports) < min(node.lineno for node in holders), (
        f"{name} imports config.ray_auth after the statement holding its ray.init"
    )


def test_conftest_imports_it():
    """The suite's in-process Ray starts, and the subprocesses that inherit its environment."""
    tree = ast.parse((ROOT / "tests" / "conftest.py").read_text(), filename="conftest.py")
    assert any(_imports_ray_auth(node) for node in tree.body)


def test_ray_cluster_sh_exports_the_mode_before_ray_start():
    """Without it, `ray start` infers token mode from the token file rather than being told."""
    lines = RAY_CLUSTER_SH.read_text().splitlines()
    exports = [
        i
        for i, line in enumerate(lines)
        if line.strip() == 'export RAY_AUTH_MODE="${RAY_AUTH_MODE:-token}"'
    ]
    starts = [i for i, line in enumerate(lines) if re.match(r'\s*"\$RAY_BIN" start\b', line)]
    assert exports, "ray_cluster.sh does not export RAY_AUTH_MODE with the :-token default"
    assert len(starts) == 1, "ray_cluster.sh should have one ray start line"
    assert min(exports) < starts[0], "ray_cluster.sh exports RAY_AUTH_MODE after its ray start"
