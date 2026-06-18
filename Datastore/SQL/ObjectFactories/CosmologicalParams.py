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


class sqla_cosmological_params_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column("name", sqla.String, index=True, unique=True, nullable=False),
                sqla.Column("omega_cc", sqla.Float(64), nullable=False),
                sqla.Column("omega_m", sqla.Float(64), nullable=False),
                sqla.Column("h", sqla.Float(64), nullable=False),
                sqla.Column("f_baryon", sqla.Float(64), nullable=False),
                sqla.Column("T_CMB_Kelvin", sqla.Float(64), nullable=False),
                sqla.Column("Neff", sqla.Float(64), nullable=False),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        from CosmologyModels.cosmo_params import CosmologicalParams

        params = payload["params"]
        name = params.name

        query = sqla.select(table.c.serial).filter(table.c.name == name)
        row = conn.execute(query).one_or_none()

        if row is None:
            insert_data = {
                "name": name,
                "omega_cc": params.omega_cc,
                "omega_m": params.omega_m,
                "h": params.h,
                "f_baryon": params.f_baryon,
                "T_CMB_Kelvin": params.T_CMB_Kelvin,
                "Neff": params.Neff,
            }
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            obj = CosmologicalParams(store_id=store_id, params=params)
            obj._new_insert = True
        else:
            store_id = row.serial
            obj = CosmologicalParams(store_id=store_id, params=params)
            obj._deserialized = True

        return obj

    def store(self, obj, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "CosmologicalParams is always fully written in build(). "
            "pool.object_store() should never be called for this type."
        )

    def validate(self, obj, conn, table, tables):
        raise NotImplementedError(
            "CosmologicalParams does not use the validate/store pipeline."
        )

    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
        return []

    def read_table(self, conn, table, tables, units=None):
        from CosmologyModels.cosmo_params import CosmologicalParams

        rows = conn.execute(sqla.select(table)).fetchall()
        results = []
        for row in rows:
            class _ParamsBundle:
                pass
            p = _ParamsBundle()
            p.name = row.name
            p.omega_cc = row.omega_cc
            p.omega_m = row.omega_m
            p.h = row.h
            p.f_baryon = row.f_baryon
            p.T_CMB_Kelvin = row.T_CMB_Kelvin
            p.Neff = row.Neff
            obj = CosmologicalParams(store_id=row.serial, params=p)
            obj._deserialized = True
            results.append(obj)
        return results

    def inventory(self, conn, table, tables):
        rows = conn.execute(sqla.select(table.c.serial, table.c.name)).fetchall()
        return {
            "validated": {
                "labels": [r.name for r in rows],
                "versions": [],
                "earliest_timestamp": None,
                "latest_timestamp": None,
            },
            "unvalidated": {
                "labels": [],
                "versions": [],
                "earliest_timestamp": None,
                "latest_timestamp": None,
            },
        }
