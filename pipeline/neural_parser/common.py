"""Shared pieces of the neural field-tagger experiment: tag set, data loaders, the rule baseline as
character spans, span trimming, date decoding.

Usage: imported by build_silver.py, train_tagger.py, evaluate.py (not a script).

The rule baseline is `pipeline/parse_entries.parse()` plus an adapter (`rule_spans`) that places the
values it returns back into the column text as character spans. Three things in the adapter are NOT
in parse() and are this experiment's own rules (marked "own rule" in every table):
  * date phrases: parse() returns numbers; the span is rebuilt from the same anchors;
  * maiden name / family surname: parse() returns them together; split as reconcile_surnames does
    (last word = family surname, a single word = maiden name);
  * godfather / godmother / her status: parse() returns the godparents column whole.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
import parse_entries as pe  # noqa: E402
from parse_entries import Text, approx_find, lev, strip, letters_only  # noqa: E402

SCRATCH = Path('/mnt/ssd240gb/anna/samogitia-htr/neural-parser')
COLS = ['baptism', 'parents', 'godparents']
# canonical order of the fields inside each column
FIELDS = {'baptism': ['BAPT_DATE', 'PRIEST', 'CHILD'],
          'parents': ['ESTATE', 'TOWNSHIP', 'FATHER', 'MOTHER', 'MAIDEN', 'SURNAME', 'BIRTH_DATE', 'VILLAGE'],
          'godparents': ['GODFATHER', 'GODMOTHER', 'GM_STATUS']}
ALL_FIELDS = [f for c in COLS for f in FIELDS[c]]
COL_OF = {f: c for c in COLS for f in FIELDS[c]}
# fields the agents' names lists can label; the others have rule-made silver only
NAME_FIELDS = ['PRIEST', 'CHILD', 'TOWNSHIP', 'FATHER', 'MOTHER', 'MAIDEN', 'SURNAME', 'VILLAGE', 'GODFATHER', 'GODMOTHER']
RULE_ONLY_FIELDS = ['BAPT_DATE', 'ESTATE', 'BIRTH_DATE', 'GM_STATUS']

TRANSLATED = {'plunge-1827-1-18': 'translations_v6_book18', 'plunge-1827-1-22': 'translations_v6_book22',
              'plunge-1886-1890': 'translations_v3_book1', 'plunge-1827-1-24': 'translations_v4_book24',
              'plunge-1827-1-25': 'translations_v6_book25'}
YEARS = {'plunge-1827-1-18': '1849-54', 'plunge-1827-1-22': '1867-74', 'plunge-1886-1890': '1886-90',
         'plunge-1827-1-24': '1896-1902', 'plunge-1827-1-25': '1902-07', 'plunge-1827-1-20': '1854-57',
         'salantai-1517-1-1': '1857-62'}
UNLABELLED = {'salantai-1517-1-1': 'crnn-ru-v4', 'plunge-1827-1-20': 'plunge-v7'}
EDGE = ' \t\n,.-=;:—–"()«»'


def load_translated(book):
    """Entries of a translated book: [{book, row_id, text{col}, names, en{col}, issues}]."""
    out = []
    for e in json.loads((ROOT / 'data' / book / 'processed/translations' / (TRANSLATED[book] + '.json')).read_text()):
        st = e.get('source_text') or {}
        if not isinstance(st, dict):
            continue
        out.append({'book': book, 'row_id': e['row_id'], 'text': {c: st.get(c) or '' for c in COLS},
                    'names': e.get('names') or [], 'en': {c: e.get(c + '_en') or '' for c in COLS}})
    return out


def load_drafts(book, model):
    """Entries of a book's machine draft: [{book, row_id, text{col}, register_year}]."""
    out = []
    for f in sorted((ROOT / 'data' / book / 'processed').glob(f'year_draft_*_{model}.json')):
        for e in json.loads(f.read_text())['entries']:
            out.append({'book': book, 'row_id': e['row_id'], 'register_year': e.get('register_year'),
                        'text': {c: e.get(c) or '' for c in COLS}})
    return out


def load_side(book):
    p = ROOT / 'data' / book / 'processed/side_columns.json'
    return json.loads(p.read_text()) if p.exists() else {}


def trim(text, s, e):
    """Span without edge whitespace and punctuation; None if nothing is left."""
    while s < e and text[s] in EDGE:
        s += 1
    while e > s and text[e - 1] in EDGE:
        e -= 1
    return (s, e) if e > s else None


