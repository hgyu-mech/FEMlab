# FreeCAD 1.1.4 reverse-engineering research (public handoff)

These files document the *independent personal* investigation of the public FreeCAD release and reference-solver experiments. This folder is not an official university or research lab software distribution.

## Files

- `evidence/`: measured distribution hashes/module inventory, Qt-UI structure, theme settings, stored FCStd numeric fields, package comparisons, synthetic probe results and the actual reference-solver run-readback JSON from 2026-10-20.
- `scripts/distribution/`: nine historical offline analysis scripts that inspect a FreeCAD Windows distribution and write structured reports.
- `scripts/assets/`: seven historical scripts to discover/extract image payloads, generate previews and test local ZIP packages.
- `IMAGE_MANIFEST.csv`: individual image paths, categories, sizes and SHA-256; **does not contain binary icons**.

## REA + GUI verification

REA source/PE analysis and a later Windows Ghidra-backed REA study were recorded locally; full native Evidence bundles (some around 9 MB) remain on the user's computer. `RUNTIME_RESULTS_20261020.md` summarizes actual Windows FreeCAD/CalculiX runs; do not confuse these with the original distribution-only inspection.

The scripts under `scripts/` contain **historical absolute `/work/...` workspace paths**. They are included verbatim for Codex review and must be parameterized, tested and sandboxed before reuse. Do not assume running `python script.py` in Codex cloud will find local D: files. They are source-level audit tools, not production WebFEA code.

## Do not copy source artwork to public MIT repository

The 3,472 original FreeCAD/Qt/third-party image file instances and the large binary packages are intentionally kept in the local workspace. No original replacements have yet been generated. Use the inventory as a design *map*, not ready-to-redistribute art or proof of new visual assets.

See `docs/web-fem/CODEX_START_HERE.md`, `docs/web-fem/ASSET_DESIGN_HANDOFF.md`, and `docs/web-fem/RUNTIME_RESULTS_20261020.md` from repository root.
