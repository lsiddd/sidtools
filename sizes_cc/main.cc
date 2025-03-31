#include <CLI/CLI.hpp>
#include <atomic>
#include <filesystem>
#include <iostream>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <iomanip>
#include <sstream>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <cctype>
#include <optional>
#include <string_view>
#include <queue>
#include <chrono>
#include <unordered_set>

#define LOG(x) std::cout << x << std::endl

namespace fs = std::filesystem;

struct ExtensionInfo {
    uintmax_t total_size = 0;
    uintmax_t file_count = 0;
    void merge(const ExtensionInfo& other) {
        total_size += other.total_size;
        file_count += other.file_count;
    }
};

struct DirEntry {
    fs::path path;
    int depth;
};

class ThreadSafeQueue {
    std::queue<DirEntry> queue_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> done_ = false;
    std::atomic<int> active_workers_ = 0;

public:
    void push(DirEntry entry) {
        std::lock_guard lock(mutex_);
        queue_.push(std::move(entry));
        cv_.notify_one();
    }

    std::optional<DirEntry> pop() {
        std::unique_lock lock(mutex_);
        cv_.wait(lock, [&] { return !queue_.empty() || (done_ && active_workers_ == 0); });
        if (queue_.empty()) return std::nullopt;
        active_workers_++;
        auto entry = std::move(queue_.front());
        queue_.pop();
        return entry;
    }

    void notify_processed() {
        active_workers_--;
        cv_.notify_all();
    }

    void set_done() {
        done_ = true;
        cv_.notify_all();
    }

    size_t size() const {
        std::lock_guard lock(mutex_);
        return queue_.size();
    }
};

struct ActiveDirectories {
    mutable std::mutex mutex;
    std::unordered_map<std::thread::id, DirEntry> active_entries;
};

std::string human_readable_size(uintmax_t size_bytes) {
    constexpr std::array<const char*, 6> units = {"B", "KB", "MB", "GB", "TB", "PB"};
    int unit_index = 0;
    double size = static_cast<double>(size_bytes);

    while (size >= 1024 && unit_index < 5) {
        size /= 1024;
        unit_index++;
    }

    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2) << size << " " << units[unit_index];
    return oss.str();
}

std::string format_with_commas(uintmax_t value) {
    std::string num = std::to_string(value);
    std::string result;
    result.reserve(num.size() + num.size() / 3);
    for (size_t i = 0; i < num.size(); ++i) {
        if (i != 0 && (num.size() - i) % 3 == 0) {
            result.push_back(',');
        }
        result.push_back(num[i]);
    }
    return result;
}

void process_directory(
    DirEntry entry,
    ThreadSafeQueue& queue,
    const std::optional<int>& max_depth,
    std::unordered_map<std::string, ExtensionInfo>& local_map,
    std::atomic<uintmax_t>& processed_files,
    std::atomic<uintmax_t>& total_processed_size
) {
    std::error_code dir_ec;
    auto dir_iter = fs::directory_iterator(entry.path, fs::directory_options::skip_permission_denied, dir_ec);
    if (dir_ec) return;

    for (const auto& e : dir_iter) {
        std::error_code ec;
        const bool is_regular = e.is_regular_file(ec);
        if (ec) continue;
        if (e.is_symlink()) continue;

        if (is_regular) {
            const uintmax_t file_size = e.file_size(ec);
            if (ec) continue;

            std::string ext = e.path().extension().string();
            if (ext.empty()) {
                ext = "no_extension";
            } else {
                std::transform(ext.begin(), ext.end(), ext.begin(),
                             [](unsigned char c) { return std::tolower(c); });
            }

            local_map[ext].total_size += file_size;
            local_map[ext].file_count += 1;
            total_processed_size.fetch_add(file_size, std::memory_order_relaxed);
            processed_files.fetch_add(1, std::memory_order_relaxed);
        } else if (e.is_directory(ec) && !ec) {
            const int new_depth = entry.depth + 1;
            if (!max_depth.has_value() || new_depth <= *max_depth) {
                queue.push({e.path(), new_depth});
            }
        }
    }
}

