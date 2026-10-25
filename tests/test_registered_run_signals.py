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

"""A signal to a registered run is recorded `killed`, and nothing it then does can say otherwise
(rrk-adoption prompt 03, W4, W5 and W6 test 4).

The subjects are `make_killed_handler`, `install_killed_handler` and `finish_after_exec` in
`RunDrivers/registered_run.py`, SecondaryGWKit's design carried through ChamPBH's. The handler is
called directly, with a stand-in run or a real `Run` in a temporary runs root; `ray.shutdown` and
`signal.alarm` are stand-ins. **One test runs a subprocess**: the wrapper with Ray stubbed
(`python -u tests/registered_run_helpers.py`) on a stand-in that waits, sent a real `SIGTERM` once
its banner is on stdout. The child is reaped by a cleanup registered before its first read. No Ray
is initialised, no store is opened, and nothing under `var/` is read or written.
"""

import io
import os
import signal
import subprocess
from pathlib import Path

import pytest
import runregistrykit

from RunDrivers import registered_run
from registered_run_helpers import (  # noqa: F401
    REPO_ROOT,
    TITLE,
    Recorder,
    no_ray_at_the_end,
    only_run,
    read_json,
    reap,
    standin_program,
    stubbed,
    subprocess_env,
    wrapper_argv,
)

SIGTERM = int(signal.SIGTERM)
SIGINT = int(signal.SIGINT)

FINGERPRINT_KEYS = ("fingerprint", "fingerprint_error", "fingerprint_sidecar")


class StandInRun:
    """Records every `finish` call as `(state, exit_code, fingerprint)`."""

    def __init__(self, fail=None):
        self.calls = []
        self.fail = fail

    def finish(self, state, exit_code=None, *, fingerprint=False):
        if self.fail is not None:
            raise self.fail
        self.calls.append((state, exit_code, fingerprint))
        return {"state": state, "exit_code": exit_code}


class Signals:
    def __init__(self, tmp_path):
        self.latch = registered_run.SignalLatch()
        self.out = io.StringIO()
        self.top = Path(tmp_path).resolve()
        self.runs_root = self.top / "runs"
        self.runs_root.mkdir()
        self.database = self.top / "store.sqlite"  # never created

    def handler(self, run):
        return registered_run.make_killed_handler(run, self.latch, stream=self.out)

    def a_real_run(self):
        return runregistrykit.begin(
            campaign="rrk-adoption",
            prompt="03",
            slug="killed-handler",
            purpose="a unit test of the killed handler, in a temporary directory",
            argv=["pytest"],
            results=str(self.database),
            root=str(self.runs_root),
            client_root=str(REPO_ROOT),
        )

    def fired(self, run, signum=SIGTERM):
        """The handler, fired as a signal during the program would fire it."""
        with pytest.raises(SystemExit) as raised:
            self.handler(run)(signum, None)
        return raised.value

    def after(self, run, exc, shutdown=None, alarm=None):
        """`finish_after_exec` with stand-ins: `(the SystemExit it raised or None, shutdown,
        alarm)`."""
        shutdown = Recorder() if shutdown is None else shutdown
        alarm = Recorder(0) if alarm is None else alarm
        try:
            registered_run.finish_after_exec(
                run, exc, self.latch, shutdown, alarm=alarm, stream=self.out
            )
        except SystemExit as e:
            return e, shutdown, alarm
        return None, shutdown, alarm


@pytest.fixture
def s(tmp_path):
    return Signals(tmp_path)


class TestTheHandler:
    def test_on_a_real_run_it_records_killed_143_at_once_without_a_fingerprint(self, s):
        run = s.a_real_run()
        raised = s.fired(run)
        assert raised.code == 143
        status = read_json(run.status_path)
        assert (status["state"], status["exit_code"]) == ("killed", 143)
        for key in FINGERPRINT_KEYS:
            assert key not in status
        assert s.latch.signum == SIGTERM
        lines = s.out.getvalue().splitlines()
        assert len(lines) == 1, lines
        assert "SIGTERM" in lines[0]
        assert "recorded killed, exit code 143" in lines[0]

    def test_a_second_signal_is_ignored_with_a_line(self, s):
        run = StandInRun()
        handler = s.handler(run)
        with pytest.raises(SystemExit):
            handler(SIGTERM, None)
        assert handler(SIGTERM, None) is None
        assert handler(SIGINT, None) is None
        assert run.calls == [("killed", 143, False)]
        assert s.latch.signum == SIGTERM
        lines = s.out.getvalue().splitlines()
        assert len(lines) == 3, lines
        assert "ignored" in lines[1]
        assert "SIGINT" in lines[2]
        assert "ignored" in lines[2]

    def test_sigint_gives_130(self, s):
        run = StandInRun()
        assert s.fired(run, SIGINT).code == 130
        assert run.calls == [("killed", 130, False)]

    def test_a_write_that_fails_does_not_stop_the_raise(self, s):
        run = StandInRun(fail=OSError("no space left on device"))
        assert s.fired(run).code == 143
        assert s.latch.signum == SIGTERM
        assert "could not record killed" in s.out.getvalue()

    def test_once_the_outcome_is_decided_a_signal_is_only_noted(self, s):
        run = StandInRun()
        assert s.latch.decide() is None
        assert s.handler(run)(SIGTERM, None) is None
        assert run.calls == []
        assert s.latch.signum is None
        assert "ignored" in s.out.getvalue()


