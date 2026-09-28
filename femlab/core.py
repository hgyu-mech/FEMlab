"""Small dense reference systems. No automatic stabilization of mechanisms."""
from dataclasses import dataclass
from typing import Mapping, Protocol
import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]


def array(value: ArrayLike, ndim: int | None = None) -> FloatArray:
    out = np.asarray(value, dtype=float)
    if (ndim is not None and out.ndim != ndim) or not np.all(np.isfinite(out)):
        raise ValueError("Expected a finite array with the requested dimension")
    return out


def positive(**values: float) -> None:
    if any(not np.isfinite(v) or v <= 0 for v in values.values()):
        raise ValueError(f"Expected positive finite parameters: {tuple(values)}")


@dataclass(frozen=True)
class StaticResult:
    displacement: FloatArray
    reaction: FloatArray
    strain_energy: float
    free_residual_norm: float


class ConstitutiveModel(Protocol):
    """Future materials must declare stress measure and return its consistent tangent."""
    def stress_tangent(self, strain: FloatArray) -> tuple[FloatArray, FloatArray]: ...


class Surrogate(Protocol):
    def fit(self, x: FloatArray, y: FloatArray): ...
    def predict(self, x: FloatArray) -> FloatArray: ...


def add_element(k: FloatArray, dofs: ArrayLike, ke: ArrayLike) -> None:
    ids = np.asarray(dofs)
    element = array(ke, 2)
    if (ids.ndim != 1 or not np.issubdtype(ids.dtype, np.integer)
            or len(np.unique(ids)) != len(ids) or np.any(ids < 0)
            or np.any(ids >= len(k)) or element.shape != (len(ids), len(ids))):
        raise ValueError("Invalid element DOFs or stiffness shape")
    k[np.ix_(ids, ids)] += element


def partition(n: int, prescribed: Mapping[int, float]):
    if any(not isinstance(i, (int, np.integer)) or i < 0 or i >= n
           or not np.isfinite(v) for i, v in prescribed.items()):
        raise ValueError("Invalid Dirichlet condition")
    fixed = np.array(sorted(prescribed), dtype=int)
    free = np.setdiff1d(np.arange(n), fixed)
    u = np.zeros(n)
    for i in fixed:
        u[i] = prescribed[i]
    return free, fixed, u


def solve_static(k: ArrayLike, force: ArrayLike,
                 prescribed: Mapping[int, float]) -> StaticResult:
    """Eliminate prescribed DOFs, including nonzero values; return full reactions.

    For small symmetric positive-definite free systems only. Ill-conditioned or
    indefinite systems are rejected, not silently regularized. Mixed units may
    require explicit nondimensionalization before this diagnostic is appropriate.
    """
    k, f = array(k, 2), array(force, 1)
    if k.shape != (len(f), len(f)) or not np.allclose(k, k.T, rtol=1e-12, atol=1e-14):
        raise ValueError("Expected square symmetric stiffness matching the force")
    free, fixed, u = partition(len(f), prescribed)
    if len(free):
        a = k[np.ix_(free, free)]
        eig = np.linalg.eigvalsh(a)
        if eig[-1] <= 0 or eig[0] <= 1e-12 * eig[-1]:
            raise ValueError("Free stiffness is singular, indefinite or ill-conditioned; check constraints")
        rhs = f[free] - k[np.ix_(free, fixed)] @ u[fixed]
        u[free] = np.linalg.solve(a, rhs)
    residual = k @ u - f
    return StaticResult(u, residual, float(0.5 * u @ k @ u),
                        float(np.linalg.norm(residual[free])))
