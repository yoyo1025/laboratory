#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INDIR_SUFFIX="result/deliverly/edge-hit-30"
OUTDIR="$BASE_DIR/result/delivery/edge-hit-30"
MODE="distribute"
RPS_LIST=(10 30 50 70 90 110 130 150 170)

mkdir -p "$OUTDIR"

for rps in "${RPS_LIST[@]}"; do
  delivery_out="$OUTDIR/delivery_times_${rps}rps_${MODE}.csv"
  endpoint_out="$OUTDIR/endpoint_times_${rps}rps_${MODE}.csv"
  retention_out="$OUTDIR/retention_delivery_process_counts_${rps}rps_${MODE}.csv"

  : > "$delivery_out"
  : > "$endpoint_out"
  : > "$retention_out"

  for edge in 1 2 3; do
    delivery_in="$BASE_DIR/edge${edge}/${INDIR_SUFFIX}/delivery_times_edge${edge}_${rps}rps_${MODE}.csv"
    endpoint_in="$BASE_DIR/edge${edge}/${INDIR_SUFFIX}/endpoint_times_edge${edge}_${rps}rps_${MODE}.csv"
    retention_in="$BASE_DIR/edge${edge}/${INDIR_SUFFIX}/retention_delivery_process_counts_edge${edge}_${rps}rps_${MODE}.csv"

    if [ -f "$delivery_in" ]; then
      cat "$delivery_in" >> "$delivery_out"
    else
      echo "missing: $delivery_in" >&2
    fi

    if [ -f "$endpoint_in" ]; then
      cat "$endpoint_in" >> "$endpoint_out"
    else
      echo "missing: $endpoint_in" >&2
    fi

    if [ -f "$retention_in" ]; then
      awk -F',' -v OFS=',' 'NR==1 { base=$2 } { $2 = $2 - base; print }' "$retention_in" >> "$retention_out"
    else
      echo "missing: $retention_in" >&2
    fi
  done

  echo "created: $delivery_out"
  echo "created: $endpoint_out"
  echo "created: $retention_out"
done
