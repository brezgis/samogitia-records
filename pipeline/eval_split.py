"""Score one or more prediction runs against checked labels of one split.

Usage: .venv/bin/python -I pipeline/eval_split.py --split validation RUN_DIR [RUN_DIR...]

RUN_DIR is a training/baseline/<run_id>/ directory (from baseline_htr.py run with
--ids-from annotations) or any directory holding predictions.json. References are
annotations with status image_checked/independently_checked in that split, after the
same integrity checks as the export. Prints CER/WER overall, per hand and per cell,
plus the worst lines. Single-reader labels: scores measure agreement with one
reader's transcription, not verified accuracy.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_htr import distance, evaluate  # noqa: E402
from htr_dataset import checked_labels  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--split', default='validation', choices=['train', 'validation', 'test'])
    ap.add_argument('--worst', type=int, default=6)
    ap.add_argument('runs', nargs='+', type=Path)
    args = ap.parse_args()
    refs = [a for a in checked_labels(json.loads((BOOK / 'training/annotations.json').read_text()))
            if a['split'] == args.split]
    ref_ids = {r['id'] for r in refs}
    for run in args.runs:
        preds = [p for p in json.loads((run / 'predictions.json').read_text()) if p['id'] in ref_ids]
        res = evaluate(refs, preds)
        print(f'\n== {run.name}  ({args.split}, {len(refs)} lines)')
        for k in sorted(res):
            m = res[k]
            print(f"  {k:24} lines={m['lines']:4} CER={m['cer']:.3f} WER={m['wer']:.3f} exact={m['exact_lines']}")
        P = {p['id']: p['text'] for p in preds}
        worst = sorted(refs, key=lambda r: -distance(r['text'], P.get(r['id'], '')) / max(1, len(r['text'])))
        for r in worst[:args.worst]:
            print(f"    ref  {r['text']!r}\n    pred {P.get(r['id'], '')!r}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
