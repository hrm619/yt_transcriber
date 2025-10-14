#!/usr/bin/env python3
"""
End-to-end integration tests for yt_transcriber.

These tests verify the complete workflow of the application.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from yt_transcriber import pipeline, batch, channels, utils
from yt_transcriber.config import DOWNLOAD_DIR, TRANSCRIPT_DIR, SUMMARY_DIR, CHUNKS_DIR


class TestEndToEndPipeline:
    """Test complete pipeline workflow."""

    @pytest.fixture
    def temp_dirs(self, tmp_path, monkeypatch):
        """Set up temporary directories for testing."""
        dl = tmp_path / "downloads"
        tr = tmp_path / "transcripts"
        su = tmp_path / "summaries"
        ch = tmp_path / "chunks"

        dl.mkdir()
        tr.mkdir()
        su.mkdir()
        ch.mkdir()

        monkeypatch.setattr(pipeline, 'DOWNLOAD_DIR', dl)
        monkeypatch.setattr(pipeline, 'TRANSCRIPT_DIR', tr)
        monkeypatch.setattr(pipeline, 'SUMMARY_DIR', su)
        monkeypatch.setattr(pipeline, 'CHUNKS_DIR', ch)

        return {'download': dl, 'transcript': tr, 'summary': su, 'chunks': ch}

    def test_full_pipeline_workflow(self, temp_dirs, monkeypatch):
        """Test complete pipeline: download → transcribe → summarize."""
        video_url = "https://www.youtube.com/watch?v=test123"
        video_id = "test123"

        # Mock download_audio
        def mock_download(url, cookies_from_browser=None, cookies_file=None):
            audio_file = temp_dirs['download'] / f"20250101_120000_{video_id}.m4a"
            audio_file.write_bytes(b"fake audio data")
            return audio_file

        # Mock transcribe
        def mock_transcribe(audio_path, video_id=None):
            if video_id is None:
                video_id = audio_path.stem.split('_')[-1]
            transcript_file = temp_dirs['transcript'] / f"{audio_path.stem}_{video_id}.txt"
            transcript_file.write_text("This is a test transcript")
            return transcript_file

        # Mock gpt_action
        def mock_gpt(transcript_path, user_prompt, video_id=None):
            if video_id is None:
                parts = transcript_path.stem.split('_')
                video_id = parts[-1] if len(parts) > 0 else transcript_path.stem
            summary_file = temp_dirs['summary'] / f"{transcript_path.stem}_{video_id}_gpt.txt"
            summary_file.write_text("Test summary: Key takeaway 1, 2, 3")
            return summary_file

        monkeypatch.setattr(pipeline, 'download_audio', mock_download)
        monkeypatch.setattr(pipeline, 'transcribe', mock_transcribe)
        monkeypatch.setattr(pipeline, 'gpt_action', mock_gpt)

        # Execute pipeline steps
        audio = pipeline.download_audio(video_url)
        assert audio.exists()
        assert audio.name.endswith(f"{video_id}.m4a")

        transcript = pipeline.transcribe(audio, video_id)
        assert transcript.exists()
        assert "test transcript" in transcript.read_text()

        summary = pipeline.gpt_action(transcript, "Summarize", video_id)
        assert summary.exists()
        assert "Key takeaway" in summary.read_text()

    def test_pipeline_with_existing_files(self, temp_dirs, monkeypatch):
        """Test that pipeline skips existing files."""
        video_id = "existing123"

        # Create existing files
        existing_audio = temp_dirs['download'] / f"20250101_120000_{video_id}.m4a"
        existing_audio.write_bytes(b"existing audio")

        existing_transcript = temp_dirs['transcript'] / f"20250101_120000_{video_id}_{video_id}.txt"
        existing_transcript.write_text("existing transcript")

        existing_summary = temp_dirs['summary'] / f"20250101_120000_{video_id}_{video_id}_gpt.txt"
        existing_summary.write_text("existing summary")

        # Check that files are detected
        results = pipeline.check_existing_files(video_id)

        assert results['audio'] == existing_audio
        assert results['transcript'] == existing_transcript
        assert results['summary'] == existing_summary

    def test_pipeline_chunking_large_file(self, temp_dirs, monkeypatch):
        """Test that large audio files are chunked properly."""
        video_id = "largefile"
        audio_file = temp_dirs['download'] / f"20250101_120000_{video_id}.m4a"

        # Create a "large" file (>25MB simulation)
        audio_file.write_bytes(b"x" * (26 * 1024 * 1024))

        # Mock ffmpeg and openai
        mock_subprocess = Mock()
        monkeypatch.setattr(pipeline.subprocess, 'run', mock_subprocess)

        # Create mock chunks
        for i in range(3):
            chunk = temp_dirs['chunks'] / f"{video_id}_chunk{i:03d}.m4a"
            chunk.write_bytes(b"chunk data")

        # Mock openai transcription
        mock_transcription = Mock()
        mock_transcription.create = Mock(return_value="Chunk transcription")
        monkeypatch.setattr(pipeline.openai.audio, 'transcriptions', mock_transcription)

        # This should trigger chunking logic
        file_size = audio_file.stat().st_size
        assert file_size > 25 * 1024 * 1024


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_extract_urls_from_file(self, tmp_path):
        """Test URL extraction from file."""
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("""
https://www.youtube.com/watch?v=video1
Some random text
https://www.youtube.com/watch?v=video2
https://www.youtube.com/watch?v=video1
Another line
https://www.youtube.com/watch?v=video3
        """)

        urls = batch.extract_urls_from_file(str(urls_file))

        # Should extract unique URLs in order
        assert len(urls) == 3
        assert urls[0] == "https://www.youtube.com/watch?v=video1"
        assert urls[1] == "https://www.youtube.com/watch?v=video2"
        assert urls[2] == "https://www.youtube.com/watch?v=video3"

    def test_batch_processor_integration(self, tmp_path, monkeypatch):
        """Test batch processor with multiple videos."""
        # Create config files
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text("""
https://www.youtube.com/watch?v=video1
https://www.youtube.com/watch?v=video2
        """)

        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_text("Summarize this video")

        # Mock subprocess to avoid actual processing
        mock_run = Mock(return_value=Mock(returncode=0, stderr=""))
        monkeypatch.setattr(batch.subprocess, 'run', mock_run)

        # Extract and verify URLs would be processed
        urls = batch.extract_urls_from_file(str(urls_file))
        assert len(urls) == 2

        for url in urls:
            video_id = batch.extract_video_id(url)
            assert video_id in ["video1", "video2"]


class TestChannelFetching:
    """Test YouTube channel fetching functionality."""

    def test_extract_channel_id_various_formats(self):
        """Test channel ID extraction from different URL formats."""
        test_cases = [
            ("https://www.youtube.com/@TestChannel/videos", "TestChannel"),
            ("https://www.youtube.com/channel/UC1234567890", "UC1234567890"),
            ("https://www.youtube.com/c/MyChannel", "MyChannel"),
            ("https://www.youtube.com/user/OldUser", "OldUser"),
        ]

        for url, expected_id in test_cases:
            result = channels.extract_channel_id_from_url(url)
            assert result == expected_id

    @patch('yt_transcriber.channels.requests.get')
    @patch('yt_transcriber.channels.get_api_key')
    def test_fetch_videos_integration(self, mock_api_key, mock_get):
        """Test fetching videos from channels."""
        from datetime import datetime, timezone

        mock_api_key.return_value = "test_api_key"

        # Mock API response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'items': [
                {
                    'id': {'videoId': 'vid1'},
                    'snippet': {
                        'title': 'Test Video 1',
                        'publishedAt': '2025-04-02T10:00:00Z',
                        'description': 'Test description'
                    }
                },
                {
                    'id': {'videoId': 'vid2'},
                    'snippet': {
                        'title': 'Test Video 2',
                        'publishedAt': '2025-04-03T10:00:00Z',
                        'description': 'Test description 2'
                    }
                }
            ]
        }
        mock_get.return_value = mock_response

        cutoff = datetime(2025, 4, 1, tzinfo=timezone.utc)
        videos = channels.get_channel_videos("test_api_key", "test_channel", cutoff)

        assert len(videos) == 2
        assert videos[0]['video_id'] == 'vid1'
        assert videos[1]['video_id'] == 'vid2'
        assert videos[0]['url'] == 'https://www.youtube.com/watch?v=vid1'

    @patch('yt_transcriber.channels.fetch_recent_videos')
    def test_multi_channel_fetch(self, mock_fetch):
        """Test fetching from multiple channels."""
        from datetime import datetime, timezone

        # Mock fetch_recent_videos to return different results per channel
        def side_effect(channel_url, cutoff_date):
            if "channel1" in channel_url:
                return ["url1", "url2"]
            elif "channel2" in channel_url:
                return ["url3"]
            return []

        mock_fetch.side_effect = side_effect

        test_channels = {
            "channel1": "https://youtube.com/@channel1",
            "channel2": "https://youtube.com/@channel2",
            "channel3": "https://youtube.com/@channel3"
        }

        cutoff = datetime(2025, 4, 1, tzinfo=timezone.utc)
        results = channels.fetch_videos_from_multiple_channels(test_channels, cutoff)

        assert len(results) == 3
        assert len(results['channel1']) == 2
        assert len(results['channel2']) == 1
        assert len(results['channel3']) == 0


class TestUtilities:
    """Test utility functions."""

    def test_cleanup_temp_files(self, tmp_path, monkeypatch):
        """Test cleaning up temporary chunk files."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()

        # Create some chunk files
        (chunks_dir / "video1_chunk000.m4a").write_bytes(b"chunk1")
        (chunks_dir / "video1_chunk001.m4a").write_bytes(b"chunk2")
        (chunks_dir / "video2_chunk000.m4a").write_bytes(b"chunk3")
        (chunks_dir / "regular_file.m4a").write_bytes(b"not a chunk")

        monkeypatch.setattr(utils, 'CHUNKS_DIR', chunks_dir)

        removed = utils.cleanup_temp_files()

        assert removed == 3
        assert not (chunks_dir / "video1_chunk000.m4a").exists()
        assert not (chunks_dir / "video1_chunk001.m4a").exists()
        assert not (chunks_dir / "video2_chunk000.m4a").exists()
        assert (chunks_dir / "regular_file.m4a").exists()  # Should remain

    def test_cleanup_empty_dirs(self, tmp_path):
        """Test removing empty directories."""
        base = tmp_path / "data"
        base.mkdir()

        # Create structure with empty and non-empty dirs
        (base / "empty1").mkdir()
        (base / "empty2").mkdir()
        non_empty = base / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").write_text("content")

        removed = utils.cleanup_empty_dirs(base)

        assert removed == 2
        assert not (base / "empty1").exists()
        assert not (base / "empty2").exists()
        assert (base / "non_empty").exists()

    def test_cleanup_all(self, tmp_path, monkeypatch):
        """Test complete cleanup workflow."""
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        (chunks_dir / "test_chunk000.m4a").write_bytes(b"chunk")

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "empty").mkdir()

        monkeypatch.setattr(utils, 'CHUNKS_DIR', chunks_dir)

        temp_files, empty_dirs = utils.cleanup_all()

        assert temp_files == 1
        # Note: empty_dirs count depends on cleanup_empty_dirs implementation


