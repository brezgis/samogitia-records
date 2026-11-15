"""Assemble per-entry draft texts for the 1888 year from line predictions + checked labels.

Usage: .venv/bin/python -I pipeline/assemble_drafts.py PREDICTIONS_DIR

For every in-year queue row, each column (baptism, parents, godparents) is rebuilt from
its line crops in order. A line uses its checked label (image_checked /
independently_checked) when one exists, otherwise the model prediction. Rejected crops
are skipped. Line-end '-' or '=' joins to the next line without a space.

Which entry a line belongs to is decided here (`reassign`), not by the layout row in its id:
the last lines of an entry often lie below the next layout row's top. A month heading written
between two entries ("Ноябрь.", "тоже.") is taken out of the text and kept on the entry it
stands above as `heading` (with `heading_month` when the month is read).

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_entries import lev  # noqa: E402

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
        elif re.search(r'[^\W\d_]\s*[-=]$', out):      # a letter before the dash: a divided word ("пругою. -" is not)
            out = re.sub(r'\s*[-=]$', '', out) + re.sub(r'^[-=]\s*', '', t)   # "Воспріемни -" + "ками": no space left behind
        else:
            out = out + ' ' + t
    return out

SNAP = 260   # px: how far a stored entry boundary may move to a detected entry start


def is_entry_start(text):
    """Baptism column of every entry opens with "Тысяча восемьсотъ ...", sometimes after the
    entry's number ("19 Тысяча"); the word may be misread ("Тысоча", "Тасяча", "Тысча")."""
    text = re.sub(r'^[\s\d.,\-=]+', '', text or '')
    s = re.sub(r'\s+', '', text).lower().replace('и', 'ы')
    if re.match(r'.{0,2}[ын][се][яа]ч', s) or s.startswith('тысяч'):
        return True
    word = re.sub(r'[\W\d_]', '', text.split()[0].lower()) if text.split() else ''
    return word.startswith('т') and 5 <= len(word) <= 7 and lev(word, 'тысяча') <= 1


def is_column_start(cell, text):
    """Opening words of each column: baptism "Тысяча", parents the estate, godparents "Воспріемн..."."""
    if cell == 'baptism':
        return is_entry_start(text)
    s = re.sub(r'\s+', '', text or '').lower().lstrip('-=.,')
    if cell == 'parents':
        if 'стьян' in s[:9] or s.startswith(('двор', 'мещ', 'мѣщ', 'шлях', 'однодв')):
            return True
        # the estate word misread ("Крентьянъ", "Крестинъ", "Критьинъ"), or an estate named after
        # a qualifier ("Тельшевскаго Мѣщанина", "Билетнаго Солдата")
        word = re.sub(r'[^\w]', '', (text or '').split()[0].lower()) if (text or '').split() else ''
        d = lev(word, 'крестьянъ') if 6 <= len(word) <= 11 else 9
        return d <= 2 or (d == 3 and word.startswith('кр') and word.endswith('нъ')) \
            or any(w in s[:30] for w in ('мѣщан', 'мещан', 'солдат'))
    return bool(re.search(r'сп[рp][іи]?е', s[:8])) or s.startswith(('воспр', 'оспр'))


HEADING_MONTHS = ['январь', 'февраль', 'мартъ', 'апрѣль', 'май', 'іюнь', 'іюль', 'августъ', 'сентябрь', 'октябрь',
                  'ноябрь', 'декабрь']


def heading_month(text):
    """A line that is nothing but a month heading: the month's number (nominative month name,
    as clerks write it between entries), 0 for "тоже" / "Мѣсяцъ" (a heading without a month
    name), None for anything else. Long names may be one letter off ("оябрь"); short ones and
    the genitive of dates ("Ноября") never match."""
    s = re.sub(r'[\W\d_]', '', (text or '').lower()).replace('m', 'т').replace('i', 'і').replace('и', 'і')
    if not 3 <= len(s) <= 9:
        return None
    if s in ('тоже', 'мѣсяцъ', 'мѣсяц', 'месяцъ'):
        return 0
    for n, m in enumerate(HEADING_MONTHS, 1):
        m = m.replace('и', 'і')
        if s in (m, m.rstrip('ъ')):
            return n
        if len(m) >= 6 and m.endswith('ь') and s != m[:-1] + 'я' and lev(s, m) <= 1:
            return n
    return None


