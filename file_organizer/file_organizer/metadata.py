"""Metadata extraction for images (EXIF), audio (ID3), and PDFs."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .logger import log_debug, log_warning

# Try to import optional dependencies
try:
    from PIL import Image
    from PIL.ExifTags import TAGS

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import mutagen
    from mutagen.easyid3 import EasyID3
    from mutagen.mp3 import MP3
    from mutagen.flac import FLAC
    from mutagen.oggvorbis import OggVorbis
    from mutagen.mp4 import MP4

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


@dataclass
class ImageMetadata:
    """Metadata extracted from an image file."""

    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    date_taken: Optional[datetime] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    orientation: Optional[int] = None
    raw_exif: dict[str, Any] = field(default_factory=dict)


@dataclass
class AudioMetadata:
    """Metadata extracted from an audio file."""

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    album_artist: Optional[str] = None
    track_number: Optional[int] = None
    total_tracks: Optional[int] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    duration_seconds: Optional[float] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None


@dataclass
class PdfMetadata:
    """Metadata extracted from a PDF file."""

    title: Optional[str] = None
    author: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    producer: Optional[str] = None
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    page_count: Optional[int] = None
    encrypted: bool = False


def is_pillow_available() -> bool:
    """Check if Pillow is available for image metadata extraction."""
    return PILLOW_AVAILABLE


def is_mutagen_available() -> bool:
    """Check if mutagen is available for audio metadata extraction."""
    return MUTAGEN_AVAILABLE


def is_pypdf_available() -> bool:
    """Check if pypdf is available for PDF metadata extraction."""
    return PYPDF_AVAILABLE


def _parse_exif_datetime(date_str: str) -> Optional[datetime]:
    """Parse an EXIF datetime string.

    Args:
        date_str: EXIF datetime string (format: YYYY:MM:DD HH:MM:SS).

    Returns:
        Parsed datetime or None if parsing fails.
    """
    try:
        return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def _convert_gps_to_decimal(gps_coords: tuple, gps_ref: str) -> Optional[float]:
    """Convert GPS coordinates from EXIF format to decimal degrees.

    Args:
        gps_coords: Tuple of (degrees, minutes, seconds).
        gps_ref: Reference direction (N, S, E, W).

    Returns:
        Decimal degrees or None if conversion fails.
    """
    try:
        degrees = float(gps_coords[0])
        minutes = float(gps_coords[1])
        seconds = float(gps_coords[2])
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        if gps_ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except (TypeError, ValueError, IndexError):
        return None


def extract_image_metadata(file_path: Path) -> Optional[ImageMetadata]:
    """Extract metadata from an image file.

    Args:
        file_path: Path to the image file.

    Returns:
        ImageMetadata object or None if extraction fails.
    """
    if not PILLOW_AVAILABLE:
        log_debug("Pillow not available, skipping image metadata extraction")
        return None

    if not file_path.is_file():
        return None

    try:
        with Image.open(file_path) as img:
            metadata = ImageMetadata(
                width=img.width,
                height=img.height,
                format=img.format,
            )

            # Extract EXIF data if available
            exif_data = img._getexif()
            if exif_data:
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    exif_dict[tag_name] = value

                metadata.raw_exif = exif_dict

                # Extract specific fields
                if "DateTimeOriginal" in exif_dict:
                    metadata.date_taken = _parse_exif_datetime(exif_dict["DateTimeOriginal"])
                elif "DateTime" in exif_dict:
                    metadata.date_taken = _parse_exif_datetime(exif_dict["DateTime"])

                metadata.camera_make = exif_dict.get("Make")
                metadata.camera_model = exif_dict.get("Model")
                metadata.orientation = exif_dict.get("Orientation")

                # Extract GPS coordinates
                gps_info = exif_dict.get("GPSInfo", {})
                if gps_info:
                    lat = gps_info.get(2)  # GPSLatitude
                    lat_ref = gps_info.get(1)  # GPSLatitudeRef
                    lon = gps_info.get(4)  # GPSLongitude
                    lon_ref = gps_info.get(3)  # GPSLongitudeRef

                    if lat and lat_ref:
                        metadata.gps_latitude = _convert_gps_to_decimal(lat, lat_ref)
                    if lon and lon_ref:
                        metadata.gps_longitude = _convert_gps_to_decimal(lon, lon_ref)

            log_debug(f"Extracted image metadata for '{file_path.name}'")
            return metadata

    except Exception as e:
        log_warning(f"Failed to extract image metadata from '{file_path}': {e}")
        return None


def extract_audio_metadata(file_path: Path) -> Optional[AudioMetadata]:
    """Extract metadata from an audio file.

    Supports MP3, FLAC, OGG, and M4A/MP4 audio files.

    Args:
        file_path: Path to the audio file.

    Returns:
        AudioMetadata object or None if extraction fails.
    """
    if not MUTAGEN_AVAILABLE:
        log_debug("mutagen not available, skipping audio metadata extraction")
        return None

    if not file_path.is_file():
        return None

    suffix = file_path.suffix.lower()

    try:
        metadata = AudioMetadata()

        if suffix == ".mp3":
            audio = MP3(file_path)
            metadata.duration_seconds = audio.info.length
            metadata.bitrate = audio.info.bitrate
            metadata.sample_rate = audio.info.sample_rate

            try:
                tags = EasyID3(file_path)
                metadata.title = tags.get("title", [None])[0]
                metadata.artist = tags.get("artist", [None])[0]
                metadata.album = tags.get("album", [None])[0]
                metadata.album_artist = tags.get("albumartist", [None])[0]
                metadata.genre = tags.get("genre", [None])[0]

                track = tags.get("tracknumber", [None])[0]
                if track and "/" in track:
                    parts = track.split("/")
                    metadata.track_number = int(parts[0])
                    metadata.total_tracks = int(parts[1])
                elif track:
                    metadata.track_number = int(track)

                year_str = tags.get("date", [None])[0]
                if year_str:
                    metadata.year = int(year_str[:4])
            except Exception:
                pass  # No ID3 tags

        elif suffix == ".flac":
            audio = FLAC(file_path)
            metadata.duration_seconds = audio.info.length
            metadata.bitrate = audio.info.bitrate if hasattr(audio.info, "bitrate") else None
            metadata.sample_rate = audio.info.sample_rate

            metadata.title = audio.get("title", [None])[0]
            metadata.artist = audio.get("artist", [None])[0]
            metadata.album = audio.get("album", [None])[0]
            metadata.genre = audio.get("genre", [None])[0]

        elif suffix == ".ogg":
            audio = OggVorbis(file_path)
            metadata.duration_seconds = audio.info.length
            metadata.bitrate = audio.info.bitrate
            metadata.sample_rate = audio.info.sample_rate

            metadata.title = audio.get("title", [None])[0]
            metadata.artist = audio.get("artist", [None])[0]
            metadata.album = audio.get("album", [None])[0]

        elif suffix in (".m4a", ".mp4", ".m4b"):
            audio = MP4(file_path)
            metadata.duration_seconds = audio.info.length
            metadata.bitrate = audio.info.bitrate
            metadata.sample_rate = audio.info.sample_rate

            metadata.title = audio.tags.get("\xa9nam", [None])[0] if audio.tags else None
            metadata.artist = audio.tags.get("\xa9ART", [None])[0] if audio.tags else None
            metadata.album = audio.tags.get("\xa9alb", [None])[0] if audio.tags else None

        else:
            # Try generic mutagen
            audio = mutagen.File(file_path)
            if audio and hasattr(audio, "info"):
                metadata.duration_seconds = getattr(audio.info, "length", None)
                metadata.bitrate = getattr(audio.info, "bitrate", None)
                metadata.sample_rate = getattr(audio.info, "sample_rate", None)

        log_debug(f"Extracted audio metadata for '{file_path.name}'")
        return metadata

    except Exception as e:
        log_warning(f"Failed to extract audio metadata from '{file_path}': {e}")
        return None


def _parse_pdf_date(date_str: str) -> Optional[datetime]:
    """Parse a PDF date string.

    PDF dates are typically in format: D:YYYYMMDDHHmmSS+HH'mm'

    Args:
        date_str: PDF date string.

    Returns:
        Parsed datetime or None if parsing fails.
    """
    if not date_str:
        return None

    try:
        # Remove 'D:' prefix if present
        if date_str.startswith("D:"):
            date_str = date_str[2:]

        # Basic parsing - try multiple formats
        for fmt in ["%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y%m%d", "%Y"]:
            try:
                # Remove timezone info for simplicity
                clean_date = date_str[:len(fmt.replace("%", ""))]
                return datetime.strptime(clean_date, fmt)
            except ValueError:
                continue

        return None
    except Exception:
        return None


def extract_pdf_metadata(file_path: Path) -> Optional[PdfMetadata]:
    """Extract metadata from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        PdfMetadata object or None if extraction fails.
    """
    if not PYPDF_AVAILABLE:
        log_debug("pypdf not available, skipping PDF metadata extraction")
        return None

    if not file_path.is_file():
        return None

    try:
        reader = PdfReader(file_path)
        metadata = PdfMetadata(
            page_count=len(reader.pages),
            encrypted=reader.is_encrypted,
        )

        if reader.metadata:
            metadata.title = reader.metadata.get("/Title")
            metadata.author = reader.metadata.get("/Author")
            metadata.subject = reader.metadata.get("/Subject")
            metadata.creator = reader.metadata.get("/Creator")
            metadata.producer = reader.metadata.get("/Producer")

            creation_date = reader.metadata.get("/CreationDate")
            if creation_date:
                metadata.creation_date = _parse_pdf_date(creation_date)

            mod_date = reader.metadata.get("/ModDate")
            if mod_date:
                metadata.modification_date = _parse_pdf_date(mod_date)

        log_debug(f"Extracted PDF metadata for '{file_path.name}'")
        return metadata

    except Exception as e:
        log_warning(f"Failed to extract PDF metadata from '{file_path}': {e}")
        return None


def get_file_date(file_path: Path) -> Optional[datetime]:
    """Get the most relevant date for a file from its metadata.

    For images, returns the date taken (EXIF).
    For audio, returns the year as January 1st of that year.
    For PDFs, returns the creation date.
    Falls back to file modification time.

    Args:
        file_path: Path to the file.

    Returns:
        The most relevant datetime for the file.
    """
    suffix = file_path.suffix.lower()

    # Try image metadata
    if suffix in (".jpg", ".jpeg", ".png", ".tiff", ".heic", ".heif"):
        meta = extract_image_metadata(file_path)
        if meta and meta.date_taken:
            return meta.date_taken

    # Try audio metadata
    elif suffix in (".mp3", ".flac", ".ogg", ".m4a", ".mp4"):
        meta = extract_audio_metadata(file_path)
        if meta and meta.year:
            return datetime(meta.year, 1, 1)

    # Try PDF metadata
    elif suffix == ".pdf":
        meta = extract_pdf_metadata(file_path)
        if meta and meta.creation_date:
            return meta.creation_date

    # Fall back to file modification time
    try:
        mtime = file_path.stat().st_mtime
        return datetime.fromtimestamp(mtime)
    except Exception:
        return None
