from abc import ABC, abstractmethod
from datetime import datetime
from math import pi as PI
from typing import Any, Optional, Tuple

from Datastore import DatastoreObject


class AbstractDiffusionModel(DatastoreObject, ABC):
    """
    Abstract base class for the MSR stochastic diffusion matrix D_ij.

    Inherits from DatastoreObject so that concrete subclasses can be
    persisted and referenced by (diffusion_serial, diffusion_type) from
    FullInstanton and SlowRollInstanton, following the same pattern as
    AbstractPotential.

    The diffusion model is a peer input to the instanton solve alongside
    InflatonTrajectory.  It is NOT a property of the trajectory: the
    trajectory is the noiseless classical background and does not depend
    on the noise model.
    """

    def __init__(
        self,
        store_id: Optional[int],
        timestamp: Optional[datetime] = None,
    ):
        DatastoreObject.__init__(self, store_id, timestamp=timestamp)

    @property
    @abstractmethod
    def type_id(self) -> int:
        """Integer type identifier, unique per diffusion model class."""
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name, e.g. 'MasslessDecoupledDiffusion'."""
        raise NotImplementedError

    @abstractmethod
    def D_matrix(
        self,
        phi: float,
        pi: float,
        potential: Any,     # AbstractPotential; Any used to avoid circular import
    ) -> Tuple[float, float, float]:
        """Return (D11, D12, D22) at field-space position (phi, pi)."""
        raise NotImplementedError


class MasslessDecoupledDiffusion(AbstractDiffusionModel):
    """
    Massless de Sitter diffusion: Hankel index ν = 3/2 exactly.

    In this limit the π noise channel decouples: D₁₂ = D₂₂ = 0.
    Only the φ channel carries noise, with amplitude D₁₁ = H²/(8π²).
    H² is computed from potential.H_sq(phi, pi).

    This is the leading-order result for slow-roll inflation in quasi-de Sitter
    spacetime, valid when ε₂ = d ln ε/dN ≪ 1.

    TODO (future prompt): implement FullHankelDiffusion with
        ν² ≈ 9/4 + (3/2)ε₂ + (1/4)ε₂²
        D₁₂ = D₁₁·(ν - 3/2),   D₂₂ = D₁₁·(ν - 3/2)²
    which is relevant for USR and CR inflationary models.
    """

    def __init__(
        self,
        store_id: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ):
        super().__init__(store_id, timestamp=timestamp)

    @property
    def type_id(self) -> int:
        from InflationConcepts.DiffusionModel.model_ids import MASSLESS_DECOUPLED_DIFFUSION
        return MASSLESS_DECOUPLED_DIFFUSION

    @property
    def name(self) -> str:
        return "MasslessDecoupledDiffusion"

    def D_matrix(
        self,
        phi: float,
        pi: float,
        potential: Any,
    ) -> Tuple[float, float, float]:
        """
        Returns (D11, 0, 0).

        D11 = H²(φ, π)/(8π²), where H² = potential.H_sq(phi, pi).
        """
        H_sq = potential.H_sq(phi, pi)
        D11  = H_sq / (8.0 * PI * PI)
        return D11, 0.0, 0.0
