"""Build site/library.js (the shelf of books) and each book site's book.js from site/library.json.

Usage: python3 site/make_library.py
For every book in library.json: if its site folder exists and has data.js, the book is "open"
(entries and translated-language counts are read from its spreads); otherwise it is listed as
"scanned" (downloaded, not read yet) when its data folder has scans, else "known". Each open
book's folder gets book.js (window.BOOK), which app.js reads for the parish, years and archive id.
"""
import json
from pathlib import Path

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent


def main():
    lib = json.loads((SITE / 'library.json').read_text())
    out = {'span': lib['span'], 'cloths': lib.get('cloths', {}), 'parishes': []}
    for p in lib['parishes']:
        books = []
        for b in p['books']:
            d = SITE / b['dir']
            rec = {'dir': b['dir'], 'years': b['years'], 'archive': b['archive'], 'cloth': b.get('cloth', 'plunge')}
            if (d / 'data.js').exists():
                n = langs = 0
                counts = {}
                for f in (d / 'spreads').glob('*.json'):
                    for e in json.loads(f.read_text())['entries']:
                        n += 1
                        for l in e['html']:
                            counts[l] = counts.get(l, 0) + 1
                rec.update(state='open', entries=n, langs=sorted(l for l, c in counts.items() if l != 'ru' and c > n * 0.5))
                (d / 'book.js').write_text('window.BOOK=' + json.dumps(
                    {'parish': p['id'], 'dir': b['dir'], 'years': b['years'], 'archive': b['archive'],
                     'scan': b.get('scan', 1), 'row': b.get('row', ''),
                     'cloth': b.get('cloth', 'plunge'), 'ribbon': b.get('ribbon', 'mazeikiai')}, ensure_ascii=False) + ';\n')
            else:
                pages = ROOT / b['data'] / 'pages'
                rec['state'] = 'scanned' if pages.exists() and any(pages.iterdir()) else 'known'
            books.append(rec)
        out['parishes'].append({'id': p['id'], 'names': p['names'], 'books': books})
    (SITE / 'library.js').write_text('window.LIBRARY=' + json.dumps(out, ensure_ascii=False) + ';\n')
    for p in out['parishes']:
        print(p['id'], [(b['dir'], b['state'], b.get('entries')) for b in p['books']])


if __name__ == '__main__':
    main()
