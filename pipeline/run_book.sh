#!/bin/bash
# Process one downloaded register book up to machine drafts (no agents).
# Usage: pipeline/run_book.sh data/<book> MODEL_DIR_NAME [SIDE_MODE]
#   e.g. pipeline/run_book.sh data/plunge-1827-1-25 plunge-v4 wide
# Steps: layout -> queue -> line split -> refine -> GPU draft -> year inference ->
#        per-year assembly + field extraction -> side-column sheets.
# Writes progress to stdout; prints the detected years at the end.
set -euo pipefail
cd "$(dirname "$0")/.."
BOOK=$1; MODEL=$2; SIDE=${3:-wide}
export SAMOGITIA_BOOK=$BOOK
export TMPDIR=${TMPDIR:-/tmp}
N=$(ls "$BOOK"/pages/*.jpg | wc -l)
echo "== $BOOK: $N scans"
nice .venv/bin/python -I pipeline/layout.py "$BOOK/pages" "$BOOK" 1 "$N" | tail -1
if grep -q '"spread"' "$BOOK/form.json" 2>/dev/null; then   # one entry spans both pages (e.g. 1827/1/20)
  rm -rf "$BOOK/layout_pages"
  .venv/bin/python -I pipeline/layout_spread.py "$BOOK"
fi
nice .venv/bin/python -I pipeline/prepare_years.py --scans "1-$N"
nice .venv/bin/python -I pipeline/segment_lines.py --queue processed/queue_years.json --all-rows \
  --scans $(seq -s ' ' 1 "$N") --out-json training/line_proposals_years.json --out-dir training/proposals_years \
  | tail -1 | cut -c1-120
nice .venv/bin/python -I pipeline/refine_lines.py --in-json training/line_proposals_years.json \
  --out-json training/line_proposals_years_v2.json --out-dir training/proposals_years_v2
rm -rf "$BOOK/training/proposals_years" "$BOOK/debug"   # first-stage crops/overlays: regenerable, large
mkdir -p "$BOOK/training" "$BOOK/processed"
[ -f "$BOOK/training/annotations.json" ] || echo "[]" > "$BOOK/training/annotations.json"   # a new book has no labels yet
PRED=$(pipeline/draft_shards.sh "/mnt/ssd240gb/anna/samogitia-htr/models/$MODEL/model.safetensors" years_v2 6 | tail -1)
rm -rf "$BOOK"/training/predictions/*shard*
echo "drafts: $PRED"
echo "$PRED" > "$BOOK/processed/latest_predictions.txt"
.venv/bin/python -I pipeline/infer_years.py "$PRED" > "$BOOK/processed/years_pass1.json"
YEARS=$(.venv/bin/python -I -c "
import json,collections
q=json.load(open('$BOOK/processed/queue_years.json'))
c=collections.Counter(x['register_year'] for x in q if x['register_year'])
print(' '.join(str(y) for y,n in sorted(c.items()) if n>=20))")
echo "years: $YEARS"
for Y in $YEARS; do
  .venv/bin/python -I pipeline/assemble_drafts.py "$PRED" --queue processed/queue_years.json \
    --proposals training/line_proposals_years_v2.json --year "$Y" | cut -c1-80
  .venv/bin/python -I pipeline/parse_entries.py "processed/year_draft_${Y}_${MODEL}.json" | cut -c1-160
done
SHEETS=${SIDE_SHEETS:-$TMPDIR/side_$(basename "$BOOK")}
rm -rf "$SHEETS"
SIDE_MODE=$SIDE SIDE_PER_SHEET=2 nice .venv/bin/python -I pipeline/side_strips.py "$SHEETS" \
  $(for Y in $YEARS; do echo "processed/year_draft_${Y}_${MODEL}.json"; done)
echo "side sheets: $SHEETS"
echo "YEARS=$YEARS"
