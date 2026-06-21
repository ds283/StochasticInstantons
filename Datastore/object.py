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

from datetime import datetime
from typing import Optional


class DatastoreObject:
    """
    Represent an object that can be serialized in a datastore
    """

    def __init__(self, store_id: Optional[int], timestamp: Optional[datetime] = None):
        self._my_id = store_id
        # timestamp is None for newly-created objects that have not yet been persisted,
        # and for objects fetched from tables that predate the timestamp column.
        # It is populated only when an existing row is re-fetched from the database.
        self._timestamp: Optional[datetime] = timestamp

    @property
    def store_id(self) -> int:
        if self._my_id is None:
            raise RuntimeError("Attempt to read datastore id before it has been set")

        return self._my_id

    @property
    def available(self) -> bool:
        return self._my_id is not None

    @property
    def timestamp(self) -> Optional[datetime]:
        return self._timestamp
