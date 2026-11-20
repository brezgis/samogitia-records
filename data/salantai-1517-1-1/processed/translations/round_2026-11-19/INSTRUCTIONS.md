# Translation instructions: Salantai baptism register, 1856–1862 (LVIA 1517/1/1)

You translate machine-read drafts of Roman Catholic baptism register entries (Salantai parish, Samogitia, Lithuania; Russian in pre-1918 spelling) into direct, natural ENGLISH and LITHUANIAN. Do not modify any existing file. Do not open other translators' output files.

## Input
Your chunk file (named in your task) is a JSON list of entries {row_id, year, month_heading, baptism, parents, godparents, margin, warnings}. baptism / parents / godparents are the three text columns of one entry as read by a handwriting-recognition model; they contain errors: wrong letters (х/к, е/с, и/н, а/о, л/м), spurious spaces inside words, joined words, dropped letters, and "-атъ/-ятъ" for "-ахъ/-яхъ" in village names. The text follows a fixed formula in this book:
- Baptism: "Тысяча восемсотъ пятьдесятъ седьмаго года [month] [ordinal] дня въ Салантовскомъ Приходскомъ Римско-Католическомъ Костелѣ мѣстнымъ Викарнымъ / Альтаристомъ Ксендзомъ [priest] окрещенъ младенецъ / окрещено дитя именемъ [NAME] со всѣми обрядами Таинства." (one clerk writes the date in digits)
- Parents: "Крестьянъ [father] и [mother] урожденной [maiden name, feminine form] [family surname, genitive plural] законныхъ супруговъ сынъ/дочь родившійся/родившаяся сего года [month] [day] дня [поутру / вечеромъ / около полудня] Салантовскаго Прихода въ деревни [village]." There is no township in this book. Other estates occur (Дворянъ, Мѣщанъ, Шляхты, Однодворцевъ, Подданныхъ); an unmarried mother is "Крестьянки … незаконнорожденный/ая".
- Godparents: "Воспріемниками были Крестьяне [name surname] съ [name surname] дѣвицею / вдовою / [husband's name, gen.] супругою."
month_heading is a month the clerk wrote between entries ("Ноябрь.", "тоже"), where there is one.

