# Design: a science-output driver for `GradientCoupledInstanton`

Target reader: whoever implements the new plotting driver. This document
proposes an architecture that (a) produces GCI-equivalent science outputs, (b)
lets GCI, `FullInstanton` (FI) and `SlowRollInstanton` (SR) share axes on the
same figures, (c) keeps the rich provenance stamping, (d) adds 2‑D `(y,N)`
visualisation and on-the-fly derived profiles, (e) folds the new `alpha` /
`n_collocation_points` axes into the sweep machinery, and (f) turns the JSON
diagnostic blobs into first-class figures alongside the science they annotate.

The headline recommendation: **do not extend `plot_InstantonSolutions.py`, and
do not fork it. Refactor its reusable machinery out into a small `plotting/`
package, then express both the existing homogeneous driver and a new
gradient-coupled driver as thin front-ends over that library, with a data
`Adapter` layer as the seam.** The adapter is what makes cross-solver overlay,
provenance, and diagnostics uniform instead of triplicated.

---

## 1. Why refactor rather than modify-in-place or fork

`plot_InstantonSolutions.py` is ~2600 lines and already mixes five concerns
that want to move at different speeds:

1. **Figure functions** (`plot_instanton_fields`, `plot_zeta_and_compaction`,
   `plot_compaction_summary`, `plot_doe_scalar_summary`, …) — pure
   matplotlib, no Ray, no datastore.
2. **Ray-remote render wrappers** (`_plot_*_item`) — one per figure, each a
   near-identical `sns.set_theme(); Path(...); call the figure function`.
3. **Data-fetch / sweep orchestration** (`_sweep_Ninit_or_Nfinal`,
   `_sweep_delta_Nstar`, `_generate_instanton_samples`,
   `_collect_doe_scalar_data`) — the vectorized `object_get_vectorized`
   binning-by-shard-key logic.
4. **Provenance / annotation** (`_provenance_footer`, `_add_cf_annotation`,
   `_cf_annotation_text`, `_extract_cf_annotation`).
5. **Orchestration** (`run_plots` + `__main__`).

Concerns 2–4 are entirely solver-agnostic and are exactly what a GCI driver
needs verbatim. Concern 1 is *mostly* shareable if the figure functions stop
reaching into `fi._values[i].phi1` directly. Concern 3 is shareable in shape
but not in payload (GCI has extra key fields). Only concern 5 is genuinely
per-driver.

- **Modify in place** loses: the file becomes ~4000 lines and every GCI change
  risks the homogeneous path.
- **Fork** loses: `_provenance_footer`, the shard-binning fetch pattern, the
  DOE scaffolding, the annotation helpers all get copy-pasted and drift.
- **Refactor + adapter** wins on the brief's own criterion — *"compare GCI with
  FI/SR as lines on the same plot"* is free once every figure function consumes
  a list of adapters instead of a hard-coded `(fi, sri)` pair.

Treat the existing file as a **quarry**: most of its bodies survive almost
unchanged, they just move and lose their hard-wired field access.

---

## 2. Proposed package layout

```
plotting/
  __init__.py
  provenance.py        # _provenance_footer, _add_annotation, version/git stamp
  annotations.py       # scalar-summary annotation blocks (was _cf_annotation_*)
  sampling.py          # _evenly_sample, grid/axis helpers, _safe_name/_safe_num
  dispatch.py          # RayWorkPool wiring, generic _render_item wrapper,
                       #   the (remote_fn, args) work-item convention
  fetch.py             # shard-key binning + object_get_vectorized helpers,
                       #   generic "fetch these targets over this grid" routines

  adapters/
    __init__.py
    base.py            # InstantonAdapter ABC/Protocol  (§3)
    full.py            # FullInstantonAdapter  (+ CompactionFunction)
    slow_roll.py       # SlowRollInstantonAdapter (+ CompactionFunction)
    gradient.py        # GradientCoupledAdapter (adds the SpatialAdapter mixin)

  figures/
    time_history.py    # field/response-vs-N (the 2x2 instanton_fields family)
    noise.py           # sigma_* vs N
    compaction.py      # zeta(r), C(r), C_bar(r)
    sweeps.py          # msr_action & compaction summary vs swept axis
    doe.py             # DOE scalar scatter families
    spatial.py         # NEW: (y,N) heatmaps, y-slices/N-slices, movies
    diagnostics.py     # NEW: compute-time / convergence / iteration figures
    stability.py       # NEW: overlays vs alpha / n_collocation

plot_InstantonSolutions.py          # thin driver: homogeneous (FI/SR/CF)
plot_GradientCoupledSolutions.py    # thin driver: gradient-coupled (+ overlay)
```

`plot_InstantonSolutions.py` shrinks to an orchestration file that imports
`plotting.*`, builds `FullInstantonAdapter`/`SlowRollInstantonAdapter`
instances, and hands lists of them to `plotting.figures.*`. Its scientific
output is byte-for-byte the same; this is the regression guard (see §9).

