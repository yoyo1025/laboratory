#!/usr/bin/env bash
set -euo pipefail

OUT="container_stats.csv"
exp_duration=60

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

# docker stats を FIFO に流す
docker stats \
  --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
  > "$tmp_fifo" &
stats_pid=$!

# docker stats 開始から60秒後に止める（開始時刻は後で決める）
(
  while [ -z "${start_epoch:-}" ]; do
    sleep 0.01
  done
  sleep "$exp_duration"
  kill "$stats_pid" 2>/dev/null || true
) &

prev_sec=""
seen_names=""
start_epoch=""

sed -u 's/\x1b\[[0-9;]*[a-zA-Z]//g' < "$tmp_fifo" \
| while IFS= read -r line; do

    # ★ 最初の出力が来た瞬間を 0 秒にする
    if [ -z "$start_epoch" ]; then
      start_epoch=$(date +%s)
    fi

    now_epoch=$(date +%s)
    elapsed=$((now_epoch - start_epoch))

    if [ "$elapsed" -ge "$exp_duration" ]; then
      break
    fi

    name=$(echo "$line" | cut -d',' -f1)

    if [ "$elapsed" != "$prev_sec" ]; then
      prev_sec="$elapsed"
      seen_names=""
    fi

    case ",$seen_names," in
      *,"$name",*) continue ;;
    esac
    seen_names="${seen_names},${name}"

    echo "$line" \
    | awk -F',' -v elapsed="$elapsed" '
      {
        split($3, mem, " / ");
        gsub(/%/, "", $2);
        gsub(/%/, "", $4);
        printf "%s,%s,%s,%s,%s,%s\n",
          elapsed, $1, $2, mem[1], mem[2], $4
      }'
done >> "$OUT"

exit 0
