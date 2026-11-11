# Licences

## Source

The scanned registers are held by the **Lietuvos valstybės istorijos archyvas** (Lithuanian
State Historical Archives, LVIA), fond 1827 (Plungė St John the Baptist Roman Catholic church),
inventory 1, published on epaveldas.lt with the rights statement **NOC-NC** (No Copyright –
Non-Commercial Use Only). Scans are not redistributed in this repository; `page_urls.txt` and the
recorded SHA-256 checksums let anyone fetch and verify them from the archive.

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

## Code

Code in `pipeline/`, `tests/` and `site/` may be reused under the MIT licence.

OpenStreetMap-derived gazetteer data: © OpenStreetMap contributors, ODbL 1.0.
