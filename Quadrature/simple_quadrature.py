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

import time
from typing import Optional, Iterable, List

from scipy.integrate import quad, solve_ivp

from Quadrature.integration_metadata import IntegrationData
from Quadrature.supervisors.base import (
    IntegrationSupervisor,
    DEFAULT_UPDATE_INTERVAL,
    RHS_timer,
)
from utilities import format_time


class QuadSupervisor(IntegrationSupervisor):
    def __init__(
        self,
        label: str,
        a: float,
        b: float,
        notify_interval: int = DEFAULT_UPDATE_INTERVAL,
    ):
        super().__init__(notify_interval)

        self._label: str = label

        self._a: float = a
        self._b: float = b

        self._range: float = b - a
        self._last_x: float = a

    def __enter__(self):
        super().__enter__()
        return self

    @property
    def label(self):
        if self._label is not None:
            return self._label

        return "numerical quadrature"

    def __exit__(self, exc_type, exc_val, exc_tb):
        super().__exit__(exc_type, exc_val, exc_tb)

    def message(self, current_x, msg):
        current_time = time.time()
        since_last_notify = current_time - self._last_notify
        since_start = current_time - self._start_time

        update_number = self.report_notify()

        complete = current_x - self._a
        remain = self._range - complete
        percent_remain = remain / self._range

        print(
            f"** STATUS UPDATE #{update_number}: {self.label} has been running for {format_time(since_start)} ({format_time(since_last_notify)} since last notification)"
        )
        print(
            f"|    current x={current_x:.8g} (init x={self._a:.8g}, target x={self._b:.8g} | complete={complete:.8g}, remain={remain:.8g}, {percent_remain:.3%} remains)"
        )
        if self._last_x is not None:
            x_delta = current_x - self._last_x
            print(f"|    advance since last update: Delta x = {x_delta:.8g}")
        print(
            f"|    {self.RHS_evaluations} evaluations, mean {self.mean_RHS_time:.5g}s per evaluation, min time = {self.min_RHS_time:.5g}s, max time = {self.max_RHS_time:.5g}s"
        )
        print(f"|    {msg}")

        self._last_x = current_x


def _quadrature_quad_impl(
    integrand, a: float, b: float, atol: float, rtol: float, label: Optional[str] = None
):
    with QuadSupervisor(label, a, b) as supervisor:
        values = []
        errs = []

        for f in integrand:

            def RHS(x):
                with RHS_timer(supervisor) as timer:
                    if supervisor.notify_available:
                        supervisor.message(x, msg="... in progress")
                        supervisor.reset_notify_time()

                    return f(x)

            value, err = quad(RHS, a=a, b=b, epsabs=atol, epsrel=rtol, limit=100)
            values.append(value)
            errs.append(err)

    if len(integrand) == 1:
        values = values[0]
        errs = errs[0]

    return {
        "data": IntegrationData(
            compute_time=supervisor.integration_time,
            compute_steps=int(supervisor.RHS_evaluations),
            RHS_evaluations=supervisor.RHS_evaluations,
            mean_RHS_time=supervisor.mean_RHS_time,
            max_RHS_time=supervisor.max_RHS_time,
            min_RHS_time=supervisor.min_RHS_time,
        ),
        "value": values,
        "abserr": errs,
    }


def _quadature_solve_ivp_impl(
    integrand,
    a: float,
    b: float,
    atol: float,
    rtol: float,
    method: str = "DOP853",
    label: Optional[str] = None,
):

    def RHS(x: float, state: List[float], supervisor: QuadSupervisor) -> List[float]:
        with RHS_timer(supervisor) as timer:
            current_value = state[0]

            if supervisor.notify_available:
                supervisor.message(x, f"current state: value={current_value:.8g}")
                supervisor.reset_notify_time()

            return [f(x) for f in integrand]

    with QuadSupervisor(label, a, b) as supervisor:
        state = [0.0 for _ in integrand]

        sol = solve_ivp(
            RHS,
            method=method,
            t_span=(a, b),
            t_eval=[b],
            y0=state,
            dense_output=True,
            atol=atol,
            rtol=rtol,
            args=(supervisor,),
        )

    if not sol.success:
        raise RuntimeError(
            f'simple_quadrature: quadrature did not terminate successfully | error at x={sol.t[0]:.5g}, "{sol.message}"'
        )

    if len(sol.t) == 0:
        raise RuntimeError(
            f"simple_quadrature: quadrature did not return any samples (min x={a:.5g}, max x={b:.5g})"
        )

    if sol.t[0] < b - atol:
        raise RuntimeError(
            f"simple_quadrature: quadrature did not terminate at expected ordinate (min x={a:.5g}, max x={b:.5g}), final x={sol.t[0]:.5g})"
        )

    if len(sol.sol(b)) != len(integrand):
        raise RuntimeError(
            f"simple_quadrature: solution does not have expected number of members (expected {len(integrand)}, found {len(sol.sol(b))})"
        )

    value = sol.sol(b)
    if len(integrand) == 1:
        value = value[0]

    return {
        "data": IntegrationData(
            compute_time=supervisor.integration_time,
            compute_steps=int(sol.nfev),
            RHS_evaluations=supervisor.RHS_evaluations,
            mean_RHS_time=supervisor.mean_RHS_time,
            max_RHS_time=supervisor.max_RHS_time,
            min_RHS_time=supervisor.min_RHS_time,
        ),
        "value": value,
        "abserr": None,
    }


def simple_quadrature(
    integrand,
    a: float,
    b: float,
    atol: float,
    rtol: float,
    method: str = "DOP853",
    label: Optional[str] = None,
):
    if not isinstance(integrand, Iterable):
        integrand = [integrand]

    if method == "quad":
        return _quadrature_quad_impl(integrand, a, b, atol, rtol, label=label)

    if method in ["RK45", "DOP853", "Radau", "LSODA", "BDF"]:
        return _quadature_solve_ivp_impl(
            integrand, a, b, atol, rtol, method, label=label
        )

    return _quadature_solve_ivp_impl(
        integrand, a, b, atol, rtol, method="DOP853", label=label
    )
