---
paths:
  - "plot_*.py"
---

# Matplotlib text must use LaTeX markup, not embedded Unicode glyphs

Loaded when Claude works on `plot_*.py` files. Applies to any text passed to
Matplotlib — titles, suptitles, axis labels, legends, annotations.

## The rule

Never embed Unicode symbols (Greek letters, stars, arrows, etc.) directly in
a plain-text string passed to Matplotlib. Always express them as LaTeX
mathtext inside `$...$`, using a raw string:

```python
# Wrong — raw Unicode glyphs in plain text
fig.suptitle(f"... δN★={dns_val:.3g}")

# Right — LaTeX mathtext
fig.suptitle(rf"... $\delta N_\star$={dns_val:.3g}")
```

## Why

A glyph outside `$...$` that isn't covered by the active font (e.g. Arial)
forces Matplotlib to do a font-fallback scan across system fonts and touch
its shared font-cache file. In a Ray-dispatched batch this happens in many
worker processes at once, all racing on the same cache file — this caused a
real incident where `plot_InstantonSolutions.py` silently hung after
dispatching a batch of `_plot_fields_item` tasks, because the suptitle used
a raw `★` (U+2605) and `δ` instead of mathtext. The sibling MSR-sweep plot,
which already used `r"$\delta N_\star$"`, was unaffected because mathtext is
rendered with Matplotlib's own internal math fonts and never touches the
system-font fallback path.

## How to apply

- Any new caption, title, or label containing Greek letters, stars, or other
  non-ASCII symbols must use `$...$` mathtext (`\delta`, `\star`, `\times`,
  etc.), not the literal Unicode character.
- This applies in particular to text rendered inside a `@ray.remote`
  function, since that's where concurrent font-cache contention bites.
- Plain ASCII strings printed to the console (not rendered by Matplotlib)
  are not affected by this rule.
