"""Generate line-boundary proposals for HTR annotation, not training labels.

Projection segmentation is a bootstrap for these ruled cells. Touching/tilted
handwriting can merge or split lines: every proposal needs image/text review.
Run: .venv/bin/python -I pipeline/segment_lines.py [--scans 93 94 ...]
"""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/__import__('os').environ.get('SAMOGITIA_BOOK','data/plunge-1886-1890')


def split_for_scan(scan):
    # All crops, variants and lines from a spread share a split.
    return 'validation' if scan % 10 == 4 else 'test' if scan % 10 == 5 else 'train'


def line_boxes(gray):
    ink=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,41,12)
    rules=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((100,1),np.uint8))
    rules |= cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((1,200),np.uint8))
    cleaned=cv2.subtract(ink,rules)
    profile=gaussian_filter1d((cleaned>0).sum(axis=1).astype(float),4)
    peaks,_=find_peaks(profile,distance=35,prominence=max(5,profile.max()*.14))
    if not len(peaks): return []
    cuts=[0]
    for a,b in zip(peaks[:-1],peaks[1:]):
        cuts.append(int(a+np.argmin(profile[a:b+1])))
    cuts.append(gray.shape[0])
    return [(max(0,a-5),min(gray.shape[0],b+5)) for a,b in zip(cuts[:-1],cuts[1:]) if b-a>=18]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scans',type=int,nargs='+',default=[93,94,95,96,111,114,115])
    ap.add_argument('--queue',default='processed/queue.json',help='queue file (relative to the book)')
    ap.add_argument('--all-rows',action='store_true',help='use every row in the queue, not only in_target_year')
    ap.add_argument('--out-json',default='training/line_proposals.json')
    ap.add_argument('--out-dir',default='training/proposals')
    args=ap.parse_args()
    queue=json.loads((BOOK/args.queue).read_text())
    out=BOOK/'training'; (BOOK/args.out_dir).mkdir(parents=True,exist_ok=True)
    proposals=[]; cache={}; skipped=[]
    for row in queue:
        if row['scan'] not in args.scans or not (row['in_target_year'] or args.all_rows): continue
        scan=row['scan']
        if scan not in cache:
            cache[scan]=np.array(Image.open(ROOT/row['source']).convert('L'))
        source=cache[scan]; h,w=source.shape
        half=w//2; start=0 if row['page']=='L' else half
        old=json.loads((BOOK/f'layout/{scan:04}.json').read_text())
        pg=next(p for p in old['pages'] if p['page']==row['page'])
        cols=pg.get('cols',[])
        # Three major text cells have ~650px gaps. Printed subcolumns may have extras.
        spans=[(a,b) for a,b in zip(cols[:-1],cols[1:]) if b-a>500]
        if len(spans)>=2:
            x0,x1=spans[0]; _,x2=spans[1]
            x3=max(cols)
        else:
            x0,x1,x2,x3=[start+int(half*f) for f in [.215,.485,.765,.96]]
        for cell,(xa,xb) in zip(['baptism','parents','godparents'],[(x0,x1),(x1,x2),(x2,x3)]):
            ya,yb=row['focal_y']; xa=max(0,xa+8);xb=min(w,xb-8)
            crop=source[ya:yb,xa:xb]
            if crop.size==0 or crop.shape[0]<20 or crop.shape[1]<20:
                skipped.append({'row_id':row['row_id'],'cell':cell,'box':[int(xa),int(ya),int(xb),int(yb)]})
                continue
            for n,(a,b) in enumerate(line_boxes(crop),1):
                ident=f"{row['row_id']}_{cell}_{n:02}"
                bbox=[xa,ya+a,xb,ya+b]
                path=BOOK/args.out_dir/f'{ident}.png'
                Image.fromarray(source[bbox[1]:bbox[3],bbox[0]:bbox[2]]).save(path)
                proposals.append({'id':ident,'scan':scan,'row_id':row['row_id'],'cell':cell,
                    'source_image':row['source'],'source_sha256':row['source_sha256'],'bbox':bbox,
                    'image':str(path.relative_to(ROOT)),'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'text':None,'status':'needs_boundary_and_text_review','split':split_for_scan(scan),
                    'hand_group':row['hand_group'],'reviewer':None,'independent_verification':False})
    (BOOK/args.out_json).write_text(json.dumps(proposals,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'scans':len(args.scans),'line_proposals':len(proposals),'skipped_cells':len(skipped),
                      'skipped':skipped[:20],'approved_labels':0}))


if __name__=='__main__': main()
