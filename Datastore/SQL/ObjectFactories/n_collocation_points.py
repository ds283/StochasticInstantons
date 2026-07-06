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

import sqlalchemy as sqla

from InflationConcepts.n_collocation_points import n_collocation_points
from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase


class sqla_n_collocation_points_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column("n_collocation_points", sqla.Integer, index=True),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        value = payload["n_collocation_points"]

        # n_collocation_points is an exact integer count, not a continuous
        # physical quantity -- lookup uses exact equality, not a
        # tolerance-banded comparison.
        query = sqla.select(table.c.serial, table.c.timestamp).filter(
            table.c.n_collocation_points == value
        )

        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            insert_data = {"n_collocation_points": value}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            timestamp = None
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            timestamp = row_data.timestamp
            attribute_set = {"_deserialized": True}

        obj = n_collocation_points(
            store_id=store_id, n_collocation_points=value, timestamp=timestamp
        )
        for key, v in attribute_set.items():
            setattr(obj, key, v)
        return obj

    def read_table(self, conn, table):
        query = sqla.select(
            table.c.serial,
            table.c.n_collocation_points,
        )
        rows = conn.execute(query.order_by(table.c.n_collocation_points))
        return [
            n_collocation_points(
                store_id=row.serial, n_collocation_points=row.n_collocation_points
            )
            for row in rows
        ]

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.timestamp,
            table.c.n_collocation_points,
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
            values.append(item.n_collocation_points)

        return {
            "earliest_timestamp": earliest_timestamp,
            "latest_timestamp": latest_timestamp,
            "values": values,
        }
