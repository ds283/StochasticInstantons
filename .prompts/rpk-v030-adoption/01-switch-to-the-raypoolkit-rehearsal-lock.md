# Prompt 01 — switch to the `raypoolkit` rehearsal lock (`v0.3.0`)

**Campaign:** [`README.md`](README.md) · **Board items:** **P1**, **S1**–**S4**, **D1**, **V1**,
**V2**, **G1** · **Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-25, with the plan. Measured at `7071bb8`, whose `ray_cluster.sh` is `main`'s;
your own measurement governs.
**Where it runs:** on the laptop, in the main checkout, on the branch `rpk-v030-adoption`.
**Gate:**
- on `rpk-v030-adoption`, at the planning commit, with `git status --porcelain` empty;
- `./venv/bin/python -m runregistrykit list` shows nothing `running` or stale;
- the venv holds `raypoolkit` 0.2.0 at `eaef0ce60e2fc354bb32f0ad576010e6a83c1976` and `datastorekit`
  0.5.0 at `f47b9a255e9ad58e0d0eaf85644f53b575884d31`, neither editable. It also holds
  `runregistrykit` 0.2.0, installed by `rrk-adoption` 01 and not in this branch's
  `requirements.txt`: expected, and left alone;
- **neither** `~/ScienceData/.rehearsal-lock` **nor** `~/.raypoolkit/rehearsal-lock` exists;
- `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`: the lock free, no SI process,
  the four ports free.

If any of these fails, stop and ask. A lock at either location is another project's or a stale
one: never remove it.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Opus**.

**Read first:**

1. [`README.md`](README.md) whole: §0.2 (why soon), §2.1 (this charter), §4, §5 and §6.2 (C2–C9).
2. **RayPoolKit** (`/Users/ds283/Documents/Code/RayPoolKit`; read, never edit):
   - at the tag, with `git -C <RPK> show v0.3.0:<path>`: `docs/rehearsal-lock.md`, the contract,
     whole (it is the interface you call: §4 the owner file, §5 whose lock, §6 the process rule and
     **"What it asks of a caller"**, §7 the commands and their exit codes, §8 `status`'s layout, §9
     the old location);
   - at `main`: `docs/adoption/rehearsal-lock/stochasticinstantons.md`, the checklist for this
     repository, whole. It was measured at `7071bb8` against blob `6c8eada` of the script, which is
     this branch's. It is data: where it and this prompt differ, this prompt governs, and where the
     tree differs from it, the tree does.
3. `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`, whole, and
   `.prompts/dk-and-rpk-migration/rehearsal-lock-brief.md` §3 (the cluster), which still governs
   its cluster half.
4. `CLAUDE.md`, "Build and test" and "Protected infrastructure"; `.documents/INFRASTRUCTURE.md`
   `:26-45`.

---

## 1. What is wanted

**Make SI's script take the package's lock, and show with SI's real cluster that it does.** The pin
moves in a commit of its own (C6); the script, the two documents, the results note and the board
follow in a second.

**Each lock command is a shell command of its own** (contract §6, "What it asks of a caller"). A
shell whose command line names `/tmp/ray-si` seeds the process rule, and everything it started is
listed. So:
- never chain a lock command or `ray_cluster.sh` with anything else in one shell command;
- never name `/tmp/ray-si` in a `PURPOSE`;
- the script passes the values to the module from its own variables, never from its command line.

## 2. What to do

Save every command and its output under `.documents/rpk-v030-adoption/out/`, each block headed by
its command: the install into `01-pip.txt`, the suites into `01-suites.txt`, the scratch checks into
`01-scratch.txt`, the live check into `01-live.txt`, the breakages into `01-breakage.txt`. Small
text only.

**2.1 The baselines, before.** `./venv/bin/pip freeze`; then `pytest -m "not integration and not
slow"` and `RAY_ADDRESS=local pytest -m integration`, serially, in the foreground, with the load
(`uptime`). README §0.4's counts: 732 (731 passed, 1 skipped) and 67 (66 passed, 1 skipped).

**2.2 The pin (P1).** `requirements.txt:59` changes from

```text
raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0
```