---

## 3. The adapter layer — the linchpin

> *"Is it worth writing the plotting code against an 'adapter' class that can
> abstract away the exact origin of the data?"* — Yes. It is the single most
> load-bearing decision here.

### 3.1 What the adapter normalises

The three solvers expose the *same physics* through *different attribute
vocabularies*:

| Concept                | FullInstanton            | SlowRollInstanton | GradientCoupledInstanton                        |
|------------------------|--------------------------|-------------------|-------------------------------------------------|
| field vs N             | `v.phi1`                 | `v.phi`           | `v.phi[node]` (2‑D; core node `-1` is analogue) |
| field velocity vs N    | `v.phi2`                 | — (slaved)        | `v.pi[node]`                                     |
| response fields        | `v.P1`, `v.P2`           | `v.P1`            | `v.rfield[node]`, `v.rmom[node]`                 |
| noise σ vs N           | `noise_profile_arrays()` | same              | derived from `rfield`/`rmom` + diluted D        |
| MSR action             | `msr_action`             | `msr_action`      | `msr_action`                                     |
| radial ζ/C profile     | `CompactionFunction.full_values` | `.slow_roll_values` | `.profile` (ζ/r_ratio/C/r_phys) + `zeta_C_r_at_time` |
| scalar summaries       | via CompactionFunction   | via CF            | via `.profile` + `diagnostics["scale_assignment"]` |
| diagnostics blob       | `diagnostics`            | `diagnostics`     | `diagnostics`                                    |

A figure function must never see the middle three columns. It should see one
interface. That interface is `InstantonAdapter`.

### 3.2 Base protocol (solver-agnostic core)

```python
class InstantonAdapter(abc.ABC):
    # ── identity / provenance ────────────────────────────────────────────
    kind: str                 # "full" | "slow-roll" | "gradient-coupled"
    display_label: str        # "Full", "SR", "GCI (n=24, α=0.1)"
    line_style: str           # default mpl style for this kind ("-", "--", ":")

    @property def available(self) -> bool: ...
    @property def failure(self)   -> bool: ...
    @property def store_id(self)  -> int | None: ...
    @property def timestamp(self): ...
    @property def coords(self) -> dict: ...
        # {"N_init", "N_final", "delta_Nstar", and for GCI "alpha",
        #  "n_collocation_points"} — grid coordinates, floats. Supplied at
        #  construction from the query context, NOT scraped off the object,
        #  so it works even for do_not_populate fetches.
    @property def tolerances(self) -> tuple: ...   # (atol, rtol)

    # ── capability query ─────────────────────────────────────────────────
    def has_channel(self, name: str) -> bool: ...
        # "phi","velocity","rfield","rmom","noise_field","noise_mom", ...
    def is_spatial(self) -> bool: ...              # True only for GCI

    # ── 1‑D time histories (the homogeneous, on-axis story) ──────────────
    def time_history(self, channel: str) -> tuple[np.ndarray, np.ndarray] | None:
        # returns (N, values). For GCI this is the CORE node (y=+1), i.e. the
        # bubble-centre trajectory — the direct analogue of FI's homogeneous
        # field. Returns None if the channel is absent (e.g. "velocity" for SR).

    def noise_history(self) -> dict | None:
        # {"N", "sigma_field", "sigma_mom"} with NaN where a channel is None.
        # For FI/SR this wraps noise_profile_arrays(); for GCI it is built from
        # rfield/rmom + diluted diffusion coefficients at the core node.

    # ── derived radial profile (ζ, C, optionally C̄, in Mpc) ─────────────
    def radial_profile(self) -> dict | None:
        # {"r_Mpc", "zeta", "C", "C_bar"}.
        # FI/SR: read straight off CompactionFunction.full/slow_roll_values.
        # GCI:  read straight off .profile once C_bar is added to it upstream
        #        (§7.3); r_Mpc = r_ratio * r_phys_out. A PURE READ — no physics
        #        in the adapter (see §7).

    # ── uniform scalar summaries (for sweeps & DOE) ──────────────────────
    def scalars(self) -> dict:
        # A single flat dict with a fixed key vocabulary shared by ALL kinds,
        # matching CompactionFunction's exposed set (§7.1):
        #   msr_action, C_peak, C_bar_peak, C_min, compensated, type_II,
        #   r_max_Mpc, r_peak_Mpc, M_max_solar, M_peak_solar,
        #   V_end_downflow, N_end_downflow, noise_field_mean, ...
        # For GCI these are PURE READS of the new persisted columns (§7.2),
        # so the values are identical-by-construction to CompactionFunction's.
        # Sweep/DOE figures never branch on kind — only on which keys are None.

    # ── diagnostics blob (uniform across kinds) ──────────────────────────
    def diagnostics(self) -> dict | None: ...
```

### 3.3 Spatial extension (GCI-only)

Figures that need the `(y,N)` field or time-resolved derived profiles ask for
the richer interface and skip the target if it isn't spatial:

```python
class SpatialAdapter(InstantonAdapter):
    @property def y_nodes(self) -> np.ndarray: ...         # LGL nodes, -1..+1
    @property def N_grid(self)  -> np.ndarray: ...         # stored sample N's

    def field_2d(self, name: str) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
        # name in {"phi","pi","rfield","rmom"} → (y, N, Z[N,y]); requires the
        # dense Value rows (store_full_values / full-populate fetch).

    def derived_at_time(self, N_query) -> dict:
        # wraps GradientCoupledInstanton.zeta_C_r_at_time(); returns
        # {"N","zeta","r_ratio","C","r_phys"}. Backed by the ExtractionCache,
        # so repeated frames in a movie are cheap after the first.
```

Usage in a figure function is a one-liner guard:

```python
spatial = [a for a in adapters if a.is_spatial() and a.available]
if not spatial:
    return   # nothing to render on a (y,N) figure
```

### 3.4 Why this makes overlay free

Every science figure function takes `adapters: list[InstantonAdapter]` and
loops:

```python
for a in adapters:
    if not (a.available and not a.failure):
        continue
    N, phi = a.time_history("phi")
    ax.plot(N, phi, a.line_style, label=a.display_label)
```

Overlaying GCI-core vs FI vs SR on one axis is then just *passing a longer
list*. The homogeneous driver passes `[full, sr]`; the GCI driver passes
`[gci, full, sr]` (or `[gci_n24, gci_n32, gci_n48]` for a convergence overlay).
No figure function ever learns there is more than one solver.

---

## 4. Data-fetch layer (`plotting/fetch.py`)

Keep the proven pattern from the current script — **pre-fetch on the driver,
bin by shard key (`delta_Nstar`), one `object_get_vectorized` per shard, then
serialise plain args into Ray render tasks** — but generalise the payload so it
carries the GCI key fields.

The GCI datastore lookup key (from the factory) is:

```
trajectory, N_init, N_final, delta_Nstar (shard key),
n_collocation_points, alpha_regularization, atol, rtol,
cosmo, diffusion_model            [+ optional N_sample, tags, label]
```

So `fetch.py` gains a `gci_key_payload(...)` alongside the existing
`_instanton_key_payload` / `_cf_key_payload`, and the binning key stays
`delta_Nstar`. A generic

```python
def fetch_over_grid(pool, class_name, shard_key_of, key_payload_of,
                    items, do_not_populate=True) -> list: ...
```

subsumes the three hand-rolled vectorized-fetch loops
(`_sweep_*`, `_generate_instanton_samples`, `_collect_doe_scalar_data`), each of
which currently re-implements the same bin→dispatch→realign dance.

**Cost/fidelity tiers (important for scheduling work):**

| Tier                    | Fetch                              | Cost   | What it unlocks |
|-------------------------|------------------------------------|--------|-----------------|
| scalars + diagnostics   | `_do_not_populate=True`            | cheap  | sweeps, DOE, **all diagnostics figures** |
| final-row ζ/C profile   | full-populate                      | medium | compaction-profile plot (§7) |
| dense `(y,N)` grid      | full-populate, `store_full_values` | heavy  | 2‑D heatmaps, movies, time-resolved derived |

The diagnostics blob rehydrates **even in the cheap tier** (it lives on the
parent row, not in the child value tables), so the diagnostics figures cost
essentially nothing extra on top of the DOE scalar pass — fold them in there
(§8).

### 4.1 The `profile_only` fetch mode and its method contract

Today `build()` calls `_populate` **and** `_populate_profile` together, only when
`not do_not_populate`, and that path *raises* if the record was stored
scalars-only. So the "always-persisted" ζ/C/r_phys profile is in practice only
*readable* via a full fetch that also drags the dense `(y,N)` grid — the medium
tier isn't actually medium. Fix: add a `profile_only=True` build path that loads
`GradientCoupledInstantonProfile` **without** the dense `Value` rows and
**without** tripping the "dense values were never stored" guard.

This is a ~10-line factory change, but — as you flagged — the care is in getting
the method return-vs-raise behaviour right across the resulting **three fetch
modes** crossed with **two storage states**. The contract the methods must
honour:

| Method / property        | `do_not_populate` | `profile_only`     | full (dense-stored)  | full (scalars-only stored) |
|--------------------------|-------------------|--------------------|----------------------|----------------------------|
| scalars (`msr_action`, `C_peak`, `M_*`, `r_*`, `noise_*`, `C_bar_peak`, …) | ✅ value | ✅ value | ✅ value | ✅ value |
| `diagnostics`            | ✅ value           | ✅ value           | ✅ value             | ✅ value |
| `profile` (ζ/C/C̄/r)     | `[]` (empty)      | ✅ populated       | ✅ populated         | ✅ populated |
| `values` (dense y,N)     | `[]` (empty)      | `[]` (empty)       | ✅ populated         | **build() raises** (as today) |
| `radial_profile()` (adapter) | `None`        | ✅                 | ✅                   | ✅ |
| `field_2d(name)`         | raise             | raise              | ✅                   | n/a (never loads) |
| `zeta_C_r_at_time(N)`    | raise             | raise              | ✅                   | n/a |