def flat_ws(text):
    idx = [k for k, ch in enumerate(text) if not ch.isspace()]
    return ''.join(text[k] for k in idx), idx


def locate(text, value, lo=0, max_ratio=0.2, exact_below=5):
    """Place `value` (words possibly joined, edges stripped) in text[lo:]: exact on the text without
    spaces, else approximate on the simplified view. Returns (s, e, distance) or None."""
    v = ''.join((value or '').split())
    if not v:
        return None
    f, idx = flat_ws(text[lo:])
    k = f.find(v)
    if k >= 0:
        return lo + idx[k], lo + idx[k + len(v) - 1] + 1, 0
    T = Text(text[lo:])
    p = strip(v)
    if not p:
        return None
    k = T.flat.find(p)
    if k >= 0:
        s, e, d = T.map[k], T.map[k + len(p) - 1] + 1, 0
    else:
        if len(p) < exact_below:
            return None
        r = approx_find(T.flat, p, 0, max_ratio)
        if not r or r[1] <= r[0]:
            return None
        s, e = T.map[r[0]], T.map[r[1] - 1] + 1
        d = lev(T.flat[r[0]:r[1]], p)
    s, e = lo + s, lo + e
    # a match that stops one or two letters short of the word's edge takes them in ("Гелен|ы")
    m = re.match(r'[%s]{1,2}(?![%s])' % (pe.LETTER, pe.LETTER), text[e:e + 3])
    if m:
        e += m.end()
    m = re.search(r'(?<![%s])[%s]{1,2}$' % (pe.LETTER, pe.LETTER), text[max(0, s - 3):s])
    if m and text[s].islower():
        s -= len(m.group())
    return s, e, d


# ---------------------------------------------------------------- dates (own rule: spans; parse(): values)
def _orig(tx, flat_pos):
    return tx.map[flat_pos] if flat_pos < len(tx.map) else len(tx.orig)


def baptism_date_span(text):
    """From the first letter of the column to the end of the day ("... года <Month> <ordinal> дня")."""
    B = Text(text)
    g = B.find('года')
    if not g:
        return None
    m, mr = pe.month_after(B, g[1])
    if not mr:
        return None
    end = _orig(B, mr[1] - 1) + 1
    d = B.find('дня', mr[1])
    if d and d[0] - mr[1] <= 30:
        end = _orig(B, d[1] - 1) + 1
    else:
        da = re.match(r'\W*(?:дня\W*)?\d{1,2}', text[end:])
        if da:
            end += da.end()
    first = re.search(r'[%s\d]' % pe.LETTER, text)
    return trim(text, first.start() if first else 0, end)


def birth_date_span(text):
    """The birth date phrase after "родивш..." (or from the year in digits): up to "дня", else to
    "года" / the day in digits after the month, else the month."""
    P = Text(text)
    rod = P.find('родивш')
    if rod:
        k = _orig(P, rod[1] - 1) + 1
        m, mr = pe.month_after(P, pe.flat_index(P, k), window=40)
    else:
        y = re.search(r'18\s*[4-9]\s*\d|19\s*0\s*\d', text)
        if not y:
            return None
        k = max(0, y.start() - 6)
        m, mr = pe.month_after(P, pe.flat_index(P, y.end()), window=12)
    if not mr:
        return None
    # the phrase begins at "сего", the first digit or the month, whichever comes first after "родивш..."
    start = _orig(P, mr[0])
    first = re.search(r'(?<![%s])[сС]ег[оа](?![%s])|\d' % (pe.LETTER, pe.LETTER), text[k:start])
    if first:
        start = k + first.start()
    if not mr:
        return None
    end = _orig(P, mr[1] - 1) + 1
    d = P.find('дня', mr[1])
    if d and d[0] - mr[1] <= 24:
        end = _orig(P, d[1] - 1) + 1
    else:
        tail = re.match(r'\W*(?:сего\s*)?(?:\d[\d\s]{0,5}\d|\d)?\s*(?:года|г\.|г(?=\s))|\W*\d{1,2}(?:го)?(?!\d)', text[end:])
        if tail:
            end += tail.end()
    return trim(text, start, end)


