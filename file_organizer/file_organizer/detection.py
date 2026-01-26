"""Content-based file type detection using magic bytes (MIME types)."""

from pathlib import Path
from typing import Optional

from .logger import log_debug, log_warning

# Try to import python-magic, fall back gracefully if not available
try:
    import magic

    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


# MIME type to category mapping
MIME_TO_CATEGORY: dict[str, str] = {
    # Videos
    "video/mp4": "videos",
    "video/x-matroska": "videos",
    "video/x-msvideo": "videos",
    "video/quicktime": "videos",
    "video/x-ms-wmv": "videos",
    "video/x-flv": "videos",
    "video/webm": "videos",
    "video/mpeg": "videos",
    "video/3gpp": "videos",
    # Audio
    "audio/mpeg": "audio",
    "audio/x-wav": "audio",
    "audio/flac": "audio",
    "audio/aac": "audio",
    "audio/ogg": "audio",
    "audio/x-ms-wma": "audio",
    "audio/mp4": "audio",
    "audio/opus": "audio",
    # Images
    "image/jpeg": "images",
    "image/png": "images",
    "image/gif": "images",
    "image/bmp": "images",
    "image/tiff": "images",
    "image/webp": "images",
    "image/svg+xml": "images",
    "image/heif": "images",
    "image/heic": "images",
    "image/x-icon": "images",
    # Documents
    "application/pdf": "documents/pdf",
    "application/msword": "documents/word",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "documents/word",
    "application/vnd.oasis.opendocument.text": "documents/word",
    "application/rtf": "documents/text",
    "application/vnd.ms-excel": "documents/excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "documents/excel",
    "application/vnd.oasis.opendocument.spreadsheet": "documents/excel",
    "application/vnd.ms-powerpoint": "documents/powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "documents/powerpoint",
    "application/vnd.oasis.opendocument.presentation": "documents/powerpoint",
    "text/plain": "documents/text",
    "text/markdown": "documents/text",
    "text/csv": "documents/data",
    "application/json": "documents/data",
    "application/xml": "documents/data",
    "text/xml": "documents/data",
    # Archives
    "application/zip": "archives",
    "application/x-tar": "archives",
    "application/gzip": "archives",
    "application/x-bzip2": "archives",
    "application/x-xz": "archives",
    "application/x-rar-compressed": "archives",
    "application/x-7z-compressed": "archives",
    # Code (text-based, often detected as text/plain)
    "text/x-python": "code/python",
    "text/javascript": "code/javascript",
    "application/javascript": "code/javascript",
    "text/html": "code/web",
    "text/css": "code/web",
    "text/x-java": "code/java",
    "text/x-c": "code/c_cpp",
    "text/x-c++": "code/c_cpp",
    "text/x-shellscript": "code/scripts",
    "application/x-sh": "code/scripts",
    # Databases
    "application/x-sqlite3": "databases",
    "application/sql": "databases",
    # Disk images
    "application/x-iso9660-image": "disk_images",
    # Fonts
    "font/ttf": "fonts",
    "font/otf": "fonts",
    "font/woff": "fonts",
    "font/woff2": "fonts",
    "application/vnd.ms-fontobject": "fonts",
}


def is_magic_available() -> bool:
    """Check if python-magic is available for content detection.

    Returns:
        True if python-magic is installed and functional.
    """
    return MAGIC_AVAILABLE


def detect_mime_type(file_path: Path) -> Optional[str]:
    """Detect the MIME type of a file using magic bytes.

    Args:
        file_path: Path to the file to analyze.

    Returns:
        The detected MIME type string, or None if detection fails.
    """
    if not MAGIC_AVAILABLE:
        log_debug("python-magic not available, skipping content detection")
        return None

    if not file_path.is_file():
        return None

    try:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(str(file_path))
        log_debug(f"Detected MIME type for '{file_path.name}': {mime_type}")
        return mime_type
    except Exception as e:
        log_warning(f"Failed to detect MIME type for '{file_path}': {e}")
        return None


def get_category_from_mime(mime_type: str) -> Optional[str]:
    """Get the category directory for a given MIME type.

    Args:
        mime_type: The MIME type string.

    Returns:
        The category directory path, or None if not mapped.
    """
    return MIME_TO_CATEGORY.get(mime_type)


def detect_file_category(file_path: Path, fallback_extension: bool = True) -> Optional[str]:
    """Detect the appropriate category for a file based on content.

    This function first tries content-based detection using MIME types.
    If that fails and fallback_extension is True, it falls back to
    extension-based detection.

    Args:
        file_path: Path to the file to analyze.
        fallback_extension: If True, fall back to extension-based detection.

    Returns:
        The category directory path, or None if unknown.
    """
    # Try content-based detection first
    mime_type = detect_mime_type(file_path)
    if mime_type:
        category = get_category_from_mime(mime_type)
        if category:
            return category

    # Fall back to extension-based detection if enabled
    if fallback_extension:
        from .config import get_config

        config = get_config()
        ext = file_path.suffix.lower()
        return config.extension_to_dir.get(ext)

    return None


def get_true_extension(file_path: Path) -> Optional[str]:
    """Suggest the correct extension for a file based on its content.

    Useful for detecting mislabeled files (e.g., .jpg that's actually a .png).

    Args:
        file_path: Path to the file to analyze.

    Returns:
        The suggested extension (including dot), or None if unknown.
    """
    if not MAGIC_AVAILABLE:
        return None

    mime_type = detect_mime_type(file_path)
    if not mime_type:
        return None

    # MIME type to typical extension mapping
    mime_to_ext: dict[str, str] = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/bmp": ".bmp",
        "image/tiff": ".tiff",
        "video/mp4": ".mp4",
        "video/x-matroska": ".mkv",
        "video/quicktime": ".mov",
        "video/webm": ".webm",
        "audio/mpeg": ".mp3",
        "audio/x-wav": ".wav",
        "audio/flac": ".flac",
        "audio/ogg": ".ogg",
        "application/pdf": ".pdf",
        "application/zip": ".zip",
        "application/gzip": ".gz",
        "application/x-tar": ".tar",
        "application/x-7z-compressed": ".7z",
        "application/x-rar-compressed": ".rar",
    }

    return mime_to_ext.get(mime_type)
