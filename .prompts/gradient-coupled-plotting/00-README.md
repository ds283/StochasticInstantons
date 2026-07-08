# Implementation prompts for the GCI plotting work — build plan

This directory contains the implementation prompts authored from
`DESIGN_gradient_coupled_plotting.md` per `PROMPT_AUTHORING_BRIEF.md`. Each
`NN-<TRACK>-<slug>.md` file is a self-contained handoff to a coding model,
using the brief's §2 template verbatim.

## Two corrections to the design, made before authoring

The brief instructs surfacing open questions, not resolving them — but these
are not open questions, they are places where the design's stated premise
does not match the current source. Propagating them as written would have
the coding model build on top of a false "current state," so they are
corrected here rather than passed through. Both are grounded in direct
reads of the real files (not the design doc's summary of them).

**1. `build_pipeline_inputs` already mints the α/n_colloc arrays.**
Design §7.4 says *"`build_pipeline_inputs` mints only
`N_init`/`N_final`/`delta_Nstar`. Add minted arrays for
`alpha_regularization` and `n_collocation_points`."* This is false today:
`config/pipeline_setup.py::build_pipeline_inputs` already registers and
returns `n_collocation_points_array` and `alpha_regularization_array`,
built from the existing `--n-collocation-points`/`--alpha-regularization`
CLI flags (`config/argument_parser.py`), which are already crossed against
the instanton grid by `main.py`. There is nothing to mint.

What *is* missing is a `low/high/samples` convenience grid-generator for
these two flags, mirroring `delta_Nstar`'s quartet — but adding one would be
actively harmful for the plotting driver specifically: unlike
`N_init`/`N_final`/`delta_Nstar` (which the plot driver reconstructs by
parsing the *same* `--config` YAML that `main.py` used, guaranteeing the
swept grid matches what was actually computed and persisted), a
plot-driver-only `--alpha-low/high/samples` grid could trivially diverge
from whatever explicit `--alpha-regularization` values `main.py` actually
computed, silently returning "not found" for most fetches. The safe,
zero-drift choice is for the plotting driver to consume
`inputs["n_collocation_points_array"]`/`inputs["alpha_regularization_array"]`
directly (exactly as it already does for `N_init_array`/`N_final_array`/
`dns_array`) rather than inventing a second, independent way to specify
these axes. **P6 and P8 below are written against this corrected
understanding** — no new `build_gci_inputs` function, no new
low/high/samples/values CLI quartet for α/n_colloc. If a genuine
convenience grid-generator for `--alpha-regularization` is wanted later,
that is a small, separate change to the *shared* parser (touching
`main.py`'s own inputs, deliberately out of scope here) and not part of
this plotting build.

**2. `_provenance_footer` reads `.atol`/`.rtol` as flat attributes, not a
`.tolerances` tuple.** Design §3.2 gives the adapter a single
`tolerances -> tuple` property. `plot_InstantonSolutions.py::_provenance_footer`
(the function this design explicitly keeps "essentially unchanged") calls
`getattr(obj, "atol", None)` / `getattr(obj, "rtol", None)` as two separate
scalar attributes and silently omits them if absent (no exception — just a
quietly thinner footer). Passing an adapter that only exposes `.tolerances`
would not crash anything, but every adapter-driven figure's provenance
footer would silently lose its tolerance annotation — a regression a golden
diff on *content* would catch (byte-identical check), but a hand-run smoke
test might not, since nothing errors. **P2 below adds flat `atol`/`rtol`
convenience properties to `InstantonAdapter` alongside `tolerances`**,
specifically so `_provenance_footer` keeps working unchanged when called
with an adapter instead of a raw compute-target object.

Everything else below follows the design and brief as written.

## Dependency graph

```
Track U (upstream science parity)          Track P (plotting)
  U1 ─────┐                                  P1 ──► P2 ──► P3
           ├──► U2a ──► U2b ──► U3 ──────────────────────────┤
                                                              ▼
                                                             P4 ──► P5a ──► P5b
                                                              │
                                                              ├──► P6
                                                              ├──► P7
                                                              └──► P8 (needs P4, P6/P7 not required)
```

- U1 → U2a → U2b → U3 is a strict chain (each edits/depends on the previous).
- P1 → P2 → P3 is a strict chain (each re-diffs against the prior prompt's
  golden run).
- **P4 depends on U3 and P3** (needs the persisted parity columns to be pure
  reads, and needs the `profile_only` fetch mode to set `fidelity`
  correctly).
- P5a/P5b, P6, P7 depend on P4 only (fan out from it).
- P8 depends on P4 at minimum; it wires in whichever of P5–P7 have landed,
  but does not strictly require all of them to exist first (a driver that
  only calls the figure families that exist so far is a legitimate
  incremental state — just don't wire a `--movies` flag before P5b lands).
- U-track and P1–P3 have no edge between them and can be authored/executed
  in parallel, exactly as the design's §11 build order says.

## File list

| # | ID  | Title | Depends on |
|---|-----|-------|------------|
| 01 | U1  | Factor shared compaction scalars | none |
| 02 | U2a | `C_bar` in the onion profile + densified classification | U1 |
| 03 | U2b | Parity scalar set inside the GCI worker | U1, U2a |
| 04 | U3  | Persist + rehydrate the parity columns | U2a, U2b |
| 05 | P1  | Extract plotting machinery, no behaviour change | none |
| 06 | P2  | Introduce the adapter, convert figures | P1 |
| 07 | P3  | `profile_only` fetch mode + method contract | P1 |
| 08 | P4  | Gradient adapter (`GradientCoupledAdapter`/`SpatialAdapter`) | U3, P2, P3 |
| 09 | P5a | Spatial figures — heatmaps + slices (static, default) | P4 |
| 10 | P5b | Spatial figures — movies (opt-in `--movies`) | P4, P5a |
| 11 | P6  | Stability/convergence figures (α / n_colloc overlays) | P4 |
| 12 | P7  | Diagnostics figures | P4 |
| 13 | P8  | New driver + compare mode | P4 (P5–P7 wired in as available) |

## Self-check (per brief §6, re-run per prompt before handoff)

- [ ] Uses the template with every field filled
- [ ] Real repo paths, not flat names
- [ ] Cites the design section(s) it implements
- [ ] *Depends on* is correct; P4→U3 honoured
- [ ] Acceptance test is verifiable without judgment
- [ ] *Must NOT* fences the right scope
- [ ] Doesn't reopen a §3 settled decision
- [ ] Any relevant open question appears as a *Decision point* with a default
- [ ] High-risk items (§5) are fenced where touched
