
python3 prepare_restart.py --fresh --total 0.004
으로 fresh start의 경우 --total타임을 정해줘서 

precice-config.xml
fluid/config_fluid_run.cfg
을 수정해서 만들어줌 (dt나 기존 옵션들 iteration같은거는 config_fluid.cfg 나 precice-config.base.xml은 직접 수정해야함)

디폴트는 fresh이고 total time은 15초 precice-config.xml에있는 값

---

cd fluid

python make_inlet.py를 이용해서 기존에 있는 fluid.su2를 이용한 boundary condition(parabolic)을 만들어줌

CONFIG_FILE=config_fluid_restart.cfg ./run.sh로 실행해줌

옵션:

FLUID_NPROC
  기본값: 8
  의미: 로컬 MPI rank 개수.
  예: FLUID_NPROC=4 ./run.sh

SU2_ENV_FILE
  기본값: ~/envs/su2_precice_751.sh
  의미: SU2 7.5.1 + pysu2 + preCICE 환경을 source할 파일.

PRECICE_CONFIG
  기본값: ../precice-config.xml
  의미: 사용할 preCICE config 파일.

FLUID_DIM
  기본값: 2
  의미: SU2 adapter에 넘기는 차원. Turek-Hron 2D라 보통 2 고정.

CONFIG_FILE
  기본값: config_fluid.cfg
  의미: SU2 config 파일.
  fresh에서는 config_fluid_run.cfg
  restart에서는 config_fluid_restart.cfg 권장.

PYTHON_BIN
  기본값: python3
  의미: SU2_preCICE_FSI.py를 실행할 Python.

MPIRUN_EXTRA
  기본값: --bind-to none --oversubscribe
  의미: mpirun에 추가로 넘길 옵션.

---
그리고 그 하부 SU2_preCICE_FSI.py가 읽는 옵션
FLUID_RESTART
  기본값: 0
  fresh면 0 또는 생략.
  restart면 1.
  1이면 restart/에 저장된 reference interface coordinates를 다시 읽어서,
  코어 수가 바뀌어도 preCICE interface 좌표를 reference 기준으로 맞춤.

FLUID_RESTART_DIR
  기본값: ../restart
  의미: fluid reference coordinate와 solid manifest가 있는 restart 디렉토리.

FLUID_KEEP_RESTART
  기본값: 1
  의미: time window가 완료될 때 오래된 restart_flow_*.dat를 정리할지 여부.

FLUID_RESTART_KEEP
  기본값: 3
  의미: 최신 restart_flow_*.dat를 몇 개 보관할지.
  BDF2 restart에는 최소 2개 연속 파일이 필요해서 기본 3으로 둠.

FLUID_INLET_RAMP
  기본값: 0
  의미: inlet ramp 사용 여부.

FLUID_INLET_RAMP_TIME
  기본값: 2.0
  의미: inlet velocity가 0에서 원래 profile까지 올라가는 시간.
  factor = 0.5 * (1 - cos(pi * t / ramp_time)).
  ramp_time 이후에는 factor=1.

FLUID_INLET_RAMP_MARKER
  기본값: inlet
  의미: ramp를 적용할 SU2 marker 이름.

FLUID_INLET_RAMP_LOG
  기본값: 0
  의미: 매 time step ramp factor를 로그로 출력할지 여부.

---

cd solid

SOLID_RESTART=1 ./run.sh (restart할꺼면)


run.sh에서 받는 옵션

SOLID_OMP_THREADS
  기본값: 10
  의미: Code_Aster 계산에 사용할 OpenMP thread 수.
  예: SOLID_OMP_THREADS=8 ./run.sh

PRECICE_CONFIG
  기본값: ../precice-config.xml
  의미: 사용할 preCICE config 파일.

SOLID_CLEAN
  기본값: 1
  의미: 실행 시작 전에 이전 Code_Aster 잔재 파일을 지울지 여부.
  지우는 파일: glob.*, vola.*, pick.code_aster.*, fort.*, *.mess, solid_*.med
  0이면 안 지움.

ENV_FILE
  기본값: ~/envs/codeaster_precice311.sh
  의미: Code_Aster + preCICE Python 환경을 source할 파일.

---
그리고 진짜 실행파일 run_solid.py 와 solid_config.py(파라미터 수정용)가 읽는 옵션

SOLID_RESTART
  기본값: 0
  fresh면 0 또는 생략.
  restart면 1.
  1이면 restart/solid_manifest.json을 읽고, 거기에 적힌 checkpoint MED에서 이어서 시작.

SOLID_RESTART_DIR
  기본값: ../restart
  의미: solid checkpoint와 manifest가 저장되는 디렉토리.

SOLID_CKPT_EVERY
  기본값: 1
  의미: 몇 time window마다 solid checkpoint를 저장할지.
  1이면 매 window마다 저장.

SOLID_CKPT_KEEP
  기본값: 2
  의미: versioned solid checkpoint를 몇 개 유지할지.
  예: solid_ckpt_00004.med, solid_ckpt_00005.med처럼 최신 2개 유지.

MESH_FILE
  기본값: beam.med
  의미: 고체 mesh 입력 파일.

RESULT_FILE
  기본값: run_solid_result.med
  의미: 마지막에 solid_*.med들을 stitch할 때 만드는 병합 결과 파일 이름.

SOLID_PERTURB_VEL
  기본값: 0
  의미: fresh start에서 초기 속도 perturbation을 줄 때 쓰는 값.
  일반 실행에서는 생략하면 됨.

FLUID_RESTART_KEEP >= SOLID_CKPT_EVERY + 2 규칙 꼭 기억(안그러면 restart가 깨짐)


