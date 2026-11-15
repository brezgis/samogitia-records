"""Generate line-boundary proposals for HTR annotation, not training labels.

Projection segmentation is a bootstrap for these ruled cells. Each cell is read with a
margin above and below, so a line crossing the row boundary is kept whole and given to the
cell holding its letter bodies; printed rules (also slightly slanted ones) are removed
first; and when the writing in a cell runs at a slope, the rows are projected along that
slope. A proposal's `bbox` is the upright box enclosing the line; `line` records the line's
own rows and slope, which refine_lines.py uses to paint out the neighbouring lines' ink.
Touching handwriting can still merge or split lines: every proposal needs image/text review.
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


CELLS=['baptism','parents','godparents']
MARGIN=120   # px of context read above and below a cell (a line and a half at these scan sizes)


def horizontal_rules(ink):
    """Printed row rules, separator strokes and long underlines, also when the page is a
    little askew: runs of at least 60 px that chain into a thin band at least 200 px wide."""
    thick=cv2.dilate(ink,np.ones((3,1),np.uint8))
    runs=cv2.morphologyEx(thick,cv2.MORPH_OPEN,np.ones((1,60),np.uint8))
    n,lab,st,_=cv2.connectedComponentsWithStats(runs,connectivity=8)
    long=[i for i in range(1,n) if st[i,2]>=200 and st[i,3]<=12+.05*st[i,2]]
    if not long: return np.zeros_like(ink)
    return cv2.dilate(np.isin(lab,long).astype(np.uint8)*255,np.ones((5,3),np.uint8))


def text_ink(gray):
    """Binary ink of the handwriting: adaptive threshold minus the printed rules."""
    ink=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,41,12)
    rules=cv2.morphologyEx(ink,cv2.MORPH_OPEN,np.ones((100,1),np.uint8))
    return cv2.subtract(ink,rules|horizontal_rules(ink))


def strip_profiles(cleaned,n=24):
    """Ink count per row in n vertical strips; returns (profiles n x h, strip centre x)."""
    edges=np.linspace(0,cleaned.shape[1],n+1).astype(int)
    P=np.array([(cleaned[:,a:b]>0).sum(axis=1) for a,b in zip(edges[:-1],edges[1:])],dtype=float)
    return P,(edges[:-1]+edges[1:])/2


def sheared_profile(P,xs,slope):
    """Row profile after sliding each strip so that writing rising or falling at `slope`
    (dy/dx; y grows downwards) lies level. The cell's centre column stays where it is."""
    xc=(xs[0]+xs[-1])/2; h=P.shape[1]; out=np.zeros(h)
    for p,x in zip(P,xs):
        d=int(round(slope*(x-xc)))            # this strip's ink sits d rows lower than at the centre
        if d>0: out[:h-d]+=p[d:]
        elif d<0: out[-d:]+=p[:h+d]
        else: out+=p
    return out


def writing_slope(P,xs,width):
    """Slope of the lines in a cell: the shear that makes the row profile sharpest. Returns 0
    unless a slant of at least 12 px across the cell sharpens the profile by 8% or more, so
    level writing is cut exactly as without this step."""
    def sharp(s): return float((gaussian_filter1d(sheared_profile(P,xs,s),2)**2).sum())
    level=sharp(0)
    if level<=0: return 0.0
    best=max((s for s in np.arange(-20,21)*.005 if abs(s)*width>=12),key=sharp,default=0.0)
    return float(best) if sharp(best)>=1.08*level else 0.0


def valley(profile,a,b):
    """Cut between two line peaks: the middle of the emptiest stretch, not its first row."""
    seg=profile[a:b+1]; top=seg.min()+max(1,.02*profile.max())
    lo=hi=int(np.argmin(seg))
    while lo>0 and seg[lo-1]<=top: lo-=1
    while hi<len(seg)-1 and seg[hi+1]<=top: hi+=1
    return a+(lo+hi)//2


