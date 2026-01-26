"""Date-based file organization mode."""

from datetime import datetime
from pathlib import Path
from typing import Literal

from tqdm import tqdm

from ..config import ConflictStyle
from ..logger import log_action, log_error
from ..metadata import get_file_date
from ..utils import move_item

# Date format options
DateFormat = Literal["year", "year_month", "year_month_day"]


def get_date_path(date: datetime, format_style: DateFormat) -> str:
    """Get the subdirectory path based on date and format.

    Args:
        date: The datetime to format.
        format_style: How to format the date into directories.

    Returns:
        Subdirectory path string (e.g., "2024" or "2024/03" or "2024/03/15").
    """
    if format_style == "year":
        return str(date.year)
    elif format_style == "year_month":
        return f"{date.year}/{date.month:02d}"
    elif format_style == "year_month_day":
        return f"{date.year}/{date.month:02d}/{date.day:02d}"
    else:
        return str(date.year)


def organize_by_date(
    source: Path,
    dest: Path,
    date_format: DateFormat = "year_month",
    use_metadata: bool = True,
    dry_run: bool = False,
    include_hidden: bool = False,
    style: ConflictStyle = "number",
) -> None:
    """Organize files by date into year/month subdirectories.

    Args:
        source: The source directory to scan.
        dest: The destination directory where organized files will be placed.
        date_format: How to organize by date (year, year_month, year_month_day).
        use_metadata: If True, try to extract date from file metadata.
        dry_run: If True, only simulate the operation.
        include_hidden: If True, include hidden files.
        style: The conflict resolution style to use.
    """
    abs_source = source.resolve()
    abs_dest = dest.resolve()

    if abs_source == abs_dest:
        log_error(
            "Source and destination directories are the same. "
            "Cannot organize in place."
        )
        return

    # Check if destination is inside source
    try:
        abs_dest.relative_to(abs_source)
        log_error(
            f"Destination directory '{dest}' is inside source directory '{source}'. "
            "Please choose a destination outside the source tree."
        )
        return
    except ValueError:
        pass

    log_action(f"Scanning '{source}' for files to organize by date...")

    # Collect files to process
    files_to_process: list[tuple[Path, datetime]] = []

    def collect_files(directory: Path) -> None:
        """Recursively collect files with their dates."""
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            log_error(f"Permission denied to access '{directory}'")
            return
        except Exception as e:
            log_error(f"Scanning directory '{directory}': {e}")
            return

        for entry in entries:
            if entry.is_symlink():
                log_action(f"Would skip symbolic link: {entry}", dry_run)
                continue

            if not include_hidden and entry.name.startswith("."):
                continue

            # Skip items inside destination
            try:
                entry.resolve().relative_to(abs_dest)
                continue
            except ValueError:
                pass

            if entry.is_file():
                # Get file date
                if use_metadata:
                    file_date = get_file_date(entry)
                else:
                    file_date = None

                if not file_date:
                    # Fall back to modification time
                    try:
                        mtime = entry.stat().st_mtime
                        file_date = datetime.fromtimestamp(mtime)
                    except Exception:
                        file_date = datetime.now()

                files_to_process.append((entry, file_date))

            elif entry.is_dir():
                collect_files(entry)

    collect_files(source)

    log_action(f"Found {len(files_to_process)} files to organize by date.")

    if not files_to_process:
        log_action("No files to organize.")
        return

    # Create date directories and move files
    created_dirs: set[Path] = set()

    for file_path, file_date in tqdm(files_to_process, desc="Organizing by date", disable=dry_run):
        if not file_path.exists():
            continue

        # Determine target directory
        date_subdir = get_date_path(file_date, date_format)
        target_dir = dest / date_subdir

        # Create directory if needed
        if target_dir not in created_dirs:
            if dry_run:
                log_action(f"Would create directory: {target_dir}", dry_run)
            else:
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    log_error(f"Creating directory '{target_dir}': {e}")
                    continue
            created_dirs.add(target_dir)

        # Move the file
        try:
            move_item(file_path, target_dir, dry_run, style)
        except Exception as e:
            log_error(f"Processing file '{file_path}': {e}")

    if dry_run:
        log_action("Date-based organization DRY RUN complete.", dry_run)
    else:
        log_action("Date-based organization complete.")


def organize_photos_by_date(
    source: Path,
    dest: Path,
    date_format: DateFormat = "year_month",
    dry_run: bool = False,
    include_hidden: bool = False,
    style: ConflictStyle = "number",
) -> None:
    """Organize photos by date using EXIF metadata.

    Only processes image files (jpg, jpeg, png, heic, etc.).

    Args:
        source: The source directory to scan.
        dest: The destination directory for organized photos.
        date_format: How to organize by date.
        dry_run: If True, only simulate the operation.
        include_hidden: If True, include hidden files.
        style: The conflict resolution style to use.
    """
    image_extensions = {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",
        ".webp", ".heic", ".heif", ".raw", ".cr2", ".nef", ".arw"
    }

    abs_source = source.resolve()
    abs_dest = dest.resolve()

    if abs_source == abs_dest:
        log_error("Source and destination directories are the same.")
        return

    log_action(f"Scanning '{source}' for photos to organize by date...")

    # Collect image files
    photos: list[tuple[Path, datetime]] = []

    def collect_photos(directory: Path) -> None:
        """Recursively collect photo files."""
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            return

        for entry in entries:
            if entry.is_symlink():
                continue

            if not include_hidden and entry.name.startswith("."):
                continue

            try:
                entry.resolve().relative_to(abs_dest)
                continue
            except ValueError:
                pass

            if entry.is_file():
                if entry.suffix.lower() in image_extensions:
                    file_date = get_file_date(entry)
                    if not file_date:
                        try:
                            mtime = entry.stat().st_mtime
                            file_date = datetime.fromtimestamp(mtime)
                        except Exception:
                            file_date = datetime.now()
                    photos.append((entry, file_date))
            elif entry.is_dir():
                collect_photos(entry)

    collect_photos(source)

    log_action(f"Found {len(photos)} photos to organize by date.")

    if not photos:
        log_action("No photos to organize.")
        return

    # Organize photos
    created_dirs: set[Path] = set()

    for photo_path, photo_date in tqdm(photos, desc="Organizing photos", disable=dry_run):
        if not photo_path.exists():
            continue

        date_subdir = get_date_path(photo_date, date_format)
        target_dir = dest / date_subdir

        if target_dir not in created_dirs:
            if not dry_run:
                target_dir.mkdir(parents=True, exist_ok=True)
            created_dirs.add(target_dir)

        try:
            move_item(photo_path, target_dir, dry_run, style)
        except Exception as e:
            log_error(f"Processing photo '{photo_path}': {e}")

    if dry_run:
        log_action("Photo organization DRY RUN complete.", dry_run)
    else:
        log_action("Photo organization complete.")
