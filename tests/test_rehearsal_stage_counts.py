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
The rehearsal log parser `.documents/dk-and-rpk-migration/rehearsal/stage_counts.py`
(dk-and-rpk-migration prompt 01, item T3).

**The fixtures were built from the shape of the lines the code printed, not copied from any run**:
no StochasticInstanton rehearsal log existed when they were written. The lines were those of
RayTools/RayWorkPool.py (the `** TITLE` banner at :181, the progress lines at :556-566, the
completion and queue summary at :581-590, with rates from `_readable_rate`) and of SI's own
Datastore actor's integrity report at open (`Datastore/SQL/Datastore.py` `_validate_on_startup`,
a factory's `Pruned N unvalidated ...` line, behind Ray's `(Name pid=N)` prefix and its colour
codes), both at prompt 01's commit and both since replaced by the packages `raypoolkit` (prompt
04) and `datastorekit` (prompt 09), whose logs the parser has read unchanged (prompt 07 for the
first, prompt 11 for both); and of main.py (the provenance line before ray.init, the lookup banners,
`** STAGE 4: COMPACTION FUNCTIONS`, the gradient branch's `>>` lines and the skip lines), and of
build.sh's `** driver exit status N`.

Loaded from its path; no Ray, no store. Under 1 s.
"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".documents" / "dk-and-rpk-migration" / "rehearsal" / "stage_counts.py"

PACKAGES = ">> packages: datastorekit not installed; raypoolkit not installed"

# a straight-through dense build (reference): every stage computes everything
FIXTURE_REFERENCE = f"""\
{PACKAGES}
2026-10-12 10:00:00,000\tINFO worker.py:1821 -- Connecting to existing Ray cluster at address: 127.0.0.1:6379...
>> Created sharded datastore "/x/02-reference.sqlite" with 10 shards

** BUILDING PARAMETER SAMPLING GRIDS
   -- using potential type "Quadratic"
   -- time sampling: 100 samples per e-fold

** COSMOLOGICAL PARAMETERS: Planck2018 (store_id=1)

** DIFFUSION MODEL: MasslessDecoupledDiffusion (store_id=1)

** STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES
   -- ALL WORK ITEMS COMPLETE in time 12.3s
      Queue summary: 1 lookup (avg 4.878/min), 1 compute (avg 4.878/min), 1 store (avg 4.878/min), 1 validation (avg 4.878/min)

** STAGE 2: FULL MSR INSTANTONS LOOKUP:
   -- 0 already computed, 10 to compute

** STAGE 2: FULL MSR INSTANTONS
   -- 2026-10-12 10:06:00 (5m 0.2s running): 3/10 work items remaining = 70.00% complete
      inflight: 0 lookup, 3 compute, 0 store, 0 validation | completed: 10 lookup (2/min, avg 2/min), 7 compute (1.4/min, avg 1.4/min), 7 store (1.4/min, avg 1.4/min), 7 validation (1.4/min, avg 1.4/min)
   -- ALL WORK ITEMS COMPLETE in time 6m 2s
      Queue summary: 10 lookup (avg 99.45/hr), 10 compute (avg 99.45/hr), 10 store (avg 99.45/hr), 10 validation (avg 99.45/hr)

** STAGE 3: SLOW-ROLL INSTANTONS LOOKUP:
   -- 0 already computed, 10 to compute

** STAGE 3: SLOW-ROLL INSTANTONS
   -- ALL WORK ITEMS COMPLETE in time 40.5s
      Queue summary: 10 lookup (avg 14.81/min), 10 compute (avg 14.81/min), 10 store (avg 14.81/min), 10 validation (avg 14.81/min)

** STAGE 4: COMPACTION FUNCTIONS

** COMPACTION FUNCTIONS LOOKUP:
   -- 0 already computed, 10 to compute

** STAGE 4: COMPACTION FUNCTIONS AND MASSES
   -- ALL WORK ITEMS COMPLETE in time 1m 4s
      Queue summary: 10 lookup (avg 9.375/min), 10 compute (avg 9.375/min), 10 store (avg 9.375/min), 10 validation (avg 9.375/min)

   >> gradient branch: 10 base grid point(s) x 1 n_collocation_points value(s) x 1 alpha_regularization value(s) = 10 gradient instanton combination(s)
   >> SAT closure seed: 10/10 base grid point(s) have an already-computed FullInstanton available to seed from

** STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS LOOKUP:
   -- 0 already computed, 10 to compute

** STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS
   -- ALL WORK ITEMS COMPLETE in time 16m 3s
      Queue summary: 10 lookup (avg 37.38/hr), 10 compute (avg 37.38/hr), 10 store (avg 37.38/hr), 10 validation (avg 37.38/hr)
** driver exit status 0
"""

# a build signalled during the gradient stage (resumed-a)
FIXTURE_INTERRUPTED = f"""\
{PACKAGES}
** STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES
   -- ALL WORK ITEMS COMPLETE in time 11.9s
      Queue summary: 1 lookup (avg 5.042/min), 1 compute (avg 5.042/min), 1 store (avg 5.042/min), 1 validation (avg 5.042/min)

** STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS LOOKUP:
   -- 0 already computed, 10 to compute

** STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS
   -- 2026-10-12 10:30:00 (5m 0.1s running): 6/10 work items remaining = 40.00% complete
      inflight: 0 lookup, 4 compute, 0 store, 0 validation | completed: 10 lookup (2/min, avg 2/min), 4 compute (48/hr, avg 48/hr), 4 store (48/hr, avg 48/hr), 4 validation (48/hr, avg 48/hr)
*** SIGTERM received at time=1760261400 on cpu 3 (pid 4242) ***
** driver exit status 134
"""

# the resume (resumed-b): its open prunes, the homogeneous stages find everything stored
FIXTURE_RESUMED = f"""\
{PACKAGES}
\x1b[36m(Datastore pid=5151)\x1b[0m !! INTEGRITY WARNING (2026-10-12T10:40:00): datastore "shard0003-store" (physical file /x/02-resumed-shard0003.sqlite)
\x1b[36m(Datastore pid=5151)\x1b[0m Pruned 1 unvalidated GradientCoupledInstanton records
>> Opened existing sharded datastore "/x/02-resumed.sqlite" with 10 shards

** STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES
   -- ALL WORK ITEMS COMPLETE in time 2.1s
      Queue summary: 1 lookup (avg 28.57/min), 0 compute (avg 0/day), 0 store (avg 0/day), 0 validation (avg 0/day)
      (no compute items were evaluated - all assets read from datastore)

** STAGE 2: FULL MSR INSTANTONS LOOKUP:
   -- 10 already computed, 0 to compute

** STAGE 3: SLOW-ROLL INSTANTONS LOOKUP:
   -- 10 already computed, 0 to compute

** STAGE 4: COMPACTION FUNCTIONS

** COMPACTION FUNCTIONS LOOKUP:
   -- 10 already computed, 0 to compute

** STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS LOOKUP:
   -- 4 already computed, 6 to compute

** STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS
   -- ALL WORK ITEMS COMPLETE in time 11m 2s
      Queue summary: 6 lookup (avg 32.63/hr), 6 compute (avg 32.63/hr), 6 store (avg 32.63/hr), 6 validation (avg 32.63/hr)
** driver exit status 0
"""

# a scalars-only build: the unified pipeline, and no gradient branch
FIXTURE_SCALARS = f"""\
{PACKAGES}
** STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES
   -- ALL WORK ITEMS COMPLETE in time 12.0s
      Queue summary: 1 lookup (avg 5/min), 1 compute (avg 5/min), 1 store (avg 5/min), 1 validation (avg 5/min)

** PIPELINE LOOKUP:
   -- 0 already computed, 10 to compute

** STAGES 2+3+4: UNIFIED PIPELINE
   -- ALL WORK ITEMS COMPLETE in time 7m 30s
      Queue summary: 10 lookup (avg 80/hr), 10 compute (avg 80/hr), 10 store (avg 80/hr), 10 validation (avg 80/hr)

** Skipping gradient branch (--targets excludes 'gradient')
** driver exit status 0
"""


@pytest.fixture(scope="module")
def sc():
    spec = importlib.util.spec_from_file_location("stage_counts", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _summary(parsed):
    """(kind, title) of each entry, in order."""
    return [(e["kind"], e["title"]) for e in parsed["entries"]]


def test_a_straight_dense_build(sc):
    """Every pool, lookup and section of a reference build, in order; counts without rates;
    the two STAGE 4 lines kept apart."""
    parsed = sc.parse_log(FIXTURE_REFERENCE)
    assert parsed["exit_status"] == 0
    assert parsed["packages"] == [PACKAGES]
    assert parsed["integrity"] == []
    assert parsed["complete_lines"] == 5
    assert _summary(parsed) == [
        ("pool", "STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES"),
        ("lookup", "STAGE 2: FULL MSR INSTANTONS"),
        ("pool", "STAGE 2: FULL MSR INSTANTONS"),
        ("lookup", "STAGE 3: SLOW-ROLL INSTANTONS"),
        ("pool", "STAGE 3: SLOW-ROLL INSTANTONS"),
        ("section", "STAGE 4: COMPACTION FUNCTIONS"),
        ("lookup", "COMPACTION FUNCTIONS"),
        ("pool", "STAGE 4: COMPACTION FUNCTIONS AND MASSES"),
        ("lookup", "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS"),
        ("pool", "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS"),
    ]
    pools = [e for e in parsed["entries"] if e["kind"] == "pool"]
    assert all(e["complete"] and not e["no_compute"] for e in pools)
    counts = [e["counts"] for e in pools]
    assert counts[0] == {"lookup": 1, "compute": 1, "store": 1, "validation": 1}
    for c in counts[1:]:
        assert c == {"lookup": 10, "compute": 10, "store": 10, "validation": 10}
    lookups = [e for e in parsed["entries"] if e["kind"] == "lookup"]
    assert all(
        (e["already_computed"], e["to_compute"], e["skipped"]) == (0, 10, 0)
        for e in lookups
    )


def test_an_interrupted_build(sc):
    """A build signalled during the gradient stage: that pool is incomplete with no summary,
    the progress line's counts are not taken for one, and the exit status is read."""
    parsed = sc.parse_log(FIXTURE_INTERRUPTED)
    assert parsed["exit_status"] == 134
    assert parsed["complete_lines"] == 1
    gradient = parsed["entries"][-1]
    assert gradient["kind"] == "pool"
    assert gradient["title"] == "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS"
    assert not gradient["complete"]
    assert gradient["counts"] is None


def test_a_resumed_build(sc):
    """The resume: the prune at open reported without Ray's prefix; stage 1 computed nothing;
    the homogeneous lookups found everything and built no pool; the gradient stage computed
    only what was missing."""
    parsed = sc.parse_log(FIXTURE_RESUMED)
    assert parsed["integrity"] == [
        "Pruned 1 unvalidated GradientCoupledInstanton records"
    ]
    assert _summary(parsed) == [
        ("pool", "STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES"),
        ("lookup", "STAGE 2: FULL MSR INSTANTONS"),
        ("lookup", "STAGE 3: SLOW-ROLL INSTANTONS"),
        ("section", "STAGE 4: COMPACTION FUNCTIONS"),
        ("lookup", "COMPACTION FUNCTIONS"),
        ("lookup", "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS"),
        ("pool", "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS"),
    ]
    stage1 = parsed["entries"][0]
    assert stage1["no_compute"]
    assert stage1["counts"] == {"lookup": 1, "compute": 0, "store": 0, "validation": 0}
    gradient_lookup = parsed["entries"][5]
    assert (gradient_lookup["already_computed"], gradient_lookup["to_compute"]) == (
        4,
        6,
    )
    assert parsed["entries"][6]["counts"]["compute"] == 6
    assert parsed["complete_lines"] == 2


def test_a_scalars_only_build(sc):
    """The unified pipeline's lookup and pool, and the skip line."""
    parsed = sc.parse_log(FIXTURE_SCALARS)
    assert _summary(parsed) == [
        ("pool", "STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES"),
        ("lookup", "PIPELINE"),
        ("pool", "STAGES 2+3+4: UNIFIED PIPELINE"),
        ("skip", "Skipping gradient branch (--targets excludes 'gradient')"),
    ]
    assert parsed["entries"][2]["counts"] == {
        "lookup": 10,
        "compute": 10,
        "store": 10,
        "validation": 10,
    }


def test_the_printed_output_carries_no_time_rate_or_pid(sc, tmp_path):
    """The printed counts carry no time, rate or pid, so equal runs print equal output; the
    command line reads several logs."""
    for fixture in (
        FIXTURE_REFERENCE,
        FIXTURE_INTERRUPTED,
        FIXTURE_RESUMED,
        FIXTURE_SCALARS,
    ):
        text = sc.format_counts("x.log", sc.parse_log(fixture))
        for fragment in ("/hr", "/min", "/sec", "/day", "running", "pid", "2026-10-12"):
            assert fragment not in text
    text = sc.format_counts("resumed.log", sc.parse_log(FIXTURE_RESUMED))
    assert (
        "STAGE 2: FULL MSR INSTANTONS LOOKUP: 10 already computed, 0 to compute" in text
    )
    assert "integrity: Pruned 1 unvalidated GradientCoupledInstanton records" in text
    assert "driver exit status: 0" in text
    text = sc.format_counts("a.log", sc.parse_log(FIXTURE_INTERRUPTED))
    assert "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS: INCOMPLETE" in text

    a = tmp_path / "a.log"
    b = tmp_path / "b.log"
    a.write_text(FIXTURE_REFERENCE)
    b.write_text(
        FIXTURE_REFERENCE.replace("16m 3s", "17m 9s").replace("37.38", "35.01")
    )
    out = tmp_path / "out.json"
    assert sc.main([str(a), str(b), "--json", str(out)]) == 0
    result = json.loads(out.read_text())
    assert result[str(a)] == result[str(b)]
