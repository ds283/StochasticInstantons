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

"""Launch a StochasticInstanton `main.py` run as a registered run (rrk-adoption prompt 03; campaign
README §2.2).

Usage, from the repository root (`main.py`'s arguments follow a bare `--`, verbatim):

    PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --campaign C --prompt N \\
        --register SLUG --purpose "one line" -- <main.py's arguments>

The four flags are required. The repository root is put first on `sys.path` by this file, so it
also runs without `PYTHONPATH`. A run launched as `main.py` itself, without this file, is recorded
nowhere, and stays possible (campaign README §6.0, R2).

WHAT IT CHANGES. Nothing of `main.py`. `main.py` is run by `runpy.run_path` as `__main__`, from its
own file, with `sys.argv` set to `[main.py, *its arguments]`: its text is never read, substituted
or compiled here, and it parses its own arguments again. What this file touches is its own process:

  1. **before anything starts** (before Ray, before `main.py` runs) it parses `main.py`'s arguments
     with `main.py`'s own parser (`config.argument_parser.create_argument_parser`, so that a
     `--database` given in a `--config` YAML file is seen), refuses what would be recorded wrongly,
     and calls `runregistrykit.begin`, which writes the run's manifest under `var/runs/`
     (`register`). The manifest's `script` is `main.py`, so that its hash is the hash of what
     computed (P4); `results` is the database, made absolute;
  2. it replaces `sys.stdout` and `sys.stderr` by proxies (`RegisteredStream`) that pass every write
     through unaltered and copy it into the run directory's `stdout.log` and `stderr.log`. stdout's
     proxy keeps the heartbeat and the stage in `status.json` current; stderr's never beats;
  3. it wraps `ray.init`, so that its own signal handler replaces Ray's straight after Ray's is
     installed (SIGNALS, below). The wrapper passes `main.py`'s arguments to the real `ray.init`
     unchanged: `main.py` attaches to the cluster its `--ray-address` names (`main.py:131`);
  4. once `main.py` has returned or raised, and its `with ShardedPool` (`main.py:1273`) has closed,
     it records how the run ended, `done`, `failed` or `killed`, with the store's fingerprint
     (`finish_after_exec`);
  5. it prints `** driver exit status N` as the last line on stdout, on a line of its own, and
     exits as `main.py` would have, with `main.py`'s own exception re-raised so that its traceback
     is what it always was (`run`). It is `build.sh`'s marker, which `interrupt_when.py` reads.

**What the heartbeat means, exactly** (the manifest's `heartbeat_means`, `HEARTBEAT_MEANS`). The
work happens in Ray tasks and actors, so a beat from this process cannot say that any of them is
progressing. A beat is taken from a line on stdout, at most once every `BEAT_MIN_INTERVAL` (30 s),
or at once when the line changes the stage (a `** ` banner, or a progress or completion line of
RayWorkPool's), and the line is the stage. RayWorkPool (`raypoolkit/RayWorkPool.py:563-600` at
`v0.3.0`) prints a progress line only after `ray.wait` has returned completed work, and only when
more than `NOTIFY_MIN_INTERVAL` (60 s) has passed since its last one **and** either
`NOTIFY_TIME_INTERVAL` (300 s) has passed or more than `NOTIFY_BATCH_SIZE` (500) queue events have
completed since it: RayPoolKit's defaults, which no `RayWorkPool(` call in `main.py` overrides. So a
fresh beat from it means work completed within about five minutes. Several of `main.py`'s queues
are silent (`title=None`). Ray also forwards the workers' own output to the driver's stdout, from a
thread of its own (`ray/_private/worker.py:2192`, `print_to_stdstream`), so a worker's line beats
too; it carries Ray's `(... pid=...)` prefix, which no stage pattern matches, so it does not move
the stage. The converse does not hold: a stage that prints nothing for longer than the staleness
window (900 s, `list --stale-after`) -- a queue whose items each take longer than that -- is
reported stale while it works, and the gradient branch's solves have run for hours each. Stale
means go and look.

SIGNALS. `register` installs `terminal` for `SIGTERM` and `SIGINT`: before Ray is up a signal is
recorded `killed`, `128 + signum`, and the process then dies by the default disposition, without
unwinding. `ray.init` installs its own `SIGTERM` handler, `sys.exit(signum)`, at its start
(`ray/_private/worker.py:1656-1661` at Ray 2.55.1; and absl's at the C level, which aborts the
process about 3 s later unless `signal.alarm(0)` cancels it, which is why a `SIGTERM`ed SI driver
has been seen to exit 134), replacing `terminal`. So the `ray.init` wrapper installs
`install_killed_handler`'s handler for both signals as soon as the real `ray.init` returns. That
handler records `killed`, `128 + signum`, at once and without a fingerprint (the pool is still
open), then raises `SystemExit(128 + signum)`, which unwinds `main.py`; `finish_after_exec` then
cancels any alarm, records `killed` again with the fingerprint, shuts Ray down and exits with
`128 + signum`. This is SecondaryGWKit's design (`RunDrivers/scoped_pipeline_run.py`; its
`docs/a3-v2-readiness-audit.md` S1-S4, measured on a Ray it started itself), carried through
ChamPBH's `RunDrivers/registered_run.py`. rrk-adoption prompt 04 measures what Ray 2.55.1,
attached to SI's external cluster, installs (P9); until then nothing here assumes that it installs
nothing.

**No marker** means the process died of a signal without unwinding: a `SIGKILL`, or a `SIGTERM` or
`SIGINT` before `ray.init`, which `terminal` records `killed` and then re-raises with the default
disposition. A `SIGKILL` records nothing at all, and the run stays `running` until a person ends it
with `python -m runregistrykit end` (`.claude/rules/run-registry.md`, the route after a hard kill).

REFUSALS. Each is one `!! ` line on stderr, exit status 2, before `begin`, so that nothing is
recorded, as `main.py`'s own refusals exit 2 (`main.py:114`, `:129`): a missing or empty flag of
this file's own; no bare `--`; `main.py`'s arguments refused by `main.py`'s own parser (a missing
`--ray-address` among them); no database (`main.py` would print its help and `sys.exit()` with no
code, `main.py:97-99`, which would be recorded `done`); an empty one; and `--inventory` (it reads
the closed store read-only and starts no Ray: run `main.py --inventory` on its own, R5). `main.py`'s
other checks (`--drop`, the address) are not repeated: a run `main.py` refuses after registration is
recorded `failed` with its exit code, 2, which is true. A store that an unfinished run names is
refused by `begin`, whose text names `python -m runregistrykit end`; nothing is created.

The test seam is `main(argv=None, *, program=MAIN_PY, runs_root=None)`: a test runs a stand-in
program into a temporary runs root. The script's entry is `run()`, which adds the refusal print,
the marker and the exit status.
"""

