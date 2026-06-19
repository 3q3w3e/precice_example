#!/usr/bin/env bash
# Fluid participant — WSL LOCAL manual run.
#   SU2 7.5.1 invasive su2-adapter, INC Navier-Stokes, 2D Turek-Hron FSI, preCICE.
#
# run.sh 와의 차이 (클러스터 -> WSL 단일 머신):
#   - SGE/qhost, FLUID_NODES, mpirun --host node:N, -x ENV 전달 전부 제거
#   - 로컬에서 FLUID_NPROC 개 MPI rank 를 그냥 띄운다 (mpirun -np N)
#   - env 파일 = ~/envs/su2_precice_751.sh (conda su2_751 python + SU2_751/bin,
#     시스템 openmpi, OMPI_MCA_osc=pt2pt)
#
# 전제: ../precice-config.xml 의 <m2n:sockets ... network="lo" /> (WSL 단일 머신)
#
# 사용법 (solid/run.sh 와 동시에, 다른 터미널에서):
#     ./run.sh                 # 기본 8 rank
#     FLUID_NPROC=4 ./run.sh   # rank 수 변경
#     FLUID_INLET_RAMP=1 FLUID_INLET_RAMP_TIME=2.0 ./run.sh

set -euo pipefail

# ── 사용자 설정 ───────────────────────────────────────────────
FLUID_NPROC="${FLUID_NPROC:-8}"                                  # 로컬 MPI rank 수
SU2_ENV_FILE="${SU2_ENV_FILE:-${HOME}/envs/su2_precice_751.sh}"  # 7.5.1 invasive 환경
PRECICE_CONFIG="${PRECICE_CONFIG:-../precice-config.xml}"
FLUID_DIM="${FLUID_DIM:-2}"
CONFIG_FILE="${CONFIG_FILE:-config_fluid.cfg}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
# WSL2: 단일 노드라 --host/-x 불필요. osc=pt2pt 는 env 파일이 설정.
MPIRUN_EXTRA="${MPIRUN_EXTRA:---bind-to none --oversubscribe}"
# ──────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- environment -------------------------------------------------------------
[ -f "${SU2_ENV_FILE}" ] || { echo "Missing SU2_ENV_FILE=${SU2_ENV_FILE}"; exit 1; }
set +eu
# shellcheck source=/dev/null
source "${SU2_ENV_FILE}"
set -eu
export PRECICE_CONFIG

cd "${SCRIPT_DIR}"
LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/${LOG_TS}log.txt"
exec > >(tee "${LOGFILE}") 2>&1

if [ ! -e inlet.dat ] && [ -f inlet_00000.dat ]; then
  ln -s inlet_00000.dat inlet.dat
fi

on_exit() {
  local ec=$?
  [ "${ec}" -eq 0 ] && echo "Run finished at: $(date '+%F %T %z') (exit=${ec})" \
                     || echo "Run failed at:   $(date '+%F %T %z') (exit=${ec})"
  echo "======================================================================"
}
trap on_exit EXIT

# --- preflight ---------------------------------------------------------------
command -v "${PYTHON_BIN}" >/dev/null 2>&1 || { echo "${PYTHON_BIN} not in PATH."; exit 1; }
command -v mpirun >/dev/null 2>&1          || { echo "ERROR: mpirun not found."; exit 1; }
"${PYTHON_BIN}" -c 'import pysu2' >/dev/null 2>&1 \
  || { echo "ERROR: 'import pysu2' failed. Is ${SU2_ENV_FILE} loaded (7.5.1)?"; exit 1; }
[ -f "${SCRIPT_DIR}/SU2_preCICE_FSI.py" ] \
  || { echo "ERROR: SU2_preCICE_FSI.py 가 ${SCRIPT_DIR} 에 없습니다."; exit 1; }

echo "======================================================================"
echo "Run started at : $(date '+%F %T %z')"
echo "Script         : ${SCRIPT_DIR}/run.sh   (WSL local manual)"
echo "NPROC          : ${FLUID_NPROC} ranks (local)"
echo "SU2_CFD        : $(command -v SU2_CFD)"
echo "python         : $(command -v ${PYTHON_BIN})"
echo "mpirun         : $(command -v mpirun)  | MPIRUN_EXTRA=${MPIRUN_EXTRA}"
echo "PRECICE_CONFIG=${PRECICE_CONFIG} | CONFIG=${CONFIG_FILE} | DIM=${FLUID_DIM}"
echo "INLET_RAMP    : ${FLUID_INLET_RAMP:-0} | TIME=${FLUID_INLET_RAMP_TIME:-2.0} | MARKER=${FLUID_INLET_RAMP_MARKER:-inlet}"
echo "======================================================================"

SU2_ARGS=( -f "${CONFIG_FILE}" --parallel -d "${FLUID_DIM}" --precice-config "${PRECICE_CONFIG}" )

# shellcheck disable=SC2086
mpirun -np "${FLUID_NPROC}" ${MPIRUN_EXTRA} \
    "${PYTHON_BIN}" SU2_preCICE_FSI.py "${SU2_ARGS[@]}"
