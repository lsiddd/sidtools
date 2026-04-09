project('TextSanitize', 'cpp',
  version: '1.0.0',
  license: 'MIT', # Or choose an appropriate license
  default_options: [
    'cpp_std=c++17',
    'buildtype=release', # Sets optimization to maximum (-O3, etc.)
    'b_lto=true'         # Enables Link Time Optimization for whole program optimization
  ]
)

src_files = [
  'src/main.cc',
  'src/cleaner.cc',
]

dependencies = []

if host_machine.system() != 'windows'
  dependencies += dependency('iconv', required: true)
endif

cpp = meson.get_compiler('cpp')
add_project_arguments(
  cpp.get_supported_arguments(['-Wall', '-Wextra', '-Wpedantic']),
  language: 'cpp'
)

executable('file_cleaner',
  src_files,
  dependencies: dependencies,
  install: true
)