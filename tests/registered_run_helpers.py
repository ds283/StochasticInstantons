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

"""The fixtures of `tests/test_registered_run*.py`, and the wrapper with Ray stubbed (rrk-adoption
prompt 03, W6). Not a test module: it has no `test_` prefix, and the test modules import it as
`registered_run_helpers` (`tests/` has no `__init__.py`; pytest puts it on `sys.path`).

**Run as a program**, from the repository root,

    python -u tests/registered_run_helpers.py RUNS_ROOT PROGRAM -- <the wrapper's arguments>

it puts the repository root on `sys.path`, replaces `ray.init` and `ray.shutdown` by stand-ins and
calls `registered_run.run(<the wrapper's arguments>, program=PROGRAM, runs_root=RUNS_ROOT)`: the
script's own entry, with its refusal print, its marker and its exit status, on a stand-in program
in a temporary runs root. The `ray.init` stand-in installs a `SIGTERM` handler as Ray 2.55.1's does
(`sys.exit(signum)`, `ray/_private/worker.py:1656-1661`), so that the wrapper's must replace it.
`-u` is required: through a pipe the stand-in's banner would otherwise be block-buffered. It ends
with `ray.is_initialized()` false, or says so and exits 99.

**As a module** it gives the tests:

- `standin_program(directory, behaviour, runs_root)`: writes a stand-in for `main.py` into a
  temporary directory. Its first statement lists the manifests under the runs root. It records
  `sys.argv`, `__name__`, `__file__` and the `SIGTERM` handler before and after its
  `ray.init(address=...)` (as `main.py:131` calls it) in `<program>.json`, prints RayWorkPool's
  banner, progress and completion lines (RayWorkPool's own format strings, with its timestamps),
  and then does what ``behaviour`` says;
- `StringWriter`, a file-like stand-in for a real stream; `Recorder`, a stand-in for `ray.init`,
  `ray.shutdown` or `signal.alarm`;
- `TakeOver`, which saves and restores everything the wrapper takes over in-process, and
  `in_process`, which runs the wrapper's `main` in this process with a cleanup registered first;
- `reap`, which kills and waits for a child;
- the launchers of the wrapper with Ray stubbed (`run_stubbed`) and of the real script
  (`run_the_script`), and `var_state`;
- `no_ray_at_the_end`, an autouse fixture each test module imports: a test that starts with
  `ray.is_initialized()` false ends with it false.

No Ray is initialised by any of it, and nothing under `var/` is read or written.
"""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "RunDrivers" / "registered_run.py"
HELPER = Path(__file__).resolve()

# a titled queue of main.py's (main.py:855), as RayWorkPool prints its banner
TITLE = "STAGE 2: FULL MSR INSTANTONS"

ADDRESS = "127.0.0.1:6390"

# what a stand-in program does after its banner and progress lines ("wait": after its banner)
BEHAVIOURS = ("return", "exit-2", "exit-1", "raise", "wait", "mid-line")

ERROR_TEXT = "the stand-in program failed on purpose"

# what the "mid-line" stand-in writes last, with no newline, before it returns
MID_LINE = "a line left unfinished"

_PROGRAM = """\
import glob as _glob
MANIFESTS_AT_START = sorted(_glob.glob({manifests!r}))

import json
import signal
import sys
import time
from datetime import datetime

import ray

BEHAVIOUR = {behaviour!r}
RECORD = {record!r}


def _handler():
    handler = signal.getsignal(signal.SIGTERM)
    return getattr(handler, "__qualname__", repr(handler))


record = {{
    "manifests_at_start": MANIFESTS_AT_START,
    "argv": list(sys.argv),
    "name": __name__,
    "file": __file__,
    "sigterm_before_init": _handler(),
}}
# as main.py:131 calls it
address = sys.argv[sys.argv.index("--ray-address") + 1] if "--ray-address" in sys.argv else None
ray.init(address=address)
record["sigterm_after_init"] = _handler()
with open(RECORD, "w") as handle:
    json.dump(record, handle)

# RayWorkPool's banner (RayWorkPool.py:206), two progress notifications (:588, :592) and the
# completion line (:606), with its format strings and its timestamps
print(f"\\n** {title}")

if BEHAVIOUR == "wait":
    # the banner is the last line before the wait, so that a test that signals once it has read
    # the banner interrupts no print half-way. It waits to be signalled; a test that never
    # signals it is failed by the 120 s cap
    sys.stdout.flush()
    deadline = time.monotonic() + 120.0
    while time.monotonic() < deadline:
        time.sleep(0.05)
    sys.exit(99)

now = datetime.now()
print(
    f"   -- {{now:%Y-%m-%d %H:%M:%S%z}} (5m 1s running): 3/5 work items remaining = "
    f"{{40.0:.2f}}% complete"
)
print("      inflight: 0 lookup, 3 compute, 0 store, 0 validation | completed: 2 lookup")
now = datetime.now()
print(
    f"   -- {{now:%Y-%m-%d %H:%M:%S%z}} (10m 2s running): 0/5 work items remaining = "
    f"{{100.0:.2f}}% complete (may be waiting for compute/store/validate tasks to finish)"
)
print("   -- ALL WORK ITEMS COMPLETE in time 10m 3s")
print("      Queue summary: 5 lookup, 5 compute, 5 store, 5 validation")

if BEHAVIOUR == "exit-2":
    sys.exit(2)
if BEHAVIOUR == "exit-1":
    sys.exit(1)
if BEHAVIOUR == "raise":
    raise RuntimeError({error!r})
if BEHAVIOUR == "mid-line":
    # what a signal handler raising between print's text and its newline leaves
    sys.stdout.write({mid_line!r})
"""


