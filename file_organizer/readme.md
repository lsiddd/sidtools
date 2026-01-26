# file_organizer

A comprehensive Python CLI tool for organizing files and directories. It provides multiple modes for managing filesystems, including finding and moving Git repositories, removing unwanted temporary or build files, and organizing files by type into category folders.

It features conflict resolution, depth limiting, handling of hidden items, and a crucial dry-run mode for safely previewing actions.

## Installation

```bash
# Install in development mode
pip install -e .

# Or install with dev dependencies for testing
pip install -e ".[dev]"
```

## Usage

The tool provides three subcommands: `git`, `cleanup`, and `organize`.

### Git Mode

Find and move Git repositories to a centralized location.

```bash
file-organizer git --source <source_dir> --destination <dest_dir> [options]
```

Options:
- `--source, -s`: The directory to scan for git repositories. **Required.**
- `--destination, -d`: The destination directory (repos go to `DEST/git/`). **Required.**
- `--dry-run, -n`: Simulate without making changes.
- `--include-hidden, -a`: Include hidden directories in the search.
- `--conflict-resolution, -c`: Conflict resolution style (`number`, `timestamp`, `uuid`). Default: `number`.
- `--cleanup-empty-dirs`: Remove empty directories after processing.
- `--verbose, -v`: Enable verbose output.

Example:
```bash
# Dry run: See which git repos would be moved
file-organizer git -s ~/projects -d ~/organized --dry-run

# Actually move git repositories
file-organizer git -s ~/projects -d ~/organized
```

### Cleanup Mode

Remove unwanted files and directories (cache, build artifacts, etc.).

```bash
file-organizer cleanup --source <source_dir> [options]
```

Options:
- `--source, -s`: The directory to scan for unwanted items. **Required.**
- `--dry-run, -n`: Simulate without making changes.
- `--include-hidden, -a`: Include hidden files and directories.
- `--verbose, -v`: Enable verbose output.

Default patterns removed:
- Python: `__pycache__`, `.venv`, `venv`, `.pyc`, `.mypy_cache`, `.pytest_cache`
- Node.js: `node_modules`
- Build: `target`, `build`, `dist`, `.cache`
- Editor: `.swp`, `.swo`, `~` (backup files)
- OS: `Thumbs.db`, `.DS_Store`, `.Trash`

Example:
```bash
# Dry run: See what would be removed
file-organizer cleanup -s ~/projects --dry-run

# Clean up with confirmation prompt
file-organizer cleanup -s ~/projects
```

### Organize Mode

Organize files by type into categorized subdirectories.

```bash
file-organizer organize --source <source_dir> --destination <dest_dir> [options]
```

Options:
- `--source, -s`: The directory to organize. **Required.**
- `--destination, -d`: The destination directory for organized files. **Required.**
- `--max-depth, -m`: Maximum recursion depth. Directories at max depth are moved whole.
- `--dry-run, -n`: Simulate without making changes.
- `--include-hidden, -a`: Include hidden files and directories.
- `--conflict-resolution, -c`: Conflict resolution style (`number`, `timestamp`, `uuid`). Default: `number`.
- `--cleanup-empty-dirs`: Remove empty directories after processing.
- `--verbose, -v`: Enable verbose output.

File categories:
- `videos/`: mp4, mkv, avi, mov, webm, etc.
- `audio/`: mp3, wav, flac, aac, ogg, etc.
- `images/`: jpg, png, gif, bmp, webp, svg, etc.
- `documents/pdf/`, `documents/word/`, `documents/excel/`, `documents/text/`
- `archives/`: zip, tar, gz, rar, 7z, etc.
- `code/python/`, `code/javascript/`, `code/go/`, etc.
- `databases/`: sqlite, sql, db
- `fonts/`: ttf, otf, woff, woff2
- `stuff/`: Files with unknown extensions
- `directories/`: Directories at max_depth

Example:
```bash
# Dry run: Preview organization
file-organizer organize -s ~/downloads -d ~/organized --dry-run

# Organize with depth limit (subdirs at depth 2+ moved whole)
file-organizer organize -s ~/downloads -d ~/organized --max-depth 2

# Organize with timestamp conflict resolution
file-organizer organize -s ~/downloads -d ~/organized -c timestamp --cleanup-empty-dirs
```

## Configuration

The tool uses `config.yaml` for customizing extension mappings and unwanted patterns. The config file is searched in:
1. Package directory
2. Current working directory

See `config.yaml` for the full list of configurable options.

## Running as a Module

```bash
python -m file_organizer git --source ~/projects --destination ~/organized --dry-run
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_utils.py -v

# Run with coverage
pytest tests/ --cov=file_organizer
```

### Type Checking

```bash
mypy file_organizer/
```

### Linting

```bash
ruff check file_organizer/
```

## Project Structure

```
file_organizer/
├── file_organizer/
│   ├── __init__.py
│   ├── __main__.py          # Entry point for python -m
│   ├── cli.py               # Typer CLI commands
│   ├── config.py            # Configuration management
│   ├── logger.py            # Logging utilities
│   ├── utils.py             # Shared utilities
│   └── modes/
│       ├── __init__.py
│       ├── git.py           # Git mode implementation
│       ├── cleanup.py       # Cleanup mode implementation
│       └── organize.py      # Organize mode implementation
├── tests/
│   ├── __init__.py
│   ├── test_utils.py
│   ├── test_git.py
│   ├── test_cleanup.py
│   └── test_organize.py
├── config.yaml              # External configuration
├── pyproject.toml           # Project metadata and dependencies
└── readme.md
```

## Warning

Use the `--dry-run` option extensively before executing any mode without it, as this tool performs potentially irreversible move and delete operations. Ensure you have backups. Symbolic links in the source are skipped.
