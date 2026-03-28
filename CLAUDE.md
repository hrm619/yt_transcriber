# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Transcriber is a Python pipeline that downloads YouTube videos, transcribes them using OpenAI's Whisper API, and generates summaries using GPT. The project supports both single-video processing and batch processing of multiple videos from configurable YouTube channels. It is domain-agnostic and can be used for any topic.

## Project Structure

```
yt_transcriber/
├── src/yt_transcriber/          # Main package
│   ├── pipeline.py              # Core download → transcribe → summarize pipeline
│   ├── batch.py                 # Batch processing for multiple videos
│   ├── channels.py              # YouTube channel URL fetching via API
│   ├── config.py                # Configuration and directory setup
│   ├── utils.py                 # Utility functions (cleanup, helpers)
│   └── cli.py                   # CLI entry points
├── tests/                       # Unit tests
│   ├── test_pipeline_and_process.py
│   ├── test_url_update.py
│   └── test_e2e.py              # End-to-end integration tests
├── config/                      # User configuration files
│   ├── channels.yaml            # Channel list for multi-channel fetching
│   ├── urls.txt                 # Input URLs for batch processing
│   └── prompt.txt               # GPT prompt for summaries
├── data/                        # Data storage (auto-created)
│   ├── raw/audio/               # Downloaded audio files
│   ├── raw/temp/                # Temporary audio chunks
│   ├── processed/transcripts/   # Whisper transcripts
│   └── processed/summaries/     # GPT summaries
└── pyproject.toml               # Package configuration and dependencies
```

## Core Architecture

### Three-Stage Pipeline (`src/yt_transcriber/pipeline.py`)

The main pipeline follows this flow:

1. **Download** (`download_audio`): Orchestrator that checks for existing files, extracts the download URL via yt-dlp, and downloads using HTTP Range requests.
   - Helper: `_check_existing_audio(video_id)` — returns existing audio path or None
   - Helper: `_extract_download_url(url)` — uses yt-dlp to get the best audio stream URL
   - Helper: `_download_in_chunks(download_url, output_path)` — chunked HTTP download with retry

2. **Transcribe** (`transcribe`): Orchestrator that routes to direct or chunked transcription based on file size.
   - Helper: `_transcribe_direct(audio_path)` — files under 25MB
   - Helper: `_transcribe_chunked(audio_path, video_id)` — files over 25MB
   - Helper: `_split_audio_into_chunks(audio_path, video_id, segment_length)` — ffmpeg splitting
   - Helper: `_transcribe_chunks(chunk_paths)` — transcribes and joins chunks

3. **Summarize** (`gpt_action`): Processes transcript with GPT using a domain-agnostic system prompt. The `user_prompt` parameter controls the analysis direction.

**Important**: Each stage checks for existing output files based on video ID to enable resumable processing.

### Public Integration API

Three functions provide clean programmatic access for external tools:

```python
from yt_transcriber.pipeline import (
    get_transcript_text,        # video_id -> str | None (check existing)
    transcribe_to_text,         # audio_path, video_id -> str (raw text)
    process_url_to_transcript,  # url -> str (full pipeline, returns text)
)
```

These return raw transcript text (not file paths) and do not run GPT summarization.

### Batch Processing (`src/yt_transcriber/batch.py`)

Processes multiple videos from `config/urls.txt`. Calls pipeline functions directly (not via subprocess). Uses prompt from `config/prompt.txt`.

Cookie authentication is configurable via the `YT_COOKIES_FROM_BROWSER` environment variable (default: None, meaning no cookie auth).

### Multi-Channel URL Fetcher (`src/yt_transcriber/channels.py`)

Fetches recent videos from YouTube channels using YouTube Data API v3:
- Channels loaded from `config/channels.yaml` via `load_channels_from_config()`
- Date filtering defaults to first day of current month
- Saves organized output files per channel and a combined file
- Requires `YOUTUBE_API_KEY` environment variable

### Channel Configuration (`config/channels.yaml`)

```yaml
channels:
  - name: "channel_display_name"
    url: "https://www.youtube.com/@ChannelHandle/videos"
  - name: "another_channel"
    url: "https://www.youtube.com/@AnotherHandle/videos"
```

