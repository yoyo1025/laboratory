BASE="/Users/tadanoyousei/laboratory/poc1"
OUTDIR="$BASE/result"
mkdir -p "$OUTDIR"

for rps in 10 20 30 40 50 60 70 80; do
  out="$OUTDIR/alignment_total_times_${rps}rps_old.csv"

  cat \
    "$BASE/edge1/result/alignment_total_times_edge1_${rps}rps_old.csv" > "$out"

  echo "created: $out"
done
