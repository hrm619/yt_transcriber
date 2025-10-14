#!/usr/bin/env python3
"""
Configuration settings for yt_transcriber application.
"""

from pathlib import Path

# Directory paths
DOWNLOAD_DIR = Path("data/raw/audio")
TRANSCRIPT_DIR = Path("data/processed/transcripts")
SUMMARY_DIR = Path("data/processed/summaries")
CHUNKS_DIR = Path("data/raw/temp")

# Audio settings
AUDIO_FORMAT = "m4a"

# API settings
WHISPER_MODEL = "whisper-1"
GPT_MODEL = "gpt-5-nano"

# Ensure directories exist
for folder in (DOWNLOAD_DIR, TRANSCRIPT_DIR, SUMMARY_DIR, CHUNKS_DIR):
    folder.mkdir(parents=True, exist_ok=True)
