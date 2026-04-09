#pragma once
#include <fstream>
#include <vector>

// Reads one line from ifs as raw bytes including its line ending.
// Returns an empty vector only at EOF with no bytes remaining.
// Handles \n, \r, and \r\n — including the case where \r falls at a
// buffer boundary (the original chunk-based approach got this wrong).
inline std::vector<char> read_line_bytes(std::ifstream& ifs) {
    std::vector<char> line;
    char c;
    while (ifs.get(c)) {
        line.push_back(c);
        if (c == '\n') break;
        if (c == '\r') {
            char next;
            if (ifs.get(next)) {
                if (next == '\n')
                    line.push_back('\n');   // CRLF: consume and include \n
                else
                    ifs.putback(next);      // bare CR: return \n to stream
            }
            break;
        }
    }
    return line;
}

// Returns the trailing newline sequence of raw_line (may be empty for the
// last line in a file with no terminator).
inline std::vector<char> get_line_ending(const std::vector<char>& raw) {
    const size_t n = raw.size();
    if (n >= 2 && raw[n - 2] == '\r' && raw[n - 1] == '\n') return {'\r', '\n'};
    if (n >= 1 && raw[n - 1] == '\n')                        return {'\n'};
    if (n >= 1 && raw[n - 1] == '\r')                        return {'\r'};
    return {};
}

// Returns a copy of bytes with any trailing \r / \n removed.
inline std::vector<char> strip_line_ending(const std::vector<char>& bytes) {
    auto end = bytes.end();
    while (end != bytes.begin() && (*(end - 1) == '\n' || *(end - 1) == '\r'))
        --end;
    return {bytes.begin(), end};
}