import argparse
import os
import re
import runpy
import signal
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = REPO_ROOT / "main.py"

# so that the script runs without PYTHONPATH: `config` and `RunDrivers` are packages of the root
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class Refusal(RuntimeError):
    """A check that stops this driver before anything is registered or started, and `begin`'s own
    refusal. `run` prints it as one `!! ` line on stderr and exits 2, with no traceback, as
    `main.py`'s own refusals exit. It is a `RuntimeError` on purpose, so that every caller that
    catches `RuntimeError` still does. A failure during the work, and a `runregistrykit.ConfigError`,
    are not refusals and keep their traceback.
    """


# the line `run` prints last on stdout: build.sh's marker, which interrupt_when.py reads
EXIT_MARKER = "** driver exit status"

# =================================================================================================
# the heartbeat

# How often the heartbeat may be rewritten. status.json is fsynced and renamed on every beat, so a
# beat is throttled rather than written per line; this is well inside RunRegistryKit's 900 s
# staleness window.
BEAT_MIN_INTERVAL = 30.0

# RayWorkPool's notify defaults at RayPoolKit v0.3.0 (DEFAULT_NOTIFY_MIN_INTERVAL,
# DEFAULT_NOTIFY_TIME_INTERVAL and DEFAULT_NOTIFY_BATCH_SIZE, raypoolkit/RayWorkPool.py:30-32),
# which no RayWorkPool( call in main.py overrides. main.py is never imported here; a test checks
# that these equal RayPoolKit's and, by ast, that main.py passes no notify_ keyword.
NOTIFY_MIN_INTERVAL = 60.0
NOTIFY_TIME_INTERVAL = 300.0
NOTIFY_BATCH_SIZE = 500

HEARTBEAT_MEANS = (
    "Refreshed when the run writes a line to stdout, at most once per {interval:.0f} s, or at "
    "once when the line changes the stage, and the line it came from is the `stage` in "
    "status.json. RayWorkPool prints a progress line only after ray.wait has returned completed "
    "work, never sooner than {notify_min:.0f} s after its last one, and otherwise only once "
    "{notify_time:.0f} s have passed or more than {notify_batch} queue events have completed "
    "since it (RayPoolKit's defaults, which main.py does not override), so a fresh heartbeat from "
    "it means work completed within about five minutes. Several of main.py's queues are silent "
    "(title=None). Ray also forwards the workers' own output to the driver's stdout, so a "
    "worker's line beats too, without moving the stage. It does NOT mean any Ray task or actor "
    "is progressing, and the converse does not hold: a stage that prints nothing for longer than "
    "the staleness window ({stale:.0f} s, `list --stale-after`), such as a queue whose items each "
    "take longer than that, is reported stale while it works, and the gradient branch's solves "
    "have run for hours each. Stale means go and look."
)

