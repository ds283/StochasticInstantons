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
Convergence-floor diagnostics for GradientCoupledInstanton (prompts 24a/24b,
plus new Diagnostic 8). Refactor of the original
``diagnose_24a_convergence_floor.py`` onto the shared harness (harness.py) --
every diagnostic below is behaviourally identical to its prompt-24a/24b
original except where noted; only the setup/fetch/IO/monkeypatch boilerplate
moved.

Diagnostics 1-7 reproduce prompts 24a/24b exactly (see
.documents/gradient-coupled-instanton/24a-diagnose-convergence-floor.md and
24b-lambda-conversion-seeding-and-trajectory-validation.md for the narrative
write-ups these numbers back). Diagnostic 8 is new: it resurrects prompt 22's
own Studies A/C (n-convergence, tau/alpha regularity sensitivity), which were
blocked at the time by the phi_end degeneracy and Picard divergence findings
(22-validation.md) and are now runnable now that non-trivial converged
solutions exist (24b).

Diagnostic 8's alpha-sensitivity half is fully implemented (alpha is already
a first-class solve_picard parameter, no production code change needed). Its
tau-sensitivity half is NOT yet runnable: tau is currently a hardcoded local
(``tau = abs(A_core)``) inside forward_rhs.py, not a parameter threaded
through solve_picard, so there is no monkeypatch point for it (unlike
OUTER_TOL_FLOOR, which prompt 24b already extracted into a module constant
for exactly this reason). Running the tau study needs a small, explicitly-
scoped production change first (add a ``tau_multiplier: float = 1.0``
parameter, default reproducing current behaviour bit-for-bit) -- see
DIAGNOSTICS_SUITE.md's "Known gaps" section. diagnostic_8's tau branch
raises NotImplementedError with this same explanation rather than silently
no-op'ing or guessing at an implementation of a production change nobody has
reviewed yet.

Run as a module:
    python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor \\
        --diagnostic 4 8 --alpha-values 0.01,0.05,0.1,0.3
    python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor --diagnostic all
