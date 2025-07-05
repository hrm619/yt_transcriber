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

from src.yt_transcriber.core.url_update import fetch_recent_videos, save_urls_to_file

def main():
    """Demonstrate fetching recent videos from the Josh and Hayden channel."""
    
    # Configuration
    channel_url = "https://www.youtube.com/@JoshandHayden/videos"
    cutoff_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    
    print("=== YouTube Recent Videos Fetcher Demo ===")
    print(f"Channel: {channel_url}")
    print(f"Cutoff Date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    try:
        # Fetch recent videos
        video_urls = fetch_recent_videos(channel_url, cutoff_date)
        
        if not video_urls:
            print("No videos found matching the criteria.")
            return
        
        print(f"\n=== Results ===")
        print(f"Found {len(video_urls)} video URLs:")
        for i, url in enumerate(video_urls, 1):
            print(f"{i:2d}. {url}")
        
        # Save to file for batch processing
        save_urls_to_file(video_urls, "config/recent_videos.txt")
        
        print(f"\n=== Next Steps ===")
        print("You can now process these videos using the batch processor:")
        print("1. Copy config/recent_videos.txt to config/urls.txt")
        print("2. Run: python run_batch.py")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 