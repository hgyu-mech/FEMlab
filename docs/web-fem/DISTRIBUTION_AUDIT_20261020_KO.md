# FreeCAD 1.1.4 Windows 배포본 실측 분석

분석일: 2026-10-20. 이 문서는 제공된 배포본의 bytes에서 도출한 자체 조사 결과입니다. 외부의 독립 검증 보고서가 아닙니다. 원본 FreeCAD 코드, binary, icon, 연구실 비공개 자료는 이 commit에 포함하지 않았습니다.

## 조사 범위와 증거 보관

Portable `FreeCAD_1.1.4-Windows-x86_64-py311.7z` 및 installer의 원본은 읽기 전용 input에서 검사했습니다. 종료 시 다시 SHA-256을 계산해 두 파일 모두 변경되지 않았음을 확인했습니다.

- 7z 크기: 418,088,341 bytes. SHA-256: `4828741fc91ee37fafcdb97a1abacb18b04ba451ac4372d9ff7a7349b36f4d6d`.
- Installer 크기: 519,314,976 bytes. 전체 hash와 전후 비교는 로컬 `input_manifest.json`에 보관했습니다.
- 7z inventory: 파일 35,582개, directory 3,214개, uncompressed 2,307,792,881 bytes. 분석 대상으로 1,549개 파일을 추출했습니다. 모든 파일의 내부 구현을 전수 분석했다는 뜻이 아닙니다.
- Windows installer, FreeCAD GUI, CalculiX executable은 실행하지 않았습니다.
- REA 6.7.0의 `inspect-with-objdump`와 `inspect-pe-resources`를 실제 실행했습니다. 두 검사는 성공했고 artifact 변경이 없었습니다. `inspect-desktop-application`은 설치된 release에서 COMMAND_NOT_FOUND였습니다.
- 별도 Python/pefile/Capstone parser로 native instructions, Qt resources, ZIP/XML/UNV 및 binary array를 해독했습니다. Ghidra 전체 decompilation은 수행하지 않았습니다.
- 검토한 Python writer/completion handler만 AST로 분리해 synthetic object/test double로 실행했습니다. 전체 application 또는 FE solve와 구분합니다.

상세 HTML·Markdown 보고서, 9개 분석 script와 evidence는 사용자의 로컬 output 폴더 `FreeCAD_1.1.4_audit_20261020`에 있습니다. `analysis_bundle.zip`은 108개 member, 2,900,369 bytes이며 ZIP CRC 검사에서 오류가 없었습니다. bundle SHA-256: `2d5085a6f5f0e327edffd4b2a90ee89a902bb1e84b39c41b9cebdf1bc8602260`. 이 GitHub 문서는 공개 가능한 조사 요약만 담습니다.

## 1. 실행 파일 및 installer 구성

루트 `FreeCAD.exe`는 129,208 bytes이며 version resource가 Chocolatey ShimGen launcher로 식별합니다. 실제 main executable은 `bin/freecad.exe`(265,912 bytes, ProductVersion 1.1.4)입니다. `FreeCADGui.dll`은 33,769,656 bytes, `FemGui.pyd`는 4,169,728 bytes입니다.

`FemGui.pyd`의 SHA-256은 `b3c15ce78f0f24163867fa18a97c4fcb7c4e3431987cb33c185157ee283617f1`이며 export entry는 1,356개입니다. import table에 Qt6 Widgets/Gui/Core, Coin4, VTK9.3, Fem.pyd, PartGui.pyd, Python311 연결이 나타납니다. import는 의존성의 증거이며 특정 조작에서 실행됐다는 증거는 아닙니다.

`ViewProviderFemConstraintContact::setEdit`에 대응하는 exported function을 RVA `0xab3e0`에서 disassemble했습니다. 해당 경로의 import 호출로 `closeDialog`, `clearSelection`, `showDialog`를 확인했습니다. 이름이 없는 내부 call은 임의로 이름을 붙이지 않았습니다.

Installer 자체는 32-bit NSIS wrapper이고 payload의 application/native FEM module은 x86-64입니다. portable과 installer에서 선택한 8개 파일(main executable, FreeCADGui/App DLL, FemGui, ccx, FEMExample, QSS, contact writer)의 SHA-256이 모두 일치했습니다. 전체 payload 동등성 또는 publisher 진위·보안 안전성을 증명하는 검사는 아닙니다.

증거 파일: `pe_summary.json`, `native_contact_setEdit.json`, `package_comparison.json`.

## 2. GUI resource와 디자인 구조

