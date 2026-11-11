"""Extract structured fields from per-entry drafts using the register's fixed formula.

Usage: .venv/bin/python -I pipeline/parse_entries.py processed/year_draft_<model>.json [--check-pilot]

Drafts are noisy (spurious spaces, similar-letter confusions), so formula anchors
("именемъ", "волости", "законныхъ", "деревнѣ" ...) are located by approximate matching
on the text with spaces removed; fields are the original text between anchors.
Ordinal day words become numbers; months are matched against old-orthography names.

Each field records `source`: "checked" if every line of its column is a checked label,
"mixed" or "model" otherwise. Model-sourced names are unreliable. Output:
processed/entries_<model>.json. --check-pilot compares against processed/pilot_reference.csv
(itself provisional machine adjudication, not ground truth).
"""
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')

MONTHS = {1: ['Января', 'Генваря'], 2: ['Февраля'], 3: ['Марта'], 4: ['Апрѣля', 'Апреля'], 5: ['Мая'],
          6: ['Іюня', 'Июня'], 7: ['Іюля', 'Июля'], 8: ['Августа'], 9: ['Сентября'], 10: ['Октября'],
          11: ['Ноября'], 12: ['Декабря']}
UNITS = ['перваго', 'втораго', 'третьяго', 'четвертаго', 'пятаго', 'шестаго', 'седьмаго', 'восьмаго', 'девятаго']
TEENS = ['десятаго', 'одиннадцатаго', 'двѣнадцатаго', 'тринадцатаго', 'четырнадцатаго', 'пятнадцатаго',
         'шестнадцатаго', 'семнадцатаго', 'восемнадцатаго', 'девятнадцатаго']
ORDINALS = {}
for i, w in enumerate(UNITS, 1):
    ORDINALS[w] = i
ORDINALS['осьмаго'] = 8
for i, w in enumerate(TEENS, 10):
    ORDINALS[w] = i
ORDINALS['шеснадцатаго'] = 16
ORDINALS['двадцатаго'] = 20
ORDINALS['тридцатаго'] = 30
for i, w in enumerate(UNITS, 1):
    ORDINALS['двадцать' + w] = 20 + i
ORDINALS['тридцатьперваго'] = 31


def strip(s):
    return unicodedata.normalize('NFC', s or '').lower().replace('ѣ', 'е').replace('і', 'и').replace('ъ', '')


