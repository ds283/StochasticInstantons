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
from math import log10, pow
from typing import Optional

from Datastore import DatastoreObject


class tolerance(DatastoreObject):
    def __init__(self, store_id: int, timestamp: Optional[datetime] = None, **kwargs):
        """
        Construct a datastore-backed object representing a tolerance (absolute or relative).
        Effectively tokenizes a floating point number to an integer.
        :param store_id: unique Datastore id. Should not be None
        :param tol: tolerance
        """
        if store_id is None:
            raise ValueError("Store ID cannot be None")
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)

        if "log10_tol" in kwargs:
            log10_tol = kwargs["log10_tol"]
            self.log10_tol = log10_tol
            self.tol = pow(10.0, log10_tol)
        elif "tol" in kwargs:
            tol = kwargs["tol"]
            self.tol = tol
            self.log10_tol = log10(tol)
        else:
            raise RuntimeError(
                'Neither "tol" nor "log10_tol" was supplied to tolerance() constructor'
            )

    def __float__(self):
        """
        Cast to float.
        :return:
        """
        return self.tol
