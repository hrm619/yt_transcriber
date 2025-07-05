#!/usr/bin/env python3
"""
Pipeline: YouTube → audio → Whisper transcript → GPT prompt output
Author: ChatGPT (April 2025)

Usage:
  1. For public videos:
     python yt_whisper_pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID"
  
  2. For private videos:
     a) Using cookies file:
        python yt_whisper_pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-file path/to/cookies.txt
     
     b) Using browser cookies:
        python yt_whisper_pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome
        
  Note: To export cookies from your browser, use a browser extension like "Get cookies.txt" 
  and save the exported cookies to a file.
"""

import argparse
import os
import sys
import tempfile
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import yt_dlp
import openai
from tqdm import tqdm
import requests
import time


# ---------- Configuration ----------------------------------------------------
DOWNLOAD_DIR = Path("data/raw/audio")
TRANSCRIPT_DIR = Path("data/processed/transcripts")
SUMMARY_DIR = Path("data/processed/summaries")
CHUNKS_DIR = Path("data/raw/temp")

AUDIO_FORMAT   = "m4a"           # Smaller than mp3, no re‑encoding step needed
WHISPER_MODEL  = "whisper-1"     # OpenAI's latest English/Multilingual model
GPT_MODEL      = "gpt-4o"  # More widely available model
# -----------------------------------------------------------------------------

# Build folders on first run
for folder in (DOWNLOAD_DIR, TRANSCRIPT_DIR, SUMMARY_DIR, CHUNKS_DIR):
    folder.mkdir(exist_ok=True)


def extract_video_id(url: str) -> str:
    """Extract the YouTube video ID from a URL."""
    match = re.search(r'v=([a-zA-Z0-9_-]+)', url)
    if not match:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    return match.group(1)


def check_existing_files(video_id: str) -> dict:
    """Check if files for this video ID already exist.
    
    Returns:
        dict: Keys are 'audio', 'transcript', 'summary' with Path values or None
    """
    results = {
        'audio': None,
        'transcript': None,
        'summary': None
    }
    
    # Check for audio file
    audio_files = list(DOWNLOAD_DIR.glob(f"*{video_id}*.{AUDIO_FORMAT}"))
    if audio_files:
        results['audio'] = audio_files[0]
    
    # Check for transcript
    transcript_files = list(TRANSCRIPT_DIR.glob(f"*{video_id}*.txt"))
    if transcript_files:
        results['transcript'] = transcript_files[0]
        
    # Check for summary
    summary_files = list(SUMMARY_DIR.glob(f"*{video_id}*_gpt.txt"))
    if summary_files:
        results['summary'] = summary_files[0]
        
    return results


