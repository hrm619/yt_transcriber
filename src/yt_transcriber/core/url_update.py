#!/usr/bin/env python3
"""
YouTube Channel URL Fetcher

This script fetches YouTube video URLs from a channel for videos published after January 1, 2025.
It uses the YouTube Data API v3 to get accurate metadata including publish dates.

Requirements:
- YouTube Data API v3 key (set as YOUTUBE_API_KEY environment variable)
- python-dateutil for date parsing
- requests for API calls

Usage:
    python src/yt_transcriber/core/url_update.py
    
    # Or import and use as a module:
    from src.yt_transcriber.core.url_update import fetch_recent_videos
    video_urls = fetch_recent_videos(channel_url, cutoff_date)
"""

import os
import re
import sys
import requests
from datetime import datetime, timezone
from typing import List, Optional
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Channel URL to fetch from
underdog_url = "https://www.youtube.com/@JoshandHayden/videos"

# Cutoff date - videos published after this date will be included
CUTOFF_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)

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
    Fetch YouTube video URLs from a channel for videos published after the cutoff date.
    
    Args:
        channel_url: YouTube channel URL
        cutoff_date: Only include videos published after this date
        
    Returns:
        List of YouTube video URLs
        
    Raises:
        YouTubeAPIError: If API operations fail
    """
    print(f"Fetching videos from: {channel_url}")
    print(f"Looking for videos published after: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Get API key
    api_key = get_api_key()
    
    # Extract channel identifier from URL
    channel_identifier = extract_channel_id_from_url(channel_url)
    if not channel_identifier:
        raise YouTubeAPIError(f"Could not extract channel identifier from URL: {channel_url}")
    
    # If it's a handle (starts with @), we need to get the channel ID
    channel_id = channel_identifier
    if channel_url.startswith('https://www.youtube.com/@'):
        print(f"Resolving channel handle: @{channel_identifier}")
        channel_id = get_channel_id_from_handle(api_key, channel_identifier)
        if not channel_id:
            raise YouTubeAPIError(f"Could not find channel ID for handle: @{channel_identifier}")
        print(f"Found channel ID: {channel_id}")
    
    # Fetch videos
    print("Fetching videos...")
    videos = get_channel_videos(api_key, channel_id, cutoff_date)
    
    # Extract URLs
    video_urls = [video['url'] for video in videos]
    
    print(f"Found {len(video_urls)} videos published after {cutoff_date.strftime('%Y-%m-%d')}")
    
    # Print video details for verification
    if videos:
        print("\nVideo details:")
        for i, video in enumerate(videos, 1):
            published_date = datetime.fromisoformat(video['published_at'].replace('Z', '+00:00'))
            print(f"{i:2d}. {video['title'][:60]}...")
            print(f"    Published: {published_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"    URL: {video['url']}")
            print()
    
    return video_urls

def save_urls_to_file(urls: List[str], output_file: str = "config/urls.txt") -> None:
    """
    Save video URLs to a file for use with the batch processor.
    
    Args:
        urls: List of YouTube video URLs
        output_file: Path to output file
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(f"{url}\n")
    
    print(f"Saved {len(urls)} URLs to {output_file}")

def main():
    """
    Main function to fetch recent videos and optionally save to file.
    """
    try:
        # Fetch recent video URLs
        video_urls = fetch_recent_videos(underdog_url, CUTOFF_DATE)
        
        if not video_urls:
            print("No videos found matching the criteria.")
            return
        
        # Print URLs
        print(f"\nFound {len(video_urls)} video URLs:")
        for i, url in enumerate(video_urls, 1):
            print(f"{i:2d}. {url}")
        
        # Ask user if they want to save to file
        save_to_file = input(f"\nSave URLs to config/urls.txt? (y/n): ").lower().strip()
        if save_to_file in ['y', 'yes']:
            save_urls_to_file(video_urls)
        
        return video_urls
        
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