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
# StochasticInstanton's rehearsal cluster, and the rehearsal lock it shares with ChamPBH and
# SecondaryGWKit. Written for dk-and-rpk-migration prompt 01a, which implemented
# .prompts/dk-and-rpk-migration/rehearsal-lock-brief.md; the brief's section 3 (the cluster) still
# governs the cluster half, and is followed exactly.
#
# Since rpk-v030-adoption prompt 01 the lock is the pinned raypoolkit package's, taken through
# `python -m raypoolkit.rehearsal_lock`, whose contract is RayPoolKit's docs/rehearsal-lock.md at
# the pinned tag. This script keeps no lock code of its own and never spells the lock's location:
# where it needs the location (stop's owner check) it asks the package. The values reach the
# module from this script's variables, so that no command line of the script's own names SI's temp
# dir: one that did would seed the module's process rule (contract section 6). For the same
# reason, a PURPOSE never names the temp dir.
#
# This script NEVER runs `ray stop`, which stops every Ray process on the machine. It stops SI's
# cluster by signalling the processes whose command line names SI's temp dir, and their
# descendants (Ray's workers carry only their process title, so they are reached through their
# parent). It never waits on a held lock, and never removes a lock that is not SI's.
#
# It may be sourced (its functions used, its main skipped): the proof of prompt 01a stops a
# decoy cluster by calling stop_cluster with the decoy's temp dir and ports.
#
# Two fixes are taken from ChamPBH's adaptation of this script (ChamPBH commit babd9d5, its
# prompt 05a changes 3 and 4): the stop confirms all four fixed ports free, as brief section 3
# asks, not the GCS port alone; and start refuses when any of the four ports is already held.

set -u

usage() {
    cat <<'EOF2'
usage: ray_cluster.sh start PURPOSE [--num-cpus N]
       ray_cluster.sh stop
       ray_cluster.sh status
       ray_cluster.sh --help

Run from the repository root.

  start PURPOSE   take the rehearsal lock through raypoolkit.rehearsal_lock
                  (~/.raypoolkit/rehearsal-lock), then start SI's Ray head on /tmp/ray-si: GCS
                  6390, client 6391, dashboard 8266, dashboard agent 52366, N CPUs (default 4),
                  and record the gcs_server's pid in the lock's owner file. PURPOSE is written to
                  the owner file, e.g. "dk-and-rpk-migration 02 (RH0)", and never names
                  /tmp/ray-si. If the lock is held, or the old location still exists, prints its
                  owner file and exits 3, starting nothing. If any of the four ports is already
                  held, or a process of the cluster is alive, exits 4 with the lock released
                  again, starting nothing. A failed start stops what it started and releases the
                  lock, which stays held if anything of the cluster is still alive. Prints the
                  cluster's address and the command that lists its actors.
  stop            stop SI's processes (SIGTERM to every process naming /tmp/ray-si, to the Ray
                  client server whose address is 127.0.0.1:6390, and to their descendants; a grace
                  period of $RAY_CLUSTER_GRACE seconds, default 15; then SIGKILL), confirm none is
                  left and all four ports (6390, 6391, 8266, 52366) are free, then release the
                  lock if its owner is SI's. Touches nothing if the lock is another project's.
  status          the lock, its owner file, whether the owner's pid is alive, the old location if
                  it exists, and the cluster's processes by the module's rule (those release
                  refuses on); then SI's processes by this script's rule (those stop signals), and
                  its four ports.

The cluster runs in Ray's token mode (RAY_AUTH_MODE=token, set by start unless the environment
holds a value), so a Ray CLI command against it needs RAY_AUTH_MODE=token in its environment.

Never runs `ray stop`. Never waits on a held lock.
EOF2
}

# ---- SI's cluster (rehearsal-lock-brief.md, section 3) ----
LOCK_PROJECT="StochasticInstantons"
SI_TEMP_DIR="/tmp/ray-si"
SI_GCS_PORT=6390
SI_CLIENT_PORT=6391
SI_DASHBOARD_PORT=8266
SI_AGENT_PORT=52366
SI_ADDRESS="127.0.0.1:${SI_GCS_PORT}"
SI_DASHBOARD="http://127.0.0.1:${SI_DASHBOARD_PORT}"
RAY_BIN="./venv/bin/ray"

# ---- the shared lock (raypoolkit.rehearsal_lock; RayPoolKit's docs/rehearsal-lock.md) ----
PYTHON_BIN="./venv/bin/python"

GRACE="${RAY_CLUSTER_GRACE:-15}"

say() { echo ">> ray_cluster: $*"; }
err() { echo ">> ray_cluster: $*" >&2; }

