import numpy as np
import pytest
from femlab.core import solve_static, add_element
from femlab.fem import bar_stiffness, truss_stiffness, beam_stiffness, beam_uniform_load, triangle_stiffness, elastic_matrix
from femlab.dynamics import newmark
from femlab.multiphysics import thermal_bar
from femlab.extensions import QuadratureRule


def test_bar_solution_reaction_energy():
    k = bar_stiffness(200e9, .001, 2)
    r = solve_static(k, [0, 1000], {0: 0})
    assert r.displacement[1] == pytest.approx(1e-5)
    assert r.reaction[0] == pytest.approx(-1000)
    assert r.strain_energy == pytest.approx(.005)
    assert r.free_residual_norm < 1e-10


def test_nonzero_constraint():
    r = solve_static(bar_stiffness(2, 3, 1), [0, 12], {0: 2})
    np.testing.assert_allclose(r.displacement, [2, 4])


def test_singular_not_silently_fixed():
    with pytest.raises(ValueError, match="singular"):
        solve_static(bar_stiffness(2, 3, 1), [0, 1], {})


@pytest.mark.parametrize("bad", [-1, 0, np.nan, np.inf])
def test_bad_material(bad):
    with pytest.raises(ValueError): bar_stiffness(bad, 1, 1)


def test_assembly_and_constraint_validation():
    k = np.zeros((3, 3))
    add_element(k, [0, 1], bar_stiffness(1, 1, 1))
    add_element(k, [1, 2], bar_stiffness(1, 1, 1))
    np.testing.assert_allclose(solve_static(k, [0, 0, 1], {0: 0}).displacement, [0, 1, 2])
    with pytest.raises(ValueError): add_element(k, [0, 0], np.eye(2))
    with pytest.raises(ValueError): solve_static(k, [0, 0, 1], {3: 0})


def test_truss_rigid_motion():
    k = truss_stiffness([[0, 0], [2, 3]], 20, 2)
    np.testing.assert_allclose(k@np.array([1, 2, 1, 2]), 0, atol=1e-13)
    np.testing.assert_allclose(k@np.array([0, 0, -3, 2]), 0, atol=1e-13)


@pytest.mark.parametrize("elements", [1, 2, 5])
def test_beam_cantilever(elements):
    l, e, inertia, force = 2., 200e9, 1e-6, 100.
    k = np.zeros((2*(elements+1),)*2); f = np.zeros(len(k)); f[-2] = force
    for i in range(elements):
        add_element(k, np.arange(2*i, 2*i+4), beam_stiffness(e, inertia, l/elements))
    r = solve_static(k, f, {0: 0, 1: 0})
    assert r.displacement[-2] == pytest.approx(force*l**3/(3*e*inertia), rel=1e-10)
    assert r.reaction[1] == pytest.approx(-force*l)


def test_beam_distributed_load():
    l, q = 2., 3.
    r = solve_static(beam_stiffness(5, 7, l), beam_uniform_load(q, l), {0: 0, 1: 0})
    assert r.displacement[2] == pytest.approx(q*l**4/(8*5*7))


@pytest.mark.parametrize("plane", ["stress", "strain"])
def test_triangle_affine_patch_and_rigid(plane):
    xy = np.array([[0., 0.], [2, 0], [.2, 1]])
    k, b, area = triangle_stiffness(xy, 1000, .25, plane=plane)
    u = np.column_stack((.01*xy[:, 0]+.03*xy[:, 1]+.7,
                         -.02*xy[:, 0]+.04*xy[:, 1]-.9)).ravel()
    strain = np.array([.01, .04, .01])
    np.testing.assert_allclose(b@u, strain, atol=1e-15)
    assert .5*u@k@u == pytest.approx(.5*area*strain@elastic_matrix(1000, .25, plane)@strain)
    rotation = np.column_stack((-xy[:, 1], xy[:, 0])).ravel()
    np.testing.assert_allclose(k@rotation, 0, atol=1e-12)


def test_triangle_multi_element_patch():
    xy = np.array([[0., 0.], [1, 0], [1, 1], [0, 1], [.5, .5]])
    tris = [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]
    k = np.zeros((10, 10))
    exact = np.column_stack((.01*xy[:, 0]+.02*xy[:, 1], -.03*xy[:, 0]+.04*xy[:, 1])).ravel()
    for tri in tris:
        dofs = (2*np.array(tri)[:, None]+[0, 1]).ravel()
        add_element(k, dofs, triangle_stiffness(xy[tri], 1000, .2)[0])
    r = solve_static(k, np.zeros(10), dict(enumerate(exact[:8])))
    np.testing.assert_allclose(r.displacement, exact, atol=1e-14)


def test_triangle_degenerate():
    with pytest.raises(ValueError): triangle_stiffness([[0, 0], [1, 0], [2, 0]], 1, .2)


def test_newmark_harmonic_and_energy():
    dt = .01; time = np.arange(501)*dt
    u, v, a = newmark([[1]], [[0]], [[4]], np.zeros((len(time), 1)), dt, [1], [0])
    np.testing.assert_allclose(u[:, 0], np.cos(2*time), atol=3.5e-4)
    np.testing.assert_allclose(.5*v[:, 0]**2+2*u[:, 0]**2, 2, atol=1e-11)
    np.testing.assert_allclose(a[:, 0], -4*u[:, 0], atol=1e-12)


@pytest.mark.parametrize("fixed", [False, True])
def test_thermal_expansion(fixed):
    bc = {0: 0, 4: 0} if fixed else {0: 0}
    r = thermal_bar(np.linspace(0, 2, 5), 10, .01, {0: 40, 4: 40}, 200e9, 1e-5, 20, bc)
    assert r["displacement"][-1] == pytest.approx(0 if fixed else .0004)
    np.testing.assert_allclose(r["stress"], -40e6 if fixed else 0, atol=1e-7)
    if not fixed: assert r["elastic_energy"] < 1e-20


def test_thermal_linear_profile():
    r = thermal_bar(np.linspace(0, 2, 5), 10, .01, {0: 20, 4: 60}, 200e9, 1e-5, 20, {0: 0})
    np.testing.assert_allclose(r["temperature"], [20, 30, 40, 50, 60])
    assert r["displacement"][-1] == pytest.approx(.0004)


def test_quadrature_contract():
    assert QuadratureRule.gauss_legendre(3).validate_moments(5) < 1e-13
    with pytest.raises(ValueError): QuadratureRule(np.array([0.]), np.array([1.])).validate_moments(2)
