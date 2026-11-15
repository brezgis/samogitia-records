"""Split a book's data.js into data.js (the list of spreads) and index.js (the search index).

Usage: python3 site/split_data.py
Older builds wrote both into data.js, which made every book wait for a megabyte of search index
before it could open. site/book/build_book.py now writes the two files itself; this converts the
books built before that, and leaves alone any book already split.
"""
from pathlib import Path

SITE = Path(__file__).resolve().parent

for d in sorted(SITE.glob('book*')):
    f = d / 'data.js'
    if not f.exists():
        continue
    s = f.read_text()
    i = s.find('\nwindow.INDEX=')
    if i < 0:
        print(d.name, 'already split' if (d / 'index.js').exists() else 'has no index')
        continue
    f.write_text(s[:i + 1])
    (d / 'index.js').write_text(s[i + 1:])
    print(d.name, 'data.js', i + 1, 'bytes; index.js', len(s) - i - 1, 'characters')
