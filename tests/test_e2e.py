#!/usr/bin/env python3
"""
End-to-end integration tests for yt_transcriber.
"""

from unittest.mock import Mock, patch

import pytest

from yt_transcriber import batch, channels, pipeline, utils


class TestEndToEndPipeline:
    """Test complete pipeline workflow."""

    @pytest.fixture
    def temp_dirs(self, tmp_path, monkeypatch):
        dl = tmp_path / "downloads"
        dl.mkdir()
        tr = tmp_path / "transcripts"
        tr.mkdir()
        su = tmp_path / "summaries"
        su.mkdir()
        ch = tmp_path / "chunks"
        ch.mkdir()

        monkeypatch.setattr(pipeline, "DOWNLOAD_DIR", dl)
        monkeypatch.setattr(pipeline, "TRANSCRIPT_DIR", tr)
        monkeypatch.setattr(pipeline, "SUMMARY_DIR", su)
        monkeypatch.setattr(pipeline, "CHUNKS_DIR", ch)

        return {"download": dl, "transcript": tr, "summary": su, "chunks": ch}

    def test_full_pipeline_workflow(self, temp_dirs, monkeypatch):
        video_url = "https://www.youtube.com/watch?v=test123"
        video_id = "test123"

        def mock_download(url, cookies_from_browser=None, cookies_file=None):
            audio_file = temp_dirs["download"] / f"20250101_120000_{video_id}.m4a"
            audio_file.write_bytes(b"fake audio data")
            return audio_file

        def mock_transcribe(audio_path, video_id=None):
            if video_id is None:
                video_id = audio_path.stem.split("_")[-1]
            transcript_file = temp_dirs["transcript"] / f"{audio_path.stem}_{video_id}.txt"
            transcript_file.write_text("This is a test transcript")
            return transcript_file

        def mock_gpt(transcript_path, user_prompt, video_id=None):
            if video_id is None:
                parts = transcript_path.stem.split("_")
                video_id = parts[-1] if parts else transcript_path.stem
            summary_file = temp_dirs["summary"] / f"{transcript_path.stem}_{video_id}_gpt.txt"
            summary_file.write_text("Test summary: Key takeaway 1, 2, 3")
            return summary_file

        monkeypatch.setattr(pipeline, "download_audio", mock_download)
        monkeypatch.setattr(pipeline, "transcribe", mock_transcribe)
        monkeypatch.setattr(pipeline, "gpt_action", mock_gpt)

        audio = pipeline.download_audio(video_url)
        assert audio.exists()
        assert audio.name.endswith(f"{video_id}.m4a")

        transcript = pipeline.transcribe(audio, video_id)
        assert transcript.exists()
        assert "test transcript" in transcript.read_text()

        summary = pipeline.gpt_action(transcript, "Summarize", video_id)
        assert summary.exists()
        assert "Key takeaway" in summary.read_text()

    def test_pipeline_with_existing_files(self, temp_dirs):
        video_id = "existing123"

        existing_audio = temp_dirs["download"] / f"20250101_120000_{video_id}.m4a"
        existing_audio.write_bytes(b"existing audio")

        existing_transcript = temp_dirs["transcript"] / f"20250101_120000_{video_id}_{video_id}.txt"
        existing_transcript.write_text("existing transcript")

        existing_summary = temp_dirs["summary"] / f"20250101_120000_{video_id}_{video_id}_gpt.txt"
        existing_summary.write_text("existing summary")

        results = pipeline.check_existing_files(video_id)
        assert results["audio"] == existing_audio
        assert results["transcript"] == existing_transcript
        assert results["summary"] == existing_summary

    def test_pipeline_chunking_large_file(self, temp_dirs):
        video_id = "largefile"
        audio_file = temp_dirs["download"] / f"20250101_120000_{video_id}.m4a"
        audio_file.write_bytes(b"x" * (26 * 1024 * 1024))

        file_size = audio_file.stat().st_size
        assert file_size > 25 * 1024 * 1024


