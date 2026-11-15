"""Fine-tune achimrabus/crnn-ctc-russian on the project's checked lines (train split), as a second,
independently built recognizer beside the Kraken model.

Usage: .venv-htr/bin/python -I pipeline/local_models/finetune_rabus.py MODEL_DIR OUT.pt [EPOCHS] [EXTRA.json]
EXTRA.json: more training lines [{image, text}] that are NOT checked labels (lines of train-split
spreads on which two recognizers gave the same text); the checked lines are then repeated three
times per epoch so they keep their weight. They never go into annotations.json.
Trains on image_checked train lines of every book, picks the epoch with the best validation CER,
writes OUT.pt in the same format as best_model.pt (so run_rabus.py reads it: put it in its own
directory as best_model.pt next to symbols.txt). GPU only.
"""
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_rabus import CRNN, ROOT  # noqa: E402


def dist(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def load(path, train):
    im = Image.open(ROOT / path).convert('L')
    h = 128
    w = max(16, int(h * im.width / im.height * (random.uniform(0.9, 1.1) if train else 1)))
    im = im.resize((w, h), Image.LANCZOS)
    if train and random.random() < 0.5:
        im = im.rotate(random.uniform(-1.5, 1.5), resample=Image.BILINEAR, fillcolor=int(np.asarray(im)[0].mean()))
    return (torch.from_numpy(np.asarray(im, dtype=np.float32) / 255) - 0.5) / 0.5


def batchify(items, train):
    xs = [load(i['image'], train) for i in items]
    W = max(x.shape[1] for x in xs)
    X = torch.ones(len(xs), 1, 128, W)
    for n, x in enumerate(xs):
        X[n, 0, :, :x.shape[1]] = x
    return X, [x.shape[1] // 8 for x in xs]


def main():
    mdir, out, epochs = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 40
    assert torch.cuda.is_available(), 'GPU only'
    random.seed(3); torch.manual_seed(3)
    ck = torch.load(mdir / 'best_model.pt', map_location='cpu', weights_only=True)
    sd = ck.get('model_state_dict', ck)
    idx2char = {int(k): v for k, v in ck['idx2char'].items()} if 'idx2char' in ck else None
    if idx2char is None:
        syms = [s.rstrip('\n\r') for s in (mdir / 'symbols.txt').read_text(encoding='utf-8').split('\n') if s.rstrip('\n\r')]
        idx2char = {i + 1: s for i, s in enumerate(s for s in syms if s != '<ctc>')}
    c2i = {(' ' if v in ('<SPACE>', '<space>') else v): k for k, v in idx2char.items()}
    data = {'train': [], 'validation': []}
    for f in sorted(ROOT.glob('data/*/training/annotations.json')):
        for a in json.loads(f.read_text()):
            if a['status'] == 'image_checked' and a['split'] in data and a['text'].strip():
                data[a['split']].append({'image': a['image'], 'text': a['text'].strip()})
    if len(sys.argv) > 4:
        extra = json.loads(Path(sys.argv[4]).read_text())
        data['train'] = data['train'] * 3 + [{'image': e['image'], 'text': e['text']} for e in extra]
        print(len(extra), 'agreed lines added', flush=True)
    missing = sorted({c for d in data['train'] for c in d['text'] if c not in c2i})
    print(len(data['train']), 'train', len(data['validation']), 'validation; characters not in the model:', missing, flush=True)
    net = CRNN(sd['fc.weight'].shape[0]); net.load_state_dict(sd); net.cuda()
    opt = torch.optim.AdamW(net.parameters(), lr=3e-4, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 6e-4, total_steps=epochs * (len(data['train']) // 16 + 1))
    ctc, best = torch.nn.CTCLoss(blank=0, zero_infinity=True), 9

    def cer():
        net.eval(); e = n = 0
        with torch.no_grad():
            for k in range(0, len(data['validation']), 32):
                items = data['validation'][k:k + 32]
                X, lens = batchify(items, False)
                ids = net(X.cuda()).argmax(2).T.tolist()
                for it, row, L in zip(items, ids, lens):
                    row = row[:L]
                    t = ''.join(' ' if idx2char.get(i) in ('<SPACE>', '<space>') else idx2char.get(i, '') for m, i in enumerate(row) if i and (m == 0 or i != row[m - 1])).strip()
                    e += dist(it['text'], t); n += len(it['text'])
        return e / n

    print('before fine-tuning: validation CER %.1f%%' % (100 * cer()), flush=True)
    for ep in range(epochs):
        net.train(); random.shuffle(data['train'])
        srt = [sorted(data['train'][k:k + 320], key=lambda d: len(d['text'])) for k in range(0, len(data['train']), 320)]
        batches = [g[k:k + 16] for g in srt for k in range(0, len(g), 16)]
        random.shuffle(batches)
        for items in batches:
            X, lens = batchify(items, True)
            tg = [torch.tensor([c2i[c] for c in it['text'] if c in c2i]) for it in items]
            lp = torch.log_softmax(net(X.cuda()), 2)
            loss = ctc(lp, torch.cat(tg), torch.tensor(lens), torch.tensor([len(t) for t in tg]))
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 5); opt.step(); sched.step()
        v = cer()
        print(f'epoch {ep + 1}: validation CER {100 * v:.1f}%', flush=True)
        if v < best:
            best = v
            torch.save({'model_state_dict': net.state_dict(), 'idx2char': idx2char}, out)
    print('best validation CER %.1f%%' % (100 * best))


if __name__ == '__main__':
    main()
