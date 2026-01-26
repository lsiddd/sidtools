"""Tests for file_organizer.modes.organize module."""

import pytest
from pathlib import Path

from file_organizer.modes.organize import organize_by_type
from file_organizer.config import reset_config


@pytest.fixture(autouse=True)
def reset_config_fixture() -> None:
    """Reset config before each test."""
    reset_config()


class TestOrganizeByType:
    """Tests for organize_by_type function."""

    def test_organize_images(self, tmp_path: Path) -> None:
        """Test organizing image files."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "photo.jpg").write_bytes(b"jpeg data")
        (source / "graphic.png").write_bytes(b"png data")
        (source / "animation.gif").write_bytes(b"gif data")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False)

        assert (dest / "images" / "photo.jpg").exists()
        assert (dest / "images" / "graphic.png").exists()
        assert (dest / "images" / "animation.gif").exists()

    def test_organize_videos(self, tmp_path: Path) -> None:
        """Test organizing video files."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "movie.mp4").write_bytes(b"mp4 data")
        (source / "clip.mkv").write_bytes(b"mkv data")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False)

        assert (dest / "videos" / "movie.mp4").exists()
        assert (dest / "videos" / "clip.mkv").exists()

    def test_organize_documents(self, tmp_path: Path) -> None:
        """Test organizing document files."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "report.pdf").write_bytes(b"pdf data")
        (source / "notes.txt").write_text("notes content")
        (source / "spreadsheet.xlsx").write_bytes(b"xlsx data")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False)

        assert (dest / "documents" / "pdf" / "report.pdf").exists()
        assert (dest / "documents" / "text" / "notes.txt").exists()
        assert (dest / "documents" / "excel" / "spreadsheet.xlsx").exists()

    def test_organize_code_files(self, tmp_path: Path) -> None:
        """Test organizing code files."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "script.py").write_text("print('hello')")
        (source / "app.js").write_text("console.log('hello')")
        (source / "main.go").write_text("package main")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False)

        assert (dest / "code" / "python" / "script.py").exists()
        assert (dest / "code" / "javascript" / "app.js").exists()
        assert (dest / "code" / "go" / "main.go").exists()

    def test_unknown_extension(self, tmp_path: Path) -> None:
        """Test files with unknown extensions go to 'stuff' directory."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "mystery.xyz").write_text("unknown content")
        (source / "data.custom").write_bytes(b"custom data")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False)

        assert (dest / "stuff" / "mystery.xyz").exists()
        assert (dest / "stuff" / "data.custom").exists()

    def test_max_depth_zero(self, tmp_path: Path) -> None:
        """Test max_depth=0 only processes items directly in source."""
        source = tmp_path / "source"
        source.mkdir()

        # File at root level
        (source / "root.txt").write_text("root")

        # File in subdirectory
        subdir = source / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, max_depth=0, dry_run=False)

        # Root file should be organized
        assert (dest / "documents" / "text" / "root.txt").exists()
        # Subdirectory should be moved to directories
        assert (dest / "directories" / "subdir").is_dir()
        assert (dest / "directories" / "subdir" / "nested.txt").exists()

    def test_max_depth_one(self, tmp_path: Path) -> None:
        """Test max_depth=1 processes source and immediate subdirs."""
        source = tmp_path / "source"
        source.mkdir()

        # Create nested structure
        (source / "level0.txt").write_text("level0")

        level1 = source / "level1"
        level1.mkdir()
        (level1 / "file1.txt").write_text("level1")

        level2 = level1 / "level2"
        level2.mkdir()
        (level2 / "file2.txt").write_text("level2")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, max_depth=1, dry_run=False)

        # Level 0 and 1 files should be organized
        assert (dest / "documents" / "text" / "level0.txt").exists()
        assert (dest / "documents" / "text" / "file1.txt").exists()
        # Level 2 directory should be moved as a whole
        assert (dest / "directories" / "level2").is_dir()
        assert (dest / "directories" / "level2" / "file2.txt").exists()

    def test_skip_hidden_files(self, tmp_path: Path) -> None:
        """Test that hidden files are skipped by default."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "visible.txt").write_text("visible")
        (source / ".hidden.txt").write_text("hidden")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False, include_hidden=False)

        assert (dest / "documents" / "text" / "visible.txt").exists()
        assert not (dest / "documents" / "text" / ".hidden.txt").exists()
        assert (source / ".hidden.txt").exists()  # Still in source

    def test_include_hidden_files(self, tmp_path: Path) -> None:
        """Test including hidden files when flag is set."""
        source = tmp_path / "source"
        source.mkdir()

        (source / ".hidden.txt").write_text("hidden")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False, include_hidden=True)

        assert (dest / "documents" / "text" / ".hidden.txt").exists()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry-run doesn't move files."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "photo.jpg").write_bytes(b"jpeg data")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=True)

        assert (source / "photo.jpg").exists()
        # In dry run, target dirs are not created
        assert not (dest / "images").exists()

    def test_skip_symlinks(self, tmp_path: Path) -> None:
        """Test that symlinks are skipped."""
        source = tmp_path / "source"
        source.mkdir()

        real_file = tmp_path / "real.txt"
        real_file.write_text("real content")

        link_file = source / "link.txt"
        link_file.symlink_to(real_file)

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False)

        assert link_file.is_symlink()
        assert real_file.exists()

    def test_conflict_resolution(self, tmp_path: Path) -> None:
        """Test conflict resolution when organizing."""
        source = tmp_path / "source"

        # Create files with same name in different directories
        (source / "dir1").mkdir(parents=True)
        (source / "dir1" / "file.txt").write_text("content1")

        (source / "dir2").mkdir()
        (source / "dir2" / "file.txt").write_text("content2")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False, style="number")

        # Both files should exist with conflict resolution
        text_dir = dest / "documents" / "text"
        assert (text_dir / "file.txt").exists()
        assert (text_dir / "file(1).txt").exists()

    def test_source_same_as_dest_error(self, tmp_path: Path) -> None:
        """Test error when source and destination are the same."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "file.txt").write_text("content")

        # Should not raise, but should log error and return early
        organize_by_type(source, source, dry_run=False)

        # File should remain unchanged
        assert (source / "file.txt").exists()

    def test_dest_inside_source_error(self, tmp_path: Path) -> None:
        """Test error when destination is inside source."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "file.txt").write_text("content")

        dest = source / "organized"

        # Should not raise, but should log error and return early
        organize_by_type(source, dest, dry_run=False)

        # File should remain unchanged
        assert (source / "file.txt").exists()

    def test_case_insensitive_extensions(self, tmp_path: Path) -> None:
        """Test that extensions are case-insensitive."""
        source = tmp_path / "source"
        source.mkdir()

        (source / "photo.JPG").write_bytes(b"jpeg data")
        (source / "image.PNG").write_bytes(b"png data")
        (source / "mixed.JpEg").write_bytes(b"jpeg data")

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False)

        assert (dest / "images" / "photo.JPG").exists()
        assert (dest / "images" / "image.PNG").exists()
        assert (dest / "images" / "mixed.JpEg").exists()

    def test_empty_source(self, tmp_path: Path) -> None:
        """Test handling of empty source directory."""
        source = tmp_path / "source"
        source.mkdir()

        dest = tmp_path / "dest"
        dest.mkdir()

        # Should not raise any errors
        organize_by_type(source, dest, dry_run=False)

    def test_preserves_file_content(self, tmp_path: Path) -> None:
        """Test that file content is preserved after moving."""
        source = tmp_path / "source"
        source.mkdir()

        original_content = "This is the original content\nWith multiple lines"
        (source / "document.txt").write_text(original_content)

        dest = tmp_path / "dest"
        dest.mkdir()

        organize_by_type(source, dest, dry_run=False)

        moved_file = dest / "documents" / "text" / "document.txt"
        assert moved_file.read_text() == original_content
