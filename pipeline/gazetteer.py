"""Rank modern place candidates; never turn a fuzzy match into a transcription.

Run: .venv/bin/python -I pipeline/gazetteer.py
Scores are string similarities, NOT probabilities or historical identifications.
"""
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "data/plunge-1886-1890"
GAZETTEER = ROOT / "data/gazetteer/osm_places_plunge_20km.json"
CYRILLIC = dict(zip("абвгдежзийклмнопрстуфхцчэыэюяѣіѳ", [
    "a", "b", "v", "g", "d", "e", "zh", "z", "i", "i", "k", "l", "m", "n", "o", "p", "r", "s", "t", "u", "f", "h", "ts", "ch", "e", "i", "e", "iu", "ia", "e", "i", "f"
]))
CYRILLIC.update({"ё": "e", "ш": "sh", "щ": "shch", "ь": "", "ъ": ""})


def key(value):
    if value is None:
        return ""
    value = str(value).lower().strip()
    # Bracketed editorial text is not a place-name. Retain the letters outside it.
    value = re.sub(r"\[[^\]]*\]|\([^)]*\)", "", value)
    value = re.sub(r"^(?:въ\s+)?(?:деревн[ѣеяи]|д[.:]|м[.:]|мѣстечк[ѣе])\s*", "", value)
    value = value.replace("ł", "l").replace("š", "sh").replace("č", "ch").replace("ž", "zh")
    value = "".join(CYRILLIC.get(c, c) for c in value)
    value = "".join(c for c in unicodedata.normalize("NFKD", value) if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", value)


def distance(a, b):
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        new = [i]
        for j, cb in enumerate(b, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j-1] + (ca != cb)))
        row = new
    return row[-1]


def similarity(a, b):
    return 1 - distance(a, b) / max(len(a), len(b), 1)


def variants(value):
    k = key(value)
    if len(k) < 3:
        return []
    out = [(k, "full")]
    # Inflection-only comparison is a secondary heuristic, never an asserted alias.
    for suffix in ("iai", "yany", "iany", "ani", "ai", "ei", "oi", "iu", "i", "y", "a", "e", "u", "as", "is"):
        if k.endswith(suffix) and len(k) - len(suffix) >= 4:
            out.append((k[:-len(suffix)], "stem"))
    return out


def load_places(path=GAZETTEER):
    places = []
    for e in json.loads(path.read_text())["elements"]:
        tags = e.get("tags", {})
        if not tags.get("name"):
            continue
        aliases = []
        for tag, value in tags.items():
            if tag in ("name", "alt_name", "old_name", "official_name") or tag.startswith(("name:", "alt_name:", "old_name:")):
                for alias in value.split(";"):
                    if variants(alias):
                        aliases.append((alias.strip(), tag))
        center = e.get("center", e)
        places.append({"place_id": f"osm:{e['type']}:{e['id']}", "name": tags['name'],
                       "lat": center.get("lat"), "lon": center.get("lon"), "aliases": aliases})
    return places


def candidates(value, places, limit=5):
    query = variants(value)
    if not query:
        return []
    ranked = []
    for place in places:
        best = (0.0, "", "", "")
        for alias, tag in place["aliases"]:
            for a, ak in query:
                for b, bk in variants(alias):
                    penalty = 0.08 if "stem" in (ak, bk) else 0
                    score = max(0, similarity(a, b) - penalty)
                    if score > best[0]:
                        best = (score, alias, tag, f"{ak}/{bk}")
        ranked.append({k: v for k, v in place.items() if k != "aliases"} | {
            "score": round(best[0], 4), "matched_alias": best[1], "alias_tag": best[2], "method": best[3]})
    ranked.sort(key=lambda c: (-c['score'], c['place_id']))
    return ranked[:limit]


def proposal(value, places):
    ranked = candidates(value, places)
    margin = round(ranked[0]['score'] - ranked[1]['score'], 4) if len(ranked) > 1 else 0
    return {"original": value, "key": key(value), "candidates": ranked, "margin": margin,
            "status": "candidate_only" if ranked else "no_readable_name",
            "separated_candidate": bool(ranked and ranked[0]['score'] >= .65 and margin >= .08),
            "confirmed_place_id": None}


def main():
    places = load_places()
    readings = []
    lookup = {}
    files = sorted((BOOK/'reads').glob('*.json'))
    for path in files:
        if 'merged' in path.name:
            continue
        for entry in json.loads(path.read_text()):
            item = {"source_file": path.name, "scan": entry['scan'], "entry_no": entry['entry_no'],
                    **proposal(entry.get('village_ru'), places)}
            readings.append(item)
            lookup[(path.name, entry['scan'], entry['entry_no'])] = item
    comparisons = []
    for a in [p for p in files if p.name.startswith('rowA')]:
        b = a.name.replace('rowA', 'rowB', 1)
        for ea in json.loads(a.read_text()):
            ra = lookup[(a.name, ea['scan'], ea['entry_no'])]
            rb = lookup.get((b, ea['scan'], ea['entry_no']))
            if rb is None:
                continue
            usable = bool(ra['key'] and rb['key'])
            same = bool(ra['candidates'] and rb['candidates'] and ra['candidates'][0]['place_id'] == rb['candidates'][0]['place_id'])
            comparisons.append({"scan": ea['scan'], "entry_no": ea['entry_no'],
                "a": ra['original'], "b": rb['original'], "comparable": usable,
                "same_normalized_reading": usable and ra['key'] == rb['key'],
                "same_top_candidate": same,
                "same_separated_candidate": same and ra['separated_candidate'] and rb['separated_candidate'],
                "candidate_a": ra['candidates'][0]['name'] if ra['candidates'] else None,
                "candidate_b": rb['candidates'][0]['name'] if rb['candidates'] else None})
    summary = {"named_places": len(places), "pairs": len(comparisons),
        **{k: sum(bool(c[k]) for c in comparisons) for k in ['comparable', 'same_normalized_reading', 'same_top_candidate', 'same_separated_candidate']},
        "confirmed_matches": 0, "warning": "Candidate convergence is not accuracy. The 20 km modern gazetteer is not a complete historical parish gazetteer."}
    out = BOOK/'review'
    out.mkdir(exist_ok=True)
    payload = {"gazetteer": str(GAZETTEER.relative_to(ROOT)), "gazetteer_sha256": hashlib.sha256(GAZETTEER.read_bytes()).hexdigest(),
        "license": "OpenStreetMap contributors, ODbL 1.0", "summary": summary, "readings": readings, "comparisons": comparisons}
    (out/'village_candidates.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2)+'\n')
    with (out/'village_comparison.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(comparisons[0]))
        w.writeheader(); w.writerows(comparisons)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