class TestBatchProcessing:
    """Test batch processing functionality."""

    def test_extract_urls_from_file(self, tmp_path):
        urls_file = tmp_path / "urls.txt"
        urls_file.write_text(
            "https://www.youtube.com/watch?v=video1\n"
            "Some random text\n"
            "https://www.youtube.com/watch?v=video2\n"
            "https://www.youtube.com/watch?v=video1\n"
            "Another line\n"
            "https://www.youtube.com/watch?v=video3\n"
        )

        urls = batch.extract_urls_from_file(str(urls_file))
        assert len(urls) == 3
        assert urls[0] == "https://www.youtube.com/watch?v=video1"
        assert urls[1] == "https://www.youtube.com/watch?v=video2"
        assert urls[2] == "https://www.youtube.com/watch?v=video3"

    def test_batch_uses_direct_calls(self):
        """Confirm batch.py imports pipeline functions directly, not subprocess."""
        import inspect

        source = inspect.getsource(batch)
        assert "subprocess" not in source


class TestChannelFetching:
    """Test YouTube channel fetching functionality."""

    def test_extract_channel_id_various_formats(self):
        test_cases = [
            ("https://www.youtube.com/@TestChannel/videos", "TestChannel"),
            ("https://www.youtube.com/channel/UC1234567890", "UC1234567890"),
            ("https://www.youtube.com/c/MyChannel", "MyChannel"),
            ("https://www.youtube.com/user/OldUser", "OldUser"),
        ]
        for url, expected_id in test_cases:
            assert channels.extract_channel_id_from_url(url) == expected_id

    @patch("yt_transcriber.channels.requests.get")
    @patch("yt_transcriber.channels.get_api_key")
    def test_fetch_videos_integration(self, mock_api_key, mock_get):
        from datetime import datetime, timezone

        mock_api_key.return_value = "test_api_key"

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid1"},
                    "snippet": {
                        "title": "Test Video 1",
                        "publishedAt": "2025-04-02T10:00:00Z",
                        "description": "Test description",
                    },
                },
                {
                    "id": {"videoId": "vid2"},
                    "snippet": {
                        "title": "Test Video 2",
                        "publishedAt": "2025-04-03T10:00:00Z",
                        "description": "Test description 2",
                    },
                },
            ]
        }
        mock_get.return_value = mock_response

        cutoff = datetime(2025, 4, 1, tzinfo=timezone.utc)
        videos = channels.get_channel_videos("test_api_key", "test_channel", cutoff)

        assert len(videos) == 2
        assert videos[0]["video_id"] == "vid1"
        assert videos[0]["url"] == "https://www.youtube.com/watch?v=vid1"

    @patch("yt_transcriber.channels.fetch_recent_videos")
    def test_multi_channel_fetch(self, mock_fetch):
        from datetime import datetime, timezone

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
            "channel3": "https://youtube.com/@channel3",
        }

        cutoff = datetime(2025, 1, 1, tzinfo=timezone.utc)
        results = channels.fetch_videos_from_multiple_channels(test_channels, cutoff)

        assert len(results) == 3
        assert len(results["channel1"]) == 2
        assert len(results["channel2"]) == 1
        assert len(results["channel3"]) == 0


