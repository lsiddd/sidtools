import os
import shutil
import sys
import argparse
import time
import re
import uuid
import datetime

def resolve_conflict(target_path, dry_run=False, style='number'):
    """Resolves naming conflicts by appending a number, timestamp, or UUID to the base name."""
    if not os.path.exists(target_path):
        return target_path

    dirname, basename = os.path.split(target_path)
    name, ext = os.path.splitext(basename)
    
    if dry_run:
         print(f"DRY RUN: Conflict detected for '{basename}'.")
    else:
         print(f"Conflict detected for '{basename}'.")

    if style == 'number':
        counter = 1
        new_basename = f"{name}({counter}){ext}"
        new_target_path = os.path.join(dirname, new_basename)
        while os.path.exists(new_target_path):
            counter += 1
            new_basename = f"{name}({counter}){ext}"
            new_target_path = os.path.join(dirname, new_basename)
        if dry_run:
            print(f"DRY RUN: Would resolve to '{os.path.basename(new_target_path)}' using number style.")
        else:
            print(f"Resolved to '{os.path.basename(new_target_path)}' using number style.")
        return new_target_path

    elif style == 'timestamp':
        # Append timestamp, fallback to number if timestamp + original name still conflicts (unlikely but possible)
        timestamp_str = datetime.datetime.now().strftime("_%Y%m%d_%H%M%S")
        new_basename = f"{name}{timestamp_str}{ext}"
        new_target_path = os.path.join(dirname, new_basename)
        counter = 1
        original_new_target_path = new_target_path
        while os.path.exists(new_target_path):
            counter += 1
            new_basename = f"{name}{timestamp_str}({counter}){ext}" # Add counter after timestamp
            new_target_path = os.path.join(dirname, new_basename)

        if dry_run:
            print(f"DRY RUN: Would resolve to '{os.path.basename(new_target_path)}' using timestamp style.")
        else:
            print(f"Resolved to '{os.path.basename(new_target_path)}' using timestamp style.")
        return new_target_path


    elif style == 'uuid':
        # Append UUID - conflicts are extremely improbable
        uuid_str = uuid.uuid4().hex
        new_basename = f"{name}_{uuid_str}{ext}"
        new_target_path = os.path.join(dirname, new_basename)
        # While loop technically not needed for UUID but kept for robustness against bizarre edge cases
        counter = 1
        original_new_target_path = new_target_path
        while os.path.exists(new_target_path):
             counter += 1
             new_basename = f"{name}_{uuid_str}({counter}){ext}"
             new_target_path = os.path.join(dirname, new_basename)

        if dry_run:
            print(f"DRY RUN: Would resolve to '{os.path.basename(new_target_path)}' using UUID style.")
        else:
            print(f"Resolved to '{os.path.basename(new_target_path)}' using UUID style.")
        return new_target_path

    else:
        # Fallback to number style for any unknown style
        print(f"Warning: Unknown conflict resolution style '{style}'. Falling back to 'number'.")
        return resolve_conflict(target_path, dry_run=dry_run, style='number')


def move_item(source_path, target_dir, dry_run=False, conflict_resolution_style='number'):
    """Moves an item (file or directory) to a target directory, resolving conflicts."""
    if not os.path.exists(source_path):
        print(f"Warning: Source path does not exist: {source_path}. Skipping move.")
        return False
        
    if os.path.islink(source_path):
        if dry_run:
            print(f"DRY RUN: Would skip symbolic link: {source_path}")
        else:
            print(f"Skipping symbolic link: {source_path}")
        return False

    if not os.path.isdir(target_dir):
        if dry_run:
            print(f"DRY RUN: Would create target directory: {target_dir}")
        else:
            print(f"Creating target directory: {target_dir}")
            try:
                os.makedirs(target_dir, exist_ok=True)
            except OSError as e:
                print(f"Error creating directory {target_dir}: {e}")
                return False

    item_name = os.path.basename(source_path)
    potential_target_path = os.path.join(target_dir, item_name)
    
    # Resolve conflict using the specified style
    resolved_target_path = resolve_conflict(potential_target_path, dry_run, conflict_resolution_style)

    if dry_run:
        print(f"DRY RUN: Would move '{source_path}' to '{resolved_target_path}'")
        return True # In dry run, we assume the move *would* succeed for reporting purposes
    else:
        try:
            print(f"Moving '{source_path}' to '{resolved_target_path}'")
            shutil.move(source_path, resolved_target_path)
            return True
        except PermissionError:
            print(f"Permission denied to move '{source_path}'. Skipping.")
            return False
        except Exception as e:
            print(f"Error moving '{source_path}' to '{resolved_target_path}': {e}")
            return False

