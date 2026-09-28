# FEMlab

**Verification-first foundations for ML-assisted computational mechanics.**

FEMlab is an independent, early-stage research and learning project maintained by
`hgyu-mech`. It combines readable mechanics baselines with machine-learning,
optimization and solver-coupling interfaces. It is not an official university or
laboratory software distribution.

**Status: `0.1.0.dev1`, experimental.** There is working code, but no claim of
industrial readiness, broad adoption, or superiority to Abaqus or Ansys.
Commercial-solver comparisons have **not** been run. Development history starts
with the actual repository commits, not with the dates of literature studied.

## Run it

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m femlab.benchmarks --output outputs/verification.json
python examples/mpm_translation.py
```

Optional, real CPU GNN training on synthetic FEM data:

```bash
python -m pip install -e ".[dev,ml]"
python examples/train_gnn.py
python -m pytest -q
```

Python 3.10+ is required. The core uses NumPy and SciPy; PyTorch is optional.
Without PyTorch, GNN tests are explicitly skipped. No API key, commercial license
or paid service is needed for these examples. This project has not been published
to PyPI; install the checked-out repository, not a similarly named package.

## What actually exists

| Area | Implemented now | Important boundary |
| --- | --- | --- |
| FEM | Bar, 2D truss, Euler-Bernoulli beam, CST triangle; assembly, nonzero Dirichlet constraints, reactions | Dense, small, linear problems; not a general nonlinear FE solver |
| Dynamics | Linear Newmark average acceleration | Constant matrices, caller-eliminated constraints |
| MPM | Explicit 2D solid MPM, quadratic B-splines, PIC/FLIP/APIC, neo-Hookean material, diagnostics | Standard gradient MPM, not MLS-MPM; no proper multi-body contact or 3D |
| Meshfree | Linear-reproducing MLS values; cubic RBF-FD 1D Poisson solver | MLS values are not a complete EFG elasticity solver |
| ML | Standardized ridge regression, grouped splitting, guarded static predictions, scalar transfer proposals | Static guard currently computes a full reference solve; no speedup claim |
| GNN | Trainable message-passing network, hard prescribed-DOF mask, synthetic FEM training example | No pretrained general solver, rotation equivariance or conservation guarantee |
| Optimization | Truss density-SIMP objective and sensitivities with SciPy SLSQP; bounded random-search baseline | Fixed truss graph; not continuum topology or shape optimization |
| Multiphysics | One-way steady 1D heat conduction and thermoelastic bar | No transient 3D coupling or fluid-structure solver |
| Interoperability | Nodal CSV with metadata checks; Abaqus/Ansys adapter contracts | Vendor execution deliberately raises `NotImplementedError` |
| Extensions | Transfer/contact/coupling/nonlocal protocols; Gauss rule moment audit | Protocols are not implemented solvers |

The bootstrap was locally checked with **50 passing tests**, including the optional
GNN tests, and **13 passing numerical benchmark gates**. See the dated machine-readable
[snapshot](docs/verification/bootstrap.json), [GNN demo report](docs/verification/gnn_demo.json)
and [limitations](docs/VALIDATION.md). These are small synthetic verification cases,
not an independent review or certification. Re-run them on your own environment.

## Research direction

```text
problem + materials + boundary conditions
                  |
      FEM / MPM / meshfree reference model
                  |
    verified cases + provenance + physical diagnostics
                  |
         ML surrogate or local policy
                  |
      constraints + rejection / fallback gates
                  |
      shape / material / density optimization
                  |
        independent high-fidelity recheck
```

The priority is ML **assistance**, not replacing mechanics with an unchecked
prediction. Proposed work includes MPM transfer policies, graph-based surrogates,
shape optimization, learned quadrature, nonlocal fracture and conservative coupling.
The [architecture](docs/ARCHITECTURE.md) specifies the boundaries; the
[roadmap](docs/ROADMAP.md) distinguishes future research from working code.

## Repository map

```text
femlab/           numerical kernels, experimental ML, optimization, contracts
examples/         runnable synthetic MPM and GNN examples
tests/            analytical, invariant, gradient and failure-path checks
docs/             architecture, validation, research roadmap, provenance
.github/          CI configuration, no secrets or automatic deployment
```

Start with [the Korean guide](docs/GETTING_STARTED_KO.md) or
[contributing](CONTRIBUTING.md). Original code is MIT-licensed. Private research
reports, course recordings, commercial results, model weights and personal data
are not redistributed; see [provenance](docs/PROVENANCE.md).

## Dissertation review and checkpointed experiments (2026-09-28)

The new [critical review](docs/reviews/PARK_2025_CRITICAL_REVIEW.md) and
[Korean summary](docs/reviews/REVIEW_SUMMARY_KO.md) distinguish source evidence,
printed inconsistencies and independent extension hypotheses. No thesis PDF,
figures, private training data or edited derivative is redistributed.

New executable components: a fixed-position momentum projection, a work-balance
audit, synthetic counterexamples, and a bounded MPM checkpoint/resume runner.
This is not the thesis ML-MPM implementation or a learned alpha/beta rollout.

```bash
python examples/review_experiments.py
python -m femlab.campaign --config configs/mpm_smoke.json --run-dir outputs/demo --chunk-steps 80 --max-seconds 60
python -m femlab.campaign --config configs/mpm_smoke.json --run-dir outputs/demo --chunk-steps 120 --max-seconds 60
```

The update has 67 locally passing tests (including optional PyTorch tests).
The [independent audit snapshot](docs/experiments/review_experiments.json) includes
an 80-step interrupted/uninterrupted replay with identical final arrays in the
tested environment. This is not evidence of multi-month reliability or accuracy
on the original dissertation problems.

[Long-running compute](docs/LONG_RUNNING_COMPUTE.md) explains GitHub job limits,
manually resumed artifacts, an opt-in workstation/HPC worker, budgets and a
read-only progress dashboard. The short `research-audit` workflow creates
downloadable results. No perpetual workflow, paid server or 70/140-day run is
automatically started.