void stats_thread_func(
    const std::atomic<uintmax_t>& processed_files,
    const std::atomic<uintmax_t>& processed_dirs,
    const std::atomic<uintmax_t>& total_processed_size,
    const std::atomic<bool>& processing_done,
    const ThreadSafeQueue& queue,
    const ActiveDirectories& active_directories,
    const fs::path& root_path
) {
    using namespace std::chrono;
    auto start_time = steady_clock::now();
    auto last_time = start_time;
    uintmax_t last_files = 0;
    uintmax_t last_dirs = 0;
    uintmax_t last_size = 0;

    while (!processing_done.load(std::memory_order_relaxed)) {
        std::this_thread::sleep_for(milliseconds(100));
        auto now = steady_clock::now();
        auto elapsed_since_last = duration_cast<duration<double>>(now - last_time).count();

        uintmax_t current_files = processed_files.load(std::memory_order_relaxed);
        uintmax_t current_dirs = processed_dirs.load(std::memory_order_relaxed);
        uintmax_t current_size = total_processed_size.load(std::memory_order_relaxed);

        uintmax_t files_diff = current_files - last_files;
        uintmax_t dirs_diff = current_dirs - last_dirs;
        uintmax_t size_diff = current_size - last_size;

        double files_per_sec = elapsed_since_last > 0 ? files_diff / elapsed_since_last : 0.0;
        double dirs_per_sec = elapsed_since_last > 0 ? dirs_diff / elapsed_since_last : 0.0;
        double size_per_sec = elapsed_since_last > 0 ? size_diff / elapsed_since_last : 0.0;

        last_files = current_files;
        last_dirs = current_dirs;
        last_size = current_size;
        last_time = now;

        int queue_size = queue.size();

        std::vector<DirEntry> current_active_entries;
        int current_max_depth = -1;
        std::unordered_set<fs::path> parent_dirs;

        {
            std::lock_guard lock(active_directories.mutex);
            for (const auto& [tid, entry] : active_directories.active_entries) {
                current_active_entries.push_back(entry);
            }
        }

        if (!current_active_entries.empty()) {
            current_max_depth = std::max_element(
                current_active_entries.begin(),
                current_active_entries.end(),
                [](const auto& a, const auto& b) { return a.depth < b.depth; }
            )->depth;

            for (const auto& entry : current_active_entries) {
                if (entry.depth == current_max_depth) {
                    parent_dirs.insert(entry.path.parent_path());
                }
            }
        }

        std::string dirs_str;
        if (!parent_dirs.empty()) {
            std::vector<fs::path> parents(parent_dirs.begin(), parent_dirs.end());
            std::vector<std::string> parent_names;
            for (const auto& parent : parents) {
                try {
                    parent_names.push_back(fs::relative(parent, root_path).string());
                } catch (const fs::filesystem_error&) {
                    parent_names.push_back(parent.string());
                }
            }

            std::ostringstream oss_dir;
            for (size_t i = 0; i < parent_names.size(); ++i) {
                if (i != 0) {
                    if (i == parent_names.size() - 1) {
                        oss_dir << " and ";
                    } else {
                        oss_dir << ", ";
                    }
                }
                oss_dir << parent_names[i];
            }
            dirs_str = oss_dir.str();
        } else {
            dirs_str = "none";
        }

        std::ostringstream oss;
        oss << "\rProgress: ";
        oss << "Size: " << human_readable_size(current_size) << " (" << human_readable_size(size_per_sec) << "/s), ";
        oss << "Files: " << format_with_commas(current_files) << " (" << std::fixed << std::setprecision(1) << files_per_sec << "/s), ";
        oss << "Dirs: " << format_with_commas(current_dirs) << " (" << std::fixed << std::setprecision(1) << dirs_per_sec << "/s), ";
        oss << "Queue: " << queue_size;
        // if (current_max_depth != -1) {
        //     oss << ", Max Depth: " << current_max_depth << " (" << dirs_str << ")";
        // }
        oss << "   ";

        // Prepare the line with fixed width to overwrite previous content
        std::string line = oss.str();
        line.resize(150, ' '); // Pad with spaces to ensure 150 characters
        line[0] = '\r'; // Ensure it starts with carriage return
        std::cerr << line << std::flush;
    }

    std::cerr << "\r" << std::string(150, ' ') << "\r" << std::flush;
}

