#!/usr/bin/env python3
# coding=utf-8
"""
run_solid.py — preCICE "Solid" participant  (Code_Aster, 2D C_PLAN, OMP-only)

wall&ramm FSI 벤치마크의 구조(Solid) 쪽.
  유체(SU2, wall&ramm_fluid) 가 보내는 계면 힘 Force 를 받아
  비선형 동역학 DYNA_NON_LINE 으로 풀고,
  계면 변위 Displacement 를 유체에 돌려준다.

coupling = parallel-implicit  (../precice-config.xml):
  한 time window 안에서 force <-> displacement 가 수렴할 때까지 preCICE 가
  coupling iteration 을 반복시킨다. 수렴 못 하면 window 시작 상태로 rollback.
  => 매 iteration 은 "checkpoint(=window 시작) 상태에서 새로" 풀어야 한다.
     그래서 DYNA_NON_LINE 에 reuse 를 쓰지 않고 항상 새 result 를 만든다.

병렬: MPI 1 rank + OpenMP  (preCICE rank=0, size=1).  MPI gather/scatter 없음.

실행:  ./run_local.sh   (유체 케이스와 동시에, 두 번째 터미널에서)
       run_aster/job.export 가 아니라 plain python3 로 실행 — 이유는 run_local.sh 참고.
"""

import os
from pathlib import Path
from datetime import datetime

import numpy as np
import precice

import sys
from code_aster import CA
from code_aster.Commands import *

import solid_checkpoint as sc   # 검증된 restart 체크포인트 I/O (harness 와 공유)

# ============ 경로 / 이름 상수 ============
CASE_DIR = Path(__file__).resolve().parent
os.chdir(CASE_DIR)                       # preCICE 가 ../ 상대경로를 쓰므로 cwd 고정

PRECICE_CONFIG = os.environ.get("PRECICE_CONFIG", "../precice-config.xml")
PARTICIPANT    = "Solid"                 # config 의 <participant name=...>
MESH_NAME      = "Solid-Mesh"            # config 의 <mesh name=...>
READ_DATA      = "Force"                 # 유체 -> 구조
WRITE_DATA     = "Displacement"          # 구조 -> 유체
DIM            = 2
ZERO_FORCE_TOL = 1.0e-12                 # |force| 가 이 값 이하면 0 으로 간주 (첫 step skip 판정용)

MESH_FILE   = os.environ.get("MESH_FILE",   "beam.med")
RESULT_FILE = os.environ.get("RESULT_FILE", "run_solid_result.med")   # 전체결과 저장용

# ---- restart (런 연장) — 자세한 동작/근거는 solid_checkpoint.py ----
RESTART_DIR     = Path(os.environ.get("SOLID_RESTART_DIR", str(CASE_DIR.parent / "restart")))  # 케이스 루트 공유 dir
MANIFEST_FILE   = RESTART_DIR / "solid_manifest.json"
CHECKPOINT_FILE = RESTART_DIR / "solid_ckpt.med"
DO_RESTART      = os.environ.get("SOLID_RESTART", "0") == "1"   # 1 = manifest 에서 재개
CKPT_EVERY      = int(os.environ.get("SOLID_CKPT_EVERY", "25")) # N window 마다 최신 1개 저장(0=off)
# perturbation A: fresh start 시 tip 횡속도(m/s). clamp→tip 선형 ramp, DEPL=0.
PERTURB_VEL     = float(os.environ.get("SOLID_PERTURB_VEL", "0"))  # 0 = 자극 없음


VOLUME_GMA = "beam"          # 2D 면 요소 그룹
IFACE_GMA  = "beam_wet"      # FSI 계면 (1D edge 그룹)
CLAMP_GMA  = "beam_fixed"    # 고정단 (1D edge 그룹)
IFACE_GNO  = "beam_wet_no"   # IFACE_GMA 로부터 만들 node 그룹

E_MOD, NU, RHO = 1.4e6, 0.40, 1.0e4      # solid.py 와 동일

MESH_UNIT, RESULT_UNIT = 20, 80          # Code_Aster fortran 파일 단위
COMP = ("DX", "DY")

# ============ Code_Aster 초기화 ============
# code_aster 메모리/CPU시간 한도 — 이 빌드는 CA.init(argv)/set_option 둘 다
# 무시하므로, init 전에 sys.argv 를 직접 세팅해야만 실제 풀에 반영된다.
#   --memory: MB (실할당은 10%가 JEVEUX reserve로 빠져 ~90%)
#   --tpmax : 초 (경과시간 한도). 둘 다 안 키우면 t≈11s에서 메모리 Segfault.
sys.argv = [sys.argv[0], "--memory", "16384", "--tpmax", "2592000"]
CA.init()

