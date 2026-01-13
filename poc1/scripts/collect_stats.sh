OUT=container_stats.csv
echo "timestamp,container_name,cpu_percent,mem_used,mem_limit,mem_percent" > "$OUT"

prev_ts=""
seen_names=""

docker stats \
  --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}" \
| sed -u 's/\x1b\[[0-9;]*[a-zA-Z]//g' \
| while IFS= read -r line; do
    ts=$(date -Iseconds)
    name=$(echo "$line" | cut -d',' -f1)

    # 秒が変わったらリセット
    if [ "$ts" != "$prev_ts" ]; then
      prev_ts="$ts"
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

    # 出力（表示形式はあなたのコードそのまま）
    echo "$line" \
    | awk -F',' -v ts="$ts" '
      {
        split($3, mem, " / ");
        gsub(/%/, "", $2);
        gsub(/%/, "", $4);
        printf "%s,%s,%s,%s,%s,%s\n",
          ts, $1, $2, mem[1], mem[2], $4
      }'
  done >> "$OUT"
