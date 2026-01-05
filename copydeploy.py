#!/usr/bin/env python3
"""
copydeploy.py - Copy folder contents from source to destination.
Supports include/exclude file filtering, dryrun mode, and sync mode.

by: Joey Yoarikso (https://github.com/yoarikso)
"""

import argparse
import fnmatch
import logging
import os
import shutil
import sys
from datetime import datetime


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Copy folder contents from source to destination.\nSupports include/exclude file filtering, dryrun mode, and sync mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 copydeploy.py --source /path/to/src --destination /path/to/dest
  python3 copydeploy.py --dryrun --source ./src --destination ./dest
  python3 copydeploy.py --source ./src --destination ./dest --exclude exclude.txt
  python3 copydeploy.py --source ./src --destination ./dest --include include.txt
        """,
    )

    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="Show what would be copied without actually copying.",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Delete files in destination that don't exist in source. Without this flag, only copy overwrite is performed.",
    )
    parser.add_argument(
        "--source",
        required=True,
        help="The source folder to copy from.",
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="The destination folder to sync to.",
    )

    # Mutually exclusive group for include/exclude
    filter_group = parser.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--exclude",
        help="Path to exclude file (.txt) listing files/folders to skip.",
    )
    filter_group.add_argument(
        "--include",
        help="Path to include file (.txt) listing files/folders to copy.",
    )

    return parser.parse_args()


def parse_filter_file(filepath):
    """
    Parse an include/exclude filter file.

    Returns a list of patterns (e.g., '/bin/*', 'file1.jpg').
    """
    patterns = []
    if not filepath:
        return patterns

    if not os.path.isfile(filepath):
        print(f"Error: Filter file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Handle inline comments (e.g., "/bin/* - This will exclude...")
            if " - " in line:
                line = line.split(" - ")[0].strip()
            if line:
                patterns.append(line)

    return patterns


def matches_pattern(rel_path, patterns):
    """
    Check if a relative path matches any of the given patterns.

    Patterns can be:
    - Exact filenames: 'file1.jpg'
    - Directory wildcards: '/bin/*'
    - Glob patterns: '*.txt'
    """
    # Normalize path separators for cross-platform compatibility
    rel_path_normalized = rel_path.replace(os.sep, "/")

    for pattern in patterns:
        pattern_normalized = pattern.replace(os.sep, "/")

        # Remove leading slash for matching
        if pattern_normalized.startswith("/"):
            pattern_normalized = pattern_normalized[1:]

        # Check for exact match
        if rel_path_normalized == pattern_normalized:
            return True

        # Check for directory prefix match (e.g., pattern 'bin/*' matches 'bin/file.txt')
        if pattern_normalized.endswith("/*"):
            dir_pattern = pattern_normalized[:-2]
            if rel_path_normalized.startswith(dir_pattern + "/") or rel_path_normalized == dir_pattern:
                return True

        # Check for fnmatch pattern match
        if fnmatch.fnmatch(rel_path_normalized, pattern_normalized):
            return True

        # Also check just the filename for simple patterns
        filename = os.path.basename(rel_path)
        if fnmatch.fnmatch(filename, pattern_normalized):
            return True

    return False


def should_sync_file(rel_path, include_patterns, exclude_patterns):
    """
    Determine if a file should be copied based on include/exclude patterns.

    - If include_patterns is set, only files matching are copied.
    - If exclude_patterns is set, files matching are skipped.
    - If neither is set, all files are copied.
    """
    if include_patterns:
        return matches_pattern(rel_path, include_patterns)
    elif exclude_patterns:
        return not matches_pattern(rel_path, exclude_patterns)
    else:
        return True


def setup_logging(dryrun=False):
    """Set up logging to file and console."""
    logger = logging.getLogger("copydeploy")
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(os.getcwd(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_suffix = "_dryrun" if dryrun else ""
    log_file = os.path.join(log_dir, f"copydeploy_{timestamp}{log_suffix}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    return logger, log_file


def get_all_files(directory):
    """Get all files in a directory with their relative paths."""
    files = set()
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, directory)
            files.add(rel_path)
    return files


def sync_folders(source, destination, include_patterns, exclude_patterns, dryrun, sync, logger):
    """
    Sync files from source to destination.

    If sync is True, also deletes files in destination that don't exist in source.

    Returns tuple of (files_copied, files_deleted, errors).
    """
    files_copied = 0
    files_deleted = 0
    errors = []

    source = os.path.abspath(source)
    destination = os.path.abspath(destination)

    if not os.path.isdir(source):
        logger.error(f"Source directory does not exist: {source}")
        return 0, 0, [f"Source directory does not exist: {source}"]

    prefix = "[DRYRUN] " if dryrun else ""

    # Get all files from source
    source_files = get_all_files(source)

    # Filter files based on include/exclude patterns
    files_to_sync = set()
    for rel_path in source_files:
        if should_sync_file(rel_path, include_patterns, exclude_patterns):
            files_to_sync.add(rel_path)

    logger.info(f"{prefix}Copying {len(files_to_sync)} files from {source} to {destination}")

    # Copy files from source to destination
    for rel_path in sorted(files_to_sync):
        src_file = os.path.join(source, rel_path)
        dst_file = os.path.join(destination, rel_path)

        try:
            # Check if file needs to be copied (doesn't exist or is different)
            needs_copy = True
            if os.path.exists(dst_file):
                src_stat = os.stat(src_file)
                dst_stat = os.stat(dst_file)
                # Compare size and modification time
                if src_stat.st_size == dst_stat.st_size and src_stat.st_mtime <= dst_stat.st_mtime:
                    needs_copy = False

            if needs_copy:
                if dryrun:
                    logger.info(f"{prefix}COPY: {rel_path}")
                else:
                    # Create destination directory if needed
                    dst_dir = os.path.dirname(dst_file)
                    if dst_dir:
                        os.makedirs(dst_dir, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    logger.info(f"COPIED: {rel_path}")
                files_copied += 1
        except Exception as e:
            error_msg = f"Error copying {rel_path}: {e}"
            logger.error(error_msg)
            errors.append(error_msg)

    # Delete files in destination that are not in source (only if --sync is enabled)
    if sync and os.path.isdir(destination):
        dest_files = get_all_files(destination)
        # Exclude log files from deletion
        dest_files = {f for f in dest_files if not (f.startswith("copydeploy_") and f.endswith(".log"))}

        for rel_path in sorted(dest_files):
            should_delete = False

            if include_patterns:
                # With include mode: delete if file matches include pattern but not in source
                if matches_pattern(rel_path, include_patterns) and rel_path not in source_files:
                    should_delete = True
            elif exclude_patterns:
                # With exclude mode: delete if file is not excluded and not in source
                if not matches_pattern(rel_path, exclude_patterns) and rel_path not in source_files:
                    should_delete = True
            else:
                # No filter: delete if not in source
                if rel_path not in source_files:
                    should_delete = True

            if should_delete:
                dst_file = os.path.join(destination, rel_path)
                try:
                    if dryrun:
                        logger.info(f"{prefix}DELETE: {rel_path}")
                    else:
                        os.remove(dst_file)
                        logger.info(f"DELETED: {rel_path}")
                    files_deleted += 1
                except Exception as e:
                    error_msg = f"Error deleting {rel_path}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

    # Clean up empty directories in destination (only if --sync is enabled)
    if sync and not dryrun and os.path.isdir(destination):
        for root, dirs, _ in os.walk(destination, topdown=False):
            for d in dirs:
                dir_path = os.path.join(root, d)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        logger.info(f"REMOVED EMPTY DIR: {os.path.relpath(dir_path, destination)}")
                except Exception:
                    pass  # Ignore errors when removing empty dirs

    return files_copied, files_deleted, errors


def main():
    """Main entry point."""
    args = parse_args()

    # Validate source directory
    if not os.path.isdir(args.source):
        print(f"Error: Source directory does not exist: {args.source}", file=sys.stderr)
        sys.exit(1)

    # Parse filter files
    include_patterns = parse_filter_file(args.include) if args.include else []
    exclude_patterns = parse_filter_file(args.exclude) if args.exclude else []

    # Set up logging
    logger, log_file = setup_logging(args.dryrun)

    if args.dryrun:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 60)

    logger.info(f"Source: {os.path.abspath(args.source)}")
    logger.info(f"Destination: {os.path.abspath(args.destination)}")
    logger.info(f"Mode: {'Sync (copy + delete)' if args.sync else 'Copy overwrite only'}")

    if include_patterns:
        logger.info(f"Include patterns: {include_patterns}")
    if exclude_patterns:
        logger.info(f"Exclude patterns: {exclude_patterns}")

    logger.info("-" * 60)

    # Perform sync
    files_copied, files_deleted, errors = sync_folders(
        args.source,
        args.destination,
        include_patterns,
        exclude_patterns,
        args.dryrun,
        args.sync,
        logger,
    )

    # Summary
    logger.info("-" * 60)
    prefix = "[DRYRUN] " if args.dryrun else ""
    logger.info(f"{prefix}Summary:")
    logger.info(f"{prefix}  Files copied: {files_copied}")
    logger.info(f"{prefix}  Files deleted: {files_deleted}")
    logger.info(f"{prefix}  Errors: {len(errors)}")

    logger.info(f"Log file: {log_file}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()

