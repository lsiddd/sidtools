"""Utility functions for file_organizer."""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from .config import ConflictStyle
from .logger import log_action, log_error, log_warning


def resolve_conflict(
    target_path: Path,
    dry_run: bool = False,
    style: ConflictStyle = "number",
) -> Path:
    """Resolve naming conflicts by appending a suffix to the base name.

    Args:
        target_path: The target path that may have a conflict.
        dry_run: If True, only simulate the operation.
        style: The style to use for conflict resolution:
               - 'number': Append a counter (e.g., file(1).txt)
               - 'timestamp': Append a timestamp (e.g., file_20231027_103000.txt)
               - 'uuid': Append a UUID (e.g., file_a1b2c3d4.txt)

    Returns:
        The resolved path that doesn't conflict with existing files.
    """
    if not target_path.exists():
        return target_path

    log_action(f"Conflict detected for '{target_path.name}'.", dry_run)

    parent = target_path.parent
    stem = target_path.stem
    suffix = target_path.suffix

    if style == "number":
        counter = 1
        new_name = f"{stem}({counter}){suffix}"
        new_path = parent / new_name
        while new_path.exists():
            counter += 1
            new_name = f"{stem}({counter}){suffix}"
            new_path = parent / new_name
        log_action(f"Resolved to '{new_name}' using number style.", dry_run)
        return new_path

    elif style == "timestamp":
        timestamp_str = datetime.now().strftime("_%Y%m%d_%H%M%S")
        new_name = f"{stem}{timestamp_str}{suffix}"
        new_path = parent / new_name
        counter = 1
        while new_path.exists():
            counter += 1
            new_name = f"{stem}{timestamp_str}({counter}){suffix}"
            new_path = parent / new_name
        log_action(f"Resolved to '{new_name}' using timestamp style.", dry_run)
        return new_path

    elif style == "uuid":
        uuid_str = uuid.uuid4().hex
        new_name = f"{stem}_{uuid_str}{suffix}"
        new_path = parent / new_name
        counter = 1
        while new_path.exists():
            counter += 1
            new_name = f"{stem}_{uuid_str}({counter}){suffix}"
            new_path = parent / new_name
        log_action(f"Resolved to '{new_name}' using UUID style.", dry_run)
        return new_path

    else:
        log_warning(f"Unknown conflict resolution style '{style}'. Falling back to 'number'.")
        return resolve_conflict(target_path, dry_run=dry_run, style="number")


def move_item(
    source_path: Path,
    target_dir: Path,
    dry_run: bool = False,
    style: ConflictStyle = "number",
) -> bool:
    """Move an item (file or directory) to a target directory.

    Args:
        source_path: The source file or directory to move.
        target_dir: The target directory to move the item into.
        dry_run: If True, only simulate the operation.
        style: The conflict resolution style to use.

    Returns:
        True if the move succeeded (or would succeed in dry-run), False otherwise.
    """
    if not source_path.exists():
        log_warning(f"Source path does not exist: {source_path}. Skipping move.")
        return False

    if source_path.is_symlink():
        log_action(f"Would skip symbolic link: {source_path}", dry_run)
        return False

    if not target_dir.is_dir():
        if dry_run:
            log_action(f"Would create target directory: {target_dir}", dry_run)
        else:
            log_action(f"Creating target directory: {target_dir}")
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                log_error(f"Creating directory {target_dir}: {e}")
                return False

    potential_target = target_dir / source_path.name
    resolved_target = resolve_conflict(potential_target, dry_run, style)

    if dry_run:
        log_action(f"Would move '{source_path}' to '{resolved_target}'", dry_run)
        return True
    else:
        try:
            log_action(f"Moving '{source_path}' to '{resolved_target}'")
            shutil.move(str(source_path), str(resolved_target))
            return True
        except PermissionError:
            log_error(f"Permission denied to move '{source_path}'. Skipping.")
            return False
        except Exception as e:
            log_error(f"Moving '{source_path}' to '{resolved_target}': {e}")
            return False


def remove_empty_dirs(directory: Path, dry_run: bool = False) -> int:
    """Remove empty directories within the specified directory (bottom-up).

    Args:
        directory: The directory to clean up.
        dry_run: If True, only simulate the operation.

    Returns:
        The number of directories removed (or that would be removed in dry-run).
    """
    log_action(f"Starting empty directory cleanup in '{directory}'...")
    removed_count = 0
    abs_directory = directory.resolve()

    def on_error(err: OSError) -> None:
        log_error(f"Accessing directory: {err}")

    # Walk bottom-up to handle nested empty directories
    for root_str, dirs, files in os.walk(str(directory), topdown=False, onerror=on_error):
        root = Path(root_str)
        if root.resolve() == abs_directory:
            continue

        try:
            if not any(root.iterdir()):
                if root.is_symlink():
                    log_action(f"Would skip removing symlink (detected as empty): {root}", dry_run)
                    continue

                if dry_run:
                    log_action(f"Would remove empty directory: {root}", dry_run)
                    removed_count += 1
                else:
                    log_action(f"Removing empty directory: {root}")
                    try:
                        root.rmdir()
                        removed_count += 1
                    except OSError as e:
                        log_error(f"Could not remove directory '{root}': {e}")
                    except PermissionError:
                        log_error(f"Permission denied to remove empty directory '{root}'.")
        except PermissionError:
            log_error(f"Permission denied to list directory '{root}' for cleanup. Skipping.")
        except Exception as e:
            log_error(f"Checking or removing directory '{root}': {e}")

    if dry_run:
        log_action(f"Empty directory cleanup complete. Would remove {removed_count} directories.", dry_run)
    else:
        log_action(f"Empty directory cleanup complete. {removed_count} directories removed.")

    return removed_count
