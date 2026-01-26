"""File organization modes."""

from .cleanup import find_and_remove_unwanted
from .dedup import find_and_move_duplicates, find_and_remove_duplicates
from .git import find_and_move_git
from .organize import organize_by_type
from .watch import watch_and_organize, watch_cleanup

__all__ = [
    "find_and_move_git",
    "find_and_remove_unwanted",
    "organize_by_type",
    "find_and_remove_duplicates",
    "find_and_move_duplicates",
    "watch_and_organize",
    "watch_cleanup",
]
