"""Layout for registers whose form runs across the whole spread (one entry = both pages).

In the 1850s Plungė book (1827/1/20) the left page holds the margin surname, No., sex tallies,
days and the baptism text; the right page holds the parents, the godparents and the witnesses'
signatures. layout.py still finds each page's ruled table; this step joins the two pages:

  * row boundaries are the union of the rules found on either page (the right page's are
    shifted by the vertical offset between the pages), so a rule missed on one page is kept;
  * every row gets explicit cell boxes: baptism on the left page, parents and godparents on the
    right page at the right page's own height;
  * all rows are filed under page "L" (the entry's row id is NNNN_L<i>); page "R" keeps its
    column rules but has no rows of its own.

usage: layout_spread.py <book dir>
The per-page result of layout.py is kept in <book>/layout_pages/ (copied on first run); the
joined layout replaces <book>/layout/NNNN.json. Re-running starts again from layout_pages/.
"""
import json
import shutil
import statistics
import sys
from pathlib import Path

MIN_ROW_H = 260
# right-page table, from its left rule: parents | godparents | signatures (px at these scan sizes)
R_TEMPLATE = [0, 865, 1731, 2211]
TOL = 45


def baptism_span(cols):
    """The widest column of the left page is the baptism text."""
    spans = [(b - a, a, b) for a, b in zip(cols, cols[1:])]
    w, a, b = max(spans, default=(0, 0, 0))
    return (a, b) if w > 900 else None


def fit_right(cols):
    """Place the right page's column template on the rules that were found (some are missed
    near the gutter); returns the four x positions or None."""
    best = None
    for c in cols:
        for t in R_TEMPLATE:
            off = c - t
            hits = sum(1 for u in R_TEMPLATE if any(abs(off + u - x) <= TOL for x in cols))
            if best is None or hits > best[0]:
                best = (hits, off)
    if not best or best[0] < 2:
        return None
    off = best[1]
    out = []
    for u in R_TEMPLATE:                       # use the found rule where there is one
        near = [x for x in cols if abs(off + u - x) <= TOL]
        out.append(int(statistics.median(near)) if near else int(off + u))
    return out


def cuts_of(pg):
    rows = pg.get('rows') or []
    return [r['y0'] for r in rows] + ([rows[-1]['y1']] if rows else [])


def join(lay, delta_default):
    pages = {p['page']: p for p in lay['pages']}
    L, R = pages.get('L', {}), pages.get('R', {})
    out_L = {k: v for k, v in L.items() if k != 'rows'}
    out_R = {k: v for k, v in R.items() if k != 'rows'}
    out_L['rows'], out_R['rows'] = [], []
    out_L['form'] = out_R['form'] = 'spread'
    out_R['merged_into'] = 'L'
    bap = baptism_span(sorted(L.get('cols') or [])) if L.get('ok') else None
    right = fit_right(sorted(R.get('cols') or [])) if R.get('ok') else None
    if not bap or not right:
        out_L['spread_note'] = 'no joined rows: ' + ('left table not found' if not bap else 'right table not found')
        return {**lay, 'pages': [out_L, out_R]}, None
    delta = (R['header_end'] - L['header_end']) if (L.get('header_end') and R.get('header_end')) else delta_default
    if abs(delta) > 150:
        delta = delta_default
    marks = sorted([(y, 'L') for y in cuts_of(L)] + [(y - delta, 'R') for y in cuts_of(R)])
    groups = []
    for y, s in marks:
        if groups and y - groups[-1][-1][0] <= 45:
            groups[-1].append((y, s))
        else:
            groups.append([(y, s)])
    cuts = []
    for g in groups:
        y = statistics.mean(v for v, _ in g)
        if not cuts or y > cuts[-1][0] + MIN_ROW_H:
            cuts.append((y, {s for _, s in g}))
    rows = []
    for (a, sa), (b, _) in zip(cuts, cuts[1:]):
        y0, y1 = int(a), int(b)
        rows.append({'y0': y0, 'y1': y1, 'seen_on': sorted(sa),
                     'cells': {'baptism': [bap[0], y0, bap[1], y1],
                               'parents': [right[0], y0 + delta, right[1], y1 + delta],
                               'godparents': [right[1], y0 + delta, right[2], y1 + delta]}})
    med = statistics.median(r['y1'] - r['y0'] for r in rows) if rows else 0
    for r in rows:
        r['suspect'] = bool(med and (r['y1'] - r['y0']) > 1.6 * med)
    out_L['rows'] = rows
    out_L['spread'] = {'delta_y': int(delta), 'baptism_x': list(bap), 'right_cols': right}
    return {**lay, 'pages': [out_L, out_R]}, delta


def main():
    book = Path(sys.argv[1])
    raw = book / 'layout_pages'
    if not raw.exists():
        shutil.copytree(book / 'layout', raw)
    lays = {f.name: json.loads(f.read_text()) for f in sorted(raw.glob('*.json'))}
    deltas = []
    for lay in lays.values():
        p = {x['page']: x for x in lay['pages']}
        if p.get('L', {}).get('header_end') and p.get('R', {}).get('header_end'):
            d = p['R']['header_end'] - p['L']['header_end']
            if abs(d) <= 150:
                deltas.append(d)
    default = int(statistics.median(deltas)) if deltas else 0
    n_rows = n_fail = 0
    for name, lay in lays.items():
        joined, _ = join(lay, default)
        (book / 'layout' / name).write_text(json.dumps(joined, indent=1))
        rows = joined['pages'][0]['rows']
        n_rows += len(rows)
        n_fail += not rows
    (book / 'form.json').write_text(json.dumps({'form': 'spread', 'note': 'one entry spans both pages; see pipeline/layout_spread.py'}))
    print(json.dumps({'spreads': len(lays), 'rows': n_rows, 'spreads_without_rows': n_fail, 'median_delta_y': default}))


if __name__ == '__main__':
    main()
