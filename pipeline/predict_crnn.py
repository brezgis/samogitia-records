"""Predict text for line crops with the CRNN recognizer (fine-tuned achimrabus/crnn-ctc-russian).

Usage: SAMOGITIA_BOOK=data/<book> .venv-htr/bin/python -I pipeline/predict_crnn.py --model DIR/best_model.pt
          [--ids-from years_v2|proposals_v2|annotations] [--set SET.json OUT.json]
Writes training/predictions/<model-dir-name>-<UTC>/predictions.json and run.json in the same form
as predict_lines.py, so assemble_drafts.py and the rest take either recognizer. With --set it
instead reads a held-out line set (local_models/build_reading_set.py) and writes OUT.json for
local_models/score_reading.py. Lines are batched by width and padded with white.
Predictions are machine drafts, never labels. GPU only.
"""
import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent / 'local_models'))
from run_rabus import CRNN  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
SOURCES = {'proposals_v2': 'line_proposals_v2.json', 'annotations': 'annotations.json',
           'years_v2': 'line_proposals_years_v2.json'}


def load_net(path):
    ck = torch.load(path, map_location='cpu', weights_only=True)
    sd = ck['model_state_dict']
    net = CRNN(sd['fc.weight'].shape[0])
    net.load_state_dict(sd)
    idx2char = {int(k): ' ' if v in ('<SPACE>', '<space>') else v for k, v in ck['idx2char'].items()}
    return net.cuda().eval(), idx2char


def tensor(path):
    im = Image.open(ROOT / path).convert('L')
    im = im.resize((max(16, int(128 * im.width / im.height)), 128), Image.LANCZOS)
    return (torch.from_numpy(np.asarray(im, dtype=np.float32) / 255) - 0.5) / 0.5


def predict(net, idx2char, images, batch=48, with_probs=False):
    """Text per image; with_probs also returns the per-step class probabilities (numpy, T x C)."""
    order = sorted(range(len(images)), key=lambda i: Image.open(ROOT / images[i]).size[0] / Image.open(ROOT / images[i]).size[1])
    out, probs = [None] * len(images), [None] * len(images)
    for k in range(0, len(order), batch):
        idx = order[k:k + batch]
        xs = [tensor(images[i]) for i in idx]
        X = torch.ones(len(xs), 1, 128, max(x.shape[1] for x in xs))
        for n, x in enumerate(xs):
            X[n, 0, :, :x.shape[1]] = x
        with torch.no_grad():
            try:
                lp = torch.log_softmax(net(X.cuda()), 2)          # T x B x C
            except torch.OutOfMemoryError:                        # GPU shared with another job: go in sixes
                torch.cuda.empty_cache()
                lp = torch.cat([torch.log_softmax(net(X[j:j + 6].cuda()), 2) for j in range(0, len(idx), 6)], 1)
        for n, i in enumerate(idx):
            T = xs[n].shape[1] // 8
            row = lp[:T, n].argmax(1).tolist()
            out[i] = ''.join(idx2char.get(c, '') for m, c in enumerate(row) if c and (m == 0 or c != row[m - 1])).strip()
            if with_probs:
                probs[i] = lp[:T, n].exp().cpu().numpy()
    return (out, probs) if with_probs else out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--ids-from', choices=sorted(SOURCES), default='years_v2')
    ap.add_argument('--set', nargs=2, type=Path)
    args = ap.parse_args()
    if not torch.cuda.is_available():
        print('CUDA unavailable; refusing CPU fallback.')
        return 2
    net, idx2char = load_net(args.model)
    if args.set:
        lines = json.loads(args.set[0].read_text())['lines']
        t = time.time()
        texts = predict(net, idx2char, [l['image'] for l in lines])
        s = round((time.time() - t) / len(lines), 4)
        args.set[1].write_text(json.dumps([{'id': l['id'], 'text': x, 'seconds': s} for l, x in zip(lines, texts)], ensure_ascii=False, indent=1))
        return 0
    items = [i for i in json.loads((BOOK / 'training' / SOURCES[args.ids_from]).read_text()) if i.get('image')]
    texts = predict(net, idx2char, [i['image'] for i in items])
    run_id = args.model.parent.name + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = BOOK / 'training/predictions' / run_id
    out.mkdir(parents=True)
    (out / 'predictions.json').write_text(json.dumps(
        [{'id': it['id'], 'text': p, 'row_id': it.get('row_id'), 'cell': it.get('cell'), 'scan': it.get('scan'),
          'split': it.get('split'), 'hand_group': it.get('hand_group')} for it, p in zip(items, texts)], ensure_ascii=False, indent=1))
    (out / 'run.json').write_text(json.dumps({
        'run_id': run_id, 'kind': 'machine_draft_predictions', 'pipeline': 'CRNN-CTC (pipeline/predict_crnn.py), greedy decoding',
        'model_path': str(args.model), 'model_sha256': hashlib.sha256(args.model.read_bytes()).hexdigest(),
        'input': SOURCES[args.ids_from], 'lines': len(items), 'torch': torch.__version__,
        'gpu': torch.cuda.get_device_name(0), 'note': 'Machine predictions, not labels.'}, indent=1))
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
