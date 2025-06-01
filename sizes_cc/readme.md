# sizes_cc/

This directory contains a C++ program (`sizes`) for analyzing disk space usage by file extension within a specified directory. It recursively traverses the directory tree, aggregates the total size and count for each file extension, and presents the results.

## Contents:

*   `main.cc`: The C++ source code for the disk usage analyzer.

## Dependencies:

*   A C++17 compatible compiler (like g++ or clang++).
*   `CLI11` library: For parsing command-line arguments (header-only).
*   Standard C++ libraries: `<filesystem>`, `<thread>`, `<atomic>`, `<unordered_map>`, etc.

You need to have the CLI11 header available.

Example compilation (adjust paths as needed):
```bash
g++ sizes_cc/main.cc -o sizes -std=c++17 -pthread -I/path/to/cli11_header/
```
Using CMake is the recommended build approach.

## Usage:

```bash
./sizes_cc/sizes [directory] [options]
```

*   `[directory]` (optional): The path to the directory to analyze. Defaults to the current directory (`.`).

## Options:

*   `-d <depth>`, `--depth <depth>`: Maximum directory depth to traverse (0 for current dir only).
*   `-t <N>`, `--top <N>`: Show only the top N extensions.
*   `-m <mode>`, `--mode <mode>`: Display mode: `size`, `count`, or `both`. Affects sorting and output columns. Default is `size`.

## Examples:

```bash
# Analyze the current directory recursively, sorted by size (default)
./sizes_cc/sizes

# Analyze /home/user/downloads up to depth 1, showing top 5 by count
./sizes_cc/sizes /home/user/downloads --depth 1 --top 5 --mode count

# Analyze /var/log showing all extensions by size and count
./sizes_cc/sizes /var/log --mode both
```

The program will print a summary table of disk usage per extension, sorted by the specified mode. A progress indicator is shown on stderr during the scan.
