from pathlib import Path
import json,html,re,zipfile,hashlib,datetime
B=Path('/work/output/FreeCAD_1.1.4_audit_20261020');E=B/'evidence'
load=lambda n:json.loads((E/n).read_text())
manifest=load('input_manifest.json');nums=load('document_numbers.json');mesh=load('mesh_mapping.json');comp=load('package_comparison.json');qt=load('qt_loose_embedded_comparison.json');tokens=load('design_tokens.json')
rr={x['object']:x for x in nums['results']}
def link(n):return f'[증거: {n}](evidence/{n})'
rows='\n'.join(f"| {label} | {mi} → {mo} | {rr[key]['fields']['DisplacementLengths']['max']:.6f} |" for label,mi,mo,key in [('3D solid',569,569,'CCX_Results'),('2D plane stress',177,408,'CCX_Results001'),('1D beam',33,200,'CCX_Results002')])
input_rows='\n'.join(f"| `{x['name']}` | {x['size_bytes']:,} | `{x['sha256']}` |" for x in manifest['inputs'])
md=f'''# FreeCAD 1.1.4 Windows 배포본 내부 분석

분석일: 2026-10-20. 대상: 사용자가 제공한 portable `.7z`와 installer `.exe`의 실제 bytes.

## 0. 수행 범위와 판정 수준

본 보고서는 파일 구조·binary·GUI resource·예제 문서·포함된 Python 코드의 제한된 실험을 다룹니다. 홈페이지 소개문을 요약한 보고서가 아닙니다. 다만 이 정보가 인터넷 어디에도 없다고 보장하지 않으며, 개발자의 설계 의도를 관측된 구조만으로 확정하지 않습니다.

- 원본 두 파일은 읽기 전용 input에서 검사했고, 종료 시 SHA-256을 다시 계산해 둘 다 변경되지 않았음을 확인했습니다.
- Windows installer, FreeCAD GUI, CalculiX 실행 파일은 실행하지 않았습니다.
- 검토한 Python 함수 두 묶음만 AST로 분리하여 synthetic object와 test double로 실행했습니다. GUI 통합 실행이나 FEM numerical verification과 구분합니다.
- Ghidra 전체 decompilation은 수행하지 않았습니다. REA의 PE resource/objdump 검사, Capstone의 native instruction 해독, 직접 작성한 Qt resource 및 저장 데이터 parser를 사용했습니다.
- 원본 코드·binary·asset은 새 FEM 구현 저장소에 복사하지 않았습니다. 이 폴더의 복구 asset은 해당 배포본을 검토하기 위한 자료입니다.

## 1. 파일의 신원과 packaging

| 입력 | 크기(bytes) | SHA-256 |
|---|---:|---|
{input_rows}

7z archive inventory에는 파일 35,582개와 directory 3,214개가 있습니다. 전체 uncompressed size는 2,307,792,881 bytes입니다. LZMA2/LZMA/BCJ2의 solid archive이며, 분석용으로 1,549개 파일을 선택 추출했습니다. 이 중 일부에 대해 깊은 검사를 했으며, 전체 파일의 모든 코드를 분석한 것은 아닙니다.

Installer는 32-bit NSIS wrapper 안에 payload를 담고 있습니다. 내부의 실제 `bin/freecad.exe` 및 FEM module은 x86-64입니다. wrapper의 bitness와 애플리케이션 bitness를 혼동하지 않아야 합니다.

두 패키지에서 선택한 8개 파일은 SHA-256이 모두 같았습니다: `bin/freecad.exe`, `bin/FreeCADGui.dll`, `bin/FreeCADApp.dll`, `lib/FemGui.pyd`, `bin/ccx.exe`, `FEMExample.FCStd`, `FreeCAD.qss`, contact writer. 전체 payload가 동일하다는 검사는 아니며, 이 결과가 publisher authenticity나 malware 부재를 증명하지도 않습니다.

{link('input_manifest.json')} · {link('archive_manifest.json')} · {link('package_comparison.json')}

## 2. `FreeCAD.exe` 한 파일이 프로그램 전체가 아닙니다

| 구성 | 이번 파일에서 관측한 사실 |
|---|---|
| 루트 `FreeCAD.exe` | 129,208 bytes, version resource가 Chocolatey ShimGen launcher로 식별됩니다. |
| `bin/freecad.exe` | 265,912 bytes, FreeCAD main executable, product version 1.1.4입니다. |
| `bin/FreeCADGui.dll` | 33,769,656 bytes. Qt Widgets, Coin4, OpenGL 등의 import가 있습니다. |
| `lib/Fem.pyd` | FEM data / mesh / VTK 계열 의존성을 가진 native Python extension입니다. |
| `lib/FemGui.pyd` | 4,169,728 bytes, 1,356개 named/ordinal export entry가 관측됩니다. FEM GUI resource와 native code가 포함됩니다. |
| `bin/ccx.exe` | 8,329,256 bytes. 별도 solver 프로그램이며 이 조사에서는 실행하지 않았습니다. |

Import table은 연결 의존성의 증거이지, 특정 사용자 조작에서 그 함수가 실행되었다는 dynamic trace는 아닙니다.

Contact의 native `ViewProviderFemConstraintContact::setEdit` export를 RVA `0xab3e0`에서 직접 disassemble했습니다. 관측된 call target에는 `closeDialog`, `clearSelection`, `showDialog`가 있습니다. 이름이 없는 내부 호출은 임의로 constructor 등으로 명명하지 않았습니다. 즉 하나의 dialog lifecycle 경로를 binary에서 확인했으며, Contact 알고리즘 전체를 복원한 것은 아닙니다.

{link('pe_summary.json')} · {link('native_contact_setEdit.json')} · {link('launcher_strings.json')}

## 3. GUI 디자인을 binary에서 복구한 결과

### 3.1 FemGui.pyd에 묶인 resource 179개

Qt `qRegisterResourceData`의 import thunk와 이를 참조하는 x64 call/jump를 찾았습니다. 직전 instruction의 `RDX`, `R8`, `R9` RIP-relative 주소로 resource tree/name/data 배열을 찾아 파싱했습니다. 압축된 payload는 해제하고 각 내용의 SHA-256을 계산했습니다. 중복 등록 경로는 같은 resource로 합쳐 집계했습니다.

| 분류 | 고유 resource 수 |
|---|---:|
| UI XML | 29 |
| SVG icon | 104 |
| 번역 QM | 46 |
| 합계 | 179 |

밖에 별도로 있는 FEM `.ui` 파일은 40개입니다. binary 속 UI XML 29개는 대응하는 외부 UI 파일과 29/29개 모두 SHA-256이 일치했습니다. 하나의 UI 정의가 외부 파일과 embedded resource 양쪽에 존재한다는 것은 확인했지만, 모든 상황에서 어느 경로가 우선 사용되는지는 별도의 runtime 확인이 필요합니다.

`FEM_ConstraintContact.svg`, `FEM_ConstraintForce.svg`, `SolverCcxTools.ui`, `ResultShow.ui` 등의 실제 payload를 복구했습니다. `StartGui.pyd`에서는 42개 resource(icons 3, theme thumbnail 3, translations 36)를 확인했습니다.

Contact의 원본 `.ui`가 이 29개 안에 있다는 뜻은 아닙니다. 일부 Qt UI는 C++ widget construction 코드로 compile되어 있으므로, 모든 창을 원래 Designer XML로 복원할 수 있다는 주장은 하지 않습니다.

{link('qt_resources_FemGui.pyd.json')} · {link('qt_loose_embedded_comparison.json')} · {link('fem_ui_inventory.json')}

### 3.2 패널 디자인에서 확인한 구체적 구성

- `MeshGmsh.ui`: element dimension/order, minimum/maximum size, 단위 입력 widget, output log. size 0.0을 automatic으로 쓰는 설명이 있습니다.
- `SolverCcxTools.ui`: working directory, static/frequency/thermomechanical/check/buckling, `Write .inp File`, `Edit .inp File`, `Run CalculiX`, log, elapsed time.
- `ResultShow.ui`: displacement magnitude와 각 component, stress, PEEQ, histogram, min/max, deformation scale, animation, user-defined equation. 결과 field가 UI에 존재하는 것과 해당 모델에서 지원·계산됐다는 사실은 다릅니다.

구현 제안: 웹에서는 `Auto`를 별도 상태로 저장하고, 숫자 0을 특별한 의미로 쓰는 설정은 adapter 경계에서만 처리합니다. 계산 가능한 result field는 solver가 반환한 metadata로 UI에 노출합니다.

### 3.3 색상과 layout은 한 파일에 고정되어 있지 않습니다

실제 `FreeCAD.qss`는 82,141 bytes이며 {len(tokens['tokens'])}종의 `@...` token이 관측됩니다. `defaults.qss`, overlay stylesheet, PreferencePack `.cfg`가 별도입니다.

예를 들어 `FreeCAD Dark.cfg`에서 View background raw DWORD는 `0x1f1f1fff`, selection은 `0x35a047ff`, theme accent 1은 `0x4aa5ffff`입니다. `FreeCAD Light.cfg`의 View background는 `0xf7f7f7ff`입니다. 이 값들은 package 설정 값이며, 사용자가 실제로 어떤 theme를 활성화했는지는 이 배포본만으로 확정하지 않습니다.

구현 제안: layout, semantic color token, icon, locale, model rendering 상태를 분리합니다. 화면의 RGB를 수작업으로 따라 그리기보다 각 상태가 무엇을 표현하는지 명세합니다.

{link('design_tokens.json')}

## 4. FCStd는 객체 그래프와 여러 data payload를 묶는 프로젝트 파일입니다

`FEMExample.FCStd`는 528,077 bytes의 ZIP container입니다. CRC 검사를 통과했으며 139개 member와 43개 document object가 있습니다.

```text
FEMExample.FCStd
  Document.xml             object types / properties / links / IDs
  GuiDocument.xml          visibility / camera / display fields / tree state
  Box.Shape.brp            B-Rep shape payload
  FemMesh*.unv             input and result meshes
  DisplacementVectors*     binary vector arrays
  DisplacementLengths*     binary scalar arrays
  vonMises*, Stats*        stored numerical results
  Data*.vtu               VTK pipeline datasets
  thumbnails/Thumbnail.png
```

`Document.xml`에서는 `ConstraintFixed`가 `(Box, Face1)`을 참조하고, `ConstraintForce`는 `(Box, Face2)`와 direction reference `(Box, Edge5)`를 저장합니다. 이것은 화면 픽셀 위치가 아니라 object/subelement reference입니다.

`CCX_Results`의 내부 name은 그대로인데 Label은 `CCX_Results003`입니다. 사용자 표시 이름과 참조용 식별자가 다르므로 웹 설계에서도 label로 객체를 연결하지 않아야 합니다.

저장된 문서 header에는 `ProgramVersion="1.2R45573 +1 (Git)"`가 적혀 있습니다. main executable의 product version 1.1.4와 다른 값입니다. 이는 저장 문서의 기록과 실행 프로그램 metadata가 다른 관측이며, 그것만으로 배포본 오류나 변조를 단정하지 않습니다.

{link('document_FEMExample.json')}

## 5. 단순한 보 예제 하나가 아니라 1D·2D·3D 비교 모델이 들어 있습니다

문서의 group label은 `3D`, `2D`, `1D`이며, 저장된 Explanation도 같은 cantilever를 solid / plane stress / beam으로 표현한 세 모델이라고 설명합니다. group link와 실제 UNV mesh를 따라가서 아래 수를 확인했습니다.

| 모델 | 입력 mesh nodes → 결과 mesh nodes | 저장된 max displacement magnitude (mm) |
|---|---:|---:|
{rows}

특히 1D의 입력은 33 nodes와 16개 3-node element이며 y=z=0인 선입니다. 결과 mesh는 200 nodes와 16개 20-node element이며 y,z 좌표가 -500~500 범위를 갖습니다. 2D 입력은 177 nodes의 평면이고, 결과는 408 nodes 및 70개 15-node element로 두께 방향 좌표가 추가되어 있습니다. 변환 원인 전체를 solver 내부에서 추적한 것은 아니지만, 입력/출력 node 집합이 다르다는 점은 파일 자체로 확인됩니다.

구현 제안: `inputMesh`와 `resultMesh`를 구분하고 mapping을 저장합니다. solver 결과의 200×3 displacement를 원래 33×3 input node 배열에 그대로 붙이는 설계는 성립하지 않습니다.

### 저장된 result를 직접 해독했습니다

3D scalar file `DisplacementLengths1`의 크기는 4,556 bytes입니다.

```text
first 4 bytes: 39 02 00 00  -> little-endian uint32 count = 569
payload:      569 float64 values
size check:   4 + 569 × 8 = 4,556 bytes
```

대응하는 `DisplacementVectors1`은 `4 + 569 × 3 × 8 = 13,660 bytes`입니다. 직접 해독한 vector에서 norm을 다시 계산한 값은 저장된 scalar와 최대 절대차 0.0으로 일치했습니다. 세 result set 모두 같은 검사를 수행했습니다.

이는 저장된 배열의 내부 일관성 검사이며, 새 FEM solve나 물리적 정확성 인증이 아닙니다. 표의 max magnitude와 Euler–Bernoulli의 횡방향 tip deflection은 엄밀히 같은 관측량이 아니므로, 그 차이를 곧바로 solver error라고 해석하지 않습니다.

{link('mesh_mapping.json')} · {link('document_numbers.json')}

## 6. XML 숫자를 그대로 solver에 넘기면 단위가 틀릴 수 있습니다

3D geometry에는 length 8000, width/height 1000이 저장되어 있습니다. Material에는 `YoungsModulus = 2.1e+08 kg/(mm*s^2)`가 있고, `Force`의 serialized scalar는 9,000,000,000입니다. force class는 `App::PropertyForce`입니다.

배포본의 `Mod/Fem/femmesh/meshtools.py`는 force를 `getValueAs("N")`으로 변환하며, CalculiX writer가 선언하는 출력 단위는 mm, N, s, K입니다. 따라서 serialized scalar를 그 단위 그대로라고 취급해서는 안 됩니다.

단위 환산 및 analytical cross-check: mm·kg·s 기준의 force 9e9는 9e6 N, 위 Young's modulus는 210000 MPa에 대응합니다. L=8000 mm, square section 1000×1000 mm이면 I=8.3333333e10 mm^4이고, P L^3/(3 E I)=87.771429 mm입니다. 문서에 저장된 reference 설명 87.77 mm와 일치합니다. 실제 FreeCAD Quantity runtime에서 변환한 실험은 아니며, 물리 단위 환산과 문서 숫자의 대조입니다.

구현 제안: API와 result file에 unit system을 명시하고, conversion을 solver adapter 한곳에 모읍니다. 숫자만 있는 JSON은 해석 명세로 충분하지 않습니다.

## 7. 계산 data와 화면 효과는 분리되어 저장됩니다

3D `WarpVector`의 Factor는 10입니다. 해당 ViewProvider의 Field는 `Displacement Magnitude`, Visibility는 true이고, 원래 pipeline 및 result object의 visibility는 별도로 저장되어 있습니다. camera에는 `OrthographicCamera`의 position/orientation/near/far/height가 기록됩니다.

그러므로 화면의 변형 크기를 실제 물리적 변위로 읽어서는 안 됩니다. 화면 좌표를 만드는 scale과 실제 displacement field는 분리해야 합니다. 저장된 회전·확대·색상·tree expansion은 모델의 material/BC와도 다른 계층입니다.

구현 제안: 프로젝트 파일을 `model`, `mesh`, `results`, `viewState`로 구분하고 `displayScale=10`이 scientific data를 바꾸지 않게 합니다.

## 8. Contact input writer를 제한적으로 실제 실행했습니다

대상은 배포본의 `write_constraint_contact.py`입니다. source SHA-256은 `229455e61fc968e5153fc382b3fb80b78069ec734483bd7431be2cd077ae9d56`입니다.

검토한 두 function만 AST로 추출하고 synthetic contact object를 전달했습니다. model/mesh/GUI/solver 실행은 하지 않았고, Quantity double은 이미 지정 단위로 주어진 값을 반환하도록 제한했습니다.

같은 synthetic surfaces와 coefficient를 유지하고 `Friction=False → True`만 바꾸자 다음 두 줄이 추가됐습니다.

```diff
+*FRICTION
+0.2, 100
```

Hard/Linear/Tied 조건도 각각 대응 keyword를 생성했습니다. 4개 case와 5개 writer assertion을 통과했습니다. 이것은 조건을 input deck으로 변환하는 동작의 증거이며, frictional contact numerical algorithm의 수렴 검증이 아닙니다.

{link('writer_probe/results.json')} · {link('writer_probe/friction_toggle.diff')}

## 9. 실패 처리에서 추가 검증할 지점을 찾았습니다

실제 포함된 `task_solver_ccxtools.py`는 QProcess로 ccx를 실행하고, 버튼을 Run → Stop → Re-run으로 바꿉니다. analysis type이 바뀌면 Edit/Run 버튼을 비활성화해 input을 다시 쓰도록 합니다.

`calculixFinished`를 synthetic test doubles로 분리 실행했습니다. normal process exit이면서 stdout 검사 실패인 경우, 이번 handler의 호출 순서는 다음이었습니다.

```text
calculixError
  -> Loading result sets...
  -> reset_mesh_purge_results_checked
  -> load_results
```

abnormal exit branch는 result load 없이 return했습니다. 이 사실만으로 화면에 잘못된 결과가 나타난다고 결론 내리지 않습니다. partial result를 의도했거나 importer가 추가 검증할 수 있으므로, 실제 nonconvergence model을 이용한 live 재현이 필요합니다.

구현 제안: `process exited`, `numerically converged`, `result imported`, `partial result`를 서로 다른 상태로 저장·표시합니다. partial result를 허용하더라도 current run ID와 convergence를 분명히 표시하고, 이전 결과를 새 성공 결과로 표시하지 않게 test합니다.

{link('solver_finish_probe.json')}

## 10. 분석 도구의 실제 실행 상태

REA 6.7.0을 분석 전용 workspace에 설치했습니다. agent 설정이나 Windows 설치 상태는 변경하지 않았습니다. `inspect-desktop-application`은 이 release에서 COMMAND_NOT_FOUND였으므로, 문서에 있는 명령이 설치 release에 존재한다고 가정하지 않았습니다. 대신 `inspect-with-objdump`와 `inspect-pe-resources`를 실제 실행했고 exit code 0 및 artifact_changed=false를 확인했습니다.

Qt resource 복구와 native call 경로 해석은 별도의 PE/Capstone parser로 수행했습니다. Ghidra로 전체 C++ source를 복원했다는 주장은 하지 않습니다. 파일/함수/GUI 상태가 서로 연결되는 일부 경로를 확인한 단계입니다.

{link('rea_femgui_objdump.json')} · {link('rea_freecad_pe_resources.json')} · {link('rea_desktop.json')} · {link('rea_package_metadata.json')}

## 11. 개발 기획에 반영할 사항

1. model identity와 표시 label을 분리합니다. CAD face selection은 object/subelement reference로 저장합니다.
2. input mesh와 result mesh를 분리하고 element/node mapping을 검증합니다.
3. canonical unit system 및 explicit conversion을 도입합니다.
4. scientific result와 view state, deformation scale, theme를 분리합니다.
5. solver input 작성·검사, execution, convergence 판정, result import를 독립 단계로 둡니다.
6. field 목록과 GUI의 solver 표기는 실제 계산 metadata에서 생성합니다.
7. 재meshing 후 face binding 유지, 저장/복원, 실패 후 partial/stale result 처리를 regression case로 만듭니다.

이것들은 관측 결과에서 도출한 별도 설계 제안이며, 이미 구현된 새 Web FEM 기능은 아닙니다. 네 가지 해석의 완성, runtime 상호작용 전수 조사, memory/performance 평가, full solver numerical verification은 이번 범위 밖입니다.

## 파일 사용

`report.html`을 열면 본문, 실제 복구 icon gallery, 원본 예제 thumbnail, evidence file 링크를 볼 수 있습니다. `scripts/`에는 재현용 분석 script가 있고, `evidence/`에는 원자료에서 도출한 manifest·hash·parser output·실험 log가 있습니다. 환경별 경로는 script 상단에서 수정해야 합니다. 외부 패키지 버전은 tool install log에 기록했습니다.
'''
(B/'REPORT_KO.md').write_text(md,encoding='utf8')
# Minimal, escaped Markdown renderer. No remote scripts or fonts.
def inline(s):
 s=html.escape(s);s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s);s=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s);return s
