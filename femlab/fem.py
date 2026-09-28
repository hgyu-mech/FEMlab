"""Linear bar, 2D truss, Euler-Bernoulli beam and constant-strain triangle."""
import numpy as np
from numpy.typing import ArrayLike
from .core import array, positive, add_element


def bar_stiffness(young: float, area: float, length: float):
    positive(young=young, area=area, length=length)
    return young * area / length * np.array([[1., -1.], [-1., 1.]])


def truss_stiffness(xy: ArrayLike, young: float, area: float):
    xy = array(xy, 2)
    if xy.shape != (2, 2):
        raise ValueError("A 2D truss needs two 2D nodes")
    delta = xy[1] - xy[0]
    length = float(np.linalg.norm(delta))
    positive(young=young, area=area, length=length)
    direction = delta / length
    b = np.r_[-direction, direction]
    return young * area / length * np.outer(b, b)


def beam_stiffness(young: float, inertia: float, length: float):
    """Local [w1, theta1, w2, theta2]; theta = dw/dx, small bending."""
    positive(young=young, inertia=inertia, length=length)
    l = length
    return young * inertia / l**3 * np.array([
        [12, 6*l, -12, 6*l], [6*l, 4*l*l, -6*l, 2*l*l],
        [-12, -6*l, 12, -6*l], [6*l, 2*l*l, -6*l, 4*l*l]])


def beam_uniform_load(load: float, length: float):
    positive(length=length)
    if not np.isfinite(load):
        raise ValueError("Load must be finite")
    return load * np.array([length/2, length**2/12, length/2, -length**2/12])


def elastic_matrix(young: float, poisson: float, plane: str = "stress"):
    positive(young=young)
    if not np.isfinite(poisson) or not -1 < poisson < 0.5:
        raise ValueError("Require -1 < Poisson ratio < 0.5")
    if plane == "stress":
        return young / (1-poisson**2) * np.array([
            [1, poisson, 0], [poisson, 1, 0], [0, 0, (1-poisson)/2]])
    if plane == "strain":
        return young / ((1+poisson)*(1-2*poisson)) * np.array([
            [1-poisson, poisson, 0], [poisson, 1-poisson, 0], [0, 0, (1-2*poisson)/2]])
    raise ValueError("plane must be 'stress' or 'strain'")


def triangle_stiffness(xy: ArrayLike, young: float, poisson: float,
                       thickness: float = 1., plane: str = "stress"):
    """Return (K, B, area); engineering shear strain convention."""
    xy = array(xy, 2)
    positive(thickness=thickness)
    if xy.shape != (3, 2):
        raise ValueError("A triangle needs three 2D nodes")
    p = np.column_stack((np.ones(3), xy))
    signed = float(np.linalg.det(p))
    edge_scale = np.max(np.linalg.norm(xy[:, None] - xy[None, :], axis=2))
    if abs(signed) <= 1e-12 * edge_scale**2:
        raise ValueError("Degenerate triangle")
    derivatives = np.linalg.inv(p)[1:]
    b = np.zeros((3, 6))
    b[0, 0::2], b[1, 1::2] = derivatives[0], derivatives[1]
    b[2, 0::2], b[2, 1::2] = derivatives[1], derivatives[0]
    area = abs(signed) / 2
    return thickness * area * b.T @ elastic_matrix(young, poisson, plane) @ b, b, area


def assemble_truss(nodes: ArrayLike, edges: ArrayLike, young: float, areas: ArrayLike):
    nodes, areas = array(nodes, 2), array(areas, 1)
    edges = np.asarray(edges)
    if (nodes.shape[1] != 2 or edges.shape != (len(areas), 2)
            or not np.issubdtype(edges.dtype, np.integer)
            or np.any(edges < 0) or np.any(edges >= len(nodes))):
        raise ValueError("Invalid truss connectivity")
    k = np.zeros((2*len(nodes), 2*len(nodes)))
    elements = []
    for edge, area in zip(edges, areas):
        dofs = (2*edge[:, None] + np.arange(2)).ravel()
        ke = truss_stiffness(nodes[edge], young, float(area))
        add_element(k, dofs, ke)
        elements.append((dofs, ke))
    return k, elements
