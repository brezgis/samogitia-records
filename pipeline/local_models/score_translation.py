"""Compare local-model translations with the current (agent) translations of the comparison set.

Usage: python3 -I pipeline/local_models/score_translation.py SET.json RUN.json [RUN.json ...]
Agreement with the reference, not accuracy: dates (all numbers in the Lithuanian / Polish baptism and
parents sentences), the margin surname's stem appearing in the parents sentence, text similarity
(difflib ratio), and how often the sentence is identical once names are ignored is left to reading.
"""
import difflib
import json
import re
import sys
from pathlib import Path

F = ('baptism', 'parents', 'godparents')


def main():
    ref = {x['id']: x for x in json.loads(Path(sys.argv[1]).read_text())}
    for f in sys.argv[2:]:
        run = json.loads(Path(f).read_text())
        print(f'\n{Path(f).stem}')
        for lang in ('en', 'lt', 'pl'):
            rows = [(ref[o['id']]['reference'], o) for o in run if f'baptism_{lang}' in o and f'baptism_{lang}' in ref[o['id']]['reference']]
            if not rows:
                continue
            sim = {c: sum(difflib.SequenceMatcher(None, r[f'{c}_{lang}'], o[f'{c}_{lang}']).ratio() for r, o in rows) / len(rows) for c in F}
            line = f"  {lang}: {len(rows)} entries; similarity " + ', '.join(f'{c} {v:.2f}' for c, v in sim.items())
            if lang != 'en':
                num = lambda s: re.findall(r'\d+', s)
                line += (f"; same date in baptism {sum(num(r[f'baptism_{lang}']) == num(o[f'baptism_{lang}']) for r, o in rows)}/{len(rows)}, "
                         f"in parents {sum(num(r[f'parents_{lang}']) == num(o[f'parents_{lang}']) for r, o in rows)}/{len(rows)}")
                line += f"; identical sentence: " + ', '.join(f"{c} {sum(r[f'{c}_{lang}'] == o[f'{c}_{lang}'] for r, o in rows)}" for c in F)
            secs = [o['seconds'][lang] for r, o in rows if lang in o.get('seconds', {})]
            print(line + f"; {sum(secs) / len(secs):.1f} s/entry")


if __name__ == '__main__':
    main()
