from datetime import datetime
from math import fabs

import sqlalchemy as sqla

from InflationConcepts.y_value import y_value
from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from config.defaults import (
    DEFAULT_Y_PRECISION,
    DEFAULT_Y_RELATIVE_PRECISION,
)


class sqla_y_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column("y", sqla.Float(64), index=True),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        y = payload["y"]

        if fabs(y) == 0:
            query = sqla.select(table.c.serial, table.c.timestamp).filter(
                sqla.func.abs(table.c.y - y) < DEFAULT_Y_PRECISION
            )
        else:
            query = sqla.select(table.c.serial, table.c.timestamp).filter(
                sqla.func.abs((table.c.y - y) / y) < DEFAULT_Y_RELATIVE_PRECISION
            )

        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            insert_data = {"y": y}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            timestamp = None
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            timestamp = row_data.timestamp
            attribute_set = {"_deserialized": True}

        obj = y_value(store_id=store_id, y=y, timestamp=timestamp)
        for key, value in attribute_set.items():
            setattr(obj, key, value)
        return obj

    def read_table(self, conn, table, tables, model_proxy=None):
        # TODO (Prompt N): add join to GradientCoupledInstantonValue/
        #  GradientCoupledCompactionFunctionSamples table when model_proxy is not None
        query = sqla.select(
            table.c.serial,
            table.c.y,
        )
        rows = conn.execute(query.order_by(table.c.y))
        return [y_value(store_id=row.serial, y=row.y) for row in rows]

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.timestamp,
            table.c.y,
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
            values.append(item.y)

        return {
            "earliest_timestamp": earliest_timestamp,
            "latest_timestamp": latest_timestamp,
            "values": values,
        }
