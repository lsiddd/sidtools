"""Cleanup mode for removing unwanted files and directories."""

import shutil
from pathlib import Path

from tqdm import tqdm

from ..config import get_config
from ..logger import log_action, log_error


def find_and_remove_unwanted(
    source: Path,
    dry_run: bool = False,
    include_hidden: bool = False,
    skip_confirm: bool = False,
) -> None:
    """Find and remove unwanted files and directories based on configured patterns.

    Args:
        source: The source directory to scan.
        dry_run: If True, only simulate the operation.
        include_hidden: If True, include hidden files/directories in the search.
        skip_confirm: If True, skip the confirmation prompt (--yes flag).
    """
    config = get_config()
    patterns = config.unwanted_patterns

    log_action(f"Scanning '{source}' for unwanted files and directories...")
    items_to_remove: list[Path] = []

    def scan_directory(directory: Path) -> None:
        """Recursively scan for unwanted items."""
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            log_error(f"Permission denied accessing '{directory}'")
            return
        except Exception as e:
            log_error(f"Accessing directory '{directory}': {e}")
            return

        dirs_to_recurse: list[Path] = []

        for entry in entries:
            if entry.is_symlink():
                log_action(f"Would skip symlink from removal scan: {entry}", dry_run)
                continue

            is_hidden = entry.name.startswith(".")
            if is_hidden and not include_hidden:
                log_action(f"Would skip hidden item from removal scan: {entry}", dry_run)
                continue

            # Check if item matches unwanted patterns
            is_unwanted = False
            for pattern in patterns:
                if pattern.search(entry.name):
                    items_to_remove.append(entry)
                    item_type = "directory" if entry.is_dir() else "file"
                    log_action(f"Found unwanted {item_type}: {entry}")
                    is_unwanted = True
                    break

            # If it's an unwanted directory, don't recurse into it
            if not is_unwanted and entry.is_dir():
                dirs_to_recurse.append(entry)

        # Recurse into non-unwanted directories
        for subdir in dirs_to_recurse:
            scan_directory(subdir)

    scan_directory(source)

    log_action(f"\nFound {len(items_to_remove)} unwanted items.")
    if not items_to_remove:
        log_action("No unwanted items found.")
        return

    # Display items to remove
    log_action("\nThe following items are marked for removal:")
    list_limit = 20
    if len(items_to_remove) > list_limit:
        log_action(f"Listing first {list_limit} of {len(items_to_remove)} items:")
        for item in items_to_remove[:list_limit]:
            log_action(str(item))
        log_action("\n...")
        log_action(f"Total items to remove: {len(items_to_remove)}")
    else:
        for item in items_to_remove:
            log_action(str(item))

    if dry_run:
        log_action("\nDRY RUN: No files or directories will be removed.", dry_run)
        log_action(
            f"Unwanted item removal DRY RUN complete. Would remove {len(items_to_remove)} items.",
            dry_run,
        )
        return

    log_action("\nWARNING: This will permanently delete these files/directories.")

    if not skip_confirm:
        confirmation = input("Proceed with removal? (yes/no): ").lower().strip()
        if confirmation != "yes":
            log_action("Removal cancelled by user.")
            return

    log_action("Starting removal...")
    removed_count = 0

    for item_path in tqdm(items_to_remove, desc="Removing items"):
        if not item_path.exists():
            log_action(
                f"Item no longer exists (possibly removed as part of a directory): {item_path}. "
                "Skipping removal."
            )
            continue

        if item_path.is_symlink():
            log_action(f"Skipping removal of symlink: {item_path}")
            continue

        try:
            if item_path.is_dir():
                log_action(f"Removing directory: {item_path}")
                shutil.rmtree(item_path)
                removed_count += 1
            else:
                log_action(f"Removing file: {item_path}")
                item_path.unlink()
                removed_count += 1
        except PermissionError:
            log_error(f"Permission denied to remove '{item_path}'. Skipping.")
        except OSError as e:
            log_error(f"Removing '{item_path}': {e}")
        except Exception as e:
            log_error(f"Unexpected error removing '{item_path}': {e}")

    log_action(f"Unwanted item removal complete. {removed_count} items removed.")
