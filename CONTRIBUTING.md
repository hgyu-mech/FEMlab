# Contributing

Open a focused issue describing the physical problem, formulation, assumptions and
expected result. Small, reviewable changes with meaningful evidence are preferable
to many empty modules or large unsupported performance claims.

1. Use a permitted synthetic example and cite the formulation.
2. Test analytical behavior or an independent converged reference, invariants,
   units, limits and deliberate failure cases. Check derivatives numerically.
3. Run `python -m pytest -q` and `python -m femlab.benchmarks`.
   For graph changes also install `.[dev,ml]` and run `examples/train_gnn.py`.
4. Describe numerical differences and limitations in the pull request. Separate
   model-training performance from physical rollout and end-to-end performance.
5. Update capability status and documentation only after implementation and tests.

Do not submit private lab reports, proprietary code, licensed commercial outputs,
personal data or secrets. Confirm ownership and license before contributing.
Disclose material AI assistance and review the result. The maintainer reviews
contributions; CI passing is necessary but not sufficient scientific validation.
