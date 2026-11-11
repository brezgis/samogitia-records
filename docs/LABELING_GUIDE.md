# Line labelling guide (HTR ground truth)

Labels pair one refined line crop (`training/line_proposals_v2.json`, images in
`training/proposals_v2/`) with the exact text visible in it. Batches go in
`training/labels/batch_NNN_<row>.json` and are merged with
`pipeline/merge_labels.py`. See that script's docstring for the format.

## Crops

`pipeline/refine_lines.py` extends each cell line so words that run across a
printed column rule stay whole. Ink belonging to neighbouring cells is painted with
the recorded paper colour (`mask_fill`); the export verifies that only those pixels
differ from the scan. A crop never contains half a glyph, but it can contain:

- a whole stray glyph or punctuation from a neighbouring cell (e.g. the comma after
  a child's name appearing at the start of the parents line). **Transcribe it:** it is
  visible text.
- specks and flourishes that are not characters. **Do not transcribe them;** say so in `note`.

Reject (`rejected_crop`) strips with only rules, flourishes, junk, two merged text
lines, or a glyph visibly cut by the top/bottom edge in a way that hides its identity.

## Transcription (diplomatic)

- Pre-1918 letters exactly as written: ъ, ѣ, і. Do not modernize, and do not add
  a letter the clerk omitted.
- In the later hand (spreads ~111+), **ѣ looks like a tall к** ("Апрѣля", "Костелѣ").
  In the early hand (≤ ~100), **т is written like m** and line-end hyphens are often
  a double stroke, transcribed `=`.
- Line-end/line-start hyphens and filler dashes as written (`три-`, `-бли`, `Прихода. -`).
- Superscripts inline: `12го`, `23го`. Underlining is not transcribed.
- Capitals and punctuation as written, including `1888.` if dotted.
- Single spaces between words; when spacing is ambiguous, follow the word division.

## Status

- `image_checked`: every character read with confidence. Exported for training and
  evaluation. One reader only: this is **not** independent verification.
- `draft`: any doubt. Mark it inline: `[Г?]елена`, `[Бекешіовъ?]`. Never exported. Names,
  villages and townships are usually drafts until a second source confirms them.
- Seeing the baseline model's output is recorded in the batch (`baseline_seen`). Treat
  it as a hint only. It modernizes spelling (drops ъ, writes е for ѣ).

## Known formula (for orientation, not for filling in unseen text)

Baptism: `Тысяча восемьсотъ восемьдесятъ восьмаго года [месяц] [день] дня, въ
Плунгянскомъ Р.К. Приходскомъ Костелѣ Викарнымъ Кс: [priest] окрещенъ младенецъ
именемъ [NAME] со всѣми обрядами Таинства.`
Parents: `Крестьянъ [township] волости [father] и [mother] изъ [maiden] [surname]
законныхъ супруговъ сынъ/дочь родившійся/родившаяся 1888 года [month] [day] дня въ
деревнѣ [village] сего Прихода.`
Godparents: `Воспріемниками были [name surname] съ [name surname] [status].`

The clerk's actual wording varies (e.g. `деревни`, `Яна и Францишки`). Transcribe what is
written, never what the formula predicts.
