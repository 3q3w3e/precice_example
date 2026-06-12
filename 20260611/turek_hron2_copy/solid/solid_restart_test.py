#!/usr/bin/env python3
# coding=utf-8
"""Standalone HHT restart-mechanism test for the Code_Aster "Solid" participant.

NO preCICE.  Prescribes a ramped transverse force on the FSI interface (beam_wet)
and marches DYNA_NON_LINE windows exactly like run_solid.py, to validate that a
DEPL/VITE/ACCE MED checkpoint reloads HHT dynamics WITHOUT a restart shock.

The physics setup (mesh/model/material/clamp), build_force_load, solve_window and
interface_displacements are copied verbatim from run_solid.py so that what we
validate here is byte-for-byte the path that will run under preCICE.

Restart path under test:
  save  -> IMPR_RESU writes DEPL+VITE+ACCE at the SAME instant t_R (consistent triple)
  load  -> LIRE_RESU rebuilds an EVOL_NOLI; fed to the EXISTING
           solve_window(..., prev_result=...) via ETAT_INIT=_F(EVOL_NOLI=...).
  => solve_window itself is unchanged; restore reuses the in-run chaining path.

Modes (fixed dt):
  baseline : python solid_restart_test.py --t-end 0.20 --out base.csv \
                    [--save-at 0.10 --save-ckpt ckpt.med]
  leg1     : python solid_restart_test.py --t-end 0.10 --save-at 0.10 \
                    --save-ckpt ckpt.med --out leg1.csv
  leg2     : python solid_restart_test.py --restart-from ckpt.med --restart-t 0.10 \
                    --t-end 0.20 --out leg2.csv
Then compare base.csv with leg1+leg2 concatenated (tip DY vs time).
"""

import os
import sys
import argparse
from pathlib import Path

import numpy as np

# ---- CLI (parsed BEFORE CA.init: this build reads sys.argv for --memory/--tpmax) ----
_ap = argparse.ArgumentParser()
_ap.add_argument("--dt", type=float, default=0.002)
_ap.add_argument("--t-end", type=float, default=0.20)
_ap.add_argument("--save-at", type=float, default=None, help="instant to drop a checkpoint")
_ap.add_argument("--save-ckpt", default="ckpt.med")
_ap.add_argument("--stop-at-save", action="store_true", help="leg1: stop right after saving")
_ap.add_argument("--restart-from", default=None, help="checkpoint MED to resume from")
_ap.add_argument("--restart-t", type=float, default=0.0, help="t_R that the checkpoint holds")
_ap.add_argument("--out", default="tip.csv")
_ap.add_argument("--fy", type=float, default=2.0, help="total transverse force (ramped)")
_ap.add_argument("--t-ramp", type=float, default=0.02, help="force ramp time")
_ap.add_argument("--ca-memory", default="4096")
_ap.add_argument("--ca-tpmax", default="3600")
OPT = _ap.parse_args()

sys.argv = [sys.argv[0], "--memory", OPT.ca_memory, "--tpmax", OPT.ca_tpmax]

from code_aster import CA
from code_aster.Commands import *

import solid_checkpoint as sc   # the functions under test (shared with run_solid.py)

CA.init()

# ============ constants (identical to run_solid.py) ============
CASE_DIR = Path(__file__).resolve().parent
os.chdir(CASE_DIR)

MESH_FILE = "beam.med"
VOLUME_GMA = "beam"
IFACE_GMA = "beam_wet"
CLAMP_GMA = "beam_fixed"
IFACE_GNO = "beam_wet_no"
E_MOD, NU, RHO = 1.4e6, 0.40, 1.0e4
MESH_UNIT = 20
DIM = 2
COMP = ("DX", "DY")

# ============ mesh / model / material / clamp ============
DEFI_FICHIER(ACTION="ASSOCIER", UNITE=MESH_UNIT, TYPE="BINARY",
             ACCES="OLD", FICHIER=str(CASE_DIR / MESH_FILE))
mesh = LIRE_MAILLAGE(UNITE=MESH_UNIT, FORMAT="MED", VERI_MAIL=_F(VERIF="OUI"))
mesh = DEFI_GROUP(reuse=mesh, MAILLAGE=mesh,
                  CREA_GROUP_NO=_F(NOM=IFACE_GNO, GROUP_MA=IFACE_GMA))
model = AFFE_MODELE(MAILLAGE=mesh,
    AFFE=_F(GROUP_MA=VOLUME_GMA, PHENOMENE="MECANIQUE", MODELISATION="C_PLAN"))
mat = DEFI_MATERIAU(ELAS=_F(E=E_MOD, NU=NU, RHO=RHO))
fmat = AFFE_MATERIAU(MAILLAGE=mesh, AFFE=_F(GROUP_MA=VOLUME_GMA, MATER=mat))
fix = AFFE_CHAR_MECA(MODELE=model, DDL_IMPO=_F(GROUP_MA=CLAMP_GMA, DX=0.0, DY=0.0))

# interface nodes + coords
iface_nodes = np.asarray(mesh.getNodes(IFACE_GNO, localNumbering=True), dtype=np.int64)
n_iface = iface_nodes.size
_coord = mesh.getCoordinatesAsSimpleFieldOnNodes()
_cvals, _ = _coord.getValues(copy=True)
_cc = list(_coord.getComponents())
iface_coords = np.column_stack([_cvals[iface_nodes, _cc.index("X")],
                                _cvals[iface_nodes, _cc.index("Y")]]).astype(np.float64)
