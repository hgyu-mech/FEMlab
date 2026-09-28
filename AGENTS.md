# Working rules for coding agents

- Read README.md, docs/ARCHITECTURE.md and docs/VALIDATION.md first.
- Preserve public API assumptions, units and current work; never force-push or
  rewrite/backdate history. Do not invent usage or test results.
- Only use redistributable synthetic data by default. Never upload private
  attachments, internal research reports, credentials or commercial databases.
- Keep implemented, experimental, interface-only and planned capabilities distinct.
- Cite exact formulations. Do not call standard MPM MLS-MPM or call an MLS shape
  function a complete meshfree solid solver.
- GNN regression error is not physical validation. Require grouped splits and
  rollout/conservation checks for new time-dependent models.
- Check analytical cases, finite differences, invariants and failure paths.
- Run: python -m pytest -q; python -m femlab.benchmarks.
- For ML changes also run: python examples/train_gnn.py (install .[dev,ml]).
- Do not claim GitHub CI passed unless its actual run completed successfully.
- Do not publish packages, paid jobs or commercial solver runs without authorization.
- Document remaining limitations rather than replacing errors with fake outputs.
