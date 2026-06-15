from CosmologyConcepts.DimensionfulQuantity import DimensionfulQuantity


class inflaton_mass(DimensionfulQuantity):
    """
    The mass parameter m in the quadratic inflationary potential V(φ) = ½ m² φ².
    Stored in units of the Planck mass.
    """
    default_unit = "PlanckMass"

    def __init__(self, store_id: int, value: float):
        super().__init__(store_id, value, "inflaton_mass")
