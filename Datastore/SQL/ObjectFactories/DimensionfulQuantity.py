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

from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from Units.base import UnitsLike
from config.defaults import (
    DEFAULT_DIMENSIONFUL_QUANTITY_PRECISION,
    DEFAULT_DIMENSIONFUL_QUANTITY_RELATIVE_PRECISION,
)


class sqla_dimensionful_quantity_factory(SQLAFactoryBase):
    def __init__(self, ObjectType):
        self.ObjectType = ObjectType

        self.value_col: str = f"value_{ObjectType.default_unit}"

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column(self.value_col, sqla.Float(64), index=True),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        value = payload["value"]
        units = payload["units"]

        try:
            unit = getattr(units, self.ObjectType.default_unit)
        except TypeError as e:
            print(
                f'TypeError encountered in sqla_dimensionful_quantity_factory.build(): self.ObjectType="{self.ObjectType.__name__}", self.ObjectType.default_unit="{self.ObjectType.default_unit}"'
            )
            raise e

        if unit is None:
            raise RuntimeError(
                f'default_unit must be a class attribute of specified object type "{self.ObjectType.__name__}"'
            )
        value_in_units = value / unit

        if fabs(value_in_units) == 0:
            query = sqla.select(
                table.c.serial,
            ).filter(
                sqla.func.abs(table.c[self.value_col] - value_in_units)
                < DEFAULT_DIMENSIONFUL_QUANTITY_PRECISION
            )
        else:
            query = sqla.select(
                table.c.serial,
            ).filter(
                sqla.func.abs(
                    (table.c[self.value_col] - value_in_units) / value_in_units
                )
                < DEFAULT_DIMENSIONFUL_QUANTITY_RELATIVE_PRECISION
            )
        row_data = conn.execute(query).one_or_none()

        # if this quantity is not already present, create a new id using the provided inserter
        if row_data is None:
            insert_data = {self.value_col: value_in_units}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            attribute_set = {"_deserialized": True}

        # return the constructed object
        obj = self.ObjectType(
            store_id=store_id,
            value=value,
        )
        for k, v in attribute_set.items():
            setattr(obj, k, v)
        return obj

    def read_table(
        self,
        conn,
        table,
        units: UnitsLike,
    ):
        unit = getattr(units, self.ObjectType.default_unit)

        # query for all value records in the table
        query = sqla.select(
            table.c.serial,
            table.c[self.value_col],
        )

        rows = conn.execute(query.order_by(table.c[self.value_col]))

        return [
            self.ObjectType(
                store_id=row.serial, value=row._mapping[self.value_col] * unit
            )
            for row in rows
        ]

    def inventory(self, conn, table, tables, units):
        unit = getattr(units, self.ObjectType.default_unit)

        query = sqla.select(
            table.c.timestamp,
            table.c[self.value_col],
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

            values.append(item._mapping[self.value_col] * unit)

        return {
            "earliest_timestamp": earliest_timestamp,
            "latest_timestamp": latest_timestamp,
            "values": values,
            "unit": self.ObjectType.default_unit,
        }
