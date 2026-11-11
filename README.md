# Samogitia parish registers

Scanned Catholic registers of the Samogitian (Telšiai) diocese → source-linked,
searchable records. Pilot: **Plungė baptisms, register year 1888**, in the 1886–1890
book (epaveldas `1827/1/23`, 202 scans). Original source: Lithuanian State Historical
Archives; recorded source licence NOC-NC. OSM data: OpenStreetMap contributors,
ODbL 1.0. Preserve provenance and source licensing with derived exports.

Methods and progress: [docs/NIGHT_LOG.md](docs/NIGHT_LOG.md); transcription conventions:
[docs/LABELING_GUIDE.md](docs/LABELING_GUIDE.md); Lithuanian terminology:
[docs/LT_GLOSSARY.md](docs/LT_GLOSSARY.md); licences: [LICENSE-DATA.md](LICENSE-DATA.md).

## Current state

| Component | Actual result |
|---|---|
| Scans | 54 spreads downloaded (92–145); boundary scans contain other years |
| Layout | 27 page sides corrected; blank/insert pages and a certification note classified |
| 1888 queue | 434 candidate entry crops, matching the terminal entry number |
| Transcription | 31 pilot entries visually adjudicated. **Machine draft of all 434 entries** (`processed/year_draft_plunge1888-v1.json/.csv`): 702 checked lines + 11,033 model lines; unverified, names unreliable |
| Village matching | Candidate rankings only; no confirmed historical identifications |
| Line segmentation | 11,832 proposals over all 54 spreads of 1888; `refine_lines.py` v2 crops keep words crossing column rules whole and paint out neighbouring-column ink |
| Training labels | 702 checked lines (494 train / 117 validation / 91 test, both hands); 328 independently verified by blind Opus+Sonnet double reading; see docs/LABELING_GUIDE.md |
| HTR model | `plunge1888-v1` (PP-OCRv6 small fine-tuned): 93.5% char accuracy on validation, 94.9% on test (base model ~81%) |
| Parsing/linking | `parse_entries.py`: formula-based fields for all 434 entries (`processed/entries_plunge1888-v1.json`). vs pilot: sex 30/31, baptism date 29/31, birth date 23/31; names weak (model-limited). Linking not implemented |

**The full-year transcription is not complete.** The pilot retains unresolved
fields. Image-reviewed values are provisional machine adjudication, not independently
verified ground truth. Reader agreement and candidate convergence are not accuracy.

Boundary corrections: `0092_R1` is 1887; `0092_R2–R3` are entries 1–2 of 1888.
Scan 144 left starts with entries 433–434, then begins 1889; scan 145 is 1889.
`0125_R4` in the **processed** layout is a certification note. Corrected row
numbering differs from the original crops: always follow the manifest's image path.

## Data and commands

Use `.venv/bin/python -I`; dependencies are recorded in `requirements-data.txt`.
Commands resolve data paths relative to the project.

```sh
.venv/bin/python -I pipeline/gazetteer.py
.venv/bin/python -I pipeline/prepare.py
.venv/bin/python -I pipeline/segment_lines.py
.venv/bin/python -I pipeline/htr_dataset.py
.venv/bin/python -I -m unittest discover -s tests -v
```

Within `data/plunge-1886-1890/`:

- `pages/`: original scans. `rows/`, `layout/`, `reads/`, `crops/`: preserved experiments.
- `review/adjudication.json`: image-review decisions and unresolved readings.
- `review/layout_overrides.json`: reviewed approximate boundaries/year exclusions.
- `review/village_candidates.json`: original strings, aliases, scores and provenance.
- `review/village_comparison.csv`: original A/B candidate-convergence experiment.
- `processed/pilot_reference.csv`: 31 entries × 12 fields, with statuses/source paths.
- `processed/pilot_reference.json`: full provenance and all earlier readings.
- `processed/queue.json`: corrected row crops and statuses. `expected_entry_no` is
  inferred ordering, **not a transcription**; `entry_no` records prior reads/anchors.
- `processed/batches/`: pending transcription jobs, at most 16 entries each.
- `processed/rows/`: context crops. Padding includes adjacent text; `focal_y` and
  `bbox` preserve the focal entry and crop coordinates in the original scan.
- `training/line_proposals.json`: proposed boundaries with no invented labels.
- `training/annotations.json`: checked/draft image–text pairs and provenance.
- `training/exports/<dataset-id>/`: checked `.png`/`.gt.txt` pairs and manifests.

The gazetteer is a modern radius-based list, not an authoritative historical parish
list. Scores are edit similarities, not confidence probabilities. Matching does
not overwrite transcriptions or automatically confirm a place.

## GPU training

Working as of 2026-11-10. `.venv-htr` is a symlink to
`<htr-store>/venv` (system and nvme1TB drives are nearly full).
Pins are in `requirements-htr.txt`, full freeze in `requirements-htr.lock`.
Kraken 7.1.1 caps torch at `<=2.14`, so 2.14.1 is excluded.

