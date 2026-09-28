# Provenance and publication boundaries

This foundation is newly written, AI-assisted reference code. It is not a port of
a private laboratory codebase, a commercial solver, a thesis implementation or a
colleague's program. The maintainer must review and understand contributions before
relying on them. There is no university/laboratory endorsement implied by the name.

High-level study topics informed the scope: FEM assembly and virtual work, beam
verification, particle-grid transfer, ML surrogates and design optimization. No
private slides, reports, recordings, thesis pages, industrial models, unpublished
numerical results or personal details are included. Public formulas and sources
are identified in REFERENCES.md; source code has not been copied from them.

Do not claim that all previous personal code has been imported. In particular,
this bootstrap does not transplant a prior MATLAB beam-analysis source file.
The beam code and synthetic examples here are independent new implementations.
A statement that a method was studied is not evidence that it has been implemented.

## Licensing

The MIT license applies to this repository's original contributed code. It does not
relicense dependencies, vendor software, external papers, private research data or
future contributions owned by someone else. Preserve third-party notices if such
material is later added under compatible permission. NumPy/SciPy/PyTorch are external
dependencies, not bundled copies.

## Public-data policy

Use synthetic fixtures by default. Before any other data is uploaded, establish
ownership, permission, redistributable license, sensitive fields and a documented
provenance record. Export from a commercial solver only where the relevant license
and project permissions permit it. Keep licensing/runtime access local.

Do not upload secrets, API keys, student identifiers, lab reports, proprietary CAD,
commercial result databases or research checkpoints without explicit clearance.
`.gitignore` is only a convenience, not a security review or removal from history.

## Honest status and history

Record real commits and tests. Do not backdate development, invent contributors,
download counts, citations, usage or benchmark outcomes. API contracts and roadmaps
must remain labeled as such. The bootstrap is not proof of established OSS adoption
or eligibility for a maintainer-support program.
