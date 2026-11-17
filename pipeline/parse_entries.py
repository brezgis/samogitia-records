"""Extract structured fields from per-entry drafts using the register's fixed formula.

Usage: .venv/bin/python -I pipeline/parse_entries.py processed/year_draft_<model>.json [--check-pilot]
           [--tagger | --tagger-spans FILE] [--priest rules] [--out FILE]

Drafts are noisy (spurious spaces, similar-letter confusions), so formula anchors
("именемъ", "волости", "законныхъ", "деревнѣ" ...) are located by approximate matching
on the text with spaces removed; fields are the original text between anchors.
Ordinal day words become numbers; months are matched against old-orthography names.

Two wordings are covered. The later one (1886 onwards) names the township: "Крестьянъ <X>ской
волости <father> и <mother> изъ <maiden name> <surname> законныхъ супруговъ". The older one
(1849-1874, and "урожд." in 1902-07) has no township: "Крестьянъ <father> и <mother> урожденной
<maiden name> <surname> законныхъ супруговъ"; there the parents stand between the estate and
"урожденной", the baptism day may be in digits ("22 Іюля", "Іюля 22 дня"), and the priest follows
"Викарнымъ / Альтаристомъ / мѣстнымъ / онаго / Ксендзомъ / Кс." or the church itself. The older
rules for dates, priest, parents and surname only fill what the later ones left empty, and depend
on the text, not on the book. Three clean-ups apply to both wordings: the words that introduce a
priest ("онаго Кс.", "Ксендзомъ") are not part of his name, the parish ("... Плунгянскаго
прихода", "сего прихода") is not part of the village, and "урожд." is not part of the surname.

A month name of three letters ("Мая") is matched exactly or as a word of its own, never inside
another word (it used to be found in "родивш-аяс-я", "Н-ая-бря", "Ма-рта"); where the month cannot
be read the day beside it is still returned, so a day may come without a month (and then without a
date). A digit standing apart before a month name belongs to the day ("13 Юня" was read as the 1st),
a digit written onto the name is its misread first letter ("7юня", "100ктября"). "волости" is not
looked for behind the parents (surnames such as "Воловскихъ", "Волонтовны" resemble it), its
abbreviation is also read as "Вол", "вос.", "восс.", and it ends before the father's name
("вол. Ст|анислава").

Each field records `source`: "checked" if every line of its column is a checked label,
"mixed" or "model" otherwise. Model-sourced names are unreliable. Output:
processed/entries_<model>.json (or --out FILE). --check-pilot compares against
processed/pilot_reference.csv (itself provisional machine adjudication, not ground truth).

Optional, off by default: the neural field tagger (pipeline/neural_parser). With --tagger the spans
file `tagger_spans_<model>.json` beside the draft is read (written beforehand by
`.venv-htr/bin/python pipeline/neural_parser/apply.py <draft>`; --tagger-spans names another file)
and each field is chosen between the rules and the tagger as `neural_parser/combine.py` describes.
Every field then carries, beside `value` and `source`, the key `by` (rules | tagger | both | none),
`conf` (the tagger's confidence in its span, where it had one) and `alt` (the value not chosen), and
five fields are added: maiden_name, family_surname, godfather, godmother, godmother_status. The old
fields keep their names and meaning (`maiden_and_surname` and `godparents` stay the rules' own), and
`source` is untouched: it says whether the TEXT was checked, `by` says who read the field out of it.
Spans made on another version of the draft (the text is compared by hash) are ignored and counted.
Without --tagger nothing changes.
"""
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / __import__('os').environ.get('SAMOGITIA_BOOK', 'data/plunge-1886-1890')

MONTHS = {1: ['Января', 'Генваря'], 2: ['Февраля'], 3: ['Марта'], 4: ['Апрѣля', 'Апреля'], 5: ['Мая'],
          6: ['Іюня', 'Июня'], 7: ['Іюля', 'Июля'], 8: ['Августа'], 9: ['Сентября'], 10: ['Октября'],
          11: ['Ноября'], 12: ['Декабря']}
UNITS = ['перваго', 'втораго', 'третьяго', 'четвертаго', 'пятаго', 'шестаго', 'седьмаго', 'восьмаго', 'девятаго']
TEENS = ['десятаго', 'одиннадцатаго', 'двѣнадцатаго', 'тринадцатаго', 'четырнадцатаго', 'пятнадцатаго',
         'шестнадцатаго', 'семнадцатаго', 'восемнадцатаго', 'девятнадцатаго']
ORDINALS = {}
for i, w in enumerate(UNITS, 1):
    ORDINALS[w] = i
ORDINALS['осьмаго'] = 8
for i, w in enumerate(TEENS, 10):
    ORDINALS[w] = i
ORDINALS['шеснадцатаго'] = 16
ORDINALS['двадцатаго'] = 20
ORDINALS['тридцатаго'] = 30
for i, w in enumerate(UNITS, 1):
    ORDINALS['двадцать' + w] = 20 + i
ORDINALS['тридцатьперваго'] = 31
# "восмаго" / "востого" (Salantai's clerk, and the recognizer's reading of "восьмаго"): without it
# "двадцать востого" is as near to "двадцать шестаго" as to "двадцать восьмаго" and the tie went to 26
ORDINALS['восмаго'] = 8
ORDINALS['двадцатьвосмаго'] = 28


def strip(s):
    return unicodedata.normalize('NFC', s or '').lower().replace('ѣ', 'е').replace('і', 'и').replace('ъ', '')


