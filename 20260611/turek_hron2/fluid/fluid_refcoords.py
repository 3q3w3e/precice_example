# coding=utf-8
"""Reference interface-coordinate persist/reload for the SU2 preCICE adapter.

SU2 7.5.1 GetInitialMeshCoord() returns the current grid coordinate.  On a
fresh run that is the undeformed reference coordinate, but on restart it is the
already-deformed restart coordinate.  preCICE must still register the Fluid mesh
at the reference interface coordinates.

This restart variant stores reference coordinates by SU2 global node id instead
of by (rank, local vertex order).  That makes the lookup independent of the MPI
partition, so a restart can be attempted with a different FLUID_NPROC.
"""

import os
from pathlib import Path

import numpy


def ref_path(refdir):
    return Path(refdir) / "fluid_ref_coords_global.npz"


def _atomic_save_npz(path, gids, coords, fresh_size):
    path = Path(path)
    tmp = path.with_name(path.stem + ".tmp.npz")
    order = numpy.argsort(gids)
    numpy.savez(
        str(tmp),
        gids=numpy.asarray(gids, dtype=numpy.int64)[order],
        coords=numpy.asarray(coords, dtype=float)[order],
        fresh_size=numpy.asarray([int(fresh_size)], dtype=numpy.int64),
    )
    os.replace(str(tmp), str(path))


def _load_ref_map(path):
    data = numpy.load(str(path))
    return (
        numpy.asarray(data["gids"], dtype=numpy.int64),
        numpy.asarray(data["coords"], dtype=float),
        int(numpy.asarray(data["fresh_size"], dtype=numpy.int64)[0])
        if "fresh_size" in data
        else None,
    )


def _lookup_coords(path, local_gids, live_shape, rank):
    gids, coords, fresh_size = _load_ref_map(path)
    local_gids = numpy.asarray(local_gids, dtype=numpy.int64)
    if local_gids.size == 0:
        return numpy.zeros(live_shape, dtype=float), fresh_size
    if coords.ndim != 2 or coords.shape[1] != live_shape[1]:
        raise RuntimeError(
            f"[Fluid] reference coordinate dimension {coords.shape} incompatible "
            f"with live shape {live_shape}"
        )

    positions = numpy.searchsorted(gids, local_gids)
    ok = positions < gids.size
    ok[ok] = gids[positions[ok]] == local_gids[ok]
    if not numpy.all(ok):
        missing = local_gids[~ok]
        preview = ", ".join(str(int(x)) for x in missing[:10])
        raise RuntimeError(
            f"[Fluid][rank {rank}] missing reference coordinates for global node ids: "
            f"{preview}{' ...' if missing.size > 10 else ''}"
        )

    ref = coords[positions]
    if ref.shape != live_shape:
        raise RuntimeError(
            f"[Fluid][rank {rank}] reference shape {ref.shape} != live shape {live_shape}"
        )
    return ref, fresh_size


def reference_interface_coords(
    live_coords,
    global_ids,
    refdir,
    rank,
    size,
    restart,
    comm=None,
):
    """Return reference coordinates for the local physical interface vertices.

    fresh:
      gather ``global_id -> live reference coord`` from all ranks and write one
      global map.  Return ``live_coords``.

    restart:
      load the global map and look up this rank's current physical vertices by
      SU2 global node id.  Return those saved reference coordinates.  The rank
      count may differ from the fresh run.
    """
    refdir = Path(refdir)
    refdir.mkdir(parents=True, exist_ok=True)
    path = ref_path(refdir)

    live = numpy.asarray(live_coords, dtype=float)
    gids = numpy.asarray(global_ids, dtype=numpy.int64)
    if live.shape[0] != gids.size:
        raise RuntimeError(
            f"[Fluid][rank {rank}] coords rows {live.shape[0]} != global ids {gids.size}"
        )

    if restart:
        ref, fresh_size = _lookup_coords(path, gids, live.shape, rank)
        if rank == 0 and fresh_size is not None and fresh_size != int(size):
            print(
                f"[Fluid] reference coords loaded from fresh nproc={fresh_size}; "
                f"current nproc={size}",
                flush=True,
            )
        return ref

    if comm is not None:
        gathered = comm.gather((gids, live), root=0)
        if rank == 0:
            all_gids = numpy.concatenate([item[0] for item in gathered])
            all_coords = numpy.vstack([item[1] for item in gathered])
            unique, counts = numpy.unique(all_gids, return_counts=True)
            if numpy.any(counts > 1):
                dup = unique[counts > 1]
                preview = ", ".join(str(int(x)) for x in dup[:10])
                raise RuntimeError(
                    f"[Fluid] duplicate physical global node ids while saving references: "
                    f"{preview}{' ...' if dup.size > 10 else ''}"
                )
            _atomic_save_npz(path, all_gids, all_coords, fresh_size=size)
        comm.Barrier()
    else:
        _atomic_save_npz(path, gids, live, fresh_size=size)

    return live
