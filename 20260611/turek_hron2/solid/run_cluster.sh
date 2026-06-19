#!/usr/bin/env bash
# Solid participant — SGE/OpenMPI cluster placement, Code_Aster OpenMP solve.
set -euo pipefail

SOLID_NODE="${SOLID_NODE:-node16}"
SOLID_OMP_THREADS="${SOLID_OMP_THREADS:-2}"
SOLID_CPU_SET="${SOLID_CPU_SET:-12,14}"
PRECICE_CONFIG="${PRECICE_CONFIG:-../precice-config.xml}"
SOLID_CLEAN="${SOLID_CLEAN:-1}"
ENV_FILE="${ENV_FILE:-${HOME}/envs/codeaster_precice311.sh}"
OPENMPI_ROOT="${SOLID_OPENMPI_ROOT:-/home/hilbert/opt/openmpi-4.1.1}"
MPIRUN_BIN="${SOLID_MPIRUN_BIN:-${OPENMPI_ROOT}/bin/mpirun}"
MPIRUN_EXTRA="${MPIRUN_EXTRA:---mca btl ^openib}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/run_${LOG_TS}.log"
exec > >(tee "${LOGFILE}") 2>&1

on_exit() {
  local ec=$?
  [ "${ec}" -eq 0 ] && echo "[run] 종료 OK   $(date '+%F %T')" \
                     || echo "[run] 실패 (exit=${ec})   $(date '+%F %T')"
  echo "======================================================================"
}
trap on_exit EXIT

[ -f "${ENV_FILE}" ] || { echo "ERROR: missing ENV_FILE=${ENV_FILE}" >&2; exit 1; }
[ -f "${SCRIPT_DIR}/run_solid.py" ] || { echo "ERROR: missing run_solid.py" >&2; exit 1; }
[ -x "${MPIRUN_BIN}" ] || { echo "ERROR: missing mpirun=${MPIRUN_BIN}" >&2; exit 1; }
[ -f "${PRECICE_CONFIG}" ] || { echo "ERROR: missing ${PRECICE_CONFIG}. Run prepare_restart.py first." >&2; exit 1; }

set +eu
# shellcheck source=/dev/null
source "${ENV_FILE}"
set -eu
unset DEBUG

export OPENMPI_ROOT OPAL_PREFIX="${OPENMPI_ROOT}"
export PATH="${OPENMPI_ROOT}/bin:${PATH}"
export LD_LIBRARY_PATH="${OPENMPI_ROOT}/lib:${LD_LIBRARY_PATH:-}"
export LIBRARY_PATH="${OPENMPI_ROOT}/lib:${LIBRARY_PATH:-}"
export MPICC="${OPENMPI_ROOT}/bin/mpicc"
export MPICXX="${OPENMPI_ROOT}/bin/mpicxx"
hash -r 2>/dev/null || true

NODE_NCORE="$(qhost -h "${SOLID_NODE}" 2>/dev/null | awk -v h="${SOLID_NODE}" '$1==h {print $5}')"
if [ -z "${NODE_NCORE}" ]; then
  NODE_NCORE="?"
  echo "[run] warning: qhost could not read ${SOLID_NODE}; continuing"
fi
if [ "${SOLID_OMP_THREADS}" = "auto" ]; then
  if [ "${NODE_NCORE}" = "?" ]; then
    echo "ERROR: SOLID_OMP_THREADS=auto needs qhost core count" >&2
    exit 1
  fi
  SOLID_OMP_THREADS="${NODE_NCORE}"
fi

if [ "${SOLID_CLEAN}" = "1" ]; then
  echo "[run] 이전 잔재 삭제 (glob/vola/pick/fort/mess/solid_*.med)"
  rm -f glob.* vola.* pick.code_aster.* fort.* ./*.mess solid_*.med
fi

echo "======================================================================"
echo "[run] 시작        : $(date '+%F %T %z')"
echo "[run] 케이스 dir  : ${SCRIPT_DIR}"
echo "[run] 실행 노드   : ${SOLID_NODE} (physical cores ${NODE_NCORE})"
echo "[run] OMP 스레드  : ${SOLID_OMP_THREADS}"
echo "[run] CPU set     : ${SOLID_CPU_SET}"
echo "[run] preCICE cfg : ${PRECICE_CONFIG}"
echo "[run] 환경 파일   : ${ENV_FILE}"
echo "[run] mpirun      : ${MPIRUN_BIN}"
echo "[run] 로그        : ${LOGFILE}"
echo "======================================================================"

# shellcheck disable=SC2086
"${MPIRUN_BIN}" --host "${SOLID_NODE}:1" -np 1 --bind-to none ${MPIRUN_EXTRA} \
  bash -c '
    cd "$1" || exit 1
    conda deactivate 2>/dev/null || true
    # shellcheck source=/dev/null
    source "$4"
    export OPENMPI_ROOT="$6" OPAL_PREFIX="$6"
    export PATH="${OPENMPI_ROOT}/bin:${PATH}"
    export LD_LIBRARY_PATH="${OPENMPI_ROOT}/lib:${LD_LIBRARY_PATH:-}"
    export LIBRARY_PATH="${OPENMPI_ROOT}/lib:${LIBRARY_PATH:-}"
    export MPICC="${OPENMPI_ROOT}/bin/mpicc" MPICXX="${OPENMPI_ROOT}/bin/mpicxx"
    unset OMP_PLACES OMP_PROC_BIND DEBUG
    export OMP_NUM_THREADS="$2"
    export PRECICE_CONFIG="$3"
    export SOLID_RESTART="${SOLID_RESTART:-0}"
    export SOLID_RESTART_DIR="${SOLID_RESTART_DIR:-}"
    export SOLID_CKPT_EVERY="${SOLID_CKPT_EVERY:-1}"
    export SOLID_CKPT_KEEP="${SOLID_CKPT_KEEP:-2}"
    exec taskset -c "$5" python3 run_solid.py --numthreads "$2"
  ' _ "${SCRIPT_DIR}" "${SOLID_OMP_THREADS}" "${PRECICE_CONFIG}" "${ENV_FILE}" "${SOLID_CPU_SET}" "${OPENMPI_ROOT}"
