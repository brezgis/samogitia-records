"""Train a field tagger on the silver spans and write its predictions.

Usage:
  PY=.venv-htr/bin/python; LIBS=/mnt/ssd240gb/anna/samogitia-htr/neural-parser/pylibs
  nice $PY pipeline/neural_parser/train_tagger.py --model char --heldout plunge-1827-1-22 --seed 1
  PYTHONPATH=$LIBS HF_HUB_OFFLINE=1 nice $PY pipeline/neural_parser/train_tagger.py --model xlmr --heldout plunge-1827-1-24 --seed 1
  nice $PY pipeline/neural_parser/train_tagger.py --model char --heldout none --seed 1 --save
Options: --model char|xlmr|rubert; --heldout BOOK|none (none = train on all five translated books and
tag Salantai 1517/1/1 and Plungė 1827/1/20); --names-only (name fields trained on the agents' names
spans alone, no rule-made name spans); --no-aug; --epochs N (default 10 for char, 3 for the encoders, as in every reported run); --save (keep the weights).
Predictions: <scratch>/preds/<model>[_namesonly][_noaug]__<heldout>__s<seed>.jsonl

Models. Each of the three columns is tagged on its own.
  char  character embedding (64) + column embedding (8) -> 2-layer BiLSTM (2x192) -> softmax over
        {O, 14 fields} per character (IO tags: a field occurs once per column, so no B- tag is needed).
  xlmr / rubert  the pretrained encoder (subword embedding table frozen) with a linear head over subwords; a subword takes the tag most
        of its characters carry, and predictions are projected back to characters by offsets.
Decoding (both): runs of one tag; runs of the same tag at most 2 characters apart are joined; the
longest run per field is kept and trimmed of edge spaces and punctuation.
Unlabelled is not "O": inside a column, where a field has no silver span, the stretch between its
labelled neighbours (in the column's fixed field order) is left out of the loss; columns without any
span, or whose spans are out of order, are not trained on.
Noise augmentation (training only, 70% of sequences each epoch): 3% of letters replaced (from a table
of the recognizers' confusions counted on two draft versions of the TRAINING books only, else a random
letter), 1% deleted, 5% of spaces removed, a space inserted after 1% of letters.
No model selection: fixed epochs, nothing is chosen on the held-out book.
"""
import argparse
import difflib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import torch
import torch.nn as nn

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import ALL_FIELDS, COLS, FIELDS, NAME_FIELDS, ROOT, SCRATCH, TRANSLATED, UNLABELLED, load_drafts, trim  # noqa: E402

TAG = {f: i + 1 for i, f in enumerate(ALL_FIELDS)}
HF = {'xlmr': 'xlm-roberta-base', 'rubert': 'DeepPavlov/rubert-base-cased'}


def load_silver():
    return [json.loads(l) for l in open(SCRATCH / 'silver/silver.jsonl')]


def column_labels(row, col, names_only=False):
    """(labels, mask) per character for one column, or None if the column is not usable."""
    text = row['text'][col]
    spans = {}
    for x in row['spans']:
        if x['col'] != col:
            continue
        if names_only and x['field'] in NAME_FIELDS:
            if not x['names']:
                continue
            spans[x['field']] = tuple(x['names'])
        else:
            spans[x['field']] = (x['s'], x['e'])
    if not spans or not text:
        return None
    order = [f for f in FIELDS[col] if f in spans]
    if any(spans[a][1] > spans[b][0] for a, b in zip(order, order[1:])):
        return None
    lab, mask = [0] * len(text), [1] * len(text)
    for f, (s, e) in spans.items():
        for k in range(s, e):
            lab[k] = TAG[f]
    fl = FIELDS[col]
    for i, f in enumerate(fl):
        if f in spans:
            continue
        lo = max([spans[g][1] for g in fl[:i] if g in spans] or [0])
        hi = min([spans[g][0] for g in fl[i + 1:] if g in spans] or [len(text)])
        for k in range(lo, hi):
            mask[k] = 0
    return lab, mask