print("=" * 62)
print("  run_solid.py — preCICE Solid participant (Code_Aster, 2D)")
print(f"  config = {PRECICE_CONFIG}")
print(f"  mesh   = {MESH_FILE}")
print(f"  OMP_NUM_THREADS = {os.environ.get('OMP_NUM_THREADS', '?')}")
print("=" * 62, flush=True)

# ============ 메쉬 / 모델 / 재료 / 경계조건 ============
DEFI_FICHIER(ACTION="ASSOCIER", UNITE=MESH_UNIT, TYPE="BINARY",
             ACCES="OLD", FICHIER=str(CASE_DIR / MESH_FILE))
mesh = LIRE_MAILLAGE(UNITE=MESH_UNIT, FORMAT="MED", VERI_MAIL=_F(VERIF="OUI"))

# 계면 edge 그룹(move_strc) 의 절점들을 모은 node 그룹 생성
mesh = DEFI_GROUP(reuse=mesh, MAILLAGE=mesh,
                  CREA_GROUP_NO=_F(NOM=IFACE_GNO, GROUP_MA=IFACE_GMA))

# 2D plane-stress 모델은 면 그룹(SOLID) 에만 건다. edge 그룹은 BC/계면 노드
# 용도라 모델 요소가 필요 없다 (계면 힘은 VECT_ASSE 로 절점에 직접 가한다).
model = AFFE_MODELE(MAILLAGE=mesh,
    AFFE=_F(GROUP_MA=VOLUME_GMA, PHENOMENE="MECANIQUE", MODELISATION="C_PLAN"))

mat  = DEFI_MATERIAU(ELAS=_F(E=E_MOD, NU=NU, RHO=RHO))
fmat = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA=VOLUME_GMA, MATER=mat))

# 고정단: nomove_strc 절점의 DX, DY 구속
fix = AFFE_CHAR_MECA(MODELE=model,
                     DDL_IMPO=_F(GROUP_MA=CLAMP_GMA, DX=0.0, DY=0.0))

# ============ 계면 노드 추출 (preCICE 에 줄 좌표) ============
#getnodes로 절점을 가져옴 
iface_nodes = np.asarray(mesh.getNodes(IFACE_GNO, localNumbering=True),
                         dtype=np.int64)
n_iface = iface_nodes.size
if n_iface == 0:
    raise RuntimeError(f"계면 노드 그룹 '{IFACE_GNO}' 가 비어있음")

_coord = mesh.getCoordinatesAsSimpleFieldOnNodes()
_cvals, _ = _coord.getValues(copy=True)
_cc = list(_coord.getComponents())
iface_coords = np.column_stack([_cvals[iface_nodes, _cc.index("X")],
                                _cvals[iface_nodes, _cc.index("Y")]]).astype(np.float64)
print(f"[Solid] 계면 노드 {n_iface} 개", flush=True)


# ============ 헬퍼 ============
def build_force_load(forces):
    """preCICE 계면 절점 힘 (n_iface, 2) -> Code_Aster 하중(AFFE_CHAR_MECA)."""
    f = CA.SimpleFieldOnNodesReal(mesh, "DEPL_R", COMP, True)
    f.setValues(0.0)
    nodes = np.repeat(iface_nodes, DIM)
    cps   = np.tile(np.asarray(COMP, dtype=object), n_iface)
    f.setValues([int(x) for x in nodes],
                [str(x) for x in cps],
                [float(x) for x in np.asarray(forces, np.float64).ravel()])
    return AFFE_CHAR_MECA(MODELE=model, VECT_ASSE=f.toFieldOnNodes())


