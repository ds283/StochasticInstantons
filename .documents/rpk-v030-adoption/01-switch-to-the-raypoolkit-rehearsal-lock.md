# 01 — switch to the `raypoolkit` rehearsal lock (`v0.3.0`)

**Subject:** Pin `raypoolkit` `v0.3.0`, and replace the lock half of SI's `ray_cluster.sh` with the
package's `raypoolkit.rehearsal_lock`
**Commits:** `3d6328e1694a6878e69d2d8437502bf41c402b4a` (the pin alone, C6), then `6c60b81`, on the
branch `rpk-v030-adoption`, on top of `0f190c8`
**Date:** 2026-10-25, by Claude Opus 5.5
**Result:** **COMPLETE.** The venv holds `raypoolkit` 0.3.0 at
`67a75b97a656accb98195a4bda93f64e6a5f3fb2`, not editable, and nothing else in it moved. The script
takes, records and releases the lock through the module and never spells its location; acceptance
2's grep goes from 5 lines to 0. S-1 to S-6 and the nine steps of the live check give the exits the
prompt names, and none of the scratch checks reached `ray start`. B1–B4 are each caught. The suites
give 732 (731 passed, 1 skipped) and 67 (66 passed, 1 skipped) before and after. No `.py` file and
no test changed. No issue is opened.

Prompt: [`.prompts/rpk-v030-adoption/01-switch-to-the-raypoolkit-rehearsal-lock.md`](../../.prompts/rpk-v030-adoption/01-switch-to-the-raypoolkit-rehearsal-lock.md),
corrected by the orchestrator's briefing (§0 of its note). Every command and its output is in
[`out/`](out/): `01-gate.txt`, `01-pip.txt`, `01-suites.txt`, `01-scratch.txt`, `01-live.txt` and
`01-breakage.txt`.

## What shipped

- **P1 — the pin** (`3d6328e`, a commit of its own). `requirements.txt:59` reads
  `raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.3.0`; no other line moved. The venv was
  installed from it with `./venv/bin/pip install -r requirements.txt`, not editable.
- **S1 — the lock half removed** from `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`:
  `LOCK_PARENT`, `LOCK_DIR`, `OWNER_FILE` and their comment; `iso_now`, `write_owner`,
  `acquire_lock` and `release_lock`. `owner_field` and `print_owner` stay, each now taking the
  owner file's path, for stop's owner check (C4). The cluster half is unchanged: `LOCK_PROJECT`, the
  cluster's values, `say`, `err`, `temp_dir_regex`, `list_cluster_pids`, `describe_pid`,
  `port_listeners`, `alive`, `stop_cluster`, the `ray start` line and `main`. The script can still
  be sourced for `stop_cluster`. 398 lines become 389.
- **The calls.** One function, `rehearsal_lock`, runs `./venv/bin/python -m raypoolkit.rehearsal_lock
  "$@"` (via `PYTHON_BIN`), unpiped. Every value comes from the script's variables (`$LOCK_PROJECT`,
  `$SI_TEMP_DIR`, `$SI_ADDRESS`, the address spelled `127.0.0.1:6390`). Two small helpers sit on
  it: `release_after_failure`, the release on a failed or interrupted start, which prints that the
  lock stays held when the module refuses; and `lock_dir`, which asks the package for
  `default_lock_dir()`.
- **S2 — `cmd_start`**: `acquire` with the `PURPOSE`, its exit passed through (`|| return $?`); the
  stale-cluster check dropped (C3); the held-port check kept, with `release_after_failure` then
  `return 4`; after `ray start` and the `gcs_server` found, `set-pid` with its pid, a refusal treated
  as the no-`gcs_server` path (`stop_cluster`, release, trap cleared, `return 1`); the `ray start`
  failed path, the no-`gcs_server` path and the trap call `release_after_failure`, and return 1 (the
  trap exits 130) whatever it returned.
