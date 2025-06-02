project('TextSanitize', 'cpp',
  version: '1.0.0',
  license: 'MIT', # Or choose an appropriate license
  default_options: [
    'cpp_std=c++17',
    'buildtype=release', # Sets optimization to maximum (-O3, etc.)
    'b_lto=true'         # Enables Link Time Optimization for whole program optimization
  ]
)

src_files = ['src/MP_main.cc']

dependencies = []

# iconv dependency is needed only on non-Windows systems based on the provided code
if host_machine.system() != 'windows'
  # iconv can be part of libc on some systems, or a separate libiconv
  # Try finding it directly
  iconv_dep = dependency('iconv', required: false)
  if not iconv_dep.found()
      # If not found by just 'iconv', try explicitly searching for the library file if needed,
      # though dependency('iconv') usually handles common cases.
      # A simple dependency check is usually sufficient for standard iconv.
      # Let's make it required if not on Windows, as the code won't compile/link without it.
      iconv_dep = dependency('iconv') # Now make it required
  endif
  dependencies += iconv_dep
endif

# IMPORTANT: Add compiler flags *before* declaring any executables or libraries.
cpp = meson.get_compiler('cpp')
add_project_arguments(
  cpp.get_supported_arguments([
    '-Wall',      # Enable all common warnings
    '-Wextra',    # Enable extra warnings
    '-Wpedantic' # Warn about non-standard language constructs
  ]),
  language : 'cpp'
)

# Define the executable (this comes *after* add_project_arguments)
executable('file_cleaner',
  src_files,
  dependencies: dependencies,
  install: true # Option to install the executable system-wide
)