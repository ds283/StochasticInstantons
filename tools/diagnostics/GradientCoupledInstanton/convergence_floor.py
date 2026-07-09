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
# Diagnostic 9 (prompt 25) -- bias-corrected target retry at n>=9. A direct
# splice of Diagnostic 3a's bias-injection mechanism onto Diagnostic 6's
# n-retry: tests whether the n in {9, 17} non-convergence Diagnostic 6 found
# is the SAME resolution-independent fixed-g_pi_core-target bias Diagnostic
# 3a already cured at delta_Nstar=1, now biting at a resolution fine enough
# to resolve it, rather than a genuine under-resolved boundary layer needing
# new numerics.
# ---------------------------------------------------------------------------

def diagnostic_9_bias_corrected_n_retry(
    m: float = 1.0e-2, delta_Nstar: float = 0.5, n_baseline: int = 5,
    n_retry: int = 9, delta_fractions=(0.0, 0.3, 1.0, 3.0),
    max_outer_cap: int = 30, wallclock_budget_seconds: float = 900.0,
):
    """Does Diagnostic 3a's fixed-``g_pi_core``-target bias explain the
    n in {9, 17} non-convergence Diagnostic 6 found at (m=1e-2,
    delta_Nstar=0.5) -- a point that converges cleanly at n=5 -- or does it
    need new numerics?

    Step 0 solves the ordinary (unperturbed, delta=0) problem at
    ``n_baseline`` and measures ``bias_n5 = max|pi_core(N) -
    g_pi_core_final(N)|``: the genuine sweep-0-to-convergence drift between
    the frozen fixed target and the converged ``pi_core`` this specific
    (m, delta_Nstar) point produces, at the resolution that DOES converge.
    Unlike Diagnostic 3a's own literal ``delta=0.03`` (calibrated at a
    different mass/delta_Nstar), this is measured fresh, not assumed.

    Step 1 re-seeds ``n_retry`` with ``phi2`` shifted by
    ``delta = frac * bias_n5`` for ``frac`` in ``delta_fractions`` (both
    signs) and re-solves under a raised ``MAX_OUTER`` cap, exactly as
    Diagnostic 3a does at its own (m, delta_Nstar).

    Interpretation of the result:
      - **Confirmed** (some swept delta converges at ``n_retry``): the
        n>=9 floor is the SAME mechanism as Diagnostic 3a's delta_Nstar=1
        floor, simply biting harder once the discretisation resolves more
        structure -- the fixed target is measurably wrong at this
        resolution, not that the resolution itself is inadequate. The cheap
        next step is a corrected/self-consistent ``g_pi_core`` target, not
        new numerics.
      - **Not confirmed** (no swept delta converges within the tested
        range): this rules out the cheap explanation. The n>=9 floor is
        evidence of genuinely under-resolved structure (a boundary-layer /
        regularity problem), and the next step is the ``tau_multiplier``
        production study (Diagnostic 8t) rather than a target correction.
        A clean negative here is a valid, complete result -- not grounds to
        keep widening ``delta_fractions`` until something converges.
    """
    print("\n" + "=" * 78, flush=True)
    print(f"DIAGNOSTIC 9: bias-corrected target retry at n={n_retry} "
          f"(m={m:.4g}, delta_Nstar={delta_Nstar})", flush=True)
    print("=" * 78, flush=True)

    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)
    H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)
    fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, delta_Nstar,
                                      label="D9 FI seed")
    lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda", 0.0)
    full_instanton_seed = h.full_instanton_seed_from(fi_data)
    print(f"[D9] FullInstanton: lambda_FI={lambda_FI!r} msr_action={fi_data.get('msr_action')!r}", flush=True)

    # ---- Step 0: measure the n=5 baseline bias, don't assume it. ----
    grid_baseline = h.LGLCollocationGrid(n_baseline)
    t0 = time.perf_counter()
    baseline_result = h.picard_module.solve_picard(
        h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid_baseline, traj, potential, dm,
        h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
        full_instanton_seed=full_instanton_seed,
        wallclock_budget_seconds=wallclock_budget_seconds,
        label=f"D9 n={n_baseline} baseline",
    )
    dt_baseline = time.perf_counter() - t0
    baseline_diag = baseline_result.get("diagnostics", {})
    if not baseline_diag.get("converged") or baseline_result.get("g_pi_core_final") is None:
        raise RuntimeError(
            f"diagnostic_9_bias_corrected_n_retry: baseline solve at n={n_baseline} "
            f"(m={m:.4g}, delta_Nstar={delta_Nstar}) did not converge, or returned no "
            f"g_pi_core_final -- bias_n5 cannot be measured. converged="
            f"{baseline_diag.get('converged')!r} bailout_tag={baseline_diag.get('bailout_tag')!r}"
        )
    pi_grid_baseline = np.asarray(baseline_result["pi_grid"])
    g_pi_core_final_baseline = np.asarray(baseline_result["g_pi_core_final"])
    bias_n5 = float(np.max(np.abs(pi_grid_baseline[:, -1] - g_pi_core_final_baseline)))
    print(f"[D9] baseline n={n_baseline}: converged=True final_lambda="
          f"{baseline_result.get('final_lambda')!r} bias_n5={bias_n5:.6g} ({dt_baseline:.1f}s)", flush=True)

    # ---- Step 1: sweep delta_fractions x bias_n5 at n_retry (both signs). ----
    frac_signed = []
    for frac in delta_fractions:
        if frac == 0.0:
            if 0.0 not in frac_signed:
                frac_signed.append(0.0)
        else:
            frac_signed.append(frac)
            frac_signed.append(-frac)

    grid_retry = h.LGLCollocationGrid(n_retry)
    sweep_rows = []
    with h.MonkeypatchGuard(h.picard_module, MAX_OUTER=max_outer_cap):
        for frac in frac_signed:
            delta = frac * bias_n5
            phi2_perturbed = np.asarray(fi_data["phi2"]) + delta
            seed = {
                "failure": False, "N_sample": fi_data["N_sample"],
                "phi1": fi_data["phi1"], "phi2": phi2_perturbed.tolist(),
                "final_lambda": lambda_FI,
            }
            t0 = time.perf_counter()
            result = h.picard_module.solve_picard(
                h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid_retry, traj, potential, dm,
                h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
                full_instanton_seed=seed,
                wallclock_budget_seconds=wallclock_budget_seconds,
                label=f"D9 n={n_retry} frac={frac:+.4g}",
            )
            dt = time.perf_counter() - t0
            diag = result.get("diagnostics", {})
            row = {
                "delta": delta, "delta_frac": frac,
                "converged": diag.get("converged"), "final_residual": diag.get("final_residual"),
                "bailout_tag": diag.get("bailout_tag"), "bailout_reason": diag.get("bailout_reason"),
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
                    N_grid_arr, phi_grid, pi_grid, rfield_grid, rmom_grid, grid_retry, potential, dm,
                    H_sq_nl_init, h.ALPHA,
                )
            else:
                row["msr_action"] = None
            sweep_rows.append(row)
            print(f"  [D9] n={n_retry} frac={frac:+.4g} delta={delta:+.6g}: "
                  f"converged={row['converged']} final_lambda={row['final_lambda']!r} "
                  f"msr_action={row['msr_action']!r} bailout={row['bailout_tag']} ({dt:.1f}s)", flush=True)

    # ---- Step 3: persist baseline + sweep together. ----
    output = {
        "m": m, "delta_Nstar": delta_Nstar, "n_baseline": n_baseline, "n_retry": n_retry,
        "bias_n5": bias_n5,
        "baseline": {
            "converged": baseline_diag.get("converged"),
            "final_residual": baseline_diag.get("final_residual"),
            "bailout_tag": baseline_diag.get("bailout_tag"),
            "final_lambda": baseline_result.get("final_lambda"),
            "outer_iterations": baseline_diag.get("outer_iterations"),
            "wallclock": dt_baseline,
        },
        "sweep": sweep_rows,
    }
    h.save_json(f"{OUT_DIR}/diagnostic9_bias_corrected_n_retry.json", output)

    # ---- Step 4: print a clear summary. ----
    print("\n--- Diagnostic 9 summary ---", flush=True)
    print(f"  bias_n5 (max|pi_core - g_pi_core_final| at n={n_baseline}) = {bias_n5:.6g}", flush=True)
    print(f"  {'delta/bias_n5':>14} {'converged':>10} {'final_lambda':>16} "
          f"{'msr_action':>16} {'bailout_tag':>18}", flush=True)
    for row in sweep_rows:
        lam_str = f"{row['final_lambda']:.6g}" if row["final_lambda"] is not None else "None"
        msr_str = f"{row['msr_action']:.6g}" if row["msr_action"] is not None else "None"
        print(f"  {row['delta_frac']:>+14.4g} {str(row['converged']):>10} "
              f"{lam_str:>16} {msr_str:>16} {str(row['bailout_tag']):>18}", flush=True)

    return output


