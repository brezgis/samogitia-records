"""Predict text for line crops through Kraken's own test pipeline (training-consistent).

Usage:
  .venv-htr/bin/python -I pipeline/predict_lines.py --model M.safetensors [--ids-from proposals_v2|annotations]
        [--rows ROW ...] [--limit N]

Why: kraken's page-level inference (RecognitionTaskModel.predict, used by baseline_htr.py)
prepares lines differently from training for these crops and under-reports fine-tuned
models (10.2% vs 6.5% CER on validation for plunge1888-v1), failing mostly on short lines
in tall crops. This script runs the exact `ketos test` data module and network call and
records each prediction, so scores here match ketos test.

Writes training/predictions/<model-stem>-<UTC>/predictions.json ({id, text, ...}, usable
by eval_split.py) and run.json. Predictions are machine drafts, never labels. GPU only.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
SOURCES = {'proposals_v2': 'line_proposals_v2.json', 'annotations': 'annotations.json',
           'years_v2': 'line_proposals_years_v2.json'}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--ids-from', choices=sorted(SOURCES), default='proposals_v2')
    ap.add_argument('--rows', nargs='*')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--batch-size', type=int, default=16)
    ap.add_argument('--shard', help='K/N: process every N-th line starting at K (run N processes in parallel, then merge with --merge)')
    ap.add_argument('--merge', nargs='+', type=Path, help='merge shard output dirs into one prediction run and exit')
    args = ap.parse_args()

    if args.merge:
        preds, runs = [], []
        for d in args.merge:
            preds += json.loads((d / 'predictions.json').read_text())
            runs.append(json.loads((d / 'run.json').read_text()))
        if len({r['model_sha256'] for r in runs}) != 1:
            raise SystemExit('Shards were produced by different models')
        out = BOOK / 'training/predictions' / (runs[0]['run_id'].split('-shard')[0] + '-merged')
        out.mkdir(parents=True, exist_ok=False)
        (out / 'predictions.json').write_text(json.dumps(preds, ensure_ascii=False, indent=1))
        (out / 'run.json').write_text(json.dumps({**runs[0], 'run_id': out.name, 'lines': len(preds),
                                                   'merged_from': [r['run_id'] for r in runs]}, indent=1))
        print(out)
        return 0
    import torch
    if not torch.cuda.is_available():
        print('CUDA unavailable; refusing CPU fallback.')
        return 2
    from kraken.train import KrakenTrainer
    from kraken.train.ppocr import PPOCRv6RecognitionModel as Module
    from kraken.configs import RecognitionInferenceConfig

    items = json.loads((BOOK / 'training' / SOURCES[args.ids_from]).read_text())
    items = [i for i in items if i.get('image') and (not args.rows or i['row_id'] in args.rows)]
    if args.limit:
        items = items[:args.limit]
    shard = ''
    if args.shard:
        k, n = (int(x) for x in args.shard.split('/'))
        items = items[k::n]
        shard = f'-shard{k}of{n}'

    tmp = Path(tempfile.mkdtemp(prefix='predict_', dir=os.environ.get('TMPDIR', '/tmp')))
    listing = []
    for n, it in enumerate(items):
        src = ROOT / it['image']
        if sha256(src) != it['image_sha256']:
            raise SystemExit(f'Checksum mismatch: {src}')
        link = tmp / f'{n:06d}.png'
        link.symlink_to(src)
        # The data module requires ground truth. We store each line's index there so every
        # prediction carries its own key back: the data module does not preserve list order.
        (tmp / f'{n:06d}.gt.txt').write_text(str(n))
        listing.append(str(link))
    (tmp / 'list.txt').write_text('\n'.join(listing) + '\n')

    cfg = dict(test_data=listing, format_type='path', linetype='bbox', num_workers=0,
               batch_size=args.batch_size)
    m_config = Module._config_class(**cfg)
    trainer = KrakenTrainer(accelerator='gpu', devices=[0], precision='32-true',
                            enable_progress_bar=False, enable_model_summary=False, num_sanity_val_steps=0)
    with trainer.init_module(empty_init=False):
        model = Module.load_from_weights(str(args.model), m_config)
    dm_config = Module._data_config_class(**cfg)
    dm_config.legacy_polygons = getattr(model.net, 'use_legacy_polygons', False)
    dm = Module._data_module_class(dm_config)

    preds = {}
    decoder = RecognitionInferenceConfig().decoder

    def capture(batch, batch_idx, dataloader_idx=0):
        out, olens = model.net(batch['image'], batch['seq_lens'])
        out = out.squeeze(2)
        for locs, key in zip(decoder(out, olens), batch['target']):
            s = ''.join(x[0] for x in model.codec.decode(locs))
            for func in model._pred_transforms:
                s = func(s)
            preds[int(key)] = s
    model.test_step = capture
    def _end():
        model.test_metrics = None
    model.on_test_epoch_end = _end
    trainer.test(model, dm, verbose=False)
    if sorted(preds) != list(range(len(items))):
        missing = len(set(range(len(items))) - set(preds))
        raise SystemExit(f'{missing} of {len(items)} lines got no prediction (filtered by the data module?)')
    preds = [preds[n] for n in range(len(items))]

    run_id = args.model.stem + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + shard
    out = BOOK / 'training/predictions' / run_id
    out.mkdir(parents=True)
    (out / 'predictions.json').write_text(json.dumps(
        [{'id': it['id'], 'text': p, 'row_id': it.get('row_id'), 'cell': it.get('cell'), 'scan': it.get('scan'),
          'split': it.get('split'), 'hand_group': it.get('hand_group')} for it, p in zip(items, preds)],
        ensure_ascii=False, indent=1))
    (out / 'run.json').write_text(json.dumps({
        'run_id': run_id, 'kind': 'machine_draft_predictions', 'pipeline': 'ketos-test data module',
        'model_path': str(args.model), 'model_sha256': sha256(args.model), 'input': SOURCES[args.ids_from],
        'lines': len(items), 'kraken': importlib.metadata.version('kraken'), 'torch': torch.__version__,
        'gpu': torch.cuda.get_device_name(0), 'note': 'Machine predictions, not labels.'}, indent=1))
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
