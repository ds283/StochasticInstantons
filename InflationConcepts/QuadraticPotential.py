from datetime import datetime
from math import log
from typing import Optional

from CosmologyConcepts.Potentials.AbstractPotential import AbstractPotential
from CosmologyConcepts.Potentials.model_ids import QUADRATIC_POTENTIAL
from InflationConcepts.inflaton_mass import inflaton_mass
from Units.base import UnitsLike


class QuadraticPotential(AbstractPotential):
    """
    Quadratic inflationary potential V(φ) = ½ m² φ².

    Parameterised by a single mass scale m, stored as an inflaton_mass object
    (in units of the Planck mass).
    """

    def __init__(self, store_id: int, m: inflaton_mass, units: Optional[UnitsLike] = None, timestamp: Optional[datetime] = None):
        super().__init__(store_id, units, timestamp=timestamp)
        self._m: inflaton_mass = m
        self._m_float: float = float(m)
        self._m_sq: float = self._m_float * self._m_float

    @property
    def m(self) -> inflaton_mass:
        return self._m

    @property
    def name(self) -> str:
        return f"QuadraticPotential(m={self._m_float:.6g} Mp)"

    @property
    def type_id(self) -> int:
        return QUADRATIC_POTENTIAL

    def V(self, phi: float) -> float:
        """V(φ) = ½ m² φ²"""
        return 0.5 * self._m_sq * phi * phi

    def dV_dphi(self, phi: float) -> float:
        """V′(φ) = m² φ"""
        return self._m_sq * phi

    def d2V_dphi2(self, phi: float) -> float:
        """V′′(φ) = m²"""
        return self._m_sq

    def log_V(self, phi: float) -> float:
        """log V = log(½) + 2 log m + 2 log |φ|. More stable than log(V(φ))."""
        return log(0.5) + 2.0 * log(self._m_float) + 2.0 * log(abs(phi))

    def d_logV_dphi(self, phi: float) -> float:
        """(d/dφ) log V = 2/φ"""
        return 2.0 / phi
