# coding=utf-8
"""Static Code_Aster solve helpers for the solid-only case.

The filename keeps the requested ``stead`` spelling.  The solver itself is a
static nonlinear equilibrium solve using the same material, clamp, gravity, and
interface-load conventions as ``solid_solver.py``.
"""

import csv
from pathlib import Path

import numpy as np
from code_aster import CA
from code_aster.Cata.Syntax import _F
from code_aster.Commands import (
    AFFE_CHAR_MECA,
    DEFI_FONCTION,
    DEFI_FICHIER,
    DEFI_LIST_REEL,
    IMPR_RESU,
    MECA_STATIQUE,
    STAT_NON_LINE,
)

from solid_model import SolidContext


def build_force_load(context: SolidContext, forces):
    """Interface forces, shaped (n_iface, 2), as a Code_Aster load."""
    config = context.config
    f = CA.SimpleFieldOnNodesReal(context.mesh, "DEPL_R", config.comp, True)
    f.setValues(0.0)
    nodes = np.repeat(context.iface_nodes, config.dim)
    comps = np.tile(np.asarray(config.comp, dtype=object), context.n_iface)
    f.setValues(
        [int(x) for x in nodes],
        [str(x) for x in comps],
        [float(x) for x in np.asarray(forces, np.float64).ravel()],
    )
    return AFFE_CHAR_MECA(MODELE=context.model, VECT_ASSE=f.toFieldOnNodes())


def solve_static_linear(context: SolidContext, forces=None):
    """Solve the linear static equilibrium under gravity and optional forces."""
    config = context.config
    if forces is None:
        forces = np.zeros((context.n_iface, config.dim), dtype=np.float64)

    load = build_force_load(context, forces)
    excit = [_F(CHARGE=context.fix), _F(CHARGE=load)]
    if context.gravity is not None:
        excit.append(_F(CHARGE=context.gravity))

    return MECA_STATIQUE(
        MODELE=context.model,
        CHAM_MATER=context.fmat,
        EXCIT=tuple(excit),
        SOLVEUR=_F(METHODE=config.solver_method),
    )


def solve_static_nonlinear(context: SolidContext, forces=None, load_level=None, n_steps=None):
    """Solve the static nonlinear equilibrium under ramped gravity/forces."""
    config = context.config
    if forces is None:
        forces = np.zeros((context.n_iface, config.dim), dtype=np.float64)

    if load_level is None:
        load_level = config.steady_load_level
    if n_steps is None:
        n_steps = config.steady_steps
    load = build_force_load(context, forces)
    t_end = float(load_level)
    n_steps = max(1, int(n_steps))
    instants = tuple(float(x) for x in np.linspace(0.0, t_end, n_steps + 1))
    tlist = DEFI_LIST_REEL(VALE=instants)
    ramp = DEFI_FONCTION(
        NOM_PARA="INST",
        VALE=(0.0, 0.0, t_end, 1.0),
        PROL_GAUCHE="CONSTANT",
        PROL_DROITE="CONSTANT",
    )

    excit = [_F(CHARGE=context.fix), _F(CHARGE=load, FONC_MULT=ramp)]
    if context.gravity is not None:
        excit.append(_F(CHARGE=context.gravity, FONC_MULT=ramp))

    return STAT_NON_LINE(
        MODELE=context.model,
        CHAM_MATER=context.fmat,
        EXCIT=tuple(excit),
        COMPORTEMENT=_F(RELATION=config.material_relation, DEFORMATION=config.deformation),
        INCREMENT=_F(LIST_INST=tlist),
        NEWTON=_F(MATRICE=config.newton_matrix, REAC_ITER=config.newton_reac_iter),
        SOLVEUR=_F(METHODE=config.solver_method),
        CONVERGENCE=_F(
            ITER_GLOB_MAXI=config.iter_glob_maxi,
            RESI_GLOB_RELA=config.resi_glob_rela,
            RESI_GLOB_MAXI=config.resi_glob_maxi,
        ),
    )


def solve_static(context: SolidContext, forces=None, solver=None, load_level=None, n_steps=None):
    """Solve static equilibrium using ``linear`` or ``nonlinear`` solver mode."""
    if solver is None:
        solver = context.config.steady_solver
    if solver == "linear":
        return solve_static_linear(context, forces=forces)
    if solver == "nonlinear":
        return solve_static_nonlinear(
            context,
            forces=forces,
            load_level=load_level,
            n_steps=n_steps,
        )
    raise ValueError(f"unknown static solver mode: {solver}")


def result_time(result, fallback=1.0):
    """Return the last stored pseudo-time for a Code_Aster result."""
    try:
        values = result.getAccessParameters().get("INST", [])
        if values:
            return float(values[-1])
    except Exception:
        pass
    return float(fallback)


def field_values_at_node(result, field_name, t, node, comp_names):
    field = None
    for para, value in (("INST", float(t)), ("NUME_ORDRE", 1), ("NUME_ORDRE", 0)):
        try:
            field = result.getField(field_name, value=value, para=para).toSimpleFieldOnNodes()
            break
        except Exception:
            continue
    if field is None:
        raise RuntimeError(f"{field_name} field extraction failed")
    vals, _ = field.getValues(copy=True)
    comps = list(field.getComponents())
    return [float(vals[node, comps.index(comp)]) for comp in comp_names]


def interface_displacements(context: SolidContext, result, t):
    """Extract interface node displacements from ``result`` at pseudo-time ``t``."""
    field = None
    for para, value in (("INST", float(t)), ("NUME_ORDRE", 1), ("NUME_ORDRE", 0)):
        try:
            field = result.getField("DEPL", value=value, para=para).toSimpleFieldOnNodes()
            break
        except Exception:
            continue
    if field is None:
        raise RuntimeError("DEPL field extraction failed")
    vals, _ = field.getValues(copy=True)
    components = list(field.getComponents())
    return np.column_stack(
        [
            vals[context.iface_nodes, components.index("DX")],
            vals[context.iface_nodes, components.index("DY")],
        ]
    ).astype(np.float64)


def write_static_med(context: SolidContext, result, filename=None):
    """Write static displacement result to a MED file."""
    config = context.config
    if filename is None:
        filename = config.steady_med
    out = config.case_dir / filename
    if out.exists():
        out.unlink()

    DEFI_FICHIER(
        ACTION="ASSOCIER",
        UNITE=config.result_unit,
        TYPE="BINARY",
        ACCES="NEW",
        FICHIER=str(out),
    )
    try:
        IMPR_RESU(
            FORMAT="MED",
            UNITE=config.result_unit,
            RESU=_F(
                RESULTAT=result,
                NOM_CHAM=("DEPL",),
                NOM_CHAM_MED=("DEPL",),
            ),
        )
    finally:
        DEFI_FICHIER(ACTION="LIBERER", UNITE=config.result_unit)
    return out


def write_probe_csv(
    context: SolidContext,
    result,
    probe_node,
    probe_coord,
    filename=None,
    load_level=None,
):
    """Write one-row probe displacement/position summary."""
    config = context.config
    if filename is None:
        filename = config.steady_csv
    t = result_time(result)
    ux, uy = field_values_at_node(result, "DEPL", t, probe_node, config.comp)
    disp = interface_displacements(context, result, t)
    norms = np.linalg.norm(disp, axis=1)
    row = {
        "load_level": float(t if load_level is None else load_level),
        "probe_x": float(probe_coord[0]),
        "probe_y": float(probe_coord[1]),
        "ux": ux,
        "uy": uy,
        "x": float(probe_coord[0]) + ux,
        "y": float(probe_coord[1]) + uy,
        "max_abs_u": float(norms.max()) if norms.size else 0.0,
        "mean_abs_u": float(norms.mean()) if norms.size else 0.0,
    }

    out = Path(filename)
    if not out.is_absolute():
        out = config.case_dir / out
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return out, row
