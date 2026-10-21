from math import fabs

import sqlalchemy as sqla

from InflationConcepts.N_init import N_init
from datastorekit.SQL.factory_base import SQLAFactoryBase
from datastorekit.store_inventory import InventorySpec
from config.defaults import (
    DEFAULT_EFOLD_PRECISION,
    DEFAULT_EFOLD_RELATIVE_PRECISION,
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

    def inventory_spec(self):
        # build() matches value alone, relatively (absolutely at 0) (dk-and-rpk-migration prompt 10)
        return InventorySpec(leaves=("value",))

    def build(self, payload, conn, table, inserter, tables, inserters):
        value = payload["value"]

        if fabs(value) == 0:
            query = sqla.select(table.c.serial, table.c.timestamp).filter(
                sqla.func.abs(table.c.value - value)
                < DEFAULT_EFOLD_PRECISION
            )
        else:
            query = sqla.select(table.c.serial, table.c.timestamp).filter(
                sqla.func.abs((table.c.value - value) / value)
                < DEFAULT_EFOLD_RELATIVE_PRECISION
            )

        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            insert_data = {"value": value}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            timestamp = None
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            timestamp = row_data.timestamp
            attribute_set = {"_deserialized": True}

        obj = N_init(store_id=store_id, value=value, timestamp=timestamp)
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
