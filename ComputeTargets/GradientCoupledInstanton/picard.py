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
"""

import time
from contextlib import contextmanager
from typing import Optional

import numpy as np
import scipy.integrate._ivp.rk as _scipy_rk
from scipy.integrate import solve_ivp

from Interpolation.spline_wrapper import SplineWrapper
from Numerics.OnionCoordinate import delta_s
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

# Number of temporal sample points spanning the local domain [0.0, N_total];
# matches FullInstanton's own floor value (N_GRID = max(300, ...)).
N_GRID_SIZE = 300


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
) -> dict:
    """
    Solve the gradient-coupled instanton BVP over the onion coordinate grid
    by Picard iteration with an outer Newton correction on the shooting
    parameter lambda = P1-equivalent terminal Lagrange multiplier.

    Boundary conditions (local N; see module docstring for the N convention):
        phi(y_j, N=0.0) = phi_init, pi(y_j, N=0.0) = pi_init  (uniform in y)
        phi(y=+1, N=N_total) = phi_end   [shooting condition on lambda]

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

    OUTER_TOL = max(atol * 100.0, 1e-6)
    INNER_TOL = atol * 10.0

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

    def _fwd_rhs(N, y, rfield_splines, rmom_splines):
        return forward_rhs(
            N, y, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
            rfield_splines, rmom_splines, diffusion_model,
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

    bg_sol, bg_step_stats = _solve_ivp_instrumented(
        instrument_stiffness,
        lambda N, y: _fwd_rhs(N, y, zero_splines, zero_splines),
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

    def picard_inner(lam: float, phi_grid_in: np.ndarray, pi_grid_in: np.ndarray):
        """
        Run Picard iteration for fixed lambda. Returns grids or Nones, plus
        the dense-output (`dense_output=True`) solve_ivp solutions of the
        *last* inner iteration's forward/backward passes -- fp_sol maps
        N -> packed forward state (unpack via forward_rhs.unpack_state),
        bp_sol maps N -> packed response state (unpack via
        response_rhs.unpack_response_state). Exposed so callers (the MSR
        action convergence diagnostic) can resample at an arbitrary, finer
        N resolution without re-solving any ODE.
        """
        nonlocal ode_solve_count
        phi_grid = phi_grid_in.copy()
        pi_grid = pi_grid_in.copy()
        rfield_grid = np.zeros((N_GRID_SIZE, n_nodes))
        rmom_grid = np.zeros((N_GRID_SIZE, n_nodes))
        n_inner_iters = 0
        fp_sol = None
        bp_sol = None

        for _ in range(MAX_INNER):
            sweep_start = time.perf_counter() if (instrument_stiffness or verbose) else None
            n_inner_iters += 1
            phi_splines = _build_node_splines(N_grid, phi_grid, y_transform='linear')
            pi_splines = _build_node_splines(N_grid, pi_grid, y_transform='linear')

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
                return None, None, None, None, n_inner_iters, None, None

            response_y = bp.y[:, ::-1]
            rfield_grid, rmom_grid = _unpack_response_grid(response_y, N_grid)

            rfield_splines = _build_node_splines(N_grid, rfield_grid, y_transform='sinh')
            rmom_splines = _build_node_splines(N_grid, rmom_grid, y_transform='sinh')

            # Forward pass, now sourced by the just-computed response fields.
            fp, fp_step_stats = _solve_ivp_instrumented(
                instrument_stiffness,
                lambda N, y: _fwd_rhs(N, y, rfield_splines, rmom_splines),
                (N_start, N_stop), state_init, method="RK45",
                t_eval=N_grid, dense_output=True, atol=atol, rtol=rtol,
            )
            ode_solve_count += 1
            if fp_step_stats is not None:
                fwd_rk45_stats.append(fp_step_stats)
            if not fp.success:
                return None, None, None, None, n_inner_iters, None, None

            phi_grid_new, pi_grid_new = _unpack_grid(fp.y, N_grid)
            inner_res = np.max(np.abs(phi_grid_new - phi_grid))
            phi_grid, pi_grid = phi_grid_new, pi_grid_new
            fp_sol, bp_sol = fp.sol, bp.sol
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
            if inner_res < INNER_TOL:
                break

        return phi_grid, pi_grid, rfield_grid, rmom_grid, n_inner_iters, fp_sol, bp_sol

    # ── Outer Newton loop on lambda ────────────────────────────────────────
    lam = 0.0
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

    for outer in range(MAX_OUTER):
        outer_iterations = outer + 1
        if verbose:
            print(f"[{_lbl}]   outer {outer_iterations}/{MAX_OUTER}: lambda={lam:.6g} "
                  f"-- residual picard_inner", flush=True)
        picard_start = time.perf_counter()
        pg, pig, rfg, rmg, n_inner, fp_sol, bp_sol = picard_inner(lam, phi_grid_f, pi_grid_f)
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

        # Finite-difference Newton step.
        dlam = max(abs(lam) * 1e-4, 1e-6)
        if verbose:
            print(f"[{_lbl}]   outer {outer_iterations}/{MAX_OUTER}: "
                  f"Newton derivative probe at lambda+dlam={lam + dlam:.6g}", flush=True)
        picard_start = time.perf_counter()
        pg_p, _, _, _, n_inner_p, _, _ = picard_inner(lam + dlam, phi_grid_f, pi_grid_f)
        picard_time_total += time.perf_counter() - picard_start
        picard_iters_total += n_inner_p
        picard_iterations_per_outer.append(n_inner_p)
        if pg_p is not None:
            dres_dlam = (pg_p[-1, -1] - pg[-1, -1]) / dlam
            if abs(dres_dlam) > 1e-14:
                lam -= residual / dres_dlam
                continue
        # Fallback nudge.
        newton_fallback_count += 1
        lam += (phi_end - pg[-1, -1]) * 0.1

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