The invariants that make this coherent:

1. **`profile` populated ⟺ profile rows were loaded** — true under `profile_only`
   and full; empty under `do_not_populate`. It is never gated on dense-value
   presence (profile rows persist unconditionally).
2. **`values` populated ⟺ dense rows were both stored and loaded** — full fetch
   of a dense-stored record only.
3. **`zeta_C_r_at_time` / `field_2d` require `_values`** — they already guard on
   `if not self._values: raise RuntimeError(...)`. Keep that guard *as the single
   source of truth*; it then does the right thing automatically in `profile_only`
   (empty `_values` → raises), so no new mode flag leaks into those methods.
4. **The scalars-only-storage guard stays on the *full* path only.** A
   `profile_only` fetch of a scalars-only-stored record must **succeed** (that is
   its whole purpose: read the profile without the dense grid). So the
   `full_values_stored is False` → raise check moves to be conditional on "dense
   values were requested", not "not do_not_populate".

The adapter cooperates by carrying a `fidelity` tag (`"scalars"` /
`"profile"` / `"dense"`) set from the fetch mode, and `is_spatial()` returns
`True` only when `fidelity == "dense"` — so spatial figures skip a
profile-only adapter cleanly instead of letting `field_2d` raise mid-render.
Getting these cells right is exactly the kind of thing to write into the
implementation prompt as this explicit table, not leave to inference.

---

## 5. Ray-dispatch layer (`plotting/dispatch.py`)

The current design (each figure has its own `@ray.remote _plot_*_item`) is
boilerplate. Collapse to **one** generic remote:

```python
@ray.remote
def _render_item(figure_fn, payload, output_dir_str, fmt, run_label):
    sns.set_theme()
    figure_fn(payload, Path(output_dir_str), fmt, run_label=run_label)
```

where `payload` is whatever the figure function needs (usually a list of
lightweight adapters + coords). The `(remote_fn, args)` work-item convention and
the terminal `RayWorkPool(..., store_results=False)` drain stay exactly as they
are in `run_plots` now — that part is solid.

**One caveat for spatial work items.** The `(y,N)` arrays and the
`zeta_C_r_at_time` recompute are large / expensive. Do **not** serialise big
arrays through the work queue. Instead pass the `GradientCoupledInstantonProxy`
(cheap `ray.put` handle) into the render task and do the `.get()` +
`field_2d()` / `derived_at_time()` **inside** the worker. Movies especially
should render frame-by-frame worker-side and emit only the finished file.

---

## 6. Figure inventory

### 6.1 Reused as-is (now adapter-fed, overlay-capable)

- **time_history** — the 2×2 `{φ, velocity, response₁, response₂}` vs N.
  For GCI the panels show the **core node (y=+1)** trajectory, captioned as such,
  so it lines up conceptually with FI's homogeneous saddle. Overlay GCI-core +
  FI + SR to see how spatial coupling shifts the centre-of-bubble history.
- **noise** — σ vs N, unchanged shape.
- **compaction** — ζ(r), C(r), C̄(r) vs r/Mpc. All three solvers on one axis,
  as pure reads once GCI carries C̄ and the full scalar set upstream (§7).
- **sweeps** — `msr_action` and compaction-summary vs a swept axis. Now the
  swept axis can be `N_init`, `N_final`, `delta_Nstar`, **`alpha`**, or
  **`n_collocation_points`** (§7.4). The mass/radius panels now include GCI
  because those scalars are persisted upstream (§7.1).
- **doe** — scalar scatter families. Markers already encode solver
  (`o` = full, `^` = SR); add a third marker for GCI.

### 6.2 New: spatial `(y,N)` figures (`figures/spatial.py`)

Two tiers, default = static, movies opt-in:

1. **Heatmaps** — `pcolormesh` over (N, y) for each of φ, π, r_φ, r_π. A 2×2
   panel. Cheap, publication-ready, and carries provenance in the footer. This
   is the primary "is the solution smooth / instability-free" diagnostic.
2. **Slice overlays** — companion to the heatmap and often more legible for
   spotting ringing: a few N-slices (profile vs y at selected e-folds) and a few
   y-slices (history vs N at selected shells: edge, mid, core). These also
   overlay cleanly against FI/SR where an analogue exists (core y-slice vs FI
   homogeneous field).
3. **Movies (opt-in `--movies`)** — `FuncAnimation` → mp4/gif. Frame = profile
   vs y (or vs r) sweeping through N, or vs N sweeping through y. Provenance is
   burned into a persistent per-frame footer + an opening title card, since a
   movie can't carry a static caption. Gate on the dense tier being available
   and behind the flag because it is the most expensive output by far.

### 6.3 New: derived-at-time figures

