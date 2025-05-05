import os
import pytest
from pathlib import Path
import sys

import yt_whisper_pipeline as pipeline
import process_videos

# Unit tests for yt_whisper_pipeline

def test_extract_video_id_valid():
    url = "https://www.youtube.com/watch?v=abc123XYZ"
    assert pipeline.extract_video_id(url) == "abc123XYZ"

def test_extract_video_id_invalid():
    with pytest.raises(ValueError):
        pipeline.extract_video_id("https://youtube.com/watch")


def test_check_existing_files(tmp_path, monkeypatch):
    # Setup temp directories
    dl = tmp_path / "downloads"; dl.mkdir()
    tr = tmp_path / "transcripts"; tr.mkdir()
    su = tmp_path / "summaries"; su.mkdir()
    monkeypatch.setattr(pipeline, 'DOWNLOAD_DIR', dl)
    monkeypatch.setattr(pipeline, 'TRANSCRIPT_DIR', tr)
    monkeypatch.setattr(pipeline, 'SUMMARY_DIR', su)
    # Create sample files
    audio_file = dl / "20230101_testid.m4a"; audio_file.write_text("audio")
    transcript_file = tr / "20230101_testid.txt"; transcript_file.write_text("transcript")
    summary_file = su / "20230101_testid_gpt.txt"; summary_file.write_text("summary")
    results = pipeline.check_existing_files("testid")
    assert results['audio'] == audio_file
    assert results['transcript'] == transcript_file
    assert results['summary'] == summary_file

class DummyYDL:
    def __init__(self, opts):
        pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass
    def extract_info(self, url, download=False):
        return {"formats": [{"ext": "m4a", "acodec": "codec", "abr": 128, "url": "http://example.com/audio"}]}

class FakeResponse:
    def __init__(self, content, headers, status_code=206):
        self._content = content
        self.headers = headers
        self.status_code = status_code
    def iter_content(self, chunk_size=8192):
        yield self._content

class FakeSession:
    def __init__(self):
        pass
    def get(self, url, headers, stream, timeout):
        # single chunk response
        headers = {"Content-Range": "bytes 0-3/4"}
        return FakeResponse(b"TEST", headers)


def test_download_audio_existing(tmp_path, monkeypatch):
    # Setup existing audio
    dl = tmp_path / "downloads"; dl.mkdir()
    monkeypatch.setattr(pipeline, 'DOWNLOAD_DIR', dl)
    url = "https://www.youtube.com/watch?v=testid"
    existing = dl / "20230101_testid.m4a"; existing.write_bytes(b"existing")
    result = pipeline.download_audio(url)
    assert result == existing


def test_download_audio_chunked(tmp_path, monkeypatch):
    # Setup directories
    dl = tmp_path / "downloads"; dl.mkdir()
    monkeypatch.setattr(pipeline, 'DOWNLOAD_DIR', dl)
    # Patch YoutubeDL and requests.Session
    monkeypatch.setattr(pipeline.yt_dlp, 'YoutubeDL', DummyYDL)
    monkeypatch.setattr(pipeline.requests, 'Session', lambda: FakeSession())
    url = "https://www.youtube.com/watch?v=testid"
    result = pipeline.download_audio(url)
    assert result.exists()
    assert result.suffix == ".m4a"
    assert result.read_bytes() == b"TEST"

# Unit tests for process_videos

def test_extract_urls_from_file(tmp_path):
    content = """https://www.youtube.com/watch?v=abc
https://example.com
https://www.youtube.com/watch?v=def
https://www.youtube.com/watch?v=abc"""
    f = tmp_path / "urls.txt"; f.write_text(content)
    urls = process_videos.extract_urls_from_file(str(f))
    assert urls == ["https://www.youtube.com/watch?v=abc", "https://www.youtube.com/watch?v=def"]


def test_read_prompt_from_file(tmp_path):
    f = tmp_path / "prompt.txt"; f.write_text("Hello Prompt\n")
    prompt = process_videos.read_prompt_from_file(str(f))
    assert prompt == "Hello Prompt"


