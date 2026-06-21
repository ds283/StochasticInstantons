from datetime import datetime
from typing import Optional

from CosmologyConcepts.DimensionlessQuantity import DimensionlessQuantity


class delta_Nstar(DimensionlessQuantity):
    """
    The excess transition time ΔN★ for a stochastic instanton.

    ΔN★ = (actual transition time) − (noiseless transition time).

    ΔN★ ~ 0 is the noiseless limit; ΔN★ ~ 1 produces a density perturbation of
    order unity. ΔN★ can in principle be negative.

    This type also serves as the shard key for the sharded SQLite database:
    records are distributed across shards by the store_id of their associated
    delta_Nstar value.
    """

    def __init__(self, store_id: int, value: float, timestamp: Optional[datetime] = None):
        super().__init__(store_id, value, "delta_Nstar", timestamp=timestamp)

    @property
    def shard_key(self) -> "delta_Nstar":
        """delta_Nstar is its own shard key."""
        return self
