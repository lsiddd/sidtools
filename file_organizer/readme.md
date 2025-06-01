# file_organizer/

This directory contains a comprehensive Python script for organizing files and directories. It provides multiple modes for managing filesystems, including finding and moving Git repositories, removing unwanted temporary or build files, and organizing files by type into category folders.

It features conflict resolution, depth limiting, handling of hidden items, and a crucial dry-run mode for safely previewing actions.

## Contents:

*   `file_organizer.py`: The main script implementing the file organization and cleanup logic.

## Dependencies:

*   `os`, `shutil`, `sys`, `argparse`, `time`, `re`, `uuid`, `datetime` (standard Python libraries). No external libraries are required.

## Usage:

```bash
python file_organizer.py --source <source_dir> --mode <mode> [options]
```

*   `--source <source_dir>`: The directory to process. **Required.**
*   `--mode <mode>`: The operation mode. Must be one of `git`, `cleanup`, or `organize`. **Required.**
*   `--destination <dest_dir>`: The base destination directory for `git` and `organize` modes. Items will be moved into subdirectories within this path (e.g., `DEST/git/`, `DEST/videos/`, `DEST/documents/`). Required for these modes. (Ignored for `cleanup` mode).

## Options:

*   `--max-depth <depth>`: (Organize mode only) Limit recursion depth. Directories at or below this depth are moved whole to the `directories` category.
*   `--dry-run`: Simulate actions without moving or deleting files. **Highly recommended to use first!**
*   `--include-hidden`: Include files/dirs starting with '.' in processing.
*   `--cleanup-empty-dirs`: Remove empty directories in the source after `git` or `organize` modes.
*   `--conflict-resolution-style <style>`: How to handle naming conflicts during moves. Choices: `number` (file(1).txt), `timestamp`, `uuid`. Default: `number`.

## Examples:

```bash
# Dry run: See which git repos in 'my_projects' would move to 'organized_files/git'
python file_organizer.py --source my_projects --mode git --destination organized_files --dry-run

# Clean up unwanted files/dirs in the current directory
python file_organizer.py --source . --mode cleanup

# Dry run: Organize files in 'downloads' into 'sorted_downloads', max depth 2, including hidden
python file_organizer.py --source downloads --mode organize --destination sorted_downloads --max-depth 2 --include-hidden --dry-run

# Organize files in 'photos' into 'backed_up_photos', resolve conflicts with timestamp, cleanup empty dirs
python file_organizer.py --source photos --mode organize --destination backed_up_photos --conflict-resolution-style timestamp --cleanup-empty-dirs
```

**Warning:** Use the `--dry-run` option extensively before executing any mode without it, as this script performs potentially irreversible move and delete operations. Ensure you have backups. Symbolic links in the source are skipped.
