"""Merge a single-reader round of whole-entry readings into one book's training/annotations.json.

Usage: .venv/bin/python -I pipeline/merge_single_reading.py data/<book> ROUND_DIR --reviewer "..."
           [--proposals training/line_proposals_years_v2.json] [--replace] [--dry-run]

ROUND_DIR holds all_results.json: [{"id", "text", "status": image_checked|draft|rejected_crop,
"note"}], one record per line crop, written by readers who saw neither a recognizer draft nor
another reading. The book is a required argument and is never taken from the environment: the
round must lie inside that book's folder, and every id must exist in that book's proposals, or
nothing is written.

Geometry, checksums, split and the proposal's `line` record (the line's rows and slope, used to
level sloped crops) are copied from the proposals. A record marked image_checked whose text is
empty or carries a doubt mark ([, ], ?) is demoted to draft; a draft without text becomes a
rejected crop. One reader, so independent_verification is false. Existing ids are only replaced
with --replace.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {'image_checked', 'draft', 'rejected_crop'}
COPY = ['scan', 'row_id', 'cell', 'source_image', 'source_sha256', 'bbox', 'bbox_v1', 'line', 'image',
        'image_sha256', 'mask_fill', 'refine_flag', 'split', 'hand_group']


def build(results, props, reviewer, label_batch):
    """Annotation records for a round's results; raises ValueError on unknown or repeated ids."""
    missing = [r['id'] for r in results if r['id'] not in props]
    if missing:
        raise ValueError(f'{len(missing)} ids are not in this book\'s proposals (e.g. {missing[:3]}): wrong book or stale round')
    seen, out, demoted = set(), [], []
    for r in results:
        ident, status, text = r['id'], r['status'], ' '.join((r.get('text') or '').split())
        if ident in seen:
            raise ValueError(f'Duplicate id in round: {ident}')
        seen.add(ident)
        if status not in STATUSES:
            raise ValueError(f'Bad status {status}: {ident}')
        note = r.get('note') or ''
        if status == 'image_checked' and (not text or any(c in text for c in '[]?')):
            status = 'draft'
            demoted.append(ident)
            note = (note + ' [marked checked by the reader, but the text is empty or doubtful: kept as draft]').strip()
        if status == 'draft' and not text:
            status = 'rejected_crop'
        p = props[ident]
        out.append({'id': ident, **{k: p.get(k) for k in COPY}, 'text': text if status != 'rejected_crop' else None,
                    'status': status, 'reviewer': reviewer, 'baseline_seen': False,
                    'independent_verification': False, 'label_batch': label_batch, 'notes': note})
    return out, demoted


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('book', type=Path, help='book folder, e.g. data/salantai-1517-1-1')
    ap.add_argument('round', type=Path, help='round folder with all_results.json')
    ap.add_argument('--reviewer', required=True)
    ap.add_argument('--proposals', default='training/line_proposals_years_v2.json')
    ap.add_argument('--replace', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    book = (args.book if args.book.is_absolute() else ROOT / args.book).resolve()
    rnd = (args.round if args.round.is_absolute() else ROOT / args.round).resolve()
    if not (book / 'training').is_dir():
        raise SystemExit(f'Not a book folder: {book}')
    if book not in rnd.parents:
        raise SystemExit(f'Round {rnd} is not inside book {book}')
    props = {p['id']: p for p in json.loads((book / args.proposals).read_text())}
    results = json.loads((rnd / 'all_results.json').read_text())
    try:
        recs, demoted = build(results, props, args.reviewer, str(rnd.relative_to(ROOT)))
    except ValueError as e:
        raise SystemExit(str(e))
    ann_path = book / 'training/annotations.json'
    ann = json.loads(ann_path.read_text())
    index = {a['id']: n for n, a in enumerate(ann)}
    clash = [r['id'] for r in recs if r['id'] in index]
    if clash and not args.replace:
        raise SystemExit(f'{len(clash)} ids already annotated (use --replace), e.g. {clash[:3]}')
    for r in recs:
        if r['id'] in index:
            ann[index[r['id']]] = r
        else:
            index[r['id']] = len(ann)
            ann.append(r)
    if not args.dry_run:
        ann_path.write_text(json.dumps(ann, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'book': str(book.relative_to(ROOT)), 'round': str(rnd.relative_to(ROOT)), 'records': len(recs),
                      **Counter(r['status'] for r in recs),
                      'checked_by_split': dict(Counter(r['split'] for r in recs if r['status'] == 'image_checked')),
                      'demoted_to_draft': demoted, 'replaced': len(clash), 'annotations_total': len(ann),
                      'written': not args.dry_run}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
