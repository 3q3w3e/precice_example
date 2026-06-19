#!/usr/bin/env bash
# ============================================================
#  run.sh — preCICE "Solid" 참가자 (wall&ramm_solid, Code_Aster, OMP 전용)
#
#  특정 계산 노드를 지정해서 그 노드에 프로세스 1개(OMP 전용)를 띄운다.
#  MPI 병렬이 아니라, mpirun 은 "프로세스를 원하는 노드에 배치"하는 용도로만
#  쓰고, 실제 가속은 그 노드의 코어를 쓰는 OpenMP 스레드가 담당한다.
#
#  사용법 (유체 케이스 wall&ramm_fluid 와 동시에, 두 번째 터미널에서):
#      ./run.sh                        # 아래 SOLID_NODE 기본값으로 실행
#      SOLID_NODE=node17 ./run.sh      # 노드 변경
#      SOLID_OMP_THREADS=12 ./run.sh   # OMP 스레드 수 수동 지정 (기본: 노드 물리코어수)
#      SOLID_CPU_SET=16,18 ./run.sh      # solid OMP 가 사용할 OS CPU 번호
#
#  run_aster/job.export 가 아니라 plain python3 로 실행한다.
#  (run_aster 는 proc.0/ 로 chdir 해서 preCICE 의 ../ 상대경로가 깨짐 — run_local.sh 주석 참고)
# ============================================================
set -euo pipefail

# ┌──────────────────────────────────────────────────────────┐
# │  사용자 설정 — 실행할 노드를 여기서 지정한다               │
# └──────────────────────────────────────────────────────────┘
SOLID_NODE="${SOLID_NODE:-node12}"                  # 계산 노드 (유휴 추천: node16/17/20, 20코어)
SOLID_OMP_THREADS="${SOLID_OMP_THREADS=2}"      # auto = 노드 물리코어수 자동 산출
SOLID_CPU_SET="${SOLID_CPU_SET:-13,15}"               # taskset OS CPU 번호. fluid socket1 홀수와 같은 socket1 의 남은 두 코어 (17,19), socket0 의 hron1 fluid 와 충돌 회피
PRECICE_CONFIG="${PRECICE_CONFIG:-../precice-config.xml}"
SOLID_CLEAN="${SOLID_CLEAN:-1}"                     # 1 = 이전 실행 잔재 삭제
ENV_FILE="${ENV_FILE:-$HOME/envs/codeaster_precice.sh}"   # code_aster + preCICE 환경
OPENMPI_ROOT="${SOLID_OPENMPI_ROOT:-/home/hilbert/opt/openmpi-4.1.1}"
MPIRUN_BIN="${SOLID_MPIRUN_BIN:-${OPENMPI_ROOT}/bin/mpirun}"
MPIRUN_EXTRA="${MPIRUN_EXTRA:---mca btl ^openib}"   # openib(infiniband) 경고 억제
SOLID_RESTART="${SOLID_RESTART:-0}"
SOLID_CKPT_EVERY="${SOLID_CKPT_EVERY:-1}"
SOLID_CKPT_KEEP="${SOLID_CKPT_KEEP:-2}"
# ────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/run_${LOG_TS}.log"
exec > >(tee "$LOGFILE") 2>&1

on_exit() {
  local ec=$?
  if [ "$ec" -eq 0 ]; then
    echo "[run] 종료 OK   $(date '+%F %T')"
  else
    echo "[run] 실패 (exit=$ec)   $(date '+%F %T')"
  fi
  echo "======================================================================"
}
trap on_exit EXIT

# --- 사전 점검 --------------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: 환경 파일이 없습니다: $ENV_FILE" >&2
  exit 1
fi
if [ ! -f "${SCRIPT_DIR}/run_solid.py" ]; then
  echo "ERROR: run_solid.py 가 ${SCRIPT_DIR} 에 없습니다." >&2
  exit 1
fi
if [ ! -x "$MPIRUN_BIN" ]; then
  echo "ERROR: Open MPI 4.1.1 mpirun 이 없습니다: $MPIRUN_BIN" >&2
  exit 1
fi

# 로컬에서 환경을 source — mpirun(openmpi-4.1.1) 을 PATH 에 올리기 위함
# shellcheck source=/dev/null
source "$ENV_FILE"

OPENMPI_ROOT="${SOLID_OPENMPI_ROOT:-/home/hilbert/opt/openmpi-4.1.1}"
MPIRUN_BIN="${SOLID_MPIRUN_BIN:-${OPENMPI_ROOT}/bin/mpirun}"
export OPENMPI_ROOT OPAL_PREFIX="$OPENMPI_ROOT"
export PATH="${OPENMPI_ROOT}/bin:${PATH}"
export LD_LIBRARY_PATH="${OPENMPI_ROOT}/lib:${LD_LIBRARY_PATH:-}"
export LIBRARY_PATH="${OPENMPI_ROOT}/lib:${LIBRARY_PATH:-}"
export MPICC="${OPENMPI_ROOT}/bin/mpicc"
export MPICXX="${OPENMPI_ROOT}/bin/mpicxx"
hash -r 2>/dev/null || true

if [ "$(command -v mpirun)" != "$MPIRUN_BIN" ]; then
  echo "ERROR: 잘못된 mpirun 을 잡았습니다: $(command -v mpirun)" >&2
  echo "       기대값: $MPIRUN_BIN" >&2
  exit 1
fi

