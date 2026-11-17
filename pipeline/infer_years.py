"""Infer each entry's register year from drafted text, for queue_years.json.

Usage: .venv/bin/python -I pipeline/infer_years.py PREDICTIONS_DIR

Evidence per row (from the model's line drafts):
  1. baptism column: the year written in words, "...восемьдесятъ <шестаго|седьмаго|восьмаго|
     девятаго> года" or "...девяностаго года" -> 1886/1887/1888/1889/1890 (strongest);
  2. parents column: the birth year in digits "18NN года" (a birth can precede the baptism
     year, so it only supports the same year or the following one).
Row votes are pooled per page side (an entry's own cue wins where clear), then the sequence
over scans is checked to be non-decreasing; rows that break it are flagged, not changed.

A book often opens with the last entries of the year before (a register begun in November).
Those few rows are too small a share of the book to count as a year of their own by the 2% rule,
so the year just before the first well-supported one is also admitted when at least three rows
at the start of the book name it in words and it wins the first page side(s). Where the year
turns in the middle of a page side, the rows above the turn that name the old year (or, the
decade misread, at least its last digit) keep it, and likewise the rows below the turn on the
old year's last side that name the new one.
Writes register_year, register_year_status and register_year_evidence into
processed/queue_years.json (in place; the previous file is kept as queue_years.json.bak).
"""
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
UNITS = {'сем': 7, 'перв': 1, 'втор': 2, 'трет': 3, 'четверт': 4, 'пят': 5, 'шест': 6, 'седьм': 7, 'восьм': 8, 'осьм': 8, 'девят': 9}


def flat(s):
    return re.sub(r'\s+', '', (s or '').lower()).replace('ѣ', 'е').replace('ъ', '')


def word_year(text):
    """Register year written in words: "...восемьдесятъ седьмаго года", "...девяностаго года",
    "...девяносто перваго года", "тысяча девятисотаго года", "...девятьсотъ третьяго года",
    "...шестьдесятаго года" (a round year), "...пятьдесятъ семаго года" (семаго for седьмаго)."""
    s = re.sub(r'[-=]', '', flat(text))        # a year word divided at the line end: "ше-" / "стаго"
    units = '|'.join(u for u in UNITS if u != 'сем') + '|(?<!во)сем'     # "семаго" for седьмаго (not the "сем" of "восемь")
    m = re.search(r'девятьсот(' + units + r')', s)
    if m:
        return 1900 + UNITS[m.group(1)]
    if re.search(r'девятисотаг', s):
        return 1900
    m = re.search(r'девяност[оа]?(' + units + r')', s)
    if m:
        return 1890 + UNITS[m.group(1)]
    if re.search(r'девяностаг|девяностог', s):
        return 1890
    m = re.search(r'семьдес[яа]т\w{0,3}?(' + units + r')', s)
    if m and not re.search(r'восемьдес', s):
        return 1870 + UNITS[m.group(1)]
    m = re.search(r'шест[ьъ]?дес[яа]т\w{0,3}?(' + units + r')', s)
    if m:
        return 1860 + UNITS[m.group(1)]
    m = re.search(r'пят[ьъ]?дес[яа]т\w{0,3}?(' + units + r')', s)
    if m:
        return 1850 + UNITS[m.group(1)]
    # the round years of a decade: "пятидесятаго", "шестьдесятаго / шестидесятаго", ...
    for stem, year in ((r'пят[ьи]?', 1850), (r'шест[ьи]?', 1860), (r'(?<!во)сем[ьи]?', 1870), (r'вос[еь]м[ьи]?', 1880)):
        if re.search(stem + r'дес[яа]таг', s):
            return year
    m = re.search(r'восемьдес[яа]т\w{0,3}?(' + units + r')', s) or \
        re.search(r'дес[яа]т\w{0,2}(' + units + r')\w{0,3}года', s)
    return 1880 + UNITS[m.group(1)] if m else None


def digit_year(text):
    m = re.search(r'1[89]\s*([0-9])\s*(\d)', text or '')
    if not m:
        return None
    y = int(m.group(0).replace(' ', '')[:4]) if m else None
    return y if 1840 <= y <= 1915 else None