def find_and_move_git(source_dir, dest_dir, dry_run=False, include_hidden=False, conflict_resolution_style='number'):
    """Finds git repositories and moves them to a 'git' subdirectory in dest_dir."""
    git_target_dir = os.path.join(dest_dir, 'git')
    print(f"Scanning '{source_dir}' for Git repositories...")
    found_repos = []

    # Using os.walk with topdown=True allows modifying dirs in place to skip directories
    # os.walk uses os.scandir internally to list directory entries efficiently.
    for root, dirs, files in os.walk(source_dir, topdown=True, onerror=lambda e: print(f"Error accessing directory: {e}")):

        # If include_hidden is False, filter out hidden directories from the list *before* processing
        # This prevents descending into hidden directories at all.
        if not include_hidden:
            # Create a new list of directories to process at this level and for recursion
            dirs[:] = [d for d in dirs if not d.startswith('.')]

        # Check if the current directory or any directory above is a symlink
        # If the root itself is a symlink, os.walk might behave differently or the check below will catch it.
        # A more robust check is needed before starting walk if source_dir itself is a symlink.
        # For links found *during* walk, we'll handle them in the move_item call.

        # Check for .git directory to identify repository root
        if '.git' in dirs:
             repo_root = root

             # Avoid processing repositories already within the target git directory
             if os.path.commonpath([repo_root, git_target_dir]) == git_target_dir:
                 if dry_run:
                     print(f"DRY RUN: Would skip '{repo_root}': Already appears to be under the target git directory.")
                 else:
                    print(f"Skipping '{repo_root}': Already appears to be under the target git directory.")
                 # Don't traverse into this directory if it's a git repo we're handling or skipping
                 dirs[:] = []
                 continue

             if repo_root not in found_repos:
                 found_repos.append(repo_root)
                 print(f"Found Git repository: {repo_root}")

             # Found a git repo, no need to traverse further down this path in os.walk
             dirs[:] = []
             continue

    print(f"\nFound {len(found_repos)} Git repositories.")
    if not found_repos:
        print("No Git repositories found.")
        return

    print(f"Moving repositories to '{git_target_dir}'...")
    moved_count = 0
    for repo_path in found_repos:
         if os.path.exists(repo_path):
            # move_item handles symlink check for the repo_path itself
            if move_item(repo_path, git_target_dir, dry_run, conflict_resolution_style):
                moved_count += 1
         else:
             print(f"Warning: Git repository path no longer exists: {repo_path}. Skipping move.")

    if dry_run:
        print(f"Git repository organization DRY RUN complete. Would move {moved_count} repositories.")
    else:
        print(f"Git repository organization complete. {moved_count} repositories moved.")


