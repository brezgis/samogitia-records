"""Train and compare CRNN recognizers (fine-tuning achimrabus/crnn-ctc-russian) on the checked lines.

Usage (GPU only), .venv-htr/bin/python -I pipeline/train_crnn.py ...
  cv OUT_DIR [--variants base strong ens3 half quarter] [--epochs 30]
      5-fold cross-validation over spreads on every checked train+validation line of all books
      (the test split is never read). Fixed epoch count, no best-epoch picking. Writes
      OUT_DIR/<variant>.json ({id, text, pred, conf}) and prints character error overall, on
      lines with a word outside the frequent formula vocabulary ("name lines") and on the rest.
  final OUT.pt [--aug strong] [--epochs 30] [--seed 1] [--with-test]
      one model on all checked train+validation lines (with --with-test: every checked line).

Variants: base = width jitter and a slight tilt (the first fine-tuning recipe); strong = also shear,
blur, stroke thickening/thinning, contrast and brightness; ens3 = three seeds of `strong`, frame
probabilities averaged; half / quarter = `strong` on 50% / 25% of the training lines (learning curve).
conf is the mean probability of the chosen class over the non-blank frames of a line.
"""
import argparse
import json
import random
import sys
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent / 'local_models'))
from run_rabus import CRNN  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/mnt/ssd240gb/anna/samogitia-htr/llm/rabus-ru/best_model.pt')
H = 128


