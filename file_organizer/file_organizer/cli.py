"""Command-line interface for file_organizer."""

from pathlib import Path
from typing import Annotated, Literal, Optional

import typer

from .config import ConflictStyle
from .logger import log_action, log_error, setup_logger
from .modes.cleanup import find_and_remove_unwanted
from .modes.dedup import KeepStrategy, find_and_move_duplicates, find_and_remove_duplicates
from .modes.git import find_and_move_git
from .modes.organize import organize_by_type
from .modes.watch import watch_and_organize
from .operations import get_latest_session, get_session, list_sessions, undo_session
from .utils import remove_empty_dirs

app = typer.Typer(
    name="file-organizer",
    help="Organize files on your hard drive using move operations.",
    add_completion=False,
)


def validate_source_dir(source: Path) -> Path:
    """Validate that the source directory exists and is a directory.

    Args:
        source: The source path to validate.

    Returns:
        The resolved absolute path.

    Raises:
        typer.Exit: If the source is invalid.
    """
    source = source.resolve()
    if not source.exists():
        log_error(f"Source directory does not exist: {source}")
        raise typer.Exit(1)
    if not source.is_dir():
        log_error(f"Source path exists but is not a directory: {source}")
        raise typer.Exit(1)
    return source


def validate_dest_dir(dest: Path, dry_run: bool) -> Path:
    """Validate and create the destination directory if needed.

    Args:
        dest: The destination path to validate.
        dry_run: If True, don't create the directory.

    Returns:
        The resolved absolute path.

    Raises:
        typer.Exit: If the destination is invalid.
    """
    dest = dest.resolve()
    if not dest.exists():
        if dry_run:
            log_action(f"Destination directory '{dest}' does not exist. Would create it.", dry_run)
        else:
            log_action(f"Destination directory '{dest}' does not exist. Creating it.")
            try:
                dest.mkdir(parents=True)
            except OSError as e:
                log_error(f"Creating destination directory '{dest}': {e}")
                raise typer.Exit(1)
    elif not dest.is_dir():
        log_error(f"Destination path exists but is not a directory: {dest}")
        raise typer.Exit(1)
    return dest


def confirm_proceed(dry_run: bool, skip_confirm: bool = False) -> bool:
    """Display warning and ask for user confirmation.

    Args:
        dry_run: If True, skip confirmation.
        skip_confirm: If True, skip the confirmation prompt (--yes flag).

    Returns:
        True if user confirms or dry_run/skip_confirm is True, False otherwise.
    """
    log_action("\nWARNING: This script moves and potentially deletes files.")
    log_action("Ensure you have backups and understand the risks before proceeding.")
    log_action("Symbolic links in the source will be skipped.")

    if dry_run or skip_confirm:
        return True

    try:
        confirmation = input("Type 'yes' to continue: ").lower().strip()
        if confirmation != "yes":
            log_action("Operation cancelled by user.")
            return False
    except (KeyboardInterrupt, EOFError):
        log_action("\nOperation cancelled.")
        return False

    return True


@app.command()
def git(
    source: Annotated[
        list[Path],
        typer.Option("--source", "-s", help="Source directory to scan (can be specified multiple times)."),
    ],
    destination: Annotated[
        Path,
        typer.Option(
            "--destination", "-d", help="The destination directory for organized repositories."
        ),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Simulate without making changes."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts (for scripting)."),
    ] = False,
    include_hidden: Annotated[
        bool,
        typer.Option("--include-hidden", "-a", help="Include hidden directories."),
    ] = False,
    conflict_resolution: Annotated[
        str,
        typer.Option(
            "--conflict-resolution",
            "-c",
            help="Conflict resolution style: number, timestamp, or uuid.",
        ),
    ] = "number",
    cleanup_empty_dirs: Annotated[
        bool,
        typer.Option("--cleanup-empty-dirs", help="Remove empty directories after processing."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output."),
    ] = False,
) -> None:
    """Find and move git repositories to destination/git/."""
    setup_logger("DEBUG" if verbose else "INFO")

    if dry_run:
        log_action("--- File Organizer: Git Mode (DRY RUN) ---", dry_run)
    else:
        log_action("--- File Organizer: Git Mode ---")

    # Validate all sources
    validated_sources = [validate_source_dir(s) for s in source]
    destination = validate_dest_dir(destination, dry_run)

    log_action(f"Sources: {', '.join(str(s) for s in validated_sources)}")
    log_action(f"Destination: {destination}")
    log_action(f"Conflict Resolution: {conflict_resolution}")
    if include_hidden:
        log_action("Including hidden directories.")
    log_action("-" * 35)

    if not confirm_proceed(dry_run, yes):
        raise typer.Exit(0)

    log_action("\nProceeding...")

    style: ConflictStyle = conflict_resolution if conflict_resolution in ("number", "timestamp", "uuid") else "number"

    # Process each source directory
    for src in validated_sources:
        log_action(f"\nProcessing source: {src}")
        find_and_move_git(src, destination, dry_run, include_hidden, style)

        if cleanup_empty_dirs:
            remove_empty_dirs(src, dry_run)

    log_action("\nScript finished.")


