# Neural field tagger for baptism entries: results (2026-11-15)

Question: can a sequence tagger pull the fields out of noisy recognizer text, and does it carry over
to a book it has not seen better than the rule parser (`pipeline/parse_entries.py`)?

**Short answer.** On every held-out Plungė book the character tagger finds the name fields more
often than the rules, by 15 to 25 points of F1 against the spans the translating agents listed, and
its family-surname span agrees with the independently read margin surname in 49–60% of entries
against 22–44% for the rules (1849–54: 32% against 22%). A fine-tuned XLM-R is about half a point
better than the character tagger, which is within what two seeds and the label noise can
distinguish. On the two unlabelled books (Salantai 1857–62, Plungė 1854–57) a blind reading of 50
disagreeing entries each put the tagger right in 126 and 139 of 161 judged fields, the rules in 12
and 8; counting only the fields `parse()` itself produces (priest, child, estate, township, father,
mother, village: no dates, no godparents, no maiden/surname split, which are this experiment's own
rules) it is 47 to 11 and 44 to 5. **Nothing here is measured against human-checked labels**: every "gold" is machine-made, the
reader of the samples was the experiment's own agent working from the draft text (no images), and
46% of all silver spans (29% of name-field spans) come from the rules alone.

## 1. Tag set

Fourteen tags, one span per field and column, tagged per character (IO: no B- tag is needed
because a field occurs once in a column). Each of the three columns is tagged on its own.

