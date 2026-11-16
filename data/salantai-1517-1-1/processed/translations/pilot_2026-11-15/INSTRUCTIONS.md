# Translation instructions: Salantai baptism register, 1856–1862 (LVIA 1517/1/1)

You translate machine-read drafts of Roman Catholic baptism register entries (Salantai parish, Samogitia, Lithuania; Russian in pre-1918 spelling) into direct, natural ENGLISH and LITHUANIAN. Do not modify any existing file. Do not open other translators' output files.

## Input
Your chunk file (named in your task) is a JSON list of entries {row_id, year, baptism, parents, godparents, margin_surname}: the three text columns of one entry (margin_surname is empty for this book). The drafts come from a handwriting-recognition model and contain errors: wrong letters (х/к, е/с, и/н, а/о, л/м), spurious spaces inside words, joined words, dropped letters. The text follows a fixed formula in this book:
- Baptism: "Тысяча восемсотъ пятьдесятъ седьмаго года [month] [ordinal] дня въ Салантовскомъ Приходскомъ Римско-Католическомъ Костелѣ мѣстнымъ Викарнымъ / Альтаристомъ Ксендзомъ [priest] окрещенъ младенецъ / окрещено дитя именемъ [NAME] со всѣми обрядами Таинства." (one clerk writes the date in digits)
- Parents: "Крестьянъ [father] и [mother] урожденной [maiden name, feminine form] [family surname, genitive plural] законныхъ супруговъ сынъ/дочь родившійся/родившаяся сего года [month] [day] дня [поутру / вечеромъ / около полудня] Салантовскаго Прихода въ деревни [village]." There is no township in this book. Other estates occur (Дворянъ, Мѣщанъ, Шляхты, Однодворцевъ); an unmarried mother is "Крестьянки … незаконнорожденный/ая".
- Godparents: "Воспріемниками были Крестьяне [name surname] съ [name surname] дѣвицею / вдовою / [husband's name, gen.] супругою."
The register year runs from January; an entry dated December of the previous year at the start of the book is normal.

## Lithuanian: follow the glossary
First read /home/anna/projects/samogitia-parishes/docs/LT_GLOSSARY.md and follow it exactly for every formula phrase, social term, family/status word, month, time of day, given-name form and surname rule. It was written for the Plungė books; use its rules for the book of 1849–1854 (1827/1/18), whose wording is the same as here ("Альтаристомъ/Викарнымъ онаго Кс.", "урожденной [fem. form] [family, gen. pl.]", time of day, no townships), with these replacements: the parish is Salantai, so "въ Салантовскомъ Р.К. Приходскомъ Костелѣ" is "Salantų Romos katalikų parapijos bažnyčioje", "Салантовскаго Прихода" is "Salantų parapijos", and "сего/здѣшняго прихода" is "šios parapijos".
Clergy: the glossary's list is Plungė's. For Salantai's priests apply the glossary's rule for clergy (surname in its Polish spelling, one fixed form per priest); the drafts garble them, so settle each priest's name from all the entries in your chunk before writing any. Names seen so far in this book (from earlier readings, forms to use): Клімовичъ → Klimowicz (Франциск), Монкевичъ → Monkiewicz (Іоаннъ), Янушевичъ → Januszewicz (Каспръ), Арвасевичъ → Arwasewicz, Контримъ → Kontrym. Others: Polish spelling by the same pattern, with [?] if unsure.

## English model
"In the year one thousand eight hundred and fifty-seven, on the [ordinal] day of [month], in the Salantai Roman Catholic parish church, the local vicar Fr. [priest] baptised an infant named [NAME] with all the rites of the Sacrament." / "Son/daughter of [father] and [mother] née [maiden name], [surname], lawfully married peasants, born on the [day] of [month] of this year in the morning, in the village of [village] of Salantai parish." / "The godparents were the peasants [name] and [name], [a maiden / a widow / wife of …]."

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
