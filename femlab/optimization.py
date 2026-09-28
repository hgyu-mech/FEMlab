"""Truss density-SIMP, verified sensitivities and bounded design search."""
import numpy as np
from scipy.optimize import minimize
from numpy.typing import ArrayLike
from .core import array, add_element, solve_static
from .fem import assemble_truss


class TrussSIMP:
    """Compliance minimization on a FIXED truss graph.

    Not continuum topology optimization, shape optimization, or manufacturing
    certification. Supports homogeneous displacement constraints only.
    """
    def __init__(self, nodes, edges, young, areas, force, prescribed, penal=3., floor=1e-5):
        if not np.isfinite(penal) or penal < 1 or not 0 < floor < 1:
            raise ValueError("Invalid SIMP parameters")
        if any(v != 0 for v in prescribed.values()):
            raise ValueError("SIMP derivative assumes homogeneous constraints")
        self.base, self.elements = assemble_truss(nodes, edges, young, areas)
        self.force, self.prescribed = array(force, 1), dict(prescribed)
        nodes, edges, areas = array(nodes, 2), np.asarray(edges), array(areas, 1)
        self.volumes = np.linalg.norm(nodes[edges[:, 1]]-nodes[edges[:, 0]], axis=1)*areas
        self.penal, self.floor = penal, floor
        solve_static(self.base, self.force, self.prescribed)

    def evaluate(self, density: ArrayLike):
        rho = array(density, 1)
        if len(rho) != len(self.elements) or np.any(rho < 0) or np.any(rho > 1):
            raise ValueError("Invalid density")
        scale = self.floor+(1-self.floor)*rho**self.penal
        k = np.zeros_like(self.base)
        for s, (dofs, ke) in zip(scale, self.elements):
            add_element(k, dofs, s*ke)
        u = solve_static(k, self.force, self.prescribed).displacement
        energy = np.array([u[d]@ke@u[d] for d, ke in self.elements])
        derivative = -(1-self.floor)*self.penal*rho**(self.penal-1)*energy
        return float(self.force@u), derivative, u

    def optimize(self, volume_fraction: float = .5, maxiter: int = 100):
        if not .01 <= volume_fraction <= 1 or maxiter < 1:
            raise ValueError("Invalid volume fraction or iterations")
        x0 = np.full(len(self.elements), volume_fraction)
        baseline = self.evaluate(x0)[0]
        scale = max(abs(baseline), 1e-12)
        weights = self.volumes/self.volumes.sum()
        result = minimize(lambda x: self.evaluate(x)[0]/scale, x0,
                          jac=lambda x: self.evaluate(x)[1]/scale,
                          bounds=[(.01, 1.)]*len(x0), method="SLSQP",
                          constraints={"type": "ineq", "fun": lambda x: volume_fraction-weights@x,
                                       "jac": lambda x: -weights},
                          options={"maxiter": maxiter, "ftol": 1e-10})
        if not result.success or weights@result.x > volume_fraction+1e-7:
            raise RuntimeError(f"Optimization failed: {result.message}")
        result.compliance = self.evaluate(result.x)[0]
        result.initial_compliance = baseline
        result.volume_fraction = float(weights@result.x)
        return result


def finite_difference_gradient(function, x: ArrayLike, step: float = 1e-6):
    x = array(x, 1)
    if not np.isfinite(step) or step <= 0:
        raise ValueError("Positive step required")
    g = np.zeros_like(x)
    for i in range(len(x)):
        h = step*max(1., abs(x[i])); delta = np.zeros_like(x); delta[i] = h
        g[i] = (function(x+delta)-function(x-delta))/(2*h)
    return g


def bounded_search(function, bounds: ArrayLike, samples: int = 64, seed: int = 0):
    """Budgeted random-search BASELINE for shape/material/transfer parameters.

    Returns a sampled best point, not a global-optimum certificate. No TLBO claim.
    Invalid simulations should raise; they are never assigned fabricated results.
    """
    b = array(bounds, 2)
    if b.shape[1] != 2 or np.any(b[:, 1] <= b[:, 0]) or samples < 1:
        raise ValueError("Invalid search bounds or sample budget")
    points = np.random.default_rng(seed).uniform(b[:, 0], b[:, 1], (samples, len(b)))
    values = np.array([function(p) for p in points], dtype=float)
    if values.shape != (samples,) or not np.all(np.isfinite(values)):
        raise ValueError("Objective must return a finite scalar")
    i = int(np.argmin(values))
    return points[i], float(values[i])