@app.command()
def cleanup(
    source: Annotated[
        list[Path],
        typer.Option("--source", "-s", help="Source directory to scan (can be specified multiple times)."),
    ],
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Simulate without making changes."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts (for scripting)."),
    ] = False,
    include_hidden: Annotated[
        bool,
        typer.Option("--include-hidden", "-a", help="Include hidden files and directories."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output."),
    ] = False,
) -> None:
    """Remove unwanted files and directories (cache, build artifacts, etc.)."""
    setup_logger("DEBUG" if verbose else "INFO")

    if dry_run:
        log_action("--- File Organizer: Cleanup Mode (DRY RUN) ---", dry_run)
    else:
        log_action("--- File Organizer: Cleanup Mode ---")

    # Validate all sources
    validated_sources = [validate_source_dir(s) for s in source]

    log_action(f"Sources: {', '.join(str(s) for s in validated_sources)}")
    if include_hidden:
        log_action("Including hidden files and directories.")
    log_action("-" * 35)

    if not confirm_proceed(dry_run, yes):
        raise typer.Exit(0)

    log_action("\nProceeding...")

    # Process each source directory
    for src in validated_sources:
        log_action(f"\nProcessing source: {src}")
        find_and_remove_unwanted(src, dry_run, include_hidden, yes)

    log_action("\nScript finished.")


@app.command()
def organize(
    source: Annotated[
        list[Path],
        typer.Option("--source", "-s", help="Source directory to organize (can be specified multiple times)."),
    ],
    destination: Annotated[
        Path,
        typer.Option("--destination", "-d", help="The destination directory for organized files."),
    ],
    max_depth: Annotated[
        Optional[int],
        typer.Option(
            "--max-depth",
            "-m",
            help="Maximum recursion depth. Directories at max depth are moved whole.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Simulate without making changes."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts (for scripting)."),
    ] = False,
    include_hidden: Annotated[
        bool,
        typer.Option("--include-hidden", "-a", help="Include hidden files and directories."),
    ] = False,
    conflict_resolution: Annotated[
        str,
        typer.Option(
            "--conflict-resolution",
            "-c",
            help="Conflict resolution style: number, timestamp, or uuid.",
        ),
    ] = "number",
    cleanup_empty_dirs: Annotated[
        bool,
        typer.Option("--cleanup-empty-dirs", help="Remove empty directories after processing."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output."),
    ] = False,
) -> None:
    """Organize files by type into categorized subdirectories."""
    setup_logger("DEBUG" if verbose else "INFO")

    if dry_run:
        log_action("--- File Organizer: Organize Mode (DRY RUN) ---", dry_run)
    else:
        log_action("--- File Organizer: Organize Mode ---")

    # Validate all sources
    validated_sources = [validate_source_dir(s) for s in source]
    destination = validate_dest_dir(destination, dry_run)

    log_action(f"Sources: {', '.join(str(s) for s in validated_sources)}")
    log_action(f"Destination: {destination}")
    log_action(f"Max Depth: {max_depth if max_depth is not None else 'Unlimited'}")
    log_action(f"Conflict Resolution: {conflict_resolution}")
    if include_hidden:
        log_action("Including hidden files and directories.")
    log_action("-" * 35)

    if not confirm_proceed(dry_run, yes):
        raise typer.Exit(0)

    log_action("\nProceeding...")

    style: ConflictStyle = conflict_resolution if conflict_resolution in ("number", "timestamp", "uuid") else "number"

    # Process each source directory
    for src in validated_sources:
        log_action(f"\nProcessing source: {src}")
        organize_by_type(src, destination, max_depth, dry_run, include_hidden, style)

        if cleanup_empty_dirs:
            remove_empty_dirs(src, dry_run)

    log_action("\nScript finished.")


@app.command()
def dedup(
    source: Annotated[
        list[Path],
        typer.Option("--source", "-s", help="Source directory to scan (can be specified multiple times)."),
    ],
    destination: Annotated[
        Optional[Path],
        typer.Option(
            "--destination", "-d",
            help="Move duplicates here instead of deleting (optional)."
        ),
    ] = None,
    keep: Annotated[
        str,
        typer.Option(
            "--keep", "-k",
            help="Strategy for which file to keep: oldest, newest, shortest_path, longest_path, first.",
        ),
    ] = "oldest",
    min_size: Annotated[
        int,
        typer.Option(
            "--min-size",
            help="Minimum file size in bytes to consider (default: 1).",
        ),
    ] = 1,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Simulate without making changes."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts (for scripting)."),
    ] = False,
    include_hidden: Annotated[
        bool,
        typer.Option("--include-hidden", "-a", help="Include hidden files."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output."),
    ] = False,
) -> None:
    """Find and remove duplicate files using content hashing."""
    setup_logger("DEBUG" if verbose else "INFO")

    if dry_run:
        log_action("--- File Organizer: Dedup Mode (DRY RUN) ---", dry_run)
    else:
        log_action("--- File Organizer: Dedup Mode ---")

    # Validate all sources
    validated_sources = [validate_source_dir(s) for s in source]

    log_action(f"Sources: {', '.join(str(s) for s in validated_sources)}")
    if destination:
        log_action(f"Destination for duplicates: {destination}")
    else:
        log_action("Mode: Delete duplicates")
    log_action(f"Keep strategy: {keep}")
    log_action(f"Minimum file size: {min_size} bytes")
    if include_hidden:
        log_action("Including hidden files.")
    log_action("-" * 35)

    if not confirm_proceed(dry_run, yes):
        raise typer.Exit(0)

    log_action("\nProceeding...")

    # Validate keep strategy
    valid_strategies = ("oldest", "newest", "shortest_path", "longest_path", "first")
    keep_strategy: KeepStrategy = keep if keep in valid_strategies else "oldest"

    # Process each source directory
    for src in validated_sources:
        log_action(f"\nProcessing source: {src}")
        if destination:
            dest = validate_dest_dir(destination, dry_run)
            find_and_move_duplicates(
                src, dest, dry_run, include_hidden, keep_strategy, min_size, yes
            )
        else:
            find_and_remove_duplicates(
                src, dry_run, include_hidden, keep_strategy, min_size, yes
            )

    log_action("\nScript finished.")


@app.command()
def undo(
    session_id: Annotated[
        Optional[str],
        typer.Argument(help="Session ID to undo (default: most recent)."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", "-n", help="Simulate without making changes."),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompts (for scripting)."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output."),
    ] = False,
) -> None:
    """Undo a previous operation session (restores moved files)."""
    setup_logger("DEBUG" if verbose else "INFO")

    if dry_run:
        log_action("--- File Organizer: Undo Mode (DRY RUN) ---", dry_run)
    else:
        log_action("--- File Organizer: Undo Mode ---")

    # Get the session to undo
    if session_id:
        session = get_session(session_id)
        if not session:
            log_error(f"Session not found: {session_id}")
            raise typer.Exit(1)
    else:
        session = get_latest_session()
        if not session:
            log_action("No operation sessions found to undo.")
            log_action("Run 'file-organizer history' to see available sessions.")
            raise typer.Exit(0)

    success, failed = undo_session(session, dry_run, yes)

    if not dry_run and (success > 0 or failed > 0):
        log_action("\nScript finished.")


@app.command()
def history(
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum number of sessions to show."),
    ] = 20,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show detailed operation counts."),
    ] = False,
) -> None:
    """Show history of operation sessions."""
    setup_logger("DEBUG" if verbose else "INFO")

    log_action("--- File Organizer: History ---")

    sessions = list_sessions(limit=limit)

    if not sessions:
        log_action("\nNo operation sessions found.")
        return

    log_action(f"\nRecent sessions (most recent first):\n")
    for session in sessions:
        move_count = sum(1 for op in session.operations if op.operation_type == "move")
        delete_count = sum(1 for op in session.operations if op.operation_type == "delete")

        status = "DRY RUN" if session.dry_run else f"{move_count} moves"
        if delete_count:
            status += f", {delete_count} deletes"

        log_action(f"  {session.session_id}  {session.mode:10}  {status}")
        if verbose:
            log_action(f"    Started: {session.started_at}")
            if session.completed_at:
                log_action(f"    Completed: {session.completed_at}")

    log_action(f"\nTo undo a session: file-organizer undo <session_id>")
    log_action(f"To undo the most recent: file-organizer undo")