def confusion_table(books):
    """{char: [(other char, count)]} from two draft versions of the same entries of the given books."""
    cache = SCRATCH / 'silver/confusions.json'
    per_book = json.loads(cache.read_text()) if cache.exists() else {}
    for b in books:
        if b in per_book:
            continue
        files = defaultdict(dict)
        for f in sorted((ROOT / 'data' / b / 'processed').glob('year_draft_*.json')):
            parts = f.stem.split('_', 3)
            if len(parts) < 4:
                continue
            year, model = parts[2], parts[3]
            files[model][year] = f
        models = sorted(files, key=lambda m: -len(files[m]))[:2]
        c = Counter()
        if len(models) == 2:
            rng = random.Random(0)
            for year in sorted(set(files[models[0]]) & set(files[models[1]])):
                a = {e['row_id']: e for e in json.loads(files[models[0]][year].read_text())['entries']}
                bb = {e['row_id']: e for e in json.loads(files[models[1]][year].read_text())['entries']}
                for rid in rng.sample(sorted(set(a) & set(bb)), min(80, len(set(a) & set(bb)))):
                    for col in COLS:
                        x, y = a[rid].get(col) or '', bb[rid].get(col) or ''
                        sm = difflib.SequenceMatcher(None, x, y, autojunk=False)
                        if sm.ratio() < 0.7:
                            continue
                        for op, i1, i2, j1, j2 in sm.get_opcodes():
                            if op == 'replace' and i2 - i1 == j2 - j1 <= 2:
                                for p, q in zip(x[i1:i2], y[j1:j2]):
                                    if p.isalpha() and q.isalpha():
                                        c[p + q] += 1
                                        c[q + p] += 1
        per_book[b] = dict(c)
        cache.write_text(json.dumps(per_book, ensure_ascii=False))
    tot = Counter()
    for b in books:
        tot.update(per_book[b])
    table = defaultdict(list)
    for pq, n in tot.items():
        if n >= 3:
            table[pq[0]].append((pq[1], n))
    return {k: ([q for q, _ in v], [n for _, n in v]) for k, v in table.items()}


LETTERS = 'абвгдежзиклмнопрстуфхцчшщъыьѣэюяі'


def augment(text, lab, mask, table, rng):
    t, l, m = [], [], []
    n = len(text)
    for k, ch in enumerate(text):
        r = rng.random()
        if ch == ' ':
            if r < 0.05 and 0 < k < n - 1:
                continue
        elif ch.isalpha():
            if r < 0.03:
                if ch in table and rng.random() < 0.8:
                    ch = rng.choices(*table[ch])[0]
                else:
                    c2 = rng.choice(LETTERS)
                    ch = c2.upper() if ch.isupper() else c2
            elif r < 0.04:
                continue
        t.append(ch), l.append(lab[k]), m.append(mask[k])
        if ch.isalpha() and k + 1 < n and text[k + 1].isalpha() and rng.random() < 0.01:
            t.append(' ')
            l.append(lab[k] if lab[k] == lab[k + 1] else 0)
            m.append(min(mask[k], mask[k + 1]))
    return ''.join(t), l, m


def decode(text, tags):
    """Per-character tag ids -> {FIELD: (s, e)}."""
    runs = defaultdict(list)
    k = 0
    while k < len(tags):
        j = k
        while j < len(tags) and tags[j] == tags[k]:
            j += 1
        if tags[k]:
            f = ALL_FIELDS[tags[k] - 1]
            if runs[f] and k - runs[f][-1][1] <= 2:
                runs[f][-1] = (runs[f][-1][0], j)
            else:
                runs[f].append((k, j))
        k = j
    out = {}
    for f, rs in runs.items():
        s, e = max(rs, key=lambda r: r[1] - r[0])
        sp = trim(text, s, e)
        if sp and sp[1] - sp[0] >= 2:
            out[f] = sp
    return out


# ---------------------------------------------------------------- character model
class CharTagger(nn.Module):
    def __init__(self, n_chars, n_tags, emb=64, hid=192):
        super().__init__()
        self.emb = nn.Embedding(n_chars, emb, padding_idx=0)
        self.col = nn.Embedding(3, 8)
        self.drop = nn.Dropout(0.3)
        self.rnn = nn.LSTM(emb + 8, hid, num_layers=2, bidirectional=True, batch_first=True, dropout=0.3)
        self.out = nn.Linear(2 * hid, n_tags)

    def forward(self, x, col, lengths):
        h = torch.cat([self.emb(x), self.col(col)[:, None, :].expand(-1, x.size(1), -1)], -1)
        packed = nn.utils.rnn.pack_padded_sequence(self.drop(h), lengths.cpu(), batch_first=True, enforce_sorted=False)
        h, _ = self.rnn(packed)
        h, _ = nn.utils.rnn.pad_packed_sequence(h, batch_first=True, total_length=x.size(1))
        return self.out(self.drop(h))


