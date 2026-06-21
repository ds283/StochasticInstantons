# Prompt: provenance footer + plot-specific metadata annotations

## Context

`plot_InstantonSolutions.py` generates six figure types via Ray-dispatched
worker functions (`_plot_trajectory_item`, `_plot_fields_item`,
`_plot_msr_sweep_item`, `_plot_compaction_item`,
`_plot_compaction_summary_item`, and the MSR action sweep). Each worker
calls a corresponding `plot_*` function that builds the actual figure.

`DatastoreObject` now exposes a `.timestamp` property (added in a prior
pass) alongside the existing `.store_id`. Various compute-target objects
(`FullInstanton`, `SlowRollInstanton`, `CompactionFunction`,
`InflatonTrajectory`) carry additional attributes — tolerances,
`msr_action`, diffusion model, thresholds, labels — that aren't currently
shown anywhere on the figures.

We want two separate, independent additions:

1. A **generic provenance footer**, added once, that introspects
   whatever attributes are present on the object(s) passed to it.
2. A small number of **plot-specific annotations**, added per figure
   function, using fields that genuinely belong to that plot's subject
   matter rather than generic provenance.

These are deliberately decoupled — the footer must not need updating
every time a new object type gains a new attribute, and plot-specific
annotations must not be folded into the footer "for convenience."

## Part 1 — generic provenance footer

Add a single function, e.g.

```python
def _provenance_footer(fig, *objs, render_time=None):
    ...
```

in `plot_InstantonSolutions.py`. Behaviour:

- Accepts one or more `DatastoreObject`-derived instances (e.g. a
  `CompactionFunction` and the `FullInstanton`/`SlowRollInstanton` it was
  built from).
- For each object, introspects available attributes via `getattr`/
  `hasattr` — do not hardcode a fixed list of "the" fields per object
  type. At minimum check for: `store_id` (guard with `.available`),
  `timestamp`, and any of `atol`, `rtol`, `label` if present as public
  properties. Skip silently (no "None" placeholders) when an attribute
  isn't present or is `None`.
- Builds one short footer line per object, joined with a separator
  (e.g. `" | "`), and renders it via `fig.text(...)` in small,
  unobtrusive font at the bottom of the figure — distinct from the
  existing `cf_annotation`-style physics summary text, which stays
  exactly as it is now.
- Also includes a render timestamp (`datetime.now()`, captured when the
  figure is built — independent of any object's `.timestamp`) and the
  module's `VERSION_LABEL`.
- Must not raise if called with an object that has no `store_id`
  available (e.g. `available is False`) or no `timestamp` — degrade
  gracefully, never crash a plot job over missing provenance.

Call this from every one of the six plot functions, passing whichever
object(s) are the natural subject of that plot (e.g. `plot_compaction_summary`
passes the list/sequence of `CompactionFunction` objects it's plotting,
or a representative one if a single footer line suffices — use your
judgement on whether per-point footers make sense vs one summary line
for sweep plots).

## Part 2 — plot-specific annotations (separate, not in the footer)

Implement independently, each directly in its own `plot_*` function:

- **`plot_instanton_fields`**: annotate `msr_action` for both full and
  slow-roll instantons (where available), placed near the existing
  `Cmax`/`C̄max` annotation text, not in the footer.
- **`plot_compaction_summary`**: replace the current hardcoded `0.4`
  threshold line with the actual value read from the `CompactionFunction`
  objects' threshold attribute(s) (`C_threshold`/`C_bar_threshold` or
  equivalent public property name — check the actual attribute name on
  the object before assuming). If the threshold is the same across all
  points being plotted, show it once in the legend label (e.g.
  `f"Threshold ({threshold:.2f})"`); if it varies, flag this to the user
  rather than silently picking one value.

## Non-goals

- Do not unify Part 1 and Part 2 into one function — keep them
  separable so the footer stays generic and the annotations stay
  explicit per-plot.
- Do not add cosmology-name or diffusion-model annotations in this pass
  — out of scope here, can be a follow-up once we've seen how the
  footer looks in practice.
- Do not change figure sizes, themes, or layout — those were already
  handled in earlier passes.

## Acceptance criteria

- [ ] `_provenance_footer` exists as a single, generically-introspecting
      function — not six near-duplicate per-plot-type implementations.
- [ ] All six plot functions call it.
- [ ] Footer never raises on objects missing `store_id`/`timestamp` —
      demonstrate with a quick smoke test passing a freshly-constructed,
      unstored object (`store_id` unavailable, `timestamp=None`).
- [ ] `msr_action` appears on `instanton_fields` plots when available.
- [ ] `compaction_summary` threshold line is read from the actual object
      attribute, not hardcoded `0.4`; confirm the attribute name by
      reading `ComputeTargets/CompactionFunction.py` rather than
      guessing it matches the prompt's placeholder name.
- [ ] Regenerate one example of each of the six plot types and visually
      confirm the footer renders without overlapping existing titles/
      annotations/legends.

## Suggested order of work

1. Read `ComputeTargets/CompactionFunction.py` to confirm the real
   threshold attribute name(s) before writing Part 2.
2. Implement `_provenance_footer` and wire it into all six plot
   functions (one commit).
3. Implement the `msr_action` annotation on `instanton_fields` (one
   commit).
4. Implement the threshold fix on `compaction_summary` (one commit).
5. Regenerate sample plots for visual review.
