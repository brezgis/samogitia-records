"""Score the taggers and the rule baseline; compare them on the unlabelled books.

Usage (after build_silver.py and train_tagger.py):
  .venv-htr/bin/python pipeline/neural_parser/evaluate.py lobo        # leave-one-book-out tables
  .venv-htr/bin/python pipeline/neural_parser/evaluate.py unlabelled [--tagger char] [--sample 50]
  .venv-htr/bin/python pipeline/neural_parser/evaluate.py leakage
Writes markdown and JSON under /mnt/ssd240gb/anna/samogitia-htr/neural-parser/results/.

Scoring (the same for every system; all spans are trimmed of edge spaces and punctuation first).
A predicted span of a field is right if both its ends are within `tol` characters of the gold span's
ends (tol 0 = exact, tol 2). Per field: recall = right / gold spans; precision = right / predictions
made where a gold span of that field exists in the entry (a prediction without gold cannot be judged
and is only counted, as "no gold"); F1 from the two.
Gold sets: "silver" (every silver span); "agents" (only spans the agents' names lists gave, with the
names-list span as gold, whatever the rule parser says); by span source; by entry tier.
Independent checks: (1) the predicted family-surname span against the margin surname read by another
agent from the side column (reconcile_surnames.reconcile -> "agree"); (2) the day decoded from the
predicted date phrase against the side column's day (same decoder for all systems).
"""
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import (ALL_FIELDS, COLS, COL_OF, NAME_FIELDS, SCRATCH, TRANSLATED, UNLABELLED, YEARS, decode_date,  # noqa: E402
                    load_drafts, rule_spans)
import reconcile_surnames as rs  # noqa: E402

RES = SCRATCH / 'results'
SHORT = {'plunge-1827-1-18': '1827/1/18', 'plunge-1827-1-22': '1827/1/22', 'plunge-1886-1890': '1886-1890',
         'plunge-1827-1-24': '1827/1/24', 'plunge-1827-1-25': '1827/1/25', 'plunge-1827-1-20': '1827/1/20',
         'salantai-1517-1-1': 'Salantai 1517/1/1'}


def load_silver():
    return [json.loads(l) for l in open(SCRATCH / 'silver/silver.jsonl')]


def load_preds(name):
    p = SCRATCH / 'preds' / (name + '.jsonl')
    if not p.exists():
        return None
    out = {}
    for l in open(p):
        r = json.loads(l)
        out[(r['book'], r['row_id'])] = {(x['col'], x['field']): (x['s'], x['e']) for x in r['spans']}
    return out


def rules_preds(entries, tag):
    """Rule spans for a list of entries, cached under preds/rules__<tag>.jsonl."""
    name = f'rules__{tag}'
    got = load_preds(name)
    if got is not None:
        return got
    stats = Counter()
    with open(SCRATCH / 'preds' / (name + '.jsonl'), 'w') as fh:
        for e in entries:
            sp = rule_spans(e, stats)
            fh.write(json.dumps({'book': e['book'], 'row_id': e['row_id'],
                                 'spans': [{'col': c, 'field': f, 's': s, 'e': t} for c in COLS for f, (s, t) in sp[c].items()]},
                                ensure_ascii=False) + '\n')
    (SCRATCH / 'preds' / (name + '.adapter.json')).write_text(json.dumps(stats))
    return load_preds(name)


def ok(p, g, tol):
    return p is not None and abs(p[0] - g[0]) <= tol and abs(p[1] - g[1]) <= tol


def prf(tp, n_pred, n_gold):
    p = tp / n_pred if n_pred else 0.0
    r = tp / n_gold if n_gold else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def score(rows, preds, gold_of, tol):
    """{field: (tp, predictions with gold, gold, predictions without gold)}."""
    c = defaultdict(lambda: [0, 0, 0, 0])
    for r in rows:
        pr = preds.get((r['book'], r['row_id']), {})
        gold = gold_of(r)
        for f in ALL_FIELDS:
            g, p = gold.get(f), pr.get((COL_OF[f], f))
            if g:
                c[f][2] += 1
                if p:
                    c[f][1] += 1
                    c[f][0] += ok(p, g, tol)
            elif p:
                c[f][3] += 1
    return c


def gold_silver(r):
    return {x['field']: (x['s'], x['e']) for x in r['spans']}


def gold_agents(r):
    return {x['field']: tuple(x['names']) for x in r['spans'] if x['names']}