- **S3 — `cmd_stop`**: the owner check first, reading `owner` at the directory `lock_dir` prints;
  another project's lock, or one with no owner file, prints its owner file and returns 1 before
  `stop_cluster`. If the package cannot be asked, it touches nothing and returns 1. Then
  `stop_cluster` (unchanged), then the module's `release` (`|| return 1`).
- **S4 — `cmd_status`, the header and the usage.** `status` prints the module's
  `status --ray-temp-dir … --ray-address …`, then the script's own listing under the heading
  `SI cluster (/tmp/ray-si), the processes stop signals: …` (C5), then the four ports; exit 0. The
  header names the module, its contract at the pinned tag, this campaign as the change, and the
  brief's §3 as what still governs the cluster; it says why no command line of the script's names
  the temp dir. The usage text gives `start`'s new exits (3 also for the old location, 4 also for a
  live process of the cluster, a failed start leaving the lock held while anything of the cluster
  is alive) and `status`'s two listings; `stop` is unchanged. `:64`'s pointer to the brief's §3
  stays (now `:78`).
- **D1 — the documents.**
  - `CLAUDE.md:14-24` (was `:14-20`): one sentence added, at `:18-22`, naming
    `raypoolkit.rehearsal_lock`, its location, the projects sharing it, its contract, and exit 3
    (held, or the old location present) as stop and ask, never wait. The paragraph is rewrapped;
    the `ray stop` sentence and its citation of the brief stay.
  - `CLAUDE.md:131` (was `:127`): `raypoolkit` `v0.3.0`.
  - `.documents/INFRASTRUCTURE.md:41-44`: `raypoolkit` `v0.3.0`, `RayWorkPool` and the shared
    rehearsal lock, with RayPoolKit's `README.md` ("Using it", "The rehearsal lock") and the
    contract `docs/rehearsal-lock.md` at the tag.
  - `.documents/INFRASTRUCTURE.md:458` (was `:456`) and `.documents/architecture-summary.md:344`:
    "pinned in `requirements.txt` at `v0.3.0`" (briefing correction 2).
- **This note and `out/`; the board; this campaign's line in `.prompts/INDEX.md`.**

## Deviations from the prompt

1. **The Gate's `runregistrykit list` was not met as written.** `STRUCTURALLY REQUIRED` (briefing
   correction 1). It exits 1 with `!! No runregistrykit.toml …`: the file is `rrk-adoption`'s, and
   this branch is cut from `main`. The item was met instead by `ls -A var/runs` (empty) and
   `pgrep -lf 'main.py|plot_GradientCoupledSolutions|plot_InstantonSolutions'` (nothing).
   `runregistrykit.toml` was not created.
2. **Two more statements of the pin changed**: `.documents/INFRASTRUCTURE.md:455-456` (§9) and
   `.documents/architecture-summary.md:343-344` ("RayWorkPool"). `STRUCTURALLY REQUIRED` (briefing
   correction 2): each states the current pin, which README §0.3 undercounted. The other "at
   `v0.2.0`" citations stay (C8). `architecture-summary.md` joins the second commit's list.
3. **What the script names.** `IMPLEMENTATION CHOICE` (the orchestrator's, briefing correction 3).
   `.raypoolkit` appears in the usage text alone (`:54`), never in a line of code; `ScienceData`
   and `.rehearsal-lock` appear nowhere in the script, comments included, nor in `CLAUDE.md`. The
   old location is written "the old location".
4. **The absolute path in `status`.** `NOTED` (briefing correction 4). Step 3 printed
   `lock: HELD (/Users/ds283/.raypoolkit/rehearsal-lock)`.
5. **`/tmp/ray-si` stays as a directory** of Ray's session directories. `NOTED` (briefing
   correction 5). "Nothing of `/tmp/ray-si` left" was judged by both listings empty and the four
   ports free.
6. **A sixth output file, `out/01-gate.txt`**, holding the Gate's checks and acceptance 2's and 3's
   greps before any change. `IMPLEMENTATION CHOICE`: the prompt names five files, none of them for
   the Gate.
