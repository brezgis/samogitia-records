"""Choose the confidence threshold of the combination and score it on held-out books.

Usage (HTR environment; the tagger runs on the CPU here, a book takes seconds):
  PY=.venv-htr/bin/python
  nice $PY pipeline/neural_parser/validate_combination.py choose      # threshold, on the choosing folds
  nice $PY pipeline/neural_parser/validate_combination.py report      # the two reported folds
Writes results/combination_choose.md and results/combination_report.md (+ .json) in the scratch folder.

Every book is tagged by the character model trained WITHOUT it (models/char__<book>__s1__lobo.pt,
trained by `train_tagger.py --heldout <book> --seed 1 --save --tag lobo`; the experiment itself kept
predictions only). The threshold and the township / priest variants are looked at on three folds
(1827/1/18, 1886-1890, 1827/1/25) and the combination is then reported on the other two, an early
book (1827/1/22) and a late one (1827/1/24), with `evaluate.py`'s own scoring functions, so the
numbers sit beside those of RESULTS.md section 4.

Systems: "rules" = today's parse_entries.py (after the two bug fixes) placed as spans by the
adapter; "rules (published)" = the cached spans the experiment scored (before the fixes); "tagger" =
the held-out character model alone; "combination" = combine.combine_entries (what
`parse_entries.py --tagger` writes).
"""
import json
import re
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import combine as cb  # noqa: E402
import evaluate as ev  # noqa: E402
from common import ALL_FIELDS, COLS, COL_OF, NAME_FIELDS, SCRATCH, YEARS, decode_date  # noqa: E402

CHOOSE = ['plunge-1827-1-18', 'plunge-1886-1890', 'plunge-1827-1-25']
REPORT = ['plunge-1827-1-22', 'plunge-1827-1-24']
BINS = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98, 1.0001]
_ROWS = {}


def rows_of(book):
    if book not in _ROWS:
        _ROWS[book] = [r for r in ev.load_silver() if r['book'] == book]
    return _ROWS[book]


def entries_of(book):
    return [{'row_id': r['row_id'], **r['text']} for r in rows_of(book)]


def tags_of(book):
    """Tagger spans with confidence from the model trained without `book`, cached."""
    cache = SCRATCH / 'preds' / f'char__{book}__s1__lobo.conf.json'
    if cache.exists():
        return json.loads(cache.read_text())
    from apply import tag_entries
    tags = tag_entries(entries_of(book), SCRATCH / 'models' / f'char__{book}__s1__lobo.pt', 'cpu')
    cache.write_text(json.dumps(tags, ensure_ascii=False))
    return tags


def _one(args):
    e, t, kw = args
    return cb.combine_entry(e, t, **kw)


def combined(book, **kw):
    entries, tags = entries_of(book), tags_of(book)
    kw = dict(kw)
    mode = kw.pop('township', 'file')
    kw['township_wording'] = {'file': cb.township_wording(entries), 'entry': None, 'never': False}[mode]
    with Pool(8) as pool:
        return pool.map(_one, [(e, t, kw) for e, t in zip(entries, tags)], chunksize=40)


def as_preds(book, per_entry):
    return {(book, r['row_id']): {(COL_OF[f], f): tuple(sp) for f, sp in spans.items()} for r, spans in zip(rows_of(book), per_entry)}


def tagger_preds(book):
    return as_preds(book, [{f: (v['s'], v['e']) for c in COLS for f, v in t[c].items()} for t in tags_of(book)])


def own_day(book, out, kind):
    """The output's own day (not a span decoded afterwards) against the side column."""
    n = made = agree = 0
    for r, o in zip(rows_of(book), out):
        d = re.sub(r'\D', '', r['side'].get(kind + '_day') or '')
        if not d or not 1 <= int(d) <= 31:
            continue
        n += 1
        v = o['fields'].get(kind + '_day', {}).get('value')
        made += bool(v)
        agree += v == int(d)
    return n, made, agree


