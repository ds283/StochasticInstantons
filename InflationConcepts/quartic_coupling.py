from datetime import datetime
from typing import Optional

from CosmologyConcepts.DimensionlessQuantity import DimensionlessQuantity


class quartic_coupling(DimensionlessQuantity):
    """
    The dimensionless self-coupling λ in the quartic inflationary potential
    V(φ) = λ φ⁴.
    """

    def __init__(self, store_id: int, value: float, timestamp: Optional[datetime] = None):
        super().__init__(store_id, value, "quartic_coupling", timestamp=timestamp)