# ---------------------------------------------------------------------------
# Diagnostic 10 (prompt 26) -- sector attribution via instrument_stiffness at
# n>=9. Diagnostic 9 ruled out the fixed-g_pi_core-target bias as the cause
# of the n in {9, 17} non-convergence Diagnostic 6 found at
# (m=1e-2, delta_Nstar=0.5). This diagnostic asks a different question of the
# SAME non-convergence: which sector -- forward (onion, SBP-SAT-ported,
# prompt 21a) or response/backward (deliberately un-ported, prompt 23) -- is
# actually destabilising as n_collocation_points increases through the
# known failure point. It flips solve_picard's existing
# instrument_stiffness flag to True (already threaded through production,
# already aggregating per-sector RK45 step statistics -- see picard.py's
# _aggregate_rk45_stats) and reads what it already measures; no new
# instrumentation and no production change.
#
# Reading the result:
#   - Forward-attributed (forward sector's rejected_fraction/steps_per_efold
#     spikes disproportionately at n>=9, backward stays bounded): consistent
#     with 21a-production-port-notes.md Sec 5.2's forward-sector tau
#     recurrence -- proceed to the tau_multiplier production prompt and
#     Diagnostic 8t.
#   - Backward-attributed (response sector's stats are the ones that spike,
#     forward stays comparatively bounded): contradicts the frozen-
#     coefficient spectral bound established in
#     23-response-sbp-sat-design-note.md Part A the same way the forward
#     sector's own Phase 1 check was contradicted by its later nonlinear
#     behaviour -- recommend re-opening the response-sector SBP-SAT question
#     rather than proceeding with the forward-only tau_multiplier prompt.
#   - Ambiguous (both sectors degrade together, or neither shows a clear
#     signal despite non-convergence): fall back to the tau_multiplier study
#     anyway (cheaper of the two remaining options, informed by real
#     precedent either way), but flag explicitly that the response sector
#     has not been ruled out.
# ---------------------------------------------------------------------------

