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
from traceback import print_tb
from typing import Optional

DEFAULT_UPDATE_INTERVAL = 5 * 60


class IntegrationSupervisor:
    def __init__(self, notify_interval: int = DEFAULT_UPDATE_INTERVAL):
        self._notify_interval: int = notify_interval

        self._RHS_time: float = 0
        self._RHS_evaluations: int = 0

        self._min_RHS_time: float = None
        self._max_RHS_time: float = None

        self._num_notifications: int = 0

        self._start_time: float = None
        self._integration_start: float = None
        self._integration_end: float = None

        self._last_notify: float = None

    def __enter__(self):
        self._start_time = time.time()
        self._last_notify: float = self._start_time

        self._integration_start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._integration_end = time.perf_counter()
        self.integration_time = self._integration_end - self._integration_start

        if exc_type is not None:
            print(f"type={exc_type}, value={exc_val}")
            print_tb(exc_tb)

    @property
    def notify_available(self) -> bool:
        return time.time() - self._last_notify > self._notify_interval

    def report_notify(self) -> int:
        self._num_notifications += 1
        return self._num_notifications

    def reset_notify_time(self):
        self._last_notify = time.time()

    def notify_new_RHS_time(self, RHS_time):
        self._RHS_time = self._RHS_time + RHS_time
        self._RHS_evaluations += 1

        if self._min_RHS_time is None or RHS_time < self._min_RHS_time:
            self._min_RHS_time = RHS_time

        if self._max_RHS_time is None or RHS_time > self._max_RHS_time:
            self._max_RHS_time = RHS_time

    @property
    def mean_RHS_time(self) -> Optional[float]:
        if self._RHS_evaluations == 0:
            return None

        return self._RHS_time / self._RHS_evaluations

    @property
    def min_RHS_time(self) -> float:
        return self._min_RHS_time

    @property
    def max_RHS_time(self) -> float:
        return self._max_RHS_time

    @property
    def RHS_evaluations(self) -> int:
        return self._RHS_evaluations


class RHS_timer:
    def __init__(self, supervisor: IntegrationSupervisor):
        self._supervisor: IntegrationSupervisor = supervisor

        self._start_time: float = None
        self._end_time: float = None
        self._elapsed: float = None

    def __enter__(self):
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._end_time = time.perf_counter()
        self._elapsed = self._end_time - self._start_time

        self._supervisor.notify_new_RHS_time(self._elapsed)

        if exc_type is not None:
            print(f"type={exc_type}, value={exc_val}")
            print_tb(exc_tb)
