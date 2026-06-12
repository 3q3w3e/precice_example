#!/usr/bin/env bash
# Fluid participant — SU2 7.5.1 "Blackbird" (invasive su2-adapter), INCOMPRESSIBLE Navier-Stokes,
# 2D "vertical cantilever in channel" FSI benchmark, driven via preCICE.
#
# MPI-PARALLEL variant: SU2 를 여러 계산 노드에 MPI 분산해서 돌린다.
# mfile(hostfile) 을 쓰지 않고, 사용할 노드를 아래 FLUID_NODES 에서 직접 지정한다.
#
# Physics/markers from the SU2 multiphysics tutorial (coarse_withinitial_dt5):
#   - INC_NAVIER_STOKES, rho=1.18, U_in=0.513 m/s, mu=1.82e-5, dt=0.005
#   - FSI interface marker = "move_fld"  (also DEFORM_MESH / FLUID_LOAD marker)
# Mesh: fsi_benchmark_fluid_noinflation.su2 (NDIME=2; markers inlet/outlet/upper/down/
#       nomove_fld/move_fld).
#
# Usage (구조 케이스 wall&ramm_solid 와 동시에, 다른 터미널에서):
#     ./run.sh                              # 아래 FLUID_NODES 기본값(node15 node16)
#     FLUID_NODES="node17 node18" ./run.sh  # 노드 변경
#     FLUID_SLOTS_PER_NODE=10 ./run.sh      # 노드당 rank 수 (기본: 노드 물리코어수)
#     FLUID_CPU_LIST="10,11,12,13,14,15,16,17" ./run.sh  # rank 0..N-1 바인딩 (hwloc 논리번호; OS 물리는 lstopo 로 확인)
#
# The preCICE config (../precice-config.xml) and ../precice-run are shared with the
# solid participant; do not run another fluid case at the same time.

# ┌──────────────────────────────────────────────────────────┐
# │  사용자 설정 — 사용할 노드를 여기서 지정한다 (mfile 안 씀) │
# └──────────────────────────────────────────────────────────┘
FLUID_NODES="${FLUID_NODES:-node10:14 node11:16}"   # 멀티노드 — "node:slots" 형식 지원. 콜론 없으면 FLUID_SLOTS_PER_NODE 적용.
FLUID_SLOTS_PER_NODE="${FLUID_SLOTS_PER_NODE=16}"   # fallback (콜론 없는 노드용). auto = qhost 노드코어수.
# FLUID_CPU_LIST 는 멀티노드 + HT 노드 (node11) 에서는 비활성. OpenMPI 가 `--bind-to core --map-by core` 로 physical core 자동 선택.
FLUID_CPU_LIST="${FLUID_CPU_LIST:-}"
# ────────────────────────────────────────────────────────────

# --- environment -----------------------------------------------------------------
if [ -z "${SU2_ENV_ALREADY_LOADED:-}" ]; then
  SU2_ENV_FILE="${SU2_ENV_FILE:-${HOME}/envs/su2_precice_751.sh}"
  if [ ! -f "${SU2_ENV_FILE}" ]; then echo "Failed to find SU2_ENV_FILE=${SU2_ENV_FILE}"; exit 1; fi
  set +e +u +o pipefail
  # shellcheck source=/dev/null
  source "${SU2_ENV_FILE}"; _rc=$?
  set -e -u -o pipefail
  [ "${_rc}" -eq 0 ] || { echo "Failed to source ${SU2_ENV_FILE}"; exit 1; }
  unset _rc
else
  set -euo pipefail
fi

# SU2 is MPI-parallel here. Keep BLAS/OpenMP runtimes from spawning a
# per-rank thread pool, which otherwise oversubscribes the MPI rank cpuset.
# Do not inherit generic thread variables from qsub -V or the login shell;
# use FLUID_* variables for intentional overrides.
export OMP_NUM_THREADS="${FLUID_OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${FLUID_OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${FLUID_MKL_NUM_THREADS:-1}"
export BLIS_NUM_THREADS="${FLUID_BLIS_NUM_THREADS:-1}"
export VECLIB_MAXIMUM_THREADS="${FLUID_VECLIB_MAXIMUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${FLUID_NUMEXPR_NUM_THREADS:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_TS="$(date '+%Y%d%m%H%M%S')"
LOGFILE="${SCRIPT_DIR}/${LOG_TS}log.txt"
exec > >(tee "${LOGFILE}") 2>&1

PRECICE_CONFIG="${PRECICE_CONFIG:-../precice-config.xml}"
FLUID_DIM="${FLUID_DIM:-2}"
SU2_MARKER="${SU2_MARKER:-beam_wet}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
MPIRUN_EXTRA="${MPIRUN_EXTRA:---bind-to core --map-by core}"  # 멀티노드용: hwloc 기반 physical core 자동 선택 (node11 의 HT 형제는 자동 회피)
CONFIG_FILE="${CONFIG_FILE:-config_fluid.cfg}"
export PRECICE_CONFIG

# --- 노드 목록 -> mpirun --host 스펙 + 총 rank 수 산출 ----------------------------
#  FLUID_NODES 의 각 노드에 slot 수를 정해 "node15:20,node16:20" 형태로 만든다 (mfile 대체).
HOST_SPEC=""
NPROC=0
for _entry in ${FLUID_NODES}; do
  case "${_entry}" in
    *:*) _n="${_entry%:*}"; _s="${_entry##*:}" ;;           # "node10:14" 형식 (per-node 슬롯)
    *)   _n="${_entry}";    _s="${FLUID_SLOTS_PER_NODE}" ;; # 콜론 없으면 default
  esac
  if [ "${_s}" = "auto" ]; then
    _s="$(qhost -h "${_n}" 2>/dev/null | awk -v h="${_n}" '$1==h {print $5}')"
    [ -n "${_s}" ] || { echo "ERROR: qhost 에서 '${_n}' 코어수를 못 구함."; exit 1; }
  fi
  HOST_SPEC="${HOST_SPEC:+${HOST_SPEC},}${_n}:${_s}"
  NPROC=$((NPROC + _s))
