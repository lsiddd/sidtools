#!/usr/bin/env bash

# latex-manager.sh
# Enhanced LaTeX compilation script with proper Biber support and dependency checks

# Configuration
PDF_VIEWER="xdg-open"   # Default PDF viewer
BUILD_DIR="./"     # Build directory for auxiliary files
LATEX_ENGINE="pdflatex" # LaTeX engine to use
BIBER_CMD="biber"       # Bibliography processor

# Check for required dependencies
check_dependencies() {
  local missing=()
  command -v $LATEX_ENGINE >/dev/null 2>&1 || missing+=("texlive-core")
  command -v $BIBER_CMD >/dev/null 2>&1 || missing+=("biber")
  command -v inkscape >/dev/null 2>&1 || missing+=("inkscape")
  command -v inotifywait >/dev/null 2>&1 || missing+=("inotify-tools")
  command -v rsync >/dev/null 2>&1 || missing+=("rsync")

  if [ ${#missing[@]} -gt 0 ]; then
    echo "Missing dependencies:"
    printf "• %s\n" "${missing[@]}"
    echo "Install with: sudo apt install ${missing[*]}"
    exit 1
  fi
}

# Clean temporary files
cleanup() {
  echo "Cleaning temporary files..."
  rm -f *.aux *.log *.out *.bbl *.blg *.toc *.lof *.lot *.fls *.fdb_latexmk
  [ -d "$BUILD_DIR" ] && rm -rf "$BUILD_DIR"
}

# Create mirrored build directory structure
create_build_dir_structure() {
  echo "Creating build structure..."
  rsync -a --filter "- $BUILD_DIR/" \
            --filter "- .git/" \
            --filter "+ */" \
            --filter "- *" \
            ./ "$BUILD_DIR/" >/dev/null
}

# Main compilation process
compile() {
  local project_main="$1"
  local base_name=$(basename -s .tex "$project_main")
  
  echo "Phase 1: Initial compilation"
  $LATEX_ENGINE -shell-escape -output-directory="$BUILD_DIR" \
    -interaction=nonstopmode "$project_main" >/dev/null || exit 1

  echo "Phase 2: Bibliography processing"
  (cd "$BUILD_DIR" && $BIBER_CMD "$base_name") || exit 1

  echo "Phase 3: Reference resolution"
  for i in {1..3}; do
    $LATEX_ENGINE -shell-escape -output-directory="$BUILD_DIR" \
      -interaction=nonstopmode "$project_main" >/dev/null || exit 1
  done

  mv "$BUILD_DIR/$base_name.pdf" .
  echo "Compilation successful: $base_name.pdf created"
}

# Open PDF in viewer
open_pdf() {
  local pdf_file="$(basename -s .tex "$1").pdf"
  [ -f "$pdf_file" ] && $PDF_VIEWER "$pdf_file" >/dev/null 2>&1 &
}

# File monitoring for auto-compile
monitor() {
  local project_main="$1"
  echo "Monitoring changes in LaTeX files..."
  while true; do
    inotifywait -qr -e modify,create,delete \
                --exclude '*.pdf|*.git/' \
                --format '%w%f' .
    compile "$project_main"
    open_pdf "$project_main"
  done
}

# Main program flow
main() {
  local project_main="main.tex"

  # Handle main file argument
  if [[ "$1" == *.tex ]] && [ -f "$1" ]; then
    project_main="$1"
    shift
  elif [ ! -f "$project_main" ]; then
    echo "Error: main.tex not found!"
    exit 1
  fi

  check_dependencies

  case "$1" in
  -m|--monitor)
    compile "$project_main"
    open_pdf "$project_main"
    monitor "$project_main"
    ;;
  -c|--clean)
    cleanup
    ;;
  -b|--build)
    compile "$project_main"
    open_pdf "$project_main"
    ;;
  *)
    echo "Usage: $0 [MAIN_FILE] [OPTION]"
    echo "Options:"
    echo "  -m, --monitor  Auto-compile on changes"
    echo "  -b, --build    Compile and open PDF"
    echo "  -c, --clean    Remove build artifacts"
    exit 1
    ;;
  esac
}

# Start main program
main "$@"