## Development Commands

### Setup

```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # macOS/Linux

# Install package in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

### Running the Pipeline

**Single video:**
```bash
yt-transcribe "https://www.youtube.com/watch?v=VIDEO_ID"

# For private videos:
yt-transcribe "URL" --cookies-from-browser chrome
yt-transcribe "URL" --cookies-file path/to/cookies.txt

# Custom prompt:
yt-transcribe "URL" --prompt "Your custom prompt here"
```

**Batch processing:**
```bash
# 1. Add URLs to config/urls.txt (one per line)
# 2. Add prompt to config/prompt.txt
# 3. Run batch processor
yt-batch
```

**Fetch recent channel videos:**
```bash
yt-fetch-channels
```

**Fetch latest videos + batch process (all-in-one):**
```bash
yt-update
```

**Cleanup temporary files:**
```bash
yt-cleanup
```

### Testing

```bash
# Run all tests
.venv/bin/python -m pytest tests/

# Run specific test file
.venv/bin/python -m pytest tests/test_pipeline_and_process.py

# Run with verbose output
.venv/bin/python -m pytest -v tests/
```

### Linting

```bash
ruff check .
```

## Configuration

**Main config** (`src/yt_transcriber/config.py`):
- `AUDIO_FORMAT = "m4a"`: Audio format for downloads
- `WHISPER_MODEL = "whisper-1"`: OpenAI Whisper model
- `GPT_MODEL = "gpt-4o"`: GPT model for summaries
- `YT_COOKIES_FROM_BROWSER`: Optional env var for cookie auth in batch mode

**Directory structure** (auto-created on first run):
- `data/raw/audio/`: Downloaded audio files
- `data/raw/temp/`: Temporary audio chunks for >25MB files
- `data/processed/transcripts/`: Whisper transcripts
- `data/processed/summaries/`: GPT summaries
- `config/`: Channel config, URLs, and prompts

## Key Implementation Details

### Video ID Extraction and File Naming

Files are named with pattern: `{timestamp}_{video_id}.{ext}` where timestamp is `YYYYmmdd_HHMMSS` UTC format.

### Deduplication Logic

All three pipeline stages check `check_existing_files(video_id)` which searches for existing files containing the video ID using glob patterns.

### Audio Chunking for Large Files

When audio files exceed 25MB (Whisper API limit):
1. `_split_audio_into_chunks` uses ffmpeg to split into 5-minute segments
2. `_transcribe_chunks` transcribes each chunk separately
3. Transcriptions are joined with spaces

## Environment Variables

Required in `.env` file:
- `YOUTUBE_API_KEY`: For channel video fetching
- `OPENAI_API_KEY`: For Whisper and GPT API calls

Optional:
- `YT_COOKIES_FROM_BROWSER`: Browser name for cookie auth in batch mode (e.g. `chrome`)

## CLI Entry Points

Defined in `pyproject.toml` and `src/yt_transcriber/cli.py`:

- `yt-transcribe`: Single video processing
- `yt-batch`: Batch processing from config/urls.txt
- `yt-fetch-channels`: Multi-channel YouTube URL fetcher
- `yt-update`: All-in-one fetch + batch process
- `yt-cleanup`: Clean up temporary files

## Module Import Structure

```python
from yt_transcriber.pipeline import download_audio, transcribe, gpt_action
from yt_transcriber.pipeline import get_transcript_text, transcribe_to_text, process_url_to_transcript
from yt_transcriber.batch import extract_urls_from_file
from yt_transcriber.channels import fetch_videos_from_multiple_channels, load_channels_from_config
from yt_transcriber.config import DOWNLOAD_DIR, WHISPER_MODEL, GPT_MODEL
from yt_transcriber.utils import cleanup_temp_files, cleanup_all
```

## Package Management

Uses `uv` with dependencies in `pyproject.toml`:
- Production: requests, python-dotenv, yt-dlp, openai, tqdm, python-dateutil, typing-extensions, pyyaml
- Dev: pytest, ruff
