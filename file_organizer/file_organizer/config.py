"""Configuration management for file_organizer."""

import os
import re
from pathlib import Path
from typing import Literal

import yaml

ConflictStyle = Literal["number", "timestamp", "uuid"]

# Application name for config directories
APP_NAME = "file-organizer"

# Default configuration embedded in code (used if config.yaml not found)
DEFAULT_EXTENSION_TO_DIR: dict[str, str] = {
    # Videos
    ".mp4": "videos", ".mkv": "videos", ".avi": "videos", ".mov": "videos",
    ".wmv": "videos", ".flv": "videos", ".webm": "videos", ".mpg": "videos",
    ".mpeg": "videos", ".3gp": "videos", ".m4v": "videos",
    # Audio
    ".mp3": "audio", ".wav": "audio", ".flac": "audio", ".aac": "audio",
    ".ogg": "audio", ".wma": "audio", ".m4a": "audio", ".opus": "audio",
    # Images
    ".jpg": "images", ".jpeg": "images", ".png": "images", ".gif": "images",
    ".bmp": "images", ".tiff": "images", ".webp": "images", ".svg": "images",
    ".heif": "images", ".heic": "images", ".ico": "images", ".cur": "images",
    # Documents
    ".txt": "documents/text", ".pdf": "documents/pdf", ".doc": "documents/word",
    ".docx": "documents/word", ".odt": "documents/word", ".rtf": "documents/text",
    ".xls": "documents/excel", ".xlsx": "documents/excel", ".ods": "documents/excel",
    ".ppt": "documents/powerpoint", ".pptx": "documents/powerpoint",
    ".odp": "documents/powerpoint", ".md": "documents/text",
    ".csv": "documents/data", ".json": "documents/data", ".xml": "documents/data",
    ".log": "documents/text",
    # Archives
    ".zip": "archives", ".tar": "archives", ".gz": "archives", ".bz2": "archives",
    ".xz": "archives", ".rar": "archives", ".7z": "archives", ".tgz": "archives",
    ".tbz2": "archives", ".txz": "archives",
    # Code
    ".py": "code/python", ".js": "code/javascript", ".html": "code/web",
    ".css": "code/web", ".java": "code/java", ".c": "code/c_cpp",
    ".cpp": "code/c_cpp", ".h": "code/c_cpp", ".hpp": "code/c_cpp",
    ".cs": "code/csharp", ".go": "code/go", ".rb": "code/ruby",
    ".php": "code/php", ".swift": "code/swift", ".kt": "code/kotlin",
    ".rs": "code/rust", ".sh": "code/scripts", ".bash": "code/scripts",
    ".ps1": "code/scripts", ".pl": "code/perl", ".r": "code/r",
    ".yml": "code/config", ".yaml": "code/config", ".ini": "code/config",
    ".cfg": "code/config", ".conf": "code/config", ".toml": "code/config",
    ".gitignore": "code/config", ".editorconfig": "code/config",
    ".gitattributes": "code/config", ".npmignore": "code/config",
    ".babelrc": "code/config", ".eslintrc": "code/config",
    ".prettierrc": "code/config", ".stylelintrc": "code/config",
    # Databases
    ".sqlite": "databases", ".sql": "databases", ".db": "databases",
    # Disk images
    ".iso": "disk_images", ".img": "disk_images", ".vhd": "disk_images",
    ".vmdk": "disk_images",
    # Fonts
    ".ttf": "fonts", ".otf": "fonts", ".woff": "fonts", ".woff2": "fonts",
    ".eot": "fonts",
}

DEFAULT_UNWANTED_PATTERNS: list[str] = [
    r"^__pycache__$",
    r"^\.venv$",
    r"^venv$",
    r"^env$",
    r"^node_modules$",
    r"^target$",
    r"^build$",
    r"^dist$",
    r"^\.mypy_cache$",
    r"^\.pytest_cache$",
    r"^\.cache$",
    r"^\.Trash-\d+$",
    r"^\.Trash$",
    r"\.pyc$",
    r"\.swp$",
    r"\.swo$",
    r"~$",
    r"^Thumbs\.db$",
    r"^\.DS_Store$",
    r"^ehthumbs\.db$",
    r"^desktop\.ini$",
    r"^\.vscode-server$",
    r"^\.wine$",
    r"^\.wine64$",
]


