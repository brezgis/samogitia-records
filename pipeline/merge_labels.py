"""Merge a batch of line transcriptions into training/annotations.json.

Usage: .venv/bin/python -I pipeline/merge_labels.py training/labels/<batch>.json

Batch file: {"reviewer": "...", "baseline_seen": true|false, "notes": "...",
             "lines": [{"id": "<line_proposals_v2 id>", "text": "...",
                        "status": "image_checked" | "draft" | "rejected_crop",
                        "note": "..."}]}

- image_checked: every character read with confidence from the crop (and the
  scan when needed). Exported for training/evaluation. NOT independent
  verification; that requires a second reader who has not seen this label.
- draft: text contains a doubt; uncertain spans are marked [..?]. Never exported.
- rejected_crop: crop itself is unusable (merged lines, cut glyphs, foreign ink).

The crop, bbox, checksums and mask fill are copied from line_proposals_v2.json
so the export can re-verify the pixels. Existing ids are only replaced with
--replace.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'data/plunge-1886-1890'
STATUSES = {'image_checked', 'draft', 'rejected_crop'}
COPY = ['scan', 'row_id', 'cell', 'source_image', 'source_sha256', 'bbox', 'bbox_v1', 'image',
        'image_sha256', 'mask_fill', 'refine_flag', 'split', 'hand_group']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('batch', type=Path)
    ap.add_argument('--replace', action='store_true')
    args = ap.parse_args()
    batch_path = args.batch if args.batch.is_absolute() else BOOK / args.batch
    batch = json.loads(batch_path.read_text())
    props = {p['id']: p for p in json.loads((BOOK / 'training/line_proposals_v2.json').read_text())}
    ann_path = BOOK / 'training/annotations.json'
    ann = json.loads(ann_path.read_text())
    index = {a['id']: n for n, a in enumerate(ann)}
    seen, counts = set(), {}
    for line in batch['lines']:
        ident, status, text = line['id'], line['status'], line.get('text')
        if ident in seen:
            raise SystemExit(f'Duplicate id in batch: {ident}')
        seen.add(ident)
        if ident not in props:
            raise SystemExit(f'Unknown proposal id: {ident}')
        if status not in STATUSES:
            raise SystemExit(f'Bad status {status}: {ident}')
        if status == 'image_checked' and (not text or any(c in text for c in '[]?\n')):
            raise SystemExit(f'Checked label is empty or marked uncertain: {ident}')
        if status == 'draft' and not text:
            raise SystemExit(f'Draft without text: {ident}')
        if ident in index and not args.replace:
            raise SystemExit(f'Already annotated (use --replace): {ident}')
        p = props[ident]
        rec = {'id': ident, **{k: p.get(k) for k in COPY}, 'text': text if status != 'rejected_crop' else None,
               'status': status, 'reviewer': batch['reviewer'], 'baseline_seen': batch.get('baseline_seen'),
               'independent_verification': False, 'label_batch': str(batch_path.relative_to(ROOT)),
               'notes': line.get('note', '')}
        if ident in index:
            ann[index[ident]] = rec
        else:
            index[ident] = len(ann)
            ann.append(rec)
        counts[status] = counts.get(status, 0) + 1
    ann_path.write_text(json.dumps(ann, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'batch': str(batch_path.relative_to(ROOT)), **counts, 'annotations_total': len(ann)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
