# Verification, validation and comparison policy

## Bootstrap evidence

The first local run used Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0 and CPU PyTorch
2.10.0. All 50 tests passed, including optional ML tests. The benchmark report has
13 passing gates and SHA-256 hashes of the source modules. These results concern
small deterministic synthetic cases only. CI has its own runtime and must be
checked separately; a local pass is not a claimed GitHub Actions pass.

`docs/verification/bootstrap.json` records numerical verification. The fixed-geometry
GNN demo's report records actual training and held-out load interpolation. Report
relative error as a property of that example, never as general accuracy of FEMlab.
No Abaqus or Ansys results were produced or fabricated.

## What is checked

- Bars and Euler-Bernoulli beams against closed forms, nonzero prescribed
  displacements, reactions, rigid modes and singular support detection.
- CST affine patch behavior, engineering shear and element/mesh checks.
- Newmark harmonic response and linear undamped energy; free/fixed thermal bars.
- MLS partition/linear reproduction and support rejection; RBF-FD exact quadratic
  behavior and sine-problem refinement.
- MPM stencil moments, force cancellation, translation, affine transfer,
  particle-grid angular momentum and material-energy derivatives. These are not
  a full nonlinear impact validation suite.
- Truss SIMP sensitivities against finite differences, a volume-constrained design,
  grouped ML splitting, fallback logic, GNN permutation behavior and training.
- Nodal CSV matching and explicit rejection of unimplemented vendor execution.

## Known limitations

Dense linear solves deliberately reject very ill-conditioned systems; scaling and
units affect conditioning. No automatic regularization hides an unconstrained model.
The MPM time-step estimate is not a nonlinear stability guarantee. Sticky walls
may introduce boundary impulses/dissipation; no blanket conservation claim applies.
The graph network is not rotation-equivariant by construction. A static residual
alone is not a displacement error bound without conditioning information.

The ML fallback implementation currently evaluates the reference solve first.
Therefore it establishes behavior, not computational savings. The truss optimizer
uses SciPy SLSQP and a nonconvex relaxation; it has no global-optimum guarantee.
The one-way thermal problem is not a coupled transient heat-mechanics solver.

## Fair commercial-solver comparisons

A benchmark must identify geometry, material law and parameters, units, supports,
loading/history, contact, element/particle resolution, integration, time step,
convergence tolerances, solver version, hardware and arithmetic precision.
Use identical physical cases, and report differences in discretization explicitly.
Vendor output is a comparison source, not automatically the exact solution.

Measure displacement/stress/force errors against analytical or converged references;
check mesh/time convergence, failure rates and work-corrected conservation. Report
wall-clock time only at comparable accuracy. Include preprocessing, ML data creation,
training, inference, rejected predictions and final verification in end-to-end cost.
Use repeated timings and disclose failed cases, not only a favorable example.

The current CSV matcher rejects unmatched meshes. Comparing different fields needs
a separately validated projection. No automatic interpolation is hidden in the
reported relative norm. At a zero reference norm, relative error is undefined.

## Before relying on a new result

Run the complete tests and benchmark script; inspect physical plausibility; confirm
units and model assumptions; compare independent references and convergence. These
checks do not qualify the software for safety-critical decisions. External users
should independently validate every intended engineering use.
