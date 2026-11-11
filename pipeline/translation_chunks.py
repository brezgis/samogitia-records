"""Write the chunk files the translation agents read.

Usage: SAMOGITIA_BOOK=data/<book> .venv/bin/python -I pipeline/translation_chunks.py MODEL OUT_DIR [PER]
Each chunk_NNN.json is a list of {row_id, year, baptism, parents, godparents, margin_surname}:
the three text columns of one entry as drafted by MODEL, plus the family surname as read from the
margin column (processed/side_columns.json), which is the same surname the parents column writes.
Prints a JSON summary {count, per, last, years} for the workflow arguments.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')


def main():
    model, out, per = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 40
    P = BOOK / 'processed'
    side = json.loads((P / 'side_columns.json').read_text()) if (P / 'side_columns.json').exists() else {}
    rows, years = [], set()
    for f in sorted(P.glob(f'entries_*_{model}.json')):
        for e in json.loads(f.read_text())['entries']:
            t = e['text']
            if not any((t.get(c) or '').strip() for c in ('baptism', 'parents', 'godparents')):
                continue
            years.add(e['register_year'])
            rows.append({'row_id': e['row_id'], 'year': e['register_year'], 'baptism': t.get('baptism') or '',
                         'parents': t.get('parents') or '', 'godparents': t.get('godparents') or '',
                         'margin_surname': (side.get(e['row_id']) or {}).get('margin_surname') or ''})
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('chunk_*.json'):
        old.unlink()
    chunks = [rows[i:i + per] for i in range(0, len(rows), per)]
    for i, c in enumerate(chunks, 1):
        (out / f'chunk_{i:03d}.json').write_text(json.dumps(c, ensure_ascii=False, indent=1))
    print(json.dumps({'dir': str(out), 'count': len(chunks), 'per': per, 'last': len(chunks[-1]) if chunks else 0,
                      'entries': len(rows), 'years': f'{min(years)}–{max(years)}' if years else ''}))


if __name__ == '__main__':
    main()
