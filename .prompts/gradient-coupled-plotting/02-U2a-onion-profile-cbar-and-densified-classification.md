### Prompt U2a — Add C̄(y) to the onion profile via densified classification

- **Implements:** design §7.2 (fidelity note), §7.3 (bullet 1: `C_bar(r)` in
  the profile).
- **Track / step:** U2a
- **Depends on:** U1
- **Files (real paths):**
  - edit: `ComputeTargets/GradientCoupledInstanton/scale_assignment.py`
  - edit: `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`
    (only the `GradientCoupledInstantonProfileValue` class and the one
    call site in `_compute_gradient_coupled_instanton` that constructs it,
    around the `zip(data["zeta"], data["r_ratio"], data["C"], data["r_phys"])`
    block — do not touch anything else in this large file; U2b and U3 make
    the other edits to it)
  - edit: `ComputeTargets/compaction_scalars.py` (pure addition — see Task
    item 1)
- **Context to read first:** `ComputeTargets/GradientCoupledInstanton/scale_assignment.py`
  in full (module docstring included — it documents the three distinct
  notions of "scale" and why the r_phys array is naturally *descending* in
  grid order); `ComputeTargets/compaction_scalars.py` (from U1); the Step D
  densification block in `ComputeTargets/CompactionFunction.py` that U1 just
  extracted into `densify_zeta_profile`/`compute_C_bar`.
- **Assumable interfaces:**
  - From U1: `compaction_scalars.densify_zeta_profile(r_v, zeta_v) -> (r_dense, zeta_dense, zeta_prime_dense)`,
    `compaction_scalars.compute_C_bar(r_dense, zeta_dense, zeta_prime_dense, r_v, zeta_v) -> np.ndarray`,
    `compaction_scalars.classify_radii(r_v, C_v, C_threshold) -> (r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge)`.
  - `assign_scales`'s current return dict keys, verbatim from the present
    code: `failure`, `r_ratio`, `C`, `r_phys`, `r_phys_out`, `r_max`,
    `r_peak`, `diagnostics`. `r_phys` is **descending** in grid order (y=-1
    outer edge → y=+1 core is smallest-r → largest-r... actually the module
    docstring states grid order runs y=-1 (outer edge, largest r) to y=+1
    (core, smallest r), so `r_phys` is naturally descending); `assign_scales`
    already re-sorts ascending via `np.argsort(r_phys)` immediately before
    calling `classify_radii` — reuse that same sorted view for the new
    densification/classification call, don't re-sort a second time
    independently.
  - `GradientCoupledInstantonProfileValue.__init__(self, node_index, zeta, r_ratio, C, r_phys)`
    is the current constructor signature (no `C_bar` parameter yet).
