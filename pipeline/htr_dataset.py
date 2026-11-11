"""Export checked line images and diplomatic .gt.txt labels for Kraken.

Draft/uncertain labels never enter a training manifest. Split by source spread,
not random lines, so overlapping crops cannot cross train/validation/test.
"""
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'data/plunge-1886-1890'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def split_for_scan(scan):
    return 'validation' if scan % 10 == 4 else 'test' if scan % 10 == 5 else 'train'


def crop_matches_source(crop, source_box, mask_fill=None):
    """Crop equals the source box, except pixels painted with the recorded mask fill
    (ink from neighbouring cells removed by refine_lines.py)."""
    a=crop.convert('L').tobytes(); b=source_box.convert('L').tobytes()
    if a==b: return True
    if mask_fill is None or len(a)!=len(b): return False
    return all(x==y or x==mask_fill for x,y in zip(a,b))


def book_prefix(book_dir):
    """Line ids are per book (scan numbers repeat across books): namespace all but the first book."""
    return '' if book_dir in ('', 'plunge-1886-1890') else book_dir + '__'


def all_annotation_files():
    return sorted(ROOT.glob('data/*/training/annotations.json'))


def combined_sha(paths):
    h=hashlib.sha256()
    for p in paths:
        h.update(str(p.relative_to(ROOT)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def checked_labels(annotations, root=ROOT):
    result=[]; ids=set(); image_splits={}; source_splits={}
    for item in annotations:
        ident=book_prefix(item.get('_book',''))+item['id']
        if ident in ids: raise ValueError(f'Duplicate annotation id: {ident}')
        ids.add(ident)
        if item['status'] not in ('image_checked','independently_checked'): continue
        if not item.get('reviewer'): raise ValueError(f'Missing reviewer: {ident}')
        text=item.get('text')
        if not text or any(c in text for c in ['[',']','?','\n','\r']):
            raise ValueError(f'Uncertain/multiline label cannot be ground truth: {ident}')
        split=split_for_scan(item['scan'])
        if item.get('split')!=split: raise ValueError(f'Spread split mismatch: {ident}')
        for path_key,hash_key in [('image','image_sha256'),('source_image','source_sha256')]:
            # the path must stay inside the project as written (no ..); bulk image folders may be
            # links to a data drive, so the link target itself is allowed to lie outside
            path=root/item[path_key]
            if '..' in Path(item[path_key]).parts or Path(item[path_key]).is_absolute():
                raise ValueError(f'Path outside project: {ident}')
            if sha(path)!=item[hash_key]: raise ValueError(f'Image changed since review: {ident}')
        with Image.open(root/item['source_image']) as source:
            x0,y0,x1,y1=item['bbox']
            if not (0<=x0<x1<=source.width and 0<=y0<y1<=source.height):
                raise ValueError(f'Invalid source box: {ident}')
            with Image.open(root/item['image']) as crop:
                if crop.size != (x1-x0,y1-y0): raise ValueError(f'Crop/box mismatch: {ident}')
                if not crop_matches_source(crop, source.crop(tuple(item['bbox'])), item.get('mask_fill')):
                    raise ValueError(f'Crop is not the recorded source pixels: {ident}')
        for table,key in [(image_splits,item['image_sha256']),(source_splits,item['source_sha256'])]:
            if key in table and table[key]!=split: raise ValueError(f'Data leakage: {ident}')
            table[key]=split
        result.append(item)
    return result


def main():
    files=all_annotation_files()
    annotations=[]
    for path in files:
        for item in json.loads(path.read_text()):
            item['_book']=path.parent.parent.name
            annotations.append(item)
    approved=checked_labels(annotations)
    version=hashlib.sha256(json.dumps(approved,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
    out=BOOK/'training/exports'/version;out.mkdir(parents=True,exist_ok=True)
    manifests={s:[] for s in ['train','validation','test']}
    for item in approved:
        target=out/(book_prefix(item['_book'])+item['id']+'.png')
        shutil.copyfile(ROOT/item['image'],target)
        target.with_suffix('.gt.txt').write_text(item['text']+'\n')
        target.with_suffix('.json').write_text(json.dumps(item,ensure_ascii=False,indent=2)+'\n')
        manifests[item['split']].append(str(target.resolve()))
    for split,paths in manifests.items():
        (out/f'{split}.txt').write_text(''.join(p+'\n' for p in paths))
    report={'dataset_id':version,'directory':str(out.relative_to(ROOT)),
        'annotation_files':[str(p.relative_to(ROOT)) for p in files],
        'annotations_sha256':combined_sha(files),'approved_labels':len(approved),
        'draft_labels':len(annotations)-len(approved),'counts':dict(Counter(i['split'] for i in approved)),
        'by_book':dict(Counter(i['_book'] for i in approved)),
        'hands_by_split':{s:dict(Counter(i['hand_group'] for i in approved if i['split']==s)) for s in manifests},
        'independently_verified_labels':sum(i.get('independent_verification',False) for i in approved),
        'independently_verified_evaluation_labels':sum(i.get('independent_verification',False) for i in approved if i['split']!='train'),
        'readiness':'pilot',
        'warning':'Labels are Claude transcriptions (blind Opus+Sonnet double reading with Opus adjudication, plus single-reader labels), not expert human ground truth.'}
    (out/'dataset.json').write_text(json.dumps(report,indent=2)+'\n')
    (BOOK/'training/dataset.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