### The margin
"margin" holds what was read, separately, from the narrow columns at the left of the entry: "surname" (the family surname the clerk wrote a second time in the margin, usually a genitive plural), "other_reading" (a second reader's different reading of it, if any), "support" ("confirmed by the parents column", "two readers agree", or "one reading, doubtful"), "entry_no", "sex" (M/F, from which count column is filled), "birth_day", "baptism_day", and "later_note" (a later annotation, sometimes Lithuanian of the 1920s).
- The margin surname and the family surname in the parents column are the same name written twice. Treat them as one name. Where the margin is "confirmed by the parents column" or "two readers agree", use the margin spelling for the family surname (unless the parents column and a godparent of the same family both clearly show a different letter: then give the form they support, with [?], and say so in issues) and do not mark it [?] for that reason alone (brackets inside the margin reading, like "Ле[к?]ніовъ", still mean a doubtful letter). Where it is "one reading, doubtful", weigh it against the parents column and "other_reading"; give the form best supported, mark it [?], and name the alternatives in issues.
- "sex" from the margin settles сынъ/дочь when the draft is garbled. Days in the margin are evidence for a garbled day in the text: if the text's day is unreadable you may give the margin's day, saying in issues that it comes from the margin; if a readable day in the text differs from the margin, keep the text and note the difference.
- Do not put the entry number or the margin itself into the translations. Translate a "later_note" in issues / issues_lt ("Later note in the margin: …").
"warnings", when present, describe a known fault of the row (pages from different openings, a missing half). Follow them and repeat the gist in issues / issues_lt.

## Lithuanian: follow the glossary
First read /home/anna/projects/samogitia-parishes/docs/LT_GLOSSARY.md and follow it exactly for every formula phrase, social term, family/status word, month, time of day, given-name form and surname rule. Its section 11 is written for this book (Salantai 1517/1/1): formula replacements (11.1), the twelve priests with ONE fixed form each (11.2: use exactly those forms; settle a garbled priest from the list and from the other entries of your chunk), the villages (11.3), terms and given names (11.4, 11.5). Where section 11 is silent, use the rules for the book of 1849–1854 (1827/1/18), whose wording is the same as here.

## English model
"In the year one thousand eight hundred and fifty-seven, on the [ordinal] day of [month], in the Salantai Roman Catholic parish church, the local vicar Fr. [priest] baptised an infant named [NAME] with all the rites of the Sacrament." / "Son/daughter of [father] and [mother] née [maiden name], [surname], lawfully married peasants, born on the [day] of [month] of this year in the morning, in the village of [village] of Salantai parish." / "The godparents were the peasants [name] and [name], [a maiden / a widow / wife of …]."

## English forms of surnames and villages (one rule for every translator)
- Family surnames and men's surnames: the SAME base form as your Lithuanian, written without Lithuanian diacritics being changed (Symutis, Možeikis, Kubilius, Mickevičius). Where the glossary's mechanical procedure leaves only a bare stem from an -овъ / -іовъ genitive plural, give that stem with [?] in both languages (Kubil [?]). Surnames in -скій / -цкій and their feminines, and names that are plainly Polish or Russian and take no Lithuanian ending, are romanised as written (Petrovskii, Petrovskaia). Women's maiden names: as written (feminine form), romanised, as in the Lithuanian "gim." form.
- Priests: the glossary's fixed Polish forms (11.2) in both languages.
- Villages: a village in the glossary's table 11.3 marked settled takes its modern name in both languages, without [?] (English: "in the village of Laiviai"). A draft spelling that only probably is one of them takes the modern name WITH [?] and a note in issues. Any other village: Lithuanian per the glossary; English the romanised form as written, put into the nominative only if the ending is plain, with [?].
- Given names in English: the standard Polish form when it is clearly that name (Jan, Kazimierz, Katarzyna), otherwise romanised with [?].

## Rules
1. Translate fully and directly into fluent sentences in each language; never word-by-word glosses. Use the year actually written in each entry.
2. Repair obvious misreadings of the formula's FIXED words, and join split words.
3. NEVER correct, guess or normalise personal names, surnames or villages beyond what the glossary allows. English: romanise (simplified Library of Congress: ж zh, х kh, ц ts, ч ch, ш sh, щ shch, ю iu, я ia, й i, ъ dropped, ѣ e, і i); the standard Polish given-name form only when it is clearly that name. Lithuanian: per the glossary (Lithuanian-alphabet transliteration, surnames reduced by its mechanical rules and declined correctly, standard Lithuanian given-name form only when clearly that name). Where a name is garbled, transliterate what is there and add [?]. The same family surname usually occurs twice in an entry (parents column; often a godparent): use that to settle the reading, and say so in issues when the two differ.
4. Garbled fragments: [illegible] (Lithuanian: [neįskaitoma]) or transliteration + [?]. Never invent content. An empty column gives "".
5. Keep dates and numbers exactly as the draft gives them; do not compute or correct. If the date is unreadable say so; do not supply one.
6. Deviations from the formula (twins, illegitimate birth, another parish, a different officiant, nobles, notes) must be translated, not dropped, and mentioned in issues / issues_lt.
7. A row that is not a baptism entry at all (stray printed heading, fragment) gets empty translations and an explanation in issues.

## Output
Write ONE file with the Write tool (path given in your task): a JSON list with one object per input entry, in the same order, for ALL entries of your chunk:
{"row_id": "...", "baptism_en": "...", "parents_en": "...", "godparents_en": "...", "baptism_lt": "...", "parents_lt": "...", "godparents_lt": "...", "names": ["Cyrillic as drafted -> English / Lithuanian", ...], "issues": "short English note on uncertain parts, or empty", "issues_lt": "the same note in Lithuanian"}
Then reply with a short summary: entries translated, how many have a doubtful name, the priests' names you settled on, and anything the project should know (formula variants, rows that are not entries, glossary rules that did not fit this book).
