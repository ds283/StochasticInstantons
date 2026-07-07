# Brief: authoring implementation prompts for the GCI plotting work

**You are** the prompt-author. Your job is to turn the build order in
`DESIGN_gradient_coupled_plotting.md` into a sequence of **implementation
prompts**, each of which will be handed to a separate coding model that edits the
real `StochasticInstanton` repository.

**You are not** implementing anything, redesigning anything, or re-deciding
anything already settled below. The architecture reasoning is done; your value is
disciplined decomposition and pinning down detail so the coding model has no room
to guess wrong.

Read first, in full: `DESIGN_gradient_coupled_plotting.md`, `FILE_MAP.md`,
`NUMERICAL_SCHEMES.md`, and the source files each prompt touches.

---

## 0. Non-negotiables for how you work

1. **One prompt = one coherent, independently-verifiable unit of change.** If a
   build-order step touches several files but lands as one testable behaviour,
   it's one prompt. If a step contains two separable behaviours with distinct
   acceptance tests (e.g. "add the columns" vs "rehydrate them"), split it. Err
   toward smaller prompts with sharper acceptance tests.
2. **Every prompt uses the template in §2. No free-form prompts.** A missing
   field (especially *Acceptance test* or *Must NOT*) is a defect.
3. **Real repo paths, not flat names.** The files you were given are flattened
   (`A_B_C.py` = `A/B/C.py`; see `FILE_MAP.md`). Every prompt must reference the
   **real** path (`ComputeTargets/GradientCoupledInstanton/picard.py`), never the
   flat name. Translate underscores→slashes yourself; do not make the coding
   model do it.
4. **Cite the design section** each prompt implements, so changes are traceable.
5. **Surface, don't resolve, the open questions.** Where design §12 marks a
   decision as open, the relevant prompt must include a *Decision point* block
   stating the question and the recommended default — it must not silently pick.
6. **Preserve the dependency graph.** Each prompt declares *Depends on*. Do not
   emit a prompt whose prerequisites haven't been authored. Honour the one hard
   cross-track edge: **P4 depends on U3.**

---

## 1. Global constraints every prompt must carry

Put these in each prompt's *Constraints* block (by reference — "follow the
codebase conventions checklist" — plus any step-specific additions). The coding
model will not know them unless you say so.

**Codebase conventions checklist (repo-wide):**

- **Ray-dispatch pattern.** Compute targets follow `@ray.remote` function →
  `FooValue` class → `Foo` plain-Python class (**never** `@ray.remote` a
  compute-target class) → `FooProxy`. See `.claude/rules/ray-dispatch.md`.
- **Factory four-method protocol:** `register()` / `build()` / `store()` /
  `validate()`. New persisted fields must be handled in `build()` (rehydrate) and
  `store()` (persist), and must not break `validate()`'s cascade.
- **Proxy pattern:** a proxy holds `store_id` + shard-routing fields only
  (`.claude/rules/proxy-pattern.md`); never serialise a full compute object
  through Ray — pass the proxy and `.get()` inside the worker.
- **Shard key is `delta_Nstar`.** All vectorized fetches bin by it; one
  `object_get_vectorized` per shard. New axes (α, n_colloc) are **not** shard
  keys.
- **`_do_not_populate=True`** is the cheap scalar+diagnostics fetch; scalars and
  the `diagnostics_json` blob live on the parent row and rehydrate in this mode.
- **`SplineWrapper` is the only sanctioned spline** (`.claude/rules/`
  `spline-interpolation.md`): `sinh` y-transform for response/large-dynamic-range
  fields, `linear` for φ/π. Never hand-roll interpolation.
- **Units** are reduced Planck (Mₚ=1, 8πG=1); dimensionful quantities divide/
  multiply by explicit unit objects (`units.Mpc`, `units.SolarMass`,
  `units.PlanckMass`).
- **Provenance on every figure** via the shared `provenance` helpers; no figure
  ships without the version/timestamp/coords footer.
- **New files carry the Apache-2.0 / University of Sussex header** copied from an
  existing source file.
- **Response/adjoint fields integrate backward** (growing-mode stability); never
  "simplify" a backward integration to forward. See `NUMERICAL_SCHEMES.md` §2.