@app.command()
def watch(
    source: Annotated[
        Path,
        typer.Option("--source", "-s", help="Directory to watch for new files."),
    ],
    destination: Annotated[
        Path,
        typer.Option("--destination", "-d", help="Destination directory for organized files."),
    ],
    include_hidden: Annotated[
        bool,
        typer.Option("--include-hidden", "-a", help="Include hidden files."),
    ] = False,
    conflict_resolution: Annotated[
        str,
        typer.Option(
            "--conflict-resolution",
            "-c",
            help="Conflict resolution style: number, timestamp, or uuid.",
        ),
    ] = "number",
    delay: Annotated[
        float,
        typer.Option(
            "--delay",
            help="Seconds to wait after file creation before moving (default: 1.0).",
        ),
    ] = 1.0,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output."),
    ] = False,
) -> None:
    """Watch a directory and organize new files in real-time."""
    setup_logger("DEBUG" if verbose else "INFO")

    log_action("--- File Organizer: Watch Mode ---")

    source = validate_source_dir(source)
    destination = validate_dest_dir(destination, dry_run=False)

    log_action(f"Watching: {source}")
    log_action(f"Destination: {destination}")
    log_action(f"Conflict Resolution: {conflict_resolution}")
    log_action(f"Delay: {delay}s")
    if include_hidden:
        log_action("Including hidden files.")
    log_action("-" * 35)

    style: ConflictStyle = conflict_resolution if conflict_resolution in ("number", "timestamp", "uuid") else "number"

    watch_and_organize(source, destination, include_hidden, style, delay)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
