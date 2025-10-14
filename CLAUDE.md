# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Transcriber is a Python pipeline that downloads YouTube videos, transcribes them using OpenAI's Whisper API, and generates summaries using GPT. The project supports both single-video processing and batch processing of multiple videos from multiple YouTube channels.

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

1. **Download** (`download_audio`): Uses yt-dlp to download audio from YouTube (m4a format)
   - Implements chunked HTTP range requests for reliable large downloads
   - Supports private videos via browser cookies or cookie files
   - Checks for existing files to avoid re-downloading

2. **Transcribe** (`transcribe`): Sends audio to OpenAI Whisper API (pipeline.py:218)
   - Automatically splits files >25MB into 5-minute chunks using ffmpeg
   - Chunks are stored in `data/raw/temp/` and combined after transcription
   - Checks for existing transcripts to avoid re-processing

3. **Summarize** (`gpt_action`): Processes transcript with GPT (pipeline.py:281)
   - System prompt configured for NFL scouting/fantasy football analysis
   - Uses GPT-4o model with temperature=0.3 for consistency
   - Checks for existing summaries to avoid re-processing

**Important**: Each stage checks for existing output files based on video ID to enable resumable processing.

### Batch Processing (`src/yt_transcriber/batch.py`)

Processes multiple videos from `config/urls.txt`. Calls the pipeline as a subprocess for each URL with shared prompt from `config/prompt.txt`.

**Note**: Currently hardcoded to use `--cookies-from-browser chrome` (batch.py:81).

### Multi-Channel URL Fetcher (`src/yt_transcriber/channels.py`)

Fetches recent videos from multiple YouTube channels using YouTube Data API v3:
- Channel list defined in `CHANNEL_URLS` dict (channels.py:37-45)
- Date filtering via `CUTOFF_DATE` (channels.py:57)
- Saves organized output files per channel and a combined file
- Requires `YOUTUBE_API_KEY` environment variable

## Development Commands

### Setup

```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # macOS/Linux

# Install package in editable mode
uv pip install -e .

# Install with dev dependencies (includes pytest, ruff)
uv pip install -e ".[dev]"

# Set up YouTube API (interactive)
python setup_api.py
```

### Running the Pipeline

After installation, you can use the CLI commands from anywhere:

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

**Alternative: Run as Python modules** (if not installed):
```bash
python -m yt_transcriber.pipeline "URL"
python -m yt_transcriber.batch
python -m yt_transcriber.channels
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_pipeline_and_process.py

# Run with verbose output
pytest -v tests/
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

**Directory structure** (auto-created on first run):
- `data/raw/audio/`: Downloaded audio files
- `data/raw/temp/`: Temporary audio chunks for >25MB files
- `data/processed/transcripts/`: Whisper transcripts
- `data/processed/summaries/`: GPT summaries
- `config/`: URLs and prompts for batch processing

## Key Implementation Details

### Video ID Extraction and File Naming

Files are named with pattern: `{timestamp}_{video_id}.{ext}` where timestamp is `YYYYmmdd_HHMMSS` UTC format. This ensures:
- Unique filenames for the same video processed at different times
- Easy sorting by processing time
- Video ID preservation for deduplication checks

### Deduplication Logic

All three pipeline stages (`download_audio`, `transcribe`, `gpt_action`) call `check_existing_files(video_id)` which searches for existing files containing the video ID in their filename using glob patterns (pipeline.py:61-88).

### Audio Chunking for Large Files

When audio files exceed 25MB (Whisper API limit), the `transcribe` function:
1. Uses ffmpeg to split audio into 5-minute segments (pipeline.py:247-252)
2. Transcribes each chunk separately
3. Joins transcriptions with spaces (pipeline.py:266)
4. Chunks are saved to `CHUNKS_DIR` with pattern `{video_id}_chunk{number}.m4a`

### Error Handling for Private Videos

When a private video is detected, the pipeline provides clear instructions about authentication options (pipeline.py:196-207) and suggests cookie-based authentication methods.

## Environment Variables

Required in `.env` file:
- `YOUTUBE_API_KEY`: For channel video fetching functionality
- `OPENAI_API_KEY`: For Whisper and GPT API calls (implicitly required by openai library)

## CLI Entry Points

The package defines five console scripts in `pyproject.toml`:

- `yt-transcribe`: Single video processing
- `yt-batch`: Batch processing from config/urls.txt
- `yt-fetch-channels`: Multi-channel YouTube URL fetcher
- `yt-update`: **All-in-one** - Fetch latest videos and batch process them
- `yt-cleanup`: Clean up temporary files and empty directories

All entry points are defined in `src/yt_transcriber/cli.py` and installed when you run `uv pip install -e .`

### Recommended Workflow

For most users, the simplest workflow is:
1. Run `yt-update` once per month to fetch and process all new videos from all channels
2. Run `yt-cleanup` periodically to clean up temporary files

For more control, you can use the individual commands (`yt-fetch-channels`, `yt-batch`, `yt-transcribe`) separately.

## Package Management

This project uses `uv` for package management with dependencies defined in `pyproject.toml`:
- Production dependencies are in the main `dependencies` array
- Development dependencies (pytest, ruff) are in `[project.optional-dependencies]`
- Install with: `uv pip install -e .` or `uv pip install -e ".[dev]"` for dev dependencies

## Module Import Structure

All modules are under the `yt_transcriber` package:

```python
from yt_transcriber.pipeline import download_audio, transcribe, gpt_action
from yt_transcriber.batch import extract_urls_from_file
from yt_transcriber.channels import fetch_videos_from_multiple_channels, CHANNEL_URLS
from yt_transcriber.config import DOWNLOAD_DIR, WHISPER_MODEL, GPT_MODEL
from yt_transcriber.utils import cleanup_temp_files, cleanup_all
```

## Testing

The project includes comprehensive unit tests and end-to-end integration tests:

**Unit tests** (`tests/test_pipeline_and_process.py`, `tests/test_url_update.py`):
- Test individual functions and components
- Mock external dependencies (APIs, filesystem)
- Fast execution for quick feedback

**End-to-end tests** (`tests/test_e2e.py`):
- Test complete workflows (download → transcribe → summarize)
- Test batch processing with multiple videos
- Test channel fetching integration
- Test utility functions
- Verify file naming patterns and deduplication logic

Run all tests with: `pytest tests/` or `pytest tests/test_e2e.py -v` for verbose output.
