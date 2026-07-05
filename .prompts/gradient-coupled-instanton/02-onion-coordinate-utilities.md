# Prompt 02 — Onion coordinate utilities

## Context

Read `./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
(§"The onion coordinate $y$" — search for the labels `eq:rH-definition`,
`eq:rout-alpha`, `eq:y-definition`, `eq:Deltas-init`,
`eq:Deltas-derivative`, `eq:self-adjoint-measure` in the tex source rather
than trusting printed equation numbers, which drift as the document is
edited) before starting.

This prompt builds a small set of pure-function coordinate utilities. Like
prompt 01, this is a standalone, physics-adjacent but not physics-coupled
module: functions take already-evaluated scalars (does the field/momentum
reconstruction and the calls into `AbstractPotential` belong to the
*caller*, not here), so this file has no dependency on `AbstractPotential`,
`InflatonTrajectory`, `DatastoreObject`, or anything Datastore-related, and
is fully testable with synthetic numbers.

**Settled design point, confirmed in discussion — do not build an
absolute-valued $r_H(N)$ or $r_{\rm out}$ anywhere.** Every quantity this
model needs, all the way through to the final scale-assignment step, is
expressible as a ratio relative to $r_{\rm out}$, or as the dimensionless
$\Delta s(N)=\ln(r_{\rm out}/r_H(N))$ itself — never $r_{\rm out}$ or
$r_H(N)$ in absolute physical units. The one place an absolute radius
enters the whole pipeline is `r_phys_out`, computed by the *existing*
Leach–Liddle machinery in a later prompt (`scale-assignment`) — nothing
here.

**Reduction to closed form, worked out and confirmed in discussion —
implement this form directly rather than the more roundabout definitional
chain in the tex:**

$$\Delta s(N) = \ln(1+\alpha) + (N-N_{\rm init}) + \tfrac12\ln\!\left(\frac{H^2_{\rm sq,core}(N)}{H^2_{\rm sq,nl,init}}\right)$$

— using the tautological identity $a(N)/a(N_{\rm init})=e^{N-N_{\rm init}}$
(no separate ODE for $a$), and expressed via $H^2$ (`H_sq`, what
`AbstractPotential` actually returns) rather than $H$, to avoid an
unnecessary square root at every call site. $H^2_{\rm sq,core}(N)$ is the
*current* core state (evaluated at the top collocation node, $y=+1$, at
whatever $N$ the RHS is being evaluated at); $H^2_{\rm sq,nl,init}$ is a
single fixed reference, computed once elsewhere (by the caller) from the
noiseless trajectory at $N_{\rm init}$.

## Task

### `Numerics/OnionCoordinate.py`

Plain functions (no class, no shared state — everything here is
stateless, evaluated fresh at each $N$ by the caller):

```python
def delta_s(N: float, N_init: float, H_sq_core: float, H_sq_nl_init: float, alpha: float) -> float:
    """Delta_s(N), per the closed form above. Raises ValueError if alpha < 0."""

def delta_s_derivative(epsilon_core: float) -> float:
    """d(Delta_s)/dN = 1 - epsilon_core(N)."""

def advection_coefficient(y, delta_s_N: float, epsilon_core: float):
    """A(y,N) = (y+1)/Delta_s(N) * (1 - epsilon_core(N)). y may be scalar or ndarray."""

def measure(y, delta_s_N: float):
    """mu(y,N) = exp(-1.5 * Delta_s(N) * y). y may be scalar or ndarray."""

def comoving_radius_ratio(y, delta_s_N: float):
    """r(y,N)/r_out = exp[-(y+1) * Delta_s(N) / 2]. y may be scalar or ndarray."""
