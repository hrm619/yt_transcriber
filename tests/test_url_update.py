#!/usr/bin/env python3
"""
Tests for the YouTube URL fetcher functionality.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.yt_transcriber.core.url_update import (
    extract_channel_id_from_url,
    YouTubeAPIError,
    get_api_key
)

class TestURLExtraction:
    """Test URL extraction functionality."""
    
    def test_extract_channel_id_from_handle_url(self):
        """Test extracting channel ID from @handle URL."""
        url = "https://www.youtube.com/@JoshandHayden/videos"
        result = extract_channel_id_from_url(url)
        assert result == "JoshandHayden"
    
    def test_extract_channel_id_from_channel_url(self):
        """Test extracting channel ID from channel/ URL."""
        url = "https://www.youtube.com/channel/UC1234567890abcdef"
        result = extract_channel_id_from_url(url)
        assert result == "UC1234567890abcdef"
    
    def test_extract_channel_id_from_c_url(self):
        """Test extracting channel ID from /c/ URL."""
        url = "https://www.youtube.com/c/TestChannel"
        result = extract_channel_id_from_url(url)
        assert result == "TestChannel"
    
    def test_extract_channel_id_from_user_url(self):
        """Test extracting channel ID from /user/ URL."""
        url = "https://www.youtube.com/user/TestUser"
        result = extract_channel_id_from_url(url)
        assert result == "TestUser"
    
    def test_extract_channel_id_invalid_url(self):
        """Test extracting channel ID from invalid URL."""
        url = "https://www.example.com/invalid"
        result = extract_channel_id_from_url(url)
        assert result is None

class TestAPIKey:
    """Test API key functionality."""
    
    @patch.dict('os.environ', {}, clear=True)
    def test_get_api_key_missing(self):
        """Test getting API key when not set."""
        with pytest.raises(YouTubeAPIError) as exc_info:
            get_api_key()
        assert "YouTube API key not found" in str(exc_info.value)
    
    @patch.dict('os.environ', {'YOUTUBE_API_KEY': 'test_key_123'})
    def test_get_api_key_present(self):
        """Test getting API key when set."""
        result = get_api_key()
        assert result == 'test_key_123'

class TestVideoFetching:
    """Test video fetching functionality."""
    
    @patch('src.yt_transcriber.core.url_update.requests.get')
    @patch('src.yt_transcriber.core.url_update.get_api_key')
    def test_get_channel_videos_success(self, mock_get_api_key, mock_requests_get):
        """Test successful video fetching."""
        from src.yt_transcriber.core.url_update import get_channel_videos
        
        # Mock API key
        mock_get_api_key.return_value = 'test_key'
        
        # Mock API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'items': [
                {
                    'id': {'videoId': 'test_video_1'},
                    'snippet': {
                        'title': 'Test Video 1',
                        'publishedAt': '2025-01-02T10:00:00Z',
                        'description': 'Test description'
                    }
                }
            ]
        }
        mock_requests_get.return_value = mock_response
        
        # Test
        cutoff_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = get_channel_videos('test_key', 'test_channel_id', cutoff_date)
        
        # Verify
        assert len(result) == 1
        assert result[0]['video_id'] == 'test_video_1'
        assert result[0]['title'] == 'Test Video 1'
        assert result[0]['url'] == 'https://www.youtube.com/watch?v=test_video_1'

def test_constants():
    """Test that constants are properly defined."""
    from src.yt_transcriber.core.url_update import underdog_url, CUTOFF_DATE
    
    assert underdog_url == "https://www.youtube.com/@JoshandHayden/videos"
    assert CUTOFF_DATE.year == 2025
    assert CUTOFF_DATE.month == 1
    assert CUTOFF_DATE.day == 1

if __name__ == "__main__":
    pytest.main([__file__]) 