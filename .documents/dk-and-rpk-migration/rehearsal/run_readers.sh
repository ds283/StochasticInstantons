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
# Every reader of a closed rehearsal store: the dk-and-rpk-migration protocol's L3
# (.prompts/dk-and-rpk-migration/README.md section 4.1). Written for dk-and-rpk-migration
# prompt 01; prompts 02, 07 and 11 run it unchanged.
#
# Amended 2026-10-20 for U11 (README section 6.1): no rehearsal builds the gradient branch, so
# step 3 (plot_GradientCoupledSolutions.py) is no longer run on any store.
#
# Amended 2026-10-20 again, after RH0's second attempt: step 2 passes the build's
# --n-collocation-points 5 --alpha-regularization 0.01. Without them the plot script's parser
# defaults (n = 33) reach config/pipeline_setup.py, which gets-or-inserts them as replicated rows
# whatever the targets, so the reader added an n_collocation_points row to the store it read.
#
# It starts and stops no Ray cluster: the caller starts one and passes its address. Every flag
# below was checked against config/argument_parser.py and each plot script's create_plot_parser
# (plot_InstantonSolutions.py, plot_GradientCoupledSolutions.py), which extend it with
# --output-dir.

set -u

usage() {
    cat <<'EOF'
usage: run_readers.sh NN STORE ADDRESS

  NN        the prompt's number, two digits (02, 07, 11)
  STORE     the store's slug (resumed, scalars, ...): the store is $REHEARSAL_ROOT/NN-STORE.sqlite
  ADDRESS   the Ray cluster's address, passed to each driver as --ray-address

Run from the repository root, on a closed store. Into $REHEARSAL_ROOT/NN-readers/STORE/:
  0. a copy of the store's primary and shards into before/, for step 4 only; no layer opens it
  1. main.py --config quadratic-minimal.yaml --database STORE --inventory
                                                    -> 1-inventory.log
  2. plot_InstantonSolutions.py --config quadratic-minimal.yaml --database STORE
       --output-dir plot_InstantonSolutions
       --n-collocation-points 5 --alpha-regularization 0.01 (the build's, so that no
       replicated row is added) [--no-store-values when STORE begins "scalars"]
                                                    -> 2-plot_InstantonSolutions.log
  3. (not run: no rehearsal store holds the gradient branch, U11)
  4. tools/compare_stores.py before/NN-STORE.sqlite NN-STORE.sqlite
                                                    -> 4-compare_stores.log, .json
Each driver is also given --ray-address ADDRESS. Each step's exit status is appended to
status.txt, and the script exits 1 if any step did not exit 0. README 4.1 expects step 4 to find
one version row (labelled 2026.3.0, written by the plot scripts' read-write pools) and
bookkeeping, and so to exit 1: the script prints compare_stores's verdict and its differing
tables, and does not judge them. It refuses to run if NN-readers/STORE/ already exists.

REHEARSAL_ROOT defaults to ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration.
EOF
    exit "${1:-2}"
}

if [[ $# -ge 1 && ( "$1" == "-h" || "$1" == "--help" ) ]]; then
    usage 0
fi
if [[ $# -ne 3 ]]; then
    usage 2
fi

NN=$1
STORE=$2
ADDRESS=$3

if [[ ! "$NN" =~ ^[0-9][0-9]$ ]]; then
    echo "!! run_readers.sh: NN must be two digits, not '$NN'" >&2
    exit 2
fi
if [[ ! "$STORE" =~ ^[A-Za-z0-9-]+$ ]]; then
    echo "!! run_readers.sh: STORE must be a slug of letters, digits and hyphens, not '$STORE'" >&2
    exit 2
fi
if [[ -z "$ADDRESS" ]]; then
    echo "!! run_readers.sh: ADDRESS must not be empty" >&2
    exit 2
fi
if [[ ! -f main.py || ! -f quadratic-minimal.yaml || ! -x venv/bin/python ]]; then
    echo "!! run_readers.sh: run from the repository root (main.py, quadratic-minimal.yaml and venv/ are read from it)" >&2
    exit 2
fi

ROOT=${REHEARSAL_ROOT:-$HOME/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration}
STEM="$ROOT/$NN-$STORE"
DB="$STEM.sqlite"
OUT="$ROOT/$NN-readers/$STORE"

if [[ ! -f "$DB" ]]; then
    echo "!! run_readers.sh: no store at $DB" >&2
    exit 2
fi
if [[ -e "$OUT" ]]; then
    echo "!! run_readers.sh: $OUT already exists; refusing to overwrite it" >&2
    exit 2
fi
shopt -s nullglob
SHARDS=("$STEM"-shard*.sqlite)
shopt -u nullglob
if [[ ${#SHARDS[@]} -eq 0 ]]; then
    echo "!! run_readers.sh: no shards match $STEM-shard*.sqlite" >&2
    exit 2
fi
mkdir -p "$OUT/before"

FAILED=0
record() {
    # record STEP NAME STATUS
    echo "step $1 $2: exit $3" >> "$OUT/status.txt"
    echo ">> run_readers.sh: step $1 $2: exit $3"
    if [[ "$3" -ne 0 ]]; then
        FAILED=1
    fi
}

# 0. the store's files as they are before any reader, for step 4 only
cp -p "$DB" "${SHARDS[@]}" "$OUT/before/"
record 0 copy-before $?

# 1. the inventory
PYTHONPATH=. ./venv/bin/python -u main.py --config quadratic-minimal.yaml --database "$DB" \
    --inventory --ray-address "$ADDRESS" > "$OUT/1-inventory.log" 2>&1
record 1 inventory $?

# 2. plot_InstantonSolutions.py; on a scalars-only store with --no-store-values, so that it
#    writes scalar_data.csv from the scalar columns. The grid flags are build.sh's: the parser's
#    defaults would be inserted into the store as replicated rows.
PLOT_ARGS=()
case "$STORE" in
    scalars*) PLOT_ARGS=(--no-store-values) ;;
esac
if [[ ${#PLOT_ARGS[@]} -gt 0 ]]; then
    PYTHONPATH=. ./venv/bin/python -u plot_InstantonSolutions.py --config quadratic-minimal.yaml \
        --database "$DB" --output-dir "$OUT/plot_InstantonSolutions" \
        --n-collocation-points 5 --alpha-regularization 0.01 --ray-address "$ADDRESS" \
        "${PLOT_ARGS[@]}" > "$OUT/2-plot_InstantonSolutions.log" 2>&1
else
    PYTHONPATH=. ./venv/bin/python -u plot_InstantonSolutions.py --config quadratic-minimal.yaml \
        --database "$DB" --output-dir "$OUT/plot_InstantonSolutions" \
        --n-collocation-points 5 --alpha-regularization 0.01 --ray-address "$ADDRESS" \
        > "$OUT/2-plot_InstantonSolutions.log" 2>&1
fi
record 2 plot_InstantonSolutions $?

# 3. plot_GradientCoupledSolutions.py is not run (U11): no rehearsal store holds the gradient
# branch, since its solves do not converge on the rehearsal grid at this tree.
echo ">> run_readers.sh: step 3 plot_GradientCoupledSolutions: not run (no rehearsal builds the gradient branch, U11)"

# 4. the store after the readers against the copy made before them
PYTHONPATH=. ./venv/bin/python -u tools/compare_stores.py "$OUT/before/$NN-$STORE.sqlite" "$DB" \
    --json "$OUT/4-compare_stores.json" > "$OUT/4-compare_stores.log" 2>&1
COMPARE=$?
record 4 compare_stores "$COMPARE"
echo ">> run_readers.sh: compare_stores's verdict (README 4.1 expects one version row, labelled 2026.3.0, and bookkeeping):"
grep -E '<-- differs|^RESULT:' "$OUT/4-compare_stores.log" | sed 's/^/     /'

exit "$FAILED"
