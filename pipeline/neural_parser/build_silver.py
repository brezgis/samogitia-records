"""Silver character-span labels for the five translated Plungė books.

Usage: PYTHONPATH=pipeline .venv-htr/bin/python pipeline/neural_parser/build_silver.py [--sample N [--seed S]]
Writes /mnt/ssd240gb/anna/samogitia-htr/neural-parser/silver/silver.jsonl and silver_stats.json;
--sample N also writes audit_sample.txt (N entries, stratified by book and tier) for reading.

Two label sources per entry (nothing here is human-checked):

NAMES  the translating agent's `names` list ("Cyrillic as drafted -> English / Lithuanian").
  1. The item's Cyrillic (notes in parentheses and [ ] ? … marks removed) is placed in a column:
     candidates are the columns whose English sentence contains the item's English rendering (all
     three if none does); in each, the string is searched exactly on the text without spaces, then
     approximately on the simplified view (<= 20% edits, none for strings under 5 letters). The
     column with the fewest edits wins; a tie between columns drops the item.
  2. The role comes from where the English rendering stands in that column's English sentence and
     from the order of the placed items in the text. parse_entries' anchors are NOT used.
     baptism:  before "baptised" -> PRIEST, after -> CHILD.
     parents:  followed by "district/township/volost" -> TOWNSHIP; after the last "born" -> VILLAGE;
               first item after "née" -> MAIDEN; before the first " and " and first in the text ->
               FATHER; between " and " and "née" -> MOTHER; the one remaining item that stands in
               the text after mother and maiden name -> SURNAME. With "illegitimate" and no "née":
               first -> MOTHER, second -> SURNAME. Items whose text order contradicts
               father < mother < maiden < surname < village are dropped.
     godparents: before the first " and " -> GODFATHER; after it -> GODMOTHER unless a "wife of /
               widow of / daughter of" stands between (then it is the husband: not a field).
               Items of one role are joined into one span when they are neighbours in the text.
RULES  common.rule_spans(): parse_entries.parse() placed back in the text, plus this experiment's
       own rules for date phrases, the maiden/surname split and the godparents.

A placed string that stops one or two letters short of a word's edge is extended to it.
Partial names. Agents often list a godparent or priest by surname only ("Козловскій" for "Викентій
Козловскій"). When the English sentence has a given name directly before the item's rendering and
no item covers it, the names span is not used: the rule span is kept if it contains it (src
"rules+part"), otherwise the field stays unlabelled.
Per span `src`: "both" (the two sources give the same span within 2 characters at each end; the
names span is kept if it was placed exactly, else the rule span), "names" (no rule span), "rules" (no names span), "conflict" (both exist and
differ; the names span is kept, the rule span is stored beside it).
Spans longer than 50 characters (dates 110, status 70) are discarded as run-on rows.
BAPT_DATE, ESTATE, BIRTH_DATE, GM_STATUS can only be "rules". ESTATE is kept only when the first
word resembles an estate word (parse() takes the first word whatever it is).
Per entry `tier`: A = at least six name-field spans are "both" and none is "conflict";
B = any other entry with at least one span; none = no span at all.
"""
import json
import random
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import (COLS, FIELDS, NAME_FIELDS, SCRATCH, TRANSLATED, load_side, load_translated, locate,  # noqa: E402
                    rule_spans, trim, _is_estate)

CYR = re.compile(r'[А-Яа-яЁёѢѣІіѲѳѴѵ]')
REL = re.compile(r'\b(?:wife|widow|daughter|son|sister|brother|servant|maid)\b[^,;.]{0,12}\bof\b')


def parse_item(it):
    if ' -> ' not in it:
        return None
    cyr, rest = it.split(' -> ', 1)
    cyr = re.sub(r'\(.*?\)|\(.*$', ' ', cyr)
    cyr = re.sub(r'[\[\]?…]|\.\.+', '', cyr).strip(' ,.;:-')
    en = rest.split(' / ')[0]
    en = re.sub(r'\[[^\]]*\]|\(.*?\)', ' ', en)
    en = re.sub(r'\s+', ' ', en).strip(' ,.;:')
    if not CYR.search(cyr):
        return None
    return cyr, en


