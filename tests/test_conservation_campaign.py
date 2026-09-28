from dataclasses import replace
import json
import numpy as np
import pytest
from femlab.conservation import project_momenta, momenta, work_balance_defect
from femlab.campaign import CampaignConfig, run_segment, load_checkpoint, run_lock


def test_local_bounded_alpha_does_not_conserve_momentum():
    x = [[0., 0.], [1., 0.]]; m = np.ones(2)
    residual = np.array([[1., 0.], [-1., 0.]])
    proposal = np.array([.9, 1.])[:, None]*residual
    assert (m@proposal)[0] == pytest.approx(-.1)
    r = project_momenta(x, proposal, m, [0, 0])
    assert r.linear_defect_after < 1e-14
    np.testing.assert_allclose(r.velocity[:, 0], [.95, -.95])
    assert r.kinetic_energy_change != 0


def test_linear_and_angular_projection():
    rng = np.random.default_rng(1)
    x, v, m = rng.normal(size=(9, 2)), rng.normal(size=(9, 2)), rng.uniform(.1, 2., 9)
    out = project_momenta(x, v, m, [1., -2.], 3.)
    p, angular = momenta(x, out.velocity, m)
    np.testing.assert_allclose(p, [1, -2], atol=1e-13)
    assert angular == pytest.approx(3.)
    again = project_momenta(x, out.velocity, m, [1, -2], 3.)
    np.testing.assert_allclose(out.velocity, again.velocity, atol=1e-14)
    # Any feasible perturbation is mass-orthogonal to the least-change correction.
    z = rng.normal(size=v.shape)
    feasible = project_momenta(x, z, m, [0, 0], 0.).velocity
    assert abs(np.sum(m[:, None]*(out.velocity-v)*feasible)) < 1e-12


def test_projection_translation_of_origin():
    x = np.array([[0, 0], [1, 0], [0, 1.]])
    v = np.array([[1, 2.], [3, 4], [5, 6]]); m = [1., 2, 3]
    target = np.array([.3, -.2]); shift = np.array([5., -7.])
    a = project_momenta(x, v, m, target, .4)
    b = project_momenta(x+shift, v, m, target, .4+shift[0]*target[1]-shift[1]*target[0])
    np.testing.assert_allclose(a.velocity, b.velocity, atol=1e-13)


def test_degenerate_and_invalid_projection():
    with pytest.raises(ValueError): project_momenta([[0, 0]], [[0, 0]], [1], [0, 0], 1)
    with pytest.raises(ValueError): project_momenta([[0, 0]], [[0, 0]], [-1], [0, 0])
    with pytest.raises(ValueError): project_momenta([[0, 0]], [[0, 0]], [1], [np.nan, 0])
    r = project_momenta([[2, 3]], [[0, 0]], [1], [1, 1], -1)
    np.testing.assert_allclose(r.velocity, [[1, 1]])


def test_work_corrected_defect():
    assert work_balance_defect(10, 13, external_work=5, physical_dissipation=2) == 0
    with pytest.raises(ValueError): work_balance_defect(1, 2, energy_scale=0)
    with pytest.raises(ValueError): work_balance_defect(1, 2, physical_dissipation=-1)


def config(): return CampaignConfig(target_steps=16, particles_per_axis=3, checkpoint_every=4)


def test_resume_matches_uninterrupted_exactly(tmp_path):
    c = config(); full, split = tmp_path/'full', tmp_path/'split'
    a = run_segment(c, full, chunk_steps=16)
    b = run_segment(c, split, chunk_steps=7)
    assert b['status'] == 'paused' and b['step'] == 7
    b = run_segment(c, split, chunk_steps=9)
    pa, _ = load_checkpoint(full, c); pb, _ = load_checkpoint(split, c)
    for name in ('x', 'v', 'mass', 'volume0', 'deformation', 'affine'):
        np.testing.assert_array_equal(getattr(pa, name), getattr(pb, name))
    assert a['status'] == b['status'] == 'completed'
    assert b['compute_seconds'] > 0
    assert json.loads((split/'progress.json').read_text())['step'] == 16


def test_checkpoint_config_and_source_guard(tmp_path, monkeypatch):
    c = config(); run_segment(c, tmp_path, chunk_steps=2)
    with pytest.raises(ValueError, match='config'): load_checkpoint(tmp_path, replace(c, dt=c.dt/2))
    monkeypatch.setattr('femlab.campaign.fingerprint', lambda: 'not-the-same-source')
    with pytest.raises(ValueError, match='Source'): load_checkpoint(tmp_path, c)


def test_checkpoint_corruption_detected(tmp_path):
    c = config(); run_segment(c, tmp_path, chunk_steps=1)
    # Modify state but retain the original signed content digest.
    with np.load(tmp_path/'checkpoint.npz', allow_pickle=False) as z:
        arrays = {name: z[name] for name in z.files}
    arrays['v'] = arrays['v']+1
    np.savez_compressed(tmp_path/'checkpoint.npz', **arrays)
    with pytest.raises(ValueError, match='integrity'): load_checkpoint(tmp_path, c)


def test_manual_stop_and_resume(tmp_path):
    c = config(); (tmp_path/'STOP').touch()
    r = run_segment(c, tmp_path)
    assert r['status'] == 'stopped' and r['step'] == 0
    (tmp_path/'STOP').unlink()
    assert run_segment(c, tmp_path, chunk_steps=16)['status'] == 'completed'


def test_persistent_budget_not_reset(tmp_path):
    c = replace(config(), max_compute_seconds=1e-10)
    a = run_segment(c, tmp_path); b = run_segment(c, tmp_path)
    assert a['status'] == b['status'] == 'budget_exhausted'
    assert b['step'] == 0 and b['compute_seconds'] >= a['compute_seconds']


def test_failed_state_is_not_committed(tmp_path):
    c = replace(config(), dt=1.)
    r = run_segment(c, tmp_path)
    assert r['status'] == 'failed' and r['step'] == 0 and 'Attempted step 1' in r['error']
    p, _ = load_checkpoint(tmp_path, c)
    assert np.all(np.isfinite(p.deformation))
    with pytest.raises(ValueError, match='frozen'): run_segment(c, tmp_path)


def test_writer_exclusion(tmp_path):
    with run_lock(tmp_path):
        with pytest.raises(RuntimeError, match='writer'):
            with run_lock(tmp_path): pass


@pytest.mark.parametrize('change', [dict(target_steps=0), dict(dt=0), dict(seed=-1),
                                   dict(checkpoint_every=0), dict(max_calendar_days=0)])
def test_invalid_campaign(change):
    with pytest.raises(ValueError): replace(config(), **change).validate()