class Config:
    """Configuration manager for file_organizer.

    Loads configuration from YAML file or uses embedded defaults.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize configuration.

        Args:
            config_path: Path to YAML configuration file. If None, searches
                        in package directory and current working directory.
        """
        self._extension_to_dir: dict[str, str] = DEFAULT_EXTENSION_TO_DIR.copy()
        self._unwanted_patterns: list[re.Pattern[str]] = []
        self._unknown_dir: str = "stuff"
        self._directories_dir: str = "directories"

        config_file = self._find_config_file(config_path)
        if config_file:
            self._load_from_yaml(config_file)
        else:
            self._compile_patterns(DEFAULT_UNWANTED_PATTERNS)

    def _find_config_file(self, config_path: Path | None) -> Path | None:
        """Find the configuration file.

        Searches in the following order:
        1. Explicit path (if provided)
        2. Current working directory (config.yaml)
        3. XDG_CONFIG_HOME (~/.config/file-organizer/config.yaml)
        4. ~/.file-organizer/config.yaml (legacy)
        5. Package directory (config.yaml)

        Args:
            config_path: Explicit path to config file.

        Returns:
            Path to config file if found, None otherwise.
        """
        if config_path and config_path.exists():
            return config_path

        # Search in current working directory
        cwd_config = Path.cwd() / "config.yaml"
        if cwd_config.exists():
            return cwd_config

        # Search in XDG_CONFIG_HOME (respects XDG Base Directory Specification)
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "")
        if xdg_config_home:
            xdg_config = Path(xdg_config_home) / APP_NAME / "config.yaml"
        else:
            xdg_config = Path.home() / ".config" / APP_NAME / "config.yaml"
        if xdg_config.exists():
            return xdg_config

        # Search in legacy home directory location
        legacy_config = Path.home() / f".{APP_NAME}" / "config.yaml"
        if legacy_config.exists():
            return legacy_config

        # Search in package directory
        package_dir = Path(__file__).parent.parent
        package_config = package_dir / "config.yaml"
        if package_config.exists():
            return package_config

        return None

    def _load_from_yaml(self, config_path: Path) -> None:
        """Load configuration from YAML file.

        Args:
            config_path: Path to the YAML configuration file.
        """
        with open(config_path) as f:
            data = yaml.safe_load(f)

        if data is None:
            self._compile_patterns(DEFAULT_UNWANTED_PATTERNS)
            return

        if "extension_to_dir" in data and isinstance(data["extension_to_dir"], dict):
            self._extension_to_dir = data["extension_to_dir"]

        if "unknown_dir" in data:
            self._unknown_dir = str(data["unknown_dir"])

        if "directories_dir" in data:
            self._directories_dir = str(data["directories_dir"])

        patterns = data.get("unwanted_patterns", DEFAULT_UNWANTED_PATTERNS)
        self._compile_patterns(patterns)

    def _compile_patterns(self, patterns: list[str]) -> None:
        """Compile regex patterns for unwanted file matching.

        Args:
            patterns: List of regex pattern strings.
        """
        self._unwanted_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in patterns
        ]

    @property
    def extension_to_dir(self) -> dict[str, str]:
        """Get the extension to directory mapping."""
        return self._extension_to_dir

    @property
    def unwanted_patterns(self) -> list[re.Pattern[str]]:
        """Get compiled unwanted file patterns."""
        return self._unwanted_patterns

    @property
    def unknown_dir(self) -> str:
        """Get the directory name for unknown file types."""
        return self._unknown_dir

    @property
    def directories_dir(self) -> str:
        """Get the directory name for directories at max depth."""
        return self._directories_dir


def get_config_dir() -> Path:
    """Get the configuration directory path.

    Uses XDG_CONFIG_HOME if set, otherwise ~/.config/file-organizer/.

    Returns:
        Path to the configuration directory.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg_config_home:
        return Path(xdg_config_home) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def get_data_dir() -> Path:
    """Get the data directory path for storing operation logs and state.

    Uses XDG_DATA_HOME if set, otherwise ~/.local/share/file-organizer/.

    Returns:
        Path to the data directory.
    """
    xdg_data_home = os.environ.get("XDG_DATA_HOME", "")
    if xdg_data_home:
        return Path(xdg_data_home) / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


# Global config instance (lazy-loaded)
_config: Config | None = None


def get_config(config_path: Path | None = None) -> Config:
    """Get or create the global configuration instance.

    Args:
        config_path: Optional path to configuration file.

    Returns:
        The configuration instance.
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reset_config() -> None:
    """Reset the global configuration instance (useful for testing)."""
    global _config
    _config = None
