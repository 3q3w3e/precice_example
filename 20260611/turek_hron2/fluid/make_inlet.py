#!/usr/bin/env python3
# coding=utf-8
"""Generate the SU2 SPECIFIED_INLET_PROFILE file for the Turek-Hron channel.

The profile is the Turek-Hron parabolic inflow (their Eq. 10):
        vf(0,y) = 1.5 * Ubar * y(H - y) / (H/2)^2
                = 1.5 * Ubar * 4 * y(H - y) / H^2
                = 6 * Ubar * y * (H - y) / H^2          (Umax = 1.5*Ubar at y=H/2)
For H = 0.41 this is 1.5*Ubar*(4.0/0.1681)*y*(0.41 - y).  It is sampled at the
mesh's *actual* inlet boundary nodes — the COORD-Y values MUST match the inlet
nodes of fluid.su2 (SU2 matches profile points to boundary nodes by coordinate),
so they are read straight from the .su2 mesh.

Writes inlet_00000.dat (the real file SU2 reads on iter 0 / fresh unsteady runs)
and points inlet.dat at it via a symlink, matching the case convention.

Usage (from fluid/):
    python3 make_inlet.py                       # Ubar=1.0, H=auto, marker=inlet
    python3 make_inlet.py --ubar 2.0 --H 0.41   # e.g. Turek-Hron FSI3
    python3 make_inlet.py --check inlet_00000.dat   # compare to an existing file
"""
import argparse
import sys
from pathlib import Path


def read_su2_inlet_nodes(su2_path, marker):
    """Return [(x, y), ...] for the unique nodes of the named boundary marker."""
    lines = Path(su2_path).read_text().splitlines()
    coords = {}
    i, n = 0, len(lines)
    inlet_nodes = None
    while i < n:
        tok = lines[i].split()
        if not tok:
            i += 1
            continue
        key = tok[0].rstrip("=")
        if key == "NPOIN":
            npoin = int(tok[1])
            for k in range(npoin):
                i += 1
                p = lines[i].split()
                x, y = float(p[0]), float(p[1])
                idx = int(p[-1]) if len(p) > 2 else k   # trailing global index, else order
                coords[idx] = (x, y)
        elif key == "MARKER_TAG":
            tag = tok[1]
            i += 1
            melems = int(lines[i].split()[-1])          # MARKER_ELEMS= N
            nodes = set()
            for k in range(melems):
                i += 1
                p = lines[i].split()
                nodes.update(int(v) for v in p[1:])     # skip element-type token
            if tag == marker:
                inlet_nodes = nodes
        i += 1
    if inlet_nodes is None:
        sys.exit(f"ERROR: marker '{marker}' not found in {su2_path}")
    pts = [coords[nd] for nd in inlet_nodes]
    pts.sort(key=lambda p: p[1])                          # order by y (cosmetic)
    return pts


def write_profile(pts, ubar, H, marker, out_path):
    rows = []
    for x, y in pts:
        U = 6.0 * ubar * y * (H - y) / (H * H)            # parabolic, 0 at walls
        if U < 0:
            U = 0.0                                       # guard tiny negatives at walls
        rows.append((x, y, 0.0, U, 1.0, 0.0))             # T=0, normal=(1,0) (inlet faces +x)
    txt = ["NMARK= 1", f"MARKER_TAG= {marker}", f"NROW={len(rows)}", "NCOL=6",
           "# COORD-X\tCOORD-Y\tTEMPERATURE\tVELOCITY\tNORMAL-X\tNORMAL-Y"]
    for r in rows:
        txt.append("\t".join(f"{v:.15e}" for v in r))
    Path(out_path).write_text("\n".join(txt) + "\n")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--su2", default="fluid.su2")
    ap.add_argument("--marker", default="inlet")
    ap.add_argument("--ubar", type=float, default=1.0, help="mean inlet velocity Ubar")
    ap.add_argument("--H", type=float, default=None, help="channel height (default: auto from inlet nodes)")
    ap.add_argument("--out", default="inlet_00000.dat")
    ap.add_argument("--no-symlink", action="store_true", help="do not (re)create inlet.dat symlink")
    ap.add_argument("--check", default=None, help="compare generated profile to this existing file (no write)")
    args = ap.parse_args()

    pts = read_su2_inlet_nodes(args.su2, args.marker)
    ys = [y for _, y in pts]
    H = args.H if args.H is not None else (max(ys) - min(ys))
    print(f"[make_inlet] {len(pts)} inlet nodes, y in [{min(ys):.5f},{max(ys):.5f}], "
          f"H={H:.5f}, Ubar={args.ubar}, Umax={1.5*args.ubar:.5f}")

    if args.check:
        # compare numeric (COORD-Y, VELOCITY) against an existing profile file
        import re
        gen = {round(y, 9): 6.0*args.ubar*y*(H-y)/(H*H) for _, y in pts}
        ref = {}
        for ln in Path(args.check).read_text().splitlines():
            p = ln.split()
            if len(p) == 6:
                try:
                    ref[round(float(p[1]), 9)] = float(p[3])
                except ValueError:
                    pass
        maxd = 0.0
        for y, U in gen.items():
            if y in ref:
                maxd = max(maxd, abs(U - ref[y]))
        print(f"[make_inlet] CHECK vs {args.check}: matched {len(ref)} rows, "
              f"max |dU| = {maxd:.3e}  -> {'MATCH' if maxd < 1e-9 else 'DIFFER'}")
        return

    rows = write_profile(pts, args.ubar, H, args.marker, args.out)
    print(f"[make_inlet] wrote {args.out} ({len(rows)} rows)")
    if not args.no_symlink:
        link = Path("inlet.dat")
        if link.is_symlink() or link.exists():
            link.unlink()
        import os
        os.symlink(args.out, "inlet.dat")
        print(f"[make_inlet] inlet.dat -> {args.out}")


if __name__ == "__main__":
    main()