def diagnostic_10_sector_attribution(
    m: float = 1.0e-2, delta_Nstar: float = 0.5, ns=(5, 7, 9, 17),
    wallclock_budget: float = 900.0,
):
    """Diagnostic 6's own n-retry pattern, plus instrument_stiffness=True,
    plus reading the six additional rk45_{forward,backward}_* keys and three
    picard_sweep_wallclock_* keys instrument_stiffness already aggregates
    per solve_picard call -- no new machinery. Same (m, delta_Nstar) point as
    Diagnostic 6, so directly comparable to that diagnostic's own
    converged/floored record at each n.

    NOTE (per this prompt's own constraints): instrument_stiffness adds
    measurement overhead (picard.py's own docstring), so a run's bailout_tag
    landing on "wallclock_budget" here where Diagnostic 6's equivalent run
    at the same n floored on "max_outer_exhausted" instead is an expected
    discrepancy from that overhead, not a sign the two runs disagree on
    convergence behaviour -- don't treat the two runs' outer-iteration
    counts as directly comparable in that case. The RK45 step statistics
    accumulated up to the bailout are still valid and are what this
    diagnostic is actually after.
    """
    print("\n" + "=" * 78, flush=True)
    print(f"DIAGNOSTIC 10: sector attribution via instrument_stiffness at m={m:.4g}, "
          f"delta_Nstar={delta_Nstar}", flush=True)
    print("=" * 78, flush=True)

    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)
    H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)
    fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, delta_Nstar,
                                      label="D10 FI seed")
    lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda", 0.0)
    full_instanton_seed = h.full_instanton_seed_from(fi_data)
    print(f"[D10] FullInstanton: lambda_FI={lambda_FI!r} msr_action={fi_data.get('msr_action')!r}", flush=True)

    rk45_keys = [
        "rk45_forward_total_steps", "rk45_forward_accepted_steps", "rk45_forward_rejected_steps",
        "rk45_forward_min_step", "rk45_forward_max_step", "rk45_forward_steps_per_efold",
        "rk45_backward_total_steps", "rk45_backward_accepted_steps", "rk45_backward_rejected_steps",
        "rk45_backward_min_step", "rk45_backward_max_step", "rk45_backward_steps_per_efold",
        "picard_sweep_wallclock_min", "picard_sweep_wallclock_mean", "picard_sweep_wallclock_max",
    ]

    def _ratio(numer, denom):
        if numer is None or denom is None or denom == 0:
            return None
        return numer / denom

    rows = []
    for n in ns:
        grid = h.LGLCollocationGrid(n)
        t0 = time.perf_counter()
        result = h.picard_module.solve_picard(
            h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid, traj, potential, dm,
            h.ATOL, h.RTOL, phi_end, instrument_stiffness=True, verbose=False,
            full_instanton_seed=full_instanton_seed,
            wallclock_budget_seconds=wallclock_budget, label=f"D10 n={n}",
        )
        dt = time.perf_counter() - t0
        diag = result.get("diagnostics", {})
        row = {
            "n_collocation_points": n,
            "converged": diag.get("converged"),
            "final_residual": diag.get("final_residual"),
            "bailout_tag": diag.get("bailout_tag"),
            "bailout_reason": diag.get("bailout_reason"),
            "outer_iterations": diag.get("outer_iterations"),
            "final_lambda": result.get("final_lambda"),
            "wallclock": dt,
        }
        for key in rk45_keys:
            row[key] = diag.get(key)
        row["forward_rejected_fraction"] = _ratio(
            row["rk45_forward_rejected_steps"], row["rk45_forward_total_steps"])
        row["backward_rejected_fraction"] = _ratio(
            row["rk45_backward_rejected_steps"], row["rk45_backward_total_steps"])
        row["backward_to_forward_steps_per_efold_ratio"] = _ratio(
            row["rk45_backward_steps_per_efold"], row["rk45_forward_steps_per_efold"])
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
        print(f"[D10] n={n}: converged={row['converged']} final_lambda={row['final_lambda']!r} "
              f"fwd_total={row['rk45_forward_total_steps']!r} "
              f"fwd_rej_frac={row['forward_rejected_fraction']!r} "
              f"bwd_total={row['rk45_backward_total_steps']!r} "
              f"bwd_rej_frac={row['backward_rejected_fraction']!r} "
              f"bailout={row['bailout_tag']} ({dt:.1f}s)", flush=True)

    output = {"m": m, "delta_Nstar": delta_Nstar, "ns": list(ns), "lambda_FI": lambda_FI, "rows": rows}
    h.save_json(f"{OUT_DIR}/diagnostic10_sector_attribution.json", output)

    def _fmt(v, spec="{:.4g}"):
        return "n/a" if v is None else spec.format(v)

    print("\n--- Diagnostic 10 summary ---", flush=True)
    header = (f"  {'n':>4} {'converged':>10} {'fwd_total':>10} {'fwd_rej_frac':>13} "
              f"{'bwd_total':>10} {'bwd_rej_frac':>13} {'bwd/fwd_steps_per_efold':>24} {'bailout_tag':>18}")
    print(header, flush=True)
    for row in rows:
        print(
            f"  {row['n_collocation_points']:>4} {str(row['converged']):>10} "
            f"{_fmt(row['rk45_forward_total_steps'], '{:.0f}'):>10} "
            f"{_fmt(row['forward_rejected_fraction']):>13} "
            f"{_fmt(row['rk45_backward_total_steps'], '{:.0f}'):>10} "
            f"{_fmt(row['backward_rejected_fraction']):>13} "
            f"{_fmt(row['backward_to_forward_steps_per_efold_ratio']):>24} "
            f"{str(row['bailout_tag']):>18}",
            flush=True,
        )

    return output


