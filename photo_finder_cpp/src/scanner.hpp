#pragma once

#include "directory_queue.hpp"
#include <filesystem>
#include <atomic>
#include <unordered_set>
#include <vector>

namespace fs = std::filesystem;

// Recognized image file extensions (lowercase).
extern const std::unordered_set<std::string> image_extensions;

// Aggregated statistics updated by worker threads.
extern std::atomic<int> g_total_scanned;
extern std::atomic<int> g_copied;
extern std::atomic<int> g_skipped;
extern std::atomic<int> g_rejected;
extern std::atomic<int> g_errors;

// Returns true if the file has EXIF Make or Model tags (i.e. camera-taken).
bool is_taken_by_camera(const fs::path& path);

// Checks EXIF, skips duplicates, copies to output_dir if appropriate.
void process_image_file(const fs::path& src, const fs::path& output_dir);

// Worker thread entry point.
void worker_function(DirectoryQueue& dir_queue, const fs::path& output_dir,
                     const std::vector<fs::path>& excluded);
