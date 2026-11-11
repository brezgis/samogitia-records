"""Add Polish translations (pl-translation workflow journal) to a translations file.

Usage: SAMOGITIA_BOOK=data/<book> [LABEL_PREFIX=pl:b18-] .venv/bin/python -I pipeline/merge_pl.py TRANSLATIONS.json JOURNAL.jsonl [JOURNAL2.jsonl ...]
TRANSLATIONS.json is relative to processed/translations/. For every returned entry the fields
baptism_pl, parents_pl, godparents_pl, issues_pl, child_pl, surname_pl and names_pl are set
(names_pl keeps the recorded Cyrillic beside each Polish rendering). Nothing else is touched.
Later journals override earlier ones. Entries not returned are counted and left without Polish.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
FIELDS = ('baptism_pl', 'parents_pl', 'godparents_pl', 'issues_pl', 'child_pl', 'surname_pl', 'names_pl')


def main():
    name, journals = sys.argv[1], sys.argv[2:]
    path = BOOK / 'processed/translations' / name
    data = json.loads(path.read_text())
    index = {t['row_id']: t for t in data}
    prefix = os.environ.get('LABEL_PREFIX', '')
    got, unknown = {}, []
    for j in journals:
        labels = {}
        for line in Path(j).read_text().splitlines():
            e = json.loads(line)
            if e.get('type') == 'started':
                labels[e['key']] = e['label']
            elif e.get('type') == 'result' and isinstance(e.get('result'), dict) and 'entries' in e['result']:
                if prefix and not labels.get(e['key'], '').startswith(prefix):
                    continue
                for x in e['result']['entries']:
                    if x.get('row_id') in index:
                        got[x['row_id']] = (x, labels.get(e['key'], '?'))
                    else:
                        unknown.append(x.get('row_id'))
    n = 0
    for rid, (x, label) in got.items():
        if not any(x.get(k) for k in ('baptism_pl', 'parents_pl', 'godparents_pl')):
            continue
        t = index[rid]
        for k in FIELDS:
            t[k] = x.get(k, [] if k == 'names_pl' else '')
        t['pl_translated_by'] = f'Claude Opus ({label}), docs/PL_GLOSSARY.md'
        n += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(json.dumps({'entries': len(data), 'polish_set': n, 'without_polish': len(data) - n, 'unknown_ids': unknown[:10]}))


if __name__ == '__main__':
    main()
