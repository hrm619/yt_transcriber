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


def run_update():
    """Entry point for fetch + batch workflow."""
    from pathlib import Path
    import shutil
    from yt_transcriber.channels import (
        fetch_videos_from_multiple_channels,
        save_channel_results_to_files,
        CHANNEL_URLS,
    )
    from yt_transcriber.batch import main as batch_main

    print("🚀 YouTube Fetch & Process Pipeline")
    print("=" * 50)
    print()

    # Step 1: Fetch latest URLs
    print("📥 Step 1: Fetching latest videos from all channels...")
    print()

    try:
        # Fetch videos (uses default cutoff date - first of current month)
        results = fetch_videos_from_multiple_channels(CHANNEL_URLS)

        # Check if any videos were found
        total_videos = sum(len(urls) for urls in results.values())
        if total_videos == 0:
            print("\n❌ No videos found. Exiting.")
            return

        print()
        print(f"✅ Found {total_videos} total videos")
        print()

        # Save results to files
        save_channel_results_to_files(results, "config")

        # Step 2: Prepare for batch processing
        print()
        print("📋 Step 2: Preparing for batch processing...")

        all_channels_file = Path("config/all_channels_urls.txt")
        urls_file = Path("config/urls.txt")

        if all_channels_file.exists():
            # Copy all_channels_urls.txt to urls.txt
            shutil.copy(all_channels_file, urls_file)
            print(f"✅ Copied {all_channels_file} to {urls_file}")
        else:
            print(f"❌ Error: {all_channels_file} not found")
            return

        # Step 3: Run batch processing
        print()
        print("⚙️  Step 3: Starting batch processing...")
        print("=" * 50)
        print()

        batch_main()

        print()
        print("=" * 50)
        print("✅ Fetch & Process Pipeline completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during fetch & process: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Default to pipeline if run directly
    run_pipeline()
