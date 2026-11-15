"""Write the published copy of every book's page images: site/<book>/img/pages/NNNN_L.webp (and _R).

Usage: nice python3 site/make_pages_webp.py [BOOK_DIR ...]      (default: every site/book*)
build_book.py cuts the pages as JPEG (kept on disk, not committed). The site loads the WebP copies
(quality 35, same pixel size: about 46% of the JPEGs' size and still easy to read), which is what
lets all the books' pages fit in the repository beside GitHub Pages' 1 GB limit.
Re-runnable: a .webp newer than its .jpg is left alone.
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

SITE = Path(__file__).resolve().parent


def one(jpg):
    out = jpg.with_suffix('.webp')
    if out.exists() and out.stat().st_mtime >= jpg.stat().st_mtime:
        return 0
    Image.open(jpg).save(out, format='WEBP', quality=35, method=5)
    return 1


def main():
    books = [Path(a).resolve() for a in sys.argv[1:]] or sorted(d for d in SITE.glob('book*') if (d / 'img/pages').is_dir())
    for book in books:
        pages = sorted((book / 'img/pages').glob('*.jpg'))
        with ProcessPoolExecutor(4) as ex:
            made = sum(ex.map(one, pages, chunksize=8))
        size = sum(p.with_suffix('.webp').stat().st_size for p in pages)
        print(f'{book.name}: {len(pages)} pages, {made} written, {size / 1e6:.0f} MB')


if __name__ == '__main__':
    main()