def find_and_remove_unwanted(source_dir, dry_run=False, include_hidden=False):
    """Finds and removes unwanted files and directories based on predefined patterns."""
    unwanted_patterns = [
        re.compile(r'^__pycache__$', re.IGNORECASE),
        re.compile(r'^\.venv$', re.IGNORECASE),
        re.compile(r'^venv$', re.IGNORECASE),
        re.compile(r'^env$', re.IGNORECASE),
        re.compile(r'^node_modules$', re.IGNORECASE),
        re.compile(r'^target$', re.IGNORECASE),
        re.compile(r'^build$', re.IGNORECASE),
        re.compile(r'^dist$', re.IGNORECASE),
        re.compile(r'^\.mypy_cache$', re.IGNORECASE),
        re.compile(r'^\.pytest_cache$', re.IGNORECASE),
        re.compile(r'^\.cache$', re.IGNORECASE),
        re.compile(r'^\.Trash-\d+$', re.IGNORECASE),
        re.compile(r'^\.Trash$', re.IGNORECASE),
        re.compile(r'\.pyc$', re.IGNORECASE),
        re.compile(r'\.swp$', re.IGNORECASE),
        re.compile(r'\.swo$', re.IGNORECASE),
        re.compile(r'~$', re.IGNORECASE),
        re.compile(r'^Thumbs\.db$', re.IGNORECASE),
        re.compile(r'^\.DS_Store$', re.IGNORECASE),
        re.compile(r'^ehthumbs\.db$', re.IGNORECASE),
        re.compile(r'^desktop\.ini$', re.IGNORECASE),
        re.compile(r'^\.vscode-server$', re.IGNORECASE),
        re.compile(r'^\.wine$', re.IGNORECASE),
        re.compile(r'^\.wine64$', re.IGNORECASE),
    ]

    print(f"Scanning '{source_dir}' for unwanted files and directories...")
    items_to_remove = []

    # Using os.walk with topdown=True allows modifying dirs in place
    for root, dirs, files in os.walk(source_dir, topdown=True, onerror=lambda e: print(f"Error accessing directory: {e}")):
        
        # Filter directories: skip hidden if include_hidden is False, and check against patterns
        dirs_to_process = []
        for dname in dirs:
            full_dpath = os.path.join(root, dname)
            
            # Symlink check
            if os.path.islink(full_dpath):
                 if dry_run:
                     print(f"DRY RUN: Would skip symlink directory from removal scan: {full_dpath}")
                 else:
                    print(f"Skipping symlink directory from removal scan: {full_dpath}")
                 continue # Skip this symlink

            # Hidden check
            if not include_hidden and dname.startswith('.'):
                # If hidden and not including hidden, skip this directory entirely
                if dry_run:
                     print(f"DRY RUN: Would skip hidden directory from removal scan: {full_dpath}")
                else:
                    print(f"Skipping hidden directory from removal scan: {full_dpath}")
                continue # Skip this hidden directory

            is_unwanted_dir = False
            for pattern in unwanted_patterns:
                if pattern.search(dname):
                    items_to_remove.append(full_dpath)
                    print(f"Found unwanted directory: {full_dpath}")
                    is_unwanted_dir = True
                    # If a directory is marked for removal, we don't need to traverse its contents
                    # We achieve this by NOT adding it to dirs_to_process
                    break # Found a pattern match, move to the next directory name

            # If it's not an unwanted directory (and not a skipped hidden/symlink), add it for traversal
            if not is_unwanted_dir:
                dirs_to_process.append(dname)

        # Update dirs in place for os.walk to control traversal
        dirs[:] = dirs_to_process

        # Process files in the current directory
        for fname in files:
            full_fpath = os.path.join(root, fname)

            # Symlink check
            if os.path.islink(full_fpath):
                if dry_run:
                    print(f"DRY RUN: Would skip symlink file from removal scan: {full_fpath}")
                else:
                    print(f"Skipping symlink file from removal scan: {full_fpath}")
                continue # Skip this symlink

            # Hidden check - apply only if not including hidden
            if not include_hidden and fname.startswith('.'):
                 if dry_run:
                     print(f"DRY RUN: Would skip hidden file from removal scan: {full_fpath}")
                 else:
                    print(f"Skipping hidden file from removal scan: {full_fpath}")
                 continue # Skip this hidden file

            is_unwanted_file = False
            for pattern in unwanted_patterns:
                 if pattern.search(fname):
                    items_to_remove.append(full_fpath)
                    print(f"Found unwanted file: {full_fpath}")
                    is_unwanted_file = True
                    break # Found a pattern match, move to the next file name


    print(f"\nFound {len(items_to_remove)} unwanted items.")
    if not items_to_remove:
        print("No unwanted items found.")
        return

    print("\nThe following items are marked for removal:")
    # Limit output for very long lists
    list_limit = 20
    if len(items_to_remove) > list_limit:
        print(f"Listing first {list_limit} of {len(items_to_remove)} items:")
        for item in items_to_remove[:list_limit]:
            print(item)
        print("\n...")
        print(f"Total items to remove: {len(items_to_remove)}")
    else:
         for item in items_to_remove:
            print(item)

    if dry_run:
        print("\nDRY RUN: No files or directories will be removed.")
        print(f"Unwanted item removal DRY RUN complete. Would remove {len(items_to_remove)} items.")
        return

    print("\nWARNING: This will permanently delete these files/directories.")
    confirmation = input("Proceed with removal? (yes/no): ").lower().strip()

    if confirmation == 'yes':
        print("Starting removal...")
        removed_count = 0
        for item_path in items_to_remove:
            if not os.path.exists(item_path):
                print(f"Warning: Item no longer exists (possibly removed as part of a directory): {item_path}. Skipping removal.")
                continue
                
            # Final check for symlink before attempting removal
            if os.path.islink(item_path):
                 print(f"Skipping removal of symlink: {item_path}")
                 continue

            try:
                if os.path.isdir(item_path):
                    print(f"Removing directory: {item_path}")
                    shutil.rmtree(item_path)
                    removed_count += 1
                else:
                    print(f"Removing file: {item_path}")
                    os.remove(item_path)
                    removed_count += 1
            except PermissionError:
                print(f"Permission denied to remove '{item_path}'. Skipping.")
            except OSError as e:
                 print(f"Error removing '{item_path}': {e}")
            except Exception as e:
                 print(f"An unexpected error occurred removing '{item_path}': {e}")

        print(f"Unwanted item removal complete. {removed_count} items removed.")
    else:
        print("Removal cancelled by user.")


