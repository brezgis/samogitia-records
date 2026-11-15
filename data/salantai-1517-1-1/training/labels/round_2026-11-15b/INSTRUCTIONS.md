# Reading instructions (Salantai 1517/1/1, 1856–1862)

You are a careful reader producing handwriting-recognition ground truth for a parish register. Work alone and blind: do NOT open annotations.json, anything under training/labels, training/predictions or processed/ of any book, or any other transcription, draft or model output, and do not open other readers' result files. Do not modify any existing file.

## The source
Salantai Roman Catholic baptism register, 1856–1862 (archive book LVIA 1517/1/1), Russian in clerks' cursive, pre-1918 spelling. Personal and place names are Lithuanian or Polish names written in Cyrillic. Each entry has three text columns. Typical wording in this book, for orientation only (transcribe what is WRITTEN, never what the formula predicts):
- baptism: "Тысяча восемсотъ пятьдесятъ седьмаго года Іюля тридцатаго дня въ Салантовскомъ Приходскомъ Р.К. Костелѣ мѣстнымъ Викарнымъ Ксендзомъ [priest] окрещенъ младенецъ именемъ [NAME] со всѣми обрядами таинства."
- parents: "Крестьянъ [father] и [mother] урожденной [maiden name, feminine form] [family surname, genitive plural] законныхъ супруговъ сынъ/дочь родившійся/родившаяся сего года [month] [day] дня поутру / вечеромъ, Салантовскаго Прихода въ деревни [village]."
- godparents: "Воспріемниками были Крестьяне [name surname] съ [name surname] дѣвицею / … супругою."
Several clerks write in this book. Learn each one's letterforms from the clear formula words of the same entry before reading its names. Known traps reported by earlier readers of this book: ѣ can look like a tall к; т is often written like m; и/н/п/л/ш and е/с are easily confused; one clerk puts a stroke under ш to tell it from и (that stroke is part of the letter, not underlining); capital Б can look like С; "ос" can look like "ае".

## Your material
`manifest.json` in this folder is keyed by entry id. For each of your entries it gives "sheets" (image paths, in order), "ids" (line ids in reading order) and "cells" (which column each line belongs to: baptism, parents, godparents). Each sheet shows up to 8 single-line crops enlarged 1.8x, numbered at the left; the number n is the index into that entry's "ids" list (numbering continues across the entry's sheets, starting at 0). Lines of one column follow each other, so read an entry as running text: a word divided at a line end continues on the next line of the same column, and the family surname in the parents column often recurs in the godparents column. Use that context to resolve letters, but only write on each line what is visible in that line's crop. Some lines are written on a slope; that is normal.

Read every sheet with the Read tool. When a line is hard, also Read its native crop at /home/anna/projects/samogitia-parishes/data/salantai-1517-1-1/training/proposals_years_v2/<line id>.png. Read /home/anna/projects/samogitia-parishes/docs/LABELING_GUIDE.md first.

## Rules
- Diplomatic transcription of exactly the complete characters visible in the crop: keep ъ, ѣ, і; do not modernise or correct the clerk's spelling ("восемсотъ", "деревни"); keep capitals, punctuation and abbreviations as written. Superscripts inline ("1го"). Underlining is not transcribed. Single spaces between words; when spacing is ambiguous, follow the word division.
- Line-end and line-start marks: write a hyphen as "-", a double stroke as "=". If the clerk's line-end mark is a dot or colon-like tick used as a hyphen, write "-". A filler dash after the end of the text is " -".
- A word the clerk struck through is not transcribed; say so in the note.
- Ink from neighbouring cells has been painted out with paper colour. A WHOLE glyph or punctuation mark that remains visible is transcribed; specks, printed rules, flourishes and strokes from the lines above or below are not.
- status "image_checked" ONLY if you are confident of every character after looking (no brackets in the text). Otherwise "draft", with each doubtful span in brackets with a question mark, e.g. "[Г?]елена". Be honest in both directions: do not bracket letters you can actually read, and do not pass a name you are guessing. "rejected_crop" (text "") if the crop is unusable: only rules/flourishes/blots, two text lines merged in one crop, or a glyph cut by the crop edge so its identity is hidden; say which in the note.

## Output
Write ONE file with the Write tool, named as your task says, in this folder: a JSON list with one object per line id for EVERY id of your entries, in manifest order:
[{"id": "<line id>", "text": "<transcription>", "status": "image_checked"|"draft"|"rejected_crop", "note": "<short note or empty>"}, ...]
Write no other files in this folder. Then reply with a short summary: lines per status, and anything about crops or conventions the project should know.
