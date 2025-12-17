BASE="/Users/tadanoyousei/laboratory/poc1"
OUTDIR="$BASE/result"
mkdir -p "$OUTDIR"

for rps in 10 20 30 40 50 60 70 80; do
  out="$OUTDIR/retention_process_counts_${rps}rps_new.csv"

  cat \
    "$BASE/edge1/result/retention_process_counts_edge1_${rps}rps_new.csv" \
    "$BASE/edge2/result/retention_process_counts_edge2_${rps}rps_new.csv" \
    "$BASE/edge3/result/retention_process_counts_edge3_${rps}rps_new.csv" \
    > "$out"

  echo "created: $out"
done
