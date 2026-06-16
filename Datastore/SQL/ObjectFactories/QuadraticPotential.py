from datetime import datetime

import sqlalchemy as sqla

from CosmologyConcepts.Potentials.model_ids import QUADRATIC_POTENTIAL
from InflationConcepts.QuadraticPotential import QuadraticPotential
from InflationConcepts.inflaton_mass import inflaton_mass
from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase


class sqla_QuadraticPotential_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column(
                    "mass_id",
                    sqla.Integer,
                    sqla.ForeignKey("inflaton_mass.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column("type_id", sqla.Integer, nullable=False),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        m: inflaton_mass = payload["m"]

        query = sqla.select(table.c.serial).filter(
            table.c.mass_id == m.store_id
        )
        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            insert_data = {"mass_id": m.store_id, "type_id": QUADRATIC_POTENTIAL}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            attribute_set = {"_deserialized": True}

        obj = QuadraticPotential(store_id=store_id, m=m, units=payload.get("units", None))
        for key, value in attribute_set.items():
            setattr(obj, key, value)
        return obj

    def load_by_serial(self, conn, tables, serial, units=None):
        """Deserialize a single QuadraticPotential by its own table serial."""
        table = tables["QuadraticPotential"]
        mass_table = tables["inflaton_mass"]

        row = conn.execute(
            sqla.select(
                table.c.serial,
                mass_table.c.serial.label("mass_serial"),
                mass_table.c["value_PlanckMass"],
            ).select_from(
                table.join(mass_table, table.c.mass_id == mass_table.c.serial)
            ).filter(table.c.serial == serial)
        ).one_or_none()

        if row is None:
            return None

        return QuadraticPotential(
            store_id=row.serial,
            m=inflaton_mass(store_id=row.mass_serial, value=row.value_PlanckMass),
            units=units,
        )

    def read_table(self, conn, table, tables):
        mass_table = tables["inflaton_mass"]

        query = sqla.select(
            table.c.serial,
            mass_table.c.serial.label("mass_serial"),
            mass_table.c[f"value_PlanckMass"],
        ).join(
            mass_table, table.c.mass_id == mass_table.c.serial
        )

        rows = conn.execute(query)
        return [
            QuadraticPotential(
                store_id=row.serial,
                m=inflaton_mass(store_id=row.mass_serial, value=row.value_PlanckMass),
            )
            for row in rows
        ]

    def inventory(self, conn, table, tables):
        mass_table = tables["inflaton_mass"]

        query = sqla.select(
            table.c.timestamp,
            mass_table.c[f"value_PlanckMass"],
        ).join(
            mass_table, table.c.mass_id == mass_table.c.serial
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
            values.append(item.value_PlanckMass)

        return {
            "earliest_timestamp": earliest_timestamp,
            "latest_timestamp": latest_timestamp,
            "values": values,
        }
