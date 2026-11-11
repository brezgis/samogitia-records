"""Build an entry queue for the book's other years (scans outside the 1888 range).

Usage: .venv/bin/python -I pipeline/prepare_years.py [--scans 1-91 146-202]

The 1888 queue (processed/queue.json, built by prepare.py with hand-checked overrides)
is NOT touched. This writes processed/queue_years.json with one row per detected table
row on the given scans, using the automatic layout in layout/NNNN.json. The register
year is left null: it is inferred later from the drafted text (infer_years.py), never
assumed from scan position. Page sides where layout found no table (covers, inserted
decrees and amendments) are listed in processed/non_table_sides_years.json.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
# scans 92-145 of book 1827/1/23 are the hand-checked 1888 queue (prepare.py); other books have none
TARGET_1888 = range(92, 146) if str(BOOK).endswith('plunge-1886-1890') else range(0)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scan_ranges(specs):
    out = []
    for s in specs:
        a, _, b = s.partition('-')
        out += list(range(int(a), int(b or a) + 1))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--scans', nargs='+', default=['1-91', '146-202'])
    args = ap.parse_args()
    scans = [s for s in scan_ranges(args.scans) if s not in TARGET_1888]
    (BOOK / 'processed/rows').mkdir(parents=True, exist_ok=True)
    queue, empty = [], []
    for scan in scans:
        lp = BOOK / f'layout/{scan:04d}.json'
        if not lp.exists():
            empty.append({'scan': scan, 'reason': 'no layout file'})
            continue
        lay = json.loads(lp.read_text())
        source = BOOK / f'pages/{scan:04d}.jpg'
        image = Image.open(source)
        w, h = image.size
        sha = digest(source)
        for pg in lay['pages']:
            rows = pg.get('rows', [])
            if not rows:
                empty.append({'page_id': f"{scan:04d}_{pg['page']}", 'reason': 'no table rows detected',
                              'note': 'cover, inserted decree/amendment, blank, or layout failure: check by eye'})
                continue
            for i, r in enumerate(rows, 1):
                row_id = f"{scan:04d}_{pg['page']}{i}"
                x0, x1 = (0, w // 2) if pg['page'] == 'L' else (w // 2, w)
                bbox = [x0, max(0, r['y0'] - 70), x1, min(h, r['y1'] + 150)]
                target = BOOK / f'processed/rows/{row_id}.jpg'
                image.crop(tuple(bbox)).save(target, quality=92)
                queue.append({'row_id': row_id, 'scan': scan, 'page': pg['page'], 'row_index': i,
                              'kind': 'baptism', 'register_year': None, 'register_year_status': 'not_inferred',
                              'entry_no': None, 'entry_no_status': 'not_read',
                              'image': str(target.relative_to(ROOT)), 'source': str(source.relative_to(ROOT)),
                              'source_sha256': sha, 'image_sha256': digest(target), 'bbox': bbox,
                              'focal_y': [r['y0'], r['y1']], 'layout_status': 'automatic_unreviewed',
                              'in_target_year': False, 'transcription_status': 'pending',
                              'hand_group': 'unknown', 'hand_group_status': 'not_assigned'})
    (BOOK / 'processed/queue_years.json').write_text(json.dumps(queue, ensure_ascii=False, indent=1))
    (BOOK / 'processed/non_table_sides_years.json').write_text(json.dumps(empty, indent=1))
    print(json.dumps({'scans': len(scans), 'rows': len(queue), 'non_table_sides': len(empty)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
