#!/usr/bin/env bash
# Fluid participant — SGE/OpenMPI cluster run.
#
# This is the cluster counterpart of run.sh. It launches SU2 on the nodes listed
# in FLUID_NODES and leaves the solid participant to ../job.sh.
set -euo pipefail

FLUID_NODES="${FLUID_NODES:-node16}"
FLUID_SLOTS_PER_NODE="${FLUID_SLOTS_PER_NODE:-6}"
FLUID_CPU_LIST="${FLUID_CPU_LIST:-0,1,2,3,4,5}"
SU2_ENV_FILE="${SU2_ENV_FILE:-${HOME}/envs/su2_precice_751.sh}"
PRECICE_CONFIG="${PRECICE_CONFIG:-../precice-config.xml}"
FLUID_DIM="${FLUID_DIM:-2}"
CONFIG_FILE="${CONFIG_FILE:-config_fluid_run.cfg}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
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
export PRECICE_CONFIG

cd "${SCRIPT_DIR}"
LOG_TS="$(date '+%Y%m%d_%H%M%S')"
LOGFILE="${SCRIPT_DIR}/${LOG_TS}log.txt"
exec > >(tee "${LOGFILE}") 2>&1

if [ ! -e inlet.dat ] && [ -f inlet_00000.dat ]; then
  ln -s inlet_00000.dat inlet.dat
fi

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
  [ "${ec}" -eq 0 ] && echo "Run finished at: $(date '+%F %T %z') (exit=${ec})" \
                     || echo "Run failed at:   $(date '+%F %T %z') (exit=${ec})"
  echo "======================================================================"
}
trap on_exit EXIT

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || { echo "ERROR: ${PYTHON_BIN} not in PATH" >&2; exit 1; }
command -v mpirun >/dev/null 2>&1 || { echo "ERROR: mpirun not found" >&2; exit 1; }
"${PYTHON_BIN}" -c 'import pysu2' >/dev/null 2>&1 || { echo "ERROR: import pysu2 failed" >&2; exit 1; }
[ -f "${CONFIG_FILE}" ] || { echo "ERROR: missing ${CONFIG_FILE}. Run prepare_restart.py first." >&2; exit 1; }
[ -f "${PRECICE_CONFIG}" ] || { echo "ERROR: missing ${PRECICE_CONFIG}. Run prepare_restart.py first." >&2; exit 1; }

echo "======================================================================"
echo "Run started at : $(date '+%F %T %z')"
echo "Script         : ${SCRIPT_DIR}/run_cluster.sh"
echo "MPI nodes      : ${FLUID_NODES}"
echo "MPI hosts      : ${HOST_SPEC} (${NPROC} ranks)"
echo "CONFIG         : ${CONFIG_FILE}"
echo "PRECICE_CONFIG : ${PRECICE_CONFIG}"
echo "INLET_RAMP     : ${FLUID_INLET_RAMP:-0} | TIME=${FLUID_INLET_RAMP_TIME:-2.0} | MARKER=${FLUID_INLET_RAMP_MARKER:-inlet}"
echo "======================================================================"

SU2_ARGS=( -f "${CONFIG_FILE}" --parallel -d "${FLUID_DIM}" --precice-config "${PRECICE_CONFIG}" )

# shellcheck disable=SC2086
mpirun --host "${HOST_SPEC}" -np "${NPROC}" ${MPIRUN_EXTRA} \
  -x PATH -x LD_LIBRARY_PATH -x PYTHONPATH -x LIBRARY_PATH -x CPATH \
  -x PKG_CONFIG_PATH -x PRECICE_ROOT -x BOOST_ROOT -x PETSC_ROOT \
  -x OPENMPI_ROOT -x SU2_RUN -x CONDA_PREFIX -x CONDA_DEFAULT_ENV -x PRECICE_CONFIG \
  -x OMP_NUM_THREADS -x OPENBLAS_NUM_THREADS -x MKL_NUM_THREADS \
  -x BLIS_NUM_THREADS -x VECLIB_MAXIMUM_THREADS -x NUMEXPR_NUM_THREADS \
  -x FLUID_INLET_RAMP -x FLUID_INLET_RAMP_TIME -x FLUID_INLET_RAMP_MARKER -x FLUID_INLET_RAMP_LOG \
  -x FLUID_RESTART -x FLUID_RESTART_DIR -x FLUID_KEEP_RESTART -x FLUID_RESTART_KEEP \
  "${PYTHON_BIN}" SU2_preCICE_FSI.py "${SU2_ARGS[@]}"
