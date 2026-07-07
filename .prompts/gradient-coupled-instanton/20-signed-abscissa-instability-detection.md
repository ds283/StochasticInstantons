# Prompt 20 — Signed spectral abscissa + RHP eigenvalue count (instability detection)

**Scope:** one commit, amending the `--mode spectrum` path in
`analyze_StiffnessSpectrum.py` (prompt 17). Purely additive: keep every
prompt-17 column; add signed real-part reporting so the sweep detects genuine
(right-half-plane) instability, not just stiffness magnitude. No operator or
scheme change.

## Why

The prompt-17 sweep reports `max_abs_re_lambda` — the *absolute value* of the
largest real part. That discards the sign, and the sign is the entire
question: a spurious `+1500` (an exponentially growing mode) is
indistinguishable from a stable `−1500` under `abs()`. The empirical
`n_collocation_points` threshold study showed the assembled operator is
genuinely unstable near `N_init` — eigenvalues in the right half-plane with
the spectral abscissa growing ∝ `n_max` — which is exactly why implicit
integrators (`Radau`/`BDF`) fail too: they faithfully integrate a semi-
discrete ODE that is itself blowing up. The sweep already computes the
eigenvalues of the correct operator (the assembled forward Jacobian, self-
checked against `forward_rhs` to ~1e-10); it only needs to report the signed
abscissa and count the unstable modes.

## Changes

Operate on the eigenvalues `ev` already computed per `(n_max, alpha, N)`:

- `spectral_abscissa = max(ev.real)` — **signed**. `> 0` ⟺ the semi-discrete
  system has an exponentially growing mode; no time integrator can rescue it.
- `n_rhp = count(ev.real > rhp_tol)`, with `rhp_tol = 1e-6 * max(1, |ev|.max())`
  (relative threshold, scale-robust).
- `growth_efold_time = 1 / spectral_abscissa` when the abscissa is `> 0`,
  else `inf`/`NaN` — the e-fold timescale of the fastest growing mode.
  Directly comparable to `N_total`: `growth_efold_time ≪ N_total` is the
  quantitative statement that the solve cannot survive the initial layer.

Keep `op_norm, max_abs_re_lambda, max_abs_im_lambda, implied_rk45_max_dt`
unchanged. Add a docstring note that `implied_rk45_max_dt` is only a *stability*
step when `spectral_abscissa ≤ 0`; when the abscissa is `> 0` **no** step is
stable (the ODE grows regardless of `dt`) and `growth_efold_time` is the
relevant number.

CSV: append `spectral_abscissa, n_rhp, growth_efold_time` (do not reorder
existing columns; prompt-17 CSVs must stay reproducible).

Self-check line: also print `spectral_abscissa` and `n_rhp` at the check
point, so a glance at the console flags instability immediately.

Optional `--plot` addition: `spectral_abscissa` vs `n_max` at a representative
`(alpha, N)` near `N_init`, with a `y=0` reference line — a positive,
`n`-growing curve is the instability at a glance.

## Expected behaviour (acceptance anchors)

- [ ] Existing columns unchanged; prompt-17 CSVs reproducible.
- [ ] At small Δs (small `N`, e.g. `N≈0.1`, `α=0.1`): `spectral_abscissa` is
  **positive** and **increases monotonically with `n_max`**. Frozen-
  coefficient reconstruction gives magnitudes of order `+50` at
  `n_max=8` rising to order `+10³` at `n_max=32` for Δs≈0.1 — the exact
  values depend on the real background state, so the sign and the
  monotone growth in `n_max` are the acceptance criteria, not the number.
- [ ] `n_rhp > 0` at small Δs and grows with `n_max` (approaching the full
  `2·n_max − 1` at the smallest Δs).
- [ ] At large Δs (production wide-transition regime, `N ≳ 5`):
  `spectral_abscissa` small or non-positive, `n_rhp` small — confirming
  the instability is an initial-layer phenomenon, consistent with the
  empirical blow-up localizing near `N_init`.
- [ ] `growth_efold_time` at small Δs is `≪ N_total` at production `n_max`.

## Notes

- The operator is unchanged from prompt 17 (assembled forward Jacobian); this
  is a reporting/interpretation amendment only.
- This makes the sweep the primary **instability detector** and the natural
  **acceptance test for a future SBP-SAT fix**: after that fix,
  `spectral_abscissa` should be `≤ 0` (up to genuine physical growth) and
  `n_rhp → 0` at all Δs and `n_max`. Capturing a pre-fix baseline now gives a
  clean before/after.

## Out of scope

- Any operator/scheme change (SBP-SAT etc.).
- Attributing the abscissa to advection vs gradient — the adjoint diagnostic
  (18/18a) and the isolated-operator analysis already do this (advection
  boundary closure is the source; the gradient is dissipative/stable).