to the same line with `@v0.3.0`. No other line moves. Then:
- `./venv/bin/pip install --dry-run -r requirements.txt`: it would install `raypoolkit-0.3.0` and
  nothing else;
- `./venv/bin/pip install -r requirements.txt`. **Never editable**;
- `pip freeze` again, differing from 2.1's by the one `raypoolkit` line, now naming
  `67a75b97a656accb98195a4bda93f64e6a5f3fb2`; `pip check`;
- `./venv/bin/python -m raypoolkit.rehearsal_lock --help`: its first line starts
  `usage: python -m raypoolkit.rehearsal_lock`.

**Commit the pin alone** (C6): `requirements.txt` only, staged by path, after showing
`git diff --cached --name-only`. The script still takes the old lock at this commit, and that is a
consistent tree: the pin changes nothing SI runs (README §0.1).

**2.3 The script (S1–S4).** Edit `ray_cluster.sh` in place (C2), as the checklist's items 2, 3 and 5
say, with its advice taken (C3–C5). Keep the file's voice, its `say`/`err` prefixes and its
comment density. Call the module as `./venv/bin/python -m raypoolkit.rehearsal_lock`, through one
small function or variable of the script's, with `--project "$LOCK_PROJECT"`, `--ray-temp-dir
"$SI_TEMP_DIR"` and, where the command takes one, `--ray-address "$SI_ADDRESS"`. Spell the address
`127.0.0.1:6390` (`SI_ADDRESS`, as now): the module looks for that spelling on the client server
(the checklist, item 3).
- **S1 — what goes.** `LOCK_PARENT`, `LOCK_DIR`, `OWNER_FILE` and their comment (`:75-78`);
  `iso_now`, `write_owner`, `acquire_lock` and `release_lock` (`:85-88`, `:96-107`, `:117-147`).
  `owner_field` and `print_owner` stay only in the form C4 needs. `LOCK_PROJECT`, the cluster's
  values, `say`, `err`, `temp_dir_regex`, `list_cluster_pids`, `describe_pid`, `port_listeners`,
  `alive`, `stop_cluster` and `main` stay unchanged. The script may still be sourced for
  `stop_cluster` (its header, `:27-28`).
- **S2 — `cmd_start`.**
  - `acquire` (with the `PURPOSE`) in place of `acquire_lock`, its exit passed through
    (`|| return $?`): 0 go on; 3 held, or the old location exists; 4 a process of the cluster is
    alive, or `ps` cannot be read, the lock released again; 1 the owner file not written; 2 a usage
    error.
  - **The stale-cluster check (`:280-286`) goes** (C3).
  - The held-port check stays, with `release` for `release_lock`, then `return 4`.
  - After `ray start` and the `gcs_server` found, **`set-pid` with its pid** in place of
    `write_owner`. If `set-pid` refuses, treat it as the no-`gcs_server` path: `stop_cluster`,
    `release`, clear the trap, `return 1`.
  - Every path that releases today calls `release` instead: the held port, `ray start` failed, no
    `gcs_server`, and the trap. On the failure paths the script returns 1 (the trap exits 130)
    whatever `release` returned, and **`release`'s refusal is not hidden**: it is what leaves the
    lock held when something of the cluster is still alive (the checklist's table in item 3.1).
- **S3 — `cmd_stop`.** First, the owner check (C4): ask the pinned package for the location,
  `./venv/bin/python -c 'from raypoolkit.rehearsal_lock import default_lock_dir;
  print(default_lock_dir())'`, and if a lock is there whose owner file's `project` or `ray_temp_dir`
  is not SI's (a missing owner file counts as not SI's), print its owner file and return 1 **before
  `stop_cluster`**, touching nothing, as today. The script never spells the location itself. Then
  `stop_cluster` (unchanged) and `release`.
