"""Reproducible reference checks; no commercial-solver performance claims."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import time
import numpy as np
import scipy
from . import __version__
from .core import solve_static
from .fem import bar_stiffness, beam_stiffness
from .meshfree import mls_shape, poisson_1d
from .mpm import MPM2D, Particles
from .ml import RidgeSurrogate, group_split
from .optimization import TrussSIMP, finite_difference_gradient
from .multiphysics import thermal_bar
from .dynamics import newmark


def run_suite():
    start = time.perf_counter(); checks = {}
    r = solve_static(bar_stiffness(200e9, .001, 2), [0, 1000], {0: 0})
    checks["bar_tip_relative_error"] = float(abs(r.displacement[1]/1e-5-1))
    r = solve_static(beam_stiffness(200e9, 1e-6, 2), [0, 0, 100, 0], {0: 0, 1: 0})
    checks["beam_tip_relative_error"] = float(abs(r.displacement[2]/(100*2**3/(3*200e9*1e-6))-1))
    nodes = np.random.default_rng(5).uniform(-1, 1, (40, 2)); point = np.array([.2, .1])
    shape = mls_shape(point, nodes, 2)
    checks["mls_linear_reproduction_error"] = float(np.linalg.norm(shape@nodes-point))
    errors = []
    for n in (21, 41):
        x = np.linspace(0, 1, n)
        u = poisson_1d(x, np.pi**2*np.sin(np.pi*x))
        errors.append(float(np.max(abs(u-np.sin(np.pi*x)))))
    checks["rbffd_sine_max_error"] = errors[-1]
    checks["rbffd_refinement_ratio"] = errors[-1]/errors[0]
    particles = Particles.create([[.42, .43], [.45, .43], [.42, .47], [.45, .47]], [.1, -.2], .001, .0001)
    mpm = MPM2D(); q = particles
    for _ in range(10): q = mpm.step(q, 1e-4)
    checks["mpm_translation_max_error"] = float(np.max(abs(q.x-particles.x-.001*particles.v)))
    checks["mpm_momentum_drift_norm"] = float(np.linalg.norm(q.mass@q.v-particles.mass@particles.v))
    p = TrussSIMP([[0, 0], [2, 0], [.7, 1]], [[0, 2], [1, 2]], 100, [.1, .1],
                  [0, 0, 0, 0, 1, -3], {0: 0, 1: 0, 2: 0, 3: 0})
    design = np.array([.4, .7]); analytical = p.evaluate(design)[1]
    numerical = finite_difference_gradient(lambda z: p.evaluate(z)[0], design)
    checks["simp_gradient_relative_error"] = float(np.linalg.norm(analytical-numerical)/np.linalg.norm(analytical))
    opt = p.optimize(.5)
    checks["simp_compliance_ratio"] = float(opt.compliance/opt.initial_compliance)
    checks["simp_volume_fraction"] = opt.volume_fraction
    forces = np.linspace(-1000, 1000, 31)[:, None]
    targets = np.array([solve_static(bar_stiffness(200e9, .001, 2), [0, f[0]], {0: 0}).displacement[1] for f in forces])
    train, test = group_split(np.arange(len(forces)), seed=7)
    model = RidgeSurrogate().fit(forces[train], targets[train])
    prediction = model.predict(forces[test])
    checks["ridge_fixed_bar_heldout_relative_l2"] = float(np.linalg.norm(prediction-targets[test])/np.linalg.norm(targets[test]))
    thermal = thermal_bar(np.linspace(0, 2, 5), 10, .01, {0: 40, 4: 40}, 200e9, 1e-5, 20, {0: 0})
    checks["thermal_free_expansion_error"] = float(abs(thermal["displacement"][-1]-.0004))
    u, v, _ = newmark([[1]], [[0]], [[4]], np.zeros((201, 1)), .01, [1], [0])
    checks["newmark_energy_drift"] = float(np.max(abs(.5*v[:, 0]**2+2*u[:, 0]**2-2)))
    limits = {"bar_tip_relative_error": 1e-10, "beam_tip_relative_error": 1e-10,
              "mls_linear_reproduction_error": 1e-10, "rbffd_sine_max_error": .01,
              "rbffd_refinement_ratio": 1., "mpm_translation_max_error": 1e-10,
              "mpm_momentum_drift_norm": 1e-10, "simp_gradient_relative_error": 1e-5,
              "simp_compliance_ratio": 1., "simp_volume_fraction": .5000001,
              "ridge_fixed_bar_heldout_relative_l2": 1e-6, "thermal_free_expansion_error": 1e-10,
              "newmark_energy_drift": 1e-9}
    passed = {name: value < limits[name] for name, value in checks.items()}
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}
    return {"schema_version": 1, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "version": __version__, "python": platform.python_version(), "platform": platform.platform(),
            "numpy": np.__version__, "scipy": scipy.__version__, "seed": 5,
            "seconds_total": time.perf_counter()-start, "source_sha256": hashes,
            "checks": checks, "upper_limits": limits, "passed": passed,
            "all_passed": all(passed.values()),
            "external_baselines": {"Abaqus": "not_run", "ANSYS": "not_run"},
            "scope": "Small synthetic verification cases only; not independent validation, production qualification or a speed comparison."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="outputs/verification.json")
    args = parser.parse_args()
    report = run_suite(); path = Path(args.output); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"all_passed": report["all_passed"], "checks": report["checks"], "output": str(path)}, indent=2))
    if not report["all_passed"]: raise SystemExit(1)


if __name__ == "__main__":
    main()
