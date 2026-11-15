"""Build the held-out line set used to compare local vision models with the trained recognizer.

Usage: python3 -I pipeline/local_models/build_reading_set.py OUT.json
Takes every image_checked line of the test split in each book (labels from the blind double
readings), attaches the newest recognizer prediction for it, and picks a few checked train-split
lines per book as worked examples for few-shot prompts.
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
YEARS = {'plunge-1827-1-18': '1849–1854', 'plunge-1827-1-20': '1854–1857', 'plunge-1827-1-22': '1867–1874',
         'plunge-1886-1890': '1886–1890', 'plunge-1827-1-24': '1896–1902', 'plunge-1827-1-25': '1902–1907',
         'rietavas-1828-1-7': '1877–1882'}


def main():
    rnd = random.Random(7)
    test, shots = [], {}
    for book, years in YEARS.items():
        T = ROOT / 'data' / book / 'training'
        ann = [a for a in json.loads((T / 'annotations.json').read_text()) if a['status'] == 'image_checked']
        pred = {p['id']: p['text'] for p in json.loads((sorted(T.glob('predictions/model-*'))[-1] / 'predictions.json').read_text())}
        for a in ann:
            if a['split'] == 'test':
                test.append({'id': f"{book}/{a['id']}", 'book': book, 'years': years, 'cell': a['cell'],
                             'image': a['image'], 'text': a['text'], 'htr': pred.get(a['id'], ''),
                             'blind_agree': (a.get('double_reading') or {}).get('adjudicated') is None})
        tr = [a for a in ann if a['split'] == 'train' and 12 <= len(a['text']) <= 45]
        shots[book] = [{'image': a['image'], 'text': a['text'], 'cell': a['cell']} for a in rnd.sample(tr, 4)]
    Path(sys.argv[1]).write_text(json.dumps({'lines': test, 'shots': shots}, ensure_ascii=False, indent=1))
    print(len(test), 'lines')


if __name__ == '__main__':
    main()
