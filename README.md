# Sid's Tools & Utils

A collection of standalone tools and utilities, each in its own subdirectory with dedicated documentation. Ordered below from most broadly useful to most specific.

---

## file_organizer/

Python CLI for bulk filesystem operations. Three subcommands:

- **`git`** — recursively finds Git repositories under a source tree and moves them to a centralized destination, with configurable conflict resolution (`number`, `timestamp`, `uuid`).
- **`cleanup`** — removes build artifacts and cache directories (`__pycache__`, `node_modules`, `target`, `.venv`, `.DS_Store`, and more) across a directory tree.
- **`organize`** — sorts files by type into categorized subdirectories (`videos/`, `audio/`, `images/`, `documents/pdf/`, `code/python/`, etc.), respecting a configurable depth limit.

All modes support `--dry-run` for safe previewing, `--include-hidden`, `--cleanup-empty-dirs`, and `--verbose`. Installable as a package via `pyproject.toml`.

```bash
uv run file-organizer git -s ~/scattered -d ~/organized --dry-run
uv run file-organizer cleanup -s ~/projects
uv run file-organizer organize -s ~/downloads -d ~/sorted --max-depth 2
```

Technology: Python (Typer). See [`./file_organizer/readme.md`](./file_organizer/readme.md).

---

## pdf_to_md/

Two `uv`-runnable scripts for converting PDFs to Markdown, covering different tradeoffs:

**`pdf_to_md.py`** uses [marker-pdf](https://github.com/VikParuchuri/marker) — ML-based layout analysis with GPU support. Best for complex documents: multi-column layouts, mixed text/figures, scanned pages. Supports `--force-ocr` and a `--debug` mode that saves layout images and bounding-box JSON.

**`pdf_to_md_light.py`** uses [pymupdf4llm](https://github.com/pymupdf/RAG) — no GPU, no large models, near-instant on native PDFs. OCR runs selectively only on pages that need it. Supports image extraction to disk or embedded as base64, selective page ranges, and Tesseract language configuration.

```bash
uv run pdf_to_md/pdf_to_md.py paper.pdf                        # marker-pdf, full ML
uv run pdf_to_md/pdf_to_md_light.py scan.pdf --force-ocr --lang por  # pymupdf, fast
uv run pdf_to_md/pdf_to_md_light.py thesis.pdf --pages 0,5-10 --images
```

Technology: Python (uv scripts, marker-pdf / pymupdf4llm).

---

## youtube_transcripts/

Downloads a YouTube video's transcript (auto-generated or manual) from a URL or bare video ID. Resolves all URL formats: `youtu.be`, `/shorts/`, `/embed/`, `/live/`, and standard `?v=` links.

Output formats: plain text (default), SRT with timestamps, or raw JSON. Language priority falls back through `pt-BR → pt → en` by default, configurable per invocation. Output file name derived from the video ID when no explicit path is given.

```bash
uv run --with youtube-transcript-api youtube_transcripts/download_transcript.py https://youtu.be/dQw4w9WgXcQ
uv run --with youtube-transcript-api youtube_transcripts/download_transcript.py <url> -f srt -o sub.srt
uv run --with youtube-transcript-api youtube_transcripts/download_transcript.py <url> -l en -l pt
```

Technology: Python (youtube-transcript-api). See [`./youtube_transcripts/requirements.txt`](./youtube_transcripts/requirements.txt).

---

## TextSanitize/

Multi-threaded C++ CLI for converting text file encodings in-place. Handles any encoding pair supported by `iconv`, including the common case of latin1 files misidentified as UTF-8.

Key behaviors: atomic replacement via `mkstemp` + `rename(2)` (no partial writes), two strategies for unrepresentable bytes (drop the byte or remove the whole line), recursive directory processing parallelized across all CPU cores, and session resumption for interrupted directory runs.

```bash
meson setup build && meson compile -C build
build/file_cleaner ./legacy -s latin1 -t UTF-8 -r -f
build/file_cleaner document.txt -t latin1 -f --remove-invalid-lines -v
```

Technology: C++17 (Meson, iconv, mmap). See [`./TextSanitize/readme.md`](./TextSanitize/readme.md).

---

## latex_compile/

Bash script that automates the full LaTeX compilation sequence, including the `pdflatex → biber → pdflatex → pdflatex` cycle needed for Biber bibliographies. Three modes: build and open the PDF (`-b`), monitor source files and recompile on change (`-m`), and clean build artifacts (`-c`). Includes dependency checks and installation hints for apt-based systems.

```bash
./latex_compile/latex_build.sh -b                    # compile main.tex and open
./latex_compile/latex_build.sh report.tex -m         # watch mode
./latex_compile/latex_build.sh -c                    # clean build dir
```

Technology: Bash (pdflatex, biber, inotify-tools). See [`./latex_compile/readme.md`](./latex_compile/readme.md).

---

## ocr/

Python script for extracting text from image and video files via Tesseract. Handles grayscale conversion and adaptive thresholding as preprocessing, configurable language codes, and frame-interval sampling for video. Output goes to stdout or a file.

```bash
uv run ocr/main.py scan.png -l por+eng
uv run ocr/main.py lecture.mp4 -f 60 -o transcript.txt
uv run ocr/main.py image.jpg --no-preprocess
```

Technology: Python (pytesseract, opencv-python). See [`./ocr/readme.md`](./ocr/readme.md).

---

## photo_finder_cpp/

C++ utility that recursively scans a directory for image files containing camera EXIF metadata (make/model tags) and copies them to a destination directory, skipping files already present by filename. Reports progress and a summary of scanned/copied/skipped/error counts.

```bash
./photo_finder /mnt/card /home/user/photos
```

Technology: C++17 (Exiv2, CLI11, spdlog). See [`./photo_finder_cpp/readme.md`](./photo_finder_cpp/readme.md).

---

## translate/

Python module wrapping the Helsinki-NLP OPUS-MT model for English-to-Portuguese neural translation. Handles sentence splitting and batch processing internally. Intended for import rather than direct invocation.

```python
from translate import translate_english_to_portuguese
result = translate_english_to_portuguese("Hello world")
```

Technology: Python (transformers). See [`./translate/readme.md`](./translate/readme.md).

---

## totp/

Two Python scripts for TOTP (RFC 6238) code generation from an `otpauth://` URI:

- **`main.py`** — standalone script with step-by-step debug output showing the full HMAC-SHA1 derivation. Useful for understanding or auditing the algorithm.
- **`lacis_code_telegram_bot.py`** — minimal Telegram bot that returns the current TOTP code on `/code`. Requires a bot API key and the `python-telegram-bot` library.

Technology: Python (standard library + python-telegram-bot). See [`./totp/readme.md`](./totp/readme.md).

---

## sizes_cc/

C++ program that traverses a directory tree and reports total size and file count per extension, sorted by size, count, or both. Supports depth limiting and a top-N filter. Progress indicator on stderr during scan.

```bash
./sizes_cc/sizes ~/downloads --top 10 --mode both
./sizes_cc/sizes /var/log --depth 1
```

Technology: C++17 (CLI11). See [`./sizes_cc/readme.md`](./sizes_cc/readme.md).

---

## gnome/clipboard_history/

GNOME Shell extension that adds a panel indicator tracking recently copied text. Items can be re-selected from the menu (which moves them back to the top of the list). History size and polling interval are configurable via the preferences dialog. Tracks text clipboard contents only.

```sh
make -C gnome/clipboard_history install
gnome-extensions enable clipboard-history@sidtools.lucas
gnome-extensions prefs clipboard-history@sidtools.lucas
```

Technology: JavaScript (GNOME Shell API, GSettings). See [`./gnome/clipboard_history/README.md`](./gnome/clipboard_history/README.md).

---

## tampermonkey_scripts/

Two browser userscripts (Tampermonkey/Violentmonkey):

- **`tampermonkey_chatgpt_temporary.js`** — appends `temporary-chat=true` to ChatGPT URLs, forcing all sessions into temporary mode.
- **`tampermonkey_regenerate_deepseek.js`** — auto-clicks the Regenerate button on DeepSeek Chat when a server-busy error is detected.

Install by pasting each script into the Tampermonkey editor. See [`./tampermonkey_scripts/readme.md`](./tampermonkey_scripts/readme.md).

---

## sentiment_analysis/

Python module wrapping `lucas-leme/FinBERT-PT-BR` (a BERT model fine-tuned on Brazilian Portuguese financial text) for positive/negative/neutral classification with confidence scores. Designed for import; works reasonably on general Portuguese text despite the financial training domain.

```python
from sentiment_analysis.sentiment import analisar_sentimento
sentimento, confianca = analisar_sentimento("Este produto é excelente.")
```

Technology: Python (transformers, torch). See [`./sentiment_analysis/readme.md`](./sentiment_analysis/readme.md).

---

## insta_stories_download/

Python scripts for downloading Instagram stories using session cookie authentication. `capture.py` downloads stories for a given username to `./story/<username>/` and prints story metadata as JSON on stdout. `speech_recon.py` optionally transcribes audio from video stories via Google Speech Recognition.

```bash
python insta_stories_download/capture.py <username> --cookies '{"sessionid": "..."}'
```

Technology: Python (requests, lxml, moviepy, speech_recognition). See [`./insta_stories_download/readme.md`](./insta_stories_download/readme.md).

---

## expl/

PowerShell scripts for running lightweight HTTP file servers on Windows. Three variants covering basic directory listing (`dllhost.ps1`), range request support for resumable downloads (`syswinmanager.ps1`), and an enhanced version with chunked transfer (`windllhost.ps1`). All serve on port 3306 and require running as Administrator.

```powershell
.\expl\syswinmanager.ps1
# access at http://server:3306/
```

Technology: PowerShell. See [`./expl/readme.md`](./expl/readme.md).
