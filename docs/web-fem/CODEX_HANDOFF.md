# Codex 구현 인계: Web FEM

상태: 계획. 이 파일은 구현 완료, numerical validation 또는 CI 통과 보고가 아니다.

## 작업 원칙

루트 `AGENTS.md`, `README.md`, `docs/ARCHITECTURE.md`, `docs/VALIDATION.md`, 이 디렉터리의 `README.md`와 `REFERENCE_AUDIT.md`를 먼저 읽는다. 기존 Python numerical package와 `web/` 내용을 확인한 뒤 새 application 위치를 정한다. 기존 dashboard나 public API를 무단으로 대체하지 않는다.

이 문서는 공개 reference와 합성 예제만 사용한다. 비공개 첨부자료를 가져오지 않는다. 연구기관의 공식 project라는 표현, 독립적으로 확인하지 않은 benchmark 수치, 실제로 실행하지 않은 성공 로그를 작성하지 않는다.

현재 FEMlab license는 MIT다. KoFEM의 AGPL source/asset/WASM을 이 저장소에 곧바로 복사하지 않는다. 재사용 경로, 별도 integration repository, notices와 source 제공 방식을 먼저 명시하고 승인받는다. upstream source를 본 뒤 clean-room/source-unseen이라고 표시하지 않는다.

## 0단계: 구현 전 확인

1. source revision, license, reference URL, 실제 열람 파일을 evidence manifest에 기록한다.
2. 이 저장소의 현재 tests/benchmarks를 local에서 실행해 baseline을 남긴다. 실패하면 먼저 보고하고 기존 결과를 새 실행 결과처럼 재사용하지 않는다.
3. 요구사항을 `planned`, `implemented`, `locally_verified`, `ci_verified`로 구분한다. GUI가 있어도 solver adapter가 없으면 기능 완료가 아니다.
4. framework/backend 선택은 architecture decision으로 기록한다. browser-only와 local/service runner를 구분한다.

## 첫 구현 단위

전체 FreeCAD clone을 한 번에 생성하지 않는다. **case schema → validation → 실제 linear solve → 결과 schema → viewer → save/load → regression test** 한 경로를 우선 완성한다.

첫 fixture는 독립적으로 만든 1D axial bar다. 이는 데이터와 unit/BC 계약을 검증하는 최소 fixture이며 3D solid 지원 완료를 의미하지 않는다.

- L = 100 mm
- A = 100 mm^2
- E = 210000 N/mm^2
- P = +1000 N
- x=0에서 Ux=0, 반대쪽에 +x force
- analytical tip displacement: P L / (E A) = 0.0047619047619 mm
- 외력에 대응하는 고정단 반력: -1000 N

위 값은 analytical expected value다. 신규 solver 실행 결과가 아니다. 이후 3D constant-strain patch와 cantilever를 추가한다. 3D face 전체를 완전 고정하면 Poisson constraint 때문에 단순 1D 해와 정확히 일치하지 않을 수 있으므로 비교 경계조건을 먼저 설계한다.

## 해석별 acceptance gate

### Linear elasticity

- rigid-body translation에서 strain/internal elastic energy가 영이 되는 formulation test.
- affine patch, nonzero prescribed displacement, component-wise BC test.
- force/reaction balance와 free-DOF residual; 의미 있는 reference와 conditioning 기록.
- coarse/medium/fine mesh 비교. singular support를 임의 regularization으로 숨기지 않는다.

### Material nonlinearity

- 먼저 small-strain J2 + isotropic hardening만 구현 범위로 지정.
- material-point 단축 loading/unloading에서 yield, hardening, plastic strain, unloading slope와 history variable을 비교.
- constitutive update 실패 시 이전 increment의 state를 복구하고 실패를 반환.
- tangent consistency는 smooth branch에서 finite-difference 방향미분으로 검사. yield transition의 비미분성은 별도로 다룬다.
- full model에서도 load increment refinement와 반력/평형을 검사.

### Geometric nonlinearity

- formulation, strain/stress measure, configuration, load direction(fixed/follower)을 먼저 명시.
- finite rigid rotation에서 spurious strain/stress가 없는지 검사.
- small-load limit가 linear 결과로 접근하는지 검사.
- 큰 변형 reference는 적절한 elastica/검증된 nonlinear reference를 사용. 작은 처짐 공식을 큰 변형 정답으로 사용하지 않는다.
- Newton convergence, load stepping, cutback과 rollback을 기록.

