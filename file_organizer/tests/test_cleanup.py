"""Tests for file_organizer.modes.cleanup module."""

import pytest
from pathlib import Path
from unittest.mock import patch

from file_organizer.modes.cleanup import find_and_remove_unwanted
from file_organizer.config import reset_config


@pytest.fixture(autouse=True)
def reset_config_fixture() -> None:
    """Reset config before each test."""
    reset_config()


class TestFindAndRemoveUnwanted:
    """Tests for find_and_remove_unwanted function."""

    def test_find_pycache(self, tmp_path: Path) -> None:
        """Test finding __pycache__ directories."""
        source = tmp_path / "source"
        pycache = source / "project" / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "module.cpython-311.pyc").write_bytes(b"bytecode")

        # Mock user input to confirm deletion
        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False)

        assert not pycache.exists()

    def test_find_node_modules(self, tmp_path: Path) -> None:
        """Test finding node_modules directories."""
        source = tmp_path / "source"
        node_modules = source / "webapp" / "node_modules"
        node_modules.mkdir(parents=True)
        (node_modules / "express").mkdir()

        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False)

        assert not node_modules.exists()

    def test_find_venv(self, tmp_path: Path) -> None:
        """Test finding venv directories."""
        source = tmp_path / "source"
        venv = source / "project" / "venv"
        venv.mkdir(parents=True)
        (venv / "bin").mkdir()

        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False)

        assert not venv.exists()

    def test_find_pyc_files(self, tmp_path: Path) -> None:
        """Test finding .pyc files."""
        source = tmp_path / "source"
        source.mkdir()
        pyc_file = source / "module.pyc"
        pyc_file.write_bytes(b"bytecode")

        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False)

        assert not pyc_file.exists()

    def test_find_swap_files(self, tmp_path: Path) -> None:
        """Test finding swap files (.swp, .swo)."""
        source = tmp_path / "source"
        source.mkdir()
        (source / ".file.swp").write_text("")
        (source / ".file.swo").write_text("")

        # Include hidden to find these files
        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False, include_hidden=True)

        assert not (source / ".file.swp").exists()
        assert not (source / ".file.swo").exists()

    def test_find_ds_store(self, tmp_path: Path) -> None:
        """Test finding .DS_Store files."""
        source = tmp_path / "source"
        source.mkdir()
        ds_store = source / ".DS_Store"
        ds_store.write_bytes(b"\x00\x00\x00\x01Bud1")

        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False, include_hidden=True)

        assert not ds_store.exists()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry-run doesn't remove files."""
        source = tmp_path / "source"
        pycache = source / "__pycache__"
        pycache.mkdir(parents=True)

        find_and_remove_unwanted(source, dry_run=True)

        assert pycache.exists()

    def test_skip_hidden_by_default(self, tmp_path: Path) -> None:
        """Test that hidden items are skipped by default."""
        source = tmp_path / "source"
        source.mkdir()

        # Hidden pycache - will be skipped
        hidden_cache = source / ".hidden" / "__pycache__"
        hidden_cache.mkdir(parents=True)

        # Normal pycache - will be found
        normal_cache = source / "project" / "__pycache__"
        normal_cache.mkdir(parents=True)

        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False, include_hidden=False)

        assert hidden_cache.exists()  # Skipped because parent is hidden
        assert not normal_cache.exists()

    def test_skip_symlinks(self, tmp_path: Path) -> None:
        """Test that symlinks are skipped."""
        source = tmp_path / "source"
        source.mkdir()

        # Create real directory
        real_cache = tmp_path / "real_cache"
        real_cache.mkdir()

        # Create symlink to it with unwanted name
        link_cache = source / "__pycache__"
        link_cache.symlink_to(real_cache)

        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False)

        assert link_cache.is_symlink()
        assert real_cache.exists()

    def test_user_cancellation(self, tmp_path: Path) -> None:
        """Test that user can cancel removal."""
        source = tmp_path / "source"
        pycache = source / "__pycache__"
        pycache.mkdir(parents=True)

        with patch("builtins.input", return_value="no"):
            find_and_remove_unwanted(source, dry_run=False)

        assert pycache.exists()

    def test_multiple_unwanted_items(self, tmp_path: Path) -> None:
        """Test finding multiple types of unwanted items."""
        source = tmp_path / "source"

        # Create various unwanted items
        (source / "project" / "__pycache__").mkdir(parents=True)
        (source / "webapp" / "node_modules").mkdir(parents=True)
        (source / "app" / "venv").mkdir(parents=True)
        (source / "build").mkdir(parents=True)
        (source / "dist").mkdir(parents=True)

        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False)

        assert not (source / "project" / "__pycache__").exists()
        assert not (source / "webapp" / "node_modules").exists()
        assert not (source / "app" / "venv").exists()
        assert not (source / "build").exists()
        assert not (source / "dist").exists()

    def test_no_unwanted_found(self, tmp_path: Path) -> None:
        """Test handling when no unwanted items are found."""
        source = tmp_path / "source"
        (source / "project" / "src").mkdir(parents=True)
        (source / "project" / "tests").mkdir(parents=True)

        # Should not raise any errors
        find_and_remove_unwanted(source, dry_run=False)

        # Directories should still exist
        assert (source / "project" / "src").exists()
        assert (source / "project" / "tests").exists()

    def test_nested_unwanted_not_double_counted(self, tmp_path: Path) -> None:
        """Test that items inside unwanted dirs aren't separately counted."""
        source = tmp_path / "source"

        # Create nested structure
        pycache = source / "__pycache__"
        pycache.mkdir(parents=True)
        # This pyc is inside pycache, shouldn't be found separately
        (pycache / "module.pyc").write_bytes(b"bytecode")

        with patch("builtins.input", return_value="yes"):
            find_and_remove_unwanted(source, dry_run=False)

        assert not pycache.exists()
