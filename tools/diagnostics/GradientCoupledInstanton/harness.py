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
Shared harness for the GradientCoupledInstanton diagnostic suite.

Every piece here was, until this refactor, copy-pasted (with small drifts)
across three or more of: diagnose_24a_convergence_floor.py,
compare_gradient_full.py, validation_22_resolved_regime.py. Consolidating it
serves two purposes: (1) it stops the three scripts' own stub classes and
setup() functions from silently diverging (compare_gradient_full.py's own
production_phi_end was, at time of writing, still the PRE-22a *degenerate*
formula -- see convergence_floor.py's module docstring), and (2) it gives
every future diagnostic prompt one obvious place to add a helper rather than
a fourth copy.

Design constraints carried over unchanged from the scripts this replaces:
  - No Ray, no Datastore. Every helper here calls production compute-target
    internals directly (``_compute_full_instanton._function``,
    ``picard_module.solve_picard``), exactly the "direct Ray-bypassing
    pattern" the prompt notes describe.
  - No production code is imported for its SIDE EFFECTS -- only its public
    (or, for the deliberate monkeypatch helpers below, module-level private)
    API.
  - ``explore_onion_stiffness.py`` (StubPotential, build_real_trajectory,
    run_case) is treated as an existing, external dependency of this
    package, not reproduced here -- it predates every prompt this suite
    documents and is not itself one of the diagnostic scripts being
    consolidated. If it moves, only the import below needs updating.

Repo path bootstrap: every script this replaces hardcoded
``sys.path.insert(0, "/Users/ds283/Documents/Code/StochasticInstantons")``.
That is preserved as a *fallback* (so this package still runs unmodified on
the machine every design note was produced on) but is now overridable via
the ``STOCHASTIC_INSTANTONS_REPO`` environment variable, so the suite is not
silently broken on a different checkout or a CI machine.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import time
from contextlib import contextmanager, redirect_stdout
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Repo path bootstrap
# ---------------------------------------------------------------------------

_DEFAULT_REPO_PATH = "/Users/ds283/Documents/Code/StochasticInstantons"
_REPO_PATH = os.environ.get("STOCHASTIC_INSTANTONS_REPO", _DEFAULT_REPO_PATH)
if _REPO_PATH not in sys.path:
    sys.path.insert(0, _REPO_PATH)

from explore_onion_stiffness import StubPotential, build_real_trajectory  # noqa: E402
from Numerics.LGLCollocation import LGLCollocationGrid  # noqa: E402
from Numerics.ShootingSolver import ShootingResult  # noqa: E402
from ComputeTargets.GradientCoupledInstanton import picard as picard_module  # noqa: E402
from ComputeTargets.GradientCoupledInstanton.msr_action import compute_msr_action  # noqa: E402
from ComputeTargets.FullInstanton import _compute_full_instanton  # noqa: E402
from Units.Planck_units import Planck_units  # noqa: E402
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion  # noqa: E402

__all__ = [
    "StubPotential", "build_real_trajectory", "LGLCollocationGrid",
    "ShootingResult", "picard_module", "compute_msr_action",
    "_compute_full_instanton", "Planck_units", "MasslessDecoupledDiffusion",
    "N_INIT", "N_FINAL", "ALPHA", "PHI0", "PI0", "ATOL", "RTOL",
    "TrajectoryProxyStub", "setup", "production_phi_end", "H_sq_nl_init_of",
    "fetch_full_instanton", "full_instanton_seed_from",
    "save_json", "load_json", "save_grids_npz", "load_grids_npz",
    "MonkeypatchGuard", "lambda_grid", "classify_inner_status",
    "sweep_evaluate", "capture_last_commit", "output_dir",
]

# ---------------------------------------------------------------------------
# Production-grid defaults (quadratic-minimal.yaml / quadratic-asteroid-small
# .yaml's own shared slice: N_init=19.5, N_final=16.0, alpha=0.1,
# phi0=15 Mp, pi0=0, atol=rtol=1e-8). Every diagnostic below accepts these as
# overridable keyword defaults rather than hardcoding them a second time.
# ---------------------------------------------------------------------------

N_INIT = 19.5
N_FINAL = 16.0
ALPHA = 0.1
PHI0 = 15.0
PI0 = 0.0
ATOL = RTOL = 1.0e-8

_SWEEP_RE = re.compile(r"picard sweep (\d+)/(\d+): max\|dphi\|=([0-9.eE+-]+)")


# ---------------------------------------------------------------------------
# Trajectory-proxy stub -- identical across all three predecessor scripts;
# _compute_full_instanton only ever calls trajectory.get()._potential.
# ---------------------------------------------------------------------------

class _PotentialHolder:
    def __init__(self, potential):
        self._potential = potential


class TrajectoryProxyStub:
    """Duck-typed InflatonTrajectoryProxy stand-in for direct (non-Ray,
    non-Datastore) calls into ``_compute_full_instanton``."""

    def __init__(self, potential):
        self._holder = _PotentialHolder(potential)

    def get(self):
        return self._holder


# ---------------------------------------------------------------------------
# Background setup, cached by (m, phi0, pi0, atol, rtol) -- every predecessor
# script cached only by mass, with phi0/pi0/atol/rtol hardcoded as module
# constants; generalized here since some diagnostics (e.g. a future
# initial-condition sensitivity study) will want to vary them too.
# ---------------------------------------------------------------------------

_TRAJ_CACHE: dict = {}


def setup(m: float, phi0: float = PHI0, pi0: float = PI0,
          atol: float = ATOL, rtol: float = RTOL):
    """Builds (potential, units, traj, dm) for a given mass, caching the
    background-trajectory integration across every diagnostic that reuses
    the same (m, phi0, pi0, atol, rtol)."""
    key = (float(m), float(phi0), float(pi0), float(atol), float(rtol))
    if key in _TRAJ_CACHE:
        return _TRAJ_CACHE[key]
    units = Planck_units()
    potential = StubPotential(m * m, units)
    print(f"[setup m={m:.4g}] integrating background trajectory "
          f"(phi0={phi0}, pi0={pi0})...", flush=True)
    traj = build_real_trajectory(potential, phi0, pi0, atol, rtol)
    print(f"[setup m={m:.4g}]   N_end = {traj.N_end:.6f}", flush=True)
    dm = MasslessDecoupledDiffusion()
    result = (potential, units, traj, dm)
    _TRAJ_CACHE[key] = result
    return result


def production_phi_end(traj, N_init: float = N_INIT, N_final: float = N_FINAL) -> float:
    """The CURRENT production ``phi_end`` formula
    (``ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py``),
    post prompt-22a: ``traj.phi_at(traj.N_end - N_final)``, independent of
    ``delta_Nstar`` and identical to FullInstanton's own convention.

    NOT the pre-22a formula (``traj.phi_at(N_offset + N_total)``) that
    prompt 22's own Finding 1 showed was an exact identity with the
    background trajectory for every delta_Nstar -- see
    archive/prompt22_validation.py's own docstring if you need that history.
    """
    return traj.phi_at(traj.N_end - N_final)


def H_sq_nl_init_of(potential, traj, N_init: float = N_INIT) -> float:
    N_offset = traj.N_end - N_init
    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    return potential.H_sq(phi_init, pi_init)


def fetch_full_instanton(potential, traj, dm, N_init: float, N_final: float,
                          delta_Nstar: float, atol: float = ATOL, rtol: float = RTOL,
                          label: str = "") -> dict:
    """Runs FullInstanton inline (bypassing Ray) at the given grid point,
    returning its own result dict (phi1/phi2/N_sample/diagnostics/msr_action).
    This IS the seed source solve_picard itself uses in production (prompt
    22c) -- calling it here just gives diagnostics the same seed without
    duplicating solve_picard's own internal call.
    """
    N_offset = traj.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    phi_end = production_phi_end(traj, N_init, N_final)
    return _compute_full_instanton._function(
        trajectory=TrajectoryProxyStub(potential), dm=dm,
        phi_init=phi_init, pi_init=pi_init, phi_final=phi_end,
        N_total=N_total, N_sample=list(np.linspace(0, N_total, 300)),
        atol=atol, rtol=rtol, label=label or "FullInstanton seed",
    )


def full_instanton_seed_from(fi_data: dict) -> Optional[dict]:
    """Builds the ``full_instanton_seed`` dict solve_picard expects, from a
    fetch_full_instanton() result -- the same four-key literal that used to
    be retyped at every call site in every predecessor script. Returns None
    if the FullInstanton solve itself failed (solve_picard's own convention
    for "no seed available", falling back to its internal bootstrap)."""
    if fi_data.get("failure", True):
        return None
    return {
        "failure": False,
        "N_sample": fi_data["N_sample"],
        "phi1": fi_data["phi1"],
        "phi2": fi_data["phi2"],
        "final_lambda": fi_data.get("diagnostics", {}).get("final_lambda", 0.0),
    }


# ---------------------------------------------------------------------------
# JSON / CSV / grid (.npz) persistence
# ---------------------------------------------------------------------------

def output_dir(*parts: str) -> str:
    """Resolves a diagnostic output directory relative to this package
    (mirrors the predecessor scripts' own OUT_DIR = .../scripts/<name>_output
    convention, but anchored under this package so it survives the move out
    of out-gradient-coupled-stiffness/scripts/)."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "output", *parts)
    os.makedirs(path, exist_ok=True)
    return path


def save_json(path: str, obj) -> str:
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2, default=str)
    print(f"  -> wrote {path}", flush=True)
    return path


def load_json(path: str):
    with open(path) as fh:
        return json.load(fh)


def save_grids_npz(path: str, *, N_grid, phi_grid, pi_grid, rfield_grid, rmom_grid,
                    grid, N_sample_FI, phi1_FI, phi2_FI, final_lambda, lambda_FI,
                    m, delta_Nstar, alpha) -> str:
    """Canonical schema for a converged GCI solve's full (N, y) grids plus its
    matching FullInstanton seed -- formalizes the ad hoc .npz layout
    diagnostic_4/plot_24b_trajectories.py originally invented between
    themselves. Any new diagnostic wanting to persist full grids for later
    plotting should use this (and load_grids_npz below) rather than a new
    bespoke layout.
    """
    np.savez(
        path,
        N_grid=np.asarray(N_grid), phi_grid=np.asarray(phi_grid),
        pi_grid=np.asarray(pi_grid), rfield_grid=np.asarray(rfield_grid),
        rmom_grid=np.asarray(rmom_grid),
        N_sample_FI=np.asarray(N_sample_FI), phi1_FI=np.asarray(phi1_FI),
        phi2_FI=np.asarray(phi2_FI),
        grid_nodes=grid.nodes, grid_weights=grid.weights,
        final_lambda=final_lambda, lambda_FI=lambda_FI,
        m=m, delta_Nstar=delta_Nstar, alpha=alpha,
    )
    print(f"  -> wrote {path}", flush=True)
    return path


def load_grids_npz(path: str) -> dict:
    """Loads a save_grids_npz() record back into a plain dict of arrays/
    scalars (np.load's own NpzFile is a lazy view; this materializes it so
    callers can pickle/pass it around freely)."""
    data = np.load(path)
    return {key: data[key] for key in data.files}


# ---------------------------------------------------------------------------
# Monkeypatch guard -- every predecessor script re-implemented its own
# try/finally around a module-level attribute override (MAX_OUTER, MAX_INNER,
# OUTER_TOL_FLOOR, solve_shooting itself). Consolidated into one context
# manager so a diagnostic can never forget the `finally` and leave a
# diagnostic-only override live for the rest of a process.
# ---------------------------------------------------------------------------

@contextmanager
def MonkeypatchGuard(module, **overrides):
    """Temporarily sets ``module.<name> = value`` for each item in
    ``overrides``, restoring the original value on exit (even if the body
    raises). Example::

        with MonkeypatchGuard(picard_module, MAX_OUTER=1, MAX_INNER=150):
            ...
    """
    originals = {name: getattr(module, name) for name in overrides}
    try:
        for name, value in overrides.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


# ---------------------------------------------------------------------------
# Lambda-sweep engine (Diagnostic 1/2's shared engine in the original
# diagnose_24a_convergence_floor.py) -- calls solve_picard's own
# evaluate()/commit() closures directly at CHOSEN lambda values instead of
# letting the secant/Armijo/trust-region outer loop pick them, by
# monkeypatching solve_shooting to a single evaluate-and-return stub.
# ---------------------------------------------------------------------------

def classify_inner_status(sweeps: list, success: bool, max_inner: int) -> str:
    """Classifies one evaluate(lambda) call's inner Picard solve from its
    captured 'picard sweep k/MAX_INNER: max|dphi|=X' log lines. Returns one
    of: 'converged', 'floored', 'diverging', 'blown-up'."""
    if not sweeps:
        return "blown-up"  # failed before completing even sweep 1 (ODE failure)
    last_k, last_r = sweeps[-1]
    # INNER_TOL as used by every predecessor script: max(atol*1e4, 1e-4) at
    # the harness's own default atol=1e-8 -- NOT picard_module's own
    # internal INNER_TOL (a different, production convergence tolerance);
    # this is purely a log-classification threshold for the harness's own
    # captured sweep trace.
    inner_tol = max(ATOL * 1.0e4, 1.0e-4)
    if success:
        if last_r < inner_tol:
            return "converged"
        if last_k >= max_inner:
            return "floored"
        return "floored"
    if len(sweeps) >= 3:
        tail = [r for _, r in sweeps[-3:]]
        growing = all(tail[i] < tail[i + 1] for i in range(len(tail) - 1))
        if growing and tail[-1] > picard_module.DIVERGENCE_RESIDUAL_FLOOR:
            return "diverging"
    return "blown-up"


def lambda_grid(lambda_FI: float, extra_negative: bool = True) -> list:
    """~12-point lambda grid bracketing 0 and lambda_FI (Diagnostic 1)."""
    if lambda_FI == 0.0:
        fracs = [0.0, 1e-6, 1e-4, 1e-2, 0.1, 0.5, 1.0, 2.0, -0.1, -0.5, -1.0, -2.0]
        return sorted(set(fracs))
    fracs = [0.0, 1e-4, 1e-2, 0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 3.0]
    lambdas = [f * lambda_FI for f in fracs]
    if extra_negative:
        lambdas += [-0.1 * lambda_FI, -1.0 * lambda_FI]
    return sorted(set(lambdas))


def sweep_evaluate(N_init, N_final, delta_Nstar, alpha, grid, traj, potential, dm,
                    phi_end, lambdas: Iterable[float], label: str = "",
                    full_instanton_seed: Optional[dict] = None,
                    wallclock_budget_seconds: Optional[float] = None,
                    atol: float = ATOL, rtol: float = RTOL) -> list:
    """Monkeypatches solve_shooting to evaluate exactly the given lambda
    values, in order, via solve_picard's OWN evaluate()/commit() closures --
    every other piece of solve_picard (FullInstanton seeding, onion
    interpolation, Part-B rescaling, wall-clock safeguard) runs completely
    unchanged. Returns a list of per-lambda dicts:
        {"lam", "residual", "success", "n_sweeps", "sweep_trace",
         "inner_status", "rfield_max_abs", "rmom_max_abs", "has_nan",
         "wallclock"}

    Each lambda gets its OWN solve_picard call (hence its own independent
    wallclock deadline) -- an expensive/stuck point cannot starve the rest
    of the sweep's budget. Not warm-started between points: every lambda is
    probed from the same sweep-0 seed.
    """
    H_sq_nl_init = H_sq_nl_init_of(potential, traj, N_init)
    records = []

    for lam in lambdas:
        captured: dict = {}

        def fake_solve_shooting(evaluate, commit, lam0, tol, max_outer, _lam=lam, **kwargs):
            residual, success, aux = evaluate(_lam)
            captured["residual"], captured["success"], captured["aux"] = residual, success, aux
            return ShootingResult(
                lam=_lam, converged=False, final_residual=None, outer_iterations=1,
                newton_fallback_count=0, n_evaluations=1, budget_exceeded=False,
            )

        with MonkeypatchGuard(picard_module, solve_shooting=fake_solve_shooting):
            buf = io.StringIO()
            t0 = time.perf_counter()
            with redirect_stdout(buf):
                picard_module.solve_picard(
                    N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
                    traj, potential, dm, atol, rtol, phi_end,
                    instrument_stiffness=False, verbose=True, label=label,
                    full_instanton_seed=full_instanton_seed,
                    wallclock_budget_seconds=wallclock_budget_seconds,
                )
            dt = time.perf_counter() - t0

        text = buf.getvalue()
        sweeps = [(int(m.group(1)), float(m.group(3))) for m in _SWEEP_RE.finditer(text)]
        residual, success, aux = (
            captured.get("residual"), captured.get("success", False), captured.get("aux"),
        )
        rec = {
            "lam": lam, "residual": residual, "success": bool(success),
            "n_sweeps": len(sweeps), "sweep_trace": sweeps,
            "inner_status": classify_inner_status(sweeps, success, picard_module.MAX_INNER),
            "wallclock": dt,
        }
        if success and aux is not None:
            pg, pig, rfg, rmg, fp_sol, bp_sol, g_pi_new = aux
            rfg, rmg = np.asarray(rfg), np.asarray(rmg)
            rec["rfield_max_abs"] = float(np.max(np.abs(rfg))) if rfg.size else None
            rec["rmom_max_abs"] = float(np.max(np.abs(rmg))) if rmg.size else None
            rec["has_nan"] = bool(np.any(~np.isfinite(rfg)) or np.any(~np.isfinite(rmg)))
        else:
            rec["rfield_max_abs"] = None
            rec["rmom_max_abs"] = None
            rec["has_nan"] = None
        records.append(rec)
        print(
            f"  [{label}] lambda={lam:.6g}: residual={residual!r} success={success} "
            f"n_sweeps={rec['n_sweeps']} status={rec['inner_status']} "
            f"rfield_max={rec['rfield_max_abs']!r} ({dt:.1f}s)",
            flush=True,
        )
    return records


@contextmanager
def capture_last_commit():
    """Wraps solve_shooting so the LAST value passed to its own commit()
    closure is captured even if the outer loop never converges (a
    non-convergent solve_picard call discards its grids in
    _failure_result(), so this is the only way to recover the last
    genuinely-committed Picard state -- used by the two-pass
    self-consistency prototype, Diagnostic 3b).

    Yields a dict that will contain {"aux": <last commit(aux) argument>}
    once the wrapped solve_picard call returns (empty if commit() was never
    called, e.g. every evaluation failed outright).
    """
    captured: dict = {}

    def _capturing_solve_shooting(evaluate, commit, *a, _orig=picard_module.solve_shooting, **kw):
        def _wrapped_commit(aux):
            captured["aux"] = aux
            commit(aux)
        return _orig(evaluate, _wrapped_commit, *a, **kw)

    with MonkeypatchGuard(picard_module, solve_shooting=_capturing_solve_shooting):
        yield captured
