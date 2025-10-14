#!/usr/bin/env python3
"""
YouTube Channel URL Fetcher

This script fetches YouTube video URLs from a channel for videos published after a cutoff date.
It uses the YouTube Data API v3 to get accurate metadata including publish dates.

Requirements:
- YouTube Data API v3 key (set in .env file as YOUTUBE_API_KEY)
- python-dateutil for date parsing
- requests for API calls

Usage:
    python -m yt_transcriber.channels

    # Or import and use as a module:
    from yt_transcriber.channels import fetch_recent_videos
    video_urls = fetch_recent_videos(channel_url, cutoff_date)
"""

import os
import re
import sys
import requests
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Install with: uv pip install python-dotenv")

# Channel URLs to fetch from
CHANNEL_URLS = {
    "underdog": "https://www.youtube.com/@JoshandHayden/videos",
    "jj": "https://www.youtube.com/@lateroundff/videos",
    "fpts": "https://www.youtube.com/@FantasyPoints/videos",
    "pff": "https://www.youtube.com/@ProFootballFocus/videos",
    "ringer_fantasy": "https://www.youtube.com/@RingerFFS/videos",
    "ringer_nfl": "https://www.youtube.com/@RingerNFL/videos",
    "athletic": "https://www.youtube.com/@TAFootballShow/videos"
}


def get_default_cutoff_date() -> datetime:
    """
    Get default cutoff date (first day of current month).

    Returns:
        datetime: First day of current month at midnight UTC
    """
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)

class YouTubeAPIError(Exception):
    """Custom exception for YouTube API errors."""
    pass

def get_api_key() -> str:
    """
    Get YouTube API key from environment variable.
    
    Returns:
        str: YouTube API key
        
    Raises:
        YouTubeAPIError: If API key is not found
    """
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise YouTubeAPIError(
            "YouTube API key not found. Please set the YOUTUBE_API_KEY environment variable.\n"
            "You can get an API key from: https://console.developers.google.com/\n"
            "1. Create a new project or select existing\n"
            "2. Enable YouTube Data API v3\n"
            "3. Create credentials (API key)\n"
            "4. Set the environment variable: export YOUTUBE_API_KEY=your_key_here"
        )
    return api_key

