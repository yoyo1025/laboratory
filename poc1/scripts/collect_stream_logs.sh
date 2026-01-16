#!/usr/bin/env bash
set -euo pipefail

EDGE="${1:-}"
RPS="${2:-}"
OUTDIR_SUFFIX="${3:-result/deliverly}"

if [ -z "$EDGE" ] || [ -z "$RPS" ]; then
  echo "usage: $0 EDGE RPS [OUTDIR_SUFFIX]" >&2
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

COMPOSE_CMD=(${COMPOSE:-docker compose})
LOG_ARGS=("${COMPOSE_CMD[@]}" -p "$PROJECT" -f "$COMPOSE_FILE" logs --no-color)
if [ "${NO_LOG_PREFIX:-1}" = "1" ]; then
  LOG_ARGS+=(--no-log-prefix)
fi
if [ -n "${SINCE:-}" ]; then
  LOG_ARGS+=(--since "$SINCE")
fi
if [ -n "${UNTIL:-}" ]; then
  LOG_ARGS+=(--until "$UNTIL")
fi
LOG_ARGS+=("$SERVICE")

PROCESSED_OUT="$OUTDIR/delivery_times_edge${EDGE}_${RPS}rps_concentrate.csv"
RETENTION_OUT="$OUTDIR/retention_delivery_process_counts_edge${EDGE}_${RPS}rps_concentrate.csv"
ENDPOINT_OUT="$OUTDIR/endpoint_times_edge${EDGE}_${RPS}rps_concentrate.csv"

: > "$PROCESSED_OUT"
: > "$RETENTION_OUT"
: > "$ENDPOINT_OUT"

"${LOG_ARGS[@]}" | awk -F': ' \
  -v processed_out="$PROCESSED_OUT" \
  -v retention_out="$RETENTION_OUT" \
  -v endpoint_out="$ENDPOINT_OUT" \
  '
  /^processed_time_stream\./ {
    key=$1
    sub(/^processed_time_stream\./,"",key)
    if (key == "endpoint_ms") {
      print key "," $2 >> endpoint_out
      next
    }
    print key "," $2 >> processed_out
    next
  }
  /^retention_stream\./ {
    sub(/^retention_stream\./,"",$1)
    print $0 >> retention_out
  }
'

echo "created: $PROCESSED_OUT"
echo "created: $RETENTION_OUT"
echo "created: $ENDPOINT_OUT"
