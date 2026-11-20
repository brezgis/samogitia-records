You read the narrow left-hand columns of a Catholic baptism register: Salantai parish (Lithuania), 1856–1862, written in Russian (pre-1918 spelling) in a clerk's cursive. This is a reading task only: look at the images and report what is written. Do not look at any other file of the project, and do not use any earlier transcription.

## What each sheet shows

Each sheet image holds 2 entries (the last may hold 1), each headed "[n] <row_id>". For each entry the same strip of the page is shown twice:

- LEFT: the strip turned so that the sideways writing reads normally. At the bottom of it is the family surname written in the margin (printed column "Прозваніе крещаемыхъ"), in Cyrillic, usually a genitive plural ("Лекніовъ", "Яковицкой", "Страздевскихъ"). Later notes are sometimes written sideways across the other columns too (a court ruling correcting the surname, "Близнецы" for twins, and so on).
- RIGHT: the strip upright. After the surname column come five narrow columns, in this order: entry number (№); running count of boys; running count of girls; day of birth; day of baptism. Only one of the two counts is filled for a child (the other holds a ditto mark „ ), which tells the sex; twins can fill both.

The strip starts at this entry's own top rule and is cut generously long, because a surname often runs on past the entry's row. So the entry you are reading is the FIRST one in the strip: the top row of numbers in the upright view, the leftmost set of numbers in the turned view, and the surname that begins beside them. Below the next ruled line (upright view) or further right (turned view) the following entry usually begins, with its own numbers and the start of its surname: that is NOT this entry, ignore it. The end of the previous entry's surname may also poke in at the very top (upright) or far left (turned): ignore that too. Some strips hold no entry at all (a page heading, a blank): then return empty values and say so in `remark`.

## What to return for every entry

- `row_id`: as printed above the entry.
- `margin_surname`: exactly as written, letter for letter (keep ъ, ѣ, і; keep the case ending; do not normalise and do not turn it into a nominative). Put a doubtful letter in brackets with a question mark: "Ле[к?]ніовъ". If a whole name is unreadable, "".
- `margin_en`: romanisation of what is written (ж zh, х kh, ц ts, ч ch, ш sh, щ shch, ю iu, я ia, й i, ъ dropped, ѣ e, і i), keeping the brackets.
- `margin_lt`: Lithuanian-alphabet transliteration of what is written (ш š, ж ž, ч č, ц c, х ch, я ja, ю ju, й j, ъ dropped, ѣ e, і i), keeping the brackets. Never reconstruct a Lithuanian original name.
- `entry_no`, `boys_count`, `girls_count`, `birth_day`, `baptism_day`: digits as written; "" where the column holds a ditto mark, is empty or cannot be read.
- `sex`: "M" if the boys count is filled, "F" if the girls count is, "?" otherwise (or if both are).
- `notes_ru`: any other writing in these columns, transcribed exactly in its own language and script; `notes_en`: its English translation; `notes_lt`: its Lithuanian translation. "" if none.
- `uncertain`: list of the field names you are not sure of.
- `remark`: anything odd about the crop (cut off, wrong strip, two entries in one); "" otherwise.

Never guess. A value you cannot read is "" and its field name goes in `uncertain`. A plausible surname is worth nothing here; only what the ink shows.

## How to work

Read every sheet listed below with the Read tool (they are JPEG images), one or two at a time, and read both views of each entry. When you have read them all, write one JSON file at the output path given below, of the form {"entries": [ {...}, ... ]}, with one object per entry in the order read, and check that it parses. Then reply with one line: the number of entries written and how many have an uncertain surname.
