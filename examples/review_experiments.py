"""Independent counterexamples and checkpoint replay, not thesis reproduction."""
import argparse
from datetime import datetime, timezone
import hashlib
import platform
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from femlab.conservation import project_momenta
from femlab.campaign import CampaignConfig, initial_state, run_segment, load_checkpoint, fingerprint
from femlab.mpm import MPM2D


def run():
    # Bounds do not implement a global conservation constraint.
    m = np.ones(2); x = np.array([[0., 0.], [1., 0.]])
    proposal = np.array([[.9, 0], [-1., 0]])
    projected = project_momenta(x, proposal, m, [0, 0])
    # Constant harmonic energy is not sufficient to identify the correct trajectory.
    t = np.linspace(0, 4, 101); wrong_u, wrong_v = np.cos(2*t), -np.sin(2*t)
    wrong_energy = .5*(wrong_u**2+wrong_v**2)
    c = CampaignConfig(target_steps=80, checkpoint_every=20, particles_per_axis=4)
    p, _ = initial_state(c)
    p.v = np.column_stack((.1*np.sin(60*p.x[:, 0]), .1*np.cos(60*p.x[:, 1])))
    common = dict(cells=c.cells, dx=1/c.cells, young=c.young, poisson=c.poisson)
    pic = MPM2D(**common, transfer='pic').step(p, c.dt)
    flip = MPM2D(**common, transfer='flip', flip_ratio=1.).step(p, c.dt)
    alpha = np.linspace(.9, 1., len(p.x))
    mixed = pic.v+alpha[:, None]*(flip.v-pic.v)
    corrected = project_momenta(pic.x, mixed, p.mass, p.mass@p.v)
    with TemporaryDirectory() as folder:
        a, b = Path(folder)/'full', Path(folder)/'resume'
        r1 = run_segment(c, a, chunk_steps=80)
        run_segment(c, b, chunk_steps=33)
        r2 = run_segment(c, b, chunk_steps=47)
        pa, _ = load_checkpoint(a, c); pb, _ = load_checkpoint(b, c)
        max_error = max(float(np.max(abs(getattr(pa, name)-getattr(pb, name))))
                        for name in ('x', 'v', 'deformation', 'affine'))
    return {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'environment': {'python': platform.python_version(), 'numpy': np.__version__},
        'audit_source_sha256': {name: hashlib.sha256((Path(__file__).resolve().parents[1]/name).read_bytes()).hexdigest() for name in ('femlab/conservation.py', 'examples/review_experiments.py')},
        'scope': 'Independent synthetic audits only. Not original data, trained policy or reproduction of Park (2025).',
        'source_fingerprint': fingerprint(),
        'bounded_local_alpha': {'linear_defect_before': projected.linear_defect_before,
                                'linear_defect_after': projected.linear_defect_after,
                                'kinetic_energy_change': projected.kinetic_energy_change},
        'actual_mpm_frame': {'linear_defect_before': corrected.linear_defect_before,
                             'linear_defect_after': corrected.linear_defect_after,
                             'kinetic_energy_change': corrected.kinetic_energy_change,
                             'note': 'Nonuniform coefficients prescribed for a diagnostic; not ML training.'},
        'energy_is_not_accuracy': {'energy_max_drift': float(np.max(abs(wrong_energy-.5))),
                                  'displacement_rmse': float(np.sqrt(np.mean((wrong_u-np.cos(t))**2))),
                                  'kinematic_residual_max': float(np.max(abs(-2*np.sin(2*t)-wrong_v)))},
        'checkpoint_replay': {'full_steps': r1['step'], 'resumed_steps': r2['step'],
                              'state_max_absolute_difference': max_error,
                              'status': r2['status']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='outputs/review_experiments.json')
    args = parser.parse_args(); report = run(); path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    assert report['checkpoint_replay']['state_max_absolute_difference'] == 0
    assert report['bounded_local_alpha']['linear_defect_after'] < 1e-12


if __name__ == '__main__': main()
