# coding=utf-8
"""Shared HHT restart-checkpoint I/O for the Code_Aster "Solid" participant.

Validated bit-for-bit by solid_restart_test.py (restart leg reproduces the
single-run baseline to 0.0000 %).  Imported by BOTH that harness and the live
run_solid.py so the two share exactly one code path.

KEY FINDING (measured, not assumed): for GREEN_LAGRANGE large strain the
DEPL/VITE/ACCE triple is NOT sufficient — omitting the Gauss-point stress field
SIEF_ELGA leaves a ~6 % drift after restart.  ETAT_INIT=_F(EVOL_NOLI=...) pulls
SIEF_ELGA (and VARI_ELGA) too, so the checkpoint MUST carry all five fields at a
single consistent instant t_R.

Restore path reuses the in-run chaining exactly:
    LIRE_RESU(5 fields) -> EVOL_NOLI  ->  solve_window(..., prev_result=that)
so solve_window itself needs no change.
"""

import os
import re
import json
from pathlib import Path

from code_aster.Commands import IMPR_RESU, LIRE_RESU, DEFI_FICHIER
from code_aster.Cata.Syntax import _F

# Consistent state of a dynamic GREEN_LAGRANGE step.  Order is irrelevant but the
# five must all be present and taken at the SAME instant t_R.
CKPT_FIELDS = ("DEPL", "VITE", "ACCE", "SIEF_ELGA", "VARI_ELGA")


def checkpoint_path_for_step(base_path, step):
    """Return a versioned checkpoint path such as solid_ckpt_00042.med."""
    base = Path(base_path)
    suffix = base.suffix or ".med"
    return base.with_name(f"{base.stem}_{int(step):05d}{suffix}")


def save_checkpoint(result, t, path, unit=80):
    """Write the 5-field consistent state at instant ``t`` to ``path`` (MED).

    Atomic: writes a sibling ``*.tmp`` then os.replace()s it onto ``path`` so a
    crash mid-write cannot corrupt the previous good checkpoint (we keep only the
    latest one for run-extension, so that one good copy must never be lost).
    """
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    DEFI_FICHIER(ACTION="ASSOCIER", UNITE=unit, TYPE="BINARY", ACCES="NEW", FICHIER=str(tmp))
    try:
        IMPR_RESU(FORMAT="MED", UNITE=unit,
                  RESU=_F(RESULTAT=result, NOM_CHAM=CKPT_FIELDS, NOM_CHAM_MED=CKPT_FIELDS,
                          INST=(float(t),), CRITERE="RELATIF", PRECISION=1.0e-6))
    finally:
        DEFI_FICHIER(ACTION="LIBERER", UNITE=unit)
    os.replace(str(tmp), str(path))   # atomic swap of the latest checkpoint


def prune_checkpoints(base_path, keep=2, protect=()):
    """Keep only the newest ``keep`` versioned solid checkpoints."""
    base = Path(base_path)
    suffix = base.suffix or ".med"
    pat = re.compile(rf"^{re.escape(base.stem)}_(\d+){re.escape(suffix)}$")
    protected = {Path(p).resolve() for p in protect}
    indexed = []
    for p in base.parent.glob(f"{base.stem}_*{suffix}"):
        m = pat.match(p.name)
        if m:
            indexed.append((int(m.group(1)), p))
    indexed.sort(key=lambda item: item[0])
    keep = max(int(keep), 0)
    for _, p in indexed[:-keep]:
        if p.resolve() in protected:
            continue
        try:
            p.unlink()
        except OSError:
            pass
    return [p.name for _, p in indexed[-keep:]]


def save_numbered_checkpoint(result, t, base_path, manifest_path, step, keep=2, unit=80):
    """Save a versioned checkpoint and atomically point the manifest to it.

    If Ctrl-C happens after writing the new MED but before the manifest update,
    the old manifest still points to the previous complete MED.
    """
    checkpoint = checkpoint_path_for_step(base_path, step)
    save_checkpoint(result, t, checkpoint, unit=unit)
    write_manifest(
        manifest_path,
        step,
        t,
        checkpoint,
        extra={"solid_checkpoint_keep": int(keep)},
    )
    prune_checkpoints(base_path, keep=keep, protect=(checkpoint,))
    return checkpoint


def load_checkpoint(path, model, fmat, unit=81):
    """Rebuild an EVOL_NOLI from a 5-field checkpoint MED, ready for ETAT_INIT."""
    DEFI_FICHIER(ACTION="ASSOCIER", UNITE=unit, TYPE="BINARY", ACCES="OLD", FICHIER=str(path))
    try:
        res = LIRE_RESU(
            TYPE_RESU="EVOL_NOLI", FORMAT="MED",
            MODELE=model, CHAM_MATER=fmat,
            COMPORTEMENT=_F(RELATION="ELAS", DEFORMATION="GREEN_LAGRANGE"),
            UNITE=unit, TOUT_ORDRE="OUI",
            FORMAT_MED=tuple(_F(NOM_CHAM=f, NOM_CHAM_MED=f) for f in CKPT_FIELDS),
        )
    finally:
        DEFI_FICHIER(ACTION="LIBERER", UNITE=unit)
    return res


def write_manifest(path, step, t, checkpoint_file, extra=None):
    """Single source of truth tying the solid checkpoint to (window k, t_R).

    The fluid side restarts from the SAME t_R, so this t/step must match the
    fluid checkpoint's.  Written atomically like the checkpoint itself.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"step": int(step), "t": float(t), "solid_checkpoint": str(checkpoint_file)}
    if extra:
        data.update(extra)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(str(tmp), str(path))


def read_manifest(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text())
