"""Organize mode for sorting files by type."""

from pathlib import Path

from tqdm import tqdm

from ..config import ConflictStyle, get_config
from ..logger import log_action, log_error
from ..utils import move_item


def organize_by_type(
    source: Path,
    dest: Path,
    max_depth: int | None = None,
    dry_run: bool = False,
    include_hidden: bool = False,
    style: ConflictStyle = "number",
) -> None:
    """Organize files by type into categorized subdirectories.

    Args:
        source: The source directory to scan.
        dest: The destination directory where organized files will be placed.
        max_depth: Maximum recursion depth. None means unlimited.
                   Depth 0 processes only items directly in source.
                   Directories at max_depth are moved to 'directories' category.
        dry_run: If True, only simulate the operation.
        include_hidden: If True, include hidden files/directories.
        style: The conflict resolution style to use.
    """
    config = get_config()
    extension_to_dir = config.extension_to_dir
    unknown_dir_name = config.unknown_dir
    directories_dir_name = config.directories_dir

    abs_source = source.resolve()
    abs_dest = dest.resolve()

    if abs_source == abs_dest:
        log_error(
            "Source and destination directories are the same. "
            "Cannot organize in place into subdirectories."
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
        pass  # dest is not relative to source, which is what we want

    # Ensure target directories exist
    target_subdirs = set(extension_to_dir.values())
    target_subdirs.add(unknown_dir_name)
    target_subdirs.add(directories_dir_name)

    log_action(f"Ensuring target directories exist under '{dest}':")
    for subdir in sorted(target_subdirs):
        full_target_subdir = dest / subdir
        if dry_run:
            log_action(f"Would ensure '{full_target_subdir}' exists.", dry_run)
        else:
            try:
                log_action(f" - {full_target_subdir}")
                full_target_subdir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                log_error(f"Creating target directory '{full_target_subdir}': {e}")
                return

    depth_info = max_depth if max_depth is not None else "Unlimited"
    log_action(
        f"\nStarting organization of '{source}' into '{dest}' (Max depth: {depth_info})...",
        dry_run,
    )

    moved_directories: set[Path] = set()

    # Collect all items to process
    items_to_process: list[tuple[Path, int, bool]] = []  # (path, depth, is_file)

    def collect_items(directory: Path, current_depth: int) -> None:
        """Recursively collect items to process."""
        if not directory.is_dir():
            if directory.resolve() not in moved_directories:
                log_error(f"'{directory}' is not a directory or was moved. Skipping traversal.")
            return

        abs_current_dir = directory.resolve()

        # Avoid traversing into the destination directory
        try:
            abs_current_dir.relative_to(abs_dest)
            log_action(
                f"Would skip traversal of '{directory}': It is within the destination tree.",
                dry_run,
            )
            return
        except ValueError:
            pass

        try:
            entries = list(directory.iterdir())
        except PermissionError:
            log_error(f"Permission denied to access '{directory}'. Skipping traversal.")
            return
        except FileNotFoundError:
            log_error(f"Directory not found during scan: '{directory}'. Skipping traversal.")
            return
        except Exception as e:
            log_error(f"Scanning directory '{directory}': {e}")
            return

        for entry in entries:
            if entry.is_symlink():
                log_action(f"Would skip symbolic link from organization: {entry}", dry_run)
                continue

            if not include_hidden and entry.name.startswith("."):
                log_action(f"Would skip hidden item from organization: {entry}", dry_run)
                continue

            # Avoid organizing items inside the destination
            abs_entry = entry.resolve()
            try:
                abs_entry.relative_to(abs_dest)
                continue
            except ValueError:
                pass

            if entry.is_file():
                items_to_process.append((entry, current_depth, True))
            elif entry.is_dir():
                if max_depth is not None and current_depth >= max_depth:
                    # At max depth, mark directory for moving as a whole
                    items_to_process.append((entry, current_depth, False))
                else:
                    # Recurse into the directory
                    collect_items(entry, current_depth + 1)

    collect_items(source, 0)

    # Process collected items
    files = [(p, d) for p, d, is_file in items_to_process if is_file]
    dirs = [(p, d) for p, d, is_file in items_to_process if not is_file]

    log_action(f"Found {len(files)} files and {len(dirs)} directories to process.")

    # Process files
    if files:
        for file_path, _ in tqdm(files, desc="Organizing files", disable=dry_run):
            if not file_path.exists():
                continue

            ext = file_path.suffix.lower()
            category_dir_name = extension_to_dir.get(ext, unknown_dir_name)
            target_category_dir = dest / category_dir_name

            try:
                move_item(file_path, target_category_dir, dry_run, style)
            except Exception as e:
                log_error(f"Processing file '{file_path}': {e}")

    # Process directories (at max depth)
    if dirs:
        target_dir = dest / directories_dir_name
        for dir_path, _ in tqdm(dirs, desc="Moving directories", disable=dry_run):
            if not dir_path.exists():
                continue

            try:
                if move_item(dir_path, target_dir, dry_run, style):
                    moved_directories.add(dir_path.resolve())
            except Exception as e:
                log_error(f"Processing directory '{dir_path}': {e}")

    if dry_run:
        log_action("File organization by type DRY RUN complete.", dry_run)
    else:
        log_action("File organization by type complete.")
