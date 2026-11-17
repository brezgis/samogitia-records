"""The character field tagger as a pipeline step: tag the three columns of each entry of a draft.

Usage (HTR environment; uses the GPU when one is free, else the CPU, where a book takes seconds):
  .venv-htr/bin/python pipeline/neural_parser/apply.py data/<book>/processed/year_draft_<year>_<model>.json
      [--model WEIGHTS.pt] [--out FILE] [--cpu]
Writes `tagger_spans_<year>_<model>.json` beside the draft (or --out). `parse_entries.py --tagger`
reads that file and combines the spans with the rule parser (`combine.py`); nothing else reads it.

From Python:
  from apply import tag_entries
  spans = tag_entries(entries)          # entries: dicts with 'baptism', 'parents', 'godparents'
  spans[i]['parents']['FATHER'] -> {'s': 34, 'e': 41, 'text': 'Іосифа', 'conf': 0.97}
The model is loaded once per process and path. `conf` is the mean, over the characters of the span,
of the probability the model gave to the span's own tag (1.0 = sure of every character).

Weights: --model, else $FIELD_TAGGER_MODEL, else the stable copy
/mnt/ssd240gb/anna/samogitia-htr/models/field-tagger-v1/char__none__s1.pt (trained on all five
translated Plungė books, see RESULTS.md and the README beside the weights).

Spans file: {"draft", "model", "model_md5", "fields", "entries": [{"row_id", "hash": {column: md5 of
the column text}, "spans": [{"col", "field", "s", "e", "text", "conf"}]}]}. Spans are character
offsets into the column text, so the hash lets the reader refuse spans of a draft that has since
been re-assembled.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import torch

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import ALL_FIELDS, COLS  # noqa: E402
from train_tagger import CharTagger, decode  # noqa: E402

STABLE = Path('/mnt/ssd240gb/anna/samogitia-htr/models/field-tagger-v1/char__none__s1.pt')
_LOADED = {}


def default_model():
    return Path(os.environ.get('FIELD_TAGGER_MODEL') or STABLE)


def text_hash(s):
    return hashlib.md5((s or '').encode()).hexdigest()[:12]


def load(model_path=None, device=None):
    """(model, vocab, fields, device), cached per path and device."""
    path = Path(model_path or default_model())
    device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
    key = (str(path), device)
    if key not in _LOADED:
        ck = torch.load(path, map_location='cpu')
        model = CharTagger(len(ck['vocab']) + 2, len(ck['fields']) + 1)
        model.load_state_dict(ck['state'])
        try:
            model.to(device)
        except RuntimeError:            # the shared GPU is full: the model is small enough for the CPU
            device = 'cpu'
            model.to(device)
        model.eval()
        _LOADED[key] = (model, ck['vocab'], ck['fields'], device)
    return _LOADED[key]


def columns_of(entry):
    t = entry.get('text') if isinstance(entry.get('text'), dict) else entry
    return {c: t.get(c) or '' for c in COLS}


def tag_entries(entries, model_path=None, device=None, batch=128):
    """Per entry, {column: {FIELD: {'s', 'e', 'text', 'conf'}}} (same order as `entries`)."""
    model, vocab, fields, device = load(model_path, device)
    assert fields == ALL_FIELDS, 'the weights were trained for another tag set'
    items = [(i, ci, columns_of(e)[c]) for i, e in enumerate(entries) for ci, c in enumerate(COLS)]
    items = sorted((x for x in items if x[2]), key=lambda x: len(x[2]))
    out = [{c: {} for c in COLS} for _ in entries]
    with torch.no_grad():
        for k in range(0, len(items), batch):
            part = items[k:k + batch]
            L = max(len(t) for _, _, t in part)
            x = torch.zeros(len(part), L, dtype=torch.long)
            for b, (_, _, t) in enumerate(part):
                x[b, :len(t)] = torch.tensor([vocab.get(ch, 1) for ch in t])
            cols = torch.tensor([ci for _, ci, _ in part])
            lens = torch.tensor([len(t) for _, _, t in part])
            try:
                logits = model(x.to(device), cols.to(device), lens)
            except RuntimeError:        # out of GPU memory beside the other job
                if device == 'cpu':
                    raise
                model.to('cpu')
                _LOADED[(str(Path(model_path or default_model())), 'cpu')] = (model, vocab, fields, 'cpu')
                device = 'cpu'
                logits = model(x, cols, lens)
            prob = torch.softmax(logits.float(), -1).cpu()
            tags = prob.argmax(-1)
            for b, (i, ci, t) in enumerate(part):
                for f, (s, e) in decode(t, tags[b, :len(t)].tolist()).items():
                    conf = prob[b, s:e, ALL_FIELDS.index(f) + 1].mean().item()
                    out[i][COLS[ci]][f] = {'s': s, 'e': e, 'text': t[s:e], 'conf': round(conf, 4)}
    return out


def spans_path(draft_path):
    p = Path(draft_path)
    return p.with_name('tagger_spans_' + p.stem.replace('year_draft_', '') + '.json')


def main():
    args = sys.argv[1:]
    opt = lambda name: args[args.index(name) + 1] if name in args else None
    src = Path(args[0])
    model_path = Path(opt('--model') or default_model())
    draft = json.loads(src.read_text())
    entries = draft['entries']
    spans = tag_entries(entries, model_path, 'cpu' if '--cpu' in args else None)
    dst = Path(opt('--out') or spans_path(src))
    rows = []
    for e, sp in zip(entries, spans):
        t = columns_of(e)
        rows.append({'row_id': e.get('row_id'), 'hash': {c: text_hash(t[c]) for c in COLS},
                     'spans': [{'col': c, 'field': f, **v} for c in COLS for f, v in sp[c].items()]})
    dst.write_text(json.dumps({'draft': str(src), 'model': str(model_path),
                               'model_md5': hashlib.md5(model_path.read_bytes()).hexdigest(),
                               'fields': ALL_FIELDS, 'entries': rows}, ensure_ascii=False, indent=1))
    print(json.dumps({'entries': len(rows), 'spans': sum(len(r['spans']) for r in rows),
                      'device': load(model_path, 'cpu' if '--cpu' in args else None)[3], 'out': str(dst)}))


if __name__ == '__main__':
    main()
