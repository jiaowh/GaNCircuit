#!/usr/bin/env bash
# Thermal runs of 10 October 2026 (declared in plans/goal-targets-2026-10-08.md). One line per layout:
# tag | export dir ('' = EPC Gerbers) | goals report | design | copper map | extra args
set -euo pipefail
cd "$(dirname "$0")/.."
X=vendor/epc/epc90133/reconstruction/export
G=results/gan
run() {
  local tag=$1 exp=$2 goals=$3 design=$4 map=$5; shift 5
  if [ -n "$exp" ]; then export EPC90133_GERBER_EXPORT=$exp; fi; PYTHONPATH=src python scripts/epc90133_thermal.py --tag "$tag" --goals "$goals" \
    --design "$design" --copper-map "$map" --factor 8 --h 5 10 25 --k-lam 0.2 0.4 0.6 --spreader "$@" \
    > "runs/thermal/$tag.log" 2>&1
}
export -f run
cat <<JOBS | xargs -P 3 -L 1 bash -c 'run "$@"' _
stock "" $G/epc90133-goals-G.json stock runs/thermal/copper-heat-stock-f8.npz
stock-route $X/stock $G/epc90133-goals-G.json stock runs/thermal/copper-heat-stock-route-f8.npz
V8 $X/V8 $G/epc90133-goals-G.json V8 runs/thermal/copper-heat-V8-route-f8.npz
V8d075 $X/V8 $G/epc90133-goals-G-V8d075.json V8d075 runs/thermal/copper-heat-V8-route-f8.npz --top-dielectric-mm 0.075
K1 $X/K1 $G/epc90133-goals-G-K1.json K1 runs/thermal/copper-heat-K1-route-f8.npz
K2 $X/K2 $G/epc90133-goals-G-K2.json K2 runs/thermal/copper-heat-K2-route-f8.npz
JOBS