def organize_by_type(source_dir, dest_dir, max_depth=None, dry_run=False, include_hidden=False, conflict_resolution_style='number'):
    """Organizes files and directories by type into subdirectories in dest_dir."""

    extension_to_dir = {
        '.mp4': 'videos', '.mkv': 'videos', '.avi': 'videos', '.mov': 'videos',
        '.wmv': 'videos', '.flv': 'videos', '.webm': 'videos', '.mpg': 'videos',
        '.mpeg': 'videos', '.3gp': 'videos', '.m4v': 'videos',
        '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio', '.aac': 'audio',
        '.ogg': 'audio', '.wma': 'audio', '.m4a': 'audio', '.opus': 'audio',
        '.jpg': 'images', '.jpeg': 'images', '.png': 'images', '.gif': 'images',
        '.bmp': 'images', '.tiff': 'images', '.webp': 'images', '.svg': 'images',
        '.heif': 'images', '.heic': 'images', '.ico': 'images', '.cur': 'images',
        '.txt': 'documents/text', '.pdf': 'documents/pdf', '.doc': 'documents/word',
        '.docx': 'documents/word', '.odt': 'documents/word', '.rtf': 'documents/text',
        '.xls': 'documents/excel', '.xlsx': 'documents/excel', '.ods': 'documents/excel',
        '.ppt': 'documents/powerpoint', '.pptx': 'documents/powerpoint', '.odp': 'documents/powerpoint',
        '.md': 'documents/text', '.csv': 'documents/data', '.json': 'documents/data',
        '.xml': 'documents/data', '.log': 'documents/text',
        '.zip': 'archives', '.tar': 'archives', '.gz': 'archives', '.bz2': 'archives',
        '.xz': 'archives', '.rar': 'archives', '.7z': 'archives', '.tgz': 'archives',
        '.tbz2': 'archives', '.txz': 'archives',
        '.py': 'code/python', '.js': 'code/javascript', '.html': 'code/web',
        '.css': 'code/web', '.java': 'code/java', '.c': 'code/c_cpp',
        '.cpp': 'code/c_cpp', '.h': 'code/c_cpp', '.hpp': 'code/c_cpp',
        '.cs': 'code/csharp', '.go': 'code/go', '.rb': 'code/ruby',
        '.php': 'code/php', '.swift': 'code/swift', '.kt': 'code/kotlin',
        '.rs': 'code/rust', '.sh': 'code/scripts', '.bash': 'code/scripts',
        '.ps1': 'code/scripts', '.pl': 'code/perl', '.r': 'code/r',
        '.yml': 'code/config', '.yaml': 'code/config', '.ini': 'code/config',
        '.cfg': 'code/config', '.conf': 'code/config', '.toml': 'code/config',
        '.gitignore': 'code/config', '.editorconfig': 'code/config',
        '.gitattributes': 'code/config', '.npmignore': 'code/config',
        '.babelrc': 'code/config', '.eslintrc': 'code/config', '.prettierrc': 'code/config',
        '.stylelintrc': 'code/config',
        '.sqlite': 'databases', '.sql': 'databases', '.db': 'databases',
        '.iso': 'disk_images', '.img': 'disk_images', '.vhd': 'disk_images', '.vmdk': 'disk_images',
        '.ttf': 'fonts', '.otf': 'fonts', '.woff': 'fonts', '.woff2': 'fonts',
        '.eot': 'fonts',
    }

    unknown_dir_name = 'stuff'
    directories_dir_name = 'directories'

    target_subdirs = set(extension_to_dir.values())
    target_subdirs.add(unknown_dir_name)
    target_subdirs.add(directories_dir_name)

    print(f"Ensuring target directories exist under '{dest_dir}':")
    for subdir in target_subdirs:
        full_target_subdir = os.path.join(dest_dir, subdir)
        if dry_run:
            print(f"DRY RUN: Would ensure '{full_target_subdir}' exists.")
        else:
            try:
                print(f" - {full_target_subdir}")
                os.makedirs(full_target_subdir, exist_ok=True)
            except OSError as e:
                print(f"Error creating target directory '{full_target_subdir}': {e}")
                return

    if dry_run:
         print(f"\nStarting organization DRY RUN of '{source_dir}' into '{dest_dir}' (Max depth: {max_depth if max_depth is not None else 'Unlimited'})...")
    else:
        print(f"\nStarting organization of '{source_dir}' into '{dest_dir}' (Max depth: {max_depth if max_depth is not None else 'Unlimited'})...")

    # Keep track of directories that were successfully moved as a whole (for depth limit)
    # This avoids trying to traverse into a directory that's no longer there.
    moved_directories = set()

    def traverse_and_organize_recursive(current_dir, current_depth):
        if not os.path.isdir(current_dir):
            # This can happen if a directory was moved by a higher level call due to max_depth
            # or if it was removed externally.
            if current_dir not in moved_directories:
                 print(f"Warning: '{current_dir}' is not a directory, does not exist, or was moved. Skipping traversal.")
            return

        abs_current_dir = os.path.abspath(current_dir)
        abs_dest_dir = os.path.abspath(dest_dir)

        # Avoid traversing into the destination directory or any of its subdirectories
        if os.path.commonpath([abs_current_dir, abs_dest_dir]) == abs_dest_dir and abs_current_dir != abs_dest_dir:
             if dry_run:
                 print(f"DRY RUN: Would skip traversal of '{current_dir}': It is within the destination directory tree.")
             else:
                print(f"Skipping traversal of '{current_dir}': It is within the destination directory tree.")
             return

        entries_to_process = []
        try:
            # os.scandir provides DirectoryEntry objects which are more efficient
            # and allow checking file type (is_file, is_dir, is_symlink) without extra syscalls.
            entries_to_process = list(os.scandir(current_dir))
        except PermissionError:
            print(f"Permission denied to access '{current_dir}'. Skipping traversal.")
            return
        except FileNotFoundError:
             # This could potentially happen if a directory is moved by an external process
             # or a very fast cleanup process between the isdir check and scandir.
             print(f"Warning: Directory not found during scan: '{current_dir}'. Skipping traversal.")
             return
        except Exception as e:
             print(f"Error scanning directory '{current_dir}': {e}")
             return

        # Separate files and directories, applying initial filters
        files_at_this_level = []
        dirs_at_this_level = []

        for entry in entries_to_process:
             item_path = entry.path
             item_name = entry.name
             
             # Symlink check - skip symlinks entirely from organization
             if entry.is_symlink():
                 if dry_run:
                     print(f"DRY RUN: Would skip symbolic link from organization: {item_path}")
                 else:
                    print(f"Skipping symbolic link from organization: {item_path}")
                 continue

             # Hidden check - skip if not including hidden and name starts with '.'
             if not include_hidden and item_name.startswith('.'):
                 if dry_run:
                     print(f"DRY RUN: Would skip hidden item from organization: {item_path}")
                 else:
                    print(f"Skipping hidden item from organization: {item_path}")
                 continue

             # Avoid trying to organize the destination directory itself if somehow listed
             abs_item_path = os.path.abspath(item_path)
             if os.path.commonpath([abs_item_path, abs_dest_dir]) == abs_dest_dir and abs_item_path != abs_dest_dir:
                  continue # Skip items inside the destination

             if entry.is_file():
                 files_at_this_level.append(entry)
             elif entry.is_dir():
                 dirs_at_this_level.append(entry)
                 

        # Process files first
        for entry in files_at_this_level:
            item_path = entry.path
            try:
                item_name = entry.name
                _, ext = os.path.splitext(item_name)
                ext = ext.lower()

                category_dir_name = extension_to_dir.get(ext, unknown_dir_name)
                target_category_dir = os.path.join(dest_dir, category_dir_name)

                # move_item handles permissions and conflicts
                move_item(item_path, target_category_dir, dry_run, conflict_resolution_style)

            except Exception as e:
                print(f"An error occurred processing file '{item_path}': {e}")

        # Process directories
        for entry in dirs_at_this_level:
             item_path = entry.path
             try:
                 # If at max depth or beyond, move the directory as a whole
                 if max_depth is not None and current_depth >= max_depth:
                     target_dir = os.path.join(dest_dir, directories_dir_name)
                     # move_item handles permissions and conflicts
                     if move_item(item_path, target_dir, dry_run, conflict_resolution_style):
                         moved_directories.add(os.path.abspath(item_path)) # Mark as moved
                 else:
                     # Otherwise, recurse into the directory
                     traverse_and_organize_recursive(item_path, current_depth + 1)

             except Exception as e:
                print(f"An error occurred processing directory '{item_path}': {e}")

    abs_source = os.path.abspath(source_dir)
    abs_dest = os.path.abspath(dest_dir)
    if abs_source == abs_dest:
         print("Error: Source and destination directories are the same. Cannot organize in place into subdirectories.")
         return

    # Check if source_dir itself is a symlink before starting traversal
    if os.path.islink(source_dir):
         print(f"Error: Source directory '{source_dir}' is a symbolic link. Skipping organization of the link itself.")
         # Note: This does NOT prevent organizing *contents* if the link is followed.
         # os.path.abspath follows links. The check above `if not os.path.isdir(current_dir)`
         # will handle if the initial path isn't a directory after resolution.
         # If you strictly mean "do nothing if the top-level SOURCE argument is a symlink", add a sys.exit(1) here.
         # For this script, we allow proceeding if the resolved path is a directory.


    traverse_and_organize_recursive(source_dir, 0)

    if dry_run:
        print("File organization by type DRY RUN complete.")
    else:
        print("File organization by type complete.")

