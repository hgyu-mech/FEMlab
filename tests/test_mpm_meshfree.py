import numpy as np
import pytest
from femlab.mpm import MPM2D, Particles, stencil2d, neo_hookean
from femlab.meshfree import mls_shape, poisson_1d


def particles():
    x = np.array([[.42, .43], [.45, .43], [.42, .47], [.45, .47]])
    return Particles.create(x, [.1, -.2], .001, .0001)


@pytest.mark.parametrize("x", [[.4, .5], [.401, .521], [.25, .25]])
def test_kernel_moments_and_gradients(x):
    terms = list(stencil2d(x, .1, 10))
    assert sum(w for _, w, _, _ in terms) == pytest.approx(1)
    np.testing.assert_allclose(sum(w*d for _, w, _, d in terms), 0, atol=1e-16)
    np.testing.assert_allclose(sum(g for _, _, g, _ in terms), 0, atol=1e-14)
    np.testing.assert_allclose(sum(np.outer(d, g) for _, _, g, d in terms), np.eye(2), atol=1e-14)
    np.testing.assert_allclose(sum(w*np.outer(d, d) for _, w, _, d in terms), .1**2/4*np.eye(2), atol=1e-16)


@pytest.mark.parametrize("transfer", ["pic", "flip", "apic"])
def test_translation_and_mass_momentum(transfer):
    solver = MPM2D(transfer=transfer); p = particles()
    mass, momentum, force = solver.p2g(p)
    assert mass.sum() == pytest.approx(p.mass.sum())
    np.testing.assert_allclose(momentum.sum(axis=(0, 1)), p.mass@p.v, atol=1e-17)
    np.testing.assert_allclose(force, 0, atol=1e-12)
    q = p
    for _ in range(5): q = solver.step(q, 1e-4)
    np.testing.assert_allclose(q.x, p.x+5e-4*p.v, atol=1e-15)
    np.testing.assert_allclose(q.v, p.v, atol=1e-14)
    np.testing.assert_allclose(q.deformation, p.deformation, atol=1e-13)


def test_apic_affine_reproduction():
    solver = MPM2D(); p = particles()
    c = np.array([[.2, -.3], [.3, -.1]])
    p.v = p.x@c.T + [.1, .2]; p.affine[:] = c
    q = solver.step(p, 1e-5)
    np.testing.assert_allclose(q.v, p.v, atol=1e-14)
    np.testing.assert_allclose(q.affine, p.affine, atol=1e-13)
    np.testing.assert_allclose(q.deformation, np.tile(np.eye(2)+1e-5*c, (4, 1, 1)), atol=1e-14)


def test_apic_p2g_angular_momentum():
    solver = MPM2D(); p = particles()
    p.affine[:] = [[0., -2.], [2., 0.]]
    mass, momentum, _ = solver.p2g(p)
    i, j = np.indices(mass.shape)
    angular_grid = np.sum(i*solver.dx*momentum[..., 1]-j*solver.dx*momentum[..., 0])
    angular_particles = np.sum(p.mass*(p.x[:, 0]*p.v[:, 1]-p.x[:, 1]*p.v[:, 0]
                            +solver.dx**2/4*(p.affine[:, 1, 0]-p.affine[:, 0, 1])))
    assert angular_grid == pytest.approx(angular_particles, abs=1e-17)


def test_gravity_linear_momentum():
    s = MPM2D(gravity=[0, -9.81]); p = particles(); dt = 1e-4
    q = s.step(p, dt)
    np.testing.assert_allclose(p.mass@q.v, p.mass@p.v+dt*p.mass.sum()*s.gravity, atol=1e-17)


def test_internal_force_balance_deformed():
    s = MPM2D(); p = particles(); p.deformation[:] = [[1.05, .03], [0, .95]]
    _, _, f = s.p2g(p)
    np.testing.assert_allclose(f.sum(axis=(0, 1)), 0, atol=1e-13)
    q = s.step(p, 1e-5)
    assert s.diagnostics(q)["minimum_J"] > 0


def test_mpm_invalid_states():
    with pytest.raises(ValueError): list(stencil2d([0, .5], .1, 10))
    with pytest.raises(ValueError): neo_hookean([[-1, 0], [0, 1]], 10, .2)
    with pytest.raises(ValueError): MPM2D().step(particles(), 1.)
    with pytest.raises(ValueError): MPM2D(transfer="magic")
    with pytest.raises(ValueError): Particles.create([[.5, .5]], [0, 0], 0, 1)


def test_neo_hookean_rigid_rotation_and_energy_derivative():
    angle = .4
    r = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    sigma, w = neo_hookean(r, 100, .2)
    np.testing.assert_allclose(sigma, 0, atol=1e-13); assert abs(w) < 1e-13
    f = np.array([[1.1, .1], [.02, .9]]); sigma, _ = neo_hookean(f, 100, .2)
    pk1 = np.linalg.det(f)*sigma@np.linalg.inv(f).T
    numeric = np.zeros((2, 2))
    for i in range(2):
        for j in range(2):
            delta = np.zeros((2, 2)); delta[i, j] = 1e-6
            numeric[i, j] = (neo_hookean(f+delta, 100, .2)[1]-neo_hookean(f-delta, 100, .2)[1])/2e-6
    np.testing.assert_allclose(pk1, numeric, rtol=1e-7, atol=1e-7)


def test_mls_affine_reproduction():
    nodes = np.random.default_rng(1).uniform(-1, 1, (30, 2)); x = [.1, .2]
    weights = mls_shape(x, nodes, 2)
    assert weights.sum() == pytest.approx(1)
    np.testing.assert_allclose(weights@nodes, x, atol=1e-14)
    assert weights@(2+3*nodes[:, 0]-4*nodes[:, 1]) == pytest.approx(1.5)


def test_mls_bad_support():
    with pytest.raises(ValueError): mls_shape([0, 0], [[0, 0], [1, 0]], 2)


def test_rbffd_quadratic_scattered():
    x = np.r_[0., np.sort(np.random.default_rng(3).uniform(.01, .99, 24)), 1.]
    u = poisson_1d(x, np.full(len(x), 2.))
    np.testing.assert_allclose(u, x*(1-x), atol=2e-12)


def test_rbffd_sine_refinement():
    errors = []
    for n in (21, 41):
        x = np.linspace(0, 1, n)
        u = poisson_1d(x, np.pi**2*np.sin(np.pi*x))
        errors.append(np.max(abs(u-np.sin(np.pi*x))))
    assert errors[1] < errors[0] and errors[1] < .01
