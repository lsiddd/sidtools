"""Duplicate detection mode for finding and removing duplicate files."""

import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Literal

from tqdm import tqdm

from ..logger import log_action, log_error, log_warning

# Try to import xxhash for fast hashing, fall back to hashlib
try:
    import xxhash

    XXHASH_AVAILABLE = True
except ImportError:
    XXHASH_AVAILABLE = False

import hashlib

# Keep strategy options
KeepStrategy = Literal["oldest", "newest", "shortest_path", "longest_path", "first"]


def is_xxhash_available() -> bool:
    """Check if xxhash is available for fast hashing."""
    return XXHASH_AVAILABLE


def compute_file_hash(file_path: Path, use_xxhash: bool = True) -> str:
    """Compute a hash of a file's contents.

    Uses xxhash if available (much faster), otherwise falls back to SHA-256.

    Args:
        file_path: Path to the file to hash.
        use_xxhash: If True and xxhash is available, use xxhash3_64.

    Returns:
        Hex digest of the file hash.
    """
    if use_xxhash and XXHASH_AVAILABLE:
        hasher = xxhash.xxh3_64()
    else:
        hasher = hashlib.sha256()

    # Read file in chunks for memory efficiency
    chunk_size = 1024 * 1024  # 1MB chunks
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError) as e:
        log_warning(f"Could not hash file '{file_path}': {e}")
        return ""


def compute_partial_hash(file_path: Path, head_bytes: int = 8192) -> str:
    """Compute a hash of the first N bytes of a file (for quick comparison).

    Args:
        file_path: Path to the file to hash.
        head_bytes: Number of bytes to hash from the start.

    Returns:
        Hex digest of the partial hash.
    """
    if XXHASH_AVAILABLE:
        hasher = xxhash.xxh3_64()
    else:
        hasher = hashlib.sha256()

    try:
        with open(file_path, "rb") as f:
            data = f.read(head_bytes)
            hasher.update(data)
        return hasher.hexdigest()
    except (OSError, PermissionError) as e:
        log_warning(f"Could not read file '{file_path}': {e}")
        return ""


def find_duplicates(
    source: Path,
    include_hidden: bool = False,
    min_size: int = 1,
) -> dict[str, list[Path]]:
    """Find duplicate files in a directory.

    Uses a multi-stage approach for efficiency:
    1. Group files by size
    2. For files with same size, compare partial hashes
    3. For files with same partial hash, compute full hash

    Args:
        source: Directory to scan for duplicates.
        include_hidden: If True, include hidden files.
        min_size: Minimum file size in bytes to consider (default: 1).

    Returns:
        Dictionary mapping file hash to list of duplicate file paths.
    """
    log_action(f"Scanning '{source}' for duplicate files...")

    # Stage 1: Group files by size
    size_groups: dict[int, list[Path]] = defaultdict(list)
    file_count = 0

    for root, dirs, files in os.walk(source):
        root_path = Path(root)

        # Skip hidden directories if not including hidden
        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in files:
            if not include_hidden and filename.startswith("."):
                continue

            file_path = root_path / filename

            if file_path.is_symlink():
                continue

            try:
                size = file_path.stat().st_size
                if size >= min_size:
                    size_groups[size].append(file_path)
                    file_count += 1
            except (OSError, PermissionError):
                continue

    log_action(f"Found {file_count} files to analyze.")

    # Filter to only sizes with potential duplicates
    potential_dupes = {size: paths for size, paths in size_groups.items() if len(paths) > 1}
    potential_count = sum(len(paths) for paths in potential_dupes.values())
    log_action(f"Found {len(potential_dupes)} size groups with {potential_count} potential duplicates.")

    if not potential_dupes:
        return {}

    # Stage 2: Compare partial hashes for files with same size
    log_action("Computing partial hashes...")
    partial_hash_groups: dict[str, list[Path]] = defaultdict(list)

    for size, paths in tqdm(potential_dupes.items(), desc="Partial hashing"):
        for path in paths:
            partial_hash = compute_partial_hash(path)
            if partial_hash:
                key = f"{size}:{partial_hash}"
                partial_hash_groups[key].append(path)

    # Filter to only partial hashes with potential duplicates
    partial_dupes = {k: v for k, v in partial_hash_groups.items() if len(v) > 1}
    partial_count = sum(len(paths) for paths in partial_dupes.values())
    log_action(f"Found {partial_count} files with matching partial hashes.")

    if not partial_dupes:
        return {}

    # Stage 3: Compute full hashes for final verification
    log_action("Computing full file hashes...")
    full_hash_groups: dict[str, list[Path]] = defaultdict(list)

    for key, paths in tqdm(partial_dupes.items(), desc="Full hashing"):
        for path in paths:
            if not path.exists():
                continue
            full_hash = compute_file_hash(path)
            if full_hash:
                full_hash_groups[full_hash].append(path)

    # Filter to only actual duplicates
    duplicates = {h: paths for h, paths in full_hash_groups.items() if len(paths) > 1}
    dupe_count = sum(len(paths) - 1 for paths in duplicates.values())  # -1 for original
    log_action(f"Found {len(duplicates)} sets of duplicates ({dupe_count} duplicate files).")

    return duplicates


