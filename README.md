# Cooking the Cat

An account of AI centric software development through Puma’s practical experience.

A principles-focused public edition of Puma’s engineering account: six parts, 31 chapters, a preface, working vocabulary and 69 references. The manuscript is dated **2 October 2026**; the focused editorial revision was approved **13 October 2026**. Technical case studies provide supporting evidence rather than a personal project roadmap. See the edition notes for attribution and the four small reading-view corrections.

## Build and preview

Python 3.12 or later is required. The text site builds without network access after its dependencies are installed.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python tools/build.py --output docs --source-repository https://github.com/MrScripty/Cooking-The-Cat
python tools/check.py --site docs
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000/`. Relative links support the repository’s exact `Cooking-The-Cat` Pages path. Reading and chapter navigation work without JavaScript. Search loads a local index; the continuous reading view supports browser Find and printing. There are no analytics, application backend or third-party runtime assets.

## PDF edition

The PDF is generated from the same continuous reading view. To rebuild it, install the optional dependency and make Chromium available, either through Playwright or with `--browser /path/to/chromium`:

```sh
python -m pip install -r requirements-pdf.txt
python tools/export_pdf.py --site docs
python tools/check.py --site docs
```

The export creates the real `docs/downloads/cooking-the-cat.pdf` and adds PDF links to the reading pages only after the file exists. Rebuilding the static site removes that generated PDF; rerun the export afterward.

## Source and evidence

- `manuscript/cooking-the-cat.md`: approved public manuscript and Markdown download source.
- `manuscript/manifest.json`: verified section boundaries, hashes and route mapping.
- `web/`: reading styles, local search and the optional approved cover.
- `tools/`: static generator, checks and optional PDF export.
- `docs/`: generated GitHub Pages site, including `.nojekyll`.

The public manuscript SHA-256 is `168310688893ecb74194b11cb3eef9df48ce4a6bdc70e2ccdf33595f2d9a5c26` (`220460` bytes). Every build verifies its full hash and all 42 section hashes. The Markdown download preserves these public-manuscript bytes; reading views apply the four documented typographic or link-label corrections. Historical claims and cited research have not been updated or rerun.

The approved cover’s supported Library transfer remains unavailable. No substitute cover has been used. Add its exact inspected bytes to `web/assets/cooking-the-cat-cover.png` when available; `--require-cover` can enforce its presence for a later build.

GitHub Pages publishes the checked-in `docs/` directory from `main`:

- [Read the web book](https://mrscripty.github.io/Cooking-The-Cat/)
- [Download the PDF](https://mrscripty.github.io/Cooking-The-Cat/downloads/cooking-the-cat.pdf)
- [Download the Markdown](https://mrscripty.github.io/Cooking-The-Cat/downloads/cooking-the-cat.md)

The owner-provided Apache License 2.0 is preserved in `LICENSE`. References do not expand the licenses of third-party works.
