"""Download one digitised register book from epaveldas.lt (LVIA scans).

Usage: python3 -I pipeline/download_book.py ARCHIVE_ID BOOK_DIR [--pages-dir DIR]
  e.g. python3 -I pipeline/download_book.py 1828/1/7 data/rietavas-1828-1-7 --pages-dir /mnt/ssd240gb/anna/samogitia-data/rietavas-1828-1-7/pages
Writes BOOK_DIR/record.json (the archive's metadata), page_urls.txt (page order = sorted URLs) and
pages/NNNN.jpg. With --pages-dir the images go there and BOOK_DIR/pages is a link to it.
Sequential, with a pause between requests; already-downloaded pages are skipped, so it can be
re-run. Scans are NOC-NC (non-commercial use only).
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) register-reader'}


def fetch(url, tries=4):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        except Exception as exc:          # network hiccup: wait and retry
            if k == tries - 1:
                raise
            time.sleep(5 * (k + 1))


def main():
    ident, book = sys.argv[1], Path(sys.argv[2])
    pages_dir = Path(sys.argv[sys.argv.index('--pages-dir') + 1]) if '--pages-dir' in sys.argv else None
    book.mkdir(parents=True, exist_ok=True)
    rec = json.loads(fetch('https://www.epaveldas.lt/vepis-api/internal/findById?id=' + urllib.parse.quote(ident, safe='')))
    urls = sorted(u for u in (rec.get('resourcesFull') or {}) if '/original/' in u)
    if not urls:
        sys.exit(f'{ident}: no page images listed')
    (book / 'record.json').write_text(json.dumps(rec, ensure_ascii=False))
    (book / 'page_urls.txt').write_text('\n'.join(urls) + '\n')
    pages = book / 'pages'
    if pages_dir and not pages.exists():
        pages_dir.mkdir(parents=True, exist_ok=True)
        pages.symlink_to(pages_dir)
    pages.mkdir(parents=True, exist_ok=True)
    got = 0
    for i, u in enumerate(urls, 1):
        dst = pages / f'{i:04d}.jpg'
        if dst.exists() and dst.stat().st_size > 50_000:
            continue
        data = fetch(u)
        tmp = dst.with_suffix('.part')
        tmp.write_bytes(data)
        tmp.rename(dst)
        got += 1
        time.sleep(0.4)
    print(json.dumps({'id': ident, 'title': rec.get('title'), 'pages': len(urls), 'downloaded_now': got}))


if __name__ == '__main__':
    main()
