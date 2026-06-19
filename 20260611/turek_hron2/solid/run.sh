#!/usr/bin/env bash
# ============================================================
#  run.sh — preCICE "Solid" 참가자, WSL LOCAL manual run.
#  Code_Aster, OpenMP 전용 (run_solid.py 는 rank0/size1 직렬 + OMP).
#
#  run.sh 와의 차이 (클러스터 -> WSL 단일 머신):
#    - SGE/qhost, SOLID_NODE, ${OPENMPI_ROOT}/bin/mpirun --host node:1 전부 제거
#    - run_solid.py 는 mpi4py 를 안 쓰고 size=1 직렬이라 mpirun 자체가 불필요
#      -> python3 run_solid.py 를 직접 실행
#    - env 파일 = ~/envs/codeaster_precice311.sh (precice 3.3.1, 유체와 동일 버전)
#
#  전제: ../precice-config.xml 의 <m2n:sockets ... network="lo" /> (WSL 단일 머신)
#
#  사용법 (fluid/run.sh 와 동시에, 두 번째 터미널에서):
#      ./run.sh                      # 기본 OMP 10 스레드
#      SOLID_OMP_THREADS=8 ./run.sh  # OMP 스레드 수 변경
# ============================================================
set -euo pipefail

# ── 사용자 설정 ───────────────────────────────────────────────
SOLID_OMP_THREADS="${SOLID_OMP_THREADS:-10}"                       # OMP 스레드 수
PRECICE_CONFIG="${PRECICE_CONFIG:-../precice-config.xml}"
SOLID_CLEAN="${SOLID_CLEAN:-1}"                                    # 1 = 이전 실행 잔재 삭제
ENV_FILE="${ENV_FILE:-$HOME/envs/codeaster_precice311.sh}"        # code_aster + preCICE
# ──────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/run_${LOG_TS}.log"
exec > >(tee "$LOGFILE") 2>&1

on_exit() {
  local ec=$?
  [ "$ec" -eq 0 ] && echo "[run] 종료 OK   $(date '+%F %T')" \
                   || echo "[run] 실패 (exit=$ec)   $(date '+%F %T')"
  echo "======================================================================"
}
trap on_exit EXIT

# --- 사전 점검 --------------------------------------------------------
[ -f "$ENV_FILE" ]                  || { echo "ERROR: 환경 파일이 없습니다: $ENV_FILE" >&2; exit 1; }
[ -f "${SCRIPT_DIR}/run_solid.py" ] || { echo "ERROR: run_solid.py 가 ${SCRIPT_DIR} 에 없습니다." >&2; exit 1; }

# code_aster + preCICE 환경 (python3 가 precice 3.3.1 를 갖는 code_aster python 으로 바뀜)
set +eu
# shellcheck source=/dev/null
source "$ENV_FILE"
set -eu
unset DEBUG

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found after sourcing $ENV_FILE" >&2; exit 1; }

# --- 이전 실행 잔재 정리 ----------------------------------------------
if [ "$SOLID_CLEAN" = "1" ]; then
  echo "[run] 이전 잔재 삭제 (glob/vola/pick/fort/mess/solid_*.med)"
  rm -f glob.* vola.* pick.code_aster.* fort.* ./*.mess solid_*.med
fi

export OMP_NUM_THREADS="$SOLID_OMP_THREADS" OMP_PLACES=cores OMP_PROC_BIND=close
export PRECICE_CONFIG

echo "======================================================================"
echo "[run] 시작        : $(date '+%F %T %z')"
echo "[run] 케이스 dir  : $SCRIPT_DIR   (WSL local)"
echo "[run] OMP 스레드  : $SOLID_OMP_THREADS"
echo "[run] preCICE cfg : $PRECICE_CONFIG"
echo "[run] 환경 파일   : $ENV_FILE"
echo "[run] python3     : $(command -v python3)"
echo "[run] 로그        : $LOGFILE"
echo "======================================================================"

# run_solid.py 는 size=1 직렬 -> mpirun 없이 직접 실행
exec python3 run_solid.py --numthreads "$SOLID_OMP_THREADS"
