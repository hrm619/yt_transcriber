#!/usr/bin/env python3
"""
Command-line interface entry points for yt_transcriber.
"""

import sys


def run_pipeline():
    """Entry point for single video processing."""
    from yt_transcriber.pipeline import main
    main()


def run_batch():
    """Entry point for batch video processing."""
    from yt_transcriber.batch import main
    main()


def run_channel_fetcher():
    """Entry point for YouTube channel URL fetcher."""
    from yt_transcriber.channels import main
    main()


def run_cleanup():
    """Entry point for cleanup utility."""
    from yt_transcriber.utils import cleanup_all

    print("🧹 Running cleanup operations...")
    temp_files, empty_dirs = cleanup_all()

    print(f"✓ Removed {temp_files} temporary chunk files")
    print(f"✓ Removed {empty_dirs} empty directories")
    print("✅ Cleanup completed")


if __name__ == "__main__":
    # Default to pipeline if run directly
    run_pipeline()
