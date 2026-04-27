#include "scanner.hpp"

#include <CLI/CLI.hpp>
#include <exiv2/error.hpp>
#include <spdlog/spdlog.h>
#include <cstdio>
#include <thread>
#include <vector>

int main(int argc, char** argv) {
    CLI::App app{"Copy camera-taken images to a flat output directory, skipping duplicates"};

    std::string              input_dir_str, output_dir_str;
    std::vector<std::string> exclude_strs;
    unsigned                 num_threads = std::max(1u, std::thread::hardware_concurrency());
    bool                     verbose     = false;

    app.add_option("input_dir",  input_dir_str,  "Source directory to scan recursively")
       ->required()
       ->check(CLI::ExistingDirectory);
    app.add_option("output_dir", output_dir_str, "Destination directory for copied photos")
       ->required();
    app.add_option("-x,--exclude", exclude_strs, "Directories to skip (repeatable)")
       ->check(CLI::ExistingDirectory);
    app.add_option("-j,--threads", num_threads, "Worker thread count")
       ->capture_default_str();
    app.add_flag("-v,--verbose",  verbose, "Log each copied/skipped file");

    CLI11_PARSE(app, argc, argv);

    spdlog::set_level(verbose ? spdlog::level::info : spdlog::level::warn);
    Exiv2::LogMsg::setLevel(verbose ? Exiv2::LogMsg::warn : Exiv2::LogMsg::mute);

    // Resolve paths using canonical for both to handle symlinks and relative paths.
    fs::path input_dir = fs::canonical(input_dir_str);

    fs::path output_dir;
    try {
        fs::create_directories(output_dir_str);
        output_dir = fs::canonical(output_dir_str);
    } catch (const fs::filesystem_error& e) {
        spdlog::error("Failed to create output directory: {}", e.what());
        return 1;
    }

    if (input_dir == output_dir) {
        spdlog::error("Input and output directories must be different");
        return 1;
    }

    std::vector<fs::path> excluded;
    for (const auto& s : exclude_strs)
        excluded.push_back(fs::canonical(s));

    DirectoryQueue dir_queue;
    dir_queue.push_if_new(input_dir);

    spdlog::warn("Launching {} worker thread(s)...", num_threads);

    std::vector<std::thread> workers;
    workers.reserve(num_threads);
    for (unsigned i = 0; i < num_threads; ++i) {
        workers.emplace_back(worker_function, std::ref(dir_queue),
                             std::ref(output_dir), std::ref(excluded));
    }

    for (auto& t : workers) {
        t.join();
    }

    // Always print summary regardless of verbosity level.
    std::printf("\nProcessing summary:\n");
    std::printf("  Scanned : %d\n", g_total_scanned.load());
    std::printf("  Copied  : %d\n", g_copied.load());
    std::printf("  Skipped : %d\n", g_skipped.load());
    std::printf("  Rejected: %d\n", g_rejected.load());
    std::printf("  Errors  : %d\n", g_errors.load());

    return g_errors.load() > 0 ? 1 : 0;
}