---

## 2. The prompt template (use verbatim)

```
### Prompt <ID> — <short imperative title>

- **Implements:** design §<refs>
- **Track / step:** <U1 | U2 | U3 | P1 … P8>
- **Depends on:** <prompt IDs, or "none">
- **Files (real paths):**
  - edit: <path>
  - add:  <path>
- **Context to read first:** <source files the coding model must read before editing>
- **Assumable interfaces:** <exact signatures/behaviours it may rely on as already true>
- **Task:** <imperative, specific, scoped to this unit>
- **Constraints:** follow the conventions checklist; plus: <step-specific musts>
- **Must NOT:** <explicit scope fences — what to leave untouched>
- **Acceptance test:** <a concrete, verifiable check — command, diff, or unit test>
- **Decision point (if any):** <open question + recommended default; instruct to
  implement the default and leave a `# DESIGN-DECISION:` comment>
```

**Rules for the fields:**

- *Assumable interfaces* exists to stop the coding model re-discovering (or
  re-deriving differently) something a prior prompt already established. State
  method signatures and their contracts explicitly. Example: "You may assume
  `GradientCoupledInstanton.profile` returns a list of objects each with
  `.node_index, .zeta, .r_ratio, .C, .C_bar, .r_phys` (C_bar added in U2)."
- *Acceptance test* must be verifiable without human judgment. Prefer, in order:
  (a) "output byte-identical to a golden run of `<command>`" for refactors;
  (b) a named unit test asserting specific values/exceptions; (c) a described
  manual check with an unambiguous pass condition. "Looks correct" is never
  acceptable.
- *Must NOT* is mandatory. Refactor prompts must forbid behaviour change;
  additive prompts must fence off the files they should not touch.

---

## 3. Settled decisions — DO NOT let a prompt reopen these

If a prompt's wording invites the coding model to reconsider any of these, rewrite
it. These are fixed:

1. **New driver + shared `plotting/` package + adapter layer.** Not
   modify-in-place, not fork. (§1–§2)
2. **Figure functions consume `list[InstantonAdapter]`.** No figure branches on
   solver kind; it branches only on capability flags / which scalar keys are
   present. (§3)
3. **Science-scalar parity is upstream** — computed in the GCI compute target and
   persisted as columns, via helpers shared with `CompactionFunction`. **Never
   reconstruct M/r/C̄ in the plotting adapter.** (§7)
4. **There is no barred `M_PBH`/`r_PBH`.** `r_max/r_peak/M_max/M_peak` derive from
   the **unbarred** `C(r)`; C̄ appears only as `C_bar_peak` + the `C_bar(r)`
   profile array. (§7.1)
5. **The parity scalar set is exactly the §7.1 table** — including `C_min`,
   `compensated`, `type_II`, `V_end_downflow`, `N_end_downflow`. Not a subset.
6. **`delta_Nstar` stays the shard key.** α and n_colloc are ordinary axes.
7. **`profile_only` obeys the §4.1 three-mode × two-state table**, and the
   dense-values guard moves to "dense values requested", not "not do_not_populate".
8. **GCI time histories use the core node (y=+1)** as the homogeneous analogue.
9. **Heatmaps + slices are default; movies are opt-in** behind `--movies`.
10. **Diagnostics collection is fused into the DOE scalar pass.**
11. **α / n_colloc axes live in a new `build_gci_inputs`**, leaving `main.py`'s
    inputs untouched.

Genuinely open (must appear as *Decision point* blocks, with the recommended
default, in the noted prompt): downflow-scalar representative for GCI (U2);
densification before GCI classification (U2); profile-only guard relocation
confirmation (P3); ffmpeg/mp4 vs gif default (P5). See design §12.

---

## 4. Per-step guidance

For each step, the specifics you must bake in and the traps to fence off. Split
into multiple prompts where noted.

### Track U — upstream science-scalar parity (prerequisite for P4)

**U1 — factor shared compaction scalars.** One prompt.
- Extract from `CompactionFunction`'s worker into a new
  `ComputeTargets/compaction_scalars.py`: the C̄ running-integral, the PBH-mass
  relation (keep the constants `k*=0.05/Mpc`, `5.6e15`), the `C_min`/
  `compensated`/`type_II` classification, and route `_classify_radii` (already
  shared) through it. Refactor `CompactionFunction` to call the new module.
- *Acceptance:* `CompactionFunction` output byte-identical to a golden run
  (name the driver command + a fixed small config, e.g. `quadratic-minimal.yaml`).
  This is a pure refactor — forbid any numeric change.
- *Trap:* the mass formula's magic constants and the `C_max`-not-`C_bar_max` use
  must be preserved exactly; call it out in *Constraints*.

**U2 — compute the parity set inside GCI.** Split into **two** prompts:
- **U2a** — add `C_bar` to `GradientCoupledInstantonProfileValue` (+ compute it
  via the U1 helper) and to the extraction/scale path; densify the node-level
  profile onto a dense r-grid before classification/integration.
  - *Decision point:* densify vs classify-on-nodes — recommend densify (matches
    `CompactionFunction`, removes n-dependence); note it changes the existing
    `diagnostics["scale_assignment"]` radii, which is acceptable.
  - *Assumable interfaces:* the U1 module's function signatures (state them).
- **U2b** — in `_compute_gradient_coupled_instanton`, after `assign_scales`,
  compute the full §7.1 scalar set via the U1 helpers and return them in the
  result dict; pick the downflow representative.
  - *Decision point:* `V/N_end_downflow` representative — recommend the
    `r_peak`-node value; leave a `# DESIGN-DECISION:` comment.
  - *Trap:* GCI downflows **per node**; the scalar must be a single value chosen
    consistently with the mass classification, not a per-node array.
