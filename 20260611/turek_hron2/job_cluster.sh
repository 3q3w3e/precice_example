#!/bin/bash
#$ -N th2frere
#$ -q all.q@node12,all.q@node14,all.q@node15,all.q@node16
#$ -pe mpi_20 80
#$ -j y
#$ -o /datanode/hilbert/su2/fsi/turek_hron2_lastlastlast/turek_hron2_dt0001_medium/turek_hron2_dt0002_fine_re_re/qsub.log
#$ -V
# ── preCICE FSI 단일 잡: fluid + solid 를 한 잡 안에서 동시 기동 ──
#    (fluid/solid 를 따로 qsub 하면 한쪽이 큐 대기 시 preCICE initialize 데드락)
#    노드/랭크/소켓(cpu-set)/OMP 배치는 각 fluid/run.sh, solid/run.sh 에 이미 박혀 있음.
set -u
export PATH="/home/hilbert/opt/openmpi-4.1.1/bin:$PATH"  # SGE+-V: conda mpirun 대신 openmpi-4.1.1 강제 (solid MPI_Init 실패 방지)
CASE="/datanode/hilbert/su2/fsi/turek_hron2_lastlastlast/turek_hron2_dt0001_medium/turek_hron2_dt0002_fine_re_re"
rm -rf "$CASE/precice-run"   # 이전 크래시가 남긴 preCICE 연결파일 제거(데드락 방지)
echo "[qsub] prepare_restart --fresh (config_fluid_run.cfg / precice-config.xml 재생성)"
python3 "$CASE/prepare_restart.py" --fresh || { echo "[qsub] prepare_restart FAILED"; exit 1; }
echo "[qsub] start $(date '+%F %T')  case=$(basename "$CASE")  exec_host=$(hostname)  NSLOTS=${NSLOTS:-?}  JOB_ID=${JOB_ID:-?}"
echo "[qsub] fluid+solid 동시 기동 (상세 로그: fluid/*log.txt , solid/run_*.log)"
FLUID_HOST_SPEC="node12:18,node14:20,node15:20,node16:20" MPIRUN_EXTRA="--bind-to core" CONFIG_FILE=config_fluid_run.cfg "$CASE/fluid/run.sh" >/dev/null 2>&1 &
FPID=$!
sleep 3
SOLID_NODE=node12 SOLID_OMP_THREADS=2 SOLID_CPU_SET=18,19 "$CASE/solid/run.sh" >/dev/null 2>&1 &
SPID=$!
wait "$FPID"; FRC=$?
wait "$SPID"; SRC=$?
echo "[qsub] end   $(date '+%F %T')  fluid_rc=$FRC  solid_rc=$SRC"
[ "$FRC" -eq 0 ] && [ "$SRC" -eq 0 ]
