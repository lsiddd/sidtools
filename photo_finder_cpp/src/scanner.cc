#include "scanner.hpp"

#include <spdlog/spdlog.h>
#include <exiv2/exiv2.hpp>
#include <algorithm>
#include <system_error>

// ---------------------------------------------------------------------------
// Globals
// ---------------------------------------------------------------------------

const std::unordered_set<std::string> image_extensions = {
    ".jpg", ".jpeg", ".png", ".tiff", ".bmp",
    ".gif", ".cr2",  ".nef", ".dng",  ".arw",
    ".raf", ".orf",  ".sr2", ".pef",  ".rw2",
};

std::atomic<int> g_total_scanned{0};
std::atomic<int> g_copied{0};
std::atomic<int> g_skipped{0};
std::atomic<int> g_rejected{0};
std::atomic<int> g_errors{0};

// ---------------------------------------------------------------------------
// EXIF check
// ---------------------------------------------------------------------------

bool is_taken_by_camera(const fs::path& path) {
    try {
        auto image = Exiv2::ImageFactory::open(path.string());
        image->readMetadata();
        Exiv2::ExifData& exif = image->exifData();
        return exif.findKey(Exiv2::ExifKey("Exif.Image.Make"))  != exif.end() ||
               exif.findKey(Exiv2::ExifKey("Exif.Image.Model")) != exif.end();
    } catch (const Exiv2::Error& e) {
        spdlog::info("EXIF read failed for {}: {}", path.string(), e.what());
        return false;
    }
}

// ---------------------------------------------------------------------------
// File processing
// ---------------------------------------------------------------------------

void process_image_file(const fs::path& src, const fs::path& output_dir) {
    ++g_total_scanned;

    if (!is_taken_by_camera(src)) {
        spdlog::info("Rejected (no camera EXIF): {}", src.string());
        ++g_rejected;
        return;
    }

    const fs::path dest = output_dir / src.filename();

    if (fs::exists(dest)) {
        spdlog::info("Skipped (duplicate): {}", src.string());
        ++g_skipped;
        return;
    }

    try {
        fs::copy_file(src, dest, fs::copy_options::skip_existing);
        fs::last_write_time(dest, fs::last_write_time(src));
        spdlog::info("Copied: {} -> {}", src.string(), dest.string());
        ++g_copied;
    } catch (const std::exception& e) {
        spdlog::error("Copy failed for {}: {}", src.string(), e.what());
        ++g_errors;
    }
}

// ---------------------------------------------------------------------------
// Worker
// ---------------------------------------------------------------------------

void worker_function(DirectoryQueue& dir_queue, const fs::path& output_dir,
                     const std::vector<fs::path>& excluded) {
    auto is_excluded = [&](const fs::path& p) {
        if (p == output_dir) return true;
        for (const auto& ex : excluded)
            if (p == ex) return true;
        return false;
    };

    fs::path current_dir;
    while (dir_queue.pop(current_dir)) {
        try {
            for (const auto& entry : fs::directory_iterator(
                     current_dir, fs::directory_options::skip_permission_denied))
            {
                if (entry.is_directory()) {
                    std::error_code ec;
                    const fs::path real_dir = fs::canonical(entry.path(), ec);
                    if (ec) {
                        spdlog::warn("Directory canonicalization failed for {}: {}",
                                     entry.path().string(), ec.message());
                        continue;
                    }
                    if (is_excluded(real_dir)) continue;
                    dir_queue.push_if_new(real_dir);
                } else if (entry.is_regular_file()) {
                    std::string ext = entry.path().extension().string();
                    std::transform(ext.begin(), ext.end(), ext.begin(),
                                   [](unsigned char c) { return std::tolower(c); });
                    if (image_extensions.count(ext)) {
                        process_image_file(entry.path(), output_dir);
                    }
                }
            }
        } catch (const fs::filesystem_error& e) {
            spdlog::error("Directory read failed for {}: {}", current_dir.string(), e.what());
        }

        dir_queue.task_done();
    }
}
