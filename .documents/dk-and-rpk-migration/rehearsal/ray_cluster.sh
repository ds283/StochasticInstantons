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
# SecondaryGWKit. Written for dk-and-rpk-migration prompt 01a, which implements
# .prompts/dk-and-rpk-migration/rehearsal-lock-brief.md: section 2 (the lock) and section 3 (the
# cluster) are followed exactly, because the contract is shared with the other projects.
#
# This script NEVER runs `ray stop`, which stops every Ray process on the machine. It stops SI's
# cluster by signalling the processes whose command line names SI's temp dir, and their
# descendants (Ray's workers carry only their process title, so they are reached through their
# parent). It never waits on a held lock, and never removes a lock that is not SI's.
#
# It may be sourced (its functions used, its main skipped): the proof of prompt 01a stops a
# decoy cluster by calling stop_cluster with the decoy's temp dir.

set -u

usage() {
    cat <<'EOF2'
usage: ray_cluster.sh start PURPOSE [--num-cpus N]
       ray_cluster.sh stop
       ray_cluster.sh status
       ray_cluster.sh --help

Run from the repository root.

  start PURPOSE   take the rehearsal lock (~/ScienceData/.rehearsal-lock), then start SI's Ray
                  head on /tmp/ray-si: GCS 6390, client 6391, dashboard 8266, dashboard agent
                  52366, N CPUs (default 4). PURPOSE is written to the lock's owner file, e.g.
                  "dk-and-rpk-migration 02 (RH0)". If the lock is held, prints its owner file and
                  exits 3, starting nothing. Prints the cluster's address and the command that
                  lists its actors.
  stop            stop SI's processes (SIGTERM to every process naming /tmp/ray-si, and to their
                  descendants; a grace period of $RAY_CLUSTER_GRACE seconds, default 15; then
                  SIGKILL), confirm none is left and port 6390 is free, then release the lock if
                  its owner is SI's. Touches nothing if the lock is another project's.
  status          the lock, its owner file, whether the owner's pid is alive, and SI's processes.

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

# ---- the shared lock (rehearsal-lock-brief.md, section 2) ----
LOCK_PARENT="$HOME/ScienceData"
LOCK_DIR="$LOCK_PARENT/.rehearsal-lock"
OWNER_FILE="$LOCK_DIR/owner"

GRACE="${RAY_CLUSTER_GRACE:-15}"

say() { echo ">> ray_cluster: $*"; }
err() { echo ">> ray_cluster: $*" >&2; }

iso_now() {
    # ISO 8601, local time with its offset as +HH:MM (macOS date gives +HHMM).
    date +%Y-%m-%dT%H:%M:%S%z | sed -E 's/([+-][0-9]{2})([0-9]{2})$/\1:\2/'
}

owner_field() {
    # owner_field KEY: the value of KEY in the owner file ("" if absent or no file).
    [ -f "$OWNER_FILE" ] || return 0
    sed -n "s/^$1: //p" "$OWNER_FILE" | head -n 1
}

write_owner() {
    # write_owner PURPOSE PID: the seven keys, in the brief's order; written to owner.tmp, renamed.
    {
        echo "project: $LOCK_PROJECT"
        echo "purpose: $1"
        echo "acquired: $(iso_now)"
        echo "host: $(hostname -s)"
        echo "ray_temp_dir: $SI_TEMP_DIR"
        echo "ray_address: $SI_ADDRESS"
        echo "pid: $2"
    } > "$LOCK_DIR/owner.tmp" && mv "$LOCK_DIR/owner.tmp" "$OWNER_FILE"
}

print_owner() {
    if [ -f "$OWNER_FILE" ]; then
        sed 's/^/    /' "$OWNER_FILE"
    else
        echo "    (no owner file)"
    fi
}

acquire_lock() {
    # acquire_lock PURPOSE. mkdir WITHOUT -p: the atomic step. Returns 3 when the lock is held.
    mkdir -p "$LOCK_PARENT" || return 1
    if mkdir "$LOCK_DIR" 2>/dev/null; then
        write_owner "$1" "-"
        return 0
    fi
    err "the rehearsal lock is held ($LOCK_DIR); its owner file:"
    print_owner >&2
    err "stop and ask the user; this script never waits on, or breaks, the lock"
    return 3
}