- *Acceptance (U2b):* a unit test on a grid point where GCI and FI should agree,
  asserting the GCI scalar set matches the FI/CF values within tolerance.

**U3 — persist + rehydrate the parity columns.** One prompt (possibly two if the
profile-table `C_bar` column is cleanly separable).
- Add scalar columns to the `GradientCoupledInstanton` table and `C_bar` to the
  `GradientCoupledInstantonProfile` table; persist in `store()`; rehydrate in
  `build()` **including the `_do_not_populate` path**.
- *Acceptance:* round-trip store→load returns identical scalars; a
  `_do_not_populate=True` fetch exposes all §7.1 scalars (and none of the dense
  values). Name both as unit tests.
- *Trap:* these are parent-row scalars — confirm `validate()`'s child-row cascade
  is untouched; state that in *Must NOT*.

### Track P — plotting

**P1 — extract machinery, no behaviour change.** One prompt (or one per module if
large: provenance / sampling / dispatch / fetch).
- Move the reusable concerns into `plotting/` per design §2; re-point
  `plot_InstantonSolutions.py` at them.
- *Acceptance:* full `plot_InstantonSolutions.py` output **byte-identical** to a
  golden run (name command + config + a fixed seed if any). Forbid behaviour
  change in *Must NOT*.
- *Trap:* the `(remote_fn, args)` work-item convention and the terminal
  `RayWorkPool(..., store_results=False)` drain must be preserved exactly.

**P2 — introduce the adapter, convert figures.** One prompt.
- Add `InstantonAdapter` + `FullInstantonAdapter` + `SlowRollInstantonAdapter`;
  convert figure functions to consume `list[InstantonAdapter]`.
- *Assumable interfaces:* the exact FI/SR/CF attribute vocabularies (give the
  mapping table from design §3.1 so the coding model wires `.phi1`/`.phi`/etc.
  correctly).
- *Acceptance:* re-diff — output byte-identical to the P1 golden run.
- *Trap:* the adapter must get grid `coords` from the **query context**, not by
  scraping the object, so it works for `_do_not_populate` fetches.

**P3 — `profile_only` fetch mode + method contract.** One prompt.
- Implement the §4.1 table in the factory `build()` and the method guards.
- *Constraints:* paste the §4.1 behaviour table **into the prompt** as the spec.
- *Decision point:* confirm no other caller depends on the current (broader)
  raise before relocating it; recommend relocating to "dense values requested".
- *Acceptance:* a unit test per row of the §4.1 table (return-value or
  raise-type per cell). This is the highest-value test set in the whole plan —
  make it exhaustive.

