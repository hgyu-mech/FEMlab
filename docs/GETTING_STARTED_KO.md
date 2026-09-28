# FEMlab 시작 가이드

이 저장소는 ML-assisted computational mechanics 연구를 위한 초기 기준 구현입니다.
실행되는 작은 솔버와 연구 확장 계약을 함께 담았지만, 상용 해석기를 이미 대체하거나
모든 연구실 자료를 코드로 이식한 프로그램은 아닙니다.

## 실행

저장소를 내려받은 폴더에서 실행하세요. Windows PowerShell 기준입니다.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
python -m femlab.benchmarks --output outputs/verification.json
python examples/mpm_translation.py
```

가상환경 활성화가 시스템 정책으로 차단되면 정책을 바꾸지 않고 다음처럼 실행할 수 있습니다.

```powershell
.venv\Scripts\python.exe -m pip install -e ".[dev,ml]"
.venv\Scripts\python.exe examples/train_gnn.py
```

`train_gnn.py`는 작은 FEM 문제에서 데이터를 생성하고 실제로 GNN을 학습합니다.
API 결제나 Abaqus 설치는 필요하지 않습니다. 결과는 `outputs/`에 생기며 기본적으로
Git 추적 대상에서 제외됩니다. 초기 예제는 CSV/JSON을 출력하며 GUI는 없습니다.

## 무엇부터 읽을까

`fem.py`의 보 요소와 `tests/test_fem.py`의 해석해 비교부터 보세요.
그다음 `mpm.py`에서 입자 상태가 격자로 전달되고 다시 입자로 돌아오는 흐름을 확인하고,
`examples/train_gnn.py`에서 물리 데이터와 학습 코드를 연결하세요.
`optimization.py`는 해석 결과를 설계변수의 목적함수와 민감도로 바꾸는 예제입니다.

FEM, MPM, meshfree는 서로 같은 방법이 아닙니다. 현재 MLS는 근사함수 값 계산,
RBF-FD는 1D Poisson 해석, MPM은 배경 격자를 사용하는 2D 입자 해석으로 구분했습니다.
ML이 숫자를 잘 맞혀도 시간 적분에서 에너지나 운동량이 나빠질 수 있으므로,
예측오차와 실제 해석 경로의 물리 오차를 별도로 확인해야 합니다.

## 실제 구현과 계획 구분

실제 구현 목록은 README 표를, 앞으로 할 일은 ROADMAP.md를 보세요.
3D MPM, 정확한 접촉, GIMP/CPDI/MLS-MPM, 비선형 대규모 FEM, SPH, peridynamics,
학습 구적법, 형상최적화, 유체-구조 연성, GPU 가속은 현재 완성된 기능이 아닙니다.
Abaqus/Ansys 어댑터도 실행 계약만 있고 실제 상용 솔버를 호출하지 않습니다.

기존 선배들의 보고서나 논문은 공개 저장소에 복사하지 않았습니다. 새 코드의 검증 결과와
참고 문헌, 미구현 목록을 분리해서 기록하며 실제 작업한 날짜의 커밋만 남깁니다.
