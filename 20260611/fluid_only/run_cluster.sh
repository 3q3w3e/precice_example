#!/usr/bin/env bash
# Fluid-only SU2 run for SGE/OpenMPI cluster nodes.

set -euo pipefail

FLUID_NODES="${FLUID_NODES:-node16}"
FLUID_SLOTS_PER_NODE="${FLUID_SLOTS_PER_NODE:-6}"
FLUID_CPU_LIST="${FLUID_CPU_LIST:-0,1,2,3,4,5}"
SU2_ENV_FILE="${SU2_ENV_FILE:-${HOME}/envs/su2_precice_751.sh}"
CONFIG_FILE="${CONFIG_FILE:-config_fluid.cfg}"
MPIRUN_EXTRA="${MPIRUN_EXTRA:---bind-to cpu-list:ordered --cpu-list ${FLUID_CPU_LIST}}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "${SU2_ENV_FILE}" ]; then
  echo "ERROR: missing SU2_ENV_FILE=${SU2_ENV_FILE}" >&2
  exit 1
fi

set +eu
# shellcheck source=/dev/null
source "${SU2_ENV_FILE}"
set -eu

export OMP_NUM_THREADS="${FLUID_OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${FLUID_OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${FLUID_MKL_NUM_THREADS:-1}"
export BLIS_NUM_THREADS="${FLUID_BLIS_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${FLUID_VECLIB_MAXIMUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${FLUID_NUMEXPR_NUM_THREADS:-1}"

cd "${SCRIPT_DIR}"
LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/${LOG_TS}log.txt"
exec > >(tee "${LOGFILE}") 2>&1

HOST_SPEC=""
NPROC=0
for node in ${FLUID_NODES}; do
  if [ "${FLUID_SLOTS_PER_NODE}" = "auto" ]; then
    slots="$(qhost -h "${node}" 2>/dev/null | awk -v h="${node}" '$1==h {print $5}')"
    if [ -z "${slots}" ]; then
      echo "ERROR: qhost could not read core count for ${node}" >&2
      exit 1
    fi
  else
    slots="${FLUID_SLOTS_PER_NODE}"
  fi
  HOST_SPEC="${HOST_SPEC:+${HOST_SPEC},}${node}:${slots}"
  NPROC=$((NPROC + slots))
done

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
[ "${NPROC}" -ge 1 ] || { echo "ERROR: total MPI ranks is 0" >&2; exit 1; }

echo "======================================================================"
echo "Run started at : $(date '+%F %T %z')"
echo "Script         : ${SCRIPT_DIR}/run_cluster.sh"
echo "MPI nodes      : ${FLUID_NODES}"
echo "MPI hosts      : ${HOST_SPEC} (${NPROC} ranks)"
echo "CONFIG         : ${CONFIG_FILE}"
echo "threads        : OMP=${OMP_NUM_THREADS} OPENBLAS=${OPENBLAS_NUM_THREADS} MKL=${MKL_NUM_THREADS}"
echo "MPIRUN_EXTRA   : ${MPIRUN_EXTRA}"
echo "======================================================================"

# shellcheck disable=SC2086
mpirun --host "${HOST_SPEC}" -np "${NPROC}" ${MPIRUN_EXTRA} \
  -x PATH -x LD_LIBRARY_PATH -x PYTHONPATH -x LIBRARY_PATH -x CPATH \
  -x PKG_CONFIG_PATH -x PRECICE_ROOT -x BOOST_ROOT -x PETSC_ROOT \
  -x OPENMPI_ROOT -x SU2_RUN -x CONDA_PREFIX -x CONDA_DEFAULT_ENV \
  -x OMP_NUM_THREADS -x OPENBLAS_NUM_THREADS -x MKL_NUM_THREADS \
  -x BLIS_NUM_THREADS -x VECLIB_MAXIMUM_THREADS -x NUMEXPR_NUM_THREADS \
  SU2_CFD "${CONFIG_FILE}"
