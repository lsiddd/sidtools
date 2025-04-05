import argparse
import cv2
import pytesseract
from pathlib import Path

SUPPORTED_IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
SUPPORTED_VIDEO_EXTS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
DEFAULT_LANGUAGES = 'por+eng+lat'  # Latin script supplement

def extract_text_from_image(image_path, languages=DEFAULT_LANGUAGES, preprocessing=True):
    """Extract text from an image file with language support"""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image from {image_path}")

    if preprocessing:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    else:
        thresh = img

    # Configure Tesseract for Latin languages
    custom_config = f'--oem 3 --psm 3 -l {languages}'
    text = pytesseract.image_to_string(thresh, config=custom_config)
    return text.strip()

def extract_text_from_video(video_path, languages=DEFAULT_LANGUAGES, frame_interval=30, preprocessing=True):
    """Extract text from video file with language support"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    text_list = []
    frame_count = 0
    custom_config = f'--oem 3 --psm 3 -l {languages}'
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_count % frame_interval == 0:
            if preprocessing:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
            else:
                thresh = frame
                
            text = pytesseract.image_to_string(thresh, config=custom_config).strip()
            if text:
                text_list.append(text)
        
        frame_count += 1
    
    cap.release()
    return '\n'.join(text_list)

def main():
    parser = argparse.ArgumentParser(description='Extract text with Latin character support')
    parser.add_argument('input', type=str, help='Path to input file')
    parser.add_argument('-o', '--output', type=str, help='Output file path')
    parser.add_argument('-l', '--languages', type=str, default=DEFAULT_LANGUAGES,
                      help='Tesseract languages (e.g., eng+fra+spa)')
    parser.add_argument('-f', '--frame-interval', type=int, default=30,
                      help='Frame interval for video processing')
    parser.add_argument('--no-preprocess', action='store_false', dest='preprocess',
                      help='Disable image preprocessing')

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file {input_path} does not exist")

    ext = input_path.suffix.lower()
    result = ""

    if ext in SUPPORTED_IMAGE_EXTS:
        result = extract_text_from_image(str(input_path), args.languages, args.preprocess)
    elif ext in SUPPORTED_VIDEO_EXTS:
        result = extract_text_from_video(str(input_path), args.languages, args.frame_interval, args.preprocess)
    else:
        raise ValueError(f"Unsupported file format: {ext}")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:  # Ensure UTF-8 encoding
            f.write(result)
        print(f"Results saved to {args.output}")
    else:
        print("Extracted Text:\n" + result)

if __name__ == "__main__":
    main()