def select_file_to_keep(paths: list[Path], strategy: KeepStrategy) -> Path:
    """Select which file to keep based on the strategy.

    Args:
        paths: List of duplicate file paths.
        strategy: Strategy for selecting which file to keep.

    Returns:
        The file path to keep.
    """
    if not paths:
        raise ValueError("Cannot select from empty list")

    if strategy == "oldest":
        return min(paths, key=lambda p: p.stat().st_mtime)
    elif strategy == "newest":
        return max(paths, key=lambda p: p.stat().st_mtime)
    elif strategy == "shortest_path":
        return min(paths, key=lambda p: len(str(p)))
    elif strategy == "longest_path":
        return max(paths, key=lambda p: len(str(p)))
    else:  # "first" - keep first one found
        return paths[0]


def find_and_remove_duplicates(
    source: Path,
    dry_run: bool = False,
    include_hidden: bool = False,
    keep_strategy: KeepStrategy = "oldest",
    min_size: int = 1,
    skip_confirm: bool = False,
) -> None:
    """Find and optionally remove duplicate files.

    Args:
        source: Directory to scan for duplicates.
        dry_run: If True, only simulate the operation.
        include_hidden: If True, include hidden files.
        keep_strategy: Strategy for selecting which duplicate to keep.
        min_size: Minimum file size in bytes to consider.
        skip_confirm: If True, skip the confirmation prompt.
    """
    duplicates = find_duplicates(source, include_hidden, min_size)

    if not duplicates:
        log_action("No duplicate files found.")
        return

    # Calculate statistics
    total_sets = len(duplicates)
    total_dupes = sum(len(paths) - 1 for paths in duplicates.values())
    total_wasted = sum(
        (len(paths) - 1) * paths[0].stat().st_size
        for paths in duplicates.values()
        if paths[0].exists()
    )

    log_action(f"\nDuplicate summary:")
    log_action(f"  - {total_sets} sets of duplicates")
    log_action(f"  - {total_dupes} duplicate files")
    log_action(f"  - {total_wasted / (1024 * 1024):.2f} MB wasted space")
    log_action(f"  - Keep strategy: {keep_strategy}")

    # Show some examples
    log_action("\nExample duplicates:")
    shown = 0
    for hash_val, paths in duplicates.items():
        if shown >= 5:
            log_action("  ...")
            break
        keep = select_file_to_keep(paths, keep_strategy)
        remove = [p for p in paths if p != keep]
        log_action(f"  Keep: {keep}")
        for r in remove[:3]:  # Show up to 3 duplicates
            log_action(f"    Remove: {r}")
        if len(remove) > 3:
            log_action(f"    ... and {len(remove) - 3} more")
        shown += 1

    if dry_run:
        log_action(f"\nDRY RUN: Would remove {total_dupes} duplicate files.", dry_run)
        return

    # Confirm with user
    if not skip_confirm:
        log_action(f"\nWARNING: This will permanently delete {total_dupes} duplicate files.")
        confirmation = input("Proceed with removal? (yes/no): ").lower().strip()
        if confirmation != "yes":
            log_action("Removal cancelled by user.")
            return

    # Remove duplicates
    log_action("\nRemoving duplicates...")
    removed_count = 0
    removed_size = 0
    errors = 0

    for hash_val, paths in tqdm(duplicates.items(), desc="Removing duplicates"):
        keep = select_file_to_keep(paths, keep_strategy)
        for path in paths:
            if path == keep:
                continue

            try:
                if path.exists():
                    size = path.stat().st_size
                    path.unlink()
                    removed_count += 1
                    removed_size += size
                    log_action(f"Removed: {path}")
            except (OSError, PermissionError) as e:
                log_error(f"Failed to remove '{path}': {e}")
                errors += 1

    log_action(f"\nDuplicate removal complete:")
    log_action(f"  - Removed {removed_count} files")
    log_action(f"  - Freed {removed_size / (1024 * 1024):.2f} MB")
    if errors:
        log_action(f"  - {errors} errors occurred")


