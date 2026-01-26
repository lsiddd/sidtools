"""Custom rules engine for flexible file organization."""

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Optional

import yaml

from .config import get_config_dir
from .detection import detect_mime_type, get_category_from_mime
from .logger import log_action, log_debug, log_error, log_warning
from .metadata import get_file_date

# Condition types
ConditionType = Literal[
    "extension",      # Match file extension
    "name_pattern",   # Match filename with glob pattern
    "name_regex",     # Match filename with regex
    "mime_type",      # Match MIME type
    "size_gt",        # Size greater than (bytes)
    "size_lt",        # Size less than (bytes)
    "path_contains",  # Path contains string
    "date_before",    # File date before
    "date_after",     # File date after
]

# Action types
ActionType = Literal[
    "move_to",        # Move to specific directory
    "skip",           # Skip this file
    "delete",         # Delete the file
    "rename",         # Rename the file
]


@dataclass
class Condition:
    """A condition that can be evaluated against a file."""

    condition_type: ConditionType
    value: Any
    negate: bool = False

    def evaluate(self, file_path: Path) -> bool:
        """Evaluate the condition against a file.

        Args:
            file_path: Path to the file to evaluate.

        Returns:
            True if condition matches, False otherwise.
        """
        result = self._evaluate_impl(file_path)
        return not result if self.negate else result

    def _evaluate_impl(self, file_path: Path) -> bool:
        """Implementation of condition evaluation."""
        try:
            if self.condition_type == "extension":
                # Match extension (case-insensitive)
                extensions = self.value if isinstance(self.value, list) else [self.value]
                ext = file_path.suffix.lower()
                return any(ext == e.lower() if e.startswith(".") else ext == f".{e.lower()}"
                          for e in extensions)

            elif self.condition_type == "name_pattern":
                # Match filename with glob pattern
                return fnmatch.fnmatch(file_path.name.lower(), self.value.lower())

            elif self.condition_type == "name_regex":
                # Match filename with regex
                pattern = re.compile(self.value, re.IGNORECASE)
                return bool(pattern.search(file_path.name))

            elif self.condition_type == "mime_type":
                # Match MIME type
                mime = detect_mime_type(file_path)
                if not mime:
                    return False
                mime_patterns = self.value if isinstance(self.value, list) else [self.value]
                return any(fnmatch.fnmatch(mime, p) for p in mime_patterns)

            elif self.condition_type == "size_gt":
                # Size greater than (in bytes, supports K/M/G suffixes)
                threshold = self._parse_size(self.value)
                return file_path.stat().st_size > threshold

            elif self.condition_type == "size_lt":
                # Size less than
                threshold = self._parse_size(self.value)
                return file_path.stat().st_size < threshold

            elif self.condition_type == "path_contains":
                # Path contains string
                return self.value.lower() in str(file_path).lower()

            elif self.condition_type == "date_before":
                # File date before specified date
                from datetime import datetime
                file_date = get_file_date(file_path)
                if not file_date:
                    return False
                target_date = datetime.fromisoformat(self.value)
                return file_date < target_date

            elif self.condition_type == "date_after":
                # File date after specified date
                from datetime import datetime
                file_date = get_file_date(file_path)
                if not file_date:
                    return False
                target_date = datetime.fromisoformat(self.value)
                return file_date > target_date

            return False

        except Exception as e:
            log_debug(f"Condition evaluation error: {e}")
            return False

    def _parse_size(self, size_value: Any) -> int:
        """Parse a size value that may include K/M/G suffixes."""
        if isinstance(size_value, int):
            return size_value

        size_str = str(size_value).upper().strip()
        multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}

        for suffix, mult in multipliers.items():
            if size_str.endswith(suffix):
                return int(float(size_str[:-1]) * mult)

        return int(size_str)


@dataclass
class Action:
    """An action to perform on a file."""

    action_type: ActionType
    value: Optional[str] = None

    def get_target_dir(self, file_path: Path, base_dest: Path) -> Optional[Path]:
        """Get the target directory for a move action.

        Args:
            file_path: Source file path.
            base_dest: Base destination directory.

        Returns:
            Target directory path, or None if not a move action.
        """
        if self.action_type != "move_to" or not self.value:
            return None

        # Support variables in target path
        target = self.value
        target = target.replace("{ext}", file_path.suffix.lstrip("."))
        target = target.replace("{name}", file_path.stem)

        # Support date variables
        file_date = get_file_date(file_path)
        if file_date:
            target = target.replace("{year}", str(file_date.year))
            target = target.replace("{month}", f"{file_date.month:02d}")
            target = target.replace("{day}", f"{file_date.day:02d}")

        return base_dest / target


