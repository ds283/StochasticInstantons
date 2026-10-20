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
# One build of the dk-and-rpk-migration rehearsal protocol (.prompts/dk-and-rpk-migration/
# README.md section 4.1): README 4.1's main.py command, verbatim but for its parameters.
# Written for dk-and-rpk-migration prompt 01; prompts 02, 07 and 11 run it unchanged.
#
# Amended 2026-10-20 for U11 (README section 6.1): the dense mode builds the homogeneous branch
# only. RH0's first attempt found that no gradient solve of the rehearsal grid converges at this
# tree (each ran over five hours with every inner Picard step failing), so no rehearsal builds
# the gradient branch. The two modes now differ only by --no-store-values.
#
# It starts and stops no Ray cluster: the caller starts one and passes its address. It runs in
# the foreground (the driver is waited on); the caller backgrounds it.

set -u

usage() {
    cat <<'EOF'
usage: build.sh NN STORE BUILD ADDRESS MODE [--profile-db]

  NN        the prompt's number, two digits (02, 07, 11)
  STORE     the store's slug: reference | resumed | scalars | scalars-2 (any slug of
            letters, digits and hyphens); the store is $REHEARSAL_ROOT/NN-STORE.sqlite
  BUILD     the build's slug: reference | resumed-a | resumed-b | scalars | scalars-2
            (any slug of letters, digits and hyphens)
  ADDRESS   the Ray cluster's address, passed to main.py as --ray-address
  MODE      dense:   --targets homogeneous (the gradient branch is not built: U11)
            scalars: --targets homogeneous --no-store-values
  --profile-db  also pass --profile-db $REHEARSAL_ROOT/NN-STORE-profile.sqlite

Runs, from the repository root:
  PYTHONPATH=. ./venv/bin/python -u main.py --config quadratic-minimal.yaml \
      --database $REHEARSAL_ROOT/NN-STORE.sqlite \
      --job-name dk-and-rpk-migration-NN-BUILD --targets TARGETS \
      --n-collocation-points 5 --alpha-regularization 0.01 --ray-address ADDRESS \
      [--no-store-values] [--profile-db $REHEARSAL_ROOT/NN-STORE-profile.sqlite]

Output goes to $REHEARSAL_ROOT/logs/NN-BUILD.log, the driver's pid to
$REHEARSAL_ROOT/logs/NN-BUILD.pid as soon as it starts, and "** driver exit status N" is
appended to the log when it ends. The script exits with the driver's status. It refuses to
overwrite an existing log.

REHEARSAL_ROOT defaults to ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration.
EOF
    exit "${1:-2}"
}

if [[ $# -ge 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
    usage 0
fi
if [[ $# -lt 5 || $# -gt 6 ]]; then
    usage 2
fi

NN=$1
STORE=$2
BUILD=$3
ADDRESS=$4
MODE=$5
PROFILE=${6:-}

if [[ ! "$NN" =~ ^[0-9][0-9]$ ]]; then
    echo "!! build.sh: NN must be two digits, not '$NN'" >&2
    exit 2
fi
if [[ ! "$STORE" =~ ^[A-Za-z0-9-]+$ ]]; then
    echo "!! build.sh: STORE must be a slug of letters, digits and hyphens, not '$STORE'" >&2
    exit 2
fi
if [[ ! "$BUILD" =~ ^[A-Za-z0-9-]+$ ]]; then
    echo "!! build.sh: BUILD must be a slug of letters, digits and hyphens, not '$BUILD'" >&2
    exit 2
fi
if [[ -z "$ADDRESS" ]]; then
    echo "!! build.sh: ADDRESS must not be empty" >&2
    exit 2
fi
case "$MODE" in
    dense)   TARGETS=(homogeneous); EXTRA=() ;;
    scalars) TARGETS=(homogeneous); EXTRA=(--no-store-values) ;;
    *) echo "!! build.sh: MODE must be dense or scalars, not '$MODE'" >&2; exit 2 ;;
esac
if [[ -n "$PROFILE" && "$PROFILE" != "--profile-db" ]]; then
    echo "!! build.sh: the sixth argument may only be --profile-db, not '$PROFILE'" >&2
    exit 2
fi
if [[ ! -f main.py || ! -f quadratic-minimal.yaml || ! -x venv/bin/python ]]; then
    echo "!! build.sh: run from the repository root (main.py, quadratic-minimal.yaml and venv/ are read from it)" >&2
    exit 2
fi

ROOT=${REHEARSAL_ROOT:-$HOME/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration}
LOGS="$ROOT/logs"
LOG="$LOGS/$NN-$BUILD.log"
PIDFILE="$LOGS/$NN-$BUILD.pid"

if [[ -e "$LOG" ]]; then
    echo "!! build.sh: $LOG already exists; refusing to overwrite it" >&2
    exit 2
fi
mkdir -p "$LOGS"

ARGS=(--config quadratic-minimal.yaml
      --database "$ROOT/$NN-$STORE.sqlite"
      --job-name "dk-and-rpk-migration-$NN-$BUILD" --targets "${TARGETS[@]}"
      --n-collocation-points 5 --alpha-regularization 0.01 --ray-address "$ADDRESS")
if [[ ${#EXTRA[@]} -gt 0 ]]; then
    ARGS+=("${EXTRA[@]}")
fi
if [[ -n "$PROFILE" ]]; then
    ARGS+=(--profile-db "$ROOT/$NN-$STORE-profile.sqlite")
fi

PYTHONPATH=. ./venv/bin/python -u main.py "${ARGS[@]}" > "$LOG" 2>&1 &
PID=$!
echo "$PID" > "$PIDFILE"
echo ">> build.sh: $NN-$BUILD started, driver pid $PID, log $LOG"

wait "$PID"
STATUS=$?
echo "** driver exit status $STATUS" >> "$LOG"
echo ">> build.sh: $NN-$BUILD ended, driver exit status $STATUS"
exit "$STATUS"