def decode_date(span_text):
    """(month, day) read from a date phrase with parse_entries' month and ordinal tables; None where
    not readable. The same decoder is applied to every system's span."""
    T = Text(span_text or '')
    best = None
    for n, names in pe.MONTHS.items():
        for name in names:
            r = T.find(name)
            if r:
                d = lev(T.flat[r[0]:r[1]], strip(name))
                if best is None or d < best[0]:
                    best = (d, n, r)
    if not best:
        return None, None
    _, month, mr = best
    before, after = T.orig[:_orig(T, mr[0])], T.orig[_orig(T, mr[1] - 1) + 1:]
    da = re.match(r'\W*(\d{1,2})(?!\s*\d)', after)
    db = re.search(r'(?<!\d)(\d{1,2})\W*$', before)
    day = int((da or db).group(1)) if (da or db) else None
    if day is None:
        dn = Text(after).find('дня')
        w = after[:Text(after).map[dn[0]]] if dn else after
        day = pe.ordinal(w)
    return month, (day if day and 1 <= day <= 31 else None)


# ---------------------------------------------------------------- godparents (own rule)
STATUS_WORDS = {'девицею': 'maiden', 'девицей': 'maiden', 'вдовою': 'widow', 'супругою': 'wife', 'женою': 'wife'}


def _status_kind(tok):
    w = strip(letters_only(tok))
    for k, kind in STATUS_WORDS.items():
        if len(w) >= len(k) - 2 and lev(w, k) <= (1 if len(k) <= 6 else 3 if len(k) >= 8 else 2):
            return kind
    return None


def _is_estate(tok):
    w = strip(letters_only(tok))
    return len(w) >= 5 and any(lev(w[:len(st)], st) <= 1 for st in pe.ESTATE_STEMS)


def godparent_spans(text):
    """Own rule. "... были [estate] <godfather> съ <godmother> <status>": the godfather is what stands
    between "были" and "съ" less estate words and titles; after "съ", a status word ("дѣвицею",
    "вдовою") closes the godmother's name, or ("супругою") the first word is her name and the rest,
    her husband's name included, is the status phrase."""
    G = Text(text)
    by = G.find('были')
    if not by:
        return {}
    start = _orig(G, by[1] - 1) + 1
    rest = text[start:]
    m = re.search(r'(?<=\s)[-=]?[сc][ъь]?(?=\s)', rest) or re.search(r'(?<=[ъйь])съ(?=\s)', rest)
    out = {}
    left = rest[:m.start()] if m else rest
    toks = [(t.start(), t.end()) for t in re.finditer(r'\S+', left)]
    while toks and (len(letters_only(left[toks[0][0]:toks[0][1]])) <= 2 or _is_estate(left[toks[0][0]:toks[0][1]])
                    or pe.is_title(left[toks[0][0]:toks[0][1]])
                    or lev(strip(letters_only(left[toks[0][0]:toks[0][1]]))[:6], 'викарн') <= 1):
        toks.pop(0)
    toks = toks[:4] if m else toks[:3]
    if toks:
        out['GODFATHER'] = trim(text, start + toks[0][0], start + toks[-1][1])
    if m:
        base = start + m.end()
        right = text[base:]
        toks = [(t.start(), t.end()) for t in re.finditer(r'\S+', right) if letters_only(t.group())]
        word = lambda i, j=None: right[toks[i][0]:toks[(i if j is None else j)][1]]
        # the status word, whole or divided in two by the recognizer ("дѣ вицею")
        kw = next(((i, i + 1) for i in range(1, len(toks) - 1) if not _status_kind(word(i))
                   and len(letters_only(word(i))) <= 4 and _status_kind(word(i) + word(i + 1))), None)
        one = next((i for i in range(1, len(toks)) if _status_kind(word(i))), None)
        if one is not None and (kw is None or one <= kw[0]):
            kw = (one, one)
        if kw is None:
            # no readable status word: two words are a name and surname; with more, a second word in
            # the masculine genitive ("Игнатія", "Ивана") is the husband's name and only the first is hers
            n = 1 if len(toks) >= 3 and strip(letters_only(word(1)))[-1:] in ('а', 'я') else 2
            if toks:
                out['GODMOTHER'] = trim(text, base + toks[0][0], base + toks[:n][-1][1])
        else:
            kind = _status_kind(word(kw[0])) or _status_kind(word(kw[0]) + word(kw[1]))
            if kind == 'wife' and kw[0] >= 2:
                # her name is the first word, or the first two when it was divided ("Ка тартиною")
                n = 2 if kw[0] >= 3 and (len(letters_only(word(0))) <= 3 or word(1)[0].islower()) \
                    and len(letters_only(word(0, 1))) <= 13 else 1
                out['GODMOTHER'] = trim(text, base + toks[0][0], base + toks[n - 1][1])
                out['GM_STATUS'] = trim(text, base + toks[n][0], base + toks[kw[1]][1])
            else:
                out['GODMOTHER'] = trim(text, base + toks[0][0], base + toks[kw[0] - 1][1])
                out['GM_STATUS'] = trim(text, base + toks[kw[0]][0], base + toks[kw[1]][1])
    return {k: v for k, v in out.items() if v}


