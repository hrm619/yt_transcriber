#!/usr/bin/env python3
"""
YouTube Channel URL Fetcher

Fetches YouTube video URLs from channels for videos published after a cutoff date.
Uses the YouTube Data API v3 for accurate metadata.

Requirements:
- YouTube Data API v3 key (set in .env as YOUTUBE_API_KEY)
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests
import yaml

from .config import CONFIG_DIR

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CHANNELS_CONFIG_PATH = CONFIG_DIR / "channels.yaml"


class YouTubeAPIError(Exception):
    """Custom exception for YouTube API errors."""
    pass


def load_channels_from_config(config_path: Path | None = None) -> dict[str, str]:
    """Load channel configuration from a YAML file.

    Args:
        config_path: Path to channels.yaml. Defaults to config/channels.yaml.

    Returns:
        Dictionary mapping channel names to URLs.

    Raises:
        FileNotFoundError: If config file does not exist.
        ValueError: If config file is empty or malformed.
    """
    if config_path is None:
        config_path = CHANNELS_CONFIG_PATH

    if not config_path.exists():
        raise FileNotFoundError(
            f"Channel config not found: {config_path}\n"
            "Create config/channels.yaml with your channel list."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "channels" not in data:
        raise ValueError(f"Invalid channels config: {config_path} (missing 'channels' key)")

    channels: dict[str, str] = {}
    for entry in data["channels"]:
        name = entry.get("name")
        url = entry.get("url")
        if name and url:
            channels[name] = url

    if not channels:
        raise ValueError(f"No channels defined in {config_path}")

    return channels


def get_default_cutoff_date() -> datetime:
    """Return the first day of the current month at midnight UTC."""
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, 1, tzinfo=timezone.utc)


def get_api_key() -> str:
    """Get YouTube API key from environment variable.

    Raises:
        YouTubeAPIError: If API key is not set.
    """
    api_key = os.getenv('YOUTUBE_API_KEY')
    if not api_key:
        raise YouTubeAPIError(
            "YouTube API key not found. Set YOUTUBE_API_KEY in your environment.\n"
            "Get a key at https://console.developers.google.com/"
        )
    return api_key


def extract_channel_id_from_url(channel_url: str) -> Optional[str]:
    """Extract channel identifier from a YouTube channel URL."""
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
    """Resolve a channel handle to a channel ID via the YouTube API."""
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'type': 'channel',
        'q': handle,
        'key': api_key,
        'maxResults': 1,
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


def get_channel_videos(
    api_key: str, channel_id: str, published_after: datetime
) -> list[dict]:
    """Fetch videos from a channel published after a given date.

    Raises:
        YouTubeAPIError: If the API request fails.
    """
    videos: list[dict] = []
    next_page_token = None
    published_after_str = published_after.strftime('%Y-%m-%dT%H:%M:%SZ')

    while True:
        url = "https://www.googleapis.com/youtube/v3/search"
        params: dict = {
            'part': 'snippet',
            'channelId': channel_id,
            'type': 'video',
            'order': 'date',
            'publishedAfter': published_after_str,
            'maxResults': 50,
            'key': api_key,
        }
        if next_page_token:
            params['pageToken'] = next_page_token

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                raise YouTubeAPIError(f"API Error: {data['error']['message']}")

            for item in data.get('items', []):
                videos.append({
                    'video_id': item['id']['videoId'],
                    'title': item['snippet']['title'],
                    'published_at': item['snippet']['publishedAt'],
                    'description': item['snippet']['description'],
                    'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                })

            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
        except requests.RequestException as e:
            raise YouTubeAPIError(f"Failed to fetch videos: {e}")

    return videos


def fetch_recent_videos(channel_url: str, cutoff_date: datetime) -> list[str]:
    """Fetch video URLs from a single channel published after the cutoff date.

    Raises:
        YouTubeAPIError: If API operations fail.
    """
    api_key = get_api_key()

    channel_identifier = extract_channel_id_from_url(channel_url)
    if not channel_identifier:
        raise YouTubeAPIError(f"Could not extract channel identifier from: {channel_url}")

    channel_id = channel_identifier
    if channel_url.startswith('https://www.youtube.com/@'):
        channel_id = get_channel_id_from_handle(api_key, channel_identifier)
        if not channel_id:
            raise YouTubeAPIError(f"Could not find channel ID for @{channel_identifier}")

    videos = get_channel_videos(api_key, channel_id, cutoff_date)
    return [video['url'] for video in videos]


def fetch_videos_from_multiple_channels(
    channel_urls: dict[str, str],
    cutoff_date: datetime | None = None,
) -> dict[str, list[str]]:
    """Fetch video URLs from multiple channels.

    Args:
        channel_urls: Mapping of channel names to URLs.
        cutoff_date: Only include videos after this date (default: first of month).

    Returns:
        Mapping of channel names to lists of video URLs.
    """
    if cutoff_date is None:
        cutoff_date = get_default_cutoff_date()

    print(f"Fetching videos from {len(channel_urls)} channels...")
    print(f"Looking for videos published after: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()

    results: dict[str, list[str]] = {}
    total_videos = 0

    for channel_name, channel_url in channel_urls.items():
        print(f"Processing channel: {channel_name}")
        print(f"   URL: {channel_url}")

        try:
            video_urls = fetch_recent_videos(channel_url, cutoff_date)
            results[channel_name] = video_urls
            total_videos += len(video_urls)
            print(f"   Found {len(video_urls)} videos")
        except YouTubeAPIError as e:
            print(f"   Error fetching from {channel_name}: {e}")
            results[channel_name] = []
        except Exception as e:
            print(f"   Unexpected error for {channel_name}: {e}")
            results[channel_name] = []

        print()

    print(f"Summary: Found {total_videos} total videos across {len(channel_urls)} channels")
    print("\nResults by channel:")
    for channel_name, video_urls in results.items():
        print(f"   {channel_name}: {len(video_urls)} videos")

    return results


def save_channel_results_to_files(
    results: dict[str, list[str]],
    channel_urls: dict[str, str],
    output_dir: str = "config",
) -> None:
    """Save video URLs from multiple channels to organized files.

    Args:
        results: Mapping of channel names to lists of video URLs.
        channel_urls: Mapping of channel names to channel URLs (for summary).
        output_dir: Directory to save files in.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    all_urls: list[str] = []
    for video_urls in results.values():
        all_urls.extend(video_urls)

    if all_urls:
        all_urls_file = output_path / "all_channels_urls.txt"
        with open(all_urls_file, 'w', encoding='utf-8') as f:
            for url in all_urls:
                f.write(f"{url}\n")
        print(f"Saved {len(all_urls)} total URLs to {all_urls_file}")

    for channel_name, video_urls in results.items():
        if video_urls:
            channel_file = output_path / f"{channel_name}_urls.txt"
            with open(channel_file, 'w', encoding='utf-8') as f:
                for url in video_urls:
                    f.write(f"{url}\n")
            print(f"Saved {len(video_urls)} URLs from {channel_name} to {channel_file}")

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
        for channel_name, channel_url in channel_urls.items():
            f.write(f"  {channel_name}: {channel_url}\n")

    print(f"Saved summary to {summary_file}")


def main() -> None:
    """Fetch recent videos from all configured channels."""
    try:
        print("YouTube Multi-Channel Video Fetcher")
        print("=" * 50)

        channel_urls = load_channels_from_config()
        cutoff_date = get_default_cutoff_date()

        print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Channels to process: {len(channel_urls)}")
        for name, url in channel_urls.items():
            print(f"   - {name}: {url}")
        print()

        results = fetch_videos_from_multiple_channels(channel_urls, cutoff_date)

        if not any(results.values()):
            print("No videos found matching the criteria from any channel.")
            return

        save_channel_results_to_files(results, channel_urls)

    except (YouTubeAPIError, FileNotFoundError, ValueError) as e:
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
