### Prompt P5b — Spatial `(y,N)` figures: movies (opt-in `--movies`)

- **Implements:** design §6.2 (item 3), §6.3 (the optional ζ(r)/C(r) movie
  through N), §9 (item 3: movie provenance).
- **Track / step:** P5b
- **Depends on:** P4, P5a
- **Files (real paths):**
  - edit: `plotting/figures/spatial.py` (add movie functions alongside
    P5a's heatmap/slice functions, in the same module — design §2 places
    all of §6.2's figures in this one file)
  - edit: `plot_GradientCoupledSolutions.py` — this file does not exist yet;
    if P8 (new driver) has not yet landed, add a placeholder/minimal
    `--movies`/`--movie-format` argument pair to whatever driver entry point
    currently exists at this point in the build (check whether P8 has
    landed before editing; if not, note in your PR/commit message that the
    flag wiring will be re-checked once P8 lands, since P8 owns the driver's
    full CLI surface)
- **Context to read first:** `plotting/figures/spatial.py` (P5a, for the
  `field_2d`/`derived_at_time` access patterns to reuse); `plotting/provenance.py::_provenance_footer`
  (P1) — note it renders a **static** footer via `fig.text(...)`, which does
  not survive `matplotlib.animation.FuncAnimation` frame-by-frame rendering,
  so movies need their own provenance treatment, not a call to this
  function per frame.
- **Assumable interfaces:** `SpatialAdapter.field_2d`/`derived_at_time` from
  P4 (raise on non-dense, as established); `plotting/adapters/gradient.py`'s
  `ExtractionCache`-backed memoisation inside `zeta_C_r_at_time` (repeated
  frame queries at nearby `N` are cheap after the first call, per
  `GradientCoupledInstanton.zeta_C_r_at_time`'s own docstring) — this is
  what makes a ζ(r)/C(r) movie through `N` affordable; do not add a second,
  separate cache layer in this prompt.
- **Task:**
  1. A `(y,N)` movie: `FuncAnimation` sweeping through `N` (frame = profile
     vs. `y`, or vs. `r` via the node's `r_ratio`/`r_phys`) for one or more
     of `φ`, `π`, `r_φ`, `r_π`, mirroring the static heatmap's panel
     selection.
  2. A ζ(r)/C(r) movie through `N`, built by calling
     `SpatialAdapter.derived_at_time(N_query)` once per frame (via the
     underlying `zeta_C_r_at_time`, cache-backed).
  3. **Persistent per-frame provenance**: burn a footer line
     (version/timestamp/coords string, same content
     `_provenance_footer` would produce, but rendered via a plain
     `ax.text`/`fig.text` call inside the animation's per-frame update
     function, not a call to `_provenance_footer` itself, since a movie has
     no single "end of render" moment for that function's `subplots_adjust`
     logic to apply against) plus an opening title-card frame carrying the
     same string, per design §9 item 3.
  4. Wire both movie functions behind the driver's `--movies` flag (default
     off) and `--movie-format {mp4,gif}` (see Decision point). When
     `--movies` is absent, these functions are simply never dispatched —
     do not add a runtime early-return inside the movie functions
     themselves for this; the gate belongs in the driver's work-item
     construction (P8), so an un-gated call to these functions (e.g. from a
     test) still renders correctly.
  5. Render **inside the Ray worker**, from the proxy, exactly as P5a's
     static figures do — a movie is the single most expensive output in the
     whole design (§6.2 item 3's own framing), so this is not optional here.
- **Constraints:** follow the conventions checklist; plus: gate mp4 support
  on `ffmpeg` availability at the call site (see Decision point) rather than
  letting `matplotlib.animation.FFMpegWriter` raise an opaque error deep
  inside a Ray worker.
- **Must NOT:** call `plotting/provenance.py::_provenance_footer` from
  inside a `FuncAnimation` frame-update callback; must NOT make movies the
  default tier (they stay strictly opt-in); must NOT change P5a's static
  heatmap/slice functions.
- **Acceptance test:** a named smoke test that renders a short (e.g.
  5-frame) `(y,N)` movie and a short ζ(r)/C(r) movie for a converged
  dense-fidelity GCI test fixture in `gif` format without error (gif needs
  only Pillow, always available), and a separate test — skipped/xfail if
  `ffmpeg` is not present on the test runner, per the Decision point below —
  exercising the `mp4` path.
- **Decision point:** ffmpeg/mp4 vs. gif default (design §12, §4 P5b). mp4
  needs `ffmpeg` on the render nodes; gif needs only Pillow (bundled with
  matplotlib). **Recommended default: `--movie-format gif`**, with mp4 as an
  explicit opt-in that fails loudly (not silently falls back to gif) with a
  clear "ffmpeg not found" message if requested but unavailable. Leave a
  comment at the format-dispatch point:
  `# DESIGN-DECISION: default movie format is gif (Pillow-only, no external dependency); mp4 is opt-in via --movie-format mp4 and requires ffmpeg on the render node — see design doc §12 "Movie dependency".`
