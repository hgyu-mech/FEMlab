"""2D explicit MPM: quadratic B-splines, PIC/FLIP/APIC, neo-Hookean solid.

Independent reference implementation, not MLS-MPM/CPDI/GIMP. One material,
unit out-of-plane thickness, interior stencils, optional sticky grid walls.
No multi-body contact, fracture, incompressibility solver or GPU backend.
"""
from dataclasses import dataclass
from itertools import product
import numpy as np
from numpy.typing import ArrayLike
from .core import array, positive


@dataclass
class Particles:
    x: np.ndarray
    v: np.ndarray
    mass: np.ndarray
    volume0: np.ndarray
    deformation: np.ndarray
    affine: np.ndarray

    @classmethod
    def create(cls, x: ArrayLike, velocity: ArrayLike, mass: ArrayLike, volume0: ArrayLike):
        x = array(x, 2).copy(); n = len(x)
        if x.shape != (n, 2) or n == 0:
            raise ValueError("Need nonempty (n,2) particle positions")
        v = np.broadcast_to(array(velocity), (n, 2)).copy()
        m = np.broadcast_to(array(mass), (n,)).copy()
        vol = np.broadcast_to(array(volume0), (n,)).copy()
        if np.any(m <= 0) or np.any(vol <= 0):
            raise ValueError("Particle mass and reference volume must be positive")
        return cls(x, v, m, vol, np.tile(np.eye(2), (n, 1, 1)), np.zeros((n, 2, 2)))

    def copy(self):
        return Particles(*(v.copy() for v in (self.x, self.v, self.mass,
                         self.volume0, self.deformation, self.affine)))


def stencil2d(x: ArrayLike, dx: float, cells: int):
    positive(dx=dx)
    if not isinstance(cells, int) or cells < 4:
        raise ValueError("Need at least four grid cells")
    x = array(x, 1)
    if x.shape != (2,):
        raise ValueError("Expected 2D position")
    base = np.floor(x/dx - .5).astype(int)
    if np.any(base < 0) or np.any(base+2 > cells):
        raise ValueError("Particle left interior support; enlarge domain, do not clip weights")
    f = x/dx - base
    w = np.array([.5*(1.5-f)**2, .75-(f-1)**2, .5*(f-.5)**2])
    dw = np.array([f-1.5, -2*(f-1), f-.5]) / dx
    for i, j in product(range(3), repeat=2):
        ij = base + [i, j]
        yield tuple(ij), w[i, 0]*w[j, 1], np.array([
            dw[i, 0]*w[j, 1], w[i, 0]*dw[j, 1]]), ij*dx-x


def neo_hookean(f: ArrayLike, young: float, poisson: float):
    """Cauchy stress and energy/reference volume, 3D law under plane strain."""
    f = array(f, 2)
    positive(young=young)
    if f.shape != (2, 2) or not np.isfinite(poisson) or not -1 < poisson < .5:
        raise ValueError("Invalid deformation or Poisson ratio")
    j = float(np.linalg.det(f))
    if j <= 0:
        raise ValueError("Nonpositive deformation determinant")
    mu = young / (2*(1+poisson))
    lam = young*poisson / ((1+poisson)*(1-2*poisson))
    stress = (mu*(f@f.T-np.eye(2)) + lam*np.log(j)*np.eye(2)) / j
    energy = .5*mu*(np.sum(f*f)-2) - mu*np.log(j) + .5*lam*np.log(j)**2
    return stress, float(energy)


