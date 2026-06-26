#!/usr/bin/env python3
# coding=utf-8
"""Solid-only Code_Aster transient run.

This runs the Turek-Hron beam without preCICE and without fluid loading.
By default the shell scripts set a small initial transverse velocity so the
beam free vibration can be checked from the CSV/MED output.
"""

import csv
import os
import sys
from pathlib import Path

import numpy as np
from code_aster import CA

from solid_config import SolidConfig


def init_code_aster():
    sys.argv = [sys.argv[0], "--memory", "16384", "--tpmax", "2592000"]
    CA.init()


def _field_values_at_node(result, field_name, t, node, comp_names):
    field = result.getField(field_name, value=float(t), para="INST").toSimpleFieldOnNodes()
    vals, _ = field.getValues(copy=True)
    comps = list(field.getComponents())
    return [float(vals[node, comps.index(comp)]) for comp in comp_names]


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


def _zero_row(context, t, step, probe_coord):
    return {
        "step": int(step),
        "time": float(t),
        "probe_x": float(probe_coord[0]),
        "probe_y": float(probe_coord[1]),
        "ux": 0.0,
        "uy": 0.0,
        "vx": 0.0,
        "vy": 0.0,
        "ax": 0.0,
        "ay": 0.0,
        "max_abs_u": 0.0,
        "mean_abs_u": 0.0,
    }


def _result_row(context, result, t, step, probe_node, probe_coord):
    from solid_solver import interface_displacements

    ux, uy = _field_values_at_node(result, "DEPL", t, probe_node, context.config.comp)
    vx, vy = _field_values_at_node(result, "VITE", t, probe_node, context.config.comp)
    ax, ay = _field_values_at_node(result, "ACCE", t, probe_node, context.config.comp)
    disp = interface_displacements(context, result, t)
    norms = np.linalg.norm(disp, axis=1)
    return {
        "step": int(step),
        "time": float(t),
        "probe_x": float(probe_coord[0]),
        "probe_y": float(probe_coord[1]),
        "ux": ux,
        "uy": uy,
        "vx": vx,
        "vy": vy,
        "ax": ax,
        "ay": ay,
        "max_abs_u": float(norms.max()) if norms.size else 0.0,
        "mean_abs_u": float(norms.mean()) if norms.size else 0.0,
    }


def main():
    config = SolidConfig.from_env()
    os.chdir(config.case_dir)
    init_code_aster()

    from solid_initial import build_initial_velocity
    from solid_model import build_solid_context
    from solid_output import stitch_med_series, write_window_med
    from solid_solver import solve_window

    try:
        context = build_solid_context(config)
        dt = config.transient_dt
        n_steps = config.transient_steps
        save_every = config.transient_save_every
        out = Path(config.transient_csv)
        csv_fsync = config.transient_csv_fsync
        zero_forces = np.zeros((context.n_iface, config.dim), dtype=np.float64)
        probe_node, probe_coord = _probe_node(context)
        init_vite = build_initial_velocity(context)

        print("=" * 62, flush=True)
        print("  run_solid_only.py - Code_Aster solid-only transient", flush=True)
        print(f"  mesh       = {config.mesh_file}", flush=True)
        print(f"  dt         = {dt:g}", flush=True)
        print(f"  steps      = {n_steps}", flush=True)
        print(f"  save_every = {save_every}", flush=True)
        print(f"  output     = {out}", flush=True)
        print(f"  csv_fsync  = {int(csv_fsync)}", flush=True)
        print(f"  perturb_v  = {config.perturb_vel:g}", flush=True)
        print(f"  gravity    = {config.gravity:g} dir={config.gravity_dir}", flush=True)
        print(f"  OMP_NUM_THREADS = {os.environ.get('OMP_NUM_THREADS', '?')}", flush=True)
        print("=" * 62, flush=True)

        fields = [
            "step",
            "time",
            "probe_x",
            "probe_y",
            "ux",
            "uy",
            "vx",
            "vy",
            "ax",
            "ay",
            "max_abs_u",
            "mean_abs_u",
        ]
        result = None
        t = 0.0

        with out.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerow(_zero_row(context, t, 0, probe_coord))
            f.flush()
            if csv_fsync:
                os.fsync(f.fileno())

            for step in range(1, n_steps + 1):
                result = solve_window(context, zero_forces, result, t, t + dt, init_vite=init_vite)
                init_vite = None
                t += dt
                row = _result_row(context, result, t, step, probe_node, probe_coord)
                writer.writerow(row)
                f.flush()
                if csv_fsync:
                    os.fsync(f.fileno())

                write_window_med(config, result, step, t, save_every=save_every)
                print(
                    f"[SolidOnly] step={step:5d} t={t:.6f} "
                    f"ux={row['ux']:.6e} uy={row['uy']:.6e} "
                    f"max|u|={row['max_abs_u']:.6e}",
                    flush=True,
                )
        print(f"[SolidOnly] wrote {out}", flush=True)

        try:
            stitch_med_series(config)
        except Exception as exc:
            print(f"[SolidOnly] stitch 실패: {exc}", flush=True)
    finally:
        CA.close()


if __name__ == "__main__":
    main()