blocks=[];lines=md.splitlines();i=0
while i<len(lines):
 s=lines[i]
 if s.startswith('```'):
  j=i+1
  while j<len(lines) and not lines[j].startswith('```'):j+=1
  blocks.append('<pre><code>'+html.escape('\n'.join(lines[i+1:j]))+'</code></pre>');i=j+1;continue
 if s.startswith('|'):
  table=[]
  while i<len(lines) and lines[i].startswith('|'):
   l=lines[i]
   if not re.fullmatch(r'[| :\-]+',l):table.append([inline(x.strip()) for x in l.strip('|').split('|')])
   i+=1
  blocks.append('<div class="table-wrap"><table>'+''.join('<tr>'+''.join(f'<{"th" if n==0 else "td"}>{c}</{"th" if n==0 else "td"}>' for c in row)+'</tr>' for n,row in enumerate(table))+'</table></div>');continue
 if s.startswith('#'):
  level=len(s)-len(s.lstrip('#'));blocks.append(f'<h{level}>'+inline(s[level:].strip())+f'</h{level}>')
 elif s.strip():blocks.append('<p>'+inline(s)+'</p>')
 i+=1
assets=[]
for name in ['FEM_ConstraintContact.svg','FEM_ConstraintForce.svg','FEM_MaterialSolid.svg','FEM_MeshGmshFromShape.svg','FEM_ResultShow.svg']:
 ps=list((E/'recovered_resources').glob('*'+name))
 if ps:assets.append('<figure><img src="evidence/recovered_resources/'+html.escape(ps[0].name)+'" alt="'+name+'"><figcaption>'+name+'</figcaption></figure>')