**P4 — gradient adapter (`GradientCoupledAdapter` / `SpatialAdapter`).** One
prompt. **Depends on U3 and P2/P3.**
- Implement the base + spatial interfaces from design §3.2–§3.3 as **pure reads**
  (parity scalars now exist upstream). Core node = y=+1 for time histories.
  `is_spatial()` true only when `fidelity == "dense"`.
- *Acceptance:* homogeneous figure functions, unchanged, produce a GCI-overlaid
  figure when passed `[gci, full, sr]`; a named smoke test renders each figure
  family with a GCI adapter without error.
- *Trap:* `field_2d`/`derived_at_time` must raise (not return None) when
  `_values` is empty; the adapter must not call them for a non-dense fidelity.

**P5 — spatial figures.** Split: **P5a** heatmaps + slices (static, default);
**P5b** movies (opt-in `--movies`).
- *P5b Decision point:* mp4 needs ffmpeg — recommend defaulting
  `--movie-format gif` (Pillow), mp4 opt-in.
- *Trap (both):* render heavy `(y,N)` / `zeta_C_r_at_time` work **inside the Ray
  worker** from a passed proxy; never serialise big arrays through the work queue.
  Movies get per-frame provenance footer + title card.

**P6 — stability figures (α / n_colloc).** One prompt. Depends on P4 + the new
`build_gci_inputs` axes.
- Overlay sweeps reusing the §3.4 mechanism; plateau plots read the persisted
  columns from the cheap fetch.

**P7 — diagnostics figures.** One prompt (or split science-cost vs stiffness vs
convergence if large). Depends on P4.
- Fuse the diagnostics collection into the DOE scalar pass; port the
  compute-times figure to be adapter-fed; add the GCI-specific figures (Picard/
  Newton counts, forward-vs-backward RK45 stiffness, per-node extraction-failure
  map). Emit `diagnostics_data.csv` beside `scalar_data.csv`.
- *Assumable interfaces:* the GCI diagnostics key list from design §8 (paste it).

**P8 — new driver + compare mode.** One prompt.
- Wire `plot_GradientCoupledSolutions.py` mirroring `run_plots`; add the new CLI
  flags (design §10) and the `--compare-with full,slow-roll` overlay path.
- *Acceptance:* end-to-end run on `quadratic-minimal.yaml` produces the full
  output tree without error; `--compare-with` yields overlaid figures.

---

## 5. High-risk areas to fence explicitly

Call these out in *Constraints*/*Must NOT* wherever a prompt touches them — they
are the places a cheaper coding model is most likely to introduce a subtle bug:

- **The fidelity-state matrix (§4.1).** Return-vs-raise must match the table
  exactly. Paste the table into P3 and P4.
- **Upstream-vs-downstream compute (§7).** No physics in the plotting adapter.
  If a prompt about the adapter starts computing C̄ or a mass, it's wrong.
- **Backward integration & sinh transform.** Any prompt near `picard.py` /
  `response_rhs.py` must not convert a backward integration to forward or swap a
  `sinh` spline for `linear`.
- **Shard-key binning.** New axes must not become shard keys; fetches still bin
  by `delta_Nstar`.
- **Golden-run equality for refactors.** U1, P1, P2 must assert byte-identity;
  do not accept "equivalent".
- **Proxy serialisation.** Heavy GCI data crosses the Ray boundary via proxy +
  worker-side `.get()`, never as arrays in a work-item tuple.

---

## 6. Self-check before emitting each prompt

- [ ] Uses the §2 template with every field filled.
- [ ] Real repo paths (not flat names).
- [ ] Cites the design section(s) it implements.
- [ ] *Depends on* is correct; no prerequisite is unauthored; P4→U3 honoured.
- [ ] *Acceptance test* is verifiable without judgment.
- [ ] *Must NOT* fences the right scope (behaviour change for refactors; file
      scope for additive work).
- [ ] Doesn't reopen any §3 settled decision.
- [ ] Any relevant §3 open question appears as a *Decision point* with a default.
- [ ] Relevant §5 high-risk items are fenced.

If a step is too large for one unambiguous acceptance test, split it and re-run
this check on each piece.
