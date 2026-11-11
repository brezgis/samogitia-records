"""Collect EN/LT translations from a translate-entries workflow journal.

Usage: .venv/bin/python -I pipeline/merge_translations.py JOURNAL.jsonl CHUNK_DIR OUT_NAME

CHUNK_DIR holds the chunk input files the translators read (chunk_*.json); each input
entry's draft text is stored beside its translation as `source_text`, so a later
redraft can detect stale translations. Writes processed/translations/OUT_NAME (under the
current SAMOGITIA_BOOK) and copies the chunk inputs to processed/translations/sources/.
Entries missing from a chunk's output are reported, not invented.
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')


def main():
    journal, chunk_dir, out_name = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    labels, results = {}, {}
    for line in journal.read_text().splitlines():
        e = json.loads(line)
        if e.get('type') == 'started':
            labels[e['key']] = e['label']
        elif e.get('type') == 'result' and isinstance(e.get('result'), dict) and 'entries' in e['result']:
            results[labels.get(e['key'], '')] = e['result']['entries']
    sources = {}
    for f in sorted(chunk_dir.glob('chunk_*.json')):
        for x in json.loads(f.read_text()):
            sources[x['row_id']] = x
    out, missing, extra = {}, [], []
    for label, entries in results.items():
        for t in entries:
            rid = t.get('row_id')
            if rid not in sources:
                extra.append(rid)
                continue
            src = sources[rid]
            out[rid] = {**t, 'source_text': {k: src[k] for k in ('baptism', 'parents', 'godparents')},
                        'translated_by': f'Claude Sonnet ({label})'}
    missing = [r for r in sources if r not in out]
    dst = BOOK / 'processed/translations'
    (dst / 'sources').mkdir(parents=True, exist_ok=True)
    (dst / out_name).write_text(json.dumps(list(out.values()), ensure_ascii=False, indent=1))
    for f in chunk_dir.glob('chunk_*.json'):
        shutil.copy(f, dst / 'sources' / f'{Path(out_name).stem}_{f.name}')
    print(json.dumps({'translated': len(out), 'inputs': len(sources), 'missing': len(missing),
                      'missing_ids': missing[:20], 'unknown_ids': extra[:20]}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
