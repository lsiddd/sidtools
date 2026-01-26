"""Git repository organization mode."""

from pathlib import Path

from tqdm import tqdm

from ..config import ConflictStyle
from ..logger import log_action, log_error
from ..utils import move_item


def find_and_move_git(
    source: Path,
    dest: Path,
    dry_run: bool = False,
    include_hidden: bool = False,
    style: ConflictStyle = "number",
) -> None:
    """Find git repositories and move them to a 'git' subdirectory.

    Args:
        source: The source directory to scan.
        dest: The destination directory where repos will be moved to dest/git/.
        dry_run: If True, only simulate the operation.
        include_hidden: If True, include hidden directories in the search.
        style: The conflict resolution style to use.
    """
    git_target_dir = dest / "git"
    log_action(f"Scanning '{source}' for Git repositories...")

    found_repos: list[Path] = []

    def scan_for_repos(directory: Path) -> None:
        """Recursively scan for git repositories."""
        try:
            entries = list(directory.iterdir())
        except PermissionError:
            log_error(f"Permission denied accessing '{directory}'")
            return
        except Exception as e:
            log_error(f"Accessing directory '{directory}': {e}")
            return

        for entry in entries:
            if entry.is_symlink():
                log_action(f"Would skip symbolic link: {entry}", dry_run)
                continue

            if not entry.is_dir():
                continue

            if not include_hidden and entry.name.startswith("."):
                continue

            # Check if this directory is already under the target
            try:
                if git_target_dir.exists():
                    entry_resolved = entry.resolve()
                    target_resolved = git_target_dir.resolve()
                    if entry_resolved.is_relative_to(target_resolved):
                        log_action(
                            f"Would skip '{entry}': Already under target git directory.",
                            dry_run,
                        )
                        continue
            except (ValueError, OSError):
                pass

            # Check if this is a git repository
            if (entry / ".git").is_dir():
                found_repos.append(entry)
                log_action(f"Found Git repository: {entry}")
                # Don't recurse into git repos
                continue

            # Recurse into subdirectories
            scan_for_repos(entry)

    scan_for_repos(source)

    log_action(f"\nFound {len(found_repos)} Git repositories.")
    if not found_repos:
        log_action("No Git repositories found.")
        return

    log_action(f"Moving repositories to '{git_target_dir}'...")
    moved_count = 0

    for repo_path in tqdm(found_repos, desc="Moving repositories", disable=dry_run):
        if repo_path.exists():
            if move_item(repo_path, git_target_dir, dry_run, style):
                moved_count += 1
        else:
            log_error(f"Git repository path no longer exists: {repo_path}. Skipping move.")

    if dry_run:
        log_action(
            f"Git repository organization DRY RUN complete. Would move {moved_count} repositories.",
            dry_run,
        )
    else:
        log_action(f"Git repository organization complete. {moved_count} repositories moved.")
