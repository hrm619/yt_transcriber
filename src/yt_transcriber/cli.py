#!/usr/bin/env python3
"""
Command-line interface entry points for yt_transcriber.
"""

import sys


def run_pipeline() -> None:
    """Entry point for single video processing."""
    from yt_transcriber.pipeline import main
    main()


def run_batch() -> None:
    """Entry point for batch video processing."""
    from yt_transcriber.batch import main
    main()


def run_channel_fetcher() -> None:
    """Entry point for YouTube channel URL fetcher."""
    from yt_transcriber.channels import main
    main()


def run_cleanup() -> None:
    """Entry point for cleanup utility."""
    from yt_transcriber.utils import cleanup_all

    print("Running cleanup operations...")
    temp_files, empty_dirs = cleanup_all()

    print(f"Removed {temp_files} temporary chunk files")
    print(f"Removed {empty_dirs} empty directories")
    print("Cleanup completed")


def run_update() -> None:
    """Entry point for fetch + batch workflow."""
    import shutil
    from pathlib import Path

    from yt_transcriber.batch import main as batch_main
    from yt_transcriber.channels import (
        fetch_videos_from_multiple_channels,
        load_channels_from_config,
        save_channel_results_to_files,
    )

    print("YouTube Fetch & Process Pipeline")
    print("=" * 50)
    print()

    try:
        channel_urls = load_channels_from_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading channel config: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        print("Step 1: Fetching latest videos from all channels...")
        print()

        results = fetch_videos_from_multiple_channels(channel_urls)

        total_videos = sum(len(urls) for urls in results.values())
        if total_videos == 0:
            print("\nNo videos found. Exiting.")
            return

        print()
        print(f"Found {total_videos} total videos")
        print()

        save_channel_results_to_files(results, channel_urls, "config")

        print()
        print("Step 2: Preparing for batch processing...")

        all_channels_file = Path("config/all_channels_urls.txt")
        urls_file = Path("config/urls.txt")

        if all_channels_file.exists():
            shutil.copy(all_channels_file, urls_file)
            print(f"Copied {all_channels_file} to {urls_file}")
        else:
            print(f"Error: {all_channels_file} not found")
            return

        print()
        print("Step 3: Starting batch processing...")
        print("=" * 50)
        print()

        batch_main()

        print()
        print("=" * 50)
        print("Fetch & Process Pipeline completed successfully!")

    except Exception as e:
        print(f"\nError during fetch & process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
