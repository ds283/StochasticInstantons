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

from typing import Set, Mapping

import ray


class BrokerPool:
    def __init__(self, table_name: str, broker_name: str, max_serial: int = 0):
        # max_serial tracks the current pool high-water mark
        self.max_serial = max_serial if max_serial is not None else 0

        self.leased = set()
        self.recycled = set()
        self.committed = set()

        self._table_name = table_name
        self._broker_name = broker_name

    def notify_largest_store_id(self, max_serial: int) -> bool:
        if max_serial is None:
            return False

        if max_serial > self.max_serial:
            self.max_serial = max_serial
            return True

        return False

    def _current_inflight_max(self) -> int:
        leased_max = max(self.leased, default=None)
        committed_max = max(self.committed, default=None)

        options = [self.max_serial, leased_max, committed_max]
        filtered_options = [x for x in options if x is not None]

        # max will raise an exception if provided an empty iterable, so we should catch any error here
        return max(filtered_options)

    def lease_serials(self, batch_size: int) -> Set[int]:
        lease_set = set()
        number_leased = 0

        while number_leased < batch_size:
            # if there are numbers to be recycled, first re-lease these

            # len(self.recycled) should be O(1), so this does not scale with the number of serials in the recycling pool
            while len(self.recycled) > 0 and number_leased < batch_size:
                recyled_lease = self.recycled.pop()
                lease_set.add(recyled_lease)
                self.leased.add(recyled_lease)
                number_leased += 1

            if number_leased >= batch_size:
                break

            # otherwise, find the first free serial number, and lease that
            # this is the first number that has not been leased or committed
            inflight_max = self._current_inflight_max()
            new_leases = set(
                inflight_max + 1 + n for n in range(batch_size - number_leased)
            )

            lease_set.update(new_leases)
            self.leased.update(new_leases)
            number_leased += len(new_leases)

        if len(lease_set) != batch_size:
            raise RuntimeError(
                f"BrokerPool: unexpected number of serial numbers allocated in lease (requested={batch_size}, allocated={len(lease_set)})"
            )

        return lease_set

    def release_serials(self, serials: Set[int]) -> bool:
        for serial in serials:
            if serial not in self.leased:
                print(
                    f'BrokerPool (broker={self._broker_name}): attempt to release serial #{serial} for table "{self._table_name}", but this has not been leased'
                )
                return False

            self.leased.remove(serial)
            self.recycled.add(serial)

        return self._prune()

    def commit_serials(self, serials: Set[int]) -> bool:
        for serial in serials:
            if serial not in self.leased:
                print(
                    f'BrokerPool (broker={self._broker_name}): attempt to commit serial #{serial} for table "{self._table_name}", but this has not been leased'
                )
                return False

            self.leased.remove(serial)
            self.committed.add(serial)

        return self._prune()

    def _prune(self) -> bool:
        # if any element of 'committed' is above the current pool high-water mark, move the high-water mark up to compensate:
        while self.max_serial + 1 in self.committed:
            self.max_serial += 1
            self.committed.remove(self.max_serial)

        # if any elements in 'recycled' are above the inflight high-water mark (values in leased+committed), remove these elements
        # (there is no need to keep track of them)
        inflight_max = self._current_inflight_max()

        self.recycled = set(x for x in self.recycled if x < inflight_max)
        return True


_TableSerialMappingType = Mapping[str, BrokerPool]


@ray.remote
class SerialPoolBroker:
    def __init__(self, name: str):
        self._tables: _TableSerialMappingType = {}
        self._my_name = name

    def notify_largest_store_ids(self, tables: Mapping[str, int]) -> None:
        for table, max_serial in tables.items():
            if table not in self._tables:
                self._tables[table] = BrokerPool(table, self._my_name, max_serial)
            else:
                self._tables[table].notify_largest_store_id(max_serial)

    def lease_serials(self, table: str, batch_size: int) -> Set[int]:
        if table in self._tables:
            return self._tables[table].lease_serials(batch_size)

        self._tables[table] = BrokerPool(table, self._my_name)
        return self._tables[table].lease_serials(batch_size)

    def release_serials(self, table: str, serials: Set[int]) -> bool:
        if table not in self._tables:
            raise RuntimeError(
                f'SerialPoolBroker: release_serials() called on non-existent table "{table}"'
            )

        return self._tables[table].release_serials(serials)

    def commit_serials(self, table: str, serials: Set[int]) -> bool:
        if table not in self._tables:
            raise RuntimeError(
                f'SerialPoolBroker: commit_serials() called on non-existent table "{table}"'
            )
        return self._tables[table].commit_serials(serials)