- **S4 — `cmd_status`, the header and the usage.**
  - `cmd_status`: the module's `status --ray-temp-dir … --ray-address …` in place of the lock's
    lines (`:357-368`); then the script's own listing under a heading that says it is what `stop`
    signals (C5); then the four ports. Exit 0, as now.
  - **The header** (`:17-28`): SI's cluster, and the shared lock taken through
    `raypoolkit.rehearsal_lock`, whose contract is RayPoolKit's `docs/rehearsal-lock.md` at the
    pinned tag; the brief's §3 governs the cluster. Name this campaign as the change, as the header
    names `dk-and-rpk-migration` 01a.
  - **The usage** (`:45-58`): `start` takes the lock through the module at
    `~/.raypoolkit/rehearsal-lock`; exit 3 if it is held **or the old location exists**; exit 4 if a
    port is held or a process of the cluster is alive, the lock released again; a failed start
    stops what it started and releases the lock, **which stays held if anything of the cluster is
    still alive**. `stop`: unchanged in substance. `status`: the lock and the processes by the
    module's rule, then the script's listing and the ports.
  - Keep `:64`'s pointer to the brief's §3; the brief's §2 is not cited anywhere live.

`bash -n` the script. Nothing in it may name `ScienceData` or `.raypoolkit` (C4).

**2.4 The documents (D1).**
- **`CLAUDE.md:126-127`**: "`raypoolkit` `v0.2.0`" becomes "`raypoolkit` `v0.3.0`". Nothing else in
  that paragraph changes.
- **`CLAUDE.md:14-20`**: one sentence added after "under the shared rehearsal lock: …": the lock is
  the pinned package's `raypoolkit.rehearsal_lock` (`~/.raypoolkit/rehearsal-lock`, shared with
  ChamPBH and SecondaryGWKit; its contract is RayPoolKit's `docs/rehearsal-lock.md`), and a held
  lock, exit 3, means stop and ask, never wait. Rewrap the paragraph to its current width. The
  sentence on `ray stop` and its citation of the brief stay.
- **`.documents/INFRASTRUCTURE.md:41-42`**: "`raypoolkit` `v0.3.0` (RayPoolKit): `RayWorkPool`, and
  the shared rehearsal lock `raypoolkit.rehearsal_lock`", with how each is called: its `README.md`
  at the tag, "Using it" and "The rehearsal lock", and the lock's contract `docs/rehearsal-lock.md`.
  Rewrap to the file's width.
- Nothing else: the citations "at `v0.2.0`" stay (C8), and no record changes (README §1).

**2.5 The scratch checks (V1).** Against a scratch `HOME`, every path of the script that starts no
Ray (C7). The real lock is never touched. Make the directory with `mktemp -d` under the session's
scratch space, never a path that names `/tmp/ray-si`, and run each command from the repository
root as `HOME=<scratch> .documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh …`, or
`HOME=<scratch> ./venv/bin/python -m raypoolkit.rehearsal_lock …` for a by-hand step. Run them
**only while the real `status` shows no SI process**: `stop` signals real processes of `/tmp/ray-si`
whatever `HOME` is.

| # | Set-up (in the scratch `HOME`) | Command | Expected |
|---|---|---|---|
| S-1 | nothing | `status` | exit 0; `lock: free (<scratch>/.raypoolkit/rehearsal-lock does not exist)`; no `old location` line; no process by either rule; the four ports free |
| S-2 | nothing | `stop` | exit 0; `stop_cluster`'s "no process names /tmp/ray-si; ports … are free"; `no lock to release (…)` |
| S-3 | `acquire` by hand with SI's values, `--purpose "rpk-v030-adoption 01 S-3"` (exit 0) | `stop` | exit 0; `released the rehearsal lock (…)`; then `status` free |
| S-4 | `acquire` by hand as ChamPBH: `--project ChamPBH --ray-temp-dir /tmp/ray-cpbh --ray-address 127.0.0.1:6380`, `--purpose "rpk-v030-adoption 01 S-4"` | `stop`, then `start "rpk-v030-adoption 01 S-4"` | `stop`: exit 1, ChamPBH's owner file printed, **no line of `stop_cluster`'s**; `start`: exit 3, the owner file printed, nothing started. Then `release` by hand as ChamPBH: exit 0 |
| S-5 | the old location: `<scratch>/ScienceData/.rehearsal-lock/` with an `owner` file of the seven keys, `purpose: rpk-v030-adoption 01 S-5` | `start "rpk-v030-adoption 01 S-5"`, then `status` | `start`: exit 3, naming the old location, and `<scratch>/.raypoolkit/rehearsal-lock` not created; `status`: `old location: PRESENT (…)`. Then remove the scratch old location |
| S-6 | a listener on `127.0.0.1:6391`, SI's client port: `./venv/bin/python -c` binding a socket, listening on it and sleeping, started in the background, its pid kept | `start "rpk-v030-adoption 01 S-6"`, then `status` | `start`: exit 4, port 6391 held, the lock released (`release` with `pid: -`); `status` free. Then kill the listener by its pid |

