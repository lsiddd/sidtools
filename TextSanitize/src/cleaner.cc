#include "cleaner.h"
#include "iconv_handle.h"
#include "session.h"

#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <mutex>
#include <thread>
#include <atomic>
#include <filesystem>
#include <cerrno>
#include <cstring>
#include <cstddef>

#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/mman.h>

namespace {

std::mutex g_log_mutex;

std::string to_display_utf8(const char* data, size_t len, const std::string& from_enc) {
    if (len == 0) return {};
    try {
        IconvHandle cd("UTF-8//TRANSLIT", from_enc);
        char*  inptr  = const_cast<char*>(data);
        size_t inleft = len;
        std::string result;
        std::vector<char> out(len * 4 + 4);
        while (inleft > 0) {
            char*  outptr  = out.data();
            size_t outleft = out.size();
            cd.convert(&inptr, &inleft, &outptr, &outleft);
            result.append(out.data(), outptr - out.data());
            if (inleft > 0) { ++inptr; --inleft; result += "\xef\xbf\xbd"; }
        }
        return result;
    } catch (...) {
        return {data, data + len};
    }
}

bool is_internal_file(const std::filesystem::path& p) {
    const std::string name = p.filename().string();
    return name == ".clean_session" || name.rfind(".clean_", 0) == 0;
}

// ---- Zero-copy line scanning -----------------------------------------------

struct LineSpan {
    const char* content_begin;
    const char* content_end;
    const char* span_end;
    bool        has_cr;
    bool        has_lf;
};

inline LineSpan next_line_span(const char* p, const char* end) {
    LineSpan s{p, p, p, false, false};

    const char* nl = static_cast<const char*>(memchr(p, '\n', (size_t)(end - p)));
    if (nl) {
        s.has_lf   = true;
        s.span_end = nl + 1;
        if (nl > p && *(nl - 1) == '\r') { s.has_cr = true; s.content_end = nl - 1; }
        else                             {                   s.content_end = nl;     }
        return s;
    }
    const char* cr = static_cast<const char*>(memchr(p, '\r', (size_t)(end - p)));
    if (cr) { s.has_cr = true; s.content_end = cr; s.span_end = cr + 1; return s; }
    s.content_end = end; s.span_end = end;
    return s;
}

// ---- iconv conversion ------------------------------------------------------

// Converts [content_begin, content_end) using cd, writing into out.
// Caller must clear() out before calling; existing capacity is reused.
// Returns true if any unconvertible byte was skipped.
bool convert_span(IconvHandle& cd,
                  const char* content_begin,
                  const char* content_end,
                  std::vector<char>& out) {
    const size_t in_len = (size_t)(content_end - content_begin);
    if (in_len == 0) return false;

    char*  inptr  = const_cast<char*>(content_begin); // safe: iconv never writes to inbuf
    size_t inleft = in_len;
    bool   had_invalid = false;

    if (out.capacity() < in_len * 2) out.reserve(in_len * 2);
    out.resize(out.capacity());
    size_t filled = 0;

    while (inleft > 0) {
        char*  outptr  = out.data() + filled;
        size_t outleft = out.size() - filled;
        if (outleft == 0) { out.resize(out.size() * 2); continue; }

        cd.convert(&inptr, &inleft, &outptr, &outleft);
        filled = (size_t)(outptr - out.data());
        if (inleft == 0) break;

        if      (errno == E2BIG)                     { out.resize(out.size() * 2); }
        else if (errno == EILSEQ || errno == EINVAL) { ++inptr; --inleft; had_invalid = true; }
        else throw std::runtime_error("iconv: " + std::string(strerror(errno)));
    }
    out.resize(filled);
    return had_invalid;
}

// ---- Chunk splitting -------------------------------------------------------

// Minimum file size (bytes) before intra-file parallelism kicks in.
// Below this threshold, thread overhead exceeds any gain.
static constexpr size_t MIN_PARALLEL_FILE_SIZE = 2 * 1024 * 1024; // 2 MB

// Splits [data, data+size) into at most `n` contiguous slices, each ending
// on a '\n' boundary (or at the end of the buffer).  The last slice absorbs
// any remainder.
std::vector<std::pair<const char*, const char*>>
make_chunks(const char* data, size_t size, size_t n) {
    std::vector<std::pair<const char*, const char*>> chunks;
    if (n <= 1 || size == 0) {
        chunks.push_back({data, data + size});
        return chunks;
    }

    const size_t target = size / n;
    const char*  p      = data;
    const char*  end    = data + size;

    for (size_t i = 0; i < n - 1 && p < end; ++i) {
        const char* split = p + target;
        if (split >= end) break;
        // Advance to just past the next '\n' so no line straddles two chunks.
        const char* nl = static_cast<const char*>(memchr(split, '\n', (size_t)(end - split)));
        const char* chunk_end = nl ? nl + 1 : end;
        chunks.push_back({p, chunk_end});
        p = chunk_end;
    }
    if (p < end) chunks.push_back({p, end});
    return chunks;
}

// ---- Per-chunk processing --------------------------------------------------

struct ChunkResult {
    std::vector<char> output;       // converted bytes, written to disk in chunk order
    std::string       verbose_log;  // per-line messages, emitted in chunk order after join
    int total_lines    = 0;
    int modified_lines = 0;
    int removed_lines  = 0;
};

// Counts newlines in [p, end) using memchr — O(n) with SIMD acceleration.
// Used to compute the starting line number for each chunk before threads launch.
int count_newlines(const char* p, const char* end) {
    int n = 0;
    while (p < end) {
        p = static_cast<const char*>(memchr(p, '\n', (size_t)(end - p)));
        if (!p) break;
        ++n; ++p;
    }
    return n;
}

ChunkResult process_chunk(const char* begin, const char* end,
                           const CleanOptions& opts,
                           const std::string& filename,
                           int line_offset) {
    ChunkResult result;
    result.output.reserve((size_t)(end - begin));

    IconvHandle       cd(opts.target_encoding, opts.source_encoding);
    std::vector<char> converted;

    const char* p = begin;
    while (p < end) {
        const LineSpan span = next_line_span(p, end);
        ++result.total_lines;

        cd.reset_state();
        converted.clear();
        const bool had_invalid = convert_span(cd, span.content_begin, span.content_end, converted);

        if (had_invalid) {
            ++result.modified_lines;
            if (opts.remove_invalid_lines) ++result.removed_lines;

            if (opts.verbose) {
                const int    line_num  = line_offset + result.total_lines - 1;
                const size_t orig_len  = (size_t)(span.content_end - span.content_begin);
                result.verbose_log
                    += std::string(40, '-') + "\n"
                    +  "File : " + filename + "\n"
                    +  "Line : " + std::to_string(line_num) + "\n"
                    +  "Act  : " + (opts.remove_invalid_lines ? "REMOVED" : "MODIFIED") + "\n"
                    +  "  Before: [" + to_display_utf8(span.content_begin, orig_len,
                                                        opts.source_encoding) + "]\n"
                    +  "  After : [" + to_display_utf8(converted.data(), converted.size(),
                                                        opts.target_encoding) + "]\n";
            }

            if (opts.remove_invalid_lines) { p = span.span_end; continue; }
        }

        result.output.insert(result.output.end(), converted.begin(), converted.end());
        if (span.has_cr) result.output.push_back('\r');
        if (span.has_lf) result.output.push_back('\n');

        p = span.span_end;
    }
    return result;
}

// ---- Output buffering -------------------------------------------------------

class FdWriter {
    int               fd_;
    std::vector<char> buf_;
    bool              error_ = false;

