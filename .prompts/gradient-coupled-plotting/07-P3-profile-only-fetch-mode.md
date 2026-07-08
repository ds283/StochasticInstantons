### Prompt P3 — `profile_only` fetch mode + the three-mode method contract

- **Implements:** design §4.1 in full.
- **Track / step:** P3
- **Depends on:** P1 (no code dependency on P2, but authored after it in
  this build order; safe to execute in parallel with P2 if needed since it
  touches a disjoint file)
- **Files (real paths):**
  - edit: `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`
    (`sqla_GradientCoupledInstantonFactory.build`, specifically the
    `if not do_not_populate:` block and everything that reads it)
  - edit: `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`
    (only the `field_2d`/`zeta_C_r_at_time`-style guards — confirm their
    exact current guard condition, `if not self._values: raise RuntimeError(...)`,
    is what you find, and leave it as the single source of truth per
    invariant 3 below; do not add a second, separate mode flag anywhere in
    this class)
- **Context to read first:** `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`'s
  `build()`, `_populate()`, `_populate_profile()` in full, and its `store()`
  (to see exactly how `full_values_stored` gets written into
  `diagnostics_json` on a scalars-only-mode store); design §4.1 in full
  (read the whole section — the behaviour table and its four invariants are
  the spec for this prompt, verbatim).
- **Assumable interfaces:** the current `build()` behaviour, stated exactly
  so you can see what must change: today, `build()` takes a single
  `do_not_populate` flag from `payload.get("_do_not_populate", False)`. When
  `False` (i.e. "populate"), it does two things unconditionally together:
  (a) raises `RuntimeError` if
  `obj._diagnostics.get("full_values_stored", True) is False` (the
  scalars-only-storage guard), then (b) calls both `self._populate(obj, ...)`
  (loads dense `GradientCoupledInstantonValue` rows into `obj._values`) and
  `self._populate_profile(obj, ...)` (loads `GradientCoupledInstantonProfile`
  rows into `obj._profile`) together. There is currently no way to load the
  profile without also attempting to load — and raising on the absence of —
  the dense values.
- **Task:** implement exactly the §4.1 table. Concretely:
  1. In `build()`, read a new `profile_only = payload.get("_profile_only", False)`
     flag alongside the existing `do_not_populate`.
  2. Change the branching so there are three mutually exclusive paths:
     - `do_not_populate=True` (regardless of `profile_only`): neither
       `_populate` nor `_populate_profile` is called; `obj._values == []`,
       `obj._profile == []`. Scalars and `diagnostics` still rehydrate from
       the row unconditionally, exactly as today.
     - `profile_only=True` and `do_not_populate=False`: call
       `_populate_profile` only. **Do not** call `_populate`. **Do not**
       raise the `full_values_stored is False` check — that check moves so
       it only fires when dense values are actually being requested (see
       invariant 4 below).
     - both `False` (today's "full populate" path): call both `_populate`
       and `_populate_profile`, and **keep** the `full_values_stored is False`
       raise exactly as today, since this is the path that requests dense
       values.
  3. Relocate the `full_values_stored is False` raise so its condition is
     "dense values were requested" (i.e. `not do_not_populate and not profile_only`)
     rather than "not do_not_populate" — per invariant 4, this is what makes
     a `profile_only` fetch of a scalars-only-stored record succeed instead
     of raising.
  4. Confirm (read the code, don't assume) that `field_2d`/
     `zeta_C_r_at_time`'s existing `if not self._values: raise RuntimeError(...)`
     guard is untouched and remains the single source of truth for those two
     methods — per invariant 3, `profile_only`'s empty `_values` will
     automatically make them raise correctly with no new flag needed there.
- **Constraints:** follow the conventions checklist; plus: paste this exact
  table into the implementation as a comment above the `build()` branching,
  so the contract is legible in the source, not just in this prompt:

  | Method / property | `do_not_populate` | `profile_only` | full (dense-stored) | full (scalars-only stored) |
  |---|---|---|---|---|
  | scalars (`msr_action`, `C_peak`, `M_*`, `r_*`, `noise_*`, `C_bar_peak`, …) | ✅ value | ✅ value | ✅ value | ✅ value |
  | `diagnostics` | ✅ value | ✅ value | ✅ value | ✅ value |
  | `profile` (ζ/C/C̄/r) | `[]` (empty) | ✅ populated | ✅ populated | ✅ populated |
  | `values` (dense y,N) | `[]` (empty) | `[]` (empty) | ✅ populated | **build() raises** |
  | `radial_profile()` (adapter, P4) | `None` | ✅ | ✅ | ✅ |
  | `field_2d(name)` | raise | raise | ✅ | n/a (never loads) |
  | `zeta_C_r_at_time(N)` | raise | raise | ✅ | n/a |

- **Must NOT:** change `_populate`'s or `_populate_profile`'s own bodies
  (only which combination of them gets called, and when the raise fires);
  must NOT touch `store()`; must NOT introduce a fourth mode or a
  `fidelity` string anywhere in this file — `fidelity` as a tag string is
  the *adapter's* concept (P4), derived from which of `do_not_populate`/
  `profile_only`/neither was used to fetch, not a new flag threaded through
  the factory itself.
- **Acceptance test:** one unit test per row of the table above (8 cells,
  since `diagnostics` and scalars behave identically across all four
  columns and can share one assertion each) — an exhaustive parametrised
  test, e.g. `tests/test_gci_profile_only_fetch_contract.py`, fixturing both
  a dense-stored and a scalars-only-stored `GradientCoupledInstanton` record
  and asserting the documented return-value-or-raise-type for every
  (method, mode) cell. This is, per the brief, "the highest-value test set
  in the whole plan" — do not abbreviate it.
- **Decision point:** confirm no other caller in the codebase depends on the
  current (broader) raise condition before relocating it (design §12, §4 P3).
  Grep the repo for `GradientCoupledInstanton` construction sites with
  `_do_not_populate` unset/`False` and no `_profile_only` — every such
  existing call site is, by definition, unaffected by the relocation (it
  still hits the "full populate" path with the raise intact); the only
  behavioural change is for **new** callers that pass `_profile_only=True`,
  which don't exist yet. **Recommended default: proceed with the
  relocation as specified above.** Leave a comment at the relocated raise:
  `# DESIGN-DECISION: this raise now fires only when dense (y,N) values are requested (not profile_only), so a profile_only fetch of a scalars-only-stored record succeeds — see design doc §4.1.`
