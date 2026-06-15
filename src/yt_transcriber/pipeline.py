#!/usr/bin/env python3
"""
Pipeline: YouTube -> audio -> Whisper transcript -> GPT prompt output

Usage:
  1. For public videos:
     python -m yt_transcriber.pipeline "https://www.youtube.com/watch?v=VIDEO_ID"

  2. For private videos:
     a) Using cookies file:
        python -m yt_transcriber.pipeline "URL" --cookies-file path/to/cookies.txt

     b) Using browser cookies:
        python -m yt_transcriber.pipeline "URL" --cookies-from-browser chrome
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import openai
import yt_dlp

from .config import (
    AUDIO_FORMAT,
    CHUNKS_DIR,
    DOWNLOAD_DIR,
    GPT_MODEL,
    SUBTITLE_DIR,
    SUMMARY_DIR,
    TRANSCRIPT_DIR,
    WHISPER_MODEL,
)

DEFAULT_SYSTEM_PROMPT = (
    "You are an expert at analyzing transcripts and producing clear, structured summaries. "
    "When asked to summarize, produce concise, structured output. "
    "Provide specific examples from the transcript to support key points."
)

# Preferred caption languages, in priority order (manual + auto-generated).
SUBTITLE_LANGS = ["en", "en-US", "en-GB", "en-orig"]


def extract_video_id(url: str) -> str:
    """Extract the YouTube video ID from a URL."""
    match = re.search(r"v=([a-zA-Z0-9_-]+)", url)
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    return match.group(1)


def check_existing_files(video_id: str) -> dict:
    """Check if files for this video ID already exist.

    Returns:
        dict: Keys are 'audio', 'transcript', 'summary' with Path values or None
    """
    results: dict = {
        "audio": None,
        "transcript": None,
        "summary": None,
    }

    audio_files = list(DOWNLOAD_DIR.glob(f"*{video_id}*.{AUDIO_FORMAT}"))
    if audio_files:
        results["audio"] = audio_files[0]

    transcript_files = list(TRANSCRIPT_DIR.glob(f"*{video_id}*.txt"))
    if transcript_files:
        results["transcript"] = transcript_files[0]

    summary_files = list(SUMMARY_DIR.glob(f"*{video_id}*_gpt.txt"))
    if summary_files:
        results["summary"] = summary_files[0]

    return results


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------


def _check_existing_audio(video_id: str) -> Path | None:
    """Return existing audio path for video_id, or None."""
    existing = check_existing_files(video_id)
    return existing["audio"]


def _build_ydl_opts(
    output_template: str,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> dict:
    """Build yt-dlp options dict for audio download."""
    opts: dict = {
        "format": f"bestaudio[ext={AUDIO_FORMAT}]/bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": AUDIO_FORMAT,
                "preferredquality": "0",
            }
        ],
        "outtmpl": output_template,
        "concurrent_fragment_downloads": 4,
        "quiet": True,
        "no_warnings": True,
    }
    if cookies_file:
        opts["cookiefile"] = cookies_file
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    return opts


def download_audio(
    url: str,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> Path:
    """Download audio from a YouTube URL using yt-dlp.

    Args:
        url: YouTube video URL
        cookies_from_browser: Browser name for cookie auth (e.g. 'chrome')
        cookies_file: Path to a Netscape-format cookies file

    Returns:
        Path to the downloaded audio file

    Raises:
        FileNotFoundError: If cookies_file does not exist
        Exception: If download fails or video is private
    """
    video_id = extract_video_id(url)

    existing = _check_existing_audio(video_id)
    if existing:
        print(f"Found existing audio file: {existing}")
        return existing

    if cookies_file and not os.path.exists(cookies_file):
        raise FileNotFoundError(f"Cookies file not found: {cookies_file}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_template = str(DOWNLOAD_DIR / f"{timestamp}_{video_id}.%(ext)s")

    opts = _build_ydl_opts(out_template, cookies_from_browser, cookies_file)

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as e:
        if "Private video" in str(e):
            error_msg = (
                "Error: This video is private and requires authentication.\n"
                "Please try one of the following methods:\n"
                "1. Use --cookies-file with an exported cookies.txt file.\n"
                "2. Use --cookies-from-browser (e.g. chrome).\n"
                "Make sure you are logged into YouTube."
            )
            raise Exception(error_msg) from e
        raise

    # Find the downloaded file (extension may vary after post-processing)
    matches = list(DOWNLOAD_DIR.glob(f"{timestamp}_{video_id}.*"))
    matches = [m for m in matches if not m.suffix == ".tmp"]
    if not matches:
        raise FileNotFoundError(f"Download completed but output file not found for {video_id}")
    return matches[0]


# ---------------------------------------------------------------------------
# Subtitle helpers (lightweight path: no audio download, no Whisper cost)
# ---------------------------------------------------------------------------


def _build_subtitle_opts(
    output_template: str,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> dict:
    """Build yt-dlp options for a caption-only download (skips the audio)."""
    opts: dict = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": SUBTITLE_LANGS,
        "subtitlesformat": "vtt",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
    }
    if cookies_file:
        opts["cookiefile"] = cookies_file
    if cookies_from_browser:
        opts["cookiesfrombrowser"] = (cookies_from_browser,)
    return opts


def _parse_vtt(vtt_text: str) -> str:
    """Extract plain text from WebVTT captions.

    Drops the header, cue timings, numeric indices, and inline tags, and
    collapses the consecutive duplicate lines that YouTube auto-captions emit.
    """
    lines: list[str] = []
    for raw in vtt_text.splitlines():
        line = re.sub(r"<[^>]+>", "", raw).strip()
        if not line or "-->" in line or line.isdigit():
            continue
        if line == "WEBVTT" or line.startswith(("Kind:", "Language:", "NOTE")):
            continue
        if lines and lines[-1] == line:
            continue
        lines.append(line)
    return " ".join(lines)


def fetch_subtitles(
    url: str,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
) -> str | None:
    """Return YouTube captions for a video as plain text, or None if it has none.

    Far lighter than download_audio + Whisper — no audio transfer, no API cost.
    Prefers manual subtitles, falling back to auto-generated English variants.
    """
    video_id = extract_video_id(url)
    for stale in SUBTITLE_DIR.glob(f"{video_id}*.vtt"):
        stale.unlink()

    out_template = str(SUBTITLE_DIR / video_id)
    opts = _build_subtitle_opts(out_template, cookies_from_browser, cookies_file)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError:
        return None

    vtt_files = sorted(SUBTITLE_DIR.glob(f"{video_id}*.vtt"))
    if not vtt_files:
        return None
    return _parse_vtt(vtt_files[0].read_text()) or None


# ---------------------------------------------------------------------------
# Transcription helpers
# ---------------------------------------------------------------------------


def _split_audio_into_chunks(
    audio_path: Path, video_id: str, segment_length: int = 300
) -> list[Path]:
    """Split audio into fixed-length chunks using ffmpeg."""
    chunk_base = CHUNKS_DIR / f"{video_id}_chunk"

    for old_chunk in CHUNKS_DIR.glob(f"{video_id}_chunk*"):
        old_chunk.unlink()

    cmd = [
        "ffmpeg",
        "-i",
        str(audio_path),
        "-f",
        "segment",
        "-segment_time",
        str(segment_length),
        "-c",
        "copy",
        f"{chunk_base}%03d.{AUDIO_FORMAT}",
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return sorted(CHUNKS_DIR.glob(f"{video_id}_chunk*.{AUDIO_FORMAT}"))


def _transcribe_chunks(chunk_paths: list[Path]) -> str:
    """Transcribe a list of audio chunks and join the results."""
    transcriptions: list[str] = []
    for chunk_file in chunk_paths:
        print(f"Transcribing chunk: {chunk_file.name}")
        with open(chunk_file, "rb") as af:
            text = openai.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=af,
                response_format="text",
            )
            transcriptions.append(text)
    return " ".join(transcriptions)


def _transcribe_direct(audio_path: Path) -> str:
    """Transcribe an audio file that fits within the Whisper API size limit."""
    with open(audio_path, "rb") as af:
        return openai.audio.transcriptions.create(
            model=WHISPER_MODEL,
            file=af,
            response_format="text",
        )


def _transcribe_chunked(audio_path: Path, video_id: str) -> str:
    """Transcribe a large audio file by splitting into chunks first."""
    chunk_paths = _split_audio_into_chunks(audio_path, video_id)
    return _transcribe_chunks(chunk_paths)


def transcribe(audio_path: Path, video_id: str | None = None) -> Path:
    """Transcribe audio with Whisper and save to disk.

    Returns:
        Path to the transcript file
    """
    if not video_id:
        video_id = audio_path.stem.split("_")[-1]

    existing = check_existing_files(video_id)
    if existing["transcript"]:
        print(f"Found existing transcript: {existing['transcript']}")
        return existing["transcript"]

    file_size = audio_path.stat().st_size
    max_size = 25 * 1024 * 1024  # 25MB

    if file_size > max_size:
        print(f"Audio file size ({file_size / 1024 / 1024:.2f}MB) exceeds API limit, splitting...")
        full_transcription = _transcribe_chunked(audio_path, video_id)
    else:
        size_mb = file_size / 1024 / 1024
        print(f"Audio file size ({size_mb:.2f}MB) within API limits, transcribing directly...")
        full_transcription = _transcribe_direct(audio_path)

    out_file = TRANSCRIPT_DIR / f"{audio_path.stem}_{video_id}.txt"
    out_file.write_text(full_transcription)
    return out_file


# ---------------------------------------------------------------------------
# GPT summarization
# ---------------------------------------------------------------------------


def gpt_action(
    transcript_path: Path,
    user_prompt: str,
    video_id: str | None = None,
) -> Path:
    """Run a GPT prompt on a transcript and save the result."""
    if not video_id:
        parts = transcript_path.stem.split("_")
        video_id = parts[-1] if len(parts) > 0 else transcript_path.stem

    existing = check_existing_files(video_id)
    if existing["summary"]:
        print(f"Found existing summary: {existing['summary']}")
        return existing["summary"]

    transcript_text = transcript_path.read_text()

    response = openai.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": transcript_text},
        ],
        temperature=0.3,
    )

    summary = (response.choices[0].message.content or "").strip()
    out_file = SUMMARY_DIR / f"{transcript_path.stem}_{video_id}_gpt.txt"
    out_file.write_text(summary)
    return out_file


# ---------------------------------------------------------------------------
# Integration API
# ---------------------------------------------------------------------------


def get_transcript_text(video_id: str) -> str | None:
    """Return raw transcript text for a video ID if it exists on disk, else None."""
    existing = check_existing_files(video_id)
    if existing["transcript"]:
        return existing["transcript"].read_text()
    return None


def transcribe_to_text(audio_path: Path, video_id: str) -> str:
    """Transcribe audio and return raw transcript text (not a file path)."""
    file_size = audio_path.stat().st_size
    max_size = 25 * 1024 * 1024

    if file_size > max_size:
        return _transcribe_chunked(audio_path, video_id)
    return _transcribe_direct(audio_path)


def process_url_to_transcript(
    url: str,
    cookies_from_browser: str | None = None,
    cookies_file: str | None = None,
    prefer_subtitles: bool = True,
) -> str:
    """Full pipeline: return raw transcript text for a YouTube URL.

    Resolution order, cheapest first: an existing on-disk transcript, then
    YouTube captions, then audio download + Whisper. Pass prefer_subtitles=False
    to force the Whisper path.

    Does not run GPT summarization. Returns transcript text directly.
    """
    video_id = extract_video_id(url)

    existing_text = get_transcript_text(video_id)
    if existing_text is not None:
        return existing_text

    if prefer_subtitles:
        subtitle_text = fetch_subtitles(url, cookies_from_browser, cookies_file)
        if subtitle_text:
            return subtitle_text

    audio = download_audio(url, cookies_from_browser, cookies_file)
    return transcribe_to_text(audio, video_id)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point for single-video processing."""
    parser = argparse.ArgumentParser(
        description="YouTube -> Whisper -> GPT pipeline",
        epilog=(
            "For private videos, provide cookies for authentication.\n"
            "Use either --cookies-file or --cookies-from-browser option."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--prompt",
        "-p",
        default="Summarize the transcript in 3 key takeaways.",
        help="Prompt to apply to the transcript with GPT",
    )
    parser.add_argument(
        "--cookies-from-browser",
        help="Browser from which to read cookies (e.g. 'chrome', 'firefox', 'safari')",
        choices=["chrome", "firefox", "edge", "safari", "opera"],
        required=False,
    )
    parser.add_argument(
        "--cookies-file",
        help="Path to a cookies file from a logged-in YouTube account",
        required=False,
    )
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)

        existing_files = check_existing_files(video_id)
        if existing_files["audio"] and existing_files["transcript"] and existing_files["summary"]:
            print(f"Video {video_id} has already been fully processed.")
            print(f"Audio: {existing_files['audio']}")
            print(f"Transcript: {existing_files['transcript']}")
            print(f"Summary: {existing_files['summary']}")
            return

        audio = download_audio(
            args.url,
            cookies_from_browser=args.cookies_from_browser,
            cookies_file=args.cookies_file,
        )
        print(f"Audio saved -> {audio}")

        transcript = transcribe(audio, video_id)
        print(f"Transcript saved -> {transcript}")

        gpt_output = gpt_action(transcript, args.prompt, video_id)
        print(f"GPT output saved -> {gpt_output}")

        print("\nPipeline finished successfully.")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        is_private = "private video" in str(e).lower()
        no_cookies = not (args.cookies_file or args.cookies_from_browser)
        if is_private and no_cookies:
            print(
                "\nTip: This appears to be a private video. "
                "Try --cookies-file or --cookies-from-browser.",
                file=sys.stderr,
            )
        sys.exit(1)


if __name__ == "__main__":
    main()
