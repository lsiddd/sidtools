# Multi-Tool Repository

This repository contains a collection of utilities and tools for various purposes including image processing, TOTP generation, disk analysis, social media interaction, and more.

---

## 📷 Photo Finder (C++)

**Locate and copy camera-taken images from directories.**

### Features
- Scans directories recursively
- Uses Exif metadata to detect camera-taken photos
- Multithreaded processing
- Duplicate detection

### Requirements
- C++17 compiler
- Meson build system
- libexiv2
- CLI11
- spdlog

### Build & Run
```bash
meson setup build
meson compile -C build
./build/photo_finder_cpp /path/input /path/output
```

---

## 🔑 TOTP Tools (Python)

**TOTP Generator and Telegram Bot**

### Features
- TOTP code generation from URIs
- Detailed debug output
- Telegram bot integration

### Requirements
- Python 3.8+
- `python-telegram-bot` package

### Usage
```bash
# Command-line version
python3 totp/main.py

# Telegram bot
python3 totp/lacis_code_telegram_bot.py
```

---

## 💾 Disk Analyzer (C++)

**Analyze disk usage by file extension**

### Features
- Multithreaded directory traversal
- Real-time statistics
- Multiple output formats
- Depth-limited scanning

### Build & Run
```bash
meson setup build
meson compile -C build
./build/sizes_cc /path/to/dir --depth 3 --mode both --top 10
```

---

## 🍽️ RU Menu Bot (Python)

**Telegram bot for university restaurant menu**

### Features
- Daily menu scraping
- Markdown formatting
- Error handling

### Usage
```bash
python3 bot_ru/main.py
```
_Replace API token in code before use_

---

## 📸 Instagram Stories Downloader (Python)

**Download Instagram stories with metadata**

### Features
- Story video/image download
- Speech-to-text transcription
- JSON metadata output
- Cookie-based authentication

### Requirements
- FFmpeg
- `moviepy`, `speech_recognition`, `requests`

### Usage
```bash
python3 capture.py username --cookies '{"cookie_name":"value"}'
```

---

## 📜 OCR Tool (Python)

**Text extraction from images/videos**

### Features
- Multi-language support
- Video frame extraction
- Image preprocessing
- UTF-8 output

### Usage
```bash
python3 ocr/main.py input.jpg -o output.txt
python3 ocr/main.py video.mp4 --frame-interval 30
```

---

## 🌐 Neural Translation (Python)

**English to Portuguese Translator**

### Requirements
- `transformers` package
- 1.5GB disk space for model

### Usage
```python
from translate import translate_english_to_portuguese
translation = translate_english_to_portuguese("Hello world")
```

---

## 😊 Sentiment Analysis (Python)

**Portuguese Text Sentiment Classifier**

### Features
- FinBERT-PT model
- Confidence scoring
- Three-class classification

### Usage
```python
sentiment, confidence = analisar_sentimento("Texto em português")
```

---

## ⚠️ Important Notes
1. Replace placeholder API tokens in Telegram bots
2. Install required dependencies for each tool
3. Some tools require external libraries:
   - Tesseract OCR for text extraction
   - Exiv2 for image metadata handling
4. Use Python virtual environments where applicable

