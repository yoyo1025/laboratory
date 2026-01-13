OUT=container_stats.csv
echo "elapsed_sec,container_name,cpu_percent,mem_used,mem_limit,mem_percent" > "$OUT"

start_epoch=$(date +%s)

prev_sec=""
seen_names=""

docker stats \
  --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
| sed -u 's/\x1b\[[0-9;]*[a-zA-Z]//g' \
| while IFS= read -r line; do
    now_epoch=$(date +%s)
    elapsed=$((now_epoch - start_epoch))

    name=$(echo "$line" | cut -d',' -f1)

    # 1秒単位でリセット
    if [ "$elapsed" != "$prev_sec" ]; then
      prev_sec="$elapsed"
      seen_names=""
    fi

    # 同じ秒で同じコンテナは捨てる
    case ",$seen_names," in
      *,"$name",*)
        continue
        ;;
    esac

    # 記録済みに追加
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