def line_y(p):
    """Height of a line's letter bodies (the `line` record of segment_lines.py when the
    proposal has one, else the middle of its box): boxes of neighbouring lines overlap, and a
    sloped line's box is much taller than its writing, so box edges do not order lines."""
    line = p.get('line')
    if line and line.get('core'):
        return (line['core'][0] + line['core'][1]) / 2
    return (p['bbox'][1] + p['bbox'][3]) / 2


def reassign(queue, props, text_of, split_missed=False, numbered=None):
    """Re-derive entry membership from detected column openings (layout boundaries are approximate).

    Per page side: each stored boundary (row focal_y start) first snaps to the nearest baptism
    line reading "Тысяча..." within SNAP px. Then, per column, it snaps again to the nearest line
    opening that column (estate word for parents, "Воспріемн..." for godparents) within SNAP px of
    the baptism boundary, because columns are not always level. A line belongs to the entry whose
    boundary for its column lies above the line's vertical centre. Boundaries without a nearby
    detected opening are kept. Where a boundary is a detected opening line, membership is by
    position relative to that line itself (`line_y`): everything above it belongs to the entry
    before, however much the boxes overlap. Month headings standing directly above a detected
    opening are removed from the lines and left in `reassign.headings` ({row_id: {cell: [line]}})
    for the entry they stand above.
    Returns (lines by row_id, {row_id: {cell: (old_y, new_y)}}).
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
    split_rows, folded, headings = [], [], {}

    def snap(y0, starts):
        near = [s for s in starts if abs(s - y0) <= SNAP]
        return (min(near, key=lambda s: abs(s - y0)) - 8) if near else y0

    for key, qs in side.items():
        qs = sorted(qs, key=lambda q: q['focal_y'][0])
        lines = line_side[key]
        opening = {c: [p for p in lines if p['cell'] == c and is_column_start(c, text_of.get(p['id']))]
                   for c in ('baptism', 'parents', 'godparents')}
        starts = {c: sorted(p['bbox'][1] for p in ps) for c, ps in opening.items()}
        # a boundary taken from an opening line (its box top - 8) -> that line's own height
        at = {(c, p['bbox'][1] - 8): line_y(p) for c, ps in opening.items() for p in ps}
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
                # a boundary that is an opening line: compare with that line; otherwise with the layout's y
                if (line_y(p) >= at[p['cell'], y] - 1) if (p['cell'], y) in at else (cy >= y):
                    owner = rid
            by_row[owner].append(p)
        # month headings: up to two heading lines directly above an entry's opening line (blank
        # crops between them ignored) come out of the text, wherever the boundary put them
        owner_of = {p['id']: rid for rid in {r for bs in bounds.values() for _, r in bs} for p in by_row.get(rid, [])}
        for c, ps in opening.items():
            col = sorted((p for p in lines if p['cell'] == c), key=line_y)
            for o in ps:
                if o['id'] not in owner_of:
                    continue
                k, found = col.index(o) - 1, []
                while k >= 0 and len(found) < 2 and line_y(o) - line_y(col[k]) <= SNAP:
                    t = text_of.get(col[k]['id']) or ''
                    if heading_month(t) is not None:
                        found.append(col[k])
                    elif re.sub(r'[\W_]', '', t):
                        break
                    k -= 1
                for h in found:
                    if h['id'] in owner_of:     # (a line above the side's first entry has no owner)
                        by_row[owner_of.pop(h['id'])].remove(h)
                    headings.setdefault(owner_of[o['id']], {}).setdefault(c, []).insert(0, h)
    order = {'baptism': 0, 'parents': 1, 'godparents': 2}
    for rid in by_row:
        by_row[rid].sort(key=lambda p: (order[p['cell']], p['bbox'][1]))
    reassign.folded = folded
    reassign.headings = headings
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
               'split_from': q.get('split_from'), 'focal_y': q.get('focal_y'), 'heading': None, 'heading_month': None}
        heads = [text_of[p['id']].strip() for cell in CELLS for p in reassign.headings.get(q['row_id'], {}).get(cell, [])]
        if heads:
            rec['heading'] = ' '.join(heads)
            rec['heading_month'] = next((m for m in map(heading_month, heads) if m), None)
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
