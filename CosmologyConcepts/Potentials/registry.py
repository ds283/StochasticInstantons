from dataclasses import dataclass
from typing import Dict

from CosmologyConcepts.Potentials.model_ids import QUADRATIC_POTENTIAL, QUARTIC_POTENTIAL
from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
from Datastore.SQL.ObjectFactories.QuadraticPotential import sqla_QuadraticPotential_factory
from Datastore.SQL.ObjectFactories.QuarticPotential import sqla_QuarticPotential_factory
from InflationConcepts.QuadraticPotential import QuadraticPotential
from InflationConcepts.QuarticPotential import QuarticPotential


@dataclass(frozen=True)
class PotentialTypeInfo:
    """
    Maps a potential's type_id to the concrete class, table, and factory
    needed to deserialize it. Add a new entry here whenever a new
    AbstractPotential subclass is introduced.
    """

    type_id: int
    slug: str
    table_name: str
    cls: type
    factory: SQLAFactoryBase


POTENTIAL_REGISTRY: Dict[int, PotentialTypeInfo] = {
    QUADRATIC_POTENTIAL: PotentialTypeInfo(
        type_id=QUADRATIC_POTENTIAL,
        slug="quadratic",
        table_name="QuadraticPotential",
        cls=QuadraticPotential,
        factory=sqla_QuadraticPotential_factory(),
    ),
    QUARTIC_POTENTIAL: PotentialTypeInfo(
        type_id=QUARTIC_POTENTIAL,
        slug="quartic",
        table_name="QuarticPotential",
        cls=QuarticPotential,
        factory=sqla_QuarticPotential_factory(),
    ),
}
