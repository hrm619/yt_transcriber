# YouTube URL Fetcher

This document explains the YouTube URL fetcher functionality that was added to the yt_transcriber project.

## Overview

The YouTube URL fetcher automatically retrieves video URLs from a YouTube channel for videos published after January 1, 2025. It uses the YouTube Data API v3 to get accurate metadata including publish dates.

## Files Created/Modified

### Core Functionality
- **`src/yt_transcriber/core/url_update.py`**: Main URL fetcher script
- **`requirements.txt`**: Updated with necessary dependencies

### Setup and Configuration
- **`setup_api.py`**: Interactive setup script for YouTube API key
- **`scripts/fetch_recent_videos.py`**: Demonstration script
- **`example_usage.py`**: Simple usage example

### Testing
- **`tests/test_url_update.py`**: Unit tests for URL fetcher functionality

### Documentation
- **`README.md`**: Updated with new functionality
- **`YOUTUBE_URL_FETCHER.md`**: This documentation file

## Features

1. **Multiple URL Format Support**: Handles various YouTube channel URL formats:
   - `https://www.youtube.com/@ChannelHandle/videos`
   - `https://www.youtube.com/channel/CHANNEL_ID`
   - `https://www.youtube.com/c/ChannelName`
   - `https://www.youtube.com/user/UserName`

2. **Date Filtering**: Only fetches videos published after January 1, 2025

3. **Pagination Support**: Handles multiple pages of results from the API

4. **Error Handling**: Comprehensive error handling for API failures

5. **Integration**: Saves URLs to `config/urls.txt` for use with existing batch processor

## Setup Instructions

1. **Install Dependencies**:
   ```bash
   uv pip install -r requirements.txt
   ```

2. **Get YouTube API Key**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing
   - Enable YouTube Data API v3
   - Create an API key
   - Optionally restrict the key to YouTube Data API v3

3. **Configure API Key**:
   ```bash
   python setup_api.py
   ```
   Or manually set the environment variable:
   ```bash
   export YOUTUBE_API_KEY=your_api_key_here
   ```

## Usage Examples

### Basic Usage
```bash
# Fetch videos and optionally save to config/urls.txt
python src/yt_transcriber/core/url_update.py

# Run the demonstration script
python scripts/fetch_recent_videos.py

# Test basic functionality without API key
python example_usage.py
```

### Programmatic Usage
```python
from src.yt_transcriber.core.url_update import fetch_recent_videos
from datetime import datetime, timezone

channel_url = "https://www.youtube.com/@JoshandHayden/videos"
cutoff_date = datetime(2025, 1, 1, tzinfo=timezone.utc)

video_urls = fetch_recent_videos(channel_url, cutoff_date)
print(f"Found {len(video_urls)} videos")
```

### Integration with Batch Processor
```bash
# 1. Fetch recent videos
python src/yt_transcriber/core/url_update.py

# 2. Process the videos
python run_batch.py
```

## Configuration

The main configuration is in `src/yt_transcriber/core/url_update.py`:

- **`underdog_url`**: The YouTube channel URL to fetch from
- **`CUTOFF_DATE`**: Only videos published after this date are included
- **`YOUTUBE_API_KEY`**: Environment variable for API authentication

## API Response Format

The script returns a list of video dictionaries with the following structure:
```python
{
    'video_id': 'VIDEO_ID',
    'title': 'Video Title',
    'published_at': '2025-01-02T10:00:00Z',
    'description': 'Video description',
    'url': 'https://www.youtube.com/watch?v=VIDEO_ID'
}
```

## Error Handling

The script handles various error conditions:
- Missing API key
- Invalid channel URLs
- API rate limiting
- Network errors
- Invalid API responses

## Testing

Run the tests to verify functionality:
```bash
python -m pytest tests/test_url_update.py -v
```

Test basic functionality without API key:
```bash
python example_usage.py
```

## Integration with Existing Pipeline

The URL fetcher integrates seamlessly with the existing yt_transcriber pipeline:

1. **Fetch URLs**: Use the URL fetcher to get recent video URLs
2. **Save to Config**: URLs are saved to `config/urls.txt`
3. **Batch Process**: Use the existing batch processor to transcribe and summarize videos

## Limitations

- Requires YouTube Data API v3 key (free tier has quotas)
- Only fetches public videos (private videos require OAuth)
- API quota limits may restrict the number of requests
- Date filtering relies on YouTube's publishedAt metadata

## Future Enhancements

Possible improvements:
- OAuth support for private videos
- Configurable date ranges
- Multiple channel support
- Playlist support
- Video duration filtering
- View count filtering

## Troubleshooting

**"No module named 'requests'"**:
```bash
uv pip install requests
```

**"YouTube API key not found"**:
```bash
export YOUTUBE_API_KEY=your_key_here
# or run: python setup_api.py
```

**"Could not extract channel identifier"**:
- Verify the channel URL format
- Ensure the URL is a valid YouTube channel URL

**"API Error: quotaExceeded"**:
- You've exceeded your daily API quota
- Wait until quota resets or increase limits in Google Cloud Console 