tip_idx = int(np.argmax(iface_coords[:, 0]))   # node closest to flap tip (max x)
print(f"[test] interface nodes={n_iface}  tip node local#={iface_nodes[tip_idx]} "
      f"at ({iface_coords[tip_idx,0]:.4f},{iface_coords[tip_idx,1]:.4f})", flush=True)


# ============ helpers (copied from run_solid.py) ============
def build_force_load(forces):
    f = CA.SimpleFieldOnNodesReal(mesh, "DEPL_R", COMP, True)
    f.setValues(0.0)
    nodes = np.repeat(iface_nodes, DIM)
    cps = np.tile(np.asarray(COMP, dtype=object), n_iface)
    f.setValues([int(x) for x in nodes],
                [str(x) for x in cps],
                [float(x) for x in np.asarray(forces, np.float64).ravel()])
    return AFFE_CHAR_MECA(MODELE=model, VECT_ASSE=f.toFieldOnNodes())


def solve_window(forces, prev_result, t0, t1):
    load = build_force_load(forces)
    tlist = DEFI_LIST_REEL(VALE=(t0, t1))
    kw = dict(
        MODELE=model, CHAM_MATER=fmat,
        EXCIT=(_F(CHARGE=fix), _F(CHARGE=load)),
        COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
        INCREMENT=_F(LIST_INST=tlist),
        SCHEMA_TEMPS=_F(SCHEMA="HHT", FORMULATION="DEPLACEMENT", ALPHA=-0.1),
        NEWTON=_F(MATRICE="TANGENTE", REAC_ITER=1),
        SOLVEUR=_F(METHODE="MUMPS"),
        CONVERGENCE=_F(ITER_GLOB_MAXI=80, RESI_GLOB_RELA=1.0e-6, RESI_GLOB_MAXI=1.0e-9),
    )
    if prev_result is not None:
        kw["ETAT_INIT"] = _F(EVOL_NOLI=prev_result)
    return DYNA_NON_LINE(**kw)


def interface_displacements(result, t):
    field = None
    for para, val in (("INST", float(t)), ("NUME_ORDRE", 2), ("NUME_ORDRE", 1)):
        try:
            field = result.getField("DEPL", value=val, para=para).toSimpleFieldOnNodes()
            break
        except Exception:
            continue
    if field is None:
        raise RuntimeError("변위장 추출 실패")
    vals, _ = field.getValues(copy=True)
    cc = list(field.getComponents())
    return np.column_stack([vals[iface_nodes, cc.index("DX")],
                            vals[iface_nodes, cc.index("DY")]]).astype(np.float64)


# ============ checkpoint save / load: imported from the SHARED module ========
# save_checkpoint / load_checkpoint live in solid_checkpoint.py so that this
# harness validates exactly the code run_solid.py uses.  Re-running this test to
# 0.0000 % is therefore a regression check of the ported functions.


# ============ prescribed force ============
def prescribed_forces(t):
    """Ramped transverse total force Fy, distributed equally over interface nodes."""
    ramp = min(1.0, t / OPT.t_ramp) if OPT.t_ramp > 0 else 1.0
    fy_node = OPT.fy * ramp / n_iface
    forces = np.zeros((n_iface, DIM), dtype=np.float64)
    forces[:, 1] = fy_node
    return forces


# ============ time loop ============
dt = OPT.dt
if OPT.restart_from:
    result = sc.load_checkpoint(OPT.restart_from, model, fmat)
    print(f"[test] checkpoint loaded: {Path(OPT.restart_from).name}", flush=True)
    t = OPT.restart_t
    print(f"[test] RESUME from t={t:.4f} to t={OPT.t_end:.4f}", flush=True)
else:
    result, t = None, 0.0
    print(f"[test] BASELINE/LEG1 from t=0 to t={OPT.t_end:.4f}", flush=True)

rows = []
nsteps = int(round((OPT.t_end - t) / dt))
for _ in range(nsteps):
    t0, t1 = t, t + dt
    forces = prescribed_forces(t1)
    trial = solve_window(forces, result, t0, t1)
    disp = interface_displacements(trial, t1)
    result, t = trial, t1
    rows.append((t, float(disp[tip_idx, 1]), float(np.abs(disp[:, 1]).max())))

    if OPT.save_at is not None and abs(t - OPT.save_at) < 0.5 * dt:
        sc.save_checkpoint(trial, t, OPT.save_ckpt)
        print(f"[test] checkpoint saved: {Path(OPT.save_ckpt).name} (5 fields @ t={t:.4f})", flush=True)
        if OPT.stop_at_save:
            print(f"[test] stop-at-save: leg1 ends at t={t:.4f}", flush=True)
            break

with open(OPT.out, "w") as fh:
    fh.write("t,tip_dy,max_abs_dy\n")
    for r in rows:
        fh.write(f"{r[0]:.6f},{r[1]:.9e},{r[2]:.9e}\n")
print(f"[test] wrote {OPT.out}  ({len(rows)} windows, last tip_dy={rows[-1][1]:.6e})", flush=True)

CA.close()
