# Web FEM 공개 구현 기획 초안

작성일: 2026-10-20
상태: **계획 및 공개 소스 조사. 이 문서 추가는 solver 기능 구현이 아니다.**

이 기획은 공개 프로젝트와 독립적인 합성 예제를 대상으로 한다. 기관의 공식 개발 계획을 대신하지 않는다. 비공개 문서, 녹음, 업무용 CAD, 미공개 알고리즘, 개인정보와 비밀 키를 포함하지 않는다. AI 지원으로 작성한 초안이며 구현과 기술적 결론에는 독립적인 검토가 필요하다.

- **[Codex 시작 페이지](CODEX_START_HERE.md)**
- [공개 소스 및 브라우저 조사 기록](REFERENCE_AUDIT.md)
- [실제 FreeCAD/CalculiX 실행 검증 결과](RUNTIME_RESULTS_20261020.md)
- [이미지 3,472개 카탈로그 및 독립 디자인 설계](ASSET_DESIGN_HANDOFF.md)
- [로컬 원본 증거 위치와 공개 범위](LOCAL_EVIDENCE_AND_LIMITS.md)
- [Codex 구현 인계와 acceptance gate](CODEX_HANDOFF.md)
- 기존 저장소의 [architecture](../ARCHITECTURE.md), [validation policy](../VALIDATION.md)는 유지한다.

## 1. 목표와 범위

FreeCAD의 화면을 소개하는 문서에서 끝내지 않고, 사용자 조작이 모델 데이터, solver 입력, 실제 계산, 결과 표시로 이어지는 경로를 분석한다. 이를 근거로 웹 기반 구조해석 플랫폼을 설계하고 단계적으로 구현한다.

| 목표 해석 | 첫 구현에서 제한할 범위 | 완료를 주장하기 전에 필요한 증거 |
| --- | --- | --- |
| Linear elasticity | 소변형, 등방성, 정적, 제한된 solid element | analytical/patch test, 반력과 residual, mesh convergence |
| Material nonlinearity | 먼저 small-strain J2 plasticity와 isotropic hardening | 단축 하중-제하, plastic strain/history, tangent 및 incremental convergence |
| Geometric nonlinearity | 명시한 finite-deformation formulation 하나 | rigid rotation/objectivity, small-load limit, 큰 변형 reference, 증분 수렴 |
| Contact nonlinearity | 먼저 frictionless normal contact, 제한된 surface pair | 접촉 전후, separation, reaction balance, gap/pressure와 penetration tolerance |

네 가지를 개별로 통과한 것과 네 가지의 임의 조합을 지원하는 것은 다르다. friction, self-contact, 모든 material law, 모든 element, 대규모 assembly, commercial solver와의 전면적 동등성은 초기 완료 범위가 아니다. Tie만으로 Contact가 구현되었다고 표시하지 않는다.

## 2. 두 종류의 구현을 구분한다

**A. 기능을 끝까지 사용하는 플랫폼 구현:** 웹 UI와 공통 모델에서 검증된 외부 solver를 호출하고 결과를 다시 가져온다. CalculiX adapter를 먼저 검토한다. 이 경우 재료·기하·접촉의 수치 알고리즘을 전부 자체 개발한 것으로 소개하지 않는다.

**B. 수치 알고리즘 자체 구현:** residual, tangent stiffness, constitutive update, contact search/enforcement를 직접 구현하거나 MFEM 위에서 구성한다. A와 동일한 독립 benchmark를 통과해야 한다. library가 있다는 이유로 비선형 기능이 자동 완성되는 것은 아니다.

권장 초기 방향은 A로 end-to-end 경로와 reference를 확보하고 B를 교체 가능한 backend로 확장하는 것이다. 이는 설계 제안이며 아직 선택·실행된 architecture가 아니다.

## 3. 제안 architecture

```text
Browser UI / optional CLI
          |
   shared command API
          |
Case model + units + stable entity IDs + revision
          |
   validation / adapter capability check
          |
          +-- Browser Worker --> WASM backend (supported small cases)
          |
          +-- Local/service job runner --> external solver adapter
          |
Results + provenance + explicit convergence status
          |
Viewer / plots / export / reproducibility report
```

웹 UI와 브라우저 내부 계산은 같은 뜻이 아니다. 복잡한 비선형 계산은 local/service runner로 먼저 연결할 수 있다. 브라우저 한정 실행이 반드시 필요한지는 별도 architecture decision으로 결정한다.

공통 명령은 모델 생성, 재료/BC/하중 추가, mesh, solve, cancel, result query, save/load를 담당하도록 설계한다. 클릭 이벤트와 자동화가 서로 다른 계산 경로를 만들지 않도록 한다. CLI/MCP 연결은 동일 명령 API가 안정화된 뒤 추가한다.

### 데이터 계약 초안

