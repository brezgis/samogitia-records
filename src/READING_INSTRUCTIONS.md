# Reading instructions: Plungė Roman Catholic baptism register, 1888

## Current source/identity rules

For new batches use `processed/queue.json` and its explicit image paths. Corrected
row numbering can differ from the original `rows/` directory. `expected_entry_no`
is an inferred coverage aid: read the actual number and retain uncertainty when it
is unclear. Do not copy the expected number as an observed fact.

The downloaded range includes 1887 and 1889 records and an administrative note;
only rows with `in_target_year: true` belong in the 1888 job. Check dates from the
image, not from that classification. The register year is the baptism-series year;
a baby baptised in January may have been born in December.

A reviewer who has seen earlier readings is not an independent third reader.
Gazetteer candidates inform separate normalization hypotheses and must never
replace the visible Cyrillic. Distinguish absent information from unreadable text.

For HTR training, transcribe the entire handwritten line, preserving line-end
hyphenation and historical letters. Selected fields cannot serve as full-line
labels. Check boundaries against the scan, including text crossing column rules.
Do not approve clipped, merged or ambiguous lines.

You are transcribing a 19th-century parish register from scanned page images. Accuracy matters
more than completeness: a wrong name is worse than a name marked unclear.

## The source

- Baptism register of the Plungė Roman Catholic parish (Samogitia, Lithuania), year 1888.
- Handwritten in Russian, pre-1918 spelling (ъ, ѣ, і), in a clerk's cursive. Names are Lithuanian
  or Polish names written in Russian letters.
- Each scan is a two-page spread. Each page is a printed table; one row is one baptism.
- Each spread has been cut into four overlapping crops: `NNNN_L1` (left page, top), `NNNN_L2`
  (left page, bottom), `NNNN_R1` (right page, top), `NNNN_R2` (right page, bottom). The top and
  bottom crops overlap, so a row near the middle appears in both: record it once.

## The columns, left to right

1. Margin, written sideways: the family surname.
2. Entry number (restarts at 1 each January), with a letter for sex: М (male) or Ж (female).
3. Two small numbers: day of birth, day of baptism.
4. When, where and by whom baptised. Formula: "Тысяча восемьсотъ восемьдесятъ восьмаго года
   [month] [day] дня въ Плунгянскомъ Р.К. приходскомъ Костелѣ [priest] окрещенъ младенецъ
   именемъ [CHILD NAME] со всѣми обрядами Таинства."
5. Parents. Formula: "[estate, e.g. Крестьянъ] [township] волости [FATHER] и [MOTHER] изъ
   [MOTHER'S MAIDEN NAME, genitive plural] [SURNAME, genitive plural] законныхъ супруговъ
   сынъ/дочь родившійся/родившаяся 1888 года [month] [day] дня въ деревнѣ [VILLAGE] сего прихода."
6. Godparents. Formula: "Воспріемниками были [NAME SURNAME] съ [NAME SURNAME] ..." with a note
   of marital status.

Later notes in other hands or languages sometimes appear in the margin; put them in `notes`.

## What to produce

Write one JSON file containing a list of objects, one per baptism entry, in page order:

```json
{
  "scan": 93,
  "entry_no": 8,
  "sex": "F",
  "birth_date": "1888-01-09",
  "baptism_date": "1888-01-10",
  "child_name_ru": "Анна",
  "priest_ru": "...",
  "estate_township_ru": "Крестьянъ Плунгянской волости",
  "father_name_ru": "...",
  "mother_name_ru": "...",
  "mother_maiden_ru": "... (as written)",
  "surname_ru": "... (as written in column 5)",
  "surname_margin_ru": "... (as written in the margin)",
  "village_ru": "...",
  "godparents_ru": "...",
  "surname_lt_guess": "likely Lithuanian form, or null",
  "village_lt_guess": "likely modern Lithuanian village name, or null",
  "uncertain": ["list of field names you are not confident in"],
  "notes": "anything else, including alternative readings like 'и or е in second letter'"
}
```

## Rules

- Transcribe what is written, letter by letter, in Cyrillic. Do not modernise spelling in the
  `_ru` fields.
- If you cannot read a word, write your best reading followed by `[?]`, or `[illegible]`, and
  add the field to `uncertain`. Give alternative readings in `notes`. Never fill a gap with a
  plausible-sounding name.
- Dates are as written in the register (Julian calendar); do not convert them.
- Work only from the images. Do not look anything up, and do not use any other source to decide
  what a name "should" be.
- Record every entry on the spread, including ones cut by the crop boundary (use both crops).
- When finished, reply with: the number of entries, how many have a non-empty `uncertain` list,
  and one sentence on legibility. Do not paste the JSON into your reply.

## When you are given row images instead of quarter-page crops

Files named `NNNN_L3.jpg` or `NNNN_R2.jpg` in the `rows` directory each show ONE table row (one
baptism) cut from scan NNNN, left or right page, counted from the top. There is no printed header
in a row image; the columns are in the same left-to-right order as described above. A row image
has a little of the neighbouring rows at its top and bottom edges: ignore text that belongs to
them. Add `"row_image": "NNNN_L3"` to each entry. If an image clearly contains two complete
entries, record both and say so in `notes`. If it contains no entry (a header or a blank), skip
it and mention it in your reply.
