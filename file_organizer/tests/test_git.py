"""Tests for file_organizer.modes.git module."""

import pytest
from pathlib import Path

from file_organizer.modes.git import find_and_move_git


class TestFindAndMoveGit:
    """Tests for find_and_move_git function."""

    def test_find_single_repo(self, tmp_path: Path) -> None:
        """Test finding and moving a single git repository."""
        # Create a fake git repo
        repo = tmp_path / "source" / "my-project"
        repo.mkdir(parents=True)
        (repo / ".git").mkdir()
        (repo / "README.md").write_text("# My Project")

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(tmp_path / "source", dest, dry_run=False)

        assert not repo.exists()
        assert (dest / "git" / "my-project").is_dir()
        assert (dest / "git" / "my-project" / ".git").is_dir()
        assert (dest / "git" / "my-project" / "README.md").exists()

    def test_find_multiple_repos(self, tmp_path: Path) -> None:
        """Test finding and moving multiple git repositories."""
        source = tmp_path / "source"

        # Create multiple fake repos
        for name in ["repo1", "repo2", "repo3"]:
            repo = source / name
            repo.mkdir(parents=True)
            (repo / ".git").mkdir()

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(source, dest, dry_run=False)

        for name in ["repo1", "repo2", "repo3"]:
            assert (dest / "git" / name).is_dir()

    def test_find_nested_repo(self, tmp_path: Path) -> None:
        """Test finding a nested git repository."""
        source = tmp_path / "source"
        nested = source / "projects" / "2024" / "my-app"
        nested.mkdir(parents=True)
        (nested / ".git").mkdir()

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(source, dest, dry_run=False)

        assert (dest / "git" / "my-app").is_dir()
        assert (dest / "git" / "my-app" / ".git").is_dir()

    def test_skip_hidden_directories(self, tmp_path: Path) -> None:
        """Test that hidden directories are skipped by default."""
        source = tmp_path / "source"

        # Create a repo in a hidden directory
        hidden_repo = source / ".hidden" / "repo"
        hidden_repo.mkdir(parents=True)
        (hidden_repo / ".git").mkdir()

        # Create a normal repo
        normal_repo = source / "normal-repo"
        normal_repo.mkdir()
        (normal_repo / ".git").mkdir()

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(source, dest, dry_run=False, include_hidden=False)

        assert (dest / "git" / "normal-repo").is_dir()
        # Hidden repo should not be moved
        assert hidden_repo.exists()

    def test_include_hidden_directories(self, tmp_path: Path) -> None:
        """Test that hidden directories are included when flag is set."""
        source = tmp_path / "source"

        # Create a repo in a hidden directory
        hidden_repo = source / ".hidden" / "repo"
        hidden_repo.mkdir(parents=True)
        (hidden_repo / ".git").mkdir()

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(source, dest, dry_run=False, include_hidden=True)

        assert (dest / "git" / "repo").is_dir()

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry-run doesn't move repositories."""
        repo = tmp_path / "source" / "my-project"
        repo.mkdir(parents=True)
        (repo / ".git").mkdir()

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(tmp_path / "source", dest, dry_run=True)

        # Repo should still be in original location
        assert repo.exists()
        assert (repo / ".git").is_dir()
        # Git dir in dest shouldn't exist
        assert not (dest / "git").exists()

    def test_skip_symlinks(self, tmp_path: Path) -> None:
        """Test that symlinked directories are skipped."""
        source = tmp_path / "source"
        source.mkdir()

        # Create a real repo
        real_repo = tmp_path / "real_repo"
        real_repo.mkdir()
        (real_repo / ".git").mkdir()

        # Create a symlink to it
        link_repo = source / "linked-repo"
        link_repo.symlink_to(real_repo)

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(source, dest, dry_run=False)

        # Symlink should still exist
        assert link_repo.is_symlink()
        # Original repo should still exist
        assert real_repo.exists()

    def test_does_not_recurse_into_git_repos(self, tmp_path: Path) -> None:
        """Test that nested repos inside git repos are not found."""
        source = tmp_path / "source"

        # Create outer repo
        outer_repo = source / "outer"
        outer_repo.mkdir(parents=True)
        (outer_repo / ".git").mkdir()

        # Create inner repo (shouldn't be found separately)
        inner_repo = outer_repo / "submodule"
        inner_repo.mkdir()
        (inner_repo / ".git").mkdir()

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(source, dest, dry_run=False)

        # Only outer should be moved
        assert (dest / "git" / "outer").is_dir()
        # Inner should be inside outer
        assert (dest / "git" / "outer" / "submodule" / ".git").is_dir()
        # Inner should not be separate
        assert not (dest / "git" / "submodule").exists()

    def test_conflict_resolution(self, tmp_path: Path) -> None:
        """Test handling of repos with the same name."""
        source = tmp_path / "source"

        # Create repos with same name in different directories
        repo1 = source / "dir1" / "project"
        repo1.mkdir(parents=True)
        (repo1 / ".git").mkdir()
        (repo1 / "file1.txt").write_text("repo1")

        repo2 = source / "dir2" / "project"
        repo2.mkdir(parents=True)
        (repo2 / ".git").mkdir()
        (repo2 / "file2.txt").write_text("repo2")

        dest = tmp_path / "dest"
        dest.mkdir()

        find_and_move_git(source, dest, dry_run=False, style="number")

        # Both should exist with conflict resolution
        assert (dest / "git" / "project").is_dir()
        assert (dest / "git" / "project(1)").is_dir()

    def test_no_repos_found(self, tmp_path: Path) -> None:
        """Test handling when no repos are found."""
        source = tmp_path / "source"
        source.mkdir()

        # Create some regular directories
        (source / "dir1").mkdir()
        (source / "dir2").mkdir()

        dest = tmp_path / "dest"
        dest.mkdir()

        # Should not raise any errors
        find_and_move_git(source, dest, dry_run=False)

        # Git directory may or may not exist depending on implementation
        # But no repos should be there
        git_dir = dest / "git"
        if git_dir.exists():
            assert not any(git_dir.iterdir())
