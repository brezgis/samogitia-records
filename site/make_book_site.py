"""Create (or refresh) the reading GUI for another register book from site/book.

Usage: python3 site/make_book_site.py FIRST_YEAR LAST_YEAR ARCHIVE_FILE START_SCAN
  e.g. python3 site/make_book_site.py 1891 1895 1827/1/25 10
Copies site/book's index.html, app.js, vendor/ and textiles into site/book-FIRST-LAST and adapts
years, citation, search year patterns and the default ribbon position. Data is built separately:
  SAMOGITIA_BOOK=data/<book> BOOK_OUT=site/book-FIRST-LAST BOOK_MODEL=<model> \
  BOOK_YEARS=FIRST-LAST BOOK_TRANSLATIONS=translations/<file>.json \
  .venv/bin/python -I site/book/build_book.py --images
"""
import re
import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent


def main():
    y0, y1, archive, scan = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    out = SITE / f'book-{y0}-{y1}'
    (out / 'img').mkdir(parents=True, exist_ok=True)
    for f in ('index.html',):
        shutil.copy(SITE / 'book' / f, out / f)
    shutil.copytree(SITE / 'book/vendor', out / 'vendor', dirs_exist_ok=True)
    shutil.copytree(SITE / 'book/img/src', out / 'img/src', dirs_exist_ok=True)
    for f in (SITE / 'book/img').glob('cloth-*.jpg'):
        shutil.copy(f, out / 'img' / f.name)
    for f in (SITE / 'book/img').glob('ribbon-*.webp'):
        shutil.copy(f, out / 'img' / f.name)
    t = (SITE / 'book/app.js').read_text()
    mid = (y0 + y1) // 2
    dash, en_to = f'{y0}–{y1}', f'{y0} to {y1}'
    reps = [
        ('for 1886 to 1890', f'for {en_to}'), ('1886–1890 m.', f'{dash} m.'), ('за 1886–1890 годы', f'за {dash} годы'),
        ('In 1888 Plungė lay', 'In these years Plungė lay'), ('1888 m. Plungė priklausė', 'Šiais metais Plungė priklausė'),
        ('В 1888 году Плунге входило', 'В эти годы Плунге входило'), ('W 1888 roku Płungiany leżały', 'W tych latach Płungiany leżały'),
        ('births and baptisms 1886–1890', f'births and baptisms {dash}'), ('1827/1/23', archive),
        ('за 1886–1890 гг.', f'за {dash} гг.'), ('1886 to 1890', en_to), ('1886–1890', dash),
        ('“10 January 1888”, “03.1887”', f'“10 January {mid}”, “03.{mid - 1}”'),
        ('„1888 sausio 10“, „03.1887“', f'„{mid} sausio 10“, „03.{mid - 1}“'),
        ('«10 января 1888», «03.1887»', f'«10 января {mid}», «03.{mid - 1}»'),
        ('„10 stycznia 1888”, „03.1887”', f'„10 stycznia {mid}”, „03.{mid - 1}”'),
        ("{ row: '0093_R3', scan: 93 }", f"{{ row: '', scan: {scan} }}"), ("|| 93, params.get('pick')", f"|| {scan}, params.get('pick')"),
        ('w.y || 1888', f'w.y || {mid}'),
        ('(18[89]\\d)', '(1[789]\\d\\d)'), ('/^18(8[6-9]|90)$/', f'/^({"|".join(str(y) for y in range(y0, y1 + 1))})$/'),
    ]
    for a, b in reps:
        t = t.replace(a, b)
    t = re.sub(r"(sub: ')[^']*January 1888(')", rf"\1Parish registers of Samogitia. Plungė, baptisms, {dash}\2", t)
    (out / 'app.js').write_text(t)
    print(out)


if __name__ == '__main__':
    main()
