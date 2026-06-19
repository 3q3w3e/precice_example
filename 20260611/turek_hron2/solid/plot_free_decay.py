#!/usr/bin/env python3
# coding=utf-8
"""Plot the CSV produced by run_free_decay.py."""

import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    csv_path = Path(sys.argv[1] if len(sys.argv) > 1 else "free_decay.csv")
    if not csv_path.exists():
        raise SystemExit(f"missing {csv_path}")

    data = np.genfromtxt(csv_path, delimiter=",", names=True)
    if data.shape == ():
        data = np.array([data], dtype=data.dtype)

    out = csv_path.with_suffix(".png")
    fig, axs = plt.subplots(3, 1, figsize=(9, 9), sharex=True)

    axs[0].plot(data["time"], data["ux"], "o-", label="Ux")
    axs[0].plot(data["time"], data["uy"], "s-", label="Uy")
    axs[0].axhline(0.0, color="0.3", lw=1)
    axs[0].set_ylabel("probe displacement")
    axs[0].legend()

    axs[1].plot(data["time"], data["vx"], "o-", label="Vx")
    axs[1].plot(data["time"], data["vy"], "s-", label="Vy")
    axs[1].axhline(0.0, color="0.3", lw=1)
    axs[1].set_ylabel("probe velocity")
    axs[1].legend()

    axs[2].plot(data["time"], data["max_abs_u"], "o-", label="max |u| on interface")
    axs[2].plot(data["time"], data["mean_abs_u"], "s-", label="mean |u| on interface")
    axs[2].set_ylabel("interface displacement norm")
    axs[2].set_xlabel("time [s]")
    axs[2].legend()

    for ax in axs:
        ax.grid(True, alpha=0.3)

    fig.suptitle(f"Solid-only free decay: {csv_path.name}")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    print(out)


if __name__ == "__main__":
    main()