# RayWorkPool's and main.py's own vocabulary, which this file only reads: a `** TITLE` banner
# (RayWorkPool.py:206, and main.py's own, `** BUILDING PARAMETER SAMPLING GRIDS`, `** STAGE 4:
# COMPACTION FUNCTIONS`, the `** ... LOOKUP:` lines and the rest), the progress line
# (RayWorkPool.py:588) and the completion line (RayWorkPool.py:606). A `>> ` line is information
# inside a stage in this repository (main.py:101's provenance, DatastoreKit's open and prune lines,
# main.py's grid counts, and this file's own registration lines), never a banner, so the banner
# pattern matches `** ` only. The progress and completion patterns are SecondaryGWKit's, unchanged.
_STAGE_BANNER = re.compile(r"^\s*\*\*\s+(\S.*?)\s*$")
_QUEUE_PROGRESS = re.compile(
    r"(\d+)/(\d+)\s+work items remaining\s*=\s*([\d.]+)%\s+complete"
)
_QUEUE_COMPLETE = re.compile(r"ALL WORK ITEMS COMPLETE")


class StageTracker:
    """Where the run has got to, read off its own output.

    The pipeline reports progress per stage and per work queue, never as one total, so there is
    no honest denominator for `units_done`/`units_total`, and this reports a sentence instead:
    the last banner, with the last progress line's figures, or "all work items complete".
    """

    def __init__(self):
        self.title = None
        self.stage = None

    def feed(self, line) -> bool:
        """Read one line; return True if the stage changed."""
        before = self.stage
        banner = _STAGE_BANNER.match(line)
        if banner is not None:
            self.title = banner.group(1)
            self.stage = self.title
        elif self.title is not None:
            progress = _QUEUE_PROGRESS.search(line)
            if progress is not None:
                remaining, total, percent = progress.groups()
                self.stage = (
                    f"{self.title}, {percent}% "
                    f"({remaining} of {total} work items remaining)"
                )
            elif _QUEUE_COMPLETE.search(line):
                self.stage = f"{self.title}, all work items complete"
        return self.stage != before


class RegisteredStream:
    """`sys.stdout` (or `sys.stderr`), with a copy into the run directory and, for stdout, a
    heartbeat off the back of it.

    Every write is passed to the real stream first, unaltered and unconditionally. The copy, the
    stage tracking and the beat come after it, and are wrapped so that a failure in any of them
    cannot cost the run a line of output or an exception it did not raise. Attribute lookups that
    are not this class's go to the real stream, so `fileno`, `isatty`, `encoding` and `buffer` are
    whatever they were.

    Ray writes the workers' output into the driver's `sys.stdout` and `sys.stderr` from a thread
    of its own (`ray/_private/worker.py:2192`, `print_to_stdstream`), so the bookkeeping runs on two
    threads. It is held under a re-entrant lock: two threads cannot garble a line's stage, and a
    signal handler that prints on the main thread while the main thread holds the lock does not
    deadlock. The real write is outside the lock.
    """

    def __init__(
        self,
        stream,
        run,
        tracker,
        copy_to=None,
        interval=BEAT_MIN_INTERVAL,
        beats=True,
    ):
        self._stream = stream
        self._run = run
        self._tracker = tracker
        self._interval = interval
        self._beats = beats
        self._pending = ""
        self._last_beat = 0.0
        # whether the last write left a line unfinished: see `mid_line`
        self._mid_line = False
        self._lock = threading.RLock()
        self._copy = None
        if copy_to is not None:
            try:
                self._copy = open(copy_to, "a", buffering=1)
            except OSError:
                self._copy = None

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def write(self, text):
        written = self._stream.write(text)
        if text:
            self._mid_line = not text.endswith("\n")
        # the output is the run's; the bookkeeping is ours, and never costs it an exception
        try:
            with self._lock:
                self._observe(text)
        except Exception:  # noqa: BLE001
            pass
        return written

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        self._stream.flush()
        copy = self._copy
        if copy is not None:
            try:
                copy.flush()
            except (OSError, ValueError):
                pass

    @property
    def mid_line(self) -> bool:
        """True when the last write ended without a newline. `print` writes its text and its
        newline separately, and a signal handler that raises between the two leaves the line
        unfinished; `run` then starts the marker on a line of its own, so that it is a whole
        line, as `interrupt_when.py`'s `startswith` reads it."""
        return self._mid_line

    def stop_beating(self):
        """Take no more beats and read no more stages; the copy goes on. `run` calls it before it
        prints the marker, which is a `** ` line that would otherwise become the stage after the
        run's terminal state was written."""
        with self._lock:
            self._beats = False

    def close_copy(self):
        """Close the run directory's copy, leaving the real stream open.

        Called only on the clean path, so that a failing run's traceback, printed by the
        interpreter after `run` unwinds, still reaches `stderr.log`. A killed or failed run loses
        nothing by not reaching it: the copy is line-buffered, and the kernel closes what is
        left."""
        with self._lock:
            copy, self._copy = self._copy, None
        if copy is not None:
            try:
                copy.close()
            except OSError:
                pass

    def _observe(self, text):
        if self._copy is not None:
            # a copy that has failed once is dropped rather than retried, and must not cost the
            # stage tracking or the heartbeat below
            try:
                self._copy.write(text)
            except Exception:  # noqa: BLE001
                self._copy = None
        if not self._beats:
            return
        self._pending += text
        if "\n" not in self._pending:
            return
        *lines, self._pending = self._pending.split("\n")
        changed = False
        for line in lines:
            changed = self._tracker.feed(line) or changed
        now = time.monotonic()
        if changed or now - self._last_beat >= self._interval:
            self._last_beat = now
            self._run.heartbeat(stage=self._tracker.stage)