def gold_src(src):
    return lambda r: {x['field']: (x['s'], x['e']) for x in r['spans'] if x['src'] == src}


def micro(c, fields):
    tp = sum(c[f][0] for f in fields)
    return prf(tp, sum(c[f][1] for f in fields), sum(c[f][2] for f in fields))


def mean(xs):
    return sum(xs) / len(xs) if xs else float('nan')


def systems_for(book):
    out = {}
    for label, pat in (('char', 'char__{b}__s{s}'), ('xlmr', 'xlmr__{b}__s{s}'), ('rubert', 'rubert__{b}__s{s}'),
                       ('char names-only', 'char_namesonly__{b}__s{s}'), ('char no-aug', 'char_noaug__{b}__s{s}')):
        seeds = [p for p in (load_preds(pat.format(b=book, s=s)) for s in (1, 2)) if p is not None]
        if seeds:
            out[label] = seeds
    return out


def margin_check(rows, preds):
    """(entries with a margin surname, predictions made, predictions agreeing with the margin)."""
    n = made = agree = 0
    for r in rows:
        m = r['side'].get('margin_surname') or ''
        if len(rs.stem(m)) < 3:
            continue
        n += 1
        p = preds.get((r['book'], r['row_id']), {}).get(('parents', 'SURNAME'))
        if p:
            made += 1
            agree += rs.reconcile(m, r['text']['parents'][p[0]:p[1]], False)['status'] == 'agree'
    return n, made, agree


def day_check(rows, preds, field, side_key):
    n = made = agree = 0
    for r in rows:
        d = re.sub(r'\D', '', r['side'].get(side_key) or '')
        if not d or not 1 <= int(d) <= 31:
            continue
        n += 1
        p = preds.get((r['book'], r['row_id']), {}).get((COL_OF[field], field))
        if p:
            made += 1
            agree += decode_date(r['text'][COL_OF[field]][p[0]:p[1]])[1] == int(d)
    return n, made, agree


def as_preds(rows, gold_of):
    return {(r['book'], r['row_id']): {(COL_OF[f], f): sp for f, sp in gold_of(r).items()} for r in rows}


