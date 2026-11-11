"""Crop the register's side columns for every entry into numbered reading sheets.

Usage: .venv/bin/python -I pipeline/side_strips.py OUT_DIR processed/year_draft_<...>.json [...]

Printed columns 1-3 of the form: (1) "Прозваніе крещаемыхъ", the family surname written
sideways in the margin; (2) "№", entry number (often with the sex letter М/Ж below it);
(3) "Число рожденія / крещенія", day of birth and day of baptism. For each entry this
writes one block: the margin column rotated to read left-to-right, and the number/date
columns upright, both cut from the original scan between this entry's top boundary and
the next entry's on the same page side. Blocks are packed six to a sheet;
OUT_DIR/manifest.json maps sheet -> [row_id per block]. Reading is done separately.
"""
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
PER_SHEET = int(os.environ.get('SIDE_PER_SHEET', '4'))
WIDE = os.environ.get('SIDE_MODE') == 'wide'   # see crop below
BLOCK_W = 1100


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for f in sys.argv[2:]:
        p = Path(f)
        p = p if p.is_absolute() else (ROOT / p if (ROOT / p).exists() else BOOK / p)
        entries += json.loads(p.read_text())['entries']
    side = defaultdict(list)
    for e in entries:
        side[(e['scan'], e['page'])].append(e)
    font = ImageFont.load_default(size=34)
    blocks, skipped = [], []
    cache = {}
    # typical left-column positions per page side (relative to the side's left edge), used
    # where a page's own column detection failed
    typical = defaultdict(list)
    for f in sorted((BOOK / 'layout').glob('*.json')):
        lay = json.loads(f.read_text())
        for pg in lay['pages']:
            c = sorted(pg.get('cols') or [])
            if len(c) >= 5:
                off = 0 if pg['page'] == 'L' else c[0] - (c[0] % 1)  # absolute; normalise below
                typical[pg['page']].append(c[:5])
    med = {k: [sorted(v[i] for v in vs)[len(vs) // 2] for i in range(5)] for k, vs in typical.items() if vs}
    for (scan, page), es in sorted(side.items()):
        lay = json.loads((BOOK / f'layout/{scan:04d}.json').read_text())
        pg = next(x for x in lay['pages'] if x['page'] == page)
        cols = sorted(pg.get('cols') or [])
        es = sorted(es, key=lambda e: e['focal_y'][0])
        estimated = False
        if len(cols) < 5:
            if page not in med:
                skipped += [{'row_id': e['row_id'], 'reason': 'columns not detected'} for e in es]
                continue
            cols, estimated = med[page], True
        if scan not in cache:
            cache = {scan: Image.open(BOOK / f'pages/{scan:04d}.jpg').convert('L')}
        im = cache[scan]
        for i, e in enumerate(es):
            y0 = max(0, e['focal_y'][0] - 20)
            nxt = es[i + 1]['focal_y'][0] if i + 1 < len(es) else None
            y1 = min(x for x in (e['focal_y'][1] + 40, nxt + 10 if nxt else None) if x)
            if y1 - y0 < 120:
                y1 = y0 + 600
            if WIDE:
                # form-agnostic: everything from the side's outer edge to the first wide column
                # (the baptism text column); rotated copy for sideways writing, upright for numbers
                wide = [c for a, c in zip(cols, cols[1:]) if c - a > 450]
                bx = min(wide) - (min(wide) - max(x for x in cols if x < min(wide))) if wide else cols[4]
                bx = max(x for x in cols if x < min(wide)) if wide else cols[4]
                left = max(0, cols[0] - 40)
                strip = im.crop((left, y0, bx + 8, y1))
                # sideways writing runs either way depending on book/page: show both rotations
                r1, r2 = strip.rotate(90, expand=True), strip.rotate(-90, expand=True)
                margin = Image.new('L', (max(r1.width, r2.width), r1.height + r2.height + 12), 160)
                margin.paste(r1, (0, 0))
                margin.paste(r2, (0, r1.height + 12))
                nums = strip
            else:
                margin = im.crop((cols[0] - 10, y0, cols[1] + 6, y1)).rotate(90, expand=True)
                nums = im.crop((cols[1] - 6, y0, cols[4] + 8, y1))
            mscale = min(1.6, (BLOCK_W - 20) / margin.width)
            margin = margin.resize((int(margin.width * mscale), int(margin.height * mscale)))
            # number/date columns at native resolution (x1.4), long side capped at 900 px
            nscale = min(1.4, 900 / nums.height)
            nums = nums.resize((max(1, int(nums.width * nscale)), max(1, int(nums.height * nscale))))
            h = 60 + max(margin.height, 0) + 10 + nums.height
            blk = Image.new('L', (BLOCK_W, h), 255)
            d = ImageDraw.Draw(blk)
            blocks.append((e['row_id'] + (' (cols estimated)' if estimated else ''), blk, d))
            d.text((10, 10), '', font=font, fill=0)
            blk.paste(margin, (10, 60))
            blk.paste(nums, (10, 70 + margin.height))
    manifest = {}
    for k in range(0, len(blocks), PER_SHEET):
        chunk = blocks[k:k + PER_SHEET]
        H = sum(b.height + 16 for _, b, _ in chunk)
        sheet = Image.new('L', (BLOCK_W, H), 200)
        y, ids = 0, []
        for n, (rid, b, d) in enumerate(chunk):
            d.rectangle([0, 0, BLOCK_W, 52], fill=255)
            d.text((10, 8), f'[{n}]  {rid}', font=font, fill=0)
            sheet.paste(b, (0, y))
            y += b.height + 16
            ids.append(rid.split(' ')[0])
        name = f'side_{k // PER_SHEET:04d}.jpg'
        sheet.save(out / name, quality=85)
        manifest[name] = ids
    (out / 'manifest.json').write_text(json.dumps({'sheets': manifest, 'skipped': skipped}, indent=1))
    print(json.dumps({'entries': len(entries), 'blocks': len(blocks), 'sheets': len(manifest), 'skipped': len(skipped)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
