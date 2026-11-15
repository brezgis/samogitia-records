# Licences

## Source

The scanned registers are held by the **Lietuvos valstybės istorijos archyvas** (Lithuanian
State Historical Archives, LVIA), fond 1827 (Plungė St John the Baptist Roman Catholic church),
inventory 1, published on epaveldas.lt with the rights statement **NOC-NC** (No Copyright –
Non-Commercial Use Only). Scans are not redistributed in this repository; `page_urls.txt` and the
recorded SHA-256 checksums let anyone fetch and verify them from the archive. Reduced reading
copies of the pages (greyscale, 1,300 px wide, WebP), which the reading site shows, are published
for non-commercial use under the same NOC-NC condition in the Hugging Face dataset
[brezgis/samogita-records](https://huggingface.co/datasets/brezgis/samogita-records).

## Derived data

Everything derived from the scans in this repository (line-crop coordinates, transcriptions,
labels, machine drafts, extracted fields, translations, side-column readings) is released under
**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**, to respect the
source's non-commercial condition. Attribute: "Plungė parish registers, LVIA f. 1827, ap. 1;
transcription and translation: samogitia-records contributors".

Machine output is not ground truth: drafts and translations are unverified and names in
particular are often misread. Labels are Claude transcriptions (blind Opus + Sonnet double
reading with Opus adjudication), not expert human readings. See `docs/` for methods and limits.

## Models

The handwriting-recognition models are fine-tuned from the PP-OCRv6 small base model for kraken
(Zenodo 10.5281/zenodo.21788405, Apache-2.0). Because they are trained on NOC-NC material, the
fine-tuned weights are released under **CC BY-NC 4.0** as well.

The current recognizer (crnn-ru-v3 and later, `pipeline/train_crnn.py`) is fine-tuned from
[achimrabus/crnn-ctc-russian](https://huggingface.co/achimrabus/crnn-ctc-russian) (Apache-2.0) and
is released under **CC BY-NC 4.0** for the same reason. Models are published at
[brezgis/samogitia-plunge-htr](https://huggingface.co/brezgis/samogitia-plunge-htr).

## Code

Code in `pipeline/`, `tests/` and `site/` may be reused under the MIT licence.

OpenStreetMap-derived gazetteer data: © OpenStreetMap contributors, ODbL 1.0.
