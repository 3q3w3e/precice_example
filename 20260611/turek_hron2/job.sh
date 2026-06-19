#!/usr/bin/env bash
#$ -N thfsi2
#$ -cwd
#$ -j y
#$ -o qsub.log
#$ -V
#
# SGE cluster launcher for the restart-capable Turek-Hron 2 case.
# Run `python3 prepare_restart.py --fresh` or `python3 prepare_restart.py --total ...`
# before qsub so precice-config.xml and the fluid run config match the segment.
set -euo pipefail

CASE_DIR="${CASE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
FLUID_RUN="${FLUID_RUN:-${CASE_DIR}/fluid/run_cluster.sh}"
SOLID_RUN="${SOLID_RUN:-${CASE_DIR}/solid/run_cluster.sh}"
JOB_CLEAN_PRECICE="${JOB_CLEAN_PRECICE:-1}"

if [ "${JOB_CLEAN_PRECICE}" = "1" ]; then
  rm -rf "${CASE_DIR}/precice-run"
fi

echo "[qsub] start $(date '+%F %T') case=${CASE_DIR} host=$(hostname) NSLOTS=${NSLOTS:-?} JOB_ID=${JOB_ID:-?}"
echo "[qsub] fluid=${FLUID_RUN}"
echo "[qsub] solid=${SOLID_RUN}"

"${FLUID_RUN}" >/dev/null 2>&1 &
FPID=$!
sleep 3
"${SOLID_RUN}" >/dev/null 2>&1 &
SPID=$!

wait "${FPID}"
FRC=$?
wait "${SPID}"
SRC=$?

echo "[qsub] end $(date '+%F %T') fluid_rc=${FRC} solid_rc=${SRC}"
[ "${FRC}" -eq 0 ] && [ "${SRC}" -eq 0 ]