@dataclass
class Rule:
    """A rule that matches files and specifies actions."""

    name: str
    conditions: list[Condition] = field(default_factory=list)
    action: Action = field(default_factory=lambda: Action("skip"))
    match_all: bool = True  # If True, all conditions must match. If False, any.
    priority: int = 0  # Higher priority rules are checked first.

    def matches(self, file_path: Path) -> bool:
        """Check if all conditions match the file.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the rule matches.
        """
        if not self.conditions:
            return True

        if self.match_all:
            return all(c.evaluate(file_path) for c in self.conditions)
        else:
            return any(c.evaluate(file_path) for c in self.conditions)


@dataclass
class RuleSet:
    """A collection of rules for file organization."""

    name: str = "default"
    rules: list[Rule] = field(default_factory=list)
    default_action: Action = field(default_factory=lambda: Action("skip"))

    def find_matching_rule(self, file_path: Path) -> Optional[Rule]:
        """Find the first rule that matches the file.

        Rules are checked in priority order (highest first).

        Args:
            file_path: Path to the file.

        Returns:
            The matching rule, or None if no rule matches.
        """
        # Sort by priority (highest first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if rule.matches(file_path):
                log_debug(f"File '{file_path.name}' matched rule '{rule.name}'")
                return rule

        return None

    def get_action_for_file(self, file_path: Path) -> Action:
        """Get the action to perform on a file.

        Args:
            file_path: Path to the file.

        Returns:
            The action to perform.
        """
        rule = self.find_matching_rule(file_path)
        if rule:
            return rule.action
        return self.default_action


def load_rules_from_yaml(yaml_path: Path) -> Optional[RuleSet]:
    """Load a rule set from a YAML file.

    Args:
        yaml_path: Path to the YAML file.

    Returns:
        The loaded RuleSet, or None if loading fails.
    """
    if not yaml_path.exists():
        log_error(f"Rules file not found: {yaml_path}")
        return None

    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        if not data:
            return RuleSet()

        name = data.get("name", "default")
        rules = []

        for rule_data in data.get("rules", []):
            conditions = []
            for cond_data in rule_data.get("conditions", []):
                conditions.append(Condition(
                    condition_type=cond_data["type"],
                    value=cond_data.get("value"),
                    negate=cond_data.get("negate", False),
                ))

            action_data = rule_data.get("action", {})
            action = Action(
                action_type=action_data.get("type", "skip"),
                value=action_data.get("value"),
            )

            rules.append(Rule(
                name=rule_data.get("name", "unnamed"),
                conditions=conditions,
                action=action,
                match_all=rule_data.get("match_all", True),
                priority=rule_data.get("priority", 0),
            ))

        default_action_data = data.get("default_action", {})
        default_action = Action(
            action_type=default_action_data.get("type", "skip"),
            value=default_action_data.get("value"),
        )

        return RuleSet(name=name, rules=rules, default_action=default_action)

    except Exception as e:
        log_error(f"Failed to load rules from '{yaml_path}': {e}")
        return None


def get_default_rules_path() -> Path:
    """Get the default path for rules files."""
    return get_config_dir() / "rules.yaml"


def create_example_rules_file(path: Path) -> bool:
    """Create an example rules file.

    Args:
        path: Path to create the rules file at.

    Returns:
        True if created successfully.
    """
    example_rules = '''# File Organizer Custom Rules
# This file defines custom rules for organizing files.

name: my_rules

# Rules are checked in priority order (highest first)
rules:
  # Move screenshots to a screenshots folder
  - name: screenshots
    priority: 10
    conditions:
      - type: name_pattern
        value: "Screenshot*"
      - type: extension
        value: [".png", ".jpg"]
    match_all: true
    action:
      type: move_to
      value: "screenshots/{year}/{month}"

  # Move large videos to a separate folder
  - name: large_videos
    priority: 5
    conditions:
      - type: extension
        value: [".mp4", ".mkv", ".avi"]
      - type: size_gt
        value: "1G"
    match_all: true
    action:
      type: move_to
      value: "videos/large"

  # Skip temporary files
  - name: skip_temp
    priority: 100
    conditions:
      - type: extension
        value: [".tmp", ".part", ".crdownload"]
    action:
      type: skip

  # Move documents by year
  - name: documents_by_year
    conditions:
      - type: mime_type
        value: "application/pdf"
    action:
      type: move_to
      value: "documents/{year}"

# Default action for files that don't match any rule
default_action:
  type: skip
'''

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            f.write(example_rules)
        log_action(f"Created example rules file at: {path}")
        return True
    except Exception as e:
        log_error(f"Failed to create rules file: {e}")
        return False
