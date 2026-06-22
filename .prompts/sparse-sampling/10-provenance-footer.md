# Prompt 10 — Two-line provenance footer with run label

## Context

`_provenance_footer` currently renders a single grey line at the very bottom
of every figure:

```
StochasticInstanton v2026.3.0  |  2026-06-22 13:36:10
```

When the same grid is computed twice — once with `--no-store-values` and
once without, or against two different databases — the output plots are
visually indistinguishable. The database filename, config file, and active
mode flags need to be in the footer.

**Before writing anything**, read the following in the current repo:
- `_provenance_footer` (lines 223–278) — current single-line implementation
- `_add_cf_annotation` (lines 194–220) — already uses proportional bottom-
  margin reservation via `tight_layout(rect=...)` and `subplots_adjust`;
  follow the same pattern for the extra footer line
- All seven `_provenance_footer` call sites (lines 362, 392, 526, 571,
  635, 748, and the `plot_doe_scalar_summary` added in Prompt 9)
- The six `@ray.remote` worker functions that call the six `plot_*`
  functions above
- `_generate_instanton_samples`, `_sweep_Ninit_or_Nfinal`,
  `_sweep_delta_Nstar`, `_run_doe_summary_plots` — the driver-side
  functions that build work-item tuples; each needs `run_label` threaded
  through so it can be included in the tuples passed to the workers
- `run_plots` — where `run_label` is constructed and where all of the above
  are called

## Task

### 1. Extend `_provenance_footer`

Add `run_label: str = ""` as a keyword-only argument after `render_time`.
When `run_label` is non-empty, render **two** lines:

```
<run_label>                      ← top line
StochasticInstanton … | …        ← existing bottom line (unchanged)
```

Use a single `fig.text(…)` call with a `\n`-joined string and
`va="bottom"` anchored at `y=0.003` — matplotlib stacks multi-line text
upward from the anchor, so the existing bottom line stays in place and
`run_label` appears above it.

Reserve extra bottom margin when two lines are needed, using the same
proportional pattern as `_add_cf_annotation`:

```python
if run_label:
    fig_height_in = fig.get_size_inches()[1]
    two_line_strip_in = 0.30   # empirical: 2 × fontsize-7 lines + gap
    bottom_frac = two_line_strip_in / fig_height_in
    current_bottom = fig.subplotpars.bottom
    if bottom_frac > current_bottom:
        fig.subplots_adjust(bottom=bottom_frac)
```

Call this adjustment **before** `fig.text(…)`, since `subplots_adjust`
after `tight_layout` overrides only the bottom margin (the other margins
remain as `tight_layout` set them). The constant `0.30` may need small
empirical tuning — if test output shows the second line clipping into axes,
increase it; if there is excessive whitespace, decrease it.

For the single-line case (`run_label` empty or omitted): behaviour is
**byte-for-byte identical** to the current implementation — no margin
adjustment, same y=0.003 placement.

### 2. Construct `run_label` in `run_plots`

At the top of `run_plots`, just after `fmt = args.format`:

```python
# ── Run provenance label ──────────────────────────────────────────────
_db_stem   = Path(args.database).name
_cfg_stem  = Path(args.config).name if getattr(args, "config", None) else None
_flags     = []
if getattr(args, "no_store_values", False):
    _flags.append("[summary-only]")
_run_label_parts = [p for p in [_db_stem, _cfg_stem] if p]
if _flags:
    _run_label_parts.append(" ".join(_flags))
run_label = "  |  ".join(_run_label_parts)
# e.g. "quad-ast-small-novalues.sqlite  |  quadratic-asteroid-small.yaml  |  [summary-only]"
```

`getattr` guards are used because `args.config` and `args.no_store_values`
may not exist in all invocation contexts (e.g. direct API use). Graceful
degradation to an empty string is fine.

### 3. Thread `run_label` through driver-side helpers

