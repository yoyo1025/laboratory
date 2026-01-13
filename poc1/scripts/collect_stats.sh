#!/usr/bin/env bash
set -euo pipefail

OUT="container_stats.csv"
exp_duration=60

echo "elapsed_sec,container_name,cpu_percent,mem_used,mem_limit,mem_percent" > "$OUT"
start_epoch=$(date +%s)

tmp_fifo="$(mktemp -u)"
mkfifo "$tmp_fifo"

cleanup() {
  # statsプロセスが生きてたら止める
  if [[ -n "${stats_pid:-}" ]] && kill -0 "$stats_pid" 2>/dev/null; then
    kill "$stats_pid" 2>/dev/null || true
    # 念のため少し待って、残ってたら強制終了
    sleep 0.2
    kill -9 "$stats_pid" 2>/dev/null || true
  fi
  rm -f "$tmp_fifo"
}
trap cleanup EXIT INT TERM

# docker stats を FIFO に流す（このPIDを60秒後に止める）
docker stats \
  --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
  > "$tmp_fifo" &
stats_pid=$!

# 60秒経ったら docker stats を止める（正常終了扱い）
(
  sleep "$exp_duration"
  kill "$stats_pid" 2>/dev/null || true
) &

prev_sec=""
seen_names=""

# FIFO から読み取り → CSVへ
sed -u 's/\x1b\[[0-9;]*[a-zA-Z]//g' < "$tmp_fifo" \
| while IFS= read -r line; do
    now_epoch=$(date +%s)
    elapsed=$((now_epoch - start_epoch))

    # ここで超過してたら抜ける（後始末はtrapに任せる）
    if [ "$elapsed" -gt "$exp_duration" ]; then
      break
    fi

    name=$(echo "$line" | cut -d',' -f1)

    # 1秒単位でリセット
    if [ "$elapsed" != "$prev_sec" ]; then
      prev_sec="$elapsed"
      seen_names=""
    fi

    # 同じ秒で同じコンテナは捨てる
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
