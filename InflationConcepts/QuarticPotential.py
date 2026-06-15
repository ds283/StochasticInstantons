from math import log
from typing import Optional

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential
from CosmologyConcepts.Potentials.model_ids import QUARTIC_POTENTIAL
from InflationConcepts.quartic_coupling import quartic_coupling
from Units.base import UnitsLike


class QuarticPotential(AbstractPotential):
    """
    Quartic inflationary potential V(φ) = λ φ⁴.

    Parameterised by a single dimensionless self-coupling λ, stored as a
    quartic_coupling object.
    """

    def __init__(self, store_id: int, lambda_: quartic_coupling, units: Optional[UnitsLike] = None):
        super().__init__(store_id, units)
        self._lambda: quartic_coupling = lambda_
        self._lambda_float: float = float(lambda_)

    @property
    def lambda_(self) -> quartic_coupling:
        return self._lambda

    @property
    def name(self) -> str:
        return f"QuarticPotential(lambda={self._lambda_float:.6g})"

    @property
    def type_id(self) -> int:
        return QUARTIC_POTENTIAL

    def V(self, phi: float) -> float:
        """V(φ) = λ φ⁴"""
        phi_sq = phi * phi
        return self._lambda_float * phi_sq * phi_sq

    def dV_dphi(self, phi: float) -> float:
        """V′(φ) = 4λ φ³"""
        return 4.0 * self._lambda_float * phi * phi * phi

    def d2V_dphi2(self, phi: float) -> float:
        """V′′(φ) = 12λ φ²"""
        return 12.0 * self._lambda_float * phi * phi

    def log_V(self, phi: float) -> float:
        """log V = log λ + 4 log |φ|. More stable than log(V(φ))."""
        return log(self._lambda_float) + 4.0 * log(abs(phi))

    def d_logV_dphi(self, phi: float) -> float:
        """(d/dφ) log V = 4/φ"""
        return 4.0 / phi
