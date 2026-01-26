"""Parallel processing utilities for file operations."""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Optional, TypeVar

from tqdm import tqdm

from .config import ConflictStyle
from .logger import log_action, log_debug, log_error
from .utils import resolve_conflict

T = TypeVar("T")


@dataclass
class MoveTask:
    """Represents a file move operation."""

    source: Path
    target_dir: Path
    style: ConflictStyle = "number"


@dataclass
class MoveResult:
    """Result of a move operation."""

    source: Path
    target: Optional[Path]
    success: bool
    error: Optional[str] = None


def get_optimal_workers(io_bound: bool = True) -> int:
    """Get the optimal number of worker threads.

    Args:
        io_bound: If True, optimize for I/O-bound tasks (more workers).
                  If False, optimize for CPU-bound tasks (fewer workers).

    Returns:
        Optimal number of workers.
    """
    cpu_count = os.cpu_count() or 4

    if io_bound:
        # For I/O-bound tasks, use more workers (limited by disk I/O)
        return min(cpu_count * 2, 16)
    else:
        # For CPU-bound tasks, use number of CPUs
        return cpu_count


def _move_file_worker(task: MoveTask) -> MoveResult:
    """Worker function to move a single file.

    Args:
        task: The move task to execute.

    Returns:
        MoveResult indicating success or failure.
    """
    try:
        if not task.source.exists():
            return MoveResult(task.source, None, False, "Source does not exist")

        if task.source.is_symlink():
            return MoveResult(task.source, None, False, "Skipping symlink")

        # Ensure target directory exists
        task.target_dir.mkdir(parents=True, exist_ok=True)

        # Resolve conflicts
        potential_target = task.target_dir / task.source.name
        resolved_target = resolve_conflict(potential_target, dry_run=False, style=task.style)

        # Perform move
        shutil.move(str(task.source), str(resolved_target))

        return MoveResult(task.source, resolved_target, True)

    except PermissionError:
        return MoveResult(task.source, None, False, "Permission denied")
    except Exception as e:
        return MoveResult(task.source, None, False, str(e))


def parallel_move_files(
    tasks: list[MoveTask],
    workers: Optional[int] = None,
    show_progress: bool = True,
    dry_run: bool = False,
) -> list[MoveResult]:
    """Move multiple files in parallel.

    Args:
        tasks: List of move tasks to execute.
        workers: Number of worker threads (auto-determined if None).
        show_progress: If True, show a progress bar.
        dry_run: If True, only simulate the operations.

    Returns:
        List of MoveResult for each task.
    """
    if not tasks:
        return []

    if dry_run:
        # In dry-run mode, just simulate the moves
        results = []
        for task in tasks:
            log_action(f"Would move '{task.source}' to '{task.target_dir}'", dry_run)
            results.append(MoveResult(task.source, task.target_dir / task.source.name, True))
        return results

    if workers is None:
        workers = get_optimal_workers(io_bound=True)

    log_debug(f"Moving {len(tasks)} files using {workers} workers")

    results: list[MoveResult] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(_move_file_worker, task): task
            for task in tasks
        }

        # Process results as they complete
        if show_progress:
            futures = tqdm(
                as_completed(future_to_task),
                total=len(tasks),
                desc="Moving files",
            )
        else:
            futures = as_completed(future_to_task)

        for future in futures:
            try:
                result = future.result()
                results.append(result)

                if result.success:
                    log_debug(f"Moved: {result.source} -> {result.target}")
                else:
                    log_error(f"Failed to move {result.source}: {result.error}")

            except Exception as e:
                task = future_to_task[future]
                results.append(MoveResult(task.source, None, False, str(e)))
                log_error(f"Unexpected error moving {task.source}: {e}")

    return results


def parallel_process(
    items: list[T],
    processor: Callable[[T], bool],
    workers: Optional[int] = None,
    show_progress: bool = True,
    desc: str = "Processing",
) -> tuple[int, int]:
    """Process items in parallel with a custom processor function.

    Args:
        items: List of items to process.
        processor: Function that processes one item, returns True on success.
        workers: Number of worker threads (auto-determined if None).
        show_progress: If True, show a progress bar.
        desc: Description for the progress bar.

    Returns:
        Tuple of (success_count, failure_count).
    """
    if not items:
        return (0, 0)

    if workers is None:
        workers = get_optimal_workers(io_bound=True)

    success_count = 0
    failure_count = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(processor, item): item for item in items}

        if show_progress:
            completed = tqdm(as_completed(futures), total=len(items), desc=desc)
        else:
            completed = as_completed(futures)

        for future in completed:
            try:
                if future.result():
                    success_count += 1
                else:
                    failure_count += 1
            except Exception:
                failure_count += 1

    return (success_count, failure_count)


def chunked_iterator(items: list[T], chunk_size: int) -> Iterator[list[T]]:
    """Yield successive chunks from a list.

    Args:
        items: List to chunk.
        chunk_size: Size of each chunk.

    Yields:
        Lists of items of the specified chunk size.
    """
    for i in range(0, len(items), chunk_size):
        yield items[i:i + chunk_size]


def parallel_hash_files(
    files: list[Path],
    workers: Optional[int] = None,
    show_progress: bool = True,
) -> dict[Path, str]:
    """Compute hashes for multiple files in parallel.

    Args:
        files: List of file paths to hash.
        workers: Number of worker threads.
        show_progress: If True, show a progress bar.

    Returns:
        Dictionary mapping file paths to their hashes.
    """
    from .modes.dedup import compute_file_hash

    if not files:
        return {}

    if workers is None:
        workers = get_optimal_workers(io_bound=True)

    results: dict[Path, str] = {}

    def hash_file(file_path: Path) -> tuple[Path, str]:
        return (file_path, compute_file_hash(file_path))

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(hash_file, f): f for f in files}

        if show_progress:
            completed = tqdm(as_completed(futures), total=len(files), desc="Hashing files")
        else:
            completed = as_completed(futures)

        for future in completed:
            try:
                path, hash_val = future.result()
                if hash_val:
                    results[path] = hash_val
            except Exception as e:
                file_path = futures[future]
                log_error(f"Failed to hash {file_path}: {e}")

    return results
