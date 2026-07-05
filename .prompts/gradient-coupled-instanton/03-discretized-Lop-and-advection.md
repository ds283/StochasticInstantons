# Prompt 03 — Discretized $\mathcal L$, advection term, Neumann hard elimination

## Context

Read `./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
before starting — in the tex, the sections "Discretizing $\mathcal L$" and
"Boundary conditions" under "Collocation basis: Legendre–Gauss–Lobatto
nodes", plus "The gradient operator in $y$" earlier in the document (search
for labels `eq:Lop-definition`, `eq:gradient-term-y` if printed equation
numbers have drifted).

This prompt has two parts: a small, deliberate rename to the module from
prompt 02, then the new discretization utilities for prompt 03 itself.

### Part A — rename `H_sq_core` → `H_sq_local` in `Numerics/OnionCoordinate.py`

`delta_s()` is used two ways: with the **core's** $H^2_{\rm sq}$ (giving the
coordinate-defining $\Delta s(N)$ used to build the $y$-domain itself), and
— as established while planning this prompt — with an **arbitrary node's
own local** $H^2_{\rm sq}$ (giving $\Delta s_{\rm loc}(y,N)$, needed by a
*later* prompt for the $(aH)_{\rm loc}$-based prefactor in the gradient
term — not built here, just the reason for this rename). `H_sq_core` no
longer describes both uses accurately. Rename the parameter to
`H_sq_local` in `delta_s()`'s signature, update its docstring to describe
both uses explicitly, and update every call site and test in
`tests/test_onion_coordinate.py` that uses the old keyword name. No change
to the function's logic — this is a rename only.

### Part B — new module

**Important scoping point, worked out and confirmed in discussion before
this prompt was written — get this boundary right:** $\mathcal L$'s own
discretization uses **only** the single, core-only, coordinate-defining
$\Delta s(N)$ — confirmed directly from the tex, which writes
$\Delta s(N)$ bare (no $y$-subscript) throughout the discretized-$\mathcal
L$ equation. The $y$-dependent $\Delta s_{\rm loc}(y,N)$/$(aH)_{\rm loc}$
combination from the rename note above is a **separate** multiplicative
prefactor, applied "wherever $\mathcal L$ appears in the equations of
motion" per the tex's own explicit statement — i.e. by the *next* prompt
(`colloc-ode-system`), not this one. **This prompt's `L_operator` must not
apply any $(aH)_{\rm loc}$ or $r_{\rm out}$-related scaling at all** — its
output is exactly the bracketed-and-exponentiated quantity in the
discretized-$\mathcal L$ equation, nothing more.

## Task

### `Numerics/DiscretizedOperators.py`

Plain functions, no class, no shared state (mirrors prompt 02's design;
depends on `numpy` only — no `AbstractPotential`, no `DatastoreObject`):

```python
def L_operator(f: np.ndarray, delta_s_N: float, y_nodes: np.ndarray, D: np.ndarray, D2: np.ndarray) -> np.ndarray:
    """
    (L f)_j = exp(delta_s_N) * exp(delta_s_N * y_j) * [ (4/delta_s_N**2)(D2 @ f)_j - (2/delta_s_N)(D @ f)_j ]

    delta_s_N is the single, core-only Delta_s(N) — NOT a per-node value.
    Does not apply any 1/r_out^2 or (aH)_loc scaling; that composition
    happens in a later prompt.
    """

def advection_term(f: np.ndarray, A_array: np.ndarray, D: np.ndarray) -> np.ndarray:
    """A_array * (D @ f), elementwise. A_array is the precomputed
    advection_coefficient(y_nodes, delta_s_N, epsilon_core) array from
    Numerics/OnionCoordinate.py — this function doesn't recompute it."""

def neumann_boundary_value(f: np.ndarray, D: np.ndarray, boundary_index: int) -> float:
    """
    Returns the boundary node value f_b consistent with a homogeneous
    Neumann condition d f/dy = 0 at that node, i.e. solves
    sum_k D[boundary_index, k] * f[k] = 0 for f[boundary_index], using
    the OTHER entries of f (f[boundary_index] itself is ignored, not
    assumed correct on entry). Returns a scalar; does not modify f. The
    only current use is boundary_index = -1 (the y=+1 / n_max node), but
    keep the index a parameter rather than hardcoding -1, since the
    formula itself doesn't care which row it's given.
    """
