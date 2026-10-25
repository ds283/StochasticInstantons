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

"""How a registered run ends, and what the wrapper refuses (rrk-adoption prompt 03, W2, W5 and W6
tests 3 and 6).

These need the script's own entry, `run`: the marker, the exit status, the refusal print and the
traceback exist only there (ChamPBH's note 03, ruling 8). So:

- **the outcomes** and **`begin`'s refusal** run the wrapper with Ray stubbed, `python -u
  tests/registered_run_helpers.py`, on a stand-in program, into a temporary runs root;
- **the refusals before `begin`**, and `--help`, run the real script, `python
  RunDrivers/registered_run.py`, with no stub and no `PYTHONPATH`: they reach neither `begin` nor
  Ray. The listing of `var/runs` is asserted unchanged by them.

Every child is reaped by a cleanup registered before its first read. The dead run of `begin`'s
refusal is made by a real child that begins a run and is sent `SIGKILL`, as SecondaryGWKit's
`test_hard_killed_predecessor.py` builds one. No Ray is initialised; no store is created.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path

import pytest

from registered_run_helpers import (  # noqa: F401
    ADDRESS,
    ERROR_TEXT,
    MID_LINE,
    REPO_ROOT,
    TITLE,
    no_ray_at_the_end,
    only_run,
    read_json,
    reap,
    run_stubbed,
    run_the_script,
    standin_program,
    subprocess_env,
    var_state,
    wrapper_argv,
)

MARKER = "** driver exit status"

# a child that begins a run on the store, heartbeats once, says where its run is, and waits to be
# killed (SecondaryGWKit's test_hard_killed_predecessor.CHILD)
CHILD = """\
import sys, time

import runregistrykit

run = runregistrykit.begin(
    campaign="example",
    prompt="01",
    slug="hard-killed",
    purpose="a run that is killed outright",
    root=sys.argv[1],
    client_root=sys.argv[2],
    argv=["a-child"],
    results=sys.argv[3],
)
run.heartbeat(units_done=1, stage="working")
print(run.path, flush=True)
time.sleep(600)
"""


class Children:
    def __init__(self, tmp_path):
        self.top = Path(tmp_path).resolve()
        self.runs_root = self.top / "runs"
        self.runs_root.mkdir()
        self.database = self.top / "store.sqlite"  # never created


@pytest.fixture
def c(tmp_path):
    return Children(tmp_path)


def assert_marker_last(stdout, status):
    lines = stdout.splitlines()
    assert lines, "nothing on stdout"
    assert lines[-1] == f"{MARKER} {status}"
    assert sum(line.startswith(MARKER) for line in lines) == 1, "the marker twice"


def assert_one_refusal_line(done, text=None):
    assert done.returncode == 2, done.stdout + done.stderr
    assert "Traceback" not in done.stderr
    lines = done.stderr.splitlines()
    assert len(lines) == 1, done.stderr
    assert lines[0].startswith("!! "), done.stderr
    assert not lines[0].startswith("!! !!"), done.stderr
    if text is not None:
        assert text in lines[0]
    assert_marker_last(done.stdout, 2)


class TestTheOutcomes:
    """A return, `sys.exit(2)`, `sys.exit(1)` and a `RuntimeError`: the state and code recorded,
    the wrapper's own exit status, and the marker last on stdout and in `stdout.log`."""

    @pytest.mark.parametrize(
        "behaviour, state, code",
        [
            ("return", "done", 0),
            ("exit-2", "failed", 2),
            ("exit-1", "failed", 1),
            ("raise", "failed", 1),
        ],
    )
    def test_each_outcome(self, c, behaviour, state, code):
        program = standin_program(c.top, behaviour, c.runs_root)
        done = run_stubbed(
            c.runs_root, program, wrapper_argv(c.database, slug=behaviour)
        )
        assert done.returncode == code, done.stdout + done.stderr
        run = only_run(c.runs_root)
        status = read_json(run / "status.json")
        assert (status["state"], status["exit_code"]) == (state, code)
        # the marker is never the stage
        assert status["stage"] == f"{TITLE}, all work items complete"
        assert_marker_last(done.stdout, code)
        assert_marker_last((run / "stdout.log").read_text(), code)
        stderr_log = (run / "stderr.log").read_text()
        if behaviour == "raise":
            assert "Traceback" in stderr_log
            assert f"RuntimeError: {ERROR_TEXT}" in stderr_log
            assert "Traceback" in done.stderr
        else:
            assert "Traceback" not in done.stderr
        assert not c.database.exists()


class TestTheMarkerIsALineOfItsOwn:
    """A program whose last write ends without a newline, as a signal handler raising between
    `print`'s text and its newline leaves it: the marker still starts a line of its own, so that
    `interrupt_when.py`'s `startswith` finds it."""

    def test_after_an_unfinished_line(self, c):
        program = standin_program(c.top, "mid-line", c.runs_root)
        done = run_stubbed(
            c.runs_root, program, wrapper_argv(c.database, slug="mid-line")
        )
        assert done.returncode == 0, done.stdout + done.stderr
        for text in (done.stdout, (only_run(c.runs_root) / "stdout.log").read_text()):
            assert text.splitlines()[-2] == MID_LINE
            assert_marker_last(text, 0)


