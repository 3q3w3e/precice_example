#!/usr/bin/env bash
# Solid-only free-decay test from restart/solid_manifest.json.
set -euo pipefail

SOLID_OMP_THREADS="${SOLID_OMP_THREADS:-2}"
ENV_FILE="${ENV_FILE:-$HOME/envs/codeaster_precice311.sh}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

[ -f "$ENV_FILE" ] || { echo "ERROR: 환경 파일이 없습니다: $ENV_FILE" >&2; exit 1; }

set +eu
# shellcheck source=/dev/null
source "$ENV_FILE"
set -eu
unset DEBUG

export OMP_NUM_THREADS="$SOLID_OMP_THREADS" OMP_PLACES=cores OMP_PROC_BIND=close

LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/free_decay_${LOG_TS}.log"
exec > >(tee "$LOGFILE") 2>&1

echo "======================================================================"
echo "[free] 시작       : $(date '+%F %T %z')"
echo "[free] OMP 스레드 : $SOLID_OMP_THREADS"
echo "[free] steps      : ${SOLID_FREE_STEPS:-20}"
echo "[free] dt         : ${SOLID_FREE_DT:-0.002}"
echo "[free] out        : ${SOLID_FREE_OUT:-free_decay.csv}"
echo "[free] 로그       : $LOGFILE"
echo "======================================================================"

exec python3 run_free_decay.py
