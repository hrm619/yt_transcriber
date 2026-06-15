from pathlib import Path

from yt_transcriber import pipeline

# --- pipeline._parse_vtt ---


def test_parse_vtt_strips_timings_tags_and_dups():
    vtt = (
        "WEBVTT\n"
        "Kind: captions\n"
        "Language: en\n"
        "\n"
        "00:00:00.000 --> 00:00:02.000\n"
        "<00:00:00.000><c>Hello</c> world\n"
        "\n"
        "00:00:02.000 --> 00:00:04.000\n"
        "Hello world\n"  # consecutive duplicate (auto-caption rollup)
        "\n"
        "00:00:04.000 --> 00:00:06.000\n"
        "second line\n"
    )
    assert pipeline._parse_vtt(vtt) == "Hello world second line"


def test_parse_vtt_empty():
    assert pipeline._parse_vtt("WEBVTT\n\n") == ""


# --- pipeline.fetch_subtitles ---


class DummySubsYDL:
    """Mock yt-dlp that writes a fake .vtt next to the outtmpl base."""

    written = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\ncaption text\n"

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def download(self, urls):
        base = self.opts["outtmpl"]
        Path(f"{base}.en.vtt").write_text(self.written)


def test_fetch_subtitles_success(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SUBTITLE_DIR", tmp_path)
    monkeypatch.setattr(pipeline.yt_dlp, "YoutubeDL", DummySubsYDL)
    text = pipeline.fetch_subtitles("https://www.youtube.com/watch?v=vid123")
    assert text == "caption text"


def test_fetch_subtitles_none_when_no_captions(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SUBTITLE_DIR", tmp_path)

    class NoopYDL(DummySubsYDL):
        def download(self, urls):  # video has no captions → nothing written
            pass

    monkeypatch.setattr(pipeline.yt_dlp, "YoutubeDL", NoopYDL)
    assert pipeline.fetch_subtitles("https://www.youtube.com/watch?v=vid123") is None


def test_fetch_subtitles_none_on_download_error(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SUBTITLE_DIR", tmp_path)

    class RaisingYDL(DummySubsYDL):
        def download(self, urls):
            raise pipeline.yt_dlp.utils.DownloadError("boom")

    monkeypatch.setattr(pipeline.yt_dlp, "YoutubeDL", RaisingYDL)
    assert pipeline.fetch_subtitles("https://www.youtube.com/watch?v=vid123") is None


def test_fetch_subtitles_clears_stale_vtt(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SUBTITLE_DIR", tmp_path)
    stale = tmp_path / "vid123.en.vtt"
    stale.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nold caption\n")

    class NoopYDL(DummySubsYDL):
        def download(self, urls):  # writes nothing; stale file must be gone already
            pass

    monkeypatch.setattr(pipeline.yt_dlp, "YoutubeDL", NoopYDL)
    assert pipeline.fetch_subtitles("https://www.youtube.com/watch?v=vid123") is None
    assert not stale.exists()


# --- pipeline.process_url_to_transcript resolution order ---

_URL = "https://www.youtube.com/watch?v=vid"


def _boom(*args, **kwargs):
    raise AssertionError("this path should not run")


def test_process_url_uses_existing_transcript_first(monkeypatch):
    monkeypatch.setattr(pipeline, "get_transcript_text", lambda vid: "CACHED")
    monkeypatch.setattr(pipeline, "fetch_subtitles", _boom)
    monkeypatch.setattr(pipeline, "download_audio", _boom)
    assert pipeline.process_url_to_transcript(_URL) == "CACHED"


def test_process_url_prefers_subtitles_over_whisper(monkeypatch):
    monkeypatch.setattr(pipeline, "get_transcript_text", lambda vid: None)
    monkeypatch.setattr(pipeline, "fetch_subtitles", lambda *a, **k: "SUBS")
    monkeypatch.setattr(pipeline, "download_audio", _boom)
    assert pipeline.process_url_to_transcript(_URL) == "SUBS"


def test_process_url_falls_back_to_whisper(monkeypatch, tmp_path):
    audio = tmp_path / "a.m4a"
    audio.write_bytes(b"x")
    monkeypatch.setattr(pipeline, "get_transcript_text", lambda vid: None)
    monkeypatch.setattr(pipeline, "fetch_subtitles", lambda *a, **k: None)
    monkeypatch.setattr(pipeline, "download_audio", lambda *a, **k: audio)
    monkeypatch.setattr(pipeline, "transcribe_to_text", lambda p, vid: "WHISPER")
    assert pipeline.process_url_to_transcript(_URL) == "WHISPER"


def test_process_url_prefer_subtitles_false_skips_captions(monkeypatch, tmp_path):
    audio = tmp_path / "a.m4a"
    audio.write_bytes(b"x")
    monkeypatch.setattr(pipeline, "get_transcript_text", lambda vid: None)
    monkeypatch.setattr(pipeline, "fetch_subtitles", _boom)
    monkeypatch.setattr(pipeline, "download_audio", lambda *a, **k: audio)
    monkeypatch.setattr(pipeline, "transcribe_to_text", lambda p, vid: "WHISPER")
    out = pipeline.process_url_to_transcript(_URL, prefer_subtitles=False)
    assert out == "WHISPER"
