"""Stage 1: page layout. Find the ruled table on each register spread and cut it into entry rows and columns.

usage: layout.py <pages dir> <out dir> <first scan> <last scan>
Writes <out>/layout/NNNN.json (boxes), <out>/rows/NNNN_<page><row>.jpg (one image per entry row)
and <out>/debug/NNNN.jpg (overlay for checking by eye).
"""
import json, os, sys
import cv2
import numpy as np

MIN_ROW_H = 260        # px; a baptism entry is never shorter than this at these scan sizes
HEADER_MAX_Y = 0.30    # the printed header ends within the top 30% of the page

def band_positions(ink, axis, nb, klen, cover):
    """Ruled-line positions found separately in nb bands, so tilted or warped lines still register."""
    n = ink.shape[1] if axis == 0 else ink.shape[0]
    edges = np.linspace(0, n, nb + 1).astype(int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        if axis == 0:      # horizontal lines: look in a vertical strip
            strip = cv2.dilate(ink[:, a:b], np.ones((5, 1), np.uint8))
            op = cv2.morphologyEx(strip, cv2.MORPH_OPEN, np.ones((1, klen), np.uint8))
            prof = op.sum(axis=1) / 255.0
        else:              # vertical lines: look in a horizontal strip
            strip = cv2.dilate(ink[a:b, :], np.ones((1, 5), np.uint8))
            op = cv2.morphologyEx(strip, cv2.MORPH_OPEN, np.ones((klen, 1), np.uint8))
            prof = op.sum(axis=0) / 255.0
        hits = np.where(prof > cover * (b - a))[0]
        groups = []
        for h in hits:
            if groups and h - groups[-1][-1] <= 10: groups[-1].append(h)
            else: groups.append([h])
        out.append([float(np.mean(g)) for g in groups])
    return out

def link(bands, tol=40, need=0.6):
    """Join per-band positions into lines; returns one position per band (nan if missing) for each line."""
    nb = len(bands)
    seed = max(range(nb), key=lambda i: len(bands[i]))
    lines = []
    for y0 in bands[seed]:
        row = [np.nan] * nb; row[seed] = y0
        for step in (1, -1):
            cur, i = y0, seed + step
            while 0 <= i < nb:
                if bands[i]:
                    j = min(bands[i], key=lambda v: abs(v - cur))
                    if abs(j - cur) <= tol: row[i] = j; cur = j
                i += step
        if np.sum(~np.isnan(row)) >= need * nb: lines.append(row)
    return lines

def analyse(gray):
    H, W = gray.shape
    page = cv2.morphologyEx((gray > 90).astype(np.uint8) * 255, cv2.MORPH_CLOSE, np.ones((61, 61), np.uint8))
    page = cv2.erode(page, np.ones((15, 15), np.uint8))
    # local contrast, so faint pencil-thin rules count as well as heavy ink
    local = cv2.adaptiveThreshold(cv2.GaussianBlur(gray, (3, 3), 0), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 41, 10)
    ink = ((local > 0) & (page > 0)).astype(np.uint8) * 255
    pages = []
    mid = W // 2
    for name, x0, x1 in (("L", 0, mid), ("R", mid, W)):
        sub = ink[:, x0:x1]
        cols_on = np.where(page[:, x0:x1].mean(axis=0) > 128)[0]
        if len(cols_on) < 500:
            pages.append({"page": name, "ok": False}); continue
        px0, px1 = int(cols_on[0]), int(cols_on[-1])
        sub = sub[:, px0:px1]
        hl = link(band_positions(sub, 0, 8, 100, 0.40), need=0.5)
        vl = link(band_positions(sub, 1, 8, 120, 0.50), need=0.5)
        hs = sorted(float(np.nanmedian(r)) for r in hl)
        vs = sorted(float(np.nanmedian(r)) for r in vl)
        if len(vs) < 3 or len(hs) < 3:
            pages.append({"page": name, "ok": False, "v": vs, "h": hs}); continue
        left, right = vs[0], vs[-1]
        top, bottom = hs[0], hs[-1]
        body = [h for h in hs if h > top + 150]
        head_end = body[0] if body else top
        cuts = [head_end]
        for h in hs:
            if h > cuts[-1] + MIN_ROW_H: cuts.append(h)
        # the table's foot is often unruled: take it from where the vertical rules stop
        vop = cv2.morphologyEx(cv2.dilate(sub, np.ones((1, 5), np.uint8)), cv2.MORPH_OPEN, np.ones((120, 1), np.uint8))
        ys = np.where(vop.sum(axis=1) / 255.0 >= 3 * 3)[0]       # at least three rules present
        foot = float(ys[-1]) if len(ys) else bottom
        if foot > cuts[-1] + MIN_ROW_H: cuts.append(foot)
        rows = [{"y0": int(a), "y1": int(b)} for a, b in zip(cuts[:-1], cuts[1:])]
        med = float(np.median([r["y1"] - r["y0"] for r in rows])) if rows else 0
        for r in rows:
            r["suspect"] = bool(med and (r["y1"] - r["y0"]) > 1.6 * med)
        pages.append({"page": name, "ok": True, "x0": int(x0 + px0 + left), "x1": int(x0 + px0 + right),
                      "top": int(top), "bottom": int(bottom), "header_end": int(head_end),
                      "cols": [int(x0 + px0 + v) for v in vs], "hlines": [int(h) for h in hs], "rows": rows})
    return pages

if __name__ == "__main__":
    src, out, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    for d in ("layout", "rows", "debug"): os.makedirs(f"{out}/{d}", exist_ok=True)
    for n in range(a, b + 1):
        p = f"{src}/{n:04d}.jpg"
        if not os.path.exists(p): continue
        gray = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        pages = analyse(gray)
        dbg = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        nrows = []
        for pg in pages:
            if not pg["ok"]:
                nrows.append("FAIL"); continue
            for c in pg["cols"]: cv2.line(dbg, (c, pg["top"]), (c, pg["bottom"]), (255, 160, 0), 4)
            for i, r in enumerate(pg["rows"], 1):
                cv2.rectangle(dbg, (pg["x0"], r["y0"]), (pg["x1"], r["y1"]), (0, 0, 255), 6)
                cv2.putText(dbg, f"{pg['page']}{i}", (pg["x0"] + 20, r["y0"] + 90), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 8)
                pad = 25
                crop = gray[max(0, r["y0"] - 40): r["y1"] + 110, max(0, pg["x0"] - 230): pg["x1"] + 30]   # text often runs below the rule
                cv2.imwrite(f"{out}/rows/{n:04d}_{pg['page']}{i}.jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
            nrows.append(str(len(pg["rows"])) + ("!" if any(r.get("suspect") for r in pg["rows"]) else ""))
        json.dump({"scan": n, "size": [int(gray.shape[1]), int(gray.shape[0])], "pages": pages}, open(f"{out}/layout/{n:04d}.json", "w"), indent=1)
        cv2.imwrite(f"{out}/debug/{n:04d}.jpg", cv2.resize(dbg, None, fx=0.35, fy=0.35), [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(n, "rows L/R:", nrows, "cols:", [len(pg.get("cols", [])) for pg in pages])