- **Task:**
  1. In `compaction_scalars.py`, no new function should be needed beyond what
     U1 already added (`densify_zeta_profile`/`compute_C_bar`/`classify_radii`)
     — confirm this before writing new code; if `assign_scales` needs the
     dense grid built from an *already-sorted-ascending* `r_v` (it does),
     the existing `densify_zeta_profile` signature already takes `(r_v, zeta_v)`
     directly, so no change to `compaction_scalars.py` should be necessary.
     Only add something there if, on inspection, you find
     `densify_zeta_profile`/`compute_C_bar` cannot be called as-is with GCI's
     sorted `(r_phys, zeta)` pair — and if so, keep the addition to a pure
     new function, not a modification of an existing U1 signature (U1 is
     already golden-tested; don't reopen it).
  2. In `assign_scales`, after computing the node-level `C` (`rho_zeta_prime`/
     the `(2/3)(1-(1+rho_zeta_prime)^2)` line) and `r_phys`, sort by `r_phys`
     ascending (the existing `sort_idx = np.argsort(r_phys)` line), then call
     `compaction_scalars.densify_zeta_profile(r_phys[sort_idx], zeta[sort_idx])`
     and `compaction_scalars.compute_C_bar(...)` to obtain a node-level
     `C_bar` array (via the same "interpolate the cumulative integral back to
     the sample points" step U1 already implements) — **do not** reimplement
     the geomspace/spline/gradient machinery inline in this file; call the
     `compaction_scalars` helpers.
  3. Re-run `compaction_scalars.classify_radii` on the **densified** grid
     rather than the raw node-level `(r_phys, C)` pair used today. This
     changes what `r_max`/`r_peak` (and, downstream, `M_max`/`M_peak` once
     U2b lands) numerically mean relative to the current behaviour — see the
     Decision point below.
  4. Add `C_bar` (a node-level array, same length and ordering as `r_ratio`/
     `C`/`r_phys` — i.e. back in the *original*, un-sorted grid order before
     returning, matching how `r_ratio`/`C`/`r_phys` are already returned) to
     `assign_scales`'s return dict.
  5. Add a `C_bar: float` parameter to `GradientCoupledInstantonProfileValue.__init__`
     and a matching `@property def C_bar(self) -> float`, mirroring `zeta`/
     `r_ratio`/`C`/`r_phys` exactly.
  6. Update the one call site in `GradientCoupledInstanton.py` that constructs
     `GradientCoupledInstantonProfileValue` from the `zip(...)` of `data["zeta"]`,
     `data["r_ratio"]`, `data["C"]`, `data["r_phys"]` to also zip in and pass
     `C_bar=cb` from a new `data["C_bar"]` key — this key does not exist yet
     in the Ray-remote function's returned dict; leave it absent for now (it
     will be `KeyError`-safe only once U2b's edit to
     `_compute_gradient_coupled_instanton` adds it — if U2a is executed
     before U2b, guard this call site with `data.get("C_bar")` defaulting to
     `None` per node, so the two prompts don't have a hard ordering
     dependency on which one runs first inside the same file).
- **Constraints:** follow the conventions checklist; plus: preserve the
  module's documented distinction between the three notions of scale — do
  not let the new densification touch the *comoving* (`r_ratio`) calculation,
  only the compaction/classification/C̄ path.
- **Must NOT:** touch `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`
  (schema and persistence are U3's job — after this prompt, `C_bar` exists
  in memory only, and a round-trip store→load will not yet carry it; that is
  an expected, acceptable transient state, not a bug to fix here); must NOT
  edit `extraction.py`, `picard.py`, `forward_rhs.py`, or `response_rhs.py`;
  must NOT change the *comoving* radius calculation or the physical-anchor
  (Leach–Liddle) solve.
- **Acceptance test:** a unit test (`tests/test_scale_assignment_densification.py`)
  against a converged `GradientCoupledInstanton` test fixture that: (a)
  asserts `assign_scales(...)["C_bar"]` is present, finite, and the same
  length/ordering as `["C"]`; (b) asserts the returned `r_max`/`r_peak`
  numerically **differ** from a stashed pre-change golden value for the same
  fixture — this is deliberately an inequality check, not the usual
  golden-run equality, because the whole point of this prompt is to change
  those two numbers (see Decision point). Document that inversion explicitly
  in the test's docstring so a future reader doesn't mistake the changed
  values for a regression.
- **Decision point:** densify vs. classify-on-raw-nodes (design §12, §4 "Per-step
  guidance" U2a). **Recommended default: densify** (matches
  `CompactionFunction`'s own fidelity, and removes an `n_collocation_points`-
  dependence artifact from `r_max`/`r_peak` that would otherwise contaminate
  the stability/convergence figures in P6 — a node-count-dependent
  classification would make the "does C_peak plateau as n grows" question
  answer itself trivially). Leave a comment at the `classify_radii` call site
  in `assign_scales`:
  `# DESIGN-DECISION: classification and C_bar integration now run on a densified log-r grid rather than the raw LGL nodes; this changes diagnostics["scale_assignment"]["r_max"/"r_peak"] relative to pre-U2a runs (see design doc §7.2 "One fidelity note" and onion_model_implementation_review.md).`
