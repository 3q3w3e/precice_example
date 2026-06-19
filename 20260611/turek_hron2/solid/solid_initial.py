# coding=utf-8
"""Initial-condition helpers for the solid participant."""

import numpy as np
from code_aster import CA

from solid_model import SolidContext


def build_initial_velocity(context: SolidContext):
    """Build perturbation A, or return None when it is disabled."""
    config = context.config
    if config.perturb_vel == 0.0 or config.do_restart:
        return None

    coord = context.mesh.getCoordinatesAsSimpleFieldOnNodes()
    cvals, _ = coord.getValues(copy=True)
    components = list(coord.getComponents())
    x = cvals[:, components.index("X")]
    xmin, xmax = float(x.min()), float(x.max())
    ramp = (x - xmin) / (xmax - xmin) if xmax > xmin else np.zeros_like(x)

    n_nodes = x.size
    vf = CA.SimpleFieldOnNodesReal(context.mesh, "DEPL_R", config.comp, True)
    vf.setValues(0.0)
    nodes = np.repeat(np.arange(n_nodes), config.dim)
    comps = np.tile(np.asarray(config.comp, dtype=object), n_nodes)
    vel = np.zeros((n_nodes, config.dim), dtype=np.float64)
    vel[:, 1] = config.perturb_vel * ramp
    vf.setValues(
        [int(i) for i in nodes],
        [str(c) for c in comps],
        [float(v) for v in vel.ravel()],
    )

    print(
        f"[Solid] PERTURB A: 초기 횡속도 tip DY={config.perturb_vel:.3e} m/s "
        f"(x {xmin:.3f}→{xmax:.3f} 선형 ramp, DEPL=0)",
        flush=True,
    )
    return vf.toFieldOnNodes()