def dist(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def checked_lines(splits):
    out = []
    for f in sorted(ROOT.glob('data/*/training/annotations.json')):
        book = f.parts[-3]
        for a in json.loads(f.read_text()):
            if a['status'] == 'image_checked' and a['split'] in splits and a['text'].strip():
                out.append({'id': f"{book}/{a['id']}", 'book': book, 'scan': a['scan'], 'image': a['image'], 'text': a['text'].strip()})
    return out


def pixels(line):
    """The line image at height 128 as a float tensor in [-1, 1], cached on the line."""
    if 'px' not in line:
        im = Image.open(ROOT / line['image']).convert('L')
        im = im.resize((max(16, int(H * im.width / im.height)), H), Image.LANCZOS)
        line['px'] = torch.from_numpy(np.asarray(im, dtype=np.uint8).copy())
    return (line['px'].float() / 255 - 0.5) / 0.5


def augment(x, kind, rnd):
    """x: H x W in [-1, 1] on the GPU (1 = white paper)."""
    w = x.shape[1]
    x = F.interpolate(x[None, None], size=(H, max(16, int(w * rnd.uniform(0.88, 1.12)))), mode='bilinear', align_corners=False)
    tilt = rnd.uniform(-1.5, 1.5) if rnd.random() < 0.5 else 0.0
    shear = rnd.uniform(-0.25, 0.25) if kind == 'strong' and rnd.random() < 0.6 else 0.0
    if tilt or shear:
        a = np.deg2rad(tilt)
        ratio = x.shape[3] / H
        theta = torch.tensor([[np.cos(a), (-np.sin(a) + shear) / ratio, 0.0], [np.sin(a) * ratio, np.cos(a), 0.0]], dtype=torch.float32, device=x.device)
        grid = F.affine_grid(theta[None], x.shape, align_corners=False)
        x = F.grid_sample(x - 1, grid, mode='bilinear', padding_mode='zeros', align_corners=False) + 1   # pad with white
    if kind == 'strong':
        r = rnd.random()
        if r < 0.2:          # thicker strokes: ink is dark, so take the local minimum
            x = -F.max_pool2d(-x, 3, 1, 1)
        elif r < 0.35:       # thinner strokes
            x = F.max_pool2d(x, 3, 1, 1)
        if rnd.random() < 0.3:
            s = rnd.uniform(0.5, 1.4)
            k = torch.arange(-3, 4, device=x.device, dtype=torch.float32)
            g = torch.exp(-k ** 2 / (2 * s * s)); g = g / g.sum()
            x = F.conv2d(F.pad(x, (3, 3, 0, 0), mode='replicate'), g.view(1, 1, 1, 7))
            x = F.conv2d(F.pad(x, (0, 0, 3, 3), mode='replicate'), g.view(1, 1, 7, 1))
        if rnd.random() < 0.6:   # contrast and paper tone, in ink units (0 = white, 2 = black)
            ink = (1 - x) * rnd.uniform(0.7, 1.25) + rnd.uniform(-0.05, 0.15)
            x = (1 - ink).clamp(-1, 1)
    return x[0, 0]


def batch(items, kind=None, rnd=None):
    xs = [pixels(i).cuda() for i in items]
    if kind:
        xs = [augment(x, kind, rnd) for x in xs]
    X = torch.ones(len(xs), 1, H, max(x.shape[1] for x in xs), device='cuda')
    for n, x in enumerate(xs):
        X[n, 0, :, :x.shape[1]] = x
    return X, [x.shape[1] // 8 for x in xs]


def base_model():
    ck = torch.load(BASE, map_location='cpu', weights_only=True)
    sd = ck.get('model_state_dict', ck)
    if 'idx2char' in ck:
        idx2char = {int(k): v for k, v in ck['idx2char'].items()}
    else:
        syms = [s.rstrip('\n\r') for s in (BASE.parent / 'symbols.txt').read_text(encoding='utf-8').split('\n') if s.rstrip('\n\r')]
        idx2char = {i + 1: s for i, s in enumerate(s for s in syms if s != '<ctc>')}
    return sd, idx2char


def train(lines, idx2char, sd, epochs, seed, kind):
    rnd = random.Random(seed)
    torch.manual_seed(seed)
    c2i = {(' ' if v in ('<SPACE>', '<space>') else v): k for k, v in idx2char.items()}
    net = CRNN(sd['fc.weight'].shape[0]); net.load_state_dict(sd); net.cuda()
    steps = epochs * ((len(lines) + 15) // 16)
    opt = torch.optim.AdamW(net.parameters(), lr=3e-4, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, 6e-4, total_steps=steps + 8)
    ctc = torch.nn.CTCLoss(blank=0, zero_infinity=True)
    lines = list(lines)
    for _ in range(epochs):
        net.train(); rnd.shuffle(lines)
        groups = [sorted(lines[k:k + 320], key=lambda d: d['px'].shape[1] if 'px' in d else 0) for k in range(0, len(lines), 320)]
        batches = [g[k:k + 16] for g in groups for k in range(0, len(g), 16)]
        rnd.shuffle(batches)
        for items in batches:
            X, lens = batch(items, kind, rnd)
            tg = [torch.tensor([c2i[c] for c in it['text'] if c in c2i]) for it in items]
            lp = torch.log_softmax(net(X), 2)
            loss = ctc(lp, torch.cat(tg), torch.tensor(lens), torch.tensor([len(t) for t in tg]))
            opt.zero_grad(); loss.backward(); torch.nn.utils.clip_grad_norm_(net.parameters(), 5); opt.step(); sched.step()
    return net.eval()


def frame_probs(nets, lines):
    """Per line: class probabilities per frame (T x C), averaged over the given models."""
    out = [None] * len(lines)
    order = sorted(range(len(lines)), key=lambda i: pixels(lines[i]).shape[1])
    for k in range(0, len(order), 48):
        idx = order[k:k + 48]
        X, lens = batch([lines[i] for i in idx])
        with torch.no_grad():
            p = sum(torch.softmax(n(X), 2) for n in nets) / len(nets)
        for n, i in enumerate(idx):
            out[i] = p[:lens[n], n].cpu()
    return out


def decode(p, idx2char):
    best = p.argmax(1).tolist()
    keep = [(c, p[t, c].item()) for t, c in enumerate(best) if c and (t == 0 or c != best[t - 1])]
    text = ''.join(' ' if idx2char.get(c) in ('<SPACE>', '<space>') else idx2char.get(c, '') for c, _ in keep).strip()
    return text, (sum(q for _, q in keep) / len(keep) if keep else 0.0)


def fold_of(line, k=5):
    return zlib.crc32(f"{line['book']}/{line['scan']}".encode()) % k


def report(name, rows, formula):
    def is_name(t):
        return any(len(w.strip('.,:;-=')) >= 4 and w.strip('.,:;-=').lower() not in formula for w in t.split())
    s = Counter()
    for r in rows:
        k = 'name' if is_name(r['text']) else 'formula'
        for g in (k, 'all'):
            s[g, 'e'] += dist(r['text'], r['pred']); s[g, 'n'] += len(r['text']); s[g, 'lines'] += 1; s[g, 'x'] += r['text'] == r['pred']
    print(f"{name:8s} " + '; '.join(f"{g} {100 * s[g, 'e'] / s[g, 'n']:.2f}% ({s[g, 'x']}/{s[g, 'lines']} lines exact)" for g in ('all', 'name', 'formula')), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['cv', 'final'])
    ap.add_argument('out', type=Path)
    ap.add_argument('--variants', nargs='+', default=['base', 'strong', 'ens3', 'half', 'quarter'])
    ap.add_argument('--epochs', type=int, default=30)
    ap.add_argument('--aug', default='strong')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--with-test', action='store_true')
    args = ap.parse_args()
    assert torch.cuda.is_available(), 'GPU only'
    sd, idx2char = base_model()
    if args.mode == 'final':
        lines = checked_lines(('train', 'validation', 'test') if args.with_test else ('train', 'validation'))
        for l in lines:
            pixels(l)
        net = train(lines, idx2char, sd, args.epochs, args.seed, args.aug)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        torch.save({'model_state_dict': net.state_dict(), 'idx2char': idx2char}, args.out)
        print(len(lines), 'lines ->', args.out)
        return
    lines = checked_lines(('train', 'validation'))
    for l in lines:
        pixels(l)
    vocab = Counter(w.strip('.,:;-=').lower() for l in lines for w in l['text'].split())
    formula = {w for w, n in vocab.items() if n >= 8}
    args.out.mkdir(parents=True, exist_ok=True)
    print(len(lines), 'checked lines in', len({(l['book'], l['scan']) for l in lines}), 'spreads; folds', Counter(fold_of(l) for l in lines), flush=True)
    rows = {v: [] for v in args.variants}
    for k in range(5):
        tr, te = [l for l in lines if fold_of(l) != k], [l for l in lines if fold_of(l) == k]
        nets = {}

        def get(kind, seed, part=1.0):
            key = (kind, seed, part)
            if key not in nets:
                sub = tr if part == 1.0 else random.Random(100 + k).sample(tr, int(len(tr) * part))
                nets[key] = train(sub, idx2char, sd, args.epochs, seed, kind)
            return nets[key]
        plan = {'base': lambda: [get('base', 1)], 'strong': lambda: [get('strong', 1)],
                'ens3': lambda: [get('strong', s) for s in (1, 2, 3)],
                'half': lambda: [get('strong', 1, 0.5)], 'quarter': lambda: [get('strong', 1, 0.25)]}
        for v in args.variants:
            for l, p in zip(te, frame_probs(plan[v](), te)):
                text, conf = decode(p, idx2char)
                rows[v].append({'id': l['id'], 'text': l['text'], 'pred': text, 'conf': round(conf, 4)})
            (args.out / f'{v}.json').write_text(json.dumps(rows[v], ensure_ascii=False, indent=1))
        print('fold', k, 'done', flush=True)
    for v in args.variants:
        report(v, rows[v], formula)


if __name__ == '__main__':
    main()
