# coding=utf-8
"""preCICE implicit-coupling loop for the solid participant."""

from datetime import datetime
from pathlib import Path

import numpy as np
import precice

import solid_checkpoint as sc
from solid_config import SolidConfig
from solid_initial import build_initial_velocity
from solid_model import SolidContext
from solid_output import stitch_med_series, write_window_med
from solid_solver import interface_displacements, solve_window


def _restore_or_start(config: SolidConfig, context: SolidContext):
    config.restart_dir.mkdir(parents=True, exist_ok=True)
    if not config.do_restart:
        return None, 0.0, 0

    manifest = sc.read_manifest(config.manifest_file)
    if manifest is None:
        raise RuntimeError(f"SOLID_RESTART=1 이지만 manifest 가 없음: {config.manifest_file}")

    result = sc.load_checkpoint(manifest["solid_checkpoint"], context.model, context.fmat)
    t = float(manifest["t"])
    step = int(manifest["step"])
    print(
        f"[Solid] RESTART: window {step}, t={t:.4f}s 에서 재개 "
        f"(ckpt={Path(manifest['solid_checkpoint']).name})",
        flush=True,
    )
    return result, t, step


def _solve_iteration(config, context, forces, result_ckp, t_ckp, dt, vite_init):
    if result_ckp is None and vite_init is not None:
        trial = solve_window(context, forces, None, t_ckp, t_ckp + dt, init_vite=vite_init)
        disp = interface_displacements(context, trial, t_ckp + dt)
    elif result_ckp is None and float(np.linalg.norm(forces)) <= config.zero_force_tol:
        trial = None
        disp = np.zeros((context.n_iface, config.dim), dtype=np.float64)
    else:
        trial = solve_window(context, forces, result_ckp, t_ckp, t_ckp + dt)
        disp = interface_displacements(context, trial, t_ckp + dt)
    return trial, disp


def run_coupling(config: SolidConfig, context: SolidContext):
    participant = precice.Participant(config.participant, config.precice_config, 0, 1)

    if participant.get_mesh_dimensions(config.mesh_name) != config.dim:
        raise RuntimeError(f"'{config.mesh_name}' 차원 불일치")

    vertex_ids = participant.set_mesh_vertices(config.mesh_name, context.iface_coords)
    result, t, step = _restore_or_start(config, context)
    vite_init = build_initial_velocity(context)

    if participant.requires_initial_data():
        if config.do_restart and result is not None:
            disp0 = interface_displacements(context, result, t)
        else:
            disp0 = np.zeros((context.n_iface, config.dim), dtype=np.float64)
        participant.write_data(config.mesh_name, config.write_data, vertex_ids, disp0)

    participant.initialize()

    result_ckp, t_ckp = result, t
    t_start = datetime.now()
    finalized = False

    print("[Solid] coupling 시작", flush=True)
    try:
        while participant.is_coupling_ongoing():
            if participant.requires_writing_checkpoint():
                result_ckp, t_ckp = result, t

            dt = participant.get_max_time_step_size()
            forces = participant.read_data(
                config.mesh_name,
                config.read_data,
                vertex_ids,
                dt,
            )

            trial, disp = _solve_iteration(
                config,
                context,
                forces,
                result_ckp,
                t_ckp,
                dt,
                vite_init,
            )

            participant.write_data(config.mesh_name, config.write_data, vertex_ids, disp)
            participant.advance(dt)

            if participant.requires_reading_checkpoint():
                result, t = result_ckp, t_ckp
            else:
                result, t = trial, t_ckp + dt
                if participant.is_time_window_complete():
                    step += 1
                    if trial is not None:
                        write_window_med(config, trial, step, t, save_every=40)
                        if config.ckpt_every > 0 and step % config.ckpt_every == 0:
                            ckpt = sc.save_numbered_checkpoint(
                                trial,
                                t,
                                config.checkpoint_file,
                                config.manifest_file,
                                step,
                                keep=config.ckpt_keep,
                            )
                            print(f"[Solid] checkpoint saved: {ckpt.name}", flush=True)
                    print(
                        f"[Solid] window {step:4d}  t={t:.4f}s  "
                        f"max|u|={np.linalg.norm(disp, axis=1).max():.3e}",
                        flush=True,
                    )

        if result is not None and config.ckpt_every > 0:
            ckpt = sc.save_numbered_checkpoint(
                result,
                t,
                config.checkpoint_file,
                config.manifest_file,
                step,
                keep=config.ckpt_keep,
            )
            print(
                f"[Solid] final checkpoint @ window {step}, t={t:.4f}s "
                f"({ckpt.name})",
                flush=True,
            )

        participant.finalize()
        finalized = True
    finally:
        if not finalized:
            try:
                participant.finalize()
            except Exception:
                pass
        elapsed = (datetime.now() - t_start).total_seconds()
        print(f"[Solid] 종료 — {step} window 완료, {elapsed:.1f}s", flush=True)
        try:
            stitch_med_series(config)
        except Exception as exc:
            print(f"[Solid] stitch 실패: {exc}", flush=True)