def table(book, systems, md, js):
    rows = rows_of(book)
    names = list(systems)
    for gname, gold_of, fields in (("agents' names spans only", ev.gold_agents, NAME_FIELDS), ('silver (all spans)', ev.gold_silver, ALL_FIELDS)):
        md.append(f'\nGold = {gname}. F1 exact / F1 within 2 characters.\n')
        md.append('| field | gold spans | ' + ' | '.join(names) + ' |')
        md.append('|---|---:|' + '---|' * len(names))
        res = {s: {tol: ev.score(rows, p, gold_of, tol) for tol in (0, 2)} for s, p in systems.items()}
        for f in fields:
            cells = [f'{100 * ev.prf(*res[s][0][f][:3])[2]:.0f} / {100 * ev.prf(*res[s][2][f][:3])[2]:.0f}' for s in names]
            md.append(f'| {f} | {res[names[0]][0][f][2]} | ' + ' | '.join(cells) + ' |')
            js.setdefault(gname, {})[f] = {s: round(100 * ev.prf(*res[s][2][f][:3])[2], 1) for s in names}
        cells = []
        for s in names:
            p, r, f1 = ev.micro(res[s][2], [f for f in fields if f in NAME_FIELDS])
            cells.append(f'{100 * f1:.1f} (P {100 * p:.0f}, R {100 * r:.0f})')
            js.setdefault(gname, {}).setdefault('micro name fields', {})[s] = round(100 * f1, 1)
        md.append('| **name fields, micro F1 ±2** | | ' + ' | '.join(cells) + ' |')
    md.append('\nSide-column checks: agreeing / spans produced / entries with a side-column value. Days are decoded from the system\'s date span by one decoder, as in section 4.\n')
    md.append('| check | ' + ' | '.join(names) + ' |')
    md.append('|---|' + '---|' * len(names))
    for label, fn in (('family surname = margin surname', lambda p: ev.margin_check(rows, p)),
                      ('baptism day = side column', lambda p: ev.day_check(rows, p, 'BAPT_DATE', 'baptism_day')),
                      ('birth day = side column', lambda p: ev.day_check(rows, p, 'BIRTH_DATE', 'birth_day'))):
        cells = []
        for s in names:
            n, made, agree = fn(systems[s])
            cells.append(f'{agree} / {made} / {n} ({100 * agree / max(n, 1):.0f}%)')
            js.setdefault(label, {})[s] = [agree, made, n]
        md.append(f'| {label} | ' + ' | '.join(cells) + ' |')


def disagreements(book, out):
    """Per tagger field, the tagger's spans the rules do not corroborate, with the agents' span as gold:
    (field, confidence, tagger right, rules right, rules gave a value)."""
    got = []
    tags = tags_of(book)
    for r, o, t in zip(rows_of(book), out, tags):
        gold = ev.gold_agents(r)
        for f in cb.TAGGER_FIELDS:
            ts = t[COL_OF[f]].get(f)
            g = gold.get(f)
            fld = o['fields'][cb.KEY[f]]
            if not ts or not g or fld['by'] == 'both':
                continue
            rsp = o['rule_spans'].get(f)
            got.append((f, ts['conf'], ev.ok((ts['s'], ts['e']), g, 2), ev.ok(tuple(rsp) if rsp else None, g, 2), bool(rsp)))
    return got


