#!/usr/bin/env bash
set -euo pipefail

RPS="${1:-}"
exp_duration=60

if [ -z "$RPS" ]; then
  echo "usage: $0 RPS" >&2
  exit 1
fi

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="$BASE_DIR/result/delivery"
mkdir -p "$OUTDIR"

OUT="$OUTDIR/container_stats_${RPS}rps_concentrate.csv"

echo "elapsed_sec,container_name,cpu_percent,mem_used,mem_limit,mem_percent" > "$OUT"

tmp_fifo="$(mktemp -u)"
mkfifo "$tmp_fifo"

cleanup() {
  if [[ -n "${stats_pid:-}" ]] && kill -0 "$stats_pid" 2>/dev/null; then
    kill "$stats_pid" 2>/dev/null || true
    sleep 0.2
    kill -9 "$stats_pid" 2>/dev/null || true
  fi
  rm -f "$tmp_fifo"
}
trap cleanup EXIT INT TERM

# ===== ミリ秒時刻取得（mac / Linux 両対応）=====
now_ms() {
  if command -v gdate >/dev/null 2>&1; then
    # coreutils が入っている場合
    gdate +%s%3N
  else
    # macOS 標準
    python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
  fi
}

# docker stats を FIFO に流す
docker stats \
  --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
  > "$tmp_fifo" &
stats_pid=$!

# docker stats 開始から exp_duration 秒後に止める
(
  while [ -z "${start_ms:-}" ]; do
    sleep 0.01
  done
  sleep "$exp_duration"
  kill "$stats_pid" 2>/dev/null || true
) &

prev_sec=""
seen_names=""
start_ms=""

sed -u 's/\x1b\[[0-9;]*[a-zA-Z]//g' < "$tmp_fifo" \
| while IFS= read -r line; do

    # 最初の出力が来た瞬間を 0 秒にする
    if [ -z "$start_ms" ]; then
      start_ms="$(now_ms)"
    fi

    now="$(now_ms)"
    elapsed_ms=$((now - start_ms))

    # 内部制御は秒単位
    elapsed_sec_int=$((elapsed_ms / 1000))

    if [ "$elapsed_sec_int" -ge "$exp_duration" ]; then
      break
    fi

    # 表示用（例: 1.234）
    elapsed_disp=$(awk -v ms="$elapsed_ms" 'BEGIN { printf "%.3f", ms/1000 }')

    name=$(echo "$line" | cut -d',' -f1)

    # 各秒・各コンテナ1回だけ出す
    if [ "$elapsed_sec_int" != "$prev_sec" ]; then
      prev_sec="$elapsed_sec_int"
      seen_names=""
    fi

    case ",$seen_names," in
      *,"$name",*) continue ;;
    esac
    seen_names="${seen_names},${name}"

    echo "$line" \
    | awk -F',' -v elapsed="$elapsed_disp" '
      {
        split($3, mem, " / ");
        gsub(/%/, "", $2);
        gsub(/%/, "", $4);
        printf "%s,%s,%s,%s,%s,%s\n",
          elapsed, $1, $2, mem[1], mem[2], $4
      }'
done >> "$OUT"

exit 0
