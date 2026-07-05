# Prompt 04 — Forward-sector collocation RHS (zeroth Picard iterate)

## Context

Read `./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
before starting — §"Instanton equations" (labels `eq:inst-phi`, `eq:inst-pi`),
§"Boundary conditions". This prompt assembles prompts 01–03 plus real
physics (`AbstractPotential`, `InflatonTrajectory`) into the forward-sector
right-hand side, with response fields identically zero (the "zeroth Picard
iterate" — response-sector RHS and the Picard iteration tying both sectors
together are later prompts, not this one).

Governing equations (eq. `inst-phi`/`inst-pi`), with $\rfield=\rmom\equiv0$:

$$\dot\phi = \pi + A\,\partial_y\phi, \qquad \dot\pi = -(3-\epsilon_{\rm SR}{\small\rm loc})\,\pi - \frac{V'(\phi)}{H^2{\small\rm loc}} + \frac{1}{r_{\rm out}^2(aH)_{\rm loc}^2}\,\mathcal L\phi + A\,\partial_y\pi$$

This is the first prompt in a new subpackage,
`ComputeTargets/GradientCoupledInstanton/`, which will accumulate
`forward_rhs.py` (this prompt), `response_rhs.py`, `picard.py`,
`extraction.py`, `scale_assignment.py` in later prompts, with the actual
`DatastoreObject` compute target arriving last to tie them together. This
is also the first prompt allowed to depend on `AbstractPotential` and
`InflatonTrajectory` directly — unlike `Numerics/`, kept physics-free
deliberately, this subpackage is where physics and numerics meet.

## Task

### Part A — documentation-only note on `AbstractPotential`

Add a one-line note to the docstrings of `H_sq`, `epsilon`, and `dV_dphi`
in `CosmologyConcepts/Potentials/AbstractPotential.py` stating that these
methods must accept and correctly broadcast over `numpy.ndarray` inputs
for `phi`/`pi`, not just Python scalars — this is relied on by vectorized
callers (this prompt is the first, but not the last). **Documentation
only, no behavior change**: don't touch the implementations, don't add
`@abstractmethod` array-handling logic, don't change any subclass. This is
purely making an existing, already-relied-upon contract explicit so a
future editor doesn't accidentally narrow these methods to scalar-only.

### Part B — `InflatonTrajectory` convenience methods

Add three small, purely additive methods to `ComputeTargets/InflatonTrajectory.py`'s
`InflatonTrajectory` class (**not** the `Proxy` — these are only ever
called after `.get()`, inside a Ray remote task, same as `phi_at`/`pi_at`
already are):

```python
def phi_before_end(self, N: float) -> float:
    """phi_at(N_end - N) — the backward-counted-N convenience used
    throughout GradientCoupledInstanton for the outer boundary row."""

def pi_before_end(self, N: float) -> float:
    """pi_at(N_end - N)."""

def rho_before_end(self, N: float) -> float:
    """rho_at(N_end - N) — provided now since it's the same pattern,
    even though this prompt doesn't use it (needed by the later
    zeta-profile-extraction prompt)."""
```

No existing method touched — purely additive.

### Part C — `ComputeTargets/GradientCoupledInstanton/forward_rhs.py`

**State vector layout.** Not all $2(n_{\rm max}+1)$ raw grid values are
independently integrated:

- $\phi_0,\pi_0$ (outer edge, $y=-1$): Dirichlet-pinned to
  `trajectory.phi_before_end(N)`/`.pi_before_end(N)` — **not** integrated,
  recomputed fresh at every RHS call.
- $\phi_{n_{\rm max}}$ (core, $y=+1$): Neumann-eliminated via
  `neumann_boundary_value` from `Numerics/DiscretizedOperators.py`
  (`boundary_index=-1`) — **not** integrated.
- $\pi_{n_{\rm max}}$ (core momentum): genuinely free, **is** integrated.
- Everything else ($\phi_1,\ldots,\phi_{n_{\rm max}-1}$,
  $\pi_1,\ldots,\pi_{n_{\rm max}}$) is integrated.

So the ODE state vector has length $2n_{\rm max}-1$:
$(\phi_1,\ldots,\phi_{n_{\rm max}-1},\ \pi_1,\ldots,\pi_{n_{\rm max}})$.
Write explicit `pack_state(phi_full, pi_full) -> np.ndarray` and
`unpack_state(state, N, N_init, alpha, H_sq_nl_init, grid, trajectory, potential) -> (phi_full, pi_full)`
functions. `unpack_state` is responsible for: inserting the state's
interior values at the right indices, calling
`trajectory.phi_before_end(N)`/`.pi_before_end(N)` for index 0, and calling
`neumann_boundary_value` (using the just-assembled `phi_full[:-1]`, i.e.
every index except the boundary one, which is what's about to be
overwritten) for index `n_max`. Test this pack/unpack pair for exact
round-trip on the *interior* values (packing what `unpack_state` produces
should return the original state exactly).

**RHS assembly**, given `(phi_full, pi_full)` from `unpack_state`:

1. Core-only $\Delta s(N)$: call `delta_s(N, N_init, H_sq_local=potential.H_sq(phi_full[-1], pi_full[-1]), H_sq_nl_init, alpha)` from `Numerics/OnionCoordinate.py`.
2. $(\mathcal L\phi)_j$ over the full array: `L_operator(phi_full, delta_s_N, grid.nodes, grid.D, grid.D2)`.
3. Per-node $\Delta s_{\rm loc}(y_j,N)$: call the **same** `delta_s()` again, but with `H_sq_local = potential.H_sq(phi_full, pi_full)` passed as the **full array** (broadcasts per Part A's contract) — gives an array, not a scalar. The gradient-term prefactor is `np.exp(-2.0 * delta_s_loc_array)`.
4. Per-node $\epsilon_{\rm loc}$, $H^2_{\rm loc}$, $V'$: `potential.epsilon(phi_full, pi_full)`, `potential.H_sq(phi_full, pi_full)`, `potential.dV_dphi(phi_full)` — vectorized calls over the full array.
5. Advection coefficient array: `advection_coefficient(grid.nodes, delta_s_N, epsilon_loc_array[-1])` (core epsilon — index into the array from step 4 rather than calling `potential.epsilon` a second time).
6. Advection terms: `advection_term(phi_full, A_array, grid.D)`, `advection_term(pi_full, A_array, grid.D)`.
7. Assemble:
   ```
   dphi_full = pi_full + advection_phi_array
   dpi_full  = -(3.0 - epsilon_loc_array) * pi_full \
               - dV_array / H_sq_loc_array \
               + exp(-2*delta_s_loc_array) * L_phi_array \
               + advection_pi_array
   ```
8. **`disable_spatial_coupling: bool` parameter** (default `False`): when
   `True`, zero **both** the gradient term (`L_phi_array` contribution) and
   **both** advection arrays before assembling — zeroing only the gradient
   term would leave nodes coupled through advection (which doesn't vanish
   at the core), so the reduction test below wouldn't actually reduce to a
   decoupled single trajectory unless both are zeroed together.
9. Return `pack_state` applied to `(dphi_full, dpi_full)` restricted to the
   integrated indices only (i.e. slice out indices `1..n_max-1` for
   `dphi_full` and `1..n_max` for `dpi_full` before packing — the
   boundary-row derivatives themselves are never used, since those aren't
   integrated states).

Top-level function: `forward_rhs(N, state, N_init, alpha, H_sq_nl_init, grid, trajectory, potential, disable_spatial_coupling=False) -> np.ndarray`.

## Tests

`tests/test_forward_rhs.py`:

- **Pack/unpack round-trip**: for a synthetic state vector, a fixed `N`,
  and a stub trajectory (simple closed-form `phi_at`/`pi_at`, no real
  ODE integration needed — same style of stub used in earlier prompts),
  confirm `pack_state(*unpack_state(state, ...))` returns exactly the
  interior portion of `state` (i.e. round-trips).
- **Boundary handling**: confirm `unpack_state`'s `phi_full[0]` equals
  `trajectory.phi_before_end(N)` and `pi_full[0]` equals
  `trajectory.pi_before_end(N)` directly; confirm `phi_full[-1]` satisfies
  the Neumann row exactly (`grid.D[-1,:] @ phi_full ≈ 0`, floating-point
  precision, not approximate).
- **`phi_before_end`/`pi_before_end`/`rho_before_end`**: unit test against
  a stub/synthetic `InflatonTrajectory`-like object confirming these
  literally call `phi_at`/`pi_at`/`rho_at` at `N_end - N`.
- **Reduction-limit cross-check, the key acceptance test**: with
  `disable_spatial_coupling=True`, for a handful of `(phi, pi)` sample
  points and a fixed potential, confirm the RHS's per-node output at
  *every* index (not just the core) matches
  `(pi, -(3-potential.epsilon(phi,pi))*pi - potential.dV_dphi(phi)/potential.H_sq(phi,pi))`
  — i.e. exactly `FullInstanton`'s own `fwd_rhs` with response fields
  zeroed (`ComputeTargets/FullInstanton.py`'s `fwd_rhs` closure), to
  floating-point precision. Construct the full state so different nodes
  have deliberately different `(phi,pi)` values (confirms the vectorized
  assembly is correct elementwise, not just at one index, since with
  spatial coupling disabled every node's derivative should depend only on
  its own local `(phi,pi)`).
- **`disable_spatial_coupling` actually zeroes what it claims**: with it
  `True`, confirm changing a *different* node's `phi`/`pi` value doesn't
  change another node's computed derivative (direct evidence of
  decoupling, independent of the reduction-formula comparison above).
- **Part A**: confirm the three docstrings contain the vectorization note
  (a simple string-content check is fine — this is a documentation
  change, not a behavioral one).

## Acceptance criteria

- [ ] `AbstractPotential.H_sq`/`.epsilon`/`.dV_dphi` docstrings updated
      with the vectorization note; no logic changed anywhere in that file.
- [ ] `InflatonTrajectory` gains `phi_before_end`, `pi_before_end`,
      `rho_before_end` — purely additive, no existing method touched.
- [ ] `ComputeTargets/GradientCoupledInstanton/forward_rhs.py` created
      with `pack_state`, `unpack_state`, `forward_rhs`.
- [ ] `disable_spatial_coupling=True` zeroes both the gradient term and
      both advection contributions together.
- [ ] Reduction-limit test passes exactly (floating-point precision)
      against `FullInstanton`'s actual `fwd_rhs` formula, at every node,
      not just the core.
- [ ] Pack/unpack round-trips exactly; boundary rows verified structurally
      (Neumann row exact zero, Dirichlet values match trajectory calls
      directly).
- [ ] No other files touched.

## Commit

Single commit, message along the lines of:
`Add forward-sector collocation RHS (response fields zero); InflatonTrajectory before-end convenience methods; AbstractPotential vectorization docstring note`
