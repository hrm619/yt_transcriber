#!/usr/bin/env python3
"""
Utility functions for yt_transcriber.
"""

import os
from pathlib import Path
from .config import CHUNKS_DIR


def cleanup_temp_files():
    """Remove temporary chunk files from the temp directory."""
    if CHUNKS_DIR.exists():
        removed_count = 0
        for file in CHUNKS_DIR.glob("*_chunk*.m4a"):
            file.unlink()
            removed_count += 1
        return removed_count
    return 0


def cleanup_empty_dirs(base_dir: Path = None):
    """
    Remove empty directories recursively.

    Args:
        base_dir: Base directory to clean (defaults to data/)

    Returns:
        Number of directories removed
    """
    if base_dir is None:
        base_dir = Path("data")

    if not base_dir.exists():
        return 0

    removed_count = 0
    for root, dirs, files in os.walk(base_dir, topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                removed_count += 1

    return removed_count


def cleanup_all():
    """
    Run all cleanup operations.

    Returns:
        Tuple of (temp_files_removed, dirs_removed)
    """
    temp_files = cleanup_temp_files()
    empty_dirs = cleanup_empty_dirs()
    return (temp_files, empty_dirs)
