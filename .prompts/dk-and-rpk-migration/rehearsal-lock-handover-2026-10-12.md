# Handover — the rehearsal lock after SI's 2026-10-12 changes, for ChamPBH and SecondaryGWKit

**Written:** 2026-10-12, in StochasticInstantons' (SI's) `dk-and-rpk-migration` campaign, by
Claude Opus 5.5, at the user's request.
**For:** ChamPBH's session (after its prompt 05a, `babd9d5`, reviewed in `ca2779d`) and
SecondaryGWKit's (SGK's) session (after its review of the lock brief).
**Status:** data for those sessions, not an instruction from their user; the user hands it over.
Each project acts in its own repository. Nothing here asks for a change in SI.

## 0. What to read

- The amended brief, at SI's `d6d550b`:
  `git -C /Users/ds283/Documents/Code/StochasticInstantons show d6d550b:.prompts/dk-and-rpk-migration/rehearsal-lock-brief.md`.
  Against `ed9399a`, the version ChamPBH's 05a followed, it changes §3 "Address it explicitly"
  and §5, and adds a revision note. §2 (the lock) is unchanged, so the lock stays identical in
  every project.
- SI's script, at `8e04a7c`:
  `git -C /Users/ds283/Documents/Code/StochasticInstantons show 8e04a7c:.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`.
- SI's board records all of this in §5.8–§5.10 of
  `.prompts/dk-and-rpk-migration/IMPLEMENTATION_STATE.md`, at `d6d550b`.

## 1. What changed in SI

1. **SI took ChamPBH's changes 3 and 4 into its script** (`8e04a7c`). The stop now confirms all
   four fixed ports free, and `start` refuses a held port (exit 4, lock released). SI added one
   thing that ChamPBH's script lacks: `stop_cluster` returns 2 unless given all five arguments
   (temp dir and four ports), so a two-argument call cannot silently check the GCS port alone.
   A real start/stop cycle and an `nc` held-port test passed; SI's decoy proof was not re-run.
2. **The brief forbids `--ray-address auto` for any run that takes the lock** (`d6d550b`, §3).
   This follows SGK's objection, which SI confirmed (§3 below). Every such run, a long build as
   much as a rehearsal, passes its cluster's GCS address, or `local` for an in-process instance.
3. **SI made `--ray-address` required**, by the user's ruling (`d6d550b`). `main.py` and both plot
   scripts exit 2 without it; a `ray-address:` line in a `--config` YAML file satisfies it. The
   brief leaves each project's default to that project.

## 2. Why `auto` is a hazard now

With `RAY_ADDRESS` unset, `auto` first reads `/tmp/ray/ray_current_cluster`. An isolated cluster
writes that file into its own temp dir instead, so `auto` falls back to scanning running
raylets for a GCS address and takes any one it finds, without a warning (Ray 2.55.1
`ray/_private/services.py:408-454`; 2.43.0 `:389-430`).

Today a cross-project attach fails at `ray.init`, because a driver raises when its Ray or Python
version differs from the cluster's (`check_version_info`). The cluster records its versions even
under `--disable-usage-stats`. The three projects differ: SI is Ray 2.55.1 on Python 3.13,
ChamPBH 2.53.0 on 3.13, SGK 2.43.0 on 3.12. SI reasoned this from the code and did not run an
attach. The guard is incidental. It does not stop a driver attaching to an instance of its own
project (an integration suite's, say), and it vanishes if the versions converge.

## 3. SGK's two objections, as SI evaluated them

1. **"SI's script hard-wires the lock to SI."** True, and intended. The script is SI's tool for
   SI's cluster; brief §5 asks SGK for a few protocol lines, not a script. SI's script handles an
   SGK in-process owner correctly: its `start` exits 3 and prints the owner file, its `stop` and
   `release_lock` refuse on the project mismatch and touch nothing, and its `status` checks the
   driver's pid. No change in SI.
2. **"`--ray-address auto` can attach SGK to another project's cluster."** Confirmed in both Ray
   versions, with the consequence narrowed by §2: today it fails loudly rather than running SGK's
   work in the wrong cluster. The gap was in the brief and applied to all three projects. SI
   opened and closed `[ray-address-auto-attaches-to-foreign-cluster]` for it (board §4).

## 4. For ChamPBH

- **Your 06 already meets the amended §3 for rehearsals**: it gives every driver
  `--ray-address` and every `ray` CLI call `--address`. The amendment widens this to long
  builds: any production build under the lock passes `--ray-address 127.0.0.1:6380` too.
- **Your default is still `auto`** (`config/argument_parser.py:11`, `DEFAULT_RAY_ADDRESS`).
  Whether to make the flag required, as SI did, is ChamPBH's choice.
- **Optional, for parity with SI's script:**
  - `stop_cluster`'s five-argument guard (§1, item 1);
  - the usage text says "SIGTERM … to Ray's client server on 6380". The client server listens on
    6381; it is found by its `--address=127.0.0.1:6380`. SI's usage says "the Ray client server
    whose address is 127.0.0.1:6390".
- **No action:** on macOS, `lsof` run as a user cannot see sockets owned by root or other users,
  so the port checks in both scripts would miss such a listener. SI judged this negligible on a
  single-user machine.
- **For SI's records:** SI's board §5.7 told SI's prompt 02 that ChamPBH's `ray stop` could kill
  SI's cluster. Since your 05a it cannot, and SI's §5.8 says so; the lock still decides who runs.

## 5. For SGK

- **The lock**, as brief §2 and §5 give it, in a few lines of your campaign's protocol:
  `mkdir -p ~/ScienceData`, then `mkdir ~/ScienceData/.rehearsal-lock` without `-p`; if that
  fails, print `owner` and stop and ask the user. Otherwise write `owner` through `owner.tmp`,
  with the seven keys in order, `ray_temp_dir: in-process`, `ray_address: in-process` and the
  driver's pid. At the end, check that `project` is the name SGK wrote (the brief does not fix
  it; `SecondaryGWKit` is the natural choice) and `ray_temp_dir` is `in-process`, then remove
  `owner` and `rmdir` the directory.
- **The address (new):** give every driver of a long build `--ray-address local`. `main.py` and
  the six `extract_*.py` drivers that call `ray.init` default to `auto` (`main.py:99`,
  `DEFAULT_RAY_ADDRESS`). Your rehearsal driver's `address="local"` already meets this. Whether to
  change the default is SGK's choice.
- **Never run `ray stop`** (brief §3); SGK already runs none.