def line_bands(gray):
    """Text lines of a cell image. Returns (slope, bands); each band is a dict with the line's
    rows at the centre column: top `a`, bottom `b`, the body of the letters `c0`..`c1` and its
    densest row `peak`; `faint` marks a low peak taken as a short line. With a non-zero slope the line runs at that slope through those rows."""
    cleaned=text_ink(gray); h,w=cleaned.shape
    P,xs=strip_profiles(cleaned)
    slope=writing_slope(P,xs,w)
    raw=sheared_profile(P,xs,slope)
    profile=gaussian_filter1d(raw,4)
    peaks,_=find_peaks(profile,distance=35,prominence=max(5,profile.max()*.14))
    if not len(peaks): return slope,[]
    # A short line (an entry's last word or two) is a low peak. It counts when it stands
    # where a line would: at least three quarters of the usual line spacing from every other.
    pitch=float(np.median(np.diff(peaks))) if len(peaks)>2 else 0
    strong=set(int(p) for p in peaks)
    if pitch:
        faint,_=find_peaks(profile,distance=35,prominence=max(5,profile.max()*.05))
        for p in faint:
            if np.abs(peaks-p).min()>=.75*pitch: peaks=np.sort(np.append(peaks,p))
    cuts=[0]+[valley(profile,a,b) for a,b in zip(peaks[:-1],peaks[1:])]+[h]
    bands=[]
    for a,b,pk in zip(cuts[:-1],cuts[1:],peaks):
        if b-a<18: continue
        c0=c1=int(pk)
        while c0>a and profile[c0-1]>=.5*profile[pk]: c0-=1
        while c1<b-1 and profile[c1+1]>=.5*profile[pk]: c1+=1
        bands.append({'a':max(0,int(a)-5),'b':min(h,int(b)+5),'c0':c0,'c1':c1,'peak':int(pk),'faint':int(pk) not in strong})
    if len(bands)>=3:
        # A line next to empty paper (an entry's last line, a line under a heading) would take
        # all of it; no line reaches much further from its letter bodies than the cell's lines
        # usually do.
        up=1.6*np.median([d['c0']-d['a'] for d in bands]); down=1.6*np.median([d['b']-d['c1'] for d in bands])
        for d in bands:
            d['a']=int(max(d['a'],d['c0']-up)); d['b']=int(min(d['b'],d['c1']+down))
    return slope,bands


def line_boxes(gray):
    """Row spans (top, bottom) of the text lines in a cell image; see line_bands."""
    return [(b['a'],b['b']) for b in line_bands(gray)[1]]


