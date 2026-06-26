#!/usr/bin/env bash
# Fluid-only SU2 run for WSL/local machines.

set -euo pipefail

FLUID_NPROC="${FLUID_NPROC:-8}"
SU2_ENV_FILE="${SU2_ENV_FILE:-${HOME}/envs/su2_precice_751.sh}"
CONFIG_FILE="${CONFIG_FILE:-config_fluid.cfg}"
MPIRUN_EXTRA="${MPIRUN_EXTRA:---bind-to none --oversubscribe}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "${SU2_ENV_FILE}" ]; then
  echo "ERROR: missing SU2_ENV_FILE=${SU2_ENV_FILE}" >&2
  exit 1
fi

set +eu
# shellcheck source=/dev/null
source "${SU2_ENV_FILE}"
set -eu

cd "${SCRIPT_DIR}"
LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/${LOG_TS}log.txt"
exec > >(tee "${LOGFILE}") 2>&1

on_exit() {
  local ec=$?
  if [ "${ec}" -eq 0 ]; then
    echo "Run finished at: $(date '+%F %T %z') (exit=${ec})"
  else
    echo "Run failed at:   $(date '+%F %T %z') (exit=${ec})"
  fi
  echo "======================================================================"
}
trap on_exit EXIT

command -v SU2_CFD >/dev/null 2>&1 || { echo "ERROR: SU2_CFD not found" >&2; exit 1; }
command -v mpirun >/dev/null 2>&1 || { echo "ERROR: mpirun not found" >&2; exit 1; }
[ -f "${CONFIG_FILE}" ] || { echo "ERROR: missing ${CONFIG_FILE}" >&2; exit 1; }
[ -f fluid.su2 ] || { echo "ERROR: missing fluid.su2" >&2; exit 1; }
[ -f inlet_00000.dat ] || { echo "ERROR: missing inlet_00000.dat" >&2; exit 1; }

echo "======================================================================"
echo "Run started at : $(date '+%F %T %z')"
echo "Script         : ${SCRIPT_DIR}/run_wsl.sh"
echo "NPROC          : ${FLUID_NPROC} ranks"
echo "SU2_CFD        : $(command -v SU2_CFD)"
echo "mpirun         : $(command -v mpirun)"
echo "CONFIG         : ${CONFIG_FILE}"
echo "MPIRUN_EXTRA   : ${MPIRUN_EXTRA}"
echo "======================================================================"

# shellcheck disable=SC2086
mpirun -np "${FLUID_NPROC}" ${MPIRUN_EXTRA} SU2_CFD "${CONFIG_FILE}"
