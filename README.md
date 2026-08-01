# FlashPDF Reader

FlashPDF Reader restores audio interactions in educational PDFs that were originally built
around Adobe Flash RichMedia annotations. It never executes Flash or modifies the source PDF:
it extracts the embedded audio and will map the document's speaker annotations to native
playback.

## Development

Install the project and its development tools:

```bash
python -m pip install -e ".[dev]"
```

Extract the embedded audio from a book:

```bash
python -m flashpdf.asset_extractor "Lesson 1-3.pdf"
```

Assets are written to `cache/` next to the PDF by default. Existing identical files are reused.

Run the reader (it automatically opens `Lesson 1-3.pdf` when launched from this project
directory):

```bash
python -m flashpdf.app
```

Use the toolbar to open another PDF, navigate pages, zoom, and control playback. Blue speaker
overlays trigger the corresponding embedded audio through the operating system's native audio
backend—Flash is never run.
