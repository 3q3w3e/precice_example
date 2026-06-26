#!/usr/bin/env bash
# Solid-only Code_Aster run for WSL/local machines.

set -euo pipefail

SOLID_OMP_THREADS="${SOLID_OMP_THREADS:-10}"
SOLID_CLEAN="${SOLID_CLEAN:-1}"
ENV_FILE="${ENV_FILE:-$HOME/envs/codeaster_precice311.sh}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/solid_only_${LOG_TS}.log"
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

[ -f "$ENV_FILE" ] || { echo "ERROR: 환경 파일이 없습니다: $ENV_FILE" >&2; exit 1; }
[ -f "${SCRIPT_DIR}/run_solid_only.py" ] || { echo "ERROR: run_solid_only.py 가 없습니다." >&2; exit 1; }
[ -f "${SCRIPT_DIR}/beam.med" ] || { echo "ERROR: beam.med 가 없습니다." >&2; exit 1; }

set +eu
# shellcheck source=/dev/null
source "$ENV_FILE"
set -eu
unset DEBUG

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found after sourcing $ENV_FILE" >&2; exit 1; }

if [ "$SOLID_CLEAN" = "1" ]; then
  echo "[run] 이전 잔재 삭제 (glob/vola/pick/fort/mess/solid_*.med/result csv)"
  rm -f glob.* vola.* pick.code_aster.* fort.* ./*.mess solid_*.med run_solid_result.med solid_only.csv
fi

export OMP_NUM_THREADS="$SOLID_OMP_THREADS" OMP_PLACES=cores OMP_PROC_BIND=close

echo "======================================================================"
echo "[run] 시작        : $(date '+%F %T %z')"
echo "[run] 케이스 dir  : $SCRIPT_DIR   (WSL local)"
echo "[run] OMP 스레드  : $SOLID_OMP_THREADS"
echo "[run] 설정 파일   : solid_config.py (환경변수로 선택 override 가능)"
echo "[run] 환경 파일   : $ENV_FILE"
echo "[run] python3     : $(command -v python3)"
echo "[run] 로그        : $LOGFILE"
echo "======================================================================"

exec python3 run_solid_only.py --numthreads "$SOLID_OMP_THREADS"