# ---------------------------------------------------------------- the rule baseline as spans
def rule_spans(entry, stats=None):
    """{col: {FIELD: (s, e)}} from parse() and the adapter. `stats` (a Counter) receives
    'filled:<FIELD>' when parse() gave a value and 'located:<FIELD>' when the adapter placed it."""
    t = entry['text']
    f = pe.parse({'baptism': t['baptism'], 'parents': t['parents'], 'godparents': t['godparents'],
                  'register_year': entry.get('register_year')})
    out = {c: {} for c in COLS}

    def put(col, field, value, lo=0):
        if not value:
            return None
        if stats is not None:
            stats['filled:' + field] += 1
        r = locate(t[col], value, lo, max_ratio=0.25, exact_below=3) or (
            locate(t[col], value, 0, max_ratio=0.25, exact_below=3) if lo else None)
        sp = trim(t[col], r[0], r[1]) if r else None
        if sp:
            out[col][field] = sp
            if stats is not None:
                stats['located:' + field] += 1
        return sp

    B, P = t['baptism'], t['parents']
    if f.get('baptism_month') and f.get('baptism_day'):
        sp = baptism_date_span(B)
        if stats is not None:
            stats['filled:BAPT_DATE'] += 1
            stats['located:BAPT_DATE'] += bool(sp)
        if sp:
            out['baptism']['BAPT_DATE'] = sp
    lo = out['baptism'].get('BAPT_DATE', (0, 0))[1]
    pr = put('baptism', 'PRIEST', f.get('priest'), lo)
    put('baptism', 'CHILD', f.get('child_name'), pr[1] if pr else lo)
    es = put('parents', 'ESTATE', f.get('estate'))
    lo = es[1] if es else 0
    tw = put('parents', 'TOWNSHIP', f.get('township'), lo)
    lo = tw[1] if tw else lo
    fa = put('parents', 'FATHER', f.get('father'), lo)
    lo = fa[1] if fa else lo
    mo = put('parents', 'MOTHER', f.get('mother'), lo)
    lo = mo[1] if mo else lo
    ms = f.get('maiden_and_surname')
    if ms:
        if stats is not None:
            stats['filled:MAIDEN+SURNAME'] += 1
        r = locate(P, ms, lo, max_ratio=0.25, exact_below=3)
        sp = trim(P, r[0], r[1]) if r else None
        if sp:
            if stats is not None:
                stats['located:MAIDEN+SURNAME'] += 1
            words = [(m.start() + sp[0], m.end() + sp[0]) for m in re.finditer(r'\S+', P[sp[0]:sp[1]])
                     if letters_only(m.group())]
            if len(words) > 1:
                a, b = trim(P, words[0][0], words[-2][1]), trim(P, *words[-1])
                if a:
                    out['parents']['MAIDEN'] = a
                if b:
                    out['parents']['SURNAME'] = b
            elif words:
                out['parents']['MAIDEN'] = sp
            lo = sp[1]
    if f.get('birth_month') and f.get('birth_day'):
        sp = birth_date_span(P)
        if stats is not None:
            stats['filled:BIRTH_DATE'] += 1
            stats['located:BIRTH_DATE'] += bool(sp)
        if sp:
            out['parents']['BIRTH_DATE'] = sp
    put('parents', 'VILLAGE', f.get('village'), lo)
    g = godparent_spans(t['godparents'])
    if stats is not None:
        for k in g:
            stats['filled:' + k] += 1
            stats['located:' + k] += 1
    out['godparents'] = g
    # a field may not overlap an earlier one in the same column
    for c in COLS:
        taken = []
        for fld in FIELDS[c]:
            sp = out[c].get(fld)
            if sp and any(sp[0] < b and a < sp[1] for a, b in taken):
                del out[c][fld]
            elif sp:
                taken.append(sp)
    return out


def spans_to_list(d):
    return [{'col': c, 'field': f, 's': s, 'e': e} for c in COLS for f, (s, e) in d.get(c, {}).items()]
