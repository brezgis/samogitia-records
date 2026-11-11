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