### Contact nonlinearity

- frictionless, 지정 surface pair부터 시작. Tie와 구분.
- gap이 있는 두 물체의 접촉 전/후 및 재분리 fixture.
- compressive-positive pressure convention을 문서화. ideal unilateral contact의 gap/pressure/complementarity를 검사하고 penalty 방식의 허용 penetration을 따로 정의.
- contact reaction balance, active-set 변화, mesh/penalty sensitivity를 기록.
- penalty stiffness를 무조건 크게 만들어 결과를 맞추지 않는다.
- friction, self-contact, arbitrary large sliding은 독립 gate 없이 지원한다고 표시하지 않는다.

개별 gate 후에 material + geometry, geometry + contact 등 조합 test를 추가한다. nonlinear tangent가 항상 symmetric positive definite라고 가정해 CG를 무조건 사용하지 않는다.

## UI / runner / result 계약

- 실제 solver 선택, version, element order, requested/available outputs에서 화면 label을 생성한다.
- surface traction과 total force를 구분하며 면적 변경 시 resultant가 어떻게 변하는지 검증한다.
- model revision을 바꾸면 기존 result가 stale임을 표시한다.
- state는 idle/checking/meshing/solving/succeeded/nonconverged/failed/cancelled 등으로 관리한다.
- local runner는 unique run directory, 명시한 executable, 인자 배열, exit code, stdout/stderr, timeout, cancellation, 파일 freshness/hash를 검사한다. 사용자 입력을 shell command에 직접 연결하지 않는다.
- backend가 지원하지 않는 요청은 명시적으로 거절한다. mock result나 하드코딩된 contour로 대체하지 않는다.
- 결과는 units, node/element ID mapping, stress 위치/averaging, deformation scale, run ID와 solver hash를 보존한다.
- `success`와 numerical verification을 별도로 표시한다. process exit 0, result file 존재, contour 표시만으로 정확성을 선언하지 않는다.

## 테스트 계층

1. Unit: units, entity mapping, serialization, result invalidation, solver capability 검사.
2. Contract: case → solver input → parsed result의 round trip. 실제 keyword diff와 orientation/DOF mapping 검사.
3. Numerical: analytical solution, patch/invariance, reference curve, convergence.
4. UI E2E: 실제 버튼/face selection 경로를 조작. test hook을 사용한 것은 그 사실을 별도로 기록.
5. Failure path: 누락 재료, 자유 강체, 잘못된 mesh, NaN, nonconvergence, cancellation, stale result, worker crash.

실패 artifact는 최소 입력, version/hash, logs, 재현 command, 기대값/실제값, 환경 정보로 구성한다. screenshot은 보조 증거이며 수치 비교의 대체물이 아니다.

## 단계별 PR 제안

| PR | 범위 | 완료 조건 |
| --- | --- | --- |
| P0 | public evidence/architecture/license decision | source와 관찰/추론/미확인 구분 |
| P1 | case/result schema + analytical fixture | units/BC/serialization tests |
| P2 | 실제 linear vertical slice | 계산-표시-저장-재로딩 + numerical gates |
| P3 | external solver adapter | 실제 실행 provenance와 실패 처리, 현재 지원 기능 명시 |
| P4 | 제한된 Contact workflow | contact 전후/separation test, Tie 대체 금지 |
| P5 | 제한된 Material/Geometry workflow | 각 nonlinear gate와 incremental convergence |
| P6 | 조합 해석과 공개 demo | 조합별 회귀 test, 출처/한계/실제 결과 공개 |

P3 이후에도 external solver 기능을 adapter로 노출한 것과 수치 kernel을 자체 개발한 것을 구분한다. MFEM 기반 자체 kernel은 같은 gate를 통과할 때만 기존 backend를 대체한다.

## 각 작업의 보고 형식

- 변경한 파일과 선택 이유.
- 실제 실행한 command와 environment.
- 실제 pass/fail/skip 수. 실행하지 않은 test는 `not run`.
- 비교 fixture의 입력, expected/observed 값, tolerance 선택 이유.
- 새로 확인한 제한과 다음 재현 가능한 작업.

비용이 드는 cloud job, 배포, 패키지 publication, 외부 model upload는 별도 승인 없이 수행하지 않는다. background agent를 시작했다고 허위로 보고하거나 후속 실행을 약속하지 않는다.