    static constexpr size_t FLUSH_THRESHOLD = 256 * 1024;

    void flush_internal() {
        const char* p   = buf_.data();
        size_t      rem = buf_.size();
        while (rem > 0) {
            ssize_t n = ::write(fd_, p, rem);
            if (n <= 0) { error_ = true; return; }
            p += n; rem -= n;
        }
        buf_.clear();
    }

public:
    FdWriter(int fd, size_t cap = 512 * 1024) : fd_(fd) { buf_.reserve(cap); }

    void append(const char* data, size_t n) {
        if (error_ || n == 0) return;
        buf_.insert(buf_.end(), data, data + n);
        if (buf_.size() >= FLUSH_THRESHOLD) flush_internal();
    }

    void flush() { flush_internal(); }
    bool ok()    const { return !error_; }

    ~FdWriter() { if (!error_) try { flush_internal(); } catch (...) {} }
};

} // namespace

// ---------------------------------------------------------------------------
// clean_single_file
// ---------------------------------------------------------------------------

FileStats clean_single_file(const std::filesystem::path& input_path,
                             const CleanOptions& opts) {
    FileStats stats;

    // ---- mmap input ---------------------------------------------------------
    int in_fd = open(input_path.c_str(), O_RDONLY);
    if (in_fd == -1)
        throw std::runtime_error("open(\"" + input_path.string() + "\"): " + strerror(errno));

    struct stat st{};
    if (fstat(in_fd, &st) == -1) {
        close(in_fd);
        throw std::runtime_error("fstat: " + std::string(strerror(errno)));
    }
    const size_t file_size = (size_t)st.st_size;

    if (file_size == 0) { close(in_fd); return stats; }

    void* mapped = mmap(nullptr, file_size, PROT_READ, MAP_PRIVATE, in_fd, 0);
    close(in_fd);
    if (mapped == MAP_FAILED)
        throw std::runtime_error("mmap: " + std::string(strerror(errno)));

    posix_madvise(mapped, file_size, POSIX_MADV_SEQUENTIAL);

    struct MmapGuard { void* p; size_t n; ~MmapGuard() { munmap(p, n); } }
        mmap_guard{mapped, file_size};

    const char* const data = static_cast<const char*>(mapped);

    // ---- create temp output file --------------------------------------------
    auto try_mkstemp = [](const std::string& dir) -> std::pair<int, std::string> {
        std::string tmpl = dir + "/.clean_XXXXXX";
        std::vector<char> buf(tmpl.begin(), tmpl.end());
        buf.push_back('\0');
        int fd = mkstemp(buf.data());
        if (fd == -1) return {-1, {}};
        return {fd, std::string(buf.data())};
    };

    auto [out_fd, tmp_str] = try_mkstemp(input_path.parent_path().string());
    if (out_fd == -1) {
        std::tie(out_fd, tmp_str) =
            try_mkstemp(std::filesystem::temp_directory_path().string());
        if (out_fd == -1)
            throw std::runtime_error("mkstemp (tried input dir and system temp): "
                                     + std::string(strerror(errno)));
    }

    struct TempGuard {
        const std::string& path; int fd; bool committed = false;
        ~TempGuard() {
            if (fd != -1) ::close(fd);
            if (!committed) { std::error_code ec; std::filesystem::remove(path, ec); }
        }
    } temp_guard{tmp_str, out_fd};

    // ---- decide parallelism -------------------------------------------------
    const size_t nthreads = (file_size < MIN_PARALLEL_FILE_SIZE)
        ? 1
        : std::max(1u, std::thread::hardware_concurrency());

    const auto chunks = make_chunks(data, file_size, nthreads);

    // ---- pre-compute per-chunk starting line numbers ------------------------
    // Only needed for verbose; count_newlines uses SIMD memchr so the scan
    // completes in a few milliseconds even for large files.
    std::vector<int> line_offsets(chunks.size(), 1);
    if (opts.verbose && chunks.size() > 1) {
        int cumulative = 1;
        for (size_t i = 0; i < chunks.size(); ++i) {
            line_offsets[i] = cumulative;
            cumulative += count_newlines(chunks[i].first, chunks[i].second);
        }
    }

    // ---- parallel conversion ------------------------------------------------
    // Each thread writes to its own ChunkResult (output bytes + verbose log).
    // No shared mutable state → no locks during conversion.
    std::vector<ChunkResult> results(chunks.size());

    if (chunks.size() == 1) {
        results[0] = process_chunk(chunks[0].first, chunks[0].second, opts,
                                    input_path.string(), line_offsets[0]);
    } else {
        std::vector<std::thread> threads;
        threads.reserve(chunks.size());
        for (size_t i = 0; i < chunks.size(); ++i) {
            threads.emplace_back([&, i] {
                results[i] = process_chunk(chunks[i].first, chunks[i].second, opts,
                                            input_path.string(), line_offsets[i]);
            });
        }
        for (auto& t : threads) t.join();
    }

    // ---- merge stats --------------------------------------------------------
    for (const auto& r : results) {
        stats.total_lines    += r.total_lines;
        stats.modified_lines += r.modified_lines;
        stats.removed_lines  += r.removed_lines;
    }

    // ---- emit verbose logs in chunk order (after all threads have joined) ---
    if (opts.verbose) {
        for (const auto& r : results)
            if (!r.verbose_log.empty()) std::cerr << r.verbose_log;
    }

    // ---- write output in chunk order ----------------------------------------
    {
        FdWriter out(out_fd);
        for (const auto& r : results)
            out.append(r.output.data(), r.output.size());
        out.flush();
        if (!out.ok())
            throw std::runtime_error("write error on temp file");
    }

    ::close(temp_guard.fd);
    temp_guard.fd = -1;

    if (std::rename(tmp_str.c_str(), input_path.string().c_str()) != 0) {
        if (errno == EXDEV) {
            std::error_code ec;
            std::filesystem::copy_file(tmp_str, input_path,
                                       std::filesystem::copy_options::overwrite_existing, ec);
            std::filesystem::remove(tmp_str, ec);
            if (ec) throw std::runtime_error("cross-device copy failed: " + ec.message());
        } else if (errno == EACCES || errno == EPERM) {
            throw std::runtime_error(
                "no write permission on \"" + input_path.parent_path().string() + "\"");
        } else {
            throw std::runtime_error("rename failed: " + std::string(strerror(errno)));
        }
    }

    temp_guard.committed = true;

    if (opts.verbose) {
        std::cerr << std::string(40, '-') << '\n'
                  << "Processed : " << input_path.string() << '\n'
                  << "  Total    : " << stats.total_lines    << " lines\n"
                  << "  Modified : " << stats.modified_lines << " lines\n"
                  << "  Removed  : " << stats.removed_lines  << " lines\n";
    }
    return stats;
}

