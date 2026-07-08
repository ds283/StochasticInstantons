# (c) University of Sussex 2026
# Created by David Seery
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Picard iteration / shooting driver for the gradient-coupled instanton model
(eq. colloc-eqs, terminal-colloc, shooting), tying together the forward and
response collocation right-hand sides of forward_rhs.py / response_rhs.py.

Mirrors FullInstanton's own adjoint/Picard/outer-Newton structure
(ComputeTargets/FullInstanton.py's _compute_full_instanton) as closely as the
grid-valued generalization allows: the same constants, the same overall
shape (background pass -> Picard inner loop -> outer Newton loop on the
shooting parameter lambda), generalized from scalar (phi, pi, P1, P2) arrays
over N to grid-valued arrays over (N, y) of shape
(len(N_grid), n_collocation_points).

N convention -- matches FullInstanton exactly. N_init/N_final/delta_Nstar
are supplied in the same "e-folds before the end of inflation" convention
as FullInstanton's own constructor parameters (N_init > N_final;
delta_Nstar the excess duration added on top of the naive N_init-N_final
span), and N_total = (N_init - N_final) + delta_Nstar is the same quantity
FullInstanton computes. But the running N actually integrated over here is
local and zero-based, exactly like FullInstanton's own t_span: it starts at
0.0 (the transition start) and increases to N_total (the transition end),
matching Numerics/OnionCoordinate.py's delta_s(N, N_init, ...), which
requires its own running N argument to *increase* away from N_init for
Delta_s(N) to grow from ln(1+alpha) (at N=N_init) to the O(10) values
reached by the transition end -- so every delta_s() call anywhere in this
module or in forward_rhs.py/response_rhs.py passes a literal 0.0 for that
N_init argument.

Trajectory lookups (InflatonTrajectory.phi_at/pi_at) use InflatonTrajectory's
own absolute N (0.0 at its own initial condition, increasing to N_end at the
end of inflation), which is a different coordinate from the local N above.
N_offset = trajectory.N_end - N_init converts between them, computed once
here from the compute target's raw parameters and threaded through to every
forward_rhs call as absolute_N = N_offset + local_N. response_rhs has no
trajectory dependency, so it needs no N_offset.

