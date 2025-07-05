#!/usr/bin/env python3
"""
Demonstration script for fetching recent YouTube videos.

This script shows how to use the URL fetcher to get videos from a channel
published after January 1, 2025.

Usage:
    python scripts/fetch_recent_videos.py
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.yt_transcriber.core.url_update import (
    fetch_videos_from_multiple_channels, 
    save_channel_results_to_files,
    CHANNEL_URLS,
    CUTOFF_DATE
)

def main():
    """Demonstrate fetching recent videos from multiple channels."""
    
    print("=== YouTube Multi-Channel Videos Fetcher Demo ===")
    print(f"Cutoff Date: {CUTOFF_DATE.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Channels: {len(CHANNEL_URLS)}")
    for name, url in CHANNEL_URLS.items():
        print(f"  • {name}: {url}")
    print()
    
    try:
        # Fetch recent videos from all channels
        results = fetch_videos_from_multiple_channels(CHANNEL_URLS, CUTOFF_DATE)
        
        if not any(results.values()):
            print("No videos found matching the criteria from any channel.")
            return
        
        print(f"\n=== Detailed Results ===")
        for channel_name, video_urls in results.items():
            if video_urls:
                print(f"\n{channel_name.upper()} ({len(video_urls)} videos):")
                for i, url in enumerate(video_urls, 1):
                    print(f"  {i:2d}. {url}")
            else:
                print(f"\n{channel_name.upper()}: No videos found")
        
        # Save to organized files for batch processing
        save_channel_results_to_files(results, "config")
        
        print(f"\n=== Next Steps ===")
        print("Files created in config/ directory:")
        print("• all_channels_urls.txt - All videos from all channels")
        print("• [channel]_urls.txt - Individual channel files")
        print("• channel_summary.txt - Summary report")
        print()
        print("You can now process these videos using the batch processor:")
        print("1. Copy config/all_channels_urls.txt to config/urls.txt")
        print("2. Run: python run_batch.py")
        print("Or process individual channels by copying specific files.")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 