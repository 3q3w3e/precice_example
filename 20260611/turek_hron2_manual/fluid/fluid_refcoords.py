# coding=utf-8
"""Reference interface-coordinate persist/reload for the SU2 preCICE adapter.

WHY (measured, not assumed -- see /tmp/su2probe):
  SU2 7.5.1 GetInitialMeshCoord() returns geometry->nodes->GetCoord() (the
  CURRENT grid coordinate), NOT the reference GetMesh_Coord().  On a fresh run
  geometry->Coord == the .su2 undeformed mesh, so it yields the reference and
  preCICE registers correctly.  But on RESTART the restart file's DEFORMED
  coords are already loaded into geometry->Coord by driver-construction time, so
  GetInitialMeshCoord returns the DEFORMED interface.  Registering the preCICE
  mesh at deformed positions corrupts the RBF mapping against the solid's
  reference mesh (verified: a +0.05 m fake deformation came straight back out).

FIX (method A, no SU2 recompile):
  On the first (non-restart) run, persist the reference interface coords per MPI
  rank.  On restart, reload them for set_mesh_vertices instead of trusting
  GetInitialMeshCoord.  (SetMeshDisplacement in the loop is unaffected -- it
  takes the absolute displacement from the reference, so the grid still deforms
  to the right place.)

Vertex order is deterministic for a fixed mesh + fixed nproc, so per-(rank,size)
files round-trip 1:1.  Restarting with a DIFFERENT nproc is rejected -- the
partitioning, hence the vertex order, would not match.
"""

import os
from pathlib import Path

import numpy


def ref_path(refdir, rank, size):
    return Path(refdir) / f"fluid_ref_coords_r{int(rank):04d}_of{int(size):04d}.npy"


def reference_interface_coords(live_coords, refdir, rank, size, restart):
    """Coords to register with preCICE: reference on both fresh and restart runs.

    live_coords : (nv, dim) from GetInitialMeshCoord this run.  Reference on a
                  fresh run; DEFORMED (do not trust) on restart.
    fresh   -> persist live_coords atomically, return them.
    restart -> return the persisted reference (live_coords ignored), after a
               shape/count check against this rank's partition.
    """
    refdir = Path(refdir)
    refdir.mkdir(parents=True, exist_ok=True)
    path = ref_path(refdir, rank, size)

    if restart:
        if not path.exists():
            raise RuntimeError(
                f"[Fluid] restart but reference-coords file is missing: {path}\n"
                f"        Was the first (non-restart) run done with the same nproc={size}?")
        ref = numpy.load(path)
        if ref.shape != numpy.asarray(live_coords).shape:
            raise RuntimeError(
                f"[Fluid] reference-coords shape {ref.shape} != live {numpy.asarray(live_coords).shape} "
                f"on rank {rank}: partitioning/nproc changed -- restart with the original nproc.")
        return ref

    # fresh run: persist (atomic) and use the live (reference) coords.
    # NB: numpy.save appends ".npy" if the name doesn't end in it, so the tmp
    # name must already end in ".npy" or os.replace would miss it.
    live = numpy.asarray(live_coords, dtype=float)
    tmp = path.with_name(path.stem + ".tmp.npy")
    numpy.save(str(tmp), live)
    os.replace(str(tmp), str(path))
    return live