def rel(path):
    """Path as stored in the proposals: relative to the project, or absolute for scratch output."""
    try: return str(Path(path).relative_to(ROOT))
    except ValueError: return str(path)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scans',type=int,nargs='+',default=[93,94,95,96,111,114,115])
    ap.add_argument('--queue',default='processed/queue.json',help='queue file (relative to the book)')
    ap.add_argument('--all-rows',action='store_true',help='use every row in the queue, not only in_target_year')
    ap.add_argument('--out-json',default='training/line_proposals.json')
    ap.add_argument('--out-dir',default='training/proposals')
    args=ap.parse_args()
    queue=json.loads((BOOK/args.queue).read_text())
    crop_dir=BOOK/args.out_dir; crop_dir.mkdir(parents=True,exist_ok=True)
    proposals=[]; cache={}; skipped=[]; seen={}
    position={row['row_id']:i for i,row in enumerate(queue)}
    for row in queue:
        if row['scan'] not in args.scans or not (row['in_target_year'] or args.all_rows): continue
        scan=row['scan']
        if scan not in cache:
            cache={scan:np.array(Image.open(ROOT/row['source']).convert('L'))}   # one page in memory at a time
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
        boxes=[(c,xa,xb,*row['focal_y']) for c,(xa,xb) in zip(['baptism','parents','godparents'],[(x0,x1),(x1,x2),(x2,x3)])]
        if row.get('cells'):   # spread form: explicit cell boxes, each at its own page's height
            boxes=[(c,b[0],b[2],max(0,b[1]),min(h,b[3])) for c,b in row['cells'].items()]
        for cell,xa,xb,ya,yb in boxes:
            xa=max(0,xa+8);xb=min(w,xb-8)
            if yb-ya<20 or xb-xa<20:
                skipped.append({'row_id':row['row_id'],'cell':cell,'box':[int(xa),int(ya),int(xb),int(yb)]})
                continue
            # The lines are found in the cell plus a margin above and below, so a line lying
            # across the cell's edge (the layout's row boundary is not exact) is seen whole. It
            # goes, uncut, to the cell that holds the body of its letters.
            wa,wb=max(0,ya-MARGIN),min(h,yb+MARGIN)
            slope,bands=line_bands(source[wa:wb,xa:xb])
            taken=seen.setdefault((scan,row['page'],cell),[])
            n=0
            for band in bands:
                peak=wa+band['peak']
                if not ya-4<=peak<yb+4 or any(abs(peak-t['peak'])<25 for t in taken): continue
                n+=1
                taken.append({'id':f"{row['row_id']}_{cell}_{n:02}",'row':row,'cell':cell,'x':(xa,xb),'slope':slope,'peak':peak,
                              'a':wa+band['a'],'b':wa+band['b'],'c0':wa+band['c0'],'c1':wa+band['c1'],'faint':band['faint']})
    for column in seen.values():
        # Neighbouring cells are read separately and may disagree at their shared edge: no
        # line's rows may reach into the letter bodies of the line above or below it.
        column.sort(key=lambda t:t['peak'])
        for u,l in zip(column[:-1],column[1:]):
            if l['a']<u['c1']: l['a']=max(l['a'],u['b']-10) if u['b']-10<l['c0'] else (u['c1']+l['c0'])//2
            if u['b']>l['c0']: u['b']=min(u['b'],l['a']+10) if l['a']+10>u['c1'] else (u['c1']+l['c0'])//2
    lines=sorted((t for column in seen.values() for t in column),key=lambda t:(position[t['row']['row_id']],CELLS.index(t['cell']) if t['cell'] in CELLS else 9,t['id']))
    for t in lines:
        row=t['row']; scan=row['scan']; xa,xb=t['x']
        if scan not in cache: cache={scan:np.array(Image.open(ROOT/row['source']).convert('L'))}
        source=cache[scan]; h=source.shape[0]
        rise=abs(t['slope'])*(xb-xa)/2
        bbox=[int(xa),int(max(0,np.floor(t['a']-rise))),int(xb),int(min(h,np.ceil(t['b']+rise)))]
        path=crop_dir/f"{t['id']}.png"
        Image.fromarray(source[bbox[1]:bbox[3],bbox[0]:bbox[2]]).save(path)
        proposals.append({'id':t['id'],'scan':scan,'row_id':row['row_id'],'cell':t['cell'],
            'source_image':row['source'],'source_sha256':row['source_sha256'],'bbox':bbox,
            # the line itself: its rows at column x (top, bottom, letter body) and its slope
            'line':{'x':(xa+xb)/2,'slope':round(t['slope'],4),'band':[int(t['a']),int(t['b'])],'core':[int(t['c0']),int(t['c1'])],**({'faint':True} if t['faint'] else {})},
            'image':rel(path),'image_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'text':None,'status':'needs_boundary_and_text_review','split':split_for_scan(scan),
            'hand_group':row['hand_group'],'reviewer':None,'independent_verification':False})
    (BOOK/args.out_json).write_text(json.dumps(proposals,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'scans':len(args.scans),'line_proposals':len(proposals),'skipped_cells':len(skipped),
                      'skipped':skipped[:20],'approved_labels':0}))


if __name__=='__main__': main()
