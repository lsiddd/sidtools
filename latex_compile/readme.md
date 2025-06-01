# latex_compile/

This directory contains a bash script designed to automate the compilation process for LaTeX documents, especially those using Biber for bibliography management.

## Contents:

*   `latex_build.sh`: A bash script that handles the multi-pass compilation needed for LaTeX documents with cross-references and Biber bibliographies. It includes options for building, cleaning, and monitoring files for automatic recompilation.

## Dependencies:

The script relies on command-line tools typically found in a TeX distribution and other system utilities:

*   `pdflatex`: The LaTeX compiler.
*   `biber`: The bibliography processor.
*   `inkscape`: Potentially required for processing SVG images if used with `shell-escape`.
*   `inotifywait`: For the `--monitor` mode (part of `inotify-tools`).
*   `rsync`: Used during setup.
*   A PDF viewer (like `xdg-open`).

The script includes a dependency check and may suggest installation commands for apt-based systems.

## Usage:

Make the script executable if necessary:
```bash
chmod +x latex_compile/latex_build.sh
```

Then run it with options:

```bash
./latex_compile/latex_build.sh [MAIN_FILE.tex] [OPTION]
```

*   `[MAIN_FILE.tex]` (optional): The main `.tex` file. Defaults to `main.tex`.
*   `[OPTION]` (optional):
    *   `-b` or `--build`: Compile the document and open the resulting PDF. (Default if no option is given).
    *   `-m` or `--monitor`: Compile, open the PDF, and watch for changes in source files to automatically recompile. Runs until interrupted (Ctrl+C).
    *   `-c` or `--clean`: Remove temporary build files and the build directory.

## Examples:

```bash
# Compile main.tex and open
./latex_compile/latex_build.sh -b

# Compile report.tex and monitor for changes
./latex_compile/latex_build.sh report.tex -m

# Clean build files for main.tex
./latex_compile/latex_build.sh -c
```

The script automates the standard `pdflatex`, `biber`, `pdflatex`, `pdflatex` sequence. Temporary files are placed in a build directory (defaulting to `./`) and the final PDF is moved back to the main directory.