def find_and_move_duplicates(
    source: Path,
    dest: Path,
    dry_run: bool = False,
    include_hidden: bool = False,
    keep_strategy: KeepStrategy = "oldest",
    min_size: int = 1,
    skip_confirm: bool = False,
) -> None:
    """Find duplicates and move them to a separate directory instead of deleting.

    Args:
        source: Directory to scan for duplicates.
        dest: Directory to move duplicates to.
        dry_run: If True, only simulate the operation.
        include_hidden: If True, include hidden files.
        keep_strategy: Strategy for selecting which duplicate to keep.
        min_size: Minimum file size in bytes to consider.
        skip_confirm: If True, skip the confirmation prompt.
    """
    duplicates = find_duplicates(source, include_hidden, min_size)

    if not duplicates:
        log_action("No duplicate files found.")
        return

    total_dupes = sum(len(paths) - 1 for paths in duplicates.values())
    log_action(f"\nFound {total_dupes} duplicate files to move to '{dest}'.")

    if dry_run:
        log_action(f"\nDRY RUN: Would move {total_dupes} duplicate files.", dry_run)
        return

    # Confirm with user
    if not skip_confirm:
        log_action(f"\nThis will move {total_dupes} duplicate files to '{dest}'.")
        confirmation = input("Proceed? (yes/no): ").lower().strip()
        if confirmation != "yes":
            log_action("Operation cancelled by user.")
            return

    # Create destination directory
    dest.mkdir(parents=True, exist_ok=True)

    # Move duplicates
    log_action("\nMoving duplicates...")
    moved_count = 0
    errors = 0

    for hash_val, paths in tqdm(duplicates.items(), desc="Moving duplicates"):
        keep = select_file_to_keep(paths, keep_strategy)
        for path in paths:
            if path == keep:
                continue

            try:
                if path.exists():
                    # Create unique destination name
                    target = dest / path.name
                    counter = 1
                    while target.exists():
                        target = dest / f"{path.stem}({counter}){path.suffix}"
                        counter += 1

                    shutil.move(str(path), str(target))
                    moved_count += 1
                    log_action(f"Moved: {path} -> {target}")
            except (OSError, PermissionError) as e:
                log_error(f"Failed to move '{path}': {e}")
                errors += 1

    log_action(f"\nDuplicate move complete:")
    log_action(f"  - Moved {moved_count} files")
    if errors:
        log_action(f"  - {errors} errors occurred")
