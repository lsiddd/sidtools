# TextSanitize

Multi-threaded CLI for converting text file encodings in-place. Reads from any encoding, converts to a target via `iconv`, and handles the ugly cases, dropping unrepresentable bytes or nuking the entire offending line.

Useful when you inherit a pile of latin1 files that insist they're UTF-8, or when a legacy pipeline refuses to eat anything but ASCII.

## Features

- Any encoding pair supported by `iconv` on your system
- Atomic in-place replacement via temp file + `rename(2)` — no partial overwrites
- Two strategies for unconvertible characters: drop bytes or remove the whole line
- Recursive directory processing, parallelised across all CPU cores
- Session resumption for interrupted directory runs
- Verbose mode showing before/after for every modified line

## Build

### Prerequisites

- C++17 compiler (GCC >= 8, Clang >= 7)
- [Meson](https://mesonbuild.com/) + [Ninja](https://ninja-build.org/)
- POSIX system (Linux or macOS) — uses `mmap`, `mkstemp`, `iconv`

**Debian/Ubuntu:**
```bash
sudo apt install build-essential meson ninja-build
```

**Fedora/RHEL:**
```bash
sudo dnf install gcc-c++ meson ninja-build
```

**macOS (Homebrew):**
```bash
brew install meson ninja
```

### Compile

```bash
meson setup build
meson compile -C build
```

Binary lands at `build/file_cleaner`. To install system-wide:

```bash
meson install -C build   # installs to /usr/local/bin by default
```

## Usage

```
file_cleaner <path> [options...]
```

| Option | Default | Description |
|---|---|---|
| `-s`, `--source-encoding ENC` | `UTF-8` | Encoding of the input files |
| `-t`, `--target-encoding ENC` | `latin1` | Encoding to convert to |
| `-v`, `--verbose` | off | Print each modified/removed line with before and after |
| `--remove-invalid-lines` | off | Remove lines containing unconvertible characters entirely |
| `-r`, `--recursive` | off | Required when `<path>` is a directory |
| `-f`, `--force-replace` | off | Required for any in-place modification (safety gate) |
| `--flush-session` | off | Ignore existing session and reprocess all files |
| `--keep-session` | off | Do not delete the session file on completion |
| `-h`, `--help` | — | Print this reference |

Run `iconv --list` to see all encoding names supported on your system.

## Examples

**Convert a single file from UTF-8 to latin1:**
```bash
file_cleaner document.txt -t latin1 -f
```

**Show every changed line:**
```bash
file_cleaner document.txt -t latin1 -f -v
```

**Drop entire lines that can't be represented in the target encoding:**
```bash
file_cleaner document.txt -t latin1 -f --remove-invalid-lines
```

**Recursively convert a directory tree:**
```bash
file_cleaner ./data -t ISO-8859-1 -r -f
```

**Resume an interrupted run** (completed files are skipped automatically):
```bash
file_cleaner ./data -t ISO-8859-1 -r -f
```

**Start fresh, ignoring any previous session:**
```bash
file_cleaner ./data -t ISO-8859-1 -r -f --flush-session
```

**Convert from a non-UTF-8 source:**
```bash
file_cleaner ./legacy -s latin1 -t UTF-8 -r -f
```

## How it works

Each file goes through this pipeline:

1. Memory-mapped with `mmap` — no buffered I/O overhead on reads.
2. Lines located via `memchr` — no per-character parsing.
3. Each line handed to `iconv`. Line endings (`\n`, `\r\n`, `\r`) are preserved as-is.
4. On `EILSEQ`, the offending byte is dropped. If `--remove-invalid-lines` is set, the line is skipped entirely.
5. Output written through a 512 KB buffer to a temp file in the same directory.
6. Temp file atomically replaces the original via `rename(2)`.

Directory processing spawns one worker thread per logical CPU core. Threads pull files from a shared queue independently. A `.clean_session` file in the target directory records completed files so interrupted runs can be resumed without reprocessing.

## License

MIT
