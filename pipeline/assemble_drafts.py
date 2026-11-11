"""Assemble per-entry draft texts for the 1888 year from line predictions + checked labels.

Usage: .venv/bin/python -I pipeline/assemble_drafts.py PREDICTIONS_DIR

For every in-year queue row, each column (baptism, parents, godparents) is rebuilt from
its line crops in order. A line uses its checked label (image_checked /
independently_checked) when one exists, otherwise the model prediction. Rejected crops
are skipped. Line-end '-' or '=' joins to the next line without a space.

Outputs processed/year_draft_<model>.json and .csv. THESE ARE MACHINE DRAFTS: model
text is unverified (about 7% character error on held-out lines; names are worse),
and line boundaries can merge or drop text. Do not treat them as transcriptions.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
CELLS = ['baptism', 'parents', 'godparents']


def join_lines(parts):
    out = ''
    for t in parts:
        t = t.strip()
        if not t:
            continue
        if not out:
            out = t
        elif re.search(r'[-=]$', out):
            out = re.sub(r'[-=]$', '', out) + re.sub(r'^[-=]', '', t)
        else:
            out = out + ' ' + t
    return out

SNAP = 260   # px: how far a stored entry boundary may move to a detected entry start


def is_entry_start(text):
    """Baptism column of every entry opens with "Тысяча восемьсотъ ..."."""
    s = re.sub(r'\s+', '', text or '').lower().replace('и', 'ы')
    return bool(re.match(r'.{0,2}[ын][се][яа]ч', s)) or s.startswith('тысяч')


def is_column_start(cell, text):
    """Opening words of each column: baptism "Тысяча", parents the estate, godparents "Воспріемн..."."""
    if cell == 'baptism':
        return is_entry_start(text)
    s = re.sub(r'\s+', '', text or '').lower().lstrip('-=.,')
    if cell == 'parents':
        return 'стьян' in s[:9] or s.startswith(('двор', 'мещ', 'мѣщ', 'шлях', 'однодв'))
    return bool(re.search(r'сп[рp][іи]?е', s[:8])) or s.startswith(('воспр', 'оспр'))


def reassign(queue, props, text_of, split_missed=False, numbered=None):
    """Re-derive entry membership from detected column openings (layout boundaries are approximate).

    Per page side: each stored boundary (row focal_y start) first snaps to the nearest baptism
    line reading "Тысяча..." within SNAP px. Then, per column, it snaps again to the nearest line
    opening that column (estate word for parents, "Воспріемн..." for godparents) within SNAP px of
    the baptism boundary, because columns are not always level. A line belongs to the entry whose
    boundary for its column lies above the line's vertical centre. Boundaries without a nearby
    detected opening are kept. Returns (lines by row_id, {row_id: {cell: (old_y, new_y)}}).
    """
    side = defaultdict(list)
    for q in queue:
        side[(q['scan'], q['page'])].append(q)
    row_side = {q['row_id']: (q['scan'], q['page']) for q in queue}
    line_side = defaultdict(list)
    for p in props:
        if p['row_id'] in row_side:
            line_side[row_side[p['row_id']]].append(p)
    by_row, snapped = defaultdict(list), {}
    split_rows, folded = [], []

    def snap(y0, starts):
        near = [s for s in starts if abs(s - y0) <= SNAP]
        return (min(near, key=lambda s: abs(s - y0)) - 8) if near else y0

    for key, qs in side.items():
        qs = sorted(qs, key=lambda q: q['focal_y'][0])
        lines = line_side[key]
        starts = {c: sorted(p['bbox'][1] for p in lines if p['cell'] == c and is_column_start(c, text_of.get(p['id'])))
                  for c in ('baptism', 'parents', 'godparents')}
        if numbered is not None:
            # a layout row with neither an entry start near its top nor an entry number in the
            # side column is the second half of an entry the layout cut in two: fold it into
            # the entry above (its lines follow the previous boundary)
            kept = []
            for q in qs:
                y0 = q['focal_y'][0]
                has_start = any(abs(s - y0) <= SNAP for s in starts['baptism'])
                if kept and not has_start and q['row_id'] not in numbered:
                    folded.append(q['row_id'])
                    continue
                kept.append(q)
            qs = kept
        if split_missed:
            # entry starts far from every stored boundary are entries the layout merged into a
            # neighbouring row: give each its own pseudo-row "<row_id>b", "<row_id>c", ...
            y0s = [q['focal_y'][0] for q in qs]
            extra = []
            for s in starts['baptism']:
                if min(abs(s - y) for y in y0s) > SNAP and all(abs(s - e['focal_y'][0]) > SNAP for e in extra):
                    parent = max((q for q in qs if q['focal_y'][0] <= s), key=lambda q: q['focal_y'][0], default=qs[0])
                    n = sum(1 for e in extra if e['split_from'] == parent['row_id'])
                    extra.append({**parent, 'row_id': parent['row_id'] + 'bcdefg'[n], 'focal_y': [int(s) - 8, int(s) + 1],
                                  'split_from': parent['row_id']})
            if extra:
                qs = sorted(qs + extra, key=lambda q: q['focal_y'][0])
                split_rows.extend(extra)
        bounds = {c: [] for c in starts}
        prev_b = None
        for q in qs:
            y0 = q['focal_y'][0]
            yb = snap(y0, starts['baptism'])
            if prev_b is not None and yb == y0:
                # an entry start lying inside the previous entry belongs to this one, however far
                inside = [s for s in starts['baptism'] if prev_b + 80 < s < y0]
                if inside:
                    yb = max(inside) - 8
            prev_b = yb
            for c in starts:
                y = yb if c == 'baptism' else snap(yb, starts[c])
                if abs(y - y0) > 40:
                    snapped.setdefault(q['row_id'], {})[c] = (y0, int(y))
                bounds[c].append((y, q['row_id']))
        for p in lines:
            cy = (p['bbox'][1] + p['bbox'][3]) / 2
            bs = bounds[p['cell']]
            if cy < bs[0][0] - 40 and bs[0][0] != qs[0]['focal_y'][0]:
                continue            # above the side's first (snapped) entry start: previous-year/header carry-over
            owner = bs[0][1]
            for y, rid in bs:
                if cy >= y:
                    owner = rid
            by_row[owner].append(p)
    order = {'baptism': 0, 'parents': 1, 'godparents': 2}
    for rid in by_row:
        by_row[rid].sort(key=lambda p: (order[p['cell']], p['bbox'][1]))
    reassign.folded = folded
    return (by_row, snapped, split_rows) if split_missed else (by_row, snapped)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pred_dir', type=Path)
    ap.add_argument('--queue', default='processed/queue.json')
    ap.add_argument('--proposals', default='training/line_proposals_v2.json')
    ap.add_argument('--year', type=int, help='register year to output (default: the 1888 target rows)')
    args = ap.parse_args()
    pred_dir = args.pred_dir
    preds = {p['id']: p['text'] for p in json.loads((pred_dir / 'predictions.json').read_text())}
    model = json.loads((pred_dir / 'run.json').read_text())
    ann = {a['id']: a for a in json.loads((BOOK / 'training/annotations.json').read_text())}
    props = json.loads((BOOK / args.proposals).read_text())
    all_rows = json.loads((BOOK / args.queue).read_text())
    if args.year:
        all_rows = [q for q in all_rows if q.get('register_year')]
        queue = [q for q in all_rows if q['register_year'] == args.year]
    else:
        all_rows = queue = [q for q in all_rows if q['in_target_year']]
    text_of = {}
    for p in props:
        a = ann.get(p['id'])
        text_of[p['id']] = a['text'] if a and a.get('text') and a['status'] in ('image_checked', 'independently_checked') \
            else preds.get(p['id'], '')
    numbered = None
    side_path = BOOK / 'processed/side_columns.json'
    if args.year and side_path.exists():
        side = json.loads(side_path.read_text())
        numbered = {r for r, v in side.items() if re.sub(r'\D', '', v.get('entry_no') or '')}
    if args.year:
        by_row, snapped, split_rows = reassign(all_rows, props, text_of, split_missed=True, numbered=numbered)
        queue = [q for q in queue if q['row_id'] not in set(reassign.folded)]
        queue = sorted(queue + [r for r in split_rows if r['register_year'] == args.year],
                       key=lambda q: (q['scan'], q['page'], q['focal_y'][0]))
    else:
        by_row, snapped = reassign(all_rows, props, text_of)
    entries = []
    for q in queue:
        lines = by_row.get(q['row_id'], [])
        rec = {'row_id': q['row_id'], 'register_year': q.get('register_year', 1888),
               'register_year_status': q.get('register_year_status', 'hand_checked_layout'),
               'scan': q['scan'], 'page': q['page'], 'split': lines[0]['split'] if lines else None,
               'expected_entry_no': q.get('expected_entry_no'), 'hand_group': q.get('hand_group'),
               'image': q['image'], 'lines': len(lines), 'lines_checked': 0, 'lines_independent': 0,
               'lines_model': 0, 'lines_rejected': 0, 'boundary_snapped': snapped.get(q['row_id']),
               'split_from': q.get('split_from'), 'focal_y': q.get('focal_y')}
        for cell in CELLS:
            parts = []
            for p in lines:
                if p['cell'] != cell:
                    continue
                a = ann.get(p['id'])
                if a and a['status'] == 'rejected_crop':
                    rec['lines_rejected'] += 1
                    continue
                if a and a['status'] in ('image_checked', 'independently_checked') and a.get('text'):
                    parts.append(a['text'])
                    rec['lines_checked'] += 1
                    rec['lines_independent'] += bool(a.get('independent_verification'))
                else:
                    parts.append(preds.get(p['id'], ''))
                    rec['lines_model'] += 1
            rec[cell] = join_lines(parts)
        later = [p for p in lines if p['cell'] == 'baptism'][2:]
        rec['boundary_warning'] = ('another entry start appears inside this entry: possibly an entry the layout missed'
                                   if any(is_entry_start(text_of.get(p['id'])) for p in later) else None)
        entries.append(rec)
    stem = Path(model['model_path']).parent.name
    if args.year:
        stem = f'{args.year}_{stem}'
    out_json = BOOK / f'processed/year_draft_{stem}.json'
    out_json.write_text(json.dumps({'model': model, 'note': __doc__.split('\n\n')[-1].strip(),
                                    'entries': entries}, ensure_ascii=False, indent=1))
    with open(BOOK / f'processed/year_draft_{stem}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=[k for k in entries[0] if k != 'image'] + ['image'])
        w.writeheader()
        w.writerows(entries)
    tot = {k: sum(e[k] for e in entries) for k in ('lines', 'lines_checked', 'lines_independent', 'lines_model', 'lines_rejected')}
    print(json.dumps({'entries': len(entries), **tot, 'boundaries_snapped': len(snapped),
                      'rows_folded_into_previous': len(getattr(reassign, 'folded', [])),
                      'out': str(out_json.relative_to(ROOT))}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
