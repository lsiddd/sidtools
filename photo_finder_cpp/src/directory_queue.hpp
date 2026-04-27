#pragma once

#include <filesystem>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <unordered_set>

namespace fs = std::filesystem;

/**
 * Thread-safe directory queue with completion tracking.
 *
 * Workers call pop() to claim a directory and task_done() when finished
 * processing it (including after pushing any subdirectories). When no
 * active tasks remain and the queue is empty, the queue self-stops and
 * all blocked pop() calls return false.
 */
class DirectoryQueue {
public:
    void push(const fs::path& p) {
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            m_queue.push(p);
        }
        m_cv.notify_one();
    }

    bool push_if_new(const fs::path& p) {
        const std::string key = p.string();

        {
            std::lock_guard<std::mutex> lock(m_mutex);
            if (!m_seen.insert(key).second) {
                return false;
            }
            m_queue.push(p);
        }

        m_cv.notify_one();
        return true;
    }

    // Returns false when the queue is stopped and empty.
    // Increments active count so the queue knows work is in flight.
    bool pop(fs::path& out) {
        std::unique_lock<std::mutex> lock(m_mutex);
        m_cv.wait(lock, [&] { return !m_queue.empty() || m_stop; });

        if (m_stop && m_queue.empty()) {
            return false;
        }

        out = std::move(m_queue.front());
        m_queue.pop();
        ++m_active;
        return true;
    }

    // Call after fully processing a popped directory (including any pushes).
    // When active reaches zero and the queue is empty, triggers shutdown.
    void task_done() {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (--m_active == 0 && m_queue.empty()) {
            m_stop = true;
            m_cv.notify_all();
        }
    }

private:
    std::queue<fs::path>    m_queue;
    std::unordered_set<std::string> m_seen;
    std::mutex              m_mutex;
    std::condition_variable m_cv;
    int                     m_active{0};
    bool                    m_stop{false};
};
