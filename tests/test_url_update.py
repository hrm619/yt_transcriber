#!/usr/bin/env python3
"""
Tests for the YouTube URL fetcher and channel config functionality.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from yt_transcriber.channels import (
    YouTubeAPIError,
    extract_channel_id_from_url,
    get_api_key,
    get_default_cutoff_date,
    load_channels_from_config,
)


class TestURLExtraction:
    """Test URL extraction functionality."""

    def test_extract_channel_id_from_handle_url(self):
        url = "https://www.youtube.com/@JoshandHayden/videos"
        assert extract_channel_id_from_url(url) == "JoshandHayden"

    def test_extract_channel_id_from_channel_url(self):
        url = "https://www.youtube.com/channel/UC1234567890abcdef"
        assert extract_channel_id_from_url(url) == "UC1234567890abcdef"

    def test_extract_channel_id_from_c_url(self):
        url = "https://www.youtube.com/c/TestChannel"
        assert extract_channel_id_from_url(url) == "TestChannel"

    def test_extract_channel_id_from_user_url(self):
        url = "https://www.youtube.com/user/TestUser"
        assert extract_channel_id_from_url(url) == "TestUser"

    def test_extract_channel_id_invalid_url(self):
        url = "https://www.example.com/invalid"
        assert extract_channel_id_from_url(url) is None


class TestAPIKey:
    """Test API key functionality."""

    @patch.dict('os.environ', {}, clear=True)
    def test_get_api_key_missing(self):
        with pytest.raises(YouTubeAPIError, match="YouTube API key not found"):
            get_api_key()

    @patch.dict('os.environ', {'YOUTUBE_API_KEY': 'test_key_123'})
    def test_get_api_key_present(self):
        assert get_api_key() == 'test_key_123'


class TestLoadChannelsFromConfig:
    """Test loading channels from YAML config."""

    def test_load_valid_config(self, tmp_path):
        config = tmp_path / "channels.yaml"
        config.write_text(
            "channels:\n"
            '  - name: "test_channel"\n'
            '    url: "https://www.youtube.com/@TestChannel/videos"\n'
            '  - name: "other"\n'
            '    url: "https://www.youtube.com/@Other/videos"\n'
        )
        result = load_channels_from_config(config)
        assert result == {
            "test_channel": "https://www.youtube.com/@TestChannel/videos",
            "other": "https://www.youtube.com/@Other/videos",
        }

    def test_load_missing_file(self, tmp_path):
        config = tmp_path / "nonexistent.yaml"
        with pytest.raises(FileNotFoundError):
            load_channels_from_config(config)

    def test_load_empty_channels(self, tmp_path):
        config = tmp_path / "channels.yaml"
        config.write_text("channels: []\n")
        with pytest.raises(ValueError, match="No channels defined"):
            load_channels_from_config(config)

    def test_load_missing_key(self, tmp_path):
        config = tmp_path / "channels.yaml"
        config.write_text("other_key: value\n")
        with pytest.raises(ValueError, match="missing 'channels' key"):
            load_channels_from_config(config)


class TestVideoFetching:
    """Test video fetching functionality."""

    @patch('yt_transcriber.channels.requests.get')
    @patch('yt_transcriber.channels.get_api_key')
    def test_get_channel_videos_success(self, mock_get_api_key, mock_requests_get):
        from yt_transcriber.channels import get_channel_videos

        mock_get_api_key.return_value = 'test_key'

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'items': [
                {
                    'id': {'videoId': 'test_video_1'},
                    'snippet': {
                        'title': 'Test Video 1',
                        'publishedAt': '2025-01-02T10:00:00Z',
                        'description': 'Test description',
                    },
                }
            ]
        }
        mock_requests_get.return_value = mock_response

        cutoff_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = get_channel_videos('test_key', 'test_channel_id', cutoff_date)

        assert len(result) == 1
        assert result[0]['video_id'] == 'test_video_1'
        assert result[0]['url'] == 'https://www.youtube.com/watch?v=test_video_1'


class TestMultiChannelFetching:
    """Test multi-channel video fetching functionality."""

    @patch('yt_transcriber.channels.fetch_recent_videos')
    def test_fetch_videos_from_multiple_channels(self, mock_fetch_recent_videos):
        from yt_transcriber.channels import fetch_videos_from_multiple_channels

        def mock_fetch(channel_url, cutoff_date):
            if "Channel1" in channel_url:
                return ["https://www.youtube.com/watch?v=test1", "https://www.youtube.com/watch?v=test2"]
            elif "Channel2" in channel_url:
                return ["https://www.youtube.com/watch?v=test3"]
            return []

        mock_fetch_recent_videos.side_effect = mock_fetch

        test_channels = {
            "ch1": "https://www.youtube.com/@Channel1/videos",
            "ch2": "https://www.youtube.com/@Channel2/videos",
            "empty": "https://www.youtube.com/@EmptyChannel/videos",
        }

        cutoff_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        result = fetch_videos_from_multiple_channels(test_channels, cutoff_date)

        assert len(result) == 3
        assert len(result["ch1"]) == 2
        assert len(result["ch2"]) == 1
        assert len(result["empty"]) == 0


def test_get_default_cutoff_date():
    cutoff = get_default_cutoff_date()
    assert isinstance(cutoff, datetime)
    assert cutoff.tzinfo == timezone.utc
    assert cutoff.day == 1
    assert cutoff.hour == 0

    now = datetime.now(timezone.utc)
    assert cutoff.year == now.year
    assert cutoff.month == now.month


if __name__ == "__main__":
    pytest.main([__file__])
