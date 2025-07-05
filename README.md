# YouTube Transcriber

A powerful Python pipeline for downloading YouTube videos, transcribing them using OpenAI's Whisper, and generating summaries or other text-based outputs using GPT.

## Features

- Download audio from YouTube videos (public or private)
- Transcribe audio using OpenAI's Whisper model
- Generate summaries or custom outputs using GPT
- Support for batch processing multiple videos
- Handles private videos using browser cookies
- Efficient audio downloading with chunked transfers
- Organized output directory structure

## Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) for package management
- FFmpeg (for audio processing)

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

3. Install dependencies:
```bash
uv pip install -r requirements.txt
```

## Usage

### Single Video Processing

```bash
python run_pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

For private videos, you can use either:
- Browser cookies:
```bash
python run_pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome
```
- Cookies file:
```bash
python run_pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-file path/to/cookies.txt
```

### Batch Processing

1. Create a `urls.txt` file with YouTube URLs (one per line)
2. Optionally create a `prompt.txt` file with your custom GPT prompt
3. Run the batch processor:
```bash
python run_batch.py
```

## Directory Structure

- `app/`: Main application code
  - `pipeline.py`: Core YouTube → Whisper → GPT pipeline
  - `batch_processor.py`: Batch processing for multiple videos
  - `config.py`: Configuration settings
- `data/`: All data storage
  - `raw/audio/`: Downloaded audio files
  - `raw/temp/`: Temporary chunk files
  - `processed/transcripts/`: Whisper transcripts
  - `processed/summaries/`: GPT-generated summaries
  - `archive/`: Archive and backup data
- `config/`: Configuration files
  - `urls.txt`: Input YouTube URLs
  - `prompt.txt`: GPT prompts
- `tests/`: Test files
- `docs/`: Documentation
- `scripts/`: Utility scripts
- `logs/`: Log files

## Configuration

The main configuration parameters are in `yt_whisper_pipeline.py`:

- `AUDIO_FORMAT`: Audio format for downloads (default: "m4a")
- `WHISPER_MODEL`: OpenAI Whisper model to use
- `GPT_MODEL`: OpenAI GPT model for text generation

## Development

This project uses:
- `ruff` for linting
- `pytest` for testing

To run tests:
```bash
pytest tests/
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here] 