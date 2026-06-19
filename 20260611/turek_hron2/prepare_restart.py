#!/usr/bin/env python3
# coding=utf-8
"""Restart orchestrator — single source of truth = the physical time t_R.

preCICE has no native restart, and its config cannot read env vars, so each
restart segment needs a freshly *generated* precice-config.xml with the right
max-time.  This script is the one place that:

  * reads t_R from the SOLID manifest (restart/solid_manifest.json) — the single
    source of truth for the restart time,
  * regenerates precice-config.xml from precice-config.base.xml with
        max-time = TOTAL - t_R         (TOTAL read from the base config)
  * generates the fluid run-config (config_fluid_restart.cfg) with
        RESTART_SOL=YES, RESTART_ITER = round(t_R/dt),
        and the RESTART entry in OUTPUT_WRT_FREQ forced to 1,
  * verifies the two consecutive restart_flow_<k-1>,<k-2>.dat exist (BDF2-direct),
  * prints the env to launch each run.sh.

Fresh (first) run: `--fresh` just generates precice-config.xml (max-time=TOTAL)
and config_fluid_run.cfg (RESTART_SOL=NO, RESTART output every window) so the
first run already produces restartable output.

Fluid RESTART_ITER is DERIVED from t_R here, never stored independently, so
fluid / solid / preCICE all reconcile on the one t_R.
"""

import os
import re
import sys
import json
import shutil
import argparse
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent
FLUID_DIR = CASE_DIR / "fluid"
SOLID_DIR = CASE_DIR / "solid"
RESTART_DIR = CASE_DIR / "restart"           # shared; solid writes its manifest here
SOLID_MANIFEST = RESTART_DIR / "solid_manifest.json"

PRECICE_BASE = CASE_DIR / "precice-config.base.xml"
PRECICE_LIVE = CASE_DIR / "precice-config.xml"

FLUID_CFG_BASE = FLUID_DIR / "config_fluid.cfg"
FLUID_CFG_RUN = FLUID_DIR / "config_fluid_run.cfg"      # fresh
FLUID_CFG_RESTART = FLUID_DIR / "config_fluid_restart.cfg"  # restart


def _read_xml_value(text, tag, attr="value"):
    m = re.search(rf'<{tag}\s+{attr}="([^"]+)"', text)
    return float(m.group(1)) if m else None


def ensure_precice_base():
    """Keep a pristine base; the live config is always (re)generated from it."""
    if not PRECICE_BASE.exists():
        if not PRECICE_LIVE.exists():
            sys.exit(f"ERROR: neither {PRECICE_BASE.name} nor {PRECICE_LIVE.name} found")
        shutil.copy2(PRECICE_LIVE, PRECICE_BASE)
        print(f"[prepare] seeded {PRECICE_BASE.name} from current {PRECICE_LIVE.name}")


def gen_precice_config(max_time):
    base = PRECICE_BASE.read_text()
    out = re.sub(r'(<max-time\s+value=")[^"]+(")',
                 rf'\g<1>{max_time:.6g}\g<2>', base)
    tmp = PRECICE_LIVE.with_name(PRECICE_LIVE.name + ".tmp")
    tmp.write_text(out)
    os.replace(str(tmp), str(PRECICE_LIVE))
    print(f"[prepare] wrote {PRECICE_LIVE.name}: max-time={max_time:.6g}")


def _set_cfg_key(text, key, value):
    """Set 'KEY= value' (uncommenting/overriding), append if absent."""
    pat = re.compile(rf'(?im)^\s*{re.escape(key)}\s*=.*$')
    line = f"{key}= {value}"
    if pat.search(text):
        return pat.sub(line, text, count=1)
    return text.rstrip() + f"\n{line}\n"


def _read_cfg_key(text, key):
    pat = re.compile(rf'(?im)^\s*{re.escape(key)}\s*=\s*(.*)$')
    m = pat.search(text)
    if not m:
        return None
    return m.group(1).split("%", 1)[0].strip()


def _parse_cfg_list(value):
    if value is None:
        return []
    raw = value.strip()
    if raw.startswith("(") and raw.endswith(")"):
        raw = raw[1:-1]
    if "," in raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [item.strip() for item in raw.split() if item.strip()]


