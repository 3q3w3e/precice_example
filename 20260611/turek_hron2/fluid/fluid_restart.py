# coding=utf-8
"""Fluid (SU2) restart bookkeeping: keep latest restart files.

Decision (measured): BDF2 dual-time restart REQUIRES two consecutive solution
files restart_flow_<k-1>.dat and restart_flow_<k-2>.dat (verified: removing the
older one aborts construction).  Run-extension therefore keeps the latest
consecutive restart files (BDF2-direct, no BDF1 warmup).  Production runs keep
one extra file so Ctrl-C between fluid output and solid manifest update is still
recoverable.

Companion to fluid_refcoords.py (reference-coords persist/reload).
"""

import os
import re
import json
from pathlib import Path

_RESTART_RE = re.compile(r"^restart_flow_(\d+)\.dat$")


def prune_restart_files(fluid_dir, keep=2):
    """Keep only the ``keep`` highest-index restart_flow_<iter>.dat files."""
    fluid_dir = Path(fluid_dir)
    idx = []
    for p in fluid_dir.glob("restart_flow_*.dat"):
        m = _RESTART_RE.match(p.name)
        if m:
            idx.append((int(m.group(1)), p))
    idx.sort(key=lambda t: t[0])
    for _, p in idx[:-keep]:          # everything but the last `keep`
        try:
            p.unlink()
        except OSError:
            pass
    return [p.name for _, p in idx[-keep:]]


def write_fluid_manifest(path, t_R, restart_iter, dt, files):
    """Record the physical time t_R (single source of truth) + the 2 files.

    restart_iter is derived as round(t_R/dt) and kept only for convenience; the
    canonical key is t_R.  Written atomically.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "t_R": float(t_R),
        "dt": float(dt),
        "restart_iter": int(restart_iter),
        "files": list(files),
    }
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(str(tmp), str(path))


def read_fluid_manifest(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text())
