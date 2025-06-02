#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <filesystem>
#include <cstdio>
#include <cerrno>
#include <cstring>
#include <algorithm>
#include <thread>
#include <future>
#include <deque>
#include <mutex>
#include <condition_variable>
#include <queue>
#include <set>

#include <unistd.h> // For close, mkstemp
#include <iconv.h>  // For iconv functions
#include <fcntl.h>  // For file flags like O_RDWR, O_CREAT, O_EXCL, O_BINARY (though binary is implicit on POSIX)

// Global mutexes for synchronization
std::mutex g_verbose_mutex;
std::mutex g_session_file_mutex;

struct CleanOptions {
    std::string target_encoding;
    bool verbose;
    bool remove_invalid_lines;
    bool recursive;
    bool force_replace;
    bool flush_session;
    bool keep_session;
};

std::string bytes_to_display_string_robust(const std::vector<char>& bytes, const std::string& from_encoding) {
    if (bytes.empty()) return "";

    iconv_t cd = iconv_open("UTF-8//TRANSLIT", from_encoding.c_str());
    if (cd == (iconv_t)-1) {
        std::lock_guard<std::mutex> lock(g_verbose_mutex);
        std::cerr << "Warning: Could not open iconv for display string conversion (from " 
                  << from_encoding << " to UTF-8//TRANSLIT): " << strerror(errno) << std::endl;
        return std::string(bytes.begin(), bytes.end());
    }

    std::vector<char> in_buf = bytes;
    char *inptr = in_buf.data();
    size_t inbytesleft = in_buf.size();

    std::string result_str;
    std::vector<char> out_buf(in_buf.size() * 4 + 1, 0);

    iconv(cd, nullptr, nullptr, nullptr, nullptr); // Reset iconv state

    while (inbytesleft > 0) {
        char *outptr = out_buf.data();
        size_t outbytesleft = out_buf.size();
        
        size_t res = iconv(cd, &inptr, &inbytesleft, &outptr, &outbytesleft);

        result_str.append(out_buf.data(), outptr - out_buf.data());

        if (res == (size_t)-1) {
            if (errno == EILSEQ || errno == EINVAL) {
                if (inbytesleft > 0) {
                    inptr++;
                    inbytesleft--;
                    result_str += "\ufffd"; // Replacement character
                } else {
                    break;
                }
            } else if (errno == E2BIG) {
                out_buf.resize(out_buf.size() * 2);
            } else {
                std::lock_guard<std::mutex> lock(g_verbose_mutex);
                std::cerr << "Error during display string iconv conversion: " << strerror(errno) << std::endl;
                iconv_close(cd);
                return result_str + "<Error>";
            }
        }
    }
    iconv_close(cd);
    return result_str;
}

// Optimized version that reads larger chunks
std::vector<char> read_line_bytes(std::ifstream& ifs) {
    const size_t BUFFER_SIZE = 4096;
    static thread_local std::vector<char> buffer(BUFFER_SIZE);
    std::vector<char> line_bytes;

    while (ifs) {
        // Read a chunk
        ifs.read(buffer.data(), BUFFER_SIZE);
        size_t read_count = ifs.gcount();
        if (read_count == 0) break;

        // Find newline in the chunk
        char* start = buffer.data();
        char* end = start + read_count;
        char* pos = std::find_if(start, end, [](char c) {
            return c == '\n' || c == '\r';
        });

        if (pos != end) {
            // Found a newline - copy everything up to and including the newline
            size_t chunk_size = pos - start + 1;
            line_bytes.insert(line_bytes.end(), start, start + chunk_size);
            
            // Check for \r\n sequence
            if (*pos == '\r' && (pos + 1 < end) && *(pos + 1) == '\n') {
                line_bytes.push_back('\n');
                // Adjust stream position to account for the extra char taken by read_line_bytes logic
                // This is specifically for when \r\n is read in one chunk, and we process it as two characters,
                // but std::find_if only finds \r. The subsequent read_line_bytes would re-read \n
                // No, this seekg is incorrect if the full \r\n was in the `read_count` chunk.
                // The current logic of `pos - start + 1` takes only the `\r` and the `\n` is left for next iteration.
                // If the `\n` is in the same chunk and we handle it, then `pos+1` should effectively consume it.
                // Re-evaluating: If `pos` is `\r`, `pos+1` might be `\n`.
                // `pos - start + 1` copies `\r`. If `pos+1` is `\n` and it's within `end`,
                // then we manually add `\n` and advance the file pointer.
                // `seekg(1, std::ios_base::cur)` is correct here IF `pos` was `\r` and the `\n` followed immediately.
                // This correctly "consumes" the `\n` for the next `read_line_bytes` call.
                ifs.seekg(1, std::ios_base::cur); // Consume the second char of CRLF
            }
            
            // Put back any extra bytes we read beyond the newline
            size_t extra_bytes = end - (pos + 1);
            if (extra_bytes > 0) {
                ifs.seekg(-static_cast<std::streamoff>(extra_bytes), std::ios_base::cur);
            }
            break;
        } else {
            // No newline found - add entire chunk
            line_bytes.insert(line_bytes.end(), start, end);
        }
    }
    return line_bytes;
}

