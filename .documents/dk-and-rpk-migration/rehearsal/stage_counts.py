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
Each pipeline stage's work-item counts from a main.py log, without the rates or times
(dk-and-rpk-migration README section 4.1, L2 and L4). Written for dk-and-rpk-migration
prompt 01; prompts 02, 07 and 11 run it unchanged.

    ./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/stage_counts.py LOG... [--json OUT]

For each log, in order, every stage line main.py and its work pools print (line numbers as of
dk-and-rpk-migration prompt 01's commit):
- a **pool** banner, `** TITLE`, printed by RayWorkPool when a titled queue is built
  (RayTools/RayWorkPool.py:181). The titles are main.py's: `STAGE 1: BACKGROUND INFLATIONARY
  TRAJECTORIES` (:729), `STAGE 2: FULL MSR INSTANTONS` (:827), `STAGE 3: SLOW-ROLL INSTANTONS`
  (:851), `STAGE 4: COMPACTION FUNCTIONS AND MASSES` (:1105), `STAGES 2+3+4: UNIFIED PIPELINE`
  (:206) and `STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS` (:667). With it:
  - whether the queue completed (`-- ALL WORK ITEMS COMPLETE`, RayWorkPool.py:581-583);
  - its queue-summary counts, without the rates (`Queue summary: 10 lookup (avg 61.3/hr),
    10 compute (...), 10 store (...), 10 validation (...)`, :584-586, gives lookup 10,
    compute 10, store 10, validation 10; `available` too where the pool has one);
  - whether the pool said no compute item was evaluated (:587-590);
- a **section** banner main.py prints itself, outside any pool: `** STAGE 4: COMPACTION
  FUNCTIONS` (main.py:862). It is kept apart from the pool `STAGE 4: COMPACTION FUNCTIONS AND
  MASSES`, which may or may not follow it;
- a **lookup** banner, `** TITLE LOOKUP:` (main.py:474-478 for each per-stage queue, :350-355
  for the unified pipeline as `PIPELINE LOOKUP`, :996-1005 for `COMPACTION FUNCTIONS LOOKUP`),
  with the line after it: N already computed, M to compute, and K skipped (no instanton
  available) where printed. A stage with nothing to compute prints its lookup and no pool;
- a **skip** line, `** Skipping ...` or `** Stopping ...` (main.py:1116, :1129, and the
  --stop-after lines at :746, :831, :855), verbatim.

And for the log as a whole: the number of `ALL WORK ITEMS COMPLETE` lines; the provenance line
(`>> packages: ...`, printed once by each driver before ray.init) verbatim; the integrity reports
of the Datastore actors at open (`Pruned N unvalidated ...` / `Found N unvalidated ...`), with
Ray's `(Name pid=N)` prefix removed; and the `** driver exit status N` line build.sh appends.
The output carries no time, rate or pid, so two logs of equal runs give equal output.

No StochasticInstanton rehearsal log existed when this was written: its test fixture is built
from the lines the code prints (tests/test_rehearsal_stage_counts.py).
"""

import argparse
import json
import re
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")
RAY_PREFIX = re.compile(r"^\((?:[^()]*?) pid=\d+(?:, ip=[^)]*)?\)\s*")
EXIT_STATUS = re.compile(r"^\*\* driver exit status (-?\d+)\s*$")
LOOKUP = re.compile(r"^\*\* (.+?) LOOKUP:\s*$")
LOOKUP_COUNTS = re.compile(
    r"^\s*-- (\d+) already computed, (\d+) to compute"
    r"(?:, (\d+) skipped \(no instanton available\))?\s*$"
)
STAGE = re.compile(r"^\*\* (STAGES? .*?)\s*$")
SKIP = re.compile(r"^\*\* ((?:Skipping|Stopping) .*?)\s*$")
COMPLETE = re.compile(r"^\s*-- ALL WORK ITEMS COMPLETE\b")
SUMMARY = re.compile(r"^\s*Queue summary: (.*)$")
SUMMARY_ITEM = re.compile(r"(\d+) (lookup|compute|store|available|validation)\b")
NO_COMPUTE = re.compile(r"^\s*\(no compute items were evaluated")
PACKAGES = re.compile(r"^>> packages: ")
INTEGRITY = re.compile(r"^(?:Pruned|Found) \d+ unvalidated ")

# banners main.py prints itself, outside any work pool (main.py:862)
SECTION_TITLES = frozenset({"STAGE 4: COMPACTION FUNCTIONS"})


def parse_log(text: str) -> dict:
    """
    {"entries": [...], "complete_lines": int, "packages": [...], "integrity": [...],
    "exit_status": int or None} for one log's text. Each entry is a dict with "kind" one of
    "pool", "section", "lookup" or "skip", and "title".
    """
    entries = []
    packages = []
    integrity = []
    complete_lines = 0
    exit_status = None
    pool = None
    lookup = None
    for raw in text.splitlines():
        line = ANSI.sub("", raw)
        bare = RAY_PREFIX.sub("", line)

        if PACKAGES.match(bare):
            packages.append(bare.strip())
            continue
        if INTEGRITY.match(bare.strip()):
            integrity.append(bare.strip())
            continue

        match = EXIT_STATUS.match(line)
        if match:
            exit_status = int(match.group(1))
            continue

        if lookup is not None:
            match = LOOKUP_COUNTS.match(line)
            lookup_entry, lookup = lookup, None
            if match:
                lookup_entry["already_computed"] = int(match.group(1))
                lookup_entry["to_compute"] = int(match.group(2))
                lookup_entry["skipped"] = (
                    int(match.group(3)) if match.group(3) is not None else 0
                )
                continue

        match = LOOKUP.match(line)
        if match:
            lookup = {
                "kind": "lookup",
                "title": match.group(1),
                "already_computed": None,
                "to_compute": None,
                "skipped": None,
            }
            entries.append(lookup)
            pool = None
            continue

        match = SKIP.match(line)
        if match:
            entries.append({"kind": "skip", "title": match.group(1)})
            pool = None
            continue

        match = STAGE.match(line)
        if match:
            title = match.group(1)
            if title in SECTION_TITLES:
                entries.append({"kind": "section", "title": title})
                pool = None
            else:
                pool = {
                    "kind": "pool",
                    "title": title,
                    "complete": False,
                    "counts": None,
                    "no_compute": False,
                }
                entries.append(pool)
            continue

        if COMPLETE.match(line):
            complete_lines += 1
            if pool is not None:
                pool["complete"] = True
            continue

        match = SUMMARY.match(line)
        if match:
            if pool is not None:
                pool["counts"] = {
                    name: int(count)
                    for count, name in SUMMARY_ITEM.findall(match.group(1))
                }
            continue

        if NO_COMPUTE.match(line):
            if pool is not None:
                pool["no_compute"] = True
            continue

    return {
        "entries": entries,
        "complete_lines": complete_lines,
        "packages": packages,
        "integrity": integrity,
        "exit_status": exit_status,
    }


def format_counts(name: str, parsed: dict) -> str:
    lines = [f"LOG {name}"]
    for line in parsed["packages"]:
        lines.append(f"  {line}")
    for line in parsed["integrity"]:
        lines.append(f"  integrity: {line}")
    if not parsed["entries"]:
        lines.append("  no stage line")
    for entry in parsed["entries"]:
        kind = entry["kind"]
        if kind == "pool":
            state = "complete" if entry["complete"] else "INCOMPLETE"
            if entry["counts"] is None:
                counts = "no queue summary"
            else:
                counts = ", ".join(f"{k} {v}" for k, v in entry["counts"].items())
            extra = "; no compute items evaluated" if entry["no_compute"] else ""
            lines.append(f"  {entry['title']}: {state}; {counts}{extra}")
        elif kind == "lookup":
            if entry["already_computed"] is None:
                lines.append(f"  {entry['title']} LOOKUP: no counts")
            else:
                lines.append(
                    f"  {entry['title']} LOOKUP: {entry['already_computed']} already "
                    f"computed, {entry['to_compute']} to compute, {entry['skipped']} skipped"
                )
        elif kind == "section":
            lines.append(f"  {entry['title']} (section)")
        else:
            lines.append(f"  {entry['title']}")
    lines.append(f"  ALL WORK ITEMS COMPLETE lines: {parsed['complete_lines']}")
    status = parsed["exit_status"]
    lines.append(
        f"  driver exit status: {'not recorded' if status is None else status}"
    )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Each stage's lookup and queue-summary counts, without rates or times, "
        "from main.py logs."
    )
    parser.add_argument("logs", nargs="+", type=Path, metavar="LOG")
    parser.add_argument("--json", metavar="OUT", help="also write the result as JSON")
    args = parser.parse_args(argv)

    result = {}
    status = 0
    for log in args.logs:
        try:
            text = log.read_text(errors="replace")
        except OSError as e:
            print(f"!! stage_counts: cannot read {log}: {e}")
            status = 2
            continue
        parsed = parse_log(text)
        result[str(log)] = parsed
        print(format_counts(str(log), parsed))

    if args.json:
        Path(args.json).write_text(json.dumps(result, indent=2) + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main())