rehearsal_lock() {
    # rehearsal_lock COMMAND [OPTIONS]: the pinned package's lock, run as a process of its own and
    # never piped. Its exit codes are the contract's (section 7); its refusals go to stderr.
    "$PYTHON_BIN" -m raypoolkit.rehearsal_lock "$@"
}

release_after_failure() {
    # A failed or interrupted start releases SI's lock. The module's refusal is printed, not
    # hidden: it leaves the lock held while anything of the cluster is still alive (contract
    # section 7). The caller's exit stays the failure's, whatever release returned.
    rehearsal_lock release --project "$LOCK_PROJECT" --ray-temp-dir "$SI_TEMP_DIR" ||
        err "the rehearsal lock stays held: something of SI's cluster may still be alive; run 'status', then 'stop', or ask the user"
}

lock_dir() {
    # The lock's location, asked of the pinned package (contract sections 2 and 3), so that this
    # script never spells it.
    "$PYTHON_BIN" -c 'from raypoolkit.rehearsal_lock import default_lock_dir; print(default_lock_dir())'
}

owner_field() {
    # owner_field FILE KEY: the value of KEY in the owner file FILE ("" if absent or no file). Each
    # line is "key: value", split at its first ": " (contract section 4).
    [ -f "$1" ] || return 0
    sed -n "s/^$2: //p" "$1" | head -n 1
}

print_owner() {
    # print_owner FILE: the owner file, indented, or "(no owner file)".
    if [ -f "$1" ]; then
        sed 's/^/    /' "$1"
    else
        echo "    (no owner file)"
    fi
}

# ---- the targeted stop (brief section 3) ----

temp_dir_regex() {
    # temp_dir_regex DIR: an ERE matching DIR in its /tmp and /private/tmp spellings, as a whole
    # path component (so /tmp/ray-si does not match /tmp/ray-simple).
    local d="${1#/private}"
    d="$(printf '%s' "$d" | sed 's/[.]/[.]/g')"
    printf '(/private)?%s([/ =]|$)' "$d"
}

list_cluster_pids() {
    # list_cluster_pids DIR GCS_PORT: one pid per line: every process whose command line names DIR,
    # and every descendant of those. Also the cluster's Ray client server, found on a real
    # cluster (prompt 01a's proof): it has no Ray ancestor in the process table (its parent is
    # launchd) and carries no temp dir, only `-m ray.util.client.server --address=127.0.0.1:GCS_PORT`.
    # Never this script's own process or its ancestors, nor any process running this script
    # (whose arguments may name DIR).
    local re re2
    re="$(temp_dir_regex "$1")"
    re2="ray[.]util[.]client[.]server --address=127[.]0[.]0[.]1:$2( |\$)"
    ps -axww -o pid= -o ppid= -o command= | awk -v re="$re" -v re2="$re2" -v self="$$" '
        { pid=$1; ppid=$2; par[pid]=ppid; cmd[pid]=$0; sub(/^[ ]*[0-9]+[ ]+[0-9]+[ ]+/, "", cmd[pid]); all[pid]=1 }
        END {
            # self and its ancestors are never ours to signal
            p=self; while (p in par && p > 1) { safe[p]=1; p=par[p] }
            for (p in all) {
                if (p in safe) continue
                if (cmd[p] ~ /ray_cluster[.]sh/) continue
                if (cmd[p] ~ re || cmd[p] ~ re2) mark[p]=1
            }
            do {
                changed=0
                for (p in all) {
                    if ((p in mark) || (p in safe)) continue
                    if ((par[p] in mark) && !(cmd[p] ~ /ray_cluster[.]sh/)) { mark[p]=1; changed=1 }
                }
            } while (changed)
            for (p in mark) print p
        }' | sort -n
}

describe_pid() {
    ps -ww -o pid= -o ppid= -o command= -p "$1" 2>/dev/null | cut -c1-150
}

port_listeners() {
    # port_listeners PORT: the lsof lines of the listeners on 127.0.0.1/any, empty when free.
    lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | sed 1d
}

alive() { kill -0 "$1" 2>/dev/null; }