std::vector<char> get_line_ending(const std::vector<char>& raw_line) {
    if (raw_line.size() >= 2 && raw_line[raw_line.size() - 2] == '\r' && raw_line.back() == '\n') {
        return {'\r', '\n'};
    } else if (!raw_line.empty() && raw_line.back() == '\n') {
        return {'\n'};
    } else if (!raw_line.empty() && raw_line.back() == '\r') {
        return {'\r'};
    }
    return {};
}

std::vector<char> rstrip_newlines(const std::vector<char>& bytes) {
    std::vector<char> stripped = bytes;
    while (!stripped.empty() && (stripped.back() == '\n' || stripped.back() == '\r')) {
        stripped.pop_back();
    }
    return stripped;
}

bool is_temporary_file(const std::filesystem::path& p) {
    const std::string filename = p.filename().string();
    return (filename.length() == 13 && filename.substr(0, 7) == ".clean_") ||
           (filename == ".clean_session");
}

bool clean_single_file(const std::filesystem::path& input_path, const CleanOptions& opts) {
    std::string temp_output_path_str;
    std::ofstream outfile;
    int modified_lines_count = 0;
    int removed_lines_count = 0;
    int total_lines_count = 0;
    iconv_t cd = (iconv_t)-1;

    try {
        // Temporary file creation (POSIX mkstemp)
        std::string temp_template = input_path.parent_path().string() + "/.clean_XXXXXX";
        std::vector<char> temp_path_vec(temp_template.begin(), temp_template.end());
        temp_path_vec.push_back('\0');
        
        int fd = mkstemp(temp_path_vec.data());
        if (fd == -1) {
            throw std::runtime_error("Failed to create temporary file: " + std::string(strerror(errno)));
        }
        close(fd); // Close the file descriptor, as ofstream will open it again
        temp_output_path_str = temp_path_vec.data();

        outfile.open(temp_output_path_str, std::ios::binary);
        if (!outfile.is_open()) {
            throw std::runtime_error("Failed to open temporary file: " + std::string(strerror(errno)));
        }

        std::ifstream infile(input_path, std::ios::binary);
        if (!infile.is_open()) {
            throw std::runtime_error("Failed to open input file: " + std::string(strerror(errno)));
        }

        // Increase buffer size for better performance
        const size_t BUF_SIZE = 64 * 1024;
        std::vector<char> in_buf(BUF_SIZE);
        infile.rdbuf()->pubsetbuf(in_buf.data(), BUF_SIZE);

        cd = iconv_open(opts.target_encoding.c_str(), "UTF-8");
        if (cd == (iconv_t)-1) {
            if (errno == EINVAL) {
                throw std::runtime_error("Unsupported encoding: " + opts.target_encoding);
            } else {
                throw std::runtime_error("iconv initialization failed: " + std::string(strerror(errno)));
            }
        }

        while (infile.good()) {
            std::vector<char> raw_line_bytes = read_line_bytes(infile);
            if (raw_line_bytes.empty() && infile.eof()) break;

            total_lines_count++;
            bool line_had_unconvertible_chars = false;
            std::vector<char> cleaned_bytes_vec;

            iconv(cd, nullptr, nullptr, nullptr, nullptr); // Reset iconv state for new line

            std::vector<char> current_line_input = raw_line_bytes;
            char *inptr = current_line_input.data();
            size_t inbytesleft = current_line_input.size();

            const size_t INITIAL_BUFFER_SIZE = 1024;
            std::vector<char> out_buffer(INITIAL_BUFFER_SIZE);

            while (inbytesleft > 0) {
                char *outptr = out_buffer.data();
                size_t outbytesleft = out_buffer.size();

                size_t res = iconv(cd, &inptr, &inbytesleft, &outptr, &outbytesleft);
                size_t converted_bytes = outptr - out_buffer.data();
                cleaned_bytes_vec.insert(cleaned_bytes_vec.end(), out_buffer.begin(), out_buffer.begin() + converted_bytes);

                if (res == (size_t)-1) {
                    if (errno == E2BIG) {
                        out_buffer.resize(out_buffer.size() * 2);
                    } else if (errno == EILSEQ || errno == EINVAL) {
                        if (inbytesleft > 0) {
                            inptr++;
                            inbytesleft--;
                            line_had_unconvertible_chars = true;
                        } else {
                            break;
                        }
                    } else {
                        throw std::runtime_error("iconv error: " + std::string(strerror(errno)));
                    }
                }
            }

            bool line_was_modified = line_had_unconvertible_chars;
            if (line_was_modified) {
                modified_lines_count++;
                if (opts.verbose) {
                    std::lock_guard<std::mutex> lock(g_verbose_mutex);
                    std::cerr << std::string(40, '-') << std::endl;
                    std::cerr << "File: " << input_path.string() << std::endl;
                    std::cerr << "Line " << total_lines_count << ":" << std::endl;
                    
                    if (opts.remove_invalid_lines) {
                        std::cerr << "Action: REMOVED" << std::endl;
                        removed_lines_count++;
                    } else {
                        std::cerr << "Action: MODIFIED" << std::endl;
                    }
                    
                    std::vector<char> original_content = rstrip_newlines(raw_line_bytes);
                    std::vector<char> cleaned_content = rstrip_newlines(cleaned_bytes_vec);
                    
                    std::string original_display = bytes_to_display_string_robust(original_content, "UTF-8");
                    std::string cleaned_display = bytes_to_display_string_robust(cleaned_content, opts.target_encoding);
                    
                    std::cerr << "Original: [" << original_display << "]" << std::endl;
                    std::cerr << "Cleaned : [" << cleaned_display << "]" << std::endl;
                }
            }

            bool should_write_line = !opts.remove_invalid_lines || !line_was_modified;
            if (should_write_line) {
                std::vector<char> newline_seq = get_line_ending(raw_line_bytes);
                std::vector<char> cleaned_content = rstrip_newlines(cleaned_bytes_vec);
                
                if (!cleaned_content.empty()) {
                    outfile.write(cleaned_content.data(), cleaned_content.size());
                }
                if (!newline_seq.empty()) {
                    outfile.write(newline_seq.data(), newline_seq.size());
                }
            }
        }

        infile.close();
        outfile.close();

        if (cd != (iconv_t)-1) {
            iconv_close(cd);
            cd = (iconv_t)-1;
        }

        // Always replace original file (POSIX rename)
        if (std::rename(temp_output_path_str.c_str(), input_path.string().c_str()) != 0) {
            throw std::runtime_error("File replacement failed: " + std::string(strerror(errno)));
        }

        if (opts.verbose) {
            std::lock_guard<std::mutex> lock(g_verbose_mutex);
            std::cerr << std::string(40, '-') << std::endl;
            std::cerr << "--- File Processed: " << input_path.string() << " ---" << std::endl;
            std::cerr << "Total lines: " << total_lines_count << std::endl;
            std::cerr << "Modified lines: " << modified_lines_count << std::endl;
            if (opts.remove_invalid_lines) {
                std::cerr << "Removed lines: " << removed_lines_count << std::endl;
            }
            std::cerr << std::string(40, '-') << std::endl;
        }

        return true;

    } catch (const std::exception& e) {
        std::lock_guard<std::mutex> lock(g_verbose_mutex);
        std::cerr << "Error processing '" << input_path.string() << "': " << e.what() << std::endl;
        
        if (!temp_output_path_str.empty()) {
            std::error_code ec;
            if (std::filesystem::exists(temp_output_path_str, ec)) {
                if (!std::filesystem::remove(temp_output_path_str, ec)) {
                    std::cerr << "Failed to clean up temp file: " << ec.message() << std::endl;
                }
            }
        }
        if (cd != (iconv_t)-1) {
            iconv_close(cd);
        }
        return false;
    }
}

