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
  5. paints out ink of the lines above and below: pieces that are cut by the line's top or
     bottom edge and do not reach the body of its letters (descender tips from the line
     above, ascender tips from below, and, for writing that runs at a slope, the parts of
     the neighbouring lines inside the upright box). Needs the `line` record written by
     segment_lines.py; without it this step is skipped,
  6. crops to the kept span with small padding; for sloped writing the box is the upright
     box around the line over the kept span only.
The label for a crop is exactly the complete characters visible in it.

A word that crosses a rule belongs to the cell it starts in, and its tail beyond the rule
goes with it. A whole word beyond the rule is not a tail: a capital's lead-in stroke or a
line-end hyphen touching the rule from the other side does not make two words one.
Crops left with no writing (less ink than one letter: a rule, a tear, a stray stroke) are
not written to the output; they are listed in <out-json stem>_dropped.json.

Otherwise vertical extents are unchanged. Output: training/line_proposals_v2.json and
training/proposals_v2/*.png. The v1 file is preserved. These remain proposals:
every crop still needs visual review before its text can become a label.

Run: .venv/bin/python -I pipeline/refine_lines.py
"""
import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segment_lines import horizontal_rules, rel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')
REACH = 220      # how far beyond the cell to look for overrunning words (px)
LEFT_SLACK = 45  # px a word may start left of the cell edge if mostly inside
SMALL = 40       # components below this area are marks (dots, diacritics, commas)
PAD = 10
WORD = 120       # an unbroken run of ink this wide is a word of its own, not a word's tail
WORD_GAP = 12    # gaps up to this wide lie inside a word
STRAY = 300      # px of ink above which a piece away from the letter bodies cannot be a mark
MIN_TEXT = 24    # a crop whose ink covers fewer columns than this (less than one letter wide) ...
MIN_HEIGHT = 12  # ... or fewer rows than this (a leftover piece of a rule) ...
MIN_INK = 700    # ... or fewer pixels than this (two short letters) holds no writing


def ink_and_rules(gray):
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 41, 12)
    # a column rule on a page that lies a little askew leans by a few px over its length:
    # look for it in ink widened by a pixel each way, and keep only the ink itself
    wide = cv2.dilate(ink, np.ones((1, 3), np.uint8))
    vert = cv2.morphologyEx(wide, cv2.MORPH_OPEN, np.ones((120, 1), np.uint8)) & ink
    vert = cv2.dilate(vert, np.ones((3, 5), np.uint8))
    return cv2.subtract(ink, vert | horizontal_rules(ink)), vert


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


def run_width(st, first):
    """Width of the unbroken run of ink (a word) that starts with component `first`."""
    x0 = st[first, 0]
    end = x0 + st[first, 2]
    for i in sorted((i for i in range(1, len(st)) if st[i, 4] >= SMALL and st[i, 0] > x0), key=lambda i: st[i, 0]):
        if st[i, 0] > end + WORD_GAP:
            break
        end = max(end, st[i, 0] + st[i, 2])
    return end - x0


def refine(source, bbox, line=None):
    """Return (bbox, crop_image, flag, fill). Ink belonging to other cells, and with `line`
    (see segment_lines.py) to the lines above and below, is painted out."""
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
        if run_width(st, b_) < WORD:       # the ink beyond the rule is a tail, not a word of its own
            parent[find(a_)] = find(b_)
    other = np.zeros(n, bool)               # pieces of the lines above and below
    if line:
        ys, xs = np.nonzero(lab)
        ids = lab[ys, xs]
        level = ys + y0 - line['slope'] * (xs + wx0 - line['x'])      # row at the line's reference column
        (top, bottom), (c0, c1) = line['band'], line['core']
        cut = np.bincount(ids, (level <= top + 1) | (level >= bottom - 2), n) > 0
        body = np.bincount(ids, (level >= c0) & (level <= c1), n) > 0
        other = cut & ~body
        # Every letter has part of itself in the body rows; only marks (dots, commas, raised
        # endings) lie wholly above or below. A word-sized piece that does not come within
        # 6 px of the body is the neighbouring line's, also when the edge does not cut it.
        near = np.bincount(ids, (level >= c0 - 6) & (level <= c1 + 6), n) > 0
        other |= ~near & (st[:, 4] >= STRAY) & (st[:, 2] >= SMALL)
    groups = {}
    for i in range(1, n):
        if st[i, 4] >= SMALL and not other[i]:
            groups.setdefault(find(i), []).append(i)
    # Snap the right boundary to the printed rule when one is found near the
    # layout's estimate; the layout can sit a few tens of px past the real rule,
    # which lets the next column's first letters in.
    lean = 3                                # a leaning rule covers no single column: count it within 3 px
    col_cover = cv2.dilate(vert, np.ones((1, 2 * lean + 1), np.uint8)).mean(axis=0)
    rules_near = [x for x in range(max(0, cx1 - 40), min(vert.shape[1], cx1 + 24)) if col_cover[x] > .8]
    right_limit = (min(rules_near) + lean - 2 - 4) if rules_near else cx1 + 4
    # The same on the left: a word that starts right of the printed rule starts in this cell,
    # whatever ends just before the rule. Without a rule the layout's edge is used.
    rules_near = [x for x in range(max(0, cx0 - 48 - lean), min(vert.shape[1], cx0 + 16 + lean)) if col_cover[x] > .8]
    left_limit = cx0 - 12
    if rules_near:                          # left edge of the rule nearest the cell
        left_limit = max(rules_near)
        while left_limit - 1 in rules_near:
            left_limit -= 1
        left_limit += lean
    keep, slack = [], []
    spans = {g: (min(st[i, 0] for i in m), max(st[i, 0] + st[i, 2] for i in m)) for g, m in groups.items()}
    for g, members in groups.items():
        start = spans[g][0]
        area = sum(st[i, 4] for i in members)
        inside = sum((lab[:, cx0:cx1] == i).sum() for i in members) / area
        # A word belongs to the cell it starts in. Layout column edges can be off by
        # a few tens of px, so a word starting just left of the edge but lying mostly
        # inside the cell may also belong here (checked below).
        if left_limit <= start < right_limit:
            keep += members
        elif cx0 - LEFT_SLACK <= start < left_limit and inside >= .6:
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
        if st[i, 4] < SMALL and not other[i] and left - 4 <= a_ and (b_ <= right + 8 or (a_ < cx1 + 6 and a_ <= right + 30)):
            keep.append(i)                  # incl. line-end hyphens before the rule
    right = max(st[i, 0] + st[i, 2] for i in keep)
    kept = np.isin(lab, keep)
    need = 2 if line and line.get('faint') else 1      # a faint line must show a short word, not a mark
    if kept.any(axis=0).sum() < need * MIN_TEXT or kept.sum() < need * MIN_INK or kept.any(axis=1).sum() < MIN_HEIGHT:
        return list(bbox), source[y0:y1, x0:x1], 'no_text', None
    drop = (lab > 0) & ~np.isin(lab, keep)
    drop = cv2.dilate(drop.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    drop &= ~cv2.dilate(kept.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    paper = int(np.median(gray[(lab == 0) & (vert == 0)]))
    gray[drop] = paper
    nx0, nx1 = max(0, left - PAD), min(wx1 - wx0, right + PAD)
    flag = 'ok'
    if right >= wx1 - wx0 - 3:
        flag = 'touches_window_edge'
    elif drop[:, nx0:nx1].any():
        flag = 'masked'
    ny0, ny1 = 0, y1 - y0
    if line and line['slope']:              # sloped writing: the upright box around the line over the kept span
        ends = [line['slope'] * (wx0 + x - line['x']) for x in (nx0, nx1)]
        ny0 = max(ny0, int(np.floor(line['band'][0] + min(ends))) - y0)
        ny1 = min(ny1, int(np.ceil(line['band'][1] + max(ends))) - y0)
    return [int(wx0 + nx0), int(y0 + ny0), int(wx0 + nx1), int(y0 + ny1)], gray[ny0:ny1, nx0:nx1], flag, paper


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--in-json', default='training/line_proposals.json')
    ap.add_argument('--out-json', default='training/line_proposals_v2.json')
    ap.add_argument('--out-dir', default='training/proposals_v2')
    args = ap.parse_args()
    props = json.loads((BOOK / args.in_json).read_text())
    outdir = BOOK / args.out_dir
    outdir.mkdir(parents=True, exist_ok=True)
    cache, out, stats, dropped = {}, [], {}, []
    for p in props:
        if p['source_image'] not in cache:
            src = ROOT / p['source_image']
            if hashlib.sha256(src.read_bytes()).hexdigest() != p['source_sha256']:
                raise SystemExit('Source checksum mismatch: ' + str(src))
            cache = {p['source_image']: np.array(Image.open(src).convert('L'))}
        source = cache[p['source_image']]
        bbox, crop, flag, paper = refine(source, p['bbox'], p.get('line'))
        stats[flag] = stats.get(flag, 0) + 1
        if flag in ('empty', 'no_text'):    # nothing to read: no crop, no proposal
            dropped.append({'id': p['id'], 'bbox_v1': p['bbox'], 'reason': flag})
            continue
        path = outdir / f"{p['id']}.png"
        Image.fromarray(crop).save(path)
        q = dict(p, bbox=bbox, bbox_v1=p['bbox'], refine_flag=flag, mask_fill=paper,
                 image=rel(path),
                 image_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        out.append(q)
    (BOOK / args.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    out_json = BOOK / args.out_json
    out_json.with_name(out_json.stem + '_dropped.json').write_text(json.dumps(dropped, indent=1) + '\n')
    print(json.dumps({'proposals': len(out), 'flags': stats}))


if __name__ == '__main__':
    main()
