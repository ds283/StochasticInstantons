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

"""The heartbeat and the stage, read off the run's own output (rrk-adoption prompt 03, W3 and W6
test 2).

The subjects are `StageTracker` and `RegisteredStream` in `RunDrivers/registered_run.py`, on a real
`Run` begun in a temporary runs root and a `StringWriter` standing in for the real stream. Time is a
fake clock, `time.monotonic` patched. The lines are RayWorkPool's, made with its own format strings
(`raypoolkit/RayWorkPool.py:206`, `:588`, `:592`, `:606`), `main.py`'s own banners and `>> ` lines,
DatastoreKit's `>> ` lines as `ShardedPool` prints them, and a worker's line as Ray forwards it,
with its `(... pid=...)` prefix. No Ray is initialised, no store is opened, and nothing under `var/`
is read or written.
"""

import sys
import threading
from datetime import datetime
from pathlib import Path
from unittest import mock

import pytest
import runregistrykit

from RunDrivers import registered_run
from RunDrivers.registered_run import RegisteredStream, StageTracker
from registered_run_helpers import REPO_ROOT, StringWriter, no_ray_at_the_end  # noqa: F401

TITLE = "STAGE 3: SLOW-ROLL INSTANTONS"
NOW = datetime(2026, 10, 25, 12, 0, 0)

BANNER = f"\n** {TITLE}"
PROGRESS = (
    f"   -- {NOW:%Y-%m-%d %H:%M:%S%z} (5m 1s running): 3/5 work items remaining = "
    f"{40.0:.2f}% complete"
)
INFLIGHT = (
    "      inflight: 0 lookup, 3 compute, 0 store, 0 validation | completed: 2 lookup"
)
COMPLETE = "   -- ALL WORK ITEMS COMPLETE in time 10m 3s"
WORKER = "\x1b[36m(_compute_full_instanton pid=89917)\x1b[0m a line a worker printed"

# every `>> ` line a build prints to stdout, as printed (the orchestrator's note for 03,
# correction 3): information inside a stage, never a banner
STORE = "/somewhere/var/datastores/a-store.sqlite"
INFORMATION_LINES = (
    # main.py:101, utilities.format_package_provenance
    ">> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a2, requested "
    "v0.5.0); raypoolkit 0.3.0 (https://github.com/ds283/RayPoolKit@67a75b9, requested v0.3.0)",
    # datastorekit/SQL/ShardedPool.py:271 and :308
    f'>> Created sharded datastore "{STORE}" with 10 shards',
    f'>> Opened existing sharded datastore "{STORE}" with 10 shards',
    # its replication and prune lines, :2147-2177 and :2542-2554
    f'>> Sharded datastore "{STORE}" was opened with a replicated write in flight '
    '(operation="store", class="efold_value", controlling shard=0, store_id=3, '
    "started=2026-10-25T12:00:00)",
    '>>   copied 2 row(s) of "efold_value" from shard 0 to shard 1: (3, 4)',
    ">>   the replication_in_flight record was cleared",
    f'>> Sharded datastore "{STORE}" was opened with a prune in flight '
    '(class="InflatonTrajectory", started=2026-10-25T12:00:00); it was run again on every shard',
    '>>   pruned 1 row(s) of "InflatonTrajectory" on shard 2',
    ">>   every shard was already pruned: nothing more was deleted",
    # main.py:654-659, :1198-1211
    "   >> gradient branch: 10 base grid point(s) x 1 n_collocation_points value(s) x 1 "
    "alpha_regularization value(s) = 10 gradient instanton combination(s)",
    "   >> SAT closure seed: 0/10 base grid point(s) have an already-computed FullInstanton "
    "available to seed from",
    "   >> 1 model × 4 CSV sample points = 4 instanton combinations",
    "   >> 1 model and 1 x 1 x 10 N_init/N_final/delta_Nstar grid = 10 parameter combinations "
    "per model = 10 instanton combinations",
    # this file's own registration lines (register)
    ">> registered_run: registered as rrk-adoption-03-unit-20261025T120000",
    ">>   manifest /somewhere/var/runs/rrk-adoption-03-unit-20261025T120000/manifest.json",
    ">>   list it with: ./venv/bin/python -m runregistrykit list",
)