void record_processed_file(const std::filesystem::path& session_file, const std::filesystem::path& file, bool verbose) {
    std::lock_guard<std::mutex> lock(g_session_file_mutex);
    std::ofstream out(session_file, std::ios::app);
    if (out) {
        out << std::filesystem::absolute(file).string() << '\n';
        if (verbose) {
            std::lock_guard<std::mutex> verbose_lock(g_verbose_mutex);
            std::cerr << "Recorded processed file: " << file.string() << std::endl;
        }
    } else if (verbose) {
        std::lock_guard<std::mutex> verbose_lock(g_verbose_mutex);
        std::cerr << "Warning: Failed to record processed file: " << file.string() << std::endl;
    }
}

int main(int argc, char* argv[]) {
    CleanOptions opts;
    opts.target_encoding = "latin1";
    opts.verbose = false;
    opts.remove_invalid_lines = false;
    opts.recursive = false;
    opts.force_replace = false;
    opts.flush_session = false;
    opts.keep_session = false;

    std::string target_path_str;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "-t" || arg == "--target-encoding") {
            if (i + 1 < argc) {
                opts.target_encoding = argv[++i];
            } else {
                std::cerr << "Error: --target-encoding requires an argument." << std::endl;
                return 1;
            }
        } else if (arg == "-v" || arg == "--verbose") {
            opts.verbose = true;
        } else if (arg == "--remove-invalid-lines") {
            opts.remove_invalid_lines = true;
        } else if (arg == "-r" || arg == "--recursive") {
            opts.recursive = true;
        } else if (arg == "-f" || arg == "--force-replace") {
            opts.force_replace = true;
        } else if (arg == "--flush-session") {
            opts.flush_session = true;
        } else if (arg == "--keep-session") {
            opts.keep_session = true;
        } else {
            if (target_path_str.empty()) {
                target_path_str = arg;
            } else {
                std::cerr << "Error: Unexpected argument '" << arg << "'" << std::endl;
                return 1;
            }
        }
    }

    if (target_path_str.empty()) {
        std::cerr << "Usage: " << argv[0] << " <path> [options...]" << std::endl;
        std::cerr << "Options:" << std::endl;
        std::cerr << "  -t, --target-encoding ENC   Set target encoding (default: latin1)" << std::endl;
        std::cerr << "  -v, --verbose                Enable verbose output" << std::endl;
        std::cerr << "  --remove-invalid-lines       Remove lines with unconvertible characters" << std::endl;
        std::cerr << "  -r, --recursive              Process directories recursively" << std::endl;
        std::cerr << "  -f, --force-replace          Force file replacement" << std::endl;
        std::cerr << "  --flush-session              Start new session (ignore existing progress)" << std::endl;
        std::cerr << "  --keep-session               Keep session file after completion" << std::endl;
        return 1;
    }

    std::filesystem::path target_path = target_path_str;

    if (!std::filesystem::exists(target_path)) {
        std::cerr << "Error: Path not found: " << target_path.string() << std::endl;
        return 1;
    }

    if (std::filesystem::is_regular_file(target_path)) {
        if (!opts.force_replace) {
            std::cerr << "Error: --force-replace required for file processing" << std::endl;
            return 1;
        }
        clean_single_file(target_path, opts);
    } 
    else if (std::filesystem::is_directory(target_path)) {
        if (!opts.recursive) {
            std::cerr << "Error: Use -r for directory processing" << std::endl;
            return 1;
        }
        if (!opts.force_replace) {
            std::cerr << "Error: --force-replace required for directory processing" << std::endl;
            return 1;
        }

        // Session file handling
        std::filesystem::path session_file = target_path / ".clean_session";
        std::set<std::string> processed_files;

        // Flush session if requested
        if (opts.flush_session && std::filesystem::exists(session_file)) {
            std::error_code ec;
            if (!std::filesystem::remove(session_file, ec) && opts.verbose) {
                std::lock_guard<std::mutex> lock(g_verbose_mutex);
                std::cerr << "Warning: Failed to remove session file: " << ec.message() << std::endl;
            }
        }

        // Load existing session
        if (std::filesystem::exists(session_file)) {
            std::ifstream in(session_file);
            if (in) {
                std::string line;
                while (std::getline(in, line)) {
                    if (!line.empty()) {
                        processed_files.insert(line);
                    }
                }
                if (opts.verbose) {
                    std::lock_guard<std::mutex> lock(g_verbose_mutex);
                    std::cerr << "Resuming from session: " << processed_files.size() 
                              << " files already processed" << std::endl;
                }
            } else if (opts.verbose) {
                std::lock_guard<std::mutex> lock(g_verbose_mutex);
                std::cerr << "Warning: Failed to open session file: " << session_file << std::endl;
            }
        }

        // Collect files to process
        std::vector<std::filesystem::path> files_to_process;
        for (const auto& entry : std::filesystem::recursive_directory_iterator(target_path)) {
            if (entry.is_regular_file() && !is_temporary_file(entry.path())) {
                std::string abs_path = std::filesystem::absolute(entry.path()).string();
                if (processed_files.find(abs_path) == processed_files.end()) {
                    files_to_process.push_back(entry.path());
                } else if (opts.verbose) {
                    std::lock_guard<std::mutex> lock(g_verbose_mutex);
                    std::cerr << "Skipping already processed file: " << entry.path().string() << std::endl;
                }
            }
        }

        if (files_to_process.empty()) {
            std::cerr << "No files to process." << std::endl;
            return 0;
        }

        if (opts.verbose) {
            std::lock_guard<std::mutex> lock(g_verbose_mutex);
            std::cerr << "Files to process: " << files_to_process.size() << std::endl;
        }

        // Thread pool setup
        size_t max_threads = std::max(1u, std::thread::hardware_concurrency());
        max_threads = std::min(max_threads, files_to_process.size());

        std::queue<std::filesystem::path> file_queue;
        for (const auto& file : files_to_process) {
            file_queue.push(file);
        }

        std::mutex queue_mutex;
        std::vector<std::thread> workers;
        std::atomic<size_t> files_processed(0);
        bool stop_workers = false; // Not strictly needed with empty check, but good practice

        auto worker = [&]() {
            while (true) {
                std::filesystem::path file_path;
                {
                    std::unique_lock<std::mutex> lock(queue_mutex);
                    if (file_queue.empty()) { // Check only for emptiness to stop
                        break;
                    }
                    file_path = file_queue.front();
                    file_queue.pop();
                }
                
                bool success = clean_single_file(file_path, opts);
                if (success) {
                    record_processed_file(session_file, file_path, opts.verbose);
                    files_processed++;
                }
            }
        };

        // Start workers
        for (size_t i = 0; i < max_threads; ++i) {
            workers.emplace_back(worker);
        }

        // Join workers
        for (auto& worker : workers) {
            if (worker.joinable()) {
                worker.join();
            }
        }

        // Clean up session file
        if (!opts.keep_session && std::filesystem::exists(session_file)) {
            std::error_code ec;
            if (!std::filesystem::remove(session_file, ec) && opts.verbose) {
                std::lock_guard<std::mutex> lock(g_verbose_mutex);
                std::cerr << "Warning: Failed to remove session file: " << ec.message() << std::endl;
            }
        }

        if (opts.verbose) {
            std::lock_guard<std::mutex> lock(g_verbose_mutex);
            std::cerr << "Processed " << files_processed << " of " << files_to_process.size()
                      << " files successfully." << std::endl;
        }
    } 
    else {
        std::cerr << "Error: Not a file or directory: " << target_path.string() << std::endl;
        return 1;
    }

    return 0;
}