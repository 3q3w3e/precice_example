#!/usr/bin/env bash
# ============================================================================
# regression_test.sh — restart correctness check for the Turek-Hron FSI case.
#
# Runs THREE coupled runs and compares the flap-tip trajectory:
#   1) BASELINE : fresh 0 -> T_END                    (the reference)
#   2) SEGMENT  : fresh 0 -> T_R   (generates restart artifacts at T_R)
#   3) RESTART  : restart T_R -> T_END
# PASS = RESTART reproduces BASELINE over [T_R, T_END].
#
# This is exactly the manual workflow, automated:
#   - "restart=no run to make restart files"  == steps 1/2 (prepare_restart --fresh)
#   - "restart from them"                      == step 3   (prepare_restart + *_RESTART=1)
#   - "check it worked"                        == compare_tip.py
#
# Usage (from the case root):
#   ./regression_test.sh                 # defaults: T_END=0.02 T_R=0.01 NPROC=2
#   T_END=0.10 T_R=0.05 FLUID_NPROC=4 ./regression_test.sh
# Each coupled run launches fluid/run.sh and solid/run.sh together (preCICE
# connects them over sockets); logs go to ./regression/.
# ============================================================================
set -uo pipefail
CASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$CASE"

T_END="${T_END:-0.02}"
T_R="${T_R:-0.01}"
NPROC="${FLUID_NPROC:-2}"
OUT="$CASE/regression"; mkdir -p "$OUT"
WATCH="solid/precice-Solid-watchpoint-Flap-Tip.log"

clean_case() {   # wipe regeneratable outputs a fresh coupled run must not inherit
  rm -rf "$CASE/precice-run" "$CASE/restart"
  rm -f fluid/restart_flow_*.dat fluid/flow_*.vtu fluid/surface_*.vtu fluid/history.csv "$WATCH"
  # ONLY our inlet_<iter>.dat symlinks — NEVER the real inlet_00000.dat profile.
  find fluid -maxdepth 1 -name 'inlet_[0-9]*.dat' -type l -delete 2>/dev/null || true
  ( cd solid && rm -f glob.* vola.* pick.code_aster.* fort.* ./*.mess \
        solid_*.med run_solid_result.med ) 2>/dev/null || true
}

run_coupled() {  # $1=label ; uses env FLUID_CFG, FLUID_RESTART, SOLID_RESTART
  local label="$1"
  rm -f "$WATCH"                                   # fresh watch-point each run
  echo "  launching fluid + solid (NPROC=$NPROC) ..."
  ( cd fluid && FLUID_NPROC="$NPROC" CONFIG_FILE="$FLUID_CFG" \
       FLUID_RESTART="${FLUID_RESTART:-0}" ./run.sh ) >"$OUT/$label.fluid.log" 2>&1 &
  local fpid=$!
  ( cd solid && SOLID_RESTART="${SOLID_RESTART:-0}" ./run.sh ) >"$OUT/$label.solid.log" 2>&1 &
  local spid=$!
  wait "$fpid"; local fr=$?
  wait "$spid"; local sr=$?
  echo "  $label: fluid exit=$fr  solid exit=$sr"
  [ "$fr" -eq 0 ] && [ "$sr" -eq 0 ]
}

echo "######## regression: T_R=$T_R  T_END=$T_END  NPROC=$NPROC ########"

echo "## 1) BASELINE 0 -> $T_END"
clean_case
python3 prepare_restart.py --fresh --total "$T_END" || exit 1
FLUID_CFG=config_fluid_run.cfg FLUID_RESTART=0 SOLID_RESTART=0 run_coupled baseline \
  || { echo "baseline run failed — see $OUT/baseline.*.log"; exit 1; }
cp "$WATCH" "$OUT/baseline_tip.log"

echo "## 2) SEGMENT 0 -> $T_R  (make restart files)"
clean_case
python3 prepare_restart.py --fresh --total "$T_R" || exit 1
FLUID_CFG=config_fluid_run.cfg FLUID_RESTART=0 SOLID_RESTART=0 run_coupled segment \
  || { echo "segment run failed — see $OUT/segment.*.log"; exit 1; }
echo "  restart artifacts:"; ls -1 restart/ 2>/dev/null | sed 's/^/    /'
ls -1 fluid/restart_flow_*.dat 2>/dev/null | sed 's/^/    /'

echo "## 3) RESTART $T_R -> $T_END"
python3 prepare_restart.py --total "$T_END" || exit 1
FLUID_CFG=config_fluid_restart.cfg FLUID_RESTART=1 SOLID_RESTART=1 run_coupled restart \
  || { echo "restart run failed — see $OUT/restart.*.log"; exit 1; }
cp "$WATCH" "$OUT/restart_tip.log"

echo "## 4) COMPARE baseline vs restart (tip-Y over [$T_R,$T_END])"
python3 compare_tip.py "$OUT/baseline_tip.log" "$OUT/restart_tip.log" "$T_R"
