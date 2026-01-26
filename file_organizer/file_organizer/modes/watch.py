"""Watch mode for real-time file organization."""

import time
from pathlib import Path
from threading import Event
from typing import Optional

from ..config import ConflictStyle, get_config
from ..logger import log_action, log_debug, log_error, log_warning
from ..utils import move_item

# Try to import watchdog
try:
    from watchdog.events import FileCreatedEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False


def is_watchdog_available() -> bool:
    """Check if watchdog is available for watch mode."""
    return WATCHDOG_AVAILABLE


if WATCHDOG_AVAILABLE:

    class OrganizeHandler(FileSystemEventHandler):
        """Handler for organizing files as they are created."""

        def __init__(
            self,
            dest: Path,
            include_hidden: bool = False,
            style: ConflictStyle = "number",
            delay: float = 1.0,
        ):
            """Initialize the handler.

            Args:
                dest: Destination directory for organized files.
                include_hidden: If True, include hidden files.
                style: Conflict resolution style.
                delay: Seconds to wait after file creation before moving.
            """
            super().__init__()
            self.dest = dest
            self.include_hidden = include_hidden
            self.style = style
            self.delay = delay
            self.config = get_config()

        def _get_target_dir(self, file_path: Path) -> Path:
            """Get the target directory for a file based on its extension.

            Args:
                file_path: Path to the file.

            Returns:
                Target directory path.
            """
            ext = file_path.suffix.lower()
            category = self.config.extension_to_dir.get(ext, self.config.unknown_dir)
            return self.dest / category

        def _should_process(self, path: Path) -> bool:
            """Check if a file should be processed.

            Args:
                path: Path to check.

            Returns:
                True if the file should be processed.
            """
            if not path.is_file():
                return False

            if path.is_symlink():
                return False

            if not self.include_hidden and path.name.startswith("."):
                return False

            # Skip temporary files
            if path.suffix in (".tmp", ".part", ".crdownload", ".download"):
                return False

            return True

        def on_created(self, event: FileCreatedEvent) -> None:
            """Handle file creation events.

            Args:
                event: The file creation event.
            """
            if event.is_directory:
                return

            file_path = Path(event.src_path)

            if not self._should_process(file_path):
                log_debug(f"Skipping: {file_path}")
                return

            # Wait for file to be fully written
            log_debug(f"New file detected: {file_path}, waiting {self.delay}s...")
            time.sleep(self.delay)

            # Verify file still exists and is complete
            if not file_path.exists():
                log_debug(f"File no longer exists: {file_path}")
                return

            # Check if file is still being written to
            try:
                initial_size = file_path.stat().st_size
                time.sleep(0.5)
                if file_path.exists() and file_path.stat().st_size != initial_size:
                    log_debug(f"File still being written: {file_path}")
                    return
            except OSError:
                return

            # Organize the file
            target_dir = self._get_target_dir(file_path)
            log_action(f"Organizing: {file_path.name} -> {target_dir}")

            if move_item(file_path, target_dir, dry_run=False, style=self.style):
                log_action(f"Moved: {file_path.name}")
            else:
                log_warning(f"Failed to move: {file_path.name}")


def watch_and_organize(
    source: Path,
    dest: Path,
    include_hidden: bool = False,
    style: ConflictStyle = "number",
    delay: float = 1.0,
    stop_event: Optional[Event] = None,
) -> None:
    """Watch a directory and organize new files in real-time.

    Args:
        source: Directory to watch for new files.
        dest: Destination directory for organized files.
        include_hidden: If True, include hidden files.
        style: Conflict resolution style.
        delay: Seconds to wait after file creation before moving.
        stop_event: Optional threading event to signal stop.
    """
    if not WATCHDOG_AVAILABLE:
        log_error("Watch mode requires the 'watchdog' package.")
        log_error("Install it with: pip install watchdog")
        return

    log_action(f"Starting watch mode on '{source}'")
    log_action(f"Files will be organized to '{dest}'")
    log_action("Press Ctrl+C to stop watching.\n")

    # Ensure destination directories exist
    config = get_config()
    target_subdirs = set(config.extension_to_dir.values())
    target_subdirs.add(config.unknown_dir)

    for subdir in target_subdirs:
        (dest / subdir).mkdir(parents=True, exist_ok=True)

    # Create event handler and observer
    handler = OrganizeHandler(dest, include_hidden, style, delay)
    observer = Observer()
    observer.schedule(handler, str(source), recursive=False)
    observer.start()

    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            time.sleep(1)
    except KeyboardInterrupt:
        log_action("\nStopping watch mode...")
    finally:
        observer.stop()
        observer.join()

    log_action("Watch mode stopped.")


def watch_cleanup(
    source: Path,
    include_hidden: bool = False,
    stop_event: Optional[Event] = None,
) -> None:
    """Watch a directory and remove unwanted files in real-time.

    Args:
        source: Directory to watch for unwanted files.
        include_hidden: If True, include hidden files/directories.
        stop_event: Optional threading event to signal stop.
    """
    if not WATCHDOG_AVAILABLE:
        log_error("Watch mode requires the 'watchdog' package.")
        log_error("Install it with: pip install watchdog")
        return

    from ..config import get_config

    config = get_config()
    patterns = config.unwanted_patterns

    class CleanupHandler(FileSystemEventHandler):
        """Handler for removing unwanted files as they are created."""

        def _is_unwanted(self, path: Path) -> bool:
            """Check if a path matches unwanted patterns."""
            for pattern in patterns:
                if pattern.search(path.name):
                    return True
            return False

        def on_created(self, event: FileCreatedEvent) -> None:
            """Handle file/directory creation events."""
            path = Path(event.src_path)

            if not include_hidden and path.name.startswith("."):
                return

            if path.is_symlink():
                return

            if self._is_unwanted(path):
                log_action(f"Removing unwanted: {path}")
                try:
                    if path.is_dir():
                        import shutil
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    log_action(f"Removed: {path.name}")
                except Exception as e:
                    log_error(f"Failed to remove {path}: {e}")

    log_action(f"Starting cleanup watch mode on '{source}'")
    log_action("Press Ctrl+C to stop watching.\n")

    handler = CleanupHandler()
    observer = Observer()
    observer.schedule(handler, str(source), recursive=True)
    observer.start()

    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            time.sleep(1)
    except KeyboardInterrupt:
        log_action("\nStopping watch mode...")
    finally:
        observer.stop()
        observer.join()

    log_action("Watch mode stopped.")
