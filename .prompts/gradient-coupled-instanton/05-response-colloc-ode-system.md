# Prompt 05 — Response-sector collocation RHS and terminal condition

## Context

Read `./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
before starting — §"Instanton equations" (labels `eq:inst-rphi`,
`eq:inst-rpi`, and the calculation panel deriving them, which fixed a sign
error found and confirmed in discussion — make sure you're reading the
corrected equations, not an older cached copy), §"Terminal condition on the
boundary node" (`eq:terminal-colloc`), §"Boundary conditions" (the spatial
$y=\pm1$ conditions on $\rfield,\rmom$), and the discretized form in
eq. `colloc-eqs`.

Governing equations, response sector (eq. `colloc-eqs`, response rows) —
**already confirmed correct against `FullInstanton`'s `bwd_rhs` in the 1D
limit, no further sign-checking needed**:

$$\dot{\rfield}_j = A(y_j,N)(D\rfield)_j + \rfield_j\,c(N) + \frac{V''(\phi_j)}{H^2(y_j,N)}\rmom_j - \frac{1}{r_{\rm out}^2(aH)_{\rm loc}(y_j,N)^2}(\mathcal L\rmom)_j$$
$$\dot{\rmom}_j = A(y_j,N)(D\rmom)_j + \rmom_j\,c(N) - \rfield_j + (3-\epsilon_{\rm SR}(y_j,N))\rmom_j$$

where $c(N) \equiv (1-\epsilon_{\rm core}(N))\left[\dfrac{1}{\Delta s(N)}-\dfrac32\right]$
is a **single scalar per $N$** (the $y$-dependence cancelled exactly
between the advective-adjoint term and a previously-missing
measure-derivative term — this is not an approximation, it's an exact
simplification derived in the tex's calculation panel). Note the gradient
term here applies $\mathcal L$ to $\rmom$ (not $\rfield$) — self-adjointness
of $\mathcal L$ moves the operator onto the *other* response field, this
is not a typo relative to the forward sector's $\mathcal L\phi$.

This is integrated **backward** in $N$ (from $N_{\rm final}$ down to
$N_{\rm init}$), same convention as `FullInstanton`'s `bwd_rhs`: the RHS
function itself still computes the literal $d/dN$ derivative (forward
sense); it's `solve_ivp`'s `t_span` that runs in reverse, handled by the
caller (the Picard driver, a later prompt), not by this RHS function.

## Task

### `ComputeTargets/GradientCoupledInstanton/response_rhs.py`

**State vector layout — mirrors the forward sector structurally, but the
roles are swapped, not identical. Get this distinction right:**

- $\rfield_0=\rmom_0=0$ (outer edge, $y=-1$): both pinned to exactly zero
  — trivial, no trajectory lookup needed (unlike the forward sector's edge
  condition, which needed `phi_before_end`/`pi_before_end`).
- $\rmom_{n_{\rm max}}$ (core): Neumann-eliminated
  (`neumann_boundary_value`, `boundary_index=-1`, same utility as prompt
  04 used for $\phi_{n_{\rm max}}$) — **not** integrated.
- $\rfield_{n_{\rm max}}$ (core): free — **is** integrated, carries the
  terminal condition. (This is the swap: in the forward sector, $\phi$ was
  eliminated at the core and $\pi$ was free; here it's the opposite —
  $\rmom$ eliminated, $\rfield$ free.)
- Everything else ($\rfield_1,\ldots,\rfield_{n_{\rm max}}$,
  $\rmom_1,\ldots,\rmom_{n_{\rm max}-1}$) is integrated — length
  $2n_{\rm max}-1$, same total as the forward sector, different indices.

Write `pack_response_state`/`unpack_response_state` as their own pair
(don't reuse `pack_state`/`unpack_state` from `forward_rhs.py` — the index
assignment genuinely differs and reusing the forward sector's functions
here would obscure that rather than simplify anything).

**Access to the current forward-pass solution.** Mirroring
`FullInstanton`'s `SplineWrapper`-based `phi1_sp`/`phi2_sp` pattern, but
now one spline *per grid node* rather than a single scalar spline — accept
`phi_splines: list[SplineWrapper]` and `pi_splines: list[SplineWrapper]`
(length $n_{\rm max}+1$ each) as parameters; evaluate
`phi_splines[j](N)`/`pi_splines[j](N)` to reconstruct the full
$(n_{\rm max}+1)$-length `phi_full`/`pi_full` arrays at whatever $N$ the
backward integrator is currently at. Building this list of splines from a
stored forward solution is the *caller's* job (the Picard driver, a later
prompt) — this prompt just consumes them.

**RHS assembly**, given `(phi_full, pi_full)` reconstructed via the
splines above and `(rfield_full, rmom_full)` from `unpack_response_state`:

1. Core-only $\Delta s(N)$ and per-node $\Delta s_{\rm loc}(y_j,N)$: same
   two calls to `delta_s()` as `forward_rhs.py` already makes (core value
   from `phi_full[-1],pi_full[-1]`; per-node array from the full arrays).
2. $c(N) = (1-\epsilon_{\rm core})[1/\Delta s(N) - 1.5]$ — a single float,
   using `epsilon_core = potential.epsilon(phi_full[-1], pi_full[-1])`.
3. $(\mathcal L\rmom)_j$: `L_operator(rmom_full, delta_s_N, grid.nodes, grid.D, grid.D2)` — applied to `rmom`, matching the equation above.
4. $V''(\phi_j)$: `potential.d2V_dphi2(phi_full)` (vectorized, same
   contract as `V`/`dV_dphi`/`H_sq`/`epsilon` established in prompt 04's
   docstring note — confirm this method already exists on
   `AbstractPotential`; if its docstring lacks the same vectorization note
   added in prompt 04, add the same one-line note here for consistency,
   documentation only).
5. Advection terms: `advection_term(rfield_full, A_array, grid.D)`,
   `advection_term(rmom_full, A_array, grid.D)` — same `A_array` construction
   as `forward_rhs.py` (needs `epsilon_core`, already computed in step 2).
6. Assemble both equations exactly as displayed above.
7. Slice out the integrated indices only
   ($\rfield_1,\ldots,\rfield_{n_{\rm max}}$;
   $\rmom_1,\ldots,\rmom_{n_{\rm max}-1}$) and pack via
   `pack_response_state`.

Top-level function:
`response_rhs(N, response_state, N_init, alpha, H_sq_nl_init, grid, phi_splines, pi_splines, potential) -> np.ndarray`.

**Terminal-state construction** — a separate small function, not part of
`response_rhs` itself:

```python
def terminal_response_state(lam: float, grid: CollocationGrid, delta_s_N_final: float) -> np.ndarray:
    """
    Builds the response state vector at N_final: all zeros except
    rfield_{n_max} = -lam / (grid.weights[-1] * measure(1.0, delta_s_N_final)).
    Uses grid.weights[-1] directly (already validated against the closed
    form 2/[n_max(n_max+1)] in prompt 01's tests) rather than recomputing it.
    """
