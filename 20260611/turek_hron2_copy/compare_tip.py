#!/usr/bin/env python3
# coding=utf-8
"""Compare flap-tip trajectories: baseline vs restart segment.

Usage: compare_tip.py baseline_tip.log restart_tip.log t_R

The watch-point log columns are:
  Time  Coordinate0 Coordinate1  Displacement0 Displacement1  Force0 Force1
preCICE time restarts at 0 each run, so the restart log's Time is shifted by +t_R
to absolute time, then compared with the baseline over the overlap [t_R, T_end].
Success = the two tip-Y trajectories coincide on the overlap (a few-window
restart transient from the empty IQN history is allowed, then they must track).
"""
import sys
import numpy as np


def load(path):
    rows = []
    for line in open(path):
        s = line.split()
        if not s or not s[0].replace(".", "").replace("e", "").replace("-", "").replace("+", "").isdigit():
            continue
        try:
            vals = [float(x) for x in s]
        except ValueError:
            continue
        if len(vals) >= 5:
            rows.append((vals[0], vals[3], vals[4]))   # Time, dispX, dispY
    a = np.array(rows)
    # collapse duplicate Times (preCICE may log per coupling-iteration); keep last
    _, idx = np.unique(a[:, 0][::-1], return_index=True)
    a = a[len(a) - 1 - idx][::-1]
    return a[np.argsort(a[:, 0])]


def main():
    base_p, rest_p, t_R = sys.argv[1], sys.argv[2], float(sys.argv[3])
    base = load(base_p)
    rest = load(rest_p)
    rest[:, 0] += t_R                                    # preCICE-relative -> absolute

    # compare on baseline times that fall in the restart's covered range
    lo, hi = rest[:, 0].min(), rest[:, 0].max()
    mask = (base[:, 0] >= lo - 1e-9) & (base[:, 0] <= hi + 1e-9)
    bt = base[mask]
    # interpolate restart onto baseline times
    ry = np.interp(bt[:, 0], rest[:, 0], rest[:, 2])
    by = bt[:, 2]
    absd = np.abs(by - ry)
    scale = max(np.abs(by).max(), 1e-30)
    rel = absd / scale

    print(f" overlap [{lo:.4f},{hi:.4f}]s  ({len(bt)} baseline points)")
    print(f" tip-Y  max|abs diff| = {absd.max():.3e}   max rel(vs peak) = {100*rel.max():.3f}%")
    # report a few samples
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        i = min(int(frac * (len(bt) - 1)), len(bt) - 1)
        print(f"   t={bt[i,0]:.4f}  baseline={by[i]:+.6e}  restart={ry[i]:+.6e}  d={by[i]-ry[i]:+.2e}")
    ok = rel.max() < 0.02            # within 2% of peak over the whole overlap
    print(" >>> PASS (restart reproduces baseline)" if ok else " >>> CHECK (diverges > 2% — see off-by-one note)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