def _force_restart_output_frequency(text):
    """Preserve visualization frequencies, force only RESTART output to every step."""
    output_files = _parse_cfg_list(_read_cfg_key(text, "OUTPUT_FILES"))
    if not output_files:
        output_files = ["RESTART", "PARAVIEW", "SURFACE_PARAVIEW"]

    freqs = _parse_cfg_list(_read_cfg_key(text, "OUTPUT_WRT_FREQ"))
    if not freqs:
        freqs = ["1"] * len(output_files)
    while len(freqs) < len(output_files):
        freqs.append(freqs[-1])

    touched_restart = False
    for i, output_file in enumerate(output_files):
        if output_file.strip().upper() in ("RESTART", "RESTART_ASCII"):
            freqs[i] = "1"
            touched_restart = True

    if not touched_restart:
        raise RuntimeError("OUTPUT_FILES must contain RESTART or RESTART_ASCII for restartable runs")

    freq_text = "(" + ", ".join(freqs[:len(output_files)]) + ")"
    return _set_cfg_key(text, "OUTPUT_WRT_FREQ", freq_text), freq_text


def gen_fluid_config(restart, restart_iter=None):
    text = FLUID_CFG_BASE.read_text()
    text, output_freq = _force_restart_output_frequency(text)
    if restart:
        text = _set_cfg_key(text, "RESTART_SOL", "YES")
        text = _set_cfg_key(text, "SOLUTION_FILENAME", "restart_flow")
        text = _set_cfg_key(text, "RESTART_ITER", str(restart_iter))
        out = FLUID_CFG_RESTART
    else:
        text = _set_cfg_key(text, "RESTART_SOL", "NO")
        out = FLUID_CFG_RUN
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_text(text)
    os.replace(str(tmp), str(out))
    print(f"[prepare] wrote {out.name}"
          + (f": RESTART_SOL=YES RESTART_ITER={restart_iter}" if restart else ": RESTART_SOL=NO")
          + f" OUTPUT_WRT_FREQ={output_freq}")
    return out


def verify_restart_files(indices):
    missing = [k for k in indices if not (FLUID_DIR / f"restart_flow_{k:05d}.dat").exists()]
    if missing:
        print(f"[prepare] WARNING: missing restart files: "
              + ", ".join(f"restart_flow_{k:05d}.dat" for k in missing))
        return False
    print("[prepare] verified restart files: "
          + ", ".join(f"restart_flow_{k:05d}.dat" for k in indices))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true", help="prepare a first (non-restart) run")
    ap.add_argument("--total", type=float, default=None,
                    help="override the run end time (s); handy for short regression tests")
    args = ap.parse_args()

    ensure_precice_base()
    base = PRECICE_BASE.read_text()
    TOTAL = args.total if args.total is not None else _read_xml_value(base, "max-time")
    DT = _read_xml_value(base, "time-window-size")
    if TOTAL is None or DT is None:
        sys.exit("ERROR: could not read max-time / time-window-size from base config")

    if args.fresh:
        gen_precice_config(TOTAL)                     # full duration, default relaxation
        gen_fluid_config(restart=False)
        print(f"\n[prepare] FRESH ready.  TOTAL={TOTAL:g}s dt={DT:g}s")
        print("  fluid:  CONFIG_FILE=config_fluid_run.cfg ./run.sh")
        print("  solid:  ./run.sh")
        return

    man = json.loads(SOLID_MANIFEST.read_text()) if SOLID_MANIFEST.exists() else None
    if man is None:
        sys.exit(f"ERROR: restart requested but {SOLID_MANIFEST} not found (run fresh first)")
    t_R = float(man["t"])                              # <-- single source of truth
    # Index derivation (the ONE place; confirmed by the coupled regression):
    #   solid step=N at t_R=N*dt; the adapter writes restart_flow_<TimeIter> with
    #   Output(TimeIter) then TimeIter+=1, so after N windows the latest file is
    #   <N-1>.  The probe showed RESTART_ITER=k reads files <k-1>,<k-2>.  Hence:
    k = round(t_R / DT)                                # = N
    restart_iter = k                                   # SU2 reads <k-1>,<k-2>
    files = [k - 1, k - 2]                             # BDF2 needs the two consecutive
    max_time = TOTAL - t_R

    print(f"[prepare] RESTART from solid manifest: t_R={t_R:g}s  (step={man.get('step')})")
    print(f"[prepare] derived: k={k}  RESTART_ITER={restart_iter}  max-time={max_time:g}s")

    gen_precice_config(max_time)
    gen_fluid_config(restart=True, restart_iter=restart_iter)
    ok = verify_restart_files(files)

    print(f"\n[prepare] RESTART ready{'' if ok else ' (WARNING: missing restart files above)'}.")
    print("  fluid:  FLUID_RESTART=1 CONFIG_FILE=config_fluid_restart.cfg ./run.sh")
    print("  solid:  SOLID_RESTART=1 ./run.sh")


if __name__ == "__main__":
    main()