# main.py's own banners, as printed (each print begins "\n"), and RayWorkPool's
BANNERS = (
    ("\n** BUILDING PARAMETER SAMPLING GRIDS", "BUILDING PARAMETER SAMPLING GRIDS"),
    (
        "\n** COSMOLOGICAL PARAMETERS: Planck2018 68% central values (store_id=1)",
        "COSMOLOGICAL PARAMETERS: Planck2018 68% central values (store_id=1)",
    ),
    (
        "\n** DIFFUSION MODEL: MasslessDecoupledDiffusion (store_id=1)",
        "DIFFUSION MODEL: MasslessDecoupledDiffusion (store_id=1)",
    ),
    (
        "\n** STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES",
        "STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES",
    ),
    (
        "\n** STAGE 2: FULL MSR INSTANTONS LOOKUP:\n   -- 0 already computed, 10 to compute",
        "STAGE 2: FULL MSR INSTANTONS LOOKUP:",
    ),
    ("\n** PIPELINE LOOKUP:\n   -- 0 already computed, 4 to compute", "PIPELINE LOOKUP:"),
    ("\n** STAGE 4: COMPACTION FUNCTIONS", "STAGE 4: COMPACTION FUNCTIONS"),
    (
        "\n** Stopping after Stage 2 (--stop-after full-instanton)",
        "Stopping after Stage 2 (--stop-after full-instanton)",
    ),
    (
        "\n** Skipping gradient branch (--targets excludes 'gradient')",
        "Skipping gradient branch (--targets excludes 'gradient')",
    ),
    (
        "\n** STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS",
        "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS",
    ),
)


class Clock:
    """A fake `time.monotonic`."""

    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


class FailingCopy:
    """A copy whose `write` raises, as a full disk would."""

    def write(self, _text):
        raise OSError("no space left on device")

    def flush(self):
        raise OSError("no space left on device")

    def close(self):
        pass


class FailingRun:
    """A run whose heartbeat cannot be written."""

    def heartbeat(self, **_kwargs):
        raise OSError("no space left on device")


class Streams:
    def __init__(self, tmp_path, request):
        self.root = Path(tmp_path).resolve()
        self.run = runregistrykit.begin(
            campaign="rrk-adoption",
            prompt="03",
            slug="streams",
            purpose="a unit test of the stream proxies, in a temporary directory",
            argv=["pytest"],
            root=str(self.root),
            client_root=str(REPO_ROOT),
        )
        self.real = StringWriter()
        self.clock = Clock()
        clock = mock.patch.object(registered_run.time, "monotonic", self.clock)
        clock.start()
        request.addfinalizer(clock.stop)
        beats = mock.patch.object(self.run, "heartbeat", wraps=self.run.heartbeat)
        self.beats = beats.start()
        request.addfinalizer(beats.stop)
        self.addcleanup = request.addfinalizer

    def stream(self, beats=True, copy_to="stdout"):
        path = self.run.stdout_path if copy_to == "stdout" else self.run.stderr_path
        stream = RegisteredStream(
            self.real, self.run, StageTracker(), copy_to=path, beats=beats
        )
        self.addcleanup(stream.close_copy)
        return stream

    def line(self, stream, text, at=None):
        if at is not None:
            self.clock.now = at
        print(text, file=stream)

    def stage(self):
        return self.run.status().get("stage")


@pytest.fixture
def s(tmp_path, request):
    return Streams(tmp_path, request)


class TestTheBeat:
    def test_lines_closer_than_thirty_seconds_beat_once(self, s):
        stream = s.stream()
        s.line(stream, WORKER, at=1000.0)
        s.line(stream, WORKER, at=1010.0)
        s.line(stream, WORKER, at=1029.9)
        assert s.beats.call_count == 1
        s.line(stream, WORKER, at=1030.0)
        assert s.beats.call_count == 2
        # a worker's line moves no stage
        assert s.stage() is None

    def test_a_banner_changes_the_stage_at_once(self, s):
        stream = s.stream()
        s.line(stream, WORKER, at=1000.0)
        assert s.beats.call_count == 1
        s.line(stream, BANNER, at=1001.0)
        assert s.beats.call_count == 2
        assert s.stage() == TITLE

    def test_the_progress_and_completion_stages(self, s):
        stream = s.stream()
        s.line(stream, BANNER, at=1000.0)
        s.line(stream, PROGRESS, at=1001.0)
        assert s.stage() == f"{TITLE}, 40.00% (3 of 5 work items remaining)"
        s.line(stream, INFLIGHT, at=1002.0)
        assert s.stage() == f"{TITLE}, 40.00% (3 of 5 work items remaining)"
        s.line(stream, COMPLETE, at=1003.0)
        assert s.stage() == f"{TITLE}, all work items complete"
        # the banner's leading newline ends an empty line, which beat as the first line; then
        # the banner, the progress line and the completion each changed the stage
        assert s.beats.call_count == 4

    @pytest.mark.parametrize("printed, stage", BANNERS, ids=[b[1] for b in BANNERS])
    def test_main_pys_own_banners_are_stages(self, printed, stage):
        tracker = StageTracker()
        tracker.feed("** an earlier banner")
        changed = False
        for line in printed.split("\n"):
            changed = tracker.feed(line) or changed
        assert changed
        assert tracker.stage == stage

    @pytest.mark.parametrize("line", INFORMATION_LINES)
    def test_a_double_angle_line_is_not_a_stage(self, line):
        tracker = StageTracker()
        assert not tracker.feed(line), line
        assert tracker.stage is None
        tracker.feed("** BUILDING PARAMETER SAMPLING GRIDS")
        assert not tracker.feed(line), line
        assert tracker.stage == "BUILDING PARAMETER SAMPLING GRIDS"

    def test_main_pys_other_lines_move_nothing(self):
        tracker = StageTracker()
        tracker.feed("** BUILDING PARAMETER SAMPLING GRIDS")
        for line in (
            '   -- using potential type "Quadratic"',
            "   -- delta_Nstar: 10 values = [ 0.1, 0.42222, 3 ]",
            "!! WARNING: FullInstanton object with store_id=3 did not validate after being "
            "emplaced in the datastore",
            WORKER,
        ):
            assert not tracker.feed(line), line
        assert tracker.stage == "BUILDING PARAMETER SAMPLING GRIDS"

    def test_stderr_does_not_beat(self, s):
        stream = s.stream(beats=False, copy_to="stderr")
        s.line(stream, BANNER, at=1000.0)
        s.line(stream, PROGRESS, at=2000.0)
        assert s.beats.call_count == 0
        assert s.stage() is None
        assert Path(s.run.stderr_path).read_text() == f"{BANNER}\n{PROGRESS}\n"

    def test_a_stream_that_has_stopped_beating_still_copies(self, s):
        stream = s.stream()
        s.line(stream, BANNER, at=1000.0)
        beats = s.beats.call_count
        stream.stop_beating()
        s.line(stream, "** driver exit status 0", at=2000.0)
        assert s.beats.call_count == beats
        assert s.stage() == TITLE
        assert Path(s.run.stdout_path).read_text().endswith("** driver exit status 0\n")


