# ocr/

This directory contains a Python script for performing Optical Character Recognition (OCR) on image and video files. It leverages the Tesseract OCR engine and OpenCV for media processing.

## Contents:

*   `main.py`: The main script for extracting text from image files and from frames of video files. It supports specifying languages and includes optional image preprocessing.

## Dependencies:

*   `pytesseract`: Python wrapper for Tesseract.
*   `opencv-python` (`cv2`): For image and video reading.
*   `pathlib`, `argparse` (standard Python libraries).

You must also install the Tesseract OCR engine itself on your system and ensure it is in your system's PATH. Install language data packs for any languages you plan to use (e.g., `tesseract-ocr-por`, `tesseract-ocr-eng`).

Install the Python dependencies:

```bash
pip install pytesseract opencv-python
```

## Usage:

```bash
python ocr/main.py <input_file> [options]
```

*   `<input_file>`: Path to the image or video file to process.

## Options:

*   `-o <output_file>`, `--output <output_file>`: Save extracted text to a file instead of printing to stdout.
*   `-l <languages>`, `--languages <languages>`: Tesseract language codes separated by `+` (default: `por+eng+lat`).
*   `-f <interval>`, `--frame-interval <interval>`: (Video only) Process only every N-th frame (default: 30).
*   `--no-preprocess`: Disable image preprocessing (grayscale, thresholding).

## Examples:

```bash
# Extract text from an image with default settings
python ocr/main.py path/to/my_image.png

# Extract text from a video using specific languages and save to file
python ocr/main.py path/to/my_video.mp4 -l eng+spa -o video_transcription.txt

# Extract text from an image without preprocessing
python ocr/main.py path/to/other_image.jpg --no-preprocess
```

Accuracy depends heavily on input quality and the installed Tesseract language data.