// ---------------------------------------------------------------------------
// clean_directory
// ---------------------------------------------------------------------------

size_t clean_directory(const std::filesystem::path& dir, const CleanOptions& opts) {
    Session session(dir, opts.flush_session);

    if (opts.verbose) {
        std::lock_guard lock(g_log_mutex);
        std::cerr << "Session: " << session.already_done() << " file(s) already processed\n";
    }

    std::vector<std::filesystem::path> pending;
    for (const auto& entry : std::filesystem::recursive_directory_iterator(
             dir, std::filesystem::directory_options::skip_permission_denied)) {
        if (!entry.is_regular_file()) continue;
        if (is_internal_file(entry.path())) continue;
        if (session.was_processed(entry.path())) {
            if (opts.verbose) {
                std::lock_guard lock(g_log_mutex);
                std::cerr << "Skip (done): " << entry.path().string() << '\n';
            }
            continue;
        }
        pending.push_back(entry.path());
    }

    if (pending.empty()) { std::cerr << "No files to process.\n"; return 0; }

    const size_t nthreads = std::min<size_t>(
        std::max(1u, std::thread::hardware_concurrency()),
        pending.size());

    std::cerr << "Processing " << pending.size() << " file(s) with "
              << nthreads << " thread(s)...\n";

    std::queue<std::filesystem::path> work;
    for (auto& p : pending) work.push(p);

    std::mutex          queue_mutex;
    std::atomic<size_t> ok{0}, fail{0};

    auto worker = [&] {
        while (true) {
            std::filesystem::path path;
            {
                std::lock_guard lock(queue_mutex);
                if (work.empty()) return;
                path = work.front();
                work.pop();
            }
            try {
                clean_single_file(path, opts);
                session.mark_processed(path);
                ++ok;
            } catch (const std::exception& e) {
                std::lock_guard lock(g_log_mutex);
                std::cerr << "Error [" << path.string() << "]: " << e.what() << '\n';
                ++fail;
            }
        }
    };

    std::vector<std::thread> threads;
    threads.reserve(nthreads);
    for (size_t i = 0; i < nthreads; ++i) threads.emplace_back(worker);
    for (auto& t : threads) t.join();

    if (!opts.keep_session) session.remove();

    std::cerr << "Done: " << ok   << " succeeded, "
                          << fail << " failed"
              << " (out of " << pending.size() << " total).\n";
    return ok.load();
}