def test_extract_video_id_process():
    assert process_videos.extract_video_id("https://www.youtube.com/watch?v=xyz123") == "xyz123"
    assert process_videos.extract_video_id("no-id") is None

# Tests for transcribe and gpt_action

def test_transcribe_new(tmp_path, monkeypatch):
    # Setup transcript directory and audio file
    monkeypatch.setattr(pipeline, 'TRANSCRIPT_DIR', tmp_path)
    audio_file = tmp_path / "prefix_testid.m4a"
    audio_file.write_bytes(b"dummy")
    # No existing transcript
    monkeypatch.setattr(pipeline, 'check_existing_files', lambda vid: {'audio': None, 'transcript': None, 'summary': None})
    # Stub Whisper API
    def fake_create(model, file, response_format):
        return "TRANSCRIPT RESULT"
    monkeypatch.setattr(pipeline.openai.audio.transcriptions, 'create', fake_create)
    result = pipeline.transcribe(audio_file, "testid")
    assert result.exists()
    assert result.name.endswith("_testid.txt")
    assert result.read_text() == "TRANSCRIPT RESULT"


def test_transcribe_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'TRANSCRIPT_DIR', tmp_path)
    existing = tmp_path / "any_testid.txt"
    existing.write_text("text")
    # Simulate existing transcript
    monkeypatch.setattr(pipeline, 'check_existing_files', lambda vid: {'audio': None, 'transcript': existing, 'summary': None})
    result = pipeline.transcribe(Path("whatever"), "testid")
    assert result == existing


def test_gpt_action_new(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'SUMMARY_DIR', tmp_path)
    transcript = tmp_path / "prefix_testid.txt"
    transcript.write_text("TRANSCRIPT")
    # No existing summary
    monkeypatch.setattr(pipeline, 'check_existing_files', lambda vid: {'audio': None, 'transcript': None, 'summary': None})
    # Stub GPT API
    class DummyMessage:
        def __init__(self, content):
            self.content = content
    class DummyChoice:
        def __init__(self):
            self.message = DummyMessage("SUMMARY RESULT")
    class DummyResponse:
        def __init__(self):
            self.choices = [DummyChoice()]
    def fake_chat_create(model, messages, temperature):
        return DummyResponse()
    monkeypatch.setattr(pipeline.openai.chat.completions, 'create', fake_chat_create)
    result = pipeline.gpt_action(transcript, "prompt", "testid")
    assert result.exists()
    assert result.read_text() == "SUMMARY RESULT"


def test_gpt_action_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'SUMMARY_DIR', tmp_path)
    existing = tmp_path / "prefix_testid_gpt.txt"
    existing.write_text("prev")
    # Simulate existing summary
    monkeypatch.setattr(pipeline, 'check_existing_files', lambda vid: {'audio': None, 'transcript': None, 'summary': existing})
    result = pipeline.gpt_action(Path("dummy"), "prompt", "testid")
    assert result == existing


def test_main_skips_processed(monkeypatch, tmp_path, capsys):
    # Setup existing processed files
    audio = tmp_path / "audio_testid.m4a"; audio.write_bytes(b"")
    transcript = tmp_path / "audio_testid_testid.txt"; transcript.write_text("t")
    summary = tmp_path / "audio_testid_testid_gpt.txt"; summary.write_text("s")
    # Stub pipeline functions
    monkeypatch.setattr(pipeline, 'extract_video_id', lambda url: "testid")
    monkeypatch.setattr(pipeline, 'check_existing_files', lambda vid: {'audio': audio, 'transcript': transcript, 'summary': summary})
    # Simulate CLI invocation
    monkeypatch.setattr(sys, 'argv', ["prog", "https://www.youtube.com/watch?v=testid"])
    result = pipeline.main()
    captured = capsys.readouterr()
    assert "has already been fully processed" in captured.out
    assert result is None 