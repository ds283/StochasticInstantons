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

from typing import Optional

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential


def noiseless_rhs(N: float, y: list, potential: AbstractPotential) -> list:
    """
    RHS of the noiseless inflationary background ODE:
        dφ/dN = π
        dπ/dN = -(3 - ε) π - V′(φ) / H²
    """
    phi, pi = y
    Hsq = potential.H_sq(phi, pi)
    eps = potential.epsilon(phi, pi)
    return [pi, -(3.0 - eps) * pi - potential.dV_dphi(phi) / Hsq]


def end_of_inflation_event(N: float, y: list, potential: AbstractPotential) -> float:
    """
    Event function: returns ε(φ, π) - 1. Caller must set .terminal=True and
    .direction=+1 on the bound closure passed to solve_ivp.
    """
    return potential.epsilon(y[0], y[1]) - 1.0


def integrate_noiseless_trajectory(
        phi0: float,
        pi0: float,
        potential: AbstractPotential,
        atol: float,
        rtol: float,
        label: Optional[str] = None,
        verbose: bool = False,
) -> tuple[object, str, list]:
    """
    Integrate the noiseless equations from (phi0, pi0) at N=0 until ε=1.

    Tries the solver chain RK45 → DOP853 → Radau → BDF → LSODA.
    Returns (sol, solver_used, solver_attempts) where sol has dense_output=True,
    or (None, None, solver_attempts) on total failure.
    """
    from scipy.integrate import solve_ivp

    def rhs(N, y):
        return noiseless_rhs(N, y, potential)

    def event(N, y):
        return end_of_inflation_event(N, y, potential)
    event.terminal  = True
    event.direction = +1

    y0     = [phi0, pi0]
    N_span = (0.0, 1000.0)

    SOLVERS = ["RK45", "DOP853", "Radau", "BDF", "LSODA"]
    sol            = None
    solver_used    = None
    solver_attempts = []
    for solver in SOLVERS:
        try:
            candidate = solve_ivp(
                rhs, N_span, y0,
                method=solver,
                events=[event],
                dense_output=True,
                atol=atol, rtol=rtol,
            )
            if candidate.success or candidate.status == 1:
                sol         = candidate
                solver_used = solver
                solver_attempts.append({
                    "solver": solver, "status": int(candidate.status),
                    "message": candidate.message,
                })
                if verbose:
                    print(f"[{label}] solver {solver} succeeded "
                          f"(status={candidate.status})")
                break
            solver_attempts.append({
                "solver": solver, "status": int(candidate.status),
                "message": candidate.message,
            })
            if verbose:
                print(f"[{label}] solver {solver} "
                      f"status={candidate.status}: {candidate.message}")
        except Exception as exc:
            solver_attempts.append({
                "solver": solver, "status": None, "message": str(exc),
            })
            if verbose:
                print(f"[{label}] solver {solver} raised: {exc}")

    return sol, solver_used, solver_attempts
