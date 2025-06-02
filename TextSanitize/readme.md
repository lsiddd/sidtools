##  **TextSanitize**

A robust, multi-threaded command-line utility for cleaning and converting text file encodings across your file system. It automatically handles invalid characters by either removing them or discarding entire problematic lines, ensuring compatibility and data integrity.

## Table of Contents

- [TextSanitize](#TextSanitize)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Why Use TextSanitize?](#why-use-TextSanitize)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Building from Source](#building-from-source)
  - [Usage](#usage)
    - [Basic Syntax](#basic-syntax)
    - [Options](#options)
    - [Examples](#examples)
  - [How Encoding Conversion Works](#how-encoding-conversion-works)
  - [Contributing](#contributing)
  - [License](#license)
  - [Acknowledgments](#acknowledgments)

## Features

-   **Target Encoding Conversion:** Convert files from assumed UTF-8 input to a specified target encoding (e.g., `latin1`, `ISO-8859-1`, `UTF-16`, etc.).
-   **Invalid Character Handling:**
    -   Automatically replaces unconvertible characters with appropriate substitutes (based on `iconv`'s `//TRANSLIT` or `//IGNORE` behavior if used for `//IGNORE` in the main conversion logic, *currently replacement is implicitly handled by `iconv` when `EILSEQ` occurs, and `remove-invalid-lines` flag specifically removes lines*).
    -   Optionally removes entire lines that contain unconvertible characters.
-   **Recursive Directory Processing:** Clean multiple files within a directory and its subdirectories.
-   **Session Management:** For directory processing, `TextSanitize` can track processed files to resume interrupted operations or avoid re-processing, storing progress in a `.clean_session` file.
-   **Multi-threaded Performance:** Leverages multiple CPU cores to process files concurrently, significantly speeding up operations on large datasets.
-   **Safe In-Place Replacement:** Uses temporary files during conversion to ensure data safety. The original file is replaced only upon successful completion.
-   **Verbose Output:** Provides detailed logs of processed files, modified lines, and removed lines.
-   **POSIX-compliant:** Designed for Linux and macOS environments. (The `mkstemp` and `iconv` dependencies point to POSIX systems).

## Why Use TextSanitize?

Many older systems or specific applications require text files to be in a particular character encoding, often `latin1` or `ISO-8859-1`. When you encounter files with mixed encodings, or content originally in UTF-8 that needs to be downgraded for compatibility, `TextSanitize` provides a robust solution.

-   **Ensuring Compatibility:** Convert modern UTF-8 files to older encodings like `latin1` for legacy systems.
-   **Data Consistency:** Standardize the encoding of a large collection of text files.
-   **Cleaning Corrupt Data:** Remove or fix lines containing characters that are invalid in the target encoding.
-   **Automation:** Process thousands of files automatically in batch mode.

## Installation

### Prerequisites

You need the following tools and libraries to build and run `TextSanitize`:

-   A C++17 compatible compiler (e.g., GCC, Clang)
-   [Meson Build System](https://mesonbuild.com/)
-   [Ninja Build System](https://ninja-build.org/)
-   `iconv` development headers and library (usually part of `glibc` on Linux, or `libiconv` on macOS via Homebrew/MacPorts).

**On Debian/Ubuntu:**
```bash
sudo apt update
sudo apt install build-essential meson ninja-build libiconv-dev
```

**On Fedora/RHEL:**
```bash
sudo dnf install gcc-c++ meson ninja-build libiconv-devel
```

**On macOS (with Homebrew):**
```bash
brew install meson ninja libiconv
```

### Building from Source

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/lsiddd/sid_tools.git # Replace with your repo URL
    cd sid_tools
    cd TextSanitize
    ```

2.  **Configure the build:**
    ```bash
    meson setup build --buildtype=release -Dcpp_std=c++17 -Db_lto=true
    ```
    This command sets up the build directory, configures a release build with C++17 standard, and enables Link Time Optimization for maximum performance.

3.  **Compile the project:**
    ```bash
    meson compile -C build
    ```

4.  **Install the executable (optional):**
    ```bash
    meson install -C build
    ```
    This will install the `TextSanitize` executable to your system's `PATH` (e.g., `/usr/local/bin`), making it globally accessible.

## Usage

### Basic Syntax

```bash
TextSanitize <path> [options...]
```

-   `<path>`: The path to the file or directory you want to process.

### Options

| Option                        | Description                                                                                                                                                                                                                                                                                                                                                               | Default      |
| :---------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :----------- |
| `-t ENC`, `--target-encoding ENC` | Specifies the target character encoding (e.g., `latin1`, `UTF-8`, `ISO-8859-1`, `UTF-16LE`). **Crucial for conversion.** Refer to `iconv --list` for supported encodings on your system.                                                                                                                                                                        | `latin1`     |
| `-v`, `--verbose`             | Enables detailed output, showing progress, modified lines, and errors.                                                                                                                                                                                                                                                                                                    | `false`      |
| `--remove-invalid-lines`      | If a line contains characters that cannot be converted to the target encoding, the entire line will be removed from the output. Otherwise, `iconv` will attempt to transliterate or replace invalid characters.                                                                                                                                                                | `false`      |
| `-r`, `--recursive`           | Processes all files within the specified directory and its subdirectories. **Required for directory processing.**                                                                                                                                                                                                                                                           | `false`      |
| `-f`, `--force-replace`       | **Mandatory** for both single file and directory processing. This flag indicates that `TextSanitize` is permitted to replace the original files with the cleaned versions. Always ensure you have backups before using this flag on critical data.                                                                                                                         | `false`      |
| `--flush-session`             | When processing a directory, this option clears any existing session file (`.clean_session`) and starts the processing from scratch. Useful if a previous run was incomplete or you want to re-process all files.                                                                                                                                                            | `false`      |
| `--keep-session`              | When processing a directory, this option prevents `TextSanitize` from deleting the `.clean_session` file upon successful completion. This can be useful for debugging or manually managing processing sessions.                                                                                                                                                               | `false`      |

### Examples

1.  **Convert a single file to `latin1` (ISO-8859-1) and replace it:**
    ```bash
    TextSanitize my_document.txt -t latin1 -f
    ```

2.  **Process an entire directory recursively, convert to `ISO-8859-1`, enable verbose output, and replace files:**
    ```bash
    TextSanitize my_data_folder -t ISO-8859-1 -r -f -v
    ```

3.  **Recursively clean a project, remove lines with unconvertible characters, and start a fresh session:**
    ```bash
    TextSanitize my_project_root --remove-invalid-lines -r -f --flush-session
    ```

4.  **Convert a file to UTF-16 Little Endian, showing detailed logs:**
    ```bash
    TextSanitize source.log -t UTF-16LE -f -v
    ```

5.  **Resume an interrupted directory cleaning process (will skip already processed files):**
    ```bash
    TextSanitize large_archive -t UTF-8 -r -f
    ```
    (No `--flush-session` means it will read the `.clean_session` file)

## How Encoding Conversion Works

`TextSanitize` utilizes the `iconv` library for character encoding conversion.

By default, it assumes that the **input file's encoding is UTF-8**. It then converts this UTF-8 content to the `--target-encoding` you specify.

When encountering characters that cannot be directly represented in the target encoding:
-   If `--remove-invalid-lines` is **NOT** used: `iconv` attempts to transliterate characters (e.g., `é` might become `e`) or replace them with a default substitute character (like `?` or `�`).
-   If `--remove-invalid-lines` **IS** used: Any line containing unconvertible characters will be skipped entirely and not written to the output file.

For verbose output, `TextSanitize` uses `iconv` with `//TRANSLIT` to display both the original and cleaned content in your terminal's UTF-8 friendly encoding, even if the conversion itself targeted a different encoding.

## Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to improve the code, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License.

## Acknowledgments

-   Uses the `iconv` library for character set conversions.
-   Built with the Meson Build System.

