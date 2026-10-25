#!/usr/bin/env bash
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
#
# One registered build of the rrk-adoption rehearsal (.prompts/rrk-adoption/
# 04-rehearse-registered-runs.md, section 1.1, H0; campaign README P8). Written for rrk-adoption
# prompt 04, after .documents/dk-and-rpk-migration/rehearsal/build.sh: the same main.py command
# (dk-and-rpk-migration README section 4.1's dense build, without --profile-db), given to the
# registered-run wrapper RunDrivers/registered_run.py after its "--".
#
# It differs from build.sh in four ways:
#   - main.py runs through the wrapper, which registers the run under var/runs/ before Ray starts;
#   - it appends no "** driver exit status N" line: the wrapper prints that marker itself, last
#     (build.sh's own second marker is why this launcher exists). It appends
#     "** launcher saw exit status N" instead, once the driver has ended, whatever ended it;
#   - the store and the launch files live in the repository's var/ (ignored by git), with
#     absolute paths, so that the wrapper and `runregistrykit list` agree on the store's path;
#   - it detaches itself (rule 3 of .claude/rules/run-registry.md): after its checks it starts,
#     under nohup, a bash that launches the driver, writes the driver's pid at once, waits on it
#     and so reaps it (so that `runregistrykit end` is never refused by a killed driver that no
#     one has reaped: RunRegistryKit's open issue
#     [04-a-killed-process-not-yet-reaped-answers-kill-0]), and appends its line. It returns at
#     once, exit 0, having printed where the log and the pid file are.
#
# It starts and stops no Ray cluster: the caller starts one and passes its address. No command
# line it creates names the cluster's temp dir.

set -u

usage() {
    cat <<'EOF'
usage: build_registered.sh STORE BUILD ADDRESS PURPOSE [LAUNCH]

  STORE     the store's slug (letters, digits and hyphens); the store is
            $PWD/var/datastores/rrk-adoption-04-STORE.sqlite
  BUILD     the build's slug (letters, digits and hyphens): the wrapper's --register, and
            main.py's --job-name rrk-adoption-04-BUILD
  ADDRESS   the Ray cluster's address, passed to main.py as --ray-address
  PURPOSE   the run's purpose, one line, passed to the wrapper as --purpose
  LAUNCH    the slug of the launch files (default BUILD): the log is
            $PWD/var/rrk-adoption-04/LAUNCH.log and the pid file LAUNCH.pid

Runs, from the repository root, detached (nohup), with the driver's stdout and stderr to the log:
  PYTHONPATH=. ./venv/bin/python -u RunDrivers/registered_run.py --campaign rrk-adoption \
      --prompt 04 --register BUILD --purpose PURPOSE -- \
      --config quadratic-minimal.yaml --database $S/rrk-adoption-04-STORE.sqlite \
      --job-name rrk-adoption-04-BUILD --targets homogeneous \
      --n-collocation-points 5 --alpha-regularization 0.01 --ray-address ADDRESS
where S=$PWD/var/datastores. The driver's pid is written to the pid file as soon as it starts,
and "** launcher saw exit status N" is appended to the log when it ends. It refuses to
overwrite an existing log. Each refusal is one "!! " line on stderr, exit 2.
EOF
    exit "${1:-2}"
}

refuse() {
    echo "!! build_registered.sh: $*" >&2
    exit 2
}

if [[ $# -ge 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
    usage 0
fi
if [[ $# -lt 4 || $# -gt 5 ]]; then
    usage 2
fi

STORE=$1
BUILD=$2
ADDRESS=$3
PURPOSE=$4
LAUNCH=${5:-$BUILD}

SLUG='^[A-Za-z0-9-]+$'
[[ "$STORE" =~ $SLUG ]] || refuse "STORE must be a slug of letters, digits and hyphens, not '$STORE'"
[[ "$BUILD" =~ $SLUG ]] || refuse "BUILD must be a slug of letters, digits and hyphens, not '$BUILD'"
[[ "$LAUNCH" =~ $SLUG ]] || refuse "LAUNCH must be a slug of letters, digits and hyphens, not '$LAUNCH'"
[[ -n "$ADDRESS" ]] || refuse "ADDRESS must not be empty"
[[ -n "${PURPOSE//[[:space:]]/}" ]] || refuse "PURPOSE must not be empty"
if [[ ! -f main.py || ! -f quadratic-minimal.yaml || ! -x venv/bin/python || ! -f RunDrivers/registered_run.py ]]; then
    refuse "run from the repository root (main.py, quadratic-minimal.yaml, RunDrivers/registered_run.py and venv/ are read from it)"
fi

S="$PWD/var/datastores"
L="$PWD/var/rrk-adoption-04"
LOG="$L/$LAUNCH.log"
PIDFILE="$L/$LAUNCH.pid"

[[ -d "$S" ]] || refuse "$S does not exist (rrk-adoption prompt 01 creates var/datastores/)"
[[ -e "$LOG" ]] && refuse "$LOG already exists; refusing to overwrite it"
mkdir -p "$L" || refuse "could not create $L"

CMD=(./venv/bin/python -u RunDrivers/registered_run.py
     --campaign rrk-adoption --prompt 04 --register "$BUILD" --purpose "$PURPOSE" --
     --config quadratic-minimal.yaml
     --database "$S/rrk-adoption-04-$STORE.sqlite"
     --job-name "rrk-adoption-04-$BUILD" --targets homogeneous
     --n-collocation-points 5 --alpha-regularization 0.01 --ray-address "$ADDRESS")

# The detached bash: launch the driver, write its pid at once, wait on it (and so reap it), then
# append the launcher's line. Its own output goes nowhere; the driver's goes to the log.
# shellcheck disable=SC2016
RUNNER='log=$1; pidfile=$2; shift 2
PYTHONPATH=. "$@" > "$log" 2>&1 < /dev/null &
pid=$!
echo "$pid" > "$pidfile"
wait "$pid"
status=$?
echo "** launcher saw exit status $status" >> "$log"'

nohup bash -c "$RUNNER" build_registered "$LOG" "$PIDFILE" "${CMD[@]}" > /dev/null 2>&1 < /dev/null &
disown

echo ">> build_registered.sh: $LAUNCH launched detached (launcher pid $!); log $LOG; pid file $PIDFILE"
exit 0
