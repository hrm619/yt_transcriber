#!/usr/bin/env python3
"""
Demo script showing programmatic usage of the multi-channel YouTube URL fetcher.

This script demonstrates how to use the fetch_videos_from_multiple_channels function
to get videos from multiple YouTube channels and organize them in a dictionary.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.yt_transcriber.core.url_update import (
    fetch_videos_from_multiple_channels,
    CHANNEL_URLS,
    CUTOFF_DATE
)

def demo_multi_channel_fetching():
    """Demonstrate multi-channel video fetching programmatically."""
    print("🚀 Multi-Channel YouTube URL Fetcher Demo")
    print("=" * 50)
    
    # Show configuration
    print(f"📅 Cutoff date: {CUTOFF_DATE.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🔗 Channels configured: {len(CHANNEL_URLS)}")
    
    for name, url in CHANNEL_URLS.items():
        print(f"   • {name}: {url}")
    print()
    
    # For demo purposes, we'll use a subset of channels to avoid API quota issues
    demo_channels = {
        "underdog": CHANNEL_URLS["underdog"],
        "jj": CHANNEL_URLS["jj"],
        "fpts": CHANNEL_URLS["fpts"]
    }
    
    print(f"📋 Demo will fetch from {len(demo_channels)} channels:")
    for name, url in demo_channels.items():
        print(f"   • {name}: {url}")
    print()
    
    try:
        # This would normally require an API key
        print("⚠️  This demo requires a YouTube Data API v3 key set as YOUTUBE_API_KEY environment variable.")
        print("   Run 'python setup_api.py' to configure your API key.")
        print()
        
        # Uncomment the following lines to actually fetch videos:
        # print("🔄 Fetching videos...")
        # results = fetch_videos_from_multiple_channels(demo_channels, CUTOFF_DATE)
        
        # Simulate results for demo
        print("📊 Simulated results structure:")
        simulated_results = {
            "underdog": [
                "https://www.youtube.com/watch?v=example1",
                "https://www.youtube.com/watch?v=example2"
            ],
            "jj": [
                "https://www.youtube.com/watch?v=example3"
            ],
            "fpts": []
        }
        
        print("Results dictionary structure:")
        for channel_name, video_urls in simulated_results.items():
            print(f"   '{channel_name}': {len(video_urls)} videos")
            for i, url in enumerate(video_urls, 1):
                print(f"      {i}. {url}")
        print()
        
        # Show how to access specific channel results
        print("💡 How to access results programmatically:")
        print("   results = fetch_videos_from_multiple_channels(CHANNEL_URLS, CUTOFF_DATE)")
        print("   underdog_videos = results['underdog']")
        print("   total_videos = sum(len(urls) for urls in results.values())")
        print("   all_urls = [url for urls in results.values() for url in urls]")
        print()
        
        # Show integration with existing pipeline
        print("🔗 Integration with existing pipeline:")
        print("   1. Fetch videos: results = fetch_videos_from_multiple_channels(...)")
        print("   2. Save to files: save_channel_results_to_files(results)")
        print("   3. Process with batch: python run_batch.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return True

def main():
    """Main demonstration function."""
    try:
        success = demo_multi_channel_fetching()
        if success:
            print("\n✅ Demo completed successfully!")
        else:
            print("\n❌ Demo encountered errors.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Demo cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 