def terminal_state(code) -> str:
    """The state to record for a `SystemExit` out of `main.py` **that no signal caused**.

    A signal after `ray.init` is recorded by `install_killed_handler`'s handler, and
    `finish_after_exec` keeps that record whatever then reaches it; this is used only when that
    handler did not fire. `SystemExit(15)` is still `killed`: Ray's own handler, `sys.exit(signum)`,
    is installed at the start of `ray.init` and this driver's only after it returns, so a `SIGTERM`
    that lands while `ray.init` runs reaches the driver as `SystemExit(15)` (read, not measured).
    `main.py` never exits 15 of its own accord: it exits 0, 1 or 2, or with a traceback.
    """
    if code is None:
        return "done"
    if code == int(signal.SIGTERM):
        return "killed"
    return "done" if code == 0 else "failed"


# =================================================================================================
# signals once Ray is up. Nothing here imports `ray`: the driver hands in `ray.shutdown`, and a test
# hands in a stand-in.

# the signals the handler takes. ray.init installs only SIGTERM on a driver; SIGINT would otherwise
# be Python's KeyboardInterrupt, recorded `failed`.
KILLED_SIGNALS = (signal.SIGTERM, signal.SIGINT)


class SignalLatch:
    """Where the handler remembers the signal that ended the run, for the driver to read.

    The exit code cannot carry it: a `SystemExit(128 + signum)` raised inside `ray.wait` reaches
    the driver as `SystemExit(1)` (SecondaryGWKit's audit S1). One latch serves a whole run.
    Installing the handler again, as a second `ray.init` would, keeps it.

    - `signum` is the first signal that reached the handler **before `main.py`'s own outcome
      reached the driver**, or `None`. It is set first, before anything else the handler does.
    - `decided` is set by `finish_after_exec` when `main.py`'s own outcome reached it first. From
      then on a signal is noted and does not change the record.
    """

    def __init__(self):
        self.signum = None
        self.decided = False

    def decide(self):
        """Mark `main.py`'s own outcome as decided, unless a signal came first.

        Returns the remembered signal, or `None` when the outcome is `main.py`'s. A signal that
        lands between the test and the assignment runs the handler while `decided` is still
        false, so the handler raises out of this call with `signum` set: the caller treats that
        as a signal that came first."""
        if self.signum is None:
            self.decided = True
        return self.signum


def _say(stream, text):
    """One line to `stream` (by default `sys.stderr` as it is when the line is written).

    Never raises. A handler that prints while the main thread is inside a write to the same
    buffered stream gets CPython's `RuntimeError: reentrant call`; a line lost that way must not
    cost the handler the steps after it."""
    try:
        print(text, file=sys.stderr if stream is None else stream, flush=True)
    except Exception:  # noqa: BLE001
        pass


def _signal_name(signum):
    try:
        return signal.Signals(signum).name
    except ValueError:
        return f"signal {signum}"


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S %z")


def make_killed_handler(run, latch, stream=None):
    """The handler `install_killed_handler` installs, built but not installed (tests call it).

    `run` is the registered `Run`; `latch` is the run's `SignalLatch`.

    **Its first call, before `main.py`'s outcome is decided:**

    1. remembers the signal in `latch.signum`, first, so that nothing after it can lose it;
    2. writes `run.finish("killed", exit_code=128 + signum)`: no fingerprint, because the pool is
       still open, and at once, because nothing after it is guaranteed. A failure to write is
       printed, and does not stop step 4: `finish_after_exec` writes the state again;
    3. prints one line of its own to stderr naming the signal and the time, since Ray's
       `*** SIGTERM received` banner no longer prints once this handler is installed. A failure to
       print never stops step 4;
    4. raises `SystemExit(128 + signum)`, which unwinds `main.py`, its `with ShardedPool` included.

    **Any other call** -- a second signal during the cleanup, or a signal after `main.py`'s own
    outcome reached the driver (`SignalLatch.decided`) -- prints one line and returns, raising
    nothing and writing nothing. `SIGKILL` remains for a person who means it.
    """

    def killed_handler(signum, _frame):
        name = _signal_name(signum)
        if latch.signum is not None or latch.decided:
            why = (
                f"the run is already being stopped by {_signal_name(latch.signum)}"
                if latch.signum is not None
                else "main.py had already ended; its own outcome is being recorded"
            )
            _say(
                stream,
                f"** {name} at {_now()}: ignored, {why}. SIGKILL stops the process at once",
            )
            return
        latch.signum = signum
        code = 128 + signum
        if run is not None:
            try:
                run.finish("killed", exit_code=code)
            except Exception as e:  # noqa: BLE001
                _say(stream, f"** {name}: could not record killed at once: {e!r}")
        _say(
            stream,
            f"** {name} at {_now()}: "
            + (f"recorded killed, exit code {code}; " if run is not None else "")
            + f"stopping main.py; the process will exit with status {code}",
        )
        raise SystemExit(code)

    return killed_handler


