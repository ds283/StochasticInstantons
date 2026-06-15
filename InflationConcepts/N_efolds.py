from dataclasses import dataclass


@dataclass
class N_efolds:
    """
    A number of e-folds measured *backwards* from the end of inflation.

    N_efolds(20) means "20 e-folds before the end of inflation".
    N_efolds(5)  means "5 e-folds before the end of inflation".

    If the end of inflation occurs at integration coordinate N_end, then
    N_efolds(k) maps to the integration coordinate N_end − k.

    This is a plain Python dataclass, not a DatastoreObject. It is never
    persisted in its own database table; it appears as a plain float column
    on the payloads of InflatonTrajectory, FullInstanton, and SlowRollInstanton.

    Convention: value > 0 (a negative value would denote a time after the end
    of inflation, outside the domain of the instanton calculation).
    """

    value: float

    def __post_init__(self):
        if not isinstance(self.value, (int, float)):
            raise TypeError(
                f"N_efolds.value must be numeric, got {type(self.value)}"
            )
        self.value = float(self.value)

    def __float__(self) -> float:
        return self.value