---

적절한 restart가 (manifest(물리시간)으로 restart 디렉토리에 남음, 물리시간t(고체기준)으로 t-1 t-2 유체의 restart파일이 필요함)

**그리고 history나 precice-*파일들은 따로 백업을 꼭해줘야함**

python3 prepare_restart.py --total 0.008
--total타임을 정해주면 

precice-config.xml
fluid/config_fluid_run.cfg

이걸 수정해줌 

그리고 다시 solid와 fluid로 가서 옵션에 맞게 run.sh를 돌려주면 됨

---
job_cluster.sh와 job_restart_cluster.sh의 경우는 qsub로 fresh start랑 restart용

qsub로 노드를 지정해주고 
#$ -N th2frere
#$ -q all.q@node12,all.q@node14,all.q@node15,all.q@node16 [[cluster macro 돌릴때 참고]] [[qsub]]
#$ -pe mpi_20 80


run_fluid_cluster.sh는 cluster용 run.sh
run_solid_cluster.sh는 cluster용 run.sh

---


FLUID_RESTART=1 CONFIG_FILE=config_fluid_restart.cfg ./run_fluid_cluster.sh

FLUID_HOST_SPEC
  기본값: 없음
  의미: 노드별 MPI rank 수를 직접 지정.
  예: FLUID_HOST_SPEC="node12:18,node14:20,node15:20,node16:20"
  **이 값이 있으면 FLUID_NODES / FLUID_SLOTS_PER_NODE보다 우선함.**

FLUID_NODES
  기본값: node12
  의미: 사용할 노드 목록. 공백으로 구분.
  예: FLUID_NODES="node12 node14 node15 node16"

FLUID_SLOTS_PER_NODE
  기본값: 16
  의미: 각 노드에서 띄울 MPI rank 수.
  예: FLUID_SLOTS_PER_NODE=20
  auto로 두면 qhost에서 노드 코어 수를 읽음.

FLUID_CPU_LIST
  기본값: 0,1,2,...,15
  의미: OpenMPI --cpu-list에 넘기는 CPU list.
  MPIRUN_EXTRA 기본값 안에서 사용됨.

SU2_ENV_FILE
  기본값: ~/envs/su2_precice_751_custom.sh
  의미: SU2 + pysu2 + preCICE 환경을 source할 파일.

PRECICE_CONFIG
  기본값: ../precice-config.xml
  의미: 사용할 preCICE config.

FLUID_DIM
  기본값: 2
  의미: SU2 adapter에 넘길 차원.

SU2_MARKER
  기본값: beam_wet
  의미: 현재 스크립트에서는 로그용에 가깝고, 실제 SU2_preCICE_FSI.py에는 --su2-marker로 넘기지 않음.

PYTHON_BIN
  기본값: python3
  의미: SU2_preCICE_FSI.py 실행에 사용할 Python.

MPIRUN_EXTRA
  기본값: --bind-to cpu-list:ordered --cpu-list ${FLUID_CPU_LIST}
  의미: mpirun에 추가로 넘길 binding 옵션.
  job_cluster.sh에서는 보통 MPIRUN_EXTRA="--bind-to core"로 덮어씀.

CONFIG_FILE
  기본값: config_fluid.cfg
  의미: 사용할 SU2 config.
  fresh: config_fluid_run.cfg
  restart: config_fluid_restart.cfg

---


SOLID_RESTART=1 ./run_solid_cluster.sh


SOLID_NODE
  기본값: node12
  의미: solid participant를 실행할 노드.
  예: SOLID_NODE=node16 ./run_solid_cluster.sh

SOLID_OMP_THREADS
  기본값: 2
  의미: Code_Aster가 사용할 OpenMP thread 수.
  예: SOLID_OMP_THREADS=4 ./run_solid_cluster.sh
  auto로 두면 qhost에서 SOLID_NODE의 물리코어 수를 읽어 사용.

SOLID_CPU_SET
  기본값: 13,15
  의미: taskset으로 solid process/thread를 묶을 OS CPU 번호.
  예: SOLID_CPU_SET=18,19 ./run_solid_cluster.sh

PRECICE_CONFIG
  기본값: ../precice-config.xml
  의미: 사용할 preCICE config.

SOLID_CLEAN
  기본값: 1
  의미: 실행 시작 전에 이전 Code_Aster 잔재 파일을 지울지 여부.
  지우는 파일:
    glob.*, vola.*, pick.code_aster.*, fort.*, *.mess, solid_*.med
  0이면 안 지움.

ENV_FILE
  기본값: ~/envs/codeaster_precice.sh
  의미: Code_Aster + preCICE 환경을 source할 파일.

SOLID_OPENMPI_ROOT
  기본값: /home/hilbert/opt/openmpi-4.1.1
  의미: solid remote placement에 사용할 OpenMPI root.

SOLID_MPIRUN_BIN
  기본값: ${SOLID_OPENMPI_ROOT}/bin/mpirun
  의미: 사용할 mpirun 실행 파일.

MPIRUN_EXTRA
  기본값: --mca btl ^openib
  의미: mpirun에 추가로 넘길 옵션.


----


지금은 bind to core로 되어있는거고 
FLUID_CPU_LIST="0,1,2,3,4,5,6,7" 
MPIRUN_EXTRA="--bind-to cpu-list:ordered --cpu-list ${FLUID_CPU_LIST}" 이렇게 하면 
유체랑 고체랑 둘다 신경써줘야함


유체랑 고체랑 겹치면 안되고
가능하면 같은 socket 안에 묶기

짝수 core = socket 0
홀수 core = socket 1
이런식으로(노드마다 다르니까 lscpu로 확인하고 )

