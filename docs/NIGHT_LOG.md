# Night log, 2026-11-11

Autonomous run requested by Anna ("work through the night ... as much transcription,
translation, model training ... as you can"). Entries are appended as work completes.

## Start state
- Book 1827/1/23 (1886–1890), 202 scans downloaded. 1888: 434 entries; other years: 1,247
  entries (1886: 362, 1887: 398, 1889: 386, 1890: 101).
- Model v2 (validation CER 8.0%; 1886–87 hand 15.3%). Labels: 634 train / 147 val / 123 test.
- Review site http://100.107.252.39:8741/ (EN/LT interface; 1888 only so far).

## Progress
- Reading round 2 (33 agents, ~3.0M tokens): 24 more 1886–87 entries + 9 from 1889–90.
  +402 checked lines (205 blind-agreed). Labels now 914 train / 189 val / 203 test.
- Side columns: printed headers transcribed and translated (EN/LT). All 1,681 entries' side
  columns (margin surname, No., sex, birth/baptism day, later notes) cropped to 421 sheets
  (`pipeline/side_strips.py`); reading workflow running (36 Sonnet agents).
- Book 1827/1/24: 298 scans downloaded to data/plunge-1827-1-24/pages; layout running.
- Model v3 training (same recipe as v2, larger dataset).
- Mistakes caught: launched the side-column workflow once with placeholder args (failed
  instantly, 0 agents, 0 tokens). Merge rule ignored 99 blind agreements in round 1 of the
  1886–87 hand; fixed and re-merged from backup.
- Side columns read for all 1,681 entries (36 Sonnet agents, ~2.5M tokens) ->
  processed/side_columns.json. Check: for 1888 the read entry number equals the hand-checked
  sequence number for 427/434 entries. Numbers show 1886 ran to No. 375, 1888 to 434.
- Found via entry numbers: 1889 entries 1–14 (scans 144–145) and one 1887 entry (scan 92)
  were in neither queue; added (12 layout rows, hand-checked years). Year inference now splits
  the book at entry-number resets: 1886: 368 rows, 1887: 396, 1889: 376, 1890: 92.
- Book 1827/1/24: layout found tables on 565/596 page sides; 2,587 rows, 67,984 lines;
  refinement running. 31 non-table sides (covers/inserts) listed.
- Model v3 (914 train lines): validation CER 7.2% (v2 9.0%); 1886–87/1889–90 group 8.7%
  (v2 13.6%). Drafting is now sharded (`pipeline/draft_shards.sh`, 6 GPU processes): ~44k lines
  in ~4 min. (A 10-shard attempt ran out of GPU memory; nothing was merged from it.)
- Book 1 redrafted with v3 and reassembled: 1886: 370, 1887: 397 (matches its last No. 397),
  1888: 434, 1889: 401, 1890: 99 entries = 1,701. Formula words read exactly, v1 -> v3:
  1886 19% -> 50%, 1887 56% -> 65%, 1888 62% -> 64%, 1889 60% -> 62%, 1890 53% -> 58%.
- Review site now shows all five years (1,701 entries) with side columns and the printed
  column headings (RU/EN/LT).
- Translation pass EN+LT launched: 43 Sonnet chunks of 40 entries + Opus review of Lithuanian.
- Book 1827/1/24 is **1896–1902** (not 1891–95; those are presumably in file 25). Drafted with
  v3 (67,984 lines). Years by a monotone page fit (isolated misreadings like "1877" for "1897"
  can't flip a page): 1896: 300, 1897: 394, 1898: 478, 1899: 402, 1900: 410, 1901: 428,
  1902: 237 entries = 2,649 (after splitting merged rows).
- Book 24 uses a later form/formula ("мѣстнымъ Викарнымъ Кс.", "окрещено дитя именемъ",
  dates in digits) and new hands: v3 drafts are weaker there. Margins carry **later Lithuanian
  annotations of the baptised person's marriage** (e.g. "Apolinaras Stoža priėmė Plungės bažn.
  rugp. 11 d. 1925 m. moterystės sakramentą, vesdamas Valeriją Brazdeikytę").
- Side columns for book 24 use a form-agnostic strip (both rotations + upright); reading
  workflow running (56 Sonnet agents). Reading round for book 24 hands running (30 entries,
  ~27 agents) -> v4. Dataset export now combines all books' labels (ids namespaced per book).
- Git: local repo initialised (not pushed); .gitignore keeps images out (~174 MB of text data).
  Licence plan: CC BY-NC 4.0 for derived data and model (scans are NOC-NC, LVIA fond 1827).
- Book 1 translated EN+LT: 1,701/1,701 entries (43 Sonnet chunks + Opus review, ~2.2M tokens)
  -> processed/translations/translations_v3_book1.json (with the source text each was made from).
  The Opus review (docs/LT_REVIEW_2026-11-11.json) found systematic Lithuanian problems, mostly
  from my glossary's parent template (father's surname after "gim."), Russian case endings left on
  surnames, husbands' surnames in the wrong case, inconsistent clergy names. Glossary revised;
  Lithuanian-only re-translation of book 1 running (43 agents). English unaffected.
- Book 24 side columns: 2,650 read (56 agents, ~5M tokens). **864 later Lithuanian marriage
  annotations** (1919–1930s) in the margins, transcribed and translated. Entry numbers used to
  fix year boundaries and fold 113 half-entries the layout had split: book 24 = 2,536 entries.
  Book 24 starts at 1896 entry No. 86 (Nos. 1–85 are presumably in another book).
- **Mistake, repaired:** merging the book-24 reading round, `merge_double_reading.py` still had
  book 1 hard-coded; because scan numbers overlap across books, it wrote 475 book-24 records onto
  book-1 line ids and demoted 19 genuine book-1 labels to draft. Restored book-1 annotations from
  the pre-round-2 backup and re-applied round 2 (2,870 records, identical to before; verified the
  only differences from the corrupted file were exactly those 19). Script now takes
  SAMOGITIA_BOOK; book-24 readings merged into book 24 (420 checked lines, 256 blind-agreed).
- Combined dataset: 1,199 train / 256 val / 271 test lines (book 1: 1,306; book 24: 420). v4 training.
- Found `site/book/` (a "reading book" builder with textile ribbon images, 202 spread JSONs),
  created 00:52–01:41 by another session/tool, not by this one. Left untouched and excluded from
  git pending Anna's confirmation. It reads the v1 drafts; current outputs are v3.
- Repository kept general per Anna: attribution "samogitia-records contributors"; family-research
  notes (original status, handoff) and the old family map stay local (.gitignore).
- `site/book/` confirmed by Anna as the main GUI and folded in: its build now reads the v3
  drafts and translations (it pointed at a file moved earlier tonight), takes Lithuanian from
  the full translations, shows the side columns (margin surname, No., sex, days, later notes)
  in the entry popover and the seven printed column headings in EN/LT/RU; its "how this was
  read" text updated to the current method. Served at http://100.107.252.39:8742/.
- Model v4 (both books): validation CER 6.6% (1886–90), 9.1% (1896–1902; v3 15.8%). Book 24
  redrafted with v4: 2,582 entries; parser learnt "дер." and the later village formula.
- Book 24 translated EN+LT: 2,582/2,582 (66 agents, ~3.5M tokens); review shows only scattered
  issues (docs/LT_REVIEW_2026-11-11_book24.json): inconsistent priest/township spellings,
  occasional -ski/-ič endings, spelled-out dates.
- Reading GUI fixes from headless-Chrome screenshots: narrow-screen layout (inline grid beat the
  media query: half-width page, black half, misplaced ribbon; pre-existing), translated column
  headers placed from the layout's measured header band and shown only on hover/tap, narrow
  columns vertical; ribbon .webp now served as image/webp (site/serve.py).
- Book 24 GUI: http://100.107.252.39:8743/ (site/book-1896-1902).
- Pushed to GitHub brezgis/samogitia-records (first commit; images excluded) and released the
  v4 model as release `htr-v4`. Hugging Face not touched: waiting for Anna to confirm repo names.
- Hugging Face: model brezgis/samogitia-plunge-htr (v4) and dataset brezgis/samogitia-plunge-lines
  (1,726 lines, train/validation/test by spread) published with cards (CC BY-NC 4.0).
- Books 1827/1/25 (271 scans) and 1827/1/22 (249 scans) downloaded. File 25 is **1902 (2nd half)
  –1907**, not 1891–95; file 22 is the **1860s** (older, simpler printed form). 1891–95 is not in
  inventory 1 files 22–25.
- Book 25 processed with run_book.sh (v4): 2,301 entries, years 1902–1907. Drafts weak on a new
  clerk/formula (birth dates and fathers rarely parsed). Reading round (30 entries) and side columns
  (48 agents) running. Book 22 pipeline running.
- Book 25: side columns 2,300 (740 later notes); reading round 394 checked lines (259 blind).
- Book 22 (1867–1874, 2,114 entries): side columns complete (9 chunks lost in a usage-limit gap,
  re-run); reading round 420 checked lines (270 blind).
- Files 20 and 18 downloaded and identified: file 18 = **1849–1854** (1,816 entries, processed;
  reading round + side columns running). File 20 (1850s) uses a two-page form: each entry spans
  the spread (left: No., counts, dates, baptism text; right: parents, godparents). The pipeline
  assumes three text columns per page side, so book 20 is set aside for a two-page layout pass.
- Files 16 and earlier are in **Polish** (pre-1848); they need a Polish model and rules.
- Disk: freed ~8 GB of regenerable crops/overlays; run_book.sh now cleans them up.
- v5 training on 4 books' labels: 1,816 train / 361 val / 363 test.

## Morning, 2026-11-11
- Committed the night's uncommitted work (books 25, 22, 18 labels and side columns). Reading GUIs
  restarted on :8742 (1886–1890) and :8743 (1896–1902); review site on :8741.
- v5 had been trained before book 18's labels were merged (454 lines), so v6 was trained on all
  five books: 2,174 train / 401 val / 419 test lines.
- Validation CER, v4 -> v5, per book: 1886–90 7.0% -> 5.9%; 1896–1902 8.8% -> 8.7%;
  1902–07 14.0% -> 7.3%; 1867–74 12.2% -> 7.3%; 1849–54 15.6% -> 14.6% (v5 had no book-18 lines).
- **Surnames reconciled** (`pipeline/reconcile_surnames.py` -> processed/surnames.json): the margin
  column and the parents column write the same family surname twice. The margin reading (agent,
  from the image) leads; the draft corroborates it or is shown as a difference. Book 1: 360 agree,
  217 draft is a garbled margin name, 954 margin only, 43 real conflicts. The GUI heading, margin
  cell and index now carry one surname; the translator's spelling is kept when it is the same name.
- GUI: on spreads away from the bookmark the ribbon's tail floated detached below the book; it now
  hangs from the cover's lower edge.
- Model v6 (5 books): validation CER 1886–90 6.6%, 1896–1902 8.7%, 1902–07 6.6%, 1867–74 6.4%,
  1849–54 10.5%. Better than v5 on the three new books, so books 25, 22 and 18 were redrafted with
  v6 (books 1 and 24 keep their v3/v4 drafts and translations).
- Books 25, 22, 18 translated EN+LT from the v6 drafts (142 Sonnet chunks + 3 Opus reviews,
  ~7.9M tokens; two chunks came back with 8/40 entries and were re-run): 2,059 + 2,062 + 1,501 =
  5,622 entries -> processed/translations/translations_v6_book{25,22,18}.json. Translators were
  given the margin surname with each entry and told to treat the two writings as one name.
- Lithuanian reviews (docs/LT_REVIEW_2026-11-11_book{25,22,18}.json) again found systematic slips:
  maiden names after "gim." (-ska / -skis / -ovna mixed), village names not in the genitive before
  "kaime", Russian endings left on surnames (-ago, -aja, -ov), inconsistent clergy and township
  spellings, spelled-out dates, patronymics rendered four ways (1900s). The glossary is dated for
  1886–1890 and lacks 1850s–70s and 1900s terms. Not yet corrected.
- Reading GUIs: 1902–1907 on :8745, 1867–1874 on :8746, 1849–1854 on :8747. Page turn reworked
  (images decoded before the leaf moves; Web Animations; bounded waits).
- Known gap: parse_entries.py rarely extracts father/mother in books 25, 22, 18 (formula variants),
  so search by parent name is weak there.

## Daytime, 2026-11-11 (Anna: "keep cooking all day")
- Pushed to GitHub (merged with the Pages setup made there: CNAME samogitia.brezgis.com, root page,
  page images of the two published books). GUI: random start spread, retry of failed page images.
- **Disk:** the system drive hit 100%. Removed the unused first-stage row crops (`data/*/rows`,
  regenerable by layout.py) and moved scans, row images and line crops of the five finished books
  to /mnt/ssd1TB/anna/samogitia-data (links left in place; .gitignore covers the links). New
  books' scans go to /mnt/ssd240gb/anna/samogitia-data. Each book needs about 5 GB while in work.
- **Book 1827/1/20 is October 1854 – August 1857** and uses a two-page form (left: margin
  surname, No., sex tallies, days, baptism; right: parents, godparents, signatures).
  `pipeline/layout_spread.py` joins the two pages (rows = union of both pages' rules, explicit
  cell boxes, all rows filed under page L); prepare_years.py and segment_lines.py accept the cell
  boxes; run_book.sh runs it when the book has form.json {"form": "spread"}. v6 draft: 813
  entries (1854: 71, 1855: 291, 1856: 269, 1857: 182). Side columns (34 Sonnet agents) and a
  reading round (30 entries, 27 agents) launched.
- **Archive survey** (Opus agent; details in the agent's report, summarised here): fond 1827 has
  only files 1–25 online; Plungė births Sept 1857–1866, 1875–1885 and 1891–1895 are NOT on
  epaveldas as scans (only catalogue links to EAIS, which blocks automated access: consistory
  duplicates LVIA 669/18 Rietavas deanery, drafts LVIA 3005/63). Compatible neighbours with full
  scans: Rietavas 1828/1/2,3,6,7,8,10,12,15 (1855–1905), Salantai 1517/1 (1856–1914), Plateliai
  1661/1/5,7,8 (1886–1915), Telšiai 1480/1 (single-page scans), Kantaučiai 1825/1. Search API:
  POST /vepis-api/internal/find {"term": "\"Rietavo RKB\"", "page": 0, "pageSize": 100,
  "filters": {"providerFacets_str": ["ARCH"]}}. `pipeline/download_book.py` added; Rietavas
  1828/1/7 (1877–82) and 1828/1/12 (1892–99) downloading.
- Lithuanian: glossary being rewritten for 1849–1907 (Opus agent) with fixed decisions on maiden
  names, women's surnames, Russian endings, places and clergy; `pipeline/lt_fix_chunks.py` and
  `merge_lt_fix.py` prepared for a correction pass over all five books (250 chunks).
- **Lithuanian correction pass** (207 Opus agents, ~21.9M tokens; glossary rewritten for
  1849–1907 first): all 9,905 entries of the five translated books re-done against the glossary,
  family surname reconciled with the margin in the same pass. English parents sentence changed
  where the family surname became the margin reading: 956 entries in 1886–90, 1,113 in
  1896–1902, 157 / 112 / 169 in the three newer books (old sentence kept in parents_en_before).
  Opus review of a sample per book afterwards: rows with any problem 6/90 (1849–54), 4/124
  (1867–74), 4/102 (1886–90), 4/155 (1896–1902), 6/124 (1902–07); no rule broken systematically
  (docs/LT_REVIEW_2026-11-11_corrected_*.json). Found on the way: the 1867–74 priest is Pacewicz
  (Пацевичъ, ~600 entries), not Jacewicz.
- **Polish** (Anna's request): docs/PL_GLOSSARY.md (Opus; surnames transliterated into Polish
  spelling, never Polonised); pilot on 1849–1854: 1,500 entries (32 Opus agents, ~3.7M tokens),
  review 16/150 rows with a slip; three formula changes from the review applied by script
  (pipeline/pl_formula_fix.py); name-spelling suggestions (-ówna, ł, rz) recorded as undecided.
  Site has a Polski switch (interface in Polish everywhere; entries in Polish for 1849–1854).
- **Site:** site/library.html, a shelf per parish on a time axis; every book runs on the same
  code with book.js (site/make_library.py from site/library.json); parish-aware text; links to
  neighbouring books; notes rebuilt; names note (recorded form / rendering / no identity claims,
  also in README); page turn rebuilt as a bending leaf of hinged strips; a cover cloth and ribbon
  per volume (11 more National Museum of Lithuania textiles, CC BY, in site/textiles/); two-page
  form shown across both pages (1854–1857). Local: http://100.107.252.39:8750/library.html.
- **Book 1827/1/20 (Oct 1854 – Aug 1857):** reading round 227 checked lines (hard hand: 129 of
  587 lines agreed blind); v7 trained on six books (file 20 validation CER 5.4% -> 3.1%, other
  books level with v6); redrafted with v7: 790 entries, margin columns read (786 surnames).
  NOT translated yet.
- **Rietavas (fond 1828):** all eight baptism books downloaded (1,778 scans, 1855–1905). 1828/1/7
  (1877–82) and 1828/1/12 (1892–99) drafted with v7: rough (new hands, grey scans; year split
  unreliable). Reading round on 1828/1/7: only 200 checked lines of 854, 263 crops rejected as
  badly cut, so line splitting needs work on these scans. v8 training on seven books.
- **Stopping point (Anna, usage limit):** no further agent runs. Open: translate 1854–1857;
  Rietavas margin columns, line splitting, redraft, translation; Polish for the other books and
  the undecided Polish name rules; glossary open questions for native readers; scans of four
  Plungė books are not on GitHub Pages (size), so the public site shows them without page images.

## Local models tried in place of agents, 2026-11-12 (Anna: "the readings with Sonnets are very expensive")
- Scripts in `pipeline/local_models/` (build_reading_set, run_reading, score_reading, run_side,
  build_translation_set, run_translation, score_translation); models, sets and outputs in
  /mnt/ssd240gb/anna/samogitia-htr/llm/ (served by ~/tools/llama.cpp's llama-server).
- **Line reading**, 485 held-out checked lines (test split of seven books); recognizer v8 on them:
  CER 7.5%. On every fourth line (122; v8 6.8%): Qwen3-VL 8B (Q4) blind 86%, with four worked
  examples of the same book 40%, correcting the v8 draft against the image 21.7% (made 62 lines
  worse, 20 better). CHURRO 3B (historical-document model) produced invented text (CER > 100%).
- **Side columns**, 33 entries of 1890, Qwen3-VL 8B against the Sonnet reading: entry number same in
  16, birth day 19, baptism day 20 (a trailing full stop counted as a difference, so a little
  low); margin surname identical in 1 of 30, about half the letters different.
- **Translation**, 40 entries (8 per book), Gemma 4 12B (QAT Q4) with the full glossary in the prompt,
  3–5 s per entry: the Lithuanian baptism sentence is close to the agents' (10 of 40 identical), but
  the date differs in 6 of 40 baptism and 6 of 40 parents sentences; parents sentences misplace the
  family surname, leave case endings wrong, ignore the margin surname, and do not recover garbled
  words (Дварянъ taken as a man's name). Usable as a rough draft only.
- **2026-11-13, continued.** A current llama.cpp was built at /mnt/ssd240gb/anna/samogitia-htr/llm/llama.cpp-new
  (the May build cannot load Gemma 4's image projector); the small models were deleted.
- **Open Russian recognizer** achimrabus/crnn-ctc-russian (CRNN+CTC, 43 MB, Apache-2.0, trained on 202,603
  lines incl. 19th-c. parish registers, pre-reform spelling): untouched it reads the 485 held-out lines at
  CER 18.1%. Fine-tuned 40 epochs (~5 min) on the 2,462 checked train lines of all books
  (`pipeline/local_models/finetune_rabus.py`; weights in llm/rabus-ru-ft/): validation 3.4%, **held-out
  test 4.0% against 7.5% for Kraken v8** (exact lines 61% vs 39%; better on every book: 1849–54 5.3 vs
  10.3, 1854–57 2.7 vs 3.7, 1867–74 6.0 vs 10.3, 1886–90 3.1 vs 6.1, 1896–1902 3.8 vs 7.6, 1902–07 3.2 vs
  6.0, Rietavas 8.3 vs 16.2). The two recognizers give the identical line for 181 of 485; 157 of those
  equal the label (most of the rest differ only in spacing around a hyphen). Not yet used for drafting.
- **Vision chat models on line reading** (122 lines; v8 6.8%): Gemma 4 12B blind 76%, with examples 57%,
  correcting v8 19.3%; Qwen3.6 27B (Q3_K_M) blind 33%, with examples 30%, correcting v8 10.4% (37 lines
  better, 38 worse). Side columns (33 entries): neither matched more than 1 of 30 margin surnames;
  numbers same as the agent in about half.
- **Translation, Qwen3.6 27B** (Q3_K_M, ~11 s per entry and language): Lithuanian baptism sentence
  identical to the agents' in 21 of 40 (Gemma 10) and the glossary's clergy forms and sentence order
  are followed, but the date differs in 8 of 37 well-formed answers, and it invents content (a month
  changed, "Ona, Gabrieliaus duktė", a township made from a given name). 3 of 40 Lithuanian and 5 of 8
  Polish answers were cut off at the 900-token limit, so Polish is not assessed.

## Cheaper pipeline trial, 2026-11-15 (Anna: redraft a book with the new recognizer; count what a template could translate)
- `pipeline/predict_crnn.py`: batched drafting with the fine-tuned CRNN (weights
  /mnt/ssd240gb/anna/samogitia-htr/models/crnn-ru-v1/best_model.pt), same output form as predict_lines.py.
  Batched it scores 3.9% on the 485 held-out lines. A whole book (50–68k lines) takes about 4–6 minutes.
- Books 1827/1/24 (1896–1902) and 1827/1/25 (1902–1907) drafted with both crnn-ru-v1 and Kraken v8
  (new files year_draft_/entries_<year>_crnn-ru-v1 and _plunge-v8; existing drafts, translations,
  surnames.json and site data untouched).
- `assemble_drafts.py`: a line ending " -" no longer leaves a space inside the joined word.
- `parse_entries.py` extended for the other books' wording: "закон. / зак. суп.", birth dates as
  "16 Іюня сего 1897 года", "1899 года 25 Февраля", "Января1 дня" or in words, and "изъ" misread or
  fused to the mother's name. Fields found, old -> new parser on the same drafts (no field fell):
  1896–1902 birth date 449 -> 2,268 of 2,603, parents' surname 466 -> 1,906; 1902–07 birth date
  0 -> 1,349 of 2,101, father 162 -> 944; 1886–90 father 536 -> 724 of 1,267; 1867–74 and 1849–54
  birth date 3 -> 1,362 and 9 -> 859, but father/mother still 0 there ("урожденной", no township).
- `pipeline/local_models/compare_drafts.py` (writes nothing). 1896–1902, Kraken v8 -> CRNN, new parser:
  baptism day equal to the side column 1,933 -> 2,149 of 2,427; birth day 1,621 -> 1,974 of 2,484; all
  six fields parsed 699 -> 1,148; parsed surname agreeing with the margin 32% -> 45%. (The margin
  surname is found whole among the words of the parents column in 60% of entries with either
  recognizer, 46% in 1902–07; that test is too coarse to show a letter-level gain.) Measured on the
  485 held-out lines: lines with a word outside the frequent formula vocabulary (226), v8 8.3% ->
  CRNN 5.4% CER; such words reproduced exactly 163 -> 196 of 266; formula-only lines 6.8% -> 2.5%.
  So the CRNN is better on names as well, by a smaller margin than on the formula.
- **Template-ready entries** (all six fields parsed and both days equal to the agent-read side column):
  933 of 2,603 (36%) in 1896–1902, 466 of 2,117 (22%) in 1902–07. Requiring also that the parsed
  surname agrees with the margin: 420 (16%) and 201 (9%). Against the agents' Lithuanian on those
  entries: baptism date the same in 892 of 932 and 448 of 463; birth date the same in 95% where the
  agent sentence has a date.
- Caution found on the way: in July 1897 (scans 59–62) the CRNN reads "Іюля" as "Іюня" in about four
  entries of ten; the agents' July is right (months run in order). Dates from a template need a
  month-order check like the existing year fit.
- Agreed lines as free training data: on train-split spreads of the two books, v8 and the CRNN give
  the same text for 23,154 of 92,948 lines; 10,720 of those contain a word outside the frequent formula
  vocabulary. Kept in /mnt/ssd240gb/anna/samogitia-htr/llm/eval/pseudo_train_b24_b25.json, never in
  annotations.json.
- **crnn-ru-v2** (checked lines x3 + the 23,154 agreed lines, 12 epochs, ~20 min; models/crnn-ru-v2):
  validation 2.7% (v1 3.4%); held-out test 3.9% overall, the same as v1 (exact lines 64% against 61%).
  Per-book differences are within noise (40–70 lines each). No measurable gain on the test: v1 stays
  the working model. Combining the two recognizers line by line was not tried: Kraken alone is right
  on only 30 of the 485 lines. Their disagreement is not a usable flag either: they differ on 304 of 485.
- `assemble_drafts.py`: the hyphen join now needs a letter before the dash (762 of 67,984 lines in
  1896–1902 end in punctuation and a dash and must not be glued). Tests: 19 pass.
- Not done: no template translator written, no book's published drafts or translations replaced.

## 2026-11-15, afternoon (Anna: improve the model further; 2–3 Sonnets + Opus; UI pass; download service; images on the live site)
- **Download service**: user unit `samogitia-download.service` (enabled; `systemctl --user status|stop
  samogitia-download`, log with `journalctl --user -u samogitia-download`). Runs
  `pipeline/download_queue.py data/download_queue.json`: 37 birth registers of 1849–1915 found through
  the archive search (Plungė, Salantai, Plateliai, Kantaučiai, Kuliai, Kartena, Telšiai; Alsėdžiai had
  none in range), one request at a time with a 1 s pause, into data/<parish>-<id>/pages on the system
  drive (92 GB free at the start); it stops by itself when less than 45 GB is free. Status in
  data/download_queue.status.json. The four Plungė "LVIA_3005_63_*" records (1883–1912 drafts, which
  would cover the missing 1891–95) answer 404: catalogue only, no scans on epaveldas. Salantai scans
  are large (about 8 MB a page), so the space floor will be reached before the queue ends.
- **UI pass** (separate agent; site/ and root index.html only, not committed): the root page opens a
  book (random between 1886–1890 and 1896–1902, the two with published scans) instead of the shelf; an
  opening riffle of six leaves to a random spread (~1.8 s, skippable, fade on phones / reduced motion,
  none on deep links); an "Other books" dialog in the book; phone layout fixes. Preview on
  http://100.107.252.39:8971/. Animation smoothness and real clicks not verified (headless only).
- **Live site images**: the site's own page images for all six books are 1.69 GB (two books, 625 MB,
  are published); GitHub Pages allows about 1 GB. WebP at the same size would be 54–64% of that
  (0.9–1.1 GB): not enough room without shrinking the pages. Undecided: see the message to Anna.
- **Model**: `pipeline/train_crnn.py` (5-fold cross-validation over spreads on the 2,936 checked
  train+validation lines, fixed 30 epochs, images cached, stronger augmentation, 3-seed averaging,
  learning curve). Error breakdown of crnn-ru-v1 on the test lines: 315 character errors, of which
  about 88 are punctuation/spacing and 12 capitalisation; the rest (2.7% of characters) are letters.
- **Reading round** (3 Sonnet readers, blind, 120 lines each): 360 parents/godparents lines of
  1902–1907 from train-split spreads that contain a non-formula word, taken from the recognizer's
  0.87–0.935 confidence band (the very lowest band is mostly bad crops and later margin notes).
- **Reading round result** (3 Sonnet readers ~270k tokens, 1 Opus adjudicator ~221k): the readers marked
  336 of 345 usable lines unsure and gave the recognizer's exact text on 11; 15 crops rejected. Opus
  adjudicated one reader's 120 lines from the image with both readings in view: 16 image_checked,
  98 draft, 6 rejected; nearer to the writing: reader 55, recognizer 45, both 14, neither 6. So about
  half a million tokens bought 16 trainable lines: on middling-hard name lines of this hand neither
  Sonnet nor Opus reads with confidence, and the round was not extended to the other 240 lines.
  Nothing merged into annotations.json; all outputs kept in
  data/plunge-1827-1-25/training/labels/round_2026-11-15/. Opus's notes: the reader miscounts minims
  in names (и/н/ш/л) and over-brackets; the recognizer has good letter shapes and endings but invents
  letters in names, drops spaces ("заксуп.") and transcribes stamps and pencil dates as text.
- **Cross-validation of training variants** (5 folds over spreads, 2,936 checked lines, 30 epochs, no
  epoch picking; character error all / name lines / formula lines): first recipe 3.84 / 4.84 / 3.08;
  stronger augmentation 3.72 / 4.89 / 2.82; three seeds averaged 3.55 / 4.51 / 2.81; half the labels
  4.79 / 5.93 / 3.91; a quarter 6.01 / 6.75 / 5.44. So each doubling of labels still takes off about
  1.1 points; augmentation and averaging are worth 0.1–0.3. Confidence (mean probability of the
  chosen class) orders lines by error: lowest fifth 9.0% CER, highest fifth 1.3% (fold 0).
  **crnn-ru-v3** = stronger augmentation on all 2,936 train+validation lines: held-out test 3.9%
  (exact 63%; v1 3.9%, 61%). v3 is the working model from here; `run_book.sh` drafts with a CRNN when
  the model name starts with "crnn-".
- **Salantai 1517/1/1 (1856–1862, 128 scans, two-page form)**: the scans are 3,200 px wide, and the
  layout step's pixel thresholds found no rows; pages/ now holds copies enlarged x1.5 (originals in
  pages_orig/, ignored by git). Then: 529 entry rows, 9,625 line crops, years 1857–1862 detected
  (1856 not), crnn-ru-v1 draft readable. 42 of 128 spreads still have no rows (not looked into).
- **Whole-entry reading pilot on Salantai** (4 Opus readers, blind, 3 entries each, ~394k tokens):
  226 lines -> 66 image_checked (29%; 43 train, 11 validation, 12 test), 134 draft, 26 rejected
  crops. About 6,000 tokens per checked line; the checked lines are mostly formula, names stay
  drafts. On the checked lines the recognizer's draft is 5.3% off (23 of 66 identical). Retraining
  with the 43 train lines (x5): the 23 held-out Salantai lines go from 4.9% to 3.5% CER (568
  characters, 28 -> 20 errors: indicative only). Readers' notes: line crops on this book often
  merge two lines or cut one (slanted baptism column on scan 15), the masking paints out real
  line-initial letters ("оспріемниками"), line-end marks look like dots/colons (no convention
  yet), struck-through words are not covered by the guide. Outputs in
  data/salantai-1517-1-1/training/labels/round_2026-11-15/; not merged into annotations.json.
- **Shipped** (Anna: "ship what we have"; pushed to GitHub, three commits). Page images are no longer
  in the repository: all six books' pages (2,736 WebP files, 778 MB; `site/make_pages_webp.py`,
  quality 35, about 46% of the JPEGs) are in the Hugging Face dataset **brezgis/samogita-records**
  (Anna's repo and spelling) under pages/<parish>-<fond>-<inv>-<file>/, with a card; the published
  site loads them from there (`?pages=hf` / `?pages=local` override; other hosts use local files).
  Recognizer **crnn-ru-v3** uploaded to brezgis/samogitia-plunge-htr with an updated card. Default
  search scope is the open book's parish. Standing rule: dataset updates and significant model
  updates are pushed to Hugging Face.
- **Salantai 1517/1/1, later on 2026-11-15.** `layout_spread.py` closes the baptism column at the right
  page when its own rule is missed: 775 rows (was 529), 4 spreads without rows (was 42). Line cropping
  reworked by an agent (`segment_lines.py`: margin above/below a cell, slanted rules, per-cell writing
  slope, cuts mid-gap; `refine_lines.py`: no join across a rule unless a tail, printed rule as left
  limit, neighbours' ink painted out, no-text crops dropped; `predict_crnn.py` levels sloped lines):
  crops that look like two lines 841 -> 264, mean recognizer confidence 0.916 -> 0.926; control book
  (20 scans of 1827/1/24, in scratch) 332 -> 31. **Re-running an already labelled book would move
  lines: on the control 66 of 557 labelled ids would name a different line or none. Do not re-run
  labelled books until labels are carried across by position.** Levelling is only in predict_crnn.py;
  training on sloped crops needs the same step (done by hand for the test below).
- **Full reading round on Salantai** (10 Opus readers x 3 entries, blind, ~1.2M tokens): 585 lines ->
  200 image_checked (34%; 154 train, 28 validation, 18 test), 361 draft, 24 rejected (4%; the pilot
  on the old crops rejected 12%). About 6,000 tokens per checked line. Yield depends on the clerk
  (one hand: 4 of 47). Readers' notes: the previous entry's last line and month headings ("Ноябрь.",
  "тоже.") filed under the next entry (three readers); unmasked ink from the line above in some crops;
  a black fill rectangle in 0072_L2_godparents_02; small corrections written between lines. Outputs in
  data/salantai-1517-1-1/training/labels/round_2026-11-15b/ (not merged into annotations.json).
- Retraining with the 154 Salantai train lines (x3, levelled) beside the 2,936 lines: on the 46
  held-out Salantai lines (1,103 characters) see the figures in the message to Anna; candidate weights
  /mnt/ssd240gb/anna/samogitia-htr/models/crnn-ru-v4-candidate.pt (not adopted, not uploaded).
- **Lidar pilots** (outside this repository). Latvia, Taurene parish (the scene in
  /mnt/ssd240gb/brezgi-lidar is Latvian, around Brežģis): page http://100.107.252.39:8815/, files in
  /mnt/ssd240gb/anna/lidar-farmsteads/. Lithuania, a 6x6 km block south of Plungė (Luknėnai, Stalgas):
  /home/anna/research/lidar-plunge/, images on http://100.107.252.39:8816/. Findings: traces survive
  under trees and are mostly erased in drained fields; the 1944 German air photograph is the real
  evidence of lost farmsteads; nothing ground-checked; lidar licence terms unread.
- **Labels merged, assembly fixed, crnn-ru-v4** (agent, evening of 2026-11-15). `pipeline/merge_single_reading.py`
  (book and round are required arguments; refuses ids not in that book): Salantai annotations.json has
  585 records (200 image_checked: 154 train / 28 validation / 18 test; 361 draft; 24 rejected).
  `assemble_drafts.py`: entry membership judged against the opening line itself (overlapping or
  sloped boxes used to leave the previous entry's last line in the next one), month headings between
  entries ("Ноябрь.", "тоже", "Мѣсяцъ") removed from the text and kept as `heading` / `heading_month`,
  looser detection of openings; `parse_entries.py` passes the headings on. Salantai: entries starting
  with their opening word, baptism 615 -> 658, parents 602 -> 617 of 714; 200 entries change text.
  Plungė 1827/1/24 1898–99 (in scratch): 218 of 813 change, 183 of them only a filler dash moved; no
  regression seen. The readers' "previous entry's tail" complaints came from sheets grouped by layout
  row, not from assembly. Tests: 22 pass (3 new). `train_crnn.py` levels sloped lines with
  predict_crnn's `level`; `final` takes --splits and --repeat BOOK=N.
- **crnn-ru-v4** (2,936 lines + 182 Salantai lines x3): Salantai test 1.4% (6 errors in 431 characters,
  18 lines) against 3.9% for v3, but the 485-line test set 4.2% against 3.9% (343 vs 317 errors; worse
  on five of seven books). So v3 stays the general model (and the one on Hugging Face); **v4 is used
  for Salantai only**. Salantai redrafted with v4, labels and the new assembly: 776 rows, of which
  62–74 are printed column-heading rows and about 29 are fragments (real entries nearer 665).
  parse_entries.py does not know this book's wording: father/mother 0 in every year, no baptism date
  or priest in 1858 (dates in digits). GPU was shared with another of Anna's jobs (little-guy-sim).
- **Parser for the older wording; heading rows and fragments** (agent, night of 2026-11-15). `parse_entries.py`
  now reads "… [father] и [mother] урожденной [maiden] [surname] законныхъ …" without a township,
  dates in digits, priests after "Ксендзомъ / онаго Кс."; priest and village values are trimmed of
  the introducing words and the parish. Old -> new on the same drafts, in memory (no Plungė file
  rewritten; no field lost a value anywhere): father/mother 1849–54 1 -> 1,146 of 1,515; 1854–57
  0 -> 629 of 790; 1867–74 0 -> 1,599 of 2,064; 1902–07 1,108 -> 1,374 of 2,117; priest 1902–07
  165 -> 1,844, 1896–1902 1,703 -> 2,535, 1886–90 968 -> 1,238. Read against the draft text, 40
  newly filled entries per book: 39, 39, 36, 38 of 40 fully right in the four older-wording books,
  35 and 32 of 40 in 1902–07 (fathers with patronymics are the weak spot).
  `assemble_drafts.py` drops printed column-heading rows at the top of a page side and, where a book
  has no side-column numbers, folds a fragment row into the entry above by text (flags what it keeps
  but doubts). **Salantai: 776 rows -> 677 entries** (75 heading rows dropped, 24 folded, 12 flagged);
  father 0 -> 588, baptism date 498 -> 609, priest 402 -> 635, birth date 410 -> 508. On
  1827/1/24 1898–99 the assembled text is unchanged; the text-only fold agrees with the numbered fold
  on 72 of 74 rows. Tests: 32 pass. The Plungė books' published entries files were NOT regenerated.
- **Opus translation pilot on Salantai** (6 translators x 40 entries, EN+LT, ~1.0M tokens, about 4,100 per
  entry against ~1,400 for Sonnet on the Plungė books): fluent, glossary followed, nothing invented;
  outputs in data/salantai-1517-1-1/processed/translations/pilot_2026-11-15/ (not merged, not on the
  site). Found: 239 of 240 entries have a doubtful name; the same priest is "Aleszewski [?]" in one chunk
  and "Chmielewski [?]" in the next; scan 11 has the godparents' text in the parents column; scans 24–25
  and 34 have entries split across page breaks and columns out of step; the first 14 entries are Nov–Dec
  1856 but labelled 1857; May baptisms with June/July births; glossary lacks Salantai's clergy, a
  village table, "-атъ" endings, "пополудни", "Администраторъ", a soldier on leave, several given names.
  The other 435 entries were not translated.
- **Neural field tagger** (agent; code and tables in pipeline/neural_parser/, RESULTS.md; models in
  /mnt/ssd240gb/anna/samogitia-htr/neural-parser/). Silver labels for 9,905 entries from the agents'
  names lists and the rule parser (measured 7.7% wrong on 704 labels, mostly span edges). A
  character-level tagger, leave-one-book-out, name fields, F1 within 2 characters against the agents'
  spans only: 85.9 / 90.8 / 93.6 / 91.5 / 88.0 on the five Plungė books against 67.0 / 76.1 / 76.7 /
  66.4 / 67.0 for the rules; XLM-R and rubert are within 0.6 of the character model. Side-column
  checks agree (family surname = margin: 32–60% tagger, 22–44% rules; birth day 63–74% against 54–65%).
  On Salantai and 1827/1/20, of 50 disagreeing entries read per book: tagger right 126 and 139 fields,
  rules right 12 and 8. No human gold; 46% of silver spans are rule-made. Parser bugs found, not
  fixed: "Мая" matched inside "родившаяся"; "волости" matched inside surnames like "Волонтетвъ".

## 2026-11-16/17 (Anna: start the Salantai fixes, wire in the tagger, push)
- **Eight Salantai scans whose two pages are not the same opening** (16, 25, 34, 79, 81, 86, 92, 112): the
  left page's baptisms and the right page's parents/godparents belong to different entries and the
  dates jump at the next scan; a leaf is missing between them (lost, or two leaves turned together
  when photographed; the folio numbers would tell). About 44 entries affected; flagged, not re-paired.
- `assemble_drafts.py`: a row whose "parents" cell is really the godparents column (scan 11: the
  right-page template was placed one column too far right; the real parents column was never cropped)
  is refiled and flagged; continuations at the top of a page side are folded into the last entry of
  the previous side; out-of-step page sides flagged; `assemble()` is a pure function. The same template
  fault is on plunge-1827-1-20 scan 4. Not re-laid-out (line ids). `infer_years.py`: a year word
  divided at the line end, "семаго", round years, and a previous year at the start of a book are read
  (Salantai: 14 entries of Nov–Dec 1856). **Salantai: 673 entries** (1856: 14, 1857: 142, 1858: 141,
  1859: 130, 1860: 66, 1861: 121, 1862: 59), 38 flagged. run_book.sh still drops years with fewer than
  20 rows (1856 was run by hand).
- `pipeline/check_months.py`: fits the baptism months as non-decreasing through the book, using the
  clerk's month headings; flags a month that breaks the order, a birth after the baptism, a birth month
  that is a misreading. Salantai: 73 entries flagged; plunge-1827-1-24 (crnn-ru-v1, in scratch): 99, with
  the known "Іюня for Іюля" of July 1897 caught (14 flags on scans 59–62).
- docs/LT_GLOSSARY.md section 11, Salantai: formulas, twelve priests with one fixed form each
  (Piotr Staszkowski ~201 entries; "Aleszewski" and "Chmielewski" are one man, "Kasper Chmielewski [?]"),
  12 villages settled against OpenStreetMap places within 15 km (data/gazetteer/
  osm_places_salantai_15km.json; 182 entries; modern names, an exception to "never restore", pending
  Anna's word), "-атъ/-ятъ" = misread "-ахъ/-яхъ", missing terms and given names (all "proposed, not
  reviewed by a native speaker").
- **Field tagger in the pipeline** (off by default: FIELD_TAGGER=1 for run_book.sh, `--tagger` for
  parse_entries.py; pipeline/neural_parser/apply.py, combine.py; weights models/field-tagger-v1). Per
  field: both agree -> `by: both`; rules empty or different -> the tagger's span if its confidence is
  at least 0.8 (0.5 for the family surname); township only where the rules find the wording in a
  fifth of a file's entries; rules decode dates. On the two held-out books the combination scores
  91.0 / 91.7 on name fields (tagger alone 90.8 / 91.6, rules 76.2 / 66.7). New fields maiden_name,
  family_surname, godfather, godmother, godmother_status; old fields and keys unchanged.
  Parser fixes on the way: "Мая" no longer found inside other words (1,062 birth months newly filled
  across seven books, 1,027 fitting their neighbours), "волости" no longer matched inside surnames,
  "Вол." variants, days kept beside an unreadable month, "восмаго", a digit standing before a month.
  A handful of correct May readings in badly garbled text are now empty. Read by the agent on 40
  Salantai entries: 464 of 480 fields right as delimited in the draft (village 35 of 40). Tests: 50.
  Salantai re-parsed with the tagger on. Plungė entries files not regenerated.

## 2026-11-19 (Anna: regenerate the Plungė entries; Salantai margin columns)
- **Plungė entries re-parsed** with the current rules and the field tagger, from the drafts the published
  books are built on (1886–90 plunge-v3 incl. 1888, 1827/1/18 v6, /20 v7, /22 v6, /24 v4, /25 v6). Re-parse
  only: no re-assembly, same rows and the same text in all 10,753 entries, tagger spans stale 0
  (new files processed/tagger_spans_*). Old -> new filled: father 1,926 -> 9,824; mother 1,926 -> 10,378;
  birth date 1,680 -> 8,569; priest 4,687 -> 10,458; village 7,585 -> 9,916; baptism date 8,620 -> 9,113.
  Emptied: 47 baptism dates (the ones looked at were a "May" guessed out of garbled text) and 17 townships
  that were parents' names. surnames.json re-run (it was reproducible from the old files; "agree" 470 ->
  2,999 of the six books). Site data rebuilt without images for all six books; translations untouched.
  Not committed.
- **Salantai margin strips.** `side_strips.py` SIDE_MODE=compact: one rotation (SIDE_ROT) and the upright
  strip side by side, two entries per sheet at about 1100 x 1500 px (the "wide" sheets were 1100 x 8000
  and reached a reader shrunk four times). Two faults fixed for the two-page form: the strip's right
  edge is the row's baptism cell (counting rules stopped short of the number columns on 38 of 124
  pages), and the strip runs 230 px past the row (surnames written downwards overrun into the next
  row). Columns here: surname, No., count of boys, count of girls, birth day, baptism day.
- **Pilot, one Sonnet and one Opus reader, the same 24 entries, blind** (on the sheets before the two
  fixes: 6 strips empty, 1 cut): 73k and 89k tokens. On the 17 whole strips every number and the sex are
  the same in both; the surname has the same letters in 12, differs by one letter in 5. Scans 25 and 86
  (mismatched openings) show a margin family different from the draft's, as expected.
- **Salantai margin columns read** (Anna approved: Sonnet for all, Opus second look where the parents
  column does not confirm). Sonnet, 17 readers x 40 entries, blind, ~1.56M tokens: 673 entries, 670
  surnames, 668 numbers. Opus, 10 readers, ~1.2M tokens, blind to the first reading, on 374 entries
  (357 whose surname did not agree with the parents column, 17 with a crop remark) recut longer and
  wider (SIDE_OVERRUN=420; sheets in /mnt/ssd240gb/anna/samogitia-htr/work/salantai-side2): the two
  readings have the same letters in 150, differ in 224 (by one or two letters in most). Where they
  differ and the parents column can tell, Opus is the closer 66 times, Sonnet 15, neither clearly 86.
  `pipeline/merge_second_reading.py` settles each surname between the two readings and the parents
  column (`margin_by`: both / second / first; the other reading kept as `margin_alt`).
  `reconcile_surnames.py` now takes the tagger's family_surname where there is one (Plungė "agree"
  2,999 -> 3,995 of 10,753). Salantai: parents column agrees with the margin 365; two readings agree
  but the parents column does not 138; one or disputed reading 170. Sex known for 665, baptism day 663.
  13 later notes, among them a consistory correction of a surname (1876) and four Lithuanian marriage
  notes of 1921–1923. Raw chunks, prompt and the first reading are in
  processed/side_reading_2026-11-19/. Not yet done: translations, site, Hugging Face.
- Found by the readers (processed/side_reading_2026-11-19/row_checks.json): rows that are not entries
  (only the tail of the previous surname, no numbers) or that share an entry number with their
  neighbour, worst on scan 34; entry 33 of 1862 (scan 122) has no row of its own; on scan 125 the
  baptism-day column is outside the strip (page layout). Birth and baptism day are the same number in
  94% of entries, as the clerk wrote them; the margin's birth day equals the day parsed from the text
  in 437 of 549, the baptism day in 594 of 622, the sex in 599 of 635.
- **Repairs to the Salantai margin readings** (Anna: "let's repair stuff"; processed/side_reading_2026-11-19/
  repairs.json, each row keeps `before_repair` and `repaired`). Looking at the whole left pages with the
  row boundaries drawn: on scans 102, 121 and 122 the layout has a false rule inside an entry and misses
  the true one, so a strip started below its entry's number line and showed the next entry; on scans
  29, 51 and 53 a reader had taken the figures of the entry below. Corrected from the page image:
  0029_L3 = 166, 0051_L3 = 186, 0053_L3 = 200, 0121_L5 = 24, 0122_L5 = 30 (the parents column confirms
  the surname), 0102_L4 takes the reading filed under the empty row 0102_L3. 0121_L2 is the end of
  entry 22, which begins at the foot of scan 120 where no row was cut (number inferred, text not
  joined). Rows with no text marked `not_an_entry` (0102_L3, 0034_L3). On the scans whose pages are
  from different openings, rows with text only on the right page no longer carry the left strip's
  reading (`right_page_only`, the reading kept under `strip_shows`). After this no entry number repeats
  or is skipped; the numbers restart at 4 and 5 after scans 79 and 92 (a leaf missing, as suspected).
  **Do not re-run assemble_drafts.py on this book as run_book.sh does: it gives 679 entries, not the
  committed 673 (the committed drafts came from a different invocation); I overwrote the drafts that
  way on 2026-11-19 and restored them from git.** The layout rules on scans 102, 121, 122 are not fixed.
- **The "mismatched" Salantai scans are seams where runs of leaves are missing, not single lost leaves.**
  Entry numbers on the left page of each seam scan and of the scan after it: 16: 55 -> 89; 25: 141 -> 152;
  34: 180 -> 64 (next year); 79: 129 -> 4 (next year); 81: 13 -> 78; 86: 102 -> 143; 92: 172 -> 5 (next
  year); 112: 105 -> 147. Some 250 or more entries of 1856–1862 are not in the 128 scans (the archive
  record lists 128 pages and all were downloaded). So the halves on a seam scan have no partner in this
  file: they can be split into honest half-entries, not re-paired. Not checked: whether the missing
  leaves are in another file (1517/1/2 onwards, years not yet read) or in the consistory's copy.
- Translation started in the background: 3 Opus translators on the first 120 of 671 entries
  (processed/translations/round_2026-11-19/: chunks with the margin reading, its support and warnings;
  INSTRUCTIONS.md updated for glossary section 11).
- **Where the missing Salantai leaves are not.** The archive records give the other Salantai files as
  1862–1872 (1517/1/2), 1872–80, 1880–86, 1886–93, 1893–98, 1898–1902, 1902–08, 1908–14: none overlaps
  1856–1862, so there is no second copy among the downloaded files. The pencilled folio numbers on the
  right-hand pages jump at the seams: scan 15 is folio 14 and scan 16 folio 21 (33 entries missing);
  scan 24 folio 29, scan 25 folio 32 (10 entries); scan 33 folio 40, scan 34 folio 57; scan 80 folio
  117, scan 81 folio 131. So the leaves were in the book when it was foliated and are counted in its
  foliation, but are not among the scans (about 5.5 entries per missing leaf, as on the leaves present).
  Not looked at: the other four seams' folios, the last folio number, FamilySearch's film of the fond,
  the consistory's duplicate.
- Search for another copy of Salantai 1856–1862 (2026-11-19): epaveldas publishes exactly the 128 images
  we have for 1517/1/1 (the record's own resource list); gen.wooyd.org's source list, Genmetrika's
  births page and the FamilySearch wiki name no second copy; FamilySearch's catalogue needs a login and
  was not searched; an epaveldas search across all holders timed out and then returned HTTP errors
  (not retried). One unfollowed lead: gen.wooyd.org lists Salantai among parishes in the Vilnius
  University Library collection on epaveldas (inventory in a linked spreadsheet, not opened).
- Translator 001 (40 entries, 178k tokens): notes that English surname and village forms are not fixed by
  the instructions (each translator chooses), that "-tis" surnames need "-čio" in the Lithuanian
  genitive, that 0007_L5 counts as "confirmed" although margin and parents column differ in the first
  letter (Тенюшіовъ / Бенюшіовъ), and that 0011_L1–L3 have empty parents columns (scan 11's known
  template fault) without a warning.
- Translators 002 and 003 back (185k tokens each; 120 entries translated in all, out_001–003, not merged).
  `reconcile_surnames.py`: a margin and a parents-column surname that differ in the first letter no
  longer count as agreeing (the Бенюшіовъ family was read Тенюшіовъ and Сенюшіовъ in the margin and
  passed as confirmed). Open before the other 551 entries: one rule for English surname and village
  forms; "-tis" -> "-čio" in the glossary; whether settled villages (11.3) keep modern names.
- **Salantai translated, EN + LT** (Anna agreed the three rules: one English rule for surnames and villages,
  modern names for the settled villages of 11.3, "-čio/-džio" spelled out in 7.2). 17 Opus translators
  x 40 entries, about 3.3M tokens (about 4,900 per entry, glossary reading included): 671 entries, every
  chunk parses with its rows in order and no Cyrillic in the translations; combined in
  processed/translations/translations_v4_salantai1.json (not on the site, not on Hugging Face). 658 of
  671 entries carry at least one [?], mostly bare stems from -овъ genitive plurals and garbled
  godparents. Chunks 001–003 were made before the English rule.
  To settle before publishing (from the translators' reports): English form of villages outside the
  settled table (as drafted, or Russian nominative plural: translators differ); Іо- as "Io-" (7.1) or
  "Jo-" (4.4); one garbled given name read Іервій / Дервій / Зервій (one translator: Jerzy [?]);
  "итоговъ Прихода" after "въ мѣстечкѣ Салантахъ"; "Губернскій Секретарь"; given names missing from
  the glossary (Саломея, Дорота, Кунигунда, Каролъ ...); margin surnames the translators think worse
  than the parents column (0090_L5, 0091_L3, 0098_L3, 0054_L3, 0057_L2, 0058_L4, 0101_L3, 0116_L2,
  0121_L9, 0041_L2, 0037_L7, 0040_L6); 0056_L3's margin holds the mother's maiden name; 0054_L1 is
  December 1858 (no. 205), filed under 1859; probable unmarked twins 0049_L7/L8, 0039_L5/L6, 0040_L2/L3;
  the bishop (Maciej Wołonczewski) baptises in 0085_L5. Scan 111 checked against the page: the margin
  rows are right, the parents column there is only garbled.
- **Salantai 1856–1862 on the site** (2026-11-19, late; not committed). New parish in site/library.json
  (names in four languages as Anna gave them) and a book folder named as the Rietavas ones are,
  `site/salantai-1856-1862` (not `book-…`): .gitignore has the matching rules, and
  `make_pages_webp.py site/salantai-1856-1862` / `make_thumbs.py salantai-1856-1862` need the folder named
  (their default is `site/book*`). 128 spreads, 670 entries placed (671 in the index: 0051_L6b, a split
  row, has no cells), EN + LT. `build_book.py`: a row flagged `not_an_entry` in side_columns.json is left
  out of spreads and index (0034_L3, 0102_L3); a `right_page_only` row gets no margin cell; Lithuanian
  is taken when the parents cell has it although the baptism cell is empty (the five right-page-only
  rows). The six Plungė books were rebuilt before and after these changes (surnames.json had changed):
  same counts, and the same bytes before and after. Page images: 256 WebP, 36 MB, in
  brezgis/samogita-records under pages/salantai-1517-1-1/, card updated; the book has "start": true.
  Seen in the browser: entry over both pages with margin and bar, Lithuanian, seam scans 34 and 86,
  the menu with three parishes, search in Salantai, images from Hugging Face (`?pages=hf`).
  Not right: translated column headings on only 15 of 128 spreads (the layout's column list on the left
  pages starts with false rules at x=1 and often ends at the baptism column); on a right-page-only row
  (0034_L2) an empty leaf covers the left page's baptism cell of another entry; the cover cloth and
  ribbon in library.json (1057426455, ukrinai) repeat a Rietavas book's cloth, all fourteen being taken.
  Rebuild after the translations change:
  `SAMOGITIA_BOOK=data/salantai-1517-1-1 BOOK_OUT=site/salantai-1856-1862 BOOK_MODEL=crnn-ru-v4 BOOK_YEARS=1856-1862 BOOK_TRANSLATIONS=translations/translations_v4_salantai1.json nice .venv/bin/python -I site/book/build_book.py && python3 site/make_library.py`
  Also seen: on the seam scans only the five `right_page_only` rows are treated as halves; every other
  row there is shown and indexed as one entry made of two (0086_L3: Józef baptised July 1860 beside
  "Daughter of … born September 1860"; 0034_L4 found in search as "Kazimierz Romanovskii … Daughter of").
  The empty leaf is on all five right-page-only rows (0025_L2, 0034_L2, 0034_L5, 0034_L7, 0081_L6). The
  Russian margin cell gives no sex (sex_letter is empty in all 673 rows). All six Plungė books open in
  headless Firefox; an address with `#s=20` and no `pick` opens on another scan in every book (app.js
  untouched, not looked into).
- **Plungė rows missing from the drafts** (2026-11-20; not committed). Anna found the first baptism of
  January 1906 (book 1827/1/25, row 0202_L2) on the page but not on the site. Its text was in the
  plunge-v6 draft after all, as pseudo-row 0202_L1b (made because row L2 starts with the end of the
  previous entry and the heading "1906 годъ Январь"), and `build_book.py` places only rows that have
  cells in line_proposals, which pseudo-rows never have. Re-keyed 0202_L1b to 0202_L2 in
  year_draft_1906_plunge-v6.json/.csv and the translations file (field `restored` in the draft, `revised`
  in the translation; parents and godparents re-translated from the page: Augustin, son of Augustin, and
  Zenaida née Kiauleikis, Srebalis [?], born 29 Dec 1905, Stalgai [?]). Fields and surnames regenerated;
  every other 1906 entry unchanged. Book 25: 2050 entries placed (was 2049), 2101 in the index.
  The other 140 candidates in lost_rows_candidates.json: none is missing text. The top of every row was
  looked at on the page; where the text went was found by matching names and the child's name against
  the published rows of the same page side, about 45 of those matches read by eye. 102 are entries with
  their own number whose text sits inside the record above; mostly that record holds two to four entries
  (the translations already render them all), but some (0178_L2, 0191_R2, 0215_R2 in book 25) hold only
  the tail of their own entry and the whole of the next, so that entry shows one row too high; where their
  own opening lines went was not traced. 38 are rows that start in the middle of an entry already
  published above. Decisions per row: /mnt/ssd240gb/anna/samogitia-htr/work/lost_rows_decisions.json.
  Not fixed: the same pseudo-row problem hides 187 more entries that are in the drafts and the index but
  on no spread (book 18: 39, 20: 10, 22: 12, 24: 99, 25: 27), among them 0017_L2b in book 18, which holds
  entries 118 and 119 together. 0202_L1 (No. 406, 31 Dec 1905) is filed as 1906-12-31; 0014_L4 in book 20
  (1854) holds the heading and entry No. 1 of 1855.
- **Salantai translations: consistency and faults pass** (2026-11-19/20; not committed). The 17 translators'
  outputs (translations_v4_salantai1.json, 671 entries; copy before the pass beside it as
  `.before_consistency.json`) brought to one set of forms: 284 entries changed. English family and men's
  surnames now take the Lithuanian base (90 forms, mostly chunks 1–3: Ventskus → Venckus, Voionchiov →
  Voionč [?], plus [?] on 19 bare stems); Іо-/Іа-/Іу- surnames are Jo-/Ja-/Ju- in Lithuanian (56
  replacements, 22 entries) and stay Io-/Ia-/Iu- in English (rule in glossary 7.1, my decision, flagged
  for Anna); 119 English village forms follow the rule now in INSTRUCTIONS.md (table rows take the row's
  one form, others the nominative plural only for a plain -ахъ/-яхъ). The garbled name Іервій / Дервій /
  Зервій / Сервій / Беррій / Геррій is one word on six page images (Іержвій with ж in 1857, Іервій
  later) and five of the nine children so named were baptised 7–23 April (St George's day): taken as
  Jerzy / Jurgis [?] in 21 entries, a judgement; Два = Эва (Ewa / Ieva [?]); Лонъ = Леонъ. "итоговъ
  Прихода" = "of the same parish" without [?] (0086_L3 image). Fourteen given names and two terms added
  to glossary 11.4/11.5 (now with an English column). Priests were already uniform.
  Data: 0054_L1 moved to the end of the 1858 entries/year-draft files (register_year 1858, dates
  1858-12-21; tagger_spans_1859, month_check and queue_years still list it under 1859). 0056_L3: the
  margin holds the mother's maiden name; side_columns now has margin_surname Рафаловъ (uncertain) and the
  reading in margin_maiden_name. Margins of 16 rows looked at on the page with the parents column: 11
  re-read (repairs.json now 21 items; three of them, 0037_L7, 0040_L6, 0054_L3, rest on the parents
  column and stay uncertain), 5 left as they were (0057_L2 т/л, 0058_L4, 0101_L3 Ю/О, 0111_L2, and
  0111_L3 С/Б, where the parents column turns out to repeat the margin word, not Осталисовъ). surnames.json regenerated: agree 336, margin 187, margin_only 99, conflict 45, draft_only 4,
  none 2. All readings from the images are mine and unverified.
- **Every drafted entry placed on its spread** (2026-11-20; not committed). `build_book.py` left out any
  entry without line cells of its own: the pseudo-rows (`0202_L1b` etc., made when assembly splits one
  layout row) and real rows missing a column (mostly pages where the layout found no godparents rule).
  New `derive_geometry()`: a pseudo-row is cut out of its parent's lines (its own and those of folded
  layout rows below it) at its own opening line (focal_y[0] + 8, from the year draft), with the parent's
  x extents; the parent's cells are cut to end there; with no opening line of its own the band would be
  split evenly (never needed). A real row missing a column takes its x from the same column on that page
  side, else from the book's usual column offsets. Such entries carry `"placed": "split" | "split-parent"
  | "derived"` in the spread JSON, and `sideFrom` when a folded row's margin reading is theirs (10).
  Placed / index now: 1886–1890 1701/1701 (was 1662), 1849–1854 1515/1515 (1475), 1854–1857 790/790
  (780), 1867–1874 2064/2064 (2052), 1896–1902 2582/2582 (2475), 1902–1907 2101/2101 (2050). Checked
  against builds made just before with hashes: index.js identical in all six books; only spreads holding
  derived rows differ (192 of 1368), and in them only by added entries and parents cut short (no other key
  changed, no box grew); data.js only by those spreads' counts and month ranges. Every split entry's box
  starts within 40 px of its opening line. Two-page forms need nothing special: the right-page cells are
  cut at the left-page opening and the two bands agree to about 1% (book 20, eight spreads). Salantai
  0051_L6b places too (dry run into the scratchpad; site/salantai-1856-1862 not rebuilt). Seen in Chrome
  on the private display: 0202_L2, 0004_R1b and 0004_R1c (book 24: Nos. 87 and 88 framed exactly),
  0017_L2b (book 18: both 118 and 119 under one leaf, as published), 0004_R1 in book 25 (godparents
  column guessed at the cut page edge; its margin box overlaps the baptism leaf, as the layout there has
  no margin rule).
  Year of December entries filed at the head of the next year: register_year was taken from the page;
  corrected in the record (and fields regenerated) for 0202_L1 in book 25 (No. 406, 31 Dec 1905), 0068_L1
  in book 18 (No. 263, 31 Dec 1850), 0080_L1 in book 22 (No. 276, 26 Dec 1869), each checked on the page.
  0202_L1's birth date stays wrong (1905-01-01: the "1 Январь" the parser read is the heading). Book 20's
  0014_L4 is right as an 1854 record; the 1855 No. 1 inside it has no date of its own on the site.
  Records holding two or more entries (153; 0017_L2b among them) are listed for later splitting in
  /mnt/ssd240gb/anna/samogitia-htr/work/multi_entry_records.json.
