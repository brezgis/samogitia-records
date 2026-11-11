"""Refine line-proposal x-extents so crops hold whole words, not cell-rule cuts.

Writing in these registers routinely runs across printed column rules. The
cell-clipped proposals (line_proposals.json) therefore cut words at both edges
and include spill from neighbouring columns. This step, per proposal:

  1. removes long printed rules (vertical/horizontal) in a tall window,
  2. finds connected ink components (cursive words or word pieces) in the band,
  3. re-joins components that touch the same vertical rule from both sides at
     the same height (a pen stroke crossing the rule),
  4. keeps joined groups that *start* in this cell (words are written left to
     right), plus small marks within the kept span; paints out the rest with
     paper colour, so no glyph is half-cut,
  5. crops to the kept span with small padding.
The label for a crop is exactly the complete characters visible in it.

Vertical extents are unchanged. Output: training/line_proposals_v2.json and
training/proposals_v2/*.png. The v1 file is preserved. These remain proposals:
every crop still needs visual review before its text can become a label.

Run: .venv/bin/python -I pipeline/refine_lines.py
"""
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
REACH = 220      # how far beyond the cell to look for overrunning words (px)
LEFT_SLACK = 45  # px a word may start left of the cell edge if mostly inside
SMALL = 40       # components below this area are marks (dots, diacritics, commas)
PAD = 10


def ink_and_rules(gray):
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 12)
    vert = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((120, 1), np.uint8))
    horiz = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((1, 200), np.uint8))
    vert = cv2.dilate(vert, np.ones((3, 5), np.uint8))
    horiz = cv2.dilate(horiz, np.ones((5, 3), np.uint8))
    return cv2.subtract(ink, vert | horiz), vert


def crossings(lab, n, vert):
    """Pairs of components that touch the same vertical rule from opposite sides
    at the same height: one pen stroke split by rule removal."""
    touches = []   # (component, side, rule_x, y)
    h, w = lab.shape
    rule_cols = np.flatnonzero(vert.any(axis=0))
    for x in rule_cols:
        for side, dx in (('L', -1), ('R', 1)):
            xx = x + dx
            if not (0 <= xx < w) or vert[:, xx].all():
                continue
            ys = np.flatnonzero(vert[:, x] & (lab[:, xx] > 0))
            for y in ys:
                touches.append((lab[y, xx], side, x, y))
    left = {}
    for c, side, x, y in touches:
        if side == 'L':
            left.setdefault(c, []).append((x, y))
    pairs = set()
    right = [(c, x, y) for c, side, x, y in touches if side == 'R']
    for cl, pts in left.items():
        for cr, xr, yr in right:
            if cr == cl:
                continue
            if any(0 < xr - xl <= 14 and abs(yr - yl) <= 8 for xl, yl in pts):
                pairs.add((cl, cr))
    return pairs


