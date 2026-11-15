"""Character error rate of reading runs against the checked labels, per book, beside the recognizer.

Usage: python3 -I pipeline/local_models/score_reading.py SET.json RUN.json [RUN.json ...]
Only lines present in a run are scored for it (the recognizer column covers the same lines).
"""
import json
import sys
from collections import Counter
from pathlib import Path


def dist(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def main():
    lines = {l['id']: l for l in json.loads(Path(sys.argv[1]).read_text())['lines']}
    for f in sys.argv[2:]:
        run = json.loads(Path(f).read_text())
        e, h, n, c, ex, hx, better, worse = Counter(), Counter(), Counter(), Counter(), Counter(), Counter(), 0, 0
        for r in run:
            l = lines[r['id']]
            for k in (l['book'], 'ALL'):
                a, b = dist(l['text'], r['text']), dist(l['text'], l['htr'])
                e[k] += a; h[k] += b; n[k] += len(l['text']); c[k] += 1
                ex[k] += r['text'] == l['text']; hx[k] += l['htr'] == l['text']
            better += a < b; worse += a > b
        print(f"\n{Path(f).stem}: {c['ALL']} lines, {sum(r['seconds'] for r in run) / len(run):.1f} s/line; "
              f"better than recognizer on {better}, worse on {worse}")
        for k in n:
            print(f"  {k:20s} n={c[k]:3d}  model CER {100 * e[k] / n[k]:5.1f}%  exact {100 * ex[k] / c[k]:3.0f}%   |"
                  f"  recognizer CER {100 * h[k] / n[k]:5.1f}%  exact {100 * hx[k] / c[k]:3.0f}%")


if __name__ == '__main__':
    main()