def download_audio(url: str, cookies_from_browser=None, cookies_file=None) -> Path:
    """
    Download audio with yt‑dlp (high‑performance settings).
    
    Args:
        url: YouTube video URL
        cookies_from_browser: Browser from which to read cookies (e.g., 'chrome')
        cookies_file: Path to a cookies file from a logged-in YouTube account
        
    Returns:
        Path to the downloaded audio file
        
    Raises:
        Exception: If the download fails or the video is private and requires authentication
    """
    video_id = extract_video_id(url)
    
    # Check for existing files
    existing_files = check_existing_files(video_id)
    if existing_files['audio']:
        print(f"Found existing audio file: {existing_files['audio']}")
        return existing_files['audio']
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outfile   = DOWNLOAD_DIR / f"{timestamp}_{video_id}.%(ext)s"

    ydl_opts = {
        # Grab only the best audio (no video) in desired container
        "format": f"bestaudio[ext={AUDIO_FORMAT}]/bestaudio/best",
        # Write directly, don't re‑mux unless absolutely required
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": AUDIO_FORMAT,
            "preferredquality": "0",  # best
        }],
        "outtmpl": str(outfile),
        # Speed tweaks
        "concurrent_fragment_downloads": 4,
        "quiet": True,
        "no_warnings": True,
        # Progress hook for tqdm
        "progress_hooks": [lambda d: _tqdm_hook(d)],
    }

    if cookies_file:
        if not os.path.exists(cookies_file):
            raise FileNotFoundError(f"Cookies file not found: {cookies_file}")
        ydl_opts["cookiefile"] = cookies_file
        print(f"Using cookies from file: {cookies_file}")

    if cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_from_browser,)
        print(f"Using cookies from browser: {cookies_from_browser}")

    global _pbar
    _pbar = tqdm(unit="B", unit_scale=True, desc="Download")

    try:
        # Manual chunked download with HTTP Range headers
        with yt_dlp.YoutubeDL({"format": f"bestaudio[ext={AUDIO_FORMAT}]/bestaudio/best", "quiet": True}) as extractor:
            info = extractor.extract_info(url, download=False)
        formats = info.get("formats", [])
        best_formats = [f for f in formats if f.get("ext") == AUDIO_FORMAT and f.get("acodec") != "none"]
        if best_formats:
            best = max(best_formats, key=lambda f: f.get("abr") or 0)
            download_url = best.get("url")
        else:
            download_url = info.get("url")

        tmp_path = DOWNLOAD_DIR / f"{timestamp}_{video_id}.tmp"
        session = requests.Session()
        chunk_size = 256 * 1024  # 256 KB
        start = 0
        total = None
        while True:
            end = start + chunk_size - 1
            headers = {"Range": f"bytes={start}-{end}"}
            retries = 0
            while True:
                try:
                    resp = session.get(download_url, headers=headers, stream=True, timeout=10)
                    if resp.status_code not in (200, 206):
                        raise Exception(f"Unexpected status code {resp.status_code}")
                    break
                except Exception:
                    retries += 1
                    if retries > 3:
                        raise
                    time.sleep(2 ** retries)
            if resp.status_code == 206:
                content_range = resp.headers.get("Content-Range")
                if content_range:
                    total = int(content_range.split("/")[-1])
            with open(tmp_path, "ab") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            if total is None or end >= total - 1:
                break
            start = end + 1

        final_path = DOWNLOAD_DIR / f"{timestamp}_{video_id}.{AUDIO_FORMAT}"
        tmp_path.rename(final_path)
        return final_path
    except yt_dlp.utils.DownloadError as e:
        if "Private video" in str(e):
            error_msg = (
                "Error: This video is private and requires authentication.\n"
                "Please try one of the following methods:\n"
                "1. Export cookies from your browser using an extension like 'Get cookies.txt' "
                "and use the --cookies-file option.\n"
                "2. Use the --cookies-from-browser option to use cookies directly from your browser.\n"
                "Example: --cookies-from-browser chrome\n"
                "Note: Make sure you are logged into the YouTube account that has access to this video."
            )
            raise Exception(error_msg) from e
        raise

    _pbar.close()


def _tqdm_hook(d):
    if d["status"] == "downloading":
        _pbar.total = d.get("total_bytes") or d.get("total_bytes_estimate")
        _pbar.update(d.get("downloaded_bytes", 0) - _pbar.n)