```

## Tests

`tests/test_response_rhs.py`:

- **Pack/unpack round-trip** for the response state, analogous to prompt
  04's test, confirming the *swapped* index layout specifically (a test
  that would pass under the forward sector's layout by accident should
  fail here — construct it so the swap is actually exercised, e.g. check
  that `unpack_response_state` places the free variable at the core in
  `rfield`, not `rmom`).
- **Boundary handling**: `rfield_full[0]==0`, `rmom_full[0]==0` exactly;
  `rmom_full[-1]` satisfies the Neumann row exactly
  (`grid.D[-1,:] @ rmom_full ≈ 0`, floating-point precision).
- **`terminal_response_state`**: for a few `lam` values, confirm every
  entry is zero except the core `rfield` entry, which matches the stated
  formula exactly (including using `grid.weights[-1]`, not a
  re-derivation).
- **Reduction-limit cross-check** (the key test, same spirit as prompt
  04's): construct a scenario with `disable_spatial_coupling`-equivalent
  conditions for the response sector — i.e. verify that when $A=0$ (pick
  `delta_s_N` such that the advection coefficient vanishes, or directly
  test the assembly with the advection/gradient contributions stripped)
  and using a single-node-equivalent setup, the surviving terms
  (`c(N)`-independent physics: the $V''/H^2$ coupling and the
  $-\rfield+(3-\epsilon)\rmom$ piece) match `FullInstanton`'s `bwd_rhs`
  (`P2 * d2V_dphi2(phi1) / Hsq`, `-P1 + (3-eps)*P2`) exactly, to
  floating-point precision — this is the direct implementation of the
  cross-check already confirmed analytically in discussion; don't skip
  re-verifying it numerically just because the algebra was checked by
  hand.
- **`c(N)` is a scalar, not an array**: an explicit type/shape check that
  the bracket term is computed once per $N$ and applied identically to
  every node, not accidentally computed per-node (would silently
  reintroduce the $y$-dependence the tex's derivation shows should cancel).

## Acceptance criteria

- [ ] `ComputeTargets/GradientCoupledInstanton/response_rhs.py` created
      with `pack_response_state`, `unpack_response_state`, `response_rhs`,
      `terminal_response_state`.
- [ ] State vector layout matches the swapped (relative to forward sector)
      Neumann/free assignment at the core, confirmed by a test that would
      fail under the forward sector's layout.
- [ ] `c(N)` computed once per $N$ (scalar), not per node.
- [ ] Gradient term applies `L_operator` to `rmom`, not `rfield`.
- [ ] `terminal_response_state` uses `grid.weights[-1]` directly, not a
      recomputed closed-form weight.
- [ ] Reduction-limit test passes numerically against `FullInstanton`'s
      actual `bwd_rhs` formula, to floating-point precision.
- [ ] No other files touched, except (if needed) a documentation-only
      vectorization note on `d2V_dphi2`, matching prompt 04's pattern.

## Commit

Single commit, message along the lines of:
`Add response-sector collocation RHS and terminal-condition construction`