def en_pos(sentence, en):
    """Position of an English rendering in a sentence (bracket marks ignored), by its full form or
    its longest word of four letters or more; -1 if absent."""
    if not en:
        return -1
    k = sentence.find(en)
    if k >= 0:
        return k
    plain = re.sub(r'\s*\[\?\]', lambda m: ' ' * len(m.group()), sentence)
    k = plain.find(en)
    if k >= 0:
        return k
    words = sorted((w for w in en.split() if len(w) >= 4), key=len, reverse=True)
    for w in words[:1]:
        k = sentence.find(w)
        if k >= 0:
            return k
    return -1


def place_items(entry, stats):
    """[(col, s, e, english position, english length)] for the items that can be placed."""
    placed = []
    for it in entry['names']:
        stats['items'] += 1
        pi = parse_item(it) if isinstance(it, str) else None
        if not pi:
            stats['items_unparsed'] += 1
            continue
        cyr, en = pi
        pos = {c: en_pos(entry['en'][c], en) for c in COLS}
        cand = [c for c in COLS if pos[c] >= 0] or COLS
        hits = []
        for c in cand:
            r = locate(entry['text'][c], cyr)
            if r:
                sp = trim(entry['text'][c], r[0], r[1])
                if sp:
                    hits.append((r[2], c, sp))
        if not hits:
            stats['items_not_located'] += 1
            continue
        hits.sort(key=lambda h: h[0])
        if len(hits) > 1 and hits[0][0] == hits[1][0]:
            stats['items_ambiguous_column'] += 1
            continue
        _, c, sp = hits[0]
        if pos[c] < 0:
            stats['items_no_english'] += 1
            continue
        stats['items_placed'] += 1
        placed.append((c, sp[0], sp[1], pos[c], len(en)))
        entry.setdefault('_dist', {})[(c, sp[0], sp[1])] = hits[0][0]
    return placed


GIVEN_BEFORE = re.compile(r'(?<![\w.])([A-ZŁŻŚŹĆ][a-ząćęłńóśźżė]{2,})(?:\s*\[\?\])?\s+$')
NOT_NAMES = {'The', 'Fr', 'Canon', 'Rev', 'Father', 'Son', 'Daughter', 'Roman', 'Catholic', 'Plungė', 'Dean', 'Prelate'}


def given_before(sent, p):
    """True if a capitalised word that looks like a given name stands just before position p of the
    English sentence ("Wincenty |Kozlovskii"): the item placed there is then only part of the name."""
    m = GIVEN_BEFORE.search(sent[:p])
    return bool(m) and m.group(1) not in NOT_NAMES


def join_role(items, text):
    """One span for the items of a role: the first item, extended over neighbours (gap <= 3 chars)."""
    items = sorted(items)
    s, e = items[0][0], items[0][1]
    for a, b in items[1:]:
        if a - e <= 3 and not re.search(r'[А-Яа-яѢѣІі]{2,}', text[e:a]):
            e = max(e, b)
    return s, e