class MPM2D:
    def __init__(self, cells: int = 24, dx: float = 1/24, young: float = 1000.,
                 poisson: float = .2, transfer: str = "apic", flip_ratio: float = .95,
                 gravity=(0., 0.), sticky_walls: bool = False):
        positive(dx=dx, young=young)
        if (not isinstance(cells, int) or cells < 4 or transfer not in {"pic", "flip", "apic"}
                or not np.isfinite(flip_ratio) or not 0 <= flip_ratio <= 1):
            raise ValueError("Invalid grid or transfer configuration")
        neo_hookean(np.eye(2), young, poisson)
        self.cells, self.dx, self.young, self.poisson = cells, dx, young, poisson
        self.transfer, self.flip_ratio = transfer, flip_ratio
        self.gravity = array(gravity, 1)
        if self.gravity.shape != (2,):
            raise ValueError("Expected 2D gravity")
        self.sticky_walls = sticky_walls

    def p2g(self, p: Particles):
        shape = (self.cells+1, self.cells+1)
        mass = np.zeros(shape); momentum = np.zeros((*shape, 2)); force = np.zeros_like(momentum)
        for n in range(len(p.x)):
            sigma, _ = neo_hookean(p.deformation[n], self.young, self.poisson)
            volume = p.volume0[n] * np.linalg.det(p.deformation[n])
            for ij, w, grad, distance in stencil2d(p.x[n], self.dx, self.cells):
                velocity = p.v[n] + (p.affine[n]@distance if self.transfer == "apic" else 0)
                mass[ij] += w*p.mass[n]
                momentum[ij] += w*p.mass[n]*velocity
                force[ij] -= volume*(sigma@grad)
        force += mass[..., None]*self.gravity
        return mass, momentum, force

    def stable_dt(self, p: Particles, cfl: float = .2):
        """Initial wave-speed estimate, NOT a nonlinear stability certificate."""
        if not 0 < cfl <= .5:
            raise ValueError("Require 0 < CFL <= 0.5")
        j = np.linalg.det(p.deformation)
        if np.any(j <= 0):
            raise ValueError("Inverted particle")
        density = p.mass / (p.volume0*j)
        wave = np.sqrt(self.young*(1-self.poisson) /
                       ((1+self.poisson)*(1-2*self.poisson)*density))
        speed = np.linalg.norm(p.v, axis=1)
        affine_speed = self.dx*np.linalg.norm(p.affine, axis=(1, 2)) if self.transfer == "apic" else 0
        return float(cfl*self.dx / np.max(wave+speed+affine_speed))

    def step(self, p: Particles, dt: float):
        positive(dt=dt)
        if dt > self.stable_dt(p):
            raise ValueError("dt exceeds conservative wave-speed estimate")
        mass, momentum, force = self.p2g(p)
        active = mass > 0
        old = np.zeros_like(momentum); old[active] = momentum[active]/mass[active, None]
        new = old.copy(); new[active] += dt*force[active]/mass[active, None]
        if self.sticky_walls:
            new[:2] = 0; new[-2:] = 0; new[:, :2] = 0; new[:, -2:] = 0
        q = p.copy()
        for n in range(len(p.x)):
            pic = np.zeros(2); delta = np.zeros(2); c = np.zeros((2, 2)); gradient = np.zeros((2, 2))
            for ij, w, grad, distance in stencil2d(p.x[n], self.dx, self.cells):
                pic += w*new[ij]
                delta += w*(new[ij]-old[ij])
                c += 4/self.dx**2*w*np.outer(new[ij], distance)
                gradient += np.outer(new[ij], grad)
            q.v[n] = ((1-self.flip_ratio)*pic + self.flip_ratio*(p.v[n]+delta)
                      if self.transfer == "flip" else pic)
            q.x[n] += dt*pic
            q.affine[n] = c if self.transfer == "apic" else 0
            q.deformation[n] = (np.eye(2)+dt*gradient)@p.deformation[n]
            neo_hookean(q.deformation[n], self.young, self.poisson)
            list(stencil2d(q.x[n], self.dx, self.cells))
        if not all(np.all(np.isfinite(v)) for v in (q.x, q.v, q.deformation, q.affine)):
            raise FloatingPointError("Nonfinite MPM state")
        return q

    def diagnostics(self, p: Particles):
        elastic = sum(vol*neo_hookean(f, self.young, self.poisson)[1]
                      for f, vol in zip(p.deformation, p.volume0))
        kinetic = .5*np.sum(p.mass[:, None]*p.v*p.v)
        affine = (.5*self.dx**2/4*np.sum(p.mass[:, None, None]*p.affine**2)
                  if self.transfer == "apic" else 0.)
        return {"mass": float(p.mass.sum()), "momentum": (p.mass@p.v).tolist(),
                "translational_kinetic": float(kinetic), "affine_kinetic": float(affine),
                "strain_energy": float(elastic), "potential": float(-p.mass@(p.x@self.gravity)),
                "minimum_J": float(np.min(np.linalg.det(p.deformation)))}
