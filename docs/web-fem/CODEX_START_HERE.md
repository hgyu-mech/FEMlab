# Codex starts here: public Web FEM research handoff

**Updated:** 2026-10-20 (KST). **Status:** research, actual reference-solver experiments and proposed architecture. **Not:** four WebFE solvers implemented.

## Check out the research branch

This material is on the **Draft PR #4 branch**, not yet merged into \`main\`.

\`\`\`bash
git fetch origin docs/web-fem-plan-20261020
git switch --track origin/docs/web-fem-plan-20261020
# If an identically named local branch exists, use: git switch docs/web-fem-plan-20261020
\`\`\`

PR: https://github.com/hgyu-mech/FEMlab/pull/4

## Required reading order

1. Repository-level \`AGENTS.md\`, \`README.md\`, \`docs/ARCHITECTURE.md\` and \`docs/VALIDATION.md\`. Preserve the existing independent experimental FEMlab project.
2. \`docs/web-fem/README.md\`, \`CODEX_HANDOFF.md\`, \`REFERENCE_AUDIT.md\`, \`FREECAD_CONTACT_SOURCE_TRACE.md\`.
3. \`DISTRIBUTION_AUDIT_20261020_KO.md\`, \`RUNTIME_RESULTS_20261020.md\` and \`LOCAL_EVIDENCE_AND_LIMITS.md\`.
4. \`ASSET_DESIGN_HANDOFF.md\` and \`research/freecad/IMAGE_MANIFEST.csv\`.
5. \`research/freecad/README.md\` and \`research/freecad/scripts/\` for reproducible analysis methods.

## Important historical results, not newly implemented capabilities

- A separate Windows FreeCAD 1.1.4 + CalculiX executable was **actually used** to run a fresh small linear cantilever, a 3D solid-solid contact case, and controlled linear/material-only/geometry-only plate cases. Read \`RUNTIME_RESULTS_20261020.md\` for numerical observations, scope and caveats.
- A source- and binary-guided study traced FreeCAD GUI/Qt resources, document serialization, CalculiX writer, selected function calls and error handling. Full FreeCAD decompilation is **not** complete.
- 3,472 image file instances (2,961 SHA-256-distinct bytes) were catalogued from the publicly distributed program, including embedded resources. The GitHub commit contains the **filename/hash catalogue**, not FreeCAD/Qt icons themselves.
- **No independently generated replacement icon set has been produced.** Do not claim 1-to-1 replacements exist or distribute original icons as newly authored.

## First implementation request for Codex

1. Inspect current repository, tests and \`web/\` before changing architecture; run baseline checks and report real outcomes. Do not overwrite the existing Python numerical modules.
2. Propose one independently implemented \`case\` / \`mesh\` / \`result\` schema with stable entity IDs, units, result-mesh mapping, solver provenance and stale-result states.
3. Make a **small, real end-to-end example**: synthetic bar → validation → actual linear solver → numeric result → viewer → save/reopen → numerical checks. Keep unsupported capabilities explicitly disabled.
4. Then design external CalculiX runner as a separate adapter, with command-argument safety, uniquely isolated run directories, exit/solver-convergence/result-import separation, logs and hash freshness checks.
5. Implement **restricted** material, geometric and contact cases one at a time with their own acceptance gates. A UI dropdown or result screenshot is not a numerical implementation.
6. Build distinct WebFEA UI components and an **original** icon set from documented semantics. Prefer testable SVG paths/components; do not simply recolor FreeCAD/Qt licensed resources.

## Reporting protocol

\`observed\`, \`verified_by_test\`, \`source_inspected\`, \`inference\`, \`planned\`, and \`not_run\` are different statements. Report actual commands, versions, test results, errors and output paths. Do not infer correctness from solver exit code, a colorful contour or a saved \`.FCStd\`. Keep realistic numerical tolerances and failure scenarios.

Never upload private meeting audio/transcripts, internal lab PPTs, unpublished algorithms, personal information, API keys or proprietary models. Do not add KoFEM's AGPL source/WASM to this MIT repository without a deliberate license/integration decision. Do not run paid services, external deployment or automatic package publishing.

**Codex cloud does not automatically see local D: drive evidence.** The public repository exposes the analysis summaries, derived statistics, scripts and asset names/hashes. The original executable archives, binary disassembly output, screenshots and large model files remain local unless individually and deliberately supplied in an authorized workspace.