gallery='<section><h2>배포본에서 직접 추출한 이미지</h2><p>왼쪽은 FCStd에 저장되어 있던 thumbnail입니다. 오른쪽은 FemGui.pyd에서 복구한 SVG입니다. 새로 렌더한 FreeCAD 실행 화면이 아닙니다.</p><div class="gallery"><figure><img class="thumb" src="evidence/FEMExample_thumbnail.png"><figcaption>Stored FCStd thumbnail</figcaption></figure>'+''.join(assets)+'</div></section>'
style='''body{font-family:system-ui,"Malgun Gothic",sans-serif;background:#f5f6f8;color:#202733;margin:0;line-height:1.75}main{max-width:1060px;margin:36px auto;background:white;padding:40px 52px;border:1px solid #dde1e7}h1{font-size:30px;line-height:1.4}h2{margin-top:44px;border-top:2px solid #dce2ea;padding-top:20px;font-size:23px}h3{margin-top:30px}p{overflow-wrap:anywhere}code{font-family:Consolas,monospace;background:#f0f2f5;padding:2px 4px;border-radius:3px;font-size:.91em}pre{background:#f0f2f5;border-left:4px solid #47627d;padding:15px;overflow:auto;line-height:1.55}pre code{padding:0}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #d7dee6;padding:10px;text-align:left;vertical-align:top}th{background:#eaf0f6}a{color:#174f8f}.gallery{display:flex;flex-wrap:wrap;gap:18px;align-items:center}figure{margin:10px;max-width:240px;text-align:center}figure img{width:64px;height:64px;object-fit:contain}figure img.thumb{width:240px;height:240px}figcaption{font-size:12px;overflow-wrap:anywhere}.stamp{font-size:13px;color:#596776}@media(max-width:700px){main{padding:20px;margin:0}h1{font-size:25px}}'''
(B/'report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>FreeCAD 1.1.4 내부 분석</title><style>'+style+'</style><main><p class="stamp">ARTIFACT AUDIT · 2026-10-20 · FILE EVIDENCE + ISOLATED PROBES</p>'+gallery+''.join(blocks)+'</main></html>',encoding='utf8')
files=[p for p in B.rglob('*') if p.is_file() and p.suffix.lower() not in ['.zip','.ttf','.otf','.woff','.woff2']]
checks={str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};(B/'OUTPUT_SHA256.json').write_text(json.dumps(checks,indent=2))
with zipfile.ZipFile(B/'analysis_bundle.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in files+[B/'OUTPUT_SHA256.json']:z.write(p,p.relative_to(B))
print('Report characters',len(md),'Files',len(files),'Bundle bytes',(B/'analysis_bundle.zip').stat().st_size)
print('Output',B)
