#include <CLI/CLI.hpp>
#include <spdlog/spdlog.h>
#include <exiv2/exiv2.hpp>
#include <filesystem>
#include <unordered_set>
#include <atomic>
#include <vector>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <algorithm>
#include <iostream>

namespace fs = std::filesystem;

#define LOG(x) std::cout << x << std::endl

// --------------------------------------------------------------------------------
// Global data: set of recognized image extensions and atomic counters
// --------------------------------------------------------------------------------

static const std::unordered_set<std::string> image_extensions = {
    ".jpg", ".jpeg", ".png", ".tiff", ".bmp",
    ".gif", ".cr2", ".nef", ".dng", ".arw",
    ".raf", ".orf", ".sr2", ".pef", ".rw2"
};

// Atomic counters for aggregated statistics
static std::atomic<int> g_total_scanned{0};
static std::atomic<int> g_copied{0};
static std::atomic<int> g_skipped{0};
static std::atomic<int> g_errors{0};

// --------------------------------------------------------------------------------
// Helper functions
// --------------------------------------------------------------------------------

/**
 * Return whether we should copy src to dest, 
 * ignoring duplicates (i.e. if dest exists, skip).
 */
std::pair<bool, std::string> should_copy(const fs::path& src, const fs::path& dest) {
    // If the destination file does not exist, we can copy.
    if (!fs::exists(dest)) {
        return {true, "new file"};
    }

    // If the file already exists, treat it as a duplicate and skip it.
    return {false, "duplicate / already exists"};
}

/**
 * Check if file was taken by a camera by reading Exif metadata.
 */
bool is_taken_by_camera(const fs::path& path) {
    try {
        auto image = Exiv2::ImageFactory::open(path.string());
        image->readMetadata();
        Exiv2::ExifData& exif_data = image->exifData();
        // If the Exif contains Make/Model, we assume it's camera-taken.
        return exif_data.findKey(Exiv2::ExifKey("Exif.Image.Make")) != exif_data.end() ||
               exif_data.findKey(Exiv2::ExifKey("Exif.Image.Model")) != exif_data.end();
    } catch (const Exiv2::Error& e) {
        spdlog::info("Error reading Exif for {}: {}", path.string(), e.what());
        return false;
    }
}

/**
 * Process a single image file:
 *  - Check if it's camera-taken
 *  - Possibly copy it to the output directory
 */
void process_image_file(const fs::path& src, const fs::path& output_dir) {
    // Just for consistent stats
    g_total_scanned++;

    // Check if the file was taken by a camera.
    if (!is_taken_by_camera(src)) {
        spdlog::info("Skipped non-camera image: {}", src.string());
        g_skipped++;
        return;
    }

    // Destination uses just the original filename at top-level of output_dir
    fs::path dest = output_dir / src.filename();

    auto [copy_needed, reason] = should_copy(src, dest);
    if (!copy_needed) {
        spdlog::info("Skipped {}: {}", reason, src.string());
        g_skipped++;
        return;
    }

    try {
        // Copy the file over if needed.
        fs::copy_file(src, dest, fs::copy_options::overwrite_existing);
        // Replicate timestamp
        fs::last_write_time(dest, fs::last_write_time(src));

        spdlog::info("Copied: {} -> {}", src.string(), dest.string());
        g_copied++;
    } catch (const std::exception& e) {
        spdlog::info("Error copying {}: {}", src.string(), e.what());
        g_errors++;
    }
}

// --------------------------------------------------------------------------------
// Thread-safe queue for directories to process
// --------------------------------------------------------------------------------

class DirectoryQueue {
public:
    void push(const fs::path& p) {
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            m_queue.push(p);
        }
        m_cv.notify_one();
    }

    bool pop(fs::path& out) {
        std::unique_lock<std::mutex> lock(m_mutex);
        // Wait until queue is not empty or we are shutting down
        m_cv.wait(lock, [&]() { return !m_queue.empty() || m_stop; });

        if (m_stop && m_queue.empty()) {
            return false; // no more work
        }

        out = std::move(m_queue.front());
        m_queue.pop();
        return true;
    }

    void stop() {
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            m_stop = true;
        }
        m_cv.notify_all();
    }

