#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-}"
RPS="${2:-}"
OUTDIR_SUFFIX="${3:-result/deliverly/edge-hit-50}"

if [ -z "$TARGET" ] || [ -z "$RPS" ]; then
  echo "usage: $0 cloud|edge1|edge2|edge3|1|2|3 RPS [OUTDIR_SUFFIX]" >&2
  exit 1
fi

EDGE_NUM=""
ROLE_LABEL=""
if [ "$TARGET" = "cloud" ]; then
  ROLE_LABEL="cloud"
else
  case "$TARGET" in
    1|edge1) EDGE_NUM="1" ;;
    2|edge2) EDGE_NUM="2" ;;
    3|edge3) EDGE_NUM="3" ;;
    *)
      echo "TARGET must be cloud, edge1, edge2, edge3, or 1-3" >&2
      exit 1
      ;;
  esac
  ROLE_LABEL="edge${EDGE_NUM}"
fi

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ "$ROLE_LABEL" = "cloud" ]; then
  COMPOSE_FILE="$BASE_DIR/cloud/compose.yml"
  OUTDIR="$BASE_DIR/cloud/$OUTDIR_SUFFIX"
  PROJECT="cloud"
  SERVICE="cloud-api"
else
  COMPOSE_FILE="$BASE_DIR/edge${EDGE_NUM}/compose.yml"
  OUTDIR="$BASE_DIR/edge${EDGE_NUM}/$OUTDIR_SUFFIX"
  PROJECT="edge${EDGE_NUM}"
  SERVICE="edge${EDGE_NUM}-api"
fi
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

mkdir -p "$OUTDIR"

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

PROCESSED_OUT="$OUTDIR/delivery_times_${ROLE_LABEL}_${RPS}rps_distribute.csv"
RETENTION_OUT="$OUTDIR/retention_delivery_process_counts_${ROLE_LABEL}_${RPS}rps_distribute.csv"
ENDPOINT_OUT="$OUTDIR/endpoint_times_${ROLE_LABEL}_${RPS}rps_distribute.csv"

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