Add `run_label: str = ""` to the signature of each driver-side function
that builds work-item tuples, and pass it into each tuple that invokes
a `@ray.remote` worker:

- `_generate_instanton_samples(…, run_label="")` — two tuples:
  `_plot_fields_item` and `_plot_compaction_item`
- `_sweep_Ninit_or_Nfinal(…, run_label="")` — two tuples per combo:
  `_plot_msr_sweep_item` and `_plot_compaction_summary_item`
- `_sweep_delta_Nstar(…, run_label="")` — same
- `_run_doe_summary_plots(…, run_label="")` — one tuple:
  `_plot_doe_summary_item`

In `run_plots`, pass `run_label=run_label` at every call site for these
four functions. Also update the `_plot_trajectory_item` work-item tuple
(built directly in the `run_plots` loop) to include `run_label`.

### 4. Thread `run_label` through `@ray.remote` workers

Add `run_label: str = ""` to the signature of each of the six workers,
and forward it to the `plot_*` function they call:

- `_plot_trajectory_item(…, run_label="")` → `plot_background_fields(…,
  run_label=run_label)` and `plot_epsilon(…, run_label=run_label)`
- `_plot_fields_item(…, run_label="")` → `plot_instanton_fields(…,
  run_label=run_label)`
- `_plot_msr_sweep_item(…, run_label="")` → `plot_msr_action_sweep(…,
  run_label=run_label)`
- `_plot_compaction_item(…, run_label="")` → `plot_zeta_and_compaction(…,
  run_label=run_label)`
- `_plot_compaction_summary_item(…, run_label="")` →
  `plot_compaction_summary(…, run_label=run_label)`
- `_plot_doe_summary_item(…, run_label="")` →
  `plot_doe_scalar_summary(…, run_label=run_label)`

### 5. Thread `run_label` through `plot_*` functions

Add `run_label: str = ""` to the signature of each pure plot function,
and pass `run_label=run_label` to its `_provenance_footer(…)` call:

- `plot_background_fields`
- `plot_epsilon`
- `plot_instanton_fields`
- `plot_msr_action_sweep`
- `plot_zeta_and_compaction`
- `plot_compaction_summary`
- `plot_doe_scalar_summary`

## Acceptance criteria

- [ ] Running `plot_InstantonSolutions.py` against the two databases from
      the smoke test (`quad-ast-small-full.sqlite` and
      `quad-ast-small-novalues.sqlite`) with the same config: the two
      compaction-summary PDFs now have visually distinct footers —
      specifically the database filename differs, and the `[summary-only]`
      flag appears on the `novalues` run.
- [ ] The second footer line (`run_label`) appears above the existing
      version/timestamp line, with no clipping into the axes content on any
      of the standard figure sizes (trajectory 2-panel, instanton fields
      2×2, sweep 3-panel, compaction 3-panel, DOE scatter 2×2 and 1×2).
- [ ] Running without `--no-store-values` and without a `--config` file:
      `run_label` contains only the database filename, the single-line
      footer remains visually similar to the current output, and no extra
      whitespace appears at the bottom.
- [ ] Running with no arguments that produce a non-empty `run_label` (i.e.,
      empty string): `_provenance_footer` produces identical output to the
      current implementation — single line at y=0.003, no margin
      adjustment.
- [ ] `git diff` touches only `plot_InstantonSolutions.py`. No compute-
      target files, no factory files, no `main.py`.

## Out of scope (do not attempt in this prompt)

- Changing any figure layout, size, or colour scheme beyond the bottom-
  margin reservation for the second footer line.
- Adding provenance to non-figure outputs (the CSV from Prompt 9 is out of
  scope — a header comment in the CSV would be a natural follow-up but is
  not part of this prompt).
- Any changes to the `--no-store-values` pipeline behaviour.

## Commit

One commit, message along the lines of:
`plot_InstantonSolutions: two-line provenance footer with database and config label`
