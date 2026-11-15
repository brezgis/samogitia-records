"""Have a local vision model read side-column strips and compare with the agents' readings.

Usage: SAMOGITIA_BOOK=data/<book> python3 -I pipeline/local_models/run_side.py STRIP_DIR OUT.json --port 8771 [--limit N]
STRIP_DIR comes from side_strips.py with SIDE_PER_SHEET=1 (one entry per image). The reference is
processed/side_columns.json (single agent reading, unverified), so the figures are agreement rates.
"""
import argparse
import base64
import json
import os
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
PROMPT = """This image shows the narrow side columns of ONE entry of a 19th-century Catholic baptism register (Plungė parish, Lithuania; Russian, pre-1918 spelling, clerk's cursive). The same strip of the page is shown three times:
- TOP: rotated 90° one way, and BELOW IT rotated 90° the other way. Exactly one of these two shows the sideways writing right side up: use it to read the family surname written in the margin (Cyrillic, often a genitive plural such as "Лайвіовъ") and any later notes written sideways (often Lithuanian, 1910s–1940s, Latin alphabet).
- BOTTOM: the strip upright: the entry number, then the day of birth and the day of baptism in two narrow columns; the sex letter М or Ж may stand below the number.
Bits of neighbouring entries can appear at the very top or bottom; read only this entry.
Answer with JSON: margin_surname (exactly as written, Cyrillic, "" if none), entry_no, birth_day, baptism_day (digits as written, "" if absent or unreadable), sex_letter ("М", "Ж" or ""), notes (any other writing, transcribed exactly, "" if none). Never guess."""
KEYS = ('margin_surname', 'entry_no', 'birth_day', 'baptism_day', 'sex_letter', 'notes')
SCHEMA = {'type': 'object', 'properties': {k: {'type': 'string'} for k in KEYS}, 'required': list(KEYS)}


def dist(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--port', type=int, default=8771)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--every', type=int, default=1)
    args = ap.parse_args()
    ref = json.loads((BOOK / 'processed/side_columns.json').read_text())
    sheets = list(json.loads((args.dir / 'manifest.json').read_text())['sheets'].items())[::args.every][:args.limit]
    done = {r['row_id']: r for r in json.loads(args.out.read_text())} if args.out.exists() else {}
    for sheet, (row,) in sheets:
        if row in done or row not in ref:
            continue
        url = 'data:image/jpeg;base64,' + base64.b64encode((args.dir / sheet).read_bytes()).decode()
        body = {'messages': [{'role': 'user', 'content': [{'type': 'image_url', 'image_url': {'url': url}}, {'type': 'text', 'text': PROMPT}]}],
                'temperature': 0, 'max_tokens': 400, 'chat_template_kwargs': {'enable_thinking': False},
                'response_format': {'type': 'json_schema', 'json_schema': {'name': 'side', 'schema': SCHEMA}}}
        t = time.time()
        m = json.loads(urllib.request.urlopen(urllib.request.Request(
            f'http://127.0.0.1:{args.port}/v1/chat/completions', json.dumps(body).encode(), {'Content-Type': 'application/json'}), timeout=600).read())
        try:
            o = json.loads(m['choices'][0]['message']['content'])
        except ValueError:
            o = {}
        done[row] = {'row_id': row, **{k: str(o.get(k, '')) for k in KEYS}, 'seconds': round(time.time() - t, 1)}
        args.out.write_text(json.dumps(list(done.values()), ensure_ascii=False, indent=1))
    clean = lambda s: re.sub(r'[\[\]?\s]', '', s or '')
    rows = [r for r in done.values() if r['row_id'] in ref]
    n = len(rows)
    for k in ('entry_no', 'birth_day', 'baptism_day'):
        print(f"{k:12s} same as agent: {sum(clean(r[k]) == clean(ref[r['row_id']].get(k)) for r in rows)}/{n}")
    sx = [(r, ref[r['row_id']]) for r in rows if ref[r['row_id']].get('sex_letter')]
    print(f"sex_letter   same as agent: {sum(r['sex_letter'] == a['sex_letter'] for r, a in sx)}/{len(sx)}")
    sn = [(clean(r['margin_surname']), clean(ref[r['row_id']].get('margin_surname'))) for r in rows if clean(ref[r['row_id']].get('margin_surname'))]
    print(f"surname      identical: {sum(a == b for a, b in sn)}/{len(sn)}; within one letter: {sum(dist(a, b) <= 1 for a, b in sn)}; "
          f"character difference {100 * sum(dist(a, b) for a, b in sn) / sum(len(b) for a, b in sn):.0f}%")
    nt = [(r, ref[r['row_id']]) for r in rows if ref[r['row_id']].get('notes_ru')]
    print(f"later notes  agent has one in {len(nt)}; model gave one in {sum(bool(r['notes']) for r, a in nt)} of those, and in "
          f"{sum(bool(r['notes']) for r in rows if not ref[r['row_id']].get('notes_ru'))} entries where the agent had none")
    print(f"{sum(r['seconds'] for r in rows) / max(1, n):.1f} s per entry")
    for r in rows[:12]:
        a = ref[r['row_id']]
        print(' ', r['row_id'], '|', a.get('margin_surname'), a.get('entry_no'), a.get('birth_day'), a.get('baptism_day'), '|', r['margin_surname'], r['entry_no'], r['birth_day'], r['baptism_day'], '|', r['notes'][:60])


if __name__ == '__main__':
    main()
