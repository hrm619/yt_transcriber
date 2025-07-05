#!/usr/bin/env python3
"""
Cleanup script for temporary files in yt_transcriber.
This script removes temporary chunk files and other cleanup tasks.
"""

import shutil
from pathlib import Path

def cleanup_temp_files():
    """Remove temporary chunk files."""
    temp_dir = Path("data/raw/temp")
    if temp_dir.exists():
        for file in temp_dir.glob("*_chunk*.m4a"):
            file.unlink()
            print(f"Removed: {file}")
        print("✓ Temporary chunk files cleaned up")

def cleanup_empty_dirs():
    """Remove empty directories."""
    for root, dirs, files in os.walk("data", topdown=False):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                print(f"Removed empty directory: {dir_path}")

if __name__ == "__main__":
    import os
    cleanup_temp_files()
    cleanup_empty_dirs()
    print("✅ Cleanup completed")