def extract_channel_id_from_url(channel_url: str) -> Optional[str]:
    """
    Extract channel ID from various YouTube channel URL formats.
    
    Args:
        channel_url: YouTube channel URL
        
    Returns:
        Channel ID or None if not found
    """
    # Handle different URL formats
    patterns = [
        r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        r'youtube\.com/c/([a-zA-Z0-9_-]+)',
        r'youtube\.com/user/([a-zA-Z0-9_-]+)',
        r'youtube\.com/@([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, channel_url)
        if match:
            return match.group(1)
    return None

def get_channel_id_from_handle(api_key: str, handle: str) -> Optional[str]:
    """
    Get channel ID from channel handle using YouTube API.
    
    Args:
        api_key: YouTube API key
        handle: Channel handle (e.g., 'JoshandHayden')
        
    Returns:
        Channel ID or None if not found
    """
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'type': 'channel',
        'q': handle,
        'key': api_key,
        'maxResults': 1
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get('items'):
            return data['items'][0]['snippet']['channelId']
    except requests.RequestException as e:
        print(f"Error searching for channel: {e}")
    
    return None

def get_channel_videos(api_key: str, channel_id: str, published_after: datetime) -> List[dict]:
    """
    Fetch videos from a YouTube channel published after a specific date.
    
    Args:
        api_key: YouTube API key
        channel_id: YouTube channel ID
        published_after: Only include videos published after this date
        
    Returns:
        List of video dictionaries with metadata
        
    Raises:
        YouTubeAPIError: If API request fails
    """
    videos = []
    next_page_token = None
    
    # Convert datetime to RFC 3339 format for API
    published_after_str = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    while True:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'type': 'video',
            'order': 'date',
            'publishedAfter': published_after_str,
            'maxResults': 50,
            'key': api_key
        }
        
        if next_page_token:
            params['pageToken'] = next_page_token
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                raise YouTubeAPIError(f"API Error: {data['error']['message']}")
            
            # Process videos from this page
            for item in data.get('items', []):
                video_info = {
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'published_at': item['snippet']['publishedAt'],
                    'description': item['snippet']['description'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                }
                videos.append(video_info)
            
            # Check if there are more pages
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
                
        except requests.RequestException as e:
            raise YouTubeAPIError(f"Failed to fetch videos: {e}")
    
    return videos

def fetch_recent_videos(channel_url: str, cutoff_date: datetime) -> List[str]:
    """
    Fetch YouTube video URLs from a single channel for videos published after the cutoff date.
    
    This function is used internally by fetch_videos_from_multiple_channels.
    
    Args:
        channel_url: YouTube channel URL
        cutoff_date: Only include videos published after this date
        
    Returns:
        List of YouTube video URLs
        
    Raises:
        YouTubeAPIError: If API operations fail
    """
    # Get API key
    api_key = get_api_key()
    
    # Extract channel identifier from URL
    channel_identifier = extract_channel_id_from_url(channel_url)
    if not channel_identifier:
        raise YouTubeAPIError(f"Could not extract channel identifier from URL: {channel_url}")
    
    # If it's a handle (starts with @), we need to get the channel ID
    channel_id = channel_identifier
    if channel_url.startswith('https://www.youtube.com/@'):
        channel_id = get_channel_id_from_handle(api_key, channel_identifier)
        if not channel_id:
            raise YouTubeAPIError(f"Could not find channel ID for handle: @{channel_identifier}")
    
    # Fetch videos
    videos = get_channel_videos(api_key, channel_id, cutoff_date)
    
    # Extract URLs
    video_urls = [video['url'] for video in videos]
    
    return video_urls

def fetch_videos_from_multiple_channels(channel_urls: dict, cutoff_date: datetime = None) -> dict:
    """
    Fetch YouTube video URLs from multiple channels for videos published after the cutoff date.

    Args:
        channel_urls: Dictionary with channel names as keys and URLs as values
        cutoff_date: Only include videos published after this date (defaults to first day of current month)

    Returns:
        Dictionary with channel names as keys and lists of video URLs as values

    Raises:
        YouTubeAPIError: If API operations fail
    """
    if cutoff_date is None:
        cutoff_date = get_default_cutoff_date()

    print(f"Fetching videos from {len(channel_urls)} channels...")
    print(f"Looking for videos published after: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    results = {}
    total_videos = 0
    
    for channel_name, channel_url in channel_urls.items():
        print(f"🔍 Processing channel: {channel_name}")
        print(f"   URL: {channel_url}")
        
        try:
            # Fetch videos for this channel
            video_urls = fetch_recent_videos(channel_url, cutoff_date)
            results[channel_name] = video_urls
            total_videos += len(video_urls)
            
            print(f"   ✅ Found {len(video_urls)} videos")
            
        except YouTubeAPIError as e:
            print(f"   ❌ Error fetching from {channel_name}: {e}")
            results[channel_name] = []  # Empty list for failed channels
        except Exception as e:
            print(f"   ❌ Unexpected error for {channel_name}: {e}")
            results[channel_name] = []
        
        print()  # Empty line between channels
    
    print(f"📊 Summary: Found {total_videos} total videos across {len(channel_urls)} channels")
    
    # Print summary by channel
    print("\n📋 Results by channel:")
    for channel_name, video_urls in results.items():
        print(f"   {channel_name}: {len(video_urls)} videos")
    
    return results

def save_channel_results_to_files(results: dict, output_dir: str = "config") -> None:
    """
    Save video URLs from multiple channels to organized files.
    
    Args:
        results: Dictionary with channel names as keys and lists of video URLs as values
        output_dir: Directory to save files in
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save all URLs to a single file
    all_urls = []
    for channel_name, video_urls in results.items():
        all_urls.extend(video_urls)
    
    if all_urls:
        all_urls_file = output_path / "all_channels_urls.txt"
        with open(all_urls_file, 'w', encoding='utf-8') as f:
            for url in all_urls:
                f.write(f"{url}\n")
        print(f"💾 Saved {len(all_urls)} total URLs to {all_urls_file}")
    
    # Save individual channel files
    for channel_name, video_urls in results.items():
        if video_urls:  # Only create files for channels with videos
            channel_file = output_path / f"{channel_name}_urls.txt"
            with open(channel_file, 'w', encoding='utf-8') as f:
                for url in video_urls:
                    f.write(f"{url}\n")
            print(f"💾 Saved {len(video_urls)} URLs from {channel_name} to {channel_file}")
    
    # Save a summary file
    summary_file = output_path / "channel_summary.txt"
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"Video Fetch Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")

        total_videos = sum(len(urls) for urls in results.values())
        f.write(f"Total videos found: {total_videos}\n")
        f.write(f"Channels processed: {len(results)}\n")
        
        f.write("Results by channel:\n")
        for channel_name, video_urls in results.items():
            f.write(f"  {channel_name}: {len(video_urls)} videos\n")
        
        f.write("\nChannel URLs:\n")
        for channel_name, channel_url in CHANNEL_URLS.items():
            f.write(f"  {channel_name}: {channel_url}\n")
    
    print(f"📄 Saved summary to {summary_file}")

def main():
    """
    Main function to fetch recent videos from all channels and organize in dictionary.
    """
    try:
        print("🚀 YouTube Multi-Channel Video Fetcher")
        print("=" * 50)

        # Get default cutoff date
        cutoff_date = get_default_cutoff_date()

        # Show configuration
        print(f"📅 Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')} (first day of current month)")
        print(f"🔗 Channels to process: {len(CHANNEL_URLS)}")
        for name, url in CHANNEL_URLS.items():
            print(f"   • {name}: {url}")
        print()

        # Fetch from all channels
        results = fetch_videos_from_multiple_channels(CHANNEL_URLS, cutoff_date)
        
        if not any(results.values()):
            print("No videos found matching the criteria from any channel.")
            return results
        
        # Ask user if they want to save to files
        save_to_file = input(f"\nSave URLs to organized files in config/? (y/n): ").lower().strip()
        if save_to_file in ['y', 'yes']:
            save_channel_results_to_files(results)
        
        return results
        
    except YouTubeAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()