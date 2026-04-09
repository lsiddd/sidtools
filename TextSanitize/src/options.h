#pragma once
#include <string>
#include <stdexcept>
#include <iostream>
#include <iconv.h>

struct CleanOptions {
    std::string source_encoding = "UTF-8";
    std::string target_encoding = "latin1";
    bool verbose             = false;
    bool remove_invalid_lines = false;
    bool recursive           = false;
    bool force_replace       = false;
    bool flush_session       = false;
    bool keep_session        = false;
};

// Returns true if iconv supports converting from source to target.
inline bool is_valid_encoding_pair(const std::string& from, const std::string& to) {
    iconv_t cd = iconv_open(to.c_str(), from.c_str());
    if (cd == (iconv_t)-1) return false;
    iconv_close(cd);
    return true;
}

struct ParseResult {
    CleanOptions opts;
    std::string  target_path;
    bool         help_requested = false;
};

inline void print_usage(const char* prog) {
    std::cerr
        << "Usage: " << prog << " <path> [options...]\n"
        << "\nOptions:\n"
        << "  -s, --source-encoding ENC   Source encoding (default: UTF-8)\n"
        << "  -t, --target-encoding ENC   Target encoding (default: latin1)\n"
        << "  -v, --verbose               Enable verbose output\n"
        << "  --remove-invalid-lines      Remove lines with unconvertible characters\n"
        << "  -r, --recursive             Process directories recursively\n"
        << "  -f, --force-replace         Permit in-place file replacement\n"
        << "  --flush-session             Discard existing session and reprocess all files\n"
        << "  --keep-session              Retain session file after completion\n"
        << "  -h, --help                  Show this message\n";
}

inline ParseResult parse_args(int argc, char* argv[]) {
    ParseResult result;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        auto next_arg = [&]() -> std::string {
            if (i + 1 >= argc)
                throw std::invalid_argument(arg + " requires an argument");
            return argv[++i];
        };

        if      (arg == "-s" || arg == "--source-encoding")  result.opts.source_encoding    = next_arg();
        else if (arg == "-t" || arg == "--target-encoding")  result.opts.target_encoding    = next_arg();
        else if (arg == "-v" || arg == "--verbose")          result.opts.verbose            = true;
        else if (arg == "--remove-invalid-lines")            result.opts.remove_invalid_lines = true;
        else if (arg == "-r" || arg == "--recursive")        result.opts.recursive          = true;
        else if (arg == "-f" || arg == "--force-replace")    result.opts.force_replace      = true;
        else if (arg == "--flush-session")                   result.opts.flush_session      = true;
        else if (arg == "--keep-session")                    result.opts.keep_session       = true;
        else if (arg == "-h" || arg == "--help")             result.help_requested          = true;
        else if (!arg.empty() && arg[0] == '-')
            throw std::invalid_argument("Unknown option: " + arg);
        else {
            if (!result.target_path.empty())
                throw std::invalid_argument("Unexpected argument: " + arg);
            result.target_path = arg;
        }
    }

    return result;
}
