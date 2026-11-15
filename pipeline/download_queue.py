"""Work through a queue of register books, downloading their scans one after another.

Usage: python3 -I pipeline/download_queue.py QUEUE.json [--min-free-gb 45] [--pause 1.0]
QUEUE.json: [{"id": archive id, "dir": "data/<book>", "title": ...}, ...] in the order wanted
(build it with --build, below). Each book is fetched like download_book.py does (record.json,
page_urls.txt, pages/NNNN.jpg), one request at a time with a pause; finished pages are skipped, so
the queue can be stopped and restarted. Before every book the free space on the drive holding
data/ is checked, and the queue stops (exit 0) when less than --min-free-gb is left.
Progress: QUEUE.status.json beside the queue ({id: {state, pages, got, bytes}}) and stdout
(the journal when run as the user service samogitia-download.service).

  python3 -I pipeline/download_queue.py --build QUEUE.json "Plungės RKB=plunge" "Salantų RKB=salantai" ...
asks the archive's search for each parish's books and queues the birth registers ("gimimo metrikų")
whose years overlap 1849-1915 and that are not in data/ yet, in the order the parishes are given.
"""
import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_book import UA, fetch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def build(queue, parishes):
    have = {json.loads(p.read_text()).get('id') for p in ROOT.glob('data/*/record.json')}
    out = []
    for spec in parishes:
        term, slug = spec.split('=')
        items, page = [], 0
        while True:
            body = json.dumps({'term': f'"{term}"', 'page': page, 'pageSize': 100, 'filters': {'providerFacets_str': ['ARCH']}}).encode()
            req = urllib.request.Request('https://www.epaveldas.lt/vepis-api/internal/find', body, {**UA, 'Content-Type': 'application/json'})
            d = json.loads(urllib.request.urlopen(req, timeout=90).read())
            items += d.get('items') or []
            page += 1
            if page >= (d.get('pagesCount') or 1):
                break
            time.sleep(1)
        picked = []
        for it in items:
            title = it.get('title') or ''
            years = [int(y) for y in re.findall(r'(?<!\d)(1[6-9]\d\d)(?!\d)', title.split('/')[-1])]
            if 'gimimo metrik' not in title or not years or it['id'] in have:
                continue
            if max(years) < 1849 or min(years) > 1915:
                continue
            picked.append({'id': it['id'], 'dir': f"data/{slug}-{re.sub(r'[^0-9A-Za-z]+', '-', it['id']).strip('-').lower()}",
                           'title': title, 'years': [min(years), max(years)]})
        picked.sort(key=lambda b: b['years'])
        print(term, len(items), 'records;', len(picked), 'birth registers queued')
        out += picked
        time.sleep(1)
    Path(queue).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(len(out), 'books ->', queue)


def main():
    if sys.argv[1] == '--build':
        return build(sys.argv[2], sys.argv[3:])
    qpath = Path(sys.argv[1])
    opt = lambda name, default: float(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
    min_free, pause = opt('--min-free-gb', 45), opt('--pause', 1.0)
    spath = qpath.with_suffix('.status.json')
    status = json.loads(spath.read_text()) if spath.exists() else {}
    for b in json.loads(qpath.read_text()):
        st = status.setdefault(b['id'], {})
        if st.get('state') in ('done', 'no_images'):
            continue
        free = shutil.disk_usage(ROOT / 'data').free / 1e9
        if free < min_free:
            print(f'stopping: {free:.0f} GB free, below the {min_free:.0f} GB floor', flush=True)
            break
        book = ROOT / b['dir']
        try:
            rec = json.loads(fetch('https://www.epaveldas.lt/vepis-api/internal/findById?id=' + urllib.parse.quote(b['id'], safe='')))
            urls = sorted(u for u in (rec.get('resourcesFull') or {}) if '/original/' in u)
            if not urls:
                st.update(state='no_images')
                print(b['id'], 'has no page images online', flush=True)
            else:
                (book / 'pages').mkdir(parents=True, exist_ok=True)
                (book / 'record.json').write_text(json.dumps(rec, ensure_ascii=False))
                (book / 'page_urls.txt').write_text('\n'.join(urls) + '\n')
                got = 0
                for i, u in enumerate(urls, 1):
                    dst = book / 'pages' / f'{i:04d}.jpg'
                    if not (dst.exists() and dst.stat().st_size > 50_000):
                        tmp = dst.with_suffix('.part')
                        tmp.write_bytes(fetch(u))
                        tmp.rename(dst)
                        got += 1
                        time.sleep(pause)
                st.update(state='done', pages=len(urls), got=got, bytes=sum(p.stat().st_size for p in (book / 'pages').glob('*.jpg')))
                print(b['id'], b['dir'], f"{len(urls)} pages, {st['bytes'] / 1e6:.0f} MB", flush=True)
        except Exception as exc:                     # leave it for the next run and go on
            if 'HTTP Error 404' in str(exc):         # catalogue-only record (scans not on epaveldas)
                st.update(state='no_images')
                spath.write_text(json.dumps(status, ensure_ascii=False, indent=1))
                print(b['id'], 'is not on epaveldas as scans (404)', flush=True)
                time.sleep(3)
                continue
            st.update(state='failed', error=str(exc)[:200])
            print(b['id'], 'failed:', exc, flush=True)
            time.sleep(60)
        spath.write_text(json.dumps(status, ensure_ascii=False, indent=1))
        time.sleep(5)
    done = [s for s in status.values() if s.get('state') == 'done']
    print(f"queue pass finished: {len(done)} books done, {sum(s.get('bytes', 0) for s in done) / 1e9:.1f} GB", flush=True)


if __name__ == '__main__':
    main()
