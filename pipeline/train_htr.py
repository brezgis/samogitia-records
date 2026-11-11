"""GPU-only Kraken training launcher. Default is a read-only preflight.

Usage: .venv-htr/bin/python -I pipeline/train_htr.py --base-model PATH [--run]
--smoke permits one epoch on the tiny bootstrap set to test installation only.
--pilot permits a small bootstrap fine-tune (>=50 train, >=10 validation, both hands
in train and validation, no independent-check requirement). Pilot models exist to
draft labels faster; their scores are not evidence of accuracy.
Run outputs go to RUNS (scratch SSD); a manifest is written to training/runs/.
"""
import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'data/plunge-1886-1890'
RUNS=Path('/mnt/ssd240gb/anna/samogitia-htr/runs')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-model',type=Path)
    ap.add_argument('--run',action='store_true')
    ap.add_argument('--smoke',action='store_true')
    ap.add_argument('--pilot',action='store_true')
    ap.add_argument('--lrate',default='0.0001')
    ap.add_argument('--epochs',type=int)
    args=ap.parse_args()
    blockers=[]
    try:
        import torch
        if not torch.cuda.is_available(): blockers.append('CUDA is not available; CPU fallback is disabled.')
        else:
            # Actually execute a kernel: availability alone misses unsupported GPU architectures.
            a=torch.ones((32,32),device='cuda:0'); (a@a).sum().item();torch.cuda.synchronize()
            print('GPU:',torch.cuda.get_device_name(0),'PyTorch:',torch.__version__,'CUDA:',torch.version.cuda)
    except ImportError: blockers.append('PyTorch is not installed in this interpreter.')
    except RuntimeError as exc: blockers.append('CUDA kernel check failed: '+str(exc))
    if not list(Path('/dev').glob('nvidia[0-9]*')):
        blockers.append('No NVIDIA GPU device nodes are exposed to this workspace.')
    try:
        version=importlib.metadata.version('kraken')
        if version!='7.1.1': blockers.append(f'Expected Kraken 7.1.1, found {version}; review CLI compatibility before changing the pin.')
    except importlib.metadata.PackageNotFoundError: blockers.append('Kraken 7.1.1 is not installed.')
    dataset_path=BOOK/'training/dataset.json'
    dataset=json.loads(dataset_path.read_text()) if dataset_path.exists() else {}
    files=sorted(ROOT.glob('data/*/training/annotations.json'))
    h=hashlib.sha256()
    for f in files:
        h.update(str(f.relative_to(ROOT)).encode()); h.update(f.read_bytes())
    if not files or h.hexdigest()!=dataset.get('annotations_sha256'):
        blockers.append('Annotations changed or are missing; rerun htr_dataset.py before training.')
    counts=dataset.get('counts',{})
    if args.smoke and args.pilot: blockers.append('Choose --smoke or --pilot, not both.')
    minimum=({'train':1,'validation':1,'test':0} if args.smoke else
             {'train':50,'validation':10,'test':0} if args.pilot else
             {'train':500,'validation':50,'test':50})
    for split,n in minimum.items():
        if counts.get(split,0)<n: blockers.append(f'{split}: {counts.get(split,0)} checked labels; initial pilot target is {n}.')
    if not args.smoke:
        for split in [s for s,n in minimum.items() if n]:
            if len(dataset.get('hands_by_split',{}).get(split,{}))<2:
                blockers.append(f'{split}: examples from both provisional handwriting groups are needed.')
        if not args.pilot and dataset.get('independently_verified_evaluation_labels',0)<100:
            blockers.append('Evaluation needs independently checked labels; initial target is 100 across validation/test.')
    if args.base_model is None or not args.base_model.is_file():
        blockers.append('Supply a downloaded, provenance-recorded baseline model with --base-model.')
    if blockers:
        print(json.dumps({'ready':False,'blockers':blockers},indent=2));return 2
    out=ROOT/dataset['directory']
    ketos=Path(sys.executable).parent/'ketos'
    if not ketos.is_file(): print('ketos executable missing beside Python');return 2
    run_id=('smoke-' if args.smoke else 'pilot-' if args.pilot else '')+dataset['dataset_id']+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    command=[str(ketos),'-d','cuda:0','--seed','1888','train','-f','path','--linetype','bbox',
             '-t',str(out/'train.txt'),'-e',str(out/'validation.txt'),
             '--load',str(args.base_model.resolve()),'--resize','union','--batch-size','8',
             '--lrate',args.lrate,'--epochs',str(args.epochs) if args.epochs else '1' if args.smoke else '30' if args.pilot else '24',
             # PP-OCRv6 defaults to a cosine schedule, which needs a finite epoch
             # count: early stopping (max_epochs unset) crashes in configure_optimizers.
             '--quit','fixed' if (args.smoke or args.pilot) else 'early',
             *(['--augment'] if args.pilot else []),
             '-o',str(RUNS/run_id)]
    print(json.dumps({'ready':True,'command':command,'smoke_test_only':args.smoke,'pilot':args.pilot},indent=2))
    if args.run:
        manifest={'run_id':run_id,'kind':'smoke' if args.smoke else 'pilot' if args.pilot else 'full',
                  'dataset_id':dataset['dataset_id'],'counts':counts,'hands_by_split':dataset.get('hands_by_split'),
                  'base_model':str(args.base_model.resolve()),
                  'base_model_sha256':hashlib.sha256(args.base_model.read_bytes()).hexdigest(),
                  'kraken':version,'torch':torch.__version__,'command':command,'output_dir':str(RUNS/run_id),
                  'started':datetime.now(timezone.utc).isoformat()}
        (BOOK/'training/runs').mkdir(parents=True,exist_ok=True)
        (BOOK/f'training/runs/{run_id}.json').write_text(json.dumps(manifest,indent=1))
        # Keep writable caches inside the project; never write a global model cache.
        import os
        env=os.environ.copy();cache=BOOK/'training/cache';cache.mkdir(exist_ok=True)
        env.update({'XDG_CACHE_HOME':str(cache),'HF_HOME':str(cache/'huggingface'),'TORCH_HOME':str(cache/'torch')})
        return subprocess.run(command,cwd=ROOT,env=env).returncode
    return 0


if __name__=='__main__':sys.exit(main())
