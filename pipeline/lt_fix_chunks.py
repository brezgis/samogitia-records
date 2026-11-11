"""Write the chunk files for a Lithuanian correction pass over an existing translations file.

Usage: SAMOGITIA_BOOK=data/<book> .venv/bin/python -I pipeline/lt_fix_chunks.py TRANSLATIONS.json OUT_DIR [PER]
TRANSLATIONS.json is relative to processed/translations/. Each chunk_NNN.json is a list of
{row_id, year, ru: {baptism, parents, godparents}, margin_surname, en: {parents}, lt: {...}}: the
draft the translation was made from, the family surname as read from the margin column
(processed/side_columns.json), and the current English and Lithuanian. Prints a JSON summary.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
CELLS = ('baptism', 'parents', 'godparents')


def main():
    name, out, per = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 40
    P = BOOK / 'processed'
    tr = json.loads((P / 'translations' / name).read_text())
    side = json.loads((P / 'side_columns.json').read_text()) if (P / 'side_columns.json').exists() else {}
    years = {}
    for f in P.glob('entries_*.json'):
        for e in json.loads(f.read_text())['entries']:
            if e.get('register_year'):
                years[e['row_id']] = e['register_year']
    rows = []
    for t in sorted(tr, key=lambda t: t['row_id']):
        m = re.search(r'\b(1[89]\d\d)\b', t.get('baptism_lt') or '')
        rows.append({'row_id': t['row_id'], 'year': years.get(t['row_id']) or (int(m.group(1)) if m else None),
                     'ru': {c: (t.get('source_text') or {}).get(c, '') for c in CELLS},
                     'margin_surname': (side.get(t['row_id']) or {}).get('margin_surname') or '',
                     'en': {'parents': t.get('parents_en', '')},      # the surname-bearing sentence, for consistency
                     'lt': {c: t.get(c + '_lt', '') for c in CELLS}})
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('chunk_*.json'):
        old.unlink()
    chunks = [rows[i:i + per] for i in range(0, len(rows), per)]
    for i, c in enumerate(chunks, 1):
        (out / f'chunk_{i:03d}.json').write_text(json.dumps(c, ensure_ascii=False, indent=1))
    ys = [r['year'] for r in rows if r['year']]
    print(json.dumps({'dir': str(out), 'count': len(chunks), 'per': per, 'last': len(chunks[-1]) if chunks else 0,
                      'entries': len(rows), 'years': f'{min(ys)}–{max(ys)}' if ys else ''}))


if __name__ == '__main__':
    main()