7. **S-5's set-up command named `/tmp/ray-si`.** `UNINTENDED DRIFT`. The `printf` that wrote the
   scratch old location's owner file carried `ray_temp_dir: /tmp/ray-si` in its text, against
   README §5's "no command line names `/tmp/ray-si` except a by-hand lock command". It ran in the
   foreground, alone, and finished before the next command; no lock command or script ran beside
   it, and it wrote only under the scratch `HOME`. Nothing was listed because of it.
8. **Step 6's `status` was not identical to step 3's.** `NOTED`. The lock's lines, the owner file
   and `owner pid 17315: alive` were the same; both listings had grown from 18 processes to 22 by
   four `ray::IDLE` workers under the raylet (`17588`–`17591`), started for step 5's driver. Both
   rules listed them, and step 8's stop signalled all 22.
9. **The script's listing heading and two helpers** (`release_after_failure`, `lock_dir`).
   `IMPLEMENTATION CHOICE`, within §2.3: the module is still called through the one function
   `rehearsal_lock`. The heading changed from `SI cluster (/tmp/ray-si): no processes` so that it
   says what the listing is (C5).
10. **B3 and B4 used no scratch `HOME`.** `NOTED`. Their checks are greps of the tree; B1 and B2
    each ran against a fresh scratch `HOME`.

## Verification performed

### The Gate (`out/01-gate.txt`)

At `0f190c8`, before any change: branch `rpk-v030-adoption`, the tree clean but for
`.documents/rpk-v030-adoption/` just made, no stash. `var/runs/` empty, no driver running, no
`gcs_server` or `raylet` (`pgrep` exit 1), `RAY_ADDRESS` unset, no `/tmp/ray/ray_current_cluster`.
The venv: `raypoolkit` 0.2.0 at `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`, `datastorekit` 0.5.0 at
`f47b9a255e9ad58e0d0eaf85644f53b575884d31` (both `direct_url.json` VCS records, no `dir_info`),
`runregistrykit` 0.2.0, `ray` 2.55.1. Neither lock location exists; `~/.raypoolkit/` exists, empty.
The old script's `status`: `lock: free`, `SI cluster (/tmp/ray-si): no processes`, the four ports
free, exit 0. The script is blob `6c8eada`, 398 lines. Acceptance 2's grep: 5 lines (`:19`, `:45`,
`:75`, `:76`, `:77`); `git grep -c 'raypoolkit\.rehearsal_lock'` on the script: no match.

### The pin (`out/01-pip.txt`)

- **Before:** `pip freeze` 84 lines; `pip check`: `No broken requirements found.`
- **The dry run** (`./venv/bin/pip install --dry-run -r requirements.txt`, exit 0): 71 `Requirement
  already satisfied` lines, `Collecting` lines for `datastorekit` (pip re-resolving its VCS line,
  not reinstalling it) and `raypoolkit`, and one result line, `Would install raypoolkit-0.3.0`.
  pip's `Resolved … to commit caf00765…` is the tag object, as at `dk-and-rpk-migration` 03.
- **The install** (exit 0): `Successfully installed raypoolkit-0.3.0`, and nothing else installed,
  upgraded or removed.
- **After:** `diff` of the two freezes is exactly
  ```text
  66c66
  < raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976
  ---
  > raypoolkit @ git+https://github.com/ds283/RayPoolKit@67a75b97a656accb98195a4bda93f64e6a5f3fb2
  ```
  84 lines still; `pip check` clean. `raypoolkit-0.3.0.dist-info/direct_url.json` is a VCS record,
  `commit_id` `67a75b97a656accb98195a4bda93f64e6a5f3fb2`, `requested_revision` `v0.3.0`, no
  `dir_info`; the only `.pth` in `site-packages` is `_virtualenv.pth`.
- `./venv/bin/python -m raypoolkit.rehearsal_lock --help`, exit 0, first line
  `usage: python -m raypoolkit.rehearsal_lock [-h]`.

### The script

`bash -n` passes. Acceptance 2's grep, on the working tree after the change: **0** lines.
Acceptance 3: `git grep -c 'raypoolkit\.rehearsal_lock'` on the script gives 7; `git grep -n -E
'raypoolkit/rehearsal-lock|\.raypoolkit'` on it finds one line, `:54`, the usage text.

