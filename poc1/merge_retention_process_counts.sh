BASE="/Users/tadanoyousei/laboratory/poc1"
OUTDIR="$BASE/result"
mkdir -p "$OUTDIR"

for rps in 10 20 30 40 50 60 70 80; do
  out="$OUTDIR/alignment_time_${rps}rps_new.csv"
  : > "$out"  # 空で初期化

  for edge in 1 2 3; do
    f="$BASE/edge${edge}/result/retention_process_counts_edge${edge}_${rps}rps.csv"
    if [ -f "$f" ]; then
      cat "$f" >> "$out"
    else
      echo "missing: $f" >&2
    fi
  done

  echo "created: $out"
done