def solve_window(forces, prev_result, t0, t1, init_vite=None):
    """[t0, t1] 한 window 를 prev_result 상태에서 출발해 푼다.

    매 coupling iteration 마다 새로 호출된다. reuse 를 쓰지 않고 항상 새
    result 를 만든다 -> rollback 시 trial 만 버리면 prev_result 는 보존된다.

    init_vite: fresh 첫 window 에서 줄 초기 속도장(perturbation A). DEPL/ACCE 는
    0 (펴진 모양 그대로 시작), VITE 만 임펄스로 줘서 동역학적으로 자극한다.
    """
    load  = build_force_load(forces)
    tlist = DEFI_LIST_REEL(VALE=(t0, t1))
    kw = dict(
        MODELE=model, CHAM_MATER=fmat,
        EXCIT=(_F(CHARGE=fix), _F(CHARGE=load)),
        COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
        INCREMENT=_F(LIST_INST=tlist),
        SCHEMA_TEMPS=_F(SCHEMA="HHT", FORMULATION="DEPLACEMENT",
                        ALPHA=-0.1),
        NEWTON=_F(MATRICE="TANGENTE", REAC_ITER=1),
        SOLVEUR=_F(METHODE="MUMPS"),
        CONVERGENCE=_F(ITER_GLOB_MAXI=80,
                       RESI_GLOB_RELA=1.0e-6, RESI_GLOB_MAXI=1.0e-9),
    )
    if prev_result is not None:
        kw["ETAT_INIT"] = _F(EVOL_NOLI=prev_result)
    elif init_vite is not None:
        kw["ETAT_INIT"] = _F(VITE=init_vite)      # perturbation: 초기 속도만
    return DYNA_NON_LINE(**kw)


def interface_displacements(result, t):
    """result 의 시각 t 변위장에서 계면 노드 변위 (n_iface, 2) 추출."""
    field = None
    for para, val in (("INST", float(t)), ("NUME_ORDRE", 2), ("NUME_ORDRE", 1)):
        try:
            field = result.getField("DEPL", value=val, para=para).toSimpleFieldOnNodes()
            break
        except Exception:
            continue
    if field is None:
        raise RuntimeError("변위장 추출 실패")
    vals, _ = field.getValues(copy=True)
    cc = list(field.getComponents())
    return np.column_stack([vals[iface_nodes, cc.index("DX")],
                            vals[iface_nodes, cc.index("DY")]]).astype(np.float64)


def write_window_med(result, step, t, save_every=40):                       # ← t 인자 추가
    """수렴 완료된 window 결과를 독립 .med 로 저장 (solid_NNNN.med).
    끝 시각 t 한 프레임만, 안정된 MED 필드명 'DEPL' 로 기록 — stitch 용."""
    if step % save_every !=0:
      return
    out = CASE_DIR / f"solid_{step:04d}.med"
    if out.exists():
        out.unlink()
    DEFI_FICHIER(ACTION="ASSOCIER", UNITE=RESULT_UNIT, TYPE="BINARY",
                 ACCES="NEW", FICHIER=str(out))
    try:
        IMPR_RESU(FORMAT="MED", UNITE=RESULT_UNIT,
                  RESU=_F(RESULTAT=result, NOM_CHAM=("DEPL",),
                          NOM_CHAM_MED=("DEPL",),                       # ← 필드명 고정
                          INST=(float(t),),                            # ← 끝 프레임만
                          CRITERE="RELATIF", PRECISION=1.0e-6))
    finally:
        DEFI_FICHIER(ACTION="LIBERER", UNITE=RESULT_UNIT)
def stitch_med_series(pattern="solid_*.med", output_name=RESULT_FILE): #이부분 살짞 이해가 안감 medcoupling사용이라는데
    """window별 solid_NNNN.med 들을 하나의 시계열 med 로 병합 (medcoupling).
    best-effort — 실패해도 개별 .med 는 그대로 남는다."""
    files = sorted(CASE_DIR.glob(pattern))
    if not files:
        print(f"[Solid] stitch: {pattern} 매칭 없음", flush=True)
        return
    try:
        import medcoupling as mc
    except Exception as exc:
        print(f"[Solid] stitch: medcoupling 없음 ({exc}) — 개별 파일 유지", flush=True)
        return

    first = mc.MEDFileData.New(str(files[0]))
    field_names = list(first.getFields().getFieldsNames())
    if not field_names:
        print("[Solid] stitch: 첫 파일에 필드 없음", flush=True)
        return

    merged = mc.MEDFileData.New()
    merged.setMeshes(first.getMeshes())
    merged_fields = mc.MEDFileFields()
    for fname in field_names:
        mts = mc.MEDFileFieldMultiTS()
        new_iter = 0
        for path in files:
            src = mc.MEDFileData.New(str(path)).getFields().getFieldWithName(fname)
            for it_pair in src.getIterations():
                f1ts = src.getTimeStep(it_pair[0], it_pair[1])
                t_phys = f1ts.getTime()[2]
                new_iter += 1
                f1ts.setTime(new_iter, 0, t_phys)     # 시간태그 재부여 -> 충돌 방지
                mts.pushBackTimeStep(f1ts)
        merged_fields.pushField(mts)
    merged.setFields(merged_fields)

    out = CASE_DIR / output_name
    if out.exists():
        out.unlink()
    merged.write(str(out), 0)
    print(f"[Solid] stitch: {out.name} 생성 ({len(files)}개 병합)", flush=True)







