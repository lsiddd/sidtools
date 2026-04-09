#pragma once
#include <filesystem>
#include <cstddef>
#include "options.h"

struct FileStats {
    int total_lines    = 0;
    int modified_lines = 0;  // lines with at least one unconvertible character
    int removed_lines  = 0;  // subset of modified_lines dropped by --remove-invalid-lines
};

// Convert a single file in-place (atomic rename via temp file).
// Throws std::runtime_error on I/O or iconv failure.
FileStats clean_single_file(const std::filesystem::path& path, const CleanOptions& opts);

// Recursively convert all files under dir.
// Returns the number of files processed successfully.
size_t clean_directory(const std::filesystem::path& dir, const CleanOptions& opts);
