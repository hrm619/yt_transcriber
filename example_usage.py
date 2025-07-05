#!/usr/bin/env python3
"""
Example usage of the YouTube URL fetcher.

This example shows how to use the URL fetcher functionality.
Note: You need to set up a YouTube Data API v3 key to actually fetch videos.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.yt_transcriber.core.url_update import (
    extract_channel_id_from_url,
    CHANNEL_URLS,
    CUTOFF_DATE
)

def demonstrate_url_extraction():
    """Demonstrate URL extraction functionality."""
    print("=== YouTube Multi-Channel URL Fetcher Demo ===")
    print()
    
    # Test different URL formats
    test_urls = [
        "https://www.youtube.com/@JoshandHayden/videos",
        "https://www.youtube.com/channel/UC1234567890abcdef",
        "https://www.youtube.com/c/TestChannel",
        "https://www.youtube.com/user/TestUser"
    ]
    
    print("Testing URL extraction:")
    for url in test_urls:
        channel_id = extract_channel_id_from_url(url)
        print(f"  {url}")
        print(f"  → Channel ID: {channel_id}")
        print()
    
    print(f"Configured channels ({len(CHANNEL_URLS)}):")
    for name, url in CHANNEL_URLS.items():
        channel_id = extract_channel_id_from_url(url)
        print(f"  • {name}: {url}")
        print(f"    → Channel ID: {channel_id}")
    print()
    
    print(f"Cutoff date: {CUTOFF_DATE.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    print("To fetch actual videos, you need to:")
    print("1. Set up a YouTube Data API v3 key")
    print("2. Run: python setup_api.py")
    print("3. Run: python src/yt_transcriber/core/url_update.py")
    print("   (Will automatically fetch from all channels and organize in dictionary)")

def main():
    """Main demonstration function."""
    try:
        demonstrate_url_extraction()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 