SBP-SAT self-consistent target for pi_core (prompts 21a, 22b)
-------------------------------------------------------------------------
forward_rhs.py's core SAT penalty for pi needs a target g_pi(N) that is
*not* pi_core itself (see that module's docstring for why a self-referential
target would make the penalty a no-op). Since pi_core previously had no
boundary condition at all, there is no live formula to compute g_pi from (as
there is for phi_core's own Neumann/regularity target) -- instead g_pi
tracks the SELF-CONSISTENT core pi(N) trajectory:

  Sweep 0: g_pi(N) seeded from an independent FullInstanton profile's own
    core (phi2) trajectory -- see _seed_pi_core_values below for the
    fetch-then-fallback preference order.
  Sweep k+1: updated from THIS sweep's own just-computed pi_core_sweep_k(N)
    -- Anderson-accelerated (prompt 22b), NOT plain lagging: prompt 22's
    Finding 2 (.documents/gradient-coupled-instanton/22-validation.md)
    showed that once phi_end is corrected to a genuinely non-degenerate
    target (prompt 22a), the naive lagged-replacement update

        g_pi(N) <- (1-theta)*g_pi_sweep_k(N) + theta*pi_core_sweep_k(N)

    DIVERGES: the sweep-to-sweep residual falls for ~15 sweeps then grows
    without bound, at every (n_collocation_points, delta_Nstar) tried, and
    under-relaxation (theta<1) only trades divergence for impractically
    slow convergence. The prompt 22b design note
    (.documents/gradient-coupled-instanton/
    22b-convergent-iteration-design-note.md) diagnoses this as a
    delayed-feedback instability in the lagged UPDATE RULE itself, not in
    the underlying forward/response coupling or the per-sweep SBP-SAT
    linear operator (whose own spectrum is unaffected by how g_pi is
    updated -- see the last paragraph below) -- confirmed by a "fork"
    experiment: freezing g_pi at its sweep-0 seed (no lag at all) converges
    the SAME coupled map in a single sweep, while the theta=1 lagged update
    diverges on the identical case.

    The fix (_AndersonMixer below) replaces the update rule with Type-I
    Anderson acceleration (Walker & Ni 2011), keeping the target genuinely
    self-consistent (so the zero-bias/closure-independence property below
    still holds) while curing the naive update's instability. Treating
    g_pi_sweep_k -> pi_core_sweep_k as a fixed-point map T(x) = pi_core(x)
    with residual g(x) = T(x) - x, Anderson combines a short window
    (default ANDERSON_WINDOW sweeps) of past (x, g) pairs via a small
    least-squares solve rather than a single-step replacement or fixed
    convex blend:

        x_{k+1} = x_k + theta*g_k - (DeltaX_k + theta*DeltaG_k) @ gamma
        gamma = argmin_g || g_k - DeltaG_k @ gamma ||_2

    where DeltaX_k/DeltaG_k are the window's successive iterate/residual
    differences and theta is the existing mixing/damping parameter
    (Walker-Ni's "beta"), still confined to (0,1]. anderson_m=0 (the
    pre-22b default) reduces this exactly to the old plain Picard/
    theta-blend update, so that code path remains available (e.g. for
    regression tests demonstrating the Finding-2 divergence). anderson_m>0
    is the new production default -- see DEFAULT_ANDERSON_M below and
    _AndersonMixer's own docstring.

At Picard convergence g_pi(N) -> pi_core(N) (the fixed-point residual g_k
goes to zero together with the Picard residual), so the SAT penalty's
forcing -> 0 at the solution regardless of which update rule reached it:
the stabiliser adds sweep-to-sweep dissipation but never biases the
converged answer. This is the concrete mechanism behind forward_rhs.py's
"closure-independence" claim, checked directly by the two-seed regression
in tests/test_picard.py (FullInstanton seed vs. background-trajectory seed
must converge to the same answer).

The per-sweep linear stability of the assembled operator is IDENTICAL
regardless of how g_pi is updated (design note Section 4): the "-tau*g"
part of the SAT is a constant additive forcing term, not part of the
Jacobian an eigenvalue analysis probes, so changing g's update rule changes
only the fixed point the iteration converges to (or whether it converges at
all), never the per-sweep operator's own spectrum. Only the *iteration's*
convergence (not its per-sweep stability) is what prompts 21a/22b's own
update-rule changes ever touch.
"""

import math
import time
from contextlib import contextmanager
from typing import Optional

import numpy as np
import scipy.integrate._ivp.rk as _scipy_rk
from scipy.integrate import solve_ivp

from Interpolation.spline_wrapper import SplineWrapper
from Numerics.OnionCoordinate import delta_s
from ComputeTargets.FullInstanton import _compute_full_instanton
from ComputeTargets.GradientCoupledInstanton.forward_rhs import (
    pack_state,
    unpack_state,
    forward_rhs,
)
from ComputeTargets.GradientCoupledInstanton.response_rhs import (
    unpack_response_state,
    response_rhs,
    terminal_response_state,
)

MAX_OUTER = 50
MAX_INNER = 30

# Backtracking-line-search budget for the outer Newton step on lambda
# (prompt 22b -- see the outer loop's own comment at the backtracking site).
# Each halving is one extra picard_inner call, so this is a small, bounded
# multiplier on outer-loop cost, not a second unbounded iteration.
MAX_BACKTRACK = 5

# Number of consecutive inner sweeps required below INNER_TOL before
# picard_inner declares convergence (prompt 22b -- see picard_inner's own
# comment at the sustained-convergence check). 1 reduces to the pre-22b
# single-dip check.
INNER_CONSECUTIVE_REQUIRED = 3

# Number of temporal sample points spanning the local domain [0.0, N_total];
# matches FullInstanton's own floor value (N_GRID = max(300, ...)).
N_GRID_SIZE = 300

# Mixing/damping factor for the pi_core SAT target's sweep-to-sweep update
# (Walker-Ni's "beta" when anderson_m>0; the old plain lagged-replacement
# blend's theta when anderson_m=0). theta=1 is a straight, undamped update.
DEFAULT_SAT_THETA = 1.0

# Anderson acceleration window (prompt 22b) -- number of past (x, g) pairs
# retained by _AndersonMixer. 0 disables acceleration entirely, reducing the
# update exactly to the old plain Picard/theta-blend rule (see the module
# docstring's "SBP-SAT self-consistent target" section and
# _AndersonMixer's own docstring). Tuned empirically against the prompt-22
# Finding 2 divergence cases: m=5 converges every (n, delta_Nstar) point
# tried within a practical sweep budget where m=0 (theta=1) diverges.
DEFAULT_ANDERSON_M = 5


class _AndersonMixer:
    """
    Type-I Anderson acceleration (Walker & Ni, SIAM J. Numer. Anal. 2011)
    for the pi_core SAT target's sweep-to-sweep fixed-point update (prompt
    22b Path 2A.2 -- see picard.py's own module docstring for the "SBP-SAT
    self-consistent target" derivation and why plain lagging diverges once
    the target is genuinely non-degenerate).

    The map being accelerated is x -> T(x), where T(x) is "the pi_core(N)
    trajectory produced by one Picard sweep run with SAT target x" --
    already computed as an ordinary side effect of picard_inner's existing
    backward+forward solve, so this class only changes how the NEXT target
    is built from the accumulated history of (x, g) pairs, where
    g = T(x) - x is the fixed-point residual. It does not add any new ODE
    solves, derivatives, or Jacobian.

    window (m): number of past (x, g) pairs retained, beyond the current
    one -- i.e. the least-squares problem uses at most m past differences.
    m=0 makes every update() call return exactly x_k + theta*g_k, the old
    plain Picard/theta-blend rule (theta=1 there is a straight replacement,
    matching the pre-22b DEFAULT_SAT_THETA=1.0 behaviour exactly).

    theta (Walker-Ni's "beta"): mixing/damping factor applied to the
    residual and to the correction's ΔG contribution; theta=1 is undamped
    Anderson, matching the module docstring's x_{k+1} formula exactly.

    Tikhonov regularization: plain (unregularized) least-squares Anderson
    was found empirically (prompt 22b acceptance testing) to STALL on this
    nonlinear map -- it knocks the residual down by ~2 orders of magnitude
    within a handful of sweeps, then oscillates indefinitely around that
    level instead of continuing to decrease. The mechanism is the classic
    Anderson failure mode on a genuinely nonlinear (non-affine) map: once
    ||g_k|| stops shrinking, ΔG's columns are all similarly-scaled "noise"
    directions rather than a well-separated basis, and the *exact*
    least-squares fit (which reproduces g_k precisely on that noisy basis)
    injects exactly that noise into the next iterate. A hard restart
    (dropping the window and falling back to an undamped plain-Picard step)
    was tried and made this WORSE, not better -- it reintroduces prompt 22
    Finding 2's own theta=1 instability on every reset. The fix that
    actually works is standard Tikhonov regularization of the small
    least-squares solve (a much gentler intervention, still smoothly
    blending in the full Anderson step when ΔG is well-conditioned):

        gamma = (ΔG^T ΔG + REG_EPS * ||ΔG||_F^2 * I)^{-1} ΔG^T g_k

    REG_EPS is a small, fixed relative regularization strength -- large
    enough to damp the noise-fitting behaviour, small enough that the
    Anderson correction still dominates the plain-Picard fallback whenever
    ΔG is genuinely well-conditioned (early sweeps, still-shrinking
    residual).
    """

    REG_EPS = 1.0e-2

    def __init__(self, window: int, theta: float):
        self._m = max(0, int(window))
        self._theta = theta
        self._X: list = []
        self._G: list = []

    def update(self, x_k: np.ndarray, g_k: np.ndarray) -> np.ndarray:
        if self._m == 0:
            return x_k + self._theta * g_k

        self._X.append(x_k)
        self._G.append(g_k)
        if len(self._X) > self._m + 1:
            self._X.pop(0)
            self._G.pop(0)

        m_k = len(self._X) - 1
        if m_k == 0:
            return x_k + self._theta * g_k

        dX = np.stack([self._X[i + 1] - self._X[i] for i in range(m_k)], axis=1)
        dG = np.stack([self._G[i + 1] - self._G[i] for i in range(m_k)], axis=1)

        gram = dG.T @ dG
        reg = self.REG_EPS * float(np.linalg.norm(dG, ord='fro') ** 2)
        gamma = np.linalg.solve(gram + reg * np.eye(m_k), dG.T @ g_k)
        return x_k + self._theta * g_k - (dX + self._theta * dG) @ gamma


# ---------------------------------------------------------------------------
# Prompt 17 Part B -- per-solve RK45 instrumentation. Pure measurement: none
# of this changes solve_ivp's method, tolerances, grid, or output values.
# ---------------------------------------------------------------------------


@contextmanager
def _count_rk45_step_attempts():
    """
    Counts every call to scipy's module-level ``rk_step`` helper -- one call
    per *attempted* RK45 step, whether that step is ultimately accepted or
    rejected (see ``scipy.integrate._ivp.rk.RungeKutta._step_impl``, whose
    inner ``while not step_accepted:`` retry loop calls ``rk_step`` exactly
    once per trial). ``RungeKutta._step_impl`` looks up the name
    ``rk_step`` in its own module's globals at call time, so temporarily
    replacing ``scipy.integrate._ivp.rk.rk_step`` redirects those calls
    without touching ``RK45`` itself.

    This is a pure observability hook: the wrapped function is a thin
    pass-through to the original ``rk_step``, so step selection, accepted
    step sizes, and every numerical output are completely unaffected --
    only a call counter increments. Restored in a ``finally`` block so a
    solver exception never leaves the patch in place.

    Combined with ``len(sol.sol.interpolants)`` (the number of *accepted*
    steps, available whenever ``dense_output=True``), this gives an exact
    rejected = total - accepted count without needing to duplicate any of
    RK45's own step-acceptance logic.
    """
    counter = {"attempts": 0}
    original = _scipy_rk.rk_step

    def _wrapped(*args, **kwargs):
        counter["attempts"] += 1
        return original(*args, **kwargs)

    _scipy_rk.rk_step = _wrapped
    try:
        yield counter
    finally:
        _scipy_rk.rk_step = original


def _solve_ivp_instrumented(instrument: bool, *args, **kwargs):
    """
    Thin wrapper around ``solve_ivp``. If ``instrument`` is False, calls
    ``solve_ivp`` completely unchanged and returns ``(sol, None)`` -- no
    monkeypatching, no extra work, so the non-instrumented path costs
    nothing beyond whatever ``dense_output``/``t_eval`` the caller already
    requested.

    If ``instrument`` is True, wraps the call with
    ``_count_rk45_step_attempts`` and returns ``(sol, step_stats)``, where
    ``step_stats`` is a dict with keys ``accepted``, ``rejected``, ``total``,
    ``step_sizes`` (list of accepted step sizes, ``abs(t_max - t_min)`` per
    dense-output interpolant). The caller must pass ``dense_output=True``
    for ``accepted``/``step_sizes`` to be populated; without it ``sol.sol``
    is ``None`` and this falls back to ``accepted=0``, ``step_sizes=[]``
    (every current call site in ``solve_picard`` passes ``dense_output=True``
    whenever it instruments, so this fallback is not expected to trigger in
    production use).
    """
    if not instrument:
        return solve_ivp(*args, **kwargs), None

    with _count_rk45_step_attempts() as counter:
        sol = solve_ivp(*args, **kwargs)

    interpolants = sol.sol.interpolants if sol.sol is not None else []
    accepted = len(interpolants)
    total = counter["attempts"]
    rejected = total - accepted
    step_sizes = [abs(ip.t - ip.t_old) for ip in interpolants]

    return sol, {
        "accepted": accepted,
        "rejected": rejected,
        "total": total,
        "step_sizes": step_sizes,
    }


def _aggregate_rk45_stats(stats_list: list, label: str, N_total: float) -> dict:
    """
    Aggregates a list of per-solve step-stats dicts (as produced by
    ``_solve_ivp_instrumented``) across every forward- or backward-direction
    ``solve_ivp`` call made during one whole ``solve_picard`` invocation --
    the zeroth Picard iterate's background pass plus every inner-Picard
    forward/backward solve across every outer Newton iteration -- into the
    six columns the diagnostics dict exposes for that direction:
    ``rk45_{label}_total_steps``, ``_accepted_steps``, ``_rejected_steps``,
    ``_min_step``, ``_max_step``, ``_steps_per_efold`` (total steps /
    N_total).

    Returns a dict of all-``None`` values if ``stats_list`` is empty (e.g.
    ``instrument_stiffness=False``, or a direction that made no solve_ivp
    calls before an early failure).
    """
    keys = (
        f"rk45_{label}_total_steps", f"rk45_{label}_accepted_steps",
        f"rk45_{label}_rejected_steps", f"rk45_{label}_min_step",
        f"rk45_{label}_max_step", f"rk45_{label}_steps_per_efold",
    )
    if not stats_list:
        return {k: None for k in keys}

    total_steps = sum(s["total"] for s in stats_list)
    accepted_steps = sum(s["accepted"] for s in stats_list)
    rejected_steps = sum(s["rejected"] for s in stats_list)
    all_step_sizes = [sz for s in stats_list for sz in s["step_sizes"]]

    return {
        f"rk45_{label}_total_steps": total_steps,
        f"rk45_{label}_accepted_steps": accepted_steps,
        f"rk45_{label}_rejected_steps": rejected_steps,
        f"rk45_{label}_min_step": min(all_step_sizes) if all_step_sizes else None,
        f"rk45_{label}_max_step": max(all_step_sizes) if all_step_sizes else None,
        f"rk45_{label}_steps_per_efold": (total_steps / N_total) if N_total else None,
    }


def _build_node_splines(N_grid: np.ndarray, values_grid: np.ndarray, y_transform: str) -> list:
    """One SplineWrapper per grid node (columns of values_grid), each built
    over the shared N_grid. values_grid has shape (len(N_grid), n_nodes)."""
    n_nodes = values_grid.shape[1]
    return [
        SplineWrapper(N_grid, values_grid[:, j], y_transform=y_transform, k=3)
        for j in range(n_nodes)
    ]


class _FullInstantonSeedPotentialHolder:
    """Duck-typed stand-in for InflatonTrajectory, exposing only the
    ._potential attribute _compute_full_instanton actually reads -- the same
    minimal stub used by tests/test_picard.py and
    scripts/compare_gradient_full.py for the same "bypass Ray, call the
    delegate directly" pattern."""

    def __init__(self, potential):
        self._potential = potential


class _FullInstantonSeedProxyStub:
    """Duck-typed stand-in for InflatonTrajectoryProxy: _compute_full_instanton
    only ever calls trajectory.get()._potential. Used only for the SAT
    pi_core seed's fallback FullInstanton delegate call below -- solve_picard
    itself already has `potential` directly, with no proxy of its own to
    reuse (its own `trajectory` parameter is the materialised
    InflatonTrajectory, not a proxy)."""

    def __init__(self, potential):
        self._holder = _FullInstantonSeedPotentialHolder(potential)

    def get(self):
        return self._holder


def _seed_pi_core_values(
    N_grid: np.ndarray,
    N_offset: float,
    phi_init: float,
    pi_init: float,
    phi_end: float,
    N_total: float,
    trajectory,
    potential,
    diffusion_model,
    atol: float,
    rtol: float,
    label: str,
    full_instanton_seed: Optional[dict],
) -> np.ndarray:
    """
    Builds the sweep-0 SAT target values for pi_core, sampled on N_grid (see
    the module docstring's "SBP-SAT lagged self-consistent target" section).
    Seed QUALITY only affects how many Picard sweeps it takes to converge,
    NEVER the converged answer (the target is overwritten every sweep by the
    solve's own core pi(N), starting from sweep 1) -- this is the whole point
    of lagging rather than fixing the target, and is checked directly by the
    two-seed closure-independence regression in tests/test_forward_rhs.py.

    Preference order:
      1. full_instanton_seed, if supplied and not itself a failure -- a
         pre-computed dict shaped like _compute_full_instanton's own return
         value. This is the "prefer fetching the already-computed
         FullInstanton result from the datastore" path: datastore access
         only happens on the driver (never inside a @ray.remote worker, see
         .claude/rules/ray-dispatch.md), so GradientCoupledInstanton.py's own
         Ray remote function is responsible for fetching one (if available)
         and passing the resulting dict in here -- solve_picard itself never
         touches the datastore.
      2. Otherwise, compute one inline via _compute_full_instanton._function
         -- bypassing Ray, the same "call the underlying function directly"
         pattern already used throughout this test suite
         (tests/test_picard.py) and scripts/compare_gradient_full.py. This is
         a well-tested, standalone delegate call, not a reimplementation of
         FullInstanton's own physics.
      3. If that ALSO fails to converge (e.g. a pathological corner of
         parameter space), fall back to the noiseless background
         trajectory's own pi(N) -- always available, no extra ODE solve,
         and exactly what every other node already tracks during the zeroth
         Picard iterate's own background pass.
    """

    def _values_from_result(data: dict) -> Optional[np.ndarray]:
        seed_N = np.asarray(data["N_sample"], dtype=float)
        seed_pi = np.asarray(data["phi2"], dtype=float)
        if len(seed_N) < 4:
            return None
        spline = SplineWrapper(seed_N, seed_pi, y_transform='linear', k=3)
        return np.asarray(spline(N_grid), dtype=float)

    if full_instanton_seed is not None and not full_instanton_seed.get("failure", True):
        vals = _values_from_result(full_instanton_seed)
        if vals is not None:
            return vals

    fi_data = _compute_full_instanton._function(
        trajectory=_FullInstantonSeedProxyStub(potential),
        dm=diffusion_model,
        phi_init=phi_init,
        pi_init=pi_init,
        phi_final=phi_end,
        N_total=N_total,
        N_sample=N_grid.tolist(),
        atol=atol,
        rtol=rtol,
        label=f"[{label}] SAT pi_core seed (FullInstanton fallback)",
    )
    if not fi_data.get("failure", True):
        vals = _values_from_result(fi_data)
        if vals is not None:
            return vals

    print(
        f"[{label}] SAT pi_core seed: FullInstanton delegate also failed to "
        f"converge; falling back to the noiseless background trajectory's "
        f"own pi(N) as the sweep-0 target. This only affects how many Picard "
        f"sweeps it takes to converge, not the converged answer -- see "
        f"forward_rhs.py's module docstring."
    )
    return np.array([trajectory.pi_at(N_offset + N) for N in N_grid])


def solve_picard(
    N_init: float,
    N_final: float,
    delta_Nstar: float,
    alpha: float,
    H_sq_nl_init: float,
    grid,
    trajectory,
    potential,
    diffusion_model,
    atol: float,
    rtol: float,
    phi_end: float,
    disable_spatial_coupling: bool = False,
    instrument_stiffness: bool = True,
    label: Optional[str] = None,
    verbose: bool = False,
    full_instanton_seed: Optional[dict] = None,
    theta: float = DEFAULT_SAT_THETA,
    anderson_m: int = DEFAULT_ANDERSON_M,
) -> dict:
    """
    Solve the gradient-coupled instanton BVP (see _solve_picard_once's own
    docstring for the full physics/algorithm description). This wrapper adds
    one thing on top: a retry-with-a-different-seed safeguard (prompt 21a
    Phase-2 acceptance finding).

    WHY THE RETRY EXISTS: a fetched full_instanton_seed (prompt 21a's
    "prefer fetching from the datastore" path) can come from a FullInstanton
    that solves a genuinely different BVP than this GradientCoupledInstanton
    does -- FullInstanton's own target is evaluated at
    trajectory.phi_at(N_end - N_final) (no delta_Nstar), whereas this
    function's own phi_end target corresponds to
    trajectory.phi_at(N_end - N_final + delta_Nstar) (see picard.py's module
    docstring on the N convention, and GradientCoupledInstanton.py's own
    compute() for phi_end's derivation). For most parameter points this
    difference is immaterial (both are close to the background), but for
    parameter points where FullInstanton's own shooting problem is poorly
    conditioned (observed on a case with an extremely small diffusion
    coefficient, requiring a P1 ~ 10^8 to hit its target), the resulting
    phi2(N) profile -- while individually smooth and physically valid AS A
    SOLUTION OF FULLINSTANTON'S OWN PROBLEM -- can be a poor match for what
    THIS BVP's pi_core(N) will actually converge to. Using it as the lagged
    SAT target's seed was observed to make the Picard iteration develop a
    slow-growing (not catastrophic-on-sweep-1, but compounding over ~10-20
    sweeps) instability, even though the SAME closure converges in a single
    sweep from either the internally-computed (tier 2/3) seed or a
    correctly-converged answer.

    Freezing the target (theta=0, i.e. never re-lagging after the seed) does
    make the Picard/Newton loop "converge" quickly in this situation, but to
    the WRONG answer -- the frozen, mismatched target biases the shooting
    problem enough that no lambda can drive the true phi_end residual below
    tolerance (observed directly: the outer Newton loop pushes lambda to
    extreme values without ever reducing the residual). So theta=0 is not a
    valid escape hatch for this failure mode; it must be treated as a
    genuine solve failure and retried with a different, internally-consistent
    seed instead.

    THE RETRY: if a solve using a supplied full_instanton_seed fails to
    converge, retry ONCE with full_instanton_seed=None -- forcing
    _seed_pi_core_values's own tier-2 (inline _compute_full_instanton call,
    which correctly targets THIS function's own phi_end) or tier-3
    (background trajectory) fallback, both of which are internally
    consistent with the BVP actually being solved here. This preserves the
    "prefer fetching from the datastore" optimisation on the common path
    (most parameter points) while never letting a mismatched-target seed
    turn into an outright solve failure. If disable_spatial_coupling=True,
    or no seed was supplied in the first place, there is nothing to retry
    with, and the single attempt's result is returned as-is.
    """
    result = _solve_picard_once(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid, trajectory,
        potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=disable_spatial_coupling,
        instrument_stiffness=instrument_stiffness, label=label, verbose=verbose,
        full_instanton_seed=full_instanton_seed, theta=theta, anderson_m=anderson_m,
    )

    needs_retry = (
        result.get("failure", False)
        and not disable_spatial_coupling
        and full_instanton_seed is not None
    )
    if not needs_retry:
        return result

    _lbl = label if label else f"phi_end={phi_end:.4g} N_init={N_init:.3g} N_final={N_final:.3g}"
    print(
        f"[{_lbl}] solve_picard: attempt with the supplied full_instanton_seed "
        f"failed to converge; retrying once with the internally-consistent "
        f"(tier 2/3) seed instead -- see solve_picard's own docstring for why "
        f"a fetched seed can occasionally mismatch this BVP's own target."
    )
    return _solve_picard_once(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid, trajectory,
        potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=disable_spatial_coupling,
        instrument_stiffness=instrument_stiffness, label=label, verbose=verbose,
        full_instanton_seed=None, theta=theta, anderson_m=anderson_m,
    )


def _solve_picard_once(
    N_init: float,
    N_final: float,
    delta_Nstar: float,
    alpha: float,
    H_sq_nl_init: float,
    grid,
    trajectory,
    potential,
    diffusion_model,
    atol: float,
    rtol: float,
    phi_end: float,
    disable_spatial_coupling: bool = False,
    instrument_stiffness: bool = True,
    label: Optional[str] = None,
    verbose: bool = False,
    full_instanton_seed: Optional[dict] = None,
    theta: float = DEFAULT_SAT_THETA,
    anderson_m: int = DEFAULT_ANDERSON_M,
) -> dict:
    """
    Single-attempt core of solve_picard -- see that function's own docstring
    for the public contract. Factored out so solve_picard can retry with a
    different seed if this attempt fails to converge (prompt 21a Phase-2
    acceptance finding, see solve_picard's own docstring for why).

    Solve the gradient-coupled instanton BVP over the onion coordinate grid
    by Picard iteration with an outer Newton correction on the shooting
    parameter lambda = P1-equivalent terminal Lagrange multiplier.

    Boundary conditions (local N; see module docstring for the N convention):
        phi(y_j, N=0.0) = phi_init, pi(y_j, N=0.0) = pi_init  (uniform in y)
        phi(y=+1, N=N_total) = phi_end   [shooting condition on lambda]

    full_instanton_seed (prompt 21a, optional): a pre-computed result dict
    shaped like _compute_full_instanton's own return value, used ONLY to
    seed sweep 0 of the lagged pi_core SAT target (see the module docstring's
    "SBP-SAT lagged self-consistent target" section and
    _seed_pi_core_values's own docstring for the full fetch-then-fallback
    preference order). None (the default) means "no pre-fetched seed
    available" -- solve_picard computes one inline instead, via
    _compute_full_instanton._function (bypassing Ray). Ignored entirely when
    disable_spatial_coupling=True (the SAT is switched off in that mode, so
    there is nothing to seed).

    theta (prompts 21a/22b, optional, default DEFAULT_SAT_THETA=1.0):
    mixing/damping factor for the pi_core target's sweep-to-sweep update.
    When anderson_m=0, this is the old plain lagged-replacement blend,
    g <- (1-theta)*g_prev + theta*u_core_new. When anderson_m>0 (the
    default), this is Walker-Ni's Anderson mixing parameter "beta" (see
    _AndersonMixer and the module docstring's "SBP-SAT self-consistent
    target" section) -- theta=1 is undamped Anderson.

    anderson_m (prompt 22b, optional, default DEFAULT_ANDERSON_M): Anderson
    acceleration window size (see _AndersonMixer). 0 disables acceleration,
    reproducing the pre-22b plain lagged-replacement update exactly (prompt
    22's Finding 2 divergence) -- kept only for regression comparison, not
    a recommended production setting.

    instrument_stiffness (prompt 17 Part B; default True): when True,
    every forward/backward RK45 solve_ivp call made during this solve (the
    zeroth Picard iterate's background pass, plus every inner-Picard
    forward/backward solve across every outer Newton iteration) is
    instrumented via _solve_ivp_instrumented/_count_rk45_step_attempts, and
    the aggregated step-count/step-size/wall-clock statistics are folded
    into the returned "diagnostics" dict under "rk45_forward_*",
    "rk45_backward_*", and "picard_sweep_wallclock_min/mean/max" (see
    _aggregate_rk45_stats's own docstring for the exact keys). This gates
    *measurement overhead only* -- it never changes solve_ivp's method,
    tolerances, grid, or the physics result (bg_sol's own dense_output flag
    is the only call-site difference; dense_output requests extra
    per-step interpolant bookkeeping but does not alter step selection or
    output values). When False, these diagnostics keys are simply absent.

    verbose (default False): print one line per inner Picard sweep and one
    line per outer Newton iteration (residual, lambda), so a long-running
    solve's progress is visible instead of blocking silently until it
    converges or exhausts MAX_OUTER. Off by default since production runs
    dispatch hundreds of solves in parallel Ray workers, where per-sweep
    prints would flood the log; intended for interactive/exploratory use.

    Returns a dict with keys:
        "N_total", "N_grid", "phi_grid", "pi_grid", "rfield_grid",
        "rmom_grid", "final_lambda", "failure", "diagnostics"
    """
    compute_start = time.perf_counter()
    ode_solve_count = 0

    # Prompt 17 Part B -- shared accumulators mutated (via .append(), never
    # reassigned) by picard_inner's closure below; aggregated into
    # "diagnostics" at every return point via _instrumentation_diagnostics().
    fwd_rk45_stats: list = []
    bwd_rk45_stats: list = []
    picard_sweep_wallclocks: list = []

    _lbl = label if label else f"phi_end={phi_end:.4g} N_init={N_init:.3g} N_final={N_final:.3g}"

    n_max = grid.n_max
    n_nodes = n_max + 1

    # Prompt 22b recalibration: atol*100 / atol*10 (the pre-22b values) were
    # never validated against genuine nonlinear coupling -- Finding 1 (prompt
    # 22) established that lambda=0 was an EXACT fixed point under the old
    # degenerate target, so these tolerances were always trivially satisfied
    # in a single sweep and never actually exercised. Once the target is
    # genuinely non-trivial (prompt 22a) and the closure is Anderson-
    # accelerated (this prompt), extensive empirical testing (design note,
    # .documents/gradient-coupled-instanton/
    # 22b-convergent-iteration-design-note.md) found the inner map's
    # achievable sweep-to-sweep residual has a genuine floor around 1e-4 to
    # 1e-5 (absolute, in phi units of order 1-10) -- NOT a bug in the
    # acceleration scheme (confirmed against scipy's own globalized
    # Newton-Krylov solver on the same isolated sub-problem, which plateaus
    # at the same level) but an intrinsic property of this discretized
    # nonlinear fixed-point map. INNER_TOL/OUTER_TOL are recalibrated here to
    # the empirically-achievable level (with a safety margin) rather than
    # left at values that can never be reached in practice.
    OUTER_TOL = max(atol * 1.0e6, 1.0e-2)
    INNER_TOL = max(atol * 1.0e4, 1.0e-4)

    N_offset = trajectory.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    N_start = 0.0
    N_stop = N_total

    N_grid = np.linspace(N_start, N_stop, N_GRID_SIZE)
    N_grid_rev = N_grid[::-1]

    if verbose:
        print(f"[{_lbl}] starting: n_nodes={n_nodes} N_total={N_total:.6g} "
              f"alpha={alpha:.6g} MAX_OUTER={MAX_OUTER} MAX_INNER={MAX_INNER}", flush=True)

    phi_init = trajectory.phi_at(N_offset + N_start)
    pi_init = trajectory.pi_at(N_offset + N_start)

    # Uniform-in-y initial condition (eq. bc-init): the core has not yet
    # deviated from the noiseless background anywhere on the grid.
    state_init = pack_state(np.full(n_nodes, phi_init), np.full(n_nodes, pi_init))

    def _unpack_grid(y_matrix: np.ndarray, N_values: np.ndarray):
        phi_grid = np.empty((len(N_values), n_nodes))
        pi_grid = np.empty((len(N_values), n_nodes))
        for i, N_i in enumerate(N_values):
            phi_full_i, pi_full_i = unpack_state(
                y_matrix[:, i], N_i, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential
            )
            phi_grid[i] = phi_full_i
            pi_grid[i] = pi_full_i
        return phi_grid, pi_grid

    def _unpack_response_grid(y_matrix: np.ndarray, N_values: np.ndarray):
        rfield_grid = np.empty((len(N_values), n_nodes))
        rmom_grid = np.empty((len(N_values), n_nodes))
        for i in range(len(N_values)):
            rfield_full_i, rmom_full_i = unpack_response_state(y_matrix[:, i], grid)
            rfield_grid[i] = rfield_full_i
            rmom_grid[i] = rmom_full_i
        return rfield_grid, rmom_grid

    def _fwd_rhs(N, y, rfield_splines, rmom_splines, g_pi_core_spline):
        return forward_rhs(
            N, y, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
            rfield_splines, rmom_splines, diffusion_model,
            g_pi_core_spline,
            disable_spatial_coupling=disable_spatial_coupling,
        )

    def _bwd_rhs(N, y, phi_splines, pi_splines):
        return response_rhs(
            N, y, alpha, H_sq_nl_init, grid, phi_splines, pi_splines, potential,
        )

    def _instrumentation_diagnostics() -> dict:
        """Folds the accumulated rk45_*/picard_sweep_wallclock_* keys into
        whatever diagnostics dict is about to be returned (success or
        failure) -- empty dict if instrument_stiffness is False, so those
        keys are simply absent rather than populated with placeholder
        values."""
        if not instrument_stiffness:
            return {}
        out = _aggregate_rk45_stats(fwd_rk45_stats, "forward", N_total)
        out.update(_aggregate_rk45_stats(bwd_rk45_stats, "backward", N_total))
        out["picard_sweep_wallclock_min"] = min(picard_sweep_wallclocks) if picard_sweep_wallclocks else None
        out["picard_sweep_wallclock_mean"] = (
            sum(picard_sweep_wallclocks) / len(picard_sweep_wallclocks) if picard_sweep_wallclocks else None
        )
        out["picard_sweep_wallclock_max"] = max(picard_sweep_wallclocks) if picard_sweep_wallclocks else None
        return out

    def _failure_diagnostics(outer_iterations, newton_fallback_count,
                              picard_iterations_per_outer, picard_time_total,
                              picard_iters_total, final_residual):
        return {
            "compute_time": time.perf_counter() - compute_start,
            "converged": False,
            "final_residual": final_residual,
            "total_ode_solves": ode_solve_count,
            "outer_iterations": outer_iterations,
            "newton_fallback_count": newton_fallback_count,
            "final_lambda": None,
            "picard_iterations_per_outer": picard_iterations_per_outer,
            "min_picard_iterations": min(picard_iterations_per_outer) if picard_iterations_per_outer else None,
            "max_picard_iterations": max(picard_iterations_per_outer) if picard_iterations_per_outer else None,
            "mean_picard_iterations": (
                sum(picard_iterations_per_outer) / len(picard_iterations_per_outer)
                if picard_iterations_per_outer else None
            ),
            "mean_time_per_picard_iteration": (
                picard_time_total / picard_iters_total if picard_iters_total else None
            ),
            **_instrumentation_diagnostics(),
        }

    def _failure_result(diagnostics):
        return {
            "failure": True,
            "N_total": N_total,
            "N_grid": [],
            "phi_grid": [], "pi_grid": [],
            "rfield_grid": [], "rmom_grid": [],
            "final_lambda": None,
            "diagnostics": diagnostics,
        }

    # ── Zeroth Picard iterate: background pass, response fields zero ──────
    zero_splines = _build_node_splines(N_grid, np.zeros((N_GRID_SIZE, n_nodes)), y_transform='sinh')

    # ── SBP-SAT lagged pi_core target: sweep-0 seed (prompt 21a) ───────────
    # See the module docstring's "SBP-SAT lagged self-consistent target"
    # section and _seed_pi_core_values's own docstring. Skipped entirely
    # when disable_spatial_coupling=True: forward_rhs zeroes the SAT penalty
    # in that mode and never dereferences this spline, so there is nothing
    # to seed and no need to pay for a FullInstanton fallback compute in
    # that (test-only) reduction path.
    if disable_spatial_coupling:
        g_pi_values = None
        g_pi_core_spline = None
    else:
        g_pi_values = _seed_pi_core_values(
            N_grid, N_offset, phi_init, pi_init, phi_end, N_total,
            trajectory, potential, diffusion_model, atol, rtol, _lbl,
            full_instanton_seed,
        )
        g_pi_core_spline = SplineWrapper(N_grid, g_pi_values, y_transform='linear', k=3)

    bg_sol, bg_step_stats = _solve_ivp_instrumented(
        instrument_stiffness,
        lambda N, y: _fwd_rhs(N, y, zero_splines, zero_splines, g_pi_core_spline),
        (N_start, N_stop), state_init, method="RK45", t_eval=N_grid, atol=atol, rtol=rtol,
        dense_output=instrument_stiffness,
    )
    ode_solve_count += 1
    if bg_step_stats is not None:
        fwd_rk45_stats.append(bg_step_stats)
    if not bg_sol.success:
        print(f"[{_lbl}] background ODE failed for zeroth Picard iterate")
        return _failure_result(_failure_diagnostics(0, 0, [], 0.0, 0, None))

    phi_grid0, pi_grid0 = _unpack_grid(bg_sol.y, N_grid)

    def picard_inner(
        lam: float, phi_grid_in: np.ndarray, pi_grid_in: np.ndarray,
        g_pi_values_in: Optional[np.ndarray],
    ):
        """
        Run Picard iteration for fixed lambda. Returns grids or Nones, plus
        the dense-output (`dense_output=True`) solve_ivp solutions of the
        *last* inner iteration's forward/backward passes -- fp_sol maps
        N -> packed forward state (unpack via forward_rhs.unpack_state),
        bp_sol maps N -> packed response state (unpack via
        response_rhs.unpack_response_state). Exposed so callers (the MSR
        action convergence diagnostic) can resample at an arbitrary, finer
        N resolution without re-solving any ODE.

        g_pi_values_in (prompt 21a) is the current lagged pi_core SAT target,
        sampled on N_grid -- None when disable_spatial_coupling=True (never
        dereferenced in that mode). Returned (updated) as the final element
        of the tuple so the caller can carry it into the NEXT outer-Newton
        call, continuing the lag chain across outer iterations rather than
        re-seeding it every time.
        """
        nonlocal ode_solve_count
        phi_grid = phi_grid_in.copy()
        pi_grid = pi_grid_in.copy()
        rfield_grid = np.zeros((N_GRID_SIZE, n_nodes))
        rmom_grid = np.zeros((N_GRID_SIZE, n_nodes))
        g_pi_values = None if g_pi_values_in is None else g_pi_values_in.copy()
        # Fresh Anderson history per picard_inner call (prompt 22b): lambda is
        # fixed within one call, but changes between outer-Newton calls, so
        # the accelerated map x -> T(x) itself changes and stale history
        # would mix iterates/residuals from a different map.
        mixer = _AndersonMixer(anderson_m, theta)
        n_inner_iters = 0
        n_consecutive_converged = 0
        fp_sol = None
        bp_sol = None

        for _ in range(MAX_INNER):
            sweep_start = time.perf_counter() if (instrument_stiffness or verbose) else None
            n_inner_iters += 1
            phi_splines = _build_node_splines(N_grid, phi_grid, y_transform='linear')
            pi_splines = _build_node_splines(N_grid, pi_grid, y_transform='linear')
            g_pi_core_spline = (
                None if g_pi_values is None
                else SplineWrapper(N_grid, g_pi_values, y_transform='linear', k=3)
            )

            # Backward pass: terminal condition at N_stop (eq. terminal-colloc).
            H_sq_core_final = potential.H_sq(phi_grid[-1, -1], pi_grid[-1, -1])
            delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_final, H_sq_nl_init, alpha)
            terminal_state = terminal_response_state(lam, grid, delta_s_N_final)

            bp, bp_step_stats = _solve_ivp_instrumented(
                instrument_stiffness,
                lambda N, y: _bwd_rhs(N, y, phi_splines, pi_splines),
                (N_stop, N_start), terminal_state, method="RK45",
                t_eval=N_grid_rev, dense_output=True, atol=atol, rtol=rtol,
            )
            ode_solve_count += 1
            if bp_step_stats is not None:
                bwd_rk45_stats.append(bp_step_stats)
            if not bp.success:
                return None, None, None, None, n_inner_iters, None, None, g_pi_values

            response_y = bp.y[:, ::-1]
            rfield_grid, rmom_grid = _unpack_response_grid(response_y, N_grid)

            rfield_splines = _build_node_splines(N_grid, rfield_grid, y_transform='sinh')
            rmom_splines = _build_node_splines(N_grid, rmom_grid, y_transform='sinh')

            # Forward pass, now sourced by the just-computed response fields.
            fp, fp_step_stats = _solve_ivp_instrumented(
                instrument_stiffness,
                lambda N, y: _fwd_rhs(N, y, rfield_splines, rmom_splines, g_pi_core_spline),
                (N_start, N_stop), state_init, method="RK45",
                t_eval=N_grid, dense_output=True, atol=atol, rtol=rtol,
            )
            ode_solve_count += 1
            if fp_step_stats is not None:
                fwd_rk45_stats.append(fp_step_stats)
            if not fp.success:
                return None, None, None, None, n_inner_iters, None, None, g_pi_values

            phi_grid_new, pi_grid_new = _unpack_grid(fp.y, N_grid)
            inner_res = np.max(np.abs(phi_grid_new - phi_grid))
            phi_grid, pi_grid = phi_grid_new, pi_grid_new
            fp_sol, bp_sol = fp.sol, bp.sol

            # ---------------------------------------------------------------
            # Self-consistent target update (prompts 21a/22b): rebuild
            # pi_core's SAT target from THIS sweep's own just-computed
            # pi_core(N) trajectory, so the NEXT sweep's SAT penalty forces
            # pi_core toward what it actually computed rather than the
            # previous (or seeded) guess. At convergence (inner_res -> 0)
            # the fixed-point residual g_k = pi_core_new - g_pi_values also
            # goes to zero, so g_pi -> pi_core exactly and the SAT forcing
            # vanishes (see forward_rhs.py's module docstring) REGARDLESS of
            # which update rule got there. The naive plain-replacement rule
            # (anderson_m=0) diverges once genuinely coupled (prompt 22
            # Finding 2); _AndersonMixer.update (anderson_m>0, the default)
            # replaces it with a convergent one -- see the module docstring's
            # "SBP-SAT self-consistent target" section.
            # ---------------------------------------------------------------
            if g_pi_values is not None:
                g_k = pi_grid_new[:, -1] - g_pi_values
                g_pi_values = mixer.update(g_pi_values, g_k)

            if instrument_stiffness:
                picard_sweep_wallclocks.append(time.perf_counter() - sweep_start)
            if verbose:
                sweep_time = time.perf_counter() - sweep_start if sweep_start is not None else None
                print(
                    f"[{_lbl}]     picard sweep {n_inner_iters}/{MAX_INNER}: "
                    f"max|dphi|={inner_res:.6e} (tol={INNER_TOL:.3e})"
                    + (f"  [{sweep_time:.2f}s]" if sweep_time is not None else ""),
                    flush=True,
                )
            # Sustained-convergence check (prompt 22b): the Anderson-
            # accelerated map's residual is not monotone -- it can dip below
            # INNER_TOL for a single sweep by chance while still far from
            # the true fixed point (observed directly: the SAME lambda,
            # re-solved from a different warm start, converged to visibly
            # different core trajectories when convergence was declared on
            # a single dip). Require INNER_CONSECUTIVE_REQUIRED consecutive
            # sweeps below tolerance before accepting convergence, so a
            # transient dip cannot be mistaken for having reached the fixed
            # point -- matches the qualitative behaviour needed for the
            # outer shooting residual to be a well-defined (reproducible)
            # function of lambda.
            if inner_res < INNER_TOL:
                n_consecutive_converged += 1
                if n_consecutive_converged >= INNER_CONSECUTIVE_REQUIRED:
                    break
            else:
                n_consecutive_converged = 0

        return phi_grid, pi_grid, rfield_grid, rmom_grid, n_inner_iters, fp_sol, bp_sol, g_pi_values

    # ── Outer secant loop on lambda ────────────────────────────────────────
    lam = 0.0
    lam_prev = None
    residual_prev = None
    # Trust-region radius (prompt 22b) capping the secant step: the secant
    # slope is a two-point estimate that can be numerically unstable when
    # the last two lambdas are close together relative to the map's own
    # curvature (observed directly: an occasional huge, oscillation-
    # inducing overshoot even after the small-dlam noise issue was fixed by
    # switching to a secant on real points). Standard trust-region control
    # -- shrink after a step needed backtracking, grow after a step that
    # succeeded outright -- bounds the extrapolation without needing a
    # second derivative estimate.
    trust_radius = 0.05
    phi_grid_f, pi_grid_f = phi_grid0, pi_grid0
    rfield_grid_f = np.zeros((N_GRID_SIZE, n_nodes))
    rmom_grid_f = np.zeros((N_GRID_SIZE, n_nodes))
    fp_sol_f = None
    bp_sol_f = None
    converged = False
    final_residual = None
    outer_iterations = 0
    newton_fallback_count = 0
    picard_iterations_per_outer = []
    picard_time_total = 0.0
    picard_iters_total = 0

    pending = None  # (pg, pig, rfg, rmg, n_inner, fp_sol, bp_sol, g_pi_values) at the current lam
    for outer in range(MAX_OUTER):
        outer_iterations = outer + 1
        if verbose:
            print(f"[{_lbl}]   outer {outer_iterations}/{MAX_OUTER}: lambda={lam:.6g} "
                  f"-- residual picard_inner", flush=True)
        if pending is not None:
            # Reuse the backtracking line search's own winning evaluation at
            # this lam (prompt 22b) -- it already ran picard_inner here, so
            # re-running it at the top of the loop would be a wasted,
            # duplicate solve.
            pg, pig, rfg, rmg, n_inner, fp_sol, bp_sol, g_pi_values = pending
            pending = None
        else:
            picard_start = time.perf_counter()
            pg, pig, rfg, rmg, n_inner, fp_sol, bp_sol, g_pi_values = picard_inner(
                lam, phi_grid_f, pi_grid_f, g_pi_values
            )
            picard_time_total += time.perf_counter() - picard_start
            picard_iters_total += n_inner
            picard_iterations_per_outer.append(n_inner)
        if pg is None:
            print(f"[{_lbl}] Picard inner failed at outer iter {outer}")
            break

        # Shooting residual: core node (y=+1), final row (N_stop).
        residual = pg[-1, -1] - phi_end
        final_residual = abs(residual)

        phi_grid_f, pi_grid_f, rfield_grid_f, rmom_grid_f = pg, pig, rfg, rmg
        fp_sol_f, bp_sol_f = fp_sol, bp_sol

        if verbose:
            print(f"[{_lbl}]   outer {outer_iterations}/{MAX_OUTER}: residual={residual:.6e} "
                  f"(tol={OUTER_TOL:.3e}), {n_inner} picard sweeps, "
                  f"{picard_time_total:.1f}s picard time so far", flush=True)

        if abs(residual) < OUTER_TOL:
            converged = True
            break
        if outer == MAX_OUTER - 1:
            # Last allowed outer iteration -- the loop is about to exit on
            # its own range() bound, so computing (and backtracking-
            # validating) a further step would be pure waste: its result
            # can never be consumed.
            break

        # Secant step on REAL evaluated (lambda, residual) points (prompt
        # 22b) -- replaces the pre-22b finite-difference Newton probe, which
        # evaluated a THROWAWAY derivative at lambda+dlam with dlam as small
        # as 1e-6. That floor was calibrated when lambda=0 was always an
        # exact fixed point (Finding 1), so the probe never had to resolve a
        # genuine signal against inner-loop noise. Once genuinely coupled, a
        # probe that small is dominated by the inner map's own O(INNER_TOL)
        # sweep-to-sweep noise (observed directly: a huge, unphysical lambda
        # overshoot on the prompt's own acceptance case), and no fixed dlam
        # floor reliably fixes this without either wasting an extra
        # picard_inner call or still being swamped by noise at a poorly-
        # conditioned point. The secant slope between the last TWO real,
        # already-converged outer iterates is a well-separated, zero-extra-
        # cost estimate (lambda moves by whatever the PREVIOUS accepted step
        # was, not an artificial infinitesimal) that reuses evaluations the
        # loop needed anyway.
        if lam_prev is None:
            # Bootstrap: no second point yet, so fall back to the same
            # residual-driven nudge used when the secant slope degenerates.
            step = None
        else:
            dres = residual - residual_prev
            step = -residual * (lam - lam_prev) / dres if abs(dres) > 1e-14 else None
        lam_prev, residual_prev = lam, residual
        if step is None:
            newton_fallback_count += 1
            step = (phi_end - pg[-1, -1]) * 0.1

        # Trust-region clip -- see trust_radius's own comment above.
        if abs(step) > trust_radius:
            step = math.copysign(trust_radius, step)

        # Armijo-style backtracking line search (prompt 22b): now that the
        # shooting problem is genuinely non-trivial (prompt 22a), an
        # undamped full Newton/fallback step was observed to both (a)
        # occasionally overshoot into an unphysical lambda (H_sq_local < 0,
        # picard_inner failing outright), AND (b) even when feasible,
        # overshoot the RESIDUAL itself -- the linearization at the current
        # lambda is a poor global model of a highly nonlinear shooting
        # residual, so a full Newton step can land at a lambda whose
        # residual is LARGER in magnitude than the one just measured. Never
        # exercised before Finding 1's fix, since lambda stayed exactly 0 on
        # the trivial branch. Halve the step until picard_inner succeeds
        # AND strictly reduces |residual|, or give up after MAX_BACKTRACK
        # halvings and take the smallest step tried regardless (bounded,
        # rather than unboundedly shrinking to zero progress).
        best_step = step
        best_result = None
        n_backtracks = 0
        for n_backtracks in range(MAX_BACKTRACK):
            picard_start = time.perf_counter()
            probe_result = picard_inner(lam + step, phi_grid_f, pi_grid_f, g_pi_values)
            picard_time_total += time.perf_counter() - picard_start
            probe_pg = probe_result[0]
            picard_iters_total += probe_result[4]
            picard_iterations_per_outer.append(probe_result[4])
            if probe_pg is not None:
                best_step = step
                best_result = probe_result
                if abs(probe_pg[-1, -1] - phi_end) < abs(residual):
                    break
            step *= 0.5
        else:
            step = best_step
        lam += step
        # Carry the accepted step's own evaluation into the next outer
        # iteration (prompt 22b) -- see the top-of-loop "pending" comment.
        pending = best_result
        # Trust-region update: no backtracking needed -> the linear model
        # was locally trustworthy, so relax the radius; any backtracking ->
        # shrink it so the next step is not similarly overconfident.
        if n_backtracks == 0 and best_result is not None:
            trust_radius = min(trust_radius * 1.2, 1.0e2)
        else:
            trust_radius = max(trust_radius * 0.5, 1.0e-6)

    diagnostics = {
        "compute_time": time.perf_counter() - compute_start,
        "converged": converged,
        "final_residual": final_residual,
        "total_ode_solves": ode_solve_count,
        "outer_iterations": outer_iterations,
        "newton_fallback_count": newton_fallback_count,
        "final_lambda": lam if converged else None,
        "picard_iterations_per_outer": picard_iterations_per_outer,
        "min_picard_iterations": min(picard_iterations_per_outer) if picard_iterations_per_outer else None,
        "max_picard_iterations": max(picard_iterations_per_outer) if picard_iterations_per_outer else None,
        "mean_picard_iterations": (
            sum(picard_iterations_per_outer) / len(picard_iterations_per_outer)
            if picard_iterations_per_outer else None
        ),
        "mean_time_per_picard_iteration": (
            picard_time_total / picard_iters_total if picard_iters_total else None
        ),
        **_instrumentation_diagnostics(),
    }

    if not converged:
        print(f"[{_lbl}] outer loop did not converge "
              f"after {MAX_OUTER} iterations (target tolerance was {OUTER_TOL})")
        return _failure_result(diagnostics)

    return {
        "failure": False,
        "N_total": N_total,
        "N_grid": N_grid.tolist(),
        "phi_grid": phi_grid_f.tolist(),
        "pi_grid": pi_grid_f.tolist(),
        "rfield_grid": rfield_grid_f.tolist(),
        "rmom_grid": rmom_grid_f.tolist(),
        "final_lambda": lam,
        "diagnostics": diagnostics,
        # Final lagged pi_core SAT target (prompt 21a), sampled on N_grid --
        # None when disable_spatial_coupling=True. Stored purely for
        # post-hoc auditability of the closure-independence claim: at
        # convergence this should equal pi_grid_f[:, -1] (the actual core
        # pi(N)) to within the Picard residual tolerance, which is exactly
        # the "SAT penalty forcing -> 0 at the solution" check (prompt 21a
        # acceptance criteria; tests/test_forward_rhs.py's closure-
        # independence regression exercises this directly).
        "g_pi_core_final": g_pi_values.tolist() if g_pi_values is not None else None,
        # Dense-output (continuous, not just N_grid-sampled) forward/response
        # solutions of the converged final Picard iteration -- scipy
        # OdeSolution callables, N -> packed state vector (unpack via
        # forward_rhs.unpack_state / response_rhs.unpack_response_state).
        # Exposed so a caller can resample at an arbitrary finer N resolution
        # (e.g. the MSR action's empirical N-quadrature convergence
        # diagnostic) without re-solving any ODE. Not JSON-serializable and
        # not consumed by the Ray remote function's own returned dict -- a
        # test-only / direct-solve_picard-caller convenience.
        "phi_pi_dense_solution": fp_sol_f,
        "response_dense_solution": bp_sol_f,
    }
