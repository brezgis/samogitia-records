"""Compare drafts of one book made by different recognizers, on names and on parse yield.

Usage: SAMOGITIA_BOOK=data/<book> python3 -I pipeline/local_models/compare_drafts.py MODEL [MODEL ...]
Reads processed/entries_<year>_<MODEL>.json and processed/side_columns.json (agent readings of the
margin). Writes nothing. Per model:
  surname  - reconcile_surnames.py's verdict on the parsed family surname against the margin surname
  in text  - the margin surname's stem found (similarity >= 0.8) among the words of the parents column,
             which does not depend on the parser
  days     - parsed baptism / birth day equal to the day read from the side column
  clean    - entries a template could translate: child, father, mother, village, both dates parsed,
             both days equal to the side column, surname agreeing with the margin
"""
import difflib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pipeline'))
from reconcile_surnames import draft_surname, reconcile, stem  # noqa: E402

BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')


def day(v):
    m = re.search(r'-(\d\d)$', v or '')
    return int(m.group(1)) if m else None


def num(v):
    d = re.sub(r'\D', '', v or '')
    return int(d) if d else None


def main():
    P = BOOK / 'processed'
    side = json.loads((P / 'side_columns.json').read_text())
    for model in sys.argv[1:]:
        c, n = Counter(), 0
        for f in sorted(P.glob(f'entries_*_{model}.json')):
            for e in json.loads(f.read_text())['entries']:
                n += 1
                F = {k: v['value'] for k, v in e['fields'].items()}
                sc = side.get(e['row_id']) or {}
                margin = sc.get('margin_surname') or ''
                ok_s = False
                if len(stem(margin)) >= 3:
                    c['with margin'] += 1
                    st = reconcile(margin, draft_surname(e['fields']), False)['status']
                    c['surname ' + st] += 1
                    ok_s = st == 'agree'
                    words = [stem(w) for w in (e['text'].get('parents') or '').split()]
                    c['in text'] += any(difflib.SequenceMatcher(None, stem(margin), w).ratio() >= 0.8 for w in words if len(w) >= 3)
                for k, s in (('baptism_date', 'baptism_day'), ('birth_date', 'birth_day')):
                    if num(sc.get(s)) is not None:
                        c[s + ' read'] += 1
                        c[s + ' same'] += day(F.get(k)) == num(sc.get(s))
                full = all(F.get(k) for k in ('child_name', 'father', 'mother', 'village', 'baptism_date', 'birth_date'))
                c['all fields parsed'] += full
                c['clean'] += bool(full and ok_s and day(F.get('baptism_date')) == num(sc.get('baptism_day'))
                                   and day(F.get('birth_date')) == num(sc.get('birth_day')))
        m = c['with margin']
        print(f"{model}: {n} entries; surname agrees with margin {c['surname agree']}/{m} ({100 * c['surname agree'] / m:.0f}%), "
              f"conflict {c['surname conflict']}, garbled {c['surname margin']}, not parsed {c['surname margin_only']}; "
              f"margin name found in parents text {c['in text']}/{m} ({100 * c['in text'] / m:.0f}%); "
              f"baptism day same {c['baptism_day same']}/{c['baptism_day read']}, birth day same {c['birth_day same']}/{c['birth_day read']}; "
              f"all fields parsed {c['all fields parsed']}; template-clean {c['clean']} ({100 * c['clean'] / n:.0f}%)")


if __name__ == '__main__':
    main()