def install_killed_handler(run, latch, stream=None):
    """Install the handler for `SIGTERM` and `SIGINT`. Call it **after** `ray.init` returns.

    `ray.init` installs Ray's own `SIGTERM` handlers, `sys.exit(signum)` in Python and absl's
    failure-signal handler in C. A Python handler installed after it replaces both at the C level,
    runs on the main thread inside `ray.wait` and `ray.get`, prints no banner and arms no alarm
    (SecondaryGWKit's audit S1). Returns the handler.
    """
    handler = make_killed_handler(run, latch, stream=stream)
    for signum in KILLED_SIGNALS:
        signal.signal(signum, handler)
    return handler


def finish_after_exec(run, exc, latch, shutdown, *, alarm=signal.alarm, stream=None):
    """What the driver does once `main.py` is over, with Ray up or not.

    `run` is the `Run`; `exc` the exception that ended `main.py`, or `None` if it returned;
    `latch` the run's `SignalLatch`; `shutdown` is `ray.shutdown` in the driver.

    **If the handler fired first** (`latch.signum`), whatever `exc` is -- `SystemExit(1)` out of a
    Ray wait, or a `RuntimeError` or `KeyboardInterrupt` from elsewhere -- the run was killed:

    1. `alarm(0)`, which cancels absl's abort if Ray's handler saw a signal first (audit S2);
    2. `run.finish("killed", exit_code=128 + signum, fingerprint=True)`, best-effort: the handler
       has written the state, and `main.py`'s `with ShardedPool` has unwound, so the store is
       closed;
    3. `shutdown()`;
    4. raises `SystemExit(128 + signum)`.

    **Otherwise** `main.py`'s own outcome is recorded: `done`/0 for a return,
    `terminal_state(exc.code)` for a `SystemExit`, `failed`/1 for anything else, each with the
    fingerprint. `alarm(0)` runs first here too, and `shutdown()` after the record. It then
    **returns**, and the caller re-raises `exc` with a bare `raise`, so the traceback is exactly
    the one it always was.

    **A signal once `main.py`'s outcome is decided** -- during this function's own fingerprint,
    for instance -- is noted by the handler and changes nothing.
    """
    try:
        signum = latch.decide()
    except BaseException:
        # the handler ran between decide()'s test and its assignment, and raised
        if latch.signum is None:
            raise
        signum = latch.signum

    remaining = alarm(0)
    if remaining:
        _say(
            stream,
            f"** cancelled an alarm with {remaining} s left: Ray's own signal handler ran",
        )

    if signum is None:
        if run is not None:
            if exc is None:
                run.finish("done", exit_code=0, fingerprint=True)
            elif isinstance(exc, SystemExit):
                run.finish(
                    terminal_state(exc.code), exit_code=exc.code, fingerprint=True
                )
            else:
                run.finish("failed", exit_code=1, fingerprint=True)
        _shut_down(shutdown, stream)
        return

    code = 128 + signum
    if exc is not None:
        _say(
            stream,
            f"** {_signal_name(signum)}: main.py ended with "
            f"{type(exc).__name__}{_code_text(exc)}; recording killed, exit code {code}",
        )
    try:
        if run is not None:
            try:
                run.finish("killed", exit_code=code, fingerprint=True)
            except Exception as e:  # noqa: BLE001
                _say(stream, f"** could not record killed with its fingerprint: {e!r}")
    finally:
        _shut_down(shutdown, stream)
    raise SystemExit(code)


def _shut_down(shutdown, stream):
    """`shutdown()`, once. A failure is printed and goes no further: it must not replace the
    exception the caller re-raises, nor the exit status a signal gave."""
    try:
        shutdown()
    except Exception as e:  # noqa: BLE001
        _say(stream, f"** ray.shutdown() raised {e!r}")


def _code_text(exc):
    return f"({exc.code!r})" if isinstance(exc, SystemExit) else ""


# =================================================================================================
# the arguments, and the refusals before begin()

_FLAGS = ("campaign", "prompt", "register", "purpose")

USAGE_TAIL = (
    "registered_run.py --campaign C --prompt N --register SLUG --purpose TEXT -- "
    "<main.py's arguments>"
)


def _refusing(what):
    """An `error` for an argparse parser that raises a `Refusal` instead of printing the usage and
    exiting 2: argparse's own error is two lines on stderr, where a refusal is one."""

    def error(message):
        raise Refusal(f"{what}: {message}")

    return error


