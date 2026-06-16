from datetime import datetime
from math import fabs

import sqlalchemy as sqla

from InflationConcepts.N_init import N_init
from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from config.defaults import (
    DEFAULT_DIMENSIONLESS_QUANTITY_PRECISION,
    DEFAULT_DIMENSIONLESS_QUANTITY_RELATIVE_PRECISION,
)


class sqla_N_init_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column("value", sqla.Float(64), index=True),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        value = payload["value"]

        if fabs(value) == 0:
            query = sqla.select(table.c.serial).filter(
                sqla.func.abs(table.c.value - value)
                < DEFAULT_DIMENSIONLESS_QUANTITY_PRECISION
            )
        else:
            query = sqla.select(table.c.serial).filter(
                sqla.func.abs((table.c.value - value) / value)
                < DEFAULT_DIMENSIONLESS_QUANTITY_RELATIVE_PRECISION
            )

        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            insert_data = {"value": value}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            attribute_set = {"_deserialized": True}

        obj = N_init(store_id=store_id, value=value)
        for key, v in attribute_set.items():
            setattr(obj, key, v)
        return obj

    def read_table(self, conn, table):
        query = sqla.select(
            table.c.serial,
            table.c.value,
        )
        rows = conn.execute(query.order_by(table.c.value))
        return [N_init(store_id=row.serial, value=row.value) for row in rows]

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.timestamp,
            table.c.value,
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
            values.append(item.value)

        return {
            "earliest_timestamp": earliest_timestamp,
            "latest_timestamp": latest_timestamp,
            "values": values,
        }