done
unset _entry _n _s
[ "${NPROC}" -ge 1 ] || { echo "ERROR: 총 rank 수가 0 입니다. FLUID_NODES 를 확인하세요."; exit 1; }

print_run_header() {
  echo "======================================================================"
  echo "Run started at: $(date '+%F %T %z')"
  echo "Script: ${SCRIPT_DIR}/run.sh"
  echo "Using PRECICE_CONFIG=${PRECICE_CONFIG} | CONFIG_FILE=${CONFIG_FILE} | FLUID_DIM=${FLUID_DIM} | SU2_MARKER=${SU2_MARKER}"
  echo "MPI nodes : ${FLUID_NODES}"
  echo "MPI hosts : ${HOST_SPEC}  (총 ${NPROC} ranks)"
  echo "mpirun    : $(command -v mpirun || echo '<not found>')  | MPIRUN_EXTRA=${MPIRUN_EXTRA}"
  echo "binding   : ${MPIRUN_EXTRA}  (FLUID_CPU_LIST=${FLUID_CPU_LIST:-<unused, --bind-to core 모드>})"
  echo "threads   : OMP=${OMP_NUM_THREADS} OPENBLAS=${OPENBLAS_NUM_THREADS} MKL=${MKL_NUM_THREADS} BLIS=${BLIS_NUM_THREADS} NUMEXPR=${NUMEXPR_NUM_THREADS}"
  echo "SU2_CFD   : $(command -v SU2_CFD || echo '<not found>') ($(SU2_CFD --help 2>/dev/null | head -1))"
  echo "python    : $(command -v ${PYTHON_BIN}) ($(${PYTHON_BIN} -c 'import sys;print(sys.version.split()[0])' 2>/dev/null || echo '?'))"
}
print_run_footer() {
  local ec="$1"
  [ "${ec}" -eq 0 ] && echo "Run finished at: $(date '+%F %T %z') (exit=${ec})" || echo "Run failed at: $(date '+%F %T %z') (exit=${ec})"
  echo "======================================================================"
}
on_exit() { local ec=$?; print_run_footer "${ec}"; }
trap on_exit EXIT

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || { echo "${PYTHON_BIN} is not in PATH."; exit 1; }
command -v mpirun >/dev/null 2>&1 || { echo "ERROR: mpirun 을 찾을 수 없습니다 (${SU2_ENV_FILE:-env} 가 openmpi 를 PATH 에 안 올림)."; exit 1; }
"${PYTHON_BIN}" -c 'import pysu2' >/dev/null 2>&1 || { echo "ERROR: 'import pysu2' failed with ${PYTHON_BIN}. Is the SU2 env loaded?"; exit 1; }
[ -f "${SCRIPT_DIR}/SU2_preCICE_FSI.py" ] || { echo "ERROR: SU2_preCICE_FSI.py 가 ${SCRIPT_DIR} 에 없습니다 (7.5.1 어댑터 FSI 스크립트 필요)."; exit 1; }

print_run_header
cd "${SCRIPT_DIR}"

# NOTE: 가져온 stock 7.5.1 어댑터 SU2_preCICE_FSI.py 에는 --su2-marker 옵션이 없다
#       (커플링 마커를 'interface' 로 하드코딩 — 스크립트 82번 줄). 그래서 여기서는
#       --su2-marker 를 넘기지 않는다. ⚠ config_fluid.cfg 의 MARKER_DEFORM_MESH 는
#       move_fld 이므로, 마커 이름을 한쪽에 맞추지 않으면 실행 시 마커 조회에서 실패한다.
SU2_ARGS=( -f "${CONFIG_FILE}" --parallel -d "${FLUID_DIM}" --precice-config "${PRECICE_CONFIG}" )

# --- mpirun 으로 지정 노드들에 MPI 분산 실행 ---------------------------------------
#  --host   : 위에서 만든 node15:20,node16:20 스펙 (mfile 미사용)
#  -x ...   : 원격 노드 rank 들에 SU2 + preCICE 런타임 환경 전달 (원격엔 env 가 로드 안 되므로 필수)
#  케이스 디렉토리(NFS 공유)는 mpirun 이 원격 wdir 로 설정 -> SU2_preCICE_FSI.py 상대경로 OK
# shellcheck disable=SC2086
mpirun --host "${HOST_SPEC}" -np "${NPROC}" ${MPIRUN_EXTRA} \
    -x PATH -x LD_LIBRARY_PATH -x PYTHONPATH -x LIBRARY_PATH -x CPATH \
    -x PKG_CONFIG_PATH -x PRECICE_ROOT -x BOOST_ROOT -x PETSC_ROOT \
    -x OPENMPI_ROOT -x SU2_RUN -x CONDA_PREFIX -x CONDA_DEFAULT_ENV -x PRECICE_CONFIG \
    -x OMP_NUM_THREADS -x OPENBLAS_NUM_THREADS -x MKL_NUM_THREADS \
    -x BLIS_NUM_THREADS -x VECLIB_MAXIMUM_THREADS -x NUMEXPR_NUM_THREADS \
    "${PYTHON_BIN}" SU2_preCICE_FSI.py "${SU2_ARGS[@]}"
