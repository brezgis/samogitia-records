"""Run a pretrained Kraken recognizer over line-proposal crops (no training).

DEPRECATED for fine-tuned models: page-level inference prepares lines differently from
training; use pipeline/predict_lines.py. Kept for the recorded base-model baseline runs.

Usage:
  .venv-htr/bin/python -I pipeline/baseline_htr.py --model /path/model.safetensors [--limit N] [--ids-from annotations]

Outputs data/plunge-1886-1890/training/baseline/<run_id>/predictions.json as a
list of {id, text, mean_confidence, ...} usable by evaluate_htr.py, plus run.json
with model checksum and environment. Predictions are machine output: they are
NOT labels and must never be copied into annotations without human/visual review.
GPU only; refuses CPU fallback.
"""
import argparse
import hashlib
import importlib.metadata
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'data/plunge-1886-1890'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--limit', type=int, help='only the first N proposals (smoke test)')
    ap.add_argument('--ids-from', choices=['proposals', 'proposals_v2', 'annotations'], default='proposals_v2')
    args = ap.parse_args()

    import torch
    if not torch.cuda.is_available():
        print('CUDA unavailable; refusing CPU fallback.')
        return 2
    x = torch.ones(8, device='cuda:0')
    torch.cuda.synchronize()
    assert float((x * 2).sum()) == 16.0

    from PIL import Image
    from kraken.configs import RecognitionInferenceConfig
    from kraken.containers import BBoxLine, Segmentation
    from kraken.tasks import RecognitionTaskModel

    src = BOOK / 'training' / {'proposals': 'line_proposals.json', 'proposals_v2': 'line_proposals_v2.json',
                               'annotations': 'annotations.json'}[args.ids_from]
    items = json.loads(src.read_text())
    if args.limit:
        items = items[:args.limit]

    model = RecognitionTaskModel.load_model(args.model)
    config = RecognitionInferenceConfig(device=[0], accelerator='gpu')

    run_id = args.model.stem + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = BOOK / 'training/baseline' / run_id
    out.mkdir(parents=True, exist_ok=False)

    preds = []
    for n, item in enumerate(items, 1):
        img_path = ROOT / item['image']
        if sha256(img_path) != item['image_sha256']:
            raise SystemExit(f'Checksum mismatch: {img_path}')
        im = Image.open(img_path)
        w, h = im.size
        seg = Segmentation(type='bbox', imagename=str(img_path), text_direction='horizontal-lr',
                           script_detection=False,
                           lines=[BBoxLine(id=item['id'], bbox=(0, 0, w, h))])
        rec = next(iter(model.predict(im, seg, config)))
        conf = list(rec.confidences) if rec.confidences is not None else []
        preds.append({'id': item['id'], 'text': rec.prediction,
                      'mean_confidence': round(sum(conf) / len(conf), 4) if conf else None,
                      'min_confidence': round(min(conf), 4) if conf else None,
                      'hand_group': item.get('hand_group'), 'cell': item.get('cell'),
                      'scan': item.get('scan'), 'split': item.get('split'), 'image': item['image']})
        if n % 100 == 0:
            print(f'{n}/{len(items)}', flush=True)

    (out / 'predictions.json').write_text(json.dumps(preds, ensure_ascii=False, indent=1))
    (out / 'run.json').write_text(json.dumps({
        'run_id': run_id, 'kind': 'pretrained_baseline_no_finetuning',
        'model_path': str(args.model), 'model_sha256': sha256(args.model),
        'input': str(src.relative_to(ROOT)), 'lines': len(preds),
        'kraken': importlib.metadata.version('kraken'), 'torch': torch.__version__,
        'cuda': torch.version.cuda, 'gpu': torch.cuda.get_device_name(0),
        'note': 'Machine predictions, not labels. Not reviewed.'}, indent=1))
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
