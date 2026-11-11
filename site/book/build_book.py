"""Build the reading book: page images, one JSON per spread, and the search index.

Run from the project root:
    .venv/bin/python -I site/book/build_book.py            # data only (fast)
    .venv/bin/python -I site/book/build_book.py --images   # also (re)cut the page images
    .venv/bin/python -I site/book/build_book.py --textiles site/book/img/src
Re-run whenever drafts or translations change; it reads whatever is in processed/.
"""
import html, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
import os
D = ROOT / os.environ.get("SAMOGITIA_BOOK", "data/plunge-1886-1890")
OUT = Path(os.environ.get("BOOK_OUT", Path(__file__).resolve().parent))
MODEL = os.environ.get("BOOK_MODEL", "plunge-v3")   # drafts/fields from this HTR model (training/runs/)
_years = os.environ.get("BOOK_YEARS")                 # e.g. "1896-1902" for another book
YEARS = ([(y, f"entries_{y}_{MODEL}.json") for y in range(int(_years.split("-")[0]), int(_years.split("-")[1]) + 1)]
         if _years else
         [(1886, f"entries_1886_{MODEL}.json"), (1887, f"entries_1887_{MODEL}.json"),
          (1888, f"entries_{MODEL}.json"), (1889, f"entries_1889_{MODEL}.json"),
          (1890, f"entries_1890_{MODEL}.json")])
TRANSLATIONS = os.environ.get("BOOK_TRANSLATIONS", "translations/translations_v3_book1.json")
PAGE_W = 1300
CELLS = ("baptism", "parents", "godparents")

def mark(text, names):
    """English draft -> HTML with uncertain readings, known names and editorial notes marked."""
    spans = []  # (start, end, cls, draft)
    def free(a, b):
        return all(b <= s or a >= e for s, e, *_ in spans)
    draft_note = {}
    for m in re.finditer(r"\s*\(draft '([^']*)'\)", text):
        draft_note[m.start()] = m
    # strip "(draft '..')" notes, remembering the reading for the word before
    carried = {}
    def strip(m):
        carried[len(out_parts[0])] = m.group(1)
        return ""
    out_parts = [""]
    pos = 0
    clean = ""
    for m in re.finditer(r"\s*\(draft '([^']*)'\)", text):
        clean += text[pos:m.start()]
        carried[len(clean)] = m.group(1)
        pos = m.end()
    clean += text[pos:]
    text = clean
    pairs = []
    for n in names:
        if "->" not in n:
            continue
        ru, en = [x.strip() for x in n.split("->", 1)]
        en = re.sub(r"\s*\[\?\]\s*$", "", en)
        en = re.sub(r"\s*\(.*?\)\s*$", "", en).strip()
        if len(en) > 1:
            pairs.append((en, ru))
    for en, ru in sorted(pairs, key=lambda p: -len(p[0])):
        m = re.search(r"(?<!\w)" + re.escape(en) + r"(?!\w)", text)
        i = m.start() if m else -1
        if i >= 0 and free(i, i + len(en)):
            spans.append((i, i + len(en), "nm", ru))
    # uncertainty marks: attach to the name or word just before
    drops = []
    for m in re.finditer(r"\s?\[\?\]", text):
        a = m.start()
        hit = next((k for k, s in enumerate(spans) if s[1] == a), None)
        if hit is not None:
            s = spans[hit]
            spans[hit] = (s[0], s[1], "u", carried.get(m.end(), s[3]))
        else:
            w = re.search(r"[^\s(\[]+$", text[:a])
            if w and free(w.start(), a):
                spans.append((w.start(), a, "u", carried.get(m.end())))
        drops.append((m.start(), m.end()))
    for m in re.finditer(r"\[[^\]?][^\]]*\]", text):
        if free(m.start(), m.end()):
            spans.append((m.start(), m.end(), "ed", None))
    events = sorted([(s, e, c, d) for s, e, c, d in spans] + [(s, e, "drop", None) for s, e in drops])
    out, pos = "", 0
    for s, e, c, d in events:
        if s < pos:
            continue
        out += html.escape(text[pos:s])
        if c != "drop":
            t = html.escape(text[s:e])
            dd = f' data-draft="{html.escape(d, quote=True)}"' if d else ""
            out += f'<span class="{c}"{dd}>{t}</span>'
        pos = e
    return out + html.escape(text[pos:])


def pct(v, lo, hi):
    return round(100 * (v - lo) / (hi - lo), 3)

def smooth(v, k=9):
    return np.convolve(v, np.ones(k) / k, mode="same")

