# Prompt 01 — LGL collocation grid and differentiation matrices

## Context

Read `./.documents/onion_model_planning.md` in full before starting, and
`./.documents/onion_notes.tex` (if this path is wrong, `onion_notes.tex`
should exist somewhere under `./.documents/` — locate it rather than
guessing at its content) for the precise equations referenced below
(§12.1 in particular). This is prompt 1 of a fresh sequence for the
`GradientCoupledInstanton` ("onion model") compute target, built on a
Legendre–Gauss–Lobatto (LGL) collocation scheme. An earlier, now-abandoned
sinc-eigenfunction spectral design was implemented and reverted before this
sequence started — nothing from that design should be reused or referenced.

The only piece of that earlier work still standing is
`Caching/ExtractionCache.py` (see
`./.prompts/gradient-coupled-instanton/OLD-0003-extraction-cache-interface.md`
for its original prompt, for context only — it needs no changes and this
prompt doesn't depend on it).

**This prompt builds a single, self-contained numerical module — no
`DatastoreObject`, no compute target, no dependence on anything else in the
codebase.** The point of keeping it self-contained is explicit: it should
be independently testable against known/tabulated results with no other
machinery involved, and swappable later (e.g. for a different
discretization) without touching any consumer. Don't let any Datastore,
Ray, or `ComputeTargets` concerns leak into this file.

## Task

### 1. `Numerics/LGLCollocation.py`

Define a small abstract interface, then one concrete implementation:

```python
class CollocationGrid(ABC):
    @property
    @abstractmethod
    def n_max(self) -> int:
        """Polynomial degree (grid has n_max + 1 nodes)."""

    @property
    @abstractmethod
    def n_collocation_points(self) -> int:
        """Number of grid nodes = n_max + 1."""

    @property
    @abstractmethod
    def nodes(self) -> np.ndarray:
        """The y_j, shape (n_collocation_points,), ascending, y_0=-1, y_{n_max}=+1."""

    @property
    @abstractmethod
    def weights(self) -> np.ndarray:
        """Quadrature weights w_j, shape (n_collocation_points,)."""

    @property
    @abstractmethod
    def D(self) -> np.ndarray:
        """First-derivative differentiation matrix, shape (n_collocation_points, n_collocation_points)."""

    @property
    @abstractmethod
    def D2(self) -> np.ndarray:
        """Second-derivative differentiation matrix, same shape."""
```

**`LGLCollocationGrid(CollocationGrid)`** — the concrete LGL implementation:

- **Constructor takes `n_collocation_points: int`, not `n_max`.** Compute
  `self._n_max = n_collocation_points - 1` **once**, in `__init__`, and
  expose it via the `n_max` property. This is the **only** place in this
  module (or, per the design discussion, in the whole codebase) that
  performs this subtraction — every other property and every later
  consumer reads `.n_max` off the constructed instance, never recomputes
  `n_collocation_points - 1` independently. Validate `n_collocation_points`
  is an integer $\geq 2$ (need at least the two endpoints; raise
  `ValueError` otherwise, with a message distinguishing "not an integer"
  from "too small" — this is a configuration error, same category as the
  guards built for earlier compute targets).
- **Node/weight generation**: interior LGL nodes are the roots of
  $P_{n_{\rm max}}'(y)$ (derivative of the Legendre polynomial of degree
  $n_{\rm max}$), found via the standard Jacobi-matrix
  (Golub–Welsch-type) eigenvalue construction — not a closed form (unlike
  Chebyshev). Reference implementations are linked in
  `onion_model_planning.md`
  (`FastGaussQuadrature.jl`, `sphglltools`); translate the algorithm
  faithfully rather than reinventing it, and cross-check the result
  against published tabulated LGL node values for small degree (see tests
  below) rather than trusting the translation by inspection. Endpoints are
  always exactly $y_0=-1$, $y_{n_{\rm max}}=+1$.
  Weights: $w_j = \dfrac{2}{n_{\rm max}(n_{\rm max}+1)\,[P_{n_{\rm max}}(y_j)]^2}$,
  with the closed-form endpoint case
  $w_0 = w_{n_{\rm max}} = \dfrac{2}{n_{\rm max}(n_{\rm max}+1)}$ — this
  exact endpoint value is already used elsewhere in the planning doc's
  terminal-condition equation, so it's worth a dedicated test that this
  formula's endpoint output matches it exactly, not just approximately.
