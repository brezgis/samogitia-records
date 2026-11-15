"""Small copies of every book's page images, for the opening riffle of the reading book.

Usage: nice -n 15 python3 site/make_thumbs.py [BOOK_DIR ...] [--force]
  e.g. nice -n 15 python3 site/make_thumbs.py                 # every site/book*/ folder
       nice -n 15 python3 site/make_thumbs.py book-1902-1907  # one book
For each site/<book>/img/pages/NNNN_L.jpg (and _R) it writes site/<book>/img/thumbs/NNNN_L.webp,
WIDTH pixels wide. A thumbnail that is newer than its page is left alone unless --force is given.
app.js (riffle) asks for img/thumbs/NNNN_S.webp by scan number; a leaf whose thumbnail is missing
or late is drawn as an empty ruled form, so a book without thumbnails still opens.
Needs Pillow with WebP. One process, on purpose: the machine is shared.
"""
import sys
from pathlib import Path

from PIL import Image

SITE = Path(__file__).resolve().parent
WIDTH, QUALITY = 300, 10       # about 20 KB a page: seen for half a second, in motion


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    force = '--force' in sys.argv
    books = [SITE / a for a in args] or sorted(d for d in SITE.glob('book*') if (d / 'img/pages').is_dir())
    for book in books:
        out = book / 'img/thumbs'
        out.mkdir(parents=True, exist_ok=True)
        made = 0
        pages = sorted((book / 'img/pages').glob('*.jpg'))
        for src in pages:
            dst = out / (src.stem + '.webp')
            if not force and dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
                continue
            with Image.open(src) as im:
                im.draft(im.mode, (WIDTH * 2, WIDTH * 4))        # decode the JPEG at reduced size: much less work
                h = round(im.height * WIDTH / im.width)
                im.convert('L').resize((WIDTH, h), Image.LANCZOS).save(dst, 'WEBP', quality=QUALITY, method=6)
            made += 1
        size = sum(f.stat().st_size for f in out.glob('*.webp'))
        print(f'{book.name}: {len(pages)} pages, {made} thumbnails written, folder {size / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
