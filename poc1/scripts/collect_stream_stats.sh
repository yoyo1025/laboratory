#!/usr/bin/env bash
set -euo pipefail

EDGE="${1:-}"
RPS="${2:-}"
DURATION="${3:-}"
OUTDIR_SUFFIX="${4:-result/deliverly}"

if [ -z "$EDGE" ] || [ -z "$RPS" ] || [ -z "$DURATION" ]; then
  echo "usage: $0 EDGE RPS DURATION_SEC [OUTDIR_SUFFIX]" >&2
  exit 1
fi

case "$EDGE" in
  1|2|3) ;;
  *)
    echo "EDGE must be 1, 2, or 3" >&2
    exit 1
    ;;
esac

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$BASE_DIR/edge${EDGE}/compose.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

OUTDIR="$BASE_DIR/edge${EDGE}/${OUTDIR_SUFFIX}"
mkdir -p "$OUTDIR"

PROJECT="edge${EDGE}"
SERVICE="edge${EDGE}-api"
INTERVAL="${INTERVAL:-1}"

COMPOSE_CMD=(${COMPOSE:-docker compose})
CONTAINER_ID="$("${COMPOSE_CMD[@]}" -p "$PROJECT" -f "$COMPOSE_FILE" ps -q "$SERVICE")"
if [ -z "$CONTAINER_ID" ]; then
  echo "container not running: $SERVICE" >&2
  exit 1
fi

OUTFILE="$OUTDIR/stats_edge${EDGE}_${RPS}rps.csv"
echo "timestamp,cpu_percent,mem_usage,mem_percent" > "$OUTFILE"

SECONDS=0
while [ "$SECONDS" -lt "$DURATION" ]; do
  docker stats --no-stream --format "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" "$CONTAINER_ID" \
    | awk -v ts="$(date '+%H:%M:%S')" '{print ts "," $0}' >> "$OUTFILE"
  sleep "$INTERVAL"
done

echo "created: $OUTFILE"
