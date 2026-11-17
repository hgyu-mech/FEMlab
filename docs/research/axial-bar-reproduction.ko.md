# 축 인장봉 교차 검증

2026-11-17에 같은 이상화 물리 문제를 FEMlab의 1D 봉과 독립적인 CalculiX 2.22의 3D 육면체에서 풀었다. 한 케이스의 선형 정적 검증 기록이다.

## 문제와 기준해

길이 100 mm, 단면 10×10 mm, $E=70{,}000$ MPa, $\nu=0$. 왼쪽 면을 고정하고 오른쪽 면에 +x 방향 합력 1,000 N을 가한다. 3D 입력 덱에서 한 개 C3D8 요소의 오른쪽 네 정점에 각각 250 N을 배분한다. 횡변형이 없는 균일 축응력 문제다.

$$
u_x(L)=\frac{FL}{EA}=0.0142857142857143\ {\mathrm{mm}},\qquad
\sigma_{xx}=\frac{F}{A}=10\ {\mathrm{MPa}},\qquad
R_x=-F=-1000\ {\mathrm{N}}.
$$

## 직접 계산한 결과

| 경로 | 끝단 변위 (mm) | 고정단 축반력 (N) | 축응력 (MPa) |
|---|---:|---:|---:|
| 해석해 | 0.0142857142857143 | −1,000 | 10 |
| FEMlab 1D, `bar_stiffness` + `solve_static` | 0.0142857142857143 | −1,000 | 변위에서 평가하면 10 |
| CalculiX 2.22, 3D C3D8 `.dat` | 0.01428571, 끝단 네 점 | −1,000, 고정면 합 | 10, 적분점 8개 |

CalculiX는 종료코드 0과 `Job finished`를 기록했다. `.dat`에 표시된 변위를 해석해와 비교하면 상대 차이는 $3.0\times10^{-7}$이다. 텍스트 출력의 반올림을 포함한 차이다. 서로 다른 차원에서 동일한 균일 축장 문제를 검증한 결과이며 다른 하중·포아송비·요소와 시간적분의 정확도는 별도 계측 대상이다.

## 다시 실행하기

저장소 루트에서 Python 3.12 이상과 NumPy로 실행한다.

```python
from femlab.core import solve_static
from femlab.fem import bar_stiffness

r = solve_static(bar_stiffness(70000.0, 100.0, 100.0), [0.0, 1000.0], {0: 0.0})
print(r.displacement[1], r.reaction[0], 70000.0 * r.displacement[1] / 100.0)
```

별도 작업 디렉터리에 [입력 덱](../../examples/benchmarks/axial_bar_3d.inp)을 복사한다. 설치된 CalculiX 실행기를 작업 디렉터리에서 `ccx -i axial_bar_3d` 형태로 호출하고 `axial_bar_3d.dat`의 `LOADED` 변위, `FIXED` 합력, `BAR` 적분점 응력을 읽는다. 번들에서 실행 파일 이름이 다르면 실제 경로를 사용한다. [CalculiX 공식 자료](https://www.dhondt.de/)