# ============ preCICE participant ============
participant = precice.Participant(PARTICIPANT, PRECICE_CONFIG, 0, 1)   # rank 0 / size 1

if participant.get_mesh_dimensions(MESH_NAME) != DIM:
    raise RuntimeError(f"'{MESH_NAME}' 차원 불일치")

# 계면 좌표를 preCICE 에 등록. vertex_ids[i] <-> iface_nodes[i] (순서 1:1 대응)
vertex_ids = participant.set_mesh_vertices(MESH_NAME, iface_coords)

# ============ restart 복원 (런 연장) — 초기 데이터 교환 전에 먼저 ============
# initialize() 전에 복원해야 requires_initial_data 에서 t_R 의 계면 변위를 유체에 줄 수
# 있다. 안 그러면 유체가 첫 window 에 disp=0 을 받아 메시를 reference 로 되돌리는데,
# restart flow 는 변형상태라 불일치로 발산한다(NaN). 5필드 체크포인트(DEPL/VITE/ACCE/
# SIEF_ELGA/VARI_ELGA)를 EVOL_NOLI 로 되살려 기존 ETAT_INIT=_F(EVOL_NOLI=...) 경로로 잇는다.
RESTART_DIR.mkdir(parents=True, exist_ok=True)
if DO_RESTART:
    _man = sc.read_manifest(MANIFEST_FILE)
    if _man is None:
        raise RuntimeError(f"SOLID_RESTART=1 이지만 manifest 가 없음: {MANIFEST_FILE}")
    result = sc.load_checkpoint(_man["solid_checkpoint"], model, fmat)
    t    = float(_man["t"])
    step = int(_man["step"])
    print(f"[Solid] RESTART: window {step}, t={t:.4f}s 에서 재개 "
          f"(ckpt={Path(_man['solid_checkpoint']).name})", flush=True)
else:
    result, t, step = None, 0.0, 0   # 현재까지 수렴된 상태 / 시각 / 완료 window 수

# ============ perturbation A: 초기 횡속도 임펄스 (fresh only) ============
# DEPL=0(펴진 모양) 그대로 두고 VITE 만 준다. clamp(x_min)에서 0, tip(x_max)에서 최대인
# 선형 ramp -> 캔틸레버 1차 모드 비슷한 자연스러운 자극. 대칭을 깨 self-excited 진동을 촉발.
vite_init = None
if PERTURB_VEL != 0.0 and not DO_RESTART:
    _cf = mesh.getCoordinatesAsSimpleFieldOnNodes()
    _cv, _ = _cf.getValues(copy=True)
    _cc = list(_cf.getComponents())
    _x = _cv[:, _cc.index("X")]
    _xmin, _xmax = float(_x.min()), float(_x.max())
    _ramp = (_x - _xmin) / (_xmax - _xmin) if _xmax > _xmin else np.zeros_like(_x)
    _nn = _x.size
    _vf = CA.SimpleFieldOnNodesReal(mesh, "DEPL_R", COMP, True)
    _vf.setValues(0.0)
    _nodes = np.repeat(np.arange(_nn), DIM)
    _cps = np.tile(np.asarray(COMP, dtype=object), _nn)
    _vel = np.zeros((_nn, DIM), dtype=np.float64)
    _vel[:, 1] = PERTURB_VEL * _ramp                       # DY 횡속도만
    _vf.setValues([int(i) for i in _nodes], [str(c) for c in _cps],
                  [float(v) for v in _vel.ravel()])
    vite_init = _vf.toFieldOnNodes()
    print(f"[Solid] PERTURB A: 초기 횡속도 tip DY={PERTURB_VEL:.3e} m/s "
          f"(x {_xmin:.3f}→{_xmax:.3f} 선형 ramp, DEPL=0)", flush=True)

# 초기 데이터(Displacement exchange 의 initialize="true"): restart 면 t_R 의 계면 변위를,
# fresh 면 0 을 보낸다. 이게 유체 메시를 restart flow 의 변형위치와 정합시킨다.
if participant.requires_initial_data():
    if DO_RESTART and result is not None:
        disp0 = interface_displacements(result, t)
    else:
        disp0 = np.zeros((n_iface, DIM), dtype=np.float64)
    participant.write_data(MESH_NAME, WRITE_DATA, vertex_ids, disp0)

participant.initialize()  # max_timestep을 반환함