release_lock() {
    # Release only if the owner's project and ray_temp_dir are SI's (brief section 2).
    if [ ! -d "$LOCK_DIR" ]; then
        say "no lock to release"
        return 0
    fi
    local proj tdir
    proj="$(owner_field project)"
    tdir="$(owner_field ray_temp_dir)"
    if [ "$proj" != "$LOCK_PROJECT" ] || [ "$tdir" != "$SI_TEMP_DIR" ]; then
        err "the lock is not SI's; not releasing it. owner has project='$proj' ray_temp_dir='$tdir'; SI is project='$LOCK_PROJECT' ray_temp_dir='$SI_TEMP_DIR'"
        return 1
    fi
    rm -f "$OWNER_FILE" "$LOCK_DIR/owner.tmp"
    rmdir "$LOCK_DIR" || { err "could not rmdir $LOCK_DIR"; return 1; }
    say "released the rehearsal lock"
    return 0
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
    # stop_cluster DIR GCS_PORT. Returns 0 when nothing is left and the port is free.
    local dir="$1" port="$2" pids p remaining left i n
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
    if [ -n "$(port_listeners "$port")" ]; then
        err "port $port is still held:"
        port_listeners "$port" >&2
        return 1
    fi
    say "no process names $dir; port $port is free"
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

    acquire_lock "$purpose" || return $?

    # The lock is free but SI's temp dir is named by a live process: a stale cluster. Not ours to
    # guess about; release the lock and say so.
    if [ -n "$(list_cluster_pids "$SI_TEMP_DIR" "$SI_GCS_PORT")" ]; then
        err "processes naming $SI_TEMP_DIR are already running (a stale cluster?); not starting. Run 'stop' first."
        release_lock
        return 4
    fi

    trap 'err "interrupted; stopping what was started"; stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT"; release_lock; exit 130' INT TERM

    local t0=$SECONDS
    "$RAY_BIN" start --head --temp-dir "$SI_TEMP_DIR" --port "$SI_GCS_PORT" \
        --ray-client-server-port "$SI_CLIENT_PORT" --dashboard-port "$SI_DASHBOARD_PORT" \
        --dashboard-agent-listen-port "$SI_AGENT_PORT" --num-cpus "$ncpus" --disable-usage-stats
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        err "ray start failed (exit $rc); stopping what it started and releasing the lock"
        stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT"
        release_lock
        trap - INT TERM
        return 1
    fi

    local gcs
    gcs="$(list_cluster_pids "$SI_TEMP_DIR" "$SI_GCS_PORT" | while read -r p; do
        describe_pid "$p" | grep -q 'gcs_server' && echo "$p"
    done | head -n 1)"
    if [ -z "$gcs" ]; then
        err "ray start succeeded but no gcs_server names $SI_TEMP_DIR; stopping"
        stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT"
        release_lock
        trap - INT TERM
        return 1
    fi
    write_owner "$purpose" "$gcs"
    trap - INT TERM
    say "address $SI_ADDRESS"
    say "dashboard $SI_DASHBOARD"
    say "actors: $RAY_BIN list actors --address $SI_ADDRESS"
    say "started in $((SECONDS - t0))s; gcs_server pid $gcs"
    return 0
}

cmd_stop() {
    local t0=$SECONDS
    if [ -d "$LOCK_DIR" ]; then
        local proj tdir
        proj="$(owner_field project)"
        tdir="$(owner_field ray_temp_dir)"
        if [ "$proj" != "$LOCK_PROJECT" ] || [ "$tdir" != "$SI_TEMP_DIR" ]; then
            err "the rehearsal lock is another project's (project='$proj' ray_temp_dir='$tdir'); touching nothing. Its owner file:"
            print_owner >&2
            return 1
        fi
    fi
    stop_cluster "$SI_TEMP_DIR" "$SI_GCS_PORT" || return 1
    release_lock || return 1
    say "stopped in $((SECONDS - t0))s"
    return 0
}

cmd_status() {
    if [ -d "$LOCK_DIR" ]; then
        echo "lock: HELD ($LOCK_DIR)"
        print_owner
        local pid
        pid="$(owner_field pid)"
        case "$pid" in
            ''|-) echo "owner pid: ${pid:--} (no cluster pid recorded yet)" ;;
            *) if alive "$pid"; then echo "owner pid $pid: alive"; else echo "owner pid $pid: NOT alive"; fi ;;
        esac
    else
        echo "lock: free ($LOCK_DIR does not exist)"
    fi
    local pids
    pids="$(list_cluster_pids "$SI_TEMP_DIR" "$SI_GCS_PORT")"
    if [ -z "$pids" ]; then
        echo "SI cluster ($SI_TEMP_DIR): no processes"
    else
        echo "SI cluster ($SI_TEMP_DIR): $(echo "$pids" | wc -l | tr -d ' ') process(es)"
        local p
        for p in $pids; do describe_pid "$p" | sed 's/^/    /'; done
    fi
    if [ -n "$(port_listeners "$SI_GCS_PORT")" ]; then echo "port $SI_GCS_PORT: held"; else echo "port $SI_GCS_PORT: free"; fi
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