class TestBeginsRefusal:
    """A store that an unfinished run in the same runs root names is refused by `begin`: exit 2,
    one `!! ` line naming `python -m runregistrykit end`, and nothing created. Once that run is
    ended, the same registration is accepted."""

    def a_hard_killed_run(self, c, request):
        child = subprocess.Popen(
            [
                sys.executable,
                "-c",
                CHILD,
                str(c.runs_root),
                str(REPO_ROOT),
                str(c.database),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT),
            env=subprocess_env(),
        )
        request.addfinalizer(lambda: reap(child))
        path = child.stdout.readline().strip()
        if not path:
            child.kill()
            child.wait(timeout=60)
            pytest.fail(f"the child began no run: {child.stderr.read()}")
        child.kill()
        assert child.wait(timeout=60) == -signal.SIGKILL
        assert read_json(Path(path) / "status.json")["state"] == "running"
        return Path(path)

    def end(self, c, run_id):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "runregistrykit",
                "end",
                run_id,
                "--reason",
                "a dead child in a test; ended by the test",
                "--root",
                str(c.runs_root),
            ],
            cwd=str(REPO_ROOT),
            env=subprocess_env(),
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )

    def test_refused_then_accepted_after_end(self, c, request):
        dead = self.a_hard_killed_run(c, request)
        listing = sorted(os.listdir(c.runs_root))
        program = standin_program(c.top, "return", c.runs_root)
        argv = wrapper_argv(c.database, slug="resume")

        refused = run_stubbed(c.runs_root, program, argv)
        assert_one_refusal_line(refused, "python -m runregistrykit end")
        assert dead.name in refused.stderr
        assert refused.stderr.rstrip().endswith("No run directory was created"), (
            refused.stderr
        )
        assert sorted(os.listdir(c.runs_root)) == listing
        assert not program.with_suffix(".json").exists(), "the program ran"

        ended = self.end(c, dead.name)
        assert ended.returncode == 0, ended.stdout + ended.stderr
        assert read_json(dead / "status.json")["state"] == "lost"

        accepted = run_stubbed(c.runs_root, program, argv)
        assert accepted.returncode == 0, accepted.stdout + accepted.stderr
        made = set(os.listdir(c.runs_root)) - set(listing)
        assert len(made) == 1
        status = read_json(c.runs_root / made.pop() / "status.json")
        assert (status["state"], status["exit_code"]) == ("done", 0)
        assert_marker_last(accepted.stdout, 0)


class TestTheRefusalsBeforeBegin:
    """The real script, no stub: each refusal is exit 2, one `!! ` line on stderr, no traceback,
    the marker last on stdout, and `var/runs` as it was."""

    def refuse(self, c, argv, text):
        before = var_state()
        done = run_the_script(argv)
        assert_one_refusal_line(done, text)
        assert var_state() == before, "a refused run changed var/"
        assert not c.database.exists()

    def argv(self, c, main_args=None, drop=None, **replace):
        argv = wrapper_argv(c.database, main_args=main_args)
        if drop is not None:
            at = argv.index(f"--{drop}")
            del argv[at : at + 2]
        for name, value in replace.items():
            argv[argv.index(f"--{name}") + 1] = value
        return argv

    @pytest.mark.parametrize("name", ["campaign", "prompt", "register", "purpose"])
    def test_each_of_the_four_flags_missing(self, c, name):
        self.refuse(
            c,
            self.argv(c, drop=name),
            f"the following arguments are required: --{name}",
        )

    def test_an_empty_flag(self, c):
        self.refuse(c, self.argv(c, purpose="  "), "--purpose is empty")

    def test_no_bare_double_dash(self, c):
        argv = self.argv(c)
        del argv[argv.index("--")]
        self.refuse(c, argv, "main.py's arguments follow a bare --")

    def test_no_database(self, c):
        self.refuse(
            c,
            self.argv(c, main_args=["--ray-address", ADDRESS]),
            "main.py's arguments: no --database",
        )

    def test_an_empty_database(self, c):
        self.refuse(
            c,
            self.argv(c, main_args=["--database", "", "--ray-address", ADDRESS]),
            "--database is empty",
        )

    def test_an_unrecognised_main_py_option(self, c):
        self.refuse(
            c,
            self.argv(
                c,
                main_args=[
                    "--database",
                    str(c.database),
                    "--ray-address",
                    ADDRESS,
                    "--no-such-option",
                ],
            ),
            "main.py's arguments: unrecognized arguments: --no-such-option",
        )

    def test_inventory(self, c):
        self.refuse(
            c,
            self.argv(
                c,
                main_args=[
                    "--database",
                    str(c.database),
                    "--ray-address",
                    ADDRESS,
                    "--inventory",
                ],
            ),
            "--inventory is not registered",
        )

    def test_no_ray_address(self, c):
        # main.py's parser refuses it (config/argument_parser.py: --ray-address is required)
        self.refuse(
            c,
            self.argv(c, main_args=["--database", str(c.database)]),
            "main.py's arguments: the following arguments are required: --ray-address",
        )


class TestHelp:
    def test_the_wrappers_help(self):
        before = var_state()
        done = run_the_script(["--help"])
        assert done.returncode == 0, done.stderr
        assert "usage: registered_run.py" in done.stdout
        assert done.stderr == ""
        assert_marker_last(done.stdout, 0)
        assert var_state() == before

    def test_main_pys_help_registers_nothing(self, c):
        before = var_state()
        done = run_the_script(wrapper_argv(c.database, main_args=["--help"]))
        assert done.returncode == 0, done.stderr
        assert "--ray-address" in done.stdout
        assert "registered as" not in done.stdout
        assert_marker_last(done.stdout, 0)
        assert var_state() == before