### The scratch checks (`out/01-scratch.txt`)

One scratch `HOME`, made by `mktemp -d` under the agent's scratch directory, removed at the end.
The real `status` first: `lock: free`, `Ray processes of /tmp/ray-si: none`, the script's listing
`none`, the four ports free. No `start` printed anything of `ray start`'s.

| # | Command | Exit | What it printed, and the lock after |
|---|---|---|---|
| S-1 | `status` | 0 | `lock: free (<H>/.raypoolkit/rehearsal-lock does not exist)`; no `old location` line; `Ray processes of /tmp/ray-si: none`; `SI cluster (/tmp/ray-si), the processes stop signals: none`; four ports free. Lock: none |
| S-2 | `stop` | 0 | `no process names /tmp/ray-si; ports 6390 6391 8266 52366 are free`; `no lock to release (<H>/…)`. Lock: none |
| S-3 | `acquire` by hand as SI (0), then `stop` | 0 | `released the rehearsal lock (<H>/…)`; then `status` exit 0, `lock: free`. Lock: none |
| S-4 | `acquire` by hand as ChamPBH (0), then `stop` | 1 | `the rehearsal lock is another project's (project='ChamPBH' ray_temp_dir='/tmp/ray-cpbh'); touching nothing`, the owner file; no line of `stop_cluster`'s. Lock: ChamPBH's |
| | then `start "rpk-v030-adoption 01 S-4"` | 3 | the module's `the rehearsal lock is held (…)`, the owner file, `stop and ask the user; …`; nothing started. Then `release` by hand as ChamPBH: 0. Lock: none |
| S-5 | the old location made in `<H>`, then `start "rpk-v030-adoption 01 S-5"` | 3 | `the old location of the rehearsal lock exists (<H>/…)`, its owner file, `… nothing was created`; `<H>/.raypoolkit/rehearsal-lock` not created |
| | then `status` | 0 | `lock: free (…)`, `old location: PRESENT (<H>/…)`. The scratch old location then removed |
| S-6 | a listener on `127.0.0.1:6391` (pid 17090), then `start "rpk-v030-adoption 01 S-6"` | 4 | `acquired …`; `port 6391 is already held; not starting:` with the listener's `lsof` line; `released the rehearsal lock (…)` (`pid: -`) |
| | then `status` | 0 | `lock: free`; both listings none; `port 6391: held`, the other three free. The listener then killed; port 6391 free |

### The live check (`out/01-live.txt`)

Real `HOME`, the script at the working tree, each command a shell command of its own.

| Step | Command | Exit | Key line |
|---|---|---|---|
| 1 | `python -m raypoolkit.rehearsal_lock status` | 0 | `lock: free (/Users/ds283/.raypoolkit/rehearsal-lock does not exist)`; no `old location` line |
| 2 | `ray_cluster.sh start "rpk-v030-adoption 01 (live check)"` | 0 | `acquired the rehearsal lock (…)`; `recorded pid 17315 in /Users/ds283/.raypoolkit/rehearsal-lock/owner`; `address 127.0.0.1:6390`; `started in 7s; gcs_server pid 17315` |
| 3 | `ray_cluster.sh status` | 0 | `lock: HELD (/Users/ds283/.raypoolkit/rehearsal-lock)`; owner `project: StochasticInstantons`, `ray_temp_dir: /tmp/ray-si`, `ray_address: 127.0.0.1:6390`, `pid: 17315`; `owner pid 17315: alive`; `Ray processes of /tmp/ray-si: 18`, among them the `gcs_server` (17315), the client server (17317) and the raylet (17332); the script's listing the same 18; the four ports held |
| 4 | `… ray-processes --ray-temp-dir /tmp/ray-si --ray-address 127.0.0.1:6390` | 1 | the same 18 pids |
| 5 | a driver: `ray.init(address="127.0.0.1:6390")` | 0 | `Connected to Ray cluster`; `'CPU': 4.0` |
| 6 | `ray_cluster.sh start "rpk-v030-adoption 01 (second start)"` | 3 | `the rehearsal lock is held (…)`, the owner file with `pid: 17315`. `status` after: the lock's lines unchanged; 22 processes (deviation 8) |
| 7 | `… release --project StochasticInstantons --ray-temp-dir /tmp/ray-si` | 1 | `release: the recorded pid 17315 is alive; not releasing`; the lock still held |
| 8 | `ray_cluster.sh stop` | 0 | `SIGTERM to 22 process(es)`; `grace period of 15s over; SIGKILL to: 17315 17316`; `no process names /tmp/ray-si; ports … are free`; `released the rehearsal lock (/Users/ds283/.raypoolkit/rehearsal-lock)`; `stopped in 20s` |
| 9 | `ray_cluster.sh status`, then step 4's command | 0, 0 | `lock: free (…)`; `Ray processes of /tmp/ray-si: none`; the script's listing none; the four ports free; `ray-processes` printed nothing |