def remove_empty_dirs(directory, dry_run=False):
    """Removes empty directories within the specified directory, bottom-up."""
    print(f"\nStarting empty directory cleanup in '{directory}'...")
    removed_count = 0
    abs_directory = os.path.abspath(directory)

    # Use topdown=False to process subdirectories before their parents
    for root, dirs, files in os.walk(directory, topdown=False, onerror=lambda e: print(f"Error accessing directory during cleanup: {e}")):
        
        # Don't try to remove the source directory itself
        if os.path.abspath(root) == abs_directory:
            continue

        # Only consider directories that were empty *after* the main processing
        # check if the directory is empty
        try:
            if not os.listdir(root):
                # Check if it's a symlink - do not remove symlinks with rmdir
                if os.path.islink(root):
                     if dry_run:
                        print(f"DRY RUN: Would skip removing symlink (detected as empty): {root}")
                     else:
                        print(f"Skipping removal of symlink (detected as empty): {root}")
                     continue

                if dry_run:
                    print(f"DRY RUN: Would remove empty directory: {root}")
                    removed_count += 1 # Count for reporting purposes
                else:
                    print(f"Removing empty directory: {root}")
                    try:
                        os.rmdir(root)
                        removed_count += 1
                    except OSError as e:
                        # This can happen if files appeared between listing and rmdir, or permissions
                        print(f"Could not remove directory '{root}' (might not be empty or permissions issue): {e}")
                    except PermissionError:
                         print(f"Permission denied to remove empty directory '{root}'.")

        except PermissionError:
            print(f"Permission denied to list directory '{root}' for cleanup. Skipping.")
        except Exception as e:
            print(f"Error checking or removing directory '{root}' during cleanup: {e}")


    if dry_run:
        print(f"Empty directory cleanup DRY RUN complete. Would remove {removed_count} directories.")
    else:
        print(f"Empty directory cleanup complete. {removed_count} directories removed.")