| column | tags |
|---|---|
| baptism | BAPT_DATE (the whole phrase "Тысяча … года <month> <day> дня"), PRIEST (name only, without "Кс." and titles), CHILD |
| parents | ESTATE (first estate word), TOWNSHIP (the adjective before "волости"), FATHER (with patronymic where written), MOTHER, MAIDEN, SURNAME (family surname), BIRTH_DATE ("сего 1869 года Мая 28. дня", "10 Мая 1900 года"; not the time of day), VILLAGE (name only, without the parish) |
| godparents | GODFATHER (given name and surname, no estate word or title), GODMOTHER (her given name and her own surname if written), GM_STATUS ("дѣвицею", "вдовою", or the husband's name with "супругою") |

## 2. Silver labels

Built by `build_silver.py` (rules in its docstring) for the 9,905 translated entries of five books.
Two sources: the agents' `names` lists placed in `source_text` (role from the English sentence, not
from the parser's anchors) and `parse()` placed back into the text. The date-phrase spans, the
maiden/surname split and all three godparent fields are **this experiment's own rules**, not
`parse()`. BAPT_DATE, ESTATE, BIRTH_DATE and GM_STATUS have no agent source, so the rules score 100%
on them by construction and those rows say nothing about rules against tagger.
Entry tier A = at least six name-field spans given identically (±2) by both sources and no
conflict; tier B = any other entry with a span. On the five translated books the adapter placed
99.9% of the values `parse()` returned (`preds/rules__*.adapter.json`); on Salantai it did not for
the birth date (section 5).

| book | entries | tier A | tier B | no span | spans in tier A entries | spans in tier B entries | both | names only | conflict | rules only | rules+part |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1827/1/18 (1849–54) | 1501 | 100 | 1393 | 8 | 1178 | 14446 | 5132 | 1287 | 1874 | 7187 | 144 |
| 1827/1/22 (1867–74) | 2062 | 371 | 1691 | 0 | 4456 | 18585 | 8810 | 1946 | 1783 | 10154 | 348 |
| 1886–1890 | 1701 | 365 | 1335 | 1 | 4826 | 15591 | 7615 | 2123 | 1252 | 9182 | 245 |
| 1827/1/24 (1896–1902) | 2582 | 219 | 2359 | 4 | 2751 | 26759 | 8906 | 4089 | 2460 | 13511 | 544 |
| 1827/1/25 (1902–07) | 2059 | 168 | 1888 | 3 | 2103 | 21015 | 7396 | 2926 | 2169 | 10335 | 292 |

| field | 1827/1/18 | 1827/1/22 | 1886–1890 | 1827/1/24 | 1827/1/25 | all | of which from the names lists |
|---|---:|---:|---:|---:|---:|---:|---:|
| BAPT_DATE | 1101 | 1638 | 1431 | 2061 | 1747 | 7978 | 0 |
| PRIEST | 1373 | 2012 | 1671 | 2505 | 1880 | 9441 | 3215 |
| CHILD | 1389 | 2021 | 1674 | 2472 | 1953 | 9509 | 6563 |
| ESTATE | 1145 | 1567 | 1326 | 1991 | 1510 | 7539 | 0 |
| TOWNSHIP | 2 | 1 | 1405 | 2245 | 1654 | 5307 | 1185 |
| FATHER | 1312 | 1873 | 1446 | 2180 | 1748 | 8559 | 7195 |
| MOTHER | 1351 | 1909 | 1533 | 2204 | 1764 | 8761 | 6588 |
| MAIDEN | 1350 | 1928 | 1582 | 2332 | 1825 | 9017 | 8609 |
| SURNAME | 1230 | 1853 | 1311 | 1852 | 1524 | 7770 | 4658 |
| BIRTH_DATE | 861 | 1360 | 1312 | 1546 | 1201 | 6280 | 0 |
| VILLAGE | 1320 | 1746 | 1486 | 2005 | 1512 | 8069 | 7480 |
| GODFATHER | 1443 | 2024 | 1662 | 2475 | 1968 | 9572 | 8363 |
| GODMOTHER | 1174 | 1879 | 1564 | 2310 | 1823 | 8750 | 5912 |
| GM_STATUS | 573 | 1230 | 1014 | 1332 | 1009 | 5158 | 0 |

| book | names items | placed in the text with a role cue | not found in the text | column ambiguous | English rendering not found | names spans judged partial |
|---|---:|---:|---:|---:|---:|---:|
| 1827/1/18 (1849–54) | 11532 | 10066 | 1147 | 106 | 212 | 231 |
| 1827/1/22 (1867–74) | 16276 | 14493 | 1384 | 248 | 150 | 432 |
| 1886–1890 | 14056 | 12837 | 116 | 182 | 919 | 312 |
| 1827/1/24 (1896–1902) | 20174 | 18188 | 703 | 212 | 1071 | 692 |
| 1827/1/25 (1902–07) | 16284 | 14269 | 1315 | 229 | 466 | 373 |

### Measured label error

Read by the experiment's agent against the draft text (not the image); B = an edge off by more than
two characters, W = wrong words. Notes: `readings/silver_audit_60.tsv`,
`readings/silver_audit_second_godparents.tsv` in the scratch folder.

First sample: 60 entries (6 per book and tier), all fields, 704 labels, 54 wrong (7.7%); 23 of 60
entries without a wrong label.

| field | labels | B | W | wrong | present in the text but unlabelled |
|---|---:|---:|---:|---:|---:|
| BAPT_DATE | 50 | 2 | 0 | 4% | 10 |
| PRIEST | 58 | 8 | 0 | 14% | 0 |
| CHILD | 60 | 2 | 0 | 3% | 0 |
| ESTATE | 49 | 1 | 0 | 2% | 11 |
| TOWNSHIP | 34 | 0 | 0 | 0% | 1 |
| FATHER | 56 | 1 | 1 | 4% | 2 |
| MOTHER | 57 | 1 | 0 | 2% | 3 |
| MAIDEN | 57 | 0 | 1 | 2% | 1 |
| SURNAME | 53 | 1 | 1 | 4% | 5 |
| BIRTH_DATE | 39 | 5 | 0 | 13% | 17 |
| VILLAGE | 48 | 0 | 0 | 0% | 10 |
| GODFATHER | 59 | 7 | 0 | 12% | 0 |
| GODMOTHER | 57 | 18 | 1 | 33% | 2 |
| GM_STATUS | 27 | 4 | 0 | 15% | 28 |

The godparent labels were too poor to train on, so two things were changed before any model was
scored: the godparent rule (divided status words, a husband's name without a readable "супругою",
a divided given name) and a "partial names" rule (agents often list a godparent by surname only).
The silver was rebuilt and frozen (md5 5b16a9b3…), and a second sample of 60 was drawn; only its
godparents column was re-read: GODFATHER 1 wrong of 60, GODMOTHER 1 of 58, GM_STATUS 2 of 44
(14 present but unlabelled). The other fields' figures above are from the first sample; their rules
did not change, apart from 36 PRIEST spans.

Main ways the silver is wrong:
- PRIEST: the rule span keeps "онаго Кс." or a piece of "Викарнымъ" before the name.
- BIRTH_DATE: `parse()` matches "Мая" inside "родивш**аяс**я" (see section 8); the span then starts in that word.
- Names placed approximately can stop short inside a divided word ("Стефано ви|ясмъ").
- Conflict spans (both sources, different edges; 9,538 spans) are the least reliable: the agents' item is kept and is sometimes only part of the name.
- Missing labels are the larger problem for coverage: BIRTH_DATE, BAPT_DATE and GM_STATUS exist only where the rules could read them. Training leaves those stretches out of the loss (they are not treated as "no field").

## 3. Models

- **char**: character embedding 64 + column embedding 8 -> 2-layer BiLSTM (2x192) -> softmax per
  character; 10 epochs, about 4 minutes; 5 MB.
- **xlmr**: `xlm-roberta-base` with a linear head over subwords, projected back to characters;
  3 epochs, about 8 minutes on the shared GPU; the subword embedding table is frozen (its gradient
  and optimizer state did not fit beside the other job: the first run skipped every batch and was
  discarded; all runs reported here skipped none). **rubert** (`DeepPavlov/rubert-base-cased`), same
  recipe, one seed.
- Noise augmentation on 70% of training sequences (letter substitutions from a confusion table
  counted on two draft versions of the training books only, deletions, spaces removed and inserted).
- Fixed epochs; nothing was selected on a held-out book. Installed: `transformers` 5.20.2 with its
  dependencies into `/mnt/ssd240gb/anna/samogitia-htr/neural-parser/pylibs` (used through
  PYTHONPATH; `.venv-htr` itself was not changed).

## 4. Leave-one-book-out

Train on four translated books, test on the fifth. All five folds for the character tagger (two
seeds each); XLM-R with two seeds, rubert, and two ablations of the character tagger on the early
book 1827/1/22 and the late book 1827/1/24.

Headline: name fields (PRIEST, CHILD, TOWNSHIP, FATHER, MOTHER, MAIDEN, SURNAME, VILLAGE,
GODFATHER, GODMOTHER), micro F1 within 2 characters, **gold = the agents' names spans only**.

| held-out book | rules | char (seed 1, seed 2) | xlmr (seed 1, seed 2) | rubert | char trained without rule-made name spans | char without augmentation |
|---|---:|---|---|---:|---:|---:|
| 1827/1/18 (1849–54) | 67.0 | 85.9 (84.9, 86.8) | | | | |
| 1827/1/22 (1867–74) | 76.1 | 90.8 (90.7, 90.9) | 91.4 (91.2, 91.5) | 91.1 | 91.3 | 89.9 |
| 1886–1890 | 76.7 | 93.6 (93.6, 93.5) | | | | |
| 1827/1/24 (1896–1902) | 66.4 | 91.5 (91.5, 91.5) | 92.0 (92.0, 92.0) | 91.7 | 92.7 | 90.7 |
| 1827/1/25 (1902–07) | 67.0 | 88.0 (88.2, 87.7) | | | | |

Same fields against **all silver spans** (a third of which are the rules' own): rules 77.7 / 83.0 /
83.8 / 78.0 / 77.5; char 82.3 / 90.8 / 92.5 / 90.8 / 88.6; xlmr 91.2 and 91.2 on the two books.

Reading the table:
- Seed-to-seed spread is 0.0–0.5 points, 1.9 on the smallest and oldest book (1849–54). The char/XLM-R/rubert differences (0.3–0.6) are consistent in sign but small; the label error measured above is larger than that.
- The gap is not only in the fields split by this experiment's own rules: against the agents' spans the tagger also leads on FATHER (92 / 97 against 87 / 77), MOTHER (93 / 92 against 85 / 67), CHILD (94 / 97 against 83 / 77) and VILLAGE (89 / 93 against 62 / 45) in the 1867–74 / 1896–1902 folds, and on PRIEST (68 / 79 against 64 / 70). The rules' MAIDEN and SURNAME figures include the last-word split, and GODFATHER/GODMOTHER are entirely this experiment's rule.
- The rules' deficit is mostly recall (R 58–70 against P 73–86): they give no value where an anchor is unreadable. The taggers answer nearly everywhere (P ≈ R ≈ 0.9).
- The tagger trained **without any rule-made name span** does as well or better against the agents' spans (91.3, 92.7), so its advantage is not an artefact of imitating the rules.
- Augmentation is worth 0.7–0.9 points.
- 1849–54 is the hardest book for both systems, and the only fold where the rules beat the tagger on tier A entries (98.2 against 91.4): it has the oldest wording and the fewest books like it in training.

Tier A and tier B separately (all silver spans, name fields, micro F1 ±2):

| held-out book | tier A: rules | tier A: char | tier B: rules | tier B: char |
|---|---:|---:|---:|---:|
| 1827/1/18 | 98.2 | 91.4 | 76.0 | 81.6 |
| 1827/1/22 | 98.4 | 98.4 | 79.3 | 89.0 |
| 1886–1890 | 99.0 | 97.7 | 78.7 | 90.9 |
| 1827/1/24 | 96.9 | 97.3 | 76.0 | 90.1 |
| 1827/1/25 | 97.3 | 96.9 | 75.4 | 87.8 |

Tier A is by definition where the rules already agree with the agents, so it cannot show a gain;
it shows the tagger does not lose much there. The whole difference is in tier B.

Where each system is alone in being right (agents' spans, ±2, char seed 1): tagger right and rules
not 2,177 / 2,640 / 2,737 / 5,312 / 3,693 spans in the five folds; rules right and tagger not
287 / 93 / 72 / 85 / 109.

### Independent checks (side columns read from the image by other agents)

Share of entries with a side-column value in which the system's span agrees with it (a missing
span counts as not agreeing). Days are decoded from the predicted date phrase by one decoder for
all systems.

| held-out book | surname = margin: rules | char | xlmr | baptism day: rules | char | birth day: rules | char | xlmr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1827/1/18 | 22% | 32% | | 68% | 70% | 54% | 63% | |
| 1827/1/22 | 44% | 57% | 58% | 72% | 75% | 63% | 74% | 74% |
| 1886–1890 | 29% | 51% | | 73% | 75% | 65% | 71% | |
| 1827/1/24 | 29% | 60% | 60% | 77% | 79% | 59% | 69% | 70% |
| 1827/1/25 | 28% | 49% | | 81% | 83% | 58% | 69% | |

Seed spread on these counts is under 1% of the entries, 1.3% for XLM-R's surname count on 1867–74 (counts per seed in the appendix).
Caveats: the margin is a single agent reading; the translating agents saw the margin, so the
silver surname is not independent of it, but the tagger's and the rules' spans are text only. The
ceiling is well under 100% because the recognizer often garbles the surname itself. Where the
rules do give a surname it agrees with the margin about as often as the tagger's does (53–57%
against 60–61% of spans given in the two main folds); the tagger's gain is mostly from answering
in more entries (1,864 against 1,640 in 1867–74; 1,836 against 958 in 1896–1902). The day figures credit the tagger for finding the phrase; the decoding
is the rule parser's own tables.

### What each gets right that the other misses (from the generated examples, agents' spans as gold)

Tagger right, rules not:
- 1827/1/22 0113_L1 MAIDEN «урожденной Давлевна Ма ценевъ»: rules «Давлевна Ма» (divided surname), tagger «Давлевна».
- 1827/1/22 0228_L3 GODFATHER «Крестьомъ Казимержръ Минеико»: rules keep the garbled estate word, tagger «Казимержръ Минеико».
- 1827/1/22 0046_L1 VILLAGE «въ деревнаъ Рулайцяхъ»: rules «аъ Рулайцяхъ», tagger «Рулайцяхъ».
- 1827/1/24 0119_L1 FATHER «волости Ишнатіяи Маріянныизъ Мицкусовъ»: rules nothing ("и" and "изъ" fused), tagger «Ишнатія».
- 1827/1/24 0028_R2 VILLAGE «въ дер. Варкаляхъ -дъѣмняго прнхода»: rules «аркаляхъ -дъѣмняго прнхода», tagger «Варкаляхъ».

Rules right, tagger not:
- 1827/1/22 0172_L1 PRIEST «Винарыемъ Кс. Пацевичемъ»: tagger «мъ Кс. Пацевичемъ» (it learned the silver's own priest error).
- 1827/1/22 0185_L5 FATHER «Анто са го Петронели»: rules «Анто», tagger «Анто са».
- 1827/1/24 0242_R1 GODMOTHER «съ Маль винсг Дуновского дѣпую»: agents and rules «Маль винсг», tagger «Маль винсг Дуновского» (here the tagger is arguably the one that is right, and the gold is partial).
- 1827/1/24 0225_L4 GODMOTHER «съ Зузанного Викентія Петровсвоео суетгою»: rules «Зузанного», tagger «Зузанного Ви».
- 1827/1/24 0196_R2 GODMOTHER «съ Лгодвиког Станнскава Виткевило дгогюю»: rules «Лгодвиког», tagger «ва Виткевило».

GODMOTHER is the tagger's weakest field (F1 73–80 against the agents' spans): where her name ends
and the husband's or the status begins depends on a garbled closing word.

### Leakage

No column text (over 40 characters, punctuation and case ignored) of any of the seven books occurs
in another book, including the shared years 1854 (1827/1/18 and 1827/1/20) and 1902 (1827/1/24 and
1827/1/25); no row id is repeated inside a book. Training asserts that no entry of the held-out
book is among the training entries; only one draft version per entry (the translated one) is ever
used; the confusion table for augmentation is counted on the training books of each fold. The same
family names and villages recur across books, which is the intended situation.

## 5. Salantai 1517/1/1 and Plungė 1827/1/20 (nothing labelled)

Models trained on all five translated books. Rules against the character tagger: it was the only
all-books model trained when the comparison was run, and it is the cheaper of two near-equal models.

The adapter placed every value `parse()` filled on these two books except: Salantai BIRTH_DATE 445
of 508 (the "4. Ноября родился" wording has the date before the verb, which this experiment's
date-span rule does not cover: those 63 are the span rule's misses, not `parse()`'s), 1827/1/20
ESTATE 753 of 764 and BIRTH_DATE 474 of 476. `parse()` itself fills father in 588 and 629 entries.


### Salantai 1517/1/1 (1857-62, draft crnn-ru-v4), 677 entries

| field | rules filled | char filled | both filled (rules, char) | same ±2 | differ | only rules | only char |
|---|---:|---:|---:|---:|---:|---:|---:|
| BAPT_DATE | 609 | 665 | 609 | 604 | 5 | 0 | 56 |
| PRIEST | 635 | 664 | 635 | 594 | 41 | 0 | 29 |
| CHILD | 640 | 663 | 638 | 621 | 17 | 2 | 25 |
| ESTATE | 669 | 660 | 655 | 647 | 8 | 14 | 5 |
| TOWNSHIP | 6 | 14 | 0 | 0 | 0 | 6 | 14 |
| FATHER | 583 | 634 | 583 | 568 | 15 | 0 | 51 |
| MOTHER | 582 | 664 | 581 | 578 | 3 | 1 | 83 |
| MAIDEN | 601 | 634 | 601 | 530 | 71 | 0 | 33 |
| SURNAME | 599 | 650 | 598 | 543 | 55 | 1 | 52 |
| BIRTH_DATE | 445 | 610 | 439 | 397 | 42 | 6 | 171 |
| VILLAGE | 569 | 660 | 569 | 388 | 181 | 0 | 91 |
| GODFATHER | 647 | 663 | 647 | 518 | 129 | 0 | 16 |
| GODMOTHER | 473 | 665 | 473 | 429 | 44 | 0 | 192 |
| GM_STATUS | 437 | 545 | 434 | 421 | 13 | 3 | 111 |

Entries where rules and the char tagger differ on at least one field: 536 of 677.

### 1827/1/20 (1854-57, draft plunge-v7), 790 entries

| field | rules filled | char filled | both filled (rules, char) | same ±2 | differ | only rules | only char |
|---|---:|---:|---:|---:|---:|---:|---:|
| BAPT_DATE | 622 | 783 | 621 | 616 | 5 | 1 | 162 |
| PRIEST | 756 | 777 | 756 | 704 | 52 | 0 | 21 |
| CHILD | 744 | 769 | 741 | 691 | 50 | 3 | 28 |
| ESTATE | 753 | 756 | 735 | 709 | 26 | 18 | 21 |
| TOWNSHIP | 5 | 56 | 0 | 0 | 0 | 5 | 56 |
| FATHER | 625 | 720 | 624 | 612 | 12 | 1 | 96 |
| MOTHER | 625 | 777 | 625 | 613 | 12 | 0 | 152 |
| MAIDEN | 672 | 731 | 672 | 594 | 78 | 0 | 59 |
| SURNAME | 669 | 763 | 668 | 603 | 65 | 1 | 95 |
| BIRTH_DATE | 474 | 768 | 473 | 464 | 9 | 1 | 295 |
| VILLAGE | 639 | 748 | 636 | 460 | 176 | 3 | 112 |
| GODFATHER | 761 | 776 | 761 | 623 | 138 | 0 | 15 |
| GODMOTHER | 659 | 774 | 658 | 424 | 234 | 1 | 116 |
| GM_STATUS | 557 | 737 | 557 | 529 | 28 | 0 | 180 |

Entries where rules and the char tagger differ on at least one field: 706 of 790.

Agreement where both fill a field is high for the baptism date, father and mother (97–99%; estate 96–99%, birth date 90–98%) and lower for
VILLAGE (68–72%), GODFATHER (80–82%), GODMOTHER (64% in 1827/1/20) and MAIDEN/SURNAME (88–91%).

### Blind reading of 50 disagreeing entries per book

For each sampled entry the two systems' spans were shown as X and Y in random order and judged
against the draft text by the experiment's agent (not against the image), then unblinded. The
reading is only partly blind: the order was shuffled, but each system's habits (the rules keeping
"Крестьянинъ", the tagger answering where the other has "—") are recognisable. Unblinded
(`results/disagreements_*.txt`, `.key.json`, `readings/disagreements_*.tsv`). "Tagger right" includes
cases where the rules gave nothing and the tagger's span is right, and the reverse.

