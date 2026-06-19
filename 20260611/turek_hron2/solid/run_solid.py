#!/usr/bin/env python3
# coding=utf-8
"""
run_solid.py — preCICE "Solid" participant  (Code_Aster, 2D C_PLAN, OMP-only)

wall&ramm FSI 벤치마크의 구조(Solid) 쪽.
유체(SU2)가 보내는 계면 힘 Force 를 받아 Code_Aster DYNA_NON_LINE 으로 풀고,
계면 변위 Displacement 를 유체에 돌려준다.

이 파일은 실행 순서만 담당한다. 세부 구현은 다음 모듈로 분리되어 있다.
  solid_config.py      환경변수/경로/상수
  solid_model.py       mesh, model, material, boundary condition
  solid_solver.py      force load, one-window solve, displacement extraction
  solid_initial.py     fresh-start perturbation
  solid_output.py      MED output/stitch
  solid_coupling.py    preCICE implicit coupling loop
  solid_checkpoint.py  restart checkpoint I/O
"""

import os
import sys

from code_aster import CA

from solid_config import SolidConfig


def init_code_aster():
    # code_aster 메모리/CPU시간 한도 — 이 빌드는 CA.init(argv)/set_option 둘 다
    # 무시하므로, init 전에 sys.argv 를 직접 세팅해야만 실제 풀에 반영된다.
    sys.argv = [sys.argv[0], "--memory", "16384", "--tpmax", "2592000"]
    CA.init()


def print_banner(config: SolidConfig):
    print("=" * 62)
    print("  run_solid.py — preCICE Solid participant (Code_Aster, 2D)")
    print(f"  config = {config.precice_config}")
    print(f"  mesh   = {config.mesh_file}")
    print(f"  OMP_NUM_THREADS = {os.environ.get('OMP_NUM_THREADS', '?')}")
    print("=" * 62, flush=True)


def main():
    config = SolidConfig.from_env()
    os.chdir(config.case_dir)
    init_code_aster()
    print_banner(config)

    # Import after CA.init() so Code_Aster command modules are loaded in the
    # same order as the runtime setup.
    from solid_coupling import run_coupling
    from solid_model import build_solid_context

    try:
        context = build_solid_context(config)
        run_coupling(config, context)
    finally:
        CA.close()


if __name__ == "__main__":
    main()
