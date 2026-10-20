# 공개 reference 조사 기록

날짜: 2026-10-20. 상태: **초기 소스 분석과 제한된 브라우저 동작 확인**. 전체 코드 audit, 독립 수치 검증, 보안 검증 또는 제품 인증이 아니다.

## 1. 재현 기준

- KoFEM 소스: `mkofler96/KoFEM`, commit `b0cae453d6eaac23bd7382c9b9f7a6b7812f311f`.
- FreeCAD 소스: `FreeCAD/FreeCAD`, tag `1.1.4`, commit `4fd3bf320d9566a27e60069fc8387448aaa3a094`.
- 공개 웹 demo의 배포 WASM checksum과 위 source commit의 일치는 별도로 검증하지 않았다.
- source를 읽은 것, browser automation 보고, 문서의 주장, 자체 제안을 아래에서 구분한다. upstream test를 이번 조사에서 직접 실행하지 않았다.

## 2. KoFEM architecture: 소스에서 확인

| 대상 | 확인한 사실 | 근거 |
| --- | --- | --- |
| 전체 pipeline | STEP/OCCT, Netgen, MFEM, C++/WASM과 React/Three.js로 설명한다 | [README](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/README.md) |
| frontend 구성 | React, React Three Fiber/Drei, Three.js, Zustand, TypeScript, Vite dependency 및 typecheck/lint/test script | [package.json](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/web/package.json) |
| 화면 shell | TopBar, Sidebar, Viewport, StatusBar를 조합 | [App.tsx](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/web/src/App.tsx) |
| workflow panel | geometry/constraints/solve/optimize/results에 따라 panel 교체 | [LeftPanel.tsx](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/web/src/components/panel/LeftPanel.tsx) |
| sidebar | resize/collapse와 작은 화면 overlay 처리 | [Sidebar.tsx](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/web/src/components/panel/Sidebar.tsx) |
| solve 연결 | readiness 검사 후 worker에 model data 전달, displacement/von Mises 저장, results mode 전환, error banner와 logs 연결 | [useSolver.ts](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/web/src/hooks/useSolver.ts) |
| solid linear solve | CG + Gauss-Seidel preconditioner, relative tolerance 1e-6, maximum iteration 5000, nonconverged면 예외 | [solve_mfem.cpp](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/engine/cpp/solve_mfem.cpp) |

`useSolver.ts`의 pre-flight는 mesh/material/BC/driving-action의 존재 등을 확인한다. 이 검사만으로 rigid-body mode가 모두 제거되었거나 수치적으로 well-posed하다고 보장하지 않는다.

`App.tsx`는 example query를 통해 미리 계산된 `.vtu`를 읽는다. 따라서 페이지를 열었을 때 contour가 보이는 것은 새 solve의 증거가 아니다. source CAD가 없는 예제에서는 remeshing이 불가능할 수 있다.

## 3. 브라우저 동작 확인: 자동화 도구의 실행 보고

