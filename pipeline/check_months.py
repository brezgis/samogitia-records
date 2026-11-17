"""Check the months of a book's parsed entries against the order the register was kept in.

Usage: SAMOGITIA_BOOK=data/<book> .venv/bin/python -I pipeline/check_months.py MODEL [--out FILE]

Baptisms are entered in date order, so through a book the baptism month never goes back except
at the turn of the year. The recognizer confuses "Іюня" and "Іюля" (and the parser finds "Мая"
where there is none), so parsed months sometimes jump. This script reads every
processed/entries_<year>_<MODEL>.json of the book in page order and fits, per entry, the month
that makes the sequence (register year, month) non-decreasing at the least cost:

  * a parsed baptism month that the fit does not keep costs 1;
  * a month heading written by the clerk above the entry (`heading_month`, from
    assemble_drafts.py) that the fit does not keep costs HEADING_WEIGHT: headings are strong
    evidence, an entry under "Іюль." is a July entry whatever its own month was read as;
  * an entry without a parsed month costs nothing and simply takes the month of its neighbours;
  * the year is the entry's register year (pipeline/infer_years.py) and is not refitted; where
    the register years themselves go back, the step is allowed at a cost of BACK_COST.

Flags per entry (`flags`):
  month_differs          the parsed baptism month is not the fitted one (the fitted month is the
                         one to trust; "Іюня" for "Іюля" is the usual case)
  heading_differs        the entry stands under a month heading that the fit did not keep
  birth_after_baptism    the birth (month, day) is later than the baptism (fitted month, parsed
                         day): same month and a later day, or the month after
  birth_month_misread    the birth month is the month after the fitted baptism month (a birth
                         in June for a May baptism): it only makes sense as a misreading of one
                         of the two months (always set together with birth_after_baptism)
  birth_long_before      the birth month is three to ten months before the baptism month: rare
                         in fact, usual when a month was misparsed or when the parents column
                         belongs to another entry
A scan on which at least three entries, and at least half of those with both dates, carry
birth_after_baptism or birth_long_before is listed in `scans_where_columns_disagree`, and its
entries get `scan_columns_disagree`: in a two-page form the left and right pages are then
probably not the same opening (a leaf missing or misbound), or the rows are out of step.
Month headings on such a scan, and on entries that assemble_drafts.py gave a `pairing_warning`
(read from the year_draft files beside the entries), are not used in the fit: the heading may
stand on the right page and belong to other baptisms. `scans_doubted` in the summary lists
the scans found either way.

Writes processed/month_check_<MODEL>.json (or --out): per entry the parsed and fitted month and
the flags, and a summary. Nothing else is changed; the entries files are not rewritten. The
check works on machine-read dates: a flag says "look here", not "this is wrong".
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
HEADING_WEIGHT = 4
BACK_COST = 6


def page_order(e):
    m = re.match(r'(\d+)_([A-Z])(\d+)(.*)', e['row_id'])
    return (e['scan'], e['page'], int(m.group(3)) if m else 0, m.group(4) if m else '')


def value(e, field):
    v = (e.get('fields') or {}).get(field)
    return v.get('value') if isinstance(v, dict) else v


def fit_months(entries):
    """entries: dicts with `register_year`, `month` (1-12 or None) and `heading_month` (1-12 or
    None/0), in page order. Returns the fitted month per entry: the cheapest sequence in which
    (register_year, month) never decreases (see the module docstring for the costs)."""
    if not entries:
        return []
    INF = float('inf')

    def cost(e, m):
        c = 0
        if e.get('month') and e['month'] != m:
            c += 1
        if e.get('heading_month') and e['heading_month'] != m:
            c += HEADING_WEIGHT
        return c

    best = [[cost(entries[0], m) for m in range(1, 13)]]
    back = [[None] * 12]
    for i in range(1, len(entries)):
        y0, y1 = entries[i - 1]['register_year'] or 0, entries[i]['register_year'] or 0
        row, brow = [], []
        for m in range(1, 13):
            arg, val = None, INF
            for m0 in range(1, 13):
                v = best[i - 1][m0 - 1] + (0 if (y0, m0) <= (y1, m) else BACK_COST)
                if v < val:
                    arg, val = m0 - 1, v
            row.append(val + cost(entries[i], m))
            brow.append(arg)
        best.append(row)
        back.append(brow)
    j = min(range(12), key=lambda j: best[-1][j])
    out = [0] * len(entries)
    for i in range(len(entries) - 1, -1, -1):
        out[i] = j + 1
        if back[i][j] is not None:
            j = back[i][j]
    return out


def check(entries, doubted=()):
    """entries: parsed entries (as in entries_<year>_<model>.json) of one book; doubted: row ids
    whose columns assembly could not pair (their month headings are not used). Returns
    (rows, summary): one row per entry in page order, and the counts."""
    entries = sorted(entries, key=page_order)
    doubted = set(doubted)
    rows, summary = _check(entries, doubted, set())
    bad = {d['scan'] for d in summary['scans_where_columns_disagree']}
    if bad:                                 # fit again without the headings of the scans found
        rows, summary = _check(entries, doubted, bad)
    summary['scans_doubted'] = sorted({d['scan'] for d in summary['scans_where_columns_disagree']}
                                      | {e['scan'] for e in entries if e['row_id'] in doubted})
    return rows, summary


def _check(entries, doubted, bad_scans):
    seq = [{'register_year': e.get('register_year'), 'month': value(e, 'baptism_month'),
            'heading_month': e.get('heading_month')} for e in entries]
    fitted = fit_months([{**s, 'heading_month': None} if e['row_id'] in doubted or e['scan'] in bad_scans else s
                         for e, s in zip(entries, seq)])
    rows = []
    for e, s, fm in zip(entries, seq, fitted):
        bm, bd = value(e, 'birth_month'), value(e, 'birth_day')
        day = value(e, 'baptism_day')
        flags = []
        if s['month'] and s['month'] != fm:
            flags.append('month_differs')
        if s['heading_month'] and s['heading_month'] != fm and e['row_id'] not in doubted and e['scan'] not in bad_scans:
            flags.append('heading_differs')
        if bm:
            gap = (fm - bm) % 12            # months from birth to baptism
            if gap == 11 or (gap == 0 and bd and day and bd > day):
                flags.append('birth_after_baptism')
            if gap == 11:
                flags.append('birth_month_misread')
            if 3 <= gap <= 10:
                flags.append('birth_long_before')
        rows.append({'row_id': e['row_id'], 'scan': e['scan'], 'page': e['page'], 'register_year': e.get('register_year'),
                     'baptism_month': s['month'], 'fitted_month': fm, 'heading_month': s['heading_month'] or None,
                     'baptism_day': day, 'birth_month': bm, 'birth_day': bd,
                     'pairing_doubted_in_assembly': e['row_id'] in doubted, 'flags': flags})
    by_scan = defaultdict(list)
    for r in rows:
        by_scan[r['scan']].append(r)
    disagree = []
    for scan, rs in sorted(by_scan.items()):
        dated = [r for r in rs if r['birth_month']]
        off = [r for r in dated if 'birth_after_baptism' in r['flags'] or 'birth_long_before' in r['flags']]
        if len(off) >= 3 and 2 * len(off) >= len(dated):
            disagree.append({'scan': scan, 'entries': len(rs), 'with_birth_month': len(dated), 'disagreeing': len(off)})
            for r in rs:
                r['flags'].append('scan_columns_disagree')
    count = Counter(f for r in rows for f in r['flags'])
    summary = {'entries': len(rows), 'with_baptism_month': sum(1 for r in rows if r['baptism_month']),
               'with_heading_month': sum(1 for r in rows if r['heading_month']),
               'with_birth_month': sum(1 for r in rows if r['birth_month']),
               'flags': dict(sorted(count.items())), 'entries_flagged': sum(1 for r in rows if r['flags']),
               'month_differs_by_scan': dict(sorted(Counter(r['scan'] for r in rows if 'month_differs' in r['flags']).items())),
               'month_differs_read_as': dict(Counter('%d read, %d fitted' % (r['baptism_month'], r['fitted_month'])
                                                     for r in rows if 'month_differs' in r['flags']).most_common()),
               'scans_where_columns_disagree': disagree}
    return rows, summary


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('model', help='model name as in processed/entries_<year>_<model>.json')
    ap.add_argument('--out', type=Path, help='output file (default: processed/month_check_<model>.json of the book)')
    args = ap.parse_args()
    files = sorted(BOOK.glob(f'processed/entries_[0-9][0-9][0-9][0-9]_{args.model}.json'))
    if not files:
        sys.exit(f'no processed/entries_<year>_{args.model}.json in {BOOK}')
    entries = [e for f in files for e in json.loads(f.read_text())['entries']]
    doubted = set()
    for f in files:                         # the drafts the entries were parsed from
        draft = f.with_name(f.name.replace('entries_', 'year_draft_', 1))
        if draft.exists():
            doubted |= {d['row_id'] for d in json.loads(draft.read_text())['entries'] if d.get('pairing_warning')}
    rows, summary = check(entries, doubted)
    out = args.out or BOOK / f'processed/month_check_{args.model}.json'
    out.write_text(json.dumps({'book': BOOK.name, 'model': args.model, 'files': [f.name for f in files],
                               'note': __doc__.split('\n\n')[-1].strip(), 'summary': summary, 'entries': rows},
                              ensure_ascii=False, indent=1))
    print(json.dumps({**summary, 'out': str(out)}, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