class TestInstall:
    def test_it_takes_sigterm_and_sigint(self, s, request):
        saved = {n: signal.getsignal(n) for n in (signal.SIGTERM, signal.SIGINT)}

        def restore():
            for number, handler in saved.items():
                signal.signal(number, handler)

        request.addfinalizer(restore)
        handler = registered_run.install_killed_handler(None, s.latch, stream=s.out)
        assert signal.getsignal(signal.SIGTERM) is handler
        assert signal.getsignal(signal.SIGINT) is handler


class TestAfterASignal:
    """The handler fired during the program: `killed`, whatever then reaches the driver, with the
    fingerprint added."""

    @pytest.mark.parametrize(
        "exc",
        [
            SystemExit(1),
            SystemExit(143),
            SystemExit(None),
            KeyboardInterrupt(),
            RuntimeError("interrupted"),
            None,
        ],
        ids=[
            "SystemExit(1), out of ray.wait",
            "SystemExit(143)",
            "SystemExit(None)",
            "KeyboardInterrupt",
            "RuntimeError",
            "no exception: the program returned",
        ],
    )
    def test_it_is_killed_143_with_the_fingerprint_whatever_reaches_the_driver(
        self, s, exc
    ):
        run = StandInRun()
        s.fired(run)
        raised, shutdown, alarm = s.after(run, exc)
        assert run.calls == [("killed", 143, False), ("killed", 143, True)]
        assert raised is not None, "it did not exit"
        assert raised.code == 143
        assert alarm.calls == [((0,), {})]
        assert len(shutdown.calls) == 1

    def test_on_a_real_run_the_fingerprint_is_taken_and_the_state_stays_killed(self, s):
        run = s.a_real_run()
        s.fired(run)
        raised, _, _ = s.after(run, SystemExit(1))
        assert raised.code == 143
        status = read_json(run.status_path)
        assert (status["state"], status["exit_code"]) == ("killed", 143)
        # the fingerprint was taken: the store does not exist, and the attempt is recorded
        assert "does not exist" in status["fingerprint_error"]

    def test_the_alarm_is_cancelled_first(self, s):
        order = []
        run = StandInRun()
        s.fired(run)

        def alarm(seconds):
            order.append(("alarm", seconds))
            return 3

        raised, _, _ = s.after(
            run, SystemExit(1), shutdown=lambda: order.append("shutdown"), alarm=alarm
        )
        assert raised.code == 143
        assert order == [("alarm", 0), "shutdown"]
        assert "cancelled an alarm with 3 s left" in s.out.getvalue()


class TestWithNoSignal:
    """No signal: the program's own outcome, each with the fingerprint, then Ray shut down, and a
    return so that the caller re-raises."""

    @pytest.mark.parametrize(
        "exc, expected",
        [
            (None, ("done", 0)),
            (SystemExit(None), ("done", None)),
            (SystemExit(0), ("done", 0)),
            (SystemExit(1), ("failed", 1)),
            (SystemExit(2), ("failed", 2)),
            (SystemExit(15), ("killed", 15)),
            (RuntimeError("a real failure"), ("failed", 1)),
            (KeyboardInterrupt(), ("failed", 1)),
        ],
        ids=[
            "returned",
            "SystemExit(None)",
            "SystemExit(0)",
            "SystemExit(1)",
            "SystemExit(2)",
            "SystemExit(15), Ray's own handler",
            "RuntimeError",
            "KeyboardInterrupt",
        ],
    )
    def test_every_outcome_is_recorded_with_the_fingerprint(self, s, exc, expected):
        run = StandInRun()
        raised, shutdown, alarm = s.after(run, exc)
        assert raised is None
        assert run.calls == [expected + (True,)]
        assert len(shutdown.calls) == 1
        assert alarm.calls == [((0,), {})]
        assert s.latch.decided

    def test_a_shutdown_that_fails_does_not_replace_the_exception(self, s):
        def failing():
            raise RuntimeError("the raylet is gone")

        raised, _, _ = s.after(StandInRun(), SystemExit(1), shutdown=failing)
        assert raised is None
        assert "ray.shutdown() raised" in s.out.getvalue()


class TestARealSigterm:
    """The wrapper with Ray stubbed, on a stand-in that waits, sent a real `SIGTERM` once its
    banner is on stdout. The stand-in `ray.init` installs a Ray-like handler, which the wrapper's
    must replace."""

    def test_it_is_killed_143_and_exits_143_with_the_marker_last(self, s, request):
        program = standin_program(s.top, "wait", s.runs_root)
        child = subprocess.Popen(
            stubbed(s.runs_root, program, wrapper_argv(s.database, slug="sigterm")),
            cwd=str(REPO_ROOT),
            env=subprocess_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        request.addfinalizer(lambda: reap(child))
        seen = []
        while True:
            line = child.stdout.readline()
            if not line:
                child.kill()
                pytest.fail(f"no banner: {''.join(seen)}{child.stderr.read()}")
            seen.append(line)
            if line.rstrip("\n") == f"** {TITLE}":
                break
        os.kill(child.pid, signal.SIGTERM)
        out, err = child.communicate(timeout=120)
        assert child.returncode == 143, err
        stdout = "".join(seen) + out
        assert stdout.splitlines()[-1] == "** driver exit status 143"
        run = only_run(s.runs_root)
        assert (run / "stdout.log").read_text().splitlines()[-1] == (
            "** driver exit status 143"
        )
        status = read_json(run / "status.json")
        assert (status["state"], status["exit_code"]) == ("killed", 143)
        assert "fingerprint_error" in status  # taken after the program unwound
        # the marker is never the stage
        assert status["stage"] == TITLE
        assert "SIGTERM" in err
        assert "recorded killed, exit code 143" in err
        assert "Traceback" not in err
