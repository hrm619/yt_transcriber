import sys
from pathlib import Path

import pytest

from yt_transcriber import batch as process_videos
from yt_transcriber import pipeline

# --- pipeline.extract_video_id ---


def test_extract_video_id_valid():
    url = "https://www.youtube.com/watch?v=abc123XYZ"
    assert pipeline.extract_video_id(url) == "abc123XYZ"


def test_extract_video_id_invalid():
    with pytest.raises(ValueError):
        pipeline.extract_video_id("https://youtube.com/watch")


# --- pipeline.check_existing_files ---


def test_check_existing_files(tmp_path, monkeypatch):
    dl = tmp_path / "downloads"
    dl.mkdir()
    tr = tmp_path / "transcripts"
    tr.mkdir()
    su = tmp_path / "summaries"
    su.mkdir()
    monkeypatch.setattr(pipeline, 'DOWNLOAD_DIR', dl)
    monkeypatch.setattr(pipeline, 'TRANSCRIPT_DIR', tr)
    monkeypatch.setattr(pipeline, 'SUMMARY_DIR', su)

    audio_file = dl / "20230101_testid.m4a"
    audio_file.write_text("audio")
    transcript_file = tr / "20230101_testid.txt"
    transcript_file.write_text("transcript")
    summary_file = su / "20230101_testid_gpt.txt"
    summary_file.write_text("summary")

    results = pipeline.check_existing_files("testid")
    assert results['audio'] == audio_file
    assert results['transcript'] == transcript_file
    assert results['summary'] == summary_file


# --- Mocks for download_audio ---


class DummyYDL:
    """Mock yt-dlp that creates a fake audio file on download."""

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def download(self, urls):
        # Parse the outtmpl to figure out where to write the fake file
        outtmpl = self.opts.get("outtmpl", "")
        output_path = outtmpl.replace("%(ext)s", "m4a")
        Path(output_path).write_bytes(b"TEST")


# --- pipeline.download_audio ---


def test_download_audio_existing(tmp_path, monkeypatch):
    dl = tmp_path / "downloads"
    dl.mkdir()
    monkeypatch.setattr(pipeline, 'DOWNLOAD_DIR', dl)
    existing = dl / "20230101_testid.m4a"
    existing.write_bytes(b"existing")
    result = pipeline.download_audio("https://www.youtube.com/watch?v=testid")
    assert result == existing


def test_download_audio_new(tmp_path, monkeypatch):
    dl = tmp_path / "downloads"
    dl.mkdir()
    monkeypatch.setattr(pipeline, 'DOWNLOAD_DIR', dl)
    monkeypatch.setattr(pipeline.yt_dlp, 'YoutubeDL', DummyYDL)

    result = pipeline.download_audio("https://www.youtube.com/watch?v=testid")
    assert result.exists()
    assert result.suffix == ".m4a"
    assert result.read_bytes() == b"TEST"


# --- batch (process_videos) ---


def test_extract_urls_from_file(tmp_path):
    content = """https://www.youtube.com/watch?v=abc
https://example.com
https://www.youtube.com/watch?v=def
https://www.youtube.com/watch?v=abc"""
    f = tmp_path / "urls.txt"
    f.write_text(content)
    urls = process_videos.extract_urls_from_file(str(f))
    assert urls == [
        "https://www.youtube.com/watch?v=abc",
        "https://www.youtube.com/watch?v=def",
    ]


def test_read_prompt_from_file(tmp_path):
    f = tmp_path / "prompt.txt"
    f.write_text("Hello Prompt\n")
    prompt = process_videos.read_prompt_from_file(str(f))
    assert prompt == "Hello Prompt"


# --- pipeline.transcribe ---


def test_transcribe_new(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'TRANSCRIPT_DIR', tmp_path)
    audio_file = tmp_path / "prefix_testid.m4a"
    audio_file.write_bytes(b"dummy")
    monkeypatch.setattr(
        pipeline, 'check_existing_files',
        lambda vid: {'audio': None, 'transcript': None, 'summary': None},
    )

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
    monkeypatch.setattr(
        pipeline, 'check_existing_files',
        lambda vid: {'audio': None, 'transcript': existing, 'summary': None},
    )
    result = pipeline.transcribe(Path("whatever"), "testid")
    assert result == existing


# --- pipeline.gpt_action ---


def test_gpt_action_new(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, 'SUMMARY_DIR', tmp_path)
    transcript = tmp_path / "prefix_testid.txt"
    transcript.write_text("TRANSCRIPT")
    monkeypatch.setattr(
        pipeline, 'check_existing_files',
        lambda vid: {'audio': None, 'transcript': None, 'summary': None},
    )

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
    monkeypatch.setattr(
        pipeline, 'check_existing_files',
        lambda vid: {'audio': None, 'transcript': None, 'summary': existing},
    )
    result = pipeline.gpt_action(Path("dummy"), "prompt", "testid")
    assert result == existing


# --- gpt_action uses domain-agnostic system prompt ---


def test_gpt_action_no_domain_references(tmp_path, monkeypatch):
    """Confirm gpt_action system prompt contains no NFL/fantasy references."""
    monkeypatch.setattr(pipeline, 'SUMMARY_DIR', tmp_path)
    transcript = tmp_path / "prefix_testid.txt"
    transcript.write_text("TRANSCRIPT")
    monkeypatch.setattr(
        pipeline, 'check_existing_files',
        lambda vid: {'audio': None, 'transcript': None, 'summary': None},
    )

    captured_messages = []

    class DummyMessage:
        def __init__(self, content):
            self.content = content

    class DummyChoice:
        def __init__(self):
            self.message = DummyMessage("result")

    class DummyResponse:
        def __init__(self):
            self.choices = [DummyChoice()]

    def fake_chat_create(model, messages, temperature):
        captured_messages.extend(messages)
        return DummyResponse()

    monkeypatch.setattr(pipeline.openai.chat.completions, 'create', fake_chat_create)
    pipeline.gpt_action(transcript, "prompt", "testid")

    system_content = captured_messages[0]["content"].lower()
    assert "nfl" not in system_content
    assert "fantasy" not in system_content
    assert "football" not in system_content
    assert "scouting" not in system_content


# --- pipeline.main skips already-processed ---


def test_main_skips_processed(monkeypatch, tmp_path, capsys):
    audio = tmp_path / "audio_testid.m4a"
    audio.write_bytes(b"")
    transcript = tmp_path / "audio_testid_testid.txt"
    transcript.write_text("t")
    summary = tmp_path / "audio_testid_testid_gpt.txt"
    summary.write_text("s")

    monkeypatch.setattr(pipeline, 'extract_video_id', lambda url: "testid")
    monkeypatch.setattr(
        pipeline, 'check_existing_files',
        lambda vid: {'audio': audio, 'transcript': transcript, 'summary': summary},
    )
    monkeypatch.setattr(sys, 'argv', ["prog", "https://www.youtube.com/watch?v=testid"])
    pipeline.main()
    captured = capsys.readouterr()
    assert "has already been fully processed" in captured.out


# --- batch does not use subprocess ---


def test_batch_no_subprocess():
    """Confirm batch.py does not use subprocess to call the pipeline."""
    import inspect
    source = inspect.getsource(process_videos)
    assert "subprocess" not in source
