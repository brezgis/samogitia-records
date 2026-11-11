"""Build the static review site (site/review/) from machine-extracted entries.

Usage: .venv/bin/python -I pipeline/build_review_site.py processed/entries_<...>.json [more years ...]

Writes site/review/data.json and links rows/ and pages/ to the scans. Serve locally, e.g.
  python3 -m http.server 8741 --bind 100.107.252.39 --directory site/review
The page shows machine drafts: every value is unverified unless marked "checked".
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
SITE = ROOT / 'site/review'
MONTHS = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def main():
    srcs = []
    for a in sys.argv[1:]:
        s = Path(a)
        srcs.append(s if s.is_absolute() else (ROOT / s if (ROOT / s).exists() else BOOK / s))
    ann = json.loads((BOOK / 'training/annotations.json').read_text())
    checked_rows = {}
    for a in ann:
        if a['status'] in ('image_checked', 'independently_checked') and a.get('row_id'):
            checked_rows[a['row_id']] = checked_rows.get(a['row_id'], 0) + 1
    # consolidated translations file(s); later files override earlier ones per row
    tr = {}
    for part in sorted((BOOK / 'processed/translations').glob('translations_*.json')):
        for x in json.loads(part.read_text()):
            tr[x['row_id']] = {k: x.get(k) for k in ('baptism_en', 'parents_en', 'godparents_en', 'names', 'issues',
                                                     'baptism_lt', 'parents_lt', 'godparents_lt', 'names_lt', 'issues_lt')}
    side_path = BOOK / 'processed/side_columns.json'
    side = json.loads(side_path.read_text()) if side_path.exists() else {}
    entries, sources = [], []
    for src in srcs:
        data = json.loads(src.read_text())
        sources.append(data['source'])
        dpath = BOOK / ('processed/year_draft_' + src.stem.replace('entries_', '') + '.json')
        drafts = {x['row_id']: x for x in json.loads(dpath.read_text())['entries']} if dpath.exists() else {}
        for e in data['entries']:
            f = dict(e['fields'])
            bm = (f.get('baptism_month') or {}).get('value')
            img_row = e.get('split_from') or e['row_id']
            entries.append({'row': e['row_id'], 'year': e.get('register_year') or 1888, 'scan': e['scan'],
                            'n': e.get('expected_entry_no'), 'hand': e.get('hand_group'), 'split': e.get('split'),
                            'month': MONTHS[bm] if bm else '', 'img': f"rows/{img_row}.jpg",
                            'page': f"pages/{e['scan']:04d}.jpg", 'checked_lines': checked_rows.get(e['row_id'], 0),
                            'fields': f, 'text': e['text'], 'en': tr.get(e['row_id']),
                            'warning': drafts.get(e['row_id'], {}).get('boundary_warning'),
                            'split_from': e.get('split_from'), 'side': side.get(e['row_id'])})
    entries.sort(key=lambda x: (x['year'], x['scan'], x['row']))
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / 'data.json').write_text(json.dumps({'sources': sources, 'entries': entries}, ensure_ascii=False))
    for name, target in (('rows', BOOK / 'processed/rows'), ('pages', BOOK / 'pages')):
        link = SITE / name
        if not link.exists():
            os.symlink(os.path.relpath(target, SITE), link)
    years = sorted({e['year'] for e in entries})
    print(json.dumps({'entries': len(entries), 'years': years, 'translated': sum(1 for e in entries if e['en']),
                      'site': str(SITE.relative_to(ROOT))}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
