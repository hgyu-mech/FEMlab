# FreeCAD / CalculiX execution evidence (2026-10-20)

## Scope and provenance

The numbers below are **read back from local experiment artifacts**, not newly computed by this GitHub commit. Actual Windows FreeCAD 1.1.4 / CalculiX runs and separate readback verification occurred in the earlier session. They demonstrate the reference application's working path, **not** an implemented WebFE solver and **not** independently established numerical accuracy. Sources remain in local `D:\RDC_Workspace\output\FreeCAD_1.1.4_workflow_20261020`.

Do not confuse the earlier **offline distribution audit** (which did not run FreeCAD/CalculiX) with the later **runtime workflow** (which did).

## Run02: linear cantilever and solid-solid contact

| Indicator | Linear cantilever | Solid-solid contact |
| --- | ---: | ---: |
| Input nodes | 228 | 2,983 |
| Input tet10 volume elements | 79 | 1,316 |
| CalculiX process return code | 0 | 0 |
| Final step time from STA / log | 1.0 | 1.0 |
| Successful increments | 1 | 8 |
| Unsuccessful attempts | 0 | 6 |
| Imported result sets | 1 | 8 |
| Max imported displacement magnitude | 87.306454114 mm | 46.284686642 mm |

The generated `.inp`, `.frd`, `.dat`, `.sta`, logs and result-containing `.FCStd` files were compared. The contact run **needed six unsuccessful attempts/cutback retries** before finishing eight accepted increments; it must not be described as a trivial one-step convergence. Independent readback cross-checked the FRD and imported result magnitudes. This proves data-path consistency, not reference accuracy or general contact robustness.

Local evidence: `run02/runtime_verification.json`, per-case `case_evidence.json`, `Mesh.inp`, `Mesh.frd`, `Mesh.sta`, `ccx_stdout.log`.

## Run03/attempt02: one model, switch exactly one analysis capability

Synthetic plate-with-hole model noted in the local verification record: 400 × 200 × 10 mm, hole diameter 100 mm, tensile pressure 130 MPa. Shared mesh: 13,234 nodes and 6,524 tet10 elements. Controlled-model audit reports same B-Rep, mesh and mechanical setup, with the indicated feature switches.

| Case | `*PLASTIC` | `NLGEOM` | Max displacement magnitude (mm) | Max von Mises (MPa) | Max imported PEEQ |
| --- | :---: | :---: | ---: | ---: | ---: |
| Linear baseline | No | No | 0.353139972949 | 570.762675780 | 0 |
| Material only | Yes | No | 1.362247402034 | 295.413086244 | 0.057173 |
| Geometry only | No | Yes | 0.352379824878 | 571.353318673 | 0 |

All three local jobs reported process return code 0, `Job finished`, final STA time 1.0 and saved result files. The material-only case's max displacement is approximately **3.858 times** its linear baseline; the geometric-only difference is approximately **−0.215%**. **This is not** evidence of general large-deformation correctness.

### Important anomalies; do not conceal

- Material-only *raw FRD* plastic-strain field had **386 negative nodal values**, minimum **−0.00119152**. The same appears after CSV import. Root cause was not independently established, so do not claim all nodal PEEQ values are physically admissible; check nodal extrapolation/averaging/solver semantics.
- The imported FreeCAD result `Time` property was **0.0** even though the final STA and FRD block reached **1.0**. To assess completion, inspect actual solver files, not a single UI property.
- Geometry-only vs linear response is close for this load/geometry. Do not use this as a large-rotation, buckling or full geometric-nonlinearity validation.

Local evidence: `run03/attempt02/runtime_verification.json`, generated keyword diffs and detailed `Mesh.*` records.

## Actual GUI and native analysis follow-up

A separate local Windows GUI examination opened the solved contact file in FEM workbench, examined Contact property/face selection, toggled friction and observed UI enablement. The edit was canceled without altering the source document. In a later import, the final `Mesh.frd` displacement plot showed approximately **46.28 mm**, consistent to display rounding with saved raw max **46.284686642 mm**; a *result-only* `.FCStd` was saved, closed and reopened successfully. That file does **not** contain the original full geometry/material/contact setup.

Native REA 6.4.0 + Ghidra 12.1.4 records exist locally for selected `FemGui.pyd` functions including contact panel construction. At least two internal value-flow reports are truncated; full binary reconstruction is not established.

Evidence and failure paths are stored locally, not uploaded here because they can contain licensed program assets or large binary artifacts.

## How to use these references

- They are behavioral baselines for tests and UI/data contracts, **not gold-standard physics solutions**.
- Run a newly created small analytical test before claiming accuracy; compare both force balance and displacement. For nonlinear cases compare incremental histories, convergence traces, contact gap/pressure, consistent reference definitions and stress recovery settings.
- Distinguish raw solver FRD/STA, imported result arrays, displayed legend, and visualization deformation scale.
