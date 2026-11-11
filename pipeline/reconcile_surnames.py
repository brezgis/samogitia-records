"""Reconcile the two writings of each entry's family surname.

Every entry carries the surname twice: sideways in the margin (printed column 1, "Прозваніе
крещаемыхъ", read from the image by an agent -> processed/side_columns.json) and inside the
parents column ("... изъ [maiden] [SURNAME] законныхъ супруговъ ...", machine draft ->
processed/entries_<year>_<model>.json, field maiden_and_surname). They are the same name written
twice by the clerk, so they are evidence for one surname, not two surnames.

Usage: SAMOGITIA_BOOK=data/<book> .venv/bin/python -I pipeline/reconcile_surnames.py MODEL
  e.g. ... reconcile_surnames.py plunge-v6
Writes processed/surnames.json: {row_id: {margin_ru, draft_ru, similarity, status, surname_ru,
nominative_ru, en, lt, uncertain}} and prints the status counts.

status:
  agree          both readings give the same stem (or nearly): corroborated
  margin         the draft is a garbled/partial version of the margin name: margin reading used
  margin_only    no usable surname in the draft: margin reading used
  conflict       two full, different names: margin reading used, both shown, needs a look
  draft_only     no margin reading: draft used
Nothing here is verified: the margin is a single agent reading and the draft is machine output.
"""
import difflib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / os.environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')

EN = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'i',
      'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
      'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'iu',
      'я': 'ia', 'ѣ': 'e', 'і': 'i', 'ѳ': 'f', 'ѵ': 'i'}
LT = {**EN, 'ж': 'ž', 'й': 'j', 'х': 'ch', 'ц': 'c', 'ч': 'č', 'ш': 'š', 'щ': 'šč', 'ю': 'ju', 'я': 'ja'}
# genitive-plural family forms -> nominative singular: (pattern, Russian, English tail, Lithuanian tail)
ENDINGS = [
    (r'скихъ?$', 'скій', 'skii', 'skis'),
    (r'цкихъ?$', 'цкій', 'tskii', 'ckis'),
    (r'(?:е|о)?вичей$', 'вичъ', 'vich', 'vičius'),
    (r'ичей$', 'ичъ', 'ich', 'ičius'),
    (r'(?<=[аиуыюеоія]с)[оіе]въ?$', '', '', ''),     # Шимкусовъ -> Шимкус, Поціусовъ -> Поціус
]


def letters(s):
    """The Cyrillic letters of a reading, without the reader's [?] marks and punctuation."""
    return re.sub(r'[^а-яёѣіѳѵ]', '', (s or '').lower())


def stem(s):
    """Comparison key: spelling variants and case endings removed."""
    s = letters(s).replace('ъ', '').replace('ѣ', 'е').replace('і', 'и').replace('ё', 'е').replace('й', 'и')
    s = re.sub(r'(ихъ|ыхъ|их|ых|ии|ои|аго)$', '', s)
    s = re.sub(r'(ичеи)$', 'ич', s)
    return re.sub(r'(иов|ов|ев|еи|а|я|у|ю|ы|и|ь)$', '', s)


def translit(s, table):
    out = ''.join(table.get(c, c) for c in s.lower())
    return out[:1].upper() + out[1:]


def nominative(ru):
    """(nominative_ru, en, lt) for a genitive-plural surname as written; unknown endings are kept."""
    w = letters(ru)
    if not w:
        return '', '', ''
    for pat, nom, en, lt in ENDINGS:
        m = re.search(pat, w)
        if m and m.start() >= 2:
            head = w[:m.start()]
            return (head + nom).capitalize(), translit(head, EN) + en, translit(head, LT) + lt
    return w.capitalize(), translit(w, EN), translit(w, LT)


def draft_surname(fields):
    v = (fields.get('maiden_and_surname') or {}).get('value') or ''
    words = [w for w in v.split() if letters(w)]
    return words[-1] if len(words) > 1 else ''      # one word alone is the maiden name or a fragment


def reconcile(margin, draft, margin_uncertain):
    ms, ds = stem(margin), stem(draft)
    sim = round(difflib.SequenceMatcher(None, ms, ds).ratio(), 2) if ms and ds else None
    if len(ms) < 3:
        status = 'draft_only' if len(ds) >= 4 else 'none'
    elif len(ds) < 4:
        status = 'margin_only'
    elif ms == ds or sim >= 0.8:
        status = 'agree'
    elif sim < 0.5 and len(ds) >= 0.7 * len(ms):
        status = 'conflict'
    else:
        status = 'margin'
    chosen = draft if status == 'draft_only' else margin if status != 'none' else ''
    nom, en, lt = nominative(chosen)
    return {'margin_ru': margin, 'draft_ru': draft, 'similarity': sim, 'status': status, 'surname_ru': chosen,
            'nominative_ru': nom, 'en': en, 'lt': lt,
            'uncertain': status != 'agree' or margin_uncertain or '?' in (margin or '')}


def main():
    model = sys.argv[1]
    P = BOOK / 'processed'
    side = json.loads((P / 'side_columns.json').read_text()) if (P / 'side_columns.json').exists() else {}
    out, counts = {}, Counter()
    # book 1's first year (1888) predates the per-year naming: entries_<model>.json
    for f in sorted(set(P.glob(f'entries_*_{model}.json')) | set(P.glob(f'entries_{model}.json'))):
        for e in json.loads(f.read_text())['entries']:
            sc = side.get(e['row_id']) or {}
            r = reconcile(sc.get('margin_surname') or '', draft_surname(e['fields']),
                          'margin_surname' in (sc.get('uncertain') or []))
            if r['status'] != 'none':
                out[e['row_id']] = r
            counts[r['status']] += 1
    (P / 'surnames.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(BOOK.name, dict(counts.most_common()))


if __name__ == '__main__':
    main()