def lev(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def approx_find(text, pattern, start=0, max_ratio=0.34):
    """Best approximate occurrence of pattern in text[start:] (Sellers). Returns (s, e) or None."""
    t, p = text[start:], pattern
    if not p or not t:
        return None
    m = len(p)
    prev = [0] * (len(t) + 1)          # free start anywhere
    starts_prev = list(range(len(t) + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * len(t)
        starts = [0] * (len(t) + 1)
        for j in range(1, len(t) + 1):
            opts = [(prev[j - 1] + (p[i - 1] != t[j - 1]), starts_prev[j - 1]),
                    (prev[j] + 1, starts_prev[j]),
                    (cur[j - 1] + 1, starts[j - 1])]
            cur[j], starts[j] = min(opts)
        prev, starts_prev = cur, starts
    best = min(range(len(t) + 1), key=lambda j: (prev[j], j))
    if prev[best] > max(1, int(m * max_ratio)):
        return None
    return start + starts_prev[best], start + best


class Text:
    """Original text with a space-free, simplified view for anchor search."""

    def __init__(self, s):
        self.orig = s or ''
        self.flat, self.map = '', []
        for k, ch in enumerate(self.orig):
            if not ch.isspace():
                self.flat += strip(ch) or ''
                self.map.extend([k] * len(strip(ch) or ''))
        self.map.append(len(self.orig))

    def find(self, word, start=0):
        r = approx_find(self.flat, strip(word).replace(' ', ''), start)
        return r

    def between(self, a, b):
        if a is None or b is None or b <= a:
            return None
        s = self.orig[self.map[a]:self.map[b]] if a < len(self.map) else ''
        s = re.sub(r'\s+', ' ', s).strip(' ,.-=;:')
        return s or None


def month_after(tx, pos):
    best = None
    for n, names in MONTHS.items():
        for name in names:
            r = tx.find(name, pos)
            if r and r[0] - pos <= 6:
                d = lev(tx.flat[r[0]:r[1]], strip(name))
                if best is None or d < best[0]:
                    best = (d, n, r)
    return (best[1], best[2]) if best else (None, None)


def ordinal(s):
    if not s:
        return None
    s = strip(s).replace(' ', '').replace('-', '').replace('=', '')
    w, d = min(((w, lev(s, strip(w))) for w in ORDINALS), key=lambda x: x[1])
    return ORDINALS[w] if d <= max(2, len(w) // 4) else None


def parse(entry):
    out = {}
    B, P, G = Text(entry['baptism']), Text(entry['parents']), Text(entry['godparents'])
    # baptism: "... года <Month> <ordinal> дня, въ ... Кс: <priest> окрещенъ младенецъ именемъ <Name> со всѣми ..."
    g = B.find('года')
    if g:
        m, mr = month_after(B, g[1])
        out['baptism_month'] = m
        if mr:
            d = B.find('дня', mr[1])
            out['baptism_day'] = ordinal(B.between(mr[1], d[0])) if d else None
    # "Кс" is too short to search the whole column (it matches inside "Тысяча"): look only
    # after "Викарнымъ", and take the priest's name up to "окрещенъ".
    vik = B.find('Викарнымъ')
    ok = B.find('окрещен', vik[1] if vik else 0)
    if vik and ok and ok[0] > vik[1]:
        pr = B.between(vik[1], ok[0]) or ''
        out['priest'] = re.sub(r'^\s*К[сеc]\s*[:.]?\s*', '', pr).strip() or None
    else:
        out['priest'] = None
    im = B.find('именемъ')
    so = B.find('совсѣми', im[1]) if im else None
    out['child_name'] = B.between(im[1], so[0] if so else len(B.flat)) if im else None
    # parents
    toks = P.orig.split()
    out['estate'] = toks[0].strip(' =-') if toks else None
    vol = P.find('волости')
    if not vol:
        # the 1886-87 clerk abbreviates "волости" as "Вол."
        mv = re.search(r'(?<![А-Яа-яЁёѢѣІі])[ВвB]ол\.', P.orig)
        if mv:
            vol = (next(i for i, k in enumerate(P.map) if k >= mv.start()),
                   next(i for i, k in enumerate(P.map) if k >= mv.end()))
    est_end = P.find(out['estate']) if out['estate'] else None
    out['township'] = P.between(est_end[1], vol[0]) if vol and est_end else None
    izy = None
    if vol:
        # "изъ" is too short for approximate search: match it as a whole word (also misread "идъ")
        mz = re.compile(r'(?<![А-Яа-яЁёѢѣІі])[иі][зд]ъ?(?![А-Яа-яЁёѢѣІі])').search(P.orig, P.map[vol[1]])
        if mz:
            fs = next(i for i, k in enumerate(P.map) if k >= mz.start())
            fe = next(i for i, k in enumerate(P.map) if k >= mz.end())
            izy = (fs, fe)
    if vol and izy:
        names = P.between(vol[1], izy[0]) or ''
        parts = re.split(r'\s+и\s+', names, maxsplit=1)
        out['father'] = parts[0] if len(parts) == 2 else None
        out['mother'] = parts[1] if len(parts) == 2 else None
    zak = P.find('законныхъ', izy[1] if izy else 0)
    out['maiden_and_surname'] = P.between(izy[1], zak[0]) if izy and zak else None
    syn, doch = P.find('сынъ'), P.find('дочь')
    if syn and not doch:
        out['sex'] = 'M'
    elif doch and not syn:
        out['sex'] = 'F'
    elif syn and doch:
        out['sex'] = 'M' if lev(P.flat[syn[0]:syn[1]], 'сын') <= lev(P.flat[doch[0]:doch[1]], 'дочь') else 'F'
    y = re.search(r'18\s*[89]\s*\d', P.orig)
    if y:
        flat_pos = next((i for i, k in enumerate(P.map) if k >= y.end()), None)
        m, mr = month_after(P, flat_pos) if flat_pos is not None else (None, None)
        out['birth_month'] = m
        if mr:
            rest = P.orig[P.map[mr[1]]:]
            dm = re.match(r'\s*[=\-.,]*\s*(\d{1,2})', rest)
            out['birth_day'] = int(dm.group(1)) if dm and 1 <= int(dm.group(1)) <= 31 else None
    dv = P.find('деревн')
    if not dv:
        # later clerks abbreviate "въ деревнѣ" as "въ дер."
        md = re.search(r'(?<![А-Яа-яЁёѢѣІі])[дД]ер\.', P.orig)
        if md:
            dv = (next(i for i, k in enumerate(P.map) if k >= md.start()),
                  next(i for i, k in enumerate(P.map) if k >= md.end()))
    mst = None if dv else re.search(r'\bМ[.ѣ]', P.orig)
    sego = P.find('сего')
    if dv and sego and sego[0] > dv[1]:
        start = dv[1] + (1 if dv[1] < len(P.flat) and P.flat[dv[1]] in 'еиь' else 0)
        out['village'] = P.between(start, sego[0])
    elif dv:
        # no "сего прихода" (later formula): village runs to "прихода", a comma or end, max 3 words
        start = dv[1] + (1 if dv[1] < len(P.flat) and P.flat[dv[1]] in 'еиь' else 0)
        rest = P.orig[P.map[start]:] if start < len(P.map) else ''
        rest = re.split(r',|\.|\s(?:[А-Яа-я]+)?[Пп]ри[хк]од', rest)[0]
        words = rest.split()[:3]
        out['village'] = ' '.join(words).strip(' -=') or None
    elif mst and sego:
        out['village'] = re.sub(r'\s+', ' ', P.orig[mst.start():P.map[sego[0]]]).strip(' ,.')
    by = G.find('были')
    out['godparents'] = G.between(by[1], len(G.flat)) if by else None
    # given names are single words: drop spurious spaces introduced by the recognizer
    for k in ('child_name', 'father', 'mother'):
        if out.get(k):
            out[k] = out[k].replace(' ', '')
    # dates: the baptism falls in the register year; a birth in a later month than the
    # baptism (e.g. December birth, January baptism) belongs to the previous year
    ry = entry.get('register_year') or 1888
    bm, bd = out.get('baptism_month'), out.get('baptism_day')
    out['baptism_date'] = f'{ry}-{bm:02d}-{bd:02d}' if bm and bd else None
    m, d = out.get('birth_month'), out.get('birth_day')
    if m and d:
        year = ry - 1 if bm and m > bm else ry
        out['birth_date'] = f'{year}-{m:02d}-{d:02d}'
    return out


def main():
    src = Path(sys.argv[1])
    src = src if src.is_absolute() else ROOT / src if (ROOT / src).exists() else BOOK / src
    draft = json.loads(src.read_text())
    ann = {a['id']: a for a in json.loads((BOOK / 'training/annotations.json').read_text())}
    props = []
    for name in ('line_proposals_v2.json', 'line_proposals_years_v2.json'):
        if (BOOK / 'training' / name).exists():
            props += json.loads((BOOK / 'training' / name).read_text())
    cell_src = {}
    for p in props:
        a = ann.get(p['id'])
        c = 'skip' if a and a['status'] == 'rejected_crop' else (
            'checked' if a and a['status'] in ('image_checked', 'independently_checked') else 'model')
        cell_src.setdefault((p['row_id'], p['cell']), set()).add(c)
    which = {'baptism': ['baptism_month', 'baptism_day', 'baptism_date', 'priest', 'child_name'],
             'godparents': ['godparents']}
    out = []
    for e in draft['entries']:
        f = parse(e)
        fields = {}
        for k, v in f.items():
            cell = next((c for c, ks in which.items() if k in ks), 'parents')
            s = cell_src.get((e['row_id'], cell), {'model'}) - {'skip'}
            fields[k] = {'value': v, 'source': 'checked' if s == {'checked'} else 'mixed' if 'checked' in s else 'model'}
        out.append({k: e.get(k) for k in ('row_id', 'register_year', 'scan', 'page', 'expected_entry_no', 'hand_group',
                                          'split', 'image', 'split_from')}
                   | {'fields': fields, 'text': {c: e[c] for c in ('baptism', 'parents', 'godparents')}})
    stem = src.stem.replace('year_draft_', '')
    dst = BOOK / f'processed/entries_{stem}.json'
    dst.write_text(json.dumps({'source': str(src.relative_to(ROOT)), 'model': draft.get('model', {}).get('model_path'),
                               'note': 'Machine-extracted fields from machine drafts. Unverified.', 'entries': out},
                              ensure_ascii=False, indent=1))
    keys = ['sex', 'baptism_date', 'birth_date', 'child_name', 'father', 'mother', 'village', 'priest']
    print(json.dumps({'entries': len(out), 'filled': {k: sum(1 for e in out if e['fields'].get(k, {}).get('value')) for k in keys},
                      'out': str(dst.relative_to(ROOT))}, ensure_ascii=False))
    if '--check-pilot' in sys.argv:
        check_pilot(out)
    return 0


def check_pilot(entries):
    ref = {}
    for r in csv.DictReader(open(BOOK / 'processed/pilot_reference.csv')):
        if r['value'] and r['status'] != 'unresolved' and '[' not in r['value']:
            ref.setdefault((int(r['scan']), int(r['entry_no'])), {})[r['field']] = r['value']
    pairs = {'sex': 'sex', 'baptism_date': 'baptism_date', 'birth_date': 'birth_date',
             'child_name': 'child_name_ru', 'father': 'father_name_ru', 'mother': 'mother_name_ru',
             'village': 'village_ru'}
    by = {(e['scan'], e['expected_entry_no']): e for e in entries}
    print('\nAgainst pilot_reference (non-unresolved values only; reference is itself provisional):')
    for ours, theirs in pairs.items():
        n = exact = near = 0
        for key, r in ref.items():
            if theirs not in r or key not in by:
                continue
            n += 1
            v = (by[key]['fields'].get(ours) or {}).get('value')
            if v is None:
                continue
            a, b = strip(str(v)).replace(' ', ''), strip(r[theirs]).replace(' ', '')
            exact += a == b
            near += lev(a, b) <= max(1, len(b) // 5)
        print(f'  {ours:13} compared={n:3} exact={exact:3} near={near:3}')


if __name__ == '__main__':
    sys.exit(main())