# --- 노드 확인 + 물리코어수 산출 (qhost) ------------------------------
NODE_NCORE="$(qhost -h "$SOLID_NODE" 2>/dev/null | awk -v h="$SOLID_NODE" '$1==h {print $5}')"
if [ -z "${NODE_NCORE}" ]; then
  if [ "$SOLID_OMP_THREADS" = "auto" ]; then
    echo "ERROR: qhost 에서 '$SOLID_NODE' 정보를 못 찾았습니다." >&2
    echo "       노드 이름을 확인하거나 SOLID_OMP_THREADS 를 직접 지정하세요." >&2
    exit 1
  fi
  echo "[run] 경고: qhost 에서 '$SOLID_NODE' 를 못 찾음 — 노드 이름 확인 권장 (계속 진행)"
  NODE_NCORE="?"
fi
if [ "$SOLID_OMP_THREADS" = "auto" ]; then
  SOLID_OMP_THREADS="$NODE_NCORE"
fi

# --- 이전 실행 잔재 정리 ----------------------------------------------
if [ "$SOLID_CLEAN" = "1" ]; then
  echo "[run] 이전 잔재 삭제 (glob/vola/pick/fort/mess/solid_*.med)"
  rm -f glob.* vola.* pick.code_aster.* fort.* ./*.mess solid_*.med
fi

# --- 실행 정보 --------------------------------------------------------
echo "======================================================================"
echo "[run] 시작        : $(date '+%F %T %z')"
echo "[run] 케이스 dir  : $SCRIPT_DIR"
echo "[run] 실행 노드   : $SOLID_NODE   (물리코어 ${NODE_NCORE})"
echo "[run] OMP 스레드  : $SOLID_OMP_THREADS"
echo "[run] CPU set     : $SOLID_CPU_SET"
echo "[run] preCICE cfg : $PRECICE_CONFIG"
echo "[run] restart     : SOLID_RESTART=$SOLID_RESTART  SOLID_RESTART_DIR=${SOLID_RESTART_DIR:-<default>}"
echo "[run] checkpoint  : every=$SOLID_CKPT_EVERY  keep=$SOLID_CKPT_KEEP"
echo "[run] 환경 파일   : $ENV_FILE"
echo "[run] OpenMPI root: $OPENMPI_ROOT"
echo "[run] mpirun      : $MPIRUN_BIN ($("$MPIRUN_BIN" --version | head -n 1))"
echo "[run] 로그        : $LOGFILE"
echo "======================================================================"

MPI_ENV_EXPORTS=(-x SOLID_RESTART -x SOLID_CKPT_EVERY -x SOLID_CKPT_KEEP)
if [ -n "${SOLID_RESTART_DIR:-}" ]; then
  MPI_ENV_EXPORTS+=(-x SOLID_RESTART_DIR)
fi

# --- mpirun 으로 지정 노드에 단일 프로세스 배치 ------------------------
#   --host <node>:1  : 해당 노드에만 배치
#   -np 1            : OMP 전용 → MPI 프로세스 1개
#   --bind-to none   : Open MPI 자체 binding 은 끄고, 아래 taskset 으로 OS CPU 번호를 직접 고정
#   원격 노드에서 환경을 다시 source 한다 (홈이 NFS 공유라 어디서나 보임).
#   $1=케이스dir  $2=OMP스레드  $3=preCICE cfg  $4=환경파일  $5=CPU set  $6=OpenMPI root
# shellcheck disable=SC2086
"$MPIRUN_BIN" --host "${SOLID_NODE}:1" -np 1 --bind-to none ${MPIRUN_EXTRA} "${MPI_ENV_EXPORTS[@]}" \
    bash -c '
        cd "$1" || exit 1
        # shellcheck source=/dev/null
        conda deactivate 2>/dev/null || true
        source "$4"
        export OPENMPI_ROOT="$6" OPAL_PREFIX="$6"
        export PATH="${OPENMPI_ROOT}/bin:${PATH}"
        export LD_LIBRARY_PATH="${OPENMPI_ROOT}/lib:${LD_LIBRARY_PATH:-}"
        export LIBRARY_PATH="${OPENMPI_ROOT}/lib:${LIBRARY_PATH:-}"
        export MPICC="${OPENMPI_ROOT}/bin/mpicc" MPICXX="${OPENMPI_ROOT}/bin/mpicxx"
        hash -r 2>/dev/null || true
        if [ "$(command -v mpirun)" != "${OPENMPI_ROOT}/bin/mpirun" ]; then
            echo "ERROR: remote wrong mpirun: $(command -v mpirun)" >&2
            exit 1
        fi
        # OMP_PROC_BIND=close + OMP_PLACES=cores 가 main thread 를 첫 place(=CPU 0) 에만 묶어버려
        # taskset 의 cpuset({0,2}) 중 CPU 2 가 미사용됨. cpuset 안에서 OMP 가 떠다니도록 둘 다 unset.
        export OMP_NUM_THREADS="$2"
        unset OMP_PLACES OMP_PROC_BIND
        export PRECICE_CONFIG="$3"
        echo "[run:remote] mpirun: $(command -v mpirun) ($(mpirun --version | head -n 1))"
        echo "[run:remote] taskset CPU set: $5"
        exec taskset -c "$5" python3 run_solid.py --numthreads "$2"
    ' _ "$SCRIPT_DIR" "$SOLID_OMP_THREADS" "$PRECICE_CONFIG" "$ENV_FILE" "$SOLID_CPU_SET" "$OPENMPI_ROOT"