"""

from __future__ import annotations

import argparse
import io
import time
from contextlib import redirect_stdout

import numpy as np

from . import harness as h

OUT_DIR = h.output_dir("convergence_floor")

MASSES = [1.0e-2, 1.0e-3, 1.0e-4, 1.0e-5]
N_COLLOC = 5


# ---------------------------------------------------------------------------
# Diagnostic 1 + 2 -- evaluate(lambda) sweep per mass + Part-B linearity check
# ---------------------------------------------------------------------------

def diagnostic_1_and_2(masses=MASSES, delta_Nstar: float = 1.0):
    print("\n" + "=" * 78, flush=True)
    print("DIAGNOSTIC 1+2: evaluate(lambda) sweep per mass + Part-B validation", flush=True)
    print("=" * 78, flush=True)

    grid = h.LGLCollocationGrid(N_COLLOC)
    all_results = {}

    for m in masses:
        potential, units, traj, dm = h.setup(m)
        phi_end = h.production_phi_end(traj)
        fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL,
                                          delta_Nstar, label=f"m={m:.4g} FI seed")
        lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda") if not fi_data.get("failure") else None
        lambda_FI = lambda_FI if lambda_FI is not None else (fi_data.get("final_lambda", 0.0) or 0.0)
        print(f"[m={m:.4g}] FullInstanton: failure={fi_data.get('failure')} "
              f"lambda_FI={lambda_FI!r} msr_action={fi_data.get('msr_action')!r}", flush=True)

        full_instanton_seed = h.full_instanton_seed_from(fi_data)

        # m=1e-2's per-Picard-sweep cost is high enough (Phase A:
        # mean_time_per_picard_iteration~82s) that a full 12-point sweep at a
        # generous per-point budget is prohibitively slow for a "cheap"
        # diagnostic -- fewer points, larger per-point budget there; the
        # other three masses get the full grid at a smaller budget.
        if m >= 1.0e-2:
            lambdas = [f * lambda_FI for f in (0.0, 0.1, 0.5, 1.0, 1.5, -0.1)]
            per_point_budget = 240.0
        else:
            lambdas = h.lambda_grid(lambda_FI)
            per_point_budget = 90.0
        print(f"[m={m:.4g}] sweeping {len(lambdas)} lambda values "
              f"(budget={per_point_budget}s/pt): {lambdas}", flush=True)

        records = h.sweep_evaluate(
            h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, grid, traj, potential, dm,
            phi_end, lambdas, label=f"D1 m={m:.4g}",
            full_instanton_seed=full_instanton_seed,
            wallclock_budget_seconds=per_point_budget,
        )
        all_results[f"{m:.4g}"] = {
            "m": m, "lambda_FI": lambda_FI,
            "fi_msr_action": fi_data.get("msr_action"),
            "records": records,
        }

    h.save_json(f"{OUT_DIR}/diagnostic1_lambda_sweep.json", all_results)

    print("\n--- Diagnostic 2: linearity / r_tilde boundedness check ---", flush=True)
    lin_report = {}
    for key, data in all_results.items():
        recs = [r for r in data["records"] if r["success"] and r["rfield_max_abs"] is not None]
        if len(recs) < 2:
            lin_report[key] = {"note": "insufficient successful evaluations to check linearity"}
            continue
        nonzero = [r for r in recs if r["lam"] != 0.0]
        ratios = [(r["lam"], r["rfield_max_abs"] / abs(r["lam"]), r["rfield_max_abs"]) for r in nonzero]
        lin_report[key] = {
            "lam_ratio_rfieldmax_pairs": ratios,
            "any_nan_or_inf": any(r["has_nan"] for r in recs),
        }
        print(f"  [m={key}] (lambda, max|rfield|/|lambda|=max|r_tilde|_approx, max|rfield|): {ratios}", flush=True)
    h.save_json(f"{OUT_DIR}/diagnostic2_linearity.json", lin_report)

    return all_results


# ---------------------------------------------------------------------------
# Diagnostic 3 -- fixed-target (pi_core SAT) bias + two-pass prototype
# ---------------------------------------------------------------------------

def diagnostic_3(m: float = 1.0e-3, delta_Nstar: float = 1.0,
                  deltas=(0.0, 0.01, -0.01, 0.03), max_outer_cap: int = 20,
                  wallclock_budget_seconds: float = 500.0):
    print("\n" + "=" * 78, flush=True)
    print(f"DIAGNOSTIC 3: fixed-target bias + two-pass prototype (m={m:.4g})", flush=True)
    print("=" * 78, flush=True)

    grid = h.LGLCollocationGrid(N_COLLOC)
    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)
    H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)
    fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, delta_Nstar, label="D3 FI seed")
    lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda", 0.0)
    print(f"[D3] FullInstanton: lambda_FI={lambda_FI!r} msr_action={fi_data.get('msr_action')!r}", flush=True)

    # ---- 3a: direct bias test -- perturb g_pi (phi2) by a uniform additive
    # shift and see whether the floored outer residual tracks it.
    bias_records = []
    with h.MonkeypatchGuard(h.picard_module, MAX_OUTER=max_outer_cap):
        for delta in deltas:
            phi2_perturbed = np.asarray(fi_data["phi2"]) + delta
            seed = {
                "failure": False, "N_sample": fi_data["N_sample"],
                "phi1": fi_data["phi1"], "phi2": phi2_perturbed.tolist(),
                "final_lambda": lambda_FI,
            }
            buf = io.StringIO()
            t0 = time.perf_counter()
            with redirect_stdout(buf):
                result = h.picard_module.solve_picard(
                    h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid,
                    traj, potential, dm, h.ATOL, h.RTOL, phi_end,
                    instrument_stiffness=False, verbose=False,
                    full_instanton_seed=seed,
                    wallclock_budget_seconds=wallclock_budget_seconds,
                    label=f"D3 bias delta={delta:+.4g}",
                )
            dt = time.perf_counter() - t0
            diag = result.get("diagnostics", {})
            rec = {
                "delta": delta, "final_residual": diag.get("final_residual"),
                "outer_residual_history": diag.get("outer_residual_history"),
                "bailout_tag": diag.get("bailout_tag"), "converged": diag.get("converged"),
                "wallclock": dt,
            }
            bias_records.append(rec)
            print(f"  [D3 bias] delta={delta:+.4g}: final_residual={rec['final_residual']!r} "
                  f"bailout={rec['bailout_tag']} ({dt:.1f}s)", flush=True)
    h.save_json(f"{OUT_DIR}/diagnostic3_bias.json", bias_records)

    # ---- 3b: two-pass self-consistency prototype (a diagnostic PROBE, not a
    # production algorithm -- prompt 24a's own closeout classifies this as a
    # clean negative: the naive full-replacement update rule diverges).
    print("\n--- Diagnostic 3b: two-pass outer self-consistency prototype ---", flush=True)
    pass_records = []
    with h.MonkeypatchGuard(h.picard_module, MAX_OUTER=max_outer_cap):
        seed = {
            "failure": False, "N_sample": fi_data["N_sample"],
            "phi1": fi_data["phi1"], "phi2": fi_data["phi2"], "final_lambda": lambda_FI,
        }
        n_passes = 3
        for p in range(n_passes):
            t0 = time.perf_counter()
            with h.capture_last_commit() as captured_commit:
                buf = io.StringIO()
                with redirect_stdout(buf):
                    result = h.picard_module.solve_picard(
                        h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid,
                        traj, potential, dm, h.ATOL, h.RTOL, phi_end,
                        instrument_stiffness=False, verbose=False,
                        full_instanton_seed=seed,
                        wallclock_budget_seconds=wallclock_budget_seconds,
                        label=f"D3b pass={p}",
                    )
            dt = time.perf_counter() - t0
            diag = result.get("diagnostics", {})
            rec = {
                "pass": p, "final_residual": diag.get("final_residual"),
                "bailout_tag": diag.get("bailout_tag"), "converged": diag.get("converged"),
                "final_lambda": result.get("final_lambda"), "wallclock": dt,
            }
            pass_records.append(rec)
            print(f"  [D3b] pass={p}: final_residual={rec['final_residual']!r} "
                  f"bailout={rec['bailout_tag']} final_lambda={rec['final_lambda']!r} ({dt:.1f}s)", flush=True)

            if result.get("failure", False):
                if captured_commit.get("aux") is None:
                    print(f"  [D3b] pass={p}: no committed grid available at all -- "
                          f"stopping two-pass early", flush=True)
                    break
                pg, pig, rfg, rmg, fp_sol, bp_sol, g_pi_new = captured_commit["aux"]
                phi_grid, pi_grid = np.asarray(pg), np.asarray(pig)
                N_grid_arr = np.asarray(result["N_grid"]) if result.get("N_grid") else None
                if N_grid_arr is None or len(N_grid_arr) != phi_grid.shape[0]:
                    N_total = (h.N_INIT - h.N_FINAL) + delta_Nstar
                    N_grid_arr = np.linspace(0.0, N_total, phi_grid.shape[0])
            else:
                phi_grid = np.asarray(result["phi_grid"])
                pi_grid = np.asarray(result["pi_grid"])
                N_grid_arr = np.asarray(result["N_grid"])
            new_lambda = result.get("final_lambda") or lambda_FI
            seed = {
                "failure": False, "N_sample": N_grid_arr.tolist(),
                "phi1": phi_grid[:, -1].tolist(), "phi2": pi_grid[:, -1].tolist(),
                "final_lambda": new_lambda,
            }
    h.save_json(f"{OUT_DIR}/diagnostic3b_two_pass.json", pass_records)

    return {"bias": bias_records, "two_pass": pass_records, "lambda_FI": lambda_FI}


# ---------------------------------------------------------------------------
# Diagnostic 4 -- small delta_Nstar walk (real outer shooting)
# ---------------------------------------------------------------------------

def diagnostic_4(m: float = 1.0e-2, delta_Nstars=(0.2, 0.3, 0.5, 0.7),
                  wallclock_budget: float = 600.0, persist_grids: bool = True):
    """Prompts 24a/24b's own delta_Nstar walk: real outer shooting (the
    prompt-24b lambda-seed conversion + corridor bound apply automatically,
    since solve_picard itself carries them -- no harness-side change
    needed). persist_grids=True additionally writes each converged point's
    full grids via harness.save_grids_npz, for trajectory_plots.py."""
    print("\n" + "=" * 78, flush=True)
    print(f"DIAGNOSTIC 4: delta_Nstar walk for first non-trivial convergence (m={m:.4g})", flush=True)
    print("=" * 78, flush=True)

    grid = h.LGLCollocationGrid(N_COLLOC)
    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)
    H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)

    rows = []
    for dNstar in delta_Nstars:
        fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, dNstar,
                                          label=f"D4 dNstar={dNstar} FI seed")
        lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda", 0.0)
        full_instanton_seed = h.full_instanton_seed_from(fi_data)
        t0 = time.perf_counter()
        result = h.picard_module.solve_picard(
            h.N_INIT, h.N_FINAL, dNstar, h.ALPHA, H_sq_nl_init, grid, traj, potential, dm,
            h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
            full_instanton_seed=full_instanton_seed,
            wallclock_budget_seconds=wallclock_budget,
            label=f"D4 dNstar={dNstar}",
        )
        dt = time.perf_counter() - t0
        diag = result.get("diagnostics", {})
        row = {
            "delta_Nstar": dNstar, "lambda_FI": lambda_FI,
            "fi_msr_action": fi_data.get("msr_action"),
            "converged": diag.get("converged"), "final_residual": diag.get("final_residual"),
            "bailout_tag": diag.get("bailout_tag"), "final_lambda": result.get("final_lambda"),
            "wallclock": dt,
            "outer_iterations": diag.get("outer_iterations"),
            "n_bracket_evaluations": diag.get("n_bracket_evaluations"),
            "lambda_seed": diag.get("lambda_seed"),
            "lambda_c_positive": diag.get("lambda_c_positive"),
            "lambda_c_negative": diag.get("lambda_c_negative"),
            "gradient_enhancement_E": diag.get("gradient_enhancement_E"),
        }
        if diag.get("converged"):
            phi_grid = np.asarray(result["phi_grid"])
            pi_grid = np.asarray(result["pi_grid"])
            rfield_grid = np.asarray(result["rfield_grid"])
            rmom_grid = np.asarray(result["rmom_grid"])
            N_grid_arr = np.asarray(result["N_grid"])
            msr = h.compute_msr_action(
                N_grid_arr, phi_grid, pi_grid, rfield_grid, rmom_grid, grid, potential, dm,
                H_sq_nl_init, h.ALPHA,
            )
            row["msr_action"] = msr
            row["S_ratio_GCI_over_FI"] = (
                msr / fi_data["msr_action"] if fi_data.get("msr_action") not in (None, 0.0) else None
            )
            if persist_grids:
                npz_path = f"{OUT_DIR}/diagnostic4_grids_m{m:.4g}_dNstar{dNstar}.npz"
                h.save_grids_npz(
                    npz_path, N_grid=N_grid_arr, phi_grid=phi_grid, pi_grid=pi_grid,
                    rfield_grid=rfield_grid, rmom_grid=rmom_grid, grid=grid,
                    N_sample_FI=fi_data["N_sample"], phi1_FI=fi_data["phi1"],
                    phi2_FI=fi_data["phi2"], final_lambda=result["final_lambda"],
                    lambda_FI=lambda_FI, m=m, delta_Nstar=dNstar, alpha=h.ALPHA,
                )
                row["grids_npz"] = npz_path
        else:
            row["msr_action"] = None
            row["S_ratio_GCI_over_FI"] = None
        rows.append(row)
        print(f"[D4] delta_Nstar={dNstar}: converged={row['converged']} "
              f"final_lambda={row['final_lambda']!r} msr_action={row['msr_action']!r} "
              f"E={row['gradient_enhancement_E']!r} outer_iters={row['outer_iterations']!r} "
              f"bailout={row['bailout_tag']} ({dt:.1f}s)", flush=True)

    h.save_json(f"{OUT_DIR}/diagnostic4_delta_nstar_walk.json", rows)
    return rows


# ---------------------------------------------------------------------------
# Diagnostic 5 -- delta_Nstar=1.0 retry across all four masses
# ---------------------------------------------------------------------------

def diagnostic_5_delta_nstar_1(masses=MASSES, delta_Nstar: float = 1.0):
    print("\n" + "=" * 78, flush=True)
    print("DIAGNOSTIC 5 (Part C): delta_Nstar=1.0 retry across all four masses", flush=True)
    print("=" * 78, flush=True)

    grid = h.LGLCollocationGrid(N_COLLOC)
    rows = []
    for m in masses:
        potential, units, traj, dm = h.setup(m)
        phi_end = h.production_phi_end(traj)
        H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)
        fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, delta_Nstar,
                                          label=f"D5 m={m:.4g} FI seed")
        lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda", 0.0)
        full_instanton_seed = h.full_instanton_seed_from(fi_data)
        budget = 900.0 if m >= 1.0e-2 else 300.0
        t0 = time.perf_counter()
        result = h.picard_module.solve_picard(
            h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid, traj, potential, dm,
            h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
            full_instanton_seed=full_instanton_seed,
            wallclock_budget_seconds=budget, label=f"D5 m={m:.4g}",
        )
        dt = time.perf_counter() - t0
        diag = result.get("diagnostics", {})
        row = {
            "m": m, "delta_Nstar": delta_Nstar, "lambda_FI": lambda_FI,
            "converged": diag.get("converged"), "final_residual": diag.get("final_residual"),
            "bailout_tag": diag.get("bailout_tag"), "bailout_reason": diag.get("bailout_reason"),
            "final_lambda": result.get("final_lambda"),
            "lambda_seed": diag.get("lambda_seed"),
            "lambda_c_positive": diag.get("lambda_c_positive"),
            "lambda_c_negative": diag.get("lambda_c_negative"),
            "gradient_enhancement_E": diag.get("gradient_enhancement_E"),
            "outer_iterations": diag.get("outer_iterations"),
            "wallclock": dt, "wallclock_budget": budget,
        }
        if diag.get("converged"):
            phi_grid = np.asarray(result["phi_grid"])
            pi_grid = np.asarray(result["pi_grid"])
            rfield_grid = np.asarray(result["rfield_grid"])
            rmom_grid = np.asarray(result["rmom_grid"])
            N_grid_arr = np.asarray(result["N_grid"])
            row["msr_action"] = h.compute_msr_action(
                N_grid_arr, phi_grid, pi_grid, rfield_grid, rmom_grid, grid, potential, dm,
                H_sq_nl_init, h.ALPHA,
            )
        else:
            row["msr_action"] = None
        rows.append(row)
        print(f"[D5] m={m:.4g}: converged={row['converged']} final_lambda={row['final_lambda']!r} "
              f"E={row['gradient_enhancement_E']!r} bailout={row['bailout_tag']} ({dt:.1f}s)", flush=True)

    h.save_json(f"{OUT_DIR}/diagnostic5_delta_nstar1_retry.json", rows)
    return rows


# ---------------------------------------------------------------------------
# Diagnostic 6 -- n_collocation_points retry at a known-converged point
# ---------------------------------------------------------------------------

def diagnostic_6_n_colloc(m: float = 1.0e-2, delta_Nstar: float = 0.5,
                           ns=(9, 17), wallclock_budget: float = 900.0):
    print("\n" + "=" * 78, flush=True)
    print(f"DIAGNOSTIC 6 (Part C): n_collocation_points retry at m={m:.4g}, delta_Nstar={delta_Nstar}", flush=True)
    print("=" * 78, flush=True)

    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)
    H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)
    fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, delta_Nstar, label="D6 FI seed")
    lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda", 0.0)
    full_instanton_seed = h.full_instanton_seed_from(fi_data)

    rows = []
    for n in ns:
        grid = h.LGLCollocationGrid(n)
        t0 = time.perf_counter()
        result = h.picard_module.solve_picard(
            h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid, traj, potential, dm,
            h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
            full_instanton_seed=full_instanton_seed,
            wallclock_budget_seconds=wallclock_budget, label=f"D6 n={n}",
        )
        dt = time.perf_counter() - t0
        diag = result.get("diagnostics", {})
        row = {
            "n_collocation_points": n, "converged": diag.get("converged"),
            "final_residual": diag.get("final_residual"), "bailout_tag": diag.get("bailout_tag"),
            "final_lambda": result.get("final_lambda"),
            "gradient_enhancement_E": diag.get("gradient_enhancement_E"),
            "outer_iterations": diag.get("outer_iterations"), "wallclock": dt,
        }
        if diag.get("converged"):
            phi_grid = np.asarray(result["phi_grid"])
            pi_grid = np.asarray(result["pi_grid"])
            rfield_grid = np.asarray(result["rfield_grid"])
            rmom_grid = np.asarray(result["rmom_grid"])
            N_grid_arr = np.asarray(result["N_grid"])
            row["msr_action"] = h.compute_msr_action(
                N_grid_arr, phi_grid, pi_grid, rfield_grid, rmom_grid, grid, potential, dm,
                H_sq_nl_init, h.ALPHA,
            )
        else:
            row["msr_action"] = None
        rows.append(row)
        print(f"[D6] n={n}: converged={row['converged']} final_lambda={row['final_lambda']!r} "
              f"E={row['gradient_enhancement_E']!r} bailout={row['bailout_tag']} ({dt:.1f}s)", flush=True)

    h.save_json(f"{OUT_DIR}/diagnostic6_n_colloc_retry.json", rows)
    return rows


# ---------------------------------------------------------------------------
# Diagnostic 7 -- OUTER_TOL sensitivity
# ---------------------------------------------------------------------------

def diagnostic_7_outer_tol_sensitivity(m: float = 1.0e-2, delta_Nstars=(0.3, 0.5, 0.7),
                                        tol_floors=(1.0e-2, 1.0e-3, 1.0e-4),
                                        wallclock_budget: float = 300.0):
    """Does OUTER_TOL_FLOOR do physics? Sweeps it at every already-converged
    (m=1e-2, delta_Nstar) point and reports whether msr_action/final_lambda
    move (prompt 24b's own finding: they don't, to bit-for-bit precision)."""
    print("\n" + "=" * 78, flush=True)
    print("DIAGNOSTIC 7: OUTER_TOL sensitivity (does the tolerance do physics?)", flush=True)
    print("=" * 78, flush=True)

    grid = h.LGLCollocationGrid(N_COLLOC)
    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)
    H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)

    rows = []
    for dNstar in delta_Nstars:
        fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, dNstar,
                                          label=f"D7 dNstar={dNstar} FI seed")
        full_instanton_seed = h.full_instanton_seed_from(fi_data)
        for floor in tol_floors:
            with h.MonkeypatchGuard(h.picard_module, OUTER_TOL_FLOOR=floor):
                t0 = time.perf_counter()
                result = h.picard_module.solve_picard(
                    h.N_INIT, h.N_FINAL, dNstar, h.ALPHA, H_sq_nl_init, grid, traj, potential, dm,
                    h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
                    full_instanton_seed=full_instanton_seed,
                    wallclock_budget_seconds=wallclock_budget,
                    label=f"D7 dNstar={dNstar} floor={floor:.1e}",
                )
            dt = time.perf_counter() - t0
            diag = result.get("diagnostics", {})
            row = {
                "delta_Nstar": dNstar, "outer_tol_floor": floor,
                "converged": diag.get("converged"), "final_residual": diag.get("final_residual"),
                "final_lambda": result.get("final_lambda"),
                "outer_iterations": diag.get("outer_iterations"),
                "bailout_tag": diag.get("bailout_tag"), "wallclock": dt,
            }
            if diag.get("converged"):
                phi_grid = np.asarray(result["phi_grid"])
                pi_grid = np.asarray(result["pi_grid"])
                rfield_grid = np.asarray(result["rfield_grid"])
                rmom_grid = np.asarray(result["rmom_grid"])
                N_grid_arr = np.asarray(result["N_grid"])
                row["msr_action"] = h.compute_msr_action(
                    N_grid_arr, phi_grid, pi_grid, rfield_grid, rmom_grid, grid, potential, dm,
                    H_sq_nl_init, h.ALPHA,
                )
            else:
                row["msr_action"] = None
            rows.append(row)
            print(f"[D7] dNstar={dNstar} floor={floor:.1e}: converged={row['converged']} "
                  f"final_lambda={row['final_lambda']!r} msr_action={row['msr_action']!r} "
                  f"outer_iters={row['outer_iterations']!r} ({dt:.1f}s)", flush=True)

    h.save_json(f"{OUT_DIR}/diagnostic7_outer_tol_sensitivity.json", rows)
    return rows


# ---------------------------------------------------------------------------
# Diagnostic 8 -- alpha/tau regularity sensitivity (prompt 22's Study C,
# resurrected). See module docstring for why the tau half is not runnable
# yet.
# ---------------------------------------------------------------------------

def diagnostic_8_alpha_sensitivity(m: float = 1.0e-2, delta_Nstars=(0.2, 0.3, 0.5, 0.7),
                                    alpha_values=(0.01, 0.05, 0.1, 0.3),
                                    wallclock_budget: float = 600.0):
    """Prompt 22 Study C (regularity), alpha half: re-solves every converged
    24b point at each alpha in alpha_values. alpha is already a first-class
    solve_picard parameter, so this needs no production code change.

    Interpretation: alpha is a REGULARIZATION of the N_init coordinate
    singularity, not physics (onion_model.tex, Numerics_OnionCoordinate.py).
    A convergent discretization's msr_action/final_lambda/max-epsilon should
    be stable (to within the same few-percent search-path noise the
    OUTER_TOL check already established, prompt 24b) as alpha varies over
    this range; a strong alpha-dependence indicates the solution is
    resolving the regularization scale itself rather than converging to a
    genuine alpha->0 continuum limit.
    """
    print("\n" + "=" * 78, flush=True)
    print("DIAGNOSTIC 8a: alpha_regularization sensitivity at every converged point", flush=True)
    print("=" * 78, flush=True)

    grid = h.LGLCollocationGrid(N_COLLOC)
    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)

    rows = []
    for dNstar in delta_Nstars:
        for alpha in alpha_values:
            # H_sq_nl_init depends on (phi_init, pi_init) only, not on alpha,
            # but is recomputed per-alpha here for symmetry with the other
            # diagnostics and because it is cheap (no ODE solve).
            H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)
            fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, dNstar,
                                              label=f"D8a dNstar={dNstar} alpha={alpha} FI seed")
            full_instanton_seed = h.full_instanton_seed_from(fi_data)
            t0 = time.perf_counter()
            result = h.picard_module.solve_picard(
                h.N_INIT, h.N_FINAL, dNstar, alpha, H_sq_nl_init, grid, traj, potential, dm,
                h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
                full_instanton_seed=full_instanton_seed,
                wallclock_budget_seconds=wallclock_budget,
                label=f"D8a dNstar={dNstar} alpha={alpha}",
            )
            dt = time.perf_counter() - t0
            diag = result.get("diagnostics", {})
            row = {
                "delta_Nstar": dNstar, "alpha": alpha,
                "converged": diag.get("converged"), "final_residual": diag.get("final_residual"),
                "bailout_tag": diag.get("bailout_tag"), "final_lambda": result.get("final_lambda"),
                "gradient_enhancement_E": diag.get("gradient_enhancement_E"),
                "outer_iterations": diag.get("outer_iterations"), "wallclock": dt,
            }
            if diag.get("converged"):
                phi_grid = np.asarray(result["phi_grid"])
                pi_grid = np.asarray(result["pi_grid"])
                rfield_grid = np.asarray(result["rfield_grid"])
                rmom_grid = np.asarray(result["rmom_grid"])
                N_grid_arr = np.asarray(result["N_grid"])
                row["msr_action"] = h.compute_msr_action(
                    N_grid_arr, phi_grid, pi_grid, rfield_grid, rmom_grid, grid, potential, dm,
                    H_sq_nl_init, alpha,
                )
                row["max_epsilon_core"] = float(np.max(0.5 * pi_grid[:, -1] ** 2))
            else:
                row["msr_action"] = None
                row["max_epsilon_core"] = None
            rows.append(row)
            print(f"[D8a] dNstar={dNstar} alpha={alpha}: converged={row['converged']} "
                  f"final_lambda={row['final_lambda']!r} msr_action={row['msr_action']!r} "
                  f"max_eps={row['max_epsilon_core']!r} ({dt:.1f}s)", flush=True)

    h.save_json(f"{OUT_DIR}/diagnostic8a_alpha_sensitivity.json", rows)
    return rows


def diagnostic_8_tau_sensitivity(*args, **kwargs):
    """NOT YET RUNNABLE -- see this module's own docstring and
    DIAGNOSTICS_SUITE.md's "Known gaps" section. tau is a hardcoded local in
    forward_rhs.py (``tau = abs(A_core)``), not a solve_picard parameter, so
    there is no monkeypatch point available from outside production code.
    Raises immediately rather than silently doing nothing or guessing at an
    un-reviewed production change.
    """
    raise NotImplementedError(
        "diagnostic_8_tau_sensitivity requires a small production change "
        "first: thread a `tau_multiplier: float = 1.0` parameter (default "
        "reproducing current behaviour bit-for-bit) from "
        "ComputeTargets/GradientCoupledInstanton/forward_rhs.py's core SAT "
        "penalty through picard.solve_picard. See DIAGNOSTICS_SUITE.md's "
        "'Known gaps' section for the scoped, single-commit prompt this "
        "needs before this function can be implemented."
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

_DIAGNOSTIC_DISPATCH = {
    "1": lambda args: diagnostic_1_and_2(),
    "2": lambda args: diagnostic_1_and_2(),  # 1 and 2 share one run; alias
    "3": lambda args: diagnostic_3(),
    "4": lambda args: diagnostic_4(),
    "5": lambda args: diagnostic_5_delta_nstar_1(),
    "6": lambda args: diagnostic_6_n_colloc(),
    "7": lambda args: diagnostic_7_outer_tol_sensitivity(),
    "8a": lambda args: diagnostic_8_alpha_sensitivity(
        alpha_values=tuple(float(x) for x in args.alpha_values.split(",")),
    ),
    "8t": lambda args: diagnostic_8_tau_sensitivity(),
}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GradientCoupledInstanton convergence-floor diagnostics "
                    "(prompts 24a/24b + Diagnostic 8). No production code is "
                    "modified by running this.",
    )
    parser.add_argument(
        "--diagnostic", nargs="+", default=["all"],
        choices=sorted(_DIAGNOSTIC_DISPATCH) + ["all"],
        help="Which diagnostic(s) to run (default: all). '8a'=alpha "
             "sensitivity, '8t'=tau sensitivity (currently raises "
             "NotImplementedError -- see module docstring).",
    )
    parser.add_argument(
        "--alpha-values", type=str, default="0.01,0.05,0.1,0.3",
        help="Comma-separated alpha_regularization values for diagnostic 8a "
             "(default: %(default)s).",
    )
    return parser


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    which = args.diagnostic
    keys = sorted(_DIAGNOSTIC_DISPATCH) if "all" in which else which
    # Diagnostics 1/2 share one run -- de-duplicate if both were requested.
    seen_12 = False
    for key in keys:
        if key in ("1", "2"):
            if seen_12:
                continue
            seen_12 = True
        _DIAGNOSTIC_DISPATCH[key](args)
    print(f"\nDone. See {OUT_DIR}/ for JSON records.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