# ---------------------------------------------------------------------------
# Diagnostic 11 -- corridor-edge proximity check at n>=9. Follow-up to
# Diagnostic 10's own ambiguous forward/backward attribution: the 24b
# lam_bounds corridor clamp (lambda_c_positive = w_core*mu(N_total)/D11,
# lambda_c_negative = 2.5x that) was derived and calibrated ONLY at n=5
# (four delta_Nstar points, one mass). w_core = grid.weights[-1], the LGL
# terminal quadrature weight, shrinks with n (0.1 at n=5, 0.0278 at n=9,
# 0.00735 at n=17 -- confirmed directly), so the corridor itself narrows by
# the same factor purely from discretisation, with no physics change. This
# diagnostic checks whether the n=9/n=17 non-convergence Diagnostic 6/9/10
# all found is (partly) an artefact of the outer loop being clamped against
# an artificially-narrow wall, rather than genuine physical/discretisation
# stiffness -- exactly the check 24b already did successfully for
# delta_Nstar=1.0 (Diagnostic 5, "final probe nowhere near either edge"),
# never yet done for n>=9.
# ---------------------------------------------------------------------------

def diagnostic_11_corridor_edge_proximity(
    m: float = 1.0e-2, delta_Nstar: float = 0.5, ns=(5, 7, 9, 17),
    wallclock_budget: float = 900.0,
):
    """Same (m, delta_Nstar) point as Diagnostics 6/9/10. For each n, captures
    lambda_seed/lambda_c_positive/lambda_c_negative (already computed by
    solve_picard regardless of convergence outcome) plus the LAST lambda the
    outer shooting loop was sitting at when it stopped -- recovered via
    harness.capture_shooting_result(), since solve_picard's own
    diagnostics["final_lambda"] is masked to None on non-convergence, hiding
    exactly the value this check needs. Reports how close that last lambda
    sat to the nearer corridor edge, as a fraction of the corridor's own
    width -- a value near 0 means the search was sitting right against the
    clamp wall (corridor-limited, not ruled out); a value well away from 0
    (as 24b found at delta_Nstar=1.0) means the clamp was not the limiting
    factor at that n.

    No production code is touched: lambda_seed/lambda_c_positive/
    lambda_c_negative are pre-existing solve_picard diagnostics keys (used
    already by Diagnostic 5); capture_shooting_result() monkeypatches
    solve_shooting the same way capture_last_commit() already does elsewhere
    in this suite, purely to observe its return value.
    """
    print("\n" + "=" * 78, flush=True)
    print(f"DIAGNOSTIC 11: corridor-edge proximity at m={m:.4g}, "
          f"delta_Nstar={delta_Nstar}", flush=True)
    print("=" * 78, flush=True)

    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)
    H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)
    fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, delta_Nstar,
                                      label="D11 FI seed")
    lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda", 0.0)
    full_instanton_seed = h.full_instanton_seed_from(fi_data)
    print(f"[D11] FullInstanton: lambda_FI={lambda_FI!r} msr_action={fi_data.get('msr_action')!r}", flush=True)

    rows = []
    for n in ns:
        grid = h.LGLCollocationGrid(n)
        w_core = float(grid.weights[-1])
        t0 = time.perf_counter()
        with h.capture_shooting_result() as captured:
            result = h.picard_module.solve_picard(
                h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid, traj, potential, dm,
                h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
                full_instanton_seed=full_instanton_seed,
                wallclock_budget_seconds=wallclock_budget, label=f"D11 n={n}",
            )
        dt = time.perf_counter() - t0
        diag = result.get("diagnostics", {})
        shoot = captured.get("result")
        last_lambda_tried = shoot.lam if shoot is not None else None

        lam_c_pos = diag.get("lambda_c_positive")
        lam_c_neg = diag.get("lambda_c_negative")
        nearest_edge_fraction = None
        if last_lambda_tried is not None and lam_c_pos is not None and lam_c_neg is not None:
            corridor_width = lam_c_pos - lam_c_neg
            if corridor_width:
                frac_from_positive = (lam_c_pos - last_lambda_tried) / corridor_width
                frac_from_negative = (last_lambda_tried - lam_c_neg) / corridor_width
                nearest_edge_fraction = min(frac_from_positive, frac_from_negative)

        row = {
            "n_collocation_points": n,
            "w_core": w_core,
            "converged": diag.get("converged"),
            "bailout_tag": diag.get("bailout_tag"),
            "bailout_reason": diag.get("bailout_reason"),
            "final_residual": diag.get("final_residual"),
            "outer_iterations": diag.get("outer_iterations"),
            "n_bracket_evaluations": diag.get("n_bracket_evaluations"),
            "lambda_seed": diag.get("lambda_seed"),
            "lambda_c_positive": lam_c_pos,
            "lambda_c_negative": lam_c_neg,
            "final_lambda": result.get("final_lambda"),
            "last_lambda_tried": last_lambda_tried,
            "nearest_edge_fraction": nearest_edge_fraction,
            "wallclock": dt,
        }
        rows.append(row)
        print(f"[D11] n={n}: converged={row['converged']} w_core={w_core:.6g} "
              f"lambda_c=[{lam_c_neg!r}, {lam_c_pos!r}] last_lambda_tried={last_lambda_tried!r} "
              f"nearest_edge_fraction={nearest_edge_fraction!r} "
              f"n_bracket_evals={row['n_bracket_evaluations']!r} bailout={row['bailout_tag']} ({dt:.1f}s)",
              flush=True)

    output = {"m": m, "delta_Nstar": delta_Nstar, "ns": list(ns), "lambda_FI": lambda_FI, "rows": rows}
    h.save_json(f"{OUT_DIR}/diagnostic11_corridor_edge_proximity.json", output)

    def _fmt(v, spec="{:.4g}"):
        return "n/a" if v is None else spec.format(v)

    print("\n--- Diagnostic 11 summary ---", flush=True)
    header = (f"  {'n':>4} {'converged':>10} {'w_core':>10} {'lambda_c_neg':>14} {'lambda_c_pos':>14} "
              f"{'last_lambda':>14} {'nearest_edge_frac':>18} {'n_bracket_evals':>16}")
    print(header, flush=True)
    for row in rows:
        print(
            f"  {row['n_collocation_points']:>4} {str(row['converged']):>10} "
            f"{_fmt(row['w_core'], '{:.4g}'):>10} "
            f"{_fmt(row['lambda_c_negative']):>14} {_fmt(row['lambda_c_positive']):>14} "
            f"{_fmt(row['last_lambda_tried']):>14} {_fmt(row['nearest_edge_fraction']):>18} "
            f"{_fmt(row['n_bracket_evaluations'], '{:.0f}'):>16}",
            flush=True,
        )

    return output


