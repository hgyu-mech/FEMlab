from dataclasses import replace
import numpy as np
import pytest
from femlab.ml import RidgeSurrogate, group_split, guarded_static, bounded_transfer_prediction
from femlab.optimization import TrussSIMP, finite_difference_gradient, bounded_search
from femlab.adapters import CaseMetadata, write_nodal_csv, compare_nodal_csv, AbaqusAdapter, AnsysAdapter
from femlab.fem import bar_stiffness


def test_ridge_heldout_loads():
    x = np.linspace(-1, 1, 25)[:, None]; y = 3*x[:, 0]+2
    train, test = group_split(np.arange(25), seed=3)
    model = RidgeSurrogate().fit(x[train], y[train])
    np.testing.assert_allclose(model.predict(x[test]), y[test], atol=1e-8)
    assert not model.in_training_box([[2.]])[0]


def test_split_no_trajectory_leakage():
    g = np.repeat(np.arange(6), 4); a, b = group_split(g)
    assert set(g[a]).isdisjoint(g[b])
    assert sorted(np.r_[a, b]) == list(range(len(g)))
    with pytest.raises(ValueError): group_split([1, 1])


def test_surrogate_failure_and_transfer_bound():
    with pytest.raises(RuntimeError): RidgeSurrogate().predict([[1]])
    model = RidgeSurrogate().fit([[0], [1]], [.2, .8])
    values, valid = bounded_transfer_prediction(model, [[.5], [2]])
    np.testing.assert_allclose(values, [.5, .95]); assert valid.tolist() == [True, False]


def test_residual_gate_and_fallback():
    k = bar_stiffness(1, 1, 1)
    u, accepted = guarded_static(k, [0, 1], {0: 2}, [900, 3], in_domain=True)
    assert accepted; np.testing.assert_allclose(u, [2, 3])
    for pred, domain in [([0, 50], True), ([0, 3], False), ([np.nan, 3], True)]:
        u, accepted = guarded_static(k, [0, 1], {0: 2}, pred, in_domain=domain)
        assert not accepted; np.testing.assert_allclose(u, [2, 3])


def problem():
    nodes = np.array([[0., 0.], [2, 0], [.7, 1]])
    return TrussSIMP(nodes, [[0, 2], [1, 2]], 100., [.1, .1], [0, 0, 0, 0, 1, -3],
                     {0: 0, 1: 0, 2: 0, 3: 0})


def test_simp_derivative_against_finite_difference():
    p = problem(); x = np.array([.4, .7])
    numeric = finite_difference_gradient(lambda z: p.evaluate(z)[0], x)
    np.testing.assert_allclose(p.evaluate(x)[1], numeric, rtol=1e-6)


def test_simp_optimization_constraint_and_improvement():
    r = problem().optimize(.5)
    assert r.volume_fraction <= .5+1e-7
    assert r.compliance < r.initial_compliance
    assert np.all(r.x >= .01) and np.all(r.x <= 1)


def test_bounded_search_is_reproducible():
    fun = lambda x: np.sum(x*x)
    a, va = bounded_search(fun, [[-1, 1], [-1, 1]], samples=128)
    b, vb = bounded_search(fun, [[-1, 1], [-1, 1]], samples=128)
    np.testing.assert_array_equal(a, b); assert va == vb and va < .1


def test_csv_identity_alignment_and_metadata(tmp_path):
    a, b = tmp_path/"a.csv", tmp_path/"b.csv"
    meta = CaseMetadata("bar", "analytic", "1", "SI", "mesh1", "tip1N", "left-fixed", "E1A1")
    write_nodal_csv(a, [1, 2], [[0], [1]])
    write_nodal_csv(b, [2, 1], [[1], [0]])
    assert compare_nodal_csv(a, b, meta, replace(meta, solver="candidate"))["relative_l2"] == 0
    with pytest.raises(ValueError): compare_nodal_csv(a, b, meta, replace(meta, units="mm"))
    with pytest.raises(ValueError): write_nodal_csv(a, [1, 1], [[0], [1]])


def test_vendor_adapters_are_explicitly_unimplemented(tmp_path):
    for adapter in [AbaqusAdapter(), AnsysAdapter()]:
        with pytest.raises(NotImplementedError): adapter.run(tmp_path/"input", tmp_path)
