"""Apply a Lithuanian correction pass (lt-fix workflow journal) to a translations file.

Usage: SAMOGITIA_BOOK=data/<book> .venv/bin/python -I pipeline/merge_lt_fix.py TRANSLATIONS.json REVISION JOURNAL.jsonl [JOURNAL2.jsonl ...]
TRANSLATIONS.json is relative to processed/translations/. For every returned entry the three
Lithuanian fields and issues_lt are replaced. parents_en is replaced only where the pass returned
a non-empty parents_en (it does so only when the family surname changed to the margin reading);
the previous English is kept in parents_en_before. Later journals override earlier ones (re-runs
of short chunks). Entries the pass did not return keep their text and are counted. The previous
file is kept once as <name>.before_<REVISION>.json.
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')


def main():
    name, revision, journals = sys.argv[1], sys.argv[2], sys.argv[3:]
    path = BOOK / 'processed/translations' / name
    data = json.loads(path.read_text())
    index = {t['row_id']: t for t in data}
    got, unknown = {}, []
    for j in journals:
        labels = {}
        for line in Path(j).read_text().splitlines():
            e = json.loads(line)
            if e.get('type') == 'started':
                labels[e['key']] = e['label']
            elif e.get('type') == 'result' and isinstance(e.get('result'), dict) and 'entries' in e['result']:
                for x in e['result']['entries']:
                    if x.get('row_id') in index:
                        got[x['row_id']] = (x, labels.get(e['key'], '?'))
                    else:
                        unknown.append(x.get('row_id'))
    updated = en_changed = 0
    for rid, (x, label) in got.items():
        t = index[rid]
        if not any(x.get(k) for k in ('baptism_lt', 'parents_lt', 'godparents_lt')):
            continue
        for k in ('baptism_lt', 'parents_lt', 'godparents_lt', 'issues_lt'):
            t[k] = x.get(k, '')
        if (x.get('parents_en') or '').strip() and x['parents_en'].strip() != (t.get('parents_en') or '').strip():
            t.setdefault('parents_en_before', t.get('parents_en', ''))
            t['parents_en'] = x['parents_en'].strip()
            en_changed += 1
        if x.get('surname_note'):
            t['surname_note'] = x['surname_note']
        t['lt_revision'] = f'{revision} ({label})'
        updated += 1
    backup = path.with_name(f'{path.stem}.before_{revision}.json')
    if not backup.exists():
        shutil.copy(path, backup)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(json.dumps({'entries': len(data), 'lithuanian_updated': updated, 'english_parents_changed': en_changed,
                      'not_updated': len(data) - updated, 'unknown_ids': unknown[:10]}))


if __name__ == '__main__':
    main()