def lobo():
    RES.mkdir(exist_ok=True)
    silver = load_silver()
    md, js = [], {}
    examples = []
    for book in TRANSLATED:
        rows = [r for r in silver if r['book'] == book]
        systems = {'rules': [rules_preds(rows, book)]} | systems_for(book)
        if len(systems) == 1:
            continue
        names = list(systems)
        js[book] = {}
        md.append(f'\n### Held out: {SHORT[book]} ({YEARS[book]}), {len(rows)} entries\n')
        for gname, gold_of, fields in (('silver (all spans)', gold_silver, ALL_FIELDS), ("agents' names spans only", gold_agents, NAME_FIELDS)):
            md.append(f'\nGold = {gname}. F1 exact / F1 within 2 characters (mean of the seeds).\n')
            md.append('| field | gold spans | ' + ' | '.join(names) + ' |')
            md.append('|---|---:|' + '---|' * len(names))
            res = {s: {tol: [score(rows, p, gold_of, tol) for p in seeds] for tol in (0, 2)} for s, seeds in systems.items()}
            for f in fields:
                n = res['rules'][0][0][f][2]
                cells = []
                for s in names:
                    f0 = mean([prf(*c[f][:3])[2] for c in res[s][0]])
                    f2 = mean([prf(*c[f][:3])[2] for c in res[s][2]])
                    cells.append(f'{100 * f0:.0f} / {100 * f2:.0f}')
                md.append(f'| {f} | {n} | ' + ' | '.join(cells) + ' |')
            cells = []
            for s in names:
                per_seed = [micro(c, [f for f in fields if f in NAME_FIELDS]) for c in res[s][2]]
                js[book].setdefault(gname, {})[s] = {'micro_name_fields_tol2_P_R_F1_per_seed': per_seed,
                                                    'no_gold_predictions': sum(res[s][2][0][f][3] for f in fields)}
                cells.append(f'{100 * mean([x[2] for x in per_seed]):.1f} (P {100 * mean([x[0] for x in per_seed]):.0f}, R {100 * mean([x[1] for x in per_seed]):.0f}'
                             + (f'; seeds {100 * per_seed[0][2]:.1f}, {100 * per_seed[1][2]:.1f})' if len(per_seed) > 1 else ')'))
            md.append('| **name fields, micro F1 ±2** | | ' + ' | '.join(cells) + ' |')
        # by span source and by entry tier (name fields, micro F1 within 2)
        md.append('\nName fields by where the silver span came from, and by entry tier: micro F1 within 2 characters (gold spans).\n')
        md.append('| subset | ' + ' | '.join(names) + ' |')
        md.append('|---|' + '---|' * len(names))
        subsets = [(f'span source: {s}', rows, gold_src(s)) for s in ('both', 'names', 'conflict', 'rules', 'rules+part')]
        subsets += [(f'entry tier {t}', [r for r in rows if r['tier'] == t], gold_silver) for t in 'AB']
        for label, sub, gold_of in subsets:
            cells, n = [], 0
            for s in names:
                cs = [score(sub, p, gold_of, 2) for p in systems[s]]
                n = sum(cs[0][f][2] for f in NAME_FIELDS)
                cells.append(f'{100 * mean([micro(c, NAME_FIELDS)[2] for c in cs]):.1f}')
            md.append(f'| {label} ({n}) | ' + ' | '.join(cells) + ' |')
        # independent checks
        md.append('\nIndependent checks: agreeing with the side column / spans produced / entries with a side-column value.\n')
        md.append('| check | ' + ' | '.join(names) + ' | silver label | agents\' span |')
        md.append('|---|' + '---|' * (len(names) + 2))
        extra = [[as_preds(rows, gold_silver)], [as_preds(rows, gold_agents)]]
        for label, fn in (('family surname = margin surname', lambda p: margin_check(rows, p)),
                          ('baptism day = side column', lambda p: day_check(rows, p, 'BAPT_DATE', 'baptism_day')),
                          ('birth day = side column', lambda p: day_check(rows, p, 'BIRTH_DATE', 'birth_day'))):
            cells = []
            for seeds in list(systems.values()) + extra:
                v = [fn(p) for p in seeds]
                n, made, agree = v[0][0], mean([x[1] for x in v]), mean([x[2] for x in v])
                cells.append(f'{agree:.0f} / {made:.0f} / {n} ({100 * agree / max(n, 1):.0f}%)'
                             + (f' [seeds {v[0][2]}, {v[1][2]}]' if len(v) > 1 else ''))
                js[book].setdefault(label, []).append(v)
            md.append(f'| {label} | ' + ' | '.join(cells) + ' |')
        # examples: tagger right where rules are not, and the reverse (agents' spans as gold, within 2)
        if 'char' in systems:
            rng = random.Random(1)
            pool = {'tagger right, rules not': [], 'rules right, tagger not': []}
            for r in rows:
                g = gold_agents(r)
                rp, tp = systems['rules'][0].get((book, r['row_id']), {}), systems['char'][0].get((book, r['row_id']), {})
                for f, sp in g.items():
                    a, b = ok(rp.get((COL_OF[f], f)), sp, 2), ok(tp.get((COL_OF[f], f)), sp, 2)
                    if a != b:
                        pool['tagger right, rules not' if b else 'rules right, tagger not'].append((r, f, sp, rp.get((COL_OF[f], f)), tp.get((COL_OF[f], f))))
            for k, items in pool.items():
                js[book][k] = len(items)
                for r, f, sp, rp, tp in rng.sample(items, min(5, len(items))):
                    t = r['text'][COL_OF[f]]
                    lo, hi = max(0, sp[0] - 45), min(len(t), sp[1] + 45)
                    examples.append(f"- **{k}** ({SHORT[book]} {r['row_id']}, {f}): «…{t[lo:hi]}…» agents: «{t[sp[0]:sp[1]]}»; "
                                    f"rules: «{t[rp[0]:rp[1]] if rp else '—'}»; tagger: «{t[tp[0]:tp[1]] if tp else '—'}»")
    (RES / 'lobo.md').write_text('\n'.join(md) + '\n\n### Examples (char tagger seed 1 against the rules; gold = agents\' spans)\n\n' + '\n'.join(examples) + '\n')
    (RES / 'lobo.json').write_text(json.dumps(js, ensure_ascii=False, indent=1))
    print('\n'.join(md))


