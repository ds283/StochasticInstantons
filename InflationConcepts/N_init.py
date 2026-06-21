from datetime import datetime
from typing import Optional

from CosmologyConcepts.DimensionlessQuantity import DimensionlessQuantity


class N_init(DimensionlessQuantity):
    """
    The number of e-folds before the end of inflation at which a stochastic
    instanton calculation begins.

    N_init is measured *backwards* from the end of inflation: N_init = 20
    means "20 e-folds before the end of inflation". Convention: value > 0.
    """

    def __init__(self, store_id: int, value: float, timestamp: Optional[datetime] = None):
        super().__init__(store_id, value, "N_init", timestamp=timestamp)
