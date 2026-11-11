"""Create (or refresh) the reading GUI for another register book from site/book.

Usage: python3 site/make_book_site.py FIRST_YEAR LAST_YEAR ARCHIVE_FILE START_SCAN
  e.g. python3 site/make_book_site.py 1891 1895 1827/1/25 10
Copies site/book's index.html, app.js, vendor/ and textiles into the book's folder (the name it
has in site/library.json, else site/book-FIRST-LAST). The pages are identical for every book:
book.js, written by site/make_library.py, says which parish, years and archive file this is.
ARCHIVE_FILE and START_SCAN are kept for compatibility; library.json is what counts.
Data is built separately:
  SAMOGITIA_BOOK=data/<book> BOOK_OUT=site/book-FIRST-LAST BOOK_MODEL=<model> \
  BOOK_YEARS=FIRST-LAST BOOK_TRANSLATIONS=translations/<file>.json \
  .venv/bin/python -I site/book/build_book.py --images
"""
import json
import re
import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent


def main():
    y0, y1, archive, scan = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    lib = json.loads((SITE / 'library.json').read_text())
    named = [b['dir'] for p in lib['parishes'] for b in p['books'] if b['archive'] == archive]
    out = SITE / (named[0] if named else f'book-{y0}-{y1}')
    (out / 'img').mkdir(parents=True, exist_ok=True)
    for f in ('index.html',):
        shutil.copy(SITE / 'book' / f, out / f)
    shutil.copytree(SITE / 'book/vendor', out / 'vendor', dirs_exist_ok=True)
    shutil.copytree(SITE / 'book/img/src', out / 'img/src', dirs_exist_ok=True)
    for f in (SITE / 'book/img').glob('cloth-*.jpg'):
        shutil.copy(f, out / 'img' / f.name)
    for f in (SITE / 'book/img').glob('ribbon-*.webp'):
        shutil.copy(f, out / 'img' / f.name)
    t = (SITE / 'book/app.js').read_text()   # identical for every book: book.js says which book this is
    (out / 'app.js').write_text(t)
    print(out)


if __name__ == '__main__':
    main()
