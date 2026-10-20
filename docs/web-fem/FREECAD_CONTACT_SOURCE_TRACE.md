# FreeCAD 1.1.4: FEM Contact Source Trace (Public-Source Audit)

> Status (2026-10-20): **Source inspection completed for this narrow path. REA binary inspection NOT run.** This is an independent study of publicly available FreeCAD 1.1.4 source. No internal lab materials or copied vendor implementations are stored here. File paths/claims below refer to release tag `1.1.4`, not unverified local installation files.

## Question
When a user edits a master/slave contact condition in FreeCAD's FEM workbench, how does the GUI selection eventually become a solver input and a result?

## Source-verified call/data path

| Stage | Version-pinned upstream source | Observed implementation |
|---|---|---|
| Qt task UI | [TaskFemConstraintContact.ui](https://github.com/FreeCAD/FreeCAD/blob/1.1.4/src/Mod/Fem/Gui/TaskFemConstraintContact.ui) | Defines master/slave face selection widgets and contact settings controls. |
| Qt button handler | [TaskFemConstraintContact.cpp](https://github.com/FreeCAD/FreeCAD/blob/1.1.4/src/Mod/Fem/Gui/TaskFemConstraintContact.cpp) | `btnAddMaster` connects to `addToSelectionMaster`; this handler obtains `Gui::Selection().getSelectionEx()`, validates selected geometry, then calls `pcConstraint->References.setValues(Objects, SubElements)`. There is a similar slave-face path. |
| Document properties | [FemConstraintContact.cpp](https://github.com/FreeCAD/FreeCAD/blob/1.1.4/src/Mod/Fem/App/FemConstraintContact.cpp) | `ConstraintContact` declares properties including `Slope`, `Adjust`, `Friction`, `FrictionCoefficient`, `StickSlope`, and `SurfaceBehavior`. Behavior names: `Hard`, `Linear`, `Tied`. |
| CalculiX writer | [write_constraint_contact.py](https://github.com/FreeCAD/FreeCAD/blob/1.1.4/src/Mod/Fem/femsolver/calculix/write_constraint_contact.py) | Writes solver-facing master/slave `*SURFACE` definitions, `*CONTACT PAIR`, `*SURFACE INTERACTION`, conditional `*SURFACE BEHAVIOR`, and optional `*FRICTION`. Actual mesh-to-surface mapping is upstream from the writer; not yet traced fully here. |
| Solver job lifecycle | [tasks.py](https://github.com/FreeCAD/FreeCAD/blob/1.1.4/src/Mod/Fem/femsolver/calculix/tasks.py) | Checks model, constructs/writes solver input, launches a separate CalculiX binary through `subprocess.Popen`, then imports `.frd` and `.dat` output. |
| Qt binary build target | [Gui/CMakeLists.txt](https://github.com/FreeCAD/FreeCAD/blob/1.1.4/src/Mod/Fem/Gui/CMakeLists.txt) | Builds `FemGui` as a shared Python extension. Inspect this module and the relevant FEM library in a local release rather than assuming `FreeCAD.exe` contains the task panel implementation. |

**Important:** The appearance of `*CONTACT PAIR` in a generated input file is **not** evidence that FreeCAD implements the contact numerical algorithm itself. The solver-facing CalculiX implementation needs a separate study.

## Small experimental trace plan (not yet executed)
1. On a **self-created synthetic** two-body FreeCAD file, record FreeCAD exact version and contact UI screenshots.
2. Set one master face and one slave face. Use the application property viewer/Python console to record names and settings; do not upload proprietary geometry.
3. Change one parameter at a time: `Friction=False` vs `True`; `SurfaceBehavior=Hard` vs `Linear`; write a fresh `.inp` after each change.
4. Diff only the generated `*SURFACE` / `*CONTACT PAIR` / `*SURFACE BEHAVIOR` / `*FRICTION` sections. Check the surface IDs and unit convention.
5. Execute CalculiX where supported. Preserve the exact `FreeCAD` version, CalculiX version, solver log, convergence/failure status, and `.frd` output. Compare against an independent reference before claiming numerical correctness.
6. Record the observations and failures separately from expectations. For benchmark publication, use geometry/inputs independently created for this study.

## REA setup/checkpoint (not yet performed on the Windows installation)
REA's official source is [morluto/rea](https://github.com/morluto/rea); see its [desktop-app guide](https://github.com/morluto/rea/blob/main/docs/desktop-applications.md) and [Windows Ghidra guide](https://github.com/morluto/rea/blob/main/docs/windows-ghidra-p0.md).

- A read-only desktop installation inventory is available via `rea inspect-desktop-application <directory> --detail complete --json`; it does **not** require Ghidra.
- Native PE pseudocode needs a compatible installed analysis provider (e.g., Ghidra 12.1.x and full JDK on Windows); `rea doctor --provider ghidra --json` checks readiness.
- Locate the **actual** installed FEM GUI binary based on the user machine. Do **not** assume a guessed path, filename, version, or hash.
- Capture SHA-256 of the inspected binary and align it with the local FreeCAD version. Keep REA machine evidence separate from what public source shows.
- REA setup must be reviewed before installing/modifying local agent configurations. Do not upload private files, whole-machine scans, or credentials to a public repo.

## Design inference for a separate Web FEM frontend
This is a **proposal**, not a representation of FreeCAD's source or a working implementation:

`contactSelection -> ContactBC model -> validated mesh-face mapping -> solver adapter -> job runner -> result parser -> viewer`

Acceptance checks must cover selection uniqueness, master/slave identity, units, no-contact vs contact behavior, friction settings, solver error paths and physical convergence. Distinguish `TIED` constraints from unilateral frictionless/frictional contact.

## Open items
- Reproduce exact local UI event sequence and generated input; verify files and binary hashes.
- Trace mesh face assignment and master/slave indexing in FreeCAD's mesh-set generation path.
- Audit CalculiX's actual nonlinear contact algorithm, iteration, tolerance and error reporting using its published source.
- Confirm contact examples and validation tolerances independently; no claim of four solved nonlinear cases is made.
