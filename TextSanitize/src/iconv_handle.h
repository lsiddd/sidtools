#pragma once
#include <iconv.h>
#include <stdexcept>
#include <string>
#include <cerrno>
#include <cstring>

// RAII wrapper for iconv_t. Non-copyable, movable.
class IconvHandle {
    iconv_t cd_;

public:
    IconvHandle(const std::string& to, const std::string& from) {
        cd_ = iconv_open(to.c_str(), from.c_str());
        if (cd_ == (iconv_t)-1)
            throw std::runtime_error(
                "iconv_open(\"" + to + "\", \"" + from + "\"): " + strerror(errno));
    }

    ~IconvHandle() {
        if (cd_ != (iconv_t)-1) iconv_close(cd_);
    }

    IconvHandle(const IconvHandle&)            = delete;
    IconvHandle& operator=(const IconvHandle&) = delete;

    IconvHandle(IconvHandle&& o) noexcept : cd_(o.cd_) {
        o.cd_ = (iconv_t)-1;
    }

    // Reset shift state without consuming input (required between independent conversions).
    void reset_state() noexcept {
        iconv(cd_, nullptr, nullptr, nullptr, nullptr);
    }

    // Thin wrapper around iconv(3). Returns (size_t)-1 and sets errno on error.
    size_t convert(char** inbuf,  size_t* inbytesleft,
                   char** outbuf, size_t* outbytesleft) noexcept {
        return iconv(cd_, inbuf, inbytesleft, outbuf, outbytesleft);
    }
};
