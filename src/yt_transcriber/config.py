#!/usr/bin/env python3
"""
Configuration settings for yt_transcriber application.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Directory paths
DOWNLOAD_DIR = Path("data/raw/audio")
TRANSCRIPT_DIR = Path("data/processed/transcripts")
SUMMARY_DIR = Path("data/processed/summaries")
CHUNKS_DIR = Path("data/raw/temp")
CONFIG_DIR = Path("config")

# Audio settings
AUDIO_FORMAT = "m4a"

# API settings
WHISPER_MODEL = "whisper-1"
GPT_MODEL = "gpt-4o"

# Cookie authentication (optional)
YT_COOKIES_FROM_BROWSER = os.getenv("YT_COOKIES_FROM_BROWSER")

# Ensure directories exist
for folder in (DOWNLOAD_DIR, TRANSCRIPT_DIR, SUMMARY_DIR, CHUNKS_DIR, CONFIG_DIR):
    folder.mkdir(parents=True, exist_ok=True)
