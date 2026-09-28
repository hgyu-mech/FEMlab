"""Meshfree building blocks, not a completed EFG/SPH solid solver."""
import numpy as np
from numpy.typing import ArrayLike
from .core import array, positive


def mls_shape(point: ArrayLike, nodes: ArrayLike, radius: float):
    """Linear reproducing MLS with compact Wendland weights in any dimension.

    Returns shape values, not derivatives. Shape values need not interpolate
    nodal data or be positive. Essential BCs need a separate EFG treatment.
    """
    x, nodes = array(point, 1), array(nodes, 2)
    positive(radius=radius)
    if nodes.shape[1] != len(x):
        raise ValueError("Point and nodes have incompatible dimensions")
    z = (nodes-x) / radius
    r = np.linalg.norm(z, axis=1)
    w = np.maximum(1-r, 0)**4 * (4*r+1)
    p = np.column_stack((np.ones(len(nodes)), z))
    moment = p.T @ (w[:, None] * p)
    if not np.isfinite(np.linalg.cond(moment)) or np.linalg.cond(moment) > 1e12:
        raise ValueError("Insufficient or degenerate MLS support")
    e = np.zeros(p.shape[1]); e[0] = 1
    return w * (p @ np.linalg.solve(moment, e))


def poisson_1d(nodes: ArrayLike, source: ArrayLike, boundary=(0., 0.), stencil: int = 7):
    """Solve -u''=source on scattered 1D nodes using local RBF-FD.

    Cubic polyharmonic kernel |r|^3, quadratic polynomial augmentation,
    scaled local coordinates, strong Dirichlet endpoints. Research baseline.
    """
    x, f = array(nodes, 1), array(source, 1)
    bc = array(boundary, 1)
    if (len(x) < 5 or np.any(np.diff(x) <= 0) or f.shape != x.shape
            or bc.shape != (2,) or not isinstance(stencil, int) or not 4 <= stencil <= len(x)):
        raise ValueError("Need increasing nodes, matching source and valid stencil")
    a = np.zeros((len(x), len(x))); rhs = f.copy()
    for i in range(1, len(x)-1):
        ids = np.argsort(abs(x-x[i]), kind="stable")[:stencil]
        scale = max(abs(x[ids]-x[i]))
        z = (x[ids]-x[i]) / scale
        p = np.column_stack((np.ones(stencil), z, z*z))
        phi = abs(z[:, None]-z[None, :])**3
        system = np.block([[phi, p], [p.T, np.zeros((3, 3))]])
        target = np.r_[-6*abs(z), [0., 0., -2.]]
        weights = np.linalg.solve(system, target)[:stencil] / scale**2
        a[i, ids] = weights
    a[0, 0] = a[-1, -1] = 1
    rhs[0], rhs[-1] = bc
    return np.linalg.solve(a, rhs)