def standin_program(directory, behaviour, runs_root) -> Path:
    """Write a stand-in for `main.py` into ``directory`` and return its path. Its record is
    `<path>.json`, beside it (`read_record`)."""
    if behaviour not in BEHAVIOURS:
        raise ValueError(f"behaviour must be one of {BEHAVIOURS}, not {behaviour!r}")
    path = Path(directory) / f"standin_{behaviour.replace('-', '_')}.py"
    path.write_text(
        _PROGRAM.format(
            manifests=str(Path(runs_root) / "*" / "manifest.json"),
            behaviour=behaviour,
            record=str(path.with_suffix(".json")),
            title=TITLE,
            error=ERROR_TEXT,
            mid_line=MID_LINE,
        )
    )
    return path


def read_record(program) -> dict:
    with open(Path(program).with_suffix(".json"), "r") as handle:
        return json.load(handle)


class StringWriter:
    """A file-like stand-in for `sys.stdout` or `sys.stderr`."""

    def __init__(self):
        self._parts = []

    def write(self, text):
        self._parts.append(text)
        return len(text)

    def flush(self):
        pass

    def text(self):
        return "".join(self._parts)


class Recorder:
    """A stand-in for `ray.init`, `ray.shutdown` or `signal.alarm`: records each call's arguments,
    calls ``side_effect`` if given, and returns ``value``."""

    def __init__(self, value=None, side_effect=None):
        self.calls = []
        self.value = value
        self.side_effect = side_effect

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.side_effect is not None:
            self.side_effect(*args, **kwargs)
        return self.value


def ray_like_sigterm_handler(signum, _frame):
    """What `ray.init` installs as the Python `SIGTERM` handler (`worker.py:1655-1656`)."""
    sys.exit(signum)


def install_ray_like_handler(*_args, **_kwargs):
    signal.signal(signal.SIGTERM, ray_like_sigterm_handler)


class TakeOver:
    """Everything the wrapper takes over in its own process: `sys.stdout`, `sys.stderr`,
    `sys.argv`, and the `SIGTERM` and `SIGINT` handlers. `restore()` closes the copies of any
    proxy it finds in place and puts every one of them back."""

    NUMBERS = (signal.SIGTERM, signal.SIGINT)

    def __init__(self):
        self.stdout, self.stderr = sys.stdout, sys.stderr
        self.argv = list(sys.argv)
        self.handlers = {number: signal.getsignal(number) for number in self.NUMBERS}

    def restore(self):
        for stream in (sys.stdout, sys.stderr):
            close_copy = getattr(stream, "close_copy", None)
            if close_copy is not None:
                close_copy()
        sys.stdout, sys.stderr = self.stdout, self.stderr
        sys.argv = self.argv
        for number, handler in self.handlers.items():
            signal.signal(number, handler)


def reap(child) -> None:
    """Kill ``child`` if it is still running, and wait for it, whatever has happened."""
    if child.poll() is None:
        child.kill()
    child.wait(timeout=60)
    for pipe in (child.stdout, child.stderr):
        if pipe is not None:
            pipe.close()


def subprocess_env() -> dict:
    """The environment of every subprocess the tests start: this one's, with no `RAY_ADDRESS`."""
    env = dict(os.environ)
    env.pop("RAY_ADDRESS", None)
    return env


def wrapper_argv(database, slug="unit", main_args=None, purpose=None) -> list:
    """The wrapper's arguments for a run of a stand-in on ``database``: the four flags, a bare
    `--`, and `main.py`'s arguments (by default the database and an explicit address)."""
    if main_args is None:
        main_args = ["--database", str(database), "--ray-address", ADDRESS]
    return [
        "--campaign",
        "rrk-adoption",
        "--prompt",
        "03",
        "--register",
        slug,
        "--purpose",
        purpose or "a test run of the wrapper, in a temporary directory",
        "--",
        *main_args,
    ]


class InProcess:
    """What one in-process `registered_run.main` left: ``outcome`` (`None`, or the exception it
    raised), the real streams it wrote through (``out``, ``err``), the `ray.init` and
    `ray.shutdown` stand-ins, and ``taken``, what it had taken over when it ended, observed before
    anything was restored."""

    def __init__(self, outcome, out, err, init, shutdown, taken):
        self.outcome = outcome
        self.out = out
        self.err = err
        self.init = init
        self.shutdown = shutdown
        self.taken = taken