Salantai 1517/1/1:

| field | tagger right | rules right | both | neither |
|---|---:|---:|---:|---:|
| BAPT_DATE | 6 | 0 | 0 | 2 |
| PRIEST | 3 | 1 | 1 | 0 |
| CHILD | 0 | 3 | 0 | 0 |
| ESTATE | 3 | 0 | 0 | 0 |
| TOWNSHIP | 1 | 3 | 0 | 0 |
| FATHER | 7 | 3 | 0 | 1 |
| MOTHER | 7 | 0 | 0 | 2 |
| MAIDEN | 12 | 0 | 0 | 0 |
| SURNAME | 10 | 1 | 0 | 1 |
| BIRTH_DATE | 7 | 0 | 0 | 5 |
| VILLAGE | 26 | 1 | 0 | 1 |
| GODFATHER | 11 | 0 | 0 | 6 |
| GODMOTHER | 21 | 0 | 0 | 3 |
| GM_STATUS | 12 | 0 | 0 | 1 |
| ALL | 126 | 12 | 1 | 22 |

Plungė 1827/1/20:

| field | tagger right | rules right | both | neither |
|---|---:|---:|---:|---:|
| BAPT_DATE | 9 | 0 | 0 | 1 |
| PRIEST | 0 | 0 | 0 | 0 |
| CHILD | 5 | 1 | 0 | 0 |
| ESTATE | 3 | 0 | 0 | 2 |
| TOWNSHIP | 2 | 4 | 0 | 0 |
| FATHER | 7 | 0 | 0 | 1 |
| MOTHER | 9 | 0 | 0 | 2 |
| MAIDEN | 12 | 0 | 0 | 0 |
| SURNAME | 12 | 0 | 0 | 0 |
| BIRTH_DATE | 26 | 1 | 1 | 0 |
| VILLAGE | 18 | 0 | 0 | 2 |
| GODFATHER | 12 | 1 | 0 | 0 |
| GODMOTHER | 17 | 0 | 0 | 3 |
| GM_STATUS | 7 | 1 | 1 | 1 |
| ALL | 139 | 8 | 2 | 12 |