def main():
    parser = argparse.ArgumentParser(
        description="Organize files on your hard drive using move operations.",
        formatter_class=argparse.RawTextHelpFormatter
        )
    parser.add_argument("--source", required=True, help="The source directory to scan and organize.")
    parser.add_argument("--destination",
                        help="The destination directory where organized files and git repos will be moved into subdirectories\n"
                             "(e.g., DEST/git, DEST/videos, DEST/code, etc.). Required for 'git' and 'organize' modes.")
    parser.add_argument("--mode", required=True, choices=['git', 'cleanup', 'organize'],
                        help="The mode of operation:\n"
                             "- 'git': Find and move git repositories.\n"
                             "- 'cleanup': Find and remove unwanted files/directories.\n"
                             "- 'organize': Move files by type and directories by depth.")
    parser.add_argument("--max-depth", type=int, default=None,
                        help="Maximum recursion depth for 'organize' mode.\n"
                             "Depth 0 means only process items directly in --source.\n"
                             "Depth 1 means process items in --source and its immediate subdirectories.\n"
                             "Directories at max_depth will be moved to the 'directories' category.\n"
                             "Default (None) means unlimited depth.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Perform a dry run. Print actions that would be taken without actually moving or deleting files.")
    parser.add_argument("--include-hidden", action="store_true",
                        help="Include hidden files and directories (starting with '.') in processing for all modes.")
    parser.add_argument("--cleanup-empty-dirs", action="store_true",
                        help="Remove empty directories in the source directory after 'git' or 'organize' modes complete.")
    parser.add_argument("--conflict-resolution-style", choices=['number', 'timestamp', 'uuid'], default='number',
                        help="Style for resolving naming conflicts when moving files/directories:\n"
                             "- 'number': Appends a counter (e.g., file(1).txt).\n"
                             "- 'timestamp': Appends a timestamp (e.g., file_20231027_103000.txt).\n"
                             "- 'uuid': Appends a UUID (e.g., file_a1b2c3d4....txt).\n"
                             "Default is 'number'.")


    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    source_dir = os.path.abspath(args.source)
    # dest_dir is processed below because it's conditional

    dry_run = args.dry_run
    include_hidden = args.include_hidden
    cleanup_empty = args.cleanup_empty_dirs
    conflict_style = args.conflict_resolution_style

    if dry_run:
        print("--- File Organizer Script (DRY RUN) ---")
        print("No files will be moved or deleted.")
    else:
        print("--- File Organizer Script ---")

    print(f"Source: {source_dir}")
    print(f"Mode: {args.mode}")
    if args.mode == 'organize':
        print(f"Max Depth: {args.max_depth if args.max_depth is not None else 'Unlimited'}")
        print(f"Conflict Resolution Style: {conflict_style}")
    elif args.mode == 'git':
         print(f"Conflict Resolution Style: {conflict_style}")

    if include_hidden:
        print("Including hidden files and directories.")
    if cleanup_empty and args.mode in ['git', 'organize']:
         print("Empty directories in source will be cleaned up after processing.")

    print("-" * 35)

    # Check if source directory exists and is a directory
    if not os.path.isdir(source_dir):
        # Also check if it exists at all but isn't a directory (like a file or broken link)
        if os.path.exists(source_dir):
             print(f"Error: Source path exists but is not a directory: {source_dir}")
        else:
            print(f"Error: Source directory does not exist: {source_dir}")
        sys.exit(1)

    # --- Conditional Destination Check ---
    dest_dir = None # Initialize dest_dir
    if args.mode in ['git', 'organize']:
        if args.destination is None:
            print(f"Error: The --destination argument is required for mode '{args.mode}'.")
            sys.exit(1)
        dest_dir = os.path.abspath(args.destination)

        # Ensure destination directory exists for git and organize modes if not dry-run
        # This is also done inside move_item, but checking here provides a clearer initial error.
        if not os.path.exists(dest_dir):
            if dry_run:
                print(f"DRY RUN: Destination directory '{dest_dir}' does not exist. Would create it.")
            else:
                print(f"Destination directory '{dest_dir}' does not exist. Creating it.")
                try:
                    os.makedirs(dest_dir)
                except OSError as e:
                    print(f"Error creating destination directory '{dest_dir}': {e}")
                    sys.exit(1)
        elif not os.path.isdir(dest_dir):
             print(f"Error: Destination path exists but is not a directory: {dest_dir}")
             sys.exit(1)

        # Ensure destination is not inside source for organize mode (checks absolute paths)
        if args.mode == 'organize':
            abs_source = os.path.abspath(source_dir)
            abs_dest = os.path.abspath(dest_dir)
            # Check if abs_dest starts with abs_source and they are not the same path
            if abs_dest.startswith(abs_source + os.sep) or abs_dest == abs_source:
                 print(f"Error: Destination directory '{dest_dir}' ({abs_dest}) is inside or the same as source directory '{source_dir}' ({abs_source}). This can cause issues with organization. Please choose a destination outside the source tree.")
                 sys.exit(1)

    print("\nWARNING: This script moves and potentially deletes files (unless --dry-run is used).")
    print("Ensure you have backups and understand the risks before proceeding.")
    print("It requires appropriate permissions to operate on the specified directories.")
    print("Symbolic links in the source will be skipped.")

    if not dry_run:
        confirm_proceed = input("Type 'yes' to continue: ").lower().strip()
        if confirm_proceed != 'yes':
            print("Operation cancelled by user.")
            sys.exit(0)

    print("\nProceeding...")

    if args.mode == 'git':
        find_and_move_git(source_dir, dest_dir, dry_run, include_hidden, conflict_style)
    elif args.mode == 'cleanup':
        # Dest_dir argument is ignored in cleanup mode as it's only for the source
        if not dry_run and args.destination is not None: # Only print note if destination was provided
             print("Note: Destination directory argument is not used in 'cleanup' mode.")
        find_and_remove_unwanted(source_dir, dry_run, include_hidden)
    elif args.mode == 'organize':
        organize_by_type(source_dir, dest_dir, args.max_depth, dry_run, include_hidden, conflict_style)

    # Post-processing: Remove empty directories if requested and not in cleanup mode
    if cleanup_empty and args.mode in ['git', 'organize']:
        remove_empty_dirs(source_dir, dry_run)

    print("\nScript finished.")

if __name__ == "__main__":
    main()