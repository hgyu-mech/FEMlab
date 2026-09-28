# Architecture: ML-assisted computational mechanics

## 1. Design contract

Keep discretization, material response, time integration, learning and optimization
separate. Every executable feature must state its assumptions, units, validation
case and unsupported regime. A proposed module is not a delivered capability.

The current package is deliberately small and dense. Its readable kernels are the
reference against which future sparse, differentiable or GPU implementations must
be checked. A fast backend must not silently change the physical problem.

## 2. Existing modules and data

| Module | Inputs | Outputs and checks |
| --- | --- | --- |
| `core` | Element matrices/DOFs, global K/f, prescribed displacements | Displacements, reactions, elastic strain energy and free residual; rejects insufficient constraints |
| `fem` | Geometry, E/A/I/thickness/Poisson ratio | Bar/truss/beam/CST element operators and consistent beam loading |
| `dynamics` | Reduced constant M/C/K, initial state, forcing, dt | Linear Newmark displacement/velocity/acceleration history |
| `mpm` | Particle x/v/m/V0/F/C, grid spacing, transfer, material | New state without modifying the input; mass, momentum, energies and minimum J |
| `meshfree` | Point cloud, query/support or 1D source/BCs | MLS shape values or RBF-FD solution; singular support fails explicitly |
| `ml` | Training arrays and whole-case group IDs | Standardized surrogate, held-out split, domain checks and fallback decision |
| `gnn` | Node/edge features, directed edge indices, optional DOF mask | Predicted nodal values; autograd training supported |
| `optimization` | Truss nodes/members, load/support, density variables | Compliance, analytic density gradients and volume-constrained design |
| `multiphysics` | 1D mesh, thermal/mechanical data, temperatures/supports | Temperature, displacement, thermal stress, reaction and elastic energy |
| `adapters` | Nodal fields and explicit case metadata | Aligned comparisons only for matching units/mesh/load/BC/material |
| `extensions` | Protocol-defined transfer, contact, coupling, nonlocal laws | Contracts only; quadrature moment audit is executable |

Conventions: lengths and forces use a self-consistent unit system; no automatic
unit conversion. FEM uses small strain and engineering shear. MPM uses a 3D
compressible neo-Hookean law reduced to plane strain with unit out-of-plane
thickness. Its positive `det(F)` gate is necessary but not sufficient for accuracy.
Particle velocity, affine velocity and deformation gradient are distinct fields.

## 3. Two learning paths

### A. Assist the numerical algorithm

A physical solver produces local, nondimensional descriptors. A policy proposes a
transfer setting, quadrature rule, solver initialization or time-step factor. The
solver validates it before use and retains a deterministic fallback.

Current demonstration: `bounded_transfer_prediction` proposes one **global scalar**
PIC/FLIP blend. It is not integrated into an adaptive MPM rollout, and it does not
reproduce a particle-wise, two-parameter research formulation. Independently
learned particle coefficients can alter global momentum, even when each is in
[0,1]. Before a local policy is accepted, formulate a joint conservation constraint
or justified correction and measure its effect on energy, momentum and accuracy.

A training-box check is only a coarse support test, not calibrated uncertainty.
Bounds and a positive Jacobian alone do not prove nonlinear stability. Planned
policy rejection criteria include full-step finite-state checks, physical work
accounting, deformation validity and comparison against a reference rollout.

### B. Assist design exploration

Generate permitted synthetic FEA/MPM cases, separate whole geometries/trajectories
before fitting preprocessing, train a surrogate, search designs, and re-evaluate
every selected design with the physical solver. Add failed or uncertain cases to
an active-learning queue. Never report a surrogate optimum as a verified physical
optimum without that final solve.

Current GNN demo predicts a fixed spring chain's displacement for held-out load
amplitudes. It actually trains weights but is not a generalization demonstration
across materials, meshes or trajectories. The current static guard performs the
full solve to establish its reference: it is a verification scaffold, not an
acceleration result.

## 4. Planned state and dataset contract

Future datasets should contain `case_id`, `trajectory_id`, geometry family,
material family, SI/unit convention, reference configuration, connectivity or
particle neighborhood, time step, boundary conditions, external work, solver
version, commit and random seed. Store mesh/particle resolution explicitly.

Nodes/particles in one trajectory must not be randomly divided between train and
test. At least three evaluations are needed: held-out cases within the training
regime, held-out mesh/particle resolution, and held-out geometry/material regimes.
For time-dependent tasks, measure the entire rollout, not just one-step MSE.

Features should be dimensionless or normalized with training-only statistics.
Mechanical BC masks and forces are inputs, not values secretly copied from target
solutions. Document whether a graph is directed and whether its aggregation and
representation satisfy permutation, rotation or conservation requirements.

## 5. Discretization families are different

FEM shares nodal DOFs through elements. MPM transports state with particles while
using a background grid. MLS is an approximation construction used by multiple
methods; MLS shape values alone do not implement MLS-MPM. RBF-FD builds local
strong-form differential operators. EFG needs weak-form integration and treatment
of essential boundary conditions. SPH needs its own kernels, consistency and
boundary treatment. Peridynamics introduces a nonlocal material model and a
horizon; it is not merely a different mesh layout.

These families share state, material and benchmark conventions, not a misleading
single function that pretends to solve all regimes.

## 6. Coupling and acceleration boundaries

Future FEM-MPM and fluid-solid coupling must exchange work-conjugate traction and
velocity or displacement, handle incompatible discretizations, and check interface
power balance. Sticky grid walls are not a substitute for frictional contact.

Future backends may use SciPy sparse matrices, PyTorch/JAX differentiation or GPU
particle kernels. Every backend needs numerical equivalence and scaling tests.
Automatic differentiation does not by itself make a constitutive law objective,
a contact algorithm differentiable everywhere or an optimizer globally correct.

See ROADMAP.md for acceptance gates and REFERENCES.md for public literature.