def choose():
    md, js = ['# Choosing the threshold (folds 1827/1/18, 1886-1890, 1827/1/25; tagger trained without the book)\n'], {}
    cases, dates = [], []
    outs = {}
    for book in CHOOSE:
        outs[book] = combined(book, threshold=0.0, priest='rules', agreed='rules')
        cases += disagreements(book, outs[book])
        # dates the rules could not decode: is the day decoded from the tagger's phrase the side column's?
        for r, o, t in zip(rows_of(book), outs[book], tags_of(book)):
            for kind, F in (('baptism', 'BAPT_DATE'), ('birth', 'BIRTH_DATE')):
                d = re.sub(r'\D', '', r['side'].get(kind + '_day') or '')
                fld = o['fields'][kind + '_day']
                if d and 1 <= int(d) <= 31 and fld['by'] == 'tagger':
                    dates.append((kind, fld['conf'], fld['value'] == int(d)))
    md.append('Tagger spans not corroborated by the rules, where the agents listed the name (gold = agents\' span, ±2), by confidence.\n')
    md.append('| confidence | rules gave another value: n | tagger right | rules right | rules gave nothing: n | tagger right |')
    md.append('|---|---:|---:|---:|---:|---:|')
    for lo, hi in zip(BINS, BINS[1:]):
        a = [c for c in cases if lo <= c[1] < hi and c[4]]
        b = [c for c in cases if lo <= c[1] < hi and not c[4]]
        pct = lambda xs, k: f'{100 * sum(x[k] for x in xs) / len(xs):.0f}%' if xs else '-'
        md.append(f'| {lo:.2f}-{min(hi, 1):.2f} | {len(a)} | {pct(a, 2)} | {pct(a, 3)} | {len(b)} | {pct(b, 2)} |')
        js[f'{lo:.2f}'] = [len(a), sum(x[2] for x in a), sum(x[3] for x in a), len(b), sum(x[2] for x in b)]
    md.append('\nThe same per field, below and above 0.8 (differ: tagger right / rules right / n; rules empty: tagger right / n).\n')
    md.append('| field | <0.8 differ | <0.8 rules empty | >=0.8 differ | >=0.8 rules empty |')
    md.append('|---|---|---|---|---|')
    for f in cb.TAGGER_FIELDS:
        cells = []
        for sel in (lambda c: c[1] < 0.8, lambda c: c[1] >= 0.8):
            a = [c for c in cases if c[0] == f and sel(c) and c[4]]
            b = [c for c in cases if c[0] == f and sel(c) and not c[4]]
            cells += [f'{sum(x[2] for x in a)} / {sum(x[3] for x in a)} / {len(a)}', f'{sum(x[2] for x in b)} / {len(b)}']
        md.append(f'| {f} | ' + ' | '.join(cells) + ' |')
    md.append('\nDates the rules did not decode, taken from the tagger\'s phrase: day equal to the side column, by confidence.\n')
    md.append('| confidence | baptism: n | right | birth: n | right |')
    md.append('|---|---:|---:|---:|---:|')
    for lo, hi in zip(BINS, BINS[1:]):
        cells = []
        for kind in ('baptism', 'birth'):
            xs = [x for x in dates if x[0] == kind and lo <= x[1] < hi]
            cells += [str(len(xs)), f'{100 * sum(x[2] for x in xs) / len(xs):.0f}%' if xs else '-']
        md.append(f'| {lo:.2f}-{min(hi, 1):.2f} | ' + ' | '.join(cells) + ' |')
    # the combination at several thresholds, and the township and priest variants
    md.append('\nName fields, micro F1 ±2 against the agents\' spans, on the choosing folds.\n')
    md.append('| setting | ' + ' | '.join(ev.SHORT[b] for b in CHOOSE) + ' | tagger spans withheld |')
    md.append('|---|' + '---:|' * (len(CHOOSE) + 1))
    settings = [('rules', None), ('tagger', None)] + [(f'combination, one threshold {t}', {'threshold': t}) for t in (0.0, 0.5, 0.7, 0.8, 0.9, 0.95)]
    settings += [('default (0.8; family surname 0.5)', {}),
                 ('default, agreed spans taken from the rules', {'agreed': 'rules'}),
                 ('default, township by entry', {'township': 'entry'}),
                 ('default, township never from the tagger', {'township': 'never'}),
                 ('default, priest from the rules only', {'priest': 'rules'})]
    for label, kw in settings:
        cells, withheld = [], 0
        for book in CHOOSE:
            if kw is None:
                preds = tagger_preds(book) if label == 'tagger' else as_preds(book, [o['rule_spans'] for o in outs[book]])
            else:
                out = combined(book, **kw)
                preds = as_preds(book, [o['spans'] for o in out])
                withheld += sum(1 for o in out for f in cb.TAGGER_FIELDS
                                if o['fields'][cb.KEY[f]]['by'] in ('rules', 'none') and 'alt' in o['fields'][cb.KEY[f]])
            c = ev.score(rows_of(book), preds, ev.gold_agents, 2)
            c0 = ev.score(rows_of(book), preds, ev.gold_agents, 0)
            per = {f: round(100 * ev.prf(*c[f][:3])[2], 1) for f in NAME_FIELDS}
            per['micro exact'] = round(100 * ev.micro(c0, NAME_FIELDS)[2], 1)
            cells.append(f'{100 * ev.micro(c, NAME_FIELDS)[2]:.1f}')
            js.setdefault('settings', {}).setdefault(label, {})[book] = per
        md.append(f'| {label} | ' + ' | '.join(cells) + f' | {withheld if kw is not None else ""} |')
    (ev.RES / 'combination_choose.md').write_text('\n'.join(md) + '\n')
    (ev.RES / 'combination_choose.json').write_text(json.dumps(js, ensure_ascii=False, indent=1))
    print('\n'.join(md))


