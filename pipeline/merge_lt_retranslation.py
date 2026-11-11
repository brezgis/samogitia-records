"""Replace only the Lithuanian fields of an existing translations file from a
retranslate-lithuanian workflow journal.

Usage: .venv/bin/python -I pipeline/merge_lt_retranslation.py JOURNAL.jsonl TRANSLATIONS.json

English fields are never touched. Entries missing from the journal keep their previous
Lithuanian (reported). The previous file is kept as <name>.before_lt_fix.json.
"""
import json
import shutil
import sys
from pathlib import Path


def main():
    journal, path = Path(sys.argv[1]), Path(sys.argv[2])
    data = json.loads(path.read_text())
    index = {t['row_id']: t for t in data}
    labels, updated, unknown = {}, 0, []
    for line in journal.read_text().splitlines():
        e = json.loads(line)
        if e.get('type') == 'started':
            labels[e['key']] = e['label']
        elif e.get('type') == 'result' and isinstance(e.get('result'), dict) and 'entries' in e['result']:
            for x in e['result']['entries']:
                t = index.get(x.get('row_id'))
                if t is None:
                    unknown.append(x.get('row_id'))
                    continue
                if not any(x.get(k) for k in ('baptism_lt', 'parents_lt', 'godparents_lt')):
                    continue
                for k in ('baptism_lt', 'parents_lt', 'godparents_lt', 'issues_lt'):
                    t[k] = x.get(k, '')
                t['lt_revision'] = f"glossary rev. 2026-11-11 ({labels.get(e['key'], '?')})"
                updated += 1
    shutil.copy(path, path.with_name(path.stem + '.before_lt_fix.json'))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(json.dumps({'entries': len(data), 'lithuanian_updated': updated,
                      'not_updated': len(data) - updated, 'unknown_ids': unknown[:10]}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
