# YouTube Transcriber

A powerful Python pipeline for downloading YouTube videos, transcribing them using OpenAI's Whisper, and generating summaries or other text-based outputs using GPT.

## Features

- Download audio from YouTube videos (public or private)
- Transcribe audio using OpenAI's Whisper model
- Generate summaries or custom outputs using GPT
- Support for batch processing multiple videos
- Handles private videos using browser cookies
- Efficient audio downloading with chunked transfers
- **NEW**: Automated YouTube channel video fetching with date filtering
- **NEW**: YouTube Data API v3 integration for accurate metadata
- Organized output directory structure

## Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) for package management
- FFmpeg (for audio processing)
- YouTube Data API v3 key (for channel video fetching)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd yt_transcriber
```

2. Create and activate a virtual environment using uv:
```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

3. Install the package:
```bash
# Production dependencies only
uv pip install -e .

# Or with development dependencies (includes pytest, ruff)
uv pip install -e ".[dev]"
```

4. Set up YouTube Data API v3 (for channel video fetching):
```bash
python setup_api.py
```
This will guide you through getting and setting up your YouTube API key.

## Usage

After installation, you can use the CLI commands from anywhere in your terminal.

### Single Video Processing

```bash
yt-transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

For private videos, you can use either:
- Browser cookies:
```bash
yt-transcribe "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome
```
- Cookies file:
```bash
yt-transcribe "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-file path/to/cookies.txt
```

### Automated Channel Video Fetching

Fetch recent videos from YouTube channels (published after the configured cutoff date):

```bash
yt-fetch-channels
```

### Batch Processing

1. Create a `config/urls.txt` file with YouTube URLs (one per line), or use the automated fetcher above
2. Optionally create a `config/prompt.txt` file with your custom GPT prompt
3. Run the batch processor:
```bash
yt-batch
```

### Fetch & Process (All-in-One)

Fetch latest videos from all channels and process them in one command:

```bash
yt-update
```

This command:
1. Fetches videos from all configured channels (since first of current month)
2. Saves URLs to `config/all_channels_urls.txt`
3. Automatically runs batch processing on all fetched videos

### Cleanup Temporary Files

Remove temporary audio chunks and empty directories:

```bash
yt-cleanup
```

## Directory Structure

- `src/yt_transcriber/`: Main package
  - `pipeline.py`: Core YouTube → Whisper → GPT pipeline
  - `batch.py`: Batch processing for multiple videos
  - `channels.py`: YouTube channel video fetcher with date filtering
  - `config.py`: Configuration settings
  - `utils.py`: Utility functions (cleanup, helpers)
  - `cli.py`: CLI entry points
- `tests/`: Unit and integration tests
  - `test_pipeline_and_process.py`: Pipeline and batch tests
  - `test_url_update.py`: Channel fetching tests
  - `test_e2e.py`: End-to-end integration tests
- `config/`: Configuration files
  - `urls.txt`: Input YouTube URLs for batch processing
  - `prompt.txt`: GPT prompts
- `data/`: All data storage (auto-created)
  - `raw/audio/`: Downloaded audio files
  - `raw/temp/`: Temporary chunk files
  - `processed/transcripts/`: Whisper transcripts
  - `processed/summaries/`: GPT-generated summaries
  - `archive/`: Archive and backup data
- `docs/`: Documentation
- `logs/`: Log files
- `pyproject.toml`: Package configuration and dependencies
- `setup_api.py`: YouTube API setup helper

## Configuration

The main configuration parameters are in `src/yt_transcriber/config.py`:

- `AUDIO_FORMAT`: Audio format for downloads (default: "m4a")
- `WHISPER_MODEL`: OpenAI Whisper model to use (default: "whisper-1")
- `GPT_MODEL`: OpenAI GPT model for text generation (default: "gpt-4o")
- Directory paths for data storage

## Development

This project uses:
- `ruff` for linting
- `pytest` for testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_e2e.py -v

# Run with coverage
pytest tests/ --cov=yt_transcriber
```

The test suite includes:
- Unit tests for individual components
- Integration tests for the complete pipeline
- End-to-end tests for real-world workflows

## License

[Add your license here]

## Contributing

[Add contribution guidelines here] 