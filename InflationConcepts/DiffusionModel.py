from abc import ABC, abstractmethod
from math import pi as PI
from typing import Any, Tuple


class AbstractDiffusionModel(ABC):
    """
    Encapsulates the stochastic diffusion matrix D_ij for the MSR instanton
    equations. D_ij = P_ij / 2, where P_ij is the dimensionless power spectrum
    matrix of the phase-space noise fields (φ, π).

    The matrix is a function of the current field-space position (φ, π) and is
    evaluated point-by-point along the trajectory, following a Markov property.

    Subclass and override D_matrix() to implement different noise models.
    The full ν-dependent expression (including metric mixing) should be
    implemented in a future FullHankelDiffusion subclass that computes ν
    from ε₂ = d ln ε/dN at each point on the trajectory.
    """

    @abstractmethod
    def D_matrix(
        self,
        phi: float,
        pi: float,
        potential: Any,     # AbstractPotential; Any used to avoid circular import
    ) -> Tuple[float, float, float]:
        """
        Return (D11, D12, D22) at field-space coordinates (phi, pi).

        The potential is supplied so that H²(φ, π) — and hence D₁₁ — can be
        computed without requiring a separate Mp argument; Mp is sourced from
        potential._units.PlanckMass.

        Units of D_ij are the same as H² (energy² in natural units).
        """
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
