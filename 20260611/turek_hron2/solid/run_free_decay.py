#!/usr/bin/env python3
# coding=utf-8
"""Solid-only free-decay test from a restart checkpoint.

This bypasses preCICE and the fluid entirely.  It loads the solid restart state
from restart/solid_manifest.json, applies zero interface force, and advances the
Code_Aster HHT dynamics for a short sequence of windows.  The expected physical
behavior is elastic return/free vibration about the undeformed equilibrium,
with numerical damping from HHT ALPHA=-0.1.
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
    out = []
    for comp in comp_names:
        out.append(float(vals[node, comps.index(comp)]))
    return out


def _probe_node(context):
    target = np.array(
        [
            float(os.environ.get("SOLID_PROBE_X", "0.6")),
            float(os.environ.get("SOLID_PROBE_Y", "0.2")),
        ],
        dtype=np.float64,
    )
    local = int(np.argmin(np.linalg.norm(context.iface_coords - target, axis=1)))
    return int(context.iface_nodes[local]), context.iface_coords[local]


def _row(context, result, t, step, probe_node, probe_coord):
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

    from solid_model import build_solid_context
    from solid_solver import interface_displacements, solve_window
    import solid_checkpoint as sc

    try:
        context = build_solid_context(config)
        manifest = sc.read_manifest(config.manifest_file)
        if manifest is None:
            raise RuntimeError(f"manifest 없음: {config.manifest_file}")

        result = sc.load_checkpoint(manifest["solid_checkpoint"], context.model, context.fmat)
        t = float(manifest["t"])
        step = int(manifest["step"])
        dt = float(os.environ.get("SOLID_FREE_DT", "0.002"))
        n_steps = int(os.environ.get("SOLID_FREE_STEPS", "20"))
        out = Path(os.environ.get("SOLID_FREE_OUT", "free_decay.csv"))
        zero_forces = np.zeros((context.n_iface, config.dim), dtype=np.float64)
        probe_node, probe_coord = _probe_node(context)

        print(
            f"[FreeDecay] restart step={step}, t={t:.6g}, "
            f"ckpt={Path(manifest['solid_checkpoint']).name}",
            flush=True,
        )
        print(
            f"[FreeDecay] zero interface force, dt={dt:g}, steps={n_steps}, "
            f"probe=({probe_coord[0]:.6g}, {probe_coord[1]:.6g})",
            flush=True,
        )

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
        rows = [_row(context, result, t, step, probe_node, probe_coord)]

        for _ in range(n_steps):
            result = solve_window(context, zero_forces, result, t, t + dt)
            t += dt
            step += 1
            rows.append(_row(context, result, t, step, probe_node, probe_coord))
            print(
                f"[FreeDecay] step={step:5d} t={t:.6f} "
                f"ux={rows[-1]['ux']:.6e} uy={rows[-1]['uy']:.6e} "
                f"max|u|={rows[-1]['max_abs_u']:.6e}",
                flush=True,
            )

        with out.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[FreeDecay] wrote {out}", flush=True)
    finally:
        CA.close()


if __name__ == "__main__":
    main()