If S-4's by-hand `acquire` exits 4, ChamPBH's cluster is running: record it, skip S-4, and go on.
**If any `start` here prints anything of `ray start`'s**, run `HOME=<scratch> … stop` at once, then
stop and ask (§4). Remove the scratch directory at the end.

**2.6 The live check (V2).** Under the real lock, with the real `HOME`: one start and stop of SI's
cluster, no build.
1. `./venv/bin/python -m raypoolkit.rehearsal_lock status`: exit 0, `lock: free (…)`, no `old
   location` line. If the lock is held (SGK may be running), **stop and ask**; never wait.
2. `ray_cluster.sh start "rpk-v030-adoption 01 (live check)"`: exit 0; the address, and the
   `gcs_server`'s pid.
3. `ray_cluster.sh status`: `lock: HELD (~/.raypoolkit/rehearsal-lock)`, the owner file with
   `project: StochasticInstantons`, `ray_temp_dir: /tmp/ray-si`, `ray_address: 127.0.0.1:6390` and
   `pid:` the `gcs_server`'s; `owner pid <pid>: alive`; the module's listing with the `gcs_server`,
   the `raylet` and the client server among its lines; the script's listing; the ports held.
4. `./venv/bin/python -m raypoolkit.rehearsal_lock ray-processes --ray-temp-dir /tmp/ray-si
   --ray-address 127.0.0.1:6390`: **exit 1**, the same processes as the module's listing in 3.
5. A driver connects: `./venv/bin/python -c 'import ray; ray.init(address="127.0.0.1:6390");
   print(ray.cluster_resources()); ray.shutdown()'`: `CPU` 4.0, exit 0.
6. A second `ray_cluster.sh start "rpk-v030-adoption 01 (second start)"`: **exit 3**, the owner file
   printed; then `status` unchanged from 3.
7. `./venv/bin/python -m raypoolkit.rehearsal_lock release --project StochasticInstantons
   --ray-temp-dir /tmp/ray-si`: **exit 1**, the recorded pid alive; the lock still held.
8. `ray_cluster.sh stop`: exit 0; `released the rehearsal lock (…)`.
9. `ray_cluster.sh status`: `lock: free (…)`; no process by either rule; the four ports free. Then
   step 4's command again: exit 0.

