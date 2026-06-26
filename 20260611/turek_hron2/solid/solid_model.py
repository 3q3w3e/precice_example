# coding=utf-8
"""Code_Aster mesh/model/material setup for the solid participant."""

from dataclasses import dataclass

import numpy as np
from code_aster.Cata.Syntax import _F
from code_aster.Commands import (
    AFFE_CHAR_MECA,
    AFFE_MATERIAU,
    AFFE_MODELE,
    DEFI_FICHIER,
    DEFI_GROUP,
    DEFI_MATERIAU,
    LIRE_MAILLAGE,
)

from solid_config import SolidConfig


@dataclass
class SolidContext:
    config: SolidConfig
    mesh: object
    model: object
    fmat: object
    fix: object
    iface_nodes: np.ndarray
    iface_coords: np.ndarray
    n_iface: int


def build_solid_context(config: SolidConfig) -> SolidContext:
    DEFI_FICHIER(
        ACTION="ASSOCIER",
        UNITE=config.mesh_unit,
        TYPE="BINARY",
        ACCES="OLD",
        FICHIER=str(config.case_dir / config.mesh_file),
    )
    mesh = LIRE_MAILLAGE(
        UNITE=config.mesh_unit,
        FORMAT="MED",
        VERI_MAIL=_F(VERIF="OUI"),
    )

    mesh = DEFI_GROUP(
        reuse=mesh,
        MAILLAGE=mesh,
        CREA_GROUP_NO=_F(NOM=config.iface_gno, GROUP_MA=config.iface_gma),
    )

    model = AFFE_MODELE(
        MAILLAGE=mesh,
        AFFE=_F(
            GROUP_MA=config.volume_gma,
            PHENOMENE="MECANIQUE",
            MODELISATION="D_PLAN",
        ),
    )
    mat = DEFI_MATERIAU(ELAS=_F(E=config.e_mod, NU=config.nu, RHO=config.rho))
    fmat = AFFE_MATERIAU(
        MAILLAGE=mesh,
        AFFE=_F(GROUP_MA=config.volume_gma, MATER=mat),
    )
    fix = AFFE_CHAR_MECA(
        MODELE=model,
        DDL_IMPO=_F(GROUP_MA=config.clamp_gma, DX=0.0, DY=0.0),
    )

    iface_nodes = np.asarray(
        mesh.getNodes(config.iface_gno, localNumbering=True),
        dtype=np.int64,
    )
    n_iface = iface_nodes.size
    if n_iface == 0:
        raise RuntimeError(f"계면 노드 그룹 '{config.iface_gno}' 가 비어있음")

    coord = mesh.getCoordinatesAsSimpleFieldOnNodes()
    cvals, _ = coord.getValues(copy=True)
    components = list(coord.getComponents())
    iface_coords = np.column_stack(
        [
            cvals[iface_nodes, components.index("X")],
            cvals[iface_nodes, components.index("Y")],
        ]
    ).astype(np.float64)

    print(f"[Solid] 계면 노드 {n_iface} 개", flush=True)
    return SolidContext(
        config=config,
        mesh=mesh,
        model=model,
        fmat=fmat,
        fix=fix,
        iface_nodes=iface_nodes,
        iface_coords=iface_coords,
        n_iface=n_iface,
    )
