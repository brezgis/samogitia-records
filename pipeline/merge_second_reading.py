"""Fold a second, independent reading of the side columns into processed/side_columns.json.

Usage: SAMOGITIA_BOOK=data/<book> .venv/bin/python -I pipeline/merge_second_reading.py MODEL CHUNK.json [...] [--write]
  MODEL names the drafts (entries_<year>_<MODEL>.json) whose parents column is the third witness.
  Each CHUNK.json is {"entries": [{row_id, margin_surname, margin_en, margin_lt, entry_no, ...}]}.

For each re-read entry the margin surname is settled between three witnesses: the first reading
(already in side_columns.json), the second reading, and the surname the draft has in the parents
column (the clerk wrote the family surname twice). Nothing here is verified by a person.
  both      the two readings have the same letters (brackets aside): kept, no longer "uncertain"
  second    they differ and the second is the one closer to the parents column (or there is no draft
            surname to compare, or neither is close): the second reading is taken, the first kept as
            `margin_alt`
  first     they differ and the first is clearly the one closer to the parents column: kept, the second
            stored as `margin_alt`
(Salantai 1517/1/1, 374 entries re-read: where the readings differed and the parents column could tell,
the second reader was the closer one 66 times, the first 15, neither clearly 86.)
`margin_by` records which; `margin_alt` the reading not chosen; `uncertain` keeps margin_surname
unless the readings agree or the chosen one matches the parents column. Numbers (entry_no, counts,
days): where the two readings differ the second is taken (its strips are cut wider) and the field is
listed in `uncertain`; an empty value never replaces a filled one. Notes: the longer transcription wins.
"""
import difflib
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reconcile_surnames import draft_surname, letters, stem  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
NUM = ('entry_no', 'boys_count', 'girls_count', 'birth_day', 'baptism_day')


def sim(a, b):
    a, b = letters(a).replace('ъ', ''), letters(b).replace('ъ', '')      # whole names: stems of short names are too short to compare
    return difflib.SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    model, chunks = args[0], args[1:]
    P = BOOK / 'processed'
    side = json.loads((P / 'side_columns.json').read_text())
    draft = {}
    for f in sorted(P.glob(f'entries_*_{model}.json')):
        for e in json.loads(f.read_text())['entries']:
            draft[e['row_id']] = draft_surname(e['fields'])
    counts, numdiff = Counter(), Counter()
    for c in chunks:
        for x in json.loads(Path(c).read_text())['entries']:
            r = x['row_id']
            a = side.get(r)
            if a is None or a.get('margin_by'):
                counts['skipped (unknown row or already merged)'] += 1
                continue
            s1, s2, d = a.get('margin_surname') or '', x.get('margin_surname') or '', draft.get(r, '')
            unc = set(a.get('uncertain') or [])
            if not letters(s2) and letters(s1):
                by = 'first'
            elif letters(s1) == letters(s2):
                by = 'both'
            else:
                q1, q2 = sim(s1, d), sim(s2, d)
                by = 'first' if q1 >= 0.6 and q1 > q2 + 0.1 else 'second'
            if by == 'both':
                unc.discard('margin_surname')
                a['margin_surname'] = s1 if s1.count('?') <= s2.count('?') else s2   # the less hedged spelling
            elif by == 'second':
                a['margin_alt'] = s1
                for k in ('margin_surname', 'margin_en', 'margin_lt'):
                    a[k] = x.get(k) or ''
                unc.add('margin_surname')
                if sim(s2, d) >= 0.8:
                    unc.discard('margin_surname')
            else:
                a['margin_alt'] = s2
                if sim(s1, d) < 0.8:
                    unc.add('margin_surname')
                else:
                    unc.discard('margin_surname')
            if by == 'both' and a['margin_surname'] == s2:
                a['margin_en'], a['margin_lt'] = x.get('margin_en') or a.get('margin_en'), x.get('margin_lt') or a.get('margin_lt')
            a['margin_by'] = by
            counts[by] += 1
            for k in NUM:
                v1, v2 = (a.get(k) or '').strip(), (x.get(k) or '').strip()
                if v2 and v1 != v2:
                    numdiff[k] += bool(v1)
                    a[k] = v2
                    if v1:
                        unc.add(k)
                        a.setdefault('first_reading', {})[k] = v1
            if a.get('boys_count') and not a.get('girls_count'):
                a['sex'] = 'M'
            elif a.get('girls_count') and not a.get('boys_count'):
                a['sex'] = 'F'
            if len(x.get('notes_ru') or '') > len(a.get('notes_ru') or ''):
                for k in ('notes_ru', 'notes_en', 'notes_lt'):
                    a[k] = x.get(k) or ''
            if x.get('remark'):
                a['remark2'] = x['remark']
            a['uncertain'] = sorted(unc)
            a['read_by'] += f'; second reading Claude Opus ({Path(c).stem})'
    print(json.dumps({'surname': dict(counts), 'numbers changed': dict(numdiff)}, ensure_ascii=False))
    if '--write' in sys.argv:
        (P / 'side_columns.json').write_text(json.dumps(side, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