def infer(queue, preds, side=None):
    """Fill register_year, register_year_status and register_year_evidence on the queue rows (in
    place) from the line predictions ({id: {row_id, cell, text}}) and, if the book has them, the
    side-column readings. Returns the number of rows that break the year order."""
    by_row = defaultdict(lambda: {'baptism': [], 'parents': []})
    for p in preds.values():
        if p['cell'] in ('baptism', 'parents'):
            by_row[p['row_id']][p['cell']].append(p['text'])
    side_votes = defaultdict(Counter)
    for q in queue:
        t = by_row.get(q['row_id'], {'baptism': [], 'parents': []})
        w = word_year(' '.join(t['baptism']))
        d = digit_year(' '.join(t['parents']))
        q['register_year_evidence'] = {'baptism_words': w, 'birth_digits': d}
        if w:
            side_votes[(q['scan'], q['page'])][w] += 2
        elif d:
            side_votes[(q['scan'], q['page'])][d] += 1
    for q in queue:
        if q.get('register_year_status') == 'hand_checked_layout':
            continue
        ev = q['register_year_evidence']
        votes = side_votes[(q['scan'], q['page'])]
        side_year = votes.most_common(1)[0][0] if votes else None
        if ev['baptism_words']:
            q['register_year'], q['register_year_status'] = ev['baptism_words'], 'inferred_from_baptism_words'
        elif ev['birth_digits'] and side_year in (ev['birth_digits'], ev['birth_digits'] + 1):
            q['register_year'], q['register_year_status'] = side_year, 'inferred_from_birth_digits_and_page'
        elif side_year:
            q['register_year'], q['register_year_status'] = side_year, 'inferred_from_page_majority'
        else:
            q['register_year'], q['register_year_status'] = None, 'no_evidence'
    # Monotone smoothing: register years never decrease through a book. Fit the best
    # non-decreasing year per page side (isotonic DP over sides, candidate years = those with
    # real support), so isolated misreadings ("1877" for "1897") cannot flip a page.
    sides = sorted(side_votes, key=lambda k: (k[0], k[1]))
    total = Counter()
    for v in side_votes.values():
        total.update(v)
    support = sum(total.values()) or 1
    cand = sorted(y for y, c in total.items() if c / support >= 0.02)

    def fit(cand):
        INF = float('inf')
        cost = [[sum(c for y2, c in side_votes[s].items() if y2 != y) for y in cand] for s in sides]
        best = [cost[0][:]]
        back = [[None] * len(cand)]
        for i in range(1, len(sides)):
            row, brow, run, arg = [], [], INF, 0
            for j in range(len(cand)):
                if best[i - 1][j] < run:
                    run, arg = best[i - 1][j], j
                row.append(cost[i][j] + run)
                brow.append(arg)
            best.append(row)
            back.append(brow)
        j = min(range(len(cand)), key=lambda j: best[-1][j])
        fitted = {}
        for i in range(len(sides) - 1, -1, -1):
            fitted[sides[i]] = cand[j]
            if back[i][j] is not None:
                j = back[i][j]
        return fitted

    if cand and sides:
        fitted = fit(cand)
        # the tail of the year before, at the start of the book: admitted if the fit gives it the
        # first side(s) and at least three rows there name it in words
        before = cand[0] - 1
        if total.get(before):
            trial = fit([before] + cand)
            lead = {s for s, y in trial.items() if y == before}
            if sum(1 for q in queue if (q['scan'], q['page']) in lead
                   and q['register_year_evidence']['baptism_words'] == before) >= 3:
                fitted = trial
        for q in queue:
            if q.get('register_year_status') == 'hand_checked_layout':
                continue
            y = fitted.get((q['scan'], q['page']))
            if y is not None and y != q['register_year']:
                q['register_year_evidence']['before_monotone'] = q['register_year']
                q['register_year'], q['register_year_status'] = y, 'inferred_monotone_page_fit'
            elif y is not None and q['register_year_status'] == 'no_evidence':
                q['register_year'], q['register_year_status'] = y, 'inferred_monotone_page_fit'
        # the year turns inside a page side: rows keep the year they name themselves
        rows_of = defaultdict(list)
        for q in sorted(queue, key=lambda q: q['focal_y'][0]):
            rows_of[(q['scan'], q['page'])].append(q)

        def names(q, y, other):
            w = q['register_year_evidence']['baptism_words']
            return w == y or bool(w and w != other and w % 10 == y % 10)     # (the decade misread: "1886" for 1856)

        def turn(q, y):
            if q.get('register_year_status') != 'hand_checked_layout' and q['register_year'] != y:
                q['register_year_evidence']['before_year_turn'] = q['register_year']
                q['register_year'], q['register_year_status'] = y, 'inferred_year_turn_in_page'

        for a, b in zip(sides, sides[1:]):
            y1, y2 = fitted[a], fitted[b]
            if y2 != y1 + 1:
                continue
            rows = rows_of[b]                   # first side of the new year: its top rows may still be the old year
            old = [i for i, q in enumerate(rows) if names(q, y1, y2)]
            new = [i for i, q in enumerate(rows) if q['register_year_evidence']['baptism_words'] == y2]
            if old and (not new or max(old) < min(new)):
                for q in rows[:max(old) + 1]:
                    turn(q, y1)
            rows = rows_of[a]                   # last side of the old year: its bottom rows may be the new year
            old = [i for i, q in enumerate(rows) if q['register_year_evidence']['baptism_words'] == y1]
            new = [i for i, q in enumerate(rows) if names(q, y2, y1)]
            if new and (not old or max(old) < min(new)):
                for q in rows[min(new):]:
                    turn(q, y2)
    # Entry numbers restart at 1 every January. With side-column readings available, split the
    # book's row sequence at number resets and give each stretch the majority year of its own
    # textual evidence (hand-checked rows count most and keep their year).
    if side:
        order = sorted(queue, key=lambda q: (q['scan'], q['page'], q['focal_y'][0]))
        segs, cur, last_n = [], [], None
        for q in order:
            m = re.sub(r'\D', '', (side.get(q['row_id']) or {}).get('entry_no') or '')
            n = int(m) if m else None
            if n is not None and last_n is not None and n <= 25 and last_n >= 150 and cur:
                segs.append(cur)
                cur = []
            cur.append(q)
            if n is not None:
                last_n = n
        if cur:
            segs.append(cur)
        for seg in segs:
            votes = Counter()
            for q in seg:
                ev = q['register_year_evidence']
                if q.get('register_year_status') == 'hand_checked_layout':
                    votes[q['register_year']] += 5
                elif ev.get('baptism_words'):
                    votes[ev['baptism_words']] += 2
                elif ev.get('birth_digits'):
                    votes[ev['birth_digits']] += 1
            if not votes:
                continue
            year = votes.most_common(1)[0][0]
            for q in seg:
                if q.get('register_year_status') == 'hand_checked_layout':
                    continue
                if q['register_year'] != year:
                    q['register_year_evidence']['previous_inference'] = q['register_year']
                q['register_year'], q['register_year_status'] = year, 'inferred_from_number_sequence'
    # order check: register years should not decrease through the book
    last, flagged = None, 0
    for q in sorted(queue, key=lambda q: (q['scan'], q['page'], q['row_index'])):
        y = q['register_year']
        if y is None:
            continue
        if last and y < last:
            q['register_year_status'] += '; ORDER_CONFLICT'
            flagged += 1
        else:
            last = y
    return flagged


def main():
    pred_dir = Path(sys.argv[1])
    preds = {p['id']: p for p in json.loads((pred_dir / 'predictions.json').read_text())}
    qpath = BOOK / 'processed/queue_years.json'
    queue = json.loads(qpath.read_text())
    shutil.copy(qpath, qpath.with_suffix('.json.bak'))
    side_path = BOOK / 'processed/side_columns.json'
    flagged = infer(queue, preds, json.loads(side_path.read_text()) if side_path.exists() else None)
    qpath.write_text(json.dumps(queue, ensure_ascii=False, indent=1))
    years = Counter(q['register_year'] for q in queue)
    first = {}
    for q in sorted(queue, key=lambda q: (q['scan'], q['page'], q['row_index'])):
        first.setdefault(q['register_year'], q['row_id'])
    print(json.dumps({'rows': len(queue), 'by_year': {str(k): v for k, v in sorted(years.items(), key=lambda x: str(x[0]))},
                      'first_row_of_year': {str(k): v for k, v in first.items()}, 'order_conflicts': flagged,
                      'status': dict(Counter(q['register_year_status'] for q in queue))}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
