# Research roadmap and acceptance gates

All stages below except the bootstrap are **planned**, not implemented. Dates of
this document are not claims of prior development. Track real work in focused
issues and tested commits; do not manufacture activity for an application.

## M0. Experimental reference foundation: implemented

Small linear FEM, explicit 2D PIC/FLIP/APIC MPM, MLS values, 1D RBF-FD, Newmark,
thermoelastic bar, ridge and trainable GNN demonstrations, truss density-SIMP,
CSV comparison and extension contracts. See the README for exact limitations.

## M1. Verified mechanics and commercial comparison

Add sparse assembly, Q4/tetrahedral/hexahedral elements, nonlinear residual and
consistent tangent interfaces, and mesh/time convergence studies. Implement a
manufactured-solution suite and compare equivalent beam/elasticity models in a
locally licensed Abaqus or Ansys installation.

Acceptance: patch tests, rigid modes, nonzero constraints, finite-difference
constitutive tangents, mesh/time convergence and metadata-matched independent
results. Record element formulation and integration, not just mesh size.

## M2. MPM robustness and transfer research

Add genuinely distinct PIC/FLIP/APIC reference experiments, B-spline grid-crossing
checks, finite-strain benchmarks and appropriate contact. Extend to 3D only after
2D tests pass. GIMP, CPDI, MLS-MPM, implicit stepping and full-mass approaches are
separate implementations requiring their own references and tests.

Acceptance: transfer reproduction, mass and linear/angular momentum accounting,
external-work-corrected energy history, particle/grid refinement, positive J,
long rollouts, translation/rotation/deformation and impact benchmarks. A two-body
collision needs a valid contact formulation before it becomes a claimed feature.

## M3. ML-assisted transfer and GNN rollout

Generate a public synthetic dataset with descriptors and physical diagnostics.
Optimize transfer settings with an explicit conservation constraint, then train
and evaluate a model against fixed-transfer and direct-search baselines. Compare
ridge/MLP before increasing graph-model complexity. A bounded random search is
currently available; TLBO and other named metaheuristics are not implemented.

Acceptance: splits by whole trajectory, geometry and resolution; reported parameter
error AND rollout error; energy/momentum checks; fallback frequency; nonfinite-state
rate; training and inference costs. Prediction accuracy alone is not the goal.
Publish a model card before redistributing any checkpoint.

## M4. Shape, material and topology optimization

Keep three problem classes separate: shape optimization moves an existing boundary;
material optimization changes constitutive/design parameters; density topology
optimization changes a material distribution. The current fixed-graph truss SIMP
is a small density relaxation, not a continuum shape/topology package.

First shape task: parameterized beam/bracket geometry with displacement/stress and
mass constraints. First material task: synthetic constitutive parameter inference
with identifiability checks. Future continuum topology: mesh-independent filtering,
volume constraints and manufacturability. Add adjoint or differentiable sensitivities
only after finite-difference comparisons pass.

Acceptance: feasible designs verified by a physical solver, gradient checks,
mesh/filter robustness, multiple starts for nonconvex problems, and uncertainty
intervals where data support them. Compare end-to-end design time at matched error.

## M5. Meshfree, nonlocal and learned integration

Add MLS derivatives, EFG weak forms and essential BC treatment; separately consider
SPH and finite-spheres formulations. Extend RBF-FD to 2D with boundary/stencil
quality checks. Add a peridynamic state/horizon and fracture-energy contract before
claiming a fracture solver. Learn quadrature nodes/weights only with positivity,
required moments and out-of-domain handling.

Acceptance: polynomial reproduction, patch/convergence tests, boundary sensitivity,
conditioning, conservation, horizon/spacing studies and correct fracture-energy
scaling. The present quadrature audit is not a trained integration model.

## M6. Multiphysics, uncertainty and scalable backends

Progress from the current one-way thermal bar to transient thermoelasticity,
conservative FEM-MPM coupling and then fluid-structure interaction. Define contact
forces, interface work and energy exchange before combining solvers. Possible
applications include structural components, compliant robotics, material design
and independently licensed biomechanical examples.

Add reduced-order models, calibrated uncertainty and active learning as justified
by measured bottlenecks. Sparse/GPU/multi-GPU implementations need reproducibility,
hardware/precision disclosure and matched-accuracy comparisons. None are current
capabilities or guaranteed performance improvements.

## Definition of done

A module moves from planned to experimental only with executable code, a cited
formulation, assumptions, independent reference checks, meaningful failure tests
and a reproducible example. Move toward validated status only after independent
review and broader benchmark evidence. Do not rename a protocol as a solved method.