def leakage():
    silver = load_silver()
    norm = lambda t: hashlib.md5(re.sub(r'\W+', '', t.lower()).encode()).hexdigest()
    by_book = defaultdict(set)
    for r in silver:
        for c in COLS:
            if len(r['text'][c]) > 40:
                by_book[r['book']].add(norm(r['text'][c]))
    for b, m in UNLABELLED.items():
        for e in load_drafts(b, m):
            for c in COLS:
                if len(e['text'][c]) > 40:
                    by_book[b].add(norm(e['text'][c]))
    out = ['| book | columns (over 40 characters) | identical column text found in any other book |', '|---|---:|---:|']
    for b in by_book:
        others = set().union(*(v for k, v in by_book.items() if k != b))
        out.append(f'| {SHORT[b]} | {len(by_book[b])} | {len(by_book[b] & others)} |')
    ids = Counter((r['book'], r['row_id']) for r in silver)
    out.append(f'\nRow ids repeated inside a book: {sum(1 for v in ids.values() if v > 1)}.')
    RES.mkdir(exist_ok=True)
    (RES / 'leakage.md').write_text('\n'.join(out) + '\n')
    print('\n'.join(out))


def unlabelled():
    tagger = sys.argv[sys.argv.index('--tagger') + 1] if '--tagger' in sys.argv else 'char'
    n_sample = int(sys.argv[sys.argv.index('--sample') + 1]) if '--sample' in sys.argv else 50
    RES.mkdir(exist_ok=True)
    md = []
    for book, model in UNLABELLED.items():
        entries = load_drafts(book, model)
        rules = rules_preds(entries, book)
        tags = {t: load_preds(f'{t}__none__s1') for t in ('char', 'xlmr')}
        tags = {t: p for t, p in tags.items() if p}
        md.append(f'\n### {SHORT[book]} ({YEARS[book]}, draft {model}), {len(entries)} entries\n')
        md.append('| field | rules filled | ' + ' | '.join(f'{t} filled' for t in tags) + f' | both filled (rules, {tagger}) | same ±2 | differ | only rules | only {tagger} |')
        md.append('|---|---:|' + '---:|' * (len(tags) + 5))
        tp = tags[tagger]
        differing = defaultdict(list)
        for f in ALL_FIELDS:
            key = (COL_OF[f], f)
            rf = sum(1 for e in entries if key in rules.get((book, e['row_id']), {}))
            tf = [sum(1 for e in entries if key in p.get((book, e['row_id']), {})) for p in tags.values()]
            both = same = only_r = only_t = 0
            for e in entries:
                a, b = rules.get((book, e['row_id']), {}).get(key), tp.get((book, e['row_id']), {}).get(key)
                if a and b:
                    both += 1
                    same += ok(a, b, 2)
                    if not ok(a, b, 2):
                        differing[e['row_id']].append((f, a, b))
                elif a:
                    only_r += 1
                    differing[e['row_id']].append((f, a, None))
                elif b:
                    only_t += 1
                    differing[e['row_id']].append((f, None, b))
            md.append(f'| {f} | {rf} | ' + ' | '.join(str(x) for x in tf) + f' | {both} | {same} | {both - same} | {only_r} | {only_t} |')
        md.append(f'\nEntries where rules and the {tagger} tagger differ on at least one field: {len(differing)} of {len(entries)}.')
        # blind reading sheet: the two systems appear as X and Y in random order per entry
        rng = random.Random(20261115)
        by_id = {e['row_id']: e for e in entries}
        sheet, key = [], {}
        for i, rid in enumerate(rng.sample(sorted(differing), min(n_sample, len(differing))), 1):
            flip = rng.random() < 0.5
            key[i] = {'row_id': rid, 'X': tagger if flip else 'rules', 'fields': [d[0] for d in differing[rid]]}
            sheet.append(f'## {i}')
            for c in COLS:
                if any(COL_OF[d[0]] == c for d in differing[rid]):
                    sheet.append(f'{c[:4]}: {by_id[rid]["text"][c]}')
            for f, a, b in differing[rid]:
                t = by_id[rid]['text'][COL_OF[f]]
                x, y = (b, a) if flip else (a, b)
                sheet.append(f'  {f}: X «{t[x[0]:x[1]] if x else "—"}» | Y «{t[y[0]:y[1]] if y else "—"}»')
        (RES / f'disagreements_{book}.txt').write_text('\n'.join(sheet) + '\n')
        (RES / f'disagreements_{book}.key.json').write_text(json.dumps(key, ensure_ascii=False, indent=1))
    (RES / 'unlabelled.md').write_text('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    {'lobo': lobo, 'unlabelled': unlabelled, 'leakage': leakage}[sys.argv[1]]()
