# pdf_to_md

Two `uv`-runnable scripts for converting PDF files to Markdown. They cover different tradeoffs between speed and accuracy, sharing a consistent CLI.

## Scripts

### `pdf_to_md.py` — ML-based, high accuracy

Uses [marker-pdf](https://github.com/VikParuchuri/marker), which applies deep learning models for layout analysis, reading-order detection, and OCR. Best for complex documents: multi-column layouts, tables, figures, and scanned pages with degraded quality. Requires significant RAM; GPU accelerates it considerably.

### `pdf_to_md_light.py` — fast, no ML dependencies

Uses [pymupdf4llm](https://github.com/pymupdf/RAG), which extracts text directly from the PDF's internal structure. Near-instant on native-text PDFs. OCR is applied selectively only on pages flagged as image-only. No GPU required.

## Usage

Both scripts are self-contained with inline dependency declarations and run directly via `uv run`.

### pdf_to_md.py

```bash
uv run pdf_to_md/pdf_to_md.py <file.pdf> [output.md] [options]
```

| Option | Description |
|---|---|
| `--force-ocr` | Force OCR on every page (for scanned or corrupted PDFs) |
| `--debug` | Save layout images and bounding-box JSON alongside the output |

```bash
uv run pdf_to_md/pdf_to_md.py paper.pdf
uv run pdf_to_md/pdf_to_md.py paper.pdf out/paper.md --force-ocr
uv run pdf_to_md/pdf_to_md.py paper.pdf --debug
```

### pdf_to_md_light.py

```bash
uv run pdf_to_md/pdf_to_md_light.py <file.pdf> [output.md] [options]
```

| Option | Description |
|---|---|
| `--force-ocr` | Force OCR on all pages |
| `--no-ocr` | Disable OCR entirely (image-only pages will be empty) |
| `--images` | Extract images to a folder next to the output file |
| `--embed-images` | Embed images as base64 in the Markdown |
| `--lang LANG` | Tesseract language code (default: `eng`; requires Tesseract installed) |
| `--pages N,M-P` | Process only specific pages, 0-based (e.g. `0,2-5,8`) |

```bash
uv run pdf_to_md/pdf_to_md_light.py thesis.pdf
uv run pdf_to_md/pdf_to_md_light.py scan.pdf --force-ocr --lang por
uv run pdf_to_md/pdf_to_md_light.py book.pdf --pages 0,10-20 --images
uv run pdf_to_md/pdf_to_md_light.py report.pdf out.md --embed-images
```

## Output

When no output path is given, both scripts write to `<input>.md` in the same directory. Output directories are created automatically.

## When to use which

| Situation | Script |
|---|---|
| Native-text PDF, need it fast | `pdf_to_md_light.py` |
| Scanned document, decent quality | `pdf_to_md_light.py --force-ocr` |
| Complex layout (columns, tables, figures) | `pdf_to_md.py` |
| Corrupted text layer or garbled output | `pdf_to_md.py --force-ocr` |
| Only specific pages needed | `pdf_to_md_light.py --pages ...` |