def lev(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        nxt = [i]
        for j, y in enumerate(b, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = nxt
    return row[-1]


def approx_find(text, pattern, start=0, max_ratio=0.34):
    """Best approximate occurrence of pattern in text[start:] (Sellers). Returns (s, e) or None."""
    t, p = text[start:], pattern
    if not p or not t:
        return None
    m = len(p)
    prev = [0] * (len(t) + 1)          # free start anywhere
    starts_prev = list(range(len(t) + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * len(t)
        starts = [0] * (len(t) + 1)
        for j in range(1, len(t) + 1):
            opts = [(prev[j - 1] + (p[i - 1] != t[j - 1]), starts_prev[j - 1]),
                    (prev[j] + 1, starts_prev[j]),
                    (cur[j - 1] + 1, starts[j - 1])]
            cur[j], starts[j] = min(opts)
        prev, starts_prev = cur, starts
    best = min(range(len(t) + 1), key=lambda j: (prev[j], j))
    if prev[best] > max(1, int(m * max_ratio)):
        return None
    return start + starts_prev[best], start + best


class Text:
    """Original text with a space-free, simplified view for anchor search."""

    def __init__(self, s):
        self.orig = s or ''
        self.flat, self.map = '', []
        for k, ch in enumerate(self.orig):
            if not ch.isspace():
                self.flat += strip(ch) or ''
                self.map.extend([k] * len(strip(ch) or ''))
        self.map.append(len(self.orig))

    def find(self, word, start=0):
        r = approx_find(self.flat, strip(word).replace(' ', ''), start)
        return r

    def between(self, a, b):
        if a is None or b is None or b <= a:
            return None
        s = self.orig[self.map[a]:self.map[b]] if a < len(self.map) else ''
        s = re.sub(r'\s+', ' ', s).strip(' ,.-=;:')
        return s or None


def letters_only(w):
    return re.sub(r'[^А-Яа-яЁёѢѣІі]', '', w)


def find_abbrev(tx, pattern, start=0):
    """An abbreviation matched by regex on the original text, as flat-view (start, end), or None."""
    m = re.compile(pattern).search(tx.orig, tx.map[start] if start < len(tx.map) else len(tx.orig))
    if not m:
        return None
    return (next(i for i, k in enumerate(tx.map) if k >= m.start()), next(i for i, k in enumerate(tx.map) if k >= m.end()))


def month_after(tx, pos, window=6):
    """The month name nearest in spelling that begins within `window` letters after flat position
    `pos`: (month number, flat (start, end)) or (None, None).

    A name of three letters ("Мая") is too short for a free approximate search: one error allowed in
    three letters matches the ending of "родивш-аяс-я", the "ая" of "Наября" or the "Ма" of a misread
    "Марта", and such a match used to win over the real month. It is found by `short_month_after`
    instead, and an inexact "Мая" never wins over another month found with the same number of errors."""
    best = None
    for n, names in MONTHS.items():
        for name in names:
            key = strip(name)
            if len(key) <= 3:
                r, d = short_month_after(tx, key, pos, window)
            else:
                r = tx.find(name, pos)
                d = lev(tx.flat[r[0]:r[1]], key) if r else None
            if r and r[0] - pos <= window:
                if best is None or d < best[0]:
                    best = (d, n, r)
    if not best:
        return None, None
    _, n, r = best
    # An inexact match may have taken the last digit of the day for the name's first letter ("13 Юня"
    # matched as "3юня", which made the day 1): the digit goes back to the day if it is the second
    # digit of a number up to 31 that stands apart from the name. A digit written onto the name, or
    # standing alone before it, or ending a longer or impossible number, is the misread first letter
    # ("7юня" for "Іюня", "100ктября" and "240 ктября" for "10 / 24 Октября", "19 9 юня", "99 юня").
    a = tx.map[r[0]]
    if r[1] - r[0] > 2 and tx.orig[a].isdigit() and tx.orig[a - 1:a].isdigit() and not tx.orig[max(0, a - 2):a - 1].isdigit() \
            and int(tx.orig[a - 1:a + 1]) <= 31 and (tx.orig[a + 1:a + 2].isspace() or tx.orig[a + 1:a + 2].isupper()):
        r = (r[0] + 1, r[1])
    return n, r


def short_month_after(tx, key, pos, window):
    """A three-letter month name beginning within `window` letters after `pos`: (flat (start, end),
    errors) or (None, None). Spelled exactly it is taken wherever it stands. Misread it must be a word
    of its own in the original text ("сая 6 дня", "Мася 2.", "28 каявъ", "го да маи", "Твая 27"): three
    to five letters, one of them wrong (two if "ая" or "Ма" is still there), with more errors against
    every other month, not the abbreviation of another month ("Мар."), and not the ending of the
    verb before it ("родивш|аяся", "родиь шаяся"). Two letters ("Ма", "ая") count only straight
    after "года" (a window of six letters, the word beginning within four). A name that ran into the
    day ("Моясетвертаго дня") counts if what follows its three letters reads as an ordinal."""
    start = tx.map[pos] if pos < len(tx.map) else len(tx.orig)
    others = [strip(nm) for names in MONTHS.values() for nm in names if strip(nm) != key]
    k = tx.flat.find(key, pos)
    if 0 <= k <= pos + window:
        # not the "мая" inside another month's misread name ("Ггомаября")
        a = tx.map[k]
        word = strip(letters_only(re.search(r'[%s]*$' % LETTER, tx.orig[:a]).group() + re.match(r'[%s]*' % LETTER, tx.orig[a:]).group()))
        if len(word) <= 5 or not (word.endswith(('ся', 'сь')) or any(approx_find(word, o) for o in others if len(o) > 4)):
            return (k, k + len(key)), 0
    for m in re.finditer(r'[%s]+' % LETTER, tx.orig[start:]):
        s = flat_index(tx, start + m.start())
        if s - pos > window:
            break
        if m.start() == 0 and start and tx.orig[start - 1].isalpha() and not tx.flat[:pos].endswith('да'):
            continue                # the rest of the word the search began in, unless that was "года" ("годачная")
        w = strip(m.group())
        lead = re.match(r'(?:го|о)?да(?=..)', w)         # "годамая", "го да маи", "годама 28"
        if lead and lev(w[lead.end():], key) < lev(w, key):
            s, w = s + lead.end(), w[lead.end():]
        else:
            lead = None
        w = re.sub(r'(?<=...)(?:в|дня)$', '', w) if len(w) > 4 else w      # "каявъ", "маядня"
        if len(w) > 5 and w[0] == key[0] and lev(w[:len(key)], key) <= 1 and not any(o.startswith(w[:len(key)]) for o in others):
            # the name ran into the day's ordinal ("Моясетвертаго", "Мааодинадцатаго", "Масячетвер таго")
            rest = tx.orig[start + m.start():]
            dn = Text(rest).find('дня')
            words = rest[:Text(rest).map[dn[0]]] if dn and dn[0] <= 40 else ''
            tail = strip(w[len(key):])
            begins = any(lev(tail[i:i + n], strip(o)[:n]) <= (1 if n <= 5 else 2) for o in ORDINALS for i in (0, 1)
                         for n in [min(len(tail) - i, 7)] if n >= 4)
            if begins and ordinal(re.sub(r'^\W*[%s]{%d}' % (LETTER, len(key)), '', words, count=1)):
                return (s, s + len(key)), 1.5
        if not (2 if lead or (window <= 6 and s - pos <= 4) else 3) <= len(w) <= 5 or (w.endswith(('ся', 'сь')) and w[0] != key[0]):
            continue
        if len(w) >= 3 and any(o.startswith(w) for o in others):
            continue
        d = lev(w, key)
        if d > 2 or (d == 2 and key[1:] not in w and not w.startswith(key[:2])):
            continue
        if d / max(len(w), len(key)) <= 0.5 and all(lev(w, o) > d for o in others):
            return (s, s + len(w)), d + 0.5
    return None, None


def day_in_words(s):
    """The ordinal day in a stretch that follows a month; a short leftover of the month's ending
    before it is dropped ("Сентябр|ая семнадцатаго", "Декабр|я двадцатаго")."""
    d = ordinal(s)
    w = (s or '').split()
    if not d and len(w) > 1 and len(letters_only(w[0])) <= 3:
        d = ordinal(' '.join(w[1:]))
    return d


def nearest_ordinal(s):
    """(day, errors) of the ordinal word nearest to `s`, or (None, None) if none is near enough."""
    if not s:
        return None, None
    s = strip(s).replace(' ', '').replace('-', '').replace('=', '')
    w, d = min(((w, lev(s, strip(w))) for w in ORDINALS), key=lambda x: x[1])
    return (ORDINALS[w], d) if d <= max(2, len(w) // 4) else (None, None)


def ordinal(s):
    return nearest_ordinal(s)[0]


def day_after_unreadable_month(words):
    """The day in "<unreadable month> <day>" (the words between "года" and "дня"), or None. The month
    is one word, or two or three pieces of one ("Апрнъ го мя восмаго"); it may have run into the day
    ("Маршестага", "Іомядвадцатъ девятаго", "Масячетвер таго"), so a long first word is cut where
    the rest reads best as an ordinal. A word that holds "двадцать" / "тридцать" is never dropped,
    and what is left must be long enough to be an ordinal ("таго" alone is not "пятаго")."""
    w = list(words)
    if len(w) >= 3 and len(letters_only(w[0])) <= 2:    # a stray mark before the month ("года в Іюомя ...")
        w.pop(0)
    if not w or w[0][0].isdigit():
        return None
    first = letters_only(w[0])
    if (nearest_ordinal(' '.join(w))[1] or 9) <= 1 or nearest_ordinal(' '.join(w))[1] == 0:
        return None                                     # no month at all: "года одинадцатаго дня" is not read
    if len(first) > 8:
        for c in range(3, len(first) - 1):
            if len(first) - c + sum(len(letters_only(x)) for x in w[1:]) < 6:
                break
            day = ordinal(first[c:] + ''.join(w[1:]))
            if day:
                return day
    tens = lambda x: any(approx_find(strip(letters_only(x)), t, 0, 0.4) for t in ('двадцать', 'тридцать'))
    for k in range(1, min(4, len(w))):
        # after the first word only pieces of one or two letters may be dropped ("го", "мя"), or the
        # month itself where a stray word stood before it ("года Крестьянъ Февраля двѣнадцатаго"),
        # never a word or a piece of the day ("двадезатъ", "Івоо цатаго")
        piece = strip(letters_only(w[k - 1]))
        is_month = any(approx_find(piece, strip(nm)) for names in MONTHS.values() for nm in names if len(strip(nm)) > 3)
        if tens(w[k - 1]) or (k > 1 and not is_month and len(piece) > 2):
            return None
        rest = ' '.join(w[k:])
        dm = re.fullmatch(r'(\d{1,2})\W*', rest)
        day = int(dm.group(1)) if dm else ordinal(rest) if len(letters_only(rest)) >= 5 else None
        if day and 1 <= day <= 31:
            return day
    return None

LETTER = 'А-Яа-яЁёѢѣІі'
# words that belong to the estate, not to the father's name ("Билетнаго Солдата Францишка и ...")
ESTATE_STEMS = ['крестьян', 'дворян', 'мещан', 'шляхт', 'однодвор', 'солдат', 'билетн', 'отставн', 'рядов',
                'вольн', 'безсрочн', 'запасн', 'унтер', 'офицер', 'гражд']
PARISH_ADJ = re.compile(r'(?:[сc]к[ао][гм][оа]|[сc]кою|шн[аяеи]го|^[сc]е?го|^того(?:же)?|^онаго)$')


def flat_index(tx, k):
    """Flat-view index of position k of the original text."""
    return next((i for i, o in enumerate(tx.map) if o >= k), len(tx.flat))


def is_title(word):
    """A word that introduces the priest's name: "Ксендзомъ" (also misread: "Кондзомъ", "Каендзомъ",
    "Кеняомъ"), "Кс." (also "Кс:", "Ксъ", "Кес:", "К.с:"), "онаго", "Каноникомъ"."""
    w = strip(letters_only(word))
    if w in ('онаго', 'оного') or (1 < len(w) <= 3 and w[0] == 'к' and w[1] in 'сеc'):
        return True
    if 4 <= len(w) <= 10 and w.startswith('кс') and lev(w, 'ксендзом') <= 3:
        return True
    return 5 <= len(w) <= 10 and w[0] in 'кі' and w.endswith(('ом', 'ем')) \
        and (lev(w, 'ксендзом') <= 3 or lev(w, 'каноником') <= 2)


def clean_priest(s):
    """The priest's name without the words that introduce it and without what follows it."""
    words = (s or '').lstrip(' :.,-=').split()
    while words:
        # "КсПацевичемъ", "Кс:нзефовичемъ", "КсендзомъІосифомъ"
        fused = re.match(r'[Кк][сеc][ъье]?(?:[.:\-]+|(?=[А-ЯІ]))|[Кк]с[а-яѣі]{2,6}мъ(?=[А-ЯІ])', words[0])
        if fused and len(words[0]) - fused.end() >= 2:
            words[0] = words[0][fused.end():]
        elif is_title(words[0]):
            words.pop(0)
        elif len(words) > 2 and is_title(words[0] + words[1]):       # "Ксен дзомъ"
            del words[:2]
        else:
            break
    while len(words) > 1 and (is_title(words[-1]) or lev(strip(letters_only(words[-1])), 'викарным') <= 2):
        words.pop()         # "... Костелѣ Іосифомъ Залескимъ Викарнымъ Ксендзомъ окрещено"
    # the priest may be named before the church: "... Кс Іоанномъ Контрымомъ въ Салантовскомъ ... Костелѣ окрещенъ"
    s = re.split(r'\s+въ\s', ' '.join(words))[0]
    return s.strip(' ,.-=;:') or None


def priest_before(B, ok):
    """Older wording: the priest stands between the last word that introduces him ("Викарнымъ",
    "Альтаристомъ", "Настоятелемъ", "мѣстнымъ", "онаго", "Ксендзомъ", "Кс.") or, failing those, the
    church ("Костелѣ"), and "окрещен...". At most four words."""
    head = Text(B.orig[:B.map[ok[0]]])
    ends = {}
    for w in ('Костелѣ', 'Викарнымъ', 'Альтаристомъ', 'Настоятелемъ', 'Ксендзомъ', 'мѣстнымъ'):
        r = head.find(w)
        if r:
            ends[head.map[r[1]]] = w
    for m in re.finditer(r'(?<![%s])(?:К[сеc]\s*[.:]|К[сc](?=\s)|[Оо]н[ао]го)' % LETTER, head.orig):
        ends[m.end()] = 'Кс.'
    for k in sorted(ends, reverse=True):
        rest = head.orig[k:]
        if ends[k] == 'Костелѣ':
            # "Костелѣ Ксендзомъ Сташковскимъ окрещено": the word after the church is the (often
            # misread) "Ксендзомъ"; a single word there is not trusted as a name
            w = rest.split()
            if len(w) < 2:
                continue
            rest = rest if is_title(w[0]) else ' '.join(w[1:])
        pr = clean_priest(rest)
        if pr and len(letters_only(pr)) >= 4:
            return pr if len(pr.split()) <= 4 else None
    return None


def find_born(P, start):
    """"урожденной" (misread, or abbreviated "урожд.") after flat position `start`, as flat (start, end)
    with the end moved to the end of the written word; None for an unmarried mother ("Крестьянки ...
    незаконнорожденный сынъ"). The nearest 70 letters are searched first: a draft may hold two entries."""
    if re.match(r'\W*\S{0,8}\s?\S{0,6}ян[кн][иі](?![%s])' % LETTER, P.orig):       # "Крестьянки", "ресть янки", "Крестьянни"
        return None
    ur = approx_find(P.flat[:start + 70], 'урожденной', start) or P.find('урожденной', start) \
        or find_abbrev(P, r'[Уу]р[оа][жш][дg]?[ъе]?\s*[.:]', start)
    if not ur or approx_find(P.flat[max(0, ur[0] - 11):ur[0] + 2], 'незаконно') \
            or re.search(r'сын|дочь', P.flat[ur[1]:ur[1] + 8]):
        return None
    if not P.orig[P.map[ur[0]] - 1].isspace():
        # the match began on the last letter of the mother's name ("Ев|ы рожденной"): start at the next word
        gap = re.match(r'\S{1,2}\s+', P.orig[P.map[ur[0]]:P.map[ur[0]] + 4])
        if gap:
            ur = (flat_index(P, P.map[ur[0]] + gap.end()), ur[1])
    tail = re.match(r'[%s]{1,3}(?=\s)' % LETTER, P.orig[P.map[ur[1]]:P.map[ur[1]] + 4])
    if tail and not P.orig[P.map[ur[1]] - 1].isspace():      # "урожденно|и Кавецкой", "урожденной|съ"
        ur = (ur[0], flat_index(P, P.map[ur[1]] + tail.end()))
    return ur


def split_parents(names, township=False):
    """"[estate words] <father> и <mother>" -> (father, mother) or (None, None). The "и" may be
    misread as another one- or two-letter word or, in the wording without a township, be lost
    between exactly two names. A given name divided by the recognizer is joined ("Стани Слава"),
    a name and patronymic are kept together ("Леона Иванова" -> "ЛеонаИванова", as the later
    wording does); other words before the father's name (an estate, a leftover) are dropped."""
    words = [w for w in (names or '').split() if letters_only(w)]
    while len(words) > 1 and len(letters_only(words[0])) <= 2:      # the tail of a divided estate word ("Крестья нъ")
        words.pop(0)
    while words and any(lev(strip(letters_only(words[0]))[:len(st)], st) <= 1 for st in ESTATE_STEMS) and len(words) > 1:
        words.pop(0)
    sep = next((i for i, w in enumerate(words) if 0 < i < len(words) - 1 and letters_only(w) in ('и', 'і', 'И', 'І')), None)
    if sep is None:
        sep = next((i for i, w in enumerate(words) if 0 < i < len(words) - 1 and len(letters_only(w)) <= 2
                    and len(letters_only(words[i - 1])) >= 4), None)
    if sep is not None:
        left, right = words[:sep], words[sep + 1:]
    elif not township and len(words) == 2 and all(len(letters_only(w)) >= 4 and w[0].isupper() for w in words):
        left, right = [re.sub(r'(?<=[аяо])[иі]$', '', words[0])], words[1:]     # "Казимираи Оршули"
    else:
        return None, None
    left = [w.strip('.,:;-=') for w in left if len(letters_only(w)) > 1] or left
    right = [w.strip('.,:;-=') for w in right if len(letters_only(w)) > 1] or right
    while len(left) > 1 and left[-1][0].isupper() and len(letters_only(left[-1])) <= 2:
        left.pop()                                                  # a stray mark after the name ("Андржея Зо")
    caps = [i for i, w in enumerate(left) if w[0].isupper()]
    k = caps[-1] if caps else 0                 # the last word that begins a name; lower-case pieces after it continue it
    if township:
        k = 0
    elif k and re.search(r'(?:ов|ев)(?:а|ича)$', strip(letters_only(''.join(left[k:])))) and left[k - 1][0].isupper():
        k -= 1                                  # a patronymic: keep the name before it
    elif k == 1 and left[0][0].isupper() and len(letters_only(left[0])) <= 6 and len(letters_only(left[1])) <= 5:
        k = 0                                   # one name in two pieces ("Стани Слава")
    father = ''.join(left[k:])
    mother = ''.join(right)
    if len(letters_only(mother)) > 14:
        mother = right[0]
    mother = re.sub(r'^[иі](?=[А-ЯІ])', '', mother)                 # "Во иМаріяны"
    return father or None, mother or None


def parents_before(stretch):
    """True if the text between the estate and a supposed "волости" already holds the parents: an
    "урожденной", an "изъ", or "<Name> и <Name>". Then the match is not the township's word but a
    surname that resembles it ("Воловскихъ", "Волонтовны", "Добровольскихъ")."""
    s = stretch or ''
    if approx_find(Text(s).flat, 'урожденной') or re.search(r'(?<![%s])[Уу]р[оа][жш][дg]?[ъе]?\s*[.:]' % LETTER, s):
        return True
    if re.search(r'(?<![%s])[иі][зд]ъ(?![%s])' % (LETTER, LETTER), s):
        return True
    words = s.split()
    for i in range(1, len(words) - 1):
        if letters_only(words[i]) in ('и', 'і') and words[i - 1][0].isupper() and len(letters_only(words[i - 1])) >= 4 \
                and not re.search(r'[сc]к[оo]?$', strip(letters_only(words[i - 1]))) \
                and letters_only(words[i + 1])[:1].isupper():
            return True         # not "Плунгянско и Вол.": a divided "...ской"
    return False


TOWNSHIP_ABBREV = re.compile(r'(?<![%s])[ВвB]о[лс]{1,2}[оъг]?\s?[.:]|(?<=[сc]к[оаеи][йиіняюмгъ]\s)[ВвB]олъ?(?=\s+[А-ЯІ][а-яѣі])' % LETTER)


def find_township_word(P, start):
    """Flat (start, end) of "волости" (approximate), or of its abbreviation ("Вол.", "вол:", misread
    "Вос."), after the estate; None where the entry names no township. An inexact match is refused
    when the parents already stand before it (`parents_before`: it is then a surname such as
    "Воловскихъ" or "Волонтовны"), and the abbreviation is looked for instead. The anchor ends where
    a new capitalised word begins ("вол. Ст|анислава", "воност И|гнатія")."""
    limit = len(P.flat)
    for _ in range(3):
        vol = approx_find(P.flat[:limit], 'волости')
        if not vol:
            break
        exact = P.flat[vol[0]:vol[1]] == 'волости'
        if exact or not parents_before(P.between(start, vol[0]) if vol[0] > start else ''):
            a, b = P.map[vol[0]], P.map[vol[1] - 1] + 1
            cut = re.search(r'(?<=[%s.:])\s+(?=[А-ЯІ])' % LETTER, P.orig[a:b])
            if cut and re.match(r'[ВвBб][оo]', P.orig[a:b]) \
                    and not re.search(r'(?:ст[иаы]|ти)$|^.{3,}ст$', strip(letters_only(P.orig[a + cut.end():b]))) \
                    and not approx_find(strip(letters_only(P.orig[a + cut.end():b])), 'лости', 0, 0.2):     # not "во В лости", "во В лосми"
                vol = (vol[0], flat_index(P, a + cut.start()))
            return vol
        limit = vol[0]
    for mv in TOWNSHIP_ABBREV.finditer(P.orig):
        vol = (flat_index(P, mv.start()), flat_index(P, mv.end()))
        if vol[0] >= start and not parents_before(P.between(start, vol[0]) if vol[0] > start else ''):
            return vol
    return None


def parse(entry):
    out = {}
    B, P, G = Text(entry['baptism']), Text(entry['parents']), Text(entry['godparents'])
    # baptism: "... года <Month> <ordinal> дня, въ ... Кс: <priest> окрещенъ младенецъ именемъ <Name> со всѣми ..."
    g = B.find('года')
    if g:
        m, mr = month_after(B, g[1])
        out['baptism_month'] = m
        if mr:
            d = B.find('дня', mr[1])
            out['baptism_day'] = day_in_words(B.between(mr[1], d[0])) if d else None
            if not out['baptism_day']:
                # the day in digits: "года 22 Іюля", "года Іюля 22 дня"
                db = re.search(r'(?<!\d)(\d{1,2})\W*$', B.orig[B.map[g[1]]:B.map[mr[0]]])
                da = re.match(r'\W*(?:дня\W*)?(\d{1,2})(?!\s*\d)', B.orig[B.map[mr[1]]:])
                day = int((db or da).group(1)) if (db or da) else None
                out['baptism_day'] = day if day and 1 <= day <= 31 else None
        if not out.get('baptism_day'):
            # the month is unreadable ("года Таромя четвертаго дня"), or what was taken for it was
            # not where the day could be read from: the day after it is still read
            d = B.find('дня', g[1])
            w = (B.between(g[1], d[0]) or '').split() if d and d[0] - g[1] <= 45 else []
            day = day_after_unreadable_month(w)
            if day:
                out['baptism_day'] = day
    # "Кс" is too short to search the whole column (it matches inside "Тысяча"): look only
    # after "Викарнымъ", and take the priest's name up to "окрещенъ". Without "Викарнымъ" (or with
    # nothing after it) the other words that introduce a priest are tried (`priest_before`).
    vik = B.find('Викарнымъ')
    ok = B.find('окрещен', vik[1] if vik else 0)
    if vik and ok and ok[0] > vik[1]:
        pr = B.between(vik[1], ok[0]) or ''
        out['priest'] = clean_priest(pr)
    else:
        out['priest'] = None
    if not out['priest']:
        ok = B.find('окрещен')
        out['priest'] = priest_before(B, ok) if ok else None
    im = B.find('именемъ')
    so = B.find('совсѣми', im[1]) if im else None
    out['child_name'] = B.between(im[1], so[0] if so else len(B.flat)) if im else None
    # parents
    toks = P.orig.split()
    out['estate'] = toks[0].strip(' =-') if toks else None
    est_end = P.find(out['estate']) if out['estate'] else None
    vol = find_township_word(P, est_end[1] if est_end else 0)
    out['township'] = P.between(est_end[1], vol[0]) if vol and est_end else None
    izy = None
    if vol:
        # "изъ" is too short for approximate search: match it as a whole word (also misread "идъ")
        mz = re.compile(r'(?<![А-Яа-яЁёѢѣІі])[иі][зд]ъ?(?![А-Яа-яЁёѢѣІі])').search(P.orig, P.map[vol[1]])
        if mz:
            fs = next(i for i, k in enumerate(P.map) if k >= mz.start())
            fe = next(i for i, k in enumerate(P.map) if k >= mz.end())
            izy = (fs, fe)
    if vol and izy:
        names = P.between(vol[1], izy[0]) or ''
        parts = re.split(r'\s+и\s+', names, maxsplit=1)
        out['father'] = parts[0] if len(parts) == 2 else None
        out['mother'] = parts[1] if len(parts) == 2 else None
    zak = P.find('законныхъ', izy[1] if izy else 0) or find_abbrev(P, r'[Зз]ак(?:он)?\s*[.:]|[Зз]акон(?=\s)', izy[1] if izy else 0)
    out['maiden_and_surname'] = P.between(izy[1], zak[0]) if izy and zak else None
    if vol and zak and not izy:
        # "изъ" misread or fused with the mother's name ("Вероникизъ", "иъ"): father = before " и ",
        # mother = the next word, the rest (minus a short leftover of "изъ") = maiden name and surname
        parts = re.split(r'\s+и\s+', P.between(vol[1], zak[0]) or '', maxsplit=1)
        if len(parts) == 2 and len(parts[1].split()) >= 3:
            w = parts[1].split()
            rest = w[2:] if len(letters_only(w[1])) <= 3 else w[1:]
            out['father'], out['mother'] = parts[0], re.sub(r'[иі]?[зд]ъ?$', '', w[0]) if len(w[0]) > 6 else w[0]
            out['maiden_and_surname'] = ' '.join(rest) or None
    if not out.get('father') or not out.get('maiden_and_surname'):
        # older wording, no township: "<estate> <father> и <mother> урожденной <maiden name> <surname>
        # законныхъ супруговъ" (also "урожд." in the later books, after the township)
        start = est_end[1] if est_end else 0
        ur = find_born(P, start)
        if ur and vol and vol[1] <= ur[0]:
            start = vol[1]
        if ur and not out.get('father'):
            out['father'], out['mother'] = split_parents(P.between(start, ur[0]), township=start != (est_end[1] if est_end else 0))
        if ur and not out.get('maiden_and_surname'):
            zk = P.find('законныхъ', ur[1]) or find_abbrev(P, r'[Зз]ак(?:он)?\s*[.:]|[Зз]акон(?=\s)', ur[1])
            if zk and not P.orig[P.map[zk[0]] - 1].isspace():
                # the match began inside the surname's ending ("Вайтковъ акопныхъ"): move to the next word
                gap = re.search(r'\s', P.orig[P.map[zk[0]]:P.map[zk[0]] + 4])
                if gap:
                    zk = (flat_index(P, P.map[zk[0]] + gap.end()), zk[1])
            ms = P.between(ur[1], zk[0]) if zk and zk[0] - ur[1] <= 50 else None
            if not ms:
                # "законныхъ" unreadable: up to "супруговъ", less the word before it
                sup = P.find('супруговъ', ur[1])
                w = (P.between(ur[1], sup[0]) or '').split() if sup and sup[0] - ur[1] <= 60 else []
                ms = ' '.join(w[:-1] if len(w) >= 3 else w) or None
            w = (ms or '').split()
            if len(w) >= 3 and re.match(r'[ЗзЧчГг]', w[-1]) and not re.search(r'(?:[ое]въ|[иы]хъ|ей|[ое]в)$', w[-1]):
                w.pop()             # the first half of a divided or misread "законныхъ" ("Зол понныхъ", "гокан- ныхъ")
            ms = ' '.join(w).strip(' -=.,:;')
            out['maiden_and_surname'] = ms if ms and len(ms.split()) <= 6 else None
    if out.get('maiden_and_surname'):
        # "... и Анны урожд. Стонкусъ зак. суп." read without "изъ": the word itself is not part of the name
        out['maiden_and_surname'] = re.sub(r'^[Уу]р[оа][жш]\S*\s+(?=\S)', '', out['maiden_and_surname'])
    syn, doch = P.find('сынъ'), P.find('дочь')
    if syn and not doch:
        out['sex'] = 'M'
    elif doch and not syn:
        out['sex'] = 'F'
    elif syn and doch:
        out['sex'] = 'M' if lev(P.flat[syn[0]:syn[1]], 'сын') <= lev(P.flat[doch[0]:doch[1]], 'дочь') else 'F'
    y = re.search(r'18\s*[89]\s*\d', P.orig)
    if y:
        flat_pos = next((i for i, k in enumerate(P.map) if k >= y.end()), None)
        m, mr = month_after(P, flat_pos) if flat_pos is not None else (None, None)
        out['birth_month'] = m
        if mr:
            rest = P.orig[P.map[mr[1]]:]
            dm = re.match(r'\s*[=\-.,]*\s*(\d{1,2})', rest)
            out['birth_day'] = int(dm.group(1)) if dm and 1 <= int(dm.group(1)) <= 31 else None
    if not (out.get('birth_month') and out.get('birth_day')):
        # other orders: "родившійся 16 Іюня сего 1897 года", "1899 года 25 Февраля", "Января1 дня",
        # day in words ("седмаго дня"). The month is looked for anywhere after "родивш".
        rod = P.find('родивш')
        if rod:
            # the verb's own ending is not searched ("родивш|аяся" holds an "ая", a misread "ійся" an "Іюня")
            k = P.map[rod[1]]
            k += re.match(r'[а-яёѣі\s]{0,6}?[сc][яьа](?![а-яёѣі])|[а-яёѣі]{0,2}', P.orig[k:]).end()
            vend = flat_index(P, k)
            m, mr = month_after(P, vend, window=40 - (vend - rod[1]))
            if mr:
                before = P.orig[k:P.map[mr[0]]]
                after = P.orig[P.map[mr[1]]:]
                db = re.search(r'(?<!\d)(\d{1,2})\W*$', before)
                # "Февра|гмя 12 дня": a leftover of the name before the day, not after a three-letter name
                # ("Ная бря 10" is not May 10)
                left = r'[а-яёѣіъ]{0,4}' if all(len(strip(nm)) > 3 for nm in MONTHS[m]) else ''
                da = re.match(left + r'\W*(\d{1,2})(?!\s*\d)', after)
                d = int((db or da).group(1)) if (db or da) else None
                if d is None:
                    dn = P.find('дня', mr[1])
                    d = day_in_words(P.between(mr[1], dn[0])) if dn and dn[0] - mr[1] <= 24 else None
                if d and 1 <= d <= 31:
                    out['birth_month'], out['birth_day'] = m, d
            if not out.get('birth_month') and not out.get('birth_day'):
                # the month is unreadable or not written ("1854 года Іюмья 22 дня", "родившаяся 25 Ігоня
                # 1901 г.", "родившаяся четвертаго дня"): the day is still read
                rest = P.orig[k:]
                dn = P.find('дня', vend)
                near = P.orig[k:P.map[dn[0]]] if dn and dn[0] - vend <= 45 else None
                dm = re.search(r'[^\d\s]\W*(\d{1,2})(?:г?о|аго)?[^\d\s]?\W{0,2}д[а-яѣ][яь]', rest[:60])
                dm = dm or re.match(r'[а-яёѣі\s]{0,8}(?:.{0,12}?(?:года|г\.))?\W*(\d{1,2})(?!\d)\W*[%s]{3,}' % LETTER, rest)
                d = int(dm.group(1)) if dm else None
                if d is None and near and not re.search(r'\d', near):
                    d = day_in_words(near)
                if d and 1 <= d <= 31:
                    out['birth_day'] = d
    if not (out.get('birth_month') and out.get('birth_day')) and (syn or doch):
        # "... Супруговъ дочь 20 Ноября родилась въ деревни ...": the date straight after "сынъ" / "дочь"
        kid = syn if out.get('sex') == 'M' or not doch else doch
        m, mr = month_after(P, kid[1], window=6)
        if mr:
            db = re.search(r'(?<!\d)(\d{1,2})\W*$', P.orig[P.map[kid[1]]:P.map[mr[0]]])
            da = re.match(r'\W*(\d{1,2})(?!\s*\d)', P.orig[P.map[mr[1]]:])
            d = int((db or da).group(1)) if (db or da) else None
            if d and 1 <= d <= 31:
                out['birth_month'], out['birth_day'] = m, d
    dv = P.find('деревн')
    # the case ending of "деревн-ѣ/-и/-ь" is skipped; not the capital of a village name
    # ("деревн Имбарахъ"), nor anything after the abbreviation ("въ дер. Іоденяхъ")
    ending = bool(dv) and dv[1] < len(P.flat) and P.flat[dv[1]] in 'еиь' and not P.orig[P.map[dv[1]]].isupper()
    if not dv:
        # later clerks abbreviate "въ деревнѣ" as "въ дер."
        md = re.search(r'(?<![А-Яа-яЁёѢѣІі])[дД]ер\.', P.orig)
        if md:
            dv = (next(i for i, k in enumerate(P.map) if k >= md.start()),
                  next(i for i, k in enumerate(P.map) if k >= md.end()))
    mst = None if dv else re.search(r'\bМ[.ѣ]', P.orig)
    sego = P.find('сего')
    if dv and sego and sego[0] <= dv[1]:
        # "родившійся сего 1869 года ... въ деревнѣ Кѣкштахъ сего прихода": the first "сего" is the year's
        ms = re.compile(r'(?<![%s])[сСc]е?г[оа](?![%s])' % (LETTER, LETTER)).search(P.orig, P.map[dv[1]])
        if ms and ms.start() - P.map[dv[1]] <= 40:
            sego = (flat_index(P, ms.start()), flat_index(P, ms.end()))
    if dv and sego and sego[0] > dv[1]:
        start = dv[1] + ending
        out['village'] = P.between(start, sego[0])
    elif dv:
        # no "сего прихода" (later formula): village runs to "прихода", a comma or end, max 3 words
        start = dv[1] + ending
        rest = P.orig[P.map[start]:] if start < len(P.map) else ''
        rest = re.split(r',|\.|\s(?:[А-Яа-я]+)?[Пп]ри[хк]о[дж]', rest)[0]
        words = rest.split()[:3]
        # "въ деревни Жеймяхъ Салантовскаго Прихода": the parish adjective is not part of the village
        cut = next((i for i, w in enumerate(words) if i and PARISH_ADJ.search(strip(letters_only(w)))), None)
        if cut:
            # ("Салан товскаго": a divided adjective takes its first half with it)
            words = words[:cut - 1] if cut > 1 and words[cut][0].islower() else words[:cut]
        out['village'] = ' '.join(words).strip(' -=') or None
    elif mst and sego:
        out['village'] = re.sub(r'\s+', ' ', P.orig[mst.start():P.map[sego[0]]]).strip(' ,.')
    by = G.find('были')
    out['godparents'] = G.between(by[1], len(G.flat)) if by else None
    # given names are single words: drop spurious spaces introduced by the recognizer
    for k in ('child_name', 'father', 'mother'):
        if out.get(k):
            out[k] = out[k].replace(' ', '')
    set_dates(out, entry.get('register_year'))
    return out


def set_dates(out, register_year):
    """baptism_date / birth_date from the months and days in `out`: the baptism falls in the register
    year; a birth in a later month than the baptism (e.g. December birth, January baptism) belongs to
    the previous year."""
    ry = register_year or 1888
    bm, bd = out.get('baptism_month'), out.get('baptism_day')
    out['baptism_date'] = f'{ry}-{bm:02d}-{bd:02d}' if bm and bd else None
    m, d = out.get('birth_month'), out.get('birth_day')
    if m and d:
        year = ry - 1 if bm and m > bm else ry
        out['birth_date'] = f'{year}-{m:02d}-{d:02d}'


def option(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else None


def main():
    src = Path(sys.argv[1])
    src = src if src.is_absolute() else ROOT / src if (ROOT / src).exists() else BOOK / src
    draft = json.loads(src.read_text())
    ann = {a['id']: a for a in json.loads((BOOK / 'training/annotations.json').read_text())}
    props = []
    for name in ('line_proposals_v2.json', 'line_proposals_years_v2.json'):
        if (BOOK / 'training' / name).exists():
            props += json.loads((BOOK / 'training' / name).read_text())
    cell_src = {}
    for p in props:
        a = ann.get(p['id'])
        c = 'skip' if a and a['status'] == 'rejected_crop' else (
            'checked' if a and a['status'] in ('image_checked', 'independently_checked') else 'model')
        cell_src.setdefault((p['row_id'], p['cell']), set()).add(c)
    which = {'baptism': ['baptism_month', 'baptism_day', 'baptism_date', 'priest', 'child_name'],
             'godparents': ['godparents', 'godfather', 'godmother', 'godmother_status']}
    stem = src.stem.replace('year_draft_', '')
    combined = tagger = None
    if '--tagger' in sys.argv or '--tagger-spans' in sys.argv:
        # the optional field tagger: its spans are read from a file, so no torch is needed here
        sys.path.insert(0, str(Path(__file__).resolve().parent / 'neural_parser'))
        sys.modules.setdefault('parse_entries', sys.modules[__name__])
        import combine
        spans_file = Path(option('--tagger-spans') or src.with_name(f'tagger_spans_{stem}.json'))
        if not spans_file.exists():
            sys.exit(f'no tagger spans at {spans_file}: run .venv-htr/bin/python pipeline/neural_parser/apply.py {src} first')
        tags, tagger = combine.load_spans(spans_file, draft['entries'])
        priest = option('--priest') or 'combine'
        combined = combine.combine_entries(draft['entries'], tags, priest=priest)
        tagger |= {'threshold': combine.THRESHOLD, 'priest': priest, 'township_wording': combine.township_wording(draft['entries'])}
    out = []
    for i, e in enumerate(draft['entries']):
        f = combined[i]['fields'] if combined else {k: {'value': v} for k, v in parse(e).items()}
        fields = {}
        for k, v in f.items():
            cell = next((c for c, ks in which.items() if k in ks), 'parents')
            s = cell_src.get((e['row_id'], cell), {'model'}) - {'skip'}
            # `source`: was the text checked; `by` / `conf` / `alt` (only with --tagger): who read the field
            fields[k] = {'value': v['value'], 'source': 'checked' if s == {'checked'} else 'mixed' if 'checked' in s else 'model'} \
                | {x: v[x] for x in ('by', 'conf', 'alt') if x in v}
        out.append({k: e.get(k) for k in ('row_id', 'register_year', 'scan', 'page', 'expected_entry_no', 'hand_group',
                                          'split', 'image', 'split_from', 'heading', 'heading_month')}
                   | {'fields': fields, 'text': {c: e[c] for c in ('baptism', 'parents', 'godparents')}})
    dst = Path(option('--out')) if option('--out') else BOOK / f'processed/entries_{stem}.json'
    rel = lambda p: str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
    doc = {'source': rel(src), 'model': draft.get('model', {}).get('model_path'),
           'note': 'Machine-extracted fields from machine drafts. Unverified.'}
    if tagger:
        doc['tagger'] = tagger
    dst.write_text(json.dumps(doc | {'entries': out}, ensure_ascii=False, indent=1))
    keys = ['sex', 'baptism_date', 'birth_date', 'child_name', 'father', 'mother', 'village', 'priest']
    report = {'entries': len(out), 'filled': {k: sum(1 for e in out if e['fields'].get(k, {}).get('value')) for k in keys},
              'out': rel(dst)}
    if tagger:
        report['tagger'] = {'stale': tagger['stale'], 'by': {b: sum(1 for e in out for v in e['fields'].values() if v.get('by') == b)
                                                             for b in ('both', 'tagger', 'rules')}}
    print(json.dumps(report, ensure_ascii=False))
    if '--check-pilot' in sys.argv:
        check_pilot(out)
    return 0


def check_pilot(entries):
    ref = {}
    for r in csv.DictReader(open(BOOK / 'processed/pilot_reference.csv')):
        if r['value'] and r['status'] != 'unresolved' and '[' not in r['value']:
            ref.setdefault((int(r['scan']), int(r['entry_no'])), {})[r['field']] = r['value']
    pairs = {'sex': 'sex', 'baptism_date': 'baptism_date', 'birth_date': 'birth_date',
             'child_name': 'child_name_ru', 'father': 'father_name_ru', 'mother': 'mother_name_ru',
             'village': 'village_ru'}
    by = {(e['scan'], e['expected_entry_no']): e for e in entries}
    print('\nAgainst pilot_reference (non-unresolved values only; reference is itself provisional):')
    for ours, theirs in pairs.items():
        n = exact = near = 0
        for key, r in ref.items():
            if theirs not in r or key not in by:
                continue
            n += 1
            v = (by[key]['fields'].get(ours) or {}).get('value')
            if v is None:
                continue
            a, b = strip(str(v)).replace(' ', ''), strip(r[theirs]).replace(' ', '')
            exact += a == b
            near += lev(a, b) <= max(1, len(b) // 5)
        print(f'  {ours:13} compared={n:3} exact={exact:3} near={near:3}')


if __name__ == '__main__':
    sys.exit(main())
