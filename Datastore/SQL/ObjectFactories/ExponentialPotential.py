# Datastore/SQL/ObjectFactories/ExponentialPotential.py
# Skeleton retained from ChamPBH — will be replaced in Prompt 2 with the
# factory for the inflationary ExponentialPotential once that type is defined.

from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase


class sqla_ExponentialPotential_factory(SQLAFactoryBase):
    def __init__(self):
        pass

    def register(self):
        return {
            "version": True,
            "timestamp": True,
            "columns": [],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        raise NotImplementedError(
            "sqla_ExponentialPotential_factory.build() is not yet implemented. "
            "This will be defined in Prompt 2."
        )
