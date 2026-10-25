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

"""What the source says, read with `ast` (rrk-adoption prompt 03, W6 tests 7 and 8), and the
notify numbers the heartbeat's sentence states.

- **`main.py` runs without RunRegistryKit** (campaign README §6.0, R2 and R3): none of `main.py`,
  `plot_InstantonSolutions.py`, `plot_GradientCoupledSolutions.py` and `utilities.py` imports
  `runregistrykit` or `RunDrivers`. Byte-identity since `1c223e8` is the results note's `git diff`,
  not a test, so that a later campaign's legitimate edit to `main.py` does not fail it.
- **The wrapper's `run.finish(` calls** (SecondaryGWKit's `test_finish_calls.py`): those inside a
  signal handler pass no `fingerprint=True`, and those after the program pass it.
- **`begin`'s two handlers**, in order: `runregistrykit.ConfigError` re-raised, then any other
  `RuntimeError` made a `Refusal` from the error.
- **The `ray.init` wrapper** calls the real `ray.init` with its arguments unchanged, and installs
  the handler after it (P9).
- **The notify numbers** in `heartbeat_means` are RayPoolKit's defaults, and no `RayWorkPool(`
  call in `main.py` passes a `notify_` keyword (the orchestrator's note for 03, correction 2).
  Importing RayPoolKit's module imports `ray` and initialises nothing.

Nothing is imported from the files read by `ast`, and nothing is run.
"""

import ast
import importlib
from pathlib import Path

from RunDrivers import registered_run
from registered_run_helpers import REPO_ROOT, WRAPPER, no_ray_at_the_end  # noqa: F401

DRIVERS = (
    "main.py",
    "plot_InstantonSolutions.py",
    "plot_GradientCoupledSolutions.py",
    "utilities.py",
)
FORBIDDEN = ("runregistrykit", "RunDrivers")

# the wrapper's signal handlers, by name: `terminal`, installed by `register` before ray.init, and
# `make_killed_handler`'s `killed_handler`, installed after it
_HANDLERS = ("terminal", "killed_handler")


def _tree(path):
    return ast.parse(Path(path).read_text(), filename=str(path))


def _function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"no function {name}")


def _called_name(call):
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _calls(node, name):
    return [
        n for n in ast.walk(node) if isinstance(n, ast.Call) and _called_name(n) == name
    ]


def _imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module is not None:
                yield node.module


def _finish_calls(path):
    """``[(inside a signal handler, passes fingerprint=True)]`` for every ``run.finish(``."""
    found = []

    def visit(node, inside):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inside = inside or node.name in _HANDLERS
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "finish"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "run"
        ):
            passes = any(
                k.arg == "fingerprint"
                and isinstance(k.value, ast.Constant)
                and k.value.value is True
                for k in node.keywords
            )
            found.append((inside, passes))
        for child in ast.iter_child_nodes(node):
            visit(child, inside)

    visit(_tree(path), False)
    return found


def test_no_driver_imports_the_registry_or_the_wrapper():
    for name in DRIVERS:
        modules = list(_imported_modules(_tree(REPO_ROOT / name)))
        assert modules, f"{name} imports nothing: the reading is wrong"
        for module in modules:
            for forbidden in FORBIDDEN:
                assert not (
                    module == forbidden or module.startswith(forbidden + ".")
                ), f"{name} imports {module}"


def test_handlers_pass_no_fingerprint_and_every_later_finish_passes_it():
    calls = _finish_calls(WRAPPER)
    outside = [passes for inside, passes in calls if not inside]
    inside = [passes for inside, passes in calls if inside]
    # finish_after_exec: done, terminal_state, failed and killed; terminal and killed_handler
    assert (len(outside), len(inside)) == (4, 2)
    assert all(outside), outside
    assert not any(inside), inside


def _is_begin_call(node):
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "begin"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "runregistrykit"
    )


def test_the_one_begin_call_has_the_two_handlers_in_order():
    tree = _tree(WRAPPER)
    assert sum(_is_begin_call(n) for n in ast.walk(tree)) == 1
    trys = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        and any(_is_begin_call(n) for stmt in node.body for n in ast.walk(stmt))
    ]
    assert len(trys) == 1
    node = trys[0]
    assert [ast.unparse(h.type) for h in node.handlers] == [
        "runregistrykit.ConfigError",
        "RuntimeError",
    ]
    config, runtime = node.handlers
    assert len(config.body) == 1
    assert isinstance(config.body[0], ast.Raise)
    assert config.body[0].exc is None, "not a bare raise"
    raised = runtime.body[0]
    assert isinstance(raised, ast.Raise)
    assert ast.unparse(raised.exc) == f"Refusal(str({runtime.name}))"
    assert ast.unparse(raised.cause) == runtime.name


def test_the_ray_init_wrapper_passes_the_arguments_unchanged_then_installs_the_handler():
    wrapper = _function(_function(_tree(WRAPPER), "main"), "_registered_ray_init")
    body = wrapper.body
    real = [i for i, stmt in enumerate(body) if _calls(stmt, "_real_ray_init")]
    install = [
        i for i, stmt in enumerate(body) if _calls(stmt, "install_killed_handler")
    ]
    assert len(real) == 1
    assert len(install) == 1, "the wrapper does not install the handler"
    assert install[0] > real[0], "installed before ray.init"
    call = _calls(body[real[0]], "_real_ray_init")[0]
    assert [ast.unparse(a) for a in call.args] + [
        ast.unparse(k) for k in call.keywords
    ] == ["*init_args", "**init_kwargs"]
    installed = _calls(body[install[0]], "install_killed_handler")[0]
    assert [ast.unparse(a) for a in installed.args] == ["run", "latch"]


def test_the_module_imports_nothing_of_ray_at_module_scope():
    for node in _tree(WRAPPER).body:
        if isinstance(node, ast.Import):
            assert "ray" not in [a.name.split(".")[0] for a in node.names]
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] != "ray"


def test_the_notify_numbers_are_raypoolkits_defaults():
    # raypoolkit/__init__.py binds the name RayWorkPool to the class, so the module is fetched
    # from sys.modules by its dotted name
    module = importlib.import_module("raypoolkit.RayWorkPool")
    assert registered_run.NOTIFY_MIN_INTERVAL == module.DEFAULT_NOTIFY_MIN_INTERVAL == 60
    assert registered_run.NOTIFY_TIME_INTERVAL == module.DEFAULT_NOTIFY_TIME_INTERVAL == 300
    assert registered_run.NOTIFY_BATCH_SIZE == module.DEFAULT_NOTIFY_BATCH_SIZE == 500


def test_no_raywork_pool_in_main_py_passes_a_notify_keyword():
    calls = _calls(_tree(REPO_ROOT / "main.py"), "RayWorkPool")
    # main.py's fourteen queues (main.py:255 to :1121)
    assert len(calls) == 14
    for call in calls:
        keywords = [k.arg for k in call.keywords]
        assert None not in keywords, "a **kwargs could carry a notify_ keyword"
        assert not [k for k in keywords if k.startswith("notify_")], keywords