def report():
    thr = float(sys.argv[sys.argv.index('--threshold') + 1]) if '--threshold' in sys.argv else cb.THRESHOLD
    md, js = [f'# The combination on the two reported folds (threshold {thr}; tagger trained without the book)\n'], {}
    for book in REPORT:
        rows = rows_of(book)
        out = combined(book, threshold=thr)
        alt = combined(book, threshold=thr, priest='rules')
        systems = {'rules (published)': ev.load_preds(f'rules__{book}'),
                   'rules': as_preds(book, [o['rule_spans'] for o in out]),
                   'tagger': tagger_preds(book),
                   'tagger (published, seed 1)': ev.load_preds(f'char__{book}__s1'),
                   'combination': as_preds(book, [o['spans'] for o in out]),
                   'combination, priest from the rules only': as_preds(book, [o['spans'] for o in alt])}
        md.append(f'\n## Held out: {ev.SHORT[book]} ({YEARS[book]}), {len(rows)} entries\n')
        js[book] = {}
        table(book, systems, md, js[book])
        md.append('\nThe output\'s own day (the value `parse_entries.py` writes, not a span decoded afterwards): agreeing / filled / entries with a side-column value.\n')
        md.append('| check | rules (parse()) | combination |')
        md.append('|---|---|---|')
        rules_only = [{'fields': {k: {'value': v} for k, v in cb.pe.parse(e).items()}} for e in entries_of(book)]
        for kind in ('baptism', 'birth'):
            cells = []
            for o in (rules_only, out):
                n, made, agree = own_day(book, o, kind)
                cells.append(f'{agree} / {made} / {n} ({100 * agree / max(n, 1):.0f}%)')
            md.append(f'| {kind} day = side column | ' + ' | '.join(cells) + ' |')
            js[book][f'own {kind} day'] = cells
        by = defaultdict(Counter)
        for o in out:
            for k, v in o['fields'].items():
                by[k][v['by']] += 1
        md.append('\nWhere the combined value came from (entries).\n')
        md.append('| field | both | tagger | rules | none |')
        md.append('|---|---:|---:|---:|---:|')
        for k in ['child_name', 'father', 'mother', 'maiden_name', 'family_surname', 'village', 'godfather', 'godmother',
                  'godmother_status', 'township', 'priest', 'baptism_day', 'birth_day']:
            md.append(f'| {k} | ' + ' | '.join(str(by[k][x]) for x in ('both', 'tagger', 'rules', 'none')) + ' |')
        js[book]['by'] = {k: dict(v) for k, v in by.items()}
    (ev.RES / 'combination_report.md').write_text('\n'.join(md) + '\n')
    (ev.RES / 'combination_report.json').write_text(json.dumps(js, ensure_ascii=False, indent=1))
    print('\n'.join(md))


if __name__ == '__main__':
    {'choose': choose, 'report': report}[sys.argv[1]]()
