# photo_finder_cpp/

This directory contains a C++ program that scans a directory tree to find image files that were likely taken by a camera, identified by the presence of EXIF metadata indicating a camera make or model. It copies these identified photos to a specified destination directory, avoiding duplicates.

## Contents:

*   `main.cc`: The C++ source code for the photo finding and copying utility.

## Dependencies:

*   A C++17 compatible compiler (like g++ or clang++).
*   `Exiv2` library: Required for reading image metadata.
*   `CLI11` library: For parsing command-line arguments (header-only).
*   `spdlog` library: For logging (header-only).
*   Standard C++ libraries: `<filesystem>`, `<thread>`, etc.

You need to install `Exiv2` development files on your system and have the CLI11 and spdlog headers available.

Example installation on Debian/Ubuntu:
```bash
sudo apt update
sudo apt install libexiv2-dev libspdlog-dev
# For CLI11, you might download the header or use CMake's FetchContent
```

## Building:

Compile the `main.cc` file, linking against the `exiv2` and `spdlog` libraries and including headers for CLI11 and spdlog. A `CMakeLists.txt` is recommended for managing dependencies and the build process.

Example simple compilation (adjust paths as needed):
```bash
g++ photo_finder_cpp/main.cc -o photo_finder -std=c++17 -pthread -lexiv2 -lspdlog -I/path/to/cli11_header/ -I/path/to/spdlog_header/
```

## Usage:

```bash
./photo_finder <input_dir> <output_dir>
```

*   `<input_dir>`: The source directory to scan recursively.
*   `<output_dir>`: The destination directory for camera-taken photos. It will be created if it doesn't exist.

## Example:

```bash
# Find camera photos in /data/raw_imports and copy them to /data/sorted_camera
./photo_finder /data/raw_imports /data/sorted_camera
```

The program will print its progress and a summary of operations (scanned, copied, skipped, errors). It determines "camera photos" based on the presence of specific EXIF tags and skips copying files that already exist in the destination directory by filename.