`FemGui.pyd`의 Qt resource registration import thunk와 호출 지점을 찾아 tree/name/data 배열 주소를 복구했습니다. 중복 등록을 제거한 고유 resource는 179개입니다: UI XML 29개, SVG icon 104개, 번역 QM 46개.

29개 embedded UI XML은 대응되는 외부 `.ui` 파일과 전부 SHA-256이 같았습니다. 외부 FEM `.ui` 파일은 총 40개였습니다. resource가 중복 존재한다는 증거이지 runtime loading 우선순위를 검증한 것은 아닙니다. 모든 C++ task panel이 원래 Designer XML로 복원된 것도 아닙니다.

`StartGui.pyd`에서는 icon 3개, theme thumbnail 3개, 번역 36개를 확인했습니다.

`FreeCAD.qss`는 82,141 bytes이고 52종의 `@...` token이 있습니다. 별도 `defaults.qss`, overlay stylesheet, PreferencePack CFG가 존재합니다. Dark CFG의 View background는 raw DWORD `0x1f1f1fff`, selection은 `0x35a047ff`, accent 1은 `0x4aa5ffff`입니다. Light background는 `0xf7f7f7ff`입니다. 배포된 설정 값이며 실제 사용자의 활성 theme를 판정한 것은 아닙니다.

`MeshGmsh.ui`에는 dimension/order, 단위가 있는 min/max size, automatic size 설명, log가 있습니다. `SolverCcxTools.ui`에는 input 작성/편집/실행 버튼, analysis type, working directory, log/time이 나뉩니다. `ResultShow.ui`에는 field/component, min/max, deformation scale, animation, user-defined equation이 있습니다. UI field 존재와 해당 모델의 solver 지원 여부는 별도입니다.

설계 제안: layout, semantic theme token, icon, locale, model/result state를 분리하고, 지원 field 목록은 실제 solver result metadata에서 생성합니다.

증거 파일: `qt_resources_FemGui.pyd.json`, `qt_loose_embedded_comparison.json`, `fem_ui_inventory.json`, `design_tokens.json`.

## 3. FCStd의 저장 구조와 객체 관계

`FEMExample.FCStd`는 528,077 bytes의 ZIP container입니다. 139개 member와 43개 document object가 있으며 ZIP CRC 검사에서 오류가 없었습니다.

- `Document.xml`: object type, property, ID와 object/subelement link.
- `GuiDocument.xml`: visibility, field, camera, tree expansion과 display state.
- `Box.Shape.brp`: B-Rep shape.
- `FemMesh*.unv`: input mesh와 result mesh.
- `DisplacementVectors*`, `DisplacementLengths*`, `vonMises*`, `Stats*`: 저장된 binary result arrays.
- `Data*.vtu`: VTK pipeline dataset.
- `thumbnails/Thumbnail.png`: 이미 저장되어 있던 preview.

Fixed constraint는 `(Box, Face1)`, force는 `(Box, Face2)` 및 direction `(Box, Edge5)`를 참조합니다. `CCX_Results`의 내부 name과 표시 Label `CCX_Results003`은 다릅니다. label로 객체를 연결하지 않아야 합니다.

문서 header의 `ProgramVersion`은 `1.2R45573 +1 (Git)`입니다. main executable 1.1.4와 다른 관측값이지만 이것만으로 변조나 오류를 판단하지 않습니다.

3D WarpVector에는 Factor 10이 저장되어 있고, ViewProvider field는 Displacement Magnitude입니다. scientific displacement와 화면 deformation scale, camera/visibility는 분리되어 있습니다.

증거 파일: `document_FEMExample.json`, `document_numbers.json`, `FEMExample_thumbnail.png`.

## 4. Input mesh와 result mesh가 같지 않습니다

문서 자체의 group label 및 Explanation은 동일 cantilever를 3D solid, 2D plane stress, 1D beam으로 표현했다고 설명합니다. 실제 UNV node/connectivity와 result array를 따라가서 다음을 확인했습니다.

| 모델 | 입력 nodes | 결과 nodes | 저장된 max displacement magnitude (mm) |
|---|---:|---:|---:|
| 3D solid | 569 | 569 | 87.93698784321887 |
| 2D plane stress | 177 | 408 | 86.87300528659505 |
| 1D beam | 33 | 200 | 88.37503911091486 |

