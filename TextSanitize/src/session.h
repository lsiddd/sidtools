#pragma once
#include <filesystem>
#include <fstream>
#include <mutex>
#include <set>
#include <string>

// Tracks which files have been successfully processed so that an interrupted
// run can be resumed without reprocessing completed files.
//
// Thread-safe: all public methods may be called concurrently.
class Session {
    std::filesystem::path    path_;
    std::set<std::string>    processed_;
    mutable std::mutex       mutex_;

public:
    // Constructs a session rooted at dir/.clean_session.
    // If flush is true the existing session file is deleted and processing starts fresh.
    explicit Session(const std::filesystem::path& dir, bool flush) {
        path_ = dir / ".clean_session";
        if (flush) {
            std::error_code ec;
            std::filesystem::remove(path_, ec);
            return;
        }
        std::ifstream in(path_);
        if (!in) return;
        std::string line;
        while (std::getline(in, line)) {
            if (!line.empty()) processed_.insert(line);
        }
    }

    bool was_processed(const std::filesystem::path& p) const {
        std::lock_guard lock(mutex_);
        return processed_.count(std::filesystem::absolute(p).string()) > 0;
    }

    void mark_processed(const std::filesystem::path& p) {
        std::string abs = std::filesystem::absolute(p).string();
        std::lock_guard lock(mutex_);
        processed_.insert(abs);
        std::ofstream out(path_, std::ios::app);
        if (out) out << abs << '\n';
    }

    size_t already_done() const {
        std::lock_guard lock(mutex_);
        return processed_.size();
    }

    void remove() {
        std::error_code ec;
        std::filesystem::remove(path_, ec);
    }
};