- **Differentiation matrices**: standard LGL differentiation matrix
  formula,
  $$D_{ij} = \frac{P_{n_{\rm max}}(y_i)}{P_{n_{\rm max}}(y_j)}\frac{1}{y_i-y_j}\quad(i\neq j),$$
  with the standard special-case diagonal entries (zero at interior nodes,
  $\pm n_{\rm max}(n_{\rm max}+1)/4$ at the two endpoints — get the sign
  right for each endpoint, don't assume symmetry). $D^{(2)}$: compute as
  $D@D$ for this prompt — simplest, standard approach at the node counts
  anticipated here (tens, not thousands) — but this is exactly what the
  polynomial-exactness test below is for; don't assume it's adequate,
  confirm it.
- Everything precomputed once in `__init__`; all properties just return
  already-computed arrays (no per-call recomputation) — this will get
  called from inside an ODE RHS in later prompts, so construction cost is
  amortized once per solve but property access needs to be cheap.
- Plain `numpy` in, plain `numpy` out. No `DatastoreObject`, no import of
  anything from `Datastore/`, `ComputeTargets/`, or `InflationConcepts/`.

### 2. Default `n_max` as a named constant

Add `DEFAULT_N_COLLOCATION_POINTS = 17` to `config/defaults.py` (17 points
= degree $n_{\rm max}=16$), with a comment stating the equivalence
explicitly and noting this is a **starting point for the mandatory
convergence scan** described in `onion_model_planning.md`, not a value to
be trusted as final without that scan. Nothing in this prompt should
hardcode `16` or `17` anywhere except this one named constant — any test
or example that needs a "reasonable default-sized" grid should import and
use it.

## Tests

`tests/test_lgl_collocation.py`:

- **Constructor validation**: non-integer or `n_collocation_points < 2`
  raises `ValueError`.
- **`n_max`/`n_collocation_points` relationship**: for a handful of
  constructed grids, assert `grid.n_max == n_collocation_points - 1` and
  `len(grid.nodes) == n_collocation_points` together, explicitly, as its
  own test — not just implied by other tests passing. This is the specific
  regression the design discussion flagged as easy to get wrong later.
- **Tabulated node values**: compare `nodes` against published LGL node
  tables for small degree (e.g. $n_{\rm max}=2,3,4$, which have simple
  closed forms, and at least one larger tabulated case such as
  $n_{\rm max}=6$ or $8$) to a tight tolerance.
- **Endpoint weights**: `weights[0]` and `weights[-1]` match
  $2/[n_{\rm max}(n_{\rm max}+1)]$ exactly (to floating-point precision,
  not just approximately) for several `n_max` values.
- **Quadrature exactness**: $\sum_j w_j\,y_j^k$ integrates $y^k$ over
  $[-1,1]$ exactly for all $k$ up to the degree LGL quadrature is exact
  for ($2n_{\rm max}-1$), compared against the closed-form
  $\int_{-1}^1 y^k\,dy$.
- **Differentiation exactness**: for polynomials up to degree
  $n_{\rm max}$ (e.g. $y^0,y^1,\ldots,y^{n_{\rm max}}$, and at least one
  non-monomial combination), confirm `D @ p(nodes)` and
  `D2 @ p(nodes)` reproduce the exact analytic first/second derivatives at
  every node, to a tight tolerance appropriate for double precision.
- **`CollocationGrid` usable through the abstract interface**: construct an
  `LGLCollocationGrid`, access it only through methods/properties declared
  on `CollocationGrid`, confirm nothing requires reaching into
  implementation details — mirrors the same test discipline used for
  `ExtractionCache`.
- Use `DEFAULT_N_COLLOCATION_POINTS` (not a hardcoded number) for any test
  that just needs "a reasonably-sized grid" rather than a specific degree.

## Acceptance criteria

- [ ] `Numerics/LGLCollocation.py` created with `CollocationGrid` (ABC) and
      `LGLCollocationGrid`.
- [ ] Constructor takes `n_collocation_points`; `n_max` is computed exactly
      once, in one place, and exposed as a read-only property — no other
      code path (in this module) independently computes
      `n_collocation_points - 1`.
- [ ] `DEFAULT_N_COLLOCATION_POINTS = 17` added to `config/defaults.py`,
      documented as `n_max = 16` with a note that this is a scan starting
      point, not a validated production value.
- [ ] No hardcoded `16`/`17` anywhere outside that one constant definition.
- [ ] All tests above pass, including tabulated-value comparison and exact
      polynomial differentiation up to degree `n_max`.
- [ ] No `DatastoreObject`, `Datastore/`, `ComputeTargets/`, or
      `InflationConcepts/` imports anywhere in `Numerics/LGLCollocation.py`.
- [ ] No other files touched.

## Commit

Single commit, message along the lines of:
`Add LGL collocation grid and differentiation matrices (standalone numerics module)`
