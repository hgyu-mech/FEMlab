# FreeCAD image extraction and original WebFEA asset design

## Actual inventory (2026-10-20)

These are **image-file occurrences within the inspected Windows FreeCAD 1.1.4 portable/installer**, not unique product features:

| Extraction source | Instances |
| --- | ---: |
| Loose image files in portable archive | 2,187 |
| Qt binary-embedded resources (FreeCAD GUI + bundled Qt DLLs) | 1,229 |
| Image members in 45 FCStd files | 38 |
| PE native resources | 16 |
| Installer-only bitmap | 2 |
| **Total** | **3,472** |
| **SHA-256-distinct image bytes** | **2,961** |

Individual formats observed: PNG 1,638; SVG 1,643; JPG 112; GIF 55; ICO 19; BMP 3; XPM 1; PPM 1. There were 39 contact-sheet PNGs and 6 preview failures, but the affected original files were preserved.

The full archive-relative image name, extraction category, byte size, extension and digest are recorded in **\`research/freecad/IMAGE_MANIFEST.csv\`**. The manifest does not contain the image bytes. It includes Qt runtime artwork, user interface images, third-party docs/templates, and other files that **do not all belong in a WebFEA UI**.

## Local, intentionally NOT pushed to public GitHub

\`\`\`text
D:\RDC_Workspace\output\FreeCAD_1.1.4_images_20261020\
  index.html                     # searchable viewer of local extracted originals
  contact_sheets\INDEX.html      # 39 overview sheets
  images\                       # 3,472 source image file instances
  FreeCAD_1.1.4_ALL_Images_3472.zip
  FreeCAD_1.1.4_GUI_Workbench_Images_1886.zip
  IMAGE_MANIFEST.csv / .json
\`\`\`

The extracted FreeCAD/Qt icons, installer binaries, copyrighted screenshot/template contents and fonts are not newly authored WebFEA assets. Keep their corresponding notices/license obligations intact. Do not upload the original images to this MIT public repository or rebrand them as our own. Public source reading and source-guided reverse engineering are documented; neither guarantees clean-room status.

## New asset work: **not yet done**

The previous conversation discussed generating 1:1 replacement images, but **no generated replacement set has actually been produced**. Do not mislabel the catalog of original assets as generated icons.

### Proposed asset workflow for Codex

1. Map unique **application functions** rather than copying all 3,472 files: \`model-new\`, \`cad-import\`, \`geometry\`, \`material\`, \`fix\`, \`force\`, \`pressure\`, \`contact\`, \`mesh\`, \`run\`, \`stop\`, \`solver-log\`, \`displacement\`, \`stress\`, \`animation\`, \`export\`, \`settings\`.
2. Group into navigation (Geometry, Materials, Constraints, Mesh, Solve, Results), actions, states, thumbnails and decorative assets.
3. Establish an original 24px SVG outline style, stroke width/round caps, simple semantic geometry, light/dark theme contrast, disabled/hover/focus states, keyboard and accessible labels. Define visual tokens before generating hundreds of assets.
4. Design original SVG paths or licensed icon dependencies under their terms. SVG/React components should be individually testable and named by operation, never copied from FreeCAD source icon bytes.
5. Build an asset registry with \`key\`, \`meaning\`, \`new_original_file\`, \`source_evidence_category\`, \`license\`, \`state\` (\`planned\` / \`created\` / \`reviewed\` / \`integrated\`).
6. Generate preview grids and run pixel/snapshot checks; confirm appearance, contrast and differences across light/dark themes. No unsupported promises of one-to-one replacement completion.
7. Only after that consider illustration/3D example image generation with separate rights and provenance.

First priority: ~20 core action icons, NOT blindly cloning Qt icons or third-party documentation figures.

## Verification and reproducibility

The original image extraction scripts and read-only investigation scripts are in \`research/freecad/scripts/\` as historical, environment-specific code. They use absolute paths from a local WSL2 workspace. Treat them as reference scripts needing environment adaptation; do not run them on a whole filesystem or fetch arbitrary archives automatically.

The authoritative local ZIPs were checksum-checked and the original FreeCAD uploads were left unchanged.
