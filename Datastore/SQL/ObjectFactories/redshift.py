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
from math import fabs
import sqlalchemy as sqla

from CosmologyConcepts import redshift
from datastorekit.SQL.factory_base import SQLAFactoryBase
from datastorekit.store_inventory import InventorySpec
from config.defaults import (
    DEFAULT_REDSHIFT_RELATIVE_PRECISION,
    DEFAULT_REDSHIFT_PRECISION,
)


class sqla_redshift_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column("z", sqla.Float(64), index=True),
            ],
        }

    def inventory_spec(self):
        # build() matches z alone, relatively (absolutely at z = 0) (dk-and-rpk-migration prompt 10)
        return InventorySpec(leaves=("z",))

    def build(self, payload, conn, table, inserter, tables, inserters):
        z = payload["z"]

        # query for this redshift in the datastore
        if fabs(z) == 0:
            query = sqla.select(table.c.serial).filter(
                sqla.func.abs((table.c.z - z) < DEFAULT_REDSHIFT_PRECISION)
            )
        else:
            query = sqla.select(
                table.c.serial,
            ).filter(
                sqla.func.abs((table.c.z - z) / z) < DEFAULT_REDSHIFT_RELATIVE_PRECISION
            )

        row_data = conn.execute(query).one_or_none()

        # if not present, create a new id using the provided inserter
        if row_data is None:
            insert_data = {"z": z}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            attribute_set = {"_deserialized": True}

        # return the constructed object
        obj = redshift(
            store_id=store_id,
            z=z,
        )
        for key, value in attribute_set.items():
            setattr(obj, key, value)
        return obj

    def read_table(self, conn, table, tables):
        query = sqla.select(
            table.c.serial,
            table.c.z,
        )

        rows = conn.execute(query.order_by(table.c.z))

        return [
            redshift(
                store_id=row.serial,
                z=row.z,
            )
            for row in rows
        ]