stop_cluster() {
    # stop_cluster DIR GCS_PORT CLIENT_PORT DASHBOARD_PORT AGENT_PORT. Returns 0 when nothing is
    # left and all four ports are free. All five arguments are required: a call with fewer would
    # silently check fewer ports.
    if [ $# -ne 5 ]; then
        err "usage: stop_cluster DIR GCS_PORT CLIENT_PORT DASHBOARD_PORT AGENT_PORT"
        return 2
    fi
    local dir="$1" port="$2" ports="$2 $3 $4 $5" pids p remaining left i n q held
    pids="$(list_cluster_pids "$dir" "$port" | tr '\n' ' ')"
    pids="${pids% }"
    if [ -z "$pids" ]; then
        say "no process names $dir"
    else
        n="$(echo $pids | wc -w | tr -d ' ')"
        say "SIGTERM to $n process(es) naming $dir, and their descendants: $pids"
        for p in $pids; do describe_pid "$p" | sed 's/^/    /'; done
        for p in $pids; do kill -TERM "$p" 2>/dev/null; done
        # The captured set is kept: workers re-parented to launchd once their raylet dies would
        # escape a second descendant search.
        i=0
        while [ "$i" -lt $((GRACE * 2)) ]; do
            remaining=""
            for p in $pids; do alive "$p" && remaining="$remaining $p"; done
            [ -z "$remaining" ] && break
            sleep 0.5
            i=$((i + 1))
        done
        remaining=""
        for p in $pids $(list_cluster_pids "$dir" "$port"); do
            alive "$p" && remaining="$remaining $p"
        done
        remaining="$(echo $remaining | tr ' ' '\n' | sort -nu | tr '\n' ' ')"
        remaining="${remaining% }"
        if [ -n "$remaining" ]; then
            say "grace period of ${GRACE}s over; SIGKILL to: $remaining"
            for p in $remaining; do kill -KILL "$p" 2>/dev/null; done
            sleep 1
        fi
    fi
    # Confirm.
    left=""
    for p in $pids $(list_cluster_pids "$dir" "$port"); do
        alive "$p" && left="$left $p"
    done
    if [ -n "$left" ]; then
        err "processes still alive after SIGKILL:$left"
        return 1
    fi
    held=""
    for q in $ports; do
        if [ -n "$(port_listeners "$q")" ]; then
            err "port $q is still held:"
            port_listeners "$q" >&2
            held="$held $q"
        fi
    done
    [ -z "$held" ] || return 1
    say "no process names $dir; ports $ports are free"
    return 0
}

# ---- commands ----

cmd_start() {
    if [ $# -lt 1 ]; then usage >&2; return 2; fi
    local purpose="$1" ncpus=4
    shift
    while [ $# -gt 0 ]; do
        case "$1" in
            --num-cpus) [ $# -ge 2 ] || { usage >&2; return 2; }; ncpus="$2"; shift 2 ;;
            *) usage >&2; return 2 ;;
        esac
    done
    case "$ncpus" in ''|*[!0-9]*) err "--num-cpus must be a positive integer"; return 2 ;; esac
    [ -x "$RAY_BIN" ] || { err "$RAY_BIN not found: run from the repository root"; return 2; }

    # The module's exit is passed through: 3 the lock held, or the old location exists (nothing
    # created); 4 a process of the cluster alive, or ps unreadable (the lock released again; this
    # is the stale-cluster check, by the rule release will apply); 1 the owner file not written;
    # 2 a usage error.
    rehearsal_lock acquire --project "$LOCK_PROJECT" --purpose "$purpose" \
        --ray-temp-dir "$SI_TEMP_DIR" --ray-address "$SI_ADDRESS" || return $?

    # A held port is not ours to take. Without this, a ray start that fails on a foreign listener
    # leaves a stop whose port check cannot pass, and the lock held.
    local q held=""
    for q in "$SI_GCS_PORT" "$SI_CLIENT_PORT" "$SI_DASHBOARD_PORT" "$SI_AGENT_PORT"; do
        if [ -n "$(port_listeners "$q")" ]; then
            err "port $q is already held; not starting:"
            port_listeners "$q" >&2
            held="$held $q"
        fi
    done
    if [ -n "$held" ]; then
        release_after_failure
        return 4
    fi

    trap 'err "interrupted; stopping what was started"; stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT" "$SI_CLIENT_PORT" "$SI_DASHBOARD_PORT" "$SI_AGENT_PORT"; release_after_failure; exit 130' INT TERM

    # Ray's authentication mode, named (ray-sqla-align 01). Since Ray 2.59, `ray start` infers
    # token mode from the token file (~/.ray/auth_token) unless told; SI names it, as
    # config/ray_auth.py does for every driver, so that the cluster and its drivers agree.
    export RAY_AUTH_MODE="${RAY_AUTH_MODE:-token}"
    local t0=$SECONDS
    "$RAY_BIN" start --head --temp-dir "$SI_TEMP_DIR" --port "$SI_GCS_PORT" \
        --ray-client-server-port "$SI_CLIENT_PORT" --dashboard-port "$SI_DASHBOARD_PORT" \
        --dashboard-agent-listen-port "$SI_AGENT_PORT" --num-cpus "$ncpus" --disable-usage-stats
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        err "ray start failed (exit $rc); stopping what it started and releasing the lock"
        stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT" "$SI_CLIENT_PORT" "$SI_DASHBOARD_PORT" "$SI_AGENT_PORT"
        release_after_failure
        trap - INT TERM
        return 1
    fi

    local gcs
    gcs="$(list_cluster_pids "$SI_TEMP_DIR" "$SI_GCS_PORT" | while read -r p; do
        describe_pid "$p" | grep -q 'gcs_server' && echo "$p"
    done | head -n 1)"
    if [ -z "$gcs" ]; then
        err "ray start succeeded but no gcs_server names $SI_TEMP_DIR; stopping"
        stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT" "$SI_CLIENT_PORT" "$SI_DASHBOARD_PORT" "$SI_AGENT_PORT"
        release_after_failure
        trap - INT TERM
        return 1
    fi
    # The gcs_server's pid in the owner file: release refuses while it is alive (contract section
    # 6, "What it asks of a caller"). A refusal is treated as no gcs_server.
    if ! rehearsal_lock set-pid --project "$LOCK_PROJECT" --ray-temp-dir "$SI_TEMP_DIR" "$gcs"; then
        err "set-pid refused the gcs_server's pid $gcs; stopping"
        stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT" "$SI_CLIENT_PORT" "$SI_DASHBOARD_PORT" "$SI_AGENT_PORT"
        release_after_failure
        trap - INT TERM
        return 1
    fi
    trap - INT TERM
    say "address $SI_ADDRESS"
    say "dashboard $SI_DASHBOARD"
    say "actors: RAY_AUTH_MODE=token $RAY_BIN list actors --address $SI_ADDRESS"
    say "started in $((SECONDS - t0))s; gcs_server pid $gcs"
    return 0
}