What the disagreements are:
- VILLAGE: the rules keep the parish adjective ("Жеймяхъ Салантовскаго") or give nothing; the tagger stops at the village.
- MAIDEN / SURNAME: a surname divided by the recognizer ("Меш кисовъ") is split wrongly by the last-word rule.
- GODFATHER / GODMOTHER: the rules keep "Крестьянинъ / Крестьянкою" misread, or give nothing when "съ" is missing (Salantai often writes "X и Y").
- Dates: the rules give nothing when the month or "года" is misread; the tagger still marks the phrase (whether the day can then be decoded is another matter).
- The tagger's own errors: it invents a TOWNSHIP in these early books (7 of 10 judged township disagreements went to the rules: there is none to find), tags an unmarried mother's name and surname together as MOTHER, and on Salantai's "4. Ноября родился" wording (date before the verb) marks only part of the date.
- Without the dates and godparent fields (this experiment's own rules) the count is 69 tagger, 12 rules, 1 both, 5 neither on Salantai and 68, 5, 0, 7 on 1827/1/20; of those, MAIDEN/SURNAME (the last-word split) are 22 and 24 for the tagger, 1 and 0 for the rules.
- "Neither" (22 and 12 fields) is mostly run-on or badly garbled text.

## 6. What to use in the pipeline today

A combination, with the tagger as the span finder and the rules kept for what they do exactly:

1. Run both. Where they agree within two characters, take the span and mark it corroborated (tier A
   behaviour: both score 97–99 against the silver there, except the tagger on 1849–54, 91).
2. Where they differ or the rules give nothing, take the **tagger's** span for CHILD, FATHER,
   MOTHER, MAIDEN, SURNAME, VILLAGE, GODFATHER, GODMOTHER, GM_STATUS and both date phrases, and
   mark it uncorroborated.
3. Keep the **rules** for TOWNSHIP in books before 1886 (drop the tagger's) and for turning a date
   phrase into month and day (the decoder, applied to the tagger's phrase when the rules found none).
   PRIEST is undecided: against the agents' spans the tagger leads (68 / 79 against 64 / 70), against
   all silver the rules do, and two thirds of the PRIEST silver is the rules' own, with the "онаго
   Кс." prefix error in it; strip a leading "Кс." from either.
4. The character tagger is enough; XLM-R's half point does not justify 550 MB and a GPU.

Why not the tagger alone: its training labels are 46% rule-made (29% for names) and 5–15% wrong on some
fields, it has no notion of a field being absent in a given wording, and its advantage is largest
exactly where no trustworthy label exists to check it.

## 7. What a gold set would need to settle it

- About 300 entries: 40–50 from each of the seven books (both unlabelled ones included), drawn at
  random and not by tier, so that garbled and unusual entries (unmarried mothers, twins, foundlings,
  nobles with titles, clergy as godparents) are represented.
- Character spans marked on the draft text by a person, for all fourteen fields, with an explicit
  "absent" where a field is not in the entry (that is what the silver cannot express) and written
  rules for divided words, fused "и"/"изъ"/"съ", patronymics and the husband's name.
- A second annotator on a third of them, to know how much two careful readers differ on the edges;
  the ±2 tolerance should be set from that.
- For names, the reading from the image beside the span, so that "right span, wrong letters" can be
  separated from "wrong span".
- With that, the table in section 4 can be redone with real precision (today a prediction where
  there is no silver span cannot be judged at all: 3,000–5,700 such tagger spans per book).

## 8. Found on the way (not changed: existing files were not touched)

Both were fixed on 2026-11-16 (section 10; `parse_entries.py` docstring). The tables of sections 2–5 were made before the fix.

- `parse_entries.py`: `month_after(P, rod[1], window=40)` can match "Мая" inside
  "родивш**аяс**я"; when the real month is misread by a letter the tie goes to May, so the birth
  month becomes 5 in some daughters' entries (1827/1/24 0124_R4, 0114_L2).
- `parse()` takes the first word as the estate whatever it is, and "волости" matches surnames such
  as "Волонтетвъ", which then produces a township made of the parents' names.

## 9. Files

- Code: `pipeline/neural_parser/common.py`, `build_silver.py`, `train_tagger.py`, `evaluate.py`.
- Pipeline step (section 10): `apply.py` (tagger -> spans file), `combine.py` (rules + tagger), `validate_combination.py`
  (threshold and held-out scores; results in the scratch `results/combination_choose.md`, `combination_report.md`);
  held-out weights `models/char__<book>__s1__lobo.pt`; stable copy of the all-books model in
  `/mnt/ssd240gb/anna/samogitia-htr/models/field-tagger-v1/`.
- Scratch `/mnt/ssd240gb/anna/samogitia-htr/neural-parser/` (about 0.8 GB): `silver/` (silver.jsonl,
  stats, the two audit samples), `preds/` (every run's predictions and the cached rule spans),
  `models/char__none__s1.pt` (5 MB) and `models/xlmr__none__s1.pt` (556 MB, half precision),
  `results/` (lobo.md/json, unlabelled.md, leakage.md, reading sheets, keys and verdicts), `logs/`
  (the log `--model_xlmr_--heldout_plunge-1827-1-22_--seed_1.log` is the discarded run; its rerun is `xlmr_22_s1_rerun.log`),
  `run_queue.sh`, `pylibs/`.

## 10. The combination as a pipeline step (2026-11-16)

Section 6 is now code. `apply.py` tags a draft and writes the spans with a confidence each (mean
probability of the span's tag over its characters); `combine.py` chooses each field between the
rules and the tagger; `parse_entries.py --tagger` writes the result (off by default; `FIELD_TAGGER=1`
in `run_book.sh`). The two parser bugs of section 8 are fixed in `parse_entries.py`, so "rules"
below is the fixed parser; "rules (published)" is the cached baseline of section 4.

**Nothing here is measured against human-checked labels either.** The combination's settings were
chosen on three held-out folds and it is reported on the other two; all five folds use the same
silver, and the reported folds' rules and tagger figures were already known from section 4.

### What the combination does

- child, father, mother, maiden name, family surname, village, godfather, godmother, her status:
  where rules and tagger agree (span ends within 2 characters, the same letters, or one is the other
  less formula words such as "Крестьянинъ" or "... Салантовскаго прихода") the field is marked
  `both`; otherwise the tagger's span is taken if its confidence reaches the threshold, else the
  rules' value stays (or the field stays empty) and the tagger's span is kept as `alt`.
- township: the tagger is heard only in a draft file where the rules themselves find "волости" /
  "Вол." in at least a fifth of the entries; elsewhere its township is dropped.
- dates: the rules' month and day; where the rules have no complete date, the tagger's phrase is
  decoded with the rules' tables if its confidence reaches the threshold.
- priest: section 6 left it undecided and the first specification was "keep the rules' value, tagger
  as alternative". On every fold that is worse than treating the priest like a name after taking
  "Кс." and titles off the tagger's span (PRIEST F1 ±2 against the agents' spans, choosing folds:
  68.9 / 84.4 / 71.4 against 71.2 / 87.8 / 73.5; reported folds: 65.3 / 74.9 against 68.4 / 77.9,
  tagger alone 68.1 / 77.2). So the default
  is the name treatment; `--priest rules` gives the first specification.
- estate, sex and the old fields `maiden_and_surname` and `godparents`: rules only.

### Threshold (chosen on 1827/1/18, 1886–1890, 1827/1/25; each tagged by the model trained without it)

Tagger spans the rules do not corroborate, where the agents listed the name (right = within 2
characters of the agents' span):

| confidence | rules gave another value: n | tagger right | rules right | rules gave nothing: n | tagger right |
|---|---:|---:|---:|---:|---:|
| 0.00–0.50 | 13 | 0% | 69% | 26 | 15% |
| 0.50–0.60 | 67 | 9% | 66% | 74 | 34% |
| 0.60–0.70 | 121 | 26% | 43% | 108 | 35% |
| 0.70–0.80 | 251 | 44% | 30% | 250 | 34% |
| 0.80–0.90 | 423 | 54% | 17% | 518 | 49% |
| 0.90–0.95 | 351 | 56% | 15% | 548 | 71% |
| 0.95–0.98 | 532 | 77% | 7% | 800 | 85% |
| 0.98–1.00 | 2320 | 96% | 1% | 3404 | 97% |

Rule used: the lowest confidence from which (a) a tagger span that contradicts the rules is right
more often than the rules' value and (b) a span the rules cannot corroborate at all is right about
as often as not. (a) holds from 0.7, (b) from 0.8: **threshold 0.8**. The family surname is the one
field that does not follow the pattern: below 0.8 its spans are still right in 108 of 133 cases
where the rules' last-word split says something else (the rules: 1) and in 66 of 113 where the rules
have nothing, so its threshold is **0.5**. Maximising F1 was not the criterion: F1 is nearly flat
from 0 to 0.8 (85.6–86.9 / 94.0–94.1 / 87.7–88.0 on the three folds), because a prediction where no
gold exists is not counted against a system; the threshold is there for those unjudged spans. At the
defaults 1,760 tagger spans are withheld on the three folds. Dates decoded from the
tagger's phrase where the rules had none agree with the side column in 93–99% of 159 cases above
0.98 and 86–100% of 66 between 0.8 and 0.98; only 9 fall below 0.8.

Other choices looked at on the same three folds (name fields, micro F1 ±2 against the agents'
spans; rules 67.1 / 77.1 / 67.0, tagger 85.1 / 93.7 / 87.9): defaults 87.6 / 94.2 / 88.1; agreed
spans taken from the rules instead of the tagger 87.5 / 94.1 / 88.0 (and 1.3–1.6 points lower on
exact edges: 83.4 / 89.5 / 83.8 against 84.8 / 91.1 / 85.1); township gate per entry 87.6 / 94.0 / 88.0, township never from the tagger 87.6 / 93.8
/ 87.9; priest from the rules only 87.5 / 94.0 / 88.0. Largest per-field deficit of the defaults
against the better single system on these folds: SURNAME −0.6 (1827/1/18), TOWNSHIP −0.5 and MAIDEN
−0.3 (1886–1890), MAIDEN −0.3 (1827/1/25).

### The two reported folds (settings fixed before they were scored)

The combination's settings (threshold, township gate, priest, agreed spans) were not touched after
these folds were first scored. The rule parser and the date decoder were: the day decoding faults
found on Salantai and in a review of the parser diff were fixed afterwards, and the tables below are
from the final code. The name-field figures did not move; the day rows moved by under one point.

Name fields, F1 within 2 characters, gold = the agents' names spans only:

| field | 1827/1/22: rules | tagger | combination | 1827/1/24: rules | tagger | combination |
|---|---:|---:|---:|---:|---:|---:|
| PRIEST | 63.7 | 68.1 | 68.4 | 70.0 | 77.2 | 77.9 |
| CHILD | 83.5 | 93.6 | 93.6 | 76.5 | 97.7 | 97.6 |
| TOWNSHIP | – | – | – | 77.1 | 83.3 | 83.6 |
| FATHER | 86.9 | 92.1 | 92.5 | 78.0 | 97.1 | 97.2 |
| MOTHER | 84.9 | 93.3 | 94.4 | 68.1 | 91.8 | 92.0 |
| MAIDEN | 76.3 | 96.7 | 96.9 | 48.5 | 95.9 | 95.9 |
| SURNAME | 79.2 | 94.9 | 94.7 | 59.4 | 94.6 | 94.5 |
| VILLAGE | 61.7 | 88.9 | 89.1 | 44.0 | 93.6 | 93.5 |
| GODFATHER | 77.1 | 96.0 | 95.9 | 84.1 | 95.6 | 95.7 |
| GODMOTHER | 67.4 | 79.7 | 79.7 | 66.0 | 73.0 | 73.3 |
| **micro** | 76.2 | 90.8 | **91.0** | 66.7 | 91.6 | **91.7** |

Published in section 4 for the same folds: rules 76.1 and 66.4, char 90.8 (90.7, 90.9) and 91.5
(91.5, 91.5). The tagger here is a retrained seed-1 model (weights had not been kept); it scores
90.8 and 91.6. No name field of the combination is more than 0.2 below the better single system;
the seed spread of section 4 is 0.0–0.5. Against all silver spans: rules 83.0 / 78.2, tagger 90.9 /
91.0, combination 91.2 / 91.4.

So on names the combination is the tagger, not better than it: +0.1 to +0.2 is inside the seed
spread. What it adds is not visible in this table: the `both` mark (54–87% of the entries per name field in
1867–74, 37–80% in 1896–1902), no invented townships in the early books (0 in 1867–74), the rules' dates,
and low-confidence spans held back.

Side-column checks (agreeing / produced / entries with a side-column value), as in section 4:

| check | 1827/1/22: rules (published) | rules | tagger | combination | 1827/1/24: rules (published) | rules | tagger | combination |
|---|---|---|---|---|---|---|---|---|
| family surname = margin | 865 / 1640 / 1954 (44%) | 865 / 1640 (44%) | 1108 / 1875 (57%) | 1102 / 1869 (56%) | 544 / 958 / 1894 (29%) | 553 / 971 (29%) | 1125 / 1840 (59%) | 1125 / 1834 (59%) |
| baptism day, decoded from the span | 1481 / 1630 / 2049 (72%) | 1472 / 1685 (72%) | 1537 / 2049 (75%) | 1527 / 1756 (75%) | 1863 / 1949 / 2422 (77%) | 1857 / 1975 (77%) | 1925 / 2420 (79%) | 1913 / 2038 (79%) |
| birth day, decoded from the span | 1285 / 1350 / 2043 (63%) | 1445 / 1620 (71%) | 1496 / 2036 (73%) | 1504 / 1688 (74%) | 1469 / 1723 / 2479 (59%) | 1672 / 1956 (67%) | 1721 / 2456 (69%) | 1704 / 1991 (69%) |
| baptism day, the output's own value | | 1762 / 1797 (86%) | | 1817 / 1853 (89%) | | 2027 / 2093 (84%) | | 2082 / 2151 (86%) |
| birth day, the output's own value | | 1618 / 1728 (79%) | | 1677 / 1792 (82%) | | 1942 / 2147 (78%) | | 1973 / 2181 (80%) |

"Decoded from the span" is section 4's measure: one decoder applied to each system's date span (for
the rules, the adapter's span). "The output's own value" is the day `parse_entries.py` writes: the
rules read a day in more ways than the span decoder does, which is why those rows are higher and
why the combination keeps the rules' dates. The rules' own birth-day rise from 63% to 71% and 59% to
67% is the "Мая inside родившаяся" fix. The margin count of the combination is 6 entries under the
tagger's in 1867–74 (0.3%; the published seeds differ by 7). In the "decoded from the span" rows the
combination is 10–17 entries (0.5–0.7%) under the tagger alone on three of the four day checks: it
gives fewer dates (1,756 against 2,049 baptism spans in 1867–74) because it takes the tagger's phrase
only where the rules have nothing and the phrase decodes under the stricter rule. Of the months it
did take from the tagger, 133 of 141 fit the baptism months of the neighbouring entries in 1867–74
and 99 of 104 in 1896–1902 (2 more have too few neighbours); every May among them (9 and 16) fits.

### Salantai 1517/1/1 (all-books model, drafts as re-assembled 2026-11-17 00:11, 673 entries)

Written to `/mnt/ssd240gb/anna/samogitia-htr/neural-parser/apply/entries_<year>_crnn-ru-v4.combined.json`
(the book's own entries files were not touched).

| field | filled | both agree | tagger, rules empty | tagger over a differing rules value | rules, tagger empty | rules kept, tagger differs below threshold | tagger withheld, rules empty | empty |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| child | 661 | 621 | 21 | 16 | 2 | 1 | 2 | 10 |
| father | 631 | 574 | 42 | 11 | 0 | 4 | 1 | 41 |
| mother | 647 | 584 | 58 | 3 | 1 | 1 | 14 | 12 |
| maiden name | 633 | 532 | 28 | 71 | 0 | 2 | 0 | 40 |
| family surname | 648 | 544 | 48 | 54 | 1 | 1 | 1 | 24 |
| village | 642 | 414 | 61 | 152 | 0 | 15 | 17 | 14 |
| godfather | 667 | 554 | 15 | 90 | 0 | 8 | 1 | 5 |
| godmother | 638 | 439 | 161 | 35 | 0 | 3 | 30 | 5 |
| godmother's status | 542 | 428 | 99 | 11 | 3 | 1 | 11 | 120 |
| priest | 663 | 613 | 23 | 26 | 0 | 1 | 1 | 9 |
| township | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 673 |
| baptism day | 630 | 606 (same date decoded) | 14 | 3 | 32 (rules; tagger's phrase absent or not decodable) | 1 | 0 | 17 |
| birth day | 553 | 481 (same date decoded) | 14 | 0 | 59 (as above; 19 of them a day without a month) | 1 | 2 | 116 |

Of the 31 dates taken from the tagger's phrase (17 baptism, 14 birth), 30 have a month that fits
the baptism months of the four entries before and after; three are May and all three fit.

Forty entries drawn at random (seed 20261117) were read against the draft text by the agent that
wrote this step (not against the image, and not blind): 464 of 480 fields right, 28 entries without
an error. Right / wrong: baptism date 39 / 1, priest 39 / 1, child 39 / 1, father 39 / 1, mother
40 / 0, maiden name 40 / 0, family surname 39 / 1, birth date 37 / 3, village 35 / 5, godfather
39 / 1, godmother 39 / 1, her status 39 / 1. "Right" means the value is the field's words as the
draft has them (a garbled name correctly delimited counts as right); a field present in the text
but left empty counts as wrong; a date whose month or day the draft itself does not show counts as
right when left empty. The village is the weak field: two were left empty, one is a rules' leftover
("оъ"), one keeps "Мѣстечкѣ" fused to the name, one keeps it from the rules. The reading found two
decoding faults that were then fixed in `parse_entries.py`, and the four dates concerned (entry 11's
baptism, entry 12's baptism and birth, entry 21's baptism) are counted as they stand after the fix
(before it: 460 of 480): "двадцать востого" was decoded as 26 (as near to "шестаго" as
to "восьмаго"; `ORDINALS` now has "восмаго"), and "12 Юня" as the 1st (the month match took the "2"
for the name's first letter).

The date decoder: `combine.py` uses `decode_date(strict=True)`, which finds the month as the fixed
rule parser does. The experiment's decoder (`strict=False`, the one behind every "decoded from the
span" row here and in section 4) still looks for month names freely and gives May for "Іюмья 22" or
"Наября"; it is kept only so those rows stay comparable, and they compare the day alone.

### Not to be trusted yet

- Any single name: a right span around a misread word is still a misread word.
- `both` is corroboration by two systems that share training signal (the tagger learned partly from
  the rules), not an independent check.
- The threshold on a new parish or clerk: it was set on Plungė folds only. On Salantai 17 villages
  and 30 godmothers were withheld that nobody has looked at.
- Godmother and her status (F1 73–80 on the reported folds), fathers with patronymics (1902–07),
  entries assembled from two rows, unmarried mothers (mother and surname in one phrase).
- Dates: a wrong month from a misread name ("Іюмя" is given as June, "Мная" as May) is not caught
  here; that is `check_months.py`'s job.

## Appendix: full leave-one-book-out tables (generated by `evaluate.py lobo`)

In the "by span source" rows the rules' 100 and 0 are true by definition (a "both" or "rules" span
is the rules' own; a "names" or "conflict" span is one the rules did not give); only the taggers'
columns carry information there.

### Held out: 1827/1/18 (1849-54), 1501 entries


Gold = silver (all spans). F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char |
|---|---:|---|---|
| BAPT_DATE | 1101 | 100 / 100 | 97 / 100 |
| PRIEST | 1373 | 93 / 93 | 61 / 66 |
| CHILD | 1389 | 79 / 86 | 82 / 89 |
| ESTATE | 1145 | 100 / 100 | 99 / 100 |
| TOWNSHIP | 2 | 100 / 100 | 0 / 0 |
| FATHER | 1312 | 89 / 90 | 93 / 95 |
| MOTHER | 1351 | 89 / 90 | 93 / 95 |
| MAIDEN | 1350 | 68 / 69 | 91 / 92 |
| SURNAME | 1230 | 85 / 85 | 85 / 86 |
| BIRTH_DATE | 861 | 100 / 100 | 85 / 91 |
| VILLAGE | 1320 | 61 / 64 | 69 / 73 |
| GODFATHER | 1443 | 53 / 55 | 82 / 85 |
| GODMOTHER | 1174 | 65 / 66 | 52 / 56 |
| GM_STATUS | 573 | 100 / 100 | 80 / 85 |
| **name fields, micro F1 ±2** | | 77.7 (P 82, R 74) | 82.3 (P 83, R 82; seeds 82.1, 82.4) |

Gold = agents' names spans only. F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char |
|---|---:|---|---|
| PRIEST | 291 | 66 / 68 | 59 / 63 |
| CHILD | 863 | 62 / 77 | 88 / 91 |
| TOWNSHIP | 0 | 0 / 0 | 0 / 0 |
| FATHER | 1087 | 86 / 87 | 92 / 94 |
| MOTHER | 969 | 84 / 86 | 90 / 94 |
| MAIDEN | 1282 | 66 / 67 | 92 / 93 |
| SURNAME | 615 | 68 / 69 | 92 / 93 |
| VILLAGE | 1150 | 55 / 58 | 75 / 79 |
| GODFATHER | 1249 | 45 / 47 | 87 / 90 |
| GODMOTHER | 787 | 44 / 46 | 49 / 53 |
| **name fields, micro F1 ±2** | | 67.0 (P 73, R 62) | 85.9 (P 86, R 86; seeds 84.9, 86.8) |

Name fields by where the silver span came from, and by entry tier: micro F1 within 2 characters (gold spans).

| subset | rules | char |
|---|---|---|
| span source: both (5132) | 100.0 | 95.4 |
| span source: names (1287) | 0.0 | 72.7 |
| span source: conflict (1874) | 0.0 | 68.9 |
| span source: rules (3507) | 100.0 | 74.0 |
| span source: rules+part (144) | 100.0 | 75.0 |
| entry tier A (868) | 98.2 | 91.4 |
| entry tier B (11076) | 76.0 | 81.6 |

Independent checks: agreeing with the side column / spans produced / entries with a side-column value.

| check | rules | char | silver label | agents' span |
|---|---|---|---|---|
| family surname = margin surname | 276 / 1001 / 1265 (22%) | 411 / 1216 / 1265 (32%) [seeds 410, 412] | 369 / 1048 / 1265 (29%) | 296 / 480 / 1265 (23%) |
| baptism day = side column | 983 / 1075 / 1440 (68%) | 1015 / 1438 / 1440 (70%) [seeds 1017, 1013] | 976 / 1064 / 1440 (68%) | 0 / 0 / 1440 (0%) |
| birth day = side column | 777 / 836 / 1440 (54%) | 912 / 1418 / 1440 (63%) [seeds 911, 912] | 777 / 835 / 1440 (54%) | 0 / 0 / 1440 (0%) |

### Held out: 1827/1/22 (1867-74), 2062 entries


Gold = silver (all spans). F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char | xlmr | rubert | char names-only | char no-aug |
|---|---:|---|---|---|---|---|---|
| BAPT_DATE | 1638 | 100 / 100 | 99 / 100 | 96 / 100 | 94 / 100 | 97 / 100 | 100 / 100 |
| PRIEST | 2012 | 85 / 86 | 81 / 84 | 80 / 84 | 81 / 83 | 80 / 81 | 81 / 84 |
| CHILD | 2021 | 86 / 90 | 88 / 93 | 87 / 93 | 87 / 93 | 88 / 93 | 88 / 93 |
| ESTATE | 1567 | 100 / 100 | 99 / 99 | 99 / 99 | 99 / 99 | 99 / 99 | 100 / 100 |
| TOWNSHIP | 1 | 100 / 100 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| FATHER | 1873 | 87 / 89 | 90 / 93 | 91 / 94 | 90 / 93 | 90 / 94 | 89 / 92 |
| MOTHER | 1909 | 88 / 90 | 91 / 94 | 90 / 94 | 91 / 94 | 91 / 94 | 90 / 94 |
| MAIDEN | 1928 | 76 / 78 | 94 / 96 | 94 / 96 | 94 / 95 | 94 / 95 | 93 / 95 |
| SURNAME | 1853 | 87 / 87 | 89 / 90 | 90 / 91 | 89 / 90 | 88 / 89 | 88 / 90 |
| BIRTH_DATE | 1360 | 100 / 100 | 89 / 92 | 91 / 94 | 91 / 96 | 88 / 91 | 91 / 92 |
| VILLAGE | 1746 | 54 / 64 | 84 / 88 | 84 / 88 | 85 / 88 | 84 / 88 | 83 / 87 |
| GODFATHER | 2024 | 78 / 80 | 92 / 95 | 93 / 96 | 93 / 95 | 93 / 95 | 92 / 94 |
| GODMOTHER | 1879 | 76 / 80 | 79 / 84 | 81 / 86 | 81 / 86 | 79 / 84 | 76 / 81 |
| GM_STATUS | 1230 | 100 / 100 | 97 / 98 | 97 / 98 | 98 / 98 | 97 / 98 | 97 / 98 |
| **name fields, micro F1 ±2** | | 83.0 (P 88, R 78) | 90.8 (P 91, R 91; seeds 90.7, 90.8) | 91.2 (P 91, R 91; seeds 91.1, 91.3) | 91.0 (P 91, R 91) | 90.4 (P 91, R 90) | 90.2 (P 90, R 90) |

Gold = agents' names spans only. F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char | xlmr | rubert | char names-only | char no-aug |
|---|---:|---|---|---|---|---|---|
| PRIEST | 769 | 61 / 64 | 65 / 68 | 65 / 68 | 66 / 68 | 70 / 72 | 63 / 66 |
| CHILD | 1201 | 75 / 83 | 90 / 94 | 90 / 94 | 89 / 94 | 90 / 94 | 90 / 94 |
| TOWNSHIP | 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| FATHER | 1593 | 85 / 87 | 89 / 92 | 90 / 94 | 90 / 93 | 90 / 93 | 89 / 92 |
| MOTHER | 1340 | 81 / 85 | 88 / 93 | 89 / 93 | 90 / 93 | 89 / 93 | 88 / 93 |
| MAIDEN | 1819 | 75 / 76 | 95 / 97 | 95 / 97 | 95 / 96 | 95 / 96 | 94 / 96 |
| SURNAME | 1163 | 79 / 79 | 94 / 95 | 95 / 96 | 93 / 95 | 95 / 96 | 91 / 94 |
| VILLAGE | 1636 | 50 / 62 | 86 / 89 | 85 / 89 | 86 / 89 | 86 / 89 | 85 / 88 |
| GODFATHER | 1806 | 74 / 77 | 93 / 96 | 95 / 97 | 94 / 96 | 94 / 96 | 93 / 95 |
| GODMOTHER | 1212 | 60 / 67 | 71 / 80 | 73 / 81 | 74 / 82 | 72 / 80 | 69 / 77 |
| **name fields, micro F1 ±2** | | 76.1 (P 83, R 70) | 90.8 (P 91, R 91; seeds 90.7, 90.9) | 91.4 (P 91, R 91; seeds 91.2, 91.5) | 91.1 (P 91, R 91) | 91.3 (P 91, R 91) | 89.9 (P 90, R 90) |

Name fields by where the silver span came from, and by entry tier: micro F1 within 2 characters (gold spans).

| subset | rules | char | xlmr | rubert | char names-only | char no-aug |
|---|---|---|---|---|---|---|
| span source: both (8810) | 100.0 | 98.9 | 99.3 | 99.1 | 99.0 | 98.5 |
| span source: names (1946) | 0.0 | 83.1 | 84.4 | 84.2 | 83.2 | 82.1 |
| span source: conflict (1783) | 0.0 | 58.8 | 59.7 | 58.8 | 62.1 | 56.0 |
| span source: rules (4359) | 100.0 | 90.3 | 90.3 | 90.2 | 87.5 | 90.4 |
| span source: rules+part (348) | 100.0 | 96.2 | 95.9 | 95.8 | 95.8 | 96.4 |
| entry tier A (3258) | 98.4 | 98.4 | 98.6 | 98.5 | 98.1 | 98.1 |
| entry tier B (13988) | 79.3 | 89.0 | 89.5 | 89.2 | 88.6 | 88.3 |

Independent checks: agreeing with the side column / spans produced / entries with a side-column value.

| check | rules | char | xlmr | rubert | char names-only | char no-aug | silver label | agents' span |
|---|---|---|---|---|---|---|---|---|
| family surname = margin surname | 865 / 1640 / 1954 (44%) | 1118 / 1864 / 1954 (57%) [seeds 1115, 1122] | 1132 / 1870 / 1954 (58%) [seeds 1120, 1145] | 1107 / 1869 / 1954 (57%) | 1139 / 1854 / 1954 (58%) | 1100 / 1868 / 1954 (56%) | 1077 / 1759 / 1954 (55%) | 902 / 1092 / 1954 (46%) |
| baptism day = side column | 1481 / 1630 / 2049 (72%) | 1538 / 2049 / 2049 (75%) [seeds 1537, 1539] | 1537 / 2049 / 2049 (75%) [seeds 1537, 1537] | 1536 / 2049 / 2049 (75%) | 1539 / 2049 / 2049 (75%) | 1542 / 2049 / 2049 (75%) | 1481 / 1630 / 2049 (72%) | 0 / 0 / 2049 (0%) |
| birth day = side column | 1285 / 1350 / 2043 (63%) | 1504 / 2034 / 2043 (74%) [seeds 1499, 1508] | 1518 / 2035 / 2043 (74%) [seeds 1520, 1516] | 1521 / 2034 / 2043 (74%) | 1500 / 2037 / 2043 (73%) | 1500 / 2035 / 2043 (73%) | 1281 / 1346 / 2043 (63%) | 0 / 0 / 2043 (0%) |

### Held out: 1886-1890 (1886-90), 1701 entries


Gold = silver (all spans). F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char |
|---|---:|---|---|
| BAPT_DATE | 1431 | 100 / 100 | 99 / 100 |
| PRIEST | 1671 | 94 / 95 | 81 / 85 |
| CHILD | 1674 | 90 / 94 | 95 / 97 |
| ESTATE | 1326 | 100 / 100 | 100 / 100 |
| TOWNSHIP | 1405 | 92 / 93 | 91 / 95 |
| FATHER | 1446 | 82 / 83 | 91 / 95 |
| MOTHER | 1533 | 77 / 79 | 88 / 94 |
| MAIDEN | 1582 | 61 / 61 | 95 / 96 |
| SURNAME | 1311 | 82 / 83 | 85 / 87 |
| BIRTH_DATE | 1312 | 100 / 100 | 85 / 88 |
| VILLAGE | 1486 | 76 / 80 | 93 / 95 |
| GODFATHER | 1662 | 80 / 84 | 89 / 93 |
| GODMOTHER | 1564 | 79 / 81 | 85 / 88 |
| GM_STATUS | 1014 | 100 / 100 | 94 / 96 |
| **name fields, micro F1 ±2** | | 83.8 (P 90, R 78) | 92.5 (P 93, R 92; seeds 92.5, 92.5) |

Gold = agents' names spans only. F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char |
|---|---:|---|---|
| PRIEST | 425 | 76 / 79 | 77 / 79 |
| CHILD | 1311 | 87 / 92 | 95 / 97 |
| TOWNSHIP | 411 | 72 / 75 | 84 / 88 |
| FATHER | 1221 | 78 / 80 | 89 / 94 |
| MOTHER | 1262 | 71 / 74 | 87 / 93 |
| MAIDEN | 1561 | 60 / 60 | 96 / 97 |
| SURNAME | 684 | 63 / 65 | 94 / 96 |
| VILLAGE | 1404 | 74 / 79 | 94 / 96 |
| GODFATHER | 1508 | 76 / 82 | 90 / 94 |
| GODMOTHER | 1203 | 71 / 75 | 83 / 88 |
| **name fields, micro F1 ±2** | | 76.7 (P 86, R 69) | 93.6 (P 94, R 93; seeds 93.6, 93.5) |

Name fields by where the silver span came from, and by entry tier: micro F1 within 2 characters (gold spans).

| subset | rules | char |
|---|---|---|
| span source: both (7615) | 100.0 | 99.0 |
| span source: names (2123) | 0.0 | 86.4 |
| span source: conflict (1252) | 0.0 | 72.6 |
| span source: rules (4099) | 100.0 | 89.7 |
| span source: rules+part (245) | 100.0 | 91.6 |
| entry tier A (3577) | 99.0 | 97.7 |
| entry tier B (11757) | 78.7 | 90.9 |

Independent checks: agreeing with the side column / spans produced / entries with a side-column value.

| check | rules | char | silver label | agents' span |
|---|---|---|---|---|
| family surname = margin surname | 459 / 1046 / 1574 (29%) | 798 / 1497 / 1574 (51%) [seeds 795, 801] | 629 / 1199 / 1574 (40%) | 415 / 578 / 1574 (26%) |
| baptism day = side column | 1084 / 1241 / 1483 (73%) | 1109 / 1483 / 1483 (75%) [seeds 1109, 1109] | 1083 / 1240 / 1483 (73%) | 0 / 0 / 1483 (0%) |
| birth day = side column | 1020 / 1221 / 1576 (65%) | 1117 / 1575 / 1576 (71%) [seeds 1119, 1115] | 1019 / 1215 / 1576 (65%) | 0 / 0 / 1576 (0%) |

### Held out: 1827/1/24 (1896-1902), 2582 entries


Gold = silver (all spans). F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char | xlmr | rubert | char names-only | char no-aug |
|---|---:|---|---|---|---|---|---|
| BAPT_DATE | 2061 | 100 / 100 | 98 / 100 | 98 / 100 | 97 / 100 | 97 / 100 | 99 / 100 |
| PRIEST | 2505 | 88 / 88 | 81 / 84 | 82 / 84 | 80 / 85 | 80 / 82 | 82 / 84 |
| CHILD | 2472 | 82 / 84 | 91 / 93 | 91 / 93 | 90 / 93 | 91 / 93 | 91 / 93 |
| ESTATE | 1991 | 100 / 100 | 99 / 100 | 99 / 100 | 99 / 100 | 99 / 99 | 100 / 100 |
| TOWNSHIP | 2245 | 95 / 95 | 91 / 95 | 91 / 94 | 89 / 94 | 87 / 92 | 92 / 96 |
| FATHER | 2180 | 81 / 82 | 94 / 97 | 95 / 98 | 95 / 98 | 93 / 97 | 94 / 97 |
| MOTHER | 2204 | 76 / 77 | 87 / 91 | 87 / 91 | 87 / 91 | 88 / 91 | 87 / 90 |
| MAIDEN | 2332 | 50 / 51 | 94 / 95 | 94 / 95 | 95 / 95 | 94 / 95 | 94 / 95 |
| SURNAME | 1852 | 75 / 76 | 89 / 91 | 89 / 91 | 89 / 91 | 90 / 91 | 89 / 91 |
| BIRTH_DATE | 1546 | 100 / 100 | 72 / 75 | 78 / 79 | 80 / 81 | 63 / 67 | 71 / 74 |
| VILLAGE | 2005 | 42 / 48 | 89 / 91 | 91 / 93 | 91 / 92 | 89 / 90 | 89 / 92 |
| GODFATHER | 2475 | 84 / 87 | 92 / 95 | 93 / 95 | 93 / 95 | 93 / 95 | 92 / 95 |
| GODMOTHER | 2310 | 78 / 79 | 76 / 77 | 78 / 79 | 77 / 79 | 75 / 78 | 71 / 72 |
| GM_STATUS | 1332 | 100 / 100 | 95 / 96 | 96 / 96 | 95 / 96 | 95 / 96 | 96 / 97 |
| **name fields, micro F1 ±2** | | 78.0 (P 87, R 71) | 90.8 (P 91, R 91; seeds 90.9, 90.7) | 91.2 (P 91, R 91; seeds 91.1, 91.4) | 91.1 (P 91, R 91) | 90.3 (P 90, R 90) | 90.4 (P 90, R 90) |

Gold = agents' names spans only. F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char | xlmr | rubert | char names-only | char no-aug |
|---|---:|---|---|---|---|---|---|
| PRIEST | 994 | 69 / 70 | 78 / 79 | 78 / 79 | 76 / 76 | 87 / 88 | 75 / 76 |
| CHILD | 1731 | 74 / 77 | 95 / 97 | 95 / 97 | 94 / 97 | 96 / 98 | 95 / 97 |
| TOWNSHIP | 447 | 72 / 76 | 80 / 84 | 80 / 84 | 81 / 84 | 83 / 87 | 79 / 83 |
| FATHER | 1756 | 75 / 77 | 93 / 97 | 94 / 97 | 94 / 97 | 92 / 96 | 93 / 96 |
| MOTHER | 1630 | 65 / 67 | 87 / 92 | 88 / 92 | 88 / 92 | 89 / 92 | 88 / 92 |
| MAIDEN | 2232 | 47 / 48 | 95 / 96 | 96 / 96 | 96 / 96 | 95 / 96 | 95 / 96 |
| SURNAME | 1209 | 57 / 59 | 93 / 95 | 93 / 94 | 92 / 93 | 96 / 97 | 91 / 93 |
| VILLAGE | 1901 | 38 / 45 | 91 / 93 | 94 / 95 | 93 / 94 | 92 / 93 | 91 / 93 |
| GODFATHER | 2080 | 79 / 84 | 93 / 95 | 93 / 96 | 93 / 96 | 93 / 96 | 92 / 95 |
| GODMOTHER | 1475 | 64 / 66 | 70 / 73 | 73 / 75 | 72 / 74 | 72 / 75 | 66 / 68 |
| **name fields, micro F1 ±2** | | 66.4 (P 78, R 58) | 91.5 (P 92, R 91; seeds 91.5, 91.5) | 92.0 (P 92, R 92; seeds 92.0, 92.0) | 91.7 (P 92, R 92) | 92.7 (P 93, R 93) | 90.7 (P 91, R 91) |

Name fields by where the silver span came from, and by entry tier: micro F1 within 2 characters (gold spans).

| subset | rules | char | xlmr | rubert | char names-only | char no-aug |
|---|---|---|---|---|---|---|
| span source: both (8906) | 100.0 | 99.0 | 99.2 | 99.1 | 99.1 | 98.6 |
| span source: names (4089) | 0.0 | 88.7 | 90.0 | 89.7 | 89.4 | 88.0 |
| span source: conflict (2460) | 0.0 | 69.1 | 69.3 | 68.3 | 75.0 | 66.9 |
| span source: rules (6581) | 100.0 | 88.6 | 89.1 | 89.3 | 84.4 | 89.2 |
| span source: rules+part (544) | 100.0 | 94.9 | 95.2 | 94.7 | 93.6 | 94.1 |
| entry tier A (2105) | 96.9 | 97.3 | 97.6 | 97.7 | 96.3 | 96.9 |
| entry tier B (20475) | 76.0 | 90.1 | 90.6 | 90.4 | 89.7 | 89.7 |

Independent checks: agreeing with the side column / spans produced / entries with a side-column value.

| check | rules | char | xlmr | rubert | char names-only | char no-aug | silver label | agents' span |
|---|---|---|---|---|---|---|---|---|
| family surname = margin surname | 544 / 958 / 1894 (29%) | 1128 / 1836 / 1894 (60%) [seeds 1134, 1121] | 1130 / 1823 / 1894 (60%) [seeds 1123, 1136] | 1114 / 1837 / 1894 (59%) | 1176 / 1843 / 1894 (62%) | 1105 / 1816 / 1894 (58%) | 816 / 1259 / 1894 (43%) | 550 / 669 / 1894 (29%) |
| baptism day = side column | 1860 / 1949 / 2422 (77%) | 1918 / 2420 / 2422 (79%) [seeds 1918, 1919] | 1918 / 2420 / 2422 (79%) [seeds 1918, 1917] | 1918 / 2419 / 2422 (79%) | 1917 / 2420 / 2422 (79%) | 1921 / 2420 / 2422 (79%) | 1858 / 1947 / 2422 (77%) | 0 / 0 / 2422 (0%) |
| birth day = side column | 1469 / 1723 / 2479 (59%) | 1715 / 2458 / 2479 (69%) [seeds 1722, 1708] | 1742 / 2459 / 2479 (70%) [seeds 1745, 1739] | 1741 / 2456 / 2479 (70%) | 1719 / 2459 / 2479 (69%) | 1688 / 2451 / 2479 (68%) | 1271 / 1492 / 2479 (51%) | 0 / 0 / 2479 (0%) |

### Held out: 1827/1/25 (1902-07), 2059 entries


Gold = silver (all spans). F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char |
|---|---:|---|---|
| BAPT_DATE | 1747 | 100 / 100 | 99 / 100 |
| PRIEST | 1880 | 88 / 88 | 85 / 86 |
| CHILD | 1953 | 85 / 89 | 89 / 94 |
| ESTATE | 1510 | 100 / 100 | 100 / 100 |
| TOWNSHIP | 1654 | 96 / 96 | 95 / 96 |
| FATHER | 1748 | 63 / 65 | 74 / 78 |
| MOTHER | 1764 | 75 / 76 | 87 / 90 |
| MAIDEN | 1825 | 51 / 51 | 90 / 92 |
| SURNAME | 1524 | 75 / 76 | 84 / 86 |
| BIRTH_DATE | 1201 | 100 / 100 | 75 / 77 |
| VILLAGE | 1512 | 57 / 64 | 91 / 92 |
| GODFATHER | 1968 | 82 / 85 | 91 / 94 |
| GODMOTHER | 1823 | 74 / 75 | 76 / 78 |
| GM_STATUS | 1009 | 100 / 100 | 95 / 96 |
| **name fields, micro F1 ±2** | | 77.5 (P 85, R 71) | 88.6 (P 89, R 88; seeds 88.7, 88.5) |

Gold = agents' names spans only. F1 exact / F1 within 2 characters (mean of the seeds).

| field | gold spans | rules | char |
|---|---:|---|---|
| PRIEST | 736 | 67 / 69 | 72 / 74 |
| CHILD | 1457 | 80 / 85 | 90 / 95 |
| TOWNSHIP | 327 | 78 / 79 | 83 / 86 |
| FATHER | 1538 | 57 / 59 | 71 / 76 |
| MOTHER | 1387 | 67 / 67 | 87 / 91 |
| MAIDEN | 1715 | 47 / 48 | 92 / 94 |
| SURNAME | 987 | 59 / 60 | 88 / 90 |
| VILLAGE | 1389 | 52 / 60 | 92 / 94 |
| GODFATHER | 1720 | 78 / 83 | 91 / 95 |
| GODMOTHER | 1235 | 60 / 62 | 71 / 75 |
| **name fields, micro F1 ±2** | | 67.0 (P 77, R 59) | 88.0 (P 88, R 88; seeds 88.2, 87.7) |

Name fields by where the silver span came from, and by entry tier: micro F1 within 2 characters (gold spans).

| subset | rules | char |
|---|---|---|
| span source: both (7396) | 100.0 | 98.5 |
| span source: names (2926) | 0.0 | 84.4 |
| span source: conflict (2169) | 0.0 | 56.9 |
| span source: rules (4868) | 100.0 | 90.2 |
| span source: rules+part (292) | 100.0 | 92.1 |
| entry tier A (1596) | 97.3 | 96.9 |
| entry tier B (16055) | 75.4 | 87.8 |

Independent checks: agreeing with the side column / spans produced / entries with a side-column value.

| check | rules | char | silver label | agents' span |
|---|---|---|---|---|
| family surname = margin surname | 488 / 1043 / 1726 (28%) | 850 / 1602 / 1726 (49%) [seeds 849, 851] | 727 / 1257 / 1726 (42%) | 612 / 755 / 1726 (35%) |
| baptism day = side column | 1597 / 1690 / 1965 (81%) | 1626 / 1945 / 1965 (83%) [seeds 1626, 1627] | 1588 / 1680 / 1965 (81%) | 0 / 0 / 1965 (0%) |
| birth day = side column | 1131 / 1279 / 1946 (58%) | 1340 / 1848 / 1946 (69%) [seeds 1338, 1342] | 1012 / 1148 / 1946 (52%) | 0 / 0 / 1946 (0%) |

### Examples (char tagger seed 1 against the rules; gold = agents' spans)

- **tagger right, rules not** (1827/1/18 0074_L3, GODFATHER): «…Воспріемникам  ли Крестьянѣ: Клеменъ Пиннусъ съ Анною Іцефа Да нелки супругою.  -…» agents: «Клеменъ Пиннусъ»; rules: «—»; tagger: «Клеменъ Пиннусъ»
- **tagger right, rules not** (1827/1/18 0061_R1, VILLAGE): «… 1850 -года Ноября Годня вечеромъ въ Деревни Мажявахъ Кулевскаго прихада. -…» agents: «Мажявахъ»; rules: «ЮденКумеыскаг»; tagger: «Мажявахъ»
- **tagger right, rules not** (1827/1/18 0122_L2, VILLAGE): «…ившаякся 1852 года. Ігома 24. дня. въ нерени Пруселяхъ таго приаода…» agents: «Пруселяхъ»; rules: «Пруселяхъ таго приаода»; tagger: «Пруселяхъ»
- **tagger right, rules not** (1827/1/18 0040_L5, CHILD): «… тіемъ Марневичемъ окріещена 2ѣ влща аменами Домицела Маріянна со восми обрядами тамнства -…» agents: «Домицела Маріянна»; rules: «—»; tagger: «Домицела Маріянна»
- **tagger right, rules not** (1827/1/18 0190_R3, MAIDEN): «…Крестіямъ Бендикта и Анпы уронденаСтаневны Ша кевъ законныъ Супруговъ Сынъ родившійся 1…» agents: «Станевны»; rules: «—»; tagger: «Станевны»
- **rules right, tagger not** (1827/1/18 0113_L1, CHILD): «…одовихомъ Матнылдамъ окрещенъ младенецъ именам оминикъ и Викторъ со всѣми обряда ми таинства…» agents: «м оминикъ и Викторъ»; rules: «оминикъ и Викторъ»; tagger: «иникъ и Викторъ»
- **rules right, tagger not** (1827/1/18 0099_L4, MAIDEN): «…: Стани Во - сла ва и Грасиль бвъ урожденной Стонзакокныхъ супри говъ снъ и Ды. Д радившііся 1…» agents: «Стон»; rules: «Стон»; tagger: «Стонзакокныхъ»
- **rules right, tagger not** (1827/1/18 0132_L1, FATHER): «…„. Кретьянъ вюдвика и Агаты урожр денной Янушевком Ірбоновъ зако…» agents: «вюдвика»; rules: «вюдвика»; tagger: «янъ вюдвика»
- **rules right, tagger not** (1827/1/18 0044_L2, VILLAGE): «…дившійся 1850 года Апреля Семаго дна Деревни Лукняъ ахъ -…» agents: «Лукняъ ахъ»; rules: «Лукняъ ахъ»; tagger: «Лукняъ»
- **rules right, tagger not** (1827/1/18 0022_R2, VILLAGE): «… дня пожтру При ода Плунгянска го въ Деревни Посуняхъ.…» agents: «Посуняхъ»; rules: «Посуняхъ»; tagger: «При ода»
- **tagger right, rules not** (1827/1/22 0113_L1, MAIDEN): «…Крестьянъ Франца и Кляры урожденной Давлевна Ма ценевъ заканныхъ супруговъ сынъ родившійс…» agents: «Давлевна»; rules: «Давлевна Ма»; tagger: «Давлевна»
- **tagger right, rules not** (1827/1/22 0228_L3, GODFATHER): «…Воспріемника ми быи: Крестьомъ Казимержръ Минеико ъ Подвикога Яна Барздцин скаго Супругою.…» agents: «Казимержръ Минеико»; rules: «Крестьомъ Казимержръ Минеико»; tagger: «Казимержръ Минеико»
- **tagger right, rules not** (1827/1/22 0046_L1, VILLAGE): «…ся сего 1869. гада Янворя 5. дня въ деревнаъ Рулайцяхъ сего зирихада. -…» agents: «Рулайцяхъ»; rules: «аъ Рулайцяхъ»; tagger: «Рулайцяхъ»
- **tagger right, rules not** (1827/1/22 0157_L2, GODMOTHER): «…Воспросмниками были Ксіонузъ Бересневияъ съ Розалеюо Ленков скою вдовахо…» agents: «Розалеюо Ленков скою»; rules: «Розалеюо Ленков»; tagger: «Розалеюо Ленков скою в»
- **tagger right, rules not** (1827/1/22 0093_L3, GODFATHER): «…Воспріемниками бысми: Михалъ Баровски съ Аннаго Франца Бумбля супругвю. …» agents: «Михалъ Баровски»; rules: «—»; tagger: «Михалъ Баровски»
- **rules right, tagger not** (1827/1/22 0178_L4, GODMOTHER): «…іемиками быми: Крестьянъ Ізефѣъ Воловскій съ Барбарого Равицедо дтѣдино…» agents: «Барбарого Равицедо»; rules: «Барбарого Равицедо»; tagger: «Барбарого Равицедо дт»
- **rules right, tagger not** (1827/1/22 0172_L1, PRIEST): «… При ходскомъ Костемѣ Мѣѣотымъ Винарыемъ Кс. Пацевичемъ окреще то дитяммснемѣ Ло д вика со всѣми обр…» agents: «Пацевичемъ»; rules: «Пацевичемъ»; tagger: «мъ Кс. Пацевичемъ»
- **rules right, tagger not** (1827/1/22 0185_L5, FATHER): «…Крестьянъ Анто са го Петронелипождетной чеснов ской Поціовъ…» agents: «Анто»; rules: «Анто»; tagger: «Анто са»
- **rules right, tagger not** (1827/1/22 0223_R3, FATHER): «…зестьянъ Игнацен Во и Викторіи уро жденной Стан ковной Юлико …» agents: «Игнацен»; rules: «Игнацен»; tagger: «Игнацен Во»
- **rules right, tagger not** (1827/1/22 0163_L6, PRIEST): «…рикодокомъ Костелѣ Пготнымъ Настоятелемъ Кс. Бересневичемъ крещено дестя Именемъ, Антони со всѣми об…» agents: «Бересневич»; rules: «Бересневиче»; tagger: «Бересневичемъ»
- **tagger right, rules not** (1886-1890 0048_R1, MAIDEN): «…пестьянъ Плунсянской Восл. озефан Анны изъ Даупіовъ Забыті овс за конныхъ супругосъ сытнъ годивш…» agents: «Даупіовъ»; rules: «—»; tagger: «Даупіовъ»
- **tagger right, rules not** (1886-1890 0171_R1, MAIDEN): «…ьянъ Берна товкон волости Госпфа иІозефы изъ Плюм кіовъ Михало вских законныхъ Супруго въ Сынъ родив…» agents: «Плюм кіовъ»; rules: «Плюм кіовъ Михало»; tagger: «Плюм кіовъ»
- **tagger right, rules not** (1886-1890 0024_L5, MAIDEN): «…Крестьянъ Плунгянской Вол Пгнаща и Барбауыеъ Венгаліовъ Мочульскитъ засконныхъ супруговъ сыснъ родив…» agents: «Венгаліовъ»; rules: «—»; tagger: «Венгаліовъ»
- **tagger right, rules not** (1886-1890 0011_R4, MAIDEN): «…естьянъ Лабардзіовскни Во Юзефа и Агнешкиизъ Педговдовъ Труннковъ за конныхъ супруговъ дочь родившая…» agents: «Педговдовъ»; rules: «—»; tagger: «Педговдовъ»
- **tagger right, rules not** (1886-1890 0046_L4, TOWNSHIP): «…Крестьянъ Олыядскни Вом. 6еранца и Анны изъ чалтутовъ Пуника кев…» agents: «Олыядскни»; rules: «—»; tagger: «Олыядскни»
- **rules right, tagger not** (1886-1890 0186_R1, VILLAGE): «…шаяя 1889г года Сктября 28г нсц. въ мберевни мекемисего…» agents: «мекеми»; rules: «мекеми»; tagger: «мекемисего»
- **rules right, tagger not** (1886-1890 0161_R3, GODFATHER): «…Воспріемникаи-ми был Янъ -Линге съ въ Петронелен Яна Римеи ниса супрупо. -…» agents: «Янъ -Линге»; rules: «Янъ -Линге»; tagger: «Янъ -Линге съ»
- **rules right, tagger not** (1886-1890 0201_R4, GODFATHER): «…-Воспріемнико ми были Кеендзъ Янъ Авгулисъ съ Анною Игнитія Чесновскаго супрушгою.…» agents: «Кеендзъ Янъ Авгулисъ»; rules: «Кеендзъ Янъ Авгулисъ»; tagger: «Янъ Авгулисъ»
- **rules right, tagger not** (1886-1890 0125_L2, GODMOTHER): «…Вос пріемниками были Лсонъ стонкемисъ съ Свон Юрія Ронейки Куаругаюа.…» agents: «Свон»; rules: «Свон»; tagger: «Свон Юрія»
- **rules right, tagger not** (1886-1890 0040_R5, FATHER): «…Крестьянъ Плунгянсъой Вол. нетрга и Агнетки изъ здраміовъ Пакало ниикіовъ зако…» agents: «нетрга»; rules: «нетрга»; tagger: «Вол. нетрга»
- **tagger right, rules not** (1827/1/24 0030_R3, MAIDEN): «…нъ Титемммскон волости Антона и Ма данены щъ Варнемисовъ Шоиковскихъ дак. суп. сыъ родившійся 16 Nояб…» agents: «Варнемисовъ»; rules: «—»; tagger: «Варнемисовъ»
- **tagger right, rules not** (1827/1/24 0260_L3, GODMOTHER): «…Воспріем нмкамми балли Адомфъстон кусъ съ Юмяною Мѣми ковскою дѣви цеюо. -…» agents: «Юмяною Мѣми ковскою»; rules: «—»; tagger: «Юмяною Мѣми ковскою»
- **tagger right, rules not** (1827/1/24 0018_R2, MAIDEN): «…рнатовской Р волости Іосифа и Петъ ронето иъ Нарвайми совъ Видеикисовъ зак. суп. сынъ родившійся ѣ 13 І…» agents: «Нарвайми совъ»; rules: «ронето иъ Нарвайми совъ»; tagger: «Нарвайми совъ»
- **tagger right, rules not** (1827/1/24 0119_L1, FATHER): «…Срестъянъ Плунгянскойволости Ишнатіяи Маріянныизъ Мицкусовъ Будры касовъ законных…» agents: «Ишнатія»; rules: «—»; tagger: «Ишнатія»
- **tagger right, rules not** (1827/1/24 0028_R2, VILLAGE): «…ь родившаяся ъ 20 Октября 1896 года .въ дер. Варкаляхъ -дъѣмняго прнхода…» agents: «Варкаляхъ»; rules: «аркаляхъ -дъѣмняго прнхода»; tagger: «Варкаляхъ»
- **rules right, tagger not** (1827/1/24 0242_R1, GODMOTHER): «…Воспріемииками -быми Кипріянъ Жилевичъ съ Маль винсг Дуновского дѣпую.…» agents: «Маль винсг»; rules: «Маль винсг»; tagger: «Маль винсг Дуновского»
- **rules right, tagger not** (1827/1/24 0229_R5, GODMOTHER): «…Воспріемниками были Игнатій По -цосъ съ Варварого Ваврусо вемио доыюю.…» agents: «Варварого Ваврусо»; rules: «Варварого Ваврусо»; tagger: «Варварого Ваврусо вемио»
- **rules right, tagger not** (1827/1/24 0225_L4, GODMOTHER): «…емниками были Ксендзъ ВиКентій Ярунагзисъ съ Зузанного Викентія Петровсвоео суетгою…» agents: «Зузанного»; rules: «Зузанного»; tagger: «Зузанного Ви»
- **rules right, tagger not** (1827/1/24 0294_L5, GODMOTHER): «…мииками быми Ксещдцъ Вик мтій Ярусгаитисъ съ Софіего Кимонтъ гдоыик.…» agents: «Софіего Кимонтъ»; rules: «Софіего Кимонтъ»; tagger: «Софіего Кимонтъ гдоыик»
- **rules right, tagger not** (1827/1/24 0196_R2, GODMOTHER): «…Востріемнтками быми Казимтъ Жебровскій съ Лгодвиког Станнскава Виткевило дгогюю.…» agents: «Лгодвиког»; rules: «Лгодвиког»; tagger: «ва Виткевило»
- **tagger right, rules not** (1827/1/25 0032_R2, SURNAME): «…сковол. Авастика и Петронинели иъ Пителисовъ Питемисо въ зак: супрсынъ родившійся сего 1903 года Янва…» agents: «Питемисо въ»; rules: «—»; tagger: «Питемисо въ»
- **tagger right, rules not** (1827/1/25 0105_R3, SURNAME): «…сти Феликса и Атья стасій урожд. Каубри совъ Бразлавскихъ оь родившаяся 6 Апрѣ ля 1904 года въ М. Плун…» agents: «Бразлавскихъ»; rules: «—»; tagger: «Бразлавскихъ»
- **tagger right, rules not** (1827/1/25 0250_L6, SURNAME): «…н тина Францева и Адеми урожденнай Мицкевичъ Мышков скихъ законныхъ су пруговъ сынъ римѣвшій) родившій…» agents: «Мышков скихъ»; rules: «скихъ»; tagger: «Мышков скихъ»
- **tagger right, rules not** (1827/1/25 0243_R4, MAIDEN): «…сти Алексондра Петроваи Маріяны уронеденниый Кнакилто Аблныксовъ гоконнь ся 3 Октабря 1906 года въ…» agents: «Кнакилто»; rules: «—»; tagger: «Кнакилто»
- **tagger right, rules not** (1827/1/25 0226_R1, GODMOTHER): «…мниками бым Аюдвинъ скій съ Марія Чсновскаю м…» agents: «Марія Чсновскаю»; rules: «—»; tagger: «Марія Чсновскаю»
- **rules right, tagger not** (1827/1/25 0085_R3, GODMOTHER): «…Воспріемниками быми Антоній При голевнійсъ Аврелію Брнинсо свпвию Воспніестики…» agents: «Аврелію Брнинсо»; rules: «Аврелію Брнинсо»; tagger: «Аврелію Брнинсо свпвию Воспніестики»
- **rules right, tagger not** (1827/1/25 0128_L4, GODMOTHER): «…Воспріемниками были Доминикъ Юркайтисъ с Домицелего Антона деию…» agents: «Домицелего»; rules: «Домицелего»; tagger: «Домицелего Антона»
- **rules right, tagger not** (1827/1/25 0072_R3, GODMOTHER): «…Воспріемниками были Игнатіе Мамонасъ съ Домитии -лог Фраи -циска Корвила супругою…» agents: «Домитии»; rules: «Домитии»; tagger: «Домитии -лог»
- **rules right, tagger not** (1827/1/25 0210_L4, CHILD): «…скомъ Костелѣ Ксендзомъ Баландисомъ окренемъ ниславъ совсѣми обрядами Таинства. …» agents: «ниславъ»; rules: «ниславъ»; tagger: «лавъ»
- **rules right, tagger not** (1827/1/25 0267_L5, PRIEST): «…гянскомъ Р.=К. прнаодскомъ Костемъ Ксендзомъ Лаунша сомъ окрещенъ младе нецѣ именемъ Юліясо всѣмиобря…» agents: «Лаунша сомъ»; rules: «Лаунша сомъ»; tagger: «—»
