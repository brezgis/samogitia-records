"""Sample translated entries of the five Plungė books as a comparison set for local language models.

Usage: python3 -I pipeline/local_models/build_translation_set.py OUT.json [PER_BOOK]
Each item: the drafted Russian columns the agents translated (source_text), the margin surname, and
the current English / Lithuanian (and Polish where present) as the reference to compare with.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOKS = {'plunge-1827-1-18': '1849–1854', 'plunge-1827-1-22': '1867–1874', 'plunge-1886-1890': '1886–1890',
         'plunge-1827-1-24': '1896–1902', 'plunge-1827-1-25': '1902–1907'}
F = ('baptism', 'parents', 'godparents')


def main():
    per = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    rnd, out = random.Random(11), []
    for book, years in BOOKS.items():
        P = ROOT / 'data' / book / 'processed'
        tr = json.loads(next(f for f in sorted((P / 'translations').glob('translations_v*_book*.json')) if 'before' not in f.name).read_text())
        side = json.loads((P / 'side_columns.json').read_text())
        full = [t for t in tr if all((t.get('source_text') or {}).get(c) for c in F) and all(t.get(c + '_lt') for c in F)]
        if any(t.get('baptism_pl') for t in full):
            full = [t for t in full if t.get('baptism_pl')]
        for t in rnd.sample(full, per):
            out.append({'id': f"{book}/{t['row_id']}", 'book': book, 'years': years,
                        'source': {c: t['source_text'][c] for c in F},
                        'margin_surname': (side.get(t['row_id']) or {}).get('margin_surname') or '',
                        'reference': {f'{c}_{l}': t.get(f'{c}_{l}', '') for l in ('en', 'lt', 'pl') for c in F if t.get(f'{c}_{l}')}})
    Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(out), 'entries')


if __name__ == '__main__':
    main()