def _wrapper_parser():
    parser = argparse.ArgumentParser(
        prog="registered_run.py",
        description="Run main.py as a registered run (RunRegistryKit). main.py's arguments "
        "follow a bare --, verbatim.",
        epilog=f"form: {USAGE_TAIL}",
    )
    parser.add_argument(
        "--campaign",
        required=True,
        help="the campaign that ordered the run, or the work a person's own launch serves",
    )
    parser.add_argument(
        "--prompt", required=True, help="the prompt that ordered the run"
    )
    parser.add_argument(
        "--register",
        required=True,
        metavar="SLUG",
        help="the run's slug: its directory is var/runs/<campaign>-<prompt>-<slug>-<time>",
    )
    parser.add_argument(
        "--purpose",
        required=True,
        help="one line a stranger can read saying what the run is for",
    )
    parser.error = _refusing("the wrapper's arguments")
    return parser


def parse_arguments(argv):
    """Split ``argv`` at its first bare `--`, parse both sides, and refuse what must not be
    registered. Returns ``(args, main_args, parsed, defaulted)``: this file's own `Namespace`,
    `main.py`'s arguments verbatim, `main.py`'s parse of them, and the option strings of `main.py`'s
    parser that took their default (neither on the command line nor in a config file).

    `main.py`'s arguments are parsed by `main.py`'s own parser, so that a `--database` given in a
    `--config` YAML file is seen. The parse is for reading only: `main.py` parses its own
    `sys.argv` again. `-- --help` prints `main.py`'s help and exits 0, and nothing is registered.
    """
    argv = list(argv)
    if "--" in argv:
        at = argv.index("--")
        own, main_args = argv[:at], argv[at + 1 :]
    else:
        own, main_args = argv, None

    parser = _wrapper_parser()
    if main_args is None and not any(a in ("-h", "--help") for a in own):
        raise Refusal(f"main.py's arguments follow a bare --: {USAGE_TAIL}")
    args = parser.parse_args(own)
    if main_args is None:  # not reached: --help has exited
        raise Refusal(f"main.py's arguments follow a bare --: {USAGE_TAIL}")
    for name in _FLAGS:
        if not getattr(args, name).strip():
            raise Refusal(f"the wrapper's arguments: --{name} is empty")

    from config.argument_parser import create_argument_parser

    main_parser = create_argument_parser()
    main_parser.error = _refusing("main.py's arguments")
    parsed = main_parser.parse_args(main_args)
    # configargparse records where each value came from; "defaults" holds the options left at
    # their default, by their last option string
    defaulted = frozenset(
        main_parser.get_source_to_settings_dict().get("defaults", {}).keys()
    )

    if parsed.database is None:
        raise Refusal(
            "main.py's arguments: no --database, on the command line or in a --config file "
            "(main.py would print its help and exit with no code, which would be recorded done)"
        )
    if not parsed.database.strip():
        raise Refusal("main.py's arguments: --database is empty")
    if parsed.inventory:
        raise Refusal(
            "main.py's arguments: --inventory is not registered. It reads the closed store "
            "read-only and starts no Ray; run main.py --inventory on its own"
        )
    return args, main_args, parsed, defaulted


# =================================================================================================
# the scope: one line from main.py's parsed arguments as given, never its grid (main.py builds that
# itself)

# a choice given as values reads as the values up to this many, and otherwise as a count and range
SCOPE_MAX_VALUES = 6


def _number(value) -> str:
    return f"{value:g}"


def _values(values, unit=None) -> str:
    suffix = f" {unit}" if unit else ""
    if len(values) <= SCOPE_MAX_VALUES:
        return ", ".join(_number(v) for v in values) + suffix
    return (
        f"{len(values)} values, {_number(min(values))}–{_number(max(values))}{suffix}"
    )


def _decades(low, high, per_decade, unit=None) -> str:
    suffix = f" {unit}" if unit else ""
    return f"10^{_number(low)}–10^{_number(high)}{suffix}, {_number(per_decade)} per decade"


def _axis(name, values, low, high, samples) -> str:
    if values:
        return f"{name} {_values(values)}"
    plural = "" if samples == 1 else "s"
    return f"{name} {_number(low)}–{_number(high)}, {samples} sample{plural}"