cmd_stop() {
    local t0=$SECONDS d
    # Whose lock is it? The module has no command for that, so the owner file is read at the
    # location the package gives (contract sections 3 and 4). If the lock is another project's,
    # or has no owner file, nothing is touched: not even SI's own cluster is stopped.
    d="$(lock_dir)"
    if [ -z "$d" ]; then
        err "could not ask raypoolkit.rehearsal_lock where the lock is; touching nothing"
        return 1
    fi
    if [ -d "$d" ]; then
        local proj tdir
        proj="$(owner_field "$d/owner" project)"
        tdir="$(owner_field "$d/owner" ray_temp_dir)"
        if [ "$proj" != "$LOCK_PROJECT" ] || [ "$tdir" != "$SI_TEMP_DIR" ]; then
            err "the rehearsal lock is another project's (project='$proj' ray_temp_dir='$tdir'); touching nothing. Its owner file:"
            print_owner "$d/owner" >&2
            return 1
        fi
    fi
    stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT" "$SI_CLIENT_PORT" "$SI_DASHBOARD_PORT" "$SI_AGENT_PORT" || return 1
    rehearsal_lock release --project "$LOCK_PROJECT" --ray-temp-dir "$SI_TEMP_DIR" || return 1
    say "stopped in $((SECONDS - t0))s"
    return 0
}

cmd_status() {
    # The lock, its owner file, the old location and the processes by the module's rule: those
    # release refuses on (contract section 8).
    rehearsal_lock status --ray-temp-dir "$SI_TEMP_DIR" --ray-address "$SI_ADDRESS" ||
        err "raypoolkit.rehearsal_lock status failed"
    # Then the processes stop signals, by this script's rule. Where the two listings differ, stop
    # leaves something that release then refuses on.
    local pids
    pids="$(list_cluster_pids "$SI_TEMP_DIR" "$SI_GCS_PORT")"
    if [ -z "$pids" ]; then
        echo "SI cluster ($SI_TEMP_DIR), the processes stop signals: none"
    else
        echo "SI cluster ($SI_TEMP_DIR), the processes stop signals: $(echo "$pids" | wc -l | tr -d ' ')"
        local p
        for p in $pids; do describe_pid "$p" | sed 's/^/    /'; done
    fi
    local q
    for q in "$SI_GCS_PORT" "$SI_CLIENT_PORT" "$SI_DASHBOARD_PORT" "$SI_AGENT_PORT"; do
        if [ -n "$(port_listeners "$q")" ]; then echo "port $q: held"; else echo "port $q: free"; fi
    done
    return 0
}

main() {
    case "${1:-}" in
        start) shift; cmd_start "$@" ;;
        stop) shift; cmd_stop ;;
        status) shift; cmd_status ;;
        -h|--help|help|"") usage; [ -z "${1:-}" ] && return 2; return 0 ;;
        *) usage >&2; return 2 ;;
    esac
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
    exit $?
fi
