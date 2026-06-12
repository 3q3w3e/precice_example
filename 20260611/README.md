# Turek-Hron FSI1/2/3 — SU2 + code_aster + preCICE

2D Turek-Hron FSI 벤치마크 (채널 내 실린더 + 탄성 깃발) 3 케이스.
유체 SU2(비압축 N-S) ↔ 고체 code_aster(탄성, 대변형) 를 preCICE 3.4.0
parallel-implicit + IQN-ILS 로 커플링.

---

## 1. 해결한 문제 (이전 실행에서 죽던 원인 2가지)

### (A) code_aster CPU 시간 한도 → `TimeLimitError`
- 기본 `tpmax = 86400초(24h)`. 그 90%(≈21.6h) 지점에서 잡이 우아하게 종료됨.
- 긴 FSI 시계열(t=15s)은 24h 안에 못 끝나 **21.6h마다 끊김**.

### (B) code_aster 메모리 한도 → `JEVEUX_62` / Segfault (exit 6/139)
- 기본 메모리 풀 4096MB(→ JEVEUX 가용 ~1103MB). FSI는 매 time-window의
  `DYNA_NON_LINE` 결과(EVOL_NOLI 시간이력)를 누적 → **t≈11s 부근에서 한도 도달**해
  메모리 할당 실패 후 Segfault.

### 고친 방법 — `solid/run_solid.py` 의 `CA.init()` 직전
이 code_aster 18.x 빌드는 `CA.init("--memory",...)`(argv)도
`set_option(...)`(init 후)도 **둘 다 무시**한다. 유일하게 먹는 경로는
**init 전에 `sys.argv` 를 직접 세팅**하는 것:

```python
import sys
sys.argv = [sys.argv[0], "--memory", "16384", "--tpmax", "2592000"]
CA.init()
```

- `--memory` 단위 = **MB**. 16384 요청 → 실할당 ~14.7GB (10%가 JEVEUX reserve로 빠짐).
  노드 RAM 62GB라 여유. 메모리 더 필요하면 숫자만 키우면 됨.
- `--tpmax` 단위 = **초**. 2592000 = 30일(reserve 빼고 ~27일). 사실상 무제한.
- 로그의 `Valeur initiale du temps CPU maximum = 86400` 줄은 init **시점** 출력이라
  계속 86400으로 찍히지만 무시. 실제 한도는 위 값으로 적용됨
  (`setting '--memory' value to 14745.60 MB` 줄이 적용 증거).

> 검증: `python3 -c "import sys; sys.argv=['x','--memory','16384','--tpmax','2592000']; from code_aster import CA; CA.init()"`
> → `setting '--memory' value to 14745.60 MB`, `allocation dynamique : 15257 Mo`

---

## 2. 파라미터 (Turek-Hron 표준)

| 케이스 | Ūbar | Re  | ρ_s    | E       | ν_s | dt      | mesh(유체) | SCHEMA      | 거동       |
|--------|------|-----|--------|---------|-----|---------|-----------|-------------|-----------|
| FSI1   | 0.2  | 20  | 1000   | 1.4e6   | 0.4 | 0.004   | coarse 8.5k| HHT α=-0.1  | 정상상태   |
| FSI2   | 1.0  | 100 | 10000  | 1.4e6   | 0.4 | 0.002   | coarse 8.5k| HHT α=-0.1  | 주기 진동  |
| FSI3   | 2.0  | 200 | 1000   | 5.6e6   | 0.4 | 0.0005  | fine 33k  | HHT α=-0.1  | 주기 진동  |

공통: 유체 ρ_f=1000, μ=1.0 (ν=1e-3); 채널 2.5×0.41; 실린더 D=0.1 at (0.2,0.2);
깃발 0.35×0.02. max-time=15s. E = 2·μ_s·(1+ν) (FSI1/2 μ_s=0.5e6, FSI3 μ_s=2.0e6).

- **Ūbar**: `fluid/inlet_00000.dat` 의 포물선 인렛 peak = 1.5·Ūbar.
- **ρ_s, E**: `solid/run_solid.py` 의 `E_MOD, NU, RHO = ...`.
- **SCHEMA**: HHT(α=-0.1)는 고주파 수치잡음만 감쇠(2차 정확도 유지) → FSI 안정.
  (Newmark γ=0.52는 인공 댐핑 + 1차 정확도라 지양.)

### 커플링 (precice-config.xml)
- parallel-implicit, IQN-ILS, max-iterations=50(FSI1/2)/100(FSI3 강화).
- 수렴: Displacement/Force 상대 2-norm < 5e-3.
- FSI3는 added-mass가 강해 IQN 강화(initial-relaxation 0.02, QR1 filter, history reset).

---

## 3. 실행

```bash
# 클러스터 (SGE) — fluid+solid 한 잡으로 동시 기동
qsub turek_hron1/job.sh
qsub turek_hron2/job.sh
qsub turek_hron3/job.sh
```

- 노드/코어 배치는 각 `fluid/run.sh`(FLUID_NODES, FLUID_CPU_LIST),
  `solid/run.sh`(SOLID_NODE, SOLID_CPU_SET) 에 박혀 있음. 실행 전 가용 노드로 조정.
- fluid·solid 를 따로 qsub하면 한쪽 큐 대기 시 preCICE initialize 데드락 → 반드시 job.sh로 같이.

### 출력
- `fluid/history.csv` : SU2 잔차 (CD/CL은 SCREEN 로그에만 — 별도 추출 필요).
- `fluid/*log.txt`    : 화면 테이블 (Inner_Iter, rms, CD, CL).
- `fluid/flow_*.vtu`, `surface_flow_*.vtu` : 유동장 (OUTPUT_WRT_FREQ 간격).
- `fluid/precice-Fluid-watchintegral-Total-Force.log` : 깃발 계면 force·변위 시계열.
- `solid/solid_*.med` : 고체 변형 (save_every 간격).