ζ(y)→ζ(r) and C(r) at N_final come from the persisted profile (cheap-ish, §4
caveat). ζ/C **as functions of `(y,N)`** are *not persisted* — they come from
`zeta_C_r_at_time` (recompute + ExtractionCache). Offer:

- a static "ζ(r) and C(r) at a few selected N" panel (a handful of cache calls),
  and
- optionally a ζ(r)/C(r) **movie** through N (many cache calls — the cache is
  what makes this affordable). Same opt-in flag as §6.2.

### 6.4 New: stability / convergence figures (`figures/stability.py`)

Directly serves *"see that outputs are stable as α and n_collocation change."*
These are **overlay sweeps** reusing §3.4:

- Fix `(N_init, N_final, δN*)`, sweep `n_collocation_points` ∈ {…}; overlay
  ζ(r)/C(r) and the core-node histories; report `max|Δ|` between successive
  resolutions as an inset or annotation → spectral-convergence evidence.
- Same for `alpha` (outer-boundary regularisation): overlay and show that the
  persisted scalars (`C_peak`, `r_max`, `M_max`, …) and the profile are
  insensitive across the α range.
- A scalar-vs-axis panel: `C_peak`, `msr_action`, `r_max`, `M_max` vs
  `n_collocation` (and vs α) with the other axes fixed — the "plateau" plot that
  demonstrates convergence at a glance. These read the same persisted columns the
  DOE pass uses, so the stability figures cost nothing beyond the cheap fetch.

---

## 7. Science-scalar parity — an upstream compute-target requirement

This section replaces the earlier "reconstruct in the adapter, skip if awkward"
framing. `M_PBH`, `r_PBH` (and the compaction quantities that classify them) are
**primary science targets**, not plotting conveniences. That GCI does not
currently produce them is an **oversight to fix upstream**, not a design choice
to work around downstream. So the requirement is explicit:

> **`GradientCoupledInstanton` must persist and expose at least the full set of
> science scalars that `CompactionFunction` persists and exposes** — computed by
> the *same* code, so the two paths are numerically identical by construction —
> and the plotting adapter then simply reads them off, exactly as it does for
> `CompactionFunction`.

### 7.1 The exact scalar set (verified against `CompactionFunction`)

`CompactionFunction` exposes each of the following **per path** (a `_full` and a
`_slow_roll` copy). GCI is a single solver, so it needs **one unsuffixed copy of
each**:

| Scalar               | Meaning                                             | How `CompactionFunction` derives it |
|----------------------|-----------------------------------------------------|-------------------------------------|
| `C_peak`             | max of `C(r)` (`C_max`)                             | `nanmax(C_v)` |
| `C_bar_peak`         | max of `C̄(r)` (`C_bar_max`)                        | `nanmax(C_bar_v)` |
| `C_min`              | min of `C(r)`                                        | `nanmin(C_v)` |
| `compensated`        | bool: `C_min < 0`                                    | shape classification |
| `type_II`            | bool: `C_min < -1`                                   | shape classification |
| `r_max`              | outermost r where `C ≥ C_threshold`                 | `_classify_radii(r, C, thr)` — **on unbarred C** |
| `r_peak`             | r at `argmax C`                                      | `_classify_radii(r, C, thr)` |
| `M_max`              | PBH mass at `r_max`                                  | `(1+C_max)·5.6e15·(k*·r_max)²·M_⊙`, `k*=0.05/Mpc` |
| `M_peak`             | PBH mass at `r_peak`                                 | `(1+C_max)·5.6e15·(k*·r_peak)²·M_⊙` |
| `V_end_downflow`     | potential at the downflow endpoint                  | from the per-path noiseless downflow |
| `N_end_downflow`     | downflow duration to ε=1                             | from the per-path noiseless downflow |

Plus the shared `C_threshold`, and the profile arrays `{r, zeta, C, C_bar}`
(already `.profile` for GCI, but **missing `C_bar`** today — see §7.3).

**Two corrections to the assumptions in the brief:**

1. **There is no "barred" `M_PBH` / `r_PBH`.** `_classify_radii` is called
   **once, on the unbarred `C(r)`** (`CompactionFunction.py:360`), and the mass
   formula uses `C_max` (unbarred). So `r_max/r_peak/M_max/M_peak` are all
   unbarred-C quantities; there is no `r_max_bar` / `M_max_bar` to match. C̄
   enters the persisted scalars **only** as `C_bar_peak`, plus the `C_bar(r)`
   profile array — consistent with your note that C̄ is now information-level and
   drives no observable. So "C(r) and C̄(r), plus bar/unbar M/r" over-counts on
   the M/r side and under-counts on the scalar side.

2. **The set is wider than `{C_peak, C_bar_peak, r_max/peak, M_max/peak}`.**
   `C_min`, `compensated`, `type_II`, `V_end_downflow`, `N_end_downflow` are also
   persisted and exposed. Since the requirement is "at least all of
   `CompactionFunction`'s", GCI should carry these too. `C_min`/`compensated`/
   `type_II` are the type-II / compensated-profile classifiers and are cheap
   by-products of already having `C(r)`; the two downflow bookkeeping scalars
   need a single representative value chosen from GCI's per-node downflow (§7.3).

