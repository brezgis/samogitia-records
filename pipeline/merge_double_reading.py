"""Merge a blind double-reading workflow (two readers + adjudicator) into annotations.

Usage: .venv/bin/python -I pipeline/merge_double_reading.py JOURNAL.jsonl [--dry-run]

The workflow journal records each agent's label ("A(opus):<batch>", "B(sonnet):<batch>",
"adjudicate:<batch>") and its structured result {"lines": [...]}. Raw readings are
saved to training/labels/double_read/<batch>.json for provenance.

Per line:
- both readers produced identical text (NFC, whitespace-collapsed, dashes unified, no [?]),
  crop_ok, and the adjudicator (if consulted) reached the same text from the image:
  image_checked with independent_verification=True (two blind readings agree). Reader
  self-confidence is not required: Sonnet marked most lines unsure even when correct.
- both readers rejected the crop: rejected_crop.
- otherwise the adjudicator's decision (status as given), independent_verification=False
  because the adjudicator saw both readings.
Lines already annotated (earlier single-reader labels) are compared, not overwritten:
an agreeing double reading upgrades them to independently verified; a conflicting one
demotes an image_checked label to draft and records both readings for review.
"""
import argparse
import os
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
COPY = ['scan', 'row_id', 'cell', 'source_image', 'source_sha256', 'bbox', 'bbox_v1', 'image',
        'image_sha256', 'mask_fill', 'refine_flag', 'split', 'hand_group']
AGREE = 'Blind double reading: Claude Opus 5.5 (A) + Claude Sonnet (B), agreeing'
ADJ = 'Claude Opus 5.5 adjudication of two blind readings (Opus 5.5 A, Sonnet B)'


def norm(s):
    s = unicodedata.normalize('NFC', s or '').replace('\u2014', '-').replace('\u2013', '-')
    return re.sub(r'\s+', ' ', s).strip()


def load_journal(path):
    labels, results = {}, {}
    for line in Path(path).read_text().splitlines():
        e = json.loads(line)
        if e.get('type') == 'started':
            labels[e['key']] = e['label']
        for k in ('result', 'output', 'value'):
            v = e.get(k)
            if isinstance(v, dict) and 'lines' in v and e.get('key') in labels:
                results[labels[e['key']]] = v
    out = {}
    for label, v in results.items():
        role, batch = label.split(':', 1)
        out.setdefault(batch, {})[role.split('(')[0]] = v['lines']
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('journal')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    batches = load_journal(args.journal)
    props = {}
    for name in ('line_proposals_v2.json', 'line_proposals_years_v2.json'):
        path = BOOK / 'training' / name
        if path.exists():
            props.update({p['id']: p for p in json.loads(path.read_text())})
    ann_path = BOOK / 'training/annotations.json'
    ann = json.loads(ann_path.read_text())
    index = {a['id']: n for n, a in enumerate(ann)}
    rawdir = BOOK / 'training/labels/double_read'
    stats, conflicts = Counter(), []
    for batch, roles in sorted(batches.items()):
        A = {l['id']: l for l in roles.get('A', [])}
        B = {l['id']: l for l in roles.get('B', [])}
        J = {l['id']: l for l in roles.get('adjudicate', [])}
        if not args.dry_run:
            rawdir.mkdir(parents=True, exist_ok=True)
            (rawdir / f'{batch}.json').write_text(json.dumps({'batch': batch, 'A': roles.get('A'), 'B': roles.get('B'),
                                                              'adjudicate': roles.get('adjudicate')},
                                                             ensure_ascii=False, indent=1))
        for ident in sorted(set(A) | set(B)):
            if ident not in props:
                stats['unknown_id'] += 1
                continue
            a, b = A.get(ident), B.get(ident)
            # Blind agreement: identical text from both readers, no doubt marks, crop usable.
            blind = (a and b and a['crop_ok'] and b['crop_ok'] and norm(a['text'])
                     and norm(a['text']) == norm(b['text']) and not re.search(r'[\[\]?]', a['text']))
            if a and b and not a['crop_ok'] and not b['crop_ok']:
                status, text, indep, reviewer = 'rejected_crop', None, False, AGREE
            elif ident in J:
                j = J[ident]
                status, text, indep, reviewer = j['status'], norm(j['text']) or None, False, ADJ
                if status == 'image_checked' and (not text or re.search(r'[\[\]?]', text)):
                    status = 'draft'
                if status == 'draft' and not text:
                    status = 'rejected_crop'
                if blind and status == 'image_checked' and text == norm(a['text']):
                    indep, reviewer = True, AGREE + '; confirmed by ' + ADJ
            elif blind:
                status, text, indep, reviewer = 'image_checked', norm(a['text']), True, AGREE
            else:
                stats['unresolved'] += 1
                continue
            readings = {'A': a, 'B': b, 'adjudicated': J.get(ident)}
            if ident in index:
                old = ann[index[ident]]
                if status == 'image_checked' and indep and old.get('text') and norm(old['text']) == text:
                    old['independent_verification'] = True
                    old['reviewer'] = old['reviewer'] + '; verified by ' + AGREE
                    stats['existing_verified'] += 1
                elif old['status'] == 'image_checked' and norm(old.get('text')) != (text or ''):
                    conflicts.append({'id': ident, 'existing': old['text'], 'new': text, 'new_status': status})
                    old['status'] = 'draft'
                    old['notes'] = (old.get('notes') or '') + f' [CONFLICT with double reading: {text!r} ({status})]'
                    old['double_reading'] = readings
                    stats['existing_conflict'] += 1
                else:
                    stats['existing_kept'] += 1
                continue
            p = props[ident]
            rec = {'id': ident, **{k: p.get(k) for k in COPY}, 'text': text if status != 'rejected_crop' else None,
                   'status': status, 'reviewer': reviewer, 'baseline_seen': False,
                   'independent_verification': indep, 'label_batch': f'double_read/{batch}',
                   'notes': '; '.join(x['note'] for x in (a, b, J.get(ident)) if x and x.get('note'))[:500],
                   'double_reading': readings}
            index[ident] = len(ann)
            ann.append(rec)
            stats[status + ('_indep' if indep else '')] += 1
    if not args.dry_run:
        ann_path.write_text(json.dumps(ann, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'batches': len(batches), **stats, 'annotations_total': len(ann)}, indent=1))
    for c in conflicts:
        print('CONFLICT', c)
    return 0


if __name__ == '__main__':
    sys.exit(main())
