#!/bin/bash
# Draft all lines of one proposals source with a model, in N parallel GPU processes, then merge.
# Usage: SAMOGITIA_BOOK=data/<book> pipeline/draft_shards.sh MODEL.safetensors SOURCE N
#   SOURCE: proposals_v2 | years_v2 | annotations   (see predict_lines.py)
# Prints the merged prediction directory on the last line.
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL=$1; SRC=$2; N=${3:-6}
export TMPDIR=${TMPDIR:-/tmp}
# each shard is CPU-bound in data loading; cap math threads so N shards share the cores
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-3} MKL_NUM_THREADS=${MKL_NUM_THREADS:-3}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
LOG=$(mktemp -d)
for ((k=0; k<N; k++)); do
  nice -n 10 .venv-htr/bin/python -I pipeline/predict_lines.py --model "$MODEL" --ids-from "$SRC" --shard "$k/$N" --batch-size 8 > "$LOG/$k.log" 2>&1 &
done
wait
DIRS=()
for ((k=0; k<N; k++)); do
  d=$(tail -1 "$LOG/$k.log")
  [ -d "$d" ] || { echo "shard $k failed:"; tail -5 "$LOG/$k.log"; exit 1; }
  DIRS+=("$d")
done
.venv/bin/python -I pipeline/predict_lines.py --model "$MODEL" --merge "${DIRS[@]}" | tail -1