### 7.2 Where the computation lives, and how identity is guaranteed

Do **not** recompute any of this in the plotting adapter. Instead:

1. **Factor the shared physics out of `CompactionFunction`'s worker** into a
   small module (e.g. `ComputeTargets/compaction_scalars.py`) exposing the exact
   routines `CompactionFunction` uses today: the C̄ running-integral, the
   `_classify_radii` call (already shared), the PBH-mass relation (with its
   `k*=0.05/Mpc` and `5.6e15` constants), and the `C_min`/`compensated`/`type_II`
   classification. `CompactionFunction` is refactored to call these (no numeric
   change — guard with an output diff), and GCI's worker calls the **same**
   functions. This is the codebase's own stated principle ("reuse
   `ln_k_phys_Mpc`/`_classify_radii` rather than reimplement") extended to the
   rest of the scalar set. Identity is then structural, not a testing aspiration.
2. **Compute them in `_compute_gradient_coupled_instanton`**, right after
   `assign_scales` (GCI already has `C(r)` via the profile and `r_phys`; it is
   missing only C̄, the mass, and the classifiers — all now shared helpers).
   Return them in the result dict.
3. **Persist as first-class columns** on the `GradientCoupledInstanton` table
   (they are parent-row scalars, so the validate/cascade-delete of child value
   rows is unaffected), and **rehydrate in the factory's `build()`** alongside
   the existing `msr_action`/`noise_*` columns — and, crucially, in the
   `_do_not_populate` path too, so the DOE/sweep/regression passes get them from
   the cheap fetch. This mirrors exactly how `msr_action` and the `noise_*`
   scalars are already handled.

**One fidelity note.** `CompactionFunction` classifies and integrates C̄ on a
**dense r-grid** (a spline densification of the profile), whereas GCI's raw
`C(r)` lives on ~`n_collocation_points` LGL nodes. To keep the numbers
comparable (and stable as `n_collocation_points` varies — the very thing the
stability figures test), densify the GCI profile onto the same style of dense
r-grid *inside the shared helper* before classification/integration, rather than
running `argmax`/threshold on the sparse node set. `scale_assignment` currently
does node-level `_classify_radii`; moving to the shared dense-grid path makes GCI
and `CompactionFunction` agree and removes an n-dependence artefact.

### 7.3 Two specific sub-decisions

- **`C_bar(r)` in the profile.** Add `C_bar` to
  `GradientCoupledInstantonProfileValue` (and its table column) so the profile is
  a full `{zeta, r_ratio, C, C_bar, r_phys}` record, matching
  `CompactionFunctionValue`'s `{r, zeta, C, C_bar}`. Computed by the same C̄
  helper. This is a schema change to the always-persisted profile table.
- **`V_end_downflow` / `N_end_downflow` for GCI.** `CompactionFunction` has a
  single downflow (per path); GCI downflows **per node** in `extraction.py`
  (`phi_end_downflow`, `N_end_downflow` are per-node arrays). Choose the
  representative consistent with the mass classification: the value at the
  **`r_peak` node** (the shell that sets `C_max`/the mass), so the scalar means
  the same thing it does for `CompactionFunction`. Document the choice in the
  worker.

### 7.4 New sweep axes (α, n_collocation)

Independently of the parity work: `build_pipeline_inputs` mints only
`N_init/N_final/delta_Nstar`. Add minted arrays for `alpha_regularization` and
`n_collocation_points` (recommend a GCI-specific `build_gci_inputs` so
`main.py`'s inputs stay untouched), from new CLI args (`--alpha-*`,
`--n-collocation-*`, mirroring the `--delta-Nstar-*` low/high/samples/values
quartet). The sweep scaffolding already generalises over "swept axis + fixed
others"; α and n_colloc slot in as two more axes. `delta_Nstar` **remains the
shard key**, so binning is unaffected.

### 7.5 Consequence for the adapter

With parity done upstream, `GradientCoupledAdapter.scalars()` and
`.radial_profile()` become **pure reads**, structurally identical to the
`CompactionFunction`-backed adapters — no physics in the plotting layer, no
"optional / skip if absent" special-casing for M/r/C̄. The `scalars()` key
vocabulary in §3.2 is now populated identically for all three solvers, so the
DOE and sweep figures need no per-kind branches at all.

---

## 8. Diagnostics as first-class output (`figures/diagnostics.py`)

> *"build this functionality into the driver, so that we produce visualisations
> of this diagnostic metadata at the same time as the science outputs."*

