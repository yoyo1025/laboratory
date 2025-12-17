BASE="/Users/tadanoyousei/laboratory/poc1"
OUTDIR="$BASE/result"
mkdir -p "$OUTDIR"

for rps in 10 20 30 40 50 60 70 80; do
  out="$OUTDIR/alignment_times_${rps}rps_new.csv"

  cat \
    "$BASE/edge1/result/alignment_times_edge1_${rps}rps_new.csv" \
    "$BASE/edge2/result/alignment_times_edge2_${rps}rps_new.csv" \
    "$BASE/edge3/result/alignment_times_edge3_${rps}rps_new.csv" \
    > "$out"

  echo "created: $out"
done
