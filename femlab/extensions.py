"""Explicit contracts for research extensions. Protocols are not implementations."""
from dataclasses import dataclass
from typing import Protocol
import numpy as np
from .core import array


class ParticleTransfer(Protocol):
    """All implementations must declare conserved quantities and valid stencils."""
    def particle_to_grid(self, particles, grid): ...
    def grid_to_particle(self, particles, grid, dt: float): ...


class CouplingOperator(Protocol):
    """Future partitioned FSI must report interface work and converged residual."""
    def exchange(self, solid_state, fluid_state, dt: float) -> dict: ...


class ContactLaw(Protocol):
    """Separate body identities and complementarity/friction tests required."""
    def solve(self, bodies, dt: float): ...


class NonlocalOperator(Protocol):
    """Future peridynamics: horizon, volume correction, damage state explicit."""
    def internal_force(self, state, horizon: float): ...


@dataclass(frozen=True)
class QuadratureRule:
    points: np.ndarray
    weights: np.ndarray

    def validate_moments(self, degree: int, tolerance: float = 1e-10):
        """Positive 1D rules on [-1,1]; finite moment checks, not universal accuracy."""
        x, w = array(self.points, 1), array(self.weights, 1)
        if (len(x) == 0 or x.shape != w.shape or np.any(abs(x) > 1)
                or np.any(w <= 0) or not isinstance(degree, int) or degree < 0
                or not np.isfinite(tolerance) or tolerance <= 0):
            raise ValueError("Invalid quadrature rule or tolerance")
        errors = [abs(w@x**k - (2/(k+1) if k % 2 == 0 else 0)) for k in range(degree+1)]
        if max(errors) > tolerance:
            raise ValueError("Quadrature failed polynomial moment validation")
        return float(max(errors))

    @classmethod
    def gauss_legendre(cls, order: int):
        if not isinstance(order, int) or order < 1:
            raise ValueError("Positive integer order required")
        return cls(*np.polynomial.legendre.leggauss(order))
