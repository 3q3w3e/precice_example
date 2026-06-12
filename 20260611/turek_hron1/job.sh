#!/bin/bash
#$ -N thfsi1
#$ -q all.q@node09
#$ -pe mpi_8 8
#$ -j y
#$ -o /home/hilbert/precice_example/20260611/turek_hron1/qsub.log
#$ -V
# ── preCICE FSI 단일 잡: fluid + solid 를 한 잡 안에서 동시 기동 ──
#    (fluid/solid 를 따로 qsub 하면 한쪽이 큐 대기 시 preCICE initialize 데드락)
#    노드/랭크/소켓(cpu-set)/OMP 배치는 각 fluid/run.sh, solid/run.sh 에 이미 박혀 있음.
set -u
export PATH="/home/hilbert/opt/openmpi-4.1.1/bin:$PATH"  # SGE+-V: conda mpirun 대신 openmpi-4.1.1 강제 (solid MPI_Init 실패 방지)
CASE="/home/hilbert/precice_example/20260611/turek_hron1"
rm -rf "$CASE/precice-run"   # 이전 크래시가 남긴 preCICE 연결파일 제거(데드락 방지)
echo "[qsub] start $(date '+%F %T')  case=$(basename "$CASE")  exec_host=$(hostname)  NSLOTS=${NSLOTS:-?}  JOB_ID=${JOB_ID:-?}"
echo "[qsub] fluid+solid 동시 기동 (상세 로그: fluid/*log.txt , solid/run_*.log)"
"$CASE/fluid/run.sh" >/dev/null 2>&1 &
FPID=$!
sleep 3
"$CASE/solid/run.sh" >/dev/null 2>&1 &
SPID=$!
wait "$FPID"; FRC=$?
wait "$SPID"; SRC=$?
echo "[qsub] end   $(date '+%F %T')  fluid_rc=$FRC  solid_rc=$SRC"
[ "$FRC" -eq 0 ] && [ "$SRC" -eq 0 ]
