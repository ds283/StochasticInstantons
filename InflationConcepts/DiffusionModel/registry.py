from dataclasses import dataclass
from typing import Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase


@dataclass
class DiffusionModelInfo:
    name: str
    factory: "SQLAFactoryBase"


# Populated by each concrete subclass factory module on import.
# Keys are type_id integers; values are DiffusionModelInfo instances.
DIFFUSION_MODEL_REGISTRY: Dict[int, DiffusionModelInfo] = {}