def names_spans(entry, stats):
    """{col: {FIELD: (s, e)}} from the agent's names list."""
    placed = place_items(entry, stats)
    out = {c: {} for c in COLS}
    partial = entry.setdefault('_partial', set())
    by_col = defaultdict(list)
    for c, s, e, p, n in placed:
        by_col[c].append((s, e, p, n))
    # baptism
    sent = entry['en']['baptism']
    m = re.search(r'bapti[sz]ed', sent)
    if m:
        roles = defaultdict(list)
        for s, e, p, n in by_col['baptism']:
            roles['PRIEST' if p < m.start() else 'CHILD'].append((s, e, p))
        for r, items in roles.items():
            out['baptism'][r] = join_role([x[:2] for x in items], entry['text']['baptism'])
            if r == 'PRIEST' and given_before(sent, min(x[2] for x in items)):
                partial.add(('baptism', r))
        if 'PRIEST' in out['baptism'] and 'CHILD' in out['baptism'] and out['baptism']['PRIEST'][0] > out['baptism']['CHILD'][0]:
            out['baptism'] = {}
            stats['order_dropped:baptism'] += 1
    # parents
    sent = entry['en']['parents']
    born = [m.start() for m in re.finditer(r'\bborn\b', sent)]
    born = born[-1] if born else len(sent) + 1
    nee = sent.find('née')
    and_ = sent.find(' and ')
    illeg = bool(re.search(r'[Ii]llegitimate|natural (?:son|daughter)|unmarried|out of wedlock', sent))
    rest, P = [], out['parents']
    for s, e, p, n in sorted(by_col['parents']):
        if re.match(r'\s*(?:\[\?\]\s*)?(?:rural\s+)?(?:district|township|volost)', sent[p + n:]):
            P.setdefault('TOWNSHIP', (s, e))
        elif p > born:
            P.setdefault('VILLAGE', (s, e))
        else:
            rest.append((s, e, p))
    if nee >= 0:
        after = sorted((x for x in rest if x[2] > nee), key=lambda x: x[2])
        before = [x for x in rest if x[2] < nee]
        if after:
            P['MAIDEN'] = after[0][:2]
        if and_ >= 0 and and_ < nee:
            fa = [x for x in before if x[2] < and_]
            mo = [x for x in before if x[2] > and_]
            if fa:
                P['FATHER'] = min(fa)[:2]
            if mo:
                P['MOTHER'] = min(mo)[:2]
        used = {P.get(k) for k in ('MAIDEN', 'FATHER', 'MOTHER')}
        floor = max([P[k][1] for k in ('MOTHER', 'MAIDEN') if k in P] or [10 ** 6])
        sur = [x for x in rest if x[:2] not in used and x[0] >= floor]
        if len(sur) == 1:
            P['SURNAME'] = sur[0][:2]
    elif illeg:
        if rest:
            P['MOTHER'] = rest[0][:2]
        if len(rest) == 2:
            P['SURNAME'] = rest[1][:2]
    elif and_ >= 0:
        fa = [x for x in rest if x[2] < and_]
        mo = [x for x in rest if x[2] > and_]
        if fa:
            P['FATHER'] = min(fa)[:2]
        if mo:
            P['MOTHER'] = min(mo)[:2]
        if 'MOTHER' in P:
            sur = [x for x in rest if x[:2] not in (P.get('FATHER'), P['MOTHER']) and x[0] >= P['MOTHER'][1]]
            if len(sur) == 1:
                P['SURNAME'] = sur[0][:2]
    order = [P[k] for k in ('FATHER', 'MOTHER', 'MAIDEN', 'SURNAME', 'VILLAGE') if k in P]
    if any(a[1] > b[0] for a, b in zip(order, order[1:])):
        stats['order_dropped:parents'] += 1
        out['parents'] = {k: v for k, v in P.items() if k == 'VILLAGE' and v[0] >= max(o[1] for o in order[:-1] or [(0, 0)])}
    # godparents
    sent = entry['en']['godparents']
    and_ = sent.find(' and ')
    if and_ >= 0:
        roles = defaultdict(list)
        for s, e, p, n in by_col['godparents']:
            if p < and_:
                roles['GODFATHER'].append((s, e, p))
            elif not REL.search(sent[and_:p]):
                roles['GODMOTHER'].append((s, e, p))
        for r, items in roles.items():
            out['godparents'][r] = join_role([x[:2] for x in items], entry['text']['godparents'])
            first = min(items)          # the item that stands first in the text
            if given_before(sent, first[2]) and not any(x[2] < first[2] for x in items):
                partial.add(('godparents', r))
        G = out['godparents']
        if 'GODFATHER' in G and 'GODMOTHER' in G and G['GODFATHER'][1] > G['GODMOTHER'][0]:
            out['godparents'] = {}
            stats['order_dropped:godparents'] += 1
    return out