**2.7 The deliberate breakages.** Apply each to the script, run the named check again against a
fresh scratch `HOME`, record which expectation failed and the diff exactly as applied, and revert.
None reaches `ray start`.
- **B1** — `cmd_stop`'s owner check removed: S-4's `stop` now runs `stop_cluster` before refusing.
- **B2** — `cmd_stop`'s `release` given `--project StochasticInstanton`: S-3's `stop` exits 1 and
  leaves the lock held (release it by hand with SI's values).
- **B3** — `cmd_stop` spells the location as `"$HOME/.raypoolkit/rehearsal-lock"` in place of asking
  the package: §3 item 3's grep finds it.
- **B4** — the usage text's `start` line names `~/ScienceData/.rehearsal-lock` again: §3 item 2's
  grep finds one line.

**2.8 The suites, after.** Both again, as in 2.1: the same counts. No `.py` file has changed:
`git diff --name-only <the pin commit> -- '*.py'` is empty.

## 3. Acceptance

1. **The pin.** The dry run adds only `raypoolkit`; after it, `raypoolkit` 0.3.0 at `67a75b97…`, not
   editable; nothing else in the freeze moves; `pip check` clean. The pin is a commit of its own.
2. **No live line names the old lock** (the checklist, item 8.2), on the working tree:

   ```bash
   P='ScienceData|\.rehearsal-lock|rehearsal-lock-brief\.md, section 2|section 2 \(the lock\)'
   { git grep -n -E "$P" -- . ':!.documents' ':!.prompts' ':!prompts' ':!science-runs'
     git grep -n -E "$P" -- .documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh; } | wc -l
   ```

   5 before, **0** after.
3. **The script calls the module and never spells the location**:
   `git grep -c 'raypoolkit\.rehearsal_lock' -- .documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`
   is at least 1, and `git grep -n -E 'raypoolkit/rehearsal-lock|\.raypoolkit' -- <the script>`
   finds nothing but comments and the usage text. `bash -n` passes.
4. **The scratch checks** S-1 to S-6 as §2.5's table says, none reaching `ray start`.
5. **The live check** as §2.6 says: the lock held with the `gcs_server`'s pid while the cluster
   runs, a second start refused (3), `release` refused (1), the driver connected, and after `stop`
   the lock free and nothing of `/tmp/ray-si` left.
6. **The breakages** B1–B4 each caught as §2.7 says.
7. **The suites** at README §0.4's counts, before and after; no `.py` file changed.
8. **The second commit's** `git diff --cached --name-only` is: the script, `CLAUDE.md`,
   `.documents/INFRASTRUCTURE.md`, `.documents/rpk-v030-adoption/` (the results note and `out/`),
   this board and `.prompts/INDEX.md`. Nothing else.

## 4. Stop conditions: stop and ask

- A Gate item is not as stated.
- **Anything exists at `~/ScienceData/.rehearsal-lock`**, or `~/.raypoolkit/rehearsal-lock` is held
  by another project, at any point. Never remove either.
- The dry run would install, upgrade or remove anything but `raypoolkit`.
- An existing test fails, or a count differs from §0.4's.
- A scratch check differs from §2.5's table, or reaches `ray start`.
- In the live check: `acquire` exits 3 or 4; the module does not list the running cluster;
  `release` succeeds while it runs; `stop` leaves a process of `/tmp/ray-si` or a port held, or the
  lock held.
- Anything suggests a defect in `raypoolkit.rehearsal_lock`, or a statement of the contract that
  the module does not keep: record it on the board and in `.documents/OPEN-ISSUES.md`, and stop.
  It is reported to RayPoolKit by the user, never worked around here.

**If you stop with SI's cluster running**, run `ray_cluster.sh stop` first, unless the stop is what
failed. **If you stop with the lock held**, say so and leave it held, with its owner file printed:
the orchestrator decides. If you stop after the install, say that the venv holds `v0.3.0`.

## 5. What this prompt does not do

- **Files it changes:** `requirements.txt` (one line; the first commit);
  `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`; `CLAUDE.md` (two places);
  `.documents/INFRASTRUCTURE.md` (one bullet); the results note and `out/`; this board;
  `.prompts/INDEX.md` (this campaign's line). `.documents/OPEN-ISSUES.md` only if an issue is opened.
- It changes no Python file and no test, and nothing a build computes or stores. It opens no store.
- It touches nothing in RayPoolKit, ChamPBH or SGK, and no record of another campaign.
- It does not merge anything: the merges of README §4 are the user's to instruct, after the review.

## 6. The results note and the board

**The results note**, `.documents/rpk-v030-adoption/01-switch-to-the-raypoolkit-rehearsal-lock.md`,
in the template of `dk-and-rpk-migration` README §5.1, with every count, the breakage record, and
the scratch and live transcripts summarised (the full text in `out/`). It ends with **a draft of
SI's part of RayPoolKit's G2 record** (README C9), for the user to commit in RayPoolKit: SI's
branch and commit, the pin at `v0.3.0` (`67a75b9`), the checklist's item 8 as it held (the grep's
5 → 0, the script calling the module, the suites unchanged), and §2.6's exits. It says that the
cross-check of `switch-over.md` §3 is still owed, once ChamPBH has switched.

**The board:** the header ("01 landed, awaiting review"); the §1 row; items P1, S1–S4, D1, V1, V2
and G1; the gate **Switch**; `### 5.1 After prompt 01 (<date>)`, with the first commit's SHA in
full and "this commit" for the second. **`.prompts/INDEX.md`:** this campaign's status.

**Two commits** (C6), each in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`: the pin (§2.2), then the rest.