def run_char(train, predict, args, table, dev):
    rng = random.Random(args.seed)
    chars = Counter(ch for t, _, _, _ in train for ch in t)
    vocab = {ch: i + 2 for i, ch in enumerate(sorted(c for c, n in chars.items() if n >= 2))}
    model = CharTagger(len(vocab) + 2, len(ALL_FIELDS) + 1).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=2e-3)
    epochs = args.epochs or 10
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=3e-3, total_steps=epochs * (len(train) // args.batch + 1))

    def batchify(items):
        L = max(len(t) for t, *_ in items)
        x = torch.zeros(len(items), L, dtype=torch.long)
        y = torch.zeros(len(items), L, dtype=torch.long)
        w = torch.zeros(len(items), L)
        for i, (t, lab, mask, _) in enumerate(items):
            x[i, :len(t)] = torch.tensor([vocab.get(ch, 1) for ch in t])
            if lab is not None:
                y[i, :len(t)] = torch.tensor(lab)
                w[i, :len(t)] = torch.tensor(mask, dtype=torch.float)
        cols = torch.tensor([c for *_, c in items])
        lens = torch.tensor([len(t) for t, *_ in items])
        return x.to(dev), y.to(dev), w.to(dev), cols.to(dev), lens

    for ep in range(epochs):
        model.train()
        data = [augment(t, l, m, table, rng) + (c,) if (not args.no_aug and rng.random() < 0.7) else (t, l, m, c)
                for t, l, m, c in train]
        data = [d for d in data if d[0]]
        rng.shuffle(data)
        tot = 0.0
        for i in range(0, len(data), args.batch):
            x, y, w, cols, lens = batchify(data[i:i + args.batch])
            loss = (nn.functional.cross_entropy(model(x, cols, lens).transpose(1, 2), y, reduction='none') * w).sum() / w.sum().clamp(min=1)
            opt.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            sched.step()
            tot += loss.item()
        print(f'epoch {ep + 1} loss {tot / (len(data) // args.batch + 1):.4f}', flush=True)
    model.eval()
    out = []
    order = sorted(range(len(predict)), key=lambda i: len(predict[i][0]))
    with torch.no_grad():
        for i in range(0, len(order), 128):
            idx = [j for j in order[i:i + 128] if predict[j][0]]
            if not idx:
                continue
            items = [(predict[j][0], None, None, predict[j][1]) for j in idx]
            x, _, _, cols, lens = batchify(items)
            tags = model(x, cols, lens).argmax(-1).cpu().tolist()
            for j, tg in zip(idx, tags):
                out.append((j, decode(predict[j][0], tg[:len(predict[j][0])])))
    if args.save:
        torch.save({'state': model.state_dict(), 'vocab': vocab, 'fields': ALL_FIELDS}, args.save_path)
    return dict(out)


# ---------------------------------------------------------------- pretrained encoder
def run_encoder(train, predict, args, table, dev):
    from transformers import AutoModel, AutoTokenizer
    rng = random.Random(args.seed)
    tok = AutoTokenizer.from_pretrained(HF[args.model])
    enc = AutoModel.from_pretrained(HF[args.model]).to(dev)
    head = nn.Linear(enc.config.hidden_size, len(ALL_FIELDS) + 1).to(dev)
    epochs = args.epochs or 3
    # the subword embedding table is frozen: its gradient and optimizer state alone (3 x 0.8 GB for
    # XLM-R) do not fit beside the other job on the shared GPU
    enc.embeddings.word_embeddings.weight.requires_grad_(False)
    enc_params = [p for p in enc.parameters() if p.requires_grad]
    params = enc_params + list(head.parameters())
    opt = torch.optim.AdamW([{'params': enc_params, 'lr': 3e-5}, {'params': head.parameters(), 'lr': 1e-3}], weight_decay=0.01)
    steps = epochs * (len(train) // args.batch + 1)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[3e-5, 1e-3], total_steps=steps, pct_start=0.1, anneal_strategy='linear')

    def encode(texts):
        return tok(texts, return_offsets_mapping=True, truncation=True, max_length=256, padding=True, return_tensors='pt')

    def forward(e):
        with torch.autocast('cuda', dtype=torch.bfloat16, enabled=dev == 'cuda'):
            h = enc(input_ids=e['input_ids'].to(dev), attention_mask=e['attention_mask'].to(dev)).last_hidden_state
        return head(h.float())

    skipped = 0
    for ep in range(epochs):
        enc.train()
        data = [augment(t, l, m, table, rng) + (c,) if (not args.no_aug and rng.random() < 0.7) else (t, l, m, c)
                for t, l, m, c in train]
        data = [d for d in data if d[0]]
        rng.shuffle(data)
        tot, nb = 0.0, 0
        for i in range(0, len(data), args.batch):
            items = data[i:i + args.batch]
            e = encode([t for t, *_ in items])
            y = torch.zeros(e['input_ids'].shape, dtype=torch.long)
            w = torch.zeros(e['input_ids'].shape)
            for b, (t, lab, mask, _) in enumerate(items):
                for k, (a, z) in enumerate(e['offset_mapping'][b].tolist()):
                    ks = [q for q in range(a, z) if not t[q].isspace()]
                    if ks:
                        y[b, k] = Counter(lab[q] for q in ks).most_common(1)[0][0]
                        w[b, k] = min(mask[q] for q in ks)
            try:
                logits = forward(e)
                loss = (nn.functional.cross_entropy(logits.transpose(1, 2), y.to(dev), reduction='none') * w.to(dev)).sum() / w.sum().clamp(min=1).to(dev)
                opt.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                tot, nb = tot + loss.item(), nb + 1
            except torch.OutOfMemoryError:
                skipped += 1
                opt.zero_grad()
                torch.cuda.empty_cache()
            sched.step()
        print(f'epoch {ep + 1} loss {tot / max(nb, 1):.4f} batches skipped for memory {skipped}', flush=True)
        if skipped > 0.05 * (ep + 1) * (len(data) // args.batch + 1):
            sys.exit('too many batches skipped for memory: no predictions written')
    enc.eval()
    out = {}
    order = sorted((i for i in range(len(predict)) if predict[i][0]), key=lambda i: len(predict[i][0]))
    with torch.no_grad():
        for i in range(0, len(order), 32):
            idx = order[i:i + 32]
            e = encode([predict[j][0] for j in idx])
            tags = forward(e).argmax(-1).cpu().tolist()
            for b, j in enumerate(idx):
                t = predict[j][0]
                ct = [0] * len(t)
                for k, (a, z) in enumerate(e['offset_mapping'][b].tolist()):
                    for q in range(a, min(z, len(t))):
                        ct[q] = tags[b][k]
                # a space between two characters of the same field belongs to it
                for q in range(1, len(t) - 1):
                    if t[q].isspace() and ct[q - 1] == ct[q + 1]:
                        ct[q] = ct[q - 1]
                out[j] = decode(t, ct)
    if args.save:
        torch.save({'encoder': {k: v.half() for k, v in enc.state_dict().items()}, 'head': head.state_dict(),
                    'base': HF[args.model], 'fields': ALL_FIELDS}, args.save_path)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--model', default='char', choices=['char', 'xlmr', 'rubert'])
    ap.add_argument('--heldout', required=True)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--epochs', type=int, default=0)
    ap.add_argument('--batch', type=int, default=0)
    ap.add_argument('--names-only', action='store_true')
    ap.add_argument('--no-aug', action='store_true')
    ap.add_argument('--save', action='store_true')
    args = ap.parse_args()
    args.batch = args.batch or (64 if args.model == 'char' else 16)
    torch.manual_seed(args.seed)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    silver = load_silver()
    train_books = [b for b in TRANSLATED if b != args.heldout]
    assert args.heldout == 'none' or args.heldout in TRANSLATED
    train, skipped = [], 0
    for r in silver:
        if r['book'] not in train_books:
            continue
        for ci, c in enumerate(COLS):
            lm = column_labels(r, c, args.names_only)
            if lm:
                train.append((r['text'][c], lm[0], lm[1], ci))
            else:
                skipped += 1
    assert not any(r['book'] == args.heldout for r in silver if r['book'] in train_books)
    if args.heldout == 'none':
        targets = [e for b, m in UNLABELLED.items() for e in load_drafts(b, m)]
    else:
        targets = [r for r in silver if r['book'] == args.heldout]
    predict = [(e['text'][c], ci) for e in targets for ci, c in enumerate(COLS)]
    table = confusion_table(train_books)
    name = args.model + ('_namesonly' if args.names_only else '') + ('_noaug' if args.no_aug else '')
    name = f'{name}__{args.heldout}__s{args.seed}'
    (SCRATCH / 'preds').mkdir(exist_ok=True)
    (SCRATCH / 'models').mkdir(exist_ok=True)
    args.save_path = SCRATCH / 'models' / (name + '.pt')
    print(f'{name}: train columns {len(train)} (unusable {skipped}) from {train_books}; predict {len(predict)} columns; '
          f'confusion table {len(table)} letters', flush=True)
    res = (run_char if args.model == 'char' else run_encoder)(train, predict, args, table, dev)
    with open(SCRATCH / 'preds' / (name + '.jsonl'), 'w') as fh:
        for i, e in enumerate(targets):
            spans = [{'col': c, 'field': f, 's': s, 'e': e_} for ci, c in enumerate(COLS)
                     for f, (s, e_) in res.get(i * 3 + ci, {}).items()]
            fh.write(json.dumps({'book': e['book'], 'row_id': e['row_id'], 'spans': spans}, ensure_ascii=False) + '\n')
    print('written', SCRATCH / 'preds' / (name + '.jsonl'))


if __name__ == '__main__':
    main()