대상은 공개 [plate-with-hole example](https://kofem.org/app/?example=plate-with-hole) 한 개다. 개인 파일을 업로드하지 않았고 로그인하지 않았다.

도구는 Geometry, Constraints, Solve, Optimize, Results 탭을 열고 `Run static solve`를 한 번 클릭했다. 이후 Results 탭 전환과 `Solved converged` 표시를 보고했다. 초기 stress contour는 preloaded result로 구분했다.

보고된 화면 정보:

- 1664 nodes, 768 CHEXA elements, 34 fixed nodes.
- field 선택: displacement magnitude, Ux/Uy/Uz, von Mises stress.
- deformation scale, automatic/manual legend range, undeformed overlay, surface/volume/wireframe.
- 새 실행 후 displacement magnitude의 화면 maximum은 약 9.688 mm.
- solver 설정 표시에는 `Direct`, output 표시에는 `U, S, RF`가 보였음.

이 수치는 **화면 관찰값이지 정답/오차 검증 결과가 아니다**. source-to-binary 대응, reference 해와의 비교, mesh convergence, 전체 logs, 정확한 wall time benchmark는 미확인이다. 도구가 screenshot capture를 보고했으나 이 문서에 독립적으로 검토 가능한 screenshot artifact는 첨부하지 않았다. 단일 solve가 완료되었다는 보고를 모든 GUI 기능이나 numerical accuracy의 보증으로 확대하지 않는다.

## 4. 개선 후보: 표시와 실행의 연결

### K-01: `Direct` 표시와 CG 경로

확인한 [SolvePanel.tsx](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/web/src/components/panel/SolvePanel.tsx)는 solver 이름을 `Direct`라는 고정 text로 표시한다. 동일 commit의 `solve_mfem.cpp`에 있는 solid linear-elastic 경로는 `mfem::CGSolver`를 호출한다.

**결론:** 조사한 source에서 UI 설명과 해당 solver 경로 사이의 불일치가 확인된다. 모든 실행 경로에 대한 결론은 아니다. 새 플랫폼은 실제 solver의 metadata에서 label을 만들어야 한다.

### K-02: 하중이 있는데 `0 load DOFs`가 보이는 경우

`useSolver.ts`는 nodal loads 또는 surface loads 중 하나만 있어도 load가 있다고 판단하지만, readiness label의 수는 nodal `loads.length`만 표시한다. browser automation도 `Loads applied · 0 load DOFs`를 보고했다.

**결론:** surface load가 있을 때 가능한 표시 불일치다. 이것만으로 solver가 하중을 누락했다고 판단하면 안 된다. 새 UI는 load type, entity count, total force 또는 traction을 분리해 표시한다.

### K-03: convergence와 output 표시의 근거

`useSolver.ts`에서 직접 받는 result는 displacement와 von Mises이고, `SolvePanel.tsx` output 설명은 고정된 `U, S, RF`다. 이 경로만으로 RF가 실제 반환·저장·표시되는지 확정할 수 없다. reaction 지원은 별도 추적 대상으로 남긴다.

solid CG 함수는 convergence 실패 시 exception을 발생시키고 partial result를 버린다. 새 플랫폼도 단순 process 종료와 converged를 분리해야 한다. residual의 normalization과 preconditioning을 기록해 서로 다른 residual 값을 같은 수치처럼 비교하지 않는다.

## 5. 테스트와 debugging 근거

직접 확인한 파일:

- [Playwright config](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/web/playwright.config.ts): build/preview를 시작하고 headless browser test를 실행하는 설정.
- [validation README](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/examples/validation/README.md): real WASM engine과 bar, beam, torsion, plate-with-hole 등 reference 비교를 설명한다. README의 CI 설명은 이번 조사에서 CI 실행까지 검증한 사실이 아니다.
- [single-DOF regression test](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/examples/validation/dof-constraint.test.mjs): Ux만 구속한 node가 Uy/Uz에서도 잘못 고정되는 결함을 검출하도록 설계되어 있다.

single-DOF test는 대칭면별 component 구속으로 단축 인장 문제를 만들고, x면의 node가 y/z 방향으로 Poisson contraction을 하는지 확인한다. finite result 검사, 신장 오차, contraction의 부호와 오차 판정이 실제 코드에 있다. 이 test를 이번 작업에서 실행한 것은 아니다.

`useSolver.ts`에는 Playwright를 위해 solve를 직접 호출할 수 있는 test hook도 있다. 따라서 E2E라는 이름만으로 모든 실제 click 경로가 검증되었다고 가정하지 않는다. UI interaction, adapter contract, numerical verification을 별도 계층으로 둔다.

## 6. FreeCAD 1.1.4: source-guided 분석 출발점

이 조사에서는 CalculiX 경로를 살폈다. FreeCAD의 모든 workbench, solver 또는 legacy/new runner를 audit한 것은 아니다.

```text
FEM document objects / analysis settings
               |
  mesh sets + CalculiX input writer
               |
             .inp
               |
      external CalculiX process
               |
         .frd / .dat import
               |
       FreeCAD result objects
```

| 기능 | 공개 source 근거 | 확인 범위 |
| --- | --- | --- |
| input writer/units | [writer.py](https://github.com/FreeCAD/FreeCAD/blob/4fd3bf320d9566a27e60069fc8387448aaa3a094/src/Mod/Fem/femsolver/calculix/writer.py) | input 작성과 mm/N/s/K, t/mm3 등 unit convention 설명 |
| run/result import | [tasks.py](https://github.com/FreeCAD/FreeCAD/blob/4fd3bf320d9566a27e60069fc8387448aaa3a094/src/Mod/Fem/femsolver/calculix/tasks.py) | Check/Prepare/Solve/Results 단계, 외부 binary 실행, FRD/DAT import |
| linear/plastic material | [write_femelement_material.py](https://github.com/FreeCAD/FreeCAD/blob/4fd3bf320d9566a27e60069fc8387448aaa3a094/src/Mod/Fem/femsolver/calculix/write_femelement_material.py) | ELASTIC와 nonlinear material 설정에 따른 PLASTIC input 작성 |
| geometric nonlinearity | [write_step_equation.py](https://github.com/FreeCAD/FreeCAD/blob/4fd3bf320d9566a27e60069fc8387448aaa3a094/src/Mod/Fem/femsolver/calculix/write_step_equation.py) | static 등 설정에서 NLGEOM, increments와 time control 작성 |
| contact | [write_constraint_contact.py](https://github.com/FreeCAD/FreeCAD/blob/4fd3bf320d9566a27e60069fc8387448aaa3a094/src/Mod/Fem/femsolver/calculix/write_constraint_contact.py) | surface sets, surface-to-surface pair, normal behavior, optional friction input 작성 |

**중요:** writer에서 keyword를 생성하는 것과 nonlinear constitutive/contact algorithm 자체를 구현하는 것은 다른 일이다. FreeCAD를 분석하는 것만으로 external solver의 모든 내부 알고리즘이 밝혀지는 것은 아니다. solver 내부 구현은 해당 solver의 공개 source와 manual을 별도 revision으로 조사해야 한다.

다음 trace는 한 번에 하나의 변수만 바꾼다: material nonlinearity OFF/ON, geometric nonlinearity OFF/ON, contact pair 없음/있음. 각각 GUI 값, document property, `.inp` diff, solver version/log, physical response를 같은 case ID로 묶는다. 실행하지 않은 비교는 완료로 기록하지 않는다.

## 7. 다른 reference와 REA

[SunCAE README](https://github.com/seamplex/suncae/blob/main/README.md)는 browser frontend와 PHP backend가 JSON 요청을 교환하고 solver input/binary 실행/3D output을 처리하는 구조를 설명한다. Gmsh와 CalculiX/FeenoX integration을 열거하며 AGPL 계열이다. 이번에는 README만 확인했고 live app이나 backend code는 실행·audit하지 않았다. browser-only가 아닌 adapter architecture의 비교 대상으로 둔다.

[REA 공식 README](https://github.com/morluto/rea/blob/main/README.md)는 local MCP/CLI를 통해 binary/application/runtime evidence를 수집하는 도구라고 설명한다. upstream은 `morluto/rea`, `rea.tools`, `rea-agents` npm을 공식 경로로 안내한다. 이번 조사에서 REA를 설치하거나 실행하지 않았다.

FreeCAD처럼 source가 공개된 경우 source trace와 runtime 관찰부터 수행하고, source만으로 해결되지 않는 native boundary/호출 관계에 한해 REA를 선택적으로 적용한다. 자동 decompilation은 정확성이나 구현 완성을 보증하지 않는다. native provider 호환성, 설정 변경, dependency와 권한을 확인하기 전에 설치 script를 실행하지 않는다.

PhotoCraft의 [공식 README](https://github.com/storytold/photocraft)는 public specification/observed behavior 기반 clean-room 접근과 command registry를 설명하지만 early alpha와 단계적 parity도 명시한다. Photoshop의 모든 기능을 이미 재현한 증거로 사용하지 않는다. 이 문서는 PhotoCraft source의 독립 audit을 수행한 것이 아니다.

## 8. 남은 확인

- KoFEM release binary와 source hash 일치, local build/test 재현.
- camera/selection/mesh quality/remeshing/undo/state invalidation의 구체 구현과 실제 failure case.
- FreeCAD command/TaskPanel부터 document object까지의 연결 및 legacy/new runner 비교.
- CalculiX 내부 constitutive update/contact formulation과 지원 범위, version 고정.
- native build/worker exception/NaN/OOM/cancel/timeout의 실제 실패 재현.
- 라이선스별 배포 경계와 source/asset provenance review.