def describe_scope(parsed, defaulted=frozenset()) -> str:
    """The manifest's `scope`, from `main.py`'s parsed arguments as given: the config file;
    `--targets`; the potential type and its own parameter (`m` for Quadratic, `lambda` for Quartic,
    the one `config/model_list.py` reads); the `N_init`, `N_final` and `delta_Nstar` choices, or
    `--sample-grid-csv` when it is given (it replaces them); `--n-collocation-points` and
    `--alpha-regularization` where given (not in ``defaulted``); `--no-store-values` and
    `--stop-after` where given; the shards; the job name.

    A choice given as values reads as the values, or as a count and a range when there are more
    than `SCOPE_MAX_VALUES`; a choice given as a range reads as its arguments."""
    parts = [f"config {parsed.config}" if parsed.config else "no config file"]
    parts.append(
        "targets " + (", ".join(parsed.targets) if parsed.targets else "none")
    )
    parts.append(f"potential {parsed.potential_type}")
    if parsed.potential_type == "Quadratic":
        if parsed.m_values_Mp:
            parts.append(f"m {_values(parsed.m_values_Mp, 'Mp')}")
        else:
            parts.append(
                "m "
                + _decades(
                    parsed.log10_m_low_Mp,
                    parsed.log10_m_high_Mp,
                    parsed.samples_per_log10_m,
                    "Mp",
                )
            )
    elif parsed.potential_type == "Quartic":
        if parsed.lambda_values:
            parts.append(f"lambda {_values(parsed.lambda_values)}")
        else:
            parts.append(
                "lambda "
                + _decades(
                    parsed.log10_lambda_low,
                    parsed.log10_lambda_high,
                    parsed.samples_per_log10_lambda,
                )
            )
    if parsed.sample_grid_csv:
        parts.append(f"sample grid {parsed.sample_grid_csv}")
    else:
        parts.append(
            _axis(
                "N_init",
                parsed.N_init_values,
                parsed.N_init_low,
                parsed.N_init_high,
                parsed.N_init_samples,
            )
        )
        parts.append(
            _axis(
                "N_final",
                parsed.N_final_values,
                parsed.N_final_low,
                parsed.N_final_high,
                parsed.N_final_samples,
            )
        )
        parts.append(
            _axis(
                "delta_Nstar",
                parsed.delta_Nstar_values,
                parsed.delta_Nstar_low,
                parsed.delta_Nstar_high,
                parsed.delta_Nstar_samples,
            )
        )
    if "--n-collocation-points" not in defaulted:
        parts.append(f"n_collocation_points {_values(parsed.n_collocation_points)}")
    if "--alpha-regularization" not in defaulted:
        parts.append(f"alpha_regularization {_values(parsed.alpha_regularization)}")
    if parsed.no_store_values:
        parts.append("--no-store-values")
    if parsed.stop_after:
        parts.append(f"stop after {', '.join(parsed.stop_after)}")
    parts.append(f"{parsed.shards} shards")
    parts.append(f"job {parsed.job_name}" if parsed.job_name else "no job name")
    return "; ".join(parts)


# =================================================================================================
# registration


def register(
    args, parsed, argv, *, defaulted=frozenset(), program=MAIN_PY, runs_root=None
):
    """Write the manifest, take over both output streams, and arrange a terminal state. Returns the
    `Run`.

    Called **before** Ray starts and before `program` runs, so that a crash in the first instant
    still leaves a record of what was running and what it was for. ``args``, ``parsed`` and
    ``defaulted`` are `parse_arguments`'; ``argv`` is this file's own arguments (`sys.argv[1:]` in
    production), recorded after this file's path as the manifest's `argv`.

    ``script`` is ``program``, `main.py` in production (P4), so that the manifest's hash is the hash
    of what computed. `begin` takes `git_head` and `git_dirty` from that file's directory.
    ``client_root`` is this repository whatever the program's directory, so that the config, the
    fingerprinter and the runs root are its own. ``runs_root`` is `begin`'s ``root``: `None`, in
    production, is the config's `var/runs`; a test passes a temporary one.

    Its three lines (the run id, the manifest, the `list` command) begin `>> `, this repository's
    form for information, which no stage pattern reads: they reach stdout and `stdout.log`, and
    the stage stays unset until `main.py`'s first banner.
    """
    try:
        import runregistrykit
    except ImportError as exc:  # pragma: no cover -- an operator-facing message
        raise Refusal(
            "the runregistrykit package is missing from this venv; install requirements.txt "
            "into it (./venv/bin/pip install -r requirements.txt)"
        ) from exc

    try:
        run = runregistrykit.begin(
            campaign=args.campaign,
            prompt=args.prompt,
            slug=args.register,
            purpose=args.purpose,
            argv=[str(Path(__file__).resolve()), *argv],
            script=str(program),
            # the store the run's results live in, which the registry names and never writes; not
            # `checkpoint`, which is a unit ledger this run does not have
            results=os.path.abspath(parsed.database),
            scope=describe_scope(parsed, defaulted),
            heartbeat_means=HEARTBEAT_MEANS.format(
                interval=BEAT_MIN_INTERVAL,
                notify_min=NOTIFY_MIN_INTERVAL,
                notify_time=NOTIFY_TIME_INTERVAL,
                notify_batch=NOTIFY_BATCH_SIZE,
                stale=runregistrykit.DEFAULT_STALE_AFTER,
            ),
            root=runs_root,
            client_root=str(REPO_ROOT),
        )
    except runregistrykit.ConfigError:
        raise
    except RuntimeError as e:
        raise Refusal(str(e)) from e

    def terminal(signum, _frame):
        """Record the death, then die exactly as the default handler would have."""
        run.finish("killed", exit_code=128 + signum)
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    for signum in KILLED_SIGNALS:
        signal.signal(signum, terminal)

    sys.stdout = RegisteredStream(
        sys.stdout,
        run,
        StageTracker(),
        copy_to=run.stdout_path,
        interval=BEAT_MIN_INTERVAL,
    )
    # stderr is copied but does not beat and carries no stage: it is where the traceback of a
    # failed run goes, and Ray's own warnings land there too, which must not count as progress
    sys.stderr = RegisteredStream(
        sys.stderr, run, StageTracker(), copy_to=run.stderr_path, beats=False
    )
    print(
        f">> registered_run: registered as {run.id}\n"
        f">>   manifest {run.manifest_path}\n"
        f">>   list it with: ./venv/bin/python -m runregistrykit list",
        flush=True,
    )
    return run