1D 입력은 16개 3-node line element이고 y=z=0입니다. 저장된 결과 mesh는 16개 20-node volume element이며 y,z 범위가 -500~500입니다. 2D 입력은 평면이고 결과 mesh에는 두께 방향 좌표가 있습니다. 변환의 solver 내부 경로 전체를 추적한 것은 아니지만, 입력/출력 mesh가 다르다는 사실은 저장 파일로 확인됩니다.

따라서 입력 `(33, 3)` 좌표에 결과 `(200, 3)` displacement를 직접 붙일 수 없습니다. 별도 resultMesh와 mapping contract가 필요합니다.

3D `DisplacementLengths1`은 4,556 bytes입니다. 첫 4 bytes `39 02 00 00`은 little-endian uint32 569이고, 뒤에 569개 float64가 있습니다: `4 + 569*8 = 4556`. VectorList는 `4 + 569*3*8 = 13660` bytes입니다. 세 result set에서 vector norm을 재계산한 값과 저장된 magnitude의 최대 절대차는 0.0이었습니다.

이는 저장 배열의 내부 일관성 검사입니다. 새 해석 실행이나 physical validation이 아닙니다. magnitude 최대값과 analytical transverse tip deflection의 차이를 곧바로 solver error로 해석하지 않습니다.

증거 파일: `mesh_mapping.json`, `document_numbers.json`.

## 5. Serialized scalar와 solver 단위의 경계

3D 모델의 Force XML에는 raw scalar `9000000000`이 있습니다. 재료에는 `YoungsModulus = 2.1e+08 kg/(mm*s^2)`가 저장됩니다. 포함된 `femmesh/meshtools.py`는 Force를 `getValueAs("N")`으로 변환하고, CalculiX writer는 mm/N/s/K 단위를 명시합니다.

mm·kg·s의 차원 환산상 force raw 9e9는 9e6 N, Young's modulus는 210000 MPa에 대응합니다. L=8000 mm, 1000×1000 mm section을 사용한 Euler–Bernoulli cross-check는 87.771429 mm로, 저장된 Explanation의 87.77 mm와 일치합니다. 이는 수식·단위 대조이며 FreeCAD Quantity runtime 변환이나 신규 FEM solve가 아닙니다.

설계 제안: unit metadata 없이 raw XML 숫자를 solver input으로 복사하지 않습니다. conversion은 adapter 경계에서 검증합니다.

## 6. Contact writer의 제한된 실행 실험

배포본 `write_constraint_contact.py`의 두 writer function만 검토 후 AST로 분리했습니다. fake contact/surface와 이미 지정 단위의 Quantity double을 사용했습니다. FreeCAD GUI, mesher, ccx를 실행하지 않았습니다.

Friction만 false→true로 바꾸고 나머지 조건을 유지하면 `*FRICTION` 및 `0.2, 100` 두 줄이 추가됐습니다. Hard/Linear/Tied variant도 검사하여 4개 case와 5개 writer assertion이 통과했습니다. 생성된 조각은 input serialization 증거이며 standalone FE deck 검증이나 contact convergence 검증이 아닙니다.

증거 파일: `writer_probe/results.json`, `writer_probe/friction_toggle.diff`.

## 7. 실패 처리에서 추가 재현이 필요한 지점

배포본 `task_solver_ccxtools.py`의 `calculixFinished`를 Qt/solver test double로 분리 실행했습니다. normal process exit이고 stdout 검사가 실패하는 경로에서 `calculixError` 이후 `reset_mesh_purge_results_checked`, `load_results`가 계속 호출됐습니다. abnormal exit는 result load 전 return했습니다.

이것만으로 사용자 화면에 잘못된 결과가 나타난다고 단정하지 않습니다. partial result를 의도했거나 importer가 추가 검사할 수 있습니다. 실제 실패 모델에서 live 재현해야 합니다.

설계 제안: process exit, numerical convergence, result import, partial/stale result를 별도 상태로 표시합니다. 현재 run ID와 결과 생성 provenance를 저장합니다.

증거 파일: `solver_finish_probe.json`.

## 다음 구현에 적용할 acceptance gates

1. model identity/label, scientific result/viewState를 분리한다.
2. input/result mesh mapping과 node/element association을 검증한다.
3. units를 명시하고 geometry/material/load conversion을 검사한다.
4. input 생성, solver 실행, convergence 판정, result import를 분리한다.
5. remeshing 후 face binding, save/load, 실패 후 partial/stale result를 regression case로 만든다.

이 내용은 신규 Web FEM 설계 제안이며, 네 가지 해석의 구현 완료 또는 상용 solver 동등성 주장이 아닙니다.