Every solver's `diagnostics` blob rehydrates on the cheap scalar fetch, and the
adapter exposes it uniformly via `.diagnostics()`. So run a **single diagnostics
collection pass fused with the DOE scalar pass** (same shard-binned vectorized
fetch already happening in `_collect_doe_scalar_data`), and emit a
`diagnostics/` figure family. The compute-times figure you attached
(`instanton_compute_times-1.png`) becomes *one* function in this family, fed by
adapters instead of FI-specific code.

GCI diagnostics keys available (from `picard.py` / the compute target):

- convergence: `converged`, `final_residual`, `outer_iterations`,
  `newton_fallback_count`, `final_lambda`
- iteration structure: `picard_iterations_per_outer`,
  `{min,max,mean}_picard_iterations`, `mean_time_per_picard_iteration`
- cost: `total_ode_solves`, `compute_time`, `compute_time_total`
- RK45 stiffness: `rk45_{forward,backward}_{total,accepted,rejected}_steps`,
  `_{min,max}_step`, `_steps_per_efold`
- sweep timing: `picard_sweep_wallclock_{min,mean,max}`
- scale assignment: `scale_assignment.{r_max,r_peak,r_phys_out,...}`
- extraction health: `extraction_failure_mask` (per-node — a *spatial* health
  map: which shells failed ζ extraction, vs y)

Proposed diagnostics figures (all solver-agnostic via the adapter):

1. **Compute-time distributions** per solver (converged vs non-converged),
   medians — the image‑8 top row, generalised.
2. **Cost vs parameters** — compute-time and `total_ode_solves` vs δN★ and ΔN,
   binned means/heatmaps (image‑8 middle/bottom).
3. **Convergence map in parameter space** — converged/non-converged scatter over
   (δN★, ΔN); for GCI add facets over α and n_colloc.
4. **Speed-up** — GCI vs FI vs SR compute-time ratios where the same grid point
   exists in more than one solver (image‑8 right column), now a genuine
   cross-solver comparison because the adapters share coords.
5. **Picard/Newton structure** — outer-iteration and Picard-iteration-count
   distributions; Newton-fallback frequency vs where in parameter space.
6. **Stiffness** — RK45 steps-per-efold, forward vs backward, vs δN★ (the
   backward/adjoint direction is where growth modes bite — this is the plot that
   tells you if the sinh-transform is holding up).
7. **Extraction-failure map** — fraction of failed shells vs (grid point), and a
   per-node (vs y) failure heatmap for individual solves — a spatial health
   check unique to GCI.

Also emit `diagnostics_data.csv` next to `scalar_data.csv`, so the existing
`regression_InstantonOutputs.py` GP-driver (or a sibling) can consume solver
cost/convergence as regression targets the same way it consumes C_max / M_PBH.

---

## 9. Provenance (keep and extend)

`_provenance_footer` and the `_add_cf_annotation` / run-label machinery move to
`plotting/provenance.py` essentially unchanged, with three extensions:

1. **New coordinate fields.** The footer's attribute introspection should pick
   up `alpha` and `n_collocation_points` for GCI, and every per-instanton figure
   should stamp the full coordinate tuple (`N_init, N_final, δN★, α, n_colloc`)
   into the title/annotation so a detached PNG is still self-describing — the
   current figures already do this for the first three.
2. **Code version + git SHA.** Extend the `StochasticInstanton vX.Y.Z` stamp
   with a short git SHA when available (fallback: version only), so a figure ties
   back to an exact commit.
3. **Movie provenance.** Static footers don't survive animation, so movies get a
   persistent per-frame footer line plus an opening title card carrying the same
   version/timestamp/coords string.

The `run_label` second line (db filename, config, mode flags like
`[summary-only]`) already does the "which run produced this" job — keep it,
and add the fidelity tier (`[scalars-only]` / `[full-fidelity]` /
`[with-movies]`) to it.

---

## 10. Driver front-ends

**`plot_GradientCoupledSolutions.py`** mirrors `run_plots`:

1. `build_pipeline_inputs` (+ new α / n_colloc arrays), fetch trajectories,
   cosmo, diffusion model.
2. For each trajectory:
   - **scalar+diagnostics pass** (cheap tier) over the full grid → DOE figures,
     diagnostics figures, `scalar_data.csv`, `diagnostics_data.csv`.
   - **sweep passes** over each axis (N_init, N_final, δN★, α, n_colloc) →
     msr/compaction summaries + the new stability overlays.
   - **detailed-sample pass** (`--max-instanton-samples`) over an evenly-sampled
     subset → time_history, noise, compaction, and the new spatial heatmaps /
     slices; movies only if `--movies`.
3. Drain the work queue exactly as now.

**Cross-solver mode.** A `--compare-with full,slow-roll` flag makes the detailed
and sweep passes additionally fetch the matching FI/SR (and CF) at each sampled
grid point, wrap them as adapters, and pass the combined list to the shared
figure functions — producing the overlaid figures with zero new plotting code.

