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
from math import fabs

import sqlalchemy as sqla

from InflationConcepts.alpha_regularization import alpha_regularization
from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from config.defaults import (
    DEFAULT_ALPHA_PRECISION,
    DEFAULT_ALPHA_RELATIVE_PRECISION,
)


class sqla_alpha_regularization_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column("alpha", sqla.Float(64), index=True),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        alpha = payload["alpha"]

        if fabs(alpha) == 0:
            query = sqla.select(table.c.serial, table.c.timestamp).filter(
                sqla.func.abs(table.c.alpha - alpha) < DEFAULT_ALPHA_PRECISION
            )
        else:
            query = sqla.select(table.c.serial, table.c.timestamp).filter(
                sqla.func.abs((table.c.alpha - alpha) / alpha)
                < DEFAULT_ALPHA_RELATIVE_PRECISION
            )

        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            insert_data = {"alpha": alpha}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            timestamp = None
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            timestamp = row_data.timestamp
            attribute_set = {"_deserialized": True}

        obj = alpha_regularization(store_id=store_id, alpha=alpha, timestamp=timestamp)
        for key, v in attribute_set.items():
            setattr(obj, key, v)
        return obj

    def read_table(self, conn, table):
        query = sqla.select(
            table.c.serial,
            table.c.alpha,
        )
        rows = conn.execute(query.order_by(table.c.alpha))
        return [
            alpha_regularization(store_id=row.serial, alpha=row.alpha)
            for row in rows
        ]

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.timestamp,
            table.c.alpha,
        )
        rows = conn.execute(query)

        earliest_timestamp: datetime = None
        latest_timestamp: datetime = None
        values = []

        for item in rows:
            if latest_timestamp is None or item.timestamp > latest_timestamp:
                latest_timestamp = item.timestamp
            if earliest_timestamp is None or item.timestamp < earliest_timestamp:
                earliest_timestamp = item.timestamp
            values.append(item.alpha)

        return {
            "earliest_timestamp": earliest_timestamp,
            "latest_timestamp": latest_timestamp,
            "values": values,
        }