Afterwards neither lock location exists and `pgrep -lf 'gcs_server|raylet'` finds nothing.

### The suites (`out/01-suites.txt`)

Serially, in the foreground, no Ray cluster up. No `slow` block: no path that selects it changed.

| Run | When | Result | Time | `uptime` load (1/5/15), before → after |
|---|---|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | before (`0f190c8`) | **732: 731 passed, 1 skipped** (136 deselected) | 32.36 s | 7.22 / 10.83 / 10.08 → 8.06 / 10.52 / 10.00 |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | before | **67: 66 passed, 1 skipped** (801 deselected) | 46.55 s | → 26.74 / 15.07 / 11.70 |
| default | after (the pin and the edits) | **732: 731 passed, 1 skipped** | 41.67 s | 15.97 / 12.23 / 11.22 → 44.97 / 20.70 / 14.41 |
| integration | after | **67: 66 passed, 1 skipped** | 51.35 s | → 51.26 / 26.66 / 17.05 |

README §0.4's counts, before and after. `git diff --name-only 3d6328e -- '*.py'` is empty.

## The deliberate-breakage record (`out/01-breakage.txt`)

Each applied to the script, checked, and reverted (`cmp` with the clean script: identical). The
diffs in `out/01-breakage.txt` apply with `git apply` from a clean tree at `6c60b81`.

| | Breakage | Check | Caught by |
|---|---|---|---|
| B1 | `cmd_stop`'s owner check removed | S-4's `stop`, ChamPBH holding a fresh scratch lock | `stop_cluster`'s two lines printed before the module's `release: the lock is not the caller's …`, exit 1: S-4's "no line of `stop_cluster`'s" fails. With SI's cluster up it would have been stopped under ChamPBH's lock |
| B2 | `cmd_stop`'s `release` given `--project StochasticInstanton` | S-3's `stop`, SI holding a fresh scratch lock | exit 1, `release: the lock is not the caller's (project is 'StochasticInstantons', not 'StochasticInstanton')`; the lock left held. Released by hand with SI's values (0) |
| B3 | `cmd_stop` spells `d="$HOME/.raypoolkit/rehearsal-lock"` | acceptance 3's grep | a second line, `:332`, a line of code |
| B4 | the usage text names `~/ScienceData/.rehearsal-lock` again | acceptance 2's grep | 1 line (`:54`) where the clean tree gives 0 |

## Observations not acted on

- **The machine's load** rose to about 51 during the integration run after the change, from about
  16 before it, with nothing of SI's running beside it. The counts were unaffected.
- **pip re-resolves `datastorekit`'s VCS line** on every `install -r` (it clones the tag to read its
  metadata) and installs nothing for it. It was so at `dk-and-rpk-migration` 03.
- **`.documents/INFRASTRUCTURE.md:46`** still says the section "points at those two documents"; the
  lock's contract is now a third. The prompt changes one bullet there, and the sentence is left.
- **`CLAUDE.md`'s pointer to the brief** (`:24`) is for `ray stop`, which is the brief's §3, and stays
  true, as the checklist's item 7 says.
