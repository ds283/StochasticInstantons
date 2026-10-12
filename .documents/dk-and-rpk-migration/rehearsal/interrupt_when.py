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
Send SIGTERM to a rehearsal driver once its log shows a stage banner and a stated delay has
passed (dk-and-rpk-migration README section 4.1, build resumed-a). Written for
dk-and-rpk-migration prompt 01; prompts 02, 07 and 11 run it unchanged.

    ./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \\
        LOG PIDFILE --banner TEXT --after SECONDS [--poll SECONDS]

It reads LOG and PIDFILE (written by build.sh) and starts nothing. It waits until LOG holds a
line containing TEXT, then SECONDS more, then sends SIGTERM to the pid in PIDFILE, and prints
what it did and when (UTC). If the driver exits before the banner appears, or during the delay,
it says so, sends nothing, and exits 1. It signals only the pid it was given.

It reports what it sent, not what the driver did: a SIGTERMed driver has been seen to exit 134,
not 143, because Ray's failure-signal handler aborts (ChamPBH's board, section 5.3). build.sh
appends the driver's own exit status to the log.

For RH0's resumed-a the banner is `STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS`
(main.py's gradient-branch pool title), and the delay is set from reference's log.
"""

import argparse
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EXIT_MARKER = "** driver exit status"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _say(message: str):
    print(f"[{_now()}] interrupt_when: {message}", flush=True)


def _read_pid(pidfile: Path):
    try:
        text = pidfile.read_text().strip()
    except OSError:
        return None
    return int(text) if text.isdigit() else None


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _log_lines(log: Path):
    try:
        return log.read_text(errors="replace").splitlines()
    except OSError:
        return []


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Send SIGTERM to the pid in PIDFILE once LOG holds a line containing "
        "--banner and --after seconds have passed. Reads the log; starts nothing."
    )
    parser.add_argument(
        "log", type=Path, help="the driver's log (build.sh's NN-BUILD.log)"
    )
    parser.add_argument(
        "pidfile", type=Path, help="the driver's pid file (build.sh's NN-BUILD.pid)"
    )
    parser.add_argument(
        "--banner", required=True, help="the text a log line must contain"
    )
    parser.add_argument(
        "--after",
        required=True,
        type=float,
        help="seconds to wait after the banner before signalling",
    )
    parser.add_argument(
        "--poll", type=float, default=1.0, help="seconds between reads (default 1)"
    )
    args = parser.parse_args(argv)

    _say(
        f'waiting for "{args.banner}" in {args.log}; then {args.after:g} s; then SIGTERM'
    )

    pid = None
    while True:
        if pid is None:
            pid = _read_pid(args.pidfile)
            if pid is not None:
                _say(f"driver pid {pid} (from {args.pidfile})")

        lines = _log_lines(args.log)
        if any(args.banner in line for line in lines):
            break
        if any(line.startswith(EXIT_MARKER) for line in lines) or (
            pid is not None and not _alive(pid)
        ):
            _say(f'the driver exited before "{args.banner}" appeared; nothing sent')
            return 1
        time.sleep(args.poll)

    _say(f'saw "{args.banner}"; waiting {args.after:g} s')
    deadline = time.monotonic() + args.after
    while time.monotonic() < deadline:
        if pid is None:
            pid = _read_pid(args.pidfile)
        if pid is not None and not _alive(pid):
            _say("the driver exited during the delay; nothing sent")
            return 1
        time.sleep(min(args.poll, max(deadline - time.monotonic(), 0.0)))

    if pid is None:
        pid = _read_pid(args.pidfile)
    if pid is None:
        _say(f"no pid in {args.pidfile}; nothing sent")
        return 1
    if not _alive(pid):
        _say("the driver has already exited; nothing sent")
        return 1

    os.kill(pid, signal.SIGTERM)
    _say(f"sent SIGTERM to pid {pid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
