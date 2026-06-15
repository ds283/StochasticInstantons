from datetime import datetime
from math import fabs

import sqlalchemy as sqla

from InflationConcepts.efold_value import efold_value
from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from config.defaults import (
    DEFAULT_EFOLD_PRECISION,
    DEFAULT_EFOLD_RELATIVE_PRECISION,
)


class sqla_efold_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column("N", sqla.Float(64), index=True),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        N = payload["N"]

        if fabs(N) == 0:
            query = sqla.select(table.c.serial).filter(
                sqla.func.abs(table.c.N - N) < DEFAULT_EFOLD_PRECISION
            )
        else:
            query = sqla.select(table.c.serial).filter(
                sqla.func.abs((table.c.N - N) / N) < DEFAULT_EFOLD_RELATIVE_PRECISION
            )

        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            insert_data = {"N": N}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            attribute_set = {"_deserialized": True}

        obj = efold_value(store_id=store_id, N=N)
        for key, value in attribute_set.items():
            setattr(obj, key, value)
        return obj

    def read_table(self, conn, table, tables, model_proxy=None):
        # TODO (Prompt 4): add join to InflatonTrajectoryValue table when model_proxy is not None
        query = sqla.select(
            table.c.serial,
            table.c.N,
        )
        rows = conn.execute(query.order_by(table.c.N))
        return [efold_value(store_id=row.serial, N=row.N) for row in rows]

    def inventory(self, conn, table, tables):
        query = sqla.select(
            table.c.timestamp,
            table.c.N,
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
            values.append(item.N)

        return {
            "earliest_timestamp": earliest_timestamp,
            "latest_timestamp": latest_timestamp,
            "values": values,
        }