**New CLI flags** (all with sensible defaults):
`--alpha-{low,high,samples,values}`, `--n-collocation-{low,high,samples,values}`,
`--movies`, `--movie-format {mp4,gif}`, `--compare-with`, `--spatial-samples`
(how many grid points get the heavy `(y,N)` treatment),
`--time-resolved-derived` (enable ζ/C(y,N) recompute figures).

---

## 11. Suggested build order

There are **two tracks**. The plotting track (P) can start immediately; the
science overlays in it depend on the upstream track (U) landing first.

**Track U — upstream compute-target work (§7), a prerequisite for science parity.**
This is *not* plotting; it is compute-target + factory + schema change, and it is
what actually makes `M_PBH`/`r_PBH` come out of GCI.

- **U1. Factor shared compaction scalars.** Extract C̄-integral, PBH-mass
  relation, `_classify_radii` (already shared), and `C_min`/`compensated`/
  `type_II` classification into `ComputeTargets/compaction_scalars.py`. Refactor
  `CompactionFunction` to call them. Acceptance: `CompactionFunction` output
  byte-identical to a golden run (pure refactor).
- **U2. Compute the parity set in GCI.** Call the shared helpers in
  `_compute_gradient_coupled_instanton` after `assign_scales`; add `C_bar` to the
  profile; pick the downflow representative (§7.3); densify the profile for
  classification (§7.2 fidelity note). Acceptance: on a case where a GCI and an
  FI share a grid point in a regime they should agree, the scalar set matches to
  tolerance.
- **U3. Persist + rehydrate.** New scalar columns + profile `C_bar` column;
  rehydrate in `build()` including the `_do_not_populate` path. Acceptance:
  round-trip store→load returns identical scalars; scalars present on a cheap
  fetch.

**Track P — plotting.**

1. **Extract, no behaviour change.** Move concerns 2–4 into `plotting/`
   (dispatch, provenance, sampling, fetch). Re-point `plot_InstantonSolutions.py`
   at them. Diff output against a golden run — must be identical. *Safety net for
   everything after.*
2. **Introduce the adapter.** Add `InstantonAdapter` + `FullInstantonAdapter` /
   `SlowRollInstantonAdapter`; convert figure functions to consume
   `list[InstantonAdapter]`. Re-diff. No new science.
3. **`profile_only` fetch mode.** Implement the §4.1 three-mode contract in the
   factory + method guards. Acceptance: the behaviour table in §4.1 holds for all
   cells (unit-test each).
4. **Gradient adapter.** Add `GradientCoupledAdapter` / `SpatialAdapter`. Once
   **U3** has landed, the homogeneous figures accept GCI for free (time history,
   noise, compaction, sweeps, DOE) as pure reads — no reconstruction.
5. **Spatial figures.** Heatmaps + slices; then movies behind the flag.
6. **Stability figures.** α / n_colloc overlays and plateau plots.
7. **Diagnostics figures.** Fuse the collection pass into the DOE pass; port the
   compute-times figure to the adapter and add the GCI-specific ones.
8. **New driver + compare mode.** Wire `plot_GradientCoupledSolutions.py` and the
   `--compare-with` overlay path.

Dependency: **P4 needs U3.** P1–P3 and U1–U3 are independent and can proceed in
parallel. P1, P2, U1 are pure refactors gated by output-equality; the rest are
additive. The adapter and the `plotting/` split mean the homogeneous and GCI
drivers never diverge in their shared machinery again.

---

## 12. Open questions to settle before coding

Resolved by the discussion, now baked into the design (§7): science-scalar parity
is done **upstream** in the GCI compute target/factory, not reconstructed in the
adapter; and there is **no barred `M_PBH`/`r_PBH`** to match. Remaining genuinely
open points:

- **Downflow-scalar representative (§7.3):** confirm that the `r_peak`-node
  downflow is the right single value for GCI's `V_end_downflow`/`N_end_downflow`
  (vs, say, the core node). Low stakes — these two are bookkeeping/diagnostic
  scalars, not observables — but pick one and document it.
- **Densification for GCI classification (§7.2):** confirm the shared helper
  should densify GCI's node-level profile onto a dense r-grid before
  `argmax`/threshold/C̄-integration (recommended, to match `CompactionFunction`
  and remove n-dependence), rather than classifying on the raw LGL nodes as
  `scale_assignment` does today. This slightly changes GCI's existing
  `diagnostics["scale_assignment"]` `r_max/r_peak` — acceptable, but a knowing
  change.
- **Profile-only guard relocation (§4.1):** the `full_values_stored is False`
  raise must move from "not do_not_populate" to "dense values requested" so a
  `profile_only` fetch of a scalars-only record succeeds. Confirm no other
  caller depends on the current (broader) raise.
- **Movie dependency:** `matplotlib.animation` needs `ffmpeg` for mp4. Confirm
  it's on the render nodes, or default `--movie-format gif` (Pillow-only) and
  treat mp4 as opt-in.
- **α / n_colloc axis home:** recommend a separate `build_gci_inputs` over
  extending `build_pipeline_inputs`, to keep `main.py`'s inputs untouched.
