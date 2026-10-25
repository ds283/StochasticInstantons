# The run registry: rules for long-running jobs

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`, whose section "Long-running jobs — the run registry" summarises it. It applies
whenever a job that may outlive a conversation is launched, watched or ended, and whenever
`var/` is touched.

RunRegistryKit's `README.md` at `v0.2.0`, "The rules", tells each rule below with the failure it
answers; its section "Ending a run whose end was never recorded" tells the route after a hard
kill. `runregistrykit.toml` sets `runs_root = "var/runs"` and
`stores_root = "var/datastores"`. Production runs are the user's: no campaign prompt starts one
except a rehearsal its plan names.

## The six rules

1. **Discovery.** `./venv/bin/python -m runregistrykit list` at the start of a session and before
   launching anything long; report anything `running`, stale or unknown. A job's existence must not
   depend on a conversation remembering it.
2. **Liveness.** A run is alive iff its pid answers `kill -0` **and** its heartbeat is inside the
   staleness window, judged on the host and boot the run recorded. Never a command-line match such
   as `pgrep -f`, which also matches the shells waiting on the job (nineteen poll loops that could
   never exit).
3. **Launch.** Detached (`nohup`, `disown`; `setsid` is not on macOS), manifest written first,
   stdout and stderr in the run directory, pid recorded.
4. **Do not babysit.** Launch, verify in one check that it started, and end the turn. Resume once,
   when it is done.
5. **Durability.** Records in `var/runs/` and stores in `var/datastores/`, under the repository
   root. Never a session scratchpad, never `/tmp`.
6. **Provenance.** Script hash and git commit are taken at launch. A record that does not match
   is discarded and recomputed, never blended, never re-stamped.

## The route after a hard kill

A run killed by `SIGKILL`, a power loss or the OOM killer never records its end.

1. `list` shows it `stale`, `!!`, and a build's `begin` on its store is refused with nothing created.
2. A person checks that the run is over, then runs
   `./venv/bin/python -m runregistrykit end RUN_ID --reason TEXT` on the host it ran on. The run is
   recorded `lost`.
3. The build is run again. It prunes unvalidated rows at open (`--prune-unvalidated` defaults to
   on), so a resume needs no flag.

A run stopped by `SIGTERM` needs no `end`: the wrapper records it `killed`. `Run.finish` is never
called by hand on a run that is not the caller's; it checks nothing.

## What `stale` means for SI

A queue that prints nothing for longer than the staleness window (900 s) while it works is shown
stale. The gradient-coupled branch is such a queue: its solves have run for hours. Stale means go
and look (`list --stale-after` widens the window for the reader), never kill.

## The sidecar

A store's sidecar, `<stem>.manifest.json`, is created by a person, after the store's first close:
`./venv/bin/python -m runregistrykit store create PRIMARY --purpose TEXT`. Nothing in the code
creates one.

## What is forbidden

- Polling a run in a loop.
- `pgrep -f` (or any command-line match) as a liveness test.
- `ray stop` (see `CLAUDE.md`).
- `git clean -x` or `-X`: `var/` is ignored, and they delete the stores in it.
- A store of a registered run outside `var/datastores/`.
- Deleting a run directory or a sidecar.
