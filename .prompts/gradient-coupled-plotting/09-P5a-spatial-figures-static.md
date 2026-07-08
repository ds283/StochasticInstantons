### Prompt P5a — Spatial `(y,N)` figures: heatmaps + slices (static, default)

- **Implements:** design §6.2 (items 1–2 only — movies are P5b), §5
  (Ray-dispatch layer's proxy-passing caveat for spatial work).
- **Track / step:** P5a
- **Depends on:** P4
- **Files (real paths):**
  - add:  `plotting/figures/spatial.py`
- **Context to read first:** `plotting/adapters/gradient.py`'s `SpatialAdapter`
  (P4) — specifically `field_2d(name)`'s return shape `(y_nodes, N_grid, Z[N,y])`
  and its raise-on-non-dense behaviour; `plotting/dispatch.py`'s
  `_render_item` generic remote (P1) and design §5's proxy-passing caveat;
  `GradientCoupledInstantonProxy` (`ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`)
  — its `.get()` method and the "never reach past the proxy" convention;
  `plotting/provenance.py::_provenance_footer` (P1).
- **Assumable interfaces:**
  - `SpatialAdapter.field_2d(name) -> (y_nodes: np.ndarray, N_grid: np.ndarray, Z: np.ndarray)`
    for `name in {"phi", "pi", "rfield", "rmom"}`, raising `RuntimeError` if
    called on a non-dense adapter (P4) — figure code must check
    `adapter.is_spatial()` **before** calling it, not rely on catching the
    raise.
  - `GradientCoupledInstantonProxy.get() -> GradientCoupledInstanton` — the
    cheap-to-serialise proxy; the full object (with its dense `.values`) is
    only materialised inside the Ray worker.
- **Task:**
  1. **Heatmaps.** A 2×2-panel figure (`φ`, `π`, `r_φ`, `r_π`), each panel a
     `pcolormesh` over `(N, y)` for one `SpatialAdapter`-fidelity GCI
     instance. Skip (return without drawing) if
     `not any(a.is_spatial() and a.available for a in adapters)` per design
     §3.3's own guard pattern — copy that exact one-liner, don't
     reimplement the check differently. Carry the provenance footer
     (`plotting/provenance.py::_provenance_footer`) and the full coordinate
     tuple (`N_init, N_final, δN★, α, n_colloc`) in the title, per design
     §9 item 1 ("every per-instanton figure should stamp the full
     coordinate tuple").
  2. **Slice overlays.** A companion figure: a handful of N-slices (profile
     vs. `y` at selected e-folds — evenly sample via
     `plotting/sampling.py::_evenly_sample`, P1) and a handful of y-slices
     (history vs. `N` at selected shells — edge `y=-1`, mid, core `y=+1`).
     The **core** y-slice must overlay cleanly against a
     `FullInstantonAdapter`'s `time_history("phi")` when one is present in
     the passed `adapters` list (design §6.2 item 2's "these also overlay
     cleanly against FI/SR where an analogue exists") — reuse the same
     `for a in adapters: ...` loop pattern from P2's converted figures, do
     not special-case GCI inside the loop body beyond the `is_spatial()`
     gate needed to pick the right data-access method.
  3. Wire both into the driver's dispatch: per design §5's caveat, do **not**
     serialise the `(y,N)` arrays through the Ray work-item tuple. Pass the
     `GradientCoupledInstantonProxy` itself into the render task and call
     `.get()` + `field_2d(...)` **inside** the worker (i.e. inside the
     `@ray.remote` function these figures are dispatched through), building
     the `SpatialAdapter` there rather than on the driver.
- **Constraints:** follow the conventions checklist; plus: heatmaps and
  slices are the **default** tier — no CLI flag gates them (only movies,
  P5b, are opt-in).
- **Must NOT:** implement movies or `matplotlib.animation` in this prompt
  (P5b); must NOT pass raw numpy arrays through the `(remote_fn, args)`
  work-item tuple for the dense `(y,N)` data — only the proxy; must NOT
  call `field_2d`/`derived_at_time` without first checking `is_spatial()`.
- **Acceptance test:** a named smoke test that renders both figures (2×2
  heatmap panel, slice-overlay panel) for a converged dense-fidelity GCI
  test fixture without error, and asserts the figure is skipped (no file
  written, no exception) when passed only non-spatial adapters (e.g.
  `[full_adapter, sr_adapter]` with no GCI present, or a GCI adapter at
  `profile`/`scalars` fidelity).
- **Decision point:** none.
