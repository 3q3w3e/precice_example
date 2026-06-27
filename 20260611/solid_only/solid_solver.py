# coding=utf-8
"""One-window Code_Aster solve helpers for the solid participant."""

import numpy as np
from code_aster import CA
from code_aster.Cata.Syntax import _F
from code_aster.Commands import AFFE_CHAR_MECA, DEFI_LIST_REEL, DYNA_NON_LINE

from solid_model import SolidContext


def build_time_scheme(config):
    scheme = config.time_scheme.strip().upper()
    if scheme == "HHT":
        return _F(SCHEMA="HHT", FORMULATION="DEPLACEMENT", ALPHA=config.hht_alpha)
    if scheme == "NEWMARK":
        return _F(
            SCHEMA="NEWMARK",
            FORMULATION="DEPLACEMENT",
            BETA=config.newmark_beta,
            GAMMA=config.newmark_gamma,
        )
    raise ValueError(f"unknown time integration scheme: {config.time_scheme}")


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


def solve_window(context: SolidContext, forces, prev_result, t0, t1, init_vite=None):
    """Solve one transient window from the previous Code_Aster result."""
    config = context.config
    load = build_force_load(context, forces)
    excit = [_F(CHARGE=context.fix), _F(CHARGE=load)]
    if context.gravity is not None:
        excit.append(_F(CHARGE=context.gravity))
    tlist = DEFI_LIST_REEL(VALE=(t0, t1))
    kw = dict(
        MODELE=context.model,
        CHAM_MATER=context.fmat,
        EXCIT=tuple(excit),
        COMPORTEMENT=_F(RELATION=config.material_relation, DEFORMATION=config.deformation),
        INCREMENT=_F(LIST_INST=tlist),
        SCHEMA_TEMPS=build_time_scheme(config),
        NEWTON=_F(MATRICE=config.newton_matrix, REAC_ITER=config.newton_reac_iter),
        SOLVEUR=_F(METHODE=config.solver_method),
        CONVERGENCE=_F(
            ITER_GLOB_MAXI=config.iter_glob_maxi,
            RESI_GLOB_RELA=config.resi_glob_rela,
            RESI_GLOB_MAXI=config.resi_glob_maxi,
        ),
    )
    if prev_result is not None:
        kw["ETAT_INIT"] = _F(EVOL_NOLI=prev_result)
    elif init_vite is not None:
        kw["ETAT_INIT"] = _F(VITE=init_vite)
    return DYNA_NON_LINE(**kw)


def interface_displacements(context: SolidContext, result, t):
    """Extract interface node displacements from ``result`` at time ``t``."""
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
    components = list(field.getComponents())
    return np.column_stack(
        [
            vals[context.iface_nodes, components.index("DX")],
            vals[context.iface_nodes, components.index("DY")],
        ]
    ).astype(np.float64)
