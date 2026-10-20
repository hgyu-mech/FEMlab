# Evidence catalog, provenance and public/private boundary

Updated 2026-10-20. This project is an independent, personal study and implementation plan. It is not an official lab distribution or a report claiming the four nonlinear methods are already implemented.

## Evidence classification

| Status | Examples |
| --- | --- |
| \`public-source-inspected\` | FreeCAD 1.1.4 contact writer and GUI C++ source, KoFEM WASM/React/MFEM source and test code |
| \`uploaded-distribution-static\` | Hashes, PE imports/exports, Qt resource inventory, theme information, model serialization and stored result checks |
| \`isolated-function-test\` | Contact writer keyword toggles and CalculiX GUI completion handler with synthetic test doubles |
| \`actual-external-solver-run\` | Local new CalculiX linear/cantilever, contact, material-only and geometry-only runs |
| \`actual-GUI-observation\` | Local FreeCAD contact property panel and result display/reopen examination |
| \`numerical-validation-not-done\` | Formal benchmark error bounds, independent reference solver convergence, comprehensive nonlinear coverage |
| \`planned\` | New WebFEA app, four-method capability and 1:1 alternative image design; no completed implementation |

## Local evidence directories (available only on the connected PC)

\`\`\`text
D:\RDC_Workspace\output\
  FreeCAD_1.1.4_audit_20261020\
    REPORT_KO.md
    report.html
    analysis_bundle.zip
    scripts\
    evidence\
  FreeCAD_1.1.4_images_20261020\
    index.html
    contact_sheets\
    images\
    IMAGE_MANIFEST.csv
    IMAGE_MANIFEST.json
    FreeCAD_1.1.4_ALL_Images_3472.zip
  FreeCAD_1.1.4_workflow_20261020\
    run02\runtime_verification.json
    run03\attempt02\runtime_verification.json
    audit_followup_20261020\검증현황.txt
    rea\
\`\`\`

These local files are NOT implicitly accessible from a cloud Codex environment. To reproduce observations there, provide the authorized FreeCAD distribution in that environment and use the scripts after adapting paths. Do **not** commit local executable archives, \`.pyd\`, \`.dll\`, \`.7z\`, installer, full source-asset screenshots or example model bundles to the MIT repo.

## Omitted materials

- Meeting audio/transcripts, internal lab materials and slide templates, task/personnel information, unpublished algorithms, credentials or identifying metadata.
- Original FreeCAD and third-party image payloads (the filename/digest manifest is included).
- Binary disassembly archives, large local \`.FCStd\` solved cases, raw \`.frd\` / \`.inp\` / screenshot bundles and recreated UI resource assets.
- No new author-created icon assets existed at the time this note was written.

## What Codex can do immediately

Read the docs, image digest catalog, runtime numeric observations and research scripts on this branch; independently reproduce a limited case from authorized local assets; develop new code and original artwork with documented licenses. Keep any unit/numerical reference test explicit about observed vs computed values. Ask before using private resources.

## Reference scope

- FreeCAD public repository: https://github.com/FreeCAD/FreeCAD/tree/1.1.4
- KoFEM public repository pinned by earlier audit: https://github.com/mkofler96/KoFEM
- Existing PR: https://github.com/hgyu-mech/FEMlab/pull/4

Every cited observation in this document has a local original evidence path or a public source URL. The structured runtime values and asset filenames can be compared against the local machine's artifacts and their recorded hashes.
