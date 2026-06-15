# CosmologyConcepts/Potentials/ExponentialPotential.py
# Skeleton retained from ChamPBH — will be adapted for inflationary ExponentialPotential
# in Prompt 2 (or later). The chameleon-specific body has been removed.

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential


class ExponentialPotential(AbstractPotential):
    """Placeholder. Will be replaced with the inflationary exponential potential."""

    def __init__(self, store_id: int, **kwargs):
        super().__init__(store_id)

    @property
    def name(self):
        raise NotImplementedError

    @property
    def type_id(self) -> int:
        raise NotImplementedError

    @property
    def bounce_region_level1_boundary(self) -> float:
        raise NotImplementedError

    @property
    def bounce_region_level2_boundary(self) -> float:
        raise NotImplementedError

    @property
    def bounce_region_level1_max_step(self) -> float:
        raise NotImplementedError

    @property
    def bounce_region_level2_max_step(self) -> float:
        raise NotImplementedError

    @property
    def hard_reflection_point(self) -> float:
        raise NotImplementedError