Baseline model: PP-OCRv6 small, Zenodo 10.5281/zenodo.21788405, Apache-2.0,
at `<htr-store>/models/ppocrv6-small/small.safetensors`
(sha256 `3108259779f5abfed3908a1c9eafba64d17e4a2a169368c539ecfeff04c018f3`).
Its model card reports 16.3% CER on its own Russian test set; nothing about this register.

```sh
# Pretrained baseline over proposals (or --ids-from annotations); predictions are NOT labels:
.venv-htr/bin/python -I pipeline/baseline_htr.py --model <model.safetensors>
# Training preflight; no training without --run:
.venv-htr/bin/python -I pipeline/train_htr.py --base-model <model.safetensors>
# One-epoch installation check; not a useful recognizer:
.venv-htr/bin/python -I pipeline/train_htr.py --base-model <model.safetensors> --smoke --run
```

Baseline outputs are in `training/baseline/<run_id>/` with `run.json` provenance.
Observed: the model modernizes orthography (drops final ъ, writes Младенец for
Младенцъ); fine-tuning is expected to address this. Its confidences are uncalibrated.
Pilot fine-tunes (2026-11-10, `--pilot`, 116 train / 19 validation lines): ketos test
on validation gives base 80.9% vs fine-tuned 82.3% character accuracy, a small gain
within noise. `baseline_htr.py` (page-level kraken inference) prepares lines differently from
training and under-reports fine-tuned models (10.2% vs 6.5% CER). Use
`pipeline/predict_lines.py`, which runs the ketos-test data module and matches it
(6.8% CER on validation for plunge1888-v1).
Run manifests and outcomes: `training/runs/*.json`; weights on the scratch SSD.

Double-reading round (2026-11-10): 45 entries read blind by Opus and Sonnet, Opus
adjudication (`pipeline/merge_double_reading.py`, raw readings in `training/labels/double_read/`).
Fine-tune on that dataset: **validation 81.5% -> 93.5%, test 80.6% -> 94.9% character
accuracy** (ketos test). Model `plunge1888-v1` on the scratch SSD; see training/runs/.

Earlier blocker was labels: preflight wants 500/50/50 checked lines plus 100
independently checked evaluation lines across both hand groups.

`pipeline/evaluate_htr.py` computes strict CER/WER from keyed reference/prediction
JSON, preserves historical characters, and counts missing predictions as errors.
Split by spread; keep test data out of training and tuning. The early/late
handwriting groups are provisional. Entry boundaries: the layout's row boundaries are approximate and on some spreads
(esp. 119–121) cut entries apart. `assemble_drafts.py` snaps each boundary to the nearest
baptism line reading "Тысяча…" (31 moved; recorded per entry as `boundary_snapped`).
English translations: `processed/translations/translations_plunge1888-v1.json` (Sonnet agents,
from the drafts; names romanized as drafted, never corrected). The exact draft text each was
made from is in `translations/sources/` (part_fix/part_fix2 supersede re-assembled entries);
all 434 matched the current drafts on 2026-11-10. Re-translate an entry if its draft changes.

Languages: everything published is bilingual English/Lithuanian. The review page has an
EN/LT switch (interface, field names, months, notes); translation files carry `*_en` and
`*_lt` fields. In Lithuanian, names are written in Lithuanian orthography as read
(Шимкусъ -> Šimkus); a standard Lithuanian given-name form (Юзефъ -> Juozapas) only where the
reading is clear. Never correct a name beyond that; mark doubt with [?].

Other years (2026-11-11): `prepare_years.py` -> `processed/queue_years.json` (1,220 rows from
scans 1-91, 146-202; the 1888 queue is untouched), lines in `training/line_proposals_years*.json`,
years inferred from drafts by `infer_years.py` (1886: 362, 1887: 398, 1889: 386, 1890: 101
entries after splitting merged rows; no order conflicts). Scans 4-48 (1886 + early 1887) are a
third hand the v1 model cannot read (~15% of formula words correct); a double-reading round
on that hand precedes v2. Inserted decrees/amendments (scans 67-68, 90-91, 150-151, 153-154)
are listed in `processed/non_table_sides_years.json` for separate review.

**Reading book (main GUI):** `site/book/` — the register as a book, EN/LT/RU, with search across
all years. Rebuild after drafts/translations change: `.venv/bin/python -I site/book/build_book.py`
(add `--images` once to cut the page images from the scans). Serve with
`python3 -m http.server 8742 --bind 100.107.252.39 --directory site/book`.

Review site (working view): `pipeline/build_review_site.py` -> `site/review/` (scan + draft + fields per entry).
Serve with `python3 -m http.server 8741 --bind 100.107.252.39 --directory site/review`.

The review site is `site/review/`.