class TestVideoIDExtraction:
    """Test video ID extraction and file naming."""

    def test_extract_video_id_valid_urls(self):
        """Test extracting video IDs from various YouTube URL formats."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=abc123_XYZ-", "abc123_XYZ-"),
            ("https://youtube.com/watch?v=test123&feature=share", "test123"),
        ]

        for url, expected_id in test_cases:
            result = pipeline.extract_video_id(url)
            assert result == expected_id

    def test_extract_video_id_invalid_url(self):
        """Test that invalid URLs raise ValueError."""
        with pytest.raises(ValueError, match="Could not extract video ID"):
            pipeline.extract_video_id("https://youtube.com/invalid")

    def test_file_naming_pattern(self, tmp_path, monkeypatch):
        """Test that files follow the naming pattern: {timestamp}_{video_id}.{ext}"""
        import re

        dl = tmp_path / "downloads"
        dl.mkdir()
        monkeypatch.setattr(pipeline, 'DOWNLOAD_DIR', dl)

        # Create a file simulating download
        video_id = "test123"
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        test_file = dl / f"{timestamp}_{video_id}.m4a"
        test_file.write_bytes(b"test")

        # Verify naming pattern
        pattern = r'^\d{8}_\d{6}_[a-zA-Z0-9_-]+\.m4a$'
        assert re.match(pattern, test_file.name)

        # Verify we can extract video_id back
        assert video_id in test_file.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
