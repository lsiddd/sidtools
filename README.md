
# Sid's Tools & Utils

This repository aggregates a collection of distinct tools and utilities, each addressing specific tasks across various domains. Each component is housed in its own subdirectory, complete with dedicated documentation.

Explore the directories below for detailed information on each tool.

## Contents:

*   **file_organizer/**:
    A Python script designed for comprehensive filesystem management. Its capabilities include automated discovery and relocation of Git repositories, pattern-based cleanup of unwanted files and directories (like build artifacts or cache folders), and organizing files into category-specific subdirectories based on type. Key features include configurable depth limits for organization, multiple conflict resolution strategies for naming clashes during moves, and an essential dry-run mode for previewing operations safely.
    *   *Technology:* Python
    *   *For full details:* Refer to [`./file_organizer/readme.md`](./file_organizer/readme.md).

*   **expl/**:
    Contains PowerShell scripts for establishing lightweight HTTP file servers. These scripts offer functionalities such as basic directory listing, serving files, and handling download requests. Variations provide features like chunked transfers and range request support for resuming downloads.
    *   *Technology:* PowerShell
    *   *For full details:* Refer to [`./expl/readme.md`](./expl/readme.md).

*   **insta_stories_download/**:
    A set of Python scripts for programmatically downloading Instagram stories. Utilizing user cookie data for authentication, these scripts can fetch story media and associated metadata. An integrated component offers optional speech recognition capabilities for video stories, saving transcriptions alongside the media.
    *   *Technology:* Python (with `requests`, `lxml`, `pytz`, `speech_recognition`, `moviepy`)
    *   *For full details:* Refer to [`./insta_stories_download/readme.md`](./insta_stories_download/readme.md).

*   **latex_compile/**:
    A Bash script specifically engineered to streamline the compilation workflow for LaTeX documents. It manages the necessary multi-pass compilation sequence, particularly relevant for documents incorporating bibliographies processed by Biber. The script includes dependency checks and options for cleanup or automated recompilation upon file changes.
    *   *Technology:* Bash (orchestrating `pdflatex`, `biber`, `inotify-tools`, etc.)
    *   *For full details:* Refer to [`./latex_compile/readme.md`](./latex_compile/readme.md).

*   **ocr/**:
    A Python script for performing Optical Character Recognition on both image and video files. It interfaces with the Tesseract OCR engine and uses OpenCV for media handling, enabling the extraction of text from visual content. Supports configurable languages and optional image preprocessing.
    *   *Technology:* Python (with `pytesseract`, `opencv-python`)
    *   *For full details:* Refer to [`./ocr/readme.md`](./ocr/readme.md).

*   **photo_finder_cpp/**:
    A C++ application designed to recursively scan a source directory, identify image files likely originating from a camera based on the presence of specific EXIF metadata (like make or model), and copy these files to a designated output directory. The utility efficiently avoids copying files that already exist in the destination.
    *   *Technology:* C++ (with `Exiv2`, `CLI11`, `spdlog`)
    *   *For full details:* Refer to [`./photo_finder_cpp/readme.md`](./photo_finder_cpp/readme.md).

*   **sentiment_analysis/**:
    Contains a Python script leveraging a pre-trained Hugging Face transformer model for sentiment analysis. While the model is fine-tuned for Brazilian Portuguese financial text, it provides robust positive/negative/neutral classification and confidence scores for general Portuguese text. Designed for integration as a module.
    *   *Technology:* Python (with `transformers`, `torch`, `numpy`)
    *   *For full details:* Refer to [`./sentiment_analysis/readme.md`](./sentiment_analysis/readme.md).

*   **sizes_cc/**:
    A C++ program for analyzing disk space utilization within a specified directory tree. It traverses the filesystem to aggregate the total size and count for files of each distinct extension, presenting a summarized report. Features include configurable depth limits and options for sorting and displaying results.
    *   *Technology:* C++ (with `CLI11`)
    *   *For full details:* Refer to [`./sizes_cc/readme.md`](./sizes_cc/readme.md).

*   **tampermonkey_scripts/**:
    A collection of JavaScript userscripts intended for deployment via browser extensions like Tampermonkey. Each script targets specific websites to modify their behavior or add minor functionalities, such as enforcing temporary chats on ChatGPT or automating regeneration attempts on DeepSeek Chat under certain conditions.
    *   *Technology:* JavaScript
    *   *For full details:* Refer to [`./tampermonkey_scripts/readme.md`](./tampermonkey_scripts/readme.md).

*   **totp/**:
    Contains Python scripts focused on the generation of Time-based One-Time Passwords (TOTP), commonly used in two-factor authentication. Includes a standalone script that demonstrates the code generation process with step-by-step debug output, and a minimal Telegram bot implementation to provide TOTP codes on demand from a configured URI.
    *   *Technology:* Python (with standard libraries like `base64`, `hmac`, `time`, `struct`, `urllib.parse`, and `python-telegram-bot` for the bot)
    *   *For full details:* Refer to [`./totp/readme.md`](./totp/readme.md).

For detailed setup instructions, dependencies, and specific usage examples for any of these tools, consult the individual `readme.md` file located within the corresponding subdirectory.