# ============ implicit coupling 루프 ============
result_ckp, t_ckp = result, t     # checkpoint = 현재 window 시작점 (restart 시 t_R)
t_start = datetime.now()
finalized = False

print("[Solid] coupling 시작", flush=True)
try:
    while participant.is_coupling_ongoing():

        # (a) window 시작이면 현재 상태를 checkpoint 로 저장
        if participant.requires_writing_checkpoint():
            result_ckp, t_ckp = result, t

        # (b) 이번 iteration 의 dt 와, 유체가 보낸 계면 힘을 읽어옴
        dt     = participant.get_max_time_step_size()
        forces = participant.read_data(MESH_NAME, READ_DATA, vertex_ids, dt)

        # (c) checkpoint 상태에서 [t_ckp, t_ckp+dt] 풀기
        #유체가 주는 힘이 0이거나 매우작을 경우 disp을 0으로 만들고 trial을 none으로 만듬 아예 풀지않음
    
        if result_ckp is None and vite_init is not None:
            # perturbed fresh start (window1): 초기 속도로 푼다. force≈0 이어도 beam 이
            # VITE 임펄스로 움직이므로 degenerate skip 하지 않는다 (자극이 목적).
            trial = solve_window(forces, None, t_ckp, t_ckp + dt, init_vite=vite_init)
            disp  = interface_displacements(trial, t_ckp + dt)
        elif result_ckp is None and float(np.linalg.norm(forces)) <= ZERO_FORCE_TOL:
            # window1·iter1: 유체가 아직 힘을 안 보냄 (force=0). 구조물은 rest →
            # M u" + C u' + K u = 0, zero IC → u(t)=0. 0 외력 + RESI_GLOB_RELA 는
            # 0/0 으로 발산하므로 이 degenerate step 만 건너뛴다 (x=0 이 정확한 답).
            trial = None
            disp  = np.zeros((n_iface, DIM), dtype=np.float64)
        #실제로 유체가 주는 힘이 있을 경우 window 풀어서 trial과 disp을 구함
        else:
            trial = solve_window(forces, result_ckp, t_ckp, t_ckp + dt)
            disp  = interface_displacements(trial, t_ckp + dt)

        # (d) 계면 변위를 유체에 돌려주고 한 칸 전진
        participant.write_data(MESH_NAME, WRITE_DATA, vertex_ids, disp)
        participant.advance(dt)

        # (e) 수렴 판정
        if participant.requires_reading_checkpoint():
            # 아직 force<->disp 안 맞음 -> trial 폐기, window 시작으로 rollback
            result, t = result_ckp, t_ckp #result는 수렴된상태(booltype) t는 현재시간 그리고 다시 while로 돌아감
        else:
            # coupling 수렴 -> trial 채택
            result, t = trial, t_ckp + dt
            if participant.is_time_window_complete():
                step += 1
                if trial is not None:
                    write_window_med(trial, step, t, save_every=40)
                    # restart 체크포인트: time window 완료 시점(=깨끗한 t_R)에서만,
                    # 최신 1개만 atomic 교체, manifest 의 (step,t)와 항상 동기.
                    if CKPT_EVERY > 0 and step % CKPT_EVERY == 0:
                        sc.save_checkpoint(trial, t, CHECKPOINT_FILE)
                        sc.write_manifest(MANIFEST_FILE, step, t, CHECKPOINT_FILE)
                print(f"[Solid] window {step:4d}  t={t:.4f}s  "
                      f"max|u|={np.linalg.norm(disp, axis=1).max():.3e}",
                      flush=True)

    # 런 연장: 종료 시 마지막 수렴 상태를 항상 체크포인트로 남긴다. 그래야 t_R(=끝
    # 시각)이 유체가 유지하는 last-2 restart 파일과 정합한다(주기 저장과 별개로 보장).
    if result is not None and CKPT_EVERY > 0:
        sc.save_checkpoint(result, t, CHECKPOINT_FILE)
        sc.write_manifest(MANIFEST_FILE, step, t, CHECKPOINT_FILE)
        print(f"[Solid] final checkpoint @ window {step}, t={t:.4f}s", flush=True)

    participant.finalize()
    finalized = True
finally:
    if not finalized:
        try:
            participant.finalize()
        except Exception:
            pass
    elapsed = (datetime.now() - t_start).total_seconds()
    print(f"[Solid] 종료 — {step} window 완료, {elapsed:.1f}s", flush=True)
    try:                                              # ← 추가: 종료 시 병합
        stitch_med_series()
    except Exception as exc:
        print(f"[Solid] stitch 실패: {exc}", flush=True)
    CA.close()