```

- `L_operator`/`advection_term` must work correctly for the full
  `(n_collocation_points,)`-length node-value array, i.e. the caller is
  responsible for having already resolved every boundary value (Dirichlet
  assignment, Neumann elimination via `neumann_boundary_value`, or a free
  dynamical value) into `f` *before* calling these — neither function
  does any boundary handling itself.
- `neumann_boundary_value`: implements
  $f_b = -\frac{1}{D_{b,b}}\sum_{k\neq b}D_{b,k}f_k$ directly from the row
  `D[boundary_index, :]`. Don't build a modified/reduced differentiation
  matrix (the tex describes the classical spectral-methods technique of
  substituting this into a reduced $D^{(2)}$; that's mathematically
  equivalent to computing the scalar boundary value first and then
  applying the ordinary, unmodified `D`/`D2` to the completed vector —
  simpler to implement and verify, and what this prompt should build).

## Tests

`tests/test_discretized_operators.py`:

- **`L_operator` exactness on polynomials**: for a handful of low-degree
  polynomials $\phi(y)$ (degree $\leq n_{\rm max}$, so `D`/`D2` from
  `LGLCollocationGrid` are exact per prompt 01's own tests) and several
  `delta_s_N` values, compare `L_operator`'s output against the
  **hand-computed closed form**
  $e^{\Delta s}e^{\Delta s y_j}\left[\frac{4}{\Delta s^2}\phi''(y_j) -
  \frac{2}{\Delta s}\phi'(y_j)\right]$, using the exact analytic
  derivatives of $\phi$ (not a second application of `D`/`D2`) as the
  reference — this is both a correctness check on `L_operator` and an
  implicit confirmation that no stray $r_{\rm out}$/$(aH)_{\rm loc}$
  scaling has crept in, since any such factor would show up as a mismatch
  against the bare closed form.
- **`advection_term` exactness**: similarly, for a polynomial $\phi$ and a
  precomputed `A_array` (call `advection_coefficient` from prompt 02 with a
  chosen `delta_s_N`/`epsilon_core`), confirm `advection_term(...)`
  matches $A(y_j,N)\,\phi'(y_j)$ using the exact analytic derivative.
- **`neumann_boundary_value` recovers a known zero-derivative point**: use
  $\phi(y)=(y-1)^2$ (exactly zero derivative at $y=+1$); evaluate $\phi$ at
  every node except the last, call `neumann_boundary_value` with
  `boundary_index=-1`, and confirm it recovers $\phi(1)=0$ exactly.
- **`neumann_boundary_value` structural property**: for an arbitrary
  (non-Neumann-consistent) array, compute the boundary value via
  `neumann_boundary_value`, write it into a copy of the array at
  `boundary_index`, and confirm `D @ f_completed` is (to floating-point
  precision) exactly zero at `boundary_index` — this tests the actual
  guarantee the function is supposed to provide, independent of any
  specific test function.
- **Integration with prompts 01–02**: construct an `LGLCollocationGrid`
  using `DEFAULT_N_COLLOCATION_POINTS`, get `delta_s_N` and `A_array` from
  `Numerics/OnionCoordinate.py` for a chosen synthetic scenario, and run
  `L_operator`/`advection_term` against it end-to-end — confirms the three
  modules compose without coupling their internals.
- **Rename propagation**: confirm `tests/test_onion_coordinate.py` still
  passes after the `H_sq_core`→`H_sq_local` rename (i.e. this prompt
  actually updates every call site, not just `OnionCoordinate.py` itself).

## Acceptance criteria

- [ ] `delta_s()` in `Numerics/OnionCoordinate.py` renamed
      `H_sq_core`→`H_sq_local`; docstring updated to describe both uses;
      all call sites and tests updated; no logic change.
- [ ] `Numerics/DiscretizedOperators.py` created with `L_operator`,
      `advection_term`, `neumann_boundary_value`.
- [ ] `L_operator` uses a single scalar `delta_s_N` (core-only), applies no
      $r_{\rm out}$/$(aH)_{\rm loc}$ scaling of any kind.
- [ ] `neumann_boundary_value` computes the scalar boundary value directly
      from `D`'s boundary row — no reduced/modified matrix construction.
- [ ] All tests above pass, including the exact-zero structural test for
      `neumann_boundary_value`.
- [ ] No dependency on `AbstractPotential`, `InflatonTrajectory`,
      `DatastoreObject`, or anything under `Datastore/`.
- [ ] No other files touched beyond the rename's call sites.

## Commit

Single commit, message along the lines of:
`Add discretized L operator, advection term, Neumann hard elimination; rename H_sq_core to H_sq_local`
