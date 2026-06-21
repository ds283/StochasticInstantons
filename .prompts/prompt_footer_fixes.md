# Prompt: fix provenance footer formatting and detail-plot layout

Follow-up to the provenance footer added in the previous pass. Four
fixes, based on visual review of regenerated sample plots:

## 1. `tolerance` objects render as `<MetadataConcepts.tolerance.tolerance object at 0x...>`

`tolerance` (in `MetadataConcepts/tolerance.py`) already implements
`__float__` (returns `self.tol`) but has no `__str__`, so an f-string
like `f"atol={atol_obj}"` falls through to the default `__repr__`.

Fix in `_provenance_footer` (`plot_InstantonSolutions.py`): when
formatting a value that has a numeric nature, coerce explicitly with
`float(val)` rather than relying on implicit `str()`/f-string
formatting, e.g. `f"atol={float(atol_obj):.2g}"`. Do not add a
`__str__` to `tolerance` itself — the existing `__float__` is
sufficient and the fix belongs in the generic formatting path, not the
class.

Apply the same explicit-`float()`-coercion pattern generally in
`_provenance_footer` for any attribute value before formatting it into
the footer string, not just `atol`/`rtol` — anywhere the footer
currently trusts an object's default string conversion.

## 2. Footer font too small on `compaction_summary` / `msr_action_sweep`

Bump the footer fontsize by 1–2pt on these two plot types specifically
(both already have plenty of vertical headroom below the axes — this
is a font-size fix, not a layout fix).

## 3. Footer too small / collides with existing annotation on
   `instanton_fields` and `compaction` (zeta/compaction) plots

These two plot types already place a multi-line `cf_annotation` physics
summary in the same general area as the new footer. Fix:
- Reserve explicit, separate vertical space for the footer via
  `fig.subplots_adjust(bottom=...)`, distinct from wherever
  `cf_annotation` is anchored, so the two never overlap regardless of
  how many lines `cf_annotation` ends up needing.
- Footer fontsize should match the size used in part 2 above (i.e. one
  consistent footer fontsize across all six plot types) rather than
  being independently smaller here.

## 4. Excess vertical whitespace at the bottom of `instanton_fields`

Separate from (3) — even after the footer/annotation collision is
fixed, there's noticeably more blank space below the bottom row of the
2x2 grid than the other plot types have. Check
`fig.subplots_adjust`/`tight_layout`/`figsize` interaction introduced
when the figure height was bumped to fix the original "compressed"
complaint, and reduce the bottom margin to something proportionate —
don't just leave room sized for the largest possible footer/annotation
combination if it's wasting space in the common case.

## Acceptance criteria

- [ ] Regenerate one example of each of the six plot types.
- [ ] `background_fields`/`background_epsilon`-style plots (objects with
      `atol`/`rtol`) show the numeric tolerance value, not a Python
      object repr.
- [ ] Footer text is legible and a consistent size across all six plot
      types.
- [ ] No overlap between footer and `cf_annotation` text on
      `instanton_fields` or `compaction` plots.
- [ ] `instanton_fields` no longer has disproportionate bottom
      whitespace relative to the other plot types.