int main(int argc, char** argv) {
    CLI::App app{"Analyze disk usage by file extension"};

    std::string dir_path = ".";
    std::optional<int> max_depth;
    std::optional<int> top;
    std::string mode = "size";

    app.add_option("directory", dir_path, "Directory to analyze")->check(CLI::ExistingDirectory);
    app.add_option("-d,--depth", max_depth, "Maximum directory depth to traverse (0 for current dir only)");
    app.add_option("-t,--top", top, "Show top N extensions");
    app.add_option("-m,--mode", mode, "Display mode: size, count, or both")
        ->check(CLI::IsMember({"size", "count", "both"}));

    CLI11_PARSE(app, argc, argv);

    const fs::path root_path(dir_path);
    if (!fs::exists(root_path)) {
        std::cerr << "Error: Directory '" << dir_path << "' does not exist\n";
        return EXIT_FAILURE;
    }

    ThreadSafeQueue queue;
    queue.push({root_path, 0});

    const unsigned num_threads = std::max(1u, std::thread::hardware_concurrency());
    std::vector<std::thread> workers;
    std::vector<std::unordered_map<std::string, ExtensionInfo>> thread_maps(num_threads);

    std::atomic<uintmax_t> processed_files{0};
    std::atomic<uintmax_t> processed_dirs{0};
    std::atomic<uintmax_t> total_processed_size{0};
    std::atomic<bool> processing_done{false};
    ActiveDirectories active_directories;

    for (unsigned i = 0; i < num_threads; ++i) {
        workers.emplace_back([&, i] {
            auto& local_map = thread_maps[i];
            while (auto entry_opt = queue.pop()) {
                processed_dirs.fetch_add(1, std::memory_order_relaxed);

                {
                    std::lock_guard lock(active_directories.mutex);
                    active_directories.active_entries[std::this_thread::get_id()] = *entry_opt;
                }

                process_directory(*entry_opt, queue, max_depth, local_map, processed_files, total_processed_size);

                {
                    std::lock_guard lock(active_directories.mutex);
                    active_directories.active_entries.erase(std::this_thread::get_id());
                }

                queue.notify_processed();
            }
        });
    }

    std::thread stats_thread(stats_thread_func, 
        std::ref(processed_files), 
        std::ref(processed_dirs),
        std::ref(total_processed_size),
        std::ref(processing_done), 
        std::ref(queue),
        std::ref(active_directories),
        root_path);

    queue.set_done();
    for (auto& t : workers) t.join();

    processing_done.store(true);
    stats_thread.join();

    std::unordered_map<std::string, ExtensionInfo> extension_map;
    for (const auto& map : thread_maps) {
        for (const auto& [ext, info] : map) {
            extension_map[ext].merge(info);
        }
    }

    std::vector<std::pair<std::string, ExtensionInfo>> sorted_entries;
    sorted_entries.reserve(extension_map.size());
    for (const auto& [ext, info] : extension_map) {
        sorted_entries.emplace_back(ext, info);
    }

    const auto sort_by_size = [](const auto& a, const auto& b) { return a.second.total_size > b.second.total_size; };
    const auto sort_by_count = [](const auto& a, const auto& b) { return a.second.file_count > b.second.file_count; };

    if (mode == "size" || mode == "both") {
        std::sort(sorted_entries.begin(), sorted_entries.end(), sort_by_size);
    } else if (mode == "count") {
        std::sort(sorted_entries.begin(), sorted_entries.end(), sort_by_count);
    }

    if (top.has_value() && *top > 0) {
        sorted_entries.resize(std::min(static_cast<size_t>(*top), sorted_entries.size()));
    }

    std::cout << "\nAnalyzing: " << fs::absolute(root_path) << "\n";
    if (max_depth.has_value()) {
        std::cout << "Maximum depth: " << *max_depth << "\n";
    }

    constexpr int column_width = 15;
    const std::vector<std::string> headers = [&] {
        std::vector<std::string> h{"Extension"};
        if (mode == "size" || mode == "both") h.push_back("Total Size");
        if (mode == "count" || mode == "both") h.push_back("File Count");
        return h;
    }();

    std::cout << '\n';
    for (const auto& h : headers) {
        std::cout << std::left << std::setw(column_width) << h << " | ";
    }
    std::cout << "\n" << std::string(column_width * headers.size() + 3 * (headers.size() - 1), '-') << "\n";

    for (const auto& [ext, info] : sorted_entries) {
        std::vector<std::string> columns{ext};
        if (mode == "size" || mode == "both") {
            columns.push_back(human_readable_size(info.total_size));
        }
        if (mode == "count" || mode == "both") {
            columns.push_back(format_with_commas(info.file_count));
        }

        for (size_t i = 0; i < columns.size(); ++i) {
            std::cout << std::left << std::setw(column_width) << columns[i];
            if (i != columns.size() - 1) std::cout << " | ";
        }
        std::cout << '\n';
    }

    return EXIT_SUCCESS;
}