def refine(source, bbox):
    """Return (bbox, crop_image, flag). Ink belonging to other cells is painted out."""
    h, w = source.shape
    x0, y0, x1, y1 = bbox
    wx0, wx1 = max(0, x0 - REACH), min(w, x1 + REACH)
    wy0, wy1 = max(0, y0 - 160), min(h, y1 + 160)
    ink, vert = ink_and_rules(source[wy0:wy1, wx0:wx1])
    ink, vert = ink[y0 - wy0:y1 - wy0], vert[y0 - wy0:y1 - wy0]
    gray = source[y0:y1, wx0:wx1].copy()
    cx0, cx1 = x0 - wx0, x1 - wx0          # cell interior (8px inside the rules)
    n, lab, st, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a_, b_ in crossings(lab, n, vert):
        parent[find(a_)] = find(b_)
    groups = {}
    for i in range(1, n):
        if st[i, 4] >= SMALL:
            groups.setdefault(find(i), []).append(i)
    # Snap the right boundary to the printed rule when one is found near the
    # layout's estimate; the layout can sit a few tens of px past the real rule,
    # which lets the next column's first letters in.
    col_cover = vert.mean(axis=0)
    rules_near = [x for x in range(max(0, cx1 - 40), min(vert.shape[1], cx1 + 24)) if col_cover[x] > .8]
    right_limit = (min(rules_near) - 2 - 4) if rules_near else cx1 + 4
    keep, slack = [], []
    spans = {g: (min(st[i, 0] for i in m), max(st[i, 0] + st[i, 2] for i in m)) for g, m in groups.items()}
    for g, members in groups.items():
        start = spans[g][0]
        area = sum(st[i, 4] for i in members)
        inside = sum((lab[:, cx0:cx1] == i).sum() for i in members) / area
        # A word belongs to the cell it starts in. Layout column edges can be off by
        # a few tens of px, so a word starting just left of the edge but lying mostly
        # inside the cell may also belong here (checked below).
        if cx0 - 12 <= start < right_limit:
            keep += members
        elif cx0 - LEFT_SLACK <= start < cx0 - 12 and inside >= .6:
            slack.append(g)
    for g in slack:
        # ...unless it directly continues ink ending just to its left (the tail of
        # a word from the previous column): a real first letter has space before it.
        start = spans[g][0]
        tail = any(o != g and o not in slack and start - 22 <= spans[o][1] <= start + 4
                   and spans[o][0] < start - 4 for o in groups)
        if not tail:
            keep += groups[g]
    if not keep:
        return list(bbox), source[y0:y1, x0:x1], 'empty', None
    left = min(st[i, 0] for i in keep)
    right = max(st[i, 0] + st[i, 2] for i in keep)
    for i in range(1, n):                   # marks within the kept span stay
        a_, b_ = st[i, 0], st[i, 0] + st[i, 2]
        if st[i, 4] < SMALL and left - 4 <= a_ and (b_ <= right + 8 or (a_ < cx1 + 6 and a_ <= right + 30)):
            keep.append(i)                  # incl. line-end hyphens before the rule
    right = max(st[i, 0] + st[i, 2] for i in keep)
    drop = (lab > 0) & ~np.isin(lab, keep)
    drop = cv2.dilate(drop.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    drop &= ~cv2.dilate(np.isin(lab, keep).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    paper = int(np.median(gray[(lab == 0) & (vert == 0)]))
    gray[drop] = paper
    nx0, nx1 = max(0, left - PAD), min(wx1 - wx0, right + PAD)
    flag = 'ok'
    if right >= wx1 - wx0 - 3:
        flag = 'touches_window_edge'
    elif drop[:, nx0:nx1].any():
        flag = 'masked'
    return [int(wx0 + nx0), int(y0), int(wx0 + nx1), int(y1)], gray[:, nx0:nx1], flag, paper


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--in-json', default='training/line_proposals.json')
    ap.add_argument('--out-json', default='training/line_proposals_v2.json')
    ap.add_argument('--out-dir', default='training/proposals_v2')
    args = ap.parse_args()
    props = json.loads((BOOK / args.in_json).read_text())
    outdir = BOOK / args.out_dir
    outdir.mkdir(exist_ok=True)
    cache, out, stats = {}, [], {}
    for p in props:
        if p['source_image'] not in cache:
            src = ROOT / p['source_image']
            if hashlib.sha256(src.read_bytes()).hexdigest() != p['source_sha256']:
                raise SystemExit('Source checksum mismatch: ' + str(src))
            cache = {p['source_image']: np.array(Image.open(src).convert('L'))}
        source = cache[p['source_image']]
        bbox, crop, flag, paper = refine(source, p['bbox'])
        stats[flag] = stats.get(flag, 0) + 1
        path = outdir / f"{p['id']}.png"
        Image.fromarray(crop).save(path)
        q = dict(p, bbox=bbox, bbox_v1=p['bbox'], refine_flag=flag, mask_fill=paper,
                 image=str(path.relative_to(ROOT)),
                 image_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        out.append(q)
    (BOOK / args.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'proposals': len(out), 'flags': stats}))


if __name__ == '__main__':
    main()