def in_process(addcleanup, program, argv, runs_root, *, init=None, shutdown=None):
    """`registered_run.main(argv, program=program, runs_root=runs_root)` in this process, with
    `ray.init` and `ray.shutdown` replaced by stand-ins before the wrapper wraps them, and with
    `sys.stdout` and `sys.stderr` replaced by `StringWriter`s for the proxies to wrap.
    ``addcleanup`` is pytest's `request.addfinalizer`: a cleanup that restores everything the
    wrapper takes over is registered with it before the call; the restoration is also made straight
    after it, once what was taken over has been observed. Returns an `InProcess`."""
    import ray

    from RunDrivers import registered_run

    saved = TakeOver()
    addcleanup(saved.restore)
    out, err = StringWriter(), StringWriter()
    sys.stdout, sys.stderr = out, err
    init = Recorder() if init is None else init
    shutdown = Recorder() if shutdown is None else shutdown
    outcome = None
    try:
        with mock.patch.object(ray, "init", init), mock.patch.object(
            ray, "shutdown", shutdown
        ):
            try:
                registered_run.main(argv, program=program, runs_root=str(runs_root))
            except BaseException as exc:  # noqa: BLE001
                outcome = exc
        taken = {
            "stdout": isinstance(sys.stdout, registered_run.RegisteredStream),
            "stderr": isinstance(sys.stderr, registered_run.RegisteredStream),
            "handlers": any(
                signal.getsignal(number) is not saved.handlers[number]
                for number in TakeOver.NUMBERS
            ),
        }
    finally:
        saved.restore()
    return InProcess(outcome, out, err, init, shutdown, taken)


def only_run(runs_root) -> Path:
    """The one run directory under ``runs_root``."""
    runs = sorted(Path(runs_root).iterdir())
    if len(runs) != 1:
        raise AssertionError(f"expected one run under {runs_root}, found {runs}")
    return runs[0]


def read_json(path) -> dict:
    with open(path, "r") as handle:
        return json.load(handle)


def stubbed(runs_root, program, argv) -> list:
    """The command line of the wrapper with Ray stubbed: `python -u tests/registered_run_helpers.py`,
    run from the repository root."""
    return [
        sys.executable,
        "-u",
        str(HELPER),
        str(runs_root),
        str(program),
        "--",
        *argv,
    ]


def run_stubbed(runs_root, program, argv):
    """The wrapper with Ray stubbed, to completion. Returns the `CompletedProcess`."""
    return subprocess.run(
        stubbed(runs_root, program, argv),
        cwd=str(REPO_ROOT),
        env=subprocess_env(),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def run_the_script(argv):
    """The real script, `python RunDrivers/registered_run.py`, with no stub and no `PYTHONPATH`,
    from the repository root. Only for runs that are refused before `begin`, or `--help`: they
    reach neither `begin` nor Ray. Returns the `CompletedProcess`."""
    env = subprocess_env()
    env.pop("PYTHONPATH", None)
    return subprocess.run(
        [sys.executable, str(WRAPPER), *argv],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )


def var_state():
    """Whether `var/` exists at the repository root, and the listing of `var/runs` if it does:
    what a refused run must leave as it found."""
    var = REPO_ROOT / "var"
    runs = var / "runs"
    listing = sorted(p.name for p in runs.iterdir()) if runs.is_dir() else None
    return var.exists(), listing


@pytest.fixture(autouse=True)
def no_ray_at_the_end():
    """Every test ends with Ray as it found it: not initialised, unless it already was.

    Two modules of the default selection, `test_plot_extraction_golden.py` and
    `test_plot_adapters_golden.py`, initialise a local Ray in the test process from a module-scoped
    fixture and leave it up for the rest of the session, so in a whole-suite run every module
    collected after them starts with Ray initialised. Run on their own, as each module here can be,
    these tests start with Ray down and must end with it down."""
    import ray

    before = ray.is_initialized()
    yield
    if not before:
        assert not ray.is_initialized(), "this test initialised Ray"


def _main(argv) -> None:
    if len(argv) < 3 or argv[2] != "--":
        print(
            "!! usage: python -u tests/registered_run_helpers.py RUNS_ROOT PROGRAM -- "
            "<the wrapper's arguments>",
            file=sys.stderr,
        )
        sys.exit(2)
    runs_root, program, wrapper_args = argv[0], Path(argv[1]), argv[3:]

    # as the wrapper does: run by path, this file's directory is first on sys.path, not the root
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    import ray

    from RunDrivers import registered_run

    try:
        with mock.patch.object(
            ray, "init", Recorder(side_effect=install_ray_like_handler)
        ), mock.patch.object(ray, "shutdown", Recorder()):
            registered_run.run(wrapper_args, program=program, runs_root=runs_root)
    finally:
        if ray.is_initialized():
            os.write(2, b"!! registered_run_helpers: Ray was initialised\n")
            os._exit(99)


if __name__ == "__main__":
    _main(sys.argv[1:])