# =================================================================================================
# the run


def main(argv=None, *, program=MAIN_PY, runs_root=None):
    """Parse, register, wrap `ray.init`, run ``program`` and record how it ended.

    Returns when ``program`` returned; raises ``program``'s own exception after recording it;
    raises `SystemExit(128 + signum)` after a signal; raises `Refusal` before anything is
    registered. ``argv`` defaults to `sys.argv[1:]`. ``program`` is `main.py` in production and a
    stand-in in a test; ``runs_root`` is `register`'s.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    args, main_args, parsed, defaulted = parse_arguments(argv)

    # (R) register the run, before Ray and before the program runs
    run = register(
        args, parsed, argv, defaulted=defaulted, program=program, runs_root=runs_root
    )

    # (S) once Ray is up, this driver's signal handler replaces Ray's. The real ray.init is
    #     called with the program's own arguments, unchanged
    import ray

    _real_ray_init = ray.init
    latch = SignalLatch()

    def _registered_ray_init(*init_args, **init_kwargs):
        context = _real_ray_init(*init_args, **init_kwargs)
        install_killed_handler(run, latch)
        return context

    ray.init = _registered_ray_init

    # (P) the program, from its own file, as __main__, with its own arguments. runpy sets
    #     sys.argv[0] to the program's path while it runs, as `python main.py` would
    sys.argv = [str(program), *main_args]
    try:
        runpy.run_path(str(program), run_name="__main__")
    except BaseException as exc:
        # raises SystemExit(128 + signum) if a signal ended the program; otherwise records its
        # outcome and returns, and this re-raises with the copies still open, so that the
        # traceback the interpreter is about to print reaches stderr.log
        finish_after_exec(run, exc, latch, ray.shutdown)
        raise
    finish_after_exec(run, None, latch, ray.shutdown)


def exit_status(code) -> int:
    """The status the interpreter exits with for `SystemExit(code)`: `None` is 0, an `int` is
    itself, and anything else (a message, which it prints) is 1."""
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


def _proxies():
    return [s for s in (sys.stdout, sys.stderr) if isinstance(s, RegisteredStream)]


def run(argv=None, *, program=MAIN_PY, runs_root=None):
    """The script's entry: `main`, then the marker, then the exit.

    - a `Refusal` is printed as one `!! ` line on stderr, and the status is 2;
    - a `SystemExit` gives Python's own status (`exit_status`), and is re-raised;
    - a `KeyboardInterrupt` that reaches here (only before registration: afterwards a `SIGINT` is
      this driver's) gives 130, as the interpreter's own exit by `SIGINT` does, and is re-raised;
    - any other exception gives 1, and is re-raised, so that the interpreter prints its traceback
      after the marker; it reaches `stderr.log`, whose copy stays open.

    In every case every proxy stops beating, and then `** driver exit status N` is printed on
    stdout, with the status the process will exit with: the last line on stdout and in
    `stdout.log`, and never the `stage` in `status.json`. The copies are then closed on the clean
    path only.
    """
    status = 1
    clean = False
    try:
        main(argv, program=program, runs_root=runs_root)
        status, clean = 0, True
    except Refusal as exc:
        status = 2
        sys.stdout.flush()
        text = str(exc)
        # one "!! ", whatever the text began with
        _say(sys.stderr, f"!! {text[3:] if text.startswith('!! ') else text}")
        raise SystemExit(2) from None
    except SystemExit as exc:
        status = exit_status(exc.code)
        raise
    except KeyboardInterrupt:
        status = 128 + int(signal.SIGINT)
        raise
    except BaseException:
        status = 1
        raise
    finally:
        for proxy in _proxies():
            proxy.stop_beating()
        # on a line of its own, even after a line a signal left unfinished
        mid_line = isinstance(sys.stdout, RegisteredStream) and sys.stdout.mid_line
        _say(sys.stdout, ("\n" if mid_line else "") + f"{EXIT_MARKER} {status}")
        if clean:
            for proxy in _proxies():
                proxy.close_copy()


if __name__ == "__main__":
    run()