def transcribe(audio_path: Path, video_id: str = None) -> Path:
    """Transcribe with Whisper via the OpenAI API."""
    # Extract video_id from audio filename if not provided
    if not video_id:
        video_id = audio_path.stem.split('_')[-1]
    
    # Check for existing transcript
    existing_files = check_existing_files(video_id)
    if existing_files['transcript']:
        print(f"Found existing transcript: {existing_files['transcript']}")
        return existing_files['transcript']
    
    # Get file size and determine if we need to split it
    file_size = audio_path.stat().st_size
    max_size = 25 * 1024 * 1024  # 25MB, Whisper API limit
    
    if file_size > max_size:
        print(f"Audio file size ({file_size/1024/1024:.2f}MB) exceeds API limit, splitting...")
        # Use ffmpeg to split the audio file into 5-minute chunks
        segment_length = 300  # 5 minutes in seconds
        
        transcriptions = []
        chunk_base = CHUNKS_DIR / f"{video_id}_chunk"
        
        # Remove any existing chunks
        for old_chunk in CHUNKS_DIR.glob(f"{video_id}_chunk*"):
            old_chunk.unlink()
        
        # Split the audio using ffmpeg
        cmd = [
            "ffmpeg", "-i", str(audio_path), "-f", "segment", 
            "-segment_time", str(segment_length), "-c", "copy",
            f"{chunk_base}%03d.{AUDIO_FORMAT}"
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Transcribe each chunk
        for chunk_file in sorted(CHUNKS_DIR.glob(f"{video_id}_chunk*.{AUDIO_FORMAT}")):
            print(f"Transcribing chunk: {chunk_file.name}")
            with open(chunk_file, "rb") as af:
                transcription = openai.audio.transcriptions.create(
                    model=WHISPER_MODEL,
                    file=af,
                    response_format="text",
                )
                transcriptions.append(transcription)
        
        # Combine all transcriptions
        full_transcription = " ".join(transcriptions)
    else:
        print(f"Audio file size ({file_size/1024/1024:.2f}MB) within API limits, transcribing directly...")
        with open(audio_path, "rb") as af:
            full_transcription = openai.audio.transcriptions.create(
                model=WHISPER_MODEL,
                file=af,
                response_format="text",
            )

    out_file = TRANSCRIPT_DIR / f"{audio_path.stem}_{video_id}.txt"
    out_file.write_text(full_transcription)
    return out_file


def gpt_action(transcript_path: Path, user_prompt: str, video_id: str = None) -> Path:
    """Run an arbitrary GPT prompt on the transcript."""
    # Extract video_id from transcript filename if not provided
    if not video_id:
        parts = transcript_path.stem.split('_')
        video_id = parts[-1] if len(parts) > 0 else transcript_path.stem
    
    # Check for existing summary
    existing_files = check_existing_files(video_id)
    if existing_files['summary']:
        print(f"Found existing summary: {existing_files['summary']}")
        return existing_files['summary']
    
    # System instructions encourage the model to behave deterministically
    system_prompt = (
        "You are an expert in translating transcripts to clear summaries."
        "You are an NFL scouting expert, with a focus on fantasy impact."
        "When asked to summarize, produce concise, structured bullet points. Provide examples when possible to back up points."
    )

    transcript_text = transcript_path.read_text()

    response = openai.chat.completions.create(
        model=GPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
            {"role": "assistant", "content": transcript_text},
        ],
        temperature=0.3,
    )

    summary = response.choices[0].message.content.strip()
    out_file = SUMMARY_DIR / f"{transcript_path.stem}_{video_id}_gpt.txt"
    out_file.write_text(summary)
    return out_file


def main():
    parser = argparse.ArgumentParser(
        description="YouTube ➜ Whisper ➜ GPT pipeline",
        epilog=(
            "For private videos, you need to provide cookies for authentication.\n"
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
        required=False
    )
    parser.add_argument(
        "--cookies-file",
        help="Path to a cookies file from a logged-in YouTube account",
        required=False
    )
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
        
        # Check for existing files
        existing_files = check_existing_files(video_id)
        
        if existing_files['audio'] and existing_files['transcript'] and existing_files['summary']:
            print(f"Video {video_id} has already been fully processed.")
            print(f"Audio: {existing_files['audio']}")
            print(f"Transcript: {existing_files['transcript']}")
            print(f"Summary: {existing_files['summary']}")
            return
        
        audio = download_audio(
            args.url,
            cookies_from_browser=args.cookies_from_browser,
            cookies_file=args.cookies_file
        )
        print(f"Audio saved → {audio}")

        transcript = transcribe(audio, video_id)
        print(f"Transcript saved → {transcript}")

        gpt_output = gpt_action(transcript, args.prompt, video_id)
        print(f"GPT output saved → {gpt_output}")

        print("\n✅  Pipeline finished successfully.")
    except FileNotFoundError as e:
        print(f"❌  Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌  Error: {e}", file=sys.stderr)
        # If the error is about a private video and no cookies were provided, 
        # suggest using cookies
        if "private video" in str(e).lower() and not (args.cookies_file or args.cookies_from_browser):
            print("\nTip: This appears to be a private video. Try using --cookies-file or --cookies-from-browser option.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
