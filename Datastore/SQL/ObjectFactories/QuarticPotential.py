import sqlalchemy as sqla

from CosmologyConcepts.Potentials.model_ids import QUARTIC_POTENTIAL
from InflationConcepts.QuarticPotential import QuarticPotential
from InflationConcepts.quartic_coupling import quartic_coupling
from datastorekit.SQL.factory_base import SQLAFactoryBase
from datastorekit.store_inventory import InventorySpec, Parent


class sqla_QuarticPotential_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column(
                    "coupling_id",
                    sqla.Integer,
                    sqla.ForeignKey("quartic_coupling.serial"),
                    index=True,
                    nullable=False,
                ),
                sqla.Column("type_id", sqla.Integer, nullable=False),
            ],
        }

    def inventory_spec(self):
        # build() matches coupling_id alone; type_id is stored, not matched (dk-and-rpk-migration
        # prompt 10)
        return InventorySpec(parents={"lambda_": Parent("coupling_id", of="quartic_coupling")})

    def build(self, payload, conn, table, inserter, tables, inserters):
        lambda_: quartic_coupling = payload["lambda_"]

        query = sqla.select(table.c.serial, table.c.timestamp).filter(
            table.c.coupling_id == lambda_.store_id
        )
        row_data = conn.execute(query).one_or_none()

        if row_data is None:
            insert_data = {
                "coupling_id": lambda_.store_id,
                "type_id": QUARTIC_POTENTIAL,
            }
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            timestamp = None
            attribute_set = {"_new_insert": True}
        else:
            store_id = row_data.serial
            timestamp = row_data.timestamp
            attribute_set = {"_deserialized": True}

        obj = QuarticPotential(store_id=store_id, lambda_=lambda_, units=payload.get("units", None), timestamp=timestamp)
        for key, value in attribute_set.items():
            setattr(obj, key, value)
        return obj

    def load_by_serial(self, conn, tables, serial, units=None):
        """Deserialize a single QuarticPotential by its own table serial."""
        table = tables["QuarticPotential"]
        coupling_table = tables["quartic_coupling"]

        row = conn.execute(
            sqla.select(
                table.c.serial,
                coupling_table.c.serial.label("coupling_serial"),
                coupling_table.c.value,
            ).select_from(
                table.join(coupling_table, table.c.coupling_id == coupling_table.c.serial)
            ).filter(table.c.serial == serial)
        ).one_or_none()

        if row is None:
            return None

        return QuarticPotential(
            store_id=row.serial,
            lambda_=quartic_coupling(store_id=row.coupling_serial, value=row.value),
            units=units,
        )

    def read_table(self, conn, table, tables):
        coupling_table = tables["quartic_coupling"]

        query = sqla.select(
            table.c.serial,
            coupling_table.c.serial.label("coupling_serial"),
            coupling_table.c.value,
        ).join(
            coupling_table, table.c.coupling_id == coupling_table.c.serial
        )

        rows = conn.execute(query)
        return [
            QuarticPotential(
                store_id=row.serial,
                lambda_=quartic_coupling(store_id=row.coupling_serial, value=row.value),
            )
            for row in rows
        ]
