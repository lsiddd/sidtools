#include <iostream>
#include <filesystem>
#include "options.h"
#include "cleaner.h"

int main(int argc, char* argv[]) {
    ParseResult parsed;
    try {
        parsed = parse_args(argc, argv);
    } catch (const std::invalid_argument& e) {
        std::cerr << "Error: " << e.what() << '\n';
        print_usage(argv[0]);
        return 1;
    }

    if (parsed.help_requested) {
        print_usage(argv[0]);
        return 0;
    }
    if (parsed.target_path.empty()) {
        print_usage(argv[0]);
        return 1;
    }

    const CleanOptions& opts = parsed.opts;

    // Validate encoding pair up front — fail fast before touching any file.
    if (!is_valid_encoding_pair(opts.source_encoding, opts.target_encoding)) {
        std::cerr << "Error: cannot convert from \"" << opts.source_encoding
                  << "\" to \"" << opts.target_encoding
                  << "\" (iconv does not support this pair)\n";
        return 1;
    }

    const std::filesystem::path target(parsed.target_path);

    if (!std::filesystem::exists(target)) {
        std::cerr << "Error: path not found: " << target << '\n';
        return 1;
    }

    if (std::filesystem::is_regular_file(target)) {
        if (!opts.force_replace) {
            std::cerr << "Error: use -f / --force-replace to permit in-place modification\n";
            return 1;
        }
        try {
            const FileStats stats = clean_single_file(target, opts);
            if (!opts.verbose) {
                std::cerr << "Done: " << stats.total_lines    << " total, "
                                      << stats.modified_lines << " modified, "
                                      << stats.removed_lines  << " removed.\n";
            }
        } catch (const std::exception& e) {
            std::cerr << "Error: " << e.what() << '\n';
            return 1;
        }

    } else if (std::filesystem::is_directory(target)) {
        if (!opts.recursive) {
            std::cerr << "Error: use -r / --recursive for directory processing\n";
            return 1;
        }
        if (!opts.force_replace) {
            std::cerr << "Error: use -f / --force-replace to permit in-place modification\n";
            return 1;
        }
        clean_directory(target, opts);

    } else {
        std::cerr << "Error: not a regular file or directory: " << target << '\n';
        return 1;
    }

    return 0;
}
