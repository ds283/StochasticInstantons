from abc import ABC, abstractmethod
from math import log

from Datastore import DatastoreObject


class AbstractPotential(DatastoreObject, ABC):
    """
    Abstract base class for inflationary scalar field potentials V(φ).

    All quantities are in natural units with the reduced Planck mass Mp = 1
    (i.e. 8πG = 1). Concrete subclasses must implement V(), dV_dphi(), and
    d2V_dphi2(). Default implementations of log_V() and d_logV_dphi() are
    provided but may be overridden for numerical stability.
    """

    def __init__(self, store_id: int):
        DatastoreObject.__init__(self, store_id)

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name, e.g. 'QuadraticPotential(m=1.23e-6 Mp)'."""
        raise NotImplementedError

    @property
    @abstractmethod
    def type_id(self) -> int:
        """Integer type identifier, unique per potential class."""
        raise NotImplementedError

    @abstractmethod
    def V(self, phi: float) -> float:
        """Potential energy V(φ)."""
        raise NotImplementedError

    @abstractmethod
    def dV_dphi(self, phi: float) -> float:
        """First derivative V′(φ)."""
        raise NotImplementedError

    @abstractmethod
    def d2V_dphi2(self, phi: float) -> float:
        """Second derivative V′′(φ)."""
        raise NotImplementedError

    def log_V(self, phi: float) -> float:
        """
        log V(φ). Default implementation calls V(). Subclasses may override for
        improved numerical stability when V spans many orders of magnitude.
        """
        return log(self.V(phi))

    def d_logV_dphi(self, phi: float) -> float:
        """
        (d/dφ) log V = V′(φ) / V(φ). Default implementation calls dV_dphi()
        and V(). Subclasses may override.
        """
        return self.dV_dphi(phi) / self.V(phi)
