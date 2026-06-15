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

import sqlalchemy as sqla

from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from Quadrature.integration_metadata import IntegrationSolver
from config.defaults import DEFAULT_STRING_LENGTH


class sqla_IntegrationSolver_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "stepping": "minimum",
            "timestamp": True,
            "columns": [
                sqla.Column("label", sqla.String(DEFAULT_STRING_LENGTH)),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        label = payload["label"]
        stepping = payload["stepping"]
        if stepping < 0:
            stepping = 0

        store_id = conn.execute(
            sqla.select(table.c.serial).filter(
                sqla.and_(table.c.label == label, table.c.stepping >= stepping)
            )
        ).scalar()

        if store_id is None:
            insert_data = {"label": label, "stepping": stepping}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)

            attribute_set = {"_new_insert": True}
        else:
            attribute_set = {"_deserialized": True}

        # return constructed object
        obj = IntegrationSolver(store_id=store_id, label=label, stepping=stepping)
        for key, value in attribute_set.items():
            setattr(obj, key, value)

        return obj
