### Prompt P1 — Extract reusable plotting machinery into `plotting/`, no behaviour change

- **Implements:** design §2 (package layout), §1 (concerns 2–4: Ray-remote
  render wrappers, data-fetch/sweep orchestration, provenance/annotation).
- **Track / step:** P1
- **Depends on:** none
- **Files (real paths):**
  - add:  `plotting/__init__.py`
  - add:  `plotting/provenance.py`
  - add:  `plotting/annotations.py`
  - add:  `plotting/sampling.py`
  - add:  `plotting/dispatch.py`
  - add:  `plotting/fetch.py`
  - edit: `plot_InstantonSolutions.py` (re-point at the new modules; delete
    the now-duplicated function bodies)
- **Context to read first:** `plot_InstantonSolutions.py` in full (it is
  ~2600 lines; at minimum read every function this prompt moves, listed
  below, plus `run_plots` and the `__main__` block to see how they're
  wired together); design §2 and §5 (Ray-dispatch layer).
- **Assumable interfaces:** none — this is a pure code-motion prompt. State,
  for your own bookkeeping, exactly which current top-level functions in
  `plot_InstantonSolutions.py` move to which new module (do not rename any
  of them in this prompt — names change, if at all, in P2):
  - → `plotting/provenance.py`: `_provenance_footer`.
  - → `plotting/annotations.py`: `_extract_cf_annotation`, `_cf_annotation_text`,
    `_add_cf_annotation`.
  - → `plotting/sampling.py`: `_evenly_sample`, `_safe_name`, `_safe_num`.
  - → `plotting/dispatch.py`: the `(remote_fn, args)` work-item convention
    used by `_dispatch_plot_work`, and a new generic `@ray.remote _render_item(figure_fn, payload, output_dir_str, fmt, run_label)`
    function per design §5 — but do **not** yet convert any of the existing
    seven `@ray.remote _plot_*_item` wrappers to call through it (that is
    P2's job, once figures take adapters); this prompt only adds the generic
    dispatcher alongside the untouched existing wrappers and moves
    `_dispatch_plot_work` itself.
  - → `plotting/fetch.py`: `_instanton_key_payload`, `_cf_key_payload`,
    `_qualifying_action`, `_extract_cf_summary`, `_cf_vectorized_fetch`, and
    a new generic `fetch_over_grid(pool, class_name, shard_key_of, key_payload_of, items, do_not_populate=True) -> list`
    per design §4 — again, add this generic function alongside the existing
    hand-rolled fetch loops (`_sweep_Ninit_or_Nfinal`, `_sweep_delta_Nstar`,
    `_generate_instanton_samples`, `_collect_doe_scalar_data`) without yet
    converting them to call it; that conversion is a separate, later
    concern the design defers past this build order (P1's job is extraction
    with zero behaviour change, not introducing a new call pattern into the
    hot path).
- **Task:** Move each function listed above verbatim (same body, same
  signature) into its new module, adjusting only the necessary imports.
  Re-point `plot_InstantonSolutions.py` to import from `plotting.*` and
  delete the now-duplicated local definitions. Add the two new generic
  helpers (`_render_item` in `dispatch.py`, `fetch_over_grid` in `fetch.py`)
  as pure additions — unused by the existing driver for now, present so P2
  onward can adopt them without a second "add the generic helper" step.
- **Constraints:** follow the conventions checklist; plus: the
  `(remote_fn, args)` work-item convention and the terminal
  `RayWorkPool(..., store_results=False)` drain in `run_plots` must be
  preserved exactly — do not change how `work_items` is built or how
  `RayWorkPool` is constructed in this prompt. Carry the Apache-2.0 /
  University of Sussex header on every new file, copied from
  `plot_InstantonSolutions.py`.
- **Must NOT:** change the behaviour, output, or call signature of any moved
  function; must NOT convert any of the seven existing `_plot_*_item`
  Ray-remote wrappers to use the new `_render_item`; must NOT convert any of
  the four hand-rolled fetch functions to use the new `fetch_over_grid`;
  must NOT touch `plot_doe_scalar_summary`, `plot_instanton_fields`, or any
  other figure-drawing function's body — those stay exactly where they are
  until P2.
- **Acceptance test:** run `python plot_InstantonSolutions.py --config quadratic-minimal.yaml --database <fixed-db>`
  before and after this change, on the same pre-populated database, and diff
  every output file in the resulting `plots/` tree byte-for-byte (or, since
  matplotlib output can carry non-deterministic metadata timestamps in some
  backends, diff with `--format svg` and strip/ignore only a documented
  metadata-timestamp field, never plot content) — must be identical. Name
  this `tests/test_plot_extraction_golden.py`, driven by a fixed small
  database and `quadratic-minimal.yaml`.
- **Decision point:** none.