def page_boxes(im):
    """Find the two paper rectangles on the black film, a little inside their edges."""
    W, H = im.size
    a = np.asarray(im.resize((W // 4, H // 4))) > 110
    h, w = a.shape
    g = int(w * .42) + int(np.argmin(smooth(a.mean(0), 15)[int(w * .42):int(w * .58)]))
    out = {}
    for side, (lo, hi) in {"L": (0, g), "R": (g, w)}.items():
        sub = a[:, lo:hi]
        rows = np.where(smooth(sub.mean(1)) > .45)[0]
        box = None
        if len(rows) > h * .3:
            y0, y1 = rows[0], rows[-1]
            cols = np.where(smooth(sub[y0 + (y1 - y0) // 10:y1 - (y1 - y0) // 10].mean(0)) > .45)[0]
            if len(cols) > w * .12:
                x0, x1 = cols[0] + lo, cols[-1] + lo
                ix, iy = int((x1 - x0) * .014), int((y1 - y0) * .009)
                box = [int(4 * (x0 + ix)), int(4 * (y0 + iy)), int(4 * (x1 - ix)), int(4 * (y1 - iy))]
        out[side] = box or ([0, 0, int(g * 4), H] if side == "L" else [int(g * 4), 0, W, H])
    hl, hr = out["L"][3] - out["L"][1], out["R"][3] - out["R"][1]
    if abs(hl - hr) < .04 * max(hl, hr):          # ordinary spread: give both pages one height
        m = min(hl, hr)
        for b in out.values():
            b[3] = int(b[1] + m)
    return out

_LAYOUT = {}
def layout_page(scan, side):
    """The layout step's record for one page side (cols, top, header_end), or None."""
    f = D / f"layout/{scan:04d}.json"
    if not f.exists():
        return None
    return next((p for p in json.loads(f.read_text())["pages"] if p["page"] == side), None)

def layout_cols(scan, side):
    """Absolute x positions of the printed column rules on one page side (from the layout step)."""
    if scan not in _LAYOUT:
        f = D / f"layout/{scan:04d}.json"
        _LAYOUT[scan] = {p["page"]: sorted(p.get("cols") or []) for p in json.loads(f.read_text())["pages"]} if f.exists() else {}
    return _LAYOUT[scan].get(side)

SIDE_WORDS = {"en": ("No.", {"M": "boy", "F": "girl"}, "born", "baptised", "Later note"),
              "lt": ("Nr.", {"M": "berniukas", "F": "mergaitė"}, "gimė", "pakrikštyta(s)", "Vėlesnė pastaba"),
              "ru": ("№", {}, "рожд.", "крещ.", "Позднейшая запись")}

def side_html(c, lang):
    """Printed columns 1-3 for one entry: margin surname, No., sex, days, later note."""
    no, sex, born, bapt, note = SIDE_WORDS[lang]
    name = c.get("margin_lt") if lang == "lt" else c.get("margin_en") if lang == "en" else c.get("margin_surname")
    bits = [c.get("entry_no") and f"{no} {c['entry_no']}",
            sex.get(c.get("sex")) if lang != "ru" else c.get("sex_letter"),
            c.get("birth_day") and f"{born} {c['birth_day']}", c.get("baptism_day") and f"{bapt} {c['baptism_day']}"]
    out = (f'<b>{html.escape(name)}</b><br>' if name else "") + html.escape(", ".join(b for b in bits if b))
    nt = c.get("notes_lt") if lang == "lt" else c.get("notes_en") if lang == "en" else c.get("notes_ru")
    if c.get("notes_ru"):
        out += f'<br><span class="ed">{html.escape(note)}: {html.escape(nt or c["notes_ru"])}</span>'
    return out

def main(args):
    P = D / "processed"
    tp = P / TRANSLATIONS
    tr = {e["row_id"]: e for e in json.loads(tp.read_text())} if tp.exists() else {}
    lt = {}
    for f in sorted(OUT.glob("lt_*.json")):      # earlier hand-made Lithuanian drafts, keyed by row
        lt.update(json.loads(f.read_text()))
    for row, t in tr.items():                     # full EN/LT translations take precedence
        if t.get("baptism_lt"):
            lt[row] = {c: t.get(c + "_lt") or "" for c in CELLS} | {"issues": t.get("issues_lt") or "", "issues_ru": ""}
    side_path = P / "side_columns.json"            # printed columns 1-3 (margin surname, No., dates, notes)
    side_cols = json.loads(side_path.read_text()) if side_path.exists() else {}
    cells = {}
    for name in ("line_proposals_years.json", "line_proposals.json"):
        if not (D / "training" / name).exists():
            continue
        for x in json.loads((D / "training" / name).read_text()):
            bb = x.get("bbox_v1") or x["bbox"]
            b = cells.setdefault((x["row_id"], x["cell"]), list(bb))
            b[0], b[1], b[2], b[3] = min(b[0], bb[0]), min(b[1], bb[1]), max(b[2], bb[2]), max(b[3], bb[3])
    index = build_index(tr)
    by = {r["row"]: r for r in index}
    per_scan = defaultdict(dict)
    for year, name in YEARS:
        for e in json.loads((P / name).read_text())["entries"]:
            if year == 1888 or e["row_id"] not in per_scan[e["scan"]]:
                per_scan[e["scan"]][e["row_id"]] = e
    boxes_path = OUT / "page_boxes.json"
    boxes = json.loads(boxes_path.read_text()) if boxes_path.exists() else {}
    scans = sorted(int(p.stem) for p in (D / "pages").glob("*.jpg"))
    (OUT / "spreads").mkdir(exist_ok=True)
    (OUT / "img/pages").mkdir(parents=True, exist_ok=True)
    manifest = []
    for scan in scans:
        key = f"{scan:04d}"
        need_img = "--images" in args or key not in boxes or not (OUT / f"img/pages/{key}_L.jpg").exists()
        if need_img:
            im = Image.open(D / f"pages/{key}.jpg").convert("L")
            boxes[key] = page_boxes(im)
            for side, b in boxes[key].items():
                p = im.crop(b)
                p.resize((PAGE_W, round(PAGE_W * p.height / p.width)), Image.LANCZOS).save(
                    OUT / f"img/pages/{key}_{side}.jpg", quality=76, optimize=True)
        spread = {"scan": scan, "pages": {s: {"img": f"img/pages/{key}_{s}.jpg", "w": b[2] - b[0], "h": b[3] - b[1]}
                                          for s, b in boxes[key].items()}, "entries": []}
        for row, e in per_scan.get(scan, {}).items():
            side = e["page"]
            x0, y0, x1, y1 = boxes[key][side]
            if not all((row, c) in cells for c in CELLS):
                continue
            bx = {}
            for c in CELLS:
                b = cells[(row, c)]
                bx[c] = [max(0, pct(b[0], x0, x1)), pct(b[1], y0, y1), min(99.4, pct(b[2], x0, x1)), pct(b[3], y0, y1)]
            sc = side_cols.get(row)
            lay = layout_cols(scan, side)
            sx0 = max(0.6, pct(lay[0], x0, x1)) if lay else 0.6
            sx1 = max(sx0 + 2, bx["baptism"][0] - 0.3)
            r, t = by[row], tr.get(row)
            names = t["names"] if t else []
            h = {"ru": {c: html.escape(e["text"].get(c) or "") for c in CELLS}}
            if sc:
                h["ru"]["side"] = side_html(sc, "ru")
            issues = {}
            if t:
                h["en"] = {c: mark(t[c + "_en"], names) for c in CELLS}
                if sc:
                    h["en"]["side"] = side_html(sc, "en")
                issues["en"] = t["issues"]
            if row in lt:
                h["lt"] = {c: mark(lt[row][c], names) for c in CELLS}
                if sc:
                    h["lt"]["side"] = side_html(sc, "lt")
                issues["lt"], issues["ru"] = lt[row]["issues"], lt[row]["issues_ru"]
            spread["entries"].append({
                "row": row, "n": r.get("n"), "side": side, "y": r["y"], "date": r.get("bapt"), "born": r.get("born"),
                "child": r.get("childEn", ""), "surname": r.get("surEn", ""), "surnameQ": r.get("surQ", False),
                "childRu": r.get("child", ""), "surnameRu": (r.get("sur", "").split() or [""])[-1],
                "band": [bx["baptism"][1], bx["baptism"][3]], "cells": bx, "html": h,
                "names": [n.split("->", 1) for n in names if "->" in n], "issues": issues,
                "sideCols": sc, "sideBox": [round(sx0, 3), bx["baptism"][1], round(sx1, 3), bx["baptism"][3]] if sc else None})
        spread["entries"].sort(key=lambda en: (en["side"], en["band"][0]))
        spread["heads"] = {}
        for side in ("L", "R"):
            lay = layout_page(scan, side)
            cols = sorted(lay.get("cols") or []) if lay else []
            if not lay or len(cols) < 7 or not lay.get("header_end") or not any(en["side"] == side for en in spread["entries"]):
                continue
            x0, y0, x1, y1 = boxes[key][side]
            k = next((i for i in range(len(cols) - 1) if cols[i + 1] - cols[i] > 450), None)
            if k is None or k < 3 or k + 3 >= len(cols):
                continue
            px = lambda v: round(max(0.3, min(99.7, pct(v, x0, x1))), 3)
            hy0, hy1 = round(max(0.2, pct(lay["top"], y0, y1)) + 0.15, 3), round(pct(lay["header_end"], y0, y1) - 0.15, 3)
            spans = [("margin", cols[0], cols[1]), ("no", cols[1], cols[2]), ("dates", cols[2], cols[k]),
                     ("baptism", cols[k], cols[k + 1]), ("parents", cols[k + 1], cols[k + 2]),
                     ("godparents", cols[k + 2], cols[k + 3]), ("sign", cols[k + 3], cols[-1])]
            spread["heads"][side] = [[name, px(a), px(b), hy0, hy1] for name, a, b in spans if px(b) - px(a) > 1]
        (OUT / f"spreads/{key}.json").write_text(json.dumps(spread, ensure_ascii=False))
        ys = Counter(en["y"] for en in spread["entries"])
        dates = sorted(en["date"] for en in spread["entries"] if en["date"] and len(en["date"]) >= 7)
        manifest.append({"scan": scan, "y": ys.most_common(1)[0][0] if ys else None, "n": len(spread["entries"]),
                         "from": dates[0][:7] if dates else None, "to": dates[-1][:7] if dates else None})
    boxes_path.write_text(json.dumps(boxes))
    (OUT / "data.js").write_text("window.SPREADS=" + json.dumps(manifest) + ";\nwindow.INDEX="
                                 + json.dumps(index, ensure_ascii=False) + ";\n")
    if "--textiles" in args:
        textiles(Path(args[args.index("--textiles") + 1]))
    print(len(scans), "spreads;", sum(m["n"] for m in manifest), "entries placed;", len(index), "in index")

def build_index(tr):
    """One compact search record per entry, every register year."""
    P = D / "processed"
    out = []
    for year, name in YEARS:
        for e in json.loads((P / name).read_text())["entries"]:
            f = {k: v.get("value") for k, v in e["fields"].items()}
            y = e.get("register_year") or year
            born = f.get("birth_date")
            if not born and f.get("birth_month") and f.get("birth_day"):
                by = y - 1 if f["birth_month"] == 12 and (f.get("baptism_month") or 12) == 1 else y
                born = f"{by}-{f['birth_month']:02d}-{f['birth_day']:02d}"
            bapt = f.get("baptism_date")
            if not bapt and f.get("baptism_month"):
                bapt = f"{y}-{f['baptism_month']:02d}" + (f"-{f['baptism_day']:02d}" if f.get("baptism_day") else "")
            r = {"row": e["row_id"], "y": y, "n": e.get("expected_entry_no"), "scan": e["scan"], "side": e["page"],
                 "sex": f.get("sex"), "child": f.get("child_name") or "", "father": f.get("father") or "",
                 "mother": f.get("mother") or "", "sur": f.get("maiden_and_surname") or "",
                 "vil": f.get("village") or "", "god": f.get("godparents") or "", "priest": f.get("priest") or "",
                 "bapt": bapt, "born": born}
            t = tr.get(e["row_id"])
            if t:
                m = re.search(r"named (.+?)(?: with all|\s*\(draft|$)", t["baptism_en"])
                r["childEn"] = re.sub(r"\s*\[.*?\]", "", m.group(1)).strip() if m else ""
                clean = lambda x: re.sub(r"\s*\[.*?\]|\s*\(draft.*?\)", "", x)
                r["parEn"] = re.sub(r", lawfully.*$", "", clean(t["parents_en"]))
                née = re.search(r"née\s+(.+)$", r["parEn"])
                parts = [w for w in re.split(r"[,\s]+", née.group(1)) if w and w != "surname"] if née else []
                if len(parts) > 1:
                    r["surEn"] = " ".join(parts[1:])
                    raw = re.search(r"née(.+?)(?:, lawfully|$)", t["parents_en"])
                    r["surQ"] = bool(raw and "[?]" in raw.group(1).split(parts[0], 1)[-1])
                r["en"] = " ".join(clean(n.split("->", 1)[1]) for n in t["names"] if "->" in n)
            out.append({k: v for k, v in r.items() if v not in ("", None)})
    return out

CLOTHS = {"plunge": "1056757085", "telsiai": "1057411152", "kretinga": "1059250648"}
RIBBONS = {"mazeikiai": ("914006288", 1), "taurage": ("914017553", 1), "ukrinai": ("914014451", 1)}

def textiles(src):
    for name, lid in CLOTHS.items():
        im = Image.open(src / f"{lid}.jpg").convert("RGB")
        w, h = im.size
        mx, my = {"kretinga": (.14, .12), "telsiai": (.09, .11)}.get(name, (.05, .06))
        im.crop((int(w * mx), int(h * my), int(w * (1 - mx)), int(h * (1 - my)))).save(OUT / f"img/cloth-{name}.jpg", quality=84)
    for name, (lid, which) in RIBBONS.items():
        im = Image.open(src / f"{lid}.jpg").convert("RGB")
        a = np.asarray(im).astype(float) / 255
        mx, mn = a.max(2), a.min(2)
        sat = (mx - mn) / np.maximum(mx, 1e-6)
        fg = (sat > .2) | (mx < .62)
        m = Image.fromarray((fg * 255).astype("uint8")).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9))
        fgc = np.asarray(m) > 127
        col = fgc.mean(0) > .08
        runs, s = [], None
        for i, b in enumerate(list(col) + [False]):
            if b and s is None: s = i
            if not b and s is not None:
                if i - s > 12: runs.append((s, i))
                s = None
        x0, x1 = runs[min(which, len(runs) - 1)]
        rows = np.where(fgc[:, x0:x1].mean(1) > .1)[0]
        y0, y1 = rows[0], rows[-1] + 1
        rgba = np.dstack([np.asarray(im)[y0:y1, x0:x1], (fgc[y0:y1, x0:x1] * 255).astype("uint8")])
        out = Image.fromarray(rgba, "RGBA")
        out.putalpha(out.getchannel("A").filter(ImageFilter.GaussianBlur(.8)))
        # straighten: slide every row sideways so the strand's centre line is vertical
        arr = np.asarray(out)
        h, w = arr.shape[:2]
        al = arr[..., 3].astype(float)
        xs = np.arange(w)
        cen = np.where(al.sum(1) > 0, (al * xs).sum(1) / np.maximum(al.sum(1), 1), np.nan)
        ok = ~np.isnan(cen)
        cen = np.interp(np.arange(h), np.arange(h)[ok], cen[ok])
        k = 61
        cen = np.convolve(np.pad(cen, k // 2, mode="edge"), np.ones(k) / k, mode="valid")
        pad = int(np.ceil(np.abs(cen - w / 2).max())) + 2
        wide = np.zeros((h, w + 2 * pad, 4), dtype=np.uint8)
        for y in range(h):
            dx = pad + int(round(w / 2 - cen[y]))
            wide[y, dx:dx + w] = arr[y]
        cols = np.where(wide[..., 3].max(0) > 8)[0]
        half = max(wide.shape[1] / 2 - cols[0], cols[-1] + 1 - wide.shape[1] / 2)
        c0 = int(wide.shape[1] / 2 - half); c1 = int(np.ceil(wide.shape[1] / 2 + half))
        wide = wide[:, c0:c1]
        out = Image.fromarray(wide, "RGBA")
        w, h = out.size
        # lengthen: loop the upper body where the braid best matches its own start, crossfaded
        ov = 48
        a0 = int(h * .06)
        f = wide.astype(float)
        best = min(range(int(h * .40), int(h * .66)), key=lambda b: np.abs(f[b:b + ov] - f[a0:a0 + ov]).mean())
        body = out.crop((0, a0, w, best + ov))
        long = body
        target = 47 * 99
        pieces = []
        while a0 and (len(pieces) + 1) * (best - a0) + (h - a0) < target:
            pieces.append(body)
        for nxt in pieces + [out.crop((0, a0, w, h))]:
            canvas = Image.new("RGBA", (w, long.height + nxt.height - ov))
            canvas.paste(long.crop((0, 0, w, long.height - ov)), (0, 0))
            ramp = np.linspace(0, 1, ov)[:, None, None]
            old = np.asarray(long.crop((0, long.height - ov, w, long.height))).astype(float)
            newp = np.asarray(nxt.crop((0, 0, w, ov))).astype(float)
            canvas.paste(Image.fromarray((old * (1 - ramp) + newp * ramp).astype("uint8"), "RGBA"), (0, long.height - ov))
            canvas.paste(nxt.crop((0, ov, w, nxt.height)), (0, long.height))
            long = canvas
        long.save(OUT / f"img/ribbon-{name}.webp", quality=86, method=6)
        print(name, long.size)


main(sys.argv[1:])