def same(a, b, tol=2):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def build_entry(entry, stats, rstats):
    ns = names_spans(entry, stats)
    rs = rule_spans(entry, rstats)
    spans = []
    for c in COLS:
        col = []
        for f in FIELDS[c]:
            n, r = ns[c].get(f), rs[c].get(f)
            if f == 'ESTATE' and r and not _is_estate(entry['text'][c][r[0]:r[1]]):
                r = None
            cap = 110 if f.endswith('DATE') else 70 if f == 'GM_STATUS' else 50
            n = n if n and n[1] - n[0] <= cap else None      # a run-on row (two entries read as one)
            r = r if r and r[1] - r[0] <= cap else None
            if n and (c, f) in entry.get('_partial', ()):
                # the agent listed only part of the name (the surname): the rule span stands if it
                # contains that part, otherwise the field is left unlabelled
                stats['partial_names:' + f] += 1
                if r and r[0] <= n[0] and n[1] <= r[1] + 2:
                    col.append({'col': c, 'field': f, 's': r[0], 'e': r[1], 'src': 'rules+part', 'names': None, 'rules': r})
                continue
            if n and r:
                src = 'both' if same(n, r) else 'conflict'
            elif n:
                src = 'names'
            elif r:
                src = 'rules'
            else:
                continue
            s, e = n or r
            if src == 'both' and entry.get('_dist', {}).get((c, n[0], n[1]), 1) > 0:
                s, e = r            # an approximately placed names span that agrees: the rule span's edges
            col.append({'col': c, 'field': f, 's': s, 'e': e, 'src': src, 'names': n, 'rules': r})
        # a rule-only span that overlaps a names-backed span is dropped; then any remaining overlap drops both
        keep = []
        for x in sorted(col, key=lambda x: x['src'].startswith('rules')):
            if any(x['s'] < y['e'] and y['s'] < x['e'] for y in keep):
                stats['overlap_dropped'] += 1
                continue
            keep.append(x)
        spans += sorted(keep, key=lambda x: x['s'])
    nm = [x for x in spans if x['field'] in NAME_FIELDS]
    both = sum(x['src'] == 'both' for x in nm)
    conf = sum(x['src'] == 'conflict' for x in nm)
    tier = 'A' if both >= 6 and conf == 0 else 'B' if spans else 'none'
    return spans, tier


def do_book(book):
    st, rst, rows = Counter(), Counter(), []
    side = load_side(book)
    for e in load_translated(book):
        spans, tier = build_entry(e, st, rst)
        sc = side.get(e['row_id']) or {}
        rows.append({'book': book, 'row_id': e['row_id'], 'text': e['text'], 'spans': spans, 'tier': tier,
                     'en': e['en'], 'names': e['names'],
                     'side': {k: sc.get(k) or '' for k in ('margin_surname', 'birth_day', 'baptism_day')},
                     'side_uncertain': sc.get('uncertain') or []})
        st['entries'] += 1
        st['tier:' + tier] += 1
        for x in spans:
            st[f"span:{x['field']}:{x['src']}"] += 1
    return book, rows, st, rst


def main():
    from multiprocessing import Pool
    out_dir = SCRATCH / 'silver'
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, stats, rstats = [], {}, {}
    with Pool(len(TRANSLATED)) as pool:
        for book, r, st, rst in pool.map(do_book, list(TRANSLATED)):
            rows += r
            stats[book], rstats[book] = st, rst
    with open(out_dir / 'silver.jsonl', 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    (out_dir / 'silver_stats.json').write_text(json.dumps(
        {'names': {b: dict(c) for b, c in stats.items()}, 'rule_adapter': {b: dict(c) for b, c in rstats.items()}},
        ensure_ascii=False, indent=1))
    for b, c in stats.items():
        print(b, {k: v for k, v in c.items() if not k.startswith('span:')})
    if '--sample' in sys.argv:
        n = int(sys.argv[sys.argv.index('--sample') + 1])
        rng = random.Random(int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 20261115)
        per = max(1, n // (2 * len(TRANSLATED)))
        lines = []
        for b in TRANSLATED:
            for tier in 'AB':
                pool = [r for r in rows if r['book'] == b and r['tier'] == tier]
                for r in rng.sample(pool, min(per, len(pool))):
                    lines.append(f"## {b} {r['row_id']} tier {tier}")
                    for c in COLS:
                        t, k, s = r['text'][c], 0, ''
                        for x in sorted((x for x in r['spans'] if x['col'] == c), key=lambda x: x['s']):
                            s += t[k:x['s']] + '⟦' + t[x['s']:x['e']] + '⟧' + x['field'] + ':' + ('p' if x['src'] == 'rules+part' else x['src'][0]) + ' '
                            k = x['e']
                        lines.append(f'{c[:4]}: ' + s + t[k:])
                        lines.append('  en: ' + r['en'][c])
                    lines.append('')
        (out_dir / 'audit_sample.txt').write_text('\n'.join(lines))
        print('audit sample:', out_dir / 'audit_sample.txt')


if __name__ == '__main__':
    main()