class TestThePassThrough:
    def test_every_write_reaches_the_real_stream_unaltered_and_the_copy(self, s):
        stream = s.stream()
        pieces = ["half a ", "line\n", BANNER, "\n", "", "two\nlines\n", "no newline"]
        for piece in pieces:
            stream.write(piece)
        stream.writelines(["a\n", "b\n"])
        stream.flush()
        expected = "".join(pieces) + "a\nb\n"
        assert s.real.text() == expected
        assert Path(s.run.stdout_path).read_text() == expected
        assert s.stage() == TITLE

    def test_a_copy_that_fails_costs_neither_the_line_nor_the_beat(self, s):
        stream = s.stream()
        stream.close_copy()
        stream._copy = FailingCopy()
        s.line(stream, BANNER, at=1000.0)
        assert s.real.text() == f"{BANNER}\n"
        assert s.stage() == TITLE
        # dropped, not retried, and a later line still gets through, and still beats
        assert stream._copy is None
        beats = s.beats.call_count
        s.line(stream, PROGRESS, at=1001.0)
        assert s.real.text() == f"{BANNER}\n{PROGRESS}\n"
        assert s.beats.call_count == beats + 1
        assert s.stage() == f"{TITLE}, 40.00% (3 of 5 work items remaining)"
        stream.flush()

    def test_a_heartbeat_that_fails_costs_no_line(self, s):
        stream = RegisteredStream(s.real, FailingRun(), StageTracker())
        s.line(stream, BANNER, at=1000.0)
        s.line(stream, WORKER, at=2000.0)
        assert s.real.text() == f"{BANNER}\n{WORKER}\n"

    def test_a_line_from_another_thread_reaches_both_and_beats(self, s):
        """Ray writes the workers' output into the driver's sys.stdout from a thread of its own
        (ChamPBH's note 03, ruling 6)."""
        stream = s.stream()
        s.clock.now = 1000.0
        thread = threading.Thread(target=lambda: print(WORKER, file=stream))
        thread.start()
        thread.join(timeout=30)
        assert not thread.is_alive()
        assert s.real.text() == f"{WORKER}\n"
        assert Path(s.run.stdout_path).read_text() == f"{WORKER}\n"
        assert s.beats.call_count == 1
        assert s.run.status()["heartbeat"] is not None

    def test_two_threads_writing_at_once_lose_no_line(self, s):
        stream = s.stream()
        s.clock.now = 1000.0
        lines = {name: [f"{name} {i}" for i in range(200)] for name in ("a", "b")}

        def write(name):
            # one write per line: print's two writes (the text, then the newline) can interleave
            # between threads on any stream, the real one included
            for line in lines[name]:
                stream.write(f"{line}\n")

        threads = [threading.Thread(target=write, args=(n,)) for n in lines]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        copied = Path(s.run.stdout_path).read_text().splitlines()
        assert sorted(copied) == sorted(lines["a"] + lines["b"])
        assert sorted(s.real.text().splitlines()) == sorted(copied)

    def test_it_knows_when_the_last_write_left_a_line_unfinished(self, s):
        stream = s.stream()
        assert not stream.mid_line
        stream.write("half a line")
        assert stream.mid_line
        stream.write("")
        assert stream.mid_line
        stream.write(" and the rest\n")
        assert not stream.mid_line

    def test_attributes_are_the_real_streams(self, s):
        stream = RegisteredStream(sys.__stdout__, s.run, StageTracker())
        assert stream.fileno() == sys.__stdout__.fileno()
        assert stream.encoding == sys.__stdout__.encoding
