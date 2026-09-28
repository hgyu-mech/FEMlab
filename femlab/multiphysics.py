"""One-way 1D steady heat -> small-strain thermoelastic bar baseline."""
import numpy as np
from .core import array, positive, add_element, solve_static
from .fem import bar_stiffness


def thermal_bar(nodes, conductivity, area, temperature_bc, young, expansion,
                reference_temperature, displacement_bc, mechanical_force=None):
    x = array(nodes, 1)
    positive(conductivity=conductivity, area=area, young=young)
    if len(x) < 2 or np.any(np.diff(x) <= 0):
        raise ValueError("Require at least two increasing bar nodes")
    if not np.isfinite(expansion) or not np.isfinite(reference_temperature):
        raise ValueError("Invalid thermal parameters")
    heat = np.zeros((len(x), len(x))); mechanical = np.zeros_like(heat)
    for i, length in enumerate(np.diff(x)):
        add_element(heat, [i, i+1], bar_stiffness(conductivity, area, length))
        add_element(mechanical, [i, i+1], bar_stiffness(young, area, length))
    t = solve_static(heat, np.zeros(len(x)), temperature_bc).displacement
    force = (np.zeros(len(x)) if mechanical_force is None else array(mechanical_force, 1).copy())
    if force.shape != x.shape:
        raise ValueError("Mechanical force shape mismatch")
    for i in range(len(x)-1):
        strain = expansion*((t[i]+t[i+1])/2-reference_temperature)
        force[i:i+2] += young*area*strain*np.array([-1., 1.])
    result = solve_static(mechanical, force, displacement_bc)
    stress = young*(np.diff(result.displacement)/np.diff(x)
                    - expansion*((t[:-1]+t[1:])/2-reference_temperature))
    # Elastic stored energy uses elastic strain, not 0.5*u.T*K*u under thermal loading.
    energy = float(np.sum(stress**2/(2*young)*area*np.diff(x)))
    return {"temperature": t, "displacement": result.displacement,
            "reaction": result.reaction, "stress": stress, "elastic_energy": energy}