private:
    std::queue<fs::path> m_queue;
    std::mutex m_mutex;
    std::condition_variable m_cv;
    bool m_stop = false;
};

// --------------------------------------------------------------------------------
// Worker function
// --------------------------------------------------------------------------------

/**
 * Each worker thread runs this function:
 * 1) Pop a directory from the queue.
 * 2) Iterate its entries. For subdirectories, enqueue them for future processing.
 *    For files, check extension and process if it's an image.
 * 3) Repeat until the queue is empty and stop() is called.
 */
void worker_function(DirectoryQueue& dir_queue, const fs::path& output_dir) {
    while (true) {
        fs::path current_dir;
        // Pop next directory to process:
        if (!dir_queue.pop(current_dir)) {
            // No more work
            break;
        }

        // Safely iterate directory contents
        try {
            for (auto& entry : fs::directory_iterator(
                     current_dir, fs::directory_options::skip_permission_denied))
            {
                if (entry.is_directory()) {
                    // Enqueue subdirectory for processing
                    dir_queue.push(entry.path());
                } else if (entry.is_regular_file()) {
                    // Check extension
                    std::string ext = entry.path().extension().string();
                    std::transform(ext.begin(), ext.end(), ext.begin(),
                                   [](unsigned char c) { return std::tolower(c); });

                    // If recognized extension, process
                    if (image_extensions.count(ext)) {
                        process_image_file(entry.path(), output_dir);
                    }
                }
            }
        } catch (const fs::filesystem_error& e) {
            spdlog::info("Error reading directory {}: {}", current_dir.string(), e.what());
            // We'll skip this directory, continue
        }
    }
}

// --------------------------------------------------------------------------------
// main
// --------------------------------------------------------------------------------

int main(int argc, char** argv) {
    CLI::App app{"Copy camera images to a single output directory ignoring duplicates"};

    std::string input_dir_str, output_dir_str;
    app.add_option("input_dir", input_dir_str, "Input directory")
       ->required()
       ->check(CLI::ExistingDirectory);
    app.add_option("output_dir", output_dir_str, "Output directory")->required();

    CLI11_PARSE(app, argc, argv);

    fs::path input_dir = fs::canonical(input_dir_str);
    fs::path output_dir = fs::absolute(output_dir_str);

    if (input_dir == output_dir) {
        spdlog::info("Input and output directories must be different");
        return 1;
    }

    try {
        fs::create_directories(output_dir);
    } catch (const fs::filesystem_error& e) {
        spdlog::info("Failed to create output directory: {}", e.what());
        return 1;
    }

    // Prepare a directory queue and push the initial input_dir
    DirectoryQueue dir_queue;
    dir_queue.push(input_dir);

    // Launch a pool of worker threads
    unsigned num_threads = std::max(1u, std::thread::hardware_concurrency());
    spdlog::info("Launching {} worker threads...", num_threads);

    std::vector<std::thread> workers;
    workers.reserve(num_threads);
    for (unsigned i = 0; i < num_threads; ++i) {
        workers.emplace_back(worker_function, std::ref(dir_queue), std::ref(output_dir));
    }

    // Wait for workers to finish. We stop() only when we know
    // we won't add any new directories (we started with just 1).
    // Since directories are pushed by threads themselves, once they are done,
    // it means there's nothing more to push.
    //
    // In a bigger, more generic system, you'd manage "active workers" or track
    // emptiness differently. Here, we can simply wait until we're sure no more
    // directories can be enqueued (the threads do it themselves).
    //
    // We'll do a small heuristic: once all threads block and the queue is empty,
    // we can stop. Alternatively, you can do it more robustly if you prefer.
    {
        // A simple solution is to join workers after we see that we won't push
        // more directories from the main thread:
        //  - There's no more directories from main, so let's call stop.
        dir_queue.stop();
        for (auto &t : workers) {
            t.join();
        }
    }

    // Print summary
    spdlog::info("\nProcessing Summary:");
    spdlog::info("Total files scanned: {}", g_total_scanned.load());
    spdlog::info("Copied files: {}", g_copied.load());
    spdlog::info("Skipped files: {}", g_skipped.load());
    spdlog::info("Errors encountered: {}", g_errors.load());

    return 0;
}