```

- `y` arguments must accept both a Python scalar and a `numpy.ndarray` (the
  full LGL node array from `Numerics/LGLCollocation.py` will be passed
  here in later prompts) — use `numpy` elementwise operations throughout,
  not Python `math`, so array inputs broadcast correctly without a
  separate code path.
- `delta_s`: validate `alpha >= 0` (raise `ValueError` — this is a
  configuration error, matching the pattern used for every other
  parameter-validity guard in this codebase; **do not** guard against
  `alpha == 0` itself, which is a mathematically well-defined input to
  this specific function (it only produces $\Delta s(N_{\rm init})=0$
  exactly — the resulting divide-by-zero, if any, happens downstream in
  whichever later prompt divides by $\Delta s(N)$, not here).
- No caching, no precomputation — these are cheap, called fresh at every
  RHS evaluation by later prompts; don't add complexity that isn't needed
  yet.

## Tests

`tests/test_onion_coordinate.py`:

- **$\Delta s(N_{\rm init})=\ln(1+\alpha)$ exactly**, for several `alpha`
  values including `alpha=0` (giving exactly `0.0`) and a few `alpha>0`
  values — construct the call so `H_sq_core == H_sq_nl_init` and
  `N == N_init` (i.e. the $N$-dependent terms vanish by construction),
  confirming the formula's $N_{\rm init}$-anchor behaviour directly, not
  just by inspection.
- **Full formula away from $N_{\rm init}$**: construct a synthetic scenario
  with a known, closed-form $H^2_{\rm sq,core}(N)$ (e.g. exponential decay,
  $H^2_{\rm sq,core}(N) = H^2_{\rm sq,nl,init}\cdot e^{-2k(N-N_{\rm init})}$
  for some constant $k$) and confirm `delta_s(...)` matches the
  hand-derived closed form
  $\Delta s(N)=\ln(1+\alpha)+(1-k)(N-N_{\rm init})$ — this exercises the
  $(N-N_{\rm init})$ and $H$-ratio terms together, not just the trivial
  $N=N_{\rm init}$ case above.
- **`delta_s` raises `ValueError` for `alpha < 0`.**
- **`delta_s_derivative`** returns `1 - epsilon_core` directly, for a
  handful of values including `epsilon_core > 1` (super-inflationary,
  still a valid numerical input even if not physically expected).
- **Advection coefficient endpoint behaviour**: `advection_coefficient`
  evaluated at `y=-1` is **exactly** `0.0` (not just small) for any
  `delta_s_N > 0` and any `epsilon_core` — this is a structural zero from
  the `(y+1)` factor, test it as an exact equality. At `y=+1`, confirm it
  equals `2/delta_s_N * (1 - epsilon_core)` directly from the formula.
- **Measure endpoint values**: `measure(-1, delta_s_N)` equals
  `exp(1.5*delta_s_N)` and `measure(+1, delta_s_N)` equals
  `exp(-1.5*delta_s_N)`, both checked directly against the closed form.
- **`comoving_radius_ratio` endpoint consistency**:
  `comoving_radius_ratio(-1, delta_s_N)` is **exactly** `1.0` for any
  `delta_s_N` (confirms $y=-1$ really does return $r_{\rm out}$ itself,
  structurally, not approximately) and
  `comoving_radius_ratio(+1, delta_s_N)` equals `exp(-delta_s_N)` — this
  second one is a cross-check that evaluating the general $r(y,N)/r_{\rm
  out}$ formula at $y=+1$ agrees with what $\Delta s(N)$'s own definition
  says $r_H(N)/r_{\rm out}$ should be, even though no separate $r_H$
  function exists to compare against directly.
- **Vectorized input**: construct an `LGLCollocationGrid` from prompt 01
  (using `DEFAULT_N_COLLOCATION_POINTS`, imported from
  `config/defaults.py`, not hardcoded) and pass `grid.nodes` directly into
  `advection_coefficient`, `measure`, and `comoving_radius_ratio`, checking
  the returned array's shape and its first/last elements against the
  scalar endpoint tests above. This is the one place this prompt touches
  prompt 01's module — confirms the two compose correctly without
  coupling their implementations.

## Acceptance criteria

- [ ] `Numerics/OnionCoordinate.py` created with `delta_s`,
      `delta_s_derivative`, `advection_coefficient`, `measure`,
      `comoving_radius_ratio` — no class, no shared state.
- [ ] No absolute-valued $r_H$ or $r_{\rm out}$ function anywhere in this
      module.
- [ ] All functions accept both scalar and `ndarray` `y` inputs via
      `numpy` operations.
- [ ] `delta_s` raises `ValueError` for `alpha < 0`; does **not** guard
      against `alpha == 0`.
- [ ] No dependency on `AbstractPotential`, `InflatonTrajectory`,
      `DatastoreObject`, or anything under `Datastore/` in this module.
- [ ] All tests above pass, including the exact-zero/exact-one structural
      checks (not approximate) at the domain endpoints.
- [ ] No other files touched.

## Commit

Single commit, message along the lines of:
`Add onion coordinate utilities (Delta_s, measure, advection coefficient, radius ratio)`
