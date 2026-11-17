"""Rule parser and field tagger combined, field by field (RESULTS.md section 6, validated in section 10).

Not a script: `parse_entries.py --tagger` calls `combine_entries`, and `validate_combination.py` scores
the same function, so what is measured is what runs. No torch here: the tagger's spans come from a
file written by `apply.py` (`load_spans`), so this runs in the CPU environment.

Per entry both systems are run: the rules (`parse_entries.parse` and, for the fields parse() does not
split, this folder's own rules in `common.py`: last word = family surname; godfather / godmother /
her status) and the tagger's spans with a confidence each. Then, per field:

  child, father, mother, maiden name, family surname, village, godfather, godmother, her status
      both give a value and agree (span ends within 2 characters; or the same letters; or one is the
      other less formula words such as "Крестьянинъ", "Кс.", "... Салантовскаго прихода")
                                        -> by "both"; the text is the tagger's span (its edges are exact more
                                           often, measured), or the shorter of the two if a formula word was trimmed
      they differ, or the rules give nothing
          tagger confidence >= threshold -> the tagger's span, by "tagger" (the rules' value, if any, in `alt`)
          below it                       -> the rules' value by "rules", or empty by "none" (the tagger's in `alt`)
      threshold: 0.8, and 0.5 for the family surname (THRESHOLD; how it was chosen: RESULTS.md section 10)
  township   the tagger is heard only where the rules themselves find "волости" / "Вол." in at least
             a fifth of the entries given (a book with the township wording); elsewhere rules only,
             and the tagger's township is dropped, not even kept in `alt`
  priest     like the name fields, after "Кс." and titles are taken off the tagger's span
             (`priest='combine'`, the default: on the three choosing folds it is at least as good as the
             better of the two). `priest='rules'` keeps the rules' value and puts the tagger's in `alt`,
             as first specified; it scored lower on every fold (RESULTS.md section 10)
  estate, sex, the legacy `maiden_and_surname` and `godparents`      rules only
  dates      the rules' month and day; where the rules have no complete date, the tagger's date
             phrase is decoded with the rules' own functions (`common.decode_date(strict=True)`: the
             month by `parse_entries.month_after`, so no "Мая" out of "Наября") if its confidence
             reaches the threshold; `baptism_date` / `birth_date` are then rebuilt as parse() does

`by` is one of rules | tagger | both | none; `conf` is the tagger's confidence where it had a span
(mean probability of the span's tag over its characters); `alt` is the value not chosen.
New fields beside parse()'s: maiden_name, family_surname, godfather, godmother, godmother_status.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import COLS, COL_OF, decode_date, rule_spans  # noqa: E402
import parse_entries as pe  # noqa: E402  (the module common.py already loaded)

# Chosen on held-out books other than the two the combination is reported on (RESULTS.md section 10):
# from 0.8 up an uncorroborated tagger span is right about as often as not or better, and right more
# often than a differing rules' value; below it the rules' value is the better bet. The family surname
# is the exception: its spans are right more often than not down to 0.5, and the rules' last-word
# split is almost never right when the two differ.
THRESHOLD = {'default': 0.80, 'SURNAME': 0.50}
TOWNSHIP_SHARE = 0.2

KEY = {'PRIEST': 'priest', 'CHILD': 'child_name', 'ESTATE': 'estate', 'TOWNSHIP': 'township', 'FATHER': 'father',
       'MOTHER': 'mother', 'MAIDEN': 'maiden_name', 'SURNAME': 'family_surname', 'VILLAGE': 'village',
       'GODFATHER': 'godfather', 'GODMOTHER': 'godmother', 'GM_STATUS': 'godmother_status'}
TAGGER_FIELDS = ['CHILD', 'FATHER', 'MOTHER', 'MAIDEN', 'SURNAME', 'VILLAGE', 'GODFATHER', 'GODMOTHER', 'GM_STATUS']
ONE_WORD = {'CHILD', 'FATHER', 'MOTHER'}          # parse() joins the pieces of a given name; so does this
NEW_KEYS = ['maiden_name', 'family_surname', 'godfather', 'godmother', 'godmother_status']
FORMULA = ['урожденной', 'урожд', 'деревне', 'деревни', 'дер', 'местечке', 'прихода', 'сего', 'здешняго', 'тогоже',
           'того', 'волости', 'вол', 'именемъ', 'законныхъ', 'супруговъ', 'викарнымъ', 'настоятелемъ', 'альтаристомъ',
           'местнымъ', 'были', 'девицею', 'вдовою', 'супругою']


def text_hash(s):
    import hashlib
    return hashlib.md5((s or '').encode()).hexdigest()[:12]


def load_spans(path, entries):
    """Tagger spans of `apply.py` for these entries: ([{col: {FIELD: {s, e, conf}}} or None], info).
    An entry whose column text is not the text the spans were made on (the draft was re-assembled
    since) gets None and is counted in info['stale']; so does an entry the file does not have."""
    data = json.loads(Path(path).read_text())
    by_id = {r['row_id']: r for r in data['entries']}
    out, stale = [], 0
    for e in entries:
        r = by_id.get(e.get('row_id'))
        if not r or any(r['hash'].get(c) != text_hash(e.get(c) or '') for c in COLS):
            out.append(None)
            stale += 1
            continue
        sp = {c: {} for c in COLS}
        for x in r['spans']:
            sp[x['col']][x['field']] = {'s': x['s'], 'e': x['e'], 'conf': x['conf']}
        out.append(sp)
    return out, {'spans': str(path), 'model': data.get('model'), 'model_md5': data.get('model_md5'), 'stale': stale}


def norm(s):
    return pe.strip(pe.letters_only(s or ''))


def threshold_of(threshold, field):
    if isinstance(threshold, dict):
        return threshold.get(field, threshold['default'])
    return threshold


def formula_word(w, field=None):
    """A word of the formula, not of a name: an estate, a title, the parish, "урожденной" ..."""
    n = norm(w)
    if n in ('', 'и', 'в', 'с', 'из', 'кс', 'м', 'д') or pe.is_title(w) or pe.PARISH_ADJ.search(n):
        return True
    if len(n) <= 2:
        # before a priest's name a short word is a misread "Кс."; elsewhere it may be a piece of a
        # divided name ("Во ловскихъ")
        return field == 'PRIEST'
    if len(n) >= 5 and any(pe.lev(n[:len(st)], st) <= 1 for st in pe.ESTATE_STEMS):
        return True
    return any(pe.lev(n, pe.strip(f)) <= (1 if len(f) <= 6 else 2) for f in FORMULA)


def trimmed(longer, shorter, field=None):
    """True if `shorter` is `longer` with only formula words taken off its ends."""
    a, b = (longer or '').split(), norm(shorter)
    if len(a) < 2 or not b:
        return False
    for i in range(len(a)):
        for j in range(i + 1, len(a) + 1):
            if (i, j) == (0, len(a)):
                continue
            if pe.lev(norm(''.join(a[i:j])), b) <= 1 and all(formula_word(w, field) for w in a[:i] + a[j:]):
                return True
    return False


def clean(text, field):
    t = re.sub(r'\s+', ' ', text or '').strip(' ,.-=;:')
    if field in ONE_WORD:
        t = t.replace(' ', '')
    return t or None


def agreement(rule_value, rule_span, tag_value, tag_span, field=None):
    """'same' | 'rules shorter' | 'tagger shorter' | None for a field both systems filled."""
    if rule_span and abs(rule_span[0] - tag_span[0]) <= 2 and abs(rule_span[1] - tag_span[1]) <= 2:
        return 'same'
    a, b = norm(rule_value), norm(tag_value)
    if a == b or (not rule_span and min(len(a), len(b)) >= 5 and pe.lev(a, b) <= 1):
        return 'same'
    if len(a) > len(b) and trimmed(rule_value, tag_value, field):
        return 'tagger shorter'
    if len(b) > len(a) and trimmed(tag_value, rule_value, field):
        return 'rules shorter'
    return None


def choose(field, rule_value, rule_span, tag, text, threshold, hear_tagger=True, agreed='tagger'):
    """One field: ({value, by, conf?, alt?}, chosen span or None)."""
    tv = clean(text[tag['s']:tag['e']], field) if tag else None
    ts = (tag['s'], tag['e']) if tag and tv else None
    conf = tag['conf'] if ts else None
    if rule_value and ts:
        how = agreement(rule_value, rule_span, tv, ts, field)
        if how:
            if how == 'tagger shorter' or (how == 'same' and agreed == 'tagger'):
                return {'value': tv, 'by': 'both', 'conf': conf}, ts
            return {'value': rule_value, 'by': 'both', 'conf': conf}, rule_span or ts
    if ts and hear_tagger and conf >= threshold_of(threshold, field):
        out = {'value': tv, 'by': 'tagger', 'conf': conf}
        if rule_value:
            out['alt'] = {'value': rule_value, 'by': 'rules'}
        return out, ts
    out = {'value': rule_value or None, 'by': 'rules' if rule_value else 'none'}
    if ts:
        out['conf'] = conf
        out['alt'] = {'value': tv, 'by': 'tagger', 'conf': conf}
    return out, (rule_span if rule_value else None)


def split_surname(value):
    """The rules' own split of "maiden name(s) + family surname": the last word is the family
    surname; a single word is the maiden name (as reconcile_surnames.draft_surname reads it)."""
    w = [x for x in (value or '').split() if pe.letters_only(x)]
    if len(w) > 1:
        return ' '.join(w[:-1]), w[-1]
    return (w[0] if w else None), None


def combine_entry(entry, tag, threshold=THRESHOLD, township_wording=None, priest='combine', agreed='tagger'):
    """entry: {'baptism', 'parents', 'godparents', 'register_year'}; tag: this entry's tagger spans
    ({col: {FIELD: {s, e, conf}}}) or None. Returns {'fields': {key: {value, by, ...}}, 'spans':
    {FIELD: (s, e)}, 'rule_spans': {FIELD: (s, e)}}; `spans` are the chosen spans (for scoring)."""
    text = {c: entry.get(c) or '' for c in COLS}
    f = pe.parse(entry)
    rs = rule_spans({'text': text, 'register_year': entry.get('register_year')}, parsed=f)
    tag = tag or {c: {} for c in COLS}
    P = text['parents']
    rule_value = {F: f.get(KEY[F]) for F in ('PRIEST', 'CHILD', 'ESTATE', 'TOWNSHIP', 'FATHER', 'MOTHER', 'VILLAGE')}
    ms = rs['parents'].get('MAIDEN'), rs['parents'].get('SURNAME')
    if ms[0] or ms[1]:
        rule_value['MAIDEN'] = clean(P[ms[0][0]:ms[0][1]], 'MAIDEN') if ms[0] else None
        rule_value['SURNAME'] = clean(P[ms[1][0]:ms[1][1]], 'SURNAME') if ms[1] else None
    else:
        rule_value['MAIDEN'], rule_value['SURNAME'] = split_surname(f.get('maiden_and_surname'))
    for F in ('GODFATHER', 'GODMOTHER', 'GM_STATUS'):
        sp = rs['godparents'].get(F)
        rule_value[F] = clean(text['godparents'][sp[0]:sp[1]], F) if sp else None
    if township_wording is None:
        township_wording = bool(f.get('township'))
    fields = {k: {'value': v, 'by': 'rules' if v else 'none'} for k, v in f.items()}
    spans = {}
    for F in ['PRIEST', 'CHILD', 'ESTATE', 'TOWNSHIP'] + TAGGER_FIELDS[1:]:
        col = COL_OF[F]
        t = tag[col].get(F)
        hear = F in TAGGER_FIELDS or (F == 'TOWNSHIP' and township_wording) or (F == 'PRIEST' and priest == 'combine')
        if F == 'TOWNSHIP' and not township_wording:
            t = None
        if F == 'PRIEST' and t:
            # the tagger's span without the words that introduce a priest; its ends move with it
            name = pe.clean_priest(text[col][t['s']:t['e']])
            k = text[col].find(name, t['s']) if name else -1
            t = dict(t, s=k, e=k + len(name)) if k >= 0 else t
        got, sp = choose(F, rule_value.get(F), rs[col].get(F), t, text[col], threshold, hear,
                         agreed if hear else 'rules')
        fields[KEY[F]] = got
        if sp:
            spans[F] = sp
    # dates: the rules decode; the tagger's phrase is decoded where the rules have no complete date
    for kind, F, col in (('baptism', 'BAPT_DATE', 'baptism'), ('birth', 'BIRTH_DATE', 'parents')):
        m, d = f.get(kind + '_month'), f.get(kind + '_day')
        t = tag[col].get(F)
        tm, td = decode_date(text[col][t['s']:t['e']], strict=True) if t else (None, None)
        info = {'by': 'rules' if (m or d) else 'none'}
        if t:
            info['conf'] = t['conf']
        if m and d:
            if (tm, td) == (m, d):
                info['by'] = 'both'
            elif tm and td:
                info['alt'] = {'value': f'{tm:02d}-{td:02d}', 'by': 'tagger', 'conf': t['conf']}
            if rs[col].get(F):
                spans[F] = rs[col][F]
        elif tm and td and t['conf'] >= threshold_of(threshold, F):
            if m or d:
                info['alt'] = {'value': f'{m or 0:02d}-{d or 0:02d}', 'by': 'rules'}
            m, d, info['by'] = tm, td, 'tagger'
            spans[F] = (t['s'], t['e'])
        elif tm and td:
            info['alt'] = {'value': f'{tm:02d}-{td:02d}', 'by': 'tagger', 'conf': t['conf']}
        fields[kind + '_month'] = dict(info, value=m)
        fields[kind + '_day'] = dict(info, value=d)
    dates = {k: v['value'] for k, v in fields.items() if k.endswith(('_month', '_day'))}
    pe.set_dates(dates, entry.get('register_year'))
    for kind in ('baptism', 'birth'):
        info = {k: v for k, v in fields[kind + '_month'].items() if k != 'value'}
        if kind + '_date' in dates or kind + '_date' in fields:
            fields[kind + '_date'] = dict(info, value=dates.get(kind + '_date'))
    for k in NEW_KEYS:
        fields.setdefault(k, {'value': None, 'by': 'none'})
    return {'fields': fields, 'spans': spans, 'rule_spans': {F: sp for c in COLS for F, sp in rs[c].items()}, 'rules': f}


def township_wording(entries):
    """True if these entries are from a book that names the township: the rules find "волости" /
    "Вол." in at least a fifth of them."""
    n = sum(1 for e in entries if pe.find_township_word(pe.Text(e.get('parents') or ''), 0))
    return n >= TOWNSHIP_SHARE * max(len(entries), 1)


def combine_entries(entries, tags, threshold=THRESHOLD, priest='combine', township='file', agreed='tagger'):
    """Entries of one draft file and their tagger spans (same order; None = no usable spans).
    township: 'file' (default: one decision for all the entries given), 'entry' (the tagger's
    township is heard where the rules found one in the same entry), 'never'."""
    gate = {'file': township_wording(entries) if township == 'file' else None, 'entry': None, 'never': False}[township]
    return [combine_entry(e, t, threshold, gate, priest, agreed) for e, t in zip(entries, tags)]