# ---------------------------------------------------------------------------
# Diagnostic 12 -- relaxed-corridor retry at n=9. Direct empirical test of
# Diagnostic 11's own finding: n=9's outer loop was pinned bit-for-bit on
# the corridor's UNwidened positive edge for its entire 50-iteration budget
# (26a-corridor-edge-proximity.md). This diagnostic sweeps the new
# CORRIDOR_POSITIVE_WIDENING production constant (default 1.0, added
# specifically to enable this test -- see picard.py's own comment at its
# definition) to see whether relaxing that wall lets n=9 actually converge.
#
# Reading the result:
#   - Converges at some widening: the corridor WAS the limiting factor --
#     a genuine root exists just beyond the unwidened kappa=1 bound. Next
#     step is revisiting CORRIDOR_POSITIVE_WIDENING's own calibration (a
#     production fix, needing the same multi-point verification 24b did for
#     CORRIDOR_NEGATIVE_WIDENING), not the tau_multiplier study.
#   - Never converges even at the widest widening tried: rules the corridor
#     out. n=9's floor is genuine stiffness -- the tau_multiplier
#     recommendation (already made in 26-sector-attribution-instrument-
#     stiffness.md) stands, now on firmer ground.
# ---------------------------------------------------------------------------

def diagnostic_12_relaxed_corridor_retry(
    m: float = 1.0e-2, delta_Nstar: float = 0.5, n: int = 9,
    widenings=(1.0, 2.5, 5.0, 10.0), wallclock_budget: float = 900.0,
):
    """Sweeps CORRIDOR_POSITIVE_WIDENING at the corridor-clamped point
    26a-corridor-edge-proximity.md identified ((m/Mp=1e-2, delta_Nstar=0.5,
    n=9)). widenings[0]=1.0 reproduces Diagnostic 11's own n=9 floor exactly
    (sanity check on this diagnostic's own harness, not a new result);
    subsequent values relax the positive AND (via the existing
    CORRIDOR_NEGATIVE_WIDENING=2.5x-of-positive relationship) negative edges
    together, preserving their calibrated ratio rather than testing an
    isolated, uncalibrated positive-only widening.

    No physics is touched: CORRIDOR_POSITIVE_WIDENING multiplies only the
    outer shooting loop's own feasibility clamp (picard.py's
    lambda_c_positive/lambda_c_negative), never lambda_seed (the bootstrap
    direction, which does not depend on it) and never anything inside
    forward_rhs.py/response_rhs.py's own per-step physics.
    """
    print("\n" + "=" * 78, flush=True)
    print(f"DIAGNOSTIC 12: relaxed-corridor retry at m={m:.4g}, "
          f"delta_Nstar={delta_Nstar}, n={n}", flush=True)
    print("=" * 78, flush=True)

    potential, units, traj, dm = h.setup(m)
    phi_end = h.production_phi_end(traj)
    H_sq_nl_init = h.H_sq_nl_init_of(potential, traj, h.N_INIT)
    fi_data = h.fetch_full_instanton(potential, traj, dm, h.N_INIT, h.N_FINAL, delta_Nstar,
                                      label="D12 FI seed")
    lambda_FI = fi_data.get("diagnostics", {}).get("final_lambda", 0.0)
    full_instanton_seed = h.full_instanton_seed_from(fi_data)
    print(f"[D12] FullInstanton: lambda_FI={lambda_FI!r} msr_action={fi_data.get('msr_action')!r}", flush=True)

    grid = h.LGLCollocationGrid(n)
    rows = []
    for widening in widenings:
        t0 = time.perf_counter()
        with h.capture_shooting_result() as captured:
            with h.MonkeypatchGuard(h.picard_module, CORRIDOR_POSITIVE_WIDENING=widening):
                result = h.picard_module.solve_picard(
                    h.N_INIT, h.N_FINAL, delta_Nstar, h.ALPHA, H_sq_nl_init, grid, traj, potential, dm,
                    h.ATOL, h.RTOL, phi_end, instrument_stiffness=False, verbose=False,
                    full_instanton_seed=full_instanton_seed,
                    wallclock_budget_seconds=wallclock_budget,
                    label=f"D12 n={n} widening={widening:.4g}",
                )
        dt = time.perf_counter() - t0
        diag = result.get("diagnostics", {})
        shoot = captured.get("result")
        last_lambda_tried = shoot.lam if shoot is not None else None

        lam_c_pos = diag.get("lambda_c_positive")
        lam_c_neg = diag.get("lambda_c_negative")
        nearest_edge_fraction = None
        if last_lambda_tried is not None and lam_c_pos is not None and lam_c_neg is not None:
            corridor_width = lam_c_pos - lam_c_neg
            if corridor_width:
                frac_from_positive = (lam_c_pos - last_lambda_tried) / corridor_width
                frac_from_negative = (last_lambda_tried - lam_c_neg) / corridor_width
                nearest_edge_fraction = min(frac_from_positive, frac_from_negative)

        row = {
            "widening": widening,
            "converged": diag.get("converged"),
            "bailout_tag": diag.get("bailout_tag"),
            "bailout_reason": diag.get("bailout_reason"),
            "final_residual": diag.get("final_residual"),
            "outer_iterations": diag.get("outer_iterations"),
            "lambda_c_positive": lam_c_pos,
            "lambda_c_negative": lam_c_neg,
            "final_lambda": result.get("final_lambda"),
            "last_lambda_tried": last_lambda_tried,
            "nearest_edge_fraction": nearest_edge_fraction,
            "wallclock": dt,
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
        print(f"[D12] widening={widening:.4g}: converged={row['converged']} "
              f"lambda_c=[{lam_c_neg!r}, {lam_c_pos!r}] final_lambda={row['final_lambda']!r} "
              f"last_lambda_tried={last_lambda_tried!r} nearest_edge_fraction={nearest_edge_fraction!r} "
              f"bailout={row['bailout_tag']} ({dt:.1f}s)", flush=True)

    output = {"m": m, "delta_Nstar": delta_Nstar, "n": n, "widenings": list(widenings),
              "lambda_FI": lambda_FI, "rows": rows}
    h.save_json(f"{OUT_DIR}/diagnostic12_relaxed_corridor_retry.json", output)

    def _fmt(v, spec="{:.4g}"):
        return "n/a" if v is None else spec.format(v)

    print("\n--- Diagnostic 12 summary ---", flush=True)
    header = (f"  {'widening':>9} {'converged':>10} {'lambda_c_neg':>14} {'lambda_c_pos':>14} "
              f"{'final_lambda':>14} {'nearest_edge_frac':>18} {'bailout_tag':>18}")
    print(header, flush=True)
    for row in rows:
        print(
            f"  {row['widening']:>9.4g} {str(row['converged']):>10} "
            f"{_fmt(row['lambda_c_negative']):>14} {_fmt(row['lambda_c_positive']):>14} "
            f"{_fmt(row['final_lambda']):>14} {_fmt(row['nearest_edge_fraction']):>18} "
            f"{str(row['bailout_tag']):>18}",
            flush=True,
        )

    return output


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
    "9": lambda args: diagnostic_9_bias_corrected_n_retry(),
    "10": lambda args: diagnostic_10_sector_attribution(),
    "11": lambda args: diagnostic_11_corridor_edge_proximity(),
    "12": lambda args: diagnostic_12_relaxed_corridor_retry(),
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