- `case_id`, `schema_version`, `model_revision`, `unit_system`, `geometry_hash`, `mesh_hash`, `solver_id`, `solver_version`, `solver_build_hash`를 기록한다.
- `nodes`: `(N, 3)`; element connectivity는 `tet4: (M4, 4)`, `tet10: (M10, 10)`처럼 topology별 분리. 첫 구현에서 지원하지 않는 element는 명시적으로 거절한다.
- 재료 ID와 속성은 body/element의 실제 연결 관계를 보존한다. 렌더링 순서와 solver node/element ID를 동일하다고 가정하지 않는다.
- CAD face, surface mesh, volume element face의 대응을 보존한다. 재메시 후 예전 triangle index로 BC를 다시 적용하지 않는다.
- Dirichlet 조건은 node와 component별 값이다. `Ux=0`을 `Ux=Uy=Uz=0`으로 바꾸지 않는다. nonzero prescribed displacement도 지원 여부를 구분한다.
- 결과 `U`: `(N,3)`. stress는 저장 위치(integration point/element/node), component order, averaging 정책을 메타데이터로 함께 제공한다. reaction은 constraint convention과 대상 DOF를 명시한다.
- solver 내부 unit system을 하나로 정하고 adapter 입출력에서만 명시적으로 변환한다. 화면의 mm/MPa와 내부 m/Pa가 다르면 모든 변환을 테스트한다.
- `success`, `nonconverged`, `failed`, `cancelled`를 구분한다. 파일 존재나 solver process 종료만으로 success를 선언하지 않는다.
- 모델 수정 시 기존 결과는 폐기하거나 `stale` 표시한다. preloaded result는 신규 실행 결과와 구분한다.

## 4. UI에서 우선 구현할 것

독립적인 디자인으로 Geometry, Materials/Sections, Constraints/Loads, Mesh, Solve, Results의 상태를 일관되게 보여 준다. 채택할 기능은 다음과 같다.

- 선택한 face와 적용된 BC/load가 tree와 viewport에서 함께 강조된다.
- 단위, load의 의미(total force 또는 traction), 적용 대상 수를 표시한다.
- 실행 전 readiness와 unsupported capability를 구분해 설명한다.
- 실행 중 stage, increment, iteration, residual 종류/정의, 경과 시간과 오류를 표시한다.
- displacement/stress field, 단위, 범례 범위, deformation scale, undeformed overlay를 제공한다.
- `Solver`, `Output`, `Converged` 표시는 고정 문구가 아니라 실제 실행 metadata에서 생성한다.
- 큰 numeric array는 반복적인 UI 상태 복사를 피하고 worker/buffer 경계를 명확히 한다.

이는 요구사항이다. 현재 FEMlab이 위 UI를 이미 제공한다는 의미가 아니다.

## 5. 공개와 라이선스

현재 FEMlab의 original code license는 MIT다. 이 변경은 original planning prose만 추가한다. KoFEM, FreeCAD, PhotoCraft, SunCAE의 소스·asset·binary를 복사하거나 기존 라이선스를 변경하지 않는다.

KoFEM은 AGPL-3.0-or-later이다. 소스 재사용이 필요하면 기존 MIT 코드와의 배포 관계, upstream notice, corresponding source 제공, 의존 라이선스를 먼저 검토한다. public repo라는 사실 자체가 준수 완료를 뜻하지 않는다. 별도 AGPL integration/fork가 필요한지는 구현 전에 결정한다. 단순 파일명 변경이나 언어 변환을 독립 구현의 증거로 삼지 않는다.

FreeCAD의 이번 조사 대상 파일들은 LGPL 계열 header를 갖는다. 프로젝트 전체의 모든 파일과 dependency가 같은 조건이라고 추정하지 말고 실제 재사용 파일별로 기록한다. source-guided 분석과 clean-room 구현은 구분한다. 원본 소스를 분석한 뒤 source-unseen clean-room이라고 홍보하지 않는다.

Public portfolio에는 직접 작성한 코드, 공개 입력의 재현 가능한 결과, 출처와 기여 범위, 실패·한계 기록을 올린다. 공개 권한이 확실하지 않은 산출물은 제외한다. private 전환은 이미 만들어진 public fork/local clone 회수 수단이 아니다.

관련 1차 자료: [KoFEM README](https://github.com/mkofler96/KoFEM/blob/b0cae453d6eaac23bd7382c9b9f7a6b7812f311f/README.md), [GNU AGPL](https://www.gnu.org/licenses/agpl-3.0.html), [GitHub visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility). 실제 제품 배포 조건은 별도로 검토한다.

## 6. 다음 결정

1. KoFEM 코드를 재사용하는 별도 AGPL integration과 독립 UI 구현 중 어느 경로를 선택할지 결정한다.
2. FreeCAD 설정 하나를 바꿀 때 생성 `.inp`가 어떻게 바뀌는지, 동일 입력을 solver가 어떻게 읽는지 trace한다.
3. 공통 case/result schema와 첫 numerical fixture부터 구현한다.
4. 각 기능은 source 확인, local 실행, numerical verification, CI를 구분해 기록한다. 네 해석 지원은 해당 acceptance gate를 실제 통과한 범위에서만 표시한다.
