"""Tests for file_organizer.utils module."""

import pytest
from pathlib import Path

from file_organizer.utils import resolve_conflict, move_item, remove_empty_dirs


class TestResolveConflict:
    """Tests for resolve_conflict function."""

    def test_no_conflict(self, tmp_path: Path) -> None:
        """Test when no conflict exists."""
        target = tmp_path / "test.txt"
        result = resolve_conflict(target, dry_run=True)
        assert result == target

    def test_number_style_single_conflict(self, tmp_path: Path) -> None:
        """Test number style with single existing file."""
        existing = tmp_path / "test.txt"
        existing.touch()

        result = resolve_conflict(existing, dry_run=True, style="number")
        assert result == tmp_path / "test(1).txt"

    def test_number_style_multiple_conflicts(self, tmp_path: Path) -> None:
        """Test number style with multiple existing files."""
        (tmp_path / "test.txt").touch()
        (tmp_path / "test(1).txt").touch()
        (tmp_path / "test(2).txt").touch()

        target = tmp_path / "test.txt"
        result = resolve_conflict(target, dry_run=True, style="number")
        assert result == tmp_path / "test(3).txt"

    def test_timestamp_style(self, tmp_path: Path) -> None:
        """Test timestamp style conflict resolution."""
        existing = tmp_path / "test.txt"
        existing.touch()

        result = resolve_conflict(existing, dry_run=True, style="timestamp")
        assert result.parent == tmp_path
        assert result.name.startswith("test_")
        assert result.suffix == ".txt"
        # Should contain timestamp pattern YYYYMMDD_HHMMSS
        assert len(result.stem) > len("test")

    def test_uuid_style(self, tmp_path: Path) -> None:
        """Test UUID style conflict resolution."""
        existing = tmp_path / "test.txt"
        existing.touch()

        result = resolve_conflict(existing, dry_run=True, style="uuid")
        assert result.parent == tmp_path
        assert result.name.startswith("test_")
        assert result.suffix == ".txt"
        # UUID hex is 32 characters
        assert len(result.stem) == len("test_") + 32

    def test_directory_conflict(self, tmp_path: Path) -> None:
        """Test conflict resolution for directories."""
        existing_dir = tmp_path / "mydir"
        existing_dir.mkdir()

        result = resolve_conflict(existing_dir, dry_run=True, style="number")
        assert result == tmp_path / "mydir(1)"


class TestMoveItem:
    """Tests for move_item function."""

    def test_move_file(self, tmp_path: Path) -> None:
        """Test moving a file to a new directory."""
        source_file = tmp_path / "source" / "test.txt"
        source_file.parent.mkdir()
        source_file.write_text("hello")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        result = move_item(source_file, target_dir, dry_run=False)
        assert result is True
        assert not source_file.exists()
        assert (target_dir / "test.txt").exists()
        assert (target_dir / "test.txt").read_text() == "hello"

    def test_move_file_dry_run(self, tmp_path: Path) -> None:
        """Test dry-run doesn't actually move files."""
        source_file = tmp_path / "source" / "test.txt"
        source_file.parent.mkdir()
        source_file.write_text("hello")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        result = move_item(source_file, target_dir, dry_run=True)
        assert result is True
        assert source_file.exists()  # Still exists in dry-run
        assert not (target_dir / "test.txt").exists()

    def test_move_directory(self, tmp_path: Path) -> None:
        """Test moving a directory."""
        source_dir = tmp_path / "source" / "mydir"
        source_dir.mkdir(parents=True)
        (source_dir / "file.txt").write_text("content")

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        result = move_item(source_dir, target_dir, dry_run=False)
        assert result is True
        assert not source_dir.exists()
        assert (target_dir / "mydir").is_dir()
        assert (target_dir / "mydir" / "file.txt").exists()

    def test_skip_symlink(self, tmp_path: Path) -> None:
        """Test that symlinks are skipped."""
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")

        link_file = tmp_path / "link.txt"
        link_file.symlink_to(real_file)

        target_dir = tmp_path / "target"
        target_dir.mkdir()

        result = move_item(link_file, target_dir, dry_run=False)
        assert result is False
        assert link_file.is_symlink()  # Still exists

    def test_nonexistent_source(self, tmp_path: Path) -> None:
        """Test handling of non-existent source."""
        source = tmp_path / "nonexistent.txt"
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        result = move_item(source, target_dir, dry_run=False)
        assert result is False

    def test_creates_target_directory(self, tmp_path: Path) -> None:
        """Test that target directory is created if it doesn't exist."""
        source_file = tmp_path / "test.txt"
        source_file.write_text("hello")

        target_dir = tmp_path / "new" / "nested" / "target"

        result = move_item(source_file, target_dir, dry_run=False)
        assert result is True
        assert target_dir.is_dir()
        assert (target_dir / "test.txt").exists()

    def test_conflict_resolution(self, tmp_path: Path) -> None:
        """Test that conflicts are resolved when moving."""
        source_file = tmp_path / "source" / "test.txt"
        source_file.parent.mkdir()
        source_file.write_text("new content")

        target_dir = tmp_path / "target"
        target_dir.mkdir()
        (target_dir / "test.txt").write_text("existing content")

        result = move_item(source_file, target_dir, dry_run=False, style="number")
        assert result is True
        assert (target_dir / "test.txt").read_text() == "existing content"
        assert (target_dir / "test(1).txt").read_text() == "new content"


class TestRemoveEmptyDirs:
    """Tests for remove_empty_dirs function."""

    def test_remove_single_empty_dir(self, tmp_path: Path) -> None:
        """Test removing a single empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        count = remove_empty_dirs(tmp_path, dry_run=False)
        assert count == 1
        assert not empty_dir.exists()

    def test_remove_nested_empty_dirs(self, tmp_path: Path) -> None:
        """Test removing nested empty directories."""
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        count = remove_empty_dirs(tmp_path, dry_run=False)
        assert count == 3
        assert not (tmp_path / "a").exists()

    def test_preserve_nonempty_dirs(self, tmp_path: Path) -> None:
        """Test that non-empty directories are preserved."""
        nonempty = tmp_path / "nonempty"
        nonempty.mkdir()
        (nonempty / "file.txt").write_text("content")

        count = remove_empty_dirs(tmp_path, dry_run=False)
        assert count == 0
        assert nonempty.exists()
        assert (nonempty / "file.txt").exists()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry-run doesn't remove directories."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        count = remove_empty_dirs(tmp_path, dry_run=True)
        assert count == 1  # Would have removed 1
        assert empty_dir.exists()  # But still exists

    def test_mixed_empty_and_nonempty(self, tmp_path: Path) -> None:
        """Test with mix of empty and non-empty directories."""
        empty1 = tmp_path / "empty1"
        empty1.mkdir()

        nonempty = tmp_path / "nonempty"
        nonempty.mkdir()
        (nonempty / "file.txt").write_text("content")

        empty2 = tmp_path / "empty2"
        empty2.mkdir()

        count = remove_empty_dirs(tmp_path, dry_run=False)
        assert count == 2
        assert not empty1.exists()
        assert not empty2.exists()
        assert nonempty.exists()
