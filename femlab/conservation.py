"""Fixed-position momentum projections for candidate particle velocities.

A diagnostic building block, not a reproduction of Park (2025)'s transfer solver.
The projection minimizes sum(m * ||v_corrected - v_proposed||^2) subject to
linear and optionally 2D angular momentum. It can change kinetic energy and
local constitutive/contact behavior. No trajectory accuracy guarantee follows.
"""
from dataclasses import dataclass
import numpy as np
from .core import array


@dataclass(frozen=True)
class ProjectionResult:
    velocity: np.ndarray
    linear_defect_before: float
    linear_defect_after: float
    angular_defect_after: float | None
    correction_mass_norm: float
    kinetic_energy_change: float


def momenta(positions, velocity, mass):
    x, v, m = array(positions, 2), array(velocity, 2), array(mass, 1)
    if (x.shape != v.shape or x.shape != (len(m), 2) or not len(m)
            or np.any(m <= 0)):
        raise ValueError("Require finite (n,2) positions/velocities and positive masses")
    return m @ v, float(m @ (x[:, 0]*v[:, 1]-x[:, 1]*v[:, 0]))


def project_momenta(positions, proposed_velocity, mass, target_linear,
                    target_angular=None):
    """Exact mass-metric least-change projection, up to floating-point error.

    Angular momentum is about the origin for translational point masses at FIXED
    positions. APIC affine angular momentum is not included. Boundary impulses
    and prescribed velocities must be dealt with by the calling discretization.
    """
    x, v, m = array(positions, 2), array(proposed_velocity, 2), array(mass, 1)
    linear, angular = momenta(x, v, m)
    target = array(target_linear, 1)
    if target.shape != (2,):
        raise ValueError("Target linear momentum must have two components")
    total_mass = float(m.sum())
    delta_p = target-linear
    center = (m @ x)/total_mass
    r = x-center
    corrected = v + delta_p/total_mass
    if target_angular is not None:
        if not np.isscalar(target_angular) or not np.isfinite(target_angular):
            raise ValueError("Target angular momentum must be a finite scalar")
        deficit = float(target_angular-angular-(center[0]*delta_p[1]-center[1]*delta_p[0]))
        inertia = float(np.sum(m[:, None]*r*r))
        scale = max(abs(angular), abs(float(target_angular)), 1.)
        if inertia <= np.finfo(float).tiny:
            if abs(deficit) > 1e-12*scale:
                raise ValueError("Infeasible angular constraint for coincident points")
        else:
            corrected += (deficit/inertia)*np.column_stack((-r[:, 1], r[:, 0]))
    if not np.all(np.isfinite(corrected)):
        raise FloatingPointError("Nonfinite momentum projection")
    after_p, after_l = momenta(x, corrected, m)
    correction = corrected-v
    return ProjectionResult(
        corrected, float(np.linalg.norm(delta_p)), float(np.linalg.norm(after_p-target)),
        None if target_angular is None else float(abs(after_l-target_angular)),
        float(np.sqrt(np.sum(m[:, None]*correction**2))),
        float(.5*np.sum(m[:, None]*(corrected**2-v**2))))


def work_balance_defect(energy_before, energy_after, external_work=0.,
                        physical_dissipation=0., energy_scale=1.):
    """Signed, work-corrected full-step defect, NOT a transfer-only energy loss.

    Positive defect means unexplained gain; negative means unexplained loss.
    The caller must compute consistent stored energy and real work/dissipation.
    """
    values = [energy_before, energy_after, external_work, physical_dissipation, energy_scale]
    if not np.all(np.isfinite(values)) or energy_scale <= 0 or physical_dissipation < 0:
        raise ValueError("Invalid energies, dissipation or normalization scale")
    return float((energy_after-energy_before-external_work+physical_dissipation)/energy_scale)
