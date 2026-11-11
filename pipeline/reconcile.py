"""Stage 3: compare two independent reads of the same entries, field by field.

usage: reconcile.py <read_a.json> <read_b.json> [<out.json>]
A field 'agrees' when both reads give the same text after removing uncertainty marks, case and hard signs.
Writes a merged file where agreed fields are kept and disagreements carry both readings.
"""
import json, re, sys

FIELDS = ["sex", "birth_date", "baptism_date", "child_name_ru", "estate_township_ru", "father_name_ru",
          "mother_name_ru", "mother_maiden_ru", "surname_ru", "surname_margin_ru", "village_ru", "godparents_ru"]

def norm(v):
    if v is None: return ""
    v = re.sub(r"\[[^\]]*\]|\(.*?\)", "", str(v)).lower()
    v = v.replace("ъ", "").replace("ѣ", "е").replace("і", "и")
    return re.sub(r"[^0-9a-zа-яё]+", "", v)

def compare(a, b):
    def index(entries):
        result = {}
        for e in entries:
            key = (e["scan"], e["entry_no"])
            if key in result:
                raise ValueError(f"Duplicate scan/entry: {key}")
            result[key] = e
        return result
    A = index(a); B = index(b)
    stats = {f: [0, 0] for f in FIELDS}
    merged = []
    for key in sorted(set(A) | set(B)):
        no = key[1]
        ea, eb = A.get(key), B.get(key)
        if not ea or not eb:
            merged.append({"entry_no": no, "status": "only_in_" + ("a" if ea else "b"), **(ea or eb)}); continue
        m = {"entry_no": no, "scan": ea.get("scan"), "row_image": ea.get("row_image"),
             "status": "unreviewed", "disagree": {}, "missing_both": []}
        for f in FIELDS:
            va, vb = norm(ea.get(f)), norm(eb.get(f))
            # Two empty/unreadable values do not provide corroborating evidence.
            same = bool(va and vb and va == vb)
            stats[f][0] += same; stats[f][1] += 1
            if same: m[f] = ea.get(f)
            elif not va and not vb:
                m[f] = None
                m["missing_both"].append(f)
            else: m["disagree"][f] = [ea.get(f), eb.get(f)]
        m["flagged_by_reader"] = sorted(set(ea.get("uncertain", [])) | set(eb.get("uncertain", [])))
        m["notes"] = [ea.get("notes"), eb.get("notes")]
        merged.append(m)
    return stats, merged

if __name__ == "__main__":
    a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
    stats, merged = compare(a, b)
    print(f"entries: a={len(a)} b={len(b)}")
    for f, (ok, n) in stats.items():
        print(f"  {f:20s} {ok}/{n}")
    tot = sum(v[0] for v in stats.values()); n = sum(v[1] for v in stats.values())
    print(f"  overall {tot}/{n} = {100*tot/max(n,1):.0f}%")
    if len(sys.argv) > 3:
        json.dump(merged, open(sys.argv[3], "w"), ensure_ascii=False, indent=1)
