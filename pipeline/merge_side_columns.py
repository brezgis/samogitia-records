"""Collect side-column readings (printed columns 1-3) from a read-side-columns workflow journal.

Usage: .venv/bin/python -I pipeline/merge_side_columns.py JOURNAL.jsonl [OUT_NAME]

Writes processed/side_columns.json (under SAMOGITIA_BOOK): {row_id: {margin_surname,
margin_en, margin_lt, entry_no, sex_letter, sex, birth_day, baptism_day, notes_ru, notes_en,
notes_lt, uncertain, read_by}}. Single Sonnet reading per entry: unverified. Later
re-reads (same row_id) override earlier ones when merged in order.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')


def main():
    journal = Path(sys.argv[1])
    out_name = sys.argv[2] if len(sys.argv) > 2 else 'side_columns.json'
    dst = BOOK / 'processed' / out_name
    data = json.loads(dst.read_text()) if dst.exists() else {}
    labels, n = {}, 0
    for line in journal.read_text().splitlines():
        e = json.loads(line)
        if e.get('type') == 'started':
            labels[e['key']] = e['label']
        elif e.get('type') == 'result' and isinstance(e.get('result'), dict) and 'entries' in e['result']:
            for x in e['result']['entries']:
                rid = x.pop('row_id', None)
                if rid:
                    data[rid] = {**x, 'read_by': f"Claude Sonnet ({labels.get(e['key'], '?')}), single reading, unverified"}
                    n += 1
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    filled = {k: sum(1 for v in data.values() if v.get(k)) for k in ('margin_surname', 'entry_no', 'birth_day', 'baptism_day', 'notes_ru')}
    print(json.dumps({'merged_now': n, 'total_rows': len(data), 'filled': filled}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
