"""Read the held-out line set with the open Russian CRNN-CTC model achimrabus/crnn-ctc-russian.

Usage: .venv-htr/bin/python -I pipeline/local_models/run_rabus.py MODEL_DIR SET.json OUT.json
MODEL_DIR holds best_model.pt and symbols.txt from Hugging Face. The network (Puigcerver 2017:
four conv blocks, three BiLSTM layers, CTC) is rebuilt here from the model card and the weights
are loaded as tensors only; greedy decoding; images scaled to height 128 as in its own pipeline.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn

ROOT = Path(__file__).resolve().parents[2]


class CRNN(nn.Module):
    def __init__(self, classes, filters=(12, 24, 48, 48), pool=(2, 2, 0, 2), hidden=256, layers=3):
        super().__init__()
        L, c = [], 1
        for f, p in zip(filters, pool):
            L += [nn.Conv2d(c, f, 3, padding=1), nn.BatchNorm2d(f), nn.LeakyReLU(0.2)]
            if p:
                L.append(nn.MaxPool2d(2, 2))
            c = f
        self.cnn = nn.Sequential(*L)
        self.rnn = nn.LSTM(filters[-1] * (128 // 2 ** sum(1 for p in pool if p)), hidden, layers, dropout=0.5, bidirectional=True)
        self.fc = nn.Linear(hidden * 2, classes)

    def forward(self, x):
        c = self.cnn(x)
        b, ch, h, w = c.shape
        return self.fc(self.rnn(c.permute(3, 0, 1, 2).reshape(w, b, ch * h))[0])


def main():
    mdir, dev = Path(sys.argv[1]), 'cuda' if torch.cuda.is_available() else 'cpu'
    ck = torch.load(mdir / 'best_model.pt', map_location='cpu', weights_only=True)
    sd = ck.get('model_state_dict', ck.get('state_dict', ck))
    if 'idx2char' in ck:
        idx2char = {int(k): v for k, v in ck['idx2char'].items()}
    else:
        syms = [s.rstrip('\n\r') for s in (mdir / 'symbols.txt').read_text(encoding='utf-8').split('\n') if s.rstrip('\n\r')]
        idx2char = {i + 1: s for i, s in enumerate(s for s in syms if s != '<ctc>')}
    idx2char = {k: ' ' if v in ('<SPACE>', '<space>') else v for k, v in idx2char.items()}
    net = CRNN(sd['fc.weight'].shape[0])
    net.load_state_dict(sd, strict=True)
    net.to(dev).eval()
    out = []
    for l in json.loads(Path(sys.argv[2]).read_text())['lines']:
        t = time.time()
        im = Image.open(ROOT / l['image']).convert('L')
        im = im.resize((max(8, int(128 * im.width / im.height)), 128), Image.LANCZOS)
        x = (torch.from_numpy(np.asarray(im, dtype=np.float32) / 255) - 0.5) / 0.5
        with torch.no_grad():
            ids = net(x[None, None].to(dev)).argmax(2)[:, 0].tolist()
        text = ''.join(idx2char.get(i, '') for n, i in enumerate(ids) if i and (n == 0 or i != ids[n - 1]))
        out.append({'id': l['id'], 'text': text.strip(), 'seconds': round(time.time() - t, 3)})
    Path(sys.argv[3]).write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
