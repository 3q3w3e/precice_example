#!/usr/bin/env python3
# coding=utf-8
"""Run the solid-only static nonlinear equilibrium solve."""

import os
import sys

import numpy as np
from code_aster import CA

from solid_config import SolidConfig


def init_code_aster():
    sys.argv = [sys.argv[0], "--memory", "16384", "--tpmax", "2592000"]
    CA.init()


def _probe_node(context):
    target = np.array(
        [
            context.config.probe_x,
            context.config.probe_y,
        ],
        dtype=np.float64,
    )
    local = int(np.argmin(np.linalg.norm(context.iface_coords - target, axis=1)))
    return int(context.iface_nodes[local]), context.iface_coords[local]


def main():
    config = SolidConfig.from_env()
    os.chdir(config.case_dir)
    init_code_aster()

    from solid_model import build_solid_context
    from solid_solver_stead import solve_static, write_probe_csv, write_static_med

    try:
        context = build_solid_context(config)
        solver = config.steady_solver
        load_level = config.steady_load_level
        n_steps = config.steady_steps
        med_file = config.steady_med
        csv_file = config.steady_csv
        probe_node, probe_coord = _probe_node(context)

        print("=" * 62, flush=True)
        print("  run_solid_stead.py - Code_Aster static solve", flush=True)
        print(f"  mesh       = {config.mesh_file}", flush=True)
        print(f"  solver     = {solver}", flush=True)
        print(f"  load_level = {load_level:g}", flush=True)
        print(f"  steps      = {n_steps}", flush=True)
        print(f"  gravity    = {config.gravity:g} dir={config.gravity_dir}", flush=True)
        print(f"  probe      = ({probe_coord[0]:.6g}, {probe_coord[1]:.6g})", flush=True)
        print(f"  med        = {med_file}", flush=True)
        print(f"  csv        = {csv_file}", flush=True)
        print(f"  OMP_NUM_THREADS = {os.environ.get('OMP_NUM_THREADS', '?')}", flush=True)
        print("=" * 62, flush=True)

        result = solve_static(context, solver=solver, load_level=load_level, n_steps=n_steps)
        med_path = write_static_med(context, result, filename=med_file)
        csv_path, row = write_probe_csv(
            context,
            result,
            probe_node,
            probe_coord,
            filename=csv_file,
            load_level=load_level,
        )
        print(
            f"[SolidStead] ux={row['ux']:.6e} uy={row['uy']:.6e} "
            f"x={row['x']:.6e} y={row['y']:.6e} max|u|={row['max_abs_u']:.6e}",
            flush=True,
        )
        print(f"[SolidStead] wrote {med_path}", flush=True)
        print(f"[SolidStead] wrote {csv_path}", flush=True)
    finally:
        CA.close()


if __name__ == "__main__":
    main()
