"""Operation logging for undo functionality and audit trails."""

import json
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from .config import get_data_dir
from .logger import log_action, log_debug, log_error, log_warning

# Operation types
OperationType = Literal["move", "delete", "create_dir"]


@dataclass
class Operation:
    """Represents a single file operation."""

    operation_type: OperationType
    source_path: str
    target_path: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert operation to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Operation":
        """Create operation from dictionary."""
        return cls(**data)


@dataclass
class OperationSession:
    """Represents a session of operations that can be undone together."""

    session_id: str
    mode: str
    started_at: str
    completed_at: Optional[str] = None
    operations: list[Operation] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> dict:
        """Convert session to dictionary."""
        return {
            "session_id": self.session_id,
            "mode": self.mode,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "dry_run": self.dry_run,
            "operations": [op.to_dict() for op in self.operations],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OperationSession":
        """Create session from dictionary."""
        operations = [Operation.from_dict(op) for op in data.get("operations", [])]
        return cls(
            session_id=data["session_id"],
            mode=data["mode"],
            started_at=data["started_at"],
            completed_at=data.get("completed_at"),
            dry_run=data.get("dry_run", False),
            operations=operations,
        )


class OperationLogger:
    """Logs file operations for undo functionality."""

    def __init__(self, mode: str, dry_run: bool = False):
        """Initialize the operation logger.

        Args:
            mode: The mode name (git, organize, cleanup, dedup).
            dry_run: If True, don't write to log file.
        """
        self.mode = mode
        self.dry_run = dry_run
        self.session = OperationSession(
            session_id=datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
            mode=mode,
            started_at=datetime.now().isoformat(),
            dry_run=dry_run,
        )
        self._log_dir = get_data_dir() / "logs"
        self._enabled = not dry_run

    def log_move(self, source: Path, target: Path, success: bool = True, error: Optional[str] = None) -> None:
        """Log a move operation.

        Args:
            source: Source path before move.
            target: Target path after move.
            success: Whether the operation succeeded.
            error: Error message if failed.
        """
        op = Operation(
            operation_type="move",
            source_path=str(source.resolve()),
            target_path=str(target.resolve()),
            success=success,
            error=error,
        )
        self.session.operations.append(op)
        log_debug(f"Logged move: {source} -> {target}")

    def log_delete(self, path: Path, success: bool = True, error: Optional[str] = None) -> None:
        """Log a delete operation.

        Args:
            path: Path that was deleted.
            success: Whether the operation succeeded.
            error: Error message if failed.
        """
        op = Operation(
            operation_type="delete",
            source_path=str(path.resolve()),
            success=success,
            error=error,
        )
        self.session.operations.append(op)
        log_debug(f"Logged delete: {path}")

    def log_create_dir(self, path: Path, success: bool = True, error: Optional[str] = None) -> None:
        """Log a directory creation operation.

        Args:
            path: Path of directory that was created.
            success: Whether the operation succeeded.
            error: Error message if failed.
        """
        op = Operation(
            operation_type="create_dir",
            source_path=str(path.resolve()),
            success=success,
            error=error,
        )
        self.session.operations.append(op)
        log_debug(f"Logged create_dir: {path}")

    def save(self) -> Optional[Path]:
        """Save the session log to disk.

        Returns:
            Path to the saved log file, or None if dry run.
        """
        if not self._enabled:
            return None

        self.session.completed_at = datetime.now().isoformat()

        # Only save if there were operations
        if not self.session.operations:
            log_debug("No operations to log")
            return None

        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            log_file = self._log_dir / f"{self.session.session_id}.json"

            with open(log_file, "w") as f:
                json.dump(self.session.to_dict(), f, indent=2)

            log_debug(f"Saved operation log to {log_file}")
            return log_file

        except Exception as e:
            log_warning(f"Failed to save operation log: {e}")
            return None


def get_log_dir() -> Path:
    """Get the operation log directory."""
    return get_data_dir() / "logs"


def list_sessions(limit: int = 20) -> list[OperationSession]:
    """List recent operation sessions.

    Args:
        limit: Maximum number of sessions to return.

    Returns:
        List of sessions, most recent first.
    """
    log_dir = get_log_dir()
    if not log_dir.exists():
        return []

    sessions = []
    log_files = sorted(log_dir.glob("*.json"), reverse=True)

    for log_file in log_files[:limit]:
        try:
            with open(log_file) as f:
                data = json.load(f)
                sessions.append(OperationSession.from_dict(data))
        except Exception as e:
            log_warning(f"Failed to read log file {log_file}: {e}")

    return sessions


def get_session(session_id: str) -> Optional[OperationSession]:
    """Get a specific operation session by ID.

    Args:
        session_id: The session ID to retrieve.

    Returns:
        The session if found, None otherwise.
    """
    log_file = get_log_dir() / f"{session_id}.json"
    if not log_file.exists():
        return None

    try:
        with open(log_file) as f:
            data = json.load(f)
            return OperationSession.from_dict(data)
    except Exception as e:
        log_error(f"Failed to read session {session_id}: {e}")
        return None


def get_latest_session() -> Optional[OperationSession]:
    """Get the most recent operation session.

    Returns:
        The most recent session, or None if no sessions exist.
    """
    sessions = list_sessions(limit=1)
    return sessions[0] if sessions else None


def undo_session(
    session: OperationSession,
    dry_run: bool = False,
    skip_confirm: bool = False,
) -> tuple[int, int]:
    """Undo all operations in a session.

    Only move operations can be undone. Delete operations cannot be reversed.

    Args:
        session: The session to undo.
        dry_run: If True, only simulate the undo.
        skip_confirm: If True, skip confirmation prompt.

    Returns:
        Tuple of (successful_undos, failed_undos).
    """
    if session.dry_run:
        log_action("Cannot undo a dry-run session (no actual operations were performed).")
        return (0, 0)

    # Filter to only reversible operations (moves)
    moves = [op for op in session.operations if op.operation_type == "move" and op.success]
    deletes = [op for op in session.operations if op.operation_type == "delete" and op.success]

    log_action(f"\nSession: {session.session_id}")
    log_action(f"Mode: {session.mode}")
    log_action(f"Started: {session.started_at}")
    log_action(f"Total operations: {len(session.operations)}")
    log_action(f"Reversible moves: {len(moves)}")
    if deletes:
        log_action(f"Irreversible deletes: {len(deletes)} (cannot be undone)")

    if not moves:
        log_action("\nNo operations to undo.")
        return (0, 0)

    if dry_run:
        log_action(f"\nDRY RUN: Would undo {len(moves)} move operations.")
        for op in moves[:10]:  # Show first 10
            log_action(f"  {op.target_path} -> {op.source_path}")
        if len(moves) > 10:
            log_action(f"  ... and {len(moves) - 10} more")
        return (len(moves), 0)

    if not skip_confirm:
        log_action(f"\nThis will undo {len(moves)} move operations.")
        confirmation = input("Proceed? (yes/no): ").lower().strip()
        if confirmation != "yes":
            log_action("Undo cancelled by user.")
            return (0, 0)

    log_action("\nUndoing operations...")
    success_count = 0
    fail_count = 0

    # Undo in reverse order
    for op in reversed(moves):
        source = Path(op.target_path)  # Current location
        target = Path(op.source_path)  # Original location

        if not source.exists():
            log_warning(f"Source no longer exists: {source}")
            fail_count += 1
            continue

        try:
            # Ensure target parent directory exists
            target.parent.mkdir(parents=True, exist_ok=True)

            # Move back to original location
            shutil.move(str(source), str(target))
            log_action(f"Restored: {target}")
            success_count += 1

        except Exception as e:
            log_error(f"Failed to restore {source} to {target}: {e}")
            fail_count += 1

    log_action(f"\nUndo complete: {success_count} restored, {fail_count} failed")
    return (success_count, fail_count)


def delete_session_log(session_id: str) -> bool:
    """Delete a session log file.

    Args:
        session_id: The session ID to delete.

    Returns:
        True if deleted, False otherwise.
    """
    log_file = get_log_dir() / f"{session_id}.json"
    if not log_file.exists():
        return False

    try:
        log_file.unlink()
        log_action(f"Deleted session log: {session_id}")
        return True
    except Exception as e:
        log_error(f"Failed to delete session log: {e}")
        return False


def cleanup_old_logs(days: int = 30) -> int:
    """Remove session logs older than specified days.

    Args:
        days: Number of days to keep logs.

    Returns:
        Number of logs deleted.
    """
    log_dir = get_log_dir()
    if not log_dir.exists():
        return 0

    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
    deleted = 0

    for log_file in log_dir.glob("*.json"):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                deleted += 1
        except Exception:
            continue

    if deleted:
        log_action(f"Cleaned up {deleted} old log files")

    return deleted