class TestUtilities:
    """Test utility functions."""

    def test_cleanup_temp_files(self, tmp_path, monkeypatch):
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()

        (chunks_dir / "video1_chunk000.m4a").write_bytes(b"chunk1")
        (chunks_dir / "video1_chunk001.m4a").write_bytes(b"chunk2")
        (chunks_dir / "video2_chunk000.m4a").write_bytes(b"chunk3")
        (chunks_dir / "regular_file.m4a").write_bytes(b"not a chunk")

        monkeypatch.setattr(utils, "CHUNKS_DIR", chunks_dir)

        removed = utils.cleanup_temp_files()
        assert removed == 3
        assert not (chunks_dir / "video1_chunk000.m4a").exists()
        assert (chunks_dir / "regular_file.m4a").exists()

    def test_cleanup_empty_dirs(self, tmp_path):
        base = tmp_path / "data"
        base.mkdir()
        (base / "empty1").mkdir()
        (base / "empty2").mkdir()
        non_empty = base / "non_empty"
        non_empty.mkdir()
        (non_empty / "file.txt").write_text("content")

        removed = utils.cleanup_empty_dirs(base)
        assert removed == 2
        assert not (base / "empty1").exists()
        assert (base / "non_empty").exists()

    def test_cleanup_all(self, tmp_path, monkeypatch):
        chunks_dir = tmp_path / "chunks"
        chunks_dir.mkdir()
        (chunks_dir / "test_chunk000.m4a").write_bytes(b"chunk")

        monkeypatch.setattr(utils, "CHUNKS_DIR", chunks_dir)

        temp_files, empty_dirs = utils.cleanup_all()
        assert temp_files == 1


class TestVideoIDExtraction:
    """Test video ID extraction and file naming."""

    def test_extract_video_id_valid_urls(self):
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=abc123_XYZ-", "abc123_XYZ-"),
            ("https://youtube.com/watch?v=test123&feature=share", "test123"),
        ]
        for url, expected_id in test_cases:
            assert pipeline.extract_video_id(url) == expected_id

    def test_extract_video_id_invalid_url(self):
        with pytest.raises(ValueError, match="Could not extract video ID"):
            pipeline.extract_video_id("https://youtube.com/invalid")

    def test_file_naming_pattern(self, tmp_path, monkeypatch):
        import re

        dl = tmp_path / "downloads"
        dl.mkdir()
        monkeypatch.setattr(pipeline, "DOWNLOAD_DIR", dl)

        video_id = "test123"
        from datetime import datetime, timezone

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        test_file = dl / f"{timestamp}_{video_id}.m4a"
        test_file.write_bytes(b"test")

        pattern = r"^\d{8}_\d{6}_[a-zA-Z0-9_-]+\.m4a$"
        assert re.match(pattern, test_file.name)
        assert video_id in test_file.name


class TestIntegrationAPI:
    """Test the integration API functions."""

    def test_get_transcript_text_exists(self, tmp_path, monkeypatch):
        tr = tmp_path / "transcripts"
        tr.mkdir()
        monkeypatch.setattr(pipeline, "TRANSCRIPT_DIR", tr)
        transcript = tr / "20250101_testid.txt"
        transcript.write_text("Hello transcript")

        result = pipeline.get_transcript_text("testid")
        assert result == "Hello transcript"

    def test_get_transcript_text_missing(self, tmp_path, monkeypatch):
        tr = tmp_path / "transcripts"
        tr.mkdir()
        monkeypatch.setattr(pipeline, "TRANSCRIPT_DIR", tr)

        result = pipeline.get_transcript_text("nonexistent")
        assert result is None

    def test_transcribe_to_text(self, tmp_path, monkeypatch):
        audio_file = tmp_path / "test.m4a"
        audio_file.write_bytes(b"small audio")

        def fake_create(model, file, response_format):
            return "transcribed text"

        monkeypatch.setattr(pipeline.openai.audio.transcriptions, "create", fake_create)

        result = pipeline.transcribe_to_text(audio_file, "vid123")
        assert result == "transcribed text"

    def test_process_url_to_transcript(self, tmp_path, monkeypatch):
        tr = tmp_path / "transcripts"
        tr.mkdir()
        monkeypatch.setattr(pipeline, "TRANSCRIPT_DIR", tr)

        transcript = tr / "20250101_testid.txt"
        transcript.write_text("existing transcript text")

        result = pipeline.process_url_to_transcript("https://www.youtube.com/watch?v=testid")
        assert result == "existing transcript text"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
