"""Pick entries of one book for a blind double-reading round and render numbered line sheets.

Usage: SAMOGITIA_BOOK=data/<book> .venv/bin/python -I pipeline/reading_sheets.py OUT_DIR [--train 22 --val 4 --test 4]

Entries are spread evenly over the book's scans within each split (splits are by spread, set
at line segmentation); entries that already have annotations are skipped. Writes
OUT_DIR/manifest.json ({row: {split, sheets, ids, cells}}) and prints workflow args
({"batches": [...]}) for register-double-reading-generic.js.
"""
import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', type=Path)
    ap.add_argument('--train', type=int, default=22)
    ap.add_argument('--val', type=int, default=4)
    ap.add_argument('--test', type=int, default=4)
    ap.add_argument('--min-lines', type=int, default=14)
    args = ap.parse_args()
    props = json.loads((BOOK / 'training/line_proposals_years_v2.json').read_text())
    done = {a['id'] for a in json.loads((BOOK / 'training/annotations.json').read_text())}
    rows = defaultdict(list)
    for p in props:
        rows[p['row_id']].append(p)
    by_split = defaultdict(list)
    for r, ls in rows.items():
        if len(ls) >= args.min_lines and not any(l['id'] in done for l in ls):
            by_split[ls[0]['split']].append(r)
    sel = {}
    for split, want in (('train', args.train), ('validation', args.val), ('test', args.test)):
        cands = sorted(by_split[split])
        step = max(1, len(cands) // max(1, want))
        sel[split] = cands[step // 2::step][:want]
    args.out.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=30)
    man = {}
    for split, rs in sel.items():
        for r in rs:
            L, sheets = rows[r], []
            for k in range(0, len(L), 8):
                ims = []
                for x in L[k:k + 8]:
                    i = Image.open(ROOT / x['image']).convert('L')
                    ims.append(i.resize((int(i.width * 1.8), int(i.height * 1.8)), Image.LANCZOS))
                s = Image.new('L', (max(i.width for i in ims) + 60, sum(i.height + 6 for i in ims)), 255)
                d, y = ImageDraw.Draw(s), 0
                for n, i in enumerate(ims):
                    d.text((4, y + i.height // 2 - 15), str(k + n), font=font, fill=0)
                    s.paste(i, (60, y))
                    y += i.height + 6
                f = args.out / f'{r}_{k // 8}.jpg'
                s.save(f, quality=88)
                sheets.append(str(f))
            man[r] = {'split': split, 'sheets': sheets, 'ids': [x['id'] for x in L], 'cells': [x['cell'] for x in L]}
    (args.out / 'manifest.json').write_text(json.dumps(man, indent=1))
    batches = []
    for split, rs in sel.items():
        for i in range(0, len(rs), 3):
            chunk = rs[i:i + 3]
            if batches and len(chunk) == 1 and batches[-1]['name'].startswith(split):
                batches[-1]['rows'] += chunk
            else:
                batches.append({'name': f'{split}-{i // 3 + 1}', 'rows': chunk})
    print(json.dumps({'entries': len(man), 'lines': sum(len(m['ids']) for m in man.values()), 'batches': batches}))


if __name__ == '__main__':
    main()
