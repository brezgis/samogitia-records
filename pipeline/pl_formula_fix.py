"""Apply the Polish formula changes of 2026-11-11 (after the first review) to finished entries.

Usage: SAMOGITIA_BOOK=data/<book> .venv/bin/python -I pipeline/pl_formula_fix.py TRANSLATIONS.json
Three mechanical rewrites, each only where the old wording matches exactly:
  1. church: "w płungiańskim rzymskokatolickim kościele parafialnym"
             -> "w kościele parafialnym rzymskokatolickim w Płungianach"
  2. rite:   "obrzędów Sakramentu" -> "obrzędów sakramentu chrztu" (also inside [ ])
  3. parents: "Włościan, prawowitych małżonków X i Y z domu Z, córka, urodzona …"
             -> "Córka włościan, prawowitych małżonków X i Y z domu Z, urodzona …"
Names are not touched. Prints how many fields each rule changed and how many parents fields did
not match the pattern (left as they were).
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
PARENTS = re.compile(r'^(?P<estate>[A-ZŁŚŻŹĆ][^,]{2,60}), prawowitych małżonków (?P<mid>.+?), (?P<kid>syn|córka), (?P<rest>urodzon[ya]\b.*)$', re.S)


def main():
    path = BOOK / 'processed/translations' / sys.argv[1]
    data = json.loads(path.read_text())
    n = {'church': 0, 'rite': 0, 'parents': 0, 'parents_unmatched': 0, 'entries_with_polish': 0}
    for t in data:
        if not t.get('baptism_pl') and not t.get('parents_pl'):
            continue
        n['entries_with_polish'] += 1
        b = t.get('baptism_pl') or ''
        b2 = b.replace('w płungiańskim rzymskokatolickim kościele parafialnym', 'w kościele parafialnym rzymskokatolickim w Płungianach')
        n['church'] += b2 != b
        b3 = b2.replace('obrzędów Sakramentu', 'obrzędów sakramentu chrztu').replace('[Sakramentu]', '[sakramentu chrztu]')
        n['rite'] += b3 != b2
        t['baptism_pl'] = b3
        p = t.get('parents_pl') or ''
        m = PARENTS.match(p)
        if m:
            e = m['estate']
            t['parents_pl'] = f"{m['kid'].capitalize()} {e[0].lower() + e[1:]}, prawowitych małżonków {m['mid']}, {m['rest']}"
            n['parents'] += 1
        elif p and 'prawowitych małżonków' in p and not re.match(r'^(Syn|Córka) ', p):
            n['parents_unmatched'] += 1
        if any(k in t for k in ('baptism_pl',)):
            t['pl_revision'] = 'formula rev. 2026-11-11 (church phrase, sakramentu chrztu, child first in the parents field)'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(json.dumps(n))


if __name__ == '__main__':
    main()