- **A lock left held is the protection working** (README §7). After a failed start, `stop` or
  `status` is the next step; the usage text and `release_after_failure`'s message say so.

## State handed on

- **SI is on the package's lock.** `ray_cluster.sh start`, `stop` and `status` keep their names and
  arguments. The lock is `~/.raypoolkit/rehearsal-lock`; a held lock, or the old location present,
  is exit 3, and means stop and ask. No `PURPOSE` and no command that runs the script may name
  `/tmp/ray-si`. README §0.2's by-hand check before a start is no longer needed: `acquire` makes it.
- **The venv holds `raypoolkit` 0.3.0** at `67a75b9`, from `3d6328e`. `rrk-adoption`'s branch still
  pins `v0.2.0`; README §4's merges, at the user's instruction, bring it the new pin before that
  campaign's 02.
- **No issue opened**; `.documents/OPEN-ISSUES.md` is unchanged.
- **The switch-over cross-check** (`switch-over.md` §3) is owed once ChamPBH has switched (C9).

## Draft: SI's part of RayPoolKit's `rehearsal-lock` G2 record

For the user to record in RayPoolKit (C9); nothing here is committed there.

> **StochasticInstantons (SI) — switched on 2026-10-25.** Branch `rpk-v030-adoption`, the pin at
> `3d6328e1694a6878e69d2d8437502bf41c402b4a` and the switch at
> `6c60b81190416570b0ebf7d02d012749b4500041` (SI's `rpk-v030-adoption` prompt 01), both on top of
> `0f190c8`, not yet merged into SI's `main`.
> `requirements.txt` pins `raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.3.0`; SI's venv
> holds `raypoolkit` 0.3.0 at `67a75b9` (`67a75b97a656accb98195a4bda93f64e6a5f3fb2`), not editable,
> with `ray` 2.55.1, and nothing else in it moved.
>
> The checklist (`docs/adoption/rehearsal-lock/stochasticinstantons.md`), item 8, as it held:
> 1. the pin reads `v0.3.0`, and the venv is installed from it;
> 2. the grep for the old lock finds **5 → 0** live lines (`ray_cluster.sh:19`, `:45`, `:75`, `:76`,
>    `:77` at `6c8eada`; none after);
> 3. `ray_cluster.sh` calls the module (`git grep -c 'raypoolkit\.rehearsal_lock'` 0 → 7): `start`
>    runs `acquire`, `set-pid` with the `gcs_server`'s pid, and `release` on every failure path;
>    `stop` reads the owner file at `default_lock_dir()` before `stop_cluster`, then `release`;
>    `status` runs the module's `status`, then the script's own listing and the ports. The script's
>    stale-cluster check is dropped (item 3.1's advice); the location is never spelled in it;
> 4. SI's suites are unchanged: 732 (731 passed, 1 skipped) and `integration` 67 (66 passed, 1
>    skipped), before and after.
>
> Under the real lock, one start and stop of SI's cluster (`/tmp/ray-si`, `127.0.0.1:6390`), no
> build: the module's `status` free (0); `start` 0, the `gcs_server`'s pid 17315 recorded by
> `set-pid`; `status` held, `owner pid 17315: alive`, 18 processes by the module's rule and the
> same 18 by the script's; `ray-processes` 1, the same 18; a driver connected (`CPU` 4.0); a second
> `start` 3; `release` by hand 1 (`the recorded pid 17315 is alive`); `stop` 0, `released the
> rehearsal lock`; then `status` free, no process by either rule, the four ports free, and
> `ray-processes` 0. Against a scratch `HOME`, every path of the script that starts no Ray gave the
> planned exits, the old location's refusal (3) among them.
>
> Still owed: the cross-check of `switch-over.md` §3. ChamPBH has switched (its `95ad91d`), so
> all three clients are on the package's lock and the cross-check can run.

*The draft's last line was corrected by the orchestrator on 2026-10-25, after the review: 01 wrote
it before ChamPBH's switch was known here.*
