import sqlalchemy as sqla

from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from InflationConcepts.DiffusionModel.model_ids import MASSLESS_DECOUPLED_DIFFUSION
from InflationConcepts.DiffusionModel.registry import (
    DIFFUSION_MODEL_REGISTRY,
    DiffusionModelInfo,
)


class sqla_MasslessDecoupledDiffusion_factory(SQLAFactoryBase):

    def __init__(self):
        pass

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [],  # No parameters: only serial and timestamp.
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion

        # MasslessDecoupledDiffusion has no parameters, so there is at most
        # one row in this table.  Look it up; insert if absent.
        row_data = conn.execute(
            sqla.select(table.c.serial, table.c.timestamp)
        ).one_or_none()

        if row_data is None:
            insert_data = {}
            if "serial" in payload:
                insert_data["serial"] = payload["serial"]
            store_id = inserter(conn, insert_data)
            obj = MasslessDecoupledDiffusion(store_id=store_id)
            setattr(obj, "_new_insert", True)
        else:
            obj = MasslessDecoupledDiffusion(
                store_id=row_data.serial,
                timestamp=row_data.timestamp,
            )
            setattr(obj, "_deserialized", True)

        return obj

    def load_by_serial(self, conn, tables, serial):
        """Deserialize a MasslessDecoupledDiffusion instance by its serial."""
        from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion

        table = tables.get("MasslessDecoupledDiffusion")
        if table is None:
            return None

        row = conn.execute(
            sqla.select(table.c.serial, table.c.timestamp)
            .filter(table.c.serial == serial)
        ).one_or_none()

        if row is None:
            return None

        return MasslessDecoupledDiffusion(store_id=row.serial, timestamp=row.timestamp)


# Register so that read_table() can reconstruct the model from a stored
# diffusion_type integer without knowing the class name at call time.
DIFFUSION_MODEL_REGISTRY[MASSLESS_DECOUPLED_DIFFUSION] = DiffusionModelInfo(
    name="MasslessDecoupledDiffusion",
    factory=sqla_MasslessDecoupledDiffusion_factory(